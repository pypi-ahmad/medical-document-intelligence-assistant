# Backend image for Medical Document Intelligence Assistant.

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY apps/backend ./apps/backend
COPY prompts ./prompts
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

FROM python:3.12.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

RUN apt-get update \
 && apt-get install -y --no-install-recommends tini curl libstdc++6 \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/apps /app/apps
COPY --from=builder --chown=app:app /app/prompts /app/prompts
COPY --from=builder --chown=app:app /app/alembic.ini /app/alembic.ini
COPY --from=builder --chown=app:app /app/pyproject.toml /app/pyproject.toml
COPY --from=builder --chown=app:app /app/uv.lock /app/uv.lock

RUN mkdir -p /app/data/uploads /app/data/artifacts \
 && chown -R app:app /app/data

ENV PATH=/app/.venv/bin:$PATH \
    UPLOAD_DIR=/app/data/uploads \
    ARTIFACTS_DIR=/app/data/artifacts

USER app

EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--app-dir", "apps/backend"]
