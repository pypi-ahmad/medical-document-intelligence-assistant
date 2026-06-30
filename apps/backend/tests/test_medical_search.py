from __future__ import annotations

import datetime

import pytest

from app.models.db_models import Document
from app.models.medical_db_models import DocumentChunk
from app.services.medical.retrieval import HybridRetriever
from tests.conftest import _test_session_maker


@pytest.mark.asyncio
async def test_hybrid_retriever_applies_date_and_metadata_filters(monkeypatch) -> None:
    async with _test_session_maker() as db:
        document = Document(
            filename="lab-report.pdf",
            original_filename="lab-report.pdf",
            file_path="/tmp/lab-report.pdf",
            file_type="pdf",
            file_size=1024,
        )
        db.add(document)
        await db.flush()

        db.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=0,
                    page_number=1,
                    section_name="Labs",
                    text_content="Hemoglobin 11.2 g/dL in January 2026.",
                    keyword_blob="hemoglobin january 2026",
                    embedding=None,
                    token_count=6,
                    metadata_json={
                        "page_number": 1,
                        "section_name": "Labs",
                        "date_min": "2026-01-10",
                        "date_max": "2026-01-10",
                    },
                ),
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=1,
                    page_number=2,
                    section_name="General",
                    text_content="Invoice generated in 2024.",
                    keyword_blob="invoice generated 2024",
                    embedding=None,
                    token_count=4,
                    metadata_json={
                        "page_number": 2,
                        "section_name": "General",
                        "date_min": "2024-08-01",
                        "date_max": "2024-08-01",
                    },
                ),
            ]
        )
        await db.flush()

        retriever = HybridRetriever()

        async def _fake_embed(_text: str) -> list[float] | None:
            return None

        monkeypatch.setattr(retriever, "embed_text", _fake_embed)

        hits, _, diagnostics = await retriever.search(
            db,
            query="hemoglobin",
            top_k=10,
            document_ids=[document.id],
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
            filters={"section_names": ["labs"], "page_numbers": [1]},
        )

    assert len(hits) == 1
    assert hits[0].chunk.page_number == 1
    assert hits[0].chunk.section_name == "Labs"
    assert diagnostics["chunks_after_filters"] == 1
    assert diagnostics["total_chunks_scanned"] == 2
    assert diagnostics["query_embedding_available"] is False


@pytest.mark.asyncio
async def test_search_endpoint_returns_filter_echo_and_diagnostics(client, monkeypatch) -> None:
    async def _fake_search(
        db,
        *,
        query: str,
        top_k: int,
        document_ids: list[str] | None = None,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
        filters: dict | None = None,
    ):
        assert query == "lab changes"
        assert top_k == 4
        assert document_ids == ["doc-1"]
        assert start_date == datetime.date(2026, 1, 1)
        assert end_date == datetime.date(2026, 2, 1)
        assert filters == {"min_score": 0.2}
        return [], 12, {"applied_filters": ["document_ids", "start_date", "end_date", "min_score"]}

    monkeypatch.setattr("app.routers.medical._retriever.search", _fake_search)

    response = await client.post(
        "/api/search",
        json={
            "query": "lab changes",
            "top_k": 4,
            "document_ids": ["doc-1"],
            "start_date": "2026-01-01",
            "end_date": "2026-02-01",
            "filters": {"min_score": 0.2},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"] == []
    assert payload["took_ms"] == 12
    assert payload["filters_applied"]["document_ids"] == ["doc-1"]
    assert payload["filters_applied"]["start_date"] == "2026-01-01"
    assert payload["filters_applied"]["end_date"] == "2026-02-01"
    assert payload["filters_applied"]["filters"] == {"min_score": 0.2}
    assert payload["diagnostics"]["applied_filters"] == [
        "document_ids",
        "start_date",
        "end_date",
        "min_score",
    ]
