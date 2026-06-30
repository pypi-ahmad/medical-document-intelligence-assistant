# FAQ

## Is this a medical diagnosis system?
No. Educational use only. It does not diagnose, prescribe, or recommend treatment.

## Can it work fully offline?
Core flow is local-first. External calls are disabled by default.

## Why local Ollama?
Privacy-first deployment and predictable control over models.

## Which files are supported?
PDF, PNG, JPG/JPEG, TIFF/TIF (including scanned/handwritten best-effort OCR).

## How are answers grounded?
Hybrid retrieval over indexed chunks with document/page citations.

## Can I clear stored memory?
Yes. Use Memory page or `DELETE /api/memory`.
