import json
from types import SimpleNamespace

import pytest

from appeal_agent.config import Settings
from appeal_agent.models import Analysis, Assessment
from evaluation import runner
from evaluation.expected_results import EXPECTED_EVALUATIONS
from evaluation.source_cases import EVALUATION_CASES
from appeal_agent.references import validate_source_reference


class FakeEvaluationProvider:
    calls: list[str] = []
    received_cases: list[dict] = []
    mode = "success"

    def __init__(self, settings: Settings) -> None:
        self.last_raw_output = None
        self.last_usage = SimpleNamespace(input_tokens=100, output_tokens=50, estimated_cost_usd=0.0007, status="received")

    async def analyze(self, case):
        self.calls.append(case.case_id)
        self.received_cases.append(case.model_dump(mode="json"))
        if self.mode == "unknown":
            self.last_usage = SimpleNamespace(input_tokens=None, output_tokens=None, estimated_cost_usd=None, status="unknown")
            raise runner.AnalysisProviderError("timed out; usage is unknown", code="provider_timeout", status_code=504)
        result = Analysis(
            case_id=case.case_id,
            findings=[],
            supporting_policy_clauses=[],
            conflicting_policy_clauses=[],
            missing_evidence=[],
            follow_up_questions=[],
            assessment=Assessment.INSUFFICIENT_EVIDENCE,
            explanation="Synthetic test output.",
            provider="anthropic",
            simulated=False,
        )
        self.last_raw_output = result.model_dump_json()
        return result


def _settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        ai_provider="anthropic",
        anthropic_api_key="not-real",
        anthropic_model="test-model",
        **overrides,
    )


@pytest.fixture(autouse=True)
def reset_fake(monkeypatch):
    FakeEvaluationProvider.calls = []
    FakeEvaluationProvider.received_cases = []
    FakeEvaluationProvider.mode = "success"
    monkeypatch.setattr(runner, "AnthropicAnalysisProvider", FakeEvaluationProvider)


@pytest.mark.anyio
async def test_dry_run_is_provider_free_and_writes_each_result(tmp_path):
    output = tmp_path / "dry.jsonl"
    summary = await runner.run_evaluation(
        ["eval-01-promotion-damage", "eval-02-final-sale"],
        live=False,
        budget_usd=0.01,
        output_path=output,
        settings=_settings(),
    )
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [record["status"] for record in records] == ["dry_run", "dry_run"]
    assert FakeEvaluationProvider.calls == []
    assert summary["counts"] == {"selected": 2, "dry_run": 2, "live_attempted": 0, "success": 0, "failure": 0, "budget_blocked": 0}


@pytest.mark.anyio
async def test_budget_reservation_blocks_before_generation(tmp_path):
    output = tmp_path / "budget.jsonl"
    summary = await runner.run_evaluation(
        ["eval-01-promotion-damage", "eval-02-final-sale"],
        live=True,
        budget_usd=0.08,
        output_path=output,
        settings=_settings(),
    )
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert records[0]["status"] == "success"
    assert records[1]["status"] == "budget_blocked"
    assert len(FakeEvaluationProvider.calls) == 1
    assert summary["counts"]["budget_blocked"] == 1


@pytest.mark.anyio
async def test_unknown_usage_keeps_reserved_cost(tmp_path):
    FakeEvaluationProvider.mode = "unknown"
    output = tmp_path / "unknown.jsonl"
    summary = await runner.run_evaluation(
        ["eval-03-missing-dates"],
        live=True,
        budget_usd=0.25,
        output_path=output,
        settings=_settings(),
    )
    record = json.loads(output.read_text(encoding="utf-8").strip())
    assert record["status"] == "error"
    assert record["usage"]["status"] == "unknown"
    assert record["maximum_cost_reserved_usd"] == summary["reserved_usd"]
    assert summary["reserved_usd"] > 0


def test_case_selection_and_expected_answers_are_separate():
    args = runner._parse_args(["--case-id", "eval-04-late-report", "--case-id", "eval-07-evidence-present", "--max-cases", "1"])
    assert args.selected_case_ids == ["eval-04-late-report"]
    assert "allowed_assessments" not in EVALUATION_CASES["eval-04-late-report"].model_dump(mode="json")
    assert EXPECTED_EVALUATIONS["eval-04-late-report"].case_id not in EVALUATION_CASES["eval-04-late-report"].model_dump(mode="json")


def test_every_expected_relevant_passage_exists_in_its_source_case():
    for case_id, expectation in EXPECTED_EVALUATIONS.items():
        case = EVALUATION_CASES[case_id]
        for reference in expectation.relevant_sources:
            validate_source_reference(case, reference)
