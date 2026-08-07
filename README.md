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
2. **Generate** — an LLM turns the question + retrieved schema context +
   conversation history into a SQL `SELECT` query, using structured
   output for a reliable response shape.
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
- OpenRouter or a local/hosted Ollama model (via LangChain's
  OpenAI-compatible and Ollama clients) for generation and embeddings
- Postgres with the pgvector extension
- uv for Python dependency management
- React (Vite) frontend

## Project structure

```
app/
  main.py                    FastAPI entrypoint, CORS, startup schema seeding
  config.py                  Environment-driven settings (pydantic-settings)
  api/routes.py               POST /chat endpoint
  services/
    chat_service.py           Orchestrates a chat turn end-to-end
    schema_retriever.py       RAG retrieval of relevant table descriptions
    sql_generator.py          LLM call that generates + validates SQL
    sql_executor.py           Runs SQL read-only, with timeout + row limit
  db/
    vector_store.py           pgvector store setup + schema-embedding seeding
    history.py                Per-session conversation history persistence
    neon_url_fix.py           Normalizes DATABASE_URL to the asyncpg driver
  data/schema_descriptions.json  Table descriptions embedded for retrieval
db/init/                      SQL run on first Postgres startup (demo schema + seed data)
frontend/                     React + Vite chat UI
tests/                        Unit tests
tools/inspect_sql.py          Manual script for debugging SQL generation
```

## Running it

1. `docker compose up --build`
2. The API is available at `http://localhost:8000` and the chat UI is
   available at `http://localhost:3000`.
3. Try the API directly:

   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"session_id": "demo", "message": "Which customers are from California?"}'
   ```

On first startup, Postgres seeds itself with a small demo dataset
(customers, orders, products, order_items, reviews — see `db/init/`),
and the app seeds the schema-description embeddings needed for
retrieval (see `app/db/vector_store.py`).

### Running the API without Docker

```bash
uv sync
uv run uvicorn app.main:app --reload
```

This still requires a reachable Postgres with the `pgvector` extension
(point `DATABASE_URL` at one, e.g. the `db` service from
`docker compose up db`).

### Running the frontend without Docker

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` (e.g. in `frontend/.env`) to the API's URL, such as
`http://localhost:8000`.

## Configuration

Settings are read from a `.env` file at the project root (see
`app/config.py`). Key variables:

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | Postgres connection string, used for both chat history and the pgvector store. Accepts a standard `postgresql://` URL; it's normalized to the `asyncpg` driver automatically. |
| `MODE` | Runtime mode; `online` uses OpenRouter for generation, otherwise Ollama is used. |
| `OPENROUTER_API_KEY`, `OPENROUTER_CHAT_MODEL`, `OPENROUTER_EMBEDDING_MODEL` | OpenRouter credentials/model names (get a key at [openrouter.ai/keys](https://openrouter.ai/keys)). |
| `OLLAMA_API_KEY`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_BASE_URL` | Ollama configuration for local/hosted chat and embedding models. |
| `SQL_MAX_ROWS` | Max rows returned per query (default `200`). |
| `SQL_STATEMENT_TIMEOUT_MS` | Postgres statement timeout in ms for generated queries (default `5000`). |
| `VITE_API_URL` | Frontend-only: base URL of the API. |

## API

### `POST /chat`

Request:

```json
{ "session_id": "demo", "message": "Which customers are from California?" }
```

Response:

```json
{
  "session_id": "demo",
  "answer": "There are 3 customers from California: ...",
  "sql": "SELECT ... FROM customers WHERE state = 'CA' LIMIT 200"
}
```

`sql` is `null` when no query was needed or generation didn't produce
one (e.g. a greeting or an unanswerable question).

### `GET /health`

Basic liveness check, returns `{"status": "ok"}`.

## Safety

Generated SQL is restricted to a single read-only `SELECT` statement —
write/DDL keywords and stacked statements are rejected before
execution — and every query runs inside a Postgres `READ ONLY`
transaction with a statement timeout and row limit as additional
safety nets.

## Tests

```bash
uv run python -m unittest discover tests
```
