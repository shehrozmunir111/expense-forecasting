#!/usr/bin/env python3
import argparse
import os
import sys
import uuid
from datetime import date

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from langgraph.checkpoint.memory import MemorySaver

from app.database import Base
from app.eval import load_dataset, run_evaluation
from app.models.expense import Expense
from app.repositories.expense_repo import ExpenseRepository
from app.services.chat_agent import ChatAgent
from app.services.finance_agent import FinanceReactAgent
from app.services.finance_tools import FinanceTools
from app.services.llm_provider import get_chat_model

# Must match the expected values in app/eval/questions.json.
SEED = {
    "2024-01": {"Food & Dining": [500.0, 300.0], "Transportation": [1200.0], "Healthcare": [200.0]},
    "2024-02": {"Food & Dining": [700.0], "Transportation": [1100.0], "Healthcare": [250.0]},
    "2024-03": {"Food & Dining": [200.0], "Transportation": [1300.0], "Healthcare": [180.0]},
}


def build_tools() -> FinanceTools:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    for month, cats in SEED.items():
        year, mm = (int(x) for x in month.split("-"))
        for category, amounts in cats.items():
            for amt in amounts:
                db.add(Expense(raw_text=f"{category} tx", amount=amt, currency="USD",
                               date=date(year, mm, 12), category=category,
                               categorization_status="categorized"))
    db.commit()
    return FinanceTools(ExpenseRepository(db))


def upload_to_langsmith(dataset):
    try:
        from langsmith import Client

        client = Client()
        name = "expense-chat-eval"
        existing = list(client.list_datasets(dataset_name=name))
        ds = existing[0] if existing else client.create_dataset(
            dataset_name=name, description="Expense chat eval questions + expected figures"
        )
        if not existing:
            client.create_examples(
                inputs=[{"question": e["question"]} for e in dataset],
                outputs=[{"expected_number": e.get("expected_number"),
                          "expected_category": e.get("expected_category")} for e in dataset],
                dataset_id=ds.id,
            )
        print(f"[langsmith] dataset '{name}' ready ({len(dataset)} examples).")
    except Exception as exc:
        print(f"[langsmith] skipped: {exc}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", action="store_true", help="Evaluate the tool-calling ReAct agent")
    parser.add_argument("--no-judge", action="store_true", help="Skip the LLM-as-judge stage")
    parser.add_argument("--langsmith", action="store_true", help="Upload the eval dataset to LangSmith")
    args = parser.parse_args()

    dataset = load_dataset()
    tools = build_tools()

    if args.agent:
        agent = FinanceReactAgent(checkpointer=MemorySaver())
        def answer_fn(q):
            r = agent.run(q, "eval-" + uuid.uuid4().hex, tools)
            return {"answer": r.answer, "sources": r.sources}
        label = "tool-calling ReAct agent"
    else:
        agent = ChatAgent(checkpointer=MemorySaver())
        def answer_fn(q):
            r = agent.run(q, "eval-" + uuid.uuid4().hex, tools)
            return {"answer": r.answer, "sources": r.sources}
        label = "adaptive-RAG agent"

    judge_llm = None if args.no_judge else get_chat_model()

    print(f"Evaluating: {label}  |  judge: {'off' if args.no_judge else 'on'}  "
          f"|  {len(dataset)} questions\n" + "=" * 72)
    report = run_evaluation(dataset, answer_fn, judge_llm=judge_llm)

    for i, item in enumerate(report["items"], 1):
        marks = []
        if item["numeric_match"] is not None:
            marks.append(f"numeric={'PASS' if item['numeric_match'] else 'FAIL'}")
        if item["retrieval_hit"] is not None:
            marks.append(f"recall={'HIT' if item['retrieval_hit'] else 'MISS'}")
        if item["judge"]:
            j = item["judge"]
            marks.append(f"judge(f={int(j['faithful'])},r={int(j['relevant'])},c={int(j['correct'])})")
        print(f"\n[{i}] Q: {item['question']}")
        print(f"    A: {item['answer']}")
        print(f"    expected_number={item['expected_number']}  ->  " + "  ".join(marks))

    print("\n" + "=" * 72 + "\nAGGREGATE")
    for key, val in report["aggregate"].items():
        print(f"  {key:22}: {val}")

    if args.langsmith:
        upload_to_langsmith(dataset)


if __name__ == "__main__":
    main()
