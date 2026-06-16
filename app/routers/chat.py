import logging
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.expense_repo import ExpenseRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_agent import chat_agent
from app.services.finance_tools import FinanceTools

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


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
    return chat_agent.run(payload.message, payload.conversation_id, tools)


@router.post("/stream")
def chat_stream(payload: ChatRequest, db: Session = Depends(get_db)):
    """Streaming variant: answer tokens as `text/plain`.

    The resolved conversation id is returned in the `X-Conversation-Id` header.
    """
    tools = FinanceTools(ExpenseRepository(db))
    cid = payload.conversation_id or uuid.uuid4().hex
    generator = chat_agent.stream(payload.message, cid, tools)
    return StreamingResponse(
        generator,
        media_type="text/plain",
        headers={"X-Conversation-Id": cid},
    )
