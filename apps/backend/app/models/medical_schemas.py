"""Pydantic schemas for medical assistant APIs."""

from __future__ import annotations

import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class SafetyEnvelope(BaseModel):
    disclaimer: str
    educational_use_only: bool = True
    prohibited_actions: list[str]


class UserBootstrapRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=12, max_length=255)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=255)


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class UserProfile(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_admin: bool
    created_at: datetime.datetime


class AuthResponse(BaseModel):
    user: UserProfile
    tokens: TokenPairResponse


class ModelRouteDecision(BaseModel):
    task: str
    selected_model: str
    candidates: list[str]
    reason: str
    gpu_available: bool


class OCRPageOut(BaseModel):
    page_number: int
    text: str
    confidence: float | None = None
    layout_json: dict[str, Any] = Field(default_factory=dict)


class EntityOut(BaseModel):
    entity_type: str
    raw_value: str
    normalized_value: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    page_number: int | None = None
    confidence: float | None = None


class LabResultOut(BaseModel):
    test_name: str
    value_text: str
    unit: str | None = None
    reference_range: str | None = None
    is_out_of_range: bool | None = None
    event_date: datetime.date | None = None
    page_number: int | None = None


class MedicationOut(BaseModel):
    medication_name: str
    dosage: str | None = None
    frequency: str | None = None
    action: str
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    page_number: int | None = None


class TimelineEventOut(BaseModel):
    id: int
    document_id: str
    event_type: str
    event_date: datetime.date | None = None
    title: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    page_number: int | None = None


class CitationOut(BaseModel):
    document_id: str
    document_name: str
    page_number: int | None = None
    chunk_id: str | None = None
    evidence_text: str


class ProcessDocumentResponse(BaseModel):
    document_id: str
    status: str
    routed_models: list[ModelRouteDecision]
    pages: list[OCRPageOut]
    entities: list[EntityOut]
    labs: list[LabResultOut]
    medications: list[MedicationOut]
    timeline_events: list[TimelineEventOut]
    indexed_chunks: int
    safety: SafetyEnvelope


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1200)
    top_k: int = Field(default=10, ge=1, le=50)
    document_ids: list[str] = Field(default_factory=list)
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int | None = None
    score: float
    keyword_score: float
    semantic_score: float
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    took_ms: int
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class QARequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    session_id: str | None = None
    document_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=10, ge=1, le=30)


class QAResponse(BaseModel):
    session_id: str
    answer: str
    extracted_information: str
    educational_background: str
    citations: list[CitationOut]
    safety: SafetyEnvelope
    model: str


class SummaryRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    summary_type: Literal[
        "plain",
        "clinical",
        "medication",
        "laboratory",
        "visit",
        "discharge",
    ] = "plain"
    length: Literal["short", "medium", "long"] = "medium"


class SummaryResponse(BaseModel):
    summary_type: str
    length: str
    content: str
    citations: list[CitationOut]
    safety: SafetyEnvelope


class TimelineRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    event_types: list[str] = Field(default_factory=list)
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None


class TimelineResponse(BaseModel):
    events: list[TimelineEventOut]
    filters_applied: dict[str, Any]


class ReportRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    title: str = "Doctor Visit Preparation Report"
    export_formats: list[str] = Field(default_factory=lambda: ["html", "pdf", "json", "markdown"])


class ReportResponse(BaseModel):
    report_id: str
    title: str
    markdown: str
    html: str
    json_payload: dict[str, Any]
    available_formats: list[str]
    safety: SafetyEnvelope


class MemoryItem(BaseModel):
    id: str
    memory_type: str
    memory_key: str
    memory_value: dict[str, Any]
    expires_at: datetime.datetime | None = None
    created_at: datetime.datetime


class MemoryCreateRequest(BaseModel):
    memory_type: Literal["short_term", "notebook", "document_history", "preference"]
    memory_key: str = Field(min_length=1, max_length=255)
    memory_value: dict[str, Any] = Field(default_factory=dict)
    ttl_days: int | None = Field(default=None, ge=1, le=365)


class MemoryClearResponse(BaseModel):
    deleted: int


class AgentRunOut(BaseModel):
    id: str
    workflow: str
    status: str
    document_id: str | None = None
    trace_json: list[Any] = Field(default_factory=list)
    started_at: datetime.datetime
    ended_at: datetime.datetime | None = None


class SystemHealthResponse(BaseModel):
    status: str
    gpu_available: bool
    gpu_info: dict[str, Any] = Field(default_factory=dict)
    ollama: dict[str, Any] = Field(default_factory=dict)
    memory_usage_mb: float
    active_agent_runs: int


class ModelConfigResponse(BaseModel):
    default_chat_model: str
    fast_chat_model: str
    summary_model: str
    entity_model: str
    embedding_model: str
    translation_model: str
    fallback_chat_models: list[str]


class ModelConfigUpdateRequest(BaseModel):
    default_chat_model: str | None = None
    fast_chat_model: str | None = None
    summary_model: str | None = None
    entity_model: str | None = None
    embedding_model: str | None = None
    translation_model: str | None = None
    fallback_chat_models: list[str] | None = None


class DoctorReportExport(BaseModel):
    report_id: str
    format: str
    content: str
