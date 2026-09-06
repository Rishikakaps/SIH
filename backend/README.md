# Rx Lens Backend

FastAPI backend for the SIH26047 Rx Lens POC.

OCR/document intelligence is the intentionally real capability in this POC. It uses EasyOCR locally for high-quality printed English PNG/JPG medical documents.

## Routes

- `POST /sessions`
- `POST /consent`
- `POST /sessions/mode`
- `POST /conversation/message`
- `POST /documents`
- `POST /documents/process`
- `GET /timeline/{session_id}`
- `GET /evidence/{session_id}`
- `GET /summary/{session_id}`
- `POST /physician/review`
- `POST /fhir/export`
- `POST /sync/mock`

## Tests

```bash
PYTHONPATH=. pytest
```

The OCR verification test uploads three generated image files through the API and checks that different visible HbA1c values are extracted as different structured lab facts.
