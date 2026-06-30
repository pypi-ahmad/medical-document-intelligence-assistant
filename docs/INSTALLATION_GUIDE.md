# Installation Guide

## What
Full local installation for backend, frontend, database, models, and observability.

## Why
Reproducible environment for development and production-like local deployment.

## How

1. Clone/open project at `/home/ahmad/AI/medical-document-intelligence-assistant`.
2. Create Python env with `uv` and sync dependencies.
3. Install frontend dependencies.
4. Configure backend `.env`.
5. Run Alembic migrations.
6. Start stack (`docker compose up --build`) or run backend/frontend directly.

## Commands

```bash
cd /home/ahmad/AI/medical-document-intelligence-assistant
uv venv --python 3.12.10 .venv
source .venv/bin/activate
uv sync --extra test --extra lint
cd apps/frontend && npm install && cd ../..
cp apps/backend/.env.example apps/backend/.env
uv run alembic upgrade head
docker compose up --build
```

## Design Decision
- Chosen Python 3.12.10 for ecosystem compatibility.
- `uv` for deterministic and fast dependency management.
- Docker Compose for local-first production parity.

## Alternatives Considered
- Python 3.13/3.14 rejected for dependency compatibility risk.
- Bare-metal deployment rejected for lower reproducibility.

## Best Practices
- Keep secrets in `.env`, never in source.
- Rotate JWT and encryption keys periodically.
- Pin model tags in config, not code.
