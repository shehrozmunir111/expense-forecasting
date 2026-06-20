import logging
import uuid
from typing import List, Optional

from langchain_core.embeddings import Embeddings

from app.config import settings
from app.services.llm_provider import get_embeddings

logger = logging.getLogger(__name__)


class LongTermMemory:
    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection: Optional[str] = None,
        embeddings: Optional[Embeddings] = None,
    ):
        self.persist_dir = persist_dir or settings.LTM_PERSIST_DIR
        self.collection = collection or settings.LTM_COLLECTION
        self._embeddings = embeddings
        self._store = None

    @property
    def embeddings(self) -> Embeddings:
        if self._embeddings is None:
            self._embeddings = get_embeddings()
        return self._embeddings

    def _get_store(self):
        if self._store is None:
            import os

            from langchain_chroma import Chroma

            os.makedirs(self.persist_dir, exist_ok=True)
            self._store = Chroma(
                collection_name=self.collection,
                embedding_function=self.embeddings,
                persist_directory=self.persist_dir,
            )
        return self._store

    def add(self, user_id: str, text: str, kind: str = "turn") -> None:
        if not text:
            return
        try:
            self._get_store().add_texts(
                texts=[text],
                metadatas=[{"user_id": user_id, "kind": kind}],
                ids=[f"{user_id}:{uuid.uuid4().hex}"],
            )
        except Exception as exc:  # pragma: no cover - memory is best-effort
            logger.warning("LTM add failed (%s).", exc)

    def add_turn(self, user_id: str, question: str, answer: str) -> None:
        self.add(user_id, f"User asked: {question}\nAssistant answered: {answer}", kind="turn")

    def recall(self, user_id: str, query: str, k: Optional[int] = None) -> List[str]:
        try:
            docs = self._get_store().similarity_search(
                query, k=k or settings.LTM_RECALL_K, filter={"user_id": user_id}
            )
            return [d.page_content for d in docs]
        except Exception as exc:  # pragma: no cover
            logger.warning("LTM recall failed (%s).", exc)
            return []

    def recall_text(self, user_id: str, query: str, k: Optional[int] = None) -> str:
        memories = self.recall(user_id, query, k)
        if not memories:
            return ""
        return "Relevant context from earlier conversations:\n" + "\n".join(
            f"- {m}" for m in memories
        )


# Module-level persistent memory store (one per process).
long_term_memory = LongTermMemory()
