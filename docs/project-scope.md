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
- A vendor-neutral analysis-provider interface and deterministic `MockAnalysisProvider`.
- Source-reference validation for findings, policy clauses, and documented deadlines.
- Local sample-case and analysis APIs.
- Focused offline tests.

Analysis is currently simulated. The only supported configuration is `AI_PROVIDER=mock`; responses explicitly identify `provider="mock"` and `simulated=true`. The mock provider accepts only the unchanged authored sample cases and makes no external requests.

## Product boundaries

- Substantive findings must link to supplied document passages.
- Documented facts must remain separate from interpretations.
- Both supporting and conflicting evidence should be surfaced when present.
- The system must not invent policy clauses, dates, amounts, or deadlines.
- Missing evidence must remain unknown and produce targeted follow-up questions.
- Source checks prove that a quotation exists, not that an interpretation is correct.
- Users review and submit responses themselves.
- There is no automatic submission or promise of a successful appeal.
- Development fixtures are clearly labeled fictional documents, not real customer cases.

## Explicitly out of scope for this milestone

- Live model providers or vendor SDKs.
- Document upload parsing, OCR, or retrieval.
- Frontend or review UI.
- Appeal drafting.
- Authentication, database, persistence, deployment, or cloud resources.
- Insurance appeals, bank chargebacks, legal advice, and automatic submission.
- Multi-agent orchestration.

## Next milestone

Build document ingestion and a review interface. After that, select and integrate a live model provider as a separate decision with explicit configuration and tests.
