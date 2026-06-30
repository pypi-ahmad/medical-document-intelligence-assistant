from __future__ import annotations

import pytest

from app.models.db_models import Document
from app.models.medical_db_models import User
from app.security.auth import hash_password
from app.services.infrastructure.model_router import RouteDecision
from app.services.medical.agents import MedicalSupervisor
from app.services.ocr.base import OCRPageResult, OCRResult
from tests.conftest import _test_session_maker


@pytest.mark.asyncio
async def test_medical_supervisor_runs_required_agent_nodes(tmp_path, monkeypatch) -> None:
    file_path = tmp_path / "doc.png"
    file_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    class _DummyOCRProvider:
        provider_id = "glmocr"

        async def extract_text(self, file_path):
            return OCRResult(
                text="Visit Date: 2026-03-01\nDiagnosis: Hypertension\nMetformin 500 mg BID",
                pages=["Visit Date: 2026-03-01"],
                provider="glmocr",
                page_results=[
                    OCRPageResult(
                        page_index=0,
                        text="Visit Date: 2026-03-01\nDiagnosis: Hypertension\nMetformin 500 mg BID",
                        confidence=0.9,
                    )
                ],
            )

    monkeypatch.setattr(
        "app.services.medical.agents.get_ocr_provider",
        lambda provider_id, *, file_path=None: _DummyOCRProvider(),
    )

    async def _fake_route(self, task: str) -> RouteDecision:
        return RouteDecision(
            task=task,
            selected_model="qwen3.5:4b",
            candidates=["qwen3.5:4b"],
            reason="test",
            gpu_available=False,
        )

    monkeypatch.setattr("app.services.medical.agents.ModelRouter.route", _fake_route)

    async with _test_session_maker() as db:
        user = User(
            email="agent-test@local",
            full_name="Agent Test",
            password_hash=hash_password("AgentTestPassword123!"),
            is_admin=True,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        document = Document(
            filename="doc.png",
            original_filename="doc.png",
            file_path=str(file_path),
            file_type="png",
            file_size=file_path.stat().st_size,
        )
        db.add(document)
        await db.flush()

        supervisor = MedicalSupervisor()
        state = await supervisor.execute(
            db,
            user=user,
            document_id=document.id,
            run_id="run-test-1",
        )

    assert state["status"] == "completed"
    agent_names = [entry["agent"] for entry in state.get("trace", [])]
    for required in [
        "OCR Agent",
        "Medical Entity Agent",
        "Timeline Agent",
        "Retrieval Agent",
        "Medical QA Agent",
        "Summarization Agent",
        "Report Generation Agent",
        "Memory Agent",
    ]:
        assert required in agent_names
