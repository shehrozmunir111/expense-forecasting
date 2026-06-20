import logging
import re
from collections import Counter
from typing import List

from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def lexical_score(query_tokens: List[str], doc_text: str) -> float:
    tokens = _tokenize(doc_text)
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    tf = sum(counts.get(q, 0) for q in query_tokens)
    return tf / (len(tokens) ** 0.5)  # length-normalized term frequency


def lexical_rerank(query: str, docs: List[Document], top_n: int) -> List[Document]:
    q_tokens = list(dict.fromkeys(_tokenize(query)))  # unique, order-preserving
    # Stable sort: ties keep original (vector-similarity) order.
    scored = sorted(
        enumerate(docs),
        key=lambda iv: (-lexical_score(q_tokens, iv[1].page_content), iv[0]),
    )
    return [d for _, d in scored[:top_n]]


def llm_rerank(query: str, docs: List[Document], top_n: int, llm) -> List[Document]:
    """Score each doc's relevance (0-1) with the LLM; keep the highest top_n."""
    from langchain_core.prompts import ChatPromptTemplate
    from pydantic import BaseModel, Field

    class _Score(BaseModel):
        relevance: float = Field(description="0.0 (irrelevant) to 1.0 (highly relevant)")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Score how relevant the fact is to answering the question. Reply with a number 0-1."),
        ("human", "Question: {q}\n\nFact: {d}"),
    ])
    scored = []
    for i, d in enumerate(docs):
        try:
            res = (prompt | llm.with_structured_output(_Score)).invoke(
                {"q": query, "d": d.page_content})
            score = float(res.relevance)
        except Exception as exc:  # pragma: no cover - degrade to lexical position
            logger.debug("llm_rerank failed on doc %d (%s); scoring 0.", i, exc)
            score = 0.0
        scored.append((score, i, d))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [d for _, _, d in scored[:top_n]]


def rerank(query: str, docs: List[Document], top_n: int, llm=None) -> List[Document]:
    """Dispatch to LLM reranking when configured and an llm is provided; else lexical."""
    if not docs:
        return []
    if llm is not None and settings.RAG_RERANK_LLM:
        return llm_rerank(query, docs, top_n, llm)
    return lexical_rerank(query, docs, top_n)
