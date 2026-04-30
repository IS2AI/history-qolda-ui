# Qolda UI

Web interface for the **Qolda** RAG (Retrieval-Augmented Generation) system — a multilingual (Kazakh / Russian / English) document QA assistant for Kazakhstan history materials.

Users upload PDF / DOCX documents, the RAG service indexes them, and the chat UI streams answers from the Qolda LLM grounded in the retrieved chunks, with citations.

## Architecture

```
┌──────────────┐       ┌────────────────┐       ┌───────────────┐
│  Gradio UI   │──────▶│ FastAPI backend│──────▶│  Qolda LLM    │
│  (frontend)  │       │  (this repo)   │       │  (vLLM/lmd.)  │
└──────┬───────┘       └────────┬───────┘       └───────────────┘
       │                        │
       │                        ▼
       │                ┌───────────────┐
       └───────────────▶│  RAG service  │
       (uploads/list)   │ (separate)    │
                        └───────────────┘
```

- **`frontend/`** — Gradio app. Handles file upload, indexing status, chat, and source display.
- **`backend/`** — FastAPI service. Orchestrates retrieval (calls RAG API) + generation (calls Qolda LLM), streams the response back.
- **External services** (not in this repo):
  - **RAG API** — document ingestion, chunking, embedding, retrieval (default `:8034`)
  - **Qolda LLM** — OpenAI-compatible inference server (default `:23333`)

## Requirements

- Python 3.10+
- A running RAG API instance (with valid API key)
- A running Qolda LLM inference endpoint (OpenAI-compatible)

## Setup

```bash
git clone git@github.com:IS2AI/qolda-ui.git
cd qolda-ui

# Install deps (adjust to your environment manager)
pip install fastapi uvicorn httpx pydantic pydantic-settings gradio python-dotenv

# Configure
cp .env.example .env
# then edit .env and set RAG_API_KEY + any URLs/ports
```

### Environment variables

| Variable        | Default                  | Purpose                              |
|-----------------|--------------------------|--------------------------------------|
| `RAG_API_URL`   | `http://localhost:8034`  | RAG service base URL                 |
| `RAG_API_KEY`   | _(required)_             | RAG service API key                  |
| `QOLDA_URL`     | `http://localhost:23333` | Qolda LLM endpoint (OpenAI-compatible) |
| `QOLDA_MODEL`   | `issai/Qolda`            | Model name to request                |
| `BACKEND_URL`   | `http://localhost:8035`  | Backend URL the frontend calls       |
| `BACKEND_PORT`  | `8035`                   | Port the backend binds to            |
| `GRADIO_PORT`   | `7860`                   | Port the frontend binds to           |
| `LOG_LEVEL`     | `INFO`                   | Logging verbosity                    |

## Running

In two terminals (or via tmux):

```bash
# Terminal 1 — backend (FastAPI on :8035)
./run_backend.sh

# Terminal 2 — frontend (Gradio on :7860)
./run_frontend.sh
```

Then open http://localhost:7860.

> The provided `run_*.sh` scripts activate a conda environment named `qolda_stack`. Edit them to match your setup, or run `uvicorn app.main:app` and `python frontend/app.py` directly.

## Usage

1. Enter a **User ID** (any string — used to namespace your documents).
2. Upload PDF / DOCX files in the **Documents** panel; wait for indexing to finish.
3. Pick an LLM from the dropdown (Qolda or Qolda-SFT).
4. Ask questions in Kazakh, Russian, or English. Sources used appear below the chat.

## Project layout

```
qolda-ui/
├── backend/
│   └── app/
│       ├── main.py           # FastAPI app + lifespan
│       ├── config.py         # pydantic-settings
│       ├── routers/chat.py   # /chat streaming endpoint
│       ├── schemas/          # request/response models
│       └── services/         # rag_client, llm_client
├── frontend/
│   ├── app.py                # Gradio UI
│   ├── clients/              # backend_api, rag_api
│   ├── components/
│   └── utils/
├── run_backend.sh
├── run_frontend.sh
├── .env.example
└── README.md
```

## License

Internal — IS2AI.
