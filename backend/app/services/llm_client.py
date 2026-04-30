import json
import logging
from typing import AsyncIterator, List

import httpx

logger = logging.getLogger(__name__)


async def stream_completion(
    messages: List[dict],
    client: httpx.AsyncClient,
    model: str,
    max_tokens: int,
    temperature: float,
) -> AsyncIterator[str]:
    """Stream tokens from Qolda /v1/chat/completions."""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    try:
        async with client.stream("POST", "/v1/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    text = delta.get("content")
                    if text:
                        yield text
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
    except httpx.ConnectError:
        raise RuntimeError("Qolda LLM is unreachable. Is it running on port 23333?")
    except httpx.TimeoutException:
        raise RuntimeError("Qolda LLM timed out. Try a shorter query or fewer tokens.")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Qolda error {e.response.status_code}: {e.response.text}")
