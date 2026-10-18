# Appeal Agent

Appeal Agent is a foundation for helping users understand a denial, compare it with supplied policy terms, identify missing evidence, and prepare an evidence-backed appeal for user review.

The first development scenario is a retailer refund denial. This repository currently contains only the backend foundation and a health endpoint. Document processing, inference, frontend, agents, and model routing are intentionally out of scope for this step.

## Requirements

- Python 3.11 or newer
- Windows PowerShell

## Setup in Windows PowerShell

From the project folder:

```powershell
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

If Python 3.11 is not the installed launcher target, use another installed Python 3.11+ interpreter explicitly, for example `py -3.14 -m venv .venv`.

## Run the API

```powershell
python -m uvicorn appeal_agent.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Check the health endpoint in a second PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:

```text
status
------
ok
```

Run the tests with:

```powershell
python -m pytest
```

## Configuration

Copy `.env.example` to `.env` for local configuration. Nebius credentials are optional at this stage and are not used by the server yet. No model ID is assumed or bundled.

## Scope

See [docs/project-scope.md](docs/project-scope.md) for the planned workflow, current status, and product boundaries.
