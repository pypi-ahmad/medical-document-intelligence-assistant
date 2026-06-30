# Medical Entity Extraction Guide

## What
Extracts patient-relevant entities from OCR text:
- diagnoses/symptoms/allergies
- medications (name/dose/frequency/action)
- lab tests/values/units/reference-ranges
- provider/hospital mentions
- date anchors for timeline

## Why
Structured entities drive timeline, retrieval filters, reports, and medication/lab views.

## How
- Rule + regex extraction over per-page OCR text
- Terminology normalization map for common aliases
- Out-of-range lab detection from explicit report ranges
- Persist to `medical_entities`, `lab_results`, `medication_history`, `timeline_events`

## Design Decision
Hybrid deterministic extraction in v1 for reliability and traceability.

## Alternatives Considered
LLM-only extraction rejected for inconsistency and evidence drift in sensitive domains.

## Best Practices
- Keep extraction line-aware to reduce cross-line false positives.
- Store page provenance for every entity.
- Keep normalization dictionary versioned.
