# Deployment Guide

## Target
Local-first production deployment via Docker Compose.

## Steps
1. Configure `.env` secrets and model tags.
2. Start stack with `docker compose up --build`.
3. Run migrations `uv run alembic upgrade head` (or startup migration path).
4. Bootstrap admin.
5. Verify health endpoints and dashboards.

## Required Checks
- `/health/ready` returns 200
- `/api/system/health` confirms Ollama/GPU visibility
- Prometheus scrape active
- Grafana dashboards accessible

## Rollback
- Keep versioned images/tags.
- Revert to prior image tag and restore DB snapshot.
