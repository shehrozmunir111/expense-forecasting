"""Tests for the Human-in-the-Loop action agent (interrupt -> approve/reject)."""
import os

os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from langgraph.checkpoint.memory import MemorySaver

from app.models.expense import Expense
from app.services.action_agent import ActionAgent


class FakeWriteModel(BaseChatModel):
    """Calls a write tool once, then answers from the tool result."""

    tool_name: str = "update_expense_category"
    tool_args: dict = {"expense_id": 1, "category": "Subscription"}

    @property
    def _llm_type(self) -> str:
        return "fake-write"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        if any(isinstance(m, ToolMessage) for m in messages):
            last = [m.content for m in messages if isinstance(m, ToolMessage)][-1]
            msg = AIMessage(content=f"Done: {last}")
        else:
            msg = AIMessage(content="", tool_calls=[
                {"name": self.tool_name, "args": self.tool_args, "id": "call_1"}])
        return ChatResult(generations=[ChatGeneration(message=msg)])


@pytest.fixture
def agent():
    return ActionAgent(checkpointer=MemorySaver())


def test_run_pauses_for_approval(agent, seeded_tools):
    resp = agent.run("Recategorize expense 1 to Subscription", "h-1", seeded_tools,
                     llm=FakeWriteModel())
    assert resp.status == "pending_approval"
    assert resp.pending["action"] == "update_category"
    assert resp.pending["expense_id"] == 1
    # Nothing changed yet.
    assert seeded_tools.repo.get_by_id(1).category != "Subscription"


def test_approve_executes_write(agent, seeded_tools):
    agent.run("Recategorize expense 1 to Subscription", "h-2", seeded_tools, llm=FakeWriteModel())
    resp = agent.approve("h-2", True, seeded_tools, llm=FakeWriteModel())
    assert resp.status == "completed"
    expense = seeded_tools.repo.get_by_id(1)
    assert expense.category == "Subscription"
    assert expense.categorization_status == "manual"


def test_reject_cancels_write(agent, seeded_tools):
    before = seeded_tools.repo.get_by_id(1).category
    agent.run("Recategorize expense 1 to Subscription", "h-3", seeded_tools, llm=FakeWriteModel())
    resp = agent.approve("h-3", False, seeded_tools, llm=FakeWriteModel())
    assert resp.status == "completed"
    assert seeded_tools.repo.get_by_id(1).category == before  # unchanged


def test_invalid_category_is_rejected_before_approval(agent, seeded_tools):
    resp = agent.run("Recategorize expense 1 to Bogus", "h-4", seeded_tools,
                     llm=FakeWriteModel(tool_args={"expense_id": 1, "category": "Bogus"}))
    # Invalid category short-circuits before any interrupt -> completes immediately.
    assert resp.status == "completed"
    assert "Invalid category" in resp.sources[0].detail


def test_delete_requires_approval_then_deletes(agent, seeded_tools):
    agent.run("Delete expense 2", "h-5", seeded_tools,
              llm=FakeWriteModel(tool_name="delete_expense", tool_args={"expense_id": 2}))
    assert seeded_tools.repo.get_by_id(2) is not None  # still there pre-approval
    agent.approve("h-5", True, seeded_tools,
                  llm=FakeWriteModel(tool_name="delete_expense", tool_args={"expense_id": 2}))
    assert seeded_tools.repo.get_by_id(2) is None


def test_hitl_endpoints(client, db, monkeypatch):
    from tests.conftest import seed_categorized
    seed_categorized(db)  # first inserted expense -> id 1
    monkeypatch.setattr("app.routers.chat.action_agent", ActionAgent(checkpointer=MemorySaver()))
    monkeypatch.setattr("app.services.action_agent._safe_chat_model",
                        lambda streaming=False: FakeWriteModel())

    r1 = client.post("/chat/action", json={"message": "Recategorize expense 1 to Subscription",
                                           "conversation_id": "h-http"})
    assert r1.json()["status"] == "pending_approval"

    r2 = client.post("/chat/approve", json={"conversation_id": "h-http", "approved": True})
    assert r2.json()["status"] == "completed"
    assert db.query(Expense).filter(Expense.id == 1).first().category == "Subscription"
