import logging
from typing import List

import httpx

from app.schemas.models import Chunk

logger = logging.getLogger(__name__)


async def search(
    user_id: str,
    query: str,
    top_k: int,
    client: httpx.AsyncClient,
) -> List[Chunk]:
    """Retrieve top-k relevant chunks from the RAG API."""
    try:
        resp = await client.post(
            f"/api/users/{user_id}/search",
            json={"query": query, "top_k": top_k},
        )
        resp.raise_for_status()
    except httpx.ConnectError:
        raise RuntimeError("RAG API is unreachable. Is it running on port 8034?")
    except httpx.TimeoutException:
        raise RuntimeError("RAG API timed out during search.")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"RAG API error {e.response.status_code}: {e.response.text}")

    results = resp.json().get("results", [])
    chunks = []
    for r in results:
        source = (
            r.get("metadata", {}).get("file_name")
            or r.get("metadata", {}).get("filename")
            or "unknown"
        )
        chunks.append(Chunk(
            content=r["content"],
            score=r["score"],
            source=source,
            metadata=r.get("metadata", {}),
        ))

    logger.info("Retrieved %d chunks for user=%s query=%r", len(chunks), user_id, query[:60])
    return chunks
