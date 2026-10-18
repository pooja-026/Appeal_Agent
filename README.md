# Appeal Agent

Appeal Agent is an independent portfolio project for helping consumers understand denied retailer refund requests, compare a denial with supplied policy terms, identify missing evidence, and prepare an evidence-backed response for review.

The current scope is damaged or incorrect online purchases where a retailer denied a refund. Insurance appeals, bank chargebacks, legal advice, and automatic submission are outside this milestone.

## What works today

- FastAPI backend with `GET /health`.
- Validated case, document, passage, finding, policy-clause, missing-evidence, assessment, and source-reference schemas.
- Three clearly fictional, internally consistent sample cases.
- `GET /sample-cases` and `GET /sample-cases/{case_id}`.
- `POST /analysis` using a deterministic local mock provider.
- Source-reference validation for cited documents, passages, and quotations.
- Offline tests with no network or model calls.

## Important: analysis is simulated

Analysis is currently simulated. `AI_PROVIDER=mock` is the only supported provider, and every analysis response includes `provider: "mock"` and `simulated: true`. The mock provider recognizes only the unchanged authored sample cases; it does not understand arbitrary documents and makes zero external inference requests.

No live model provider has been selected. No credentials or model downloads are required.

## Requirements

- Python 3.11 or newer
- Windows PowerShell

## Setup in Windows PowerShell

From the project folder, use a standard CPython installation. If the Python launcher has a broken 3.11/3.12 entry, use an available standard installation such as 3.14:

```powershell
py -3.14 -m venv .venv314 --without-pip
python -m pip --python .venv314 install -e ".[dev]"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv314\Scripts\Activate.ps1
```

With a standard Python installation that includes `ensurepip`, the shorter setup is:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The server defaults to mock mode, so copying `.env.example` is optional. If you do create `.env`, it should contain:

```text
AI_PROVIDER=mock
```

Do not commit `.env`.

If an older local `.env` still contains `NEBIUS_API_KEY`, `NEBIUS_BASE_URL`, or `NEBIUS_MODEL`, remove those variables manually. This project does not read them. Do not paste or print your `.env` contents.

## Run the API

```powershell
python -m uvicorn appeal_agent.main:app --reload
```

The API is available at `http://127.0.0.1:8000`.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:

```text
status
------
ok
```

## Try the sample workflow

Open the interactive API documentation at:

```text
http://127.0.0.1:8000/docs
```

Use `GET /sample-cases` to list cases. Then use `GET /sample-cases/{case_id}` to retrieve source documents. Copy that response into the request body for `POST /analysis`.

PowerShell can perform the same workflow without manually reconstructing JSON:

```powershell
$sample = Invoke-RestMethod http://127.0.0.1:8000/sample-cases/case-a-damaged-sale
$sampleJson = $sample | ConvertTo-Json -Depth 20
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analysis -ContentType "application/json" -Body $sampleJson
```

Try `case-b-missing-dates` to see an `insufficient_evidence` assessment with follow-up questions, or `case-c-final-sale-change-mind` to see `no_supported_basis`.

## Tests

```powershell
python -m pytest
```

The tests are offline and do not call a model provider or any external network service.

## Citation validation limitation

The backend verifies that every cited document and passage exists in the submitted case and that the quoted text occurs in that passage, allowing only whitespace normalization. This establishes that a source and quotation exist; it does not prove that an interpretation is correct, that a policy applies legally, or that an appeal will succeed.

## Boundaries and next milestone

Users review and submit responses themselves. This milestone does not include document ingestion, upload parsing, OCR, retrieval, appeal drafting, authentication, a database, deployment, a frontend, or a multi-agent framework.

The next milestone is document ingestion and a review interface, followed by selecting and integrating a live model provider separately.
