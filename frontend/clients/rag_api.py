import logging
import time
from pathlib import Path
from typing import List

import httpx

logger = logging.getLogger(__name__)


class RagApiClient:
    def __init__(self, base_url: str, api_key: str):
        self._client = httpx.Client(
            base_url=base_url,
            headers={"X-Api-Key": api_key},
            timeout=httpx.Timeout(connect=5.0, read=120.0, write=60.0, pool=5.0),
        )

    def upload_documents(self, user_id: str, file_paths: List[str]) -> dict:
        """Upload files and return the response (indexing runs in background)."""
        files = []
        handles = []
        try:
            for path in file_paths:
                f = open(path, "rb")
                handles.append(f)
                files.append(("files", (Path(path).name, f, "application/octet-stream")))
            resp = self._client.post(f"/api/users/{user_id}/documents/upload", files=files)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Upload failed ({e.response.status_code}): {e.response.text}")
        finally:
            for f in handles:
                f.close()

    def list_documents(self, user_id: str) -> List[dict]:
        """List documents. Each item has: filename, status, row_count, error."""
        try:
            resp = self._client.get(f"/api/users/{user_id}/documents")
            resp.raise_for_status()
            data = resp.json()
            return data.get("documents", [])
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"List failed ({e.response.status_code}): {e.response.text}")

    def delete_documents(self, user_id: str, document_ids: List[str]) -> dict:
        """Delete documents by their document_ids."""
        try:
            resp = self._client.delete(
                f"/api/users/{user_id}/documents",
                json={"document_ids": document_ids},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Delete failed ({e.response.status_code}): {e.response.text}")

    def reindex_all(self, user_id: str) -> dict:
        """Trigger re-indexing of all uploaded files."""
        try:
            resp = self._client.post(f"/api/users/{user_id}/documents/reindex")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Reindex failed ({e.response.status_code}): {e.response.text}")

    def poll_until_done(self, user_id: str, timeout: int = 600) -> List[dict]:
        """
        Poll /documents until all docs leave 'indexing' state.
        Returns final document list. Raises RuntimeError on timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            docs = self.list_documents(user_id)
            if not docs:
                return docs
            if all(d.get("status") != "indexing" for d in docs):
                return docs
            time.sleep(3)
        raise RuntimeError(f"Indexing did not complete within {timeout}s")
