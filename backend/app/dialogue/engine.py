from __future__ import annotations

from .questions import AYUSH_PENDING_PHYSICIAN_FIELDS, FIELD_LABELS, PATHWAYS, ayush_pathway, base_pathway
from ..models import ClinicalFact, ClinicalMode, FactSource, Language, Session


HINDI_PROMPTS = {
    "chief_complaint": "आज आपको मुख्य तकलीफ क्या है?",
    "associated_symptoms": "क्या सांस फूलना, पसीना, बेहोशी या दर्द हाथ/जबड़े तक जा रहा है?",
    "allergies": "क्या आपको किसी दवा से एलर्जी है?",
}


def initialize_session(session: Session) -> Session:
    session.pending_fields = ayush_pathway() if session.mode == ClinicalMode.ayush else base_pathway()
    session.current_field = session.pending_fields[0]
    return session


def phrase_question(field: str, language: Language) -> str:
    if language == Language.hi and field in HINDI_PROMPTS:
        return HINDI_PROMPTS[field]
    return FIELD_LABELS.get(field, f"Please tell us about {field.replace('_', ' ')}.")


def options_for(field: str) -> list[str]:
    options = {
        "chief_complaint": ["Chest pain", "Fever", "Abdominal pain", "Headache"],
        "associated_symptoms": ["Breathlessness and sweating", "No breathlessness", "Pain moving to arm or jaw"],
        "allergies": ["No known allergies", "Penicillin allergy", "Not sure"],
        "medications": ["Metformin 500 mg", "Amlodipine 5 mg", "No regular medicines"],
        "prakriti_proxy": ["Dry skin and light sleep", "Heat intolerance and acidity", "Heaviness and slow digestion"],
    }
    return options.get(field, ["Yes", "No", "Not sure"])


def submit_turn(session: Session, content: str, input_type: str) -> tuple[ClinicalFact, Session]:
    if not session.current_field:
        session.completed = True
        raise ValueError("Interview already complete")

    asked_field = session.current_field
    field = _field_from_content(content) or asked_field
    fact = ClinicalFact(
        session_id=session.id,
        ontology_path=f"{session.mode}.{field}",
        label=field.replace("_", " ").title(),
        value=content,
        source=FactSource.patient_interview,
        confidence=1.0 if input_type == "tapped_option" else 0.88,
        metadata={"input_type": input_type},
    )

    if asked_field == "chief_complaint":
        pathway = _pathway_for_complaint(content)
        session.pending_fields = [f for f in session.pending_fields if f not in {asked_field, field}]
        for extra in pathway:
            if extra not in session.pending_fields:
                session.pending_fields.insert(0, extra)
    else:
        session.pending_fields = [f for f in session.pending_fields if f not in {asked_field, field}]

    session.current_field = session.pending_fields[0] if session.pending_fields else None
    session.completed = session.current_field is None
    return fact, session


def _pathway_for_complaint(content: str) -> list[str]:
    text = content.lower()
    for trigger, fields in PATHWAYS.items():
        if trigger in text:
            return fields
    return []


def _field_from_content(content: str) -> str | None:
    text = content.lower()
    if "allerg" in text:
        return "allergies"
    if any(term in text for term in ["metformin", "amlodipine", "medicine", "medication"]):
        return "medications"
    return None


def next_prompt(session: Session) -> dict[str, object]:
    return {
        "completed": session.completed,
        "current_field": session.current_field,
        "question": None if session.completed else phrase_question(session.current_field or "", session.language),
        "options": [] if session.completed else options_for(session.current_field or ""),
        "physician_pending_fields": AYUSH_PENDING_PHYSICIAN_FIELDS if session.mode == ClinicalMode.ayush else [],
    }
