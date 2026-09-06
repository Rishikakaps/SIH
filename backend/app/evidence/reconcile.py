from __future__ import annotations

from collections import defaultdict

from ..models import ClinicalFact, EvidenceRecord, EvidenceStatus, FactSource


def reconcile(session_id: str, facts: list[ClinicalFact]) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    groups: dict[str, list[ClinicalFact]] = defaultdict(list)
    for fact in facts:
        groups[fact.ontology_path.split(".")[-1]].append(fact)

    for key, grouped in groups.items():
        if key == "hba1c":
            value = float(grouped[0].value)
            low, high = grouped[0].metadata.get("reference_range", [0, 999])
            if value < low or value > high:
                records.append(EvidenceRecord(session_id=session_id, ontology_path=grouped[0].ontology_path, status=EvidenceStatus.out_of_range, message="HbA1c is outside the supplied reference range and requires physician review.", fact_ids=[f.id for f in grouped]))
            continue

        patient_values = [_normalize(f.value) for f in grouped if f.source == FactSource.patient_interview]
        document_values = [_normalize(f.value) for f in grouped if f.source in {FactSource.document, FactSource.lab}]
        if patient_values and document_values:
            conflict = any("no known" in v for v in patient_values) and any("allergy" in v and "penicillin" in v for v in document_values)
            status = EvidenceStatus.conflict if conflict or set(patient_values) != set(document_values) else EvidenceStatus.consistent
            message = "Discrepancy noted; physician verification required." if status == EvidenceStatus.conflict else "Patient report and document evidence are consistent."
            records.append(EvidenceRecord(session_id=session_id, ontology_path=grouped[0].ontology_path, status=status, message=message, fact_ids=[f.id for f in grouped]))
        else:
            records.append(EvidenceRecord(session_id=session_id, ontology_path=grouped[0].ontology_path, status=EvidenceStatus.unverified, message="Evidence captured and awaiting physician review.", fact_ids=[f.id for f in grouped]))
    return records


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace(".", "").split())
