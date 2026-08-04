"""
SQL generator for the Chat-with-Database app.

Takes a user's question, retrieved schema context (from
schema_retriever), and conversation history, and asks an LLM (via
OpenRouter) to produce a SQL query + a natural language explanation.

Uses LangChain's structured output (a bound Pydantic schema) rather
than free-text + manual parsing, so the response shape is reliable.

This file does NOT execute the generated SQL — see sql_executor
(not built yet). It does basic sanity validation only (e.g. rejecting
anything that isn't a SELECT); deeper validation (column/table
existence, sqlglot parsing, etc.) belongs in that later file.
"""

from typing import TypedDict

from langchain_ollama import ChatOllama
from langchain_nvidia_ai_endpoints import ChatNVIDIA

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel, Field

from app.config import settings
from app.db.history import HistoryTurn

# Keywords that indicate the model tried to generate something other
# than a read-only query. Basic guardrail only — not a substitute for
# proper SQL parsing/validation in the executor step.
DISALLOWED_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "TRUNCATE", "CREATE", "GRANT", "REVOKE",
)


class SQLGeneration(BaseModel):
    """Structured response the LLM must produce.

    NOTE: Some OpenRouter providers fail when Pydantic emits an `anyOf`
    schema for nullable union types (e.g. `str | None`). To avoid that
    interoperability problem we use an empty-string sentinel for "no
    SQL" instead of a nullable type. Callers should treat an empty
    string as `None`.
    """

    sql: str = Field(
        default="",
        description=(
            "A single read-only SELECT query that answers the user's question, "
            "using only the tables/columns from the provided schema context. "
            "Empty string if no query is needed (e.g. a greeting or a question "
            "that can't be answered from this schema)."
        ),
    )
    answer: str = Field(
        description="A natural language response to the user: either an "
        "explanation of what the query above does, or a direct reply if "
        "no SQL was generated.",
    )


class SQLGenerationResult(TypedDict):
    sql: str | None
    answer: str

if settings.mode == "offline":
    _llm = ChatOllama(
        model=settings.OLLAMA_ONLINE_CHAT_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )
else:
    _llm = ChatNVIDIA(
        model=settings.OPENROUTER_CHAT_MODEL,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
    )



_structured_llm = _llm.with_structured_output(SQLGeneration)

_SYSTEM_PROMPT = """\
You are a careful SQL analyst. Given relevant table descriptions and a \
user's question, write a single PostgreSQL SELECT query that answers it.

Rules:
- You must respond in a JSON object with two fields: `sql` and `answer`.
- you must generate sql query in the `sql` field, and a natural language explanation in the `answer` field.
- Only use tables/columns mentioned in the schema context below.
- Only generate read-only SELECT queries. Never write/modify data.
- If the question can't be answered from the given schema context, \
leave `sql` null and explain why in `answer`.
- `sql` is for the sql query itself; `answer` is a natural language explanation of what the query does.
- If the question is a greeting or otherwise doesn't need SQL, leave `sql` null and
- Keep `answer` concise and non-technical where possible.

Schema context:
{schema_context}
"""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)

_chain = _prompt | _structured_llm


def _history_to_messages(history: list[HistoryTurn]) -> list[HumanMessage | AIMessage]:
    """Convert stored history turns into LangChain message objects."""
    messages: list[HumanMessage | AIMessage] = []
    for turn in history:
        messages.append(HumanMessage(content=turn["user_message"]))
        messages.append(AIMessage(content=turn["answer"]))
    return messages


def _is_safe_select(sql: str) -> bool:
    """Basic sanity check: must look like a single read-only SELECT."""
    normalized = sql.strip().strip(";").upper()
    if not normalized.startswith("SELECT"):
        return False
    if any(keyword in normalized for keyword in DISALLOWED_KEYWORDS):
        return False
    if ";" in sql.strip().rstrip(";"):
        # Reject anything that looks like multiple stacked statements.
        return False
    return True


_ANSWER_SYSTEM_PROMPT = """\
You are a helpful analyst. Given the user's question, the SQL query \
that was run, and the resulting rows, write a concise natural language \
answer. Reference specific numbers/values from the results where \
relevant. If the results are empty, say so plainly rather than \
guessing at an answer. Be brief and non-technical where possible. Return only the answer text, \
without any additional commentary or formatting.
"""

_answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _ANSWER_SYSTEM_PROMPT),
        ("human", "Question: {question}\n\nSQL: {sql}\n\nResults: {results}"),
    ]
)

_answer_chain = _answer_prompt | _llm


async def summarize_results(question: str, sql: str, results: list[dict]) -> str:
    """
    Turn real query results into a natural language answer.

    Args:
        question: The user's original question.
        sql: The SQL query that was executed.
        results: The rows returned by sql_executor.execute_sql, as dicts.

    Returns:
        A natural language answer grounded in the actual results.
    """
    response = await _answer_chain.ainvoke(
        {
            "question": question,
            "sql": sql,
            "results": results if results else "(no rows returned)",
        }
    )
    return response.content


async def generate_sql(
    question: str,
    schema_context: str,
    history: list[HistoryTurn],
) -> SQLGenerationResult:
    """
    Generate a SQL query (and explanation) for a user's question.

    Args:
        question: The user's natural language question.
        schema_context: Retrieved table descriptions from schema_retriever.
        history: Prior turns in this session, used for conversational context.

    Returns:
        A dict with `sql` (str or None) and `answer` (str). If the model
        produced SQL that fails basic safety checks, `sql` is set to
        None and `answer` explains that the query was rejected.
    """
    try:
        result: SQLGeneration = await _chain.ainvoke(
            {
                "schema_context": schema_context or "(no relevant tables found)",
                "history": _history_to_messages(history),
                "question": question,
            }
        )
    except Exception:
        return SQLGenerationResult(
            sql=None,
            answer=(
                Exception 
            ),
        )

    sql_value = result.sql.strip() if result.sql else ""
    if sql_value and not _is_safe_select(sql_value):
        return SQLGenerationResult(
            sql=None,
            answer=(
                "I generated a query but it didn't pass safety checks "
                "(only read-only SELECT statements are allowed), so I didn't "
                "run it. Could you rephrase your question?"
            ),
        )

    return SQLGenerationResult(sql=sql_value or None, answer=result.answer)
