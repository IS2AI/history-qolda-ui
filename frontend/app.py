import logging
import os
import time
from pathlib import Path
from typing import List

import gradio as gr
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from clients.backend_api import BackendApiClient
from clients.rag_api import RagApiClient
from utils.formatting import format_citations, history_to_messages

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ── Clients ───────────────────────────────────────────────────────────────────
rag_client = RagApiClient(
    base_url=os.getenv("RAG_API_URL", "http://localhost:8034"),
    api_key=os.getenv("RAG_API_KEY", ""),
)
backend_client = BackendApiClient(
    base_url=os.getenv("BACKEND_URL", "http://localhost:8035"),
)

STATUS_EMOJI = {"indexing": "⏳", "completed": "✅", "failed": "❌"}

MODELS = {
    "Qolda (issai/Qolda) — port 23333": {
        "url": "http://localhost:23333",
        "model": "issai/Qolda",
    },
    "Qolda-sft (qolda-internvl-sft-9273) — port 23334": {
        "url": "http://localhost:23334",
        "model": "/shared/home/galammadin.askar/.cache/huggingface/hub/qolda-sft-9273",
    },
}


def _docs_to_rows(docs: List[dict]) -> list:
    rows = []
    for d in docs:
        status = d.get("status", "?")
        emoji = STATUS_EMOJI.get(status, "❓")
        chunks = d.get("row_count", 0)
        error = d.get("error") or ""
        label = f"{emoji} {status}" + (f" — {error[:60]}" if error else "")
        rows.append([d.get("filename", ""), d.get("id", ""), chunks, label])
    return rows


# ── Handlers ──────────────────────────────────────────────────────────────────

def refresh_docs(user_id: str):
    if not user_id.strip():
        return [], "⚠️ Enter a User ID first."
    try:
        docs = rag_client.list_documents(user_id.strip())
        rows = _docs_to_rows(docs)
        indexing = sum(1 for d in docs if d.get("status") == "indexing")
        completed = sum(1 for d in docs if d.get("status") == "completed")
        failed = sum(1 for d in docs if d.get("status") == "failed")
        parts = [f"✅ {completed} ready"]
        if indexing:
            parts.append(f"⏳ {indexing} indexing")
        if failed:
            parts.append(f"❌ {failed} failed")
        return rows, "  |  ".join(parts) if docs else "No documents yet."
    except Exception as e:
        logger.error("refresh_docs error: %s", e)
        return [], f"❌ {e}"


def upload_docs(user_id: str, files):
    """Upload files then stream progress until indexing finishes."""
    if not user_id.strip():
        yield "⚠️ Enter a User ID first.", []
        return
    if not files:
        yield "⚠️ Select at least one file.", []
        return

    uid = user_id.strip()
    paths = [f.name for f in files] if hasattr(files[0], "name") else list(files)

    # Upload
    yield f"⬆️ Uploading {len(paths)} file(s)…", []
    try:
        result = rag_client.upload_documents(uid, paths)
    except Exception as e:
        logger.error("upload_docs error: %s", e)
        yield f"❌ Upload failed: {e}", []
        return

    n = len(result.get("documents", paths))
    yield f"✅ Uploaded {n} file(s). Indexing started — please wait…", []

    # Poll until all docs leave "indexing" state (max 10 min)
    deadline = time.time() + 600
    while time.time() < deadline:
        time.sleep(4)
        try:
            docs = rag_client.list_documents(uid)
        except Exception:
            continue

        rows = _docs_to_rows(docs)
        indexing = sum(1 for d in docs if d.get("status") == "indexing")
        completed = sum(1 for d in docs if d.get("status") == "completed")
        failed = sum(1 for d in docs if d.get("status") == "failed")

        if indexing == 0:
            msg = f"✅ Done! {completed} ready"
            if failed:
                msg += f", ❌ {failed} failed"
            yield msg, rows
            return

        yield (
            f"⏳ Indexing… {completed} done, {indexing} in progress, {failed} failed",
            rows,
        )

    # Timeout
    rows, msg = refresh_docs(uid)
    yield f"⚠️ Indexing still running (timeout). Check status with Refresh.", rows


def reindex_docs(user_id: str):
    """Trigger re-indexing of all uploaded files."""
    if not user_id.strip():
        yield "⚠️ Enter a User ID first.", []
        return

    uid = user_id.strip()
    yield "🔄 Triggering re-index…", []
    try:
        rag_client.reindex_all(uid)
    except Exception as e:
        yield f"❌ Re-index failed: {e}", []
        return

    yield "⏳ Re-indexing started…", []

    deadline = time.time() + 600
    while time.time() < deadline:
        time.sleep(4)
        try:
            docs = rag_client.list_documents(uid)
        except Exception:
            continue

        rows = _docs_to_rows(docs)
        indexing = sum(1 for d in docs if d.get("status") == "indexing")
        completed = sum(1 for d in docs if d.get("status") == "completed")
        failed = sum(1 for d in docs if d.get("status") == "failed")

        if indexing == 0:
            msg = f"✅ Done! {completed} ready"
            if failed:
                msg += f", ❌ {failed} failed"
            yield msg, rows
            return

        yield (
            f"⏳ Re-indexing… {completed} done, {indexing} in progress, {failed} failed",
            rows,
        )

    rows, msg = refresh_docs(uid)
    yield "⚠️ Re-indexing still running (timeout). Use Refresh to check.", rows


def delete_docs(user_id: str, doc_ids_str: str):
    """Delete documents by comma-separated document IDs."""
    if not user_id.strip():
        return "⚠️ Enter a User ID first.", []
    doc_ids = [d.strip() for d in doc_ids_str.split(",") if d.strip()]
    if not doc_ids:
        return "⚠️ Enter document IDs to delete (comma-separated).", []
    try:
        rag_client.delete_documents(user_id.strip(), doc_ids)
        rows, msg = refresh_docs(user_id)
        return f"✅ Deleted {len(doc_ids)} document(s).", rows
    except Exception as e:
        logger.error("delete_docs error: %s", e)
        return f"❌ Delete failed: {e}", []


def send_message(user_id: str, message: str, history: List, top_k: int, model_choice: str):
    """Streaming chat handler."""
    if not user_id.strip():
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "⚠️ Enter a User ID first."},
        ]
        yield history, [], ""
        return
    if not message.strip():
        yield history, [], ""
        return

    history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": ""}]
    yield history, [], ""

    import re as _re
    def _clean(text: str) -> str:
        # Strip <think>...</think> blocks Qolda sometimes emits
        return _re.sub(r"<think>.*?</think>", "", text, flags=_re.DOTALL).strip()

    backend_history = []
    for m in history[:-1]:
        logger.debug("history item type=%s value=%r", type(m), m)
        if not isinstance(m, dict):
            continue
        role = m.get("role", "")
        content = _clean(str(m.get("content") or ""))
        if role in ("user", "assistant") and content:
            backend_history.append({"role": role, "content": content})
    logger.info("backend_history len=%d items=%r", len(backend_history), backend_history)

    selected = MODELS.get(model_choice, {})
    llm_url = selected.get("url")
    llm_model = selected.get("model")

    citations = []
    for accumulated_text, new_citations in backend_client.stream_chat(
        user_id=user_id.strip(),
        message=message.strip(),
        history=backend_history,
        top_k=int(top_k),
        llm_url=llm_url,
        llm_model=llm_model,
    ):
        import re as _re2
        display_text = _re2.sub(r"<think>.*?</think>", "", accumulated_text, flags=_re2.DOTALL).strip()
        history[-1]["content"] = display_text or accumulated_text
        if new_citations:
            citations = new_citations
        yield history, format_citations(citations), ""

    logger.info("Chat complete: user=%s citations=%d", user_id, len(citations))


def clear_chat():
    return [], None, ""


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="Qolda RAG Chat v2") as demo:

    gr.Markdown(
        """
        # Qolda RAG Chat
        Upload your documents, then ask questions in Kazakh, Russian, or English.
        """
    )

    with gr.Row():
        user_id_input = gr.Textbox(
            label="User ID",
            placeholder="e.g. askar, askar-1",
            scale=2,
        )
        model_dropdown = gr.Dropdown(
            choices=list(MODELS.keys()),
            value=list(MODELS.keys())[0],
            label="LLM Model",
            scale=2,
        )
        top_k_slider = gr.Slider(
            minimum=1, maximum=10, value=5, step=1,
            label="Retrieval top-k",
            scale=1,
        )

    with gr.Row(equal_height=False):

        # ── Left: Documents panel ──────────────────────────────────────────
        with gr.Column(scale=1, min_width=320):
            gr.Markdown("### Documents")

            doc_status = gr.Markdown("")
            doc_table = gr.Dataframe(
                headers=["Filename", "ID", "Chunks", "Status"],
                datatype=["str", "str", "number", "str"],
                label="Indexed documents",
                interactive=False,
                wrap=True,
            )

            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh", size="sm", scale=1)
                reindex_btn = gr.Button("♻️ Re-index all", size="sm", scale=1)

            with gr.Accordion("Upload new files", open=True):
                file_input = gr.File(
                    file_count="multiple",
                    label="PDF / DOCX / DOC",
                    file_types=[".pdf", ".docx", ".doc"],
                )
                upload_btn = gr.Button("⬆️ Upload & Index", variant="primary")

            with gr.Accordion("Delete documents", open=False):
                delete_input = gr.Textbox(
                    label="Document IDs (comma-separated, copy from ID column above)",
                    placeholder="uuid1, uuid2",
                )
                delete_btn = gr.Button("Delete selected", variant="stop")

        # ── Right: Chat panel ──────────────────────────────────────────────
        with gr.Column(scale=2):
            gr.Markdown("### Chat")

            chatbot = gr.Chatbot(
                label="Conversation",
                height=500,
                buttons=["copy", "copy_all"],
            )
            msg_input = gr.Textbox(
                label="Your message",
                placeholder="Ask a question about your documents…",
                lines=2,
                submit_btn=True,
            )

            with gr.Row():
                send_btn = gr.Button("Send", variant="primary", scale=3)
                clear_btn = gr.Button("Clear", scale=1)

            gr.Markdown("#### Sources used")
            citations_table = gr.Dataframe(
                headers=["#", "Source", "Score", "Excerpt"],
                datatype=["number", "str", "str", "str"],
                wrap=True,
                interactive=False,
            )

    # ── Event wiring ──────────────────────────────────────────────────────────

    refresh_btn.click(refresh_docs, inputs=[user_id_input], outputs=[doc_table, doc_status])

    reindex_btn.click(reindex_docs, inputs=[user_id_input], outputs=[doc_status, doc_table])

    upload_btn.click(upload_docs, inputs=[user_id_input, file_input], outputs=[doc_status, doc_table])

    delete_btn.click(delete_docs, inputs=[user_id_input, delete_input], outputs=[doc_status, doc_table])

    send_btn.click(
        send_message,
        inputs=[user_id_input, msg_input, chatbot, top_k_slider, model_dropdown],
        outputs=[chatbot, citations_table, msg_input],
    )
    msg_input.submit(
        send_message,
        inputs=[user_id_input, msg_input, chatbot, top_k_slider, model_dropdown],
        outputs=[chatbot, citations_table, msg_input],
    )

    clear_btn.click(clear_chat, outputs=[chatbot, citations_table, msg_input])

    user_id_input.change(refresh_docs, inputs=[user_id_input], outputs=[doc_table, doc_status])


if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("GRADIO_PORT", "7860")),
        show_error=True,
    )
