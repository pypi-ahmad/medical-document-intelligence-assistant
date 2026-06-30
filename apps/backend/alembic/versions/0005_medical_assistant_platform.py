"""Medical assistant platform tables.

Revision ID: 0005_medical_assistant_platform
Revises: 0004_evidence_entities_verifier
Create Date: 2026-06-27 23:59:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_medical_assistant_platform"
down_revision: str | Sequence[str] | None = "0004_evidence_entities_verifier"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )

    op.create_table(
        "ocr_pages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.String(length=32), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("page_text", sa.Text(), nullable=False),
        sa.Column("layout_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ocr_pages_document_id", "ocr_pages", ["document_id"])

    op.create_table(
        "medical_entities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.String(length=32), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("attributes_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("span_start", sa.Integer(), nullable=True),
        sa.Column("span_end", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_medical_entities_document_id", "medical_entities", ["document_id"])
    op.create_index("ix_medical_entities_entity_type", "medical_entities", ["entity_type"])

    op.create_table(
        "lab_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.String(length=32), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_name", sa.String(length=255), nullable=False),
        sa.Column("value_text", sa.String(length=128), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("reference_range", sa.String(length=128), nullable=True),
        sa.Column("is_out_of_range", sa.Boolean(), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("source_span", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_lab_results_document_id", "lab_results", ["document_id"])

    op.create_table(
        "medication_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.String(length=32), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("medication_name", sa.String(length=255), nullable=False),
        sa.Column("dosage", sa.String(length=128), nullable=True),
        sa.Column("frequency", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False, server_default="mentioned"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("source_span", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_medication_history_document_id", "medication_history", ["document_id"])
    op.create_index("ix_medication_history_medication_name", "medication_history", ["medication_name"])

    op.create_table(
        "timeline_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.String(length=32), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_timeline_events_document_id", "timeline_events", ["document_id"])
    op.create_index("ix_timeline_events_event_type", "timeline_events", ["event_type"])
    op.create_index("ix_timeline_events_event_date", "timeline_events", ["event_date"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("document_id", sa.String(length=32), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_name", sa.String(length=128), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("keyword_blob", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_document_chunk", "document_chunks", ["document_id", "chunk_index"], unique=True)

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("session_id", sa.String(length=32), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("safety_mode", sa.String(length=32), nullable=False, server_default="safe"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    op.create_table(
        "generated_reports",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("document_ids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("markdown_body", sa.Text(), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("json_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "memory_entries",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memory_type", sa.String(length=64), nullable=False),
        sa.Column("memory_key", sa.String(length=255), nullable=False),
        sa.Column("memory_value", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_memory_entries_memory_type", "memory_entries", ["memory_type"])
    op.create_index("ix_memory_entries_expires_at", "memory_entries", ["expires_at"])
    op.create_index("ix_memory_entries_user_type", "memory_entries", ["user_id", "memory_type"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_id", sa.String(length=32), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("workflow", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("trace_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_document_id", "agent_runs", ["document_id"])

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("value_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_table("system_settings")

    op.drop_index("ix_agent_runs_document_id", table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_index("ix_memory_entries_user_type", table_name="memory_entries")
    op.drop_index("ix_memory_entries_expires_at", table_name="memory_entries")
    op.drop_index("ix_memory_entries_memory_type", table_name="memory_entries")
    op.drop_table("memory_entries")

    op.drop_table("generated_reports")

    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")

    op.drop_index("ix_document_chunks_document_chunk", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_timeline_events_event_date", table_name="timeline_events")
    op.drop_index("ix_timeline_events_event_type", table_name="timeline_events")
    op.drop_index("ix_timeline_events_document_id", table_name="timeline_events")
    op.drop_table("timeline_events")

    op.drop_index("ix_medication_history_medication_name", table_name="medication_history")
    op.drop_index("ix_medication_history_document_id", table_name="medication_history")
    op.drop_table("medication_history")

    op.drop_index("ix_lab_results_document_id", table_name="lab_results")
    op.drop_table("lab_results")

    op.drop_index("ix_medical_entities_entity_type", table_name="medical_entities")
    op.drop_index("ix_medical_entities_document_id", table_name="medical_entities")
    op.drop_table("medical_entities")

    op.drop_index("ix_ocr_pages_document_id", table_name="ocr_pages")
    op.drop_table("ocr_pages")

    op.drop_table("refresh_tokens")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
