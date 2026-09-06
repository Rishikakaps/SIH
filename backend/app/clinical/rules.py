from __future__ import annotations

from ..models import ClinicalFact, ClinicalFlag


def evaluate_red_flags(session_id: str, facts: list[ClinicalFact], existing_codes: set[str]) -> list[ClinicalFlag]:
    text = " ".join(f.value.lower() for f in facts)
    new_flags: list[ClinicalFlag] = []
    if "RF_CHEST_PAIN_DYSPNEA" not in existing_codes:
        has_chest_pain = "chest pain" in text or "सीने" in text
        has_dyspnea = any(term in text for term in ["breathless", "breathlessness", "sweating", "sweaty", "सांस", "पसीना"])
        if has_chest_pain and has_dyspnea:
            new_flags.append(
                ClinicalFlag(
                    session_id=session_id,
                    code="RF_CHEST_PAIN_DYSPNEA",
                    reason="Chest pain with breathlessness or sweating requires priority triage verification.",
                    triggering_fact_ids=[f.id for f in facts if any(term in f.value.lower() for term in ["chest pain", "breath", "sweat", "सीने", "सांस", "पसीना"])],
                )
            )
    return new_flags
