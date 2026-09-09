"use client";
import { useEffect, useRef, useState } from "react";

type Recording = { blob: Blob; existing: string; session: string; revision: number };

export function useRecordedSpeech(api: string, language: "en" | "hi", context: string,
  session: string | undefined, revision: number, allowExternal: boolean, setText: (text: string) => void) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);
  const [hasRecording, setHasRecording] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const audio = useRef<AudioContext | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const request = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const active = useRef(false);
  const saved = useRef<Recording | null>(null);
  const consent = useRef(allowExternal); consent.current = allowExternal;
  const updateText = useRef(setText); updateText.current = setText;
  const t = (en: string, hi: string) => language === "hi" ? hi : en;

  function releaseMicrophone() {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    stream.current?.getTracks().forEach(track => track.stop()); stream.current = null;
    void audio.current?.close().catch(() => {}); audio.current = null;
    setLevel(0);
  }
  function cancel() {
    generation.current++;
    request.current?.abort(); request.current = null;
    const current = recorder.current; recorder.current = null;
    if (current) { current.ondataavailable = current.onstop = current.onerror = null; if (current.state !== "inactive") current.stop(); }
    releaseMicrophone(); saved.current = null; active.current = false;
    setHasRecording(false); setListening(false); setProcessing(false); setStarting(false); setSeconds(0);
  }
  useEffect(() => {
    setSupported(window.isSecureContext && typeof navigator.mediaDevices?.getUserMedia === "function" && typeof window.MediaRecorder === "function");
    setError("");
    return cancel;
  }, [language, context, allowExternal]);

  async function transcribe(recording: Recording, token: number) {
    if (token !== generation.current || !consent.current) return;
    active.current = true; setProcessing(true); setError("");
    const controller = new AbortController(); request.current = controller;
    const timeout = setTimeout(() => controller.abort(), 130000);
    try {
      const form = new FormData();
      form.append("session_id", recording.session); form.append("revision", String(recording.revision));
      // This value comes from the unchecked-by-default, explicit recording consent checkbox.
      form.append("allow_external_processing", String(consent.current)); form.append("language", "auto");
      const extension = recording.blob.type.includes("mp4") ? "mp4" : recording.blob.type.includes("ogg") ? "ogg" : "webm";
      form.append("file", recording.blob, `recording.${extension}`);
      const response = await fetch(`${api}/speech/transcribe`, { method: "POST", body: form, signal: controller.signal });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new Error(typeof result?.detail === "string" ? result.detail : "Transcription failed. Please retry.");
      if (typeof result?.text !== "string" || !result.text.trim()) throw new Error("No speech returned. Record again.");
      if (token !== generation.current || !consent.current) return;
      const combined = [recording.existing.trim(), result.text.trim()].filter(Boolean).join(" ");
      if (combined.length > 5000) throw new Error("This answer exceeds 5000 characters. Shorten the typed answer or record less speech.");
      updateText.current(combined); saved.current = null; setHasRecording(false);
    } catch (caught) {
      if (token === generation.current) setError(caught instanceof Error && caught.name !== "AbortError" ? caught.message : t("Transcription timed out. Retry the recording.", "आवाज़ को पाठ में बदलने में समय लगा। फिर कोशिश करें।"));
    } finally {
      clearTimeout(timeout);
      if (token === generation.current) { request.current = null; active.current = false; setProcessing(false); }
    }
  }
  async function start(existing: string) {
    if (active.current || !session || !consent.current) return;
    cancel(); const token = generation.current; active.current = true;
    setStarting(true); setListening(true); setError("");
    window.speechSynthesis?.cancel();
    try {
      const mic = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true }, video: false });
      if (token !== generation.current || !consent.current) { mic.getTracks().forEach(track => track.stop()); return; }
      stream.current = mic;
      const mime = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus", "audio/webm"].find(value => MediaRecorder.isTypeSupported(value));
      const current = new MediaRecorder(mic, mime ? { mimeType: mime, audioBitsPerSecond: 64000 } : undefined);
      recorder.current = current;
      const chunks: Blob[] = []; let bytes = 0;
      current.ondataavailable = event => { if (event.data.size) { chunks.push(event.data); bytes += event.data.size; if (bytes > 11 * 1024 * 1024 && current.state === "recording") current.stop(); } };
      current.onerror = () => { cancel(); setError(t("The microphone stopped unexpectedly. Check the device and record again.", "माइक्रोफ़ोन बंद हो गया। उपकरण जाँचकर फिर रिकॉर्ड करें।")); };
      current.onstop = () => {
        if (token !== generation.current || !consent.current) return;
        recorder.current = null; releaseMicrophone(); setListening(false); setStarting(false);
        const blob = new Blob(chunks, { type: current.mimeType || mime || "audio/webm" });
        if (blob.size < 64 || blob.size > 12 * 1024 * 1024) { active.current = false; setError(t("Recording was empty or too large. Please record again.", "रिकॉर्डिंग खाली या बहुत बड़ी है। फिर रिकॉर्ड करें।")); return; }
        const recording = { blob, existing, session, revision };
        saved.current = recording; setHasRecording(true); void transcribe(recording, token);
      };
      current.start(250); setStarting(false);
      let analyser: AnalyserNode | undefined;
      try { const ac = new AudioContext(); audio.current = ac; analyser = ac.createAnalyser(); analyser.fftSize = 256; ac.createMediaStreamSource(mic).connect(analyser); void ac.resume().catch(() => {}); } catch { /* Recording works even when the meter is unavailable. */ }
      const started = Date.now(); const samples = new Uint8Array(256);
      timer.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - started) / 1000); setSeconds(elapsed);
        if (analyser) { analyser.getByteTimeDomainData(samples); const rms = Math.sqrt(samples.reduce((sum, value) => sum + ((value - 128) / 128) ** 2, 0) / samples.length); setLevel(Math.min(1, rms * 6)); }
        if (elapsed >= 90 && current.state === "recording") current.stop();
      }, 100);
    } catch (caught) {
      if (token !== generation.current) return;
      cancel();
      const name = caught instanceof Error ? caught.name : "";
      setError(name === "NotAllowedError" ? t("Allow microphone access in browser site settings and Windows privacy settings, then retry.", "ब्राउज़र और Windows सेटिंग में माइक्रोफ़ोन की अनुमति देकर फिर कोशिश करें।") : name === "NotFoundError" ? t("No microphone found. Connect one and retry.", "माइक्रोफ़ोन नहीं मिला। जोड़कर फिर कोशिश करें।") : t("Cannot open the microphone. Close other recording apps and use Chrome or Edge at localhost:3000.", "माइक्रोफ़ोन शुरू नहीं हुआ। अन्य रिकॉर्डिंग ऐप बंद करें और localhost:3000 पर Chrome या Edge उपयोग करें।"));
    }
  }
  function stop() { if (recorder.current?.state === "recording") recorder.current.stop(); else if (starting) cancel(); }
  return { supported, listening, processing, starting, error, seconds, level, hasRecording, start, stop, cancel,
    retry: () => { if (!active.current && saved.current && consent.current) void transcribe(saved.current, generation.current); } };
}
