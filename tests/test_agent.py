"""Tests for the tool-calling (ReAct) finance agent.

Offline: a FakeToolCallingModel drives the tool loop deterministically (emit a
tool call, then answer from the tool result). Covers toolset correctness,
end-to-end tool selection + grounded answer, multi-turn memory, and the
LLM-down fallback.
"""
import os

os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from typing import List, Optional

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from langgraph.checkpoint.memory import MemorySaver

from app.services.finance_agent import (
    FinanceReactAgent,
    build_finance_toolset,
    _sources_from_messages,
)


class FakeToolCallingModel(BaseChatModel):
    """Calls `tool_name` once, then answers using the returned ToolMessage."""

    tool_name: str = "get_biggest_category"
    tool_args: dict = {}

    @property
    def _llm_type(self) -> str:
        return "fake-tool-calling"

    def bind_tools(self, tools, **kwargs):  # create_react_agent calls this
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        tool_results = [m.content for m in messages if isinstance(m, ToolMessage)]
        if tool_results:
            msg = AIMessage(content=f"Based on the data: {tool_results[-1]}")
        else:
            msg = AIMessage(
                content="",
                tool_calls=[{"name": self.tool_name, "args": self.tool_args, "id": "call_1"}],
            )
        return ChatResult(generations=[ChatGeneration(message=msg)])


@pytest.fixture
def agent():
    return FinanceReactAgent(checkpointer=MemorySaver())


# --------------------------------------------------------------------------- #
# Toolset (deterministic, no LLM)                                              #
# --------------------------------------------------------------------------- #

def test_toolset_returns_correct_numbers(seeded_tools):
    by_name = {t.name: t for t in build_finance_toolset(seeded_tools)}
    assert set(by_name) >= {
        "get_category_summary", "get_category_total", "get_biggest_category",
        "get_forecast", "get_monthly_summary", "list_months", "list_recent_transactions",
    }
    # Jan groceries == 800 (from services)
    out = by_name["get_category_total"].invoke({"category": "Groceries", "month": "2024-01"})
    assert "800.00" in out
    # Biggest category == Car/Fuel 3600
    biggest = by_name["get_biggest_category"].invoke({})
    assert "Car/Fuel" in biggest and "3600.00" in biggest


def test_sources_from_messages_extracts_tool_calls():
    msgs = [
        HumanMessage(content="q"),
        ToolMessage(content="Car/Fuel: 3600.00 UAH", name="get_biggest_category", tool_call_id="x"),
        AIMessage(content="answer"),
    ]
    sources = _sources_from_messages(msgs)
    assert len(sources) == 1
    assert sources[0].kind == "tool"
    assert sources[0].label == "get_biggest_category"


# --------------------------------------------------------------------------- #
# End-to-end tool loop (fake model)                                            #
# --------------------------------------------------------------------------- #

def test_agent_calls_tool_and_grounds_answer(agent, seeded_tools):
    resp = agent.run(
        "What's my biggest category?",
        "ra-test",
        seeded_tools,
        llm=FakeToolCallingModel(tool_name="get_biggest_category"),
    )
    assert resp.grounded is True
    assert "Car/Fuel" in resp.answer and "3600.00" in resp.answer
    assert [s.label for s in resp.sources] == ["get_biggest_category"]


def test_agent_multi_turn_memory(agent, seeded_tools):
    cid = "ra-mem"
    llm = FakeToolCallingModel(tool_name="get_biggest_category")
    agent.run("biggest category?", cid, seeded_tools, llm=llm)
    agent.run("and again?", cid, seeded_tools, llm=llm)
    saved = agent._checkpointer.get({"configurable": {"thread_id": cid}})
    # Two turns -> two human messages persisted (plus AI/tool messages).
    humans = [m for m in saved["channel_values"]["messages"] if isinstance(m, HumanMessage)]
    assert len(humans) == 2


# --------------------------------------------------------------------------- #
# Fallback (LLM unavailable)                                                   #
# --------------------------------------------------------------------------- #

def test_agent_fallback_when_no_llm(agent, seeded_tools, monkeypatch):
    monkeypatch.setattr("app.services.finance_agent._safe_chat_model",
                        lambda streaming=False: None)
    resp = agent.run("biggest category?", "ra-fb", seeded_tools)  # llm defaults -> None
    assert resp.grounded is False
    assert "UAH" in resp.answer
    assert resp.sources  # top categories surfaced from services


def test_agent_endpoint_offline(client, db, monkeypatch):
    from tests.conftest import seed_categorized
    seed_categorized(db)
    monkeypatch.setattr(
        "app.routers.chat.finance_react_agent",
        FinanceReactAgent(checkpointer=MemorySaver()),
    )
    monkeypatch.setattr(
        "app.services.finance_agent._safe_chat_model",
        lambda streaming=False: FakeToolCallingModel(tool_name="get_biggest_category"),
    )
    r = client.post("/chat/agent", json={"message": "biggest category?", "conversation_id": "rae-1"})
    assert r.status_code == 200
    body = r.json()
    assert "Car/Fuel" in body["answer"]
    assert body["grounded"] is True
