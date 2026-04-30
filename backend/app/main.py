import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create shared httpx clients once at startup
    app.state.rag_http = httpx.AsyncClient(
        base_url=settings.rag_api_url,
        headers={"X-Api-Key": settings.rag_api_key},
        timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
    )
    app.state.llm_http = httpx.AsyncClient(
        base_url=settings.qolda_url,
        timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0),
    )
    logger.info("Started — RAG=%s  LLM=%s", settings.rag_api_url, settings.qolda_url)
    yield
    await app.state.rag_http.aclose()
    await app.state.llm_http.aclose()
    logger.info("Shutdown — HTTP clients closed")


app = FastAPI(
    title="Qolda UI Backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error("422 validation error — body: %s — errors: %s", body.decode()[:500], exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


app.include_router(chat.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
