# Update and enable AI image review

**For version 3, read [V3_START_HERE.md](V3_START_HERE.md) first.** It covers the clinical focus, visible AI button status, and new recorded voice input.

This version adds document deletion and optional image-based OCR correction through the Groq API. Local OCR and manual correction continue to work without an API key. The earlier interface, history correction, language switching, and speech fixes are included.

## Update your existing Windows installation

1. Download and fully extract `SIH-main-v3-clinical-voice.zip`.
2. Stop your running backend and frontend with Ctrl+C in both terminals. Download any records you need first: sessions are stored in memory and disappear when the backend stops.
3. Copy the **contents** of the new `SIH-main` folder into your existing project folder (for example `D:\SIH\SIH-main-fixed\SIH-main`). Replace matching files. Keep your existing `.venv`, `backend\.ocr-models`, and `backend\.env` if present. These are not in the ZIP, so normal copy-and-replace preserves them.
4. In that existing project folder, double-click **update-windows.cmd**. Keep internet connected. This installs updated dependencies and rebuilds the interface; it reuses your existing Python environment and OCR models.
5. Follow the API setup below, then run **start-backend.cmd** and **start-frontend.cmd**. Open http://localhost:3000 and refresh the page.

For a fresh installation, install Python 3.12 and Node.js 22 with npm, reopen your terminal, and run **setup-windows.cmd** instead. First setup downloads packages and OCR models and can take several minutes. See README.md for the complete usage guide. If a download times out, rerun the same setup/update launcher; downloads have longer timeouts and retries.

## Enable the free API

1. Create a Groq account and an API key at https://console.groq.com/keys. Use the **Free plan**; no paid upgrade is required for its available quota.
2. Double-click **configure-ai.cmd** in the project folder. Paste the key when prompted; characters are hidden. Press Enter. Do not paste your key into chat or frontend code.
3. Restart the backend and refresh the app. The key is read from `backend\.env` and stays on the backend. Never share that file with your ZIP.

The default vision model is `qwen/qwen3.6-27b`. Model availability and free usage limits are controlled by Groq; see https://console.groq.com/docs/rate-limits. The app reports quota or model errors and has no automatic paid fallback. Keep your Groq account on the Free plan if you want to avoid paid usage. This is a preview model; `GROQ_VISION_MODEL` in `backend\.env` can be changed to a compatible Groq vision model if needed.

On macOS/Linux, copy `backend/.env.example` to `backend/.env`, fill in `GROQ_API_KEY`, and restart the backend. For Docker, supply it at runtime using `docker compose --env-file backend/.env -f docker/docker-compose.yml up --build`. Keys are excluded from Docker builds.

## Review a document

1. Upload a PNG/JPG in **Documents**, then continue to **Review**.
2. Compare **Original image** with **Saved OCR text**. Zoom the original as needed. You can edit and save the local OCR directly.
3. To request AI assistance, tick **Send this image and its saved OCR text to Groq**, then click **Review image with AI**. Save or discard manual edits first. Only this selected image and its saved OCR text are sent; the interview and other documents are not included.
4. Read the separate **AI suggested text** and **Check these unclear areas**. Compare against the image and edit the suggestion. Names, medicine strengths, decimals, dates, and handwritten instructions need particular attention. Keep unreadable passages marked `[unclear]`.
5. Tick the human-review confirmation, then click **Accept reviewed text**. Until then, the suggestion has not replaced your saved OCR. You can ignore it and keep the saved version.
6. Continue to **Prepare physician draft**. The draft includes the full saved transcription and uncertainty notes as well as the supported structured fields. A changed document requires a fresh physician approval.

For the supplied English/Gujarati prescription style, choose **English document** for initial local OCR, then use AI image review for the multilingual page. The local OCR language selector currently supports English and Hindi, not Gujarati. AI review reads the actual image and is instructed to preserve Gujarati/Hindi script and flag unclear handwriting rather than infer missing text. It can still make mistakes; it cannot guarantee error-free transcription.

## Delete an uploaded document

Click **Delete document** next to it on either **Documents** or **Review**, then **Delete permanently**. **Keep document** cancels. Deletion removes the original image, OCR, pending suggestion, extracted facts, and timeline entries from this local session. It also invalidates any previous physician approval/export in the app. Previously downloaded JSON files are separate files and are not erased.

## Data and troubleshooting

- Images and records are stored in backend memory; restarting clears them. Refreshing the page begins a new browser flow.
- AI review is an external API action. It requires the separate checkbox for the document. Provider retention is governed by Groq, not the local Delete button. Groq documents its data controls and optional Zero Data Retention at https://console.groq.com/docs/your-data.
- **AI not configured:** run configure-ai.cmd, restart the backend, refresh the page. Ensure you configured the same project folder whose backend you started.
- **Key rejected:** check the key/account/model access in Groq, then rerun configure-ai.cmd.
- **Usage limit reached:** wait for your quota to reset or use manual correction. Retrying immediately will not bypass the limit.
- **Timeout, incomplete, or invalid review:** nothing is applied. Retry later, retake a clearer image, or edit manually.
- **Old interface still showing:** stop both old servers, run update-windows.cmd in the correct folder, restart both, and refresh localhost:3000.

Version 3 was tested with 68 backend tests, a production build, live Groq review of synthetic clinical data, and live transcription of public test audio. Accuracy on your prescription and physical microphone is unmeasured. See TESTING.md for browser verification limits.
