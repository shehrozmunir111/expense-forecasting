# FinanceFlow - Expense Forecasting Dashboard

React frontend for the expense forecasting API.

## Setup

```bash
cp .env.example .env
# Edit .env if your backend runs on a different port

npm install
npm run dev
```

## Build

```bash
npm run build
```

## Tech Stack

- React 18 + Vite + TypeScript
- TailwindCSS + shadcn/ui
- Framer Motion (animations)
- Recharts (charts)
- TanStack Query (server state)
- Zustand (client state)
- Axios (API client)
- react-router-dom v6 (routing)

## Pages

| Route | Page |
|-------|------|
| `/` | Dashboard — stat cards, charts, recent transactions |
| `/expenses` | Expenses — paginated table, filters, CRUD |
| `/upload` | Upload — CSV/JSON drag & drop, manual entry |
| `/forecast` | Forecast — per-category predictions, model info |
| `/chat` | Chat — RAG, ReAct agent, Supervisor, HITL approval flow |
| `/settings` | Settings — theme, model info, maintenance |
