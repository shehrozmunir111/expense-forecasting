"""Tests for the "Chat with your finances" Adaptive-RAG agent.

Everything here runs fully offline: the LLM is mocked with FakeListChatModel and
embeddings use the deterministic HashingEmbeddings, so no LM Studio / network is
needed. Covers retrieve, grade (useful + weak->rewrite), answer, multi-turn
memory, numeric correctness (from services), and LLM-down fallback.
"""
import os

os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from datetime import date

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from langgraph.checkpoint.memory import MemorySaver

from app.database import Base
from app.ml.forecaster import ExpenseForecaster
from app.models.expense import Expense
from app.repositories.expense_repo import ExpenseRepository
from app.services.chat_agent import ChatAgent
from app.services.finance_retriever import FinanceRetriever, build_fact_cards
from app.services.finance_tools import FinanceTools
from app.services.forecasting import forecasting_service
from app.services.llm_provider import HashingEmbeddings


# --------------------------------------------------------------------------- #
# Fixtures / helpers                                                           #
# --------------------------------------------------------------------------- #

# Groceries: Jan 800 (500+300), Feb 700, Mar 200  -> all-time 1700
# Car/Fuel:  Jan 1200, Feb 1100, Mar 1300          -> all-time 3600
_SEED = {
    "2024-01": {"Groceries": [500.0, 300.0], "Car/Fuel": [1200.0]},
    "2024-02": {"Groceries": [700.0], "Car/Fuel": [1100.0]},
    "2024-03": {"Groceries": [200.0], "Car/Fuel": [1300.0]},
}


def _seed(db):
    rows = []
    for month, cats in _SEED.items():
        year, mm = (int(x) for x in month.split("-"))
        for category, amounts in cats.items():
            for amt in amounts:
                rows.append(
                    Expense(
                        raw_text=f"{category} tx",
                        amount=amt,
                        currency="UAH",
                        date=date(year, mm, 10),
                        category=category,
                        categorization_status="categorized",
                    )
                )
    db.add_all(rows)
    db.commit()


@pytest.fixture
def tools(tmp_path, monkeypatch):
    # Isolate forecast model persistence to tmp_path (mirrors test_forecast.py).
    monkeypatch.setattr("app.ml.forecaster.MODEL_FILE", str(tmp_path / "model.joblib"))
    monkeypatch.setattr("app.ml.forecaster.META_FILE", str(tmp_path / "meta.json"))
    monkeypatch.setattr("app.config.settings.MODEL_PATH", str(tmp_path))
    forecasting_service.forecaster = ExpenseForecaster()

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    _seed(db)
    try:
        yield FinanceTools(ExpenseRepository(db))
    finally:
        db.close()


@pytest.fixture
def agent():
    # Fresh in-process memory per test for isolation.
    return ChatAgent(checkpointer=MemorySaver())


def fake_llm(*responses):
    return FakeListChatModel(responses=list(responses))


class BoomLLM(FakeListChatModel):
    """A chat model that always fails on call -> exercises the fallback path."""

    def _generate(self, *args, **kwargs):
        raise RuntimeError("LLM unreachable")

    async def _agenerate(self, *args, **kwargs):
        raise RuntimeError("LLM unreachable")


# --------------------------------------------------------------------------- #
# Numeric correctness (numbers come from deterministic services)               #
# --------------------------------------------------------------------------- #

def test_finance_tools_numbers_match_services(tools):
    assert tools.category_total("Groceries", "2024-01")["total"] == 800.0
    assert tools.category_total("Car/Fuel", "2024-02")["total"] == 1100.0

    all_time = {r["category"]: r["total"] for r in tools.category_summary()}
    assert all_time["Groceries"] == 1700.0
    assert all_time["Car/Fuel"] == 3600.0

    jan = tools.monthly_summary("2024-01")
    assert jan["total_expenses"] == 2000.0  # 800 + 1200
    assert tools.distinct_months() == ["2024-01", "2024-02", "2024-03"]


def test_fact_cards_embed_real_numbers(tools):
    cards = build_fact_cards(tools)
    texts = [c.page_content for c in cards]
    # The Jan groceries figure (800.00) appears verbatim, sourced from services.
    assert any("800.00" in t and "Groceries" in t and "2024-01" in t for t in texts)
    # Forecast cards exist (>= 2 months of history were trained).
    assert any(c.metadata.get("kind") == "forecast" for c in cards)


# --------------------------------------------------------------------------- #
# Retrieve                                                                     #
# --------------------------------------------------------------------------- #

def test_retrieve_returns_relevant_docs(tools):
    retriever = FinanceRetriever(tools, embeddings=HashingEmbeddings(), k=4)
    try:
        docs = retriever.retrieve("how much on groceries in January 2024")
        assert docs, "expected at least one retrieved fact card"
        assert any("Groceries" in (d.metadata.get("category") or "") for d in docs)
    finally:
        retriever.close()


def test_retrieve_empty_when_no_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.ml.forecaster.MODEL_FILE", str(tmp_path / "model.joblib"))
    monkeypatch.setattr("app.ml.forecaster.META_FILE", str(tmp_path / "meta.json"))
    monkeypatch.setattr("app.config.settings.MODEL_PATH", str(tmp_path))
    forecasting_service.forecaster = ExpenseForecaster()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    empty_tools = FinanceTools(ExpenseRepository(sessionmaker(bind=engine)()))
    retriever = FinanceRetriever(empty_tools, embeddings=HashingEmbeddings())
    assert retriever.retrieve("anything") == []


# --------------------------------------------------------------------------- #
# Grade node                                                                   #
# --------------------------------------------------------------------------- #

def _grade_state(docs):
    return {"documents": docs, "original_question": "groceries in Jan?"}


def test_grade_useful(tools):
    node = ChatAgent._make_grade(fake_llm("USEFUL"))
    out = node(_grade_state([{"kind": "x", "label": "l", "detail": "groceries 800 UAH"}]))
    assert out["grade"] == "useful"


def test_grade_weak(tools):
    node = ChatAgent._make_grade(fake_llm("WEAK"))
    out = node(_grade_state([{"kind": "x", "label": "l", "detail": "unrelated fact"}]))
    assert out["grade"] == "weak"


def test_grade_empty_docs_is_weak():
    node = ChatAgent._make_grade(fake_llm("USEFUL"))
    assert node(_grade_state([]))["grade"] == "weak"


def test_grade_without_llm_defaults_useful():
    node = ChatAgent._make_grade(None)
    out = node(_grade_state([{"kind": "x", "label": "l", "detail": "fact"}]))
    assert out["grade"] == "useful"


# --------------------------------------------------------------------------- #
# Answer + adaptive rewrite                                                    #
# --------------------------------------------------------------------------- #

def test_answer_is_grounded_and_has_sources(agent, tools):
    resp = agent.run(
        "How much did I spend on groceries in January 2024?",
        "t-answer",
        tools,
        llm=fake_llm("USEFUL", "You spent 800.00 UAH on groceries in January 2024."),
        embeddings=HashingEmbeddings(),
    )
    assert resp.answer == "You spent 800.00 UAH on groceries in January 2024."
    assert resp.grounded is True
    assert resp.rewritten is False
    assert resp.sources, "answer should cite retrieved fact cards"


def test_weak_grade_triggers_rewrite(agent, tools):
    # First grade WEAK -> rewrite -> second grade USEFUL -> answer.
    resp = agent.run(
        "and that one?",
        "t-rewrite",
        tools,
        llm=fake_llm("WEAK", "groceries spending in 2024-01", "USEFUL", "It was 800.00 UAH."),
        embeddings=HashingEmbeddings(),
    )
    assert resp.rewritten is True
    assert resp.answer == "It was 800.00 UAH."


# --------------------------------------------------------------------------- #
# Multi-turn memory                                                            #
# --------------------------------------------------------------------------- #

def test_multi_turn_memory_persists(agent, tools):
    cid = "t-memory"
    llm = fake_llm("USEFUL", "Jan groceries were 800.00 UAH.",
                   "USEFUL", "Feb groceries were 700.00 UAH.")
    agent.run("groceries in Jan 2024?", cid, tools, llm=llm, embeddings=HashingEmbeddings())
    agent.run("and the next month?", cid, tools, llm=llm, embeddings=HashingEmbeddings())

    saved = agent._checkpointer.get({"configurable": {"thread_id": cid}})
    messages = saved["channel_values"]["messages"]
    # 2 human + 2 ai messages accumulated across the two turns.
    assert len(messages) == 4
    human_texts = [m.content for m in messages if isinstance(m, HumanMessage)]
    assert "groceries in Jan 2024?" in human_texts
    assert "and the next month?" in human_texts


def test_separate_conversations_do_not_share_memory(agent, tools):
    agent.run("groceries in Jan?", "conv-a", tools,
              llm=fake_llm("USEFUL", "800 UAH"), embeddings=HashingEmbeddings())
    other = agent._checkpointer.get({"configurable": {"thread_id": "conv-b"}})
    assert other is None  # conv-b was never used


# --------------------------------------------------------------------------- #
# Graceful fallback (LLM unavailable)                                          #
# --------------------------------------------------------------------------- #

def test_fallback_when_llm_unreachable(agent, tools):
    resp = agent.run(
        "How much on groceries in January 2024?",
        "t-fallback",
        tools,
        llm=BoomLLM(responses=["unused"]),
        embeddings=HashingEmbeddings(),
    )
    assert resp.grounded is False
    # Fallback still surfaces real, service-computed figures from the fact cards.
    assert "UAH" in resp.answer
    assert resp.sources


def test_fallback_with_no_data_is_graceful(tmp_path, monkeypatch, agent):
    monkeypatch.setattr("app.ml.forecaster.MODEL_FILE", str(tmp_path / "model.joblib"))
    monkeypatch.setattr("app.ml.forecaster.META_FILE", str(tmp_path / "meta.json"))
    monkeypatch.setattr("app.config.settings.MODEL_PATH", str(tmp_path))
    forecasting_service.forecaster = ExpenseForecaster()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    empty_tools = FinanceTools(ExpenseRepository(sessionmaker(bind=engine)()))
    resp = agent.run("anything?", "t-empty", empty_tools,
                     llm=BoomLLM(responses=["unused"]), embeddings=HashingEmbeddings())
    assert resp.grounded is False
    assert resp.answer  # a non-empty, friendly message
    assert resp.sources == []


# --------------------------------------------------------------------------- #
# HTTP endpoint (offline: agent deps mocked)                                   #
# --------------------------------------------------------------------------- #

def test_chat_endpoint_offline(client, db, monkeypatch):
    _seed(db)
    monkeypatch.setattr(
        "app.services.chat_agent._safe_chat_model",
        lambda streaming=False: fake_llm("USEFUL", "You spent 800.00 UAH on groceries in January 2024."),
    )
    monkeypatch.setattr(
        "app.services.finance_retriever.get_embeddings",
        lambda: HashingEmbeddings(),
    )

    r = client.post("/chat", json={
        "message": "How much did I spend on groceries in January 2024?",
        "conversation_id": "http-test-1",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "You spent 800.00 UAH on groceries in January 2024."
    assert body["conversation_id"] == "http-test-1"
    assert body["grounded"] is True
    assert len(body["sources"]) >= 1
