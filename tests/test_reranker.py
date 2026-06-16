"""Tests for the reranker (lexical default + LLM option)."""
import os

os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.services.reranker import lexical_rerank, lexical_score, rerank


def _docs():
    return [
        Document(page_content="In 2024-02, spending on Dining was 250.00 UAH."),
        Document(page_content="In 2024-01, spending on Groceries was 800.00 UAH over 2 transactions."),
        Document(page_content="Forecast for 2024-04: Car/Fuel predicted at 1400.00 UAH."),
        Document(page_content="In 2024-01, spending on Groceries was the largest grocery month."),
    ]


def test_lexical_rerank_promotes_relevant_doc():
    # The most groceries+January relevant docs should rank top, even though they
    # are not first in the input order.
    ranked = lexical_rerank("groceries spending in January 2024", _docs(), top_n=2)
    assert all("Groceries" in d.page_content for d in ranked)


def test_lexical_score_zero_for_no_overlap():
    assert lexical_score(["xyz", "qwerty"], "completely unrelated text") == 0.0
    assert lexical_score(["groceries"], "spending on groceries") > 0.0


def test_rerank_truncates_to_top_n():
    ranked = rerank("groceries", _docs(), top_n=2)
    assert len(ranked) == 2


def test_rerank_empty_returns_empty():
    assert rerank("anything", [], top_n=3) == []


def test_rerank_defaults_to_lexical_when_no_llm():
    # No llm passed -> deterministic lexical path (must not call any model).
    ranked = rerank("car fuel forecast", _docs(), top_n=1)
    assert "Car/Fuel" in ranked[0].page_content


def test_llm_rerank_path_is_resilient(monkeypatch):
    # FakeListChatModel can't do structured output -> llm_rerank scores 0 and
    # falls back to original order without crashing.
    monkeypatch.setattr("app.config.settings.RAG_RERANK_LLM", True)
    ranked = rerank("groceries", _docs(), top_n=2, llm=FakeListChatModel(responses=["0.9"]))
    assert len(ranked) == 2
