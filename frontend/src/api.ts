export type DocumentType = "denial" | "policy" | "receipt" | "correspondence" | "other";
export type Assessment = "potentially_supported" | "insufficient_evidence" | "no_supported_basis";
export type FindingClassification = "documented_fact" | "interpretation";

export interface Passage {
  passage_id: string;
  text: string;
  page_number: number | null;
}

export interface SourceDocument {
  document_id: string;
  document_type: DocumentType;
  title: string;
  passages: Passage[];
}

export interface Case {
  case_id: string;
  title: string;
  created_at: string;
  documents: SourceDocument[];
}

export interface SampleCaseSummary {
  case_id: string;
  title: string;
  description: string;
}

export interface SourceReference {
  document_id: string;
  passage_id: string;
  quoted_text: string;
}

export interface Finding {
  classification: FindingClassification;
  statement: string;
  sources: SourceReference[];
}

export interface PolicyClause {
  statement: string;
  source: SourceReference;
}

export interface MissingEvidence {
  item: string;
  why_needed: string;
}

export interface DocumentedDeadline {
  description: string;
  source: SourceReference;
  date: string | null;
}

export interface Analysis {
  case_id: string;
  findings: Finding[];
  supporting_policy_clauses: PolicyClause[];
  conflicting_policy_clauses: PolicyClause[];
  missing_evidence: MissingEvidence[];
  follow_up_questions: string[];
  assessment: Assessment;
  explanation: string;
  documented_deadline: DocumentedDeadline | null;
  provider: string;
  simulated: boolean;
  model: string | null;
}

export interface AnalysisConfig {
  provider: string;
  live_analysis_configured: boolean;
}

export interface ExtractionResponse {
  document: SourceDocument;
  metadata: {
    format: "pdf" | "txt";
    page_count: number;
    character_count: number;
    passage_count: number;
  };
  warnings: string[];
}

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, options);
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message = typeof detail === "string" ? detail : detail?.message;
    throw new ApiError(message || "The request could not be completed.", response.status, detail?.code);
  }
  return payload as T;
}

export const api = {
  listSampleCases: () => request<SampleCaseSummary[]>("/sample-cases"),
  getSampleCase: (caseId: string) => request<Case>(`/sample-cases/${encodeURIComponent(caseId)}`),
  analyzeCase: (value: Case) => request<Analysis>("/analysis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  }),
  getAnalysisConfig: () => request<AnalysisConfig>("/analysis/config"),
  analyzeLive: (value: Case) => request<Analysis>("/live-analysis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  }),
  extractDocument: (file: File, documentType: DocumentType, title: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("document_type", documentType);
    if (title.trim()) form.append("title", title.trim());
    return request<ExtractionResponse>("/documents/extract", { method: "POST", body: form });
  },
};
