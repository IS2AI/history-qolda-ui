import logging
import gradio as gr
from clients.rag_api import RagApiClient

logger = logging.getLogger(__name__)


def build_document_panel(rag_client: RagApiClient):
    """Returns a Gradio column with document upload/list/delete controls."""

    def refresh_docs(user_id: str):
        if not user_id.strip():
            return gr.update(value=[]), "⚠️ Enter a User ID first."
        try:
            docs = rag_client.list_documents(user_id.strip())
            rows = [
                [d.get("filename", ""), d.get("document_id", ""), d.get("chunk_count", 0)]
                for d in docs
            ]
            return gr.update(value=rows), f"✅ {len(docs)} document(s) found."
        except Exception as e:
            return gr.update(value=[]), f"❌ {e}"

    def upload_docs(user_id: str, files):
        if not user_id.strip():
            return "⚠️ Enter a User ID first.", gr.update(value=[])
        if not files:
            return "⚠️ Select files to upload.", gr.update(value=[])
        try:
            paths = [f.name for f in files] if hasattr(files[0], "name") else files
            result = rag_client.upload_documents(user_id.strip(), paths)
            msg = f"✅ Uploaded {len(paths)} file(s). Processing started."
            rows, status = refresh_docs(user_id)
            return msg, rows
        except Exception as e:
            return f"❌ Upload failed: {e}", gr.update(value=[])

    def delete_docs(user_id: str, selected_filenames: str):
        if not user_id.strip():
            return "⚠️ Enter a User ID first.", gr.update(value=[])
        if not selected_filenames.strip():
            return "⚠️ Enter filename(s) to delete (comma-separated).", gr.update(value=[])
        filenames = [f.strip() for f in selected_filenames.split(",") if f.strip()]
        try:
            rag_client.delete_documents(user_id.strip(), filenames)
            rows, status = refresh_docs(user_id)
            return f"✅ Deleted: {', '.join(filenames)}", rows
        except Exception as e:
            return f"❌ Delete failed: {e}", gr.update(value=[])

    with gr.Column():
        gr.Markdown("### Documents")

        status_box = gr.Markdown("")

        doc_table = gr.Dataframe(
            headers=["Filename", "ID", "Chunks"],
            datatype=["str", "str", "number"],
            label="Indexed documents",
            interactive=False,
            wrap=True,
        )

        refresh_btn = gr.Button("🔄 Refresh", size="sm")

        gr.Markdown("**Upload**")
        file_input = gr.File(
            file_count="multiple",
            label="Select PDF / DOCX / DOC files",
            file_types=[".pdf", ".docx", ".doc"],
        )
        upload_btn = gr.Button("⬆️ Upload & Index", variant="primary")

        gr.Markdown("**Delete**")
        delete_input = gr.Textbox(
            label="Filenames to delete (comma-separated)",
            placeholder="report.pdf, thesis.docx",
        )
        delete_btn = gr.Button("🗑️ Delete", variant="stop")

    return doc_table, status_box, file_input, upload_btn, refresh_btn, delete_input, delete_btn, refresh_docs, upload_docs, delete_docs
