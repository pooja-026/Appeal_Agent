# Project scope

## Goal

Appeal Agent will help users understand a denial, compare it with supplied policy terms, identify missing evidence, and prepare an evidence-backed appeal for the user to review.

The first development scenario is a retailer refund denial. Other denial categories are future scope.

## Planned workflow

1. Upload documents.
2. Extract facts with source references.
3. Compare the denial with supplied policy terms.
4. Ask for missing information.
5. Draft an appeal and evidence checklist for user review.

## Current implementation status

This foundation includes:

- A small FastAPI backend package.
- `GET /health`, returning `{"status": "ok"}`.
- Environment-based configuration with local `.env` support.
- Dependency declarations and a Python test setup.
- Project documentation and an MIT license.

The server starts without a Nebius API key. NVIDIA Nemotron inference through Nebius Token Factory is intentionally not implemented yet, and no model ID is specified.

## Product boundaries

- Substantive findings must link to supplied document passages.
- Documented facts must remain separate from interpretations.
- The system must surface both supporting and conflicting evidence.
- The system must not invent policy clauses, dates, amounts, or deadlines.
- The system must explain when evidence is insufficient.
- Users review and submit appeals themselves.
- There is no automated appeal submission or promise of a successful appeal.
- Development and demonstrations use clearly labeled fictional documents.

## Explicitly out of scope for this foundation

- Document upload, parsing, OCR, or document processing.
- Inference calls or model routing.
- Agents and orchestration.
- React/TypeScript frontend.
- Database or persistence layer.
- Automated submission to a retailer, insurer, or other third party.
