# Project scope

## Product goal

Appeal Agent helps consumers understand denied retailer refund requests, compare the denial with supplied policy terms, identify missing evidence, and prepare an evidence-backed response for review.

The initial product scope is damaged or incorrect online purchases where a retailer denied a refund. Insurance appeals, bank chargebacks, legal advice, and automatic submission are outside this milestone.

## Planned workflow

1. Ingest user-supplied denial, policy, receipt, and correspondence documents.
2. Extract facts with stable source references.
3. Compare the denial with supplied policy terms.
4. Separate documented facts from interpretations.
5. Surface supporting and conflicting evidence.
6. Ask targeted questions when evidence is missing.
7. Prepare an evidence-backed response for user review.

## Current implementation status

This milestone includes:

- FastAPI backend with `GET /health`.
- Pydantic schemas for cases, documents, passages, findings, policy clauses, missing evidence, assessments, deadlines, and source references.
- Three clearly fictional authored sample cases with stable passage IDs.
- Source documents stored separately from expected evaluation findings.
- A vendor-neutral analysis-provider interface, deterministic `MockAnalysisProvider`, and an explicitly configured `AnthropicAnalysisProvider`.
- Source-reference validation for findings, policy clauses, and documented deadlines.
- Local sample-case and analysis APIs.
- Bounded local extraction for UTF-8 text and text-based PDFs, with stable source passages and page references.
- A React/TypeScript/Vite frontend with separate fictional-sample and local-document review flows.
- Typed frontend API integration through a local Vite proxy, evidence navigation, upload warnings, and in-memory session state.
- A live-analysis route that performs one bounded Anthropic Messages API request with structured JSON output, token counting, cost checks, and citation validation.
- An explicit post-analysis drafting route that derives an allowed draft type from the assessment, revalidates the exact case fingerprint and citations, and returns a structured response draft with paragraph evidence, checklist items, and usage metadata.
- A frontend drafting review with required user confirmation, optional name and requested remedy, in-memory editing, reset, copy, and UTF-8 TXT download. Draft evidence always refers to the original generated paragraphs; it is not presented as validation for later edits.
- Focused offline backend and frontend tests using mocked SDK responses; no test makes a paid call.

Sample analysis remains simulated and always uses the mock provider. Uploaded documents can use Anthropic only when `AI_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, and an explicit `ANTHROPIC_MODEL` are configured. Live results explicitly identify `provider="anthropic"` and `simulated=false`; failures never fall back to fixture findings.

## Product boundaries

- Substantive findings must link to supplied document passages.
- Documented facts must remain separate from interpretations.
- Both supporting and conflicting evidence should be surfaced when present.
- The system must not invent policy clauses, dates, amounts, or deadlines.
- Missing evidence must remain unknown and produce targeted follow-up questions.
- Source checks prove that a quotation exists, not that an interpretation is correct.
- Users review and submit responses themselves.
- Drafts are user-reviewed only; the application does not send, email, or automatically submit them.
- There is no automatic submission or promise of a successful appeal.
- Development fixtures are clearly labeled fictional documents, not real customer cases.

## Explicitly out of scope for this milestone

- Additional live model providers, model downloads, paid tools, prompt caching, and multi-model routing.
- OCR or retrieval.
- Automatic appeal submission, emailing, and PDF export.
- Authentication, database, persistence, deployment, or cloud resources.
- Insurance appeals, bank chargebacks, legal advice, and automatic submission.
- Multi-agent orchestration.

## Document extraction limitations

PDF extraction uses `pypdf` locally and may produce reading-order errors for tables and multi-column layouts. It does not reproduce visual layout perfectly. Empty-text pages are warnings rather than proof that OCR is needed, and OCR is not implemented. Uploaded originals are processed in bounded memory and are not retained by the application.

The 10 MiB upload, 30-page PDF, and 100,000-character extracted-text limits prevent unbounded normal inputs but do not make PDF parsing fully secure. Public deployment will require process isolation, timeouts, stronger resource controls, and security review.

## Drafting safeguards

The drafting request includes the original source passages and the already reviewed analysis as untrusted content. The server revalidates the analysis citations, compares its SHA-256 fingerprint with the current case, and derives the permitted draft type in application code: reconsideration request for potentially supported cases, clarification request for insufficient evidence, or an explicitly selected goodwill request for no supported basis. A matching fingerprint proves only that the submitted case representation is unchanged; it does not prove analysis authenticity or semantic correctness. Reference checks prove that quoted text exists, not that the model's interpretation is correct. Name, remedy, document, and analysis changes make a generated draft outdated in the browser.

## Next milestone

Next work can improve document ingestion and the review interface, then evaluate the drafting experience with additional offline fixtures and human review. A separately selected live provider may replace or supplement Anthropic later.

## Anthropic integration limitations

The live path sends extracted document text, document IDs, passage IDs, page numbers, and titles to Anthropic. The application asks for structured JSON and validates the returned Pydantic content and every source quotation. Quotation validation proves that a source and quotation exist in the submitted case; it does not prove semantic correctness or legal eligibility. The current provider does not enable extended/adaptive thinking, does not retry, and permits one live generation at a time. Token counting is performed before generation when supported by the SDK. Prepaid balance and account auto-reload settings remain account-level controls outside this application.
