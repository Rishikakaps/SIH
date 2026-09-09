from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Language(StrEnum):
    hi = "hi"
    en = "en"


class ClinicalMode(StrEnum):
    general_medicine = "general_medicine"
    ayush = "ayush"


class FactSource(StrEnum):
    patient_interview = "patient_interview"
    document = "document"
    lab = "lab"
    system = "system"
    physician_verified = "physician_verified"


class EvidenceStatus(StrEnum):
    consistent = "CONSISTENT"
    conflict = "CONFLICT"
    out_of_range = "OUT_OF_RANGE"
    missing = "MISSING"
    unverified = "UNVERIFIED"


class Patient(BaseModel):
    id: str = Field(default_factory=lambda: f"pat_{uuid4().hex[:10]}")
    name: str = "Rajesh Sharma"
    age: int = 56
    sex: str = "Male"
    abha_id: str = "DEMO-ABHA-91-2481-5574"
    opd: str = "General Medicine"


class Consent(BaseModel):
    session_id: str
    scope: list[str]
    language: Language
    granted_at: str = Field(default_factory=now_iso)
    revoked_at: str | None = None


class Session(BaseModel):
    id: str = Field(default_factory=lambda: f"ses_{uuid4().hex[:10]}")
    patient_id: str
    language: Language = Language.en
    mode: ClinicalMode = ClinicalMode.general_medicine
    created_at: str = Field(default_factory=now_iso)
    consent: Consent | None = None
    current_field: str | None = None
    pending_fields: list[str] = Field(default_factory=list)
    completed: bool = False
    synced: bool = False
    revision: int = 0


class ClinicalFact(BaseModel):
    id: str = Field(default_factory=lambda: f"fact_{uuid4().hex[:10]}")
    session_id: str
    ontology_path: str
    label: str
    value: str
    source: FactSource
    confidence: float = 1.0
    source_ref: str | None = None
    recorded_at: str = Field(default_factory=now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClinicalFlag(BaseModel):
    id: str = Field(default_factory=lambda: f"flag_{uuid4().hex[:10]}")
    session_id: str
    code: str
    severity: str = "urgent"
    reason: str
    triggering_fact_ids: list[str]
    created_at: str = Field(default_factory=now_iso)


class DocumentRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"doc_{uuid4().hex[:10]}")
    session_id: str
    filename: str
    doc_type_hint: str | None = None
    status: str = "processed"
    ocr_text: str
    original_ocr_text: str = ""
    revision: int = 0
    ai_suggestion: dict[str, Any] | None = None
    review_notes: list[str] = Field(default_factory=list)
    confidence: float = 0.94
    extracted: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)


class EvidenceRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"ev_{uuid4().hex[:10]}")
    session_id: str
    ontology_path: str
    status: EvidenceStatus
    message: str
    fact_ids: list[str]
    created_at: str = Field(default_factory=now_iso)


class TimelineEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"time_{uuid4().hex[:10]}")
    session_id: str
    date: str
    date_precision: str = "day"
    title: str
    details: str
    source_ref: str


class PhysicianReview(BaseModel):
    session_id: str
    physician_id: str
    edits: dict[str, Any] = Field(default_factory=dict)
    decision: str
    reviewed_at: str = Field(default_factory=now_iso)


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"audit_{uuid4().hex[:10]}")
    actor: str
    action: str
    entity_id: str
    at: str = Field(default_factory=now_iso)
    details: dict[str, Any] = Field(default_factory=dict)
