# RAG Guide

## What
Hybrid retrieval and grounded generation over uploaded medical documents.

## Why
Balances semantic recall with exact keyword precision and keeps answers evidence-grounded.

## How
- Section-aware chunking with page/section metadata
- Embeddings via local Ollama embedding model
- Hybrid scoring: semantic cosine + keyword overlap
- Top-k context to QA/summarization/report prompts
- Citation payload includes document, page, chunk, evidence text

## Design Decision
Weighted hybrid retrieval with configurable semantic/keyword weights.

## Alternatives Considered
- Vector-only rejected (weak exact match behavior)
- Keyword-only rejected (weak semantic recall)

## Best Practices
- Re-index incrementally after reprocessing docs.
- Keep chunk sizes moderate to avoid context dilution.
- Always return abstention when evidence insufficient.
