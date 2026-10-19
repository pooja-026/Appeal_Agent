from types import SimpleNamespace

import pytest

from appeal_agent.config import Settings
from appeal_agent.fixtures.expected_findings import EXPECTED_ANALYSES
from appeal_agent.fixtures.source_documents import SAMPLE_CASES
from appeal_agent.models import AnalysisContent
from appeal_agent.providers import AnalysisProviderError, AnthropicAnalysisProvider


def _response(text: str, *, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=120, output_tokens=240),
    )


class FakeMessages:
    def __init__(self, response: SimpleNamespace | Exception) -> None:
        self.response = response
        self.create_calls = 0
        self.count_calls = 0

    async def count_tokens(self, **_: object) -> SimpleNamespace:
        self.count_calls += 1
        return SimpleNamespace(input_tokens=120)

    async def create(self, **_: object) -> SimpleNamespace:
        self.create_calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _provider(messages: FakeMessages, **overrides: object) -> AnthropicAnalysisProvider:
    values = {
        "ai_provider": "anthropic",
        "anthropic_api_key": "test-key-not-real",
        "anthropic_model": "claude-sonnet-5-5",
        **overrides,
    }
    return AnthropicAnalysisProvider(Settings(**values), client=SimpleNamespace(messages=messages))


@pytest.mark.anyio
async def test_valid_structured_response_is_validated_and_tagged() -> None:
    case = SAMPLE_CASES["case-a-damaged-sale"]
    expected = EXPECTED_ANALYSES[case.case_id].model_dump(
        mode="json", exclude={"case_id", "provider", "simulated", "model", "case_fingerprint"}
    )
    messages = FakeMessages(_response(AnalysisContent.model_validate(expected).model_dump_json()))

    analysis = await _provider(messages).analyze(case)

    assert analysis.provider == "anthropic"
    assert analysis.model == "claude-sonnet-5-5"
    assert analysis.simulated is False
    assert messages.count_calls == 1
    assert messages.create_calls == 1


@pytest.mark.anyio
async def test_fabricated_citation_is_rejected_without_success() -> None:
    case = SAMPLE_CASES["case-a-damaged-sale"]
    expected = EXPECTED_ANALYSES[case.case_id].model_dump(
        mode="json", exclude={"case_id", "provider", "simulated", "model", "case_fingerprint"}
    )
    expected["findings"][0]["sources"][0]["quoted_text"] = "invented quote"
    messages = FakeMessages(_response(AnalysisContent.model_validate(expected).model_dump_json()))

    with pytest.raises(AnalysisProviderError, match="citation") as error:
        await _provider(messages).analyze(case)
    assert error.value.code == "invalid_model_citation"


@pytest.mark.anyio
async def test_malformed_and_truncated_output_fail_clearly() -> None:
    case = SAMPLE_CASES["case-a-damaged-sale"]
    malformed = _provider(FakeMessages(_response("not-json")))
    with pytest.raises(AnalysisProviderError) as malformed_error:
        await malformed.analyze(case)
    assert malformed_error.value.code == "invalid_model_output"

    truncated = _provider(FakeMessages(_response("{}", stop_reason="max_tokens")))
    with pytest.raises(AnalysisProviderError) as truncated_error:
        await truncated.analyze(case)
    assert truncated_error.value.code == "output_limit_reached"


@pytest.mark.anyio
async def test_missing_configuration_and_input_limits_block_generation() -> None:
    with pytest.raises(AnalysisProviderError, match="API_KEY"):
        AnthropicAnalysisProvider(
            Settings(_env_file=None, ai_provider="anthropic", anthropic_api_key="", anthropic_model="test-model"),
            client=SimpleNamespace(),
        )

    case = SAMPLE_CASES["case-a-damaged-sale"]
    messages = FakeMessages(_response("{}"))
    provider = _provider(messages, anthropic_max_input_characters=10)
    with pytest.raises(AnalysisProviderError) as limit_error:
        await provider.analyze(case)
    assert limit_error.value.code == "input_size_limit_exceeded"
    assert messages.count_calls == 0
    assert messages.create_calls == 0


@pytest.mark.anyio
async def test_provider_errors_are_mapped_without_fallback() -> None:
    class RateLimitError(Exception):
        pass

    case = SAMPLE_CASES["case-a-damaged-sale"]
    messages = FakeMessages(RateLimitError())
    provider = _provider(messages)
    with pytest.raises(AnalysisProviderError) as error:
        await provider.analyze(case)
    assert error.value.code == "provider_rate_limit"
    assert provider.last_usage is not None
    assert provider.last_usage.status == "unknown"
