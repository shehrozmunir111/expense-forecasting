"""Multi-agent supervisor with handoff.

Classifies each request and hands off to the right specialist:

- **action** -> HITL ActionAgent (modify/delete data, with approval)
- **qa**     -> Adaptive-RAG ChatAgent (analytical questions over the data)

Routing uses the LLM (structured output) with a deterministic keyword fallback,
so it still routes sensibly when the model is unavailable. The chosen route is
returned on the response as `routed_to`.
"""
import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.chat import ChatResponse
from app.services.action_agent import action_agent as _action_agent
from app.services.chat_agent import _safe_chat_model, chat_agent as _chat_agent
from app.services.finance_tools import FinanceTools

logger = logging.getLogger(__name__)

# Write-intent keywords for the deterministic fallback. Prefixes use \w* so
# "recategorize"/"reclassify" match; phrase patterns need their connector word.
_ACTION_RE = re.compile(
    r"\b(delete|remove|recategor\w*|re-categor\w*|reclassif\w*|update|rename)\b"
    r"|\bchange\b.*\bto\b|\bset\b.*\bcategor|\bmark\b.*\bas\b|\bmove\b.*\bto\b|\bfix\b.*\bcategor",
    re.IGNORECASE,
)

_CLASSIFY_SYSTEM = (
    "Route a personal-finance request. Return route='action' if the user wants to "
    "CHANGE or DELETE their data (recategorize, delete, update an expense). "
    "Otherwise return route='qa' (questions, summaries, forecasts)."
)


class _Route(BaseModel):
    route: str = Field(description="'action' or 'qa'")


def classify(message: str, llm) -> str:
    """Return 'action' or 'qa'. LLM-first with a keyword fallback."""
    if llm is not None:
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [("system", _CLASSIFY_SYSTEM), ("human", "{q}")]
        )
        try:
            res = (prompt | llm.with_structured_output(_Route)).invoke({"q": message})
            route = (res.route or "").strip().lower()
            if route in ("action", "qa"):
                return route
        except Exception as exc:
            logger.debug("LLM classify failed (%s); using keyword fallback.", exc)
    return "action" if _ACTION_RE.search(message or "") else "qa"


class Supervisor:
    def __init__(self, qa_agent=None, action_agent=None):
        self.qa_agent = qa_agent or _chat_agent
        self.action_agent = action_agent or _action_agent

    def run(
        self,
        message: str,
        conversation_id: Optional[str],
        tools: FinanceTools,
        llm=None,
        retriever=None,
    ) -> ChatResponse:
        llm = llm if llm is not None else _safe_chat_model()
        route = classify(message, llm)
        if route == "action":
            resp = self.action_agent.run(message, conversation_id, tools, llm=llm)
        else:
            resp = self.qa_agent.run(message, conversation_id, tools, llm=llm, retriever=retriever)
        resp.routed_to = route
        return resp


supervisor = Supervisor()
