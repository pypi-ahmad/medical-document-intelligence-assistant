# Performance Guide

## What to Measure
- OCR latency per page
- Retrieval latency (`/search`, `/qa/query`)
- End-to-end processing time per document
- GPU memory and utilization
- Agent run durations

## Optimization Levers
- Smaller generation models for interactive chat
- Tune chunk size/overlap
- Tune `top_k`
- Pre-warm Ollama models
- Use batched re-index jobs for large uploads

## Observability
Use Prometheus + Grafana dashboards and inspect `/api/system/health`.
