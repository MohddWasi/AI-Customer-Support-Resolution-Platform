FROM python:3.14-slim

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./

RUN pip install uv && uv sync --frozen --no-dev

COPY backend/app ./app

COPY worker ./worker

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]