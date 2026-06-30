# OCR Guide

## What
Dual OCR pipeline:
- Primary: `glm-ocr:latest` (semantic transcription, supports image + scanned PDF via page rasterization)
- Secondary: PaddleOCR (images) or PyMuPDF (PDF) for layout blocks, confidence, and table/region metadata

## Why
GLM OCR gives robust semantic extraction for noisy medical scans. Secondary OCR improves confidence and layout fidelity.

## How
1. Upload file.
2. Validate MIME/extension.
3. Decrypt-at-use to temporary file for OCR.
4. Run primary OCR.
5. For PDF input, rasterize each page then OCR page-by-page with GLM.
6. Optional secondary OCR/layout parser selected by file type.
7. Merge page text + block/table/confidence metadata.
8. Persist into `ocr_pages`.

## Design Decision
- OCR providers abstracted behind `BaseOCRProvider`.
- Deterministic provider registry with auto routing.

## Alternatives Considered
- Single OCR provider rejected (confidence/layout requirements not consistently met).

## Best Practices
- Keep `temperature=0` for OCR prompting.
- Track OCR latency and page-level confidence.
- Keep raw OCR traces for audit/debug.
