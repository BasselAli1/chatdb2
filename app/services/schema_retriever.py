"""
Schema retriever for the Chat-with-Database app.

Performs the RAG retrieval step: given a user's natural language
question, finds the most relevant table descriptions from a PGVector
store so the SQL-generation step only sees schema context that
actually matters for this question (instead of the entire schema).

This file ASSUMES the vector store has already been populated (one
embedded document per table, e.g. "orders: stores customer orders,
columns include id, customer_id, status, total, created_at..."). The
seeding/ingestion process is a separate concern (a startup script or
ingestion file), not implemented here.
"""

from app.db.vector_store import get_vector_store

DEFAULT_TOP_K = 5


async def retrieve_relevant_schema(question: str, top_k: int = DEFAULT_TOP_K) -> str:
    """
    Retrieve the most relevant table descriptions for a given question.

    Args:
        question: The user's natural language question.
        top_k: Max number of table-description chunks to retrieve.

    Returns:
        A single string containing the retrieved table descriptions,
        concatenated and ready to drop into the SQL-generation prompt.
        Returns an empty string if nothing relevant is found.
    """
    store = await get_vector_store()
    if store is None:
        return ""

    results = await store.asimilarity_search(question, k=top_k)

    if not results:
        return ""

    # Join with clear separators so the LLM can tell where one table's
    # description ends and the next begins.
    return "\n\n".join(doc.page_content for doc in results)
