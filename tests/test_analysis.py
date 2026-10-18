import pytest
from fastapi import HTTPException

from appeal_agent.api import analyze_case, get_sample_case, list_sample_cases
from appeal_agent.fixtures.expected_findings import EXPECTED_ANALYSES
from appeal_agent.fixtures.source_documents import SAMPLE_CASES
from appeal_agent.models import Assessment, SourceReference
from appeal_agent.providers import MockAnalysisProvider, MockAnalysisUnavailable
from appeal_agent.references import InvalidSourceReference, validate_source_reference


def test_all_sample_cases_return_expected_simulated_assessments() -> None:
    expected = {
        "case-a-damaged-sale": Assessment.POTENTIALLY_SUPPORTED,
        "case-b-missing-dates": Assessment.INSUFFICIENT_EVIDENCE,
        "case-c-final-sale-change-mind": Assessment.NO_SUPPORTED_BASIS,
    }

    summaries = list_sample_cases()

    assert {summary.case_id for summary in summaries} == set(expected)
    for summary in summaries:
        analysis = analyze_case(get_sample_case(summary.case_id))
        assert analysis.assessment is expected[summary.case_id]
        assert analysis.provider == "mock"
        assert analysis.simulated is True


def test_sample_case_response_contains_sources_but_not_evaluation_answers() -> None:
    response = get_sample_case("case-a-damaged-sale")
    response_text = response.model_dump_json()

    assert "a-policy-p1" in response_text
    assert "potentially_supported" not in response_text
    assert "findings" not in response_text
    assert "follow_up_questions" not in response_text


def test_modified_or_unknown_mock_input_is_not_given_canned_success() -> None:
    modified = get_sample_case("case-a-damaged-sale").model_copy(deep=True)
    modified.title = "Modified customer case"

    with pytest.raises(HTTPException) as modified_error:
        analyze_case(modified)
    assert getattr(modified_error.value, "status_code", None) == 422

    unknown = get_sample_case("case-a-damaged-sale").model_copy(deep=True)
    unknown.case_id = "unknown-case"
    with pytest.raises(MockAnalysisUnavailable):
        MockAnalysisProvider(SAMPLE_CASES, {}).analyze(unknown)


def test_missing_dates_remain_unknown_and_trigger_questions() -> None:
    analysis = analyze_case(get_sample_case("case-b-missing-dates"))

    assert analysis.assessment is Assessment.INSUFFICIENT_EVIDENCE
    assert analysis.documented_deadline is None
    assert len(analysis.follow_up_questions) == 2
    assert {item.item for item in analysis.missing_evidence} == {
        "Delivery date",
        "Damage-report date",
    }


def test_nonexistent_reference_and_fabricated_quote_are_rejected() -> None:
    case = get_sample_case("case-a-damaged-sale")

    with pytest.raises(InvalidSourceReference, match="does not exist"):
        validate_source_reference(
            case,
            SourceReference(
                document_id="missing-document",
                passage_id="missing-passage",
                quoted_text="anything",
            ),
        )

    bad_analysis = EXPECTED_ANALYSES["case-a-damaged-sale"].model_copy(deep=True)
    bad_analysis.supporting_policy_clauses[0].source.quoted_text = "fabricated clause"
    from appeal_agent.references import validate_analysis_references

    with pytest.raises(InvalidSourceReference, match="not present"):
        validate_analysis_references(case, bad_analysis)

    with pytest.raises(InvalidSourceReference, match="not present"):
        validate_source_reference(
            case,
            SourceReference(
                document_id="a-policy",
                passage_id="a-policy-p1",
                quoted_text="This policy clause was invented.",
            ),
        )


def test_unsupported_provider_value_fails_clearly() -> None:
    from appeal_agent.config import Settings

    with pytest.raises(ValueError, match="Unsupported AI_PROVIDER"):
        Settings(ai_provider="unselected-provider")
