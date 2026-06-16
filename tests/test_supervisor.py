"""Tests for the multi-agent supervisor (routing + handoff)."""
import os

os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from app.schemas.chat import ChatResponse
from app.services.supervisor import Supervisor, classify


class StubAgent:
    """Records calls and returns a canned response."""

    def __init__(self, name):
        self.name = name
        self.calls = []

    def run(self, message, conversation_id, tools, llm=None, retriever=None):
        self.calls.append(message)
        return ChatResponse(answer=f"{self.name} handled it", sources=[],
                            conversation_id=conversation_id or "x")


# --------------------------------------------------------------------------- #
# Classifier (keyword fallback, deterministic with no/!structured llm)         #
# --------------------------------------------------------------------------- #

def test_classify_action_keywords():
    assert classify("Delete expense 5", None) == "action"
    assert classify("Recategorize my Netflix charge to Subscription", None) == "action"
    assert classify("change expense 3 to Dining", None) == "action"


def test_classify_qa_default():
    assert classify("How much did I spend on groceries in January?", None) == "qa"
    assert classify("What's my forecast for next month?", None) == "qa"


# --------------------------------------------------------------------------- #
# Handoff                                                                      #
# --------------------------------------------------------------------------- #

def test_supervisor_routes_qa_to_chat_agent(seeded_tools):
    qa, action = StubAgent("qa"), StubAgent("action")
    sup = Supervisor(qa_agent=qa, action_agent=action)
    resp = sup.run("How much on groceries in Jan?", "s-1", seeded_tools, llm=None)
    assert resp.routed_to == "qa"
    assert qa.calls and not action.calls
    assert "qa handled" in resp.answer


def test_supervisor_routes_action_to_action_agent(seeded_tools):
    qa, action = StubAgent("qa"), StubAgent("action")
    sup = Supervisor(qa_agent=qa, action_agent=action)
    resp = sup.run("Delete expense 2", "s-2", seeded_tools, llm=None)
    assert resp.routed_to == "action"
    assert action.calls and not qa.calls


def test_supervisor_endpoint_routes(client, db, monkeypatch):
    from tests.conftest import seed_categorized
    seed_categorized(db)
    qa, action = StubAgent("qa"), StubAgent("action")
    monkeypatch.setattr("app.routers.chat.supervisor", Supervisor(qa_agent=qa, action_agent=action))
    monkeypatch.setattr("app.services.supervisor._safe_chat_model", lambda streaming=False: None)

    r = client.post("/chat/supervisor", json={"message": "How much on dining in Feb 2024?",
                                              "conversation_id": "s-http"})
    body = r.json()
    assert body["routed_to"] == "qa"
    assert "qa handled" in body["answer"]
