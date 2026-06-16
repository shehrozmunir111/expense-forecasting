import logging
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.repositories.expense_repo import ExpenseRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_agent import chat_agent
from app.services.finance_agent import finance_react_agent
from app.services.finance_tools import FinanceTools
from app.services.rag_index import RagIndexRetriever, rag_index

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


def _build_retriever(tools: FinanceTools):
    """Persistent production RAG index by default; ephemeral when disabled."""
    if settings.RAG_PERSISTENT:
        return RagIndexRetriever(rag_index, tools)
    return None  # chat_agent builds an ephemeral FinanceRetriever


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Ask plain-language questions about your own finances.

    Uses Adaptive RAG (retrieve -> grade -> rewrite -> answer) over fact cards
    built from the deterministic summary/forecast services, so every number
    matches the REST endpoints. Pass a stable `conversation_id` to keep
    multi-turn context (the same id is returned for convenience).
    """
    tools = FinanceTools(ExpenseRepository(db))
    return chat_agent.run(payload.message, payload.conversation_id, tools,
                          retriever=_build_retriever(tools))


@router.post("/stream")
def chat_stream(payload: ChatRequest, db: Session = Depends(get_db)):
    """Streaming variant: answer tokens as `text/plain`.

    The resolved conversation id is returned in the `X-Conversation-Id` header.
    """
    tools = FinanceTools(ExpenseRepository(db))
    cid = payload.conversation_id or uuid.uuid4().hex
    generator = chat_agent.stream(payload.message, cid, tools,
                                  retriever=_build_retriever(tools))
    return StreamingResponse(
        generator,
        media_type="text/plain",
        headers={"X-Conversation-Id": cid},
    )


@router.post("/agent", response_model=ChatResponse)
def chat_agent_endpoint(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Tool-calling (ReAct) variant: the LLM decides which deterministic finance
    tool to call, then answers. Same memory model as `/chat`. Numbers always
    come from the tools (the existing services), never the model.
    """
    tools = FinanceTools(ExpenseRepository(db))
    return finance_react_agent.run(payload.message, payload.conversation_id, tools)


@router.post("/agent/stream")
def chat_agent_stream(payload: ChatRequest, db: Session = Depends(get_db)):
    """Streaming variant of the tool-calling agent (`text/plain`)."""
    tools = FinanceTools(ExpenseRepository(db))
    cid = payload.conversation_id or uuid.uuid4().hex
    generator = finance_react_agent.stream(payload.message, cid, tools)
    return StreamingResponse(
        generator,
        media_type="text/plain",
        headers={"X-Conversation-Id": cid},
    )


@router.post("/reindex")
def reindex(force: bool = True, db: Session = Depends(get_db)):
    """(Re)build the persistent RAG index from current data.

    Returns `{"status": "rebuilt"|"cached", "documents": N}`. With the default
    fingerprint caching, an unchanged dataset returns `cached` unless `force`.
    """
    if not settings.RAG_PERSISTENT:
        return {"status": "disabled", "detail": "RAG_PERSISTENT is false; index is ephemeral."}
    tools = FinanceTools(ExpenseRepository(db))
    return rag_index.ensure_fresh(tools, force=force)
