"""End-to-end medical document processing pipeline."""

from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Document
from app.models.medical_db_models import User
from app.security.crypto import EncryptedPayload, EncryptionService
from app.services.infrastructure.model_router import ModelRouter
from app.services.medical.agents import (
    MedicalSupervisor,
    complete_agent_run,
    create_agent_run,
    persist_pipeline_outputs,
)
from app.services.medical.chunking import chunk_pages
from app.services.medical.memory import MemoryService
from app.services.medical.retrieval import HybridRetriever
from app.services.medical.safety import build_safety_envelope


class MedicalPipelineService:
    def __init__(self) -> None:
        self.router = ModelRouter()
        self.retriever = HybridRetriever(router=self.router)
        self.memory = MemoryService()
        self.supervisor = MedicalSupervisor(retriever=self.retriever, memory_service=self.memory)
        self.encryption = EncryptionService()

    async def process_document(
        self,
        db: AsyncSession,
        *,
        user: User,
        document_id: str,
    ) -> dict:
        document = await db.get(Document, document_id)
        if document is None:
            raise ValueError("Document not found")

        run = await create_agent_run(db, user=user, document_id=document_id, workflow="medical_pipeline")
        ocr_file_path = self._decrypt_for_ocr_if_needed(document.file_path)
        try:
            state = await self.supervisor.execute(
                db,
                user=user,
                document_id=document_id,
                run_id=run.id,
                file_path_override=str(ocr_file_path),
            )
        finally:
            if ocr_file_path != Path(document.file_path):
                ocr_file_path.unlink(missing_ok=True)

        if state.get("status") == "failed":
            await complete_agent_run(db, run=run, state=state)
            return {
                "document_id": document_id,
                "status": "failed",
                "error": state.get("error", "Unknown failure"),
                "routed_models": state.get("routed_models", []),
                "pages": [],
                "entities": [],
                "labs": [],
                "medications": [],
                "timeline_events": [],
                "indexed_chunks": 0,
                "warnings": state.get("warnings", []),
                "safety": build_safety_envelope().model_dump(),
            }

        pages = state.get("page_results", [])
        entities_bundle = state.get("entities_bundle", {})
        chunk_records = state.get("chunk_records") or [asdict(chunk) for chunk in chunk_pages(pages)]

        indexed = await persist_pipeline_outputs(
            db,
            document_id=document_id,
            page_results=pages,
            entities_bundle=entities_bundle,
            chunks=chunk_records,
            retriever=self.retriever,
        )

        await self.memory.add_memory(
            db,
            user=user,
            memory_type="document_history",
            memory_key=f"processed:{document_id}",
            memory_value={
                "document_id": document_id,
                "filename": document.original_filename,
                "indexed_chunks": indexed,
                "entities": len(entities_bundle.get("entities", [])),
                "summary_preview": state.get("summary_preview"),
                "timeline_summary": state.get("timeline_summary", {}),
            },
            ttl_days=None,
        )

        state["status"] = "completed"
        await complete_agent_run(db, run=run, state=state)

        return {
            "document_id": document_id,
            "status": "completed",
            "routed_models": state.get("routed_models", []),
            "pages": [
                {
                    "page_number": page.page_index + 1,
                    "text": page.text,
                    "confidence": page.confidence,
                    "layout_json": {
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
                            }
                            for table in page.tables
                        ],
                    },
                }
                for page in pages
            ],
            "entities": entities_bundle.get("entities", []),
            "labs": entities_bundle.get("labs", []),
            "medications": entities_bundle.get("medications", []),
            "timeline_events": [
                {
                    "id": 0,
                    "document_id": document_id,
                    "event_type": event["event_type"],
                    "event_date": event.get("event_date"),
                    "title": event["title"],
                    "description": event.get("description"),
                    "metadata": event.get("metadata", {}),
                    "page_number": event.get("page_number"),
                }
                for event in entities_bundle.get("timeline_events", [])
            ],
            "indexed_chunks": indexed,
            "warnings": state.get("warnings", []),
            "safety": build_safety_envelope().model_dump(),
        }

    def _decrypt_for_ocr_if_needed(self, file_path: str) -> Path:
        source = Path(file_path)
        meta = Path(f"{file_path}.meta")
        if not meta.exists():
            return source

        payload = EncryptedPayload(
            nonce_b64=meta.read_text(encoding="utf-8").strip(),
            ciphertext_b64=source.read_text(encoding="utf-8"),
        )
        plaintext = self.encryption.decrypt_bytes(payload)
        suffix = "".join(source.suffixes) or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(plaintext)
            return Path(tmp.name)
