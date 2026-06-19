"""Lightweight, dependency-free guardrails for the chat feature.

- **Input guard**: blocks oversized input and obvious prompt-injection attempts;
  flags likely off-topic questions (soft flag, not a block).
- **Output guard**: verifies *groundedness* — every amount-like number in the
  answer must appear in the retrieved context; otherwise the answer is flagged
  as ungrounded (a possible hallucination). Also flags leaked PII (emails).

This is intentionally a small, transparent, offline-testable layer rather than a
heavy external framework (NeMo Guardrails / guardrails-ai). Those can be swapped
in later behind the same `check_input` / `check_output` interface.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

# Prompt-injection / jailbreak patterns (case-insensitive).
_INJECTION_PATTERNS = [
    r"ignore (all|any|previous|prior|the above)",
    r"disregard (all|any|previous|prior|the above)",
    r"forget (all|everything|previous|your)",
    r"you are now",
    r"system prompt",
    r"reveal your (system )?prompt",
    r"act as (an?|the)",
    r"developer mode",
    r"jailbreak",
]

# A few finance words; absence is a soft off-topic flag (never a hard block).
_FINANCE_HINTS = [
    "spend", "spent", "spending", "expense", "expenses", "budget", "cost", "paid",
    "category", "categories", "forecast", "month", "housing", "transportation",
    "dining", "food", "utilities", "insurance", "healthcare", "entertainment",
    "shopping", "education", "travel", "subscriptions", "salary", "freelance",
    "investment", "income", "transaction", "total", "save", "saving", "money",
]

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Amount-like numbers: 3+ digits, or anything with a decimal/thousands separator.
_AMOUNT_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{3,}")

MAX_INPUT_CHARS = 2000


@dataclass
class InputGuard:
    allowed: bool
    reason: str = ""
    flags: List[str] = field(default_factory=list)


@dataclass
class OutputGuard:
    passed: bool
    grounded: bool
    flags: List[str] = field(default_factory=list)
    ungrounded_numbers: List[str] = field(default_factory=list)


def check_input(message: str) -> InputGuard:
    flags: List[str] = []
    text = (message or "").strip()

    if not text:
        return InputGuard(allowed=False, reason="empty message")
    if len(text) > MAX_INPUT_CHARS:
        return InputGuard(allowed=False, reason="message too long", flags=["too_long"])

    low = text.lower()
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, low):
            return InputGuard(allowed=False, reason="possible prompt injection",
                              flags=["prompt_injection"])

    if not any(h in low for h in _FINANCE_HINTS):
        flags.append("possibly_off_topic")  # soft flag only

    return InputGuard(allowed=True, flags=flags)


def _normalize_number(token: str) -> str:
    token = token.replace(",", "")
    if "." in token:
        token = token.rstrip("0").rstrip(".")  # 800.00 -> 800
    return token


def check_output(answer: str, context: str) -> OutputGuard:
    """Flag any amount-like number in `answer` that is absent from `context`."""
    flags: List[str] = []
    ctx = (context or "").replace(",", "")
    ctx_norm = ctx
    # Pre-normalize context numbers so 800 matches 800.00 in the answer.
    for m in _AMOUNT_RE.findall(ctx):
        ctx_norm += " " + _normalize_number(m)

    ungrounded: List[str] = []
    for raw in _AMOUNT_RE.findall(answer or ""):
        norm = _normalize_number(raw)
        if norm and norm not in ctx_norm:
            ungrounded.append(raw)

    grounded = not ungrounded
    if ungrounded:
        flags.append("ungrounded_numbers")
    if _EMAIL_RE.search(answer or ""):
        flags.append("pii_email")

    return OutputGuard(passed=grounded and "pii_email" not in flags,
                       grounded=grounded, flags=flags, ungrounded_numbers=ungrounded)


REFUSAL_MESSAGE = (
    "I can only help with questions about your own expenses and forecasts. "
    "Please rephrase your question about your spending."
)
