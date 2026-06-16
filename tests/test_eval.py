"""Tests for the AI evaluation harness (app/eval).

Offline: deterministic evaluators are tested directly; the LLM-as-judge is
exercised with FakeListChatModel; run_evaluation is driven by a stub answer_fn.
"""
import os

os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.eval.evaluators import (
    JudgeVerdict,
    judge_answer,
    load_dataset,
    numeric_match,
    retrieval_hit,
    run_evaluation,
)
from app.schemas.chat import Source


# --------------------------------------------------------------------------- #
# Dataset                                                                      #
# --------------------------------------------------------------------------- #

def test_dataset_loads_and_is_well_formed():
    data = load_dataset()
    assert len(data) >= 5
    for ex in data:
        assert "question" in ex
        assert "expected_number" in ex


# --------------------------------------------------------------------------- #
# numeric_match                                                                #
# --------------------------------------------------------------------------- #

def test_numeric_match_various_formats():
    assert numeric_match("You spent 800.00 UAH", 800.0) is True
    assert numeric_match("It was 800 UAH", 800.0) is True
    assert numeric_match("Total: 1,300.00 UAH", 1300.0) is True   # comma stripped
    assert numeric_match("You spent 750 UAH", 800.0) is False
    assert numeric_match("no number expected", None) is None


# --------------------------------------------------------------------------- #
# retrieval_hit                                                                #
# --------------------------------------------------------------------------- #

def test_retrieval_hit_matches_category_and_month():
    sources = [
        Source(kind="category_summary", label="Groceries 2024-01",
               detail="In 2024-01, spending on Groceries was 800.00 UAH."),
        Source(kind="forecast", label="Forecast Dining 2024-04", detail="..."),
    ]
    assert retrieval_hit(sources, "Groceries", "2024-01") is True
    assert retrieval_hit(sources, "Groceries", "2024-09") is False
    assert retrieval_hit(sources, None, None) is None
    assert retrieval_hit([], "Groceries", "2024-01") is False


def test_retrieval_hit_accepts_dict_sources():
    sources = [{"label": "Car/Fuel 2024-03", "detail": "In 2024-03, Car/Fuel was 1300.00 UAH."}]
    assert retrieval_hit(sources, "Car/Fuel", "2024-03") is True


# --------------------------------------------------------------------------- #
# LLM-as-judge                                                                 #
# --------------------------------------------------------------------------- #

def test_judge_none_without_llm():
    assert judge_answer("q", "a", "ctx", None) is None


def test_judge_text_fallback_parses_flags():
    # FakeListChatModel can't tool-call -> structured fails -> text parse path.
    llm = FakeListChatModel(responses=["faithful=yes relevant=yes correct=no"])
    verdict = judge_answer("q", "a", "ctx", llm)
    assert isinstance(verdict, JudgeVerdict)
    assert verdict.faithful is True and verdict.relevant is True and verdict.correct is False


# --------------------------------------------------------------------------- #
# run_evaluation                                                               #
# --------------------------------------------------------------------------- #

def test_run_evaluation_aggregates():
    dataset = [
        {"question": "groceries jan?", "expected_number": 800.0,
         "expected_category": "Groceries", "expected_month": "2024-01"},
        {"question": "car march?", "expected_number": 1300.0,
         "expected_category": "Car/Fuel", "expected_month": "2024-03"},
    ]

    def answer_fn(q):
        if "groceries" in q:
            return {"answer": "You spent 800.00 UAH.",
                    "sources": [Source(kind="category_summary", label="Groceries 2024-01",
                                       detail="In 2024-01 Groceries was 800.00 UAH.")]}
        return {"answer": "It was 999.00 UAH.",  # wrong number on purpose
                "sources": [Source(kind="category_summary", label="Car/Fuel 2024-03",
                                   detail="In 2024-03 Car/Fuel was 1300.00 UAH.")]}

    report = run_evaluation(dataset, answer_fn, judge_llm=None)
    assert report["aggregate"]["n"] == 2
    assert report["aggregate"]["groundedness_numeric"] == 0.5  # 1 of 2 correct
    assert report["aggregate"]["retrieval_recall"] == 1.0      # both retrieved right fact
    assert "judge_faithful" not in report["aggregate"]         # no judge -> no judge metrics


def test_run_evaluation_with_judge():
    dataset = [{"question": "groceries jan?", "expected_number": 800.0,
                "expected_category": "Groceries", "expected_month": "2024-01"}]

    def answer_fn(q):
        return {"answer": "You spent 800.00 UAH.",
                "sources": [Source(kind="category_summary", label="Groceries 2024-01",
                                   detail="In 2024-01 Groceries was 800.00 UAH.")]}

    judge = FakeListChatModel(responses=["faithful=yes relevant=yes correct=yes"])
    report = run_evaluation(dataset, answer_fn, judge_llm=judge)
    assert report["aggregate"]["judge_faithful"] == 1.0
    assert report["aggregate"]["judge_correct"] == 1.0
