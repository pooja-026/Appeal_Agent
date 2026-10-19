# Appeal Agent

Appeal Agent is an independent portfolio project that helps consumers understand denied retailer refund requests, compare a denial with supplied policy terms, identify missing evidence, and prepare an evidence-backed response for review.

The initial scope is damaged or incorrect online purchases where a retailer denied a refund. Insurance appeals, bank chargebacks, legal advice, and automatic submission are outside scope.

## Current status

The backend provides validated case schemas, fictional sample cases, local PDF/TXT extraction, source-reference validation, and a React/Vite interface. Sample findings remain deterministic and simulated. Uploaded documents can now be analyzed through Anthropic only when the backend is explicitly configured with `AI_PROVIDER=anthropic`; there is no silent fallback to mock findings.

Live analysis is bounded and user-triggered: one generation at a time, five documents maximum, 60,000 extracted characters maximum, 12,000 input tokens maximum, 3,000 output tokens maximum, no SDK retries, explicit timeout, and a $0.10 maximum estimated request cost. After a successful live analysis, the user can explicitly request a bounded response draft. Drafting is separately labeled and metered, requires review confirmation, and never submits anything to a retailer. The application does not record document text, letter text, or credentials. Prepaid balance and account auto-reload are account-level controls and are not replaced by these per-request limits.

## Verified Anthropic details

Verified from official Anthropic documentation on October 18, 2026:

- Recommended current Sonnet API alias: `claude-sonnet-5-5`.
- First-party Claude API availability is listed in the [official model overview](https://platform.claude.com/docs/en/models/overview).
- Standard pricing shown there is $2 per million input tokens and $10 per million output tokens for Sonnet 5.5. See the [official pricing page](https://platform.claude.com/docs/en/about-claude/pricing).
- The implementation uses the official [Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python) with `AsyncAnthropic`, `max_retries=0`, and an explicit timeout.
- The implementation uses the [Messages token-counting API](https://platform.claude.com/docs/en/api/http/messages/count_tokens) before generation and [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) through `output_config.format`.
- Current Sonnet 5.5 is documented as using adaptive thinking. This milestone does not enable thinking; the configured output limit is therefore used without adding a thinking budget.

Structured outputs can still be invalid for refusals or `max_tokens` truncation, so those responses are rejected. Quotation checks prove that a source and quotation exist in the submitted documents; they do not prove that an interpretation is semantically or legally correct.

## Configuration

Copy `.env.example` to `.env` if desired. Keep `.env` local and never commit it. The example defaults to mock mode:

```text
AI_PROVIDER=mock
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=
```

For live analysis, set `AI_PROVIDER=anthropic`, provide your backend-only `ANTHROPIC_API_KEY`, and set the explicit model ID `ANTHROPIC_MODEL=claude-sonnet-5-5`. The server, not the browser, reads the credential. Unsupported provider values produce a clear configuration error. The sample-case flow always uses mock findings and makes no model call.

## Windows PowerShell setup

Use the existing project-local Python environment. If it does not have pip, bootstrap pip inside that environment; do not install system software:

```powershell
Set-Location C:\Users\HP\Desktop\Appeal_Agent
.\.venv314\Scripts\python.exe -m ensurepip --upgrade
.\.venv314\Scripts\python.exe -m pip install -e ".[dev]"
```

Install frontend dependencies:

```powershell
Set-Location C:\Users\HP\Desktop\Appeal_Agent\frontend
npm install
```

## Run both services

Terminal 1, from the project root:

```powershell
Set-Location C:\Users\HP\Desktop\Appeal_Agent
.\.venv314\Scripts\python.exe -m uvicorn appeal_agent.main:app --reload
```

Terminal 2:

```powershell
Set-Location C:\Users\HP\Desktop\Appeal_Agent\frontend
npm run dev
```

Open the user-facing app at `http://localhost:5173/`. It is the React interface; `http://127.0.0.1:8000/docs` is the FastAPI API explorer. The frontend proxies `/api/*` to the backend.

## Try the sample flow

Use `/docs` or the frontend’s “Try an example” screen. The API equivalent is:

```powershell
$sample = Invoke-RestMethod http://127.0.0.1:8000/sample-cases/case-a-damaged-sale
$sampleJson = $sample | ConvertTo-Json -Depth 20
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analysis -ContentType "application/json" -Body $sampleJson
```

This returns `provider: "mock"` and `simulated: true`. It recognizes only unchanged authored fixtures.

## Analyze uploaded documents

After setting the live variables in `.env`, restart the backend. Open the frontend, choose “Review my documents,” upload at least one denial and one policy document, and click “Analyze my documents.” The explicit confirmation text explains that extracted text will be sent to Anthropic. Uploaded documents are held in browser memory only and refresh clears them.

The same live route is `POST /live-analysis`. The original `POST /analysis` route remains the sample-only simulated route. After reviewing a live result, use the frontend's explicit response-draft controls; the backend `POST /drafts` route revalidates the document fingerprint and citations, gates draft type from the assessment, and keeps the editable draft in browser memory. Drafting is not available for simulated examples and nothing is automatically submitted.

For one bounded command-line smoke test using tiny fictional documents, run this only after configuring the verified model ID. It requires the explicit `--live` flag and makes at most one generation request; it is not executed by the test suite:

```powershell
Set-Location C:\Users\HP\Desktop\Appeal_Agent
.\.venv314\Scripts\python.exe .\scripts\smoke_anthropic.py --live
```

It prints structured findings, token usage, and estimated cost without secrets. Never put the API key in the command line.

## Extraction and local limits

`POST /documents/extract` accepts text-based `.pdf` and UTF-8 `.txt` files. Extraction is local and temporary; originals are not retained. Limits are 10 MiB upload size, 30 PDF pages, 100,000 extracted characters, and five documents per frontend session. PDF text is extracted page by page and split deterministically without joining pages. Tables and columns may have reading-order errors, and OCR is not implemented.

PowerShell multipart example:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/documents/extract" `
  -F "file=@examples/fictional-refund-sample.pdf" `
  -F "document_type=receipt" `
  -F "title=Fictional refund sample"
```

The examples are clearly fictional and suitable for local testing only. The local development server is not ready for public sensitive-document uploads. Before public deployment, add process isolation, parser timeouts, stronger resource controls, authentication, and a security review; current limits do not make PDF parsing fully secure.

## Tests and build

## Synthetic evaluation

The repository includes eight synthetic evaluation cases and a sequential, offline-by-default runner. Source documents are separated from expected labels and reviewer notes; expected answers are never sent to the provider. See [docs/evaluation-framework.md](docs/evaluation-framework.md) and [docs/evaluation-review-sheet.md](docs/evaluation-review-sheet.md).

Dry run all eight cases without provider calls:

```powershell
Set-Location C:\Users\HP\Desktop\Appeal_Agent
.\.venv314\Scripts\python.exe -m evaluation.runner
```

An explicit bounded live run for two selected cases requires both `--live` and a run budget:

```powershell
Set-Location C:\Users\HP\Desktop\Appeal_Agent
.\.venv314\Scripts\python.exe -m evaluation.runner --live --max-cases 2 --budget-usd 0.25 --case-id eval-01-promotion-damage --case-id eval-05-contradictory-dates
```

Live evaluation was not executed as part of development verification.

Backend offline tests:

```powershell
Set-Location C:\Users\HP\Desktop\Appeal_Agent
.\.venv314\Scripts\python.exe -m pytest
```

Frontend tests and production build:

```powershell
Set-Location C:\Users\HP\Desktop\Appeal_Agent\frontend
npm test -- --run
npm run build
```

All automated tests use mocked provider responses and make no paid API calls or external inference requests.

## Boundaries and next steps

Findings must cite supplied passages, facts remain separate from interpretations, and supporting/conflicting evidence and missing information must remain visible. The system does not invent policy terms, dates, amounts, deadlines, legal rules, or success probabilities. Users review and submit any response themselves.

The next milestone is document ingestion improvements and a review interface for live results. Current drafting is a concise, editable response for review only; its original paragraph references remain separate from user edits and do not validate edited wording. Authentication, databases, retrieval, OCR, multi-agent orchestration, cloud deployment, and additional model providers remain future work.
