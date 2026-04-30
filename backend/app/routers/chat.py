import json
import logging
import time as _time
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas.models import ChatRequest, Chunk, CitationEvent, ErrorEvent, TokenEvent
from app.services import llm_client, rag_client

logger = logging.getLogger(__name__)
router = APIRouter()

SYSTEM_PROMPT_TEMPLATE = """\
Сіз пайдаланушының құжаттарына негізделген сұрақтарға жауап беретін көмекші жүйесіз.
Тек берілген контекстке сүйеніп жауап беріңіз. Егер контекстте жауап болмаса, соны ашық айтыңыз.

You are a helpful assistant that answers questions based on the user's uploaded documents.
Answer ONLY using the provided context. If the answer cannot be found in the context, say so clearly.

Context:
{context}
"""


def _build_system_prompt(chunks: list[Chunk], custom: str | None) -> str:
    if custom:
        return custom
    if not chunks:
        return (
            "You are a helpful assistant. "
            "The user has no documents indexed yet — let them know and ask them to upload documents first."
        )
    context = "\n\n".join(
        f"[{i+1}] (source: {c.source}, score: {c.score:.3f})\n{c.content}"
        for i, c in enumerate(chunks)
    )
    return SYSTEM_PROMPT_TEMPLATE.format(context=context)


async def _stream(request: ChatRequest, app_state) -> AsyncIterator[str]:
    """Core streaming generator: retrieve → build prompt → stream LLM → emit citations."""

    def sse(event: dict) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    # 1. Retrieve chunks
    rag_start = _time.monotonic()
    try:
        chunks = await rag_client.search(
            user_id=request.user_id,
            query=request.message,
            top_k=request.top_k,
            client=app_state.rag_http,
        )
    except RuntimeError as e:
        yield sse(ErrorEvent(message=str(e)).model_dump())
        return
    rag_time = round(_time.monotonic() - rag_start, 3)
    yield sse({"type": "timing", "rag_time": rag_time})

    # 2. Build messages
    system = _build_system_prompt(chunks, request.system_prompt)
    messages = [{"role": "system", "content": system}]
    for m in request.history:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": request.message})

    # 3. Stream LLM tokens — use per-request override URL/model if provided
    if request.llm_url:
        llm_http = httpx.AsyncClient(
            base_url=request.llm_url,
            timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0),
        )
    else:
        llm_http = app_state.llm_http
    llm_model = request.llm_model or settings.qolda_model

    try:
        async for token in llm_client.stream_completion(
            messages=messages,
            client=llm_http,
            model=llm_model,
            max_tokens=settings.qolda_max_tokens,
            temperature=settings.qolda_temperature,
        ):
            yield sse(TokenEvent(text=token).model_dump())
    except RuntimeError as e:
        yield sse(ErrorEvent(message=str(e)).model_dump())
        return
    finally:
        if request.llm_url:
            await llm_http.aclose()

    # 4. Emit citations
    yield sse(CitationEvent(chunks=chunks).model_dump())
    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(request: ChatRequest, req: Request) -> StreamingResponse:
    logger.info("Chat request: user=%s query=%r top_k=%d", request.user_id, request.message[:60], request.top_k)
    return StreamingResponse(
        _stream(request, req.app.state),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
