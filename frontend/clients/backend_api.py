import json
import logging
from typing import Iterator, List, Tuple

import httpx

logger = logging.getLogger(__name__)


class BackendApiClient:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    def stream_chat(
        self,
        user_id: str,
        message: str,
        history: List[dict],
        top_k: int = 5,
        llm_url: str | None = None,
        llm_model: str | None = None,
    ) -> Iterator[Tuple[str, List[dict]]]:
        """
        Yields (accumulated_answer, citations) tuples as tokens arrive.
        citations is [] until the final citation event.
        """
        payload = {
            "user_id": user_id,
            "message": message,
            "history": history,
            "top_k": top_k,
        }
        if llm_url:
            payload["llm_url"] = llm_url
        if llm_model:
            payload["llm_model"] = llm_model

        accumulated = ""
        citations = []

        with httpx.Client(timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)) as client:
            try:
                with client.stream("POST", f"{self._base_url}/chat", json=payload) as resp:
                    if resp.status_code != 200:
                        resp.read()
                        logger.error("Backend %s: %s", resp.status_code, resp.text)
                        yield f"⚠️ Backend error {resp.status_code}: {resp.text}", []
                        return
                    for line in resp.iter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if data == "[DONE]":
                            break
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        etype = event.get("type")
                        if etype == "token":
                            accumulated += event.get("text", "")
                            yield accumulated, citations
                        elif etype == "citations":
                            citations = event.get("chunks", [])
                            yield accumulated, citations
                        elif etype == "error":
                            error_msg = event.get("message", "Unknown error")
                            logger.error("Backend error: %s", error_msg)
                            yield f"⚠️ Error: {error_msg}", citations
                            return

            except httpx.ConnectError:
                yield "⚠️ Cannot connect to backend. Is it running on port 8035?", []
            except httpx.TimeoutException:
                yield "⚠️ Request timed out.", citations
            except httpx.HTTPStatusError as e:
                yield f"⚠️ Backend error {e.response.status_code}", []
