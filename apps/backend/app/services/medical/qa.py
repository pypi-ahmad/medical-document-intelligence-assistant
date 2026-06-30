"""Grounded medical QA service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.medical_db_models import ChatMessage, ChatSession, User
from app.services.infrastructure.model_router import ModelRouter
from app.services.infrastructure.ollama_client import OllamaClient, OllamaError
from app.services.medical.retrieval import HybridRetriever
from app.services.medical.safety import (
    append_disclaimer,
    blocked_response_text,
    is_prohibited_medical_request,
)


@dataclass(slots=True)
class QAResult:
    session_id: str
    answer: str
    extracted_information: str
    educational_background: str
    citations: list[dict]
    model: str


@dataclass(slots=True)
class QAContext:
    prompt: str
    system: str
    model: str
    citations: list[dict]
    extracted_context: str
    educational_context: str


class MedicalQAService:
    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        ollama_client: OllamaClient | None = None,
        router: ModelRouter | None = None,
    ) -> None:
        self.ollama = ollama_client or OllamaClient(timeout_seconds=15.0)
        self.router = router or ModelRouter(self.ollama)
        self.retriever = retriever or HybridRetriever(self.ollama, self.router)

    async def answer(
        self,
        db: AsyncSession,
        *,
        user: User,
        question: str,
        session_id: str | None,
        document_ids: list[str],
        top_k: int,
    ) -> QAResult:
        session = await self.ensure_session(db, user=user, session_id=session_id, question=question)

        if is_prohibited_medical_request(question):
            blocked = blocked_response_text()
            await self.store_message(db, session.id, "user", question, [])
            await self.store_message(db, session.id, "assistant", blocked, [])
            return QAResult(
                session_id=session.id,
                answer=blocked,
                extracted_information="",
                educational_background="",
                citations=[],
                model="guardrail",
            )

        context = await self.build_context(
            db,
            question=question,
            document_ids=document_ids,
            top_k=top_k,
        )

        try:
            generation = await self.ollama.generate(
                model=context.model,
                prompt=context.prompt,
                system=context.system,
                options={"temperature": 0.1},
            )
            answer_text = append_disclaimer(generation.content.strip())
        except OllamaError:
            fallback = (
                "Extracted Information From Uploaded Documents:\n"
                f"{_fallback_extract(context.extracted_context)}\n\n"
                "Educational Background Information:\n"
                f"{_fallback_extract(context.educational_context)}"
            )
            answer_text = append_disclaimer(fallback)

        extracted_part, educational_part = _split_answer(answer_text)

        await self.store_message(db, session.id, "user", question, [])
        await self.store_message(db, session.id, "assistant", answer_text, context.citations)

        return QAResult(
            session_id=session.id,
            answer=answer_text,
            extracted_information=extracted_part,
            educational_background=educational_part,
            citations=context.citations,
            model=context.model,
        )

    async def build_context(
        self,
        db: AsyncSession,
        *,
        question: str,
        document_ids: list[str],
        top_k: int,
    ) -> QAContext:
        hits, _, diagnostics = await self.retriever.search(
            db,
            query=question,
            top_k=max(1, min(top_k, settings.max_chunks_per_query)),
            document_ids=document_ids,
        )
        citations = [
            {
                "document_id": hit.chunk.document_id,
                "document_name": hit.document_name,
                "page_number": hit.chunk.page_number,
                "chunk_id": hit.chunk.id,
                "evidence_text": hit.chunk.text_content[:450],
            }
            for hit in hits
        ]
        extracted_context = "\n\n".join(hit.chunk.text_content for hit in hits)
        educational_context = _load_local_reference_context(question)
        route = await self.router.route("qa")
        prompt = (
            "Answer using two sections:\n"
            "1) Extracted Information From Uploaded Documents\n"
            "2) Educational Background Information\n\n"
            "Never diagnose, prescribe, or recommend treatment."
            " If evidence missing, explicitly say evidence unavailable.\n\n"
            f"Question:\n{question}\n\n"
            f"Extracted Context:\n{extracted_context[:16000]}\n\n"
            f"Educational Reference Context:\n{educational_context[:5000]}\n\n"
            f"Retrieval diagnostics: {diagnostics}"
        )
        system = (
            "You are medical document assistant for education only. "
            "Do not provide diagnosis, treatment recommendation, or prescriptions."
        )
        return QAContext(
            prompt=prompt,
            system=system,
            model=route.selected_model,
            citations=citations,
            extracted_context=extracted_context,
            educational_context=educational_context,
        )

    async def ensure_session(
        self,
        db: AsyncSession,
        *,
        user: User,
        session_id: str | None,
        question: str,
    ) -> ChatSession:
        if session_id:
            session = await db.get(ChatSession, session_id)
            if session:
                return session

        session = ChatSession(user_id=user.id, title=question[:120] or "Medical Chat")
        db.add(session)
        await db.flush()
        return session

    async def store_message(
        self,
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        citations: list[dict],
    ) -> None:
        db.add(
            ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                citations_json=citations,
                safety_mode="safe",
            )
        )
        await db.flush()


def _split_answer(answer: str) -> tuple[str, str]:
    marker_a = "Extracted Information From Uploaded Documents"
    marker_b = "Educational Background Information"
    if marker_a in answer and marker_b in answer:
        first = answer.split(marker_a, maxsplit=1)[1]
        extracted, educational = first.split(marker_b, maxsplit=1)
        return extracted.strip(" :\n"), educational.strip(" :\n")
    return answer, ""


def _fallback_extract(text: str) -> str:
    snippet = " ".join([line.strip() for line in text.splitlines() if line.strip()][:8])
    if not snippet:
        return "No supporting evidence found in local index."
    return snippet[:900]


def _load_local_reference_context(question: str) -> str:
    reference_path = Path(__file__).resolve().parents[3] / "data" / "medical_references.md"
    if not reference_path.exists():
        return (
            "General educational note: Lab reference ranges vary by laboratory. "
            "Medication changes must be reviewed with licensed clinicians."
        )

    reference_text = reference_path.read_text(encoding="utf-8")
    terms = {token.lower() for token in question.split() if len(token) > 3}
    paragraphs = [p.strip() for p in reference_text.split("\n\n") if p.strip()]
    scored: list[tuple[int, str]] = []
    for paragraph in paragraphs:
        p_lower = paragraph.lower()
        score = sum(1 for term in terms if term in p_lower)
        scored.append((score, paragraph))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [paragraph for score, paragraph in scored[:4] if score > 0]
    if not selected:
        selected = paragraphs[:2]
    return "\n\n".join(selected)
