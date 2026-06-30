"""Section-aware chunking for OCR pages."""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass

from dateutil import parser as date_parser

from app.services.ocr.base import OCRPageResult

_HEADING_RE = re.compile(r"^(?:[A-Z][A-Z\s\-]{2,}|\d+\.\s+[A-Z].+)$")
_DATE_PATTERN = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class ChunkRecord:
    chunk_index: int
    page_number: int
    section_name: str | None
    text_content: str
    keyword_blob: str
    token_count: int
    metadata_json: dict[str, str | int | list[str]]


def chunk_pages(pages: list[OCRPageResult], target_words: int = 180, overlap_words: int = 30) -> list[ChunkRecord]:
    """Chunk OCR pages preserving sections and page traceability."""
    chunks: list[ChunkRecord] = []
    chunk_index = 0

    for page in pages:
        section = "General"
        buffer_words: list[str] = []
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]

        for line in lines:
            if _HEADING_RE.match(line):
                if buffer_words:
                    text = " ".join(buffer_words)
                    metadata = _build_metadata(
                        text=text,
                        page_number=page.page_index + 1,
                        section_name=section,
                    )
                    chunks.append(
                        ChunkRecord(
                            chunk_index=chunk_index,
                            page_number=page.page_index + 1,
                            section_name=section,
                            text_content=text,
                            keyword_blob=_keywords(text),
                            token_count=len(buffer_words),
                            metadata_json=metadata,
                        )
                    )
                    chunk_index += 1
                    buffer_words = buffer_words[-overlap_words:]
                section = line.title()
                continue

            words = line.split()
            if not words:
                continue
            buffer_words.extend(words)

            while len(buffer_words) >= target_words:
                text = " ".join(buffer_words[:target_words])
                metadata = _build_metadata(
                    text=text,
                    page_number=page.page_index + 1,
                    section_name=section,
                )
                chunks.append(
                    ChunkRecord(
                        chunk_index=chunk_index,
                        page_number=page.page_index + 1,
                        section_name=section,
                        text_content=text,
                        keyword_blob=_keywords(text),
                        token_count=target_words,
                        metadata_json=metadata,
                    )
                )
                chunk_index += 1
                buffer_words = buffer_words[target_words - overlap_words :]

        if buffer_words:
            text = " ".join(buffer_words)
            metadata = _build_metadata(
                text=text,
                page_number=page.page_index + 1,
                section_name=section,
            )
            chunks.append(
                ChunkRecord(
                    chunk_index=chunk_index,
                    page_number=page.page_index + 1,
                    section_name=section,
                    text_content=text,
                    keyword_blob=_keywords(text),
                    token_count=len(buffer_words),
                    metadata_json=metadata,
                )
            )
            chunk_index += 1

    return chunks


def _keywords(text: str) -> str:
    tokens = [token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text)]
    # keep deterministic order while deduplicating
    seen: set[str] = set()
    ordered = [token for token in tokens if not (token in seen or seen.add(token))]
    return " ".join(ordered[:80])


def _build_metadata(text: str, page_number: int, section_name: str | None) -> dict[str, str | int | list[str]]:
    metadata: dict[str, str | int | list[str]] = {
        "page_number": page_number,
        "section_name": section_name or "",
    }
    date_values = _extract_dates(text)
    if date_values:
        metadata["detected_dates"] = [value.isoformat() for value in date_values[:8]]
        metadata["date_min"] = date_values[0].isoformat()
        metadata["date_max"] = date_values[-1].isoformat()
    return metadata


def _extract_dates(text: str) -> list[datetime.date]:
    dates: set[datetime.date] = set()
    for token in _DATE_PATTERN.findall(text):
        try:
            parsed = date_parser.parse(token, fuzzy=False)
        except (ValueError, OverflowError):
            continue
        dates.add(parsed.date())
    return sorted(dates)
