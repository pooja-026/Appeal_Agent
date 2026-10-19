import { useEffect, useRef, useState } from "react";
import { api, type Analysis, type Case, type DocumentType, type Passage, type SampleCaseSummary, type SourceDocument, ApiError } from "./api";

type Screen = "home" | "examples" | "uploads";

const documentTypeLabels: Record<DocumentType, string> = {
  denial: "Denial or refusal",
  policy: "Retailer policy",
  receipt: "Receipt or order record",
  correspondence: "Messages with the retailer",
  other: "Other document",
};

const assessmentLabels = {
  potentially_supported: "Potentially supported",
  insufficient_evidence: "Insufficient evidence",
  no_supported_basis: "No supported basis in these documents",
};

function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [sampleCases, setSampleCases] = useState<SampleCaseSummary[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState("");
  const [selectedSample, setSelectedSample] = useState<Case | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [sampleLoading, setSampleLoading] = useState(false);
  const [sampleError, setSampleError] = useState("");
  const [uploadDocuments, setUploadDocuments] = useState<SourceDocument[]>([]);
  const [uploadWarnings, setUploadWarnings] = useState<Record<string, string[]>>({});
  const [uploadError, setUploadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [liveConfigured, setLiveConfigured] = useState(false);
  const [liveAnalysis, setLiveAnalysis] = useState<Analysis | null>(null);
  const [liveAnalyzing, setLiveAnalyzing] = useState(false);
  const [evidence, setEvidence] = useState<{ document: SourceDocument; passage: Passage } | null>(null);
  const sampleRequest = useRef(0);
  const liveRequest = useRef(0);

  useEffect(() => {
    if (screen !== "uploads") return;
    let active = true;
    api.getAnalysisConfig()
      .then((config) => { if (active) setLiveConfigured(config.live_analysis_configured); })
      .catch(() => { if (active) setLiveConfigured(false); });
    return () => { active = false; };
  }, [screen]);

  useEffect(() => {
    if (screen !== "examples" || sampleCases.length > 0) return;
    let active = true;
    setSampleLoading(true);
    setSampleError("");
    api.listSampleCases()
      .then((items) => { if (active) setSampleCases(items); })
      .catch((error: unknown) => { if (active) setSampleError(toMessage(error)); })
      .finally(() => { if (active) setSampleLoading(false); });
    return () => { active = false; };
  }, [screen, sampleCases.length]);

  const openExamples = () => {
    setScreen("examples");
    setAnalysis(null);
    setSampleError("");
  };

  const selectSample = (caseId: string) => {
    setSelectedSampleId(caseId);
    setSelectedSample(null);
    setAnalysis(null);
    setSampleError("");
    const requestId = ++sampleRequest.current;
    setSampleLoading(true);
    api.getSampleCase(caseId)
      .then((value) => { if (requestId === sampleRequest.current) setSelectedSample(value); })
      .catch((error: unknown) => { if (requestId === sampleRequest.current) setSampleError(toMessage(error)); })
      .finally(() => { if (requestId === sampleRequest.current) setSampleLoading(false); });
  };

  const showFindings = () => {
    if (!selectedSample) return;
    const requestId = ++sampleRequest.current;
    setSampleLoading(true);
    setSampleError("");
    setAnalysis(null);
    api.analyzeCase(selectedSample)
      .then((value) => { if (requestId === sampleRequest.current) setAnalysis(value); })
      .catch((error: unknown) => { if (requestId === sampleRequest.current) setSampleError(toMessage(error)); })
      .finally(() => { if (requestId === sampleRequest.current) setSampleLoading(false); });
  };

  const clearWorkspace = () => {
    ++liveRequest.current;
    setUploadDocuments([]);
    setUploadWarnings({});
    setUploadError("");
    setLiveAnalysis(null);
  };

  const uploadDocument = async (file: File, type: DocumentType, title: string) => {
    if (uploadDocuments.length >= 5) {
      setUploadError("You can review up to five documents in one session.");
      return;
    }
    setUploading(true);
    setUploadError("");
    try {
      const result = await api.extractDocument(file, type, title);
      if (uploadDocuments.some((document) => document.document_id === result.document.document_id)) {
        setUploadError("This document is already in your workspace. Choose a different file or clear the duplicate.");
        return;
      }
      setUploadDocuments((current) => {
        if (current.some((document) => document.document_id === result.document.document_id) || current.length >= 5) return current;
        return [...current, result.document];
      });
      setUploadWarnings((current) => ({ ...current, [result.document.document_id]: result.warnings }));
      setLiveAnalysis(null);
      ++liveRequest.current;
    } catch (error: unknown) {
      setUploadError(toMessage(error));
    } finally {
      setUploading(false);
    }
  };

  const analyzeUploadedDocuments = () => {
    if (!liveConfigured || uploadDocuments.length === 0 || liveAnalyzing) return;
    const hasDenial = uploadDocuments.some((document) => document.document_type === "denial");
    const hasPolicy = uploadDocuments.some((document) => document.document_type === "policy");
    if (!hasDenial || !hasPolicy) {
      setUploadError("Add at least one denial and one retailer policy document before analysis.");
      return;
    }
    const requestId = ++liveRequest.current;
    const casePayload: Case = {
      case_id: "uploaded-local-session",
      title: "Uploaded documents",
      created_at: new Date().toISOString(),
      documents: uploadDocuments,
    };
    setLiveAnalyzing(true);
    setLiveAnalysis(null);
    setUploadError("");
    api.analyzeLive(casePayload)
      .then((value) => { if (requestId === liveRequest.current) setLiveAnalysis(value); })
      .catch((error: unknown) => { if (requestId === liveRequest.current) setUploadError(toMessage(error)); })
      .finally(() => { if (requestId === liveRequest.current) setLiveAnalyzing(false); });
  };

  return (
    <div className="app-shell">
      <header className="site-header">
        <button className="brand" onClick={() => setScreen("home")} aria-label="Return to Appeal Agent home">
          <span className="brand-mark" aria-hidden="true">↗</span>
          <span>Appeal Agent</span>
        </button>
        <span className="header-note">Evidence organizer for denied online purchases</span>
      </header>

      <main className="main-content">
        {screen === "home" && <Home onExamples={openExamples} onUploads={() => setScreen("uploads")} />}
        {screen === "examples" && (
          <ExampleView
            cases={sampleCases}
            selectedId={selectedSampleId}
            selected={selectedSample}
            analysis={analysis}
            loading={sampleLoading}
            error={sampleError}
            onBack={() => setScreen("home")}
            onSelect={selectSample}
            onShowFindings={showFindings}
            onEvidence={setEvidence}
          />
        )}
        {screen === "uploads" && (
          <UploadView
            documents={uploadDocuments}
            warnings={uploadWarnings}
            error={uploadError}
            uploading={uploading}
            liveConfigured={liveConfigured}
            liveAnalysis={liveAnalysis}
            liveAnalyzing={liveAnalyzing}
            onBack={() => setScreen("home")}
            onUpload={uploadDocument}
            onRemove={(id) => { ++liveRequest.current; setUploadDocuments((items) => items.filter((item) => item.document_id !== id)); setLiveAnalysis(null); }}
            onClear={clearWorkspace}
            onAnalyze={analyzeUploadedDocuments}
            onEvidence={setEvidence}
          />
        )}
      </main>

      {evidence && <EvidenceDialog evidence={evidence} onClose={() => setEvidence(null)} />}
      <footer className="site-footer">Your documents stay in this browser session. Refreshing clears the workspace.</footer>
    </div>
  );
}

function Home({ onExamples, onUploads }: { onExamples: () => void; onUploads: () => void }) {
  return (
    <section className="home-page" aria-labelledby="home-title">
      <div className="hero-copy">
        <p className="eyebrow">A calmer way to read a refund denial</p>
        <h1 id="home-title">Understand what your documents say.</h1>
        <p className="hero-subtitle">Appeal Agent helps you compare a retailer’s decision with the policy and evidence you provide.</p>
        <p className="boundary-note">This is an organizer for your review, not legal advice and not an automatic appeal service.</p>
      </div>
      <div className="choice-grid">
        <ChoiceCard number="01" title="Try an example" description="Explore a fictional case with prepared example findings." onClick={onExamples} />
        <ChoiceCard number="02" title="Review my documents" description="Upload a PDF or text file and check its extracted text. Live analysis appears only when the backend is explicitly configured." onClick={onUploads} />
      </div>
    </section>
  );
}

function ChoiceCard({ number, title, description, onClick }: { number: string; title: string; description: string; onClick: () => void }) {
  return <button className="choice-card" onClick={onClick}>
    <span className="choice-number">{number}</span>
    <span className="choice-title">{title}<span aria-hidden="true"> →</span></span>
    <span className="choice-description">{description}</span>
  </button>;
}

function ExampleView(props: {
  cases: SampleCaseSummary[]; selectedId: string; selected: Case | null; analysis: Analysis | null;
  loading: boolean; error: string; onBack: () => void; onSelect: (id: string) => void;
  onShowFindings: () => void; onEvidence: (evidence: { document: SourceDocument; passage: Passage }) => void;
}) {
  return <section className="workspace" aria-labelledby="examples-title">
    <button className="back-link" onClick={props.onBack}>← Back to start</button>
    <div className="section-heading"><p className="eyebrow">Fictional examples</p><h1 id="examples-title">Start with a prepared case</h1><p>These examples are authored for demonstration. They are not real customer cases.</p></div>
    {props.error && <ErrorMessage message={props.error} />}
    {props.loading && !props.selected && <StatusMessage>Loading examples…</StatusMessage>}
    <div className="sample-list">
      {props.cases.map((item) => <button key={item.case_id} className={`sample-option ${props.selectedId === item.case_id ? "selected" : ""}`} onClick={() => props.onSelect(item.case_id)}>
        <span className="sample-option-title">{item.title}</span><span>{item.description}</span>
      </button>)}
    </div>
    {props.selected && <div className="case-panel">
      <div className="case-intro"><p className="eyebrow">Selected example</p><h2>{props.selected.title}</h2><p>Read the supplied source documents first, then view the simulated findings.</p></div>
      <SourceDocuments documents={props.selected.documents} onEvidence={props.onEvidence} />
      <button className="primary-button" onClick={props.onShowFindings} disabled={props.loading}>{props.loading ? "Preparing findings…" : "Show example findings"}</button>
      {props.analysis && <AnalysisView analysis={props.analysis} documents={props.selected.documents} onEvidence={props.onEvidence} simulated />}
    </div>}
  </section>;
}

function UploadView(props: {
  documents: SourceDocument[]; warnings: Record<string, string[]>; error: string; uploading: boolean;
  liveConfigured: boolean; liveAnalysis: Analysis | null; liveAnalyzing: boolean;
  onBack: () => void; onUpload: (file: File, type: DocumentType, title: string) => Promise<void>;
  onRemove: (id: string) => void; onClear: () => void; onAnalyze: () => void; onEvidence: (evidence: { document: SourceDocument; passage: Passage }) => void;
}) {
  const [type, setType] = useState<DocumentType>("other");
  const [title, setTitle] = useState("");
  const fileInputId = "document-file";
  return <section className="workspace" aria-labelledby="uploads-title">
    <button className="back-link" onClick={props.onBack}>← Back to start</button>
    <div className="section-heading"><p className="eyebrow">Your documents</p><h1 id="uploads-title">Review extracted text</h1><p>Upload up to five PDF or UTF-8 text documents. Extraction happens locally through this app; analysis, when enabled, sends the extracted text to Anthropic.</p></div>
    <div className="upload-card">
      <div className="field-row">
        <label htmlFor={fileInputId}>Document file <span className="field-hint">PDF or TXT</span></label>
        <input id={fileInputId} type="file" accept=".pdf,.txt,application/pdf,text/plain" disabled={props.uploading || props.documents.length >= 5} onChange={async (event) => {
          const input = event.currentTarget;
          const file = input.files?.[0];
          if (file) await props.onUpload(file, type, title);
          input.value = "";
        }} />
      </div>
      <div className="field-row compact-fields"><div><label htmlFor="document-type">What is this?</label><select id="document-type" value={type} onChange={(event) => setType(event.target.value as DocumentType)} disabled={props.uploading}><option value="denial">{documentTypeLabels.denial}</option><option value="policy">{documentTypeLabels.policy}</option><option value="receipt">{documentTypeLabels.receipt}</option><option value="correspondence">{documentTypeLabels.correspondence}</option><option value="other">{documentTypeLabels.other}</option></select></div><div><label htmlFor="document-title">Optional title</label><input id="document-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="For example, Order email" disabled={props.uploading} /></div></div>
      <p className="upload-limit">{props.documents.length} of 5 documents added. Uploads are sent to the local FastAPI server one at a time.</p>
    </div>
    {props.uploading && <StatusMessage>Extracting text…</StatusMessage>}
    {props.error && <ErrorMessage message={props.error} />}
    {props.documents.length > 0 && <div className="document-workspace"><div className="workspace-toolbar"><h2>Extracted documents</h2><button className="text-button" onClick={props.onClear}>Clear workspace</button></div>{props.documents.map((document, index) => <ExtractedDocument key={document.document_id} document={document} warnings={props.warnings[document.document_id] ?? []} isNewest={index === props.documents.length - 1} onRemove={props.onRemove} onEvidence={props.onEvidence} />)}{props.liveConfigured && <div className="live-analysis-card"><h2>Analyze my documents</h2><p>AI analysis sends the extracted text to Anthropic. It is not automatic, and the result is for your review against your documents.</p><p className="upload-limit">For this initial workflow, include at least one denial and one retailer policy document.</p><button className="primary-button" onClick={props.onAnalyze} disabled={props.liveAnalyzing}>{props.liveAnalyzing ? "Analyzing documents..." : "Analyze my documents"}</button></div>}{props.liveAnalysis && <div className="live-analysis-result"><div className="live-label">AI-generated analysis — review against your documents</div><AnalysisView analysis={props.liveAnalysis} documents={props.documents} onEvidence={props.onEvidence} simulated={false} /></div>}</div>}
  </section>;
}

function SourceDocuments({ documents, onEvidence }: { documents: SourceDocument[]; onEvidence: (evidence: { document: SourceDocument; passage: Passage }) => void }) {
  return <div className="source-documents"><h3>Supplied documents</h3>{documents.map((document) => <details key={document.document_id}><summary>{document.title}<span className="document-type">{documentTypeLabels[document.document_type]}</span></summary><div className="passage-list">{document.passages.map((passage) => <PassageCard key={passage.passage_id} document={document} passage={passage} onEvidence={onEvidence} />)}</div></details>)}</div>;
}

function ExtractedDocument({ document, warnings, isNewest, onRemove, onEvidence }: { document: SourceDocument; warnings: string[]; isNewest: boolean; onRemove: (id: string) => void; onEvidence: (evidence: { document: SourceDocument; passage: Passage }) => void }) {
  const [expanded, setExpanded] = useState(isNewest);
  useEffect(() => { if (isNewest) setExpanded(true); }, [isNewest]);
  const passageCount = document.passages.length;
  const passageLabel = `${passageCount} ${passageCount === 1 ? "extracted passage" : "extracted passages"}`;
  return <section className="extracted-document" aria-labelledby={`document-${document.document_id}`}>
    <div className="extracted-header">
      <div><h3 id={`document-${document.document_id}`}>{document.title}</h3><p className="document-type">{documentTypeLabels[document.document_type]} · <span className="passage-count">{passageLabel}</span></p></div>
      <div className="document-actions"><button className="text-button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded}>{expanded ? "Hide extracted text" : "Show extracted text"}</button><button className="remove-button" onClick={() => onRemove(document.document_id)}>Remove</button></div>
    </div>
    {expanded && <div className="extracted-body">{warnings.map((warning) => <p className="warning" key={warning}>Notice: {warning}</p>)}{passageCount > 0 ? document.passages.map((passage) => <PassageCard key={passage.passage_id} document={document} passage={passage} onEvidence={onEvidence} />) : <p className="empty-passages">No usable passages were extracted from this document.</p>}</div>}
  </section>;
}

function PassageCard({ document, passage, onEvidence }: { document: SourceDocument; passage: Passage; onEvidence: (evidence: { document: SourceDocument; passage: Passage }) => void }) {
  return <div className="passage-card"><p className="passage-meta">{passage.page_number ? `Page ${passage.page_number}` : "Extracted passage"}</p><p>{passage.text}</p><button className="evidence-button" onClick={() => onEvidence({ document, passage })}>View evidence</button></div>;
}

function AnalysisView({ analysis, documents, onEvidence, simulated }: { analysis: Analysis; documents: SourceDocument[]; onEvidence: (evidence: { document: SourceDocument; passage: Passage }) => void; simulated: boolean }) {
  return <section className="analysis-result" aria-labelledby="analysis-title"><div className="simulated-label">Fictional example — simulated findings</div><div className={`assessment assessment-${analysis.assessment}`}><p className="eyebrow">Assessment</p><h2 id="analysis-title">{assessmentLabels[analysis.assessment]}</h2><p>{analysis.explanation}</p></div><AnalysisSection title="What the documents suggest"><div className="finding-list">{analysis.findings.map((finding, index) => <div className="finding" key={`${finding.statement}-${index}`}><span className={`classification classification-${finding.classification}`}>{finding.classification === "documented_fact" ? "Documented fact" : "Interpretation"}</span><p>{finding.statement}</p><CitationList sources={finding.sources} documents={documents} onEvidence={onEvidence} /></div>)}</div></AnalysisSection><AnalysisSection title="What supports your request"><ClauseList clauses={analysis.supporting_policy_clauses} documents={documents} onEvidence={onEvidence} empty="No supporting policy clause was identified in the supplied documents." /></AnalysisSection><AnalysisSection title="What could weaken your request"><ClauseList clauses={analysis.conflicting_policy_clauses} documents={documents} onEvidence={onEvidence} empty="No conflicting policy clause was identified in the supplied documents." /></AnalysisSection><AnalysisSection title="What information is missing">{analysis.missing_evidence.length ? <ul className="plain-list">{analysis.missing_evidence.map((item) => <li key={item.item}><strong>{item.item}</strong><span>{item.why_needed}</span></li>)}</ul> : <p className="muted">No additional evidence was identified by this fictional analysis.</p>}</AnalysisSection><AnalysisSection title="Questions to answer">{analysis.follow_up_questions.length ? <ul className="question-list">{analysis.follow_up_questions.map((question) => <li key={question}>{question}</li>)}</ul> : <p className="muted">No follow-up questions were identified.</p>}</AnalysisSection><AnalysisSection title="Deadline, if documented">{analysis.documented_deadline ? <div className="deadline"><p>{analysis.documented_deadline.description}</p><CitationList sources={[analysis.documented_deadline.source]} documents={documents} onEvidence={onEvidence} /></div> : <p className="muted">No deadline is documented in the supplied documents.</p>}</AnalysisSection></section>;
}

function AnalysisSection({ title, children }: { title: string; children: React.ReactNode }) { return <section className="analysis-section"><h3>{title}</h3>{children}</section>; }

function ClauseList({ clauses, documents, onEvidence, empty }: { clauses: { statement: string; source: { document_id: string; passage_id: string; quoted_text: string } }[]; documents: SourceDocument[]; onEvidence: (evidence: { document: SourceDocument; passage: Passage }) => void; empty: string }) { return clauses.length ? <div className="clause-list">{clauses.map((clause) => <div className="clause" key={clause.statement}><p>{clause.statement}</p><CitationList sources={[clause.source]} documents={documents} onEvidence={onEvidence} /></div>)}</div> : <p className="muted">{empty}</p>; }

function CitationList({ sources, documents, onEvidence }: { sources: { document_id: string; passage_id: string; quoted_text: string }[]; documents: SourceDocument[]; onEvidence: (evidence: { document: SourceDocument; passage: Passage }) => void }) {
  return <div className="citation-list">{sources.map((source) => { const document = documents.find((item) => item.document_id === source.document_id); const passage = document?.passages.find((item) => item.passage_id === source.passage_id); return document && passage ? <button className="citation" key={`${source.document_id}-${source.passage_id}-${source.quoted_text}`} onClick={() => onEvidence({ document, passage })}>View evidence <span>“{source.quoted_text}”</span></button> : null; })}</div>;
}

function EvidenceDialog({ evidence, onClose }: { evidence: { document: SourceDocument; passage: Passage }; onClose: () => void }) {
  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="evidence-dialog" role="dialog" aria-modal="true" aria-labelledby="evidence-title"><div className="dialog-heading"><div><p className="eyebrow">Evidence passage</p><h2 id="evidence-title">{evidence.document.title}</h2></div><button className="close-button" onClick={onClose} aria-label="Close evidence">×</button></div><p className="document-type">{documentTypeLabels[evidence.document.document_type]}{evidence.passage.page_number ? ` · Page ${evidence.passage.page_number}` : ""}</p><blockquote>{evidence.passage.text}</blockquote><button className="primary-button" onClick={onClose}>Done</button></section></div>;
}

function StatusMessage({ children }: { children: React.ReactNode }) { return <p className="status-message" role="status">{children}</p>; }
function ErrorMessage({ message }: { message: string }) { return <p className="error-message" role="alert">{message}</p>; }
function toMessage(error: unknown) { return error instanceof ApiError ? error.message : "Something went wrong while contacting the local API."; }

export default App;
