"""Tests for the production RAG index (app/services/rag_index.py).

Offline: a tmp persist dir + HashingEmbeddings, no LM Studio. Covers document
build (fact cards + transactions + stable ids), fingerprint caching, rebuild on
data change, dedup (no duplicate ids), retrieval recall, and the /chat/reindex
endpoint.
"""
import os

os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.ml.forecaster import ExpenseForecaster
from app.models.expense import Expense
from app.repositories.expense_repo import ExpenseRepository
from app.services.finance_tools import FinanceTools
from app.services.forecasting import forecasting_service
from app.services.llm_provider import HashingEmbeddings
from app.services.rag_index import RagIndex, RagIndexRetriever, build_documents


@pytest.fixture
def index(tmp_path):
    return RagIndex(
        persist_dir=str(tmp_path / "chroma"),
        collection="test_facts",
        embeddings=HashingEmbeddings(),
    )


def _add(db, category, amount, d, status="categorized"):
    db.add(Expense(raw_text=f"{category} tx", amount=amount, currency="USD",
                   date=d, category=category, categorization_status=status))
    db.commit()


# --------------------------------------------------------------------------- #
# Document building                                                            #
# --------------------------------------------------------------------------- #

def test_build_documents_has_cards_and_transactions(seeded_tools):
    docs, ids = build_documents(seeded_tools)
    assert len(docs) == len(ids)
    assert len(set(ids)) == len(ids), "ids must be unique (dedup)"
    kinds = {d.metadata["kind"] for d in docs}
    assert "category_summary" in kinds
    assert "transaction" in kinds  # transaction-level docs included
    # a Jan groceries transaction doc carries category/month metadata
    tx = [d for d in docs if d.metadata["kind"] == "transaction"
          and d.metadata.get("category") == "Food & Dining" and d.metadata.get("month") == "2024-01"]
    assert tx


# --------------------------------------------------------------------------- #
# Persistence + fingerprint caching + rebuild                                  #
# --------------------------------------------------------------------------- #

def test_ensure_fresh_rebuilds_then_caches(index, seeded_tools):
    first = index.ensure_fresh(seeded_tools)
    assert first["status"] == "rebuilt"
    assert first["documents"] > 0
    # Unchanged data -> served from cache (no re-embedding).
    second = index.ensure_fresh(seeded_tools)
    assert second["status"] == "cached"
    assert second["documents"] == first["documents"]


def test_ensure_fresh_detects_data_change(index, seeded_tools):
    index.ensure_fresh(seeded_tools)
    before = index._count()
    # Add a new transaction -> signature changes -> rebuild with more docs.
    _add(seeded_tools.repo.db, "Food & Dining", 99.0, date(2024, 3, 20))
    result = index.ensure_fresh(seeded_tools)
    assert result["status"] == "rebuilt"
    assert index._count() > before


def test_no_duplicate_documents_on_forced_rebuild(index, seeded_tools):
    index.ensure_fresh(seeded_tools)
    count1 = index._count()
    index.ensure_fresh(seeded_tools, force=True)  # rebuild same data
    assert index._count() == count1  # stable ids -> no duplicates


def test_persistence_survives_new_instance(tmp_path, seeded_tools):
    persist = str(tmp_path / "chroma")
    idx1 = RagIndex(persist_dir=persist, collection="persist_test", embeddings=HashingEmbeddings())
    idx1.ensure_fresh(seeded_tools)
    n = idx1._count()
    # New instance over the same dir reads the persisted vectors + fingerprint.
    idx2 = RagIndex(persist_dir=persist, collection="persist_test", embeddings=HashingEmbeddings())
    assert idx2._count() == n
    assert idx2.ensure_fresh(seeded_tools)["status"] == "cached"


# --------------------------------------------------------------------------- #
# Retrieval                                                                    #
# --------------------------------------------------------------------------- #

def test_retrieve_recall(index, seeded_tools):
    index.ensure_fresh(seeded_tools)
    docs = index.retrieve("Food & Dining spending in January 2024", k=5)
    assert docs
    assert any("Food & Dining" in (d.metadata.get("category") or "") for d in docs)


def test_retriever_adapter_lazy_refresh(index, seeded_tools):
    retriever = RagIndexRetriever(index, seeded_tools, k=3)
    docs = retriever.retrieve("biggest transportation spending")
    assert docs
    retriever.close()  # no-op for persistent index; must not raise
    assert index._count() > 0


def test_retrieve_empty_index_returns_empty(tmp_path):
    empty = RagIndex(persist_dir=str(tmp_path / "c"), collection="empty", embeddings=HashingEmbeddings())
    assert empty.retrieve("anything") == []


# --------------------------------------------------------------------------- #
# /chat/reindex endpoint                                                       #
# --------------------------------------------------------------------------- #

def test_reindex_endpoint(client, db, tmp_path, monkeypatch):
    from tests.conftest import seed_categorized
    seed_categorized(db)
    # Enable persistent RAG for this test, pointed at a tmp dir + offline embeddings.
    monkeypatch.setattr("app.config.settings.RAG_PERSISTENT", True)
    test_index = RagIndex(persist_dir=str(tmp_path / "chroma"), collection="ep_test",
                          embeddings=HashingEmbeddings())
    monkeypatch.setattr("app.routers.chat.rag_index", test_index)

    r = client.post("/chat/reindex")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "rebuilt"
    assert body["documents"] > 0
    # Second call without changes -> cached.
    assert client.post("/chat/reindex", params={"force": "false"}).json()["status"] == "cached"
