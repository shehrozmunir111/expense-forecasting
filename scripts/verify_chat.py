#!/usr/bin/env python3
import os
import sys
from datetime import date

# Load .env so LM Studio base URL / models apply.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass

# Make sure the project root is importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from langgraph.checkpoint.memory import MemorySaver

from app.config import settings
from app.database import Base
from app.models.expense import Expense
from app.repositories.expense_repo import ExpenseRepository
from app.services.chat_agent import ChatAgent
from app.services.finance_tools import FinanceTools

# 4 months of categorized data. Car/Fuel is intentionally the largest category.
SEED = {
    "2024-01": {"Groceries": [500.0, 300.0], "Car/Fuel": [1200.0], "Dining": [200.0]},
    "2024-02": {"Groceries": [700.0], "Car/Fuel": [1100.0], "Dining": [250.0]},
    "2024-03": {"Groceries": [600.0], "Car/Fuel": [1300.0], "Dining": [180.0]},
    "2024-04": {"Groceries": [900.0], "Car/Fuel": [1400.0], "Dining": [300.0]},
}


def build_tools() -> FinanceTools:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    rows = []
    for month, cats in SEED.items():
        year, mm = (int(x) for x in month.split("-"))
        for category, amounts in cats.items():
            for amt in amounts:
                rows.append(
                    Expense(
                        raw_text=f"{category} purchase",
                        amount=amt,
                        currency="USD",
                        date=date(year, mm, 12),
                        category=category,
                        categorization_status="categorized",
                    )
                )
    db.add_all(rows)
    db.commit()
    return FinanceTools(ExpenseRepository(db))


def hr(title=""):
    print("\n" + "=" * 70)
    if title:
        print(title)
        print("-" * 70)


def main():
    print(f"LLM provider : {settings.CHAT_LLM_PROVIDER}  model={settings.CHAT_LLM_MODEL}")
    print(f"Base URL     : {settings.LLM_BASE_URL or '(cloud default)'}")
    print(f"Embeddings   : {settings.EMBEDDING_MODEL}")

    tools = build_tools()

    hr("GROUND TRUTH (computed by deterministic services)")
    jan_groc = tools.category_total("Groceries", "2024-01")["total"]
    feb_groc = tools.category_total("Groceries", "2024-02")["total"]
    totals = {r["category"]: r["total"] for r in tools.category_summary()}
    biggest = max(totals, key=totals.get)
    print(f"  Jan 2024 Groceries total : {jan_groc:.2f} USD")
    print(f"  Feb 2024 Groceries total : {feb_groc:.2f} USD")
    print(f"  All-time totals          : {totals}")
    print(f"  Biggest category overall : {biggest} ({totals[biggest]:.2f} USD)")
    fc = tools.forecast()
    if fc:
        print(f"  Forecast month           : {fc['forecast_month']}")

    agent = ChatAgent(checkpointer=MemorySaver())
    cid = "verify-session"

    turns = [
        ("How much did I spend on groceries in January 2024?", jan_groc),
        ("And what about the next month?", feb_groc),  # follow-up -> needs memory
        ("Which category did I spend the most on overall?", biggest),
    ]

    hr("CONVERSATION (live LLM, single thread_id => memory on)")
    all_ok = True
    for i, (question, expected) in enumerate(turns, 1):
        resp = agent.run(question, cid, tools)
        print(f"\n[Turn {i}] You: {question}")
        print(f"         Bot: {resp.answer}")
        print(f"         (rewritten={resp.rewritten}, grounded={resp.grounded}, "
              f"sources={[s.label for s in resp.sources][:3]})")
        needle = f"{expected:.2f}".rstrip("0").rstrip(".") if isinstance(expected, float) else str(expected)
        match = (needle in resp.answer) or (str(expected) in resp.answer)
        print(f"         numeric/answer check -> expected '{needle}'  =>  "
              f"{'MATCH' if match else 'NOT FOUND (inspect manually)'}")
        all_ok = all_ok and match

    hr("MEMORY")
    saved = agent._checkpointer.get({"configurable": {"thread_id": cid}})
    msgs = saved["channel_values"]["messages"] if saved else []
    print(f"  messages persisted in thread '{cid}': {len(msgs)} "
          f"(expected {len(turns) * 2})")

    hr("RESULT")
    print("  All numeric checks matched." if all_ok
          else "  Some answers didn't contain the expected figure verbatim "
               "(phrasing varies with local models; verify the printed values).")
    print("  Memory OK." if len(msgs) == len(turns) * 2 else "  Memory check: unexpected message count.")


if __name__ == "__main__":
    main()
