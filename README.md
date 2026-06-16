# Expense Forecasting API

FastAPI backend for importing personal finance transactions, categorizing them with an LLM, and forecasting next-month spending with a lightweight ML model.

The project is designed for a simple local-first workflow: SQLite by default, optional PostgreSQL through Docker Compose, reproducible tests, and persisted forecasting models.

## Features

- Bulk upload expenses and income transactions
- Automatic LLM-based expense categorization
- Manual category overrides
- Paginated expense listing with month, category, status, and income filters
- Category and monthly summaries
- Per-category next-month forecasts
- Forecast model persistence and startup reload
- Conversational "Chat with your finances" — Adaptive RAG + memory over your own data
- Tool-calling (ReAct) agent variant — the LLM picks deterministic finance tools
- Production-grade RAG — persistent Chroma index with fingerprint-based refresh
- AI evaluation harness — groundedness, retrieval recall, and LLM-as-judge metrics
- SQLite by default, PostgreSQL-ready configuration
- Docker and Docker Compose support
- Test suite covering API, repository, service, and ML behavior

## Tech Stack

| Area | Technology |
|------|------------|
| API | FastAPI, Uvicorn |
| Database | SQLAlchemy, SQLite, PostgreSQL via psycopg |
| Validation | Pydantic v2, pydantic-settings |
| LLM providers | Anthropic or OpenAI |
| ML | pandas, scikit-learn, joblib |
| Conversational AI | LangGraph, LangChain (LCEL), Chroma; LM Studio or cloud LLM |
| Tests | pytest, FastAPI TestClient |

## Project Structure

```text
app/
|-- main.py                   # FastAPI app, lifespan, CORS, router registration
|-- config.py                 # Environment-based settings
|-- database.py               # SQLAlchemy engine and session factory
|-- models/expense.py         # Expense and forecast cache ORM models
|-- schemas/                  # Pydantic request/response schemas (incl. chat.py)
|-- repositories/             # Database access layer
|-- services/
|   |-- categorization.py     # LLM categorization service
|   |-- forecasting.py        # Forecasting orchestration service
|   |-- finance_tools.py      # Deterministic accessors used by the chat agent
|   |-- finance_retriever.py  # Ephemeral Chroma retrieval over service "fact cards"
|   |-- rag_index.py          # Persistent (production) RAG index + fingerprint refresh
|   |-- llm_provider.py       # Chat model + embeddings factory (LM Studio / cloud)
|   |-- chat_agent.py         # LangGraph Adaptive-RAG agent with memory
|   `-- finance_agent.py      # Tool-calling (ReAct) agent with memory
|-- eval/                     # AI evaluation: dataset + evaluators
|-- ml/forecaster.py          # Train, predict, persist, and reload ML models
`-- routers/                  # Health, expenses, forecast, and chat routes

tests/
|-- conftest.py
|-- test_expenses.py
|-- test_forecast.py
|-- test_chat.py              # Adaptive-RAG agent
|-- test_agent.py             # Tool-calling agent
|-- test_rag.py               # Persistent RAG index
`-- test_eval.py              # Evaluation harness

scripts/
|-- seed_data.py              # Seed synthetic transactions via the API
|-- verify_chat.py            # Live multi-turn chat verification (memory + numbers)
`-- evaluate.py               # AI evaluation runner (groundedness / recall / judge)
```

## Requirements

- Python 3.11 recommended
- Docker Desktop optional
- Anthropic or OpenAI API key if using automatic categorization

Python 3.11 is recommended because the pinned ML stack has stable wheels for it. Newer Python versions may attempt to build scikit-learn from source.

## Quick Start

Create and activate a Python 3.11 virtual environment:

```powershell
cd D:\Projects\expense-forecasting
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set one provider key:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
```

Run the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

Open the interactive API docs:

```text
http://localhost:8000/docs
```

## Docker

SQLite default service:

```powershell
docker compose up --build
```

PostgreSQL profile:

```powershell
docker compose --profile pg up --build
```

When the PostgreSQL profile is enabled, the PostgreSQL-backed API is exposed on:

```text
http://localhost:8001
```

The default SQLite API remains available on:

```text
http://localhost:8000
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `Expense Forecasting API` | Application name |
| `APP_VERSION` | `1.0.0` | Application version |
| `DEBUG` | `false` | Enables SQL echo when true |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DATABASE_URL` | `sqlite:///./data/expenses.db` | SQLite or PostgreSQL connection URL |
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` | unset | Required for Anthropic categorization |
| `OPENAI_API_KEY` | unset | Required for OpenAI categorization |
| `LLM_MODEL` | `claude-haiku-4-5-20251001` | Anthropic model identifier |
| `LLM_MAX_TOKENS` | `2048` | Maximum tokens for LLM responses |
| `LLM_BATCH_SIZE` | `20` | Transactions per categorization batch |
| `MODEL_PATH` | `./data/models` | Persisted model directory |
| `MIN_MONTHS_FOR_FORECAST` | `2` | Minimum distinct months required for forecasting |

PostgreSQL example:

```env
DATABASE_URL=postgresql+psycopg://expense:expense@localhost:5432/expense_db
```

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check and database status |
| `POST` | `/expenses/upload` | Bulk upload expenses or income |
| `GET` | `/expenses/` | Paginated list with filters |
| `GET` | `/expenses/{expense_id}` | Retrieve one expense |
| `PATCH` | `/expenses/{expense_id}` | Update notes, income flag, or manual category |
| `DELETE` | `/expenses/{expense_id}` | Delete an expense |
| `GET` | `/expenses/summary/by-category` | Category totals |
| `GET` | `/expenses/summary/monthly?month=YYYY-MM` | Monthly income/expense summary |
| `POST` | `/expenses/categorize/run` | Run pending categorization synchronously |
| `GET` | `/forecast/` | Generate next-month forecast |
| `POST` | `/forecast/train` | Retrain forecasting model |
| `GET` | `/forecast/model-info` | Forecast model readiness and metadata |
| `POST` | `/chat` | Ask plain-language questions about your finances (Adaptive RAG + memory) |
| `POST` | `/chat/stream` | Same, streamed token-by-token (`text/plain`) |
| `POST` | `/chat/agent` | Tool-calling (ReAct) variant — the LLM picks finance tools |
| `POST` | `/chat/agent/stream` | Tool-calling variant, streamed (`text/plain`) |
| `POST` | `/chat/reindex` | Rebuild the persistent RAG index (`?force=true|false`) |

## Example Workflow

Upload expenses:

```bash
curl -X POST http://localhost:8000/expenses/upload \
  -H "Content-Type: application/json" \
  -d '{
    "expenses": [
      {
        "raw_text": "ATB 450 UAH",
        "amount": 450,
        "currency": "UAH",
        "date": "2024-01-10"
      },
      {
        "raw_text": "WOG 1200 UAH",
        "amount": 1200,
        "currency": "UAH",
        "date": "2024-01-12"
      }
    ],
    "auto_categorize": true
  }'
```

Run categorization manually:

```bash
curl -X POST http://localhost:8000/expenses/categorize/run
```

Train the forecast model:

```bash
curl -X POST http://localhost:8000/forecast/train
```

Get a forecast:

```bash
curl http://localhost:8000/forecast/
```

## Forecasting Behavior

The forecaster trains one model per category. It uses:

- month ordinal
- calendar month number
- quarter
- lag-1 previous-month category spending

Forecasting requires at least two distinct months of categorized expense data. Predictions are clamped to zero or above, saved to disk, and reloaded when the application starts.

## Chat with your finances

A conversational endpoint that answers plain-language questions about *your own* data, for example:

- "How much did I spend on groceries in January 2024?"
- "And what about the next month?" (follow-ups use conversation memory)
- "Which category did I spend the most on overall?"
- "What's next month's food forecast?"

### How it works (Adaptive RAG + memory)

The agent is a small LangGraph state machine:

```text
retrieve --> grade --> (rewrite --> retrieve)* --> answer
```

1. **retrieve** — builds short "fact cards" from the existing summary/forecast services and indexes them in a Chroma vector store, then retrieves the cards most relevant to the question.
2. **grade** (LCEL) — judges whether the retrieved cards are relevant and sufficient.
3. **rewrite** — if they are weak, the question is rewritten (resolving follow-ups using the conversation) and retrieval is retried.
4. **answer** (LCEL: `prompt | llm | StrOutputParser`) — phrases a short, grounded answer.

**Numbers are never computed by the LLM.** Every figure in an answer comes from the deterministic repository/forecast services — the same code behind `/expenses/summary/*` and `/forecast/` — so chat answers always match those endpoints. **Memory** is provided by a LangGraph checkpointer keyed by `conversation_id` (in-memory for SQLite/dev, PostgreSQL for the Postgres profile), so multi-turn follow-ups keep context. If the LLM is unreachable, the endpoint returns a templated summary of the retrieved facts instead of failing.

### Endpoint

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How much did I spend on groceries in January 2024?", "conversation_id": "user-42"}'
```

```json
{
  "answer": "You spent 800.00 UAH on groceries in January 2024.",
  "sources": [
    {
      "kind": "category_summary",
      "label": "Groceries 2024-01",
      "detail": "In 2024-01, spending on Groceries was 800.00 UAH over 2 transactions (40.0% of that month)."
    }
  ],
  "conversation_id": "user-42",
  "rewritten": false,
  "grounded": true
}
```

Reuse the same `conversation_id` for follow-up questions. A token-by-token streaming variant is available at `POST /chat/stream` (`text/plain`; the resolved id is returned in the `X-Conversation-Id` response header).

### LLM configuration

The agent is provider-agnostic and configured via `.env`. By default it targets a local **LM Studio** server (OpenAI-compatible), so no cloud key is required:

```env
CHAT_LLM_PROVIDER=openai
CHAT_LLM_MODEL=google/gemma-4-12b-qat
LLM_BASE_URL=http://localhost:1234/v1
OPENAI_API_KEY=lm-studio
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5
EMBEDDING_BASE_URL=http://localhost:1234/v1
```

To use the cloud instead, set `CHAT_LLM_PROVIDER` to `openai` (real key, clear `LLM_BASE_URL`), `anthropic`, or `gemini` (`pip install langchain-google-genai`). See `.env.example` for all options. Optional LangSmith tracing is enabled by running the API with `uvicorn app.main:app --env-file .env`.

### Verify it end-to-end

With LM Studio running, this seeds deterministic data and runs a live 3-turn conversation, confirming that memory works and the numbers match the services:

```powershell
python scripts/verify_chat.py
```

### Tool-calling agent (ReAct)

`POST /chat/agent` is a tool-calling variant: instead of pre-injecting retrieved facts, the LLM is given the finance services as **tools** (`get_category_summary`, `get_category_total`, `get_monthly_summary`, `get_biggest_category`, `get_forecast`, `list_months`, `list_recent_transactions`) and decides which to call (LangGraph's `create_react_agent`). It shares the same conversation memory as `/chat`.

```bash
curl -X POST http://localhost:8000/chat/agent \
  -H "Content-Type: application/json" \
  -d '{"message": "Which category did I spend the most on?", "conversation_id": "user-42"}'
```

The response `sources` list the tool calls the model made (name + returned value), so the grounding is transparent. As with `/chat`, every figure is produced by the tools (the deterministic services) — never the model. `grounded` is `true` only when the model actually called a tool. A streaming variant is at `POST /chat/agent/stream`.

> Adaptive RAG (`/chat`) vs ReAct (`/chat/agent`): RAG *guarantees* grounding by injecting facts before answering; ReAct is more flexible (the model chooses tools) but relies on the model to call them. Both are provided to compare the patterns.

### Production RAG index

By default (`RAG_PERSISTENT=true`) `/chat` retrieves from a **persistent Chroma index** under `RAG_PERSIST_DIR` (`./data/chroma`), not an ephemeral per-request one. Production patterns:

- **Persistence**: embeddings live on disk and survive restarts.
- **Fingerprint caching**: a cheap dataset signature (row count / max id / max `updated_at`) is stored next to the index; if nothing changed, queries skip re-embedding.
- **Stable ids + clean rebuild on change**: documents carry stable ids (no duplicates); a data change triggers a rebuild so deleted rows never linger.
- **Richer corpus**: summary/forecast fact cards plus transaction-level documents with category/month metadata.

Force a rebuild (e.g. after bulk categorizing a new month):

```bash
curl -X POST "http://localhost:8000/chat/reindex?force=true"
# -> {"status": "rebuilt", "documents": 42}
```

Set `RAG_PERSISTENT=false` to fall back to the ephemeral index (used by the test suite). For the PostgreSQL profile, point embeddings at the same store; pgvector can replace Chroma by swapping the vector store in `rag_index.py`.

### AI evaluation

`scripts/evaluate.py` scores the agent on a small labelled dataset (`app/eval/questions.json`) with three evaluator families:

- **Numeric groundedness** (deterministic): does the answer contain the exact figure the services compute? Catches hallucinated/miscomputed numbers with no judge needed.
- **Retrieval recall@k** (deterministic): did retrieval surface a fact for the expected category/month?
- **LLM-as-judge**: faithfulness / relevance / correctness, scored by the local model (structured output, with a text-parse fallback).

```powershell
python scripts/evaluate.py              # adaptive-RAG agent, with judge
python scripts/evaluate.py --agent      # tool-calling ReAct agent
python scripts/evaluate.py --no-judge   # deterministic metrics only (fast)
python scripts/evaluate.py --langsmith  # also upload the dataset to LangSmith
```

It prints per-question PASS/FAIL/HIT marks plus aggregate rates (`groundedness_numeric`, `retrieval_recall`, and `judge_*`). The deterministic evaluators run fully offline; the judge uses the configured LLM.

## Running Tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Current status:

```text
70 passed
```

The tests cover upload, pagination, CRUD, manual categorization, validation, summaries, no-data forecasts, insufficient-data forecasts, training, prediction, confidence bounds, year rollover, persistence, LLM fallback behavior, and service exception handling. The AI suites add: Adaptive RAG (retrieve / grade / rewrite / answer / multi-turn memory / numeric correctness / fallback), the tool-calling agent (tool selection, memory, fallback), the persistent RAG index (build, fingerprint caching, rebuild-on-change, dedup, recall, `/chat/reindex`), and the evaluation harness (numeric groundedness, retrieval recall, LLM-as-judge) — all fully offline (LLM mocked, no LM Studio/network required).

## Notes for Development

- Use Python 3.11 for local development.
- Keep `.env` out of git.
- SQLite data and persisted models live under `data/`.
- The background categorization task opens its own DB session.
- PostgreSQL support uses `postgresql+psycopg://...` URLs.

## Commit Recommendation

For this README update, use a separate commit:

```text
Update project README documentation
```

For future work, prefer focused commits for UI, deployment, authentication, reporting, or forecasting improvements.
