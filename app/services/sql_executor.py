"""
SQL executor for the Chat-with-Database app.

Executes a SQL query (already generated + basic-validated by
sql_generator.py) against the demo Postgres database and returns rows
as plain dicts.

Safety measures applied here (on top of the "must be a SELECT, no
write/DDL keywords" check already done in sql_generator.py):
    - A Postgres statement_timeout is set for the session, so a runaway
      query can't hang the request indefinitely.
    - The query is run inside a READ ONLY transaction, so even if a
      write statement somehow slipped through, Postgres itself would
      reject it.
    - A LIMIT is appended if the query doesn't already have one, so a
      broad SELECT can't accidentally return the entire table.

This file assumes the SQL it receives has already passed the checks in
sql_generator.py — it does not re-validate SQL safety itself, only
enforces execution-time limits.
"""

import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings

_engine = create_async_engine(settings.ASYNC_DATABASE_URL)

# Cheap check for an existing LIMIT clause. Not bulletproof (e.g. won't
# catch "LIMIT" inside a string literal) but sql_generator.py already
# restricts input to simple read-only SELECTs, so this is a reasonable
# safety net rather than a full SQL parser.
_LIMIT_PATTERN = re.compile(r"\bLIMIT\s+\d+\b", re.IGNORECASE)


class SQLExecutionError(Exception):
    """Raised when the query fails to execute against the database."""


def _with_limit(sql: str, max_rows: int) -> str:
    """Append a LIMIT clause if the query doesn't already have one."""
    stripped = sql.strip().rstrip(";")
    if _LIMIT_PATTERN.search(stripped):
        return stripped
    return f"{stripped} LIMIT {max_rows}"


async def execute_sql(sql: str) -> list[dict]:
    """
    Execute a validated read-only SQL query and return the results.

    Args:
        sql: A SQL SELECT statement, already checked by sql_generator.py.

    Returns:
        A list of row dicts (column name -> value).

    Raises:
        SQLExecutionError: If the query fails (bad syntax, unknown
            column/table, timeout, etc.). The original database error
            is included in the message for debugging/logging, but
            callers should show the user a friendly message rather
            than this raw text.
    """
    bounded_sql = _with_limit(sql, settings.SQL_MAX_ROWS)
    #print(f"Executing SQL (with enforced limit):\n{bounded_sql}")
    async with AsyncSession(_engine) as session:
        try:
            await session.execute(
                text(f"SET LOCAL statement_timeout = {settings.SQL_STATEMENT_TIMEOUT_MS}")
            )
            await session.execute(text("SET TRANSACTION READ ONLY"))
            result = await session.execute(text(bounded_sql))
            rows = result.mappings().all()
        except Exception as exc:
            raise SQLExecutionError(str(exc)) from exc
        finally:
            # READ ONLY transaction never needs committing; rolling back
            # is the correct way to close it cleanly either way.
            await session.rollback()

    return [dict(row) for row in rows]
