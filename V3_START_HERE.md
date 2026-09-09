# Version 3: AI review button, clinical OCR and voice input

## Install this update

1. Fully extract **SIH-main-v3-clinical-voice.zip**.
2. Stop the existing backend and frontend using Ctrl+C in both terminals. Export anything you need first; restarting the backend clears its in-memory sessions.
3. Copy the new **SIH-main** folder's contents into your current project folder, replacing matching files. Keep `.venv`, `backend/.ocr-models` and `backend/.env`; none are included in this ZIP.
4. Double-click **update-windows.cmd** in that existing project folder. Wait for **Update complete**.
5. Start **start-backend.cmd** and **start-frontend.cmd**, then refresh http://localhost:3000. Do not leave the old servers running on ports 8000/3000.

Your existing Groq key works for both features. You do not need to create another key. If starting fresh, run **setup-windows.cmd**, then **configure-ai.cmd**. Use Groq's Free plan to stay within its free quota.

To verify you are running the new backend, open http://127.0.0.1:8000/ai/status. It should include `"version":"3"` and `"review_focus":"clinical"`. The interview should have a **Voice input method** selector. If either is missing, the old server or old build is still running.

## AI image review

Upload your image, open **Review**, check the separate image-sharing checkbox and click **Review image with AI**.

The button now changes to **Reading clinical details…**, with a spinner and elapsed time beside it. On failure, an error appears **inside the same AI panel**, with the saved text kept intact. Once the cause is resolved, click the same button to retry. Repeated clicks are blocked while the request runs. The frontend proxy allows time for the backend's AI request to finish or return a useful error.

AI reads two overlapping close views covering the whole page and organizes its suggestion into:

- Patient details, age and date
- Treating doctor, using the signature/stamp where identifiable
- Diagnoses and history as written
- Medicines, strengths and visible directions
- Handwritten notes, including margins and stop/change instructions
- Vitals, tests and follow-up

Addresses, phone numbers, advertisements and unrelated staff directories are omitted. Printed medicines and handwritten changes are kept distinguishable. Unreadable words are marked `[unclear]`; absent sections are marked `[not shown]`. No medicine, dose or diagnosis should be inferred from customary treatment.

The page explicitly labels **local OCR** versus a completed **AI suggestion**. The old noisy OCR does not disappear when you click: the AI suggestion appears separately below it. Compare and edit that suggestion, check the human-review confirmation, then click **Accept reviewed text** to replace the saved text. Original OCR remains available for comparison.

## Voice input

1. On the interview screen, keep **Record & transcribe · Groq API** selected under **Voice input method**.
2. Check **Send my recording to Groq for transcription when I press Stop**.
3. Click **Speak your answer** and allow microphone access in the browser. Record for up to 90 seconds. Watch the level meter: if it remains flat while speaking, check the selected microphone in browser/Windows settings.
4. Click **Stop recording**. The microphone is released and the recording is sent for transcription. Wait for the transcript, review/edit it, then click **Save & continue**.

This route uses microphone recording plus Groq's Whisper API, so it does not depend on the browser speech service that produced the connection error. It accepts natural speech, with automatic language detection for English, Hindi and mixed speech. Accuracy still varies with audio quality, language and names.

If transcription fails, **Retry transcription** resends the retained recording, so you need not speak again. **Discard recording** clears it; if used during recording, no upload starts. Discarding after an upload has started cannot undo data already sent. Audio is not saved to the app's disk or patient record. A successful transcript remains an editable draft until you submit it. Short recordings still count toward Groq's audio quota.

**Browser speech service** remains an optional method. It may send audio to the browser provider and can still fail to connect in some browsers. The default API method is the fix for that dependency, not a guarantee that every microphone or network will work.

## Verification and limits

68 backend tests and the frontend production build passed. A live Groq image request using a synthetic clinical page returned the important sections, and a live Whisper request transcribed a public speech test fixture. The user's prescription was not sent during this verification; its AI accuracy remains unmeasured. No physical microphone accuracy claim is made.

The final local browser test server launch was blocked by the execution environment, so the new browser recording and inline feedback flows have not completed end-to-end browser verification. See TESTING.md for the precise scope.

Groq documentation: [speech transcription](https://console.groq.com/docs/speech-to-text), [vision](https://console.groq.com/docs/vision), [free-tier limits](https://console.groq.com/docs/rate-limits), [data controls](https://console.groq.com/docs/your-data). The app has no paid-provider fallback. Medical handwriting, medicine details and numbers still require human checking.
