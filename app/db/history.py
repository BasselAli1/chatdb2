"""
Conversation history store for the Chat-with-Database app.

Backs session-based chat history with a Postgres table via async
SQLAlchemy. Two operations only:
    - load_history: fetch the last N turns for a session, oldest first
    - save_turn: persist a new turn (user message, generated SQL, answer)

For demo simplicity, this file also ensures the history table exists
on first use (create-if-missing) rather than relying on a separate
migrations setup.
"""

from datetime import datetime, timezone
from typing import TypedDict

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import settings

Base = declarative_base()

DEFAULT_HISTORY_WINDOW = 10


class ChatHistoryRow(Base):
    """A single stored turn: one user message + the resulting answer/SQL."""

    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    sql = Column(Text, nullable=True)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class HistoryTurn(TypedDict):
    user_message: str
    sql: str | None
    answer: str


_engine = create_async_engine(settings.ASYNC_DATABASE_URL, pool_pre_ping=True)
_tables_ready = False


async def _ensure_tables() -> None:
    """Create the chat_history table if it doesn't exist yet (demo-simple)."""
    global _tables_ready
    if _tables_ready:
        return
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _tables_ready = True


async def load_history(
    session_id: str, limit: int = DEFAULT_HISTORY_WINDOW
) -> list[HistoryTurn]:
    """
    Load the most recent turns for a session, oldest first.

    Args:
        session_id: The session to load history for.
        limit: Max number of turns to return (most recent `limit` turns).

    Returns:
        A list of HistoryTurn dicts, ordered oldest to newest, ready to
        feed into the SQL generator as conversational context.
    """
    await _ensure_tables()

    async with AsyncSession(_engine) as session:
        stmt = (
            select(ChatHistoryRow)
            .where(ChatHistoryRow.session_id == session_id)
            .order_by(ChatHistoryRow.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

    # rows come back newest-first (for the LIMIT to work correctly);
    # reverse so callers get chronological order.
    rows = list(reversed(rows))

    return [
        HistoryTurn(user_message=row.user_message, sql=row.sql, answer=row.answer)
        for row in rows
    ]


async def save_turn(
    session_id: str, user_message: str, sql: str | None, answer: str
) -> None:
    """
    Persist a new turn to the session's history.

    Args:
        session_id: The session this turn belongs to.
        user_message: The user's original question.
        sql: The SQL that was generated for this turn, if any.
        answer: The natural language answer returned to the user.
    """
    await _ensure_tables()
  
    row = ChatHistoryRow(
        session_id=session_id,
        user_message=user_message,
        sql=sql,
        answer=answer,
        created_at=datetime.now(timezone.utc),
    )

    async with AsyncSession(_engine) as session:
        session.add(row)
        await session.commit()
