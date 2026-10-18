# Appeal Agent

Appeal Agent is an independent portfolio project for helping consumers understand denied retailer refund requests, compare a denial with supplied policy terms, identify missing evidence, and prepare an evidence-backed response for review.

The current scope is damaged or incorrect online purchases where a retailer denied a refund. Insurance appeals, bank chargebacks, legal advice, and automatic submission are outside this milestone.

## What works today

- FastAPI backend with `GET /health`.
- Validated case, document, passage, finding, policy-clause, missing-evidence, assessment, and source-reference schemas.
- Three clearly fictional, internally consistent sample cases.
- `GET /sample-cases` and `GET /sample-cases/{case_id}`.
- `POST /analysis` using a deterministic local mock provider.
- `POST /documents/extract` for local text extraction from `.txt` and text-based `.pdf` files.
- Source-reference validation for cited documents, passages, and quotations.
- React/TypeScript/Vite frontend with fictional sample review and local document extraction flows.
- Typed frontend API client, evidence navigation, upload warnings, and in-memory document workspace.
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

## Run the application

Run the backend and frontend in separate Windows PowerShell terminals. The Vite development server proxies `/api/*` requests to the FastAPI server at `127.0.0.1:8000`; the backend routes themselves remain available at their existing paths.

### Terminal 1: FastAPI backend

```powershell
python -m uvicorn appeal_agent.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. If the virtual environment is not activated, use:

```powershell
.\.venv314\Scripts\python.exe -m uvicorn appeal_agent.main:app --reload
```

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### Terminal 2: React frontend

```powershell
Set-Location .\frontend
npm install
npm run dev
```

Open the user-facing application at `http://localhost:5173/`. The API explorer remains at `http://127.0.0.1:8000/docs`.

The frontend currently supports fictional example findings and real local extraction only. Uploaded documents are not sent to `/analysis`, because simulated analysis intentionally accepts only unchanged authored sample cases.

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

## Extract a document

Supported formats and limits:

- UTF-8 `.txt` files.
- PDFs with extractable text, processed page by page.
- Maximum upload size: 10 MiB.
- Maximum PDF length: 30 pages.
- Maximum extracted text: 100,000 characters.
- Long text is split into deterministic passages of approximately 1,600 characters without combining separate PDF pages.

Open `/docs`, select `POST /documents/extract`, choose a fictional sample file, select a document type, and execute the request. The response contains the extracted `document`, metadata, stable passage IDs, one-based PDF page numbers, and warnings.

PowerShell example:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/documents/extract" `
  -F "file=@examples/fictional-refund-sample.pdf" `
  -F "document_type=receipt" `
  -F "title=Fictional refund sample"
```

For a text file:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/documents/extract" `
  -F "file=@examples/fictional-refund-sample.txt" `
  -F "document_type=correspondence"
```

The files in `examples/` are clearly fictional and are for local manual testing only. Uploaded originals are read in bounded chunks, processed in memory, and not retained by the application after the request. The filename is used only as a title default; it is never used as a filesystem path.

PDF extraction may produce reading-order errors, especially for tables and multi-column layouts. It does not guarantee visual-layout fidelity. Empty-text pages are reported as warnings because they may be blank or image-based; OCR is not supported yet. The current local development server is not ready for public sensitive-document uploads. Before public use, add process isolation, timeouts, stronger resource controls, and security review; the application limits reduce exposure but do not make PDF parsing fully secure.

## Tests

```powershell
python -m pytest
```

The tests are offline and do not call a model provider or any external network service.

## Citation validation limitation

The backend verifies that every cited document and passage exists in the submitted case and that the quoted text occurs in that passage, allowing only whitespace normalization. This establishes that a source and quotation exist; it does not prove that an interpretation is correct, that a policy applies legally, or that an appeal will succeed.

## Frontend behavior and limitations

- The sample flow retrieves a source case and sends that unchanged payload to `/analysis`.
- Findings preserve the documented-fact versus interpretation distinction and expose cited passages through “View evidence”.
- The upload flow accepts up to five PDF or TXT files sequentially, keeps extracted documents in memory only, and clears them on refresh.
- Uploaded documents show extracted text and warnings but do not receive canned sample findings or AI analysis.
- Frontend tests cover sample rendering, evidence navigation, upload errors, and stale-response handling.

## Boundaries and next milestone

Users review and submit responses themselves. This milestone does not include document ingestion, upload parsing, OCR, retrieval, appeal drafting, authentication, a database, deployment, a frontend, or a multi-agent framework.

The next milestone is improving document ingestion and the review interface, followed by selecting and integrating a live model provider separately.
