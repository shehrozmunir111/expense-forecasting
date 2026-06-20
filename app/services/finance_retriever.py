import logging
import uuid
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.config import settings
from app.services.finance_tools import FinanceTools
from app.services.llm_provider import get_embeddings

logger = logging.getLogger(__name__)


def build_fact_cards(tools: FinanceTools, max_months: int = 6) -> List[Document]:
    """Turn deterministic service output into retrievable Documents."""
    docs: List[Document] = []
    months = tools.distinct_months()
    recent = months[-max_months:] if months else []

    # All-time per-category totals
    for r in tools.category_summary():
        docs.append(
            Document(
                page_content=(
                    f"All-time spending on {r['category']}: {r['total']:.2f} USD "
                    f"across {r['count']} transactions ({r['percentage']}% of total spending)."
                ),
                metadata={
                    "kind": "category_summary",
                    "scope": "all_time",
                    "category": r["category"],
                    "label": f"{r['category']} (all-time)",
                },
            )
        )

    # Per recent month: a summary card + one card per category in that month
    for m in recent:
        ms = tools.monthly_summary(m)
        top = ", ".join(f"{c['category']} {c['total']:.0f}" for c in ms["categories"][:3]) or "no expenses"
        docs.append(
            Document(
                page_content=(
                    f"Month {m}: total expenses {ms['total_expenses']:.2f} USD, "
                    f"income {ms['total_income']:.2f} USD, net {ms['net']:.2f} USD. "
                    f"Top categories: {top}."
                ),
                metadata={"kind": "monthly_summary", "month": m, "label": f"Summary {m}"},
            )
        )
        for c in tools.category_summary(month=m):
            docs.append(
                Document(
                    page_content=(
                        f"In {m}, spending on {c['category']} was {c['total']:.2f} USD "
                        f"over {c['count']} transactions ({c['percentage']}% of that month)."
                    ),
                    metadata={
                        "kind": "category_summary",
                        "scope": m,
                        "month": m,
                        "category": c["category"],
                        "label": f"{c['category']} {m}",
                    },
                )
            )

    # Forecast cards (next month), when the model has enough history
    fc = tools.forecast()
    if fc:
        fmonth = fc["forecast_month"]
        for cat, d in fc["predictions"].items():
            docs.append(
                Document(
                    page_content=(
                        f"Forecast for {fmonth}: {cat} predicted at {d['predicted_amount']:.2f} USD "
                        f"(range {d['confidence_interval_low']:.0f}-{d['confidence_interval_high']:.0f}, "
                        f"trend {d['trend']})."
                    ),
                    metadata={"kind": "forecast", "month": fmonth, "category": cat, "label": f"Forecast {cat} {fmonth}"},
                )
            )

    return docs


class FinanceRetriever:
    """Vector retrieval over the fact-card corpus, backed by Chroma (embeddings injectable for tests)."""

    def __init__(
        self,
        tools: FinanceTools,
        embeddings: Optional[Embeddings] = None,
        k: Optional[int] = None,
        max_months: int = 6,
    ):
        self.tools = tools
        self.k = k or settings.CHAT_RETRIEVAL_K
        self._embeddings = embeddings
        self._docs = build_fact_cards(tools, max_months=max_months)
        self._collection_name = "finance_chat_" + uuid.uuid4().hex[:12]
        self._client = None
        self._store = None

    @property
    def documents(self) -> List[Document]:
        return self._docs

    @property
    def embeddings(self) -> Embeddings:
        if self._embeddings is None:
            self._embeddings = get_embeddings()
        return self._embeddings

    def _ensure_store(self):
        if self._store is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            from langchain_chroma import Chroma

            self._client = chromadb.EphemeralClient(
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            self._store = Chroma(
                client=self._client,
                collection_name=self._collection_name,
                embedding_function=self.embeddings,
            )
            if self._docs:
                self._store.add_documents(self._docs)
        return self._store

    def retrieve(self, query: str, k: Optional[int] = None) -> List[Document]:
        if not self._docs:
            return []
        store = self._ensure_store()
        k = k or self.k
        if settings.RAG_RERANK:
            from app.services.reranker import rerank

            candidates = store.similarity_search(query, k=max(k, settings.RAG_FETCH_K))
            return rerank(query, candidates, k)
        return store.similarity_search(query, k=k)

    def close(self) -> None:
        """Drop the ephemeral collection so per-request memory is reclaimed."""
        if self._client is not None:
            try:
                self._client.delete_collection(self._collection_name)
            except Exception:  # pragma: no cover - best effort cleanup
                pass
        self._store = None
        self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
