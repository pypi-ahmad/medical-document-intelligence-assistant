"""Summary generation service with strict educational framing."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Document
from app.models.medical_db_models import DocumentChunk
from app.services.infrastructure.model_router import ModelRouter
from app.services.infrastructure.ollama_client import OllamaClient, OllamaError
from app.services.medical.safety import append_disclaimer, build_safety_envelope

_SUMMARY_PROMPTS = {
    "plain": "Write plain-language summary of uploaded medical documents.",
    "clinical": "Write concise clinical summary with key findings and dates.",
    "medication": "Summarize medications, dosages, frequencies, and changes over time.",
    "laboratory": "Summarize laboratory findings, highlight values outside reference ranges.",
    "visit": "Summarize doctor visits, procedures, and major events chronologically.",
    "discharge": "Summarize discharge details, follow-up instructions, and documented status.",
}

_LENGTH_HINT = {
    "short": "Max 120 words.",
    "medium": "Around 220 words.",
    "long": "Around 450 words.",
}


class SummaryService:
    def __init__(self, ollama_client: OllamaClient | None = None, router: ModelRouter | None = None) -> None:
        self.ollama = ollama_client or OllamaClient(timeout_seconds=15.0)
        self.router = router or ModelRouter(self.ollama)

    async def summarize(
        self,
        db: AsyncSession,
        *,
        document_ids: list[str],
        summary_type: str,
        length: str,
    ) -> tuple[str, str]:
        context = await self._load_context(db, document_ids)
        if not context.strip():
            return "No indexed content found for selected documents.", ""

        route = await self.router.route("summary")
        prompt = (
            f"{_SUMMARY_PROMPTS.get(summary_type, _SUMMARY_PROMPTS['plain'])}\n"
            f"{_LENGTH_HINT.get(length, _LENGTH_HINT['medium'])}\n"
            "Use only evidence from provided context. If uncertain, say so.\n"
            "Do not diagnose, prescribe, or recommend treatment.\n\n"
            f"Context:\n{context[:18000]}"
        )
        system = (
            "You are educational medical document assistant. "
            "Always avoid diagnosis/treatment advice."
        )
        try:
            generation = await self.ollama.generate(
                model=route.selected_model,
                prompt=prompt,
                system=system,
                options={"temperature": 0.1},
            )
            return append_disclaimer(generation.content.strip()), route.selected_model
        except OllamaError:
            # deterministic fallback to avoid silent failures
            return append_disclaimer(self._fallback_summary(context, summary_type)), route.selected_model

    async def _load_context(self, db: AsyncSession, document_ids: list[str]) -> str:
        stmt = select(DocumentChunk.text_content).order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
        if document_ids:
            stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))
        rows = (await db.execute(stmt)).scalars().all()
        if rows:
            return "\n\n".join(rows)

        doc_stmt = select(Document.original_filename, Document.file_path)
        if document_ids:
            doc_stmt = doc_stmt.where(Document.id.in_(document_ids))
        docs = (await db.execute(doc_stmt)).all()
        return "\n".join(f"Document: {name} ({path})" for name, path in docs)

    @staticmethod
    def _fallback_summary(context: str, summary_type: str) -> str:
        lines = [line.strip() for line in context.splitlines() if line.strip()]
        selected = " ".join(lines[:12])
        return (
            f"{summary_type.title()} summary (fallback mode): {selected[:900]}. "
            "Educational use only. Consult qualified healthcare professionals for decisions."
        )


def default_safety():
    return build_safety_envelope()
