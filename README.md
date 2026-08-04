# Chat with Database

A text-to-SQL app that uses RAG to let you ask natural language questions
over a Postgres database. Instead of stuffing an entire schema into every
prompt, table descriptions are embedded (via pgvector) and only the
relevant ones are retrieved for a given question — the same
retrieve-then-generate pattern used in document Q&A, applied to schema
metadata instead of text chunks.

## How it works

1. **Retrieve** — the question is embedded and matched against stored
   table descriptions in pgvector, returning only the relevant tables
   (not the whole schema).
2. **Generate** — an LLM (via OpenRouter) turns the question + retrieved
   schema context + conversation history into a SQL `SELECT` query,
   using structured output for a reliable response shape.
3. **Validate** — the generated SQL is checked (must be a read-only
   `SELECT`, no write/DDL keywords, no stacked statements) before it's
   allowed to run.
4. **Execute** — the query runs inside a Postgres `READ ONLY`
   transaction, with a statement timeout and an automatic row limit as
   safety nets.
5. **Answer** — a second LLM call turns the real query results into a
   natural language answer, grounded in actual data.

Conversation history is stored per-session in Postgres, so follow-up
questions have context.

## Stack

- FastAPI + SQLAlchemy (async) + asyncpg
- LangChain + langchain-postgres (PGVector) for retrieval
- OpenRouter (via LangChain's OpenAI-compatible client) for generation
- Postgres with the pgvector extension
- uv for dependency management

## Project structure

```
app/
  api/routes.py           - POST /chat endpoint
  services/
    chat_service.py       - orchestrates one chat turn
    schema_retriever.py   - RAG retrieval over table descriptions
    sql_generator.py      - LLM SQL generation + results summarization
    sql_executor.py       - safe, read-only SQL execution
  db/
    history.py            - Postgres-backed conversation history
    vector_store.py        - shared PGVector factory + schema seeding
  data/schema_descriptions.json - demo table descriptions (RAG source)
  config.py                - settings (reads .env)
  main.py                   - FastAPI app, CORS, startup seeding
db/init/                    - demo schema + sample data (auto-run by Postgres on first boot)
docker-compose.yml
Dockerfile
pyproject.toml
```

## Running it

1. Make sure Ollama is installed and running locally, and that the models you want are available
   (for example `llama3.2:3b` and `nomic-embed-text`).
2. `docker compose up --build`
3. The API is available at `http://localhost:8000` and the chat UI is available at `http://localhost:3000`.
4. Try the API directly:

   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"session_id": "demo", "message": "Which customers are from California?"}'
   ```

On first startup, Postgres seeds itself with a small demo dataset
(customers, orders, products, order_items, reviews — see `db/init/`),
and the app seeds the schema-description embeddings needed for
retrieval (see `app/db/vector_store.py`).

## Notes / current limitations

- Demo dataset only — "bring your own database" mode isn't built yet;
  it would need its own schema-introspection-based seeding path.
- No frontend yet — this is API-only for now.
- SQL validation is intentionally basic (keyword checks), not a full
  SQL parser — reasonable for a demo, would want tightening for a
  real multi-tenant deployment.
