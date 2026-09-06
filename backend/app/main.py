from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .clinical.rules import evaluate_red_flags
from .dialogue.engine import initialize_session, next_prompt, submit_turn
from .documents.service import create_demo_documents, process_document
from .evidence.reconcile import reconcile
from .fhir.service import build_bundle
from .models import ClinicalMode, Consent, Language, Patient, PhysicianReview, Session
from .store import store
from .summary.service import generate_summary

app = FastAPI(title="Rx Lens API", version="0.1.0-poc")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class CreateSessionRequest(BaseModel):
    patient_id: str | None = None
    language: Language = Language.en
    mode: ClinicalMode = ClinicalMode.general_medicine


class ConsentRequest(BaseModel):
    session_id: str
    scope: list[str]
    language: Language = Language.en


class MessageRequest(BaseModel):
    session_id: str
    input_type: str
    content: str


class ReviewRequest(BaseModel):
    session_id: str
    physician_id: str
    edits: dict = {}
    decision: str


class ExportRequest(BaseModel):
    session_id: str


class ModeRequest(BaseModel):
    session_id: str
    mode: ClinicalMode


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sessions", status_code=201)
def create_session(body: CreateSessionRequest) -> dict[str, object]:
    patient = Patient(id=body.patient_id) if body.patient_id else Patient()
    store.patients[patient.id] = patient
    session = initialize_session(Session(patient_id=patient.id, language=body.language, mode=body.mode))
    store.sessions[session.id] = session
    store.log("system", "session.created", session.id, mode=session.mode, language=session.language)
    return {"session": session, "patient": patient, "next": next_prompt(session)}


@app.post("/consent", status_code=201)
def record_consent(body: ConsentRequest) -> Consent:
    session = _session(body.session_id)
    consent = Consent(session_id=session.id, scope=body.scope, language=body.language)
    session.consent = consent
    store.consents[session.id] = consent
    store.log("patient", "consent.granted", session.id, scope=body.scope)
    return consent


@app.post("/sessions/mode")
def select_mode(body: ModeRequest) -> dict[str, object]:
    session = _consented_session(body.session_id)
    if store.facts[session.id]:
        raise HTTPException(409, "Mode cannot be changed after interview starts")
    session.mode = body.mode
    initialize_session(session)
    store.log("patient", "session.mode_selected", session.id, mode=body.mode)
    return {"session": session, "next": next_prompt(session)}


@app.post("/conversation/message")
def conversation_message(body: MessageRequest) -> dict[str, object]:
    session = _consented_session(body.session_id)
    fact, session = submit_turn(session, body.content, body.input_type)
    store.facts[session.id].append(fact)
    new_flags = evaluate_red_flags(session.id, store.facts[session.id], {flag.code for flag in store.flags[session.id]})
    store.flags[session.id].extend(new_flags)
    store.log("patient", "fact.recorded", fact.id, ontology_path=fact.ontology_path)
    for flag in new_flags:
        store.log("system", "red_flag.raised", flag.id, code=flag.code)
    return {"fact": fact, "next": next_prompt(session), "flags": store.flags[session.id]}


@app.post("/documents", status_code=202)
async def upload_document(session_id: str = Form(...), doc_type_hint: str | None = Form(None), file: UploadFile = File(...)) -> dict[str, object]:
    _consented_session(session_id)
    raw = await file.read()
    doc, facts, timeline = process_document(session_id, file.filename or "document.png", doc_type_hint, raw=raw)
    store.documents[session_id].append(doc)
    store.facts[session_id].extend(facts)
    store.timeline[session_id].extend(timeline)
    store.evidence[session_id] = reconcile(session_id, store.facts[session_id])
    store.log("patient", "document.processed", doc.id, filename=doc.filename)
    return {"document": doc, "facts": facts, "evidence": store.evidence[session_id]}


@app.post("/documents/process")
def process_demo_document(body: ExportRequest) -> dict[str, object]:
    _consented_session(body.session_id)
    docs_dir = Path(__file__).resolve().parents[2] / "demo_documents"
    created_paths = create_demo_documents(docs_dir)
    processed = []
    all_facts = []
    for path in created_paths:
        doc_type = "lab_report" if "lab" in path.name else "prescription"
        doc, facts, timeline = process_document(body.session_id, path.name, doc_type, raw=path.read_bytes())
        store.documents[body.session_id].append(doc)
        store.facts[body.session_id].extend(facts)
        store.timeline[body.session_id].extend(timeline)
        processed.append(doc)
        all_facts.extend(facts)
    store.evidence[body.session_id] = reconcile(body.session_id, store.facts[body.session_id])
    return {"documents": processed, "facts": all_facts, "evidence": store.evidence[body.session_id]}


@app.get("/patients/{patient_id}")
def patient_record(patient_id: str) -> dict[str, object]:
    patient = store.patients.get(patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    return {"patient": patient}


@app.get("/timeline/{session_id}")
def timeline(session_id: str) -> list:
    _session(session_id)
    return sorted(store.timeline[session_id], key=lambda ev: (ev.date == "unknown", ev.date))


@app.get("/evidence/{session_id}")
def evidence(session_id: str) -> list:
    _session(session_id)
    store.evidence[session_id] = reconcile(session_id, store.facts[session_id])
    return store.evidence[session_id]


@app.get("/summary/{session_id}")
def summary(session_id: str) -> dict[str, object]:
    session = _session(session_id)
    ev = reconcile(session_id, store.facts[session_id])
    store.evidence[session_id] = ev
    return generate_summary(session, store.facts[session_id], store.flags[session_id], ev)


@app.post("/physician/review")
def physician_review(body: ReviewRequest) -> PhysicianReview:
    _session(body.session_id)
    review = PhysicianReview(**body.model_dump())
    store.reviews[body.session_id] = review
    store.log("physician", "review.submitted", body.session_id, decision=body.decision)
    return review


@app.post("/fhir/export")
def fhir_export(body: ExportRequest) -> dict[str, object]:
    session = _session(body.session_id)
    review = store.reviews.get(session.id)
    if not review or review.decision != "accept":
        raise HTTPException(403, "Physician approval required before FHIR export")
    patient = store.patients[session.patient_id]
    return build_bundle(patient, session, store.facts[session.id], review)


@app.post("/sync/mock")
def sync_mock(body: ExportRequest) -> dict[str, object]:
    session = _session(body.session_id)
    session.synced = True
    store.log("system", "fhir.mock_synced", session.id)
    return {"status": "success", "endpoint": "mock ABDM/HIS", "session_id": session.id}


def _session(session_id: str) -> Session:
    session = store.sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


def _consented_session(session_id: str) -> Session:
    session = _session(session_id)
    if not session.consent:
        raise HTTPException(403, "Consent required before clinical data capture")
    return session
