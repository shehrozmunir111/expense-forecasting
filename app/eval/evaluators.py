"""AI evaluation harness for the chat feature.

Three evaluator families:

- **numeric_match** (deterministic): does the answer contain the exact figure the
  services compute? This is the strongest signal — it catches hallucinated or
  miscomputed numbers without any judge model.
- **retrieval_hit** (deterministic): did retrieval surface a fact relevant to the
  expected category/month? (retrieval recall@k)
- **judge_answer** (LLM-as-judge): faithfulness / relevance / correctness scored
  by a judge LLM with structured output (offline-capable via the local model;
  degrades to text parsing, then to None if the judge is unavailable).

``run_evaluation`` ties them together over a dataset and returns per-item rows
plus aggregate rates. It is agnostic to which agent produced the answer — callers
pass an ``answer_fn(question) -> {"answer", "sources"}``.
"""
import json
import logging
import os
import re
from typing import Callable, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DATASET_PATH = os.path.join(os.path.dirname(__file__), "questions.json")


def load_dataset(path: Optional[str] = None) -> List[dict]:
    with open(path or DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Deterministic evaluators                                                     #
# --------------------------------------------------------------------------- #

def numeric_match(answer: str, expected_number: Optional[float]) -> Optional[bool]:
    """True if `answer` contains `expected_number` (common formattings).

    Returns None when there is no expected number to check.
    """
    if expected_number is None:
        return None
    haystack = answer.replace(",", "")
    candidates = {
        f"{expected_number:.2f}",
        f"{expected_number:.1f}",
        f"{expected_number:.0f}",
        str(int(expected_number)) if float(expected_number).is_integer() else f"{expected_number}",
    }
    return any(c in haystack for c in candidates)


def retrieval_hit(
    sources: List,
    expected_category: Optional[str],
    expected_month: Optional[str],
) -> Optional[bool]:
    """True if any source mentions the expected category and month (recall@k).

    `sources` items may be Pydantic Source objects or dicts with label/detail.
    Returns None when there is nothing specific to look for.
    """
    if not expected_category and not expected_month:
        return None
    if not sources:
        return False

    def text_of(s) -> str:
        if isinstance(s, dict):
            return f"{s.get('label', '')} {s.get('detail', '')}".lower()
        return f"{getattr(s, 'label', '')} {getattr(s, 'detail', '')}".lower()

    for s in sources:
        t = text_of(s)
        cat_ok = (not expected_category) or (expected_category.lower() in t)
        month_ok = (not expected_month) or (expected_month.lower() in t)
        if cat_ok and month_ok:
            return True
    return False


# --------------------------------------------------------------------------- #
# LLM-as-judge                                                                 #
# --------------------------------------------------------------------------- #

class JudgeVerdict(BaseModel):
    faithful: bool = Field(description="Answer is supported by the provided context; no invented facts.")
    relevant: bool = Field(description="Answer addresses the question.")
    correct: bool = Field(description="Answer is factually correct given the context.")


_JUDGE_SYSTEM = (
    "You are a strict evaluator of a finance assistant's answer. Judge only from "
    "the provided context. Mark `faithful` false if the answer states figures not "
    "present in the context."
)
_JUDGE_HUMAN = (
    "Question:\n{question}\n\nContext (ground-truth facts):\n{context}\n\n"
    "Answer to evaluate:\n{answer}"
)


def judge_answer(question: str, answer: str, context: str, judge_llm) -> Optional[JudgeVerdict]:
    """LLM-as-judge verdict, or None if no judge / the judge is unreachable."""
    if judge_llm is None:
        return None
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_messages(
        [("system", _JUDGE_SYSTEM), ("human", _JUDGE_HUMAN)]
    )
    payload = {"question": question, "answer": answer, "context": context}
    try:
        chain = prompt | judge_llm.with_structured_output(JudgeVerdict)
        return chain.invoke(payload)
    except Exception as exc:
        logger.debug("structured judge failed (%s); trying text parse.", exc)
    try:
        text_prompt = ChatPromptTemplate.from_messages(
            [("system", _JUDGE_SYSTEM + " Reply with faithful=, relevant=, correct= each yes or no."),
             ("human", _JUDGE_HUMAN)]
        )
        verdict = (text_prompt | judge_llm | StrOutputParser()).invoke(payload).lower()

        def flag(name: str) -> bool:
            m = re.search(rf"{name}\s*[:=]\s*(yes|true|no|false)", verdict)
            return bool(m and m.group(1) in ("yes", "true"))

        return JudgeVerdict(faithful=flag("faithful"), relevant=flag("relevant"), correct=flag("correct"))
    except Exception as exc:
        logger.warning("judge LLM unavailable (%s); skipping judge.", exc)
        return None


# --------------------------------------------------------------------------- #
# Orchestration                                                                #
# --------------------------------------------------------------------------- #

def _rate(values: List[Optional[bool]]) -> Optional[float]:
    scored = [v for v in values if v is not None]
    if not scored:
        return None
    return round(sum(1 for v in scored if v) / len(scored), 3)


def run_evaluation(
    dataset: List[dict],
    answer_fn: Callable[[str], dict],
    judge_llm=None,
    k_recall: Optional[int] = None,
) -> dict:
    """Evaluate `answer_fn` over `dataset`. Returns {"items":[...], "aggregate":{...}}.

    `answer_fn(question)` must return {"answer": str, "sources": [...]}.
    """
    items = []
    for ex in dataset:
        result = answer_fn(ex["question"])
        answer = result.get("answer", "")
        sources = result.get("sources", []) or []
        context = "\n".join(
            (s.get("detail") if isinstance(s, dict) else getattr(s, "detail", "")) for s in sources
        )

        num_ok = numeric_match(answer, ex.get("expected_number"))
        recall_ok = retrieval_hit(sources, ex.get("expected_category"), ex.get("expected_month"))
        verdict = judge_answer(ex["question"], answer, context, judge_llm) if judge_llm else None

        items.append({
            "question": ex["question"],
            "answer": answer,
            "expected_number": ex.get("expected_number"),
            "numeric_match": num_ok,
            "retrieval_hit": recall_ok,
            "judge": verdict.model_dump() if verdict else None,
        })

    aggregate = {
        "n": len(items),
        "groundedness_numeric": _rate([i["numeric_match"] for i in items]),
        "retrieval_recall": _rate([i["retrieval_hit"] for i in items]),
    }
    judged = [i["judge"] for i in items if i["judge"]]
    if judged:
        aggregate["judge_faithful"] = _rate([j["faithful"] for j in judged])
        aggregate["judge_relevant"] = _rate([j["relevant"] for j in judged])
        aggregate["judge_correct"] = _rate([j["correct"] for j in judged])
    return {"items": items, "aggregate": aggregate}
