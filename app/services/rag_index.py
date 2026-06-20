import json
import logging
import os
import threading
from typing import List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.config import settings
from app.models.expense import CategorizationStatus
from app.services.finance_retriever import build_fact_cards
from app.services.finance_tools import FinanceTools
from app.services.llm_provider import get_embeddings

logger = logging.getLogger(__name__)


def build_documents(tools: FinanceTools, tx_limit: int = 10000) -> Tuple[List[Document], List[str]]:
    """Build (documents, stable_ids) from deterministic services + transactions."""
    docs = build_fact_cards(tools)
    ids = [f"{d.metadata.get('kind', 'fact')}:{d.metadata.get('label', i)}"
           for i, d in enumerate(docs)]

    # Transaction-level documents (categorized expenses only).
    rows = tools.repo.get_all(limit=tx_limit, is_income=False)
    for e in rows:
        if not e.category or e.categorization_status not in (
            CategorizationStatus.CATEGORIZED, CategorizationStatus.MANUAL
        ):
            continue
        month = e.date.strftime("%Y-%m")
        docs.append(Document(
            page_content=(
                f"Transaction on {e.date}: \"{e.raw_text}\" — {float(e.amount):.2f} "
                f"{e.currency} categorized as {e.category}."
            ),
            metadata={
                "kind": "transaction",
                "category": e.category,
                "month": month,
                "label": f"tx#{e.id} {e.category} {month}",
            },
        ))
        ids.append(f"tx:{e.id}")
    return docs, ids


class RagIndex:
    """Persistent Chroma index with fingerprint-based refresh (embeddings injectable for tests)."""

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection: Optional[str] = None,
        embeddings: Optional[Embeddings] = None,
    ):
        self.persist_dir = persist_dir or settings.RAG_PERSIST_DIR
        self.collection = collection or settings.RAG_COLLECTION
        self._embeddings = embeddings
        self._store = None
        self._lock = threading.Lock()

    # -- embeddings / store ------------------------------------------------ #

    @property
    def embeddings(self) -> Embeddings:
        if self._embeddings is None:
            self._embeddings = get_embeddings()
        return self._embeddings

    def _get_store(self):
        if self._store is None:
            from langchain_chroma import Chroma

            os.makedirs(self.persist_dir, exist_ok=True)
            self._store = Chroma(
                collection_name=self.collection,
                embedding_function=self.embeddings,
                persist_directory=self.persist_dir,
            )
        return self._store

    def _count(self) -> int:
        try:
            return self._get_store()._collection.count()
        except Exception:  # pragma: no cover
            return 0

    # -- fingerprint sidecar ---------------------------------------------- #

    @property
    def _fingerprint_path(self) -> str:
        return os.path.join(self.persist_dir, f"{self.collection}.fingerprint.json")

    def _read_fingerprint(self) -> Optional[str]:
        try:
            with open(self._fingerprint_path) as f:
                return json.load(f).get("signature")
        except Exception:
            return None

    def _write_fingerprint(self, signature: str, n_docs: int) -> None:
        os.makedirs(self.persist_dir, exist_ok=True)
        with open(self._fingerprint_path, "w") as f:
            json.dump({"signature": signature, "documents": n_docs}, f)

    # -- public API -------------------------------------------------------- #

    def ensure_fresh(self, tools: FinanceTools, force: bool = False) -> dict:
        """Reindex only if the dataset changed (or force=True). Returns a status."""
        signature = json.dumps(tools.repo.dataset_signature(), sort_keys=True)
        with self._lock:
            if not force and signature == self._read_fingerprint() and self._count() > 0:
                return {"status": "cached", "documents": self._count()}

            docs, ids = build_documents(tools)
            store = self._get_store()
            try:
                store.delete_collection()  # drop stale (handles edits/deletes)
            except Exception:  # pragma: no cover
                pass
            self._store = None
            store = self._get_store()  # fresh, empty collection
            if docs:
                store.add_documents(docs, ids=ids)  # stable ids => idempotent
            self._write_fingerprint(signature, len(docs))
            logger.info("RAG index rebuilt: %d documents (%s).", len(docs), self.collection)
            return {"status": "rebuilt", "documents": len(docs)}

    def retrieve(self, query: str, k: Optional[int] = None) -> List[Document]:
        if self._count() == 0:
            return []
        k = k or settings.CHAT_RETRIEVAL_K
        if settings.RAG_RERANK:
            from app.services.reranker import rerank

            candidates = self._get_store().similarity_search(query, k=max(k, settings.RAG_FETCH_K))
            return rerank(query, candidates, k)
        return self._get_store().similarity_search(query, k=k)


class RagIndexRetriever:
    """Per-request adapter matching the FinanceRetriever interface; ensures freshness, then serves search."""

    def __init__(self, index: RagIndex, tools: FinanceTools, k: Optional[int] = None):
        self.index = index
        self.tools = tools
        self.k = k
        self._fresh = False

    def retrieve(self, query: str, k: Optional[int] = None) -> List[Document]:
        if not self._fresh:
            try:
                self.index.ensure_fresh(self.tools)
            except Exception as exc:  # pragma: no cover - degrade gracefully
                logger.warning("RAG ensure_fresh failed (%s); querying as-is.", exc)
            self._fresh = True
        return self.index.retrieve(query, k=k or self.k)

    def close(self) -> None:
        pass


# Module-level persistent index (one per process).
rag_index = RagIndex()
