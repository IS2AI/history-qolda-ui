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
git clone git@github.com:IS2AI/history-qolda-ui.git
cd history-qolda-ui

# Install deps
pip install -r requirements.txt

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

## Datasets

System evaluation uses two public datasets released alongside this project:

### UNT Kazakhstan History MCQ — [`issai/unt-kz-history-mcq`](https://huggingface.co/datasets/issai/unt-kz-history-mcq)

A 1,081-question multiple-choice benchmark drawn from the Kazakhstan UNT (Unified National Testing) history exam. Each of the four evaluated architectures runs the full set independently, producing 4,324 inference runs per evaluation cycle. Response quality is measured by exact string match between the model's predicted label and the ground-truth label in the evaluation CSV. Accuracy is:

```
Acc = (1/N) · Σ 𝟙[yᵢ = yᵢ*],     N = 1,081
```

where `𝟙[·]` returns 1 on an exact match and 0 otherwise. No LLM judge is involved at this stage, so MCQ accuracy is fully reproducible and free from judge-model variability.

Sample questions:

| # | Question (Kazakh) | A | B | C | D | Answer |
|---|---|---|---|---|---|:---:|
| 1 | «Тарих-и Рашиди» еңбегін жазған ғалым? | Мұхаммед Хайдар Дулати | Масуд ибн Осман | Бабыр | Әбілғазы Баһадүр | A |
| 2 | Қазақтың ең көп таралған ою-өрнегі | Түйемойын | Сыңармүйіз | Қосмүйіз | Қошқар мүйіз | D |
| 3 | 1940–1980 жылдары бұқаралық ақпарат құралдарының рөлі | Технологиялық инновация | Саяси тұрақтылық | Қоғамдық пікірді қалыптастыру | Экономикалық даму | C |
| 4 | МТС-тердің (машина-трактор станциялары) негізгі қызметі | Салық жинау | Техниканы жалға беру | Егінді қабылдау | Өнімді сату | B |
| 5 | 1989 жылы қабылданған «Тілдер туралы» заңның басты жаңалығы | Қазақ тілі мемлекеттік мәртебе алды | Барлық тілдер жойылды | Латын әліпбиі міндетті болды | Орыс тілі мемлекеттік мәртебе алды | A |

### Multilingual Open-Ended Queries — [`issai/kz-history-queries-multilingual`](https://huggingface.co/datasets/issai/kz-history-queries-multilingual)

A manually constructed set of 500 open-ended questions covering five thematic domains, prepared in Kazakh, Russian, and English for multilingual coverage of the Kazakhstan history domain:

1. **Ancient Kazakhstan** (1–100)
2. **Kazakh Kaganate** (101–200)
3. **Soviet Period** (201–300)
4. **Independence Era** (301–400)
5. **Adversarial Trap Questions** (401–500) — embeds false premises, historical myths, and anachronisms to probe whether models can identify and correct faulty assumptions.

## License

Internal — IS2AI.
