from __future__ import annotations

import pytest

from app.config import settings
from app.services.medical.qa import QAContext


@pytest.mark.asyncio
async def test_qa_stream_emits_sse_events(client, monkeypatch) -> None:
    original_auth = settings.enable_auth
    settings.enable_auth = False
    try:
        async def _fake_build_context(db, *, question: str, document_ids: list[str], top_k: int):
            return QAContext(
                prompt="prompt",
                system="system",
                model="qwen3.5:4b",
                citations=[
                    {
                        "document_id": "doc-1",
                        "document_name": "report.pdf",
                        "page_number": 1,
                        "chunk_id": "chunk-1",
                        "evidence_text": "Hemoglobin: 11.2 g/dL",
                    }
                ],
                extracted_context="Hemoglobin: 11.2 g/dL",
                educational_context="General explanation",
            )

        async def _fake_stream(*, model: str, prompt: str, system: str, options: dict):
            yield "Extracted Information From Uploaded Documents:\nHemoglobin 11.2 g/dL.\n\n"
            yield "Educational Background Information:\nRange interpretation varies by lab."

        monkeypatch.setattr("app.routers.medical._qa.build_context", _fake_build_context)
        monkeypatch.setattr("app.routers.medical._ollama.generate_stream", _fake_stream)

        response = await client.post(
            "/api/qa/query/stream",
            json={
                "question": "What labs are outside range?",
                "document_ids": [],
                "top_k": 5,
            },
        )
        assert response.status_code == 200
        body = response.text
        assert "event: session" in body
        assert "event: token" in body
        assert "event: done" in body
        assert "Disclaimer:" in body
    finally:
        settings.enable_auth = original_auth


@pytest.mark.asyncio
async def test_qa_stream_blocked_question_returns_guardrail(client) -> None:
    original_auth = settings.enable_auth
    settings.enable_auth = False
    try:
        response = await client.post(
            "/api/qa/query/stream",
            json={
                "question": "Can you diagnose me from this report?",
                "document_ids": [],
                "top_k": 5,
            },
        )
        assert response.status_code == 200
        body = response.text
        assert "event: session" in body
        assert "\"model\": \"guardrail\"" in body
        assert "cannot provide diagnosis" in body.lower()
    finally:
        settings.enable_auth = original_auth
