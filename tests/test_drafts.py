from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from appeal_agent import api
from appeal_agent.config import Settings
from appeal_agent.fixtures.expected_findings import EXPECTED_ANALYSES
from appeal_agent.fixtures.source_documents import SAMPLE_CASES
from appeal_agent.models import DraftContent, DraftParagraph, DraftType, SourceReference, UsageMetadata
from appeal_agent.references import case_fingerprint


def _live_request(case_id: str, *, reviewed: bool = True, goodwill: bool = False, desired_outcome: str = "either"):
    case = SAMPLE_CASES[case_id].model_copy(deep=True)
    analysis = EXPECTED_ANALYSES[case_id].model_copy(update={
        "provider": "anthropic",
        "simulated": False,
        "model": "claude-sonnet-5-5",
        "case_fingerprint": case_fingerprint(case),
    })
    return api.DraftRequest(
        case=case,
        analysis=analysis,
        name=None,
        desired_outcome=desired_outcome,
        reviewed_findings=reviewed,
        goodwill_requested=goodwill,
    )


class FakeDraftProvider:
    calls: list[DraftType] = []
    outcomes: list[str] = []
    invalid = False
    invalid_recipient = False

    def __init__(self, settings: Settings) -> None:
        self.last_usage = SimpleNamespace(input_tokens=100, output_tokens=200, estimated_cost_usd=0.01, status="received")

    async def generate_draft(self, case, analysis, *, name, desired_outcome, draft_type):
        self.calls.append(draft_type)
        self.outcomes.append(desired_outcome.value)
        document = case.documents[0]
        passage = document.passages[0]
        quote = "fabricated quote" if self.invalid else passage.text[: min(20, len(passage.text))]
        recipient_name = "Unsupported Retailer" if self.invalid_recipient else None
        recipient_source = SourceReference(
            document_id=document.document_id,
            passage_id=passage.passage_id,
            quoted_text="fabricated retailer quote",
        ) if self.invalid_recipient else None
        return DraftContent(
            draft_type=draft_type,
            subject="Request for review",
            recipient_name=recipient_name,
            recipient_source=recipient_source,
            paragraphs=[DraftParagraph(
                paragraph_id="paragraph-1",
                text="Please review the supplied records.",
                sources=[SourceReference(document_id=document.document_id, passage_id=passage.passage_id, quoted_text=quote)],
            )],
            evidence_checklist=[],
            confirmation_items=[],
        )


@pytest.fixture(autouse=True)
def configured_provider(monkeypatch):
    FakeDraftProvider.calls = []
    FakeDraftProvider.outcomes = []
    FakeDraftProvider.invalid = False
    FakeDraftProvider.invalid_recipient = False
    monkeypatch.setattr(api, "get_settings", lambda: Settings(_env_file=None, ai_provider="anthropic", anthropic_api_key="not-real", anthropic_model="claude-sonnet-5-5"))
    monkeypatch.setattr(api, "AnthropicAnalysisProvider", FakeDraftProvider)


@pytest.mark.anyio
async def test_assessment_gates_draft_type_and_goodwill_choice():
    await api.generate_draft(_live_request("case-a-damaged-sale", desired_outcome="refund"))
    await api.generate_draft(_live_request("case-b-missing-dates", desired_outcome="replacement"))
    with pytest.raises(HTTPException) as blocked:
        await api.generate_draft(_live_request("case-c-final-sale-change-mind"))
    assert blocked.value.status_code == 422
    await api.generate_draft(_live_request("case-c-final-sale-change-mind", goodwill=True, desired_outcome="either"))
    assert FakeDraftProvider.calls == [DraftType.RECONSIDERATION_REQUEST, DraftType.CLARIFICATION_REQUEST, DraftType.GOODWILL_REQUEST]
    assert FakeDraftProvider.outcomes == ["refund", "replacement", "either"]


@pytest.mark.anyio
async def test_review_confirmation_and_stale_analysis_are_required():
    with pytest.raises(HTTPException) as unreviewed:
        await api.generate_draft(_live_request("case-a-damaged-sale", reviewed=False))
    assert unreviewed.value.status_code == 422

    request = _live_request("case-a-damaged-sale")
    request.case.title = "Changed after analysis"
    with pytest.raises(HTTPException) as stale:
        await api.generate_draft(request)
    assert stale.value.status_code == 409


@pytest.mark.anyio
async def test_invalid_draft_citations_are_rejected():
    FakeDraftProvider.invalid = True
    with pytest.raises(HTTPException) as invalid:
        await api.generate_draft(_live_request("case-a-damaged-sale"))
    assert invalid.value.status_code == 502
    assert invalid.value.detail["code"] == "invalid_draft_citation"


@pytest.mark.anyio
async def test_unsupported_recipient_name_or_quote_is_rejected():
    FakeDraftProvider.invalid_recipient = True
    with pytest.raises(HTTPException) as invalid:
        await api.generate_draft(_live_request("case-a-damaged-sale"))
    assert invalid.value.status_code == 502
    assert invalid.value.detail["code"] == "invalid_draft_citation"
