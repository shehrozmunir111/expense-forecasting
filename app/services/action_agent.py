"""Human-in-the-Loop (HITL) action agent.

A tool-calling agent whose tools *mutate* data (recategorize / delete an
expense). Each write tool calls LangGraph's ``interrupt()`` BEFORE doing anything,
so the graph pauses and the API returns the proposed action for human approval.
On ``/chat/approve`` the graph resumes via ``Command(resume=...)`` and either
performs the write (fresh DB session) or cancels.

Because a resumed node re-runs from the top, ``interrupt()`` is the first thing
each tool does — no side effect happens before approval. The request-scoped repo
is passed via a ContextVar so the write executes against the *approving*
request's session, not the (closed) original one.
"""
import contextvars
import logging
import uuid
import warnings
from typing import List, Optional

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool

warnings.filterwarnings("ignore", message=".*create_react_agent has been moved.*")
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt

from app.models.expense import EXPENSE_CATEGORIES, CategorizationStatus
from app.schemas.chat import ChatResponse, Source
from app.services.chat_agent import _build_checkpointer, _safe_chat_model
from app.services.finance_tools import FinanceTools

logger = logging.getLogger(__name__)

# Carries the current request's repository into the (module-level) tools.
_current_repo: contextvars.ContextVar = contextvars.ContextVar("action_repo", default=None)

_SYSTEM = (
    "You are a finance assistant that can MODIFY the user's data. For any request "
    "to recategorize or delete an expense, call the matching tool with the correct "
    "expense id. Every write requires explicit human approval (handled by the "
    "system). Do not claim a change was made unless a tool confirms it."
)


def build_action_tools() -> List[StructuredTool]:
    def update_expense_category(expense_id: int, category: str) -> str:
        """Change an expense's category (requires human approval). category must be a
        valid expense category."""
        if category not in EXPENSE_CATEGORIES:
            return f"Invalid category '{category}'. Valid: {', '.join(EXPENSE_CATEGORIES)}."
        decision = interrupt({
            "action": "update_category", "expense_id": expense_id, "category": category,
            "summary": f"Recategorize expense #{expense_id} to '{category}'",
        }) or {}
        if not decision.get("approved"):
            return f"Cancelled by user: expense {expense_id} was not changed."
        repo = _current_repo.get()
        if repo is None:
            return "No database session available."
        updated = repo.update_expense(expense_id, {
            "category": category,
            "categorization_status": CategorizationStatus.MANUAL,
            "category_confidence": 1.0,
        })
        if not updated:
            return f"Expense {expense_id} not found."
        return f"Updated expense {expense_id} to category {category}."

    def delete_expense(expense_id: int) -> str:
        """Permanently delete an expense (requires human approval)."""
        decision = interrupt({
            "action": "delete", "expense_id": expense_id,
            "summary": f"Delete expense #{expense_id}",
        }) or {}
        if not decision.get("approved"):
            return f"Cancelled by user: expense {expense_id} was not deleted."
        repo = _current_repo.get()
        if repo is None:
            return "No database session available."
        ok = repo.delete_expense(expense_id)
        return f"Deleted expense {expense_id}." if ok else f"Expense {expense_id} not found."

    return [
        StructuredTool.from_function(func=update_expense_category, name="update_expense_category"),
        StructuredTool.from_function(func=delete_expense, name="delete_expense"),
    ]


def _final_answer(messages) -> str:
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


def _tool_sources(messages) -> List[Source]:
    return [Source(kind="tool", label=m.name or "tool", detail=str(m.content))
            for m in messages if isinstance(m, ToolMessage)]


class ActionAgent:
    def __init__(self, checkpointer=None):
        self._checkpointer = checkpointer if checkpointer is not None else _build_checkpointer()

    def _config(self, cid: str) -> dict:
        return {"configurable": {"thread_id": cid}}

    def _graph(self, llm):
        return create_react_agent(llm, build_action_tools(), prompt=_SYSTEM,
                                  checkpointer=self._checkpointer)

    def run(self, message: str, conversation_id: Optional[str], tools: FinanceTools, llm=None) -> ChatResponse:
        cid = conversation_id or uuid.uuid4().hex
        llm = llm if llm is not None else _safe_chat_model()
        if llm is None:
            return ChatResponse(answer="The assistant is unavailable; no changes were made.",
                                sources=[], conversation_id=cid, status="completed", grounded=False)
        graph = self._graph(llm)
        token = _current_repo.set(tools.repo)
        try:
            result = graph.invoke({"messages": [HumanMessage(content=message)]}, self._config(cid))
        finally:
            _current_repo.reset(token)

        interrupts = result.get("__interrupt__")
        if interrupts:
            pending = interrupts[0].value
            return ChatResponse(
                answer=f"Approval required: {pending.get('summary', 'confirm this action')}. "
                       f"Call /chat/approve with approved=true to proceed.",
                sources=[], conversation_id=cid, status="pending_approval",
                pending=pending, grounded=True,
            )
        msgs = result["messages"]
        return ChatResponse(answer=_final_answer(msgs) or "Done.", sources=_tool_sources(msgs),
                            conversation_id=cid, status="completed", grounded=True)

    def approve(self, conversation_id: str, approved: bool, tools: FinanceTools, llm=None) -> ChatResponse:
        cid = conversation_id
        llm = llm if llm is not None else _safe_chat_model()
        if llm is None:
            return ChatResponse(answer="The assistant is unavailable; no changes were made.",
                                sources=[], conversation_id=cid, status="completed", grounded=False)
        graph = self._graph(llm)
        token = _current_repo.set(tools.repo)
        try:
            result = graph.invoke(Command(resume={"approved": approved}), self._config(cid))
        finally:
            _current_repo.reset(token)
        msgs = result["messages"]
        return ChatResponse(answer=_final_answer(msgs) or ("Approved." if approved else "Rejected."),
                            sources=_tool_sources(msgs), conversation_id=cid,
                            status="completed", grounded=True)


# Module-level singleton sharing one memory store for the app's lifetime.
action_agent = ActionAgent()
