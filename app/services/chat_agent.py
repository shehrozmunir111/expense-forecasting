"""Conversational "Chat with your finances" agent.

A LangGraph implementation of Adaptive RAG over the user's own data:

    retrieve -> grade -> (rewrite -> retrieve)* -> answer

Key properties:
- Numbers are never computed by the LLM. Retrieval surfaces grounded fact cards
  built from deterministic services; the answer chain only phrases them.
- Memory is provided by a LangGraph checkpointer keyed by ``conversation_id``
  (MemorySaver for dev/SQLite, PostgresSaver for the PostgreSQL profile), so
  follow-up questions keep context.
- Graceful fallback: if the LLM/LM Studio is unreachable, the grader defaults to
  "useful" and the answer falls back to a templated summary of the facts.
"""
import logging
import uuid
import warnings
from typing import Annotated, List, Optional

from langchain_core.messages import AIMessage, AIMessageChunk, AnyMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.config import settings
from app.schemas.chat import ChatResponse, Source
from app.services.finance_retriever import FinanceRetriever
from app.services.finance_tools import FinanceTools
from app.services.llm_provider import get_chat_model

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Prompts                                                                      #
# --------------------------------------------------------------------------- #

_GRADE_SYSTEM = (
    "You grade whether retrieved facts are relevant and sufficient to answer a "
    "user's question about their personal finances. Respond strictly."
)
_GRADE_HUMAN = (
    "User question:\n{question}\n\nRetrieved facts:\n{context}\n\n"
    "Are these facts relevant and sufficient to answer the question?"
)

_REWRITE_SYSTEM = (
    "You rewrite a user's latest finance question into a single standalone search "
    "query. Resolve pronouns/follow-ups using the conversation, and name the "
    "relevant spending category and month (YYYY-MM) explicitly when implied. "
    "Return ONLY the rewritten query, nothing else."
)

_ANSWER_SYSTEM = (
    "You are a personal-finance assistant. Answer the user's question using ONLY "
    "the facts provided.\n"
    "- The facts already contain exact amounts computed from the user's own data. "
    "Use those numbers verbatim; never invent or recalculate figures.\n"
    "- Currency is UAH unless a fact says otherwise.\n"
    "- Be concise: 1-3 sentences.\n"
    "- If the facts do not contain the answer, say you don't have that data yet."
)


class _GradeDecision(BaseModel):
    """Structured grader output."""
    relevant: bool = Field(description="True if the facts are relevant AND sufficient to answer.")


# --------------------------------------------------------------------------- #
# Graph state                                                                  #
# --------------------------------------------------------------------------- #

class ChatState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    original_question: str   # the user's question, answered verbatim
    question: str            # retrieval query (may be rewritten)
    documents: List[dict]    # serializable fact cards: {kind,label,detail}
    grade: str               # "useful" | "weak"
    rewrites: int
    rewritten: bool
    grounded: bool
    answer: str


def _doc_to_source(d) -> dict:
    md = d.metadata or {}
    return {
        "kind": md.get("kind", "fact"),
        "label": md.get("label", md.get("kind", "fact")),
        "detail": d.page_content,
    }


def _format_context(documents: List[dict]) -> str:
    if not documents:
        return "(no matching data found)"
    return "\n".join(f"{i+1}. {d['detail']}" for i, d in enumerate(documents))


def _recent_history(messages: List[AnyMessage], keep: int = 6) -> List[AnyMessage]:
    # Drop the latest human turn (it is passed explicitly) and keep prior context.
    prior = messages[:-1] if messages else []
    return prior[-keep:]


class ChatAgent:
    """Holds the shared checkpointer (memory) and builds a graph per request."""

    def __init__(self, checkpointer=None):
        self._checkpointer = checkpointer if checkpointer is not None else _build_checkpointer()

    # -- public API ----------------------------------------------------- #

    def run(
        self,
        message: str,
        conversation_id: Optional[str],
        tools: FinanceTools,
        llm=None,
        retriever: Optional[FinanceRetriever] = None,
        embeddings=None,
    ) -> ChatResponse:
        cid = conversation_id or uuid.uuid4().hex
        llm = llm if llm is not None else _safe_chat_model()
        retriever = retriever or FinanceRetriever(tools, embeddings=embeddings)
        graph = self._build_graph(retriever, llm)
        try:
            state = graph.invoke(self._initial_state(message), self._config(cid))
        finally:
            retriever.close()

        return ChatResponse(
            answer=state["answer"],
            sources=[Source(**s) for s in state.get("documents", [])],
            conversation_id=cid,
            rewritten=state.get("rewritten", False),
            grounded=state.get("grounded", True),
        )

    def stream(
        self,
        message: str,
        conversation_id: Optional[str],
        tools: FinanceTools,
        llm=None,
        retriever: Optional[FinanceRetriever] = None,
        embeddings=None,
    ):
        """Yield answer tokens as they are generated (memory still persists).

        Falls back to yielding the whole answer at once if token streaming fails.
        """
        cid = conversation_id or uuid.uuid4().hex
        llm = llm if llm is not None else _safe_chat_model(streaming=True)
        retriever = retriever or FinanceRetriever(tools, embeddings=embeddings)
        graph = self._build_graph(retriever, llm)
        streamed_any = False
        try:
            with warnings.catch_warnings():
                # The structured grader emits a benign pydantic serialize warning
                # when captured by stream_mode="messages"; suppress just here.
                warnings.simplefilter("ignore")
                for chunk, meta in graph.stream(
                    self._initial_state(message), self._config(cid), stream_mode="messages"
                ):
                    # Yield only incremental answer tokens (AIMessageChunk), not the
                    # full AIMessage the node writes to the messages channel.
                    if (
                        meta.get("langgraph_node") == "answer"
                        and isinstance(chunk, AIMessageChunk)
                        and chunk.content
                    ):
                        streamed_any = True
                        yield chunk.content
        except Exception as exc:  # pragma: no cover - degrade to non-streaming
            logger.warning("Token streaming failed (%s); returning full answer.", exc)
        finally:
            retriever.close()

        if not streamed_any:
            # Fallback: produce the answer non-streamed and emit once.
            resp = self.run(message, cid, tools, llm=_safe_chat_model(), retriever=None,
                            embeddings=embeddings)
            yield resp.answer

    # -- internals ------------------------------------------------------ #

    @staticmethod
    def _config(cid: str) -> dict:
        return {"configurable": {"thread_id": cid}}

    @staticmethod
    def _initial_state(message: str) -> dict:
        # Per-turn fields are reset here; `messages` is appended via the reducer.
        return {
            "messages": [HumanMessage(content=message)],
            "original_question": message,
            "question": message,
            "documents": [],
            "grade": "",
            "rewrites": 0,
            "rewritten": False,
            "grounded": True,
            "answer": "",
        }

    def _build_graph(self, retriever: FinanceRetriever, llm):
        graph = StateGraph(ChatState)
        graph.add_node("retrieve", self._make_retrieve(retriever))
        graph.add_node("grade", self._make_grade(llm))
        graph.add_node("rewrite", self._make_rewrite(llm))
        graph.add_node("answer", self._make_answer(llm))

        graph.add_edge(START, "retrieve")
        graph.add_edge("retrieve", "grade")
        graph.add_conditional_edges(
            "grade", self._decide, {"answer": "answer", "rewrite": "rewrite"}
        )
        graph.add_edge("rewrite", "retrieve")
        graph.add_edge("answer", END)
        return graph.compile(checkpointer=self._checkpointer)

    @staticmethod
    def _decide(state: ChatState) -> str:
        if state["grade"] == "useful":
            return "answer"
        if state["rewrites"] >= settings.CHAT_MAX_REWRITES:
            return "answer"
        return "rewrite"

    # -- nodes (closures capture per-request deps) ---------------------- #

    @staticmethod
    def _make_retrieve(retriever: FinanceRetriever):
        def retrieve(state: ChatState) -> dict:
            docs = retriever.retrieve(state["question"])
            return {"documents": [_doc_to_source(d) for d in docs]}
        return retrieve

    @staticmethod
    def _make_grade(llm):
        def grade(state: ChatState) -> dict:
            docs = state["documents"]
            if not docs:
                return {"grade": "weak"}
            if llm is None:
                return {"grade": "useful"}
            ctx = _format_context(docs)
            prompt = ChatPromptTemplate.from_messages(
                [("system", _GRADE_SYSTEM), ("human", _GRADE_HUMAN)]
            )
            # Showcase structured output; degrade to text parsing for models
            # that can't do tool/function calling.
            try:
                chain = prompt | llm.with_structured_output(_GradeDecision)
                decision = chain.invoke({"question": state["original_question"], "context": ctx})
                return {"grade": "useful" if decision.relevant else "weak"}
            except Exception as exc:
                logger.debug("structured grade failed (%s); falling back to text.", exc)
            try:
                text_prompt = ChatPromptTemplate.from_messages(
                    [("system", _GRADE_SYSTEM + " Reply with exactly USEFUL or WEAK."),
                     ("human", _GRADE_HUMAN)]
                )
                chain = text_prompt | llm | StrOutputParser()
                verdict = chain.invoke({"question": state["original_question"], "context": ctx}).lower()
                return {"grade": "weak" if "weak" in verdict else "useful"}
            except Exception as exc:
                logger.warning("grade LLM unavailable (%s); proceeding to answer.", exc)
                return {"grade": "useful"}
        return grade

    @staticmethod
    def _make_rewrite(llm):
        def rewrite(state: ChatState) -> dict:
            n = state["rewrites"] + 1
            if llm is None:
                return {"rewrites": n, "rewritten": True}
            prompt = ChatPromptTemplate.from_messages(
                [("system", _REWRITE_SYSTEM),
                 MessagesPlaceholder("history"),
                 ("human", "Latest question: {question}")]
            )
            try:
                chain = prompt | llm | StrOutputParser()
                new_q = chain.invoke(
                    {"history": _recent_history(state["messages"]),
                     "question": state["original_question"]}
                ).strip()
                if new_q:
                    return {"question": new_q, "rewrites": n, "rewritten": True}
            except Exception as exc:
                logger.warning("rewrite LLM unavailable (%s); reusing question.", exc)
            return {"rewrites": n, "rewritten": True}
        return rewrite

    @staticmethod
    def _make_answer(llm):
        def answer(state: ChatState) -> dict:
            docs = state["documents"]
            ctx = _format_context(docs)
            if llm is not None:
                prompt = ChatPromptTemplate.from_messages(
                    [("system", _ANSWER_SYSTEM),
                     MessagesPlaceholder("history"),
                     ("human", "Question: {question}\n\nFacts:\n{context}")]
                )
                try:
                    chain = prompt | llm | StrOutputParser()
                    text = chain.invoke(
                        {"history": _recent_history(state["messages"]),
                         "question": state["original_question"],
                         "context": ctx}
                    ).strip()
                    if text:
                        return {"answer": text, "grounded": True,
                                "messages": [AIMessage(content=text)]}
                except Exception as exc:
                    logger.warning("answer LLM unavailable (%s); using templated fallback.", exc)
            text = _fallback_answer(docs)
            return {"answer": text, "grounded": False, "messages": [AIMessage(content=text)]}
        return answer


def _fallback_answer(documents: List[dict]) -> str:
    if not documents:
        return "I don't have any expense data yet to answer that. Upload and categorize some expenses first."
    bullets = "\n".join(f"- {d['detail']}" for d in documents[:3])
    return "I couldn't reach the language model, but here's what your data shows:\n" + bullets


def _safe_chat_model(streaming: bool = False):
    try:
        return get_chat_model(streaming=streaming)
    except Exception as exc:
        logger.warning("Chat model could not be constructed (%s); fallback mode.", exc)
        return None


def _build_checkpointer():
    """MemorySaver by default; PostgresSaver on the PostgreSQL profile."""
    url = settings.DATABASE_URL or ""
    if url.startswith("postgresql"):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            conn = url.replace("postgresql+psycopg", "postgresql")
            cm = PostgresSaver.from_conn_string(conn)
            saver = cm.__enter__()  # held for the app's lifetime
            saver.setup()
            logger.info("Chat memory: PostgresSaver")
            return saver
        except Exception as exc:
            logger.warning("PostgresSaver unavailable (%s); using in-memory chat memory.", exc)
    from langgraph.checkpoint.memory import MemorySaver

    logger.info("Chat memory: MemorySaver (in-process)")
    return MemorySaver()


# Module-level singleton: one shared memory store for the app's lifetime.
chat_agent = ChatAgent()
