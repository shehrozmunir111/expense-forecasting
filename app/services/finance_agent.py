import logging
import uuid
import warnings
from typing import List, Optional

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool

# create_react_agent: prebuilt ReAct loop, still supported in langgraph 1.x; silence the move notice.
warnings.filterwarnings("ignore", message=".*create_react_agent has been moved.*")
from langgraph.prebuilt import create_react_agent

from app.schemas.chat import ChatResponse, Source
from app.services.chat_agent import _build_checkpointer, _safe_chat_model
from app.services.finance_tools import FinanceTools

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a personal-finance assistant. The user asks about their own spending.\n"
    "ALWAYS use the provided tools to obtain figures — never invent or estimate "
    "numbers yourself. Pick the most specific tool for the question, call it, then "
    "answer concisely (1-3 sentences) using the returned numbers verbatim. Currency "
    "is USD. Months are YYYY-MM. If a tool reports no data, say you don't have it yet."
    " Answer ONLY the specific time period the user asked about."
)


def build_finance_toolset(tools: FinanceTools) -> List[StructuredTool]:
    """Wrap deterministic services as LLM-callable tools (closures over `tools`)."""

    def get_category_summary(month: Optional[str] = None) -> str:
        """Totals per spending category. Optionally pass a month as 'YYYY-MM' to
        scope to that month; omit it for all-time totals."""
        rows = tools.category_summary(month=month)
        if not rows:
            return f"No categorized spending found{f' for {month}' if month else ''}."
        scope = month or "all time"
        parts = [f"{r['category']}: {r['total']:.2f} USD ({r['count']} tx)" for r in rows]
        return f"Spending by category ({scope}): " + "; ".join(parts)

    def get_monthly_summary(month: str) -> str:
        """Income, expenses, net and category breakdown for one month ('YYYY-MM')."""
        ms = tools.monthly_summary(month)
        top = "; ".join(f"{c['category']} {c['total']:.2f}" for c in ms["categories"][:5])
        return (
            f"{month}: expenses {ms['total_expenses']:.2f} USD, income "
            f"{ms['total_income']:.2f} USD, net {ms['net']:.2f} USD. Categories: "
            f"{top or 'none'}."
        )

    def get_category_total(category: str, month: Optional[str] = None) -> str:
        """Total spent on a single category (e.g. 'Groceries'), optionally for a
        given month 'YYYY-MM'."""
        row = tools.category_total(category, month=month)
        scope = month or "all time"
        if not row:
            return f"No spending on {category} for {scope}."
        return (f"{category} ({scope}): {row['total']:.2f} USD over {row['count']} "
                f"transactions.")

    def get_biggest_category() -> str:
        """The single category with the highest all-time spending."""
        rows = tools.category_summary()
        if not rows:
            return "No categorized spending found."
        top = max(rows, key=lambda r: r["total"])
        return f"Biggest category overall: {top['category']} at {top['total']:.2f} USD."

    def get_forecast() -> str:
        """Next-month per-category spending forecast (requires >= 2 months history)."""
        fc = tools.forecast()
        if not fc:
            return "Not enough history to forecast yet (need >= 2 months of data)."
        parts = [f"{cat} {d['predicted_amount']:.2f} ({d['trend']})"
                 for cat, d in fc["predictions"].items()]
        return f"Forecast for {fc['forecast_month']}: " + "; ".join(parts)

    def list_months() -> str:
        """List the YYYY-MM months that have expense data."""
        months = tools.distinct_months()
        return "Months with data: " + (", ".join(months) if months else "none")

    def list_recent_transactions(category: Optional[str] = None,
                                 month: Optional[str] = None, limit: int = 8) -> str:
        """Recent individual transactions, optionally filtered by category and/or
        month ('YYYY-MM')."""
        rows = tools.recent_transactions(limit=limit, category=category, month=month)
        if not rows:
            return "No matching transactions."
        return "; ".join(f"{r['date']} {r['raw_text']} {r['amount']:.2f} "
                         f"({r['category']})" for r in rows)

    specs = [
        (get_category_summary, "get_category_summary"),
        (get_monthly_summary, "get_monthly_summary"),
        (get_category_total, "get_category_total"),
        (get_biggest_category, "get_biggest_category"),
        (get_forecast, "get_forecast"),
        (list_months, "list_months"),
        (list_recent_transactions, "list_recent_transactions"),
    ]
    return [StructuredTool.from_function(func=f, name=n) for f, n in specs]


def _sources_from_messages(messages) -> List[Source]:
    """Turn each tool call/result into a Source for transparency/grounding."""
    sources: List[Source] = []
    for m in messages:
        if isinstance(m, ToolMessage):
            sources.append(Source(
                kind="tool",
                label=m.name or "tool",
                detail=str(m.content),
            ))
    return sources


class FinanceReactAgent:
    def __init__(self, checkpointer=None):
        self._checkpointer = checkpointer if checkpointer is not None else _build_checkpointer()

    def _config(self, cid: str) -> dict:
        return {"configurable": {"thread_id": cid}}

    def run(
        self,
        message: str,
        conversation_id: Optional[str],
        tools: FinanceTools,
        llm=None,
    ) -> ChatResponse:
        cid = conversation_id or uuid.uuid4().hex
        llm = llm if llm is not None else _safe_chat_model()
        if llm is None:
            return self._fallback(message, cid, tools)

        toolset = build_finance_toolset(tools)
        graph = create_react_agent(llm, toolset, prompt=_SYSTEM, checkpointer=self._checkpointer)
        try:
            result = graph.invoke({"messages": [HumanMessage(content=message)]}, self._config(cid))
        except Exception as exc:
            logger.warning("ReAct agent failed (%s); using deterministic fallback.", exc)
            return self._fallback(message, cid, tools)

        messages = result["messages"]
        answer = ""
        for m in reversed(messages):
            if isinstance(m, AIMessage) and m.content:
                answer = m.content if isinstance(m.content, str) else str(m.content)
                break
        sources = _sources_from_messages(messages)
        return ChatResponse(
            answer=answer or "I couldn't produce an answer.",
            sources=sources,
            conversation_id=cid,
            rewritten=False,
            grounded=bool(sources),  # grounded == the model actually called a tool
        )

    def stream(self, message: str, conversation_id: Optional[str], tools: FinanceTools, llm=None):
        cid = conversation_id or uuid.uuid4().hex
        llm = llm if llm is not None else _safe_chat_model(streaming=True)
        if llm is None:
            yield self._fallback(message, cid, tools).answer
            return
        toolset = build_finance_toolset(tools)
        graph = create_react_agent(llm, toolset, prompt=_SYSTEM, checkpointer=self._checkpointer)
        streamed = False
        try:
            for chunk, meta in graph.stream(
                {"messages": [HumanMessage(content=message)]}, self._config(cid),
                stream_mode="messages",
            ):
                # Final-answer tokens: AI chunks with text and no pending tool calls.
                if (getattr(chunk, "content", "") and not getattr(chunk, "tool_calls", None)
                        and chunk.__class__.__name__ == "AIMessageChunk"):
                    streamed = True
                    yield chunk.content
        except Exception as exc:  # pragma: no cover
            logger.warning("ReAct streaming failed (%s).", exc)
        if not streamed:
            yield self.run(message, cid, tools, llm=_safe_chat_model()).answer

    def _fallback(self, message: str, cid: str, tools: FinanceTools) -> ChatResponse:
        rows = tools.category_summary()
        if not rows:
            answer = "I don't have any expense data yet to answer that."
            sources = []
        else:
            top = sorted(rows, key=lambda r: -r["total"])[:3]
            answer = ("I couldn't reach the language model, but your top categories are: "
                      + "; ".join(f"{r['category']} {r['total']:.2f} USD" for r in top) + ".")
            sources = [Source(kind="category_summary", label=r["category"],
                              detail=f"{r['category']}: {r['total']:.2f} USD") for r in top]
        return ChatResponse(answer=answer, sources=sources, conversation_id=cid,
                            rewritten=False, grounded=False)


# Module-level singleton sharing one memory store for the app's lifetime.
finance_react_agent = FinanceReactAgent()
