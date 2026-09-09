"use client";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, Languages, LoaderCircle, Mic, Pencil, Stethoscope, Trash2, Sparkles } from "lucide-react";
import type { Doc, Lang } from "./page";

export function Welcome({ language, busy, start }: { language: Lang; busy: boolean; start: () => void }) {
  const t = (en: string, hi: string) => language === "hi" ? hi : en;
  return <><div className="hero panel"><div className="hero-copy"><span className="badge"><span className="dot" />{t("A little preparation. Better care.", "थोड़ी तैयारी। बेहतर देखभाल।")}</span><h2>{t("Let’s make your next visit ", "अपनी अगली मुलाक़ात ")}<em>{t("feel simpler.", "आसान बनाएँ।")}</em></h2><p>{t("Tell us how you’re feeling, add your medical documents, and help your doctor see the complete picture.", "अपनी तकलीफ़ बताएँ, चिकित्सा दस्तावेज़ जोड़ें और डॉक्टर को पूरी जानकारी समझने में मदद करें।")}</p><button className="primary start-button" disabled={busy} onClick={start}>{busy ? <LoaderCircle className="spin" size={20} /> : <ArrowRight size={20} />}{t("Start your visit", "अपनी मुलाक़ात शुरू करें")}</button><small>{t("No sign-up needed · Uses a demo patient", "पंजीकरण की ज़रूरत नहीं · डेमो मरीज़ का उपयोग")}</small></div><div className="visit-card"><div className="visit-icon"><Stethoscope size={40} strokeWidth={1.4} /></div><span className="eyebrow">{t("YOUR VISIT AT A GLANCE", "आपकी मुलाक़ात की एक झलक")}</span><h3>{t("More time for what matters.", "ज़रूरी बातों के लिए अधिक समय।")}</h3>{[[t("Share your story", "अपनी बात बताएँ"),t("Speak, type, or choose an answer", "बोलें, लिखें या उत्तर चुनें")],[t("Bring your records", "अपने रिकॉर्ड जोड़ें"),t("Read text from medical documents", "चिकित्सा दस्तावेज़ों से पाठ पढ़ें")],[t("Review together", "मिलकर समीक्षा करें"),t("A clear draft for your physician", "आपके डॉक्टर के लिए स्पष्ट मसौदा")]].map(([title, text], i) => <div className="visit-row" key={title}><span>{i + 1}</span><div><strong>{title}</strong><p>{text}</p></div></div>)}</div></div><div className="feature-row"><div><Languages /><strong>{t("English & Hindi", "अंग्रेज़ी और हिन्दी")}</strong><p>{t("Switch languages at any point", "किसी भी समय भाषा बदलें")}</p></div><div><Mic /><strong>{t("Use your own words", "अपने शब्दों में बताएँ")}</strong><p>{t("Review your transcript before sending", "भेजने से पहले अपने शब्द जाँचें")}</p></div><div><Pencil /><strong>{t("Room to make changes", "बदलाव करना आसान है")}</strong><p>{t("Go back and correct an answer", "पीछे जाएँ और उत्तर सुधारें")}</p></div></div></>;
}

export function DeleteDocumentButton({ busy, language, remove }: { busy: boolean; language: Lang; remove: () => void }) {
  const [confirm, setConfirm] = useState(false);
  const t = (en: string, hi: string) => language === "hi" ? hi : en;
  return <div className="delete-controls">{confirm ? <><p>{t("Delete this document and its extracted information? This cannot be undone.", "यह दस्तावेज़ और इसकी निकाली गई जानकारी मिटाएँ? इसे वापस नहीं लाया जा सकेगा।")}</p><button className="secondary" disabled={busy} onClick={() => setConfirm(false)}>{t("Keep document", "दस्तावेज़ रखें")}</button><button className="secondary danger" disabled={busy} onClick={remove}>{t("Delete permanently", "हमेशा के लिए मिटाएँ")}</button></> : <button className="text-button danger" disabled={busy} onClick={() => setConfirm(true)}><Trash2 size={16} />{t("Delete document", "दस्तावेज़ मिटाएँ")}</button>}</div>;
}

export type AiStatus = { configured: boolean; provider: string; model: string };
type SaveReview = { suggestionId: string; confirmed: boolean };
export function DocumentEditor({ doc, language, busy, save, remove, reviewWithAI, imageUrl, ai, onDirty }: {
  doc: Doc; language: Lang; busy: boolean; save: (text: string, review?: SaveReview) => void;
  remove: () => void; reviewWithAI: () => Promise<void>; imageUrl: string; ai: AiStatus | null;
  onDirty: (id: string, dirty: boolean) => void;
}) {
  const [text, setText] = useState(doc.ocr_text);
  const [suggested, setSuggested] = useState(doc.ai_suggestion?.corrected_text || "");
  const [allowCloud, setAllowCloud] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [zoom, setZoom] = useState(100);
  const [imageError, setImageError] = useState(false);
  const [suggestionTouched, setSuggestionTouched] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const reviewLock = useRef(false);
  const [reviewError, setReviewError] = useState("");
  const [reviewSeconds, setReviewSeconds] = useState(0);
  useEffect(() => { if (!reviewing) return; const timer = setInterval(() => setReviewSeconds(value => value + 1), 1000); return () => clearInterval(timer); }, [reviewing]);
  async function requestReview() {
    if (reviewLock.current || busy || !allowCloud) return;
    reviewLock.current = true;
    setReviewing(true); setReviewError(""); setReviewSeconds(0);
    try { await reviewWithAI(); }
    catch (caught) { setReviewError(caught instanceof Error ? caught.message : "AI review failed. Please retry."); }
    finally { reviewLock.current = false; setReviewing(false); }
  }
  const t = (en: string, hi: string) => language === "hi" ? hi : en;
  const dirty = text !== doc.ocr_text;
  useEffect(() => { setSuggested(doc.ai_suggestion?.corrected_text || ""); setConfirmed(false); setSuggestionTouched(false); }, [doc.ai_suggestion?.id]);
  useEffect(() => { onDirty(doc.id, dirty || suggestionTouched); }, [doc.id, dirty, suggestionTouched, onDirty]);
  return <article className="panel document-editor">
    <div className="question-meta"><h3>{doc.filename}</h3><span className="badge">{Math.round(doc.confidence * 100)}% {t("OCR engine confidence", "OCR इंजन का विश्वास")}</span><DeleteDocumentButton busy={busy} language={language} remove={remove} /></div>
    <div className="notice" role="status">{doc.ai_suggestion ? t("AI suggestion ready below. Compare and accept it to replace the saved text.", "AI सुझाव नीचे तैयार है। तुलना करके स्वीकार करें तभी सहेजा पाठ बदलेगा।") : doc.status === "ai_reviewed_by_user" ? t("AI review accepted by you.", "आपने AI समीक्षा स्वीकार की है।") : t("This is local OCR, not an AI-reviewed result. Use AI image review below to extract clinical details.", "यह स्थानीय OCR है, AI समीक्षा नहीं। चिकित्सा जानकारी के लिए नीचे AI समीक्षा चलाएँ।")}</div>
    <div className="document-compare">
      <div className="source-panel"><div className="question-meta"><strong>{t("Original image", "मूल तस्वीर")}</strong><label>{t("Zoom", "ज़ूम")} <select aria-label={t("Image zoom", "तस्वीर ज़ूम")} value={zoom} onChange={e => setZoom(Number(e.target.value))}><option value={100}>100%</option><option value={150}>150%</option><option value={200}>200%</option><option value={300}>300%</option></select></label></div>
        {doc.source_available && !imageError ? <div className="source-image-scroll"><img src={imageUrl} alt={t("Original uploaded document", "अपलोड किया गया मूल दस्तावेज़")} style={{ width: `${zoom}%`, maxWidth: "none" }} onError={() => setImageError(true)} /></div> : <p>{t("Original image unavailable. Re-upload it for AI review.", "मूल तस्वीर उपलब्ध नहीं है। AI समीक्षा के लिए दोबारा अपलोड करें।")}</p>}
      </div>
      <div><label className="field-label" htmlFor={`doc-${doc.id}`}>{t("Saved OCR text — check and correct", "सहेजा गया OCR पाठ — जाँचें और सुधारें")}</label><textarea id={`doc-${doc.id}`} value={text} disabled={busy} onChange={e => setText(e.target.value)} /><div className="actions"><button className="secondary" disabled={busy || !text.trim() || !dirty} onClick={() => save(text)}>{t("Save corrected text", "सुधारा गया पाठ सहेजें")}</button>{dirty && <button className="text-button" disabled={busy} onClick={() => setText(doc.ocr_text)}>{t("Discard text edits", "पाठ के बदलाव रद्द करें")}</button>}{doc.status === "manually_corrected" && <span className="badge">{t("Manually corrected", "हाथ से सुधारा गया")}</span>}{doc.status === "ai_reviewed_by_user" && <span className="badge">{t("AI suggestion reviewed by user", "AI सुझाव की उपयोगकर्ता ने समीक्षा की")}</span>}</div>
      {doc.confidence < .75 && <p className="speech-error">{t("Low OCR confidence. Check names, numbers and doses against the image.", "OCR का विश्वास कम है। तस्वीर में नाम, संख्या और खुराक जाँचें।")}</p>}
      <details><summary>{t("Original OCR before corrections", "सुधार से पहले मूल OCR")}</summary><pre>{doc.original_ocr_text || doc.ocr_text}</pre></details></div>
    </div>
    <section className="ai-review-panel"><h3><Sparkles size={19} />{t("AI image review", "AI तस्वीर समीक्षा")}</h3><p>{t("Focus: patient age, treating doctor, diagnoses, medicines and handwritten notes. Two overlapping views cover the page; addresses and advertising are omitted. Check every suggestion against the image.", "ध्यान: मरीज़ की आयु, डॉक्टर, निदान, दवाएँ और हाथ से लिखे नोट। पते और विज्ञापन छोड़कर तस्वीर के दो हिस्से पढ़े जाते हैं। हर सुझाव तस्वीर से जाँचें।")}</p>
      {!ai?.configured && <div className="soft-box"><strong>{t("Connect the free-tier API once", "एक बार मुफ़्त API जोड़ें")}</strong><p>{t("Create a free Groq API key, run configure-ai.cmd in the project folder, and restart the backend. Keep your key out of the frontend and chat.", "मुफ़्त Groq API कुंजी बनाएँ, प्रोजेक्ट फ़ोल्डर में configure-ai.cmd चलाएँ और बैकएंड फिर शुरू करें। कुंजी फ्रंटएंड या चैट में न डालें।")}</p><a href="https://console.groq.com/keys" target="_blank" rel="noreferrer">{t("Create Groq API key", "Groq API कुंजी बनाएँ")}</a></div>}
      {!doc.ai_suggestion && <><label className="consent cloud-consent"><input type="checkbox" checked={allowCloud} disabled={busy} onChange={e => setAllowCloud(e.target.checked)} /><span>{t("Send this image and its saved OCR text to Groq for AI review. Free-plan usage limits apply.", "इस तस्वीर और सहेजे गए OCR पाठ को AI समीक्षा के लिए Groq को भेजें। मुफ़्त योजना की उपयोग सीमाएँ लागू हैं।")}</span></label><button className="primary" disabled={busy || !allowCloud || !ai?.configured || !doc.source_available || dirty} onClick={requestReview} aria-busy={reviewing}>{reviewing ? <LoaderCircle className="spin" size={17} /> : <Sparkles size={17} />}{reviewing ? t("Reading clinical details…", "चिकित्सा जानकारी पढ़ रहे हैं…") : t("Review image with AI", "AI से तस्वीर की समीक्षा करें")}</button>{dirty && <p>{t("Save or discard your text edits before running AI review.", "AI समीक्षा से पहले पाठ के बदलाव सहेजें या रद्द करें।")}</p>}</>}
      {reviewing && <p role="status">{t("Reading the image and handwritten regions. This may take up to two minutes.", "तस्वीर और हाथ से लिखे हिस्से पढ़ रहे हैं। दो मिनट तक लग सकते हैं।")} {reviewSeconds}s</p>}
      {reviewError && <div className="notice warning" role="alert"><strong>{t("AI review did not complete", "AI समीक्षा पूरी नहीं हुई")}</strong><p>{reviewError}</p><p>{t("Your saved OCR is unchanged. Fix the issue and retry this button.", "सहेजा OCR नहीं बदला। समस्या ठीक करके फिर बटन दबाएँ।")}</p></div>}
      {doc.ai_suggestion && <div className="ai-suggestion"><span className="badge">{t("Suggestion only · Not saved to your record", "केवल सुझाव · रिकॉर्ड में नहीं सहेजा गया")}</span><p>{doc.ai_suggestion.quality_notes}</p>{doc.ai_suggestion.uncertainties.length > 0 && <div className="notice warning"><strong>{t("Check these unclear areas", "इन अस्पष्ट हिस्सों को जाँचें")}</strong><ul>{doc.ai_suggestion.uncertainties.map((item, i) => <li key={i}><strong>{item.location}:</strong> {item.reason}</li>)}</ul></div>}
      <label className="field-label" htmlFor={`suggestion-${doc.id}`}>{t("AI suggested text — editable before acceptance", "AI का सुझाया पाठ — स्वीकार करने से पहले बदल सकते हैं")}</label><textarea id={`suggestion-${doc.id}`} className="ai-text" value={suggested} disabled={busy} onChange={e => { setSuggested(e.target.value); setSuggestionTouched(true); setConfirmed(false); }} />
      <label className="consent"><input type="checkbox" checked={confirmed} disabled={busy} onChange={e => setConfirmed(e.target.checked)} /><span>{t("I compared this text with the image, checked doses and numbers, and left unreadable text marked as unclear.", "मैंने पाठ की तस्वीर से तुलना की, खुराक और संख्याएँ जाँचीं और अपठनीय पाठ को अस्पष्ट चिह्नित रखा।")}</span></label>
      <div className="actions"><button className="primary" disabled={busy || !confirmed || !suggested.trim() || dirty} onClick={() => save(suggested, { suggestionId: doc.ai_suggestion!.id, confirmed })}>{t("Accept reviewed text", "जाँचा गया पाठ स्वीकार करें")}</button><button className="secondary" disabled={busy} onClick={() => { setSuggested(doc.ai_suggestion!.corrected_text); setSuggestionTouched(false); setConfirmed(false); }}>{t("Reset suggestion edits", "सुझाव के बदलाव रीसेट करें")}</button></div><p className="small-note">{t("You can ignore this suggestion and keep the saved OCR above. Acceptance replaces the saved text and requires a new physician review.", "आप सुझाव को अनदेखा करके ऊपर का सहेजा OCR रख सकते हैं। स्वीकार करने पर सहेजा पाठ बदलेगा और डॉक्टर की नई समीक्षा आवश्यक होगी।")}</p></div>}
    </section>
    <details><summary>{t("View extracted structure", "निकाली गई संरचना देखें")}</summary><pre>{JSON.stringify(doc.extracted, null, 2)}</pre></details><p className="small-note">{t("Structured field extraction still supports a limited set of report labels. The full saved document text is also included in the physician draft.", "जानकारी की संरचित निकासी कुछ रिपोर्ट लेबल तक सीमित है। पूरा सहेजा पाठ भी डॉक्टर के मसौदे में शामिल है।")}</p>
  </article>;
}
