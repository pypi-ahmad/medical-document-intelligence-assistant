# API Documentation Guide

OpenAPI is served at `/docs` and `/redoc`.

## Core Endpoints

- `POST /api/auth/bootstrap`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/documents/`
- `GET /api/documents/`
- `POST /api/medical/process/{document_id}`
- `GET /api/medical/documents/{document_id}/ocr`
- `GET /api/medical/documents/{document_id}/entities`
- `GET /api/medical/documents/{document_id}/labs`
- `GET /api/medical/documents/{document_id}/medications`
- `POST /api/search`
- `POST /api/qa/query`
- `POST /api/qa/query/stream` (SSE token stream)
- `POST /api/summaries`
- `POST /api/timelines`
- `POST /api/reports/generate`
- `GET /api/reports/{report_id}`
- `GET /api/reports/{report_id}/export`
- `GET/POST/DELETE /api/memory`
- `GET /api/agents/runs`
- `GET/PATCH /api/models/config`
- `GET /api/system/health`

## Security
- JWT bearer auth required for protected routes.
- Rate limiting via SlowAPI.
- Upload validation + MIME verification.

## Safety Contract
All generative endpoints include educational-use disclaimer and must avoid diagnosis/treatment/prescribing.

## Streaming QA Contract
- Endpoint: `POST /api/qa/query/stream`
- Response type: `text/event-stream`
- Event sequence:
  - `session` -> `{session_id, model}`
  - `token` -> `{text}` repeated
  - `done` -> final payload with `answer`, `citations`, `model`, `safety`
- Guardrail behavior: prohibited medical questions stream a `guardrail` response without model generation.

## Search Contract (`POST /api/search`)
- Request supports:
  - `query` (string),
  - `top_k` (int),
  - `document_ids` (list),
  - `start_date` / `end_date` (ISO date),
  - `filters` (dict).
- Implemented filter keys:
  - `min_score` (0.0-1.0),
  - `page_numbers` (list[int]),
  - `section_names` (list[str]),
  - `must_contain` (list[str]),
  - `metadata` (dict exact-match),
  - `query_terms_match` (bool).
- Response now includes:
  - `filters_applied` echo payload,
  - `diagnostics` (`total_chunks_scanned`, `chunks_after_filters`, `chunks_discarded_by_score`, `query_embedding_available`, `applied_filters`, weight config),
  - scored `results` with semantic + keyword breakdown.

## Timeline Contract (`POST /api/timelines`)
- Request supports:
  - `document_ids`,
  - `event_types`,
  - `start_date`,
  - `end_date`.
- Response includes `filters_applied` echo and filtered timeline events.
