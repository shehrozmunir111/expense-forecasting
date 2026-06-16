"""Tests for long-term / semantic memory (per-user persistent recall)."""
import os

os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.services.llm_provider import HashingEmbeddings
from app.services.long_term_memory import LongTermMemory


@pytest.fixture
def memory(tmp_path):
    return LongTermMemory(persist_dir=str(tmp_path / "mem"), collection="test_mem",
                          embeddings=HashingEmbeddings())


def test_add_and_recall(memory):
    memory.add("user-1", "User prefers to call Car/Fuel expenses 'gaadi kharcha'.")
    memory.add("user-1", "User asked about groceries spending in January.")
    hits = memory.recall("user-1", "what did I call my car expenses?", k=2)
    assert hits
    assert any("gaadi" in h for h in hits)


def test_recall_is_user_scoped(memory):
    memory.add("user-a", "User A loves tracking groceries.")
    memory.add("user-b", "User B only cares about fuel.")
    a_hits = memory.recall("user-a", "groceries", k=5)
    assert all("User A" in h or "groceries" in h.lower() for h in a_hits)
    assert all("User B" not in h for h in a_hits)


def test_recall_text_formats_or_empty(memory):
    assert memory.recall_text("nobody", "anything") == ""
    memory.add_turn("user-1", "How much on dining?", "You spent 250 UAH.")
    text = memory.recall_text("user-1", "dining")
    assert "earlier conversations" in text.lower()
    assert "250" in text


def test_persistence_across_instances(tmp_path):
    d = str(tmp_path / "mem")
    m1 = LongTermMemory(persist_dir=d, collection="persist_mem", embeddings=HashingEmbeddings())
    m1.add("user-1", "User prefers concise answers.")
    m2 = LongTermMemory(persist_dir=d, collection="persist_mem", embeddings=HashingEmbeddings())
    assert m2.recall("user-1", "answer style", k=3)  # survives a new instance


def test_chat_endpoint_stores_memory(client, db, tmp_path, monkeypatch):
    from tests.conftest import seed_categorized
    seed_categorized(db)
    monkeypatch.setattr("app.config.settings.LONG_TERM_MEMORY", True)
    test_mem = LongTermMemory(persist_dir=str(tmp_path / "mem"), collection="http_mem",
                              embeddings=HashingEmbeddings())
    monkeypatch.setattr("app.routers.chat.long_term_memory", test_mem)
    monkeypatch.setattr(
        "app.services.chat_agent._safe_chat_model",
        lambda streaming=False: FakeListChatModel(responses=["USEFUL", "You spent 800.00 UAH."]),
    )
    monkeypatch.setattr("app.services.finance_retriever.get_embeddings", lambda: HashingEmbeddings())

    client.post("/chat", json={"message": "groceries in Jan 2024?", "conversation_id": "mem-http"})
    # The turn should have been stored for later recall.
    assert test_mem.recall("mem-http", "groceries", k=3)
