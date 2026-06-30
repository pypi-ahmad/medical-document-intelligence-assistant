# Medical Document Intelligence Assistant

Local-first AI platform for medical document understanding and organization using local Ollama models.

## Safety First (Read Before Use)

This project is **for educational document analysis only**.

It is **not** a medical device and must **not** be used to:
- diagnose disease,
- prescribe medication,
- recommend treatment,
- replace licensed clinicians.

Every medical QA/summary/report response carries an educational-use safety disclaimer.

---

## Verified Production Run (Real Execution)

Validated on **June 30, 2026** from this repository:
`/home/ahmad/AI/medical-document-intelligence-assistant`

### Environment verified
- Python (venv): `3.12.10`
- `uv`: `0.11.19`
- Node: `v24.16.0`
- npm: `11.13.0`
- GPU: NVIDIA RTX 4060 Laptop GPU (8GB VRAM) detected by backend system health
- Ollama local models available (including `glm-ocr`, `qwen3.5:4b`, `qwen3-embedding:4b`, `phi4-mini:3.8b`, `granite4.1:3b`)

### Build + test outputs from real run
- `uv sync --frozen --extra test --extra lint` completed
- Python package artifacts built:
  - `dist/medical_document_intelligence_assistant-1.0.0-py3-none-any.whl`
  - `dist/medical_document_intelligence_assistant-1.0.0.tar.gz`
- Frontend production build (`next build`) completed; all pages generated
- Backend tests: `844 passed, 2 skipped`

### Live end-to-end verification status
- `artifacts/verification/verification_live_run.json`
- `artifacts/verification/verification_live_run.md`
- Result: **32/32 checks passed**
- Built-in matrix script (`apps/backend/scripts/e2e_validation.py`) in parser-baseline mode: **33/33 checks passed**
- Included real workflow:
  - upload sample documents (prescription, lab report, scanned document, handwritten note)
  - OCR/parsing
  - medical entity extraction
  - retrieval/search
  - grounded QA with citations
  - summary generation
  - timeline generation
  - doctor report generation

---

## What This System Does

### Inputs supported
- prescriptions
- lab reports
- scanned PDFs/images
- handwritten notes (best effort)
- referral letters
- consultation/discharge-style text documents

### Core capabilities
- OCR + page-level text extraction
- layout-aware storage (blocks/tables when available)
- medical entities, medications, and lab values extraction
- lab out-of-range detection against stated reference ranges
- timeline event generation
- hybrid retrieval (keyword + semantic)
- grounded question answering with citations
- summary generation (`plain`, `clinical`, `medication`, `laboratory`, `visit`, `discharge`)
- doctor visit preparation report with safety disclaimer
- local persistence of documents, entities, timelines, chat, reports, and embeddings

---

## Architecture (High-Level)

### Backend (`apps/backend`)
- FastAPI API surface
- Modular services:
  - OCR providers (`glmocr`, `paddleocr`, `docling`, internal `pymupdf`)
  - medical extraction pipeline
  - hybrid retrieval + embeddings
  - QA/summarization/report/timeline services
  - model routing and GPU-aware local inference integration
- Storage:
  - SQLAlchemy models + Alembic
  - SQLite for local runtime (`e2e_live.db`) or PostgreSQL in production

### Frontend (`apps/frontend`)
- Next.js 14 App Router
- Production pages for dashboard, upload center, chat, OCR viewer, timeline, labs, reports, memory, model manager, monitoring
- API proxy to backend via `API_PROXY_TARGET`

### Processing flow
Document upload -> OCR -> extraction/normalization -> chunking -> embedding -> hybrid retrieval -> grounded QA/summaries/timelines/reports

---

## Project Structure

- `apps/backend`: API, services, models, migrations, tests
- `apps/frontend`: web app
- `docs`: architecture/install/deploy/ocr/rag/timeline/troubleshooting guides
- `artifacts/verification`: live verification outputs
- `dist`: built Python packages

---

## Zero-to-Hero Setup (Exact Commands)

### 1) Enter project

```bash
cd /home/ahmad/AI/medical-document-intelligence-assistant
```

### 2) Create/use venv + install dependencies

```bash
uv venv --python 3.12.10 .venv
source .venv/bin/activate
uv sync --frozen --extra test --extra lint
```

### 3) Build backend package

```bash
uv build
```

### 4) Build frontend (production)

```bash
cd apps/frontend
npm ci --no-audit --no-fund
API_PROXY_TARGET=http://127.0.0.1:18000 npm run build
cd ../..
```

### 5) Start backend (local SQLite mode)

```bash
ENABLE_AUTH=false \
SKIP_ALEMBIC=1 \
ENABLE_GLM_OCR=true \
DATABASE_URL=sqlite+aiosqlite:///./e2e_live.db \
SYNC_DATABASE_URL=sqlite:///./e2e_live.db \
uv run uvicorn app.main:app --app-dir apps/backend --host 127.0.0.1 --port 18000
```

### 6) Start frontend (production)

```bash
cd apps/frontend
API_PROXY_TARGET=http://127.0.0.1:18000 npm run start -- --hostname 127.0.0.1 --port 3100
```

### 7) Access
- Frontend: `http://127.0.0.1:3100`
- Backend health: `http://127.0.0.1:18000/health`
- OpenAPI docs: `http://127.0.0.1:18000/docs`

---

## Real End-to-End Execution (How It Was Verified)

A live verifier was executed against running backend/frontend and generated:
- `artifacts/verification/verification_live_run.json`
- `artifacts/verification/verification_live_run.md`

### What it verified
- prescription upload + processing
- lab report upload + processing
- scanned document upload + OCR
- handwritten note OCR (best effort)
- layout preservation for PDF docs where applicable
- medical entity extraction
- medication extraction
- lab value extraction + out-of-range flags
- vector/hybrid search
- grounded QA with citations
- summaries
- timeline generation
- doctor report generation
- educational-only disclaimer behavior
- frontend route availability/usability
- backend API availability
- database + vector metadata persistence

### Key measured outputs from the latest live run
- checks: `32 passed / 0 failed`
- DB persistence counts for new documents:
  - `documents=4`
  - `ocr_pages=4`
  - `entities=79`
  - `labs=6`
  - `medications=17`
  - `timeline_events=47`
  - `chunks=5`
  - `embeddings_non_null=5`
- Real chain sample (single workflow): upload -> process -> OCR page(1) -> entities(8) -> retrieval hits(5) -> QA citations(5) -> summary -> timeline -> report

---

## API Surface (Core)

- `POST /api/documents/`
- `POST /api/medical/process/{document_id}`
- `GET /api/medical/documents/{document_id}/ocr`
- `GET /api/medical/documents/{document_id}/entities`
- `GET /api/medical/documents/{document_id}/medications`
- `GET /api/medical/documents/{document_id}/labs`
- `POST /api/search`
- `POST /api/qa/query`
- `POST /api/summaries`
- `POST /api/timelines`
- `POST /api/reports/generate`
- `GET /api/reports/{report_id}/export`
- `GET /api/medical/disclaimer`
- `GET /api/system/health`

---

## Testing Commands

### Full backend tests

```bash
timeout 2400s uv run pytest apps/backend/tests -q
```

### Live medical workflow verifier

```bash
./.venv/bin/python scripts/verify_medical_live.py
```

### Repository-native extraction E2E matrix (parser baseline mode)

```bash
ENABLE_AUTH=false \
SKIP_ALEMBIC=1 \
ENABLE_GLM_OCR=false \
DATABASE_URL=sqlite+aiosqlite:///./e2e_live.db \
SYNC_DATABASE_URL=sqlite:///./e2e_live.db \
uv run uvicorn app.main:app --app-dir apps/backend --host 127.0.0.1 --port 18000

MDIA_API_BASE=http://127.0.0.1:18000/api ./.venv/bin/python apps/backend/scripts/e2e_validation.py
```

### Targeted test (medical agent path)

```bash
uv run pytest apps/backend/tests/test_medical_agents.py -q
```

### Lint

```bash
uv run ruff check apps/backend/app/services/medical/agents.py
```

---

## Known Runtime Notes

- `/health/ready` may return `503` when cloud LLM provider keys are intentionally not configured.
- Local medical assistant workflow remains operational with Ollama models and is validated by live workflow artifacts.
- Next.js rewrites are build-time sensitive for this setup; build frontend with
  `API_PROXY_TARGET=http://127.0.0.1:18000` to avoid `/api/*` proxying to the default `127.0.0.1:8000`.
- If port conflicts occur, free them before restart:

```bash
fuser -k 18000/tcp || true
fuser -k 3100/tcp || true
```

---

## Security + Privacy

- Files are encrypted at rest in upload path.
- Local-first execution is supported; keep sensitive medical documents on local machine.
- Use environment variables for secrets (`JWT_SECRET_KEY`, encryption key, provider keys).
- Enable auth and hardened settings for non-local deployment.

---

## Documentation Index

- `docs/INSTALLATION_GUIDE.md`
- `docs/ARCHITECTURE_GUIDE.md`
- `docs/FOLDER_STRUCTURE.md`
- `docs/API_DOCUMENTATION.md`
- `docs/OCR_GUIDE.md`
- `docs/MEDICAL_ENTITY_EXTRACTION_GUIDE.md`
- `docs/RAG_GUIDE.md`
- `docs/TIMELINE_GUIDE.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/DOCKER_GUIDE.md`
- `docs/OLLAMA_GUIDE.md`
- `docs/GPU_GUIDE.md`
- `docs/TROUBLESHOOTING_GUIDE.md`
- `docs/FAQ.md`
- `docs/PERFORMANCE_GUIDE.md`
- `docs/BEGINNER_GUIDE.md`

---

## Final Safety Reminder

This application helps organize and explain uploaded medical documents for educational use only. It does not diagnose diseases, prescribe medications, or recommend treatments. Always consult a qualified healthcare professional for medical decisions.
