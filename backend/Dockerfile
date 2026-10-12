FROM python:3.14-slim

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./

RUN pip install uv && uv sync --frozen --no-dev

# Use the venv directly so `uv run` doesn't re-sync dev dependencies at startup
ENV PATH="/app/.venv/bin:$PATH"

COPY backend/app ./app

COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini

COPY worker ./worker

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]