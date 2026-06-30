"""Doctor visit report generation."""

from __future__ import annotations

import datetime
import io
import json

from jinja2 import Template
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db_models import Document
from app.models.medical_db_models import (
    GeneratedReport,
    LabResult,
    MedicationHistory,
    TimelineEvent,
    User,
)
from app.services.medical.safety import build_safety_envelope

_REPORT_TEMPLATE = Template(
    """
# {{ title }}

Generated at: {{ generated_at }}

## Uploaded Documents Reviewed
{% for doc in documents -%}
- {{ doc.original_filename }} ({{ doc.file_type }})
{% endfor %}

## Medications Mentioned
{% for med in medications -%}
- {{ med.medication_name }}{% if med.dosage %} {{ med.dosage }}{% endif %}{% if med.frequency %} ({{ med.frequency }}){% endif %} [{{ med.action }}]
{% endfor %}

## Laboratory Findings
{% for lab in labs -%}
- {{ lab.test_name }}: {{ lab.value_text }}{% if lab.unit %} {{ lab.unit }}{% endif %}
  {% if lab.reference_range %}(Ref: {{ lab.reference_range }}){% endif %}
  {% if lab.is_out_of_range is not none %} - {% if lab.is_out_of_range %}Outside range{% else %}Within range{% endif %}{% endif %}
{% endfor %}

## Timeline of Events
{% for event in timeline -%}
- {% if event.event_date %}{{ event.event_date }}{% else %}Unknown date{% endif %}: {{ event.title }}
{% endfor %}

## Questions to Discuss With a Healthcare Professional
- Which findings require follow-up testing?
- Are there medication interactions or contraindications to review?
- What trend changes in labs or symptoms need professional interpretation?

## Glossary of Terms
{% for term in glossary -%}
- **{{ term.term }}**: {{ term.definition }}
{% endfor %}

## Disclaimer
{{ disclaimer }}
""".strip()
)


class ReportService:
    async def generate_doctor_visit_report(
        self,
        db: AsyncSession,
        *,
        user: User,
        document_ids: list[str],
        title: str,
    ) -> GeneratedReport:
        documents = await self._documents(db, document_ids)
        labs = await self._labs(db, document_ids)
        medications = await self._medications(db, document_ids)
        timeline = await self._timeline(db, document_ids)
        glossary = _build_glossary(labs, medications)
        safety = build_safety_envelope()

        markdown_body = _REPORT_TEMPLATE.render(
            title=title,
            generated_at=datetime.datetime.now(datetime.UTC).isoformat(),
            documents=documents,
            labs=labs,
            medications=medications,
            timeline=timeline,
            glossary=glossary,
            disclaimer=safety.disclaimer,
        )
        html_body = _markdown_to_html(markdown_body)

        payload = {
            "title": title,
            "documents": [doc.original_filename for doc in documents],
            "labs": [
                {
                    "test_name": lab.test_name,
                    "value": lab.value_text,
                    "unit": lab.unit,
                    "reference_range": lab.reference_range,
                    "is_out_of_range": lab.is_out_of_range,
                }
                for lab in labs
            ],
            "medications": [
                {
                    "medication_name": med.medication_name,
                    "dosage": med.dosage,
                    "frequency": med.frequency,
                    "action": med.action,
                }
                for med in medications
            ],
            "timeline": [
                {
                    "event_type": event.event_type,
                    "event_date": event.event_date.isoformat() if event.event_date else None,
                    "title": event.title,
                    "description": event.description,
                }
                for event in timeline
            ],
            "safety": safety.model_dump(),
        }

        report = GeneratedReport(
            user_id=user.id,
            report_type="doctor_visit",
            title=title,
            document_ids_json=document_ids,
            markdown_body=markdown_body,
            html_body=html_body,
            json_payload=payload,
        )
        db.add(report)
        await db.flush()
        return report

    async def export_report_content(self, db: AsyncSession, report_id: str, fmt: str) -> str:
        report = await db.get(GeneratedReport, report_id)
        if report is None:
            raise ValueError("Report not found")

        fmt_l = fmt.lower().strip()
        if fmt_l == "markdown":
            return report.markdown_body
        if fmt_l == "html":
            return report.html_body
        if fmt_l == "json":
            return json.dumps(report.json_payload, ensure_ascii=True, indent=2)
        if fmt_l == "pdf":
            return _render_pdf_base64(report.title, report.markdown_body)
        raise ValueError(f"Unsupported export format: {fmt}")

    async def _documents(self, db: AsyncSession, document_ids: list[str]) -> list[Document]:
        stmt = select(Document)
        if document_ids:
            stmt = stmt.where(Document.id.in_(document_ids))
        return list((await db.execute(stmt)).scalars().all())

    async def _labs(self, db: AsyncSession, document_ids: list[str]) -> list[LabResult]:
        stmt = select(LabResult)
        if document_ids:
            stmt = stmt.where(LabResult.document_id.in_(document_ids))
        return list((await db.execute(stmt)).scalars().all())

    async def _medications(self, db: AsyncSession, document_ids: list[str]) -> list[MedicationHistory]:
        stmt = select(MedicationHistory)
        if document_ids:
            stmt = stmt.where(MedicationHistory.document_id.in_(document_ids))
        return list((await db.execute(stmt)).scalars().all())

    async def _timeline(self, db: AsyncSession, document_ids: list[str]) -> list[TimelineEvent]:
        stmt = select(TimelineEvent).order_by(TimelineEvent.event_date, TimelineEvent.id)
        if document_ids:
            stmt = stmt.where(TimelineEvent.document_id.in_(document_ids))
        return list((await db.execute(stmt)).scalars().all())


def _build_glossary(labs: list[LabResult], medications: list[MedicationHistory]) -> list[dict[str, str]]:
    terms: list[dict[str, str]] = []
    seen: set[str] = set()

    for lab in labs:
        term = lab.test_name.strip().lower()
        if term and term not in seen:
            seen.add(term)
            terms.append({"term": lab.test_name, "definition": "Laboratory test mentioned in uploaded records."})

    for med in medications:
        term = med.medication_name.strip().lower()
        if term and term not in seen:
            seen.add(term)
            terms.append({"term": med.medication_name, "definition": "Medication name extracted from uploaded records."})

    return terms[:25]


def _markdown_to_html(markdown_text: str) -> str:
    # Keep conversion local and deterministic without external services.
    lines = markdown_text.splitlines()
    html_lines: list[str] = ["<article class='report'>"]
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            html_lines.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("- "):
            html_lines.append(f"<li>{stripped[2:]}</li>")
        else:
            html_lines.append(f"<p>{stripped}</p>")
    html_lines.append("</article>")
    return "\n".join(html_lines)


def _render_pdf_base64(title: str, markdown_text: str) -> str:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            story.append(Paragraph(stripped[2:], styles["Heading1"]))
        elif stripped.startswith("## "):
            story.append(Paragraph(stripped[3:], styles["Heading2"]))
        elif stripped.startswith("- "):
            story.append(Paragraph(f"• {stripped[2:]}", styles["BodyText"]))
        else:
            story.append(Paragraph(stripped, styles["BodyText"]))
        story.append(Spacer(1, 4))
    doc.build(story)

    import base64

    return base64.b64encode(buffer.getvalue()).decode("ascii")


def supported_report_formats() -> list[str]:
    return settings.report_export_format_list
