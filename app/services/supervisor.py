"""Multi-agent supervisor with handoff.

Classifies each request and hands off to the right specialist:

- **action** -> HITL ActionAgent (modify/delete data, with approval)
- **agent**  -> ReAct FinanceAgent (complex analysis with tool calls)
- **rag**    -> Adaptive-RAG ChatAgent (simple fact-based Q&A)

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
from app.services.finance_agent import finance_react_agent as _finance_agent
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
    "Route a personal-finance request.\n"
    "- Return route='action' if the user wants to CHANGE or DELETE their data "
    "(recategorize, delete, update an expense).\n"
    "- Return route='agent' if the user asks a complex or comparative question "
    "that needs the LLM to call tools (e.g. 'which category did I spend the most on?', "
    "'compare this month to last month', 'show me my biggest expenses').\n"
    "- Return route='rag' for simple questions, summaries, or forecasts that can be "
    "answered from pre-built fact cards (e.g. 'how much did I spend on food?', "
    "'what is my forecast for next month?')."
)


class _Route(BaseModel):
    route: str = Field(description="'action', 'agent', or 'rag'")


def classify(message: str, llm) -> str:
    """Return 'action', 'agent', or 'rag'. LLM-first with a keyword fallback."""
    if llm is not None:
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [("system", _CLASSIFY_SYSTEM), ("human", "{q}")]
        )
        try:
            res = (prompt | llm.with_structured_output(_Route)).invoke({"q": message})
            route = (res.route or "").strip().lower()
            if route in ("action", "agent", "rag"):
                return route
        except Exception as exc:
            logger.debug("LLM classify failed (%s); using keyword fallback.", exc)
    return "action" if _ACTION_RE.search(message or "") else "rag"


class Supervisor:
    def __init__(self, qa_agent=None, action_agent=None, finance_agent=None):
        self.qa_agent = qa_agent or _chat_agent
        self.action_agent = action_agent or _action_agent
        self.finance_agent = finance_agent or _finance_agent

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
        elif route == "agent":
            resp = self.finance_agent.run(message, conversation_id, tools)
        else:
            resp = self.qa_agent.run(message, conversation_id, tools, llm=llm, retriever=retriever)
        resp.routed_to = route
        return resp


supervisor = Supervisor()
