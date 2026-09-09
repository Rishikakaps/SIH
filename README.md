# Rx Lens — clinical image review and recorded voice (v3)

A bilingual patient intake demo for General Medicine and AYUSH, with editable history, browser speech input, document OCR, physician review, and a downloadable demo record.

**Updating an existing installation? Start with [V3_START_HERE.md](V3_START_HERE.md) for the latest fixes and exact update steps.** This version adds deletion on Documents and Review, original-image comparison with zoom, and optional OCR suggestions through Groq's free-tier vision API. Run `configure-ai.cmd` to add your own free API key; every suggestion requires your review before acceptance.

## Start here on Windows

1. Extract the ZIP completely. Open the extracted `SIH-main` folder. Do not run files from inside the ZIP preview.
2. Install **Python 3.12** from https://www.python.org/downloads/ and **Node.js 22 LTS** from https://nodejs.org/. Include the Python launcher and npm in their installers. Reopen your terminal afterward.
3. Double-click **`setup-windows.cmd`** once. It creates `.venv`, installs Python and frontend packages, builds the app, and downloads the English and Hindi OCR models. Keep internet connected; first setup can take several minutes and requires several GB of free disk space. If it reports a failure, fix the displayed issue and run it again.
4. Double-click **`start-backend.cmd`**. Leave that terminal running.
5. Double-click **`start-frontend.cmd`**. Leave this second terminal running too.
6. Open **http://localhost:3000** in Chrome. Edge can be used for the interface; availability of speech recognition depends on the browser and its speech service.

On subsequent runs, only steps 4–6 are needed. To stop, press Ctrl+C in both terminals. After editing frontend source, run `npm run build` inside `frontend` before restarting it.

## How to use it

1. Click **Start your visit**, read the consent information, tick the checkbox, and continue. The patient is the included demo identity, Rajesh Sharma.
2. Choose **General medicine** or **AYUSH care**.
3. Pick a suggested answer, type your own answer, or use **Speak your answer**. Suggestions only select an answer: **Save & continue** submits it. You can change a selection before submitting.
4. For voice, select **Record & transcribe · Groq API**, enable the separate recording consent checkbox, then allow microphone access. Speak naturally, press **Stop recording**, wait for transcription, review or edit it, then press **Save & continue**. This uses your configured Groq key and supports natural speech with automatic language detection. Each recording answers the current question. A failed transcription can be retried or discarded. The older browser speech service is available as an optional method.
5. Use **English / हिन्दी** in the top right at any stage. Questions, suggestions, saved option labels, and main controls switch language without resetting the session. The optional browser speech method uses `en-IN` or `hi-IN`; API transcription detects the spoken language automatically. Free-text answers, source documents, and clinical JSON are preserved in their original language; this switch is not a general-purpose translation service.
6. To correct the last submitted answer, press **Back**. To edit an older answer, choose **Edit** in Saved answers or Review, then **Reopen answer**. The chosen answer is prefilled; that answer and subsequent interview answers reopen so an obsolete branch cannot remain in the record. Uploaded documents are retained. A changed record needs physician review again.
7. To change modes, choose **Care mode** in the progress list. If you have already answered questions, confirm **Change mode & restart**. This clears interview answers, keeps documents, and invalidates old approval. Selecting the same mode resumes it.
8. At Documents, select the **document language** separately from the interface language. Use **English document** for English reports, and **Hindi / mixed Hindi and English** for Hindi text. Upload a clear upright PNG/JPG, up to 10 MB and 20 megapixels. PDFs must be exported to images first. You can add multiple images, try the two included sample documents, or continue without documents.
9. At Review, compare extracted text with the original image beside it. Correct mistakes and click **Save corrected text**, or request **Review image with AI** after configuring your Groq key. AI output is a separate editable suggestion; compare it with the image, confirm your review, then accept it. Saving reruns structured extraction, replaces old document facts, and updates evidence. **Delete document** is available on both Documents and Review. The confidence percentage describes local OCR output; it is not a guarantee of medical accuracy.
10. Choose **Prepare physician draft**. The physician can amend the draft, reject it, or approve it. After rejection, edit the draft to enable approval again. Approval creates a downloadable JSON record; **Simulate hospital sync** is a demo action.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| Start button shows a connection error | Start the backend and open http://127.0.0.1:8000/health. It should show `{"status":"ok"}`. Check the backend terminal if it does not. |
| Address already in use | Close the old terminal/server occupying port 3000 or 8000, then restart. |
| Microphone permission denied | Allow microphone access in the browser's site settings and Windows microphone privacy settings. Retry the button. |
| Speech is unavailable or shows a network error | Use Chrome on `http://localhost:3000`, check internet connectivity, and allow microphone access. Speech support and availability vary. Typing remains available. |
| Hindi speech is poor | Select हिन्दी before recording, use a quiet room, and correct the transcript before saving. Mixed-language speech and names may need editing. |
| Read aloud fails | Install a voice for the selected language in the operating system/browser, or read the question on screen. |
| OCR is unavailable | From the project folder run `.\.venv\Scripts\python.exe backend\setup_ocr.py` while connected to the internet. This retries model downloads. Restart the backend afterward. |
| OCR numbers/text are wrong | Select the correct document language; retake a clear, well-lit, upright photo; then use the editable text preview. English reports should use the English model. |
| No clinical fields were extracted | Raw OCR still appears. The parser recognizes supported English labels such as `Diagnosis:`, `Medication:`, `Allergy:`, and HbA1c with `Value:` / `Reference range:`. It does not interpret every report layout or Hindi clinical fields. |
| Page was refreshed / backend restarted | The app is an in-memory demo. Page refresh starts a new browser flow; backend restart removes server records. Download needed exports before closing. |

Default voice input records audio and sends it to Groq after explicit recording consent and Stop; it uses the backend Groq key. The optional browser speech method uses Web Speech API and may send audio to the browser provider without a project key. Real live microphone accuracy cannot be guaranteed for every accent, language mix, browser, or environment. See [MDN's SpeechRecognition documentation](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition).

Initial OCR runs locally with EasyOCR after the initial model download. English and Hindi models are selected separately to avoid the Hindi recognizer confusing English medical numerals. Optional AI review sends the selected image and its saved OCR to Groq only after the document's separate opt-in. Handwriting, poor photos, mixed-language pages, and unusual tables still require careful correction. See [EasyOCR documentation](https://www.jaided.ai/easyocr/documentation/) and [AI setup and review instructions](UPDATE_AND_AI_SETUP.md).

## macOS / Linux

Install Python 3.12 and Node.js 22 with npm, then run from the extracted folder:

```bash
bash setup.sh
```

Start each server in its own terminal:

```bash
bash start-backend.sh
```

```bash
bash start-frontend.sh
```

Open http://localhost:3000. On some Linux distributions you may need the Python venv package and system OpenGL/GLib libraries required by the OCR dependencies.

## Developer setup without the launchers

Windows PowerShell, from `SIH-main`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe backend\setup_ocr.py
cd frontend
npm ci
npm run build
```

The launchers use a single backend worker because storage is in memory. The frontend proxies `/api` to `http://127.0.0.1:8000`. Override `API_BASE_URL` before building/running if needed. `NEXT_PUBLIC_API_BASE_URL` remains supported for an explicit direct browser API URL.

Optional Docker configuration is in `docker/docker-compose.yml`. Run `docker compose -f docker/docker-compose.yml up --build` from the root. Docker setup is provided but was not executed in the Windows verification environment. The first OCR request downloads its selected model into the named Docker volume. No unused PostgreSQL service is included.

## Tests

From `backend`, with the project virtual environment:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

The `ocr` tests run real image recognition. To check logic without OCR models:

```powershell
..\.venv\Scripts\python.exe -m pytest -m "not ocr" -q
```

From `frontend`:

```powershell
npm run typecheck
npm run build
```

The optional browser smoke script uses Playwright and installed Edge. With both servers running:

```powershell
npm install --no-save playwright
node tests/ui-smoke.cjs
```

Set `BROWSER_CHANNEL=chrome` to use installed Chrome instead. This script injects a mock speech recognizer to exercise transcript accumulation, language choice, permissions errors, and manual confirmation. It does not validate a live microphone or the external speech service. OCR in this browser test uses the real backend.

## What changed

- Responsive interface with consistent spacing, larger controls, progress navigation, bilingual screens, and mobile layouts.
- Start/submit actions use a synchronous in-flight guard and disabled states; backend answer revisions reject stale duplicate submissions.
- Complete question and option translations for both pathways; language changes update the active session.
- Previous-answer and older-answer correction in both modes, including after completion; mode changes can restart the interview while retaining documents.
- Real browser speech input replacing the hard-coded chest-pain transcript, with continuous results, editable preview, error messages, cleanup, and typing fallback.
- Validated image uploads, English/Hindi OCR model selection, Windows font support, readable failures, confidence display, and editable OCR results.
- Missing lab values stay unknown, missing reference ranges no longer crash, and each lab result is evaluated separately.
- Correct question order and answers tied to the question asked. Free-form complaints receive follow-up questions.
- History/document changes recalculate evidence and flags and clear obsolete approval/sync state. Complete patient history is included in the draft.
- Portable launchers, a working same-origin API proxy, current instructions, and regression coverage.

## Demo limits

This remains the original hackathon proof of concept. ABHA identity and hospital sync are simulated; there is no production identity service, login, persistent database, or certified clinical decision system. Flags and clinical field extraction are limited deterministic rules. The JSON export is a FHIR-style demo bundle, not a validated ABDM integration. All clinical interpretation requires physician review. Use sample data for the demo.

Interactive API documentation is available at http://127.0.0.1:8000/docs while the backend is running. The supplied `docs/spec/13_API_SPEC.yaml` is the original specification; the running API docs describe the updated endpoints.
