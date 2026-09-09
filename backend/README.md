# Backend

See the project-root README.md for setup and usage. Use Python 3.12 and the root `.venv`.

Start from this folder: `../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` (Windows: `..\.venv\Scripts\python.exe`).

Run `python setup_ocr.py` with this environment before the first OCR request. Models are cached in `backend/.ocr-models`.

Live API docs: http://127.0.0.1:8000/docs

Added endpoints:
- `POST /sessions/language`: change UI/interview language without resetting history.
- `POST /conversation/rewind`: reopen a fact and all subsequent interview answers using the current revision.
- `POST /documents/{document_id}/text`: correct document text and regenerate dependent facts/evidence.
- `DELETE /documents/{document_id}`: JSON body with session_id and document revision; removes image, document facts, and timeline entries, invalidating approval.
- `GET /documents/{document_id}/image?session_id=...`: consent/ownership checked original image with no-store headers.
- `GET /ai/status`: provider, model, and configured boolean; never returns the key.
- `POST /documents/{document_id}/ai-review`: JSON body with session_id, document revision, and allow_external_processing=true. Stores a separate suggestion, never changes saved OCR automatically.

AI acceptance uses the text endpoint with revision, ai_suggestion_id, and confirm_reviewed=true. Stale, deleted, concurrent, or incomplete results are rejected. Full saved document text and uncertainty notes are included in the physician draft. API setup and data flow are documented in ../UPDATE_AND_AI_SETUP.md.

Mode selection accepts `reset_history`; message submission accepts a revision; document upload accepts `ocr_language` (`en` or `hi`). Server records and approvals are held in memory. Restarting the backend resets them.

Version 3: `POST /speech/transcribe` accepts multipart session_id, revision, language (auto/en/hi), allow_external_processing, and an audio file up to 12 MB. It requires session consent and separate external-processing consent. It returns an unsaved transcript and rejects stale question revisions. Audio is passed directly to Groq without application disk storage. `GROQ_SPEECH_MODEL` defaults to whisper-large-v3. Vision review now validates seven clinical sections and omits irrelevant letterhead.
