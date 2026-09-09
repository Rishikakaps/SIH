from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .clinical.rules import evaluate_red_flags
from .ai.ocr_review import configuration, review_image, ReviewUnavailable
from .ai.transcription import transcribe_audio, MAX_AUDIO_BYTES
from .dialogue.engine import initialize_session, next_prompt, submit_turn
from .dialogue.engine import phrase_question
from .dialogue.localization import choices
from .documents.service import create_demo_documents, process_document
from .evidence.reconcile import reconcile
from .fhir.service import build_bundle
from .models import ClinicalMode, Consent, FactSource, Language, Patient, PhysicianReview, Session
from .store import store
from .summary.service import generate_summary

app = FastAPI(title="Rx Lens API", version="0.1.0-poc")
state_lock = RLock()
ai_inflight: set[str] = set()
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
    input_type: Literal["tapped_option", "typed_text", "voice_transcript"]
    content: str = Field(min_length=1, max_length=5000)
    revision: int | None = None


class ReviewRequest(BaseModel):
    session_id: str
    physician_id: str
    edits: dict = {}
    decision: Literal["accept", "reject"]


class ExportRequest(BaseModel):
    session_id: str


class ModeRequest(BaseModel):
    session_id: str
    mode: ClinicalMode
    reset_history: bool = False


class LanguageRequest(BaseModel):
    session_id: str
    language: Language


class RewindRequest(BaseModel):
    session_id: str
    fact_id: str
    revision: int


class DocumentEditRequest(BaseModel):
    session_id: str
    text: str = Field(min_length=1, max_length=100000)
    revision: int | None = None
    ai_suggestion_id: str | None = None
    confirm_reviewed: bool = False


class DocumentActionRequest(BaseModel):
    session_id: str
    revision: int


class AiReviewRequest(DocumentActionRequest):
    allow_external_processing: bool = False


def _invalidate(session: Session):
    store.reviews.pop(session.id, None)
    session.synced = False
    session.revision += 1
    store.flags[session.id] = evaluate_red_flags(session.id, store.facts[session.id], set())
    store.evidence[session.id] = reconcile(session.id, store.facts[session.id])


def _state(session: Session):
    facts = []
    for fact in store.facts[session.id]:
        item = fact.model_dump()
        field = fact.metadata.get("field")
        if fact.source == FactSource.patient_interview and field:
            item["question"] = phrase_question(field, session.language)
            values = choices(field)
            item["display_value"] = choices(field, session.language == Language.hi)[values.index(fact.value)] if fact.value in values else fact.value
        facts.append(item)
    return {"session": session, "next": next_prompt(session), "facts": facts,
            "flags": store.flags[session.id], "documents": [{**d.model_dump(), "source_available": d.id in store.document_images} for d in store.documents[session.id]],
            "evidence": store.evidence[session.id]}


@app.post("/sessions/language")
def change_language(body: LanguageRequest):
    with state_lock:
        session = _session(body.session_id)
        session.language = body.language
        return _state(session)


@app.post("/conversation/rewind")
def rewind(body: RewindRequest):
    with state_lock:
        session = _consented_session(body.session_id)
        if session.revision != body.revision:
            raise HTTPException(409, "History changed. Please reload the current session.")
        history = [f for f in store.facts[session.id] if f.source == FactSource.patient_interview]
        index = next((i for i, f in enumerate(history) if f.id == body.fact_id), None)
        if index is None:
            raise HTTPException(404, "Answer not found")
        initialize_session(session)
        for fact in history[:index]:
            submit_turn(session, fact.value, fact.metadata.get("input_type", "typed_text"))
        store.facts[session.id] = history[:index] + [f for f in store.facts[session.id] if f.source != FactSource.patient_interview]
        _invalidate(session)
        store.log("patient", "history.rewound", session.id, fact_id=body.fact_id)
        return {**_state(session), "previous_answer": history[index].value}


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
    with state_lock:
        session = _consented_session(body.session_id)
        if session.mode == body.mode:
            return _state(session)
        history = [f for f in store.facts[session.id] if f.source == FactSource.patient_interview]
        if history and not body.reset_history:
            raise HTTPException(409, "Confirm reset_history to change mode and restart the interview")
        store.facts[session.id] = [f for f in store.facts[session.id] if f.source != FactSource.patient_interview]
        session.mode = body.mode
        initialize_session(session)
        _invalidate(session)
        store.log("patient", "session.mode_selected", session.id, mode=body.mode)
        return _state(session)


@app.post("/conversation/message")
def conversation_message(body: MessageRequest) -> dict[str, object]:
    with state_lock:
        session = _consented_session(body.session_id)
        if body.revision is not None and body.revision != session.revision:
            raise HTTPException(409, "This answer was already submitted or the question changed.")
        try:
            fact, session = submit_turn(session, body.content, body.input_type)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        store.facts[session.id].append(fact)
        _invalidate(session)
        store.log("patient", "fact.recorded", fact.id, ontology_path=fact.ontology_path)
        return {**_state(session), "fact": fact}


@app.post("/documents", status_code=202)
async def upload_document(session_id: str = Form(...), doc_type_hint: str | None = Form(None), ocr_language: Literal["en", "hi"] = Form("en"), file: UploadFile = File(...)) -> dict[str, object]:
    _consented_session(session_id)
    raw = await file.read(10 * 1024 * 1024 + 1)
    await file.close()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "Please upload an image smaller than 10 MB.")
    try:
        doc, facts, timeline = await run_in_threadpool(process_document, session_id, file.filename or "document.png", doc_type_hint, raw=raw, ocr_language=ocr_language)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    store.documents[session_id].append(doc)
    store.document_images[doc.id] = raw
    store.facts[session_id].extend(facts)
    store.timeline[session_id].extend(timeline)
    _invalidate(_session(session_id))
    store.log("patient", "document.processed", doc.id, filename=doc.filename)
    return {**_state(_session(session_id)), "document": doc}


@app.post("/documents/process")
def process_demo_document(body: ExportRequest) -> dict[str, object]:
    _consented_session(body.session_id)
    docs_dir = Path(__file__).resolve().parents[2] / "demo_documents"
    created_paths = create_demo_documents(docs_dir)
    processed = []
    all_facts = []
    all_timeline = []
    images = {}
    for path in created_paths:
        doc_type = "lab_report" if "lab" in path.name else "prescription"
        try:
            doc, facts, timeline = process_document(body.session_id, path.name, doc_type, raw=path.read_bytes())
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc
        all_timeline.extend(timeline)
        processed.append(doc)
        images[doc.id] = path.read_bytes()
        all_facts.extend(facts)
    store.documents[body.session_id].extend(processed)
    store.document_images.update(images)
    store.facts[body.session_id].extend(all_facts)
    store.timeline[body.session_id].extend(all_timeline)
    _invalidate(_session(body.session_id))
    return _state(_session(body.session_id))


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
    result = generate_summary(session, store.facts[session_id], store.flags[session_id], ev)
    result["sections"]["documents"] = [{"filename": d.filename, "text": d.ocr_text, "review_status": d.status, "review_notes": d.review_notes} for d in store.documents[session_id]]
    return result


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
    review = store.reviews.get(session.id)
    if not review or review.decision != "accept":
        raise HTTPException(403, "Current physician approval is required before sync")
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


@app.post("/documents/{document_id}/text")
def correct_document(document_id: str, body: DocumentEditRequest):
    with state_lock:
        session = _consented_session(body.session_id)
        doc = next((d for d in store.documents[session.id] if d.id == document_id), None)
        if doc is None:
            raise HTTPException(404, "Document not found")
        if body.revision is not None and body.revision != doc.revision:
            raise HTTPException(409, "Document changed. Reload it before saving.")
        if body.ai_suggestion_id:
            if not body.confirm_reviewed:
                raise HTTPException(400, "Review the image and confirm the suggested text before saving.")
            if not doc.ai_suggestion or doc.ai_suggestion["id"] != body.ai_suggestion_id or doc.ai_suggestion["base_revision"] != doc.revision:
                raise HTTPException(409, "This AI suggestion is no longer current. Run a new review.")
        if not body.text.strip():
            raise HTTPException(422, "Document text cannot be empty")
        updated, facts, timeline = process_document(session.id, doc.filename, doc.doc_type_hint, text=body.text)
        for fact in facts:
            fact.source_ref = doc.id
            fact.metadata["manually_corrected"] = True
            if body.ai_suggestion_id:
                fact.metadata["ai_assisted_human_reviewed"] = True
            fact.confidence = doc.confidence
        for event in timeline:
            event.source_ref = doc.id
        doc.ocr_text = updated.ocr_text
        doc.extracted = updated.extracted
        doc.status = "ai_reviewed_by_user" if body.ai_suggestion_id else "manually_corrected"
        doc.revision += 1
        doc.review_notes = [f"{u['location']}: {u['reason']}" for u in doc.ai_suggestion["uncertainties"]] if body.ai_suggestion_id else []
        doc.ai_suggestion = None
        store.facts[session.id] = [f for f in store.facts[session.id] if f.source_ref != doc.id] + facts
        store.timeline[session.id] = [t for t in store.timeline[session.id] if t.source_ref != doc.id] + timeline
        _invalidate(session)
        return _state(session)


@app.get("/ai/status")
def ai_status():
    return configuration()


@app.post("/speech/transcribe")
async def transcribe_recording(session_id: str = Form(...), revision: int = Form(...),
                               allow_external_processing: bool = Form(False),
                               language: Literal["auto", "en", "hi"] = Form("auto"),
                               file: UploadFile = File(...)):
    with state_lock:
        session = _consented_session(session_id)
        if not allow_external_processing:
            raise HTTPException(400, "Confirm sending this recording to Groq for transcription.")
        if session.revision != revision:
            raise HTTPException(409, "The question changed. Record your answer again.")
    try:
        raw = await file.read(MAX_AUDIO_BYTES + 1)
    finally:
        await file.close()
    if len(raw) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Recording too large. Keep each answer under 90 seconds.")
    if len(raw) < 64:
        raise HTTPException(422, "Recording was empty or too short. Record again.")
    try:
        text = await run_in_threadpool(transcribe_audio, raw, language)
    except ReviewUnavailable as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    with state_lock:
        if _consented_session(session_id).revision != revision:
            raise HTTPException(409, "The question changed during transcription. The result was discarded.")
    return {"text": text, "provider": "Groq", "saved": False}


@app.post("/documents/{document_id}/ai-review")
def ai_review(document_id: str, body: AiReviewRequest):
    with state_lock:
        session = _consented_session(body.session_id)
        doc = next((d for d in store.documents[session.id] if d.id == document_id), None)
        if doc is None:
            raise HTTPException(404, "Document not found")
        if not body.allow_external_processing:
            raise HTTPException(400, "Confirm sending this document image and OCR text to Groq for AI review.")
        if doc.revision != body.revision:
            raise HTTPException(409, "Document changed. Reload it before AI review.")
        raw = store.document_images.get(document_id)
        if raw is None:
            raise HTTPException(409, "Original image unavailable. Upload the document again for image-based AI review.")
        if document_id in ai_inflight:
            raise HTTPException(409, "AI review is already running for this document.")
        if doc.ai_suggestion and doc.ai_suggestion["base_revision"] == doc.revision:
            return _state(session)
        snapshot_text = doc.ocr_text
        ai_inflight.add(document_id)
    try:
        try:
            suggestion = review_image(raw, snapshot_text)
        except ReviewUnavailable as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc
        with state_lock:
            current = next((d for d in store.documents[session.id] if d.id == document_id), None)
            if current is None:
                raise HTTPException(404, "Document was deleted while AI review ran. The result was discarded.")
            if current.revision != body.revision:
                raise HTTPException(409, "Document changed while AI review ran. The result was discarded.")
            current.ai_suggestion = {**suggestion, "id": uuid4().hex, "base_revision": current.revision,
                                     "provider": "Groq", "model": configuration()["model"]}
            store.log("system", "document.ai_suggested", document_id)
            return _state(session)
    finally:
        with state_lock:
            ai_inflight.discard(document_id)


@app.get("/documents/{document_id}/image")
def document_image(document_id: str, session_id: str):
    _consented_session(session_id)
    if not any(d.id == document_id for d in store.documents[session_id]):
        raise HTTPException(404, "Document not found")
    raw = store.document_images.get(document_id)
    if raw is None:
        raise HTTPException(404, "Original image unavailable. Upload the document again.")
    return Response(raw, media_type="image/png" if raw.startswith(b"\x89PNG") else "image/jpeg", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@app.delete("/documents/{document_id}")
def delete_document(document_id: str, body: DocumentActionRequest):
    with state_lock:
        session = _consented_session(body.session_id)
        doc = next((d for d in store.documents[session.id] if d.id == document_id), None)
        if doc is None:
            raise HTTPException(404, "Document not found")
        if doc.revision != body.revision:
            raise HTTPException(409, "Document changed. Reload it before deleting.")
        store.documents[session.id] = [d for d in store.documents[session.id] if d.id != document_id]
        store.document_images.pop(document_id, None)
        store.facts[session.id] = [f for f in store.facts[session.id] if f.source_ref != document_id]
        store.timeline[session.id] = [t for t in store.timeline[session.id] if t.source_ref != document_id]
        _invalidate(session)
        store.log("patient", "document.deleted", document_id)
        return _state(session)
