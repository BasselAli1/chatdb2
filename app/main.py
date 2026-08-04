"""
FastAPI app entrypoint for the Chat-with-Database app.

Responsibilities:
    - Register the chat router (app/api/routes.py).
    - Enable CORS for all origins (portfolio demo — no auth/session
      cookies in play, so this is low-risk; tighten if this ever
      becomes a real multi-tenant deployment).
    - Auto-seed the schema vector store on startup, so the demo works
      out of the box without a manual setup step. Seeding is idempotent
      (see vector_store.seed_schema_descriptions), so this is safe to
      run on every startup.
    - Expose a simple health check endpoint.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as chat_router
from app.db.vector_store import seed_schema_descriptions

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed the demo schema descriptions into the vector store.
    # If Ollama or the vector store is unavailable, keep the app running
    # and return a friendly chat error later instead of crashing startup.
    try:
        await seed_schema_descriptions()
    except Exception as exc:
        logger.warning("Skipping schema seeding because the embedding service is unavailable: %s", exc)
    yield
    # No shutdown cleanup needed yet (engines are process-lifetime).


app = FastAPI(title="Chat with Database", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chatdb2.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/health")
async def health() -> dict:
    """Basic liveness check."""
    return {"status": "ok"}
