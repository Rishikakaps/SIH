"use client";
import { useEffect, useRef, useState } from "react";

type Recognition = {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void; stop(): void; abort(): void;
};
type SpeechWindow = Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };

export function useSpeech(language: "en" | "hi", context: string, setText: (text: string) => void) {
  const ref = useRef<Recognition | null>(null);
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");
  const updateText = useRef(setText);
  updateText.current = setText;
  function cancel() {
    const recognition = ref.current;
    ref.current = null;
    if (recognition) {
      recognition.onresult = recognition.onerror = recognition.onend = null;
      recognition.abort();
    }
    setListening(false);
  }
  useEffect(() => {
    const win = window as SpeechWindow;
    setSupported(Boolean(win.SpeechRecognition || win.webkitSpeechRecognition));
    setError("");
    return cancel;
  }, [language, context]);
  function start(existingText: string) {
    if (ref.current) return;
    const win = window as SpeechWindow;
    const Constructor = win.SpeechRecognition || win.webkitSpeechRecognition;
    if (!Constructor) return;
    window.speechSynthesis?.cancel();
    const recognition = new Constructor();
    ref.current = recognition;
    recognition.lang = language === "hi" ? "hi-IN" : "en-IN";
    recognition.continuous = true;
    recognition.interimResults = true;
    setError("");
    let heard = false;
    let failed = false;
    recognition.onresult = (event) => {
      if (ref.current !== recognition) return;
      const transcript = Array.from(event.results).map(result => result[0].transcript).join(" ").trim();
      heard = heard || Boolean(transcript);
      updateText.current([existingText.trim(), transcript].filter(Boolean).join(" "));
    };
    recognition.onerror = (event) => {
      failed = true;
      const messages: Record<string, [string, string]> = {
        "not-allowed": ["Microphone access was denied. Allow it in browser site settings, then retry.", "माइक्रोफ़ोन की अनुमति नहीं मिली। ब्राउज़र की साइट सेटिंग में अनुमति देकर फिर कोशिश करें।"],
        "audio-capture": ["No microphone found. Connect one or type your answer.", "माइक्रोफ़ोन नहीं मिला। इसे जोड़ें या उत्तर लिखें।"],
        "network": ["The speech service could not connect. Check your internet connection or type your answer.", "वॉइस सेवा से संपर्क नहीं हुआ। इंटरनेट जाँचें या उत्तर लिखें।"],
        "no-speech": ["No speech detected. Try again or type your answer.", "आवाज़ सुनाई नहीं दी। फिर कोशिश करें या उत्तर लिखें।"],
      };
      if (event.error !== "aborted") setError((messages[event.error] || ["Speech recognition stopped. Retry or type your answer.", "वॉइस पहचान रुक गई। फिर कोशिश करें या उत्तर लिखें।"])[language === "hi" ? 1 : 0]);
    };
    recognition.onend = () => {
      if (ref.current !== recognition) return;
      ref.current = null;
      setListening(false);
      if (!heard && !failed) setError(language === "hi" ? "कोई आवाज़ नहीं मिली। फिर कोशिश करें या लिखें।" : "No speech captured. Try again or type your answer.");
    };
    try { setListening(true); recognition.start(); }
    catch { cancel(); setError(language === "hi" ? "माइक्रोफ़ोन शुरू नहीं हुआ। फिर कोशिश करें।" : "Could not start the microphone. Please retry."); }
  }
  return { supported, listening, error, start, stop: () => ref.current?.stop(), cancel };
}
