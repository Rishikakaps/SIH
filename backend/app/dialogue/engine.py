from __future__ import annotations

from .questions import AYUSH_PENDING_PHYSICIAN_FIELDS, FIELD_LABELS, PATHWAYS, ayush_pathway, base_pathway
from .localization import HINDI_PROMPTS, choices
from ..models import ClinicalFact, ClinicalMode, FactSource, Language, Session


def initialize_session(session: Session) -> Session:
    session.pending_fields = ayush_pathway() if session.mode == ClinicalMode.ayush else base_pathway()
    session.current_field = session.pending_fields[0]
    session.completed = False
    return session


def phrase_question(field: str, language: Language) -> str:
    return HINDI_PROMPTS[field] if language == Language.hi else FIELD_LABELS[field]


def submit_turn(session: Session, content: str, input_type: str) -> tuple[ClinicalFact, Session]:
    if not session.current_field:
        raise ValueError("Interview already complete")
    content = content.strip()
    if not content:
        raise ValueError("Please enter an answer")
    field = session.current_field
    fact = ClinicalFact(
        session_id=session.id, ontology_path=f"{session.mode}.{field}",
        label=field.replace("_", " ").title(), value=content,
        source=FactSource.patient_interview,
        metadata={"input_type": input_type, "field": field, "language": session.language},
    )
    session.pending_fields = session.pending_fields[1:]
    if field == "chief_complaint":
        extras = _pathway_for_complaint(content)
        session.pending_fields = extras + [f for f in session.pending_fields if f not in extras]
    session.current_field = session.pending_fields[0] if session.pending_fields else None
    session.completed = session.current_field is None
    return fact, session


def _pathway_for_complaint(content: str) -> list[str]:
    text = content.lower()
    aliases = {"chest pain": ["chest pain", "pain in my chest", "सीने में दर्द", "छाती में दर्द", "seene", "chhati"],
               "fever": ["fever", "बुखार", "bukhar"],
               "abdominal pain": ["abdominal pain", "stomach pain", "पेट में दर्द", "pet mein dard"],
               "headache": ["headache", "head ache", "सिरदर्द", "सिर में दर्द", "sar dard"]}
    for key, terms in aliases.items():
        if any(term in text for term in terms):
            return PATHWAYS[key].copy()
    return ["onset", "duration", "severity", "associated_symptoms"]


def next_prompt(session: Session) -> dict[str, object]:
    field = session.current_field or ""
    return {
        "completed": session.completed, "current_field": session.current_field,
        "question": None if session.completed else phrase_question(field, session.language),
        "options": [] if session.completed else choices(field),
        "option_labels": [] if session.completed else choices(field, session.language == Language.hi),
        "remaining": len(session.pending_fields),
        "physician_pending_fields": AYUSH_PENDING_PHYSICIAN_FIELDS if session.mode == ClinicalMode.ayush else [],
    }
