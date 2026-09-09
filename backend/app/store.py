from __future__ import annotations

from collections import defaultdict

from .models import (
    AuditEvent,
    ClinicalFact,
    ClinicalFlag,
    Consent,
    DocumentRecord,
    EvidenceRecord,
    Patient,
    PhysicianReview,
    Session,
    TimelineEvent,
)


class MemoryStore:
    def __init__(self) -> None:
        self.patients: dict[str, Patient] = {}
        self.sessions: dict[str, Session] = {}
        self.consents: dict[str, Consent] = {}
        self.facts: dict[str, list[ClinicalFact]] = defaultdict(list)
        self.flags: dict[str, list[ClinicalFlag]] = defaultdict(list)
        self.documents: dict[str, list[DocumentRecord]] = defaultdict(list)
        self.document_images: dict[str, bytes] = {}
        self.evidence: dict[str, list[EvidenceRecord]] = defaultdict(list)
        self.timeline: dict[str, list[TimelineEvent]] = defaultdict(list)
        self.reviews: dict[str, PhysicianReview] = {}
        self.audit: list[AuditEvent] = []

    def log(self, actor: str, action: str, entity_id: str, **details: object) -> None:
        self.audit.append(AuditEvent(actor=actor, action=action, entity_id=entity_id, details=details))

    def reset(self) -> None:
        self.__init__()


store = MemoryStore()
