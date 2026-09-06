# Rx Lens

Rx Lens is a Smart India Hackathon SIH26047 proof of concept for a patient-facing clinical case-taking platform. It helps prepare a physician-ready case summary before consultation by combining guided patient history, document OCR, evidence checks, physician review, and FHIR-style export.

## SIH Problem

- Problem Statement ID: 26047
- Title: Patient Case-Taking Software
- Organization: Ministry of Ayush
- Department: All India Institute of Ayurveda
- Theme: MedTech / BioTech / HealthTech

## What This POC Implements

- Next.js patient kiosk and physician review frontend
- FastAPI backend for sessions, consent, history, documents, summary, FHIR export, and mock sync
- Consent gate before clinical intake
- General Medicine golden path with red-flag detection
- AYUSH intake mode with physician-pending assessment fields
- Real EasyOCR document OCR for high-quality printed English medical images
- Structured extraction of labs, medications, allergies, abnormal values, conflicts, and timeline evidence
- Physician amend/reject/approve workflow
- FHIR-like bundle generation only after physician approval
- Mock ABDM/HIS sync

## POC Boundaries

This is a hackathon POC, not a production clinical device.

- ABHA/ABDM identity is sandboxed.
- ABDM/HIS sync is simulated.
- Storage is in-memory.
- Voice input is a sandbox interaction.
- OCR is real local EasyOCR for printed English medical documents; Hindi OCR is experimental.
- Clinical reasoning is deterministic/rule-based and doctor-supervised.

## Run Locally

Start the backend in one terminal:

```bash
cd /Users/rishika/Documents/Codex/2026-08-29/files-mentioned-by-the-user-sih/outputs/rx-lens-full
bash start-backend.sh
```

Start the frontend in a second terminal:

```bash
cd /Users/rishika/Documents/Codex/2026-08-29/files-mentioned-by-the-user-sih/outputs/rx-lens-full
bash start-frontend.sh
```

Open:

```text
http://localhost:3000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Demo Flow

1. Identify: continue with demo ABHA.
2. Consent: tick consent and continue.
3. Mode: choose General Medicine or AYUSH.
4. History: answer guided questions. For the red-flag path, choose chest pain and breathlessness/sweating.
5. Documents: upload a PNG/JPG medical document or run the included demo documents through OCR.
6. Review: inspect OCR text, structured facts, conflicts, abnormal values, and evidence.
7. Physician: amend, reject, or approve the draft.
8. Sync: export the FHIR-like bundle and simulate ABDM/HIS sync.
9. Architecture: view what is real versus sandboxed in the POC.

## Verification

Backend:

```bash
cd backend
PYTHONPATH=. pytest -q
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

The backend test suite includes a real OCR proof: it creates visually similar lab-report PNGs with different HbA1c values, uploads them through the document endpoint, and checks that OCR extracts the different values from the image pixels.
