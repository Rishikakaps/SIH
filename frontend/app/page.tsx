"use client";

import { ChangeEvent, useMemo, useState } from "react";
import { FileScan, HeartPulse, Languages, Mic, RefreshCcw, Send, ShieldCheck, Stethoscope, Volume2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const steps = ["Identify", "Consent", "Mode", "History", "Documents", "Review", "Physician", "Sync", "Architecture"];

type Session = { id: string; patient_id: string; mode: string; language: string };
type Patient = { id: string; name: string; age: number; sex: string; abha_id: string; opd: string };
type Prompt = { completed: boolean; current_field: string | null; question: string | null; options: string[]; physician_pending_fields: string[] };
type Flag = { code: string; reason: string };
type Fact = { id: string; label: string; value: string; ontology_path: string; source: string; source_ref?: string; metadata?: Record<string, unknown> };
type Evidence = { status: string; message: string; fact_ids: string[] };
type DocumentRecord = { id: string; filename: string; ocr_text: string; confidence: number; extracted: any };
type LoadState = "idle" | "loading" | "success" | "error";
type ReviewState = "draft" | "editing" | "approved" | "rejected";

export default function Home() {
  const [step, setStep] = useState(0);
  const [maxStep, setMaxStep] = useState(0);
  const [language, setLanguage] = useState<"en" | "hi">("hi");
  const [session, setSession] = useState<Session | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [consentChecked, setConsentChecked] = useState(false);
  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [flags, setFlags] = useState<Flag[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [editedSummary, setEditedSummary] = useState("");
  const [fhir, setFhir] = useState<any>(null);
  const [synced, setSynced] = useState(false);
  const [loading, setLoading] = useState<LoadState>("idle");
  const [loadingText, setLoadingText] = useState("");
  const [error, setError] = useState("");
  const [voiceState, setVoiceState] = useState<"idle" | "listening" | "ready">("idle");
  const [reviewState, setReviewState] = useState<ReviewState>("draft");

  const redFlag = flags.length > 0;
  const visibleFacts = useMemo(() => facts.slice(-10), [facts]);

  function go(next: number) {
    if (next <= maxStep || next === 8) setStep(next);
  }

  function advance(next: number) {
    setMaxStep((current) => Math.max(current, next));
    setStep(next);
  }

  async function run<T>(label: string, action: () => Promise<T>): Promise<T | null> {
    setError("");
    setLoading("loading");
    setLoadingText(label);
    try {
      const result = await action();
      setLoading("success");
      return result;
    } catch (caught) {
      setLoading("error");
      setError(caught instanceof Error ? caught.message : "Something went wrong. Please retry this step.");
      return null;
    }
  }

  async function createSession() {
    const res = await run("Preparing demo ABHA session...", () => postJson("/sessions", { language, mode: "general_medicine" }));
    if (!res) return;
    setSession(res.session);
    setPatient(res.patient);
    setPrompt(res.next);
    advance(1);
  }

  async function consent() {
    if (!consentChecked || !session) return;
    const res = await run("Recording consent...", () => postJson("/consent", { session_id: session.id, scope: ["history", "documents", "physician_sharing"], language }));
    if (res) advance(2);
  }

  async function selectMode(mode: "general_medicine" | "ayush") {
    if (!session) return;
    const res = await run("Loading clinical pathway...", () => postJson("/sessions/mode", { session_id: session.id, mode }));
    if (!res) return;
    setSession(res.session);
    setPrompt(res.next);
    advance(3);
  }

  async function submitAnswer(content: string, inputType = "tapped_option") {
    if (!session) return;
    const res = await run("Structuring patient response...", () => postJson("/conversation/message", { session_id: session.id, input_type: inputType, content }));
    if (!res) return;
    setFacts((current) => [...current, res.fact]);
    setPrompt(res.next);
    setFlags(res.flags);
    if (res.next.completed) advance(4);
  }

  async function sandboxVoice() {
    setVoiceState("listening");
    await delay(900);
    setVoiceState("ready");
    await submitAnswer("Chest pain", "voice_transcript");
  }

  async function uploadDocument(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !session) return;
    const form = new FormData();
    form.append("session_id", session.id);
    form.append("doc_type_hint", file.name.toLowerCase().includes("lab") ? "lab_report" : "prescription");
    form.append("file", file);
    const res = await run("Uploading... Reading document... Extracting clinical information...", async () => {
      const response = await fetch(`${API}/documents`, { method: "POST", body: form });
      if (!response.ok) throw new Error("upload failed");
      return response.json();
    });
    if (!res) return;
    setDocuments((current) => [...current, res.document]);
    setFacts((current) => [...current, ...res.facts]);
    setEvidence(res.evidence);
    advance(5);
  }

  async function processDemoDocuments() {
    if (!session) return;
    const res = await run("Rendering demo documents... Running EasyOCR... Structuring evidence...", () => postJson("/documents/process", { session_id: session.id }));
    if (!res) return;
    setDocuments((current) => [...current, ...(res.documents || [])]);
    setFacts((current) => [...current, ...res.facts]);
    setEvidence(res.evidence);
    advance(5);
  }

  async function loadSummary() {
    if (!session) return;
    const res = await run("Generating physician draft...", async () => {
      const response = await fetch(`${API}/summary/${session.id}`);
      if (!response.ok) throw new Error("summary failed");
      return response.json();
    });
    if (!res) return;
    setSummary(res);
    setEditedSummary(JSON.stringify(res.sections, null, 2));
    setReviewState("draft");
    advance(6);
  }

  async function approveAndExport() {
    if (!session || reviewState === "rejected") return;
    const res = await run("Saving physician review and preparing FHIR record...", async () => {
      await postJson("/physician/review", { session_id: session.id, physician_id: "dr_demo", decision: "accept", edits: { summary_text: editedSummary } });
      return postJson("/fhir/export", { session_id: session.id });
    });
    if (!res) return;
    setReviewState("approved");
    setFhir(res);
    advance(7);
  }

  async function rejectDraft() {
    if (!session) return;
    await run("Recording rejected draft...", () => postJson("/physician/review", { session_id: session.id, physician_id: "dr_demo", decision: "reject", edits: { summary_text: editedSummary } }));
    setReviewState("rejected");
  }

  async function sync() {
    if (!session || !fhir) return;
    const res = await run("Sending to simulated ABDM/HIS connector...", () => postJson("/sync/mock", { session_id: session.id }));
    if (res) setSynced(true);
  }

  return (
    <main className="shell">
      <aside className="rail">
        <div>
          <p className="eyebrow">SIH26047 sandbox</p>
          <h1>Rx Lens</h1>
          <p className="sub">Prepare a patient history before the doctor meets the patient.</p>
        </div>
        <nav className="steps">
          {steps.map((item, index) => (
            <button key={item} disabled={index > maxStep && index !== 8} className={`step ${index === step ? "active" : ""} ${index < step ? "done" : ""}`} onClick={() => go(index)}>
              {index + 1}. {item}
            </button>
          ))}
        </nav>
        <button className="ghost" onClick={() => window.location.reload()}><RefreshCcw size={16} /> Finish Session</button>
      </aside>
      <section className="stage">
        <header className="topbar">
          <div><p className="eyebrow">{step >= 6 ? "Physician workspace" : "Patient kiosk"}</p><h2>{steps[step]}</h2></div>
          <span className={`chip ${synced ? "green" : ""}`}>{synced ? "Sandbox Sync Complete" : "Unsynced"}</span>
        </header>
        {loading === "loading" && <div className="panel"><span className="chip amber">{loadingText}</span></div>}
        {error && <div className="panel alert"><h3>{error}</h3></div>}
        {redFlag && <div className="panel alert"><span className="chip red">Priority clinical attention recommended</span><h3>Reason: chest pain with breathlessness</h3><p>{flags[0].reason}</p></div>}
        {step === 0 && <IdentifyScreen language={language} setLanguage={setLanguage} createSession={createSession} />}
        {step === 1 && <ConsentScreen checked={consentChecked} setChecked={setConsentChecked} consent={consent} />}
        {step === 2 && <ModeScreen patient={patient} selectMode={selectMode} />}
        {step === 3 && <InterviewScreen prompt={prompt} submitAnswer={submitAnswer} sandboxVoice={sandboxVoice} voiceState={voiceState} />}
        {step === 4 && <DocumentsScreen uploadDocument={uploadDocument} processDemoDocuments={processDemoDocuments} />}
        {step === 5 && <ReviewScreen documents={documents} facts={visibleFacts} evidence={evidence} loadSummary={loadSummary} />}
        {step === 6 && <PhysicianScreen patient={patient} evidence={evidence} prompt={prompt} summary={summary} editedSummary={editedSummary} setEditedSummary={setEditedSummary} reviewState={reviewState} setReviewState={setReviewState} approveAndExport={approveAndExport} rejectDraft={rejectDraft} />}
        {step === 7 && <FhirScreen fhir={fhir} sync={sync} synced={synced} />}
        {step === 8 && <ArchitecturePanel />}
      </section>
    </main>
  );
}

function IdentifyScreen({ language, setLanguage, createSession }: any) {
  return <div className="panel grid two"><div><h3 className="question">Let&apos;s prepare your medical history before you meet the doctor.</h3><p>Demo ABHA identity, large touch targets, Hindi-first flow, and sandbox audio affordances for low-literacy use.</p></div><div className="grid control-stack"><button type="button" className="option" onClick={() => setLanguage("hi")}><Languages /> Hindi {language === "hi" && <span className="chip green">Selected</span>}</button><button type="button" className="option" onClick={() => setLanguage("en")}><Languages /> English {language === "en" && <span className="chip green">Selected</span>}</button><button type="button" className="primary" onClick={createSession} onPointerDown={(event) => event.currentTarget.classList.add("pressed")} onPointerUp={(event) => event.currentTarget.classList.remove("pressed")}><Send size={18} /> Continue with Demo ABHA</button></div></div>;
}

function ConsentScreen({ checked, setChecked, consent }: any) {
  return <div className="panel grid"><ShieldCheck size={34} /><h3 className="question">We will collect your answers and process your uploaded medical papers so the doctor can review them.</h3><p>This is a sandbox demo. Your history, document text, and summary will be shown to the physician screen for review.</p><label className="tile"><input type="checkbox" checked={checked} onChange={(event) => setChecked(event.target.checked)} /> I understand and consent.</label><div className="actions"><button className="secondary" onClick={() => alert("Sandbox audio: consent explanation would be spoken aloud here.")}><Volume2 size={18} /> Listen</button><button className="primary" disabled={!checked} onClick={consent}>Continue</button></div></div>;
}

function ModeScreen({ patient, selectMode }: any) {
  return <div className="panel grid two"><div className="tile"><h3>Demo Patient</h3><p>{patient?.name}, {patient?.age}, {patient?.sex}</p><span className="chip amber">{patient?.abha_id}</span></div><button className="tile" onClick={() => selectMode("general_medicine")}><Stethoscope /><h3>General Medicine Golden Path</h3><p>Chest pain, SOCRATES follow-up, breathlessness red flag, document evidence, physician review.</p></button><button className="tile" onClick={() => selectMode("ayush")}><HeartPulse /><h3>Show AYUSH Mode</h3><p>Dashavidha-oriented patient intake with physician assessment pending fields.</p></button></div>;
}

function InterviewScreen({ prompt, submitAnswer, sandboxVoice, voiceState }: any) {
  return <div className="panel grid"><h3 className="question">{prompt?.question || "Interview complete"}</h3><div className="grid two"><button className="tile" onClick={sandboxVoice}><Mic /><h3>{voiceState === "listening" ? "Listening..." : "Sandbox voice"}</h3><p>{voiceState === "ready" ? "Transcript: Subah se seene mein dard hai." : "Tap to simulate one controlled ASR transcript."}</p></button><div className="grid">{prompt?.options?.map((option: string) => <button className="option" key={option} onClick={() => submitAnswer(option)}>{option}</button>)}</div></div></div>;
}

function DocumentsScreen({ uploadDocument, processDemoDocuments }: any) {
  return <div className="panel grid"><FileScan size={34} /><h3 className="question">Add previous medical documents.</h3><p>Real OCR path: uploaded PNG/JPG is read by EasyOCR, converted to extracted text, then structured into labs, medications, allergies, evidence, and timeline.</p><input type="file" accept="image/png,image/jpeg" onChange={uploadDocument} /><div className="actions"><button className="primary" onClick={processDemoDocuments}>Run included demo documents through OCR</button></div></div>;
}

function ReviewScreen({ documents, facts, evidence, loadSummary }: any) {
  return <div className="panel grid summary"><div className="grid">{documents.map((doc: DocumentRecord) => <div className="tile" key={doc.id}><span className="chip green">Original uploaded file: {doc.filename}</span><h3>Extracted text</h3><pre>{doc.ocr_text}</pre><h3>Clinical structure</h3><pre>{JSON.stringify(doc.extracted, null, 2)}</pre></div>)}</div><div className="grid">{facts.map((fact: Fact) => <div className="fact" key={fact.id}><strong>{fact.label}</strong>{fact.value}<br /><span className="chip">{fact.source}</span></div>)}{evidence.map((ev: Evidence) => <div className="tile" key={ev.fact_ids.join("-")}><span className={`chip ${ev.status === "CONFLICT" ? "red" : ev.status === "OUT_OF_RANGE" ? "amber" : ""}`}>{ev.status}</span><p>{ev.message}</p></div>)}<button className="primary" onClick={loadSummary}>Generate physician draft</button></div></div>;
}

function PhysicianScreen({ patient, evidence, prompt, summary, editedSummary, setEditedSummary, reviewState, setReviewState, approveAndExport, rejectDraft }: any) {
  return <div className="panel grid summary"><div><h3>{patient?.name}</h3><p className={`chip ${reviewState === "approved" ? "green" : reviewState === "rejected" ? "red" : "amber"}`}>{reviewState === "approved" ? "PHYSICIAN VERIFIED" : reviewState === "rejected" ? "Draft rejected" : summary?.label}</p><textarea value={editedSummary} onChange={(event) => { setEditedSummary(event.target.value); setReviewState("editing"); }} /></div><div className="grid">{prompt?.physician_pending_fields?.length > 0 && <div className="tile"><h3>AYUSH physician assessment pending</h3><p>{prompt.physician_pending_fields.join(", ")}</p><span className="chip violet">Not self-reported or inferred</span></div>}{evidence.map((ev: Evidence) => <div className="tile" key={ev.fact_ids.join("-")}><span className="chip red">{ev.status}</span><p>{ev.message}</p></div>)}<button className="secondary" onClick={() => setReviewState("editing")}>Amend</button><button className="secondary" onClick={rejectDraft}>Reject</button><button className="primary" disabled={reviewState === "rejected"} onClick={approveAndExport}>Approve and export</button></div></div>;
}

function FhirScreen({ fhir, sync, synced }: any) {
  const resources = fhir?.entry?.map((entry: any) => entry.resource.resourceType) || [];
  return <div className="panel grid"><h3 className="question">FHIR Bundle Preview</h3><div className="grid three">{resources.map((resource: string, index: number) => <div className="tile" key={`${resource}-${index}`}><span className="chip green">{resource}</span></div>)}</div><details><summary>View technical payload</summary><pre>{JSON.stringify(fhir, null, 2)}</pre></details><div className="actions"><button className="primary" onClick={sync}>Sync to sandbox ABDM/HIS</button><span className={`chip ${synced ? "green" : "amber"}`}>{synced ? "Sandbox Sync Complete" : "Ready"}</span></div></div>;
}

function ArchitecturePanel() {
  const rows = [["Clinical interview", "Working deterministic/adaptive engine"], ["Red-flag rules", "Working deterministic rules"], ["AYUSH intake", "Working POC pathway"], ["Document extraction", "Real EasyOCR for high-quality printed English images"], ["Voice", "Sandbox ASR adapter; target Bhashini / AI4Bharat"], ["Physician review", "Working approve/amend/reject"], ["FHIR generation", "Working POC bundle generation"], ["ABDM / HIS", "Simulated connector"], ["Data", "In-memory sandbox store; target secure persistent datastore"]];
  return <div className="panel grid"><h3 className="question">Sandbox Architecture</h3>{rows.map(([name, detail]) => <div className="fact" key={name}><strong>{name}</strong>{detail}</div>)}</div>;
}

async function postJson(path: string, body: unknown) {
  const response = await fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
