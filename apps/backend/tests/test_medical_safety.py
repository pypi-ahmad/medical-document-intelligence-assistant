from app.services.medical.safety import blocked_response_text, is_prohibited_medical_request


def test_blocks_diagnosis_and_treatment_requests() -> None:
    assert is_prohibited_medical_request("Can you diagnose my disease from these reports?")
    assert is_prohibited_medical_request("What treatment plan should I follow?")


def test_allows_document_understanding_questions() -> None:
    assert not is_prohibited_medical_request("What medications are listed in my documents?")
    assert "cannot provide diagnosis" in blocked_response_text().lower()
