"""
App configuration for the Chat-with-Database app.

Centralizes all environment-driven settings using pydantic-settings.
Every other file that needed config so far (history.py, vector_store.py,
schema_retriever.py, sql_generator.py) imports `settings` from here.

Values are read from a .env file (or real environment variables) at
process startup. See .env.example for the expected keys.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.db.neon_url_fix import to_asyncpg_url

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    # Runtime mode controlling whether to use local Ollama embeddings/chat.
    mode: str = Field("online", env="MODE")

    # Postgres connection string, used both for the chat_history table
    # (via SQLAlchemy) and the PGVector schema-embeddings store.
    # Expected format: postgresql+asyncpg://user:password@host:port/dbname
    DATABASE_URL: str
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return to_asyncpg_url(self.DATABASE_URL)
    # Optional OpenRouter settings retained for compatibility.
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_CHAT_MODEL: str | None = None
    OPENROUTER_EMBEDDING_MODEL: str | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Ollama model configuration for local embeddings/chat usage.
    OLLAMA_API_KEY: str | None = None
    OLLAMA_EMBEDDING_MODEL: str = "snowflake-arctic-embed:22m"
    OLLAMA_CHAT_MODEL: str = "llama3.2:3b"
    OLLAMA_BASE_URL: str = "https://ollama.com/api"
    

    # Safety net for sql_executor.py: max rows returned per query, and
    # a statement timeout (ms) enforced at the Postgres session level.
    SQL_MAX_ROWS: int = 200
    SQL_STATEMENT_TIMEOUT_MS: int = 5000

    


settings = Settings()
