import pytest

from app.services.medical.extraction import extract_entities_from_pages
from app.services.ocr.base import OCRPageResult


@pytest.mark.asyncio
async def test_extract_entities_and_labs_and_medications() -> None:
    page = OCRPageResult(
        page_index=0,
        text=(
            "Patient Name: John Doe\n"
            "Patient ID: MRN-12345\n"
            "Sex: Male\n"
            "Age: 47\n"
            "Visit Date: 2026-02-14\n"
            "Procedure: Coronary angiography\n"
            "Vaccination: Influenza booster\n"
            "Diagnosis: Hypertension\n"
            "Allergy: Penicillin\n"
            "Hemoglobin: 11.2 g/dL (12.0-16.0)\n"
            "Metformin 500 mg BID\n"
            "Medication started on 2026-02-14"
        ),
        confidence=0.91,
    )

    bundle = extract_entities_from_pages([page])

    assert any(entity["entity_type"] == "diagnosis_mentioned" for entity in bundle.entities)
    assert any(entity["entity_type"] == "allergy" for entity in bundle.entities)
    assert any(entity["entity_type"] == "patient_name" for entity in bundle.entities)
    assert any(entity["entity_type"] == "patient_id" for entity in bundle.entities)
    assert any(entity["entity_type"] == "patient_age" for entity in bundle.entities)
    assert any(entity["entity_type"] == "patient_sex" for entity in bundle.entities)
    assert any(entity["entity_type"] == "procedure" for entity in bundle.entities)
    assert any(entity["entity_type"] == "vaccination" for entity in bundle.entities)
    assert any(entity["entity_type"] == "visit_date" for entity in bundle.entities)
    assert any(lab["test_name"] == "hemoglobin" for lab in bundle.labs)
    assert any(lab["is_out_of_range"] is True for lab in bundle.labs)
    assert any(med["medication_name"].lower() == "metformin" for med in bundle.medications)
    assert any(event["event_type"] == "lab_test" for event in bundle.timeline_events)
    assert any(event["event_type"] == "doctor_visit" for event in bundle.timeline_events)
    assert any(event["event_type"] == "procedure" for event in bundle.timeline_events)
    assert any(event["event_type"] == "vaccination" for event in bundle.timeline_events)
