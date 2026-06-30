"""LangGraph-based supervisor and specialized medical agents."""

from __future__ import annotations

import asyncio
import datetime
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Document
from app.models.medical_db_models import (
    AgentRun,
    LabResult,
    MedicalEntity,
    MedicationHistory,
    OCRPage,
    TimelineEvent,
    User,
)
from app.services.infrastructure.model_router import ModelRouter, RouteDecision
from app.services.medical.chunking import chunk_pages
from app.services.medical.extraction import ExtractionBundle, extract_entities_from_pages
from app.services.medical.memory import MemoryService
from app.services.medical.retrieval import HybridRetriever
from app.services.ocr.base import OCRPageResult, OCRProviderError
from app.services.ocr.registry import get_ocr_provider


class AgentState(TypedDict, total=False):
    run_id: str
    user_id: str
    document_id: str
    file_path: str
    page_results: list[OCRPageResult]
    entities_bundle: dict[str, Any]
    chunk_records: list[dict[str, Any]]
    retrieval_preview: list[dict[str, Any]]
    timeline_summary: dict[str, Any]
    summary_preview: str
    qa_preview: str
    report_outline: dict[str, Any]
    warnings: list[str]
    routed_models: list[dict[str, Any]]
    indexed_chunks: int
    status: str
    error: str
    trace: list[dict[str, Any]]


class MedicalSupervisor:
    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        memory_service: MemoryService | None = None,
        model_router: ModelRouter | None = None,
    ) -> None:
        self.retriever = retriever or HybridRetriever()
        self.memory_service = memory_service or MemoryService()
        self.router = model_router or ModelRouter()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("ocr_agent", self.ocr_agent)
        graph.add_node("entity_agent", self.entity_agent)
        graph.add_node("timeline_agent", self.timeline_agent)
        graph.add_node("retrieval_agent", self.retrieval_agent)
        graph.add_node("parallel_clinical_agents", self.parallel_clinical_agents)
        graph.add_node("memory_agent", self.memory_agent)

        graph.add_edge(START, "ocr_agent")
        graph.add_conditional_edges(
            "ocr_agent",
            self._after_ocr,
            {"entity_agent": "entity_agent", "END": END},
        )
        graph.add_edge("entity_agent", "timeline_agent")
        graph.add_edge("timeline_agent", "retrieval_agent")
        graph.add_edge("retrieval_agent", "parallel_clinical_agents")
        graph.add_edge("parallel_clinical_agents", "memory_agent")
        graph.add_edge("memory_agent", END)
        return graph.compile()

    async def execute(
        self,
        db: AsyncSession,
        *,
        user: User,
        document_id: str,
        run_id: str,
        file_path_override: str | None = None,
    ) -> AgentState:
        document = await db.get(Document, document_id)
        if document is None:
            raise ValueError("Document not found")

        initial_state: AgentState = {
            "run_id": run_id,
            "user_id": user.id,
            "document_id": document.id,
            "file_path": file_path_override or document.file_path,
            "status": "running",
            "trace": [],
            "routed_models": [],
        }
        final_state = await self.graph.ainvoke(initial_state)
        return final_state

    async def ocr_agent(self, state: AgentState) -> AgentState:
        file_path = Path(state["file_path"])
        primary_decision = await self.router.route("ocr")
        state["routed_models"].append(_route_to_dict(primary_decision))
        state["trace"].append({"agent": "OCR Agent", "status": "running"})

        if not file_path.exists():
            state["status"] = "failed"
            state["error"] = f"File not found: {file_path.name}"
            state["trace"].append({"agent": "OCR Agent", "status": "failed", "error": state["error"]})
            return state

        try:
            provider = get_ocr_provider("glmocr", file_path=file_path)
        except (ValueError, OCRProviderError):
            provider = get_ocr_provider("auto", file_path=file_path)

        try:
            primary_result = await _with_retries(provider.extract_text, file_path, retries=2)
        except OCRProviderError as exc:
            state["status"] = "failed"
            state["error"] = str(exc)
            state["trace"].append({"agent": "OCR Agent", "status": "failed", "error": str(exc)})
            return state

        # Dual OCR path: merge confidence/layout from secondary parser when available.
        # - Images: PaddleOCR enriches layout/boxes.
        # - PDFs: PyMuPDF enriches page structure.
        secondary_pages: dict[int, OCRPageResult] = {}
        secondary_provider_id = "paddleocr"
        if file_path.suffix.lower() == ".pdf":
            secondary_provider_id = "pymupdf"
        try:
            secondary = get_ocr_provider(secondary_provider_id, file_path=file_path)
            secondary_result = await _with_retries(secondary.extract_text, file_path, retries=1)
            secondary_pages = {page.page_index: page for page in secondary_result.page_results}
        except Exception:
            secondary_pages = {}

        merged_pages: list[OCRPageResult] = []
        for page in primary_result.page_results:
            secondary_page = secondary_pages.get(page.page_index)
            merged_pages.append(
                OCRPageResult(
                    page_index=page.page_index,
                    text=page.text,
                    blocks=secondary_page.blocks if secondary_page and secondary_page.blocks else page.blocks,
                    tables=secondary_page.tables if secondary_page and secondary_page.tables else page.tables,
                    confidence=(
                        secondary_page.confidence
                        if secondary_page and secondary_page.confidence is not None
                        else page.confidence
                    ),
                )
            )

        state["page_results"] = merged_pages
        state["trace"].append(
            {
                "agent": "OCR Agent",
                "status": "completed",
                "pages": len(merged_pages),
                "provider": provider.provider_id,
                "secondary_provider": secondary_provider_id if secondary_pages else None,
            }
        )
        return state

    async def entity_agent(self, state: AgentState) -> AgentState:
        state["trace"].append({"agent": "Medical Entity Agent", "status": "running"})
        decision = await self.router.route("entity_extraction")
        state["routed_models"].append(_route_to_dict(decision))
        pages = state.get("page_results", [])
        try:
            bundle: ExtractionBundle = await _with_retries(_extract_entities_async, pages, retries=1)
        except Exception as exc:
            state["status"] = "failed"
            state["error"] = f"Entity extraction failed: {exc}"
            state["trace"].append({"agent": "Medical Entity Agent", "status": "failed", "error": str(exc)})
            return state

        state["entities_bundle"] = {
            "entities": bundle.entities,
            "labs": bundle.labs,
            "medications": bundle.medications,
            "timeline_events": bundle.timeline_events,
        }
        state["trace"].append(
            {
                "agent": "Medical Entity Agent",
                "status": "completed",
                "entities": len(bundle.entities),
                "labs": len(bundle.labs),
                "medications": len(bundle.medications),
            }
        )
        return state

    async def timeline_agent(self, state: AgentState) -> AgentState:
        state["trace"].append({"agent": "Timeline Agent", "status": "running"})
        if state.get("status") == "failed":
            state["trace"].append({"agent": "Timeline Agent", "status": "skipped"})
            return state
        if not state.get("page_results"):
            state["status"] = "failed"
            state["error"] = "No OCR pages available for downstream agents"
            state["trace"].append(
                {"agent": "Timeline Agent", "status": "failed", "error": state["error"]}
            )
            return state
        decision = await self.router.route("timeline")
        state["routed_models"].append(_route_to_dict(decision))
        events = state.get("entities_bundle", {}).get("timeline_events", [])
        event_counter = Counter(event.get("event_type", "unknown") for event in events)
        state["timeline_summary"] = {
            "total_events": len(events),
            "event_counts": dict(event_counter),
            "model": decision.selected_model,
        }
        state["trace"].append(
            {
                "agent": "Timeline Agent",
                "status": "completed",
                "events": len(events),
            }
        )
        return state

    async def retrieval_agent(self, state: AgentState) -> AgentState:
        state["trace"].append({"agent": "Retrieval Agent", "status": "running"})
        decision = await self.router.route("embedding")
        state["routed_models"].append(_route_to_dict(decision))
        pages = state.get("page_results", [])
        chunks = [asdict(chunk) for chunk in chunk_pages(pages)]
        state["chunk_records"] = chunks
        state["indexed_chunks"] = len(chunks)
        state["retrieval_preview"] = _retrieval_preview(chunks)
        state["trace"].append(
            {
                "agent": "Retrieval Agent",
                "status": "completed",
                "chunks": len(chunks),
                "model": decision.selected_model,
            }
        )
        return state

    async def parallel_clinical_agents(self, state: AgentState) -> AgentState:
        state["trace"].append({"agent": "Clinical Parallel Stage", "status": "running"})
        runs = await asyncio.gather(
            self._run_parallel_agent(state, "Medical QA Agent", self._qa_patch),
            self._run_parallel_agent(state, "Summarization Agent", self._summary_patch),
            self._run_parallel_agent(state, "Report Generation Agent", self._report_patch),
        )
        failures = 0
        for run in runs:
            state["trace"].append(run["trace"])
            _merge_state_patch(state, run.get("patch", {}))
            if run.get("error"):
                failures += 1

        if failures == len(runs):
            state["status"] = "failed"
            state["error"] = "All clinical parallel agents failed"
            state["trace"].append(
                {
                    "agent": "Clinical Parallel Stage",
                    "status": "failed",
                    "failures": failures,
                }
            )
            return state

        if failures:
            warnings = state.get("warnings", [])
            warnings.append(f"{failures} clinical parallel agent(s) failed")
            state["warnings"] = warnings

        state["trace"].append(
            {
                "agent": "Clinical Parallel Stage",
                "status": "completed",
                "failures": failures,
            }
        )
        return state

    async def memory_agent(self, state: AgentState) -> AgentState:
        state["trace"].append({"agent": "Memory Agent", "status": "running"})
        state["trace"].append(
            {
                "agent": "Memory Agent",
                "status": "completed",
                "captured_keys": [
                    key
                    for key in (
                        "timeline_summary",
                        "summary_preview",
                        "qa_preview",
                        "report_outline",
                        "retrieval_preview",
                    )
                    if key in state
                ],
            }
        )
        state["status"] = "completed"
        return state

    @staticmethod
    def _after_ocr(state: AgentState) -> str:
        if state.get("status") == "failed":
            return "END"
        return "entity_agent"

    async def _run_parallel_agent(self, state: AgentState, agent_name: str, fn) -> dict[str, Any]:
        try:
            patch = await _with_retries(fn, state, retries=1)
            return {
                "trace": {
                    "agent": agent_name,
                    "status": "completed",
                    **patch.get("metrics", {}),
                },
                "patch": patch,
                "error": None,
            }
        except Exception as exc:
            return {
                "trace": {"agent": agent_name, "status": "failed", "error": str(exc)},
                "patch": {},
                "error": str(exc),
            }

    async def _qa_patch(self, state: AgentState) -> dict[str, Any]:
        decision = await self.router.route("qa")
        entities = state.get("entities_bundle", {}).get("entities", [])
        labs = state.get("entities_bundle", {}).get("labs", [])
        medications = state.get("entities_bundle", {}).get("medications", [])
        questions = [
            "Which findings need follow-up with licensed clinician?",
            "Are any medication changes documented over time?",
            "Which lab values are outside stated reference ranges?",
        ]
        if not labs:
            questions = questions[:2]
        qa_preview = (
            "Document-derived quick view:\n"
            f"- Entities extracted: {len(entities)}\n"
            f"- Labs detected: {len(labs)}\n"
            f"- Medications detected: {len(medications)}\n"
            "Questions to discuss with clinician:\n"
            + "\n".join(f"- {question}" for question in questions)
        )
        return {
            "qa_preview": qa_preview,
            "routed_models": [_route_to_dict(decision)],
            "metrics": {"model": decision.selected_model, "questions": len(questions)},
        }

    async def _summary_patch(self, state: AgentState) -> dict[str, Any]:
        decision = await self.router.route("summary")
        timeline_summary = state.get("timeline_summary", {})
        lab_count = len(state.get("entities_bundle", {}).get("labs", []))
        med_count = len(state.get("entities_bundle", {}).get("medications", []))
        event_count = timeline_summary.get("total_events", 0)
        summary = (
            "Educational summary draft: "
            f"{lab_count} lab findings, {med_count} medication mentions, "
            f"{event_count} timeline events."
        )
        return {
            "summary_preview": summary,
            "routed_models": [_route_to_dict(decision)],
            "metrics": {"model": decision.selected_model, "events": event_count},
        }

    async def _report_patch(self, state: AgentState) -> dict[str, Any]:
        decision = await self.router.route("report")
        bundle = state.get("entities_bundle", {})
        outline = {
            "documents_reviewed": 1,
            "medications_mentioned": len(bundle.get("medications", [])),
            "laboratory_findings": len(bundle.get("labs", [])),
            "timeline_events": len(bundle.get("timeline_events", [])),
            "has_glossary": True,
            "includes_clinician_questions": True,
        }
        return {
            "report_outline": outline,
            "routed_models": [_route_to_dict(decision)],
            "metrics": {"model": decision.selected_model, "sections": len(outline)},
        }


async def persist_pipeline_outputs(
    db: AsyncSession,
    *,
    document_id: str,
    page_results: list[OCRPageResult],
    entities_bundle: dict[str, Any],
    chunks: list[dict[str, Any]],
    retriever: HybridRetriever,
) -> int:
    await db.execute(delete(OCRPage).where(OCRPage.document_id == document_id))
    await db.execute(delete(MedicalEntity).where(MedicalEntity.document_id == document_id))
    await db.execute(delete(LabResult).where(LabResult.document_id == document_id))
    await db.execute(delete(MedicationHistory).where(MedicationHistory.document_id == document_id))
    await db.execute(delete(TimelineEvent).where(TimelineEvent.document_id == document_id))

    for page in page_results:
        db.add(
            OCRPage(
                document_id=document_id,
                page_number=page.page_index + 1,
                page_text=page.text,
                layout_json={
                    "blocks": [
                        {
                            "text": block.text,
                            "bbox": list(block.bbox) if block.bbox else None,
                            "confidence": block.confidence,
                            "label": block.label,
                        }
                        for block in page.blocks
                    ],
                    "tables": [
                        {
                            "cells": table.cells,
                            "bbox": list(table.bbox) if table.bbox else None,
                            "confidence": table.confidence,
                            "page_index": table.page_index,
                        }
                        for table in page.tables
                    ],
                },
                confidence=page.confidence,
                provider="dual-path",
            )
        )

    for entity in entities_bundle.get("entities", []):
        db.add(
            MedicalEntity(
                document_id=document_id,
                entity_type=str(entity["entity_type"]),
                raw_value=str(entity["raw_value"]),
                normalized_value=(
                    str(entity["normalized_value"]) if entity.get("normalized_value") else None
                ),
                attributes_json=_json_safe(dict(entity.get("attributes", {}))),
                page_number=entity.get("page_number"),
                confidence=entity.get("confidence"),
            )
        )

    for lab in entities_bundle.get("labs", []):
        db.add(
            LabResult(
                document_id=document_id,
                test_name=str(lab["test_name"]),
                value_text=str(lab["value_text"]),
                unit=lab.get("unit"),
                reference_range=lab.get("reference_range"),
                is_out_of_range=lab.get("is_out_of_range"),
                event_date=lab.get("event_date"),
                page_number=lab.get("page_number"),
                source_span=lab.get("source_span"),
            )
        )

    for medication in entities_bundle.get("medications", []):
        db.add(
            MedicationHistory(
                document_id=document_id,
                medication_name=str(medication["medication_name"]),
                dosage=medication.get("dosage"),
                frequency=medication.get("frequency"),
                action=str(medication.get("action") or "mentioned"),
                start_date=medication.get("start_date"),
                end_date=medication.get("end_date"),
                page_number=medication.get("page_number"),
                source_span=medication.get("source_span"),
            )
        )

    for event in entities_bundle.get("timeline_events", []):
        db.add(
            TimelineEvent(
                document_id=document_id,
                event_type=str(event["event_type"]),
                event_date=event.get("event_date"),
                title=str(event["title"]),
                description=event.get("description"),
                metadata_json=_json_safe(dict(event.get("metadata", {}))),
                page_number=event.get("page_number"),
            )
        )

    await db.flush()
    indexed = await retriever.index_chunks(db, document_id=document_id, chunks=chunks)
    return indexed


async def _extract_entities_async(pages: list[OCRPageResult]) -> ExtractionBundle:
    return extract_entities_from_pages(pages)


def _merge_state_patch(state: AgentState, patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if key == "metrics":
            continue
        if key == "routed_models":
            existing = state.get("routed_models", [])
            existing.extend(value)
            state["routed_models"] = existing
            continue
        state[key] = value


def _retrieval_preview(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    token_counter: Counter[str] = Counter()
    for chunk in chunks:
        text = str(chunk.get("text_content") or "")
        for token in re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text.lower()):
            token_counter[token] += 1
    top_terms = [term for term, _ in token_counter.most_common(12)]
    preview: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks[:5], start=1):
        preview.append(
            {
                "rank": idx,
                "chunk_index": chunk.get("chunk_index"),
                "page_number": chunk.get("page_number"),
                "snippet": str(chunk.get("text_content") or "")[:200],
                "top_terms": top_terms[:6],
            }
        )
    return preview


def _route_to_dict(route: RouteDecision) -> dict[str, Any]:
    return {
        "task": route.task,
        "selected_model": route.selected_model,
        "candidates": route.candidates,
        "reason": route.reason,
        "gpu_available": route.gpu_available,
    }


def _json_safe(value: Any) -> Any:
    """Convert nested values into JSON-serializable primitives."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return value


async def create_agent_run(db: AsyncSession, *, user: User | None, document_id: str | None, workflow: str) -> AgentRun:
    run = AgentRun(
        user_id=user.id if user else None,
        document_id=document_id,
        workflow=workflow,
        status="running",
        trace_json=[],
    )
    db.add(run)
    await db.flush()
    return run


async def complete_agent_run(db: AsyncSession, *, run: AgentRun, state: AgentState) -> None:
    run.status = state.get("status", "completed")
    run.trace_json = state.get("trace", [])
    run.error_text = state.get("error")
    run.ended_at = datetime.datetime.now(datetime.UTC)
    await db.flush()


async def list_agent_runs(db: AsyncSession, *, user_id: str | None = None, limit: int = 50) -> list[AgentRun]:
    stmt = select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)
    if user_id:
        stmt = stmt.where(AgentRun.user_id == user_id)
    return list((await db.execute(stmt)).scalars().all())


async def _with_retries(call, *args, retries: int):
    attempt = 0
    while True:
        try:
            return await call(*args)
        except Exception:
            attempt += 1
            if attempt > retries:
                raise
            await asyncio.sleep(min(0.4 * attempt, 1.5))
