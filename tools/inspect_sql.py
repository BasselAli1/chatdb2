"""
Run this script to invoke the LLM SQL generation chain and print the raw model output
for debugging. It calls the internal LangChain `_chain` defined in
`app.services.sql_generator` to get the structured response before any application
sanitization. Run with the project's Python: `.venv/bin/python3 tools/inspect_sql.py`.
"""
import asyncio

from app.services import sql_generator
from app.services.sql_executor import execute_sql


async def main():
    question = "what is the number of customers?"
    schema_context = await _maybe_get_schema_context()
    print("Question:\n", question)
    print("Schema context (truncated):\n", (schema_context[:100] + '...') if schema_context and len(schema_context) > 100 else schema_context)

    payload = {
        "schema_context": schema_context or "(no relevant tables found)",
        "history": [],
        "question": question,
    }

    print("Invoking the structured LLM chain...")
    result = await sql_generator._chain.ainvoke(payload)
    
    x = await sql_generator.generate_sql(question=question, schema_context=schema_context, history=[]) # Call to ensure any side effects are executed
    print(x)
    # Print full raw result returned by the chain
    print("\nRaw chain result object:", repr(result))

    # Attempt to access `.sql` and `.answer` (SQLGeneration model fields)
    sql = getattr(result, "sql", None)
    answer = getattr(result, "answer", None)

    print("\nExtracted fields:")
    print("sql:\n", sql)
    print("answer:\n", answer)
    executed_sql = await execute_sql(sql)  # Call to ensure any side effects are executed
    print("\nExecuted SQL results:", executed_sql)
    print(await sql_generator.summarize_results(question=question, sql=sql, results=executed_sql))  # Call to ensure any side effects are executed

async def _maybe_get_schema_context():
    # Try to load the schema context via the retriever if available for a more realistic prompt.
    try:
        from app.services.schema_retriever import retrieve_relevant_schema

        return await retrieve_relevant_schema(question="Show me the number of customers from each country.")
    except Exception:
        return Exception


if __name__ == "__main__":
    asyncio.run(main())
