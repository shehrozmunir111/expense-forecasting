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
| Tests | pytest, FastAPI TestClient |

## Project Structure

```text
app/
|-- main.py                   # FastAPI app, lifespan, CORS, router registration
|-- config.py                 # Environment-based settings
|-- database.py               # SQLAlchemy engine and session factory
|-- models/expense.py         # Expense and forecast cache ORM models
|-- schemas/                  # Pydantic request/response schemas
|-- repositories/             # Database access layer
|-- services/
|   |-- categorization.py     # LLM categorization service
|   `-- forecasting.py        # Forecasting orchestration service
|-- ml/forecaster.py          # Train, predict, persist, and reload ML models
`-- routers/                  # Health, expenses, and forecast routes

tests/
|-- conftest.py
|-- test_expenses.py
`-- test_forecast.py
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

## Running Tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Current status:

```text
32 passed
```

The tests cover upload, pagination, CRUD, manual categorization, validation, summaries, no-data forecasts, insufficient-data forecasts, training, prediction, confidence bounds, year rollover, persistence, LLM fallback behavior, and service exception handling.

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
