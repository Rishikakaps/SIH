from __future__ import annotations
import re
from ..models import ClinicalFact, ClinicalFlag


def evaluate_red_flags(session_id: str, facts: list[ClinicalFact], existing_codes: set[str]) -> list[ClinicalFlag]:
    # Limited demo rule. Discard explicit negations before checking positive symptoms.
    def positive(value):
        text = value.lower()
        text = re.sub(r"(?:no|not|without|denies)\s+(?:(?:any|having)\s+)?(?:chest pain|breathlessness|breathless|sweating)(?:\s+(?:or|and)\s+(?:breathlessness|sweating))?", "", text)
        text = re.sub(r"(?:साँस|सांस)\s+नहीं\s+फूलती|(?:साँस|सांस)\s+फूलना\s+नहीं|पसीना\s+नहीं(?:\s+आता)?|(?:सीने|छाती)\s+में\s+दर्द\s+नहीं", "", text)
        return text
    texts = [(f, positive(f.value)) for f in facts]
    chest = [f.id for f, t in texts if any(s in t for s in ["chest pain", "pain in my chest", "सीने में दर्द", "छाती में दर्द"])]
    breath = [f.id for f, t in texts if any(s in t for s in ["breathless", "sweating", "सांस फूल", "साँस फूल", "पसीना"])]
    if chest and breath and "RF_CHEST_PAIN_DYSPNEA" not in existing_codes:
        return [ClinicalFlag(session_id=session_id, code="RF_CHEST_PAIN_DYSPNEA", reason="Chest pain with breathlessness or sweating requires priority triage verification.", triggering_fact_ids=list(dict.fromkeys(chest + breath)))]
    return []
