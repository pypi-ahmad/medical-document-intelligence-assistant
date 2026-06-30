"""Hybrid retrieval over locally indexed medical document chunks."""

from __future__ import annotations

import datetime
import math
import time
from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db_models import Document
from app.models.medical_db_models import DocumentChunk
from app.services.infrastructure.model_router import ModelRouter
from app.services.infrastructure.ollama_client import OllamaClient, OllamaError


@dataclass(slots=True)
class SearchHit:
    chunk: DocumentChunk
    document_name: str
    semantic_score: float
    keyword_score: float
    final_score: float


class HybridRetriever:
    def __init__(self, ollama_client: OllamaClient | None = None, router: ModelRouter | None = None) -> None:
        self.ollama = ollama_client or OllamaClient(timeout_seconds=15.0)
        self.router = router or ModelRouter(self.ollama)

    async def embed_text(self, text: str) -> list[float] | None:
        route = await self.router.route("embedding")
        try:
            return await self.ollama.embed(model=route.selected_model, text=text)
        except OllamaError:
            return None

    async def index_chunks(self, db: AsyncSession, document_id: str, chunks: list[dict]) -> int:
        for item in chunks:
            embedding = await self.embed_text(item["text_content"])
            db.add(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=item["chunk_index"],
                    page_number=item["page_number"],
                    section_name=item.get("section_name"),
                    text_content=item["text_content"],
                    keyword_blob=item.get("keyword_blob", ""),
                    embedding=embedding,
                    token_count=item.get("token_count"),
                    metadata_json=item.get("metadata_json", {}),
                )
            )
        await db.flush()
        return len(chunks)

    async def search(
        self,
        db: AsyncSession,
        *,
        query: str,
        top_k: int,
        document_ids: list[str] | None = None,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
        filters: dict | None = None,
    ) -> tuple[list[SearchHit], int, dict[str, int | bool | float | str | list[str]]]:
        started = time.perf_counter()
        query_embedding = await self.embed_text(query)
        query_tokens = _token_set(query)

        stmt: Select[tuple[DocumentChunk, Document]] = select(DocumentChunk, Document).join(
            Document, DocumentChunk.document_id == Document.id
        )
        if document_ids:
            stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))

        rows = (await db.execute(stmt)).all()
        hits: list[SearchHit] = []
        filtered_rows = 0
        discarded_by_score = 0
        filters_applied = _describe_filters(
            document_ids=document_ids,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
        )
        min_score = _extract_min_score(filters)

        for chunk, doc in rows:
            if not _passes_filters(
                chunk=chunk,
                start_date=start_date,
                end_date=end_date,
                filters=filters,
                query=query,
            ):
                continue
            filtered_rows += 1
            semantic_score = _cosine(query_embedding, chunk.embedding) if query_embedding else 0.0
            keyword_score = _keyword_overlap(query_tokens, _token_set(chunk.keyword_blob), chunk.text_content)
            final_score = (
                settings.hybrid_semantic_weight * semantic_score
                + settings.hybrid_keyword_weight * keyword_score
            )
            if final_score <= max(0.0, min_score):
                discarded_by_score += 1
                continue
            hits.append(
                SearchHit(
                    chunk=chunk,
                    document_name=doc.original_filename,
                    semantic_score=semantic_score,
                    keyword_score=keyword_score,
                    final_score=final_score,
                )
            )

        hits.sort(key=lambda item: item.final_score, reverse=True)
        took_ms = int((time.perf_counter() - started) * 1000)
        diagnostics: dict[str, int | bool | float | str | list[str]] = {
            "total_chunks_scanned": len(rows),
            "chunks_after_filters": filtered_rows,
            "chunks_discarded_by_score": discarded_by_score,
            "query_embedding_available": bool(query_embedding),
            "applied_filters": filters_applied,
            "semantic_weight": settings.hybrid_semantic_weight,
            "keyword_weight": settings.hybrid_keyword_weight,
        }
        return hits[:top_k], took_ms, diagnostics


def _token_set(text: str) -> set[str]:
    return {token.lower() for token in text.split() if token.strip()}


def _keyword_overlap(query_tokens: set[str], chunk_tokens: set[str], chunk_text: str) -> float:
    if not query_tokens or not chunk_tokens:
        return 0.0
    intersection = len(query_tokens.intersection(chunk_tokens))
    jaccard = intersection / max(len(query_tokens.union(chunk_tokens)), 1)
    coverage = intersection / max(len(query_tokens), 1)
    phrase_bonus = 0.08 if " ".join(sorted(query_tokens))[:32] in chunk_text.lower() else 0.0
    return min(1.0, (0.6 * coverage) + (0.4 * jaccard) + phrase_bonus)


def _cosine(a: list[float] | None, b: list[float] | None) -> float:
    if a is None or b is None or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _describe_filters(
    *,
    document_ids: list[str] | None,
    start_date: datetime.date | None,
    end_date: datetime.date | None,
    filters: dict | None,
) -> list[str]:
    labels: list[str] = []
    if document_ids:
        labels.append("document_ids")
    if start_date is not None:
        labels.append("start_date")
    if end_date is not None:
        labels.append("end_date")
    if not isinstance(filters, dict):
        return labels
    if filters.get("page_numbers"):
        labels.append("page_numbers")
    if filters.get("section_names"):
        labels.append("section_names")
    if filters.get("must_contain"):
        labels.append("must_contain")
    if filters.get("metadata"):
        labels.append("metadata")
    if filters.get("min_score") is not None:
        labels.append("min_score")
    return labels


def _extract_min_score(filters: dict | None) -> float:
    if not isinstance(filters, dict):
        return 0.0
    value = filters.get("min_score")
    if value is None:
        return 0.0
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return 0.0


def _passes_filters(
    *,
    chunk: DocumentChunk,
    start_date: datetime.date | None,
    end_date: datetime.date | None,
    filters: dict | None,
    query: str,
) -> bool:
    metadata = chunk.metadata_json if isinstance(chunk.metadata_json, dict) else {}
    if not _passes_date_filter(metadata, start_date=start_date, end_date=end_date):
        return False
    if not isinstance(filters, dict):
        return True

    page_numbers = filters.get("page_numbers")
    if isinstance(page_numbers, list):
        normalized_pages = {int(value) for value in page_numbers if isinstance(value, int)}
        if normalized_pages and (chunk.page_number not in normalized_pages):
            return False

    section_names = filters.get("section_names")
    if isinstance(section_names, list):
        normalized_sections = {
            str(value).strip().lower() for value in section_names if str(value).strip()
        }
        section = (chunk.section_name or "").strip().lower()
        if normalized_sections and section not in normalized_sections:
            return False

    must_contain = filters.get("must_contain")
    if isinstance(must_contain, list):
        haystack = chunk.text_content.lower()
        if not all(str(needle).strip().lower() in haystack for needle in must_contain):
            return False

    metadata_filter = filters.get("metadata")
    if isinstance(metadata_filter, dict):
        for key, expected in metadata_filter.items():
            actual = metadata.get(str(key))
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False

    query_terms = filters.get("query_terms_match")
    if isinstance(query_terms, bool) and query_terms:
        query_tokens = _token_set(query)
        chunk_tokens = _token_set(chunk.keyword_blob)
        if not query_tokens.intersection(chunk_tokens):
            return False

    return True


def _passes_date_filter(
    metadata: dict,
    *,
    start_date: datetime.date | None,
    end_date: datetime.date | None,
) -> bool:
    if start_date is None and end_date is None:
        return True

    date_min = _parse_iso_date(metadata.get("date_min"))
    date_max = _parse_iso_date(metadata.get("date_max"))
    if date_min is None or date_max is None:
        return False
    if start_date is not None and date_max < start_date:
        return False
    return not (end_date is not None and date_min > end_date)


def _parse_iso_date(value: object) -> datetime.date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None
