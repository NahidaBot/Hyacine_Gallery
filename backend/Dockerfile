FROM python:3.14-slim AS base

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS dev
RUN pip install --no-cache-dir -e ".[dev]"
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
