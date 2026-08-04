"""
Shared vector store access for the Chat-with-Database app.

Two responsibilities:
    1. get_vector_store() - a single shared PGVector instance, used by
       both the retriever (schema_retriever.py, read path) and the
       seeding script below (write path). Centralizing this avoids
       duplicating connection/collection setup in multiple files.
    2. seed_schema_descriptions() - a one-off ingestion routine that
       embeds demo table descriptions (from app/data/schema_descriptions.json)
       into the store. Intended to be run manually or on startup for the
       demo dataset; NOT meant for "bring your own database" mode, which
       will need its own (schema-introspection-based) seeding path later.
"""

import json
from pathlib import Path

from langchain_postgres import PGVector
from langchain_ollama import OllamaEmbeddings
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

from langchain_core.documents import Document

from app.config import settings
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine

SCHEMA_COLLECTION_NAME = "schema_descriptions"

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "schema_descriptions.json"

_vector_store: PGVector | None = None


async def get_vector_store() -> PGVector | None:
    """
    Return a shared PGVector instance for the schema_descriptions collection.

    Lazily constructed and cached at module level so both the retriever
    and the seeding routine reuse the same connection/embeddings setup.

    Uses async_mode=True: PGVector normally sets up the vector extension
    and its internal tables synchronously at construction time, which
    breaks when called from inside an async context (raises a
    "greenlet_spawn has not been called" error). async_mode=True skips
    that automatic sync setup, and we call the async equivalent
    (__apost_init__) explicitly instead.
    """
    global _vector_store
    if _vector_store is None:
        if settings.mode == "offline":
            embeddings = OllamaEmbeddings(
                model=settings.OLLAMA_EMBEDDING_MODEL
            )
        else:
            embeddings = NVIDIAEmbeddings(
                api_key=settings.OPENROUTER_API_KEY,
                model=settings.OPENROUTER_EMBEDDING_MODEL,
                base_url=settings.OPENROUTER_BASE_URL,
            )
        _vector_store = PGVector(
            embeddings=embeddings,
            collection_name=SCHEMA_COLLECTION_NAME,
            connection=settings.ASYNC_DATABASE_URL,
            use_jsonb=True,
            async_mode=True,
        )
        try:
            await _vector_store.__apost_init__()
        except ProgrammingError as e:
            # asyncpg / SQLAlchemy may raise a ProgrammingError when a
            # statement contains multiple commands (asyncpg doesn't allow
            # preparing multi-statement SQL). Fall back to creating the
            # vector extension with a separate exec to avoid the
            # "cannot insert multiple commands into a prepared statement" error.
            err_text = str(e)
            if "cannot insert multiple commands into a prepared statement" in err_text:
                engine = create_async_engine(settings.ASYNC_DATABASE_URL)
                async with engine.begin() as conn:
                    # Run the extension creation as a single command
                    await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector;")
                await engine.dispose()
                # After creating the extension, ensure tables and collection exist
                await _vector_store.acreate_tables_if_not_exists()
                await _vector_store.acreate_collection()
            else:
                raise
        except Exception:
            # If Ollama or the embedding service is unavailable, keep the
            # application usable and let chat requests return a friendly error.
            _vector_store = None
    return _vector_store


def _load_table_descriptions() -> list[dict]:
    """Read the demo table descriptions from the JSON data file."""
    with open(_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


async def seed_schema_descriptions() -> int:
    """
    Embed demo table descriptions into the vector store.

    Reads app/data/schema_descriptions.json and adds one Document per
    table (using the table name as an ID, so re-running this is
    idempotent - re-seeding overwrites rather than duplicates entries).

    Returns:
        The number of table descriptions seeded.
    """
    entries = _load_table_descriptions()

    documents = [
        Document(
            page_content=entry["description"],
            metadata={"table": entry["table"]},
        )
        for entry in entries
    ]
    ids = [entry["table"] for entry in entries]

    store = await get_vector_store()
    if store is None:
        return 0

    await store.aadd_documents(documents, ids=ids)

    return len(documents)


if __name__ == "__main__":
    import asyncio

    count = asyncio.run(seed_schema_descriptions())
    print(f"Seeded {count} table descriptions into '{SCHEMA_COLLECTION_NAME}'.")
