from pydantic import BaseModel
from typing import Literal, List


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    user_id: str
    message: str
    history: List[ChatMessage] = []
    top_k: int = 5
    system_prompt: str | None = None
    llm_url: str | None = None       # override LLM endpoint URL
    llm_model: str | None = None     # override model name


class Chunk(BaseModel):
    content: str
    score: float
    source: str
    metadata: dict = {}


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    text: str


class CitationEvent(BaseModel):
    type: Literal["citations"] = "citations"
    chunks: List[Chunk]


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str
