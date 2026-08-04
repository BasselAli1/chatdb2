"""
API routes for the Chat-with-Database app.

This file currently exposes a single endpoint: POST /chat
It is intentionally thin — request/response models live here, but the
actual RAG + text-to-SQL logic is delegated to a service layer
(app.services.chat_service) that we will build in a later file.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# NOTE: chat_service does not exist yet — this import is a forward
# reference for the next file we build. Routes stay decoupled from
# implementation details (LLM calls, RAG retrieval, SQL execution).
from app.services.chat_service import DatabaseUnavailableError, handle_chat_message

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""

    session_id: str = Field(
        ...,
        description="Client-generated ID used to track conversation history "
        "for this session. Reuse the same ID across messages in one chat.",
        min_length=1,
    )
    message: str = Field(
        ...,
        description="The user's natural language question about the database.",
        min_length=1,
    )


class ChatResponse(BaseModel):
    """Response returned after processing a chat message."""

    session_id: str
    answer: str = Field(..., description="Natural language answer to the user's question.")
    sql: str | None = Field(
        default=None,
        description="The SQL query that was generated and executed, if any. "
        "Shown to the user for transparency.",
    )


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Handle a single chat turn.

    Looks up (or starts) the conversation history for `session_id`,
    passes the new message + history to the chat service, and returns
    the generated answer along with the SQL that produced it.
    """
    try:
        result = await handle_chat_message(
            session_id=request.session_id,
            message=request.message,
        )
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        session_id=request.session_id,
        answer=result["answer"],
        sql=result.get("sql"),
    )