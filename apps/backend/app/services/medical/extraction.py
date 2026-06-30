"""Medical entity extraction, normalization, and timeline event construction."""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Any

from dateutil import parser as date_parser

from app.services.ocr.base import OCRPageResult

_DATE_PATTERN = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)

_LAB_PATTERN = re.compile(
    r"(?P<test>[A-Za-z][A-Za-z0-9\s\-/()]{2,80})[:\-]\s*"
    r"(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z%/]+)?"
    r"(?:\s*\((?P<range>[^)]+)\))?",
)

_MEDICATION_PATTERN = re.compile(
    r"(?P<name>[A-Z][A-Za-z0-9\-]{2,40})\s+"
    r"(?P<dosage>\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|units?|iu))"
    r"(?:\s+(?P<frequency>(?:once|twice|thrice|daily|bid|tid|qid|q\d+h|every\s+\d+\s*(?:hours?|days?))))?",
    re.IGNORECASE,
)

_VISIT_DATE_PATTERN = re.compile(
    r"\b(?P<label>visit date|date of visit|date of service|admission date|discharge date)\s*[:\-]\s*(?P<value>.+)",
    re.IGNORECASE,
)

_SIMPLE_TERM_MAP = {
    "haemoglobin": "hemoglobin",
    "hb": "hemoglobin",
    "wbc": "white blood cell count",
    "bp": "blood pressure",
    "hr": "heart rate",
    "temp": "temperature",
}
_LAB_KEYWORDS = {
    "hemoglobin",
    "haemoglobin",
    "wbc",
    "rbc",
    "platelet",
    "creatinine",
    "glucose",
    "sodium",
    "potassium",
    "alt",
    "ast",
    "bilirubin",
    "cholesterol",
    "triglyceride",
    "hba1c",
}
_PROCEDURE_LABELS = ("procedure", "procedures", "operation", "surgery", "imaging", "study")
_VACCINATION_LABELS = ("vaccination", "vaccinations", "immunization", "immunizations", "vaccine")
_PROVIDER_LABELS = ("doctor", "provider", "physician", "consultant")
_HOSPITAL_LABELS = ("hospital", "facility", "clinic", "medical center")
_PATIENT_FIELDS = {
    "patient_name": ("patient name", "name"),
    "patient_id": ("patient id", "mrn", "medical record number"),
    "patient_age": ("age",),
    "patient_sex": ("sex", "gender"),
}


@dataclass(slots=True)
class ExtractionBundle:
    entities: list[dict[str, Any]]
    labs: list[dict[str, Any]]
    medications: list[dict[str, Any]]
    timeline_events: list[dict[str, Any]]


def extract_entities_from_pages(pages: list[OCRPageResult]) -> ExtractionBundle:
    entities: list[dict[str, Any]] = []
    labs: list[dict[str, Any]] = []
    medications: list[dict[str, Any]] = []
    timeline_events: list[dict[str, Any]] = []

    for page in pages:
        text = page.text or ""
        page_number = page.page_index + 1

        patient_info = _extract_patient_information(text)
        for field_name, field_value in patient_info.items():
            entities.append(
                {
                    "entity_type": field_name,
                    "raw_value": field_value,
                    "normalized_value": field_value.strip(),
                    "attributes": {"field": field_name},
                    "page_number": page_number,
                    "confidence": page.confidence,
                }
            )

        for label, date_value in _extract_visit_dates(text):
            entities.append(
                {
                    "entity_type": "visit_date",
                    "raw_value": f"{label}: {date_value.isoformat()}",
                    "normalized_value": date_value.isoformat(),
                    "attributes": {"label": label},
                    "page_number": page_number,
                    "confidence": page.confidence,
                }
            )
            timeline_events.append(
                {
                    "event_type": "doctor_visit",
                    "event_date": date_value,
                    "title": f"{label.title()} documented",
                    "description": f"{label.title()}: {date_value.isoformat()}",
                    "metadata": {"label": label},
                    "page_number": page_number,
                }
            )

        detected_dates = _extract_dates(text)
        for date_value in detected_dates:
            timeline_events.append(
                {
                    "event_type": "document_date",
                    "event_date": date_value,
                    "title": f"Document date detected ({date_value.isoformat()})",
                    "description": "Date extracted from OCR text",
                    "metadata": {},
                    "page_number": page_number,
                }
            )

        for diagnosis in _extract_labeled_values(text, labels=("diagnosis", "diagnoses")):
            entities.append(
                {
                    "entity_type": "diagnosis_mentioned",
                    "raw_value": diagnosis,
                    "normalized_value": _normalize_term(diagnosis),
                    "attributes": {},
                    "page_number": page_number,
                    "confidence": page.confidence,
                }
            )
            timeline_events.append(
                {
                    "event_type": "diagnosis_mention",
                    "event_date": detected_dates[0] if detected_dates else None,
                    "title": "Diagnosis mentioned",
                    "description": diagnosis,
                    "metadata": {"diagnosis": diagnosis},
                    "page_number": page_number,
                }
            )

        for symptom in _extract_labeled_values(text, labels=("symptom", "symptoms", "chief complaint")):
            entities.append(
                {
                    "entity_type": "symptom",
                    "raw_value": symptom,
                    "normalized_value": _normalize_term(symptom),
                    "attributes": {},
                    "page_number": page_number,
                    "confidence": page.confidence,
                }
            )

        for allergy in _extract_labeled_values(text, labels=("allergy", "allergies")):
            entities.append(
                {
                    "entity_type": "allergy",
                    "raw_value": allergy,
                    "normalized_value": _normalize_term(allergy),
                    "attributes": {},
                    "page_number": page_number,
                    "confidence": page.confidence,
                }
            )

        for provider in _extract_labeled_values(text, labels=_PROVIDER_LABELS):
            entities.append(
                {
                    "entity_type": "healthcare_provider",
                    "raw_value": provider,
                    "normalized_value": provider.strip(),
                    "attributes": {},
                    "page_number": page_number,
                    "confidence": page.confidence,
                }
            )

        for hospital in _extract_labeled_values(text, labels=_HOSPITAL_LABELS):
            entities.append(
                {
                    "entity_type": "hospital",
                    "raw_value": hospital,
                    "normalized_value": hospital.strip(),
                    "attributes": {},
                    "page_number": page_number,
                    "confidence": page.confidence,
                }
            )

        for procedure in _extract_labeled_values(text, labels=_PROCEDURE_LABELS):
            normalized_procedure = _normalize_term(procedure)
            entities.append(
                {
                    "entity_type": "procedure",
                    "raw_value": procedure,
                    "normalized_value": normalized_procedure,
                    "attributes": {},
                    "page_number": page_number,
                    "confidence": page.confidence,
                }
            )
            timeline_events.append(
                {
                    "event_type": "procedure",
                    "event_date": detected_dates[0] if detected_dates else None,
                    "title": f"Procedure: {procedure}",
                    "description": procedure,
                    "metadata": {"procedure": normalized_procedure},
                    "page_number": page_number,
                }
            )

        for vaccination in _extract_labeled_values(text, labels=_VACCINATION_LABELS):
            normalized_vaccine = _normalize_term(vaccination)
            entities.append(
                {
                    "entity_type": "vaccination",
                    "raw_value": vaccination,
                    "normalized_value": normalized_vaccine,
                    "attributes": {},
                    "page_number": page_number,
                    "confidence": page.confidence,
                }
            )
            timeline_events.append(
                {
                    "event_type": "vaccination",
                    "event_date": detected_dates[0] if detected_dates else None,
                    "title": f"Vaccination: {vaccination}",
                    "description": vaccination,
                    "metadata": {"vaccination": normalized_vaccine},
                    "page_number": page_number,
                }
            )

        for line in text.splitlines():
            for match in _LAB_PATTERN.finditer(line):
                test_name = _normalize_term(match.group("test"))
                value_text = match.group("value").strip()
                unit = (match.group("unit") or "").strip() or None
                ref_range = (match.group("range") or "").strip() or None
                if not _looks_like_lab(test_name, unit, ref_range):
                    continue
                out_of_range = _is_out_of_range(value_text, ref_range)

                lab = {
                    "test_name": test_name,
                    "value_text": value_text,
                    "unit": unit,
                    "reference_range": ref_range,
                    "is_out_of_range": out_of_range,
                    "event_date": detected_dates[0] if detected_dates else None,
                    "page_number": page_number,
                    "source_span": match.group(0),
                }
                labs.append(lab)
                entities.append(
                    {
                        "entity_type": "laboratory_value",
                        "raw_value": match.group(0),
                        "normalized_value": test_name,
                        "attributes": {
                            "value": value_text,
                            "unit": unit,
                            "reference_range": ref_range,
                            "is_out_of_range": out_of_range,
                        },
                        "page_number": page_number,
                        "confidence": page.confidence,
                    }
                )
                timeline_events.append(
                    {
                        "event_type": "lab_test",
                        "event_date": lab["event_date"],
                        "title": f"Lab: {test_name}",
                        "description": f"{value_text} {unit or ''}".strip(),
                        "metadata": {
                            "test_name": test_name,
                            "value": value_text,
                            "unit": unit,
                            "reference_range": ref_range,
                            "is_out_of_range": out_of_range,
                        },
                        "page_number": page_number,
                    }
                )

        for match in _MEDICATION_PATTERN.finditer(text):
            medication_name = match.group("name").strip()
            dosage = match.group("dosage").strip()
            frequency = (match.group("frequency") or "").strip() or None
            action = _classify_medication_action(text, match.start())
            medication = {
                "medication_name": medication_name,
                "dosage": dosage,
                "frequency": frequency,
                "action": action,
                "start_date": detected_dates[0] if action == "started" and detected_dates else None,
                "end_date": detected_dates[0] if action == "stopped" and detected_dates else None,
                "page_number": page_number,
                "source_span": match.group(0),
            }
            medications.append(medication)
            entities.append(
                {
                    "entity_type": "medication",
                    "raw_value": match.group(0),
                    "normalized_value": _normalize_term(medication_name),
                    "attributes": {
                        "dosage": dosage,
                        "frequency": frequency,
                        "action": action,
                    },
                    "page_number": page_number,
                    "confidence": page.confidence,
                }
            )
            timeline_events.append(
                {
                    "event_type": "medication_change",
                    "event_date": medication["start_date"] or medication["end_date"],
                    "title": f"Medication {action}: {medication_name}",
                    "description": f"{dosage} {frequency or ''}".strip(),
                    "metadata": medication,
                    "page_number": page_number,
                }
            )

    return ExtractionBundle(
        entities=entities,
        labs=labs,
        medications=medications,
        timeline_events=timeline_events,
    )


def _extract_dates(text: str) -> list[datetime.date]:
    dates: list[datetime.date] = []
    for found in _DATE_PATTERN.findall(text):
        try:
            parsed = date_parser.parse(found, fuzzy=False)
            dates.append(parsed.date())
        except (ValueError, OverflowError):
            continue
    unique_dates = sorted(set(dates))
    return unique_dates


def _extract_labeled_values(text: str, labels: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for label in labels:
        pattern = re.compile(rf"{re.escape(label)}\s*[:\-]\s*(.+)", re.IGNORECASE)
        for line in text.splitlines():
            match = pattern.search(line)
            if match:
                value = match.group(1).strip()
                if value:
                    values.append(value)
    return values


def _extract_patient_information(text: str) -> dict[str, str]:
    extracted: dict[str, str] = {}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for field_name, labels in _PATIENT_FIELDS.items():
        for line in lines:
            lower_line = line.lower()
            for label in labels:
                prefix = f"{label.lower()}:"
                alt_prefix = f"{label.lower()}-"
                if lower_line.startswith(prefix) or lower_line.startswith(alt_prefix):
                    _, _, value = line.partition(":")
                    if not value and "-" in line:
                        value = line.split("-", maxsplit=1)[1]
                    value = value.strip()
                    if value:
                        extracted[field_name] = value
                        break
            if field_name in extracted:
                break
    return extracted


def _extract_visit_dates(text: str) -> list[tuple[str, datetime.date]]:
    extracted: list[tuple[str, datetime.date]] = []
    for line in text.splitlines():
        match = _VISIT_DATE_PATTERN.search(line)
        if not match:
            continue
        raw_date = match.group("value").strip()
        try:
            parsed = date_parser.parse(raw_date, fuzzy=True).date()
        except (ValueError, OverflowError):
            continue
        label = match.group("label").strip().lower()
        extracted.append((label, parsed))
    return extracted


def _normalize_term(term: str) -> str:
    normalized = term.strip().lower()
    return _SIMPLE_TERM_MAP.get(normalized, normalized)


def _is_out_of_range(value_text: str, reference_range: str | None) -> bool | None:
    if reference_range is None:
        return None
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*[-]\s*(-?\d+(?:\.\d+)?)", reference_range)
    if not match:
        return None
    try:
        value = float(value_text)
        low = float(match.group(1))
        high = float(match.group(2))
    except ValueError:
        return None
    return value < low or value > high


def _classify_medication_action(page_text: str, offset: int) -> str:
    start_idx = max(0, offset - 60)
    context = page_text[start_idx : offset + 60].lower()
    if any(token in context for token in ("stopped", "discontinued", "stop ")):
        return "stopped"
    if any(token in context for token in ("started", "initiated", "new ")):
        return "started"
    return "mentioned"


def _looks_like_lab(test_name: str, unit: str | None, reference_range: str | None) -> bool:
    lowered = test_name.lower()
    if unit is not None or reference_range is not None:
        return True
    return any(keyword in lowered for keyword in _LAB_KEYWORDS)
