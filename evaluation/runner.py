"""Sequential, offline-by-default evaluation runner for synthetic cases."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from appeal_agent.config import Settings, get_settings
from appeal_agent.models import Analysis
from appeal_agent.providers import (
    SONNET_INPUT_PRICE_PER_MTOK,
    SONNET_OUTPUT_PRICE_PER_MTOK,
    AnalysisProviderError,
    AnthropicAnalysisProvider,
)
from appeal_agent.references import InvalidSourceReference, validate_analysis_references

from .expected_results import EXPECTED_EVALUATIONS
from .source_cases import EVALUATION_CASES


_PROMPT_VERSION_HASH = hashlib.sha256(AnthropicAnalysisProvider._system_prompt().encode("utf-8")).hexdigest()


def prompt_hash() -> str:
    return _PROMPT_VERSION_HASH


def maximum_request_cost(settings: Settings) -> float:
    return round(
        settings.anthropic_max_input_tokens / 1_000_000 * SONNET_INPUT_PRICE_PER_MTOK
        + settings.anthropic_max_output_tokens / 1_000_000 * SONNET_OUTPUT_PRICE_PER_MTOK,
        8,
    )


@dataclass
class Budget:
    limit_usd: float
    reserved_usd: float = 0.0

    def reserve(self, amount: float) -> bool:
        if self.reserved_usd + amount > self.limit_usd + 1e-12:
            return False
        self.reserved_usd = round(self.reserved_usd + amount, 8)
        return True


def _usage(provider: Any) -> dict[str, Any]:
    record = getattr(provider, "last_usage", None)
    if record is None:
        return {"input_tokens": None, "output_tokens": None, "estimated_cost_usd": None, "status": "unknown"}
    return {
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "estimated_cost_usd": record.estimated_cost_usd,
        "status": record.status,
    }


def _output(provider: Any, analysis: Analysis | None) -> Any:
    raw = getattr(provider, "last_raw_output", None)
    if raw is not None:
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return raw
    return analysis.model_dump(mode="json") if analysis is not None else None


def _base_result(case_id: str, settings: Settings, live: bool) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "synthetic": True,
        "model_id": settings.anthropic_model if live else None,
        "prompt_version_hash": prompt_hash(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "returned_assessment": None,
        "allowed_assessments": list(EXPECTED_EVALUATIONS[case_id].allowed_assessments),
        "assessment_matches_allowed": None,
        "citation_validation": "not_run",
        "latency_ms": None,
        "usage": {"input_tokens": None, "output_tokens": None, "estimated_cost_usd": None, "status": "not_run"},
        "maximum_cost_reserved_usd": 0.0,
        "actual_model_output": None,
        "error": None,
        "model_quality_counted": live,
    }


async def _run_live_case(case_id: str, settings: Settings, budget: Budget) -> dict[str, Any]:
    result = _base_result(case_id, settings, live=True)
    try:
        provider = AnthropicAnalysisProvider(settings)
    except AnalysisProviderError as exc:
        result.update(status="configuration_error", error={"code": exc.code, "message": str(exc)})
        return result

    reservation = maximum_request_cost(settings)
    if not budget.reserve(reservation):
        result.update(
            status="budget_blocked",
            maximum_cost_reserved_usd=reservation,
            error={"code": "run_budget_exceeded", "message": "The next request's maximum estimated cost exceeds the remaining run budget."},
        )
        return result
    result["maximum_cost_reserved_usd"] = reservation
    started = time.perf_counter()
    analysis: Analysis | None = None
    try:
        # Only the source Case is passed to the provider. Expected results remain local.
        analysis = await provider.analyze(EVALUATION_CASES[case_id])
        validate_analysis_references(EVALUATION_CASES[case_id], analysis)
        result.update(
            status="success",
            returned_assessment=analysis.assessment.value,
            assessment_matches_allowed=analysis.assessment.value in EXPECTED_EVALUATIONS[case_id].allowed_assessments,
            citation_validation="passed",
        )
    except AnalysisProviderError as exc:
        citation_status = "failed" if exc.code == "invalid_model_citation" else "not_run"
        result.update(
            status={
                "model_refusal": "refusal",
                "output_limit_reached": "truncation",
                "invalid_model_output": "validation_failure",
                "invalid_model_citation": "validation_failure",
            }.get(exc.code, "error"),
            citation_validation=citation_status,
            error={"code": exc.code, "message": str(exc)},
        )
    except InvalidSourceReference as exc:
        result.update(status="validation_failure", citation_validation="failed", error={"code": "invalid_model_citation", "message": str(exc)})
    except Exception:
        result.update(status="error", error={"code": "evaluation_error", "message": "The evaluation case failed without exposing provider details."})
    finally:
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result["usage"] = _usage(provider)
        result["actual_model_output"] = _output(provider, analysis)
    return result


def _dry_result(case_id: str, settings: Settings) -> dict[str, Any]:
    result = _base_result(case_id, settings, live=False)
    result.update(status="dry_run", model_quality_counted=False)
    return result


def _write_result(handle: Any, result: dict[str, Any]) -> None:
    handle.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    handle.flush()


async def run_evaluation(case_ids: list[str], *, live: bool, budget_usd: float, output_path: Path, settings: Settings) -> dict[str, Any]:
    budget = Budget(budget_usd)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = {"selected": len(case_ids), "dry_run": 0, "live_attempted": 0, "success": 0, "failure": 0, "budget_blocked": 0}
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for case_id in case_ids:
            if live:
                counts["live_attempted"] += 1
                result = await _run_live_case(case_id, settings, budget)
            else:
                counts["dry_run"] += 1
                result = _dry_result(case_id, settings)
            if result["status"] == "success":
                counts["success"] += 1
            elif result["status"] == "budget_blocked":
                counts["budget_blocked"] += 1
            elif live:
                counts["failure"] += 1
            _write_result(handle, result)
    summary = {
        "synthetic": True,
        "live": live,
        "counts": counts,
        "budget_usd": budget_usd,
        "reserved_usd": budget.reserved_usd,
        "results_path": str(output_path),
    }
    summary_path = output_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the synthetic Appeal Agent evaluation set.")
    parser.add_argument("--live", action="store_true", help="Make bounded Anthropic calls; omitted means dry-run.")
    parser.add_argument("--max-cases", type=int, default=None, help="Maximum selected cases to process sequentially.")
    parser.add_argument("--budget-usd", type=float, default=None, help="Required with --live; maximum reserved cost for this run.")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="Case ID to run; repeat to select multiple cases.")
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/latest.jsonl"), help="JSONL result path.")
    args = parser.parse_args(argv)
    if args.live and (args.budget_usd is None or args.budget_usd <= 0):
        parser.error("--live requires a positive --budget-usd")
    if args.max_cases is not None and args.max_cases <= 0:
        parser.error("--max-cases must be positive")
    selected = args.case_ids or list(EVALUATION_CASES)
    unknown = [case_id for case_id in selected if case_id not in EVALUATION_CASES]
    if unknown:
        parser.error(f"unknown case ID: {', '.join(unknown)}")
    args.selected_case_ids = selected[: args.max_cases]
    if args.budget_usd is None:
        args.budget_usd = 0.0
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = get_settings()
    summary = asyncio.run(run_evaluation(args.selected_case_ids, live=args.live, budget_usd=args.budget_usd, output_path=args.output, settings=settings))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
