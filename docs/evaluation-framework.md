# Synthetic evaluation framework

Appeal Agent now includes eight clearly synthetic cases for evaluating the existing analysis workflow. They are not customer records and do not represent real outcomes.

The model-input cases are in [`evaluation/source_cases.py`](../evaluation/source_cases.py). Expected assessments, required observations, prohibited claims, source passages, and rationales are separate in [`evaluation/expected_results.py`](../evaluation/expected_results.py). The runner passes only a `Case` to the provider; it never sends expected answers or reviewer notes.

## Dry run

Dry-run mode is the default and makes no provider calls:

```powershell
Set-Location C:\Users\HP\Desktop\Appeal_Agent
.\.venv314\Scripts\python.exe -m evaluation.runner
```

Results are written incrementally to `evaluation/results/latest.jsonl` by default. A summary is written beside it as `latest.summary.json`. These dry-run records are setup records, not model-quality results.

## Bounded live run

Live execution requires an explicit `--live` flag and a positive run budget. This command selects two cases and reserves no more than the configured maximum estimated cost for the run:

```powershell
Set-Location C:\Users\HP\Desktop\Appeal_Agent
.\.venv314\Scripts\python.exe -m evaluation.runner --live --max-cases 2 --budget-usd 0.25 --case-id eval-01-promotion-damage --case-id eval-05-contradictory-dates
```

The runner processes cases sequentially, makes no automatic retries, reserves the maximum per-request estimate before each generation, and stops before a call that could exceed the remaining budget. If a provider timeout leaves usage unknown, the reservation is retained. Each result is flushed to JSONL as soon as that case finishes, so interrupted runs retain completed records.

Live result records include the synthetic case ID, model ID, analysis prompt hash, timestamp, status, returned assessment, allowed-label comparison, citation-validation status, latency, usage, reserved cost, sanitized error information, and the structured model output when available. Failures and budget-blocked cases remain visible. Counts and denominators are in the summary file; dry runs and mocked responses are never counted as model-quality results.

## Human review

Use [`docs/evaluation-review-sheet.md`](./evaluation-review-sheet.md) for semantic review. Automated schema and quotation checks establish that cited sources and quoted strings exist; they cannot establish that a claim is factually correct, semantically complete, or properly interpreted. Leave review fields as `not reviewed` until a person examines the output.

This is an eight-case synthetic evaluation, not a statistically meaningful estimate of production quality. It does not cover all document layouts, languages, retailers, policies, OCR behavior, or adversarial inputs. Before relying on results, review both successes and failures and preserve the exact prompt hash and model ID.
