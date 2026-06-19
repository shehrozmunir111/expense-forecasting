# FinanceFlow

AI powered personal finance platform. It categorizes expenses, forecasts next month spending, and lets you **chat with your finances** in plain language. Built on FastAPI with a React dashboard, a LangGraph + RAG assistant, full test coverage, and Docker.

<p align="center">
  <img src="assets/dashboard.png" alt="FinanceFlow dashboard" width="900">
</p>

## Highlights

- **Chat with your finances.** Ask questions like "how much did I spend last month?" and get answers grounded in your own data, with citations and conversation memory.
- **Adaptive RAG** (retrieve, grade, rewrite, answer) over fact cards built from deterministic services, so every figure matches the API and is never hallucinated.
- **Tool calling ReAct agent**, a **multi agent supervisor** that auto routes each question, and **Human in the Loop** approval for any data change.
- **Production RAG**: persistent vector index with fingerprint caching, reranking, and per user long term memory.
- **Guardrails** (input injection/topic checks, output groundedness) plus an **AI evaluation harness** (groundedness, retrieval recall, LLM as judge).
- **Provider agnostic LLM**: local LM Studio by default, or cloud OpenAI / Anthropic / Gemini. One factory, switch via `.env`.
- Solid core: LLM categorization, per category ML forecasting, summaries, a clean layered architecture, and SQLite or PostgreSQL.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic v2, SQLite / PostgreSQL |
| AI | LangGraph, LangChain (LCEL), Chroma, LM Studio / OpenAI / Anthropic |
| ML | scikit-learn, pandas, joblib |
| Frontend | React 18, TypeScript, Vite, Tailwind, TanStack Query, Recharts |
| Tooling | Docker & Compose, pytest (105 tests) |

## Quick Start

**Backend** (Python 3.11):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env        # then set provider keys or the LM Studio URL
uvicorn app.main:app --reload --port 8000     # http://localhost:8000/docs
```

**Frontend**:

```powershell
cd frontend; npm install; npm run dev
```

**Docker** (SQLite by default; add `--profile pg` for PostgreSQL):

```powershell
docker compose up --build
```

## The AI assistant

A LangGraph agent answers questions about your own data. Numbers come from deterministic services (the same code behind `/expenses/summary/*` and `/forecast/`), so chat answers always match the API and the LLM only phrases them. Memory is keyed by `conversation_id`. If the LLM is unreachable, the agent falls back to a templated, fact grounded answer.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How much did I spend last month?", "conversation_id": "user-42"}'
# { "answer": "You spent 48829.00 USD last month.", "sources": [...], "grounded": true }
```

| Capability | Endpoint or setting |
|------------|---------------------|
| Adaptive RAG chat (plus streaming) | `POST /chat`, `POST /chat/stream` |
| Tool calling ReAct agent | `POST /chat/agent` |
| Multi agent auto routing | `POST /chat/supervisor` returns `routed_to` |
| Human in the Loop write and approval | `POST /chat/action` then `POST /chat/approve` |
| Rebuild persistent RAG index | `POST /chat/reindex` |
| Reranking, long term memory, guardrails | `RAG_RERANK`, `LONG_TERM_MEMORY`, `GUARDRAILS` |

**LLM config** (`.env`) defaults to a local LM Studio server (OpenAI compatible, no cloud key):

```env
CHAT_LLM_PROVIDER=openai
CHAT_LLM_MODEL=google/gemma-4-12b-qat
LLM_BASE_URL=http://localhost:1234/v1
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5
```

To use the cloud, set `CHAT_LLM_PROVIDER` to `anthropic`, `gemini`, or `openai` with a real key and clear `LLM_BASE_URL`. See `.env.example` for all options.

## Core API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/expenses/upload` | Bulk upload expenses or income (optional auto categorize) |
| `GET` | `/expenses/`, `/expenses/summary/by-category`, `/expenses/summary/monthly` | List and summaries |
| `POST` | `/expenses/categorize/run` | LLM categorization |
| `GET` | `/forecast/`, `POST /forecast/train` | Next month per category forecast |
| `POST` | `/chat*` | Conversational assistant (see above) |

Full interactive docs at `/docs`.

## Evaluation and Tests

```powershell
python -m pytest -q          # 105 passed, fully offline (LLM mocked)
python scripts/evaluate.py   # groundedness, retrieval recall, LLM as judge
python scripts/verify_chat.py  # live multi turn demo (memory and numeric correctness)
```

## Architecture

Layered: routers, services, repositories, ml and models. The AI lives in `app/services/` (`chat_agent`, `finance_agent`, `action_agent`, `supervisor`, `rag_index`, `reranker`, `long_term_memory`, `guardrails`, `llm_provider`), with deterministic `finance_tools` as the single source of truth for every figure.
