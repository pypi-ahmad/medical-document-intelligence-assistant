# Troubleshooting Guide

## Common Issues

### 1) 401 Unauthorized everywhere
- Bootstrap/login first.
- Verify bearer token in frontend local storage.

### 2) OCR fails
- Check `OLLAMA_BASE_URL` and model presence (`ollama list`).
- Ensure uploaded file type is supported.

### 3) Migration errors
- Confirm `DATABASE_URL` + `SYNC_DATABASE_URL` consistency.
- Run `uv run alembic upgrade head` manually.

### 4) No retrieval results
- Ensure document was processed after upload.
- Confirm chunks/embeddings exist for that document.

### 5) High latency
- Use smaller chat model in model manager.
- Reduce `top_k` for QA/search.

### 6) Frontend build fails
- Remove stale route files using old API imports.
- Re-run `npm install` then `npm run build`.
