# Verification report

Verified on Windows with Python 3.12, Node.js, and Edge in headless mode.

- Backend: 68 automated tests passed, including four tests running actual EasyOCR models.
- Document deletion: ownership/revision checks, source image removal, dependent facts/timeline removal, approval invalidation, and rejection of late AI results after deletion or edits.
- AI integration: separate suggestions, explicit external-processing consent, human confirmation before acceptance, original OCR retention, uncertainty notes/full text in the draft, duplicate request rejection, quota/key/timeout errors, and malformed/truncated output rejection. Transport tests use simulated Groq responses and verify that both the actual image and OCR are included, without exposing the key.
- Previous v2 browser verification (not rerun for v3): deletion/cancel on Documents, image rendering, AI opt-in, separate editable suggestions, confirmation before acceptance, unsaved-edit navigation blocking, physician draft, deletion on Review, and invalidation of prior approval/export passed. Desktop (1440px) and mobile (390px) screenshots were inspected; no page-level horizontal overflow was detected.
- OCR: extracted different HbA1c values (7.2, 9.1, 6.8) from generated PNG pixels; read the sample prescription/lab report; detected readable Hindi words from a Devanagari image; rejected a blank image.
- Validation: empty/corrupt/oversize uploads, blank answers, missing sessions, missing lab numbers, missing reference ranges, and multiple lab results.
- History: both modes support undo after completion, older-answer correction, branch replacement, preserved documents, and approval invalidation.
- Frontend: production build and TypeScript checks passed.
- Previous browser smoke test: duplicate start/answer clicks, language switching without data loss, both-mode correction, completion undo, editable multi-part speech transcripts, Hindi/English speech configuration, microphone-denial errors, real OCR, OCR correction, reject/amend/approve, JSON download, and simulated sync passed.
- Layout: desktop (1440px) and phone (390px) screenshots inspected. English and Hindi phone layouts had no document-level horizontal overflow.

Speech events were simulated for repeatable browser testing. Live microphone capture and external speech-service accuracy were not tested on the user's microphone. The app now invokes the real browser API, but results depend on the browser/service, permissions, microphone, connection, and speaker.

Version 3 live checks used the configured Groq key without printing or packaging it. A synthetic page produced focused patient/doctor/medicine/diagnosis/test sections. A public speech fixture from the Vosk project was transcribed through the real Whisper endpoint. These are integration checks, not a medical accuracy benchmark. The supplied personal prescription was not uploaded during this verification and its AI accuracy is unmeasured. The personal image, credentials, public audio fixture and scratch server are excluded from the ZIP.

Version 3 adds 15 speech API tests covering both consents, draft-only results, stale questions, file/language limits, multipart audio transport, provider errors, timeouts, invalid output and silence handling. Vision transport tests require the clinical schema and two image views. Production build and TypeScript checks passed after the final changes.

The final isolated browser server launch was denied by the execution environment, so v3 MediaRecorder capture, inline loading/error rendering and retry have not completed end-to-end browser verification. A prepared browser test exists in the development workspace, but no passing result is claimed. Live use of the user's physical microphone was not tested.

The Windows launchers were reviewed and their build/server commands exercised. The interactive installer UI and macOS/Linux/Docker launchers were not run end to end. OCR models and installed dependencies are intentionally excluded from the source ZIP and are downloaded during setup.
