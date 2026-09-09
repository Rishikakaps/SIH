from __future__ import annotations

from ..models import ClinicalFact, ClinicalFlag, EvidenceRecord, Session


def generate_summary(session: Session, facts: list[ClinicalFact], flags: list[ClinicalFlag], evidence: list[EvidenceRecord]) -> dict[str, object]:
    by_label = {fact.label: fact for fact in facts}
    sections = {
        "chief_complaint": _fact_line(by_label.get("Chief Complaint")),
        "hpi": [_fact_line(f) for f in facts if f.ontology_path.split(".")[-1] in {"onset", "location", "character", "radiation", "severity", "duration", "associated_symptoms"}],
        "medications": [_fact_line(f) for f in facts if "medications" in f.ontology_path],
        "allergies": [_fact_line(f) for f in facts if "allergies" in f.ontology_path],
        "investigations": [_fact_line(f) for f in facts if "investigations" in f.ontology_path],
        "evidence": [{"status": ev.status, "message": ev.message, "fact_ids": ev.fact_ids} for ev in evidence],
        "red_flags": [flag.model_dump() for flag in flags],
        "mode": session.mode,
        "patient_history": [{"field": f.label, **_fact_line(f)} for f in facts if f.source == "patient_interview"],
        "traceable_fact_ids": [fact.id for fact in facts],
    }
    return {"label": "AI-generated draft - physician verification required", "sections": sections}


def _fact_line(fact: ClinicalFact | None) -> dict[str, str] | None:
    if fact is None:
        return None
    return {"text": fact.value, "fact_id": fact.id, "source": fact.source}
