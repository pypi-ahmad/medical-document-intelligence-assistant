"""Medical assistant database models.

These models extend the base upload/extraction schema with production
entities required by the medical-document workflow.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.db_models import Base


def _uuid32() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid32)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid32)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))


class OCRPage(Base):
    __tablename__ = "ocr_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    page_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    layout_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MedicalEntity(Base):
    __tablename__ = "medical_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str | None] = mapped_column(Text)
    attributes_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    page_number: Mapped[int | None] = mapped_column(Integer)
    span_start: Mapped[int | None] = mapped_column(Integer)
    span_end: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value_text: Mapped[str] = mapped_column(String(128), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(64))
    reference_range: Mapped[str | None] = mapped_column(String(128))
    is_out_of_range: Mapped[bool | None] = mapped_column(Boolean)
    event_date: Mapped[datetime.date | None] = mapped_column(Date)
    page_number: Mapped[int | None] = mapped_column(Integer)
    source_span: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MedicationHistory(Base):
    __tablename__ = "medication_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    dosage: Mapped[str | None] = mapped_column(String(128))
    frequency: Mapped[str | None] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="mentioned")
    start_date: Mapped[datetime.date | None] = mapped_column(Date)
    end_date: Mapped[datetime.date | None] = mapped_column(Date)
    page_number: Mapped[int | None] = mapped_column(Integer)
    source_span: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_date: Mapped[datetime.date | None] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    page_number: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid32)
    document_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_name: Mapped[str | None] = mapped_column(String(128))
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    keyword_blob: Mapped[str] = mapped_column(Text, nullable=False, default="")
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    token_count: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid32)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Medical chat")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid32)
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    safety_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="safe")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid32)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id", ondelete="CASCADE"))
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    markdown_body: Mapped[str] = mapped_column(Text, nullable=False)
    html_body: Mapped[str] = mapped_column(Text, nullable=False)
    json_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid32)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id", ondelete="CASCADE"))
    memory_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    memory_key: Mapped[str] = mapped_column(String(255), nullable=False)
    memory_value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid32)
    user_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id", ondelete="SET NULL"))
    document_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("documents.id", ondelete="SET NULL"), index=True
    )
    workflow: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    trace_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    error_text: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(64))
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


Index("ix_entities_doc_type", MedicalEntity.document_id, MedicalEntity.entity_type)
Index("ix_labs_doc_test", LabResult.document_id, LabResult.test_name)
Index("ix_medication_doc_name", MedicationHistory.document_id, MedicationHistory.medication_name)
Index("ix_timeline_doc_date", TimelineEvent.document_id, TimelineEvent.event_date)
Index("ix_chunks_doc_chunk", DocumentChunk.document_id, DocumentChunk.chunk_index, unique=True)
Index("ix_memory_user_type", MemoryEntry.user_id, MemoryEntry.memory_type)
