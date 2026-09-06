from __future__ import annotations

from ..models import ClinicalFact, Patient, PhysicianReview, Session


def build_bundle(patient: Patient, session: Session, facts: list[ClinicalFact], review: PhysicianReview | None = None) -> dict[str, object]:
    entries = [
        {
            "resource": {
                "resourceType": "Patient",
                "id": patient.id,
                "identifier": [{"system": "https://healthid.ndhm.gov.in", "value": patient.abha_id}],
                "name": [{"text": patient.name}],
                "extension": [{"url": "https://rxlens.example/mode", "valueString": session.mode}],
            }
        },
        {"resource": {"resourceType": "Encounter", "id": session.id, "status": "finished", "subject": {"reference": f"Patient/{patient.id}"}}},
    ]
    for fact in facts:
        entries.append({"resource": _resource_for_fact(fact, patient)})
    if review and review.edits.get("summary_text"):
        entries.append(
            {
                "resource": {
                    "resourceType": "Composition",
                    "id": f"approved-summary-{session.id}",
                    "status": "final",
                    "type": {"text": "Physician-approved clinical history summary"},
                    "subject": {"reference": f"Patient/{patient.id}"},
                    "author": [{"display": review.physician_id}],
                    "title": "Physician Verified Rx Lens Summary",
                    "section": [{"title": "Approved Summary", "text": {"status": "generated", "div": str(review.edits["summary_text"])}}],
                }
            }
        )
    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}


def _resource_for_fact(fact: ClinicalFact, patient: Patient) -> dict[str, object]:
    subject = {"reference": f"Patient/{patient.id}"}
    if "allergies" in fact.ontology_path:
        return {"resourceType": "AllergyIntolerance", "id": fact.id, "patient": subject, "code": {"text": fact.value}}
    if "medications" in fact.ontology_path:
        return {"resourceType": "MedicationStatement", "id": fact.id, "status": "recorded", "subject": subject, "medicationCodeableConcept": {"text": fact.value}}
    if "investigations" in fact.ontology_path:
        return {"resourceType": "Observation", "id": fact.id, "status": "preliminary", "subject": subject, "code": {"text": fact.label}, "valueString": fact.value}
    return {"resourceType": "Observation", "id": fact.id, "status": "preliminary", "subject": subject, "code": {"text": fact.label}, "valueString": fact.value}
