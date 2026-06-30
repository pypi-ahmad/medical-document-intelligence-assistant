# Architecture Guide

## What
Modular monolith architecture with explicit domain boundaries and LangGraph orchestration.

## Why
Single-repo development speed with strong separation of concerns and production maintainability.

## How

- **API layer**: FastAPI routers (`auth`, `documents`, `medical`)
- **Domain services**: OCR, extraction, retrieval, QA, summaries, timeline, reports, memory
- **Agent orchestration**: LangGraph supervisor with specialized agents
  - OCR Agent
  - Medical Entity Agent
  - Timeline Agent
  - Retrieval Agent
  - Medical QA Agent
  - Summarization Agent
  - Report Generation Agent
  - Memory Agent
  - Execution model: sequential stages + conditional branch after OCR + parallel clinical stage (QA/summary/report) + retries
- **Persistence**: SQLAlchemy models + Alembic migrations
- **Storage**: Encrypted local file storage
- **Models**: Local Ollama via policy-based model router
- **Observability**: OpenTelemetry + Prometheus + Grafana + Loki

## Design Decisions
- LangGraph for deterministic branching/retry/traceability.
- Dual OCR strategy for semantic quality + confidence/layout fields.
- Hybrid retrieval to balance recall and precision.
- Strict safety guardrails for medical-risk prompts.

## Alternatives Considered
- Microservices rejected (higher ops overhead for single-machine target).
- LLM-only extraction rejected (lower determinism + higher hallucination risk).

## Best Practices
- Keep prompts versioned and deterministic.
- Persist citations/provenance with all generated outputs.
- Separate extracted evidence from educational context in responses.
