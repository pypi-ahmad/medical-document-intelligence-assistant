"""Medical assistant API endpoints."""

from __future__ import annotations

import datetime
import json
import os

import psutil
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.medical_db_models import (
    AgentRun,
    GeneratedReport,
    LabResult,
    MedicalEntity,
    MedicationHistory,
    OCRPage,
    SystemSetting,
)
from app.models.medical_schemas import (
    AgentRunOut,
    DoctorReportExport,
    MemoryClearResponse,
    MemoryCreateRequest,
    MemoryItem,
    ModelConfigResponse,
    ModelConfigUpdateRequest,
    ProcessDocumentResponse,
    QARequest,
    QAResponse,
    ReportRequest,
    ReportResponse,
    SearchRequest,
    SearchResponse,
    SummaryRequest,
    SummaryResponse,
    SystemHealthResponse,
    TimelineEventOut,
    TimelineRequest,
    TimelineResponse,
)
from app.security.auth import get_current_user
from app.services.infrastructure.gpu_monitor import probe_gpu
from app.services.infrastructure.model_router import ModelRouter
from app.services.infrastructure.ollama_client import OllamaClient
from app.services.medical.memory import MemoryService
from app.services.medical.pipeline import MedicalPipelineService
from app.services.medical.qa import MedicalQAService
from app.services.medical.reporting import ReportService
from app.services.medical.retrieval import HybridRetriever
from app.services.medical.safety import (
    append_disclaimer,
    blocked_response_text,
    build_safety_envelope,
    is_prohibited_medical_request,
)
from app.services.medical.summarization import SummaryService
from app.services.medical.timeline import TimelineService

router = APIRouter(prefix="/api", tags=["Medical Assistant"])

_pipeline = MedicalPipelineService()
_retriever = HybridRetriever()
_qa = MedicalQAService(retriever=_retriever)
_summary = SummaryService()
_timeline = TimelineService()
_reports = ReportService()
_memory = MemoryService()
_ollama = OllamaClient()
_router = ModelRouter(_ollama)


@router.post("/medical/process/{document_id}", response_model=ProcessDocumentResponse)
async def process_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> ProcessDocumentResponse:
    try:
        payload = await _pipeline.process_document(db, user=user, document_id=document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ProcessDocumentResponse(**payload)


@router.get("/medical/documents/{document_id}/ocr", response_model=list[dict])
async def get_ocr_pages(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[dict]:
    pages = list(
        (
            await db.execute(
                select(OCRPage).where(OCRPage.document_id == document_id).order_by(OCRPage.page_number)
            )
        ).scalars()
    )
    return [
        {
            "page_number": page.page_number,
            "text": page.page_text,
            "confidence": page.confidence,
            "layout_json": page.layout_json,
            "provider": page.provider,
        }
        for page in pages
    ]


@router.get("/medical/documents/{document_id}/entities", response_model=list[dict])
async def get_entities(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[dict]:
    rows = list(
        (
            await db.execute(
                select(MedicalEntity)
                .where(MedicalEntity.document_id == document_id)
                .order_by(MedicalEntity.entity_type, MedicalEntity.id)
            )
        ).scalars()
    )
    return [
        {
            "id": row.id,
            "entity_type": row.entity_type,
            "raw_value": row.raw_value,
            "normalized_value": row.normalized_value,
            "attributes": row.attributes_json,
            "page_number": row.page_number,
            "confidence": row.confidence,
        }
        for row in rows
    ]


@router.get("/medical/documents/{document_id}/labs", response_model=list[dict])
async def get_labs(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[dict]:
    rows = list(
        (
            await db.execute(
                select(LabResult).where(LabResult.document_id == document_id).order_by(LabResult.id)
            )
        ).scalars()
    )
    return [
        {
            "test_name": row.test_name,
            "value_text": row.value_text,
            "unit": row.unit,
            "reference_range": row.reference_range,
            "is_out_of_range": row.is_out_of_range,
            "event_date": row.event_date,
            "page_number": row.page_number,
        }
        for row in rows
    ]


@router.get("/medical/documents/{document_id}/medications", response_model=list[dict])
async def get_medications(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[dict]:
    rows = list(
        (
            await db.execute(
                select(MedicationHistory)
                .where(MedicationHistory.document_id == document_id)
                .order_by(MedicationHistory.id)
            )
        ).scalars()
    )
    return [
        {
            "medication_name": row.medication_name,
            "dosage": row.dosage,
            "frequency": row.frequency,
            "action": row.action,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "page_number": row.page_number,
        }
        for row in rows
    ]


@router.post("/search", response_model=SearchResponse)
async def hybrid_search(
    payload: SearchRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> SearchResponse:
    hits, took_ms, diagnostics = await _retriever.search(
        db,
        query=payload.query,
        top_k=payload.top_k,
        document_ids=payload.document_ids,
        start_date=payload.start_date,
        end_date=payload.end_date,
        filters=payload.filters,
    )
    return SearchResponse(
        query=payload.query,
        took_ms=took_ms,
        filters_applied={
            "document_ids": payload.document_ids,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "filters": payload.filters,
        },
        diagnostics=diagnostics,
        results=[
            {
                "chunk_id": hit.chunk.id,
                "document_id": hit.chunk.document_id,
                "document_name": hit.document_name,
                "page_number": hit.chunk.page_number,
                "score": hit.final_score,
                "keyword_score": hit.keyword_score,
                "semantic_score": hit.semantic_score,
                "text": hit.chunk.text_content,
                "metadata": hit.chunk.metadata_json,
            }
            for hit in hits
        ],
    )


@router.post("/qa/query", response_model=QAResponse)
async def question_answering(
    payload: QARequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> QAResponse:
    result = await _qa.answer(
        db,
        user=user,
        question=payload.question,
        session_id=payload.session_id,
        document_ids=payload.document_ids,
        top_k=payload.top_k,
    )
    return QAResponse(
        session_id=result.session_id,
        answer=result.answer,
        extracted_information=result.extracted_information,
        educational_background=result.educational_background,
        citations=result.citations,
        safety=build_safety_envelope(),
        model=result.model,
    )


@router.post("/qa/query/stream")
async def question_answering_stream(
    payload: QARequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> StreamingResponse:
    session = await _qa.ensure_session(
        db,
        user=user,
        session_id=payload.session_id,
        question=payload.question,
    )
    safety = build_safety_envelope().model_dump()

    if is_prohibited_medical_request(payload.question):
        blocked = blocked_response_text()
        await _qa.store_message(db, session.id, "user", payload.question, [])
        await _qa.store_message(db, session.id, "assistant", blocked, [])

        async def blocked_stream():
            yield _sse_event("session", {"session_id": session.id, "model": "guardrail"})
            yield _sse_event("token", {"text": blocked})
            yield _sse_event(
                "done",
                {
                    "session_id": session.id,
                    "answer": blocked,
                    "citations": [],
                    "model": "guardrail",
                    "safety": safety,
                },
            )

        return StreamingResponse(blocked_stream(), media_type="text/event-stream")

    context = await _qa.build_context(
        db,
        question=payload.question,
        document_ids=payload.document_ids,
        top_k=payload.top_k,
    )

    await _qa.store_message(db, session.id, "user", payload.question, [])

    async def event_stream():
        yield _sse_event("session", {"session_id": session.id, "model": context.model})
        chunks: list[str] = []
        answer_text = ""
        try:
            async for token in _ollama.generate_stream(
                model=context.model,
                prompt=context.prompt,
                system=context.system,
                options={"temperature": 0.1},
            ):
                chunks.append(token)
                yield _sse_event("token", {"text": token})
            answer_text = append_disclaimer("".join(chunks).strip())
        except Exception:
            fallback = (
                "Extracted Information From Uploaded Documents:\n"
                "Evidence could not be streamed from selected model.\n\n"
                "Educational Background Information:\n"
                "Use uploaded citations and verify with qualified clinician."
            )
            answer_text = append_disclaimer(fallback)
            yield _sse_event("token", {"text": answer_text})

        await _qa.store_message(db, session.id, "assistant", answer_text, context.citations)
        yield _sse_event(
            "done",
            {
                "session_id": session.id,
                "answer": answer_text,
                "citations": context.citations,
                "model": context.model,
                "safety": safety,
            },
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/summaries", response_model=SummaryResponse)
async def generate_summary(
    payload: SummaryRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> SummaryResponse:
    content, model_used = await _summary.summarize(
        db,
        document_ids=payload.document_ids,
        summary_type=payload.summary_type,
        length=payload.length,
    )

    hits, _, _ = await _retriever.search(
        db,
        query=f"{payload.summary_type} summary",
        top_k=4,
        document_ids=payload.document_ids,
    )
    citations = [
        {
            "document_id": hit.chunk.document_id,
            "document_name": hit.document_name,
            "page_number": hit.chunk.page_number,
            "chunk_id": hit.chunk.id,
            "evidence_text": hit.chunk.text_content[:300],
        }
        for hit in hits
    ]

    return SummaryResponse(
        summary_type=payload.summary_type,
        length=payload.length,
        content=f"{content}\n\nModel used: {model_used}",
        citations=citations,
        safety=build_safety_envelope(),
    )


@router.post("/timelines", response_model=TimelineResponse)
async def timeline(
    payload: TimelineRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> TimelineResponse:
    events = await _timeline.list_events(
        db,
        document_ids=payload.document_ids,
        event_types=payload.event_types,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    return TimelineResponse(
        events=[
            TimelineEventOut(
                id=event.id,
                document_id=event.document_id,
                event_type=event.event_type,
                event_date=event.event_date,
                title=event.title,
                description=event.description,
                metadata=event.metadata_json,
                page_number=event.page_number,
            )
            for event in events
        ],
        filters_applied={
            "document_ids": payload.document_ids,
            "event_types": payload.event_types,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
        },
    )


@router.post("/reports/generate", response_model=ReportResponse)
async def generate_report(
    payload: ReportRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> ReportResponse:
    report = await _reports.generate_doctor_visit_report(
        db,
        user=user,
        document_ids=payload.document_ids,
        title=payload.title,
    )
    return ReportResponse(
        report_id=report.id,
        title=report.title,
        markdown=report.markdown_body,
        html=report.html_body,
        json_payload=report.json_payload,
        available_formats=settings.report_export_format_list,
        safety=build_safety_envelope(),
    )


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> ReportResponse:
    report = await db.get(GeneratedReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse(
        report_id=report.id,
        title=report.title,
        markdown=report.markdown_body,
        html=report.html_body,
        json_payload=report.json_payload,
        available_formats=settings.report_export_format_list,
        safety=build_safety_envelope(),
    )


@router.get("/reports/{report_id}/export", response_model=DoctorReportExport)
async def export_report(
    report_id: str,
    format: str = Query(default="markdown"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> DoctorReportExport:
    try:
        content = await _reports.export_report_content(db, report_id=report_id, fmt=format)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DoctorReportExport(report_id=report_id, format=format.lower(), content=content)


@router.post("/memory", response_model=MemoryItem)
async def create_memory(
    payload: MemoryCreateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> MemoryItem:
    entry = await _memory.add_memory(
        db,
        user=user,
        memory_type=payload.memory_type,
        memory_key=payload.memory_key,
        memory_value=payload.memory_value,
        ttl_days=payload.ttl_days,
    )
    return MemoryItem(
        id=entry.id,
        memory_type=entry.memory_type,
        memory_key=entry.memory_key,
        memory_value=entry.memory_value,
        expires_at=entry.expires_at,
        created_at=entry.created_at,
    )


@router.get("/memory", response_model=list[MemoryItem])
async def list_memory(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> list[MemoryItem]:
    items = await _memory.list_memory(db, user=user)
    return [
        MemoryItem(
            id=item.id,
            memory_type=item.memory_type,
            memory_key=item.memory_key,
            memory_value=item.memory_value,
            expires_at=item.expires_at,
            created_at=item.created_at,
        )
        for item in items
    ]


@router.delete("/memory", response_model=MemoryClearResponse)
async def clear_memory(
    memory_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> MemoryClearResponse:
    deleted = await _memory.clear_memory(db, user=user, memory_type=memory_type)
    return MemoryClearResponse(deleted=deleted)


@router.get("/agents/runs", response_model=list[AgentRunOut])
async def agent_runs(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AgentRunOut]:
    rows = list(
        (
            await db.execute(
                select(AgentRun).where(AgentRun.user_id == user.id).order_by(AgentRun.started_at.desc()).limit(limit)
            )
        ).scalars()
    )
    return [
        AgentRunOut(
            id=row.id,
            workflow=row.workflow,
            status=row.status,
            document_id=row.document_id,
            trace_json=row.trace_json,
            started_at=row.started_at,
            ended_at=row.ended_at,
        )
        for row in rows
    ]


@router.get("/models/config", response_model=ModelConfigResponse)
async def get_model_config(_user=Depends(get_current_user)) -> ModelConfigResponse:
    return ModelConfigResponse(
        default_chat_model=settings.default_chat_model,
        fast_chat_model=settings.fast_chat_model,
        summary_model=settings.summary_model,
        entity_model=settings.entity_model,
        embedding_model=settings.embedding_model,
        translation_model=settings.translation_model,
        fallback_chat_models=settings.fallback_chat_model_list,
    )


@router.patch("/models/config", response_model=ModelConfigResponse)
async def update_model_config(
    payload: ModelConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> ModelConfigResponse:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    update_fields = payload.model_dump(exclude_none=True)
    current = await db.get(SystemSetting, "model_config")
    existing = current.value_json if current else {}
    existing.update(update_fields)

    if current is None:
        db.add(SystemSetting(key="model_config", value_json=existing))
    else:
        current.value_json = existing

    if payload.default_chat_model is not None:
        settings.default_chat_model = payload.default_chat_model
    if payload.fast_chat_model is not None:
        settings.fast_chat_model = payload.fast_chat_model
    if payload.summary_model is not None:
        settings.summary_model = payload.summary_model
    if payload.entity_model is not None:
        settings.entity_model = payload.entity_model
    if payload.embedding_model is not None:
        settings.embedding_model = payload.embedding_model
    if payload.translation_model is not None:
        settings.translation_model = payload.translation_model
    if payload.fallback_chat_models is not None:
        settings.fallback_chat_models = ",".join(payload.fallback_chat_models)

    return ModelConfigResponse(
        default_chat_model=settings.default_chat_model,
        fast_chat_model=settings.fast_chat_model,
        summary_model=settings.summary_model,
        entity_model=settings.entity_model,
        embedding_model=settings.embedding_model,
        translation_model=settings.translation_model,
        fallback_chat_models=settings.fallback_chat_model_list,
    )


@router.get("/system/health", response_model=SystemHealthResponse)
async def system_health(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> SystemHealthResponse:
    gpu_info = probe_gpu()
    try:
        ollama_health = await _ollama.health()
    except Exception as exc:
        ollama_health = {"ok": False, "error": str(exc), "models": []}

    active_runs = (
        await db.execute(
            select(AgentRun).where(AgentRun.user_id == user.id).where(AgentRun.status == "running")
        )
    ).scalars()
    active_count = len(list(active_runs))

    process = psutil.Process(os.getpid())
    return SystemHealthResponse(
        status="ok" if ollama_health.get("ok") else "degraded",
        gpu_available=bool(gpu_info.get("available")),
        gpu_info=gpu_info,
        ollama=ollama_health,
        memory_usage_mb=float(process.memory_info().rss) / (1024 * 1024),
        active_agent_runs=active_count,
    )


@router.get("/medical/disclaimer")
async def disclaimer() -> dict:
    return {
        "disclaimer": settings.medical_disclaimer,
        "updated_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }


def _sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=True)}\n\n"
