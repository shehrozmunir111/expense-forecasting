from pydantic import BaseModel, Field
from typing import List, Optional


class ChatRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=2000,
        description="Plain-language question about your finances",
    )
    conversation_id: Optional[str] = Field(
        None, max_length=100,
        description="Thread id for multi-turn memory. Auto-generated when omitted; "
                    "reuse it to keep follow-ups in context.",
    )
    stream: bool = Field(
        default=False,
        description="Stream the answer token-by-token (text/event-stream).",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "is mahine groceries pe kitna gaya?",
                "conversation_id": "user-42",
            }
        }
    }


class Source(BaseModel):
    """A grounded fact pulled from deterministic services and shown to the LLM."""
    kind: str = Field(..., description="category_summary | monthly_summary | forecast | transaction")
    label: str = Field(..., description="Short human-readable label")
    detail: str = Field(..., description="The exact fact text the answer was grounded in")


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    conversation_id: str
    rewritten: bool = Field(False, description="True if adaptive-RAG rewrote the query and retried")
    grounded: bool = Field(True, description="False when the LLM was unavailable and a templated fallback was used")
