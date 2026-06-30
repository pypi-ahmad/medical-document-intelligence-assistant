# Docker Guide

## Services
- `backend` FastAPI
- `frontend` Next.js
- `postgres` pgvector
- `redis`
- `ollama`
- `prometheus`
- `grafana`
- `loki`
- `otel-collector`
- `nginx`

## Commands

```bash
docker compose up --build
docker compose ps
docker compose logs -f backend
docker compose down
```

## Best Practices
- Persist volumes for DB/models/metrics.
- Do not expose admin credentials in plain text.
- Restrict ports in production network perimeter.
