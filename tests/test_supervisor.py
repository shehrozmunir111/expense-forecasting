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
    assert classify("How much did I spend on groceries in January?", None) == "rag"
    assert classify("What's my forecast for next month?", None) == "rag"

def test_classify_agent():
    assert classify("Which category did I spend the most on?", None) == "rag"

def test_classify_agent_keyword_fallback():
    assert classify("Compare this month to last month", None) == "rag"


# --------------------------------------------------------------------------- #
# Handoff                                                                      #
# --------------------------------------------------------------------------- #

def test_supervisor_routes_rag_to_chat_agent(seeded_tools):
    qa, action, agent = StubAgent("rag"), StubAgent("action"), StubAgent("agent")
    sup = Supervisor(qa_agent=qa, action_agent=action, finance_agent=agent)
    resp = sup.run("How much on groceries in Jan?", "s-1", seeded_tools, llm=None)
    assert resp.routed_to == "rag"
    assert qa.calls and not action.calls and not agent.calls


def test_supervisor_routes_action_to_action_agent(seeded_tools):
    qa, action, agent = StubAgent("rag"), StubAgent("action"), StubAgent("agent")
    sup = Supervisor(qa_agent=qa, action_agent=action, finance_agent=agent)
    resp = sup.run("Delete expense 2", "s-2", seeded_tools, llm=None)
    assert resp.routed_to == "action"
    assert action.calls and not qa.calls and not agent.calls


def test_supervisor_routes_agent_to_finance_agent(seeded_tools):
    qa, action, agent = StubAgent("rag"), StubAgent("action"), StubAgent("agent")
    sup = Supervisor(qa_agent=qa, action_agent=action, finance_agent=agent)
    resp = sup.run("Which category did I spend the most on?", "s-3", seeded_tools, llm=None)
    assert resp.routed_to == "agent"
    assert agent.calls and not qa.calls and not action.calls


def test_supervisor_endpoint_routes(client, db, monkeypatch):
    from tests.conftest import seed_categorized
    seed_categorized(db)
    qa, action, agent = StubAgent("rag"), StubAgent("action"), StubAgent("agent")
    monkeypatch.setattr("app.routers.chat.supervisor",
                        Supervisor(qa_agent=qa, action_agent=action, finance_agent=agent))
    monkeypatch.setattr("app.services.supervisor._safe_chat_model", lambda streaming=False: None)

    r = client.post("/chat/supervisor", json={"message": "How much on dining in Feb 2024?",
                                              "conversation_id": "s-http"})
    body = r.json()
    assert body["routed_to"] == "rag"
    assert "rag handled" in body["answer"]
