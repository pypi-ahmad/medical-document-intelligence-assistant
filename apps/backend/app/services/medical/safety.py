"""Safety policy enforcement for educational-only medical assistant."""

from __future__ import annotations

from app.config import settings
from app.models.medical_schemas import SafetyEnvelope

_PROHIBITED_PATTERNS = [
    "diagnose",
    "diagnosis recommendation",
    "what disease do i have",
    "prescribe",
    "prescription for",
    "dosage should i take",
    "treatment plan",
    "which medicine should i start",
    "replace my doctor",
]


def build_safety_envelope() -> SafetyEnvelope:
    return SafetyEnvelope(
        disclaimer=settings.medical_disclaimer,
        prohibited_actions=[
            "No diagnosis",
            "No treatment recommendation",
            "No medication prescribing",
            "Not a substitute for licensed clinicians",
        ],
    )


def is_prohibited_medical_request(text: str) -> bool:
    normalized = text.lower().strip()
    return any(pattern in normalized for pattern in _PROHIBITED_PATTERNS)


def blocked_response_text() -> str:
    return (
        "I cannot provide diagnosis, treatment, or medication advice. "
        "I can help organize what your uploaded documents say and provide "
        "educational explanations. Please discuss decisions with a qualified clinician."
    )


def append_disclaimer(text: str) -> str:
    body = text.strip()
    disclaimer = settings.medical_disclaimer.strip()
    if disclaimer.lower() in body.lower():
        return body
    if body:
        return f"{body}\n\nDisclaimer: {disclaimer}"
    return f"Disclaimer: {disclaimer}"
