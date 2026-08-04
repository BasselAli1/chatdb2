FROM python:3.12-slim

# Install uv (fast Python package manager/resolver)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /code

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-cache

COPY app ./app

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
