"""
Chat service for the Chat-with-Database app.

Orchestrates a single chat turn:
    1. Load prior conversation history for the session (from Postgres).
    2. Retrieve relevant schema context for the question (RAG step).
    3. Generate a SQL query via the LLM (LangChain), using history + schema context.
    4. If SQL was generated, execute it against the demo database and
       generate a final answer grounded in the real results. If execution
       fails, fall back to a friendly error message instead of raising.
    5. Persist the new turn to history.
    6. Return the final answer + the SQL that was run (if any).
"""

import logging

from typing import TypedDict

from app.db.history import load_history, save_turn
from app.services.schema_retriever import retrieve_relevant_schema
from app.services.sql_generator import generate_sql, summarize_results
from app.services.sql_executor import execute_sql, SQLExecutionError

logger = logging.getLogger(__name__)

class DatabaseUnavailableError(RuntimeError):
    """Raised when the app cannot reach the configured database."""


class ChatResult(TypedDict):
    answer: str
    sql: str | None


async def handle_chat_message(session_id: str, message: str) -> ChatResult:
    """
    Process one user message within a session and return an answer.

    Args:
        session_id: Identifier used to load/save conversation history.
        message: The user's natural language question.

    Returns:
        A dict with the natural language `answer` and the `sql` that was
        run to produce it (None if no SQL was needed — e.g. a greeting,
        an unanswerable question, or a query that failed validation).
    """
    try:
        history = await load_history(session_id)
    except Exception as exc:
        logger.exception("Failed to load chat history for session %s", session_id)
        raise DatabaseUnavailableError(
            "The chat history store is unavailable right now.", exc
        ) from exc

    try:
        schema_context = await retrieve_relevant_schema(question=message)
    except Exception as exc:
        raise DatabaseUnavailableError(
            exc
        ) from exc

    generation = await generate_sql(
        question=message,
        schema_context=schema_context,
        history=history,
    )

    sql = generation.get("sql")
    answer = generation["answer"]

    if sql:
        try:
            results = await execute_sql(sql)
            answer = await summarize_results(question=message, sql=sql, results=results)
        except SQLExecutionError:
            # Query passed generation-time validation but failed to run
            # (e.g. referenced a column that doesn't actually exist).
            # Fall back to a friendly message rather than a 500 — this
            # is an expected outcome, not an exceptional one.
            sql = None
            answer = (
                "I generated a query for that, but it failed to run against "
                "the database. Could you try rephrasing your question?"
            )

    await save_turn(session_id=session_id, user_message=message, sql=sql, answer=answer)

    return ChatResult(answer=answer, sql=sql)
