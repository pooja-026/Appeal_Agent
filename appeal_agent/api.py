"""HTTP routes for sample cases, local extraction, and explicitly gated analysis."""

import inspect

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from .config import get_settings
from .fixtures.expected_findings import EXPECTED_ANALYSES
from .fixtures.source_documents import SAMPLE_CASES
from .ingestion import extract_document, read_upload_limited
from .models import (
    Analysis,
    Case,
    DraftRequest,
    DraftResponse,
    DraftType,
    DocumentExtractionResponse,
    DocumentType,
    SampleCaseSummary,
    UsageMetadata,
)
from .providers import (
    AnalysisProviderError,
    AnthropicAnalysisProvider,
    MockAnalysisProvider,
    MockAnalysisUnavailable,
)
from .references import InvalidSourceReference, case_fingerprint, validate_analysis_references, validate_draft_references
from .ingestion import ExtractionProblem

router = APIRouter()

_SAMPLE_DESCRIPTIONS = {
    "case-a-damaged-sale": "A damaged sale item with timely reporting and supporting correspondence.",
    "case-b-missing-dates": "A damaged item whose delivery and reporting dates are missing.",
    "case-c-final-sale-change-mind": "A final-sale change-of-mind request covered by an explicit exclusion.",
}


def _mock_provider() -> MockAnalysisProvider:
    settings = get_settings()
    return MockAnalysisProvider(SAMPLE_CASES, EXPECTED_ANALYSES)


async def _run_provider(provider: object, case: Case) -> Analysis:
    result = provider.analyze(case)  # type: ignore[attr-defined]
    if inspect.isawaitable(result):
        return await result
    return result


@router.get("/sample-cases", response_model=list[SampleCaseSummary], tags=["samples"])
def list_sample_cases() -> list[SampleCaseSummary]:
    return [
        SampleCaseSummary(
            case_id=case.case_id,
            title=case.title,
            description=_SAMPLE_DESCRIPTIONS[case.case_id],
        )
        for case in SAMPLE_CASES.values()
    ]


@router.get("/sample-cases/{case_id}", response_model=Case, tags=["samples"])
def get_sample_case(case_id: str) -> Case:
    case = SAMPLE_CASES.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Sample case not found")
    return case.model_copy(deep=True)


@router.post("/analysis", response_model=Analysis, tags=["analysis"])
def analyze_case(case: Case) -> Analysis:
    try:
        return _mock_provider().analyze(case)
    except MockAnalysisUnavailable as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "mock_analysis_unavailable", "message": str(exc)},
        ) from exc
    except InvalidSourceReference as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis provider returned invalid source references",
        ) from exc


@router.get("/analysis/config", tags=["analysis"])
def analysis_config() -> dict[str, bool | str]:
    """Expose only whether the backend has explicitly enabled live analysis."""

    settings = get_settings()
    live_configured = (
        settings.ai_provider == "anthropic"
        and bool(settings.anthropic_api_key)
        and bool(settings.anthropic_model)
    )
    return {
        "provider": settings.ai_provider,
        "live_analysis_configured": live_configured,
    }


@router.post("/live-analysis", response_model=Analysis, tags=["analysis"])
async def live_analyze_case(case: Case) -> Analysis:
    """Analyze supplied documents with the configured live provider only."""

    settings = get_settings()
    if settings.ai_provider != "anthropic":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "live_analysis_not_enabled", "message": "Live analysis is not enabled."},
        )
    try:
        analysis = await _run_provider(AnthropicAnalysisProvider(settings), case)
        return analysis.model_copy(update={"case_fingerprint": case_fingerprint(case)})
    except AnalysisProviderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from None


@router.post(
    "/drafts",
    response_model=DraftResponse,
    tags=["drafts"],
    summary="Generate a user-reviewed reconsideration or clarification draft",
    description=(
        "Drafting is explicit and sends the current documents and reviewed analysis to Anthropic. "
        "The result is kept in memory only; nothing is sent to a retailer."
    ),
)
async def generate_draft(request: DraftRequest) -> DraftResponse:
    settings = get_settings()
    if settings.ai_provider != "anthropic":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "live_analysis_not_enabled", "message": "Live drafting is not enabled."},
        )

    analysis = request.analysis
    current_fingerprint = case_fingerprint(request.case)
    if analysis.provider != "anthropic" or analysis.simulated:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "live_analysis_required", "message": "Drafting requires a successful live analysis."},
        )
    if not request.reviewed_findings:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "review_confirmation_required", "message": "Confirm that you reviewed the findings against your documents before drafting."},
        )
    if analysis.case_id != request.case.case_id or analysis.case_fingerprint != current_fingerprint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "stale_analysis", "message": "The analysis does not match the current document version."},
        )
    try:
        validate_analysis_references(request.case, analysis)
    except InvalidSourceReference:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_analysis_citation", "message": "The supplied analysis contains an invalid source reference."},
        ) from None

    if analysis.assessment.value == "potentially_supported":
        expected_type = DraftType.RECONSIDERATION_REQUEST
    elif analysis.assessment.value == "insufficient_evidence":
        expected_type = DraftType.CLARIFICATION_REQUEST
    else:
        if not request.goodwill_requested:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "goodwill_choice_required", "message": "Choose the explicitly labeled goodwill request option before drafting."},
            )
        expected_type = DraftType.GOODWILL_REQUEST

    provider = AnthropicAnalysisProvider(settings)
    try:
        content = await provider.generate_draft(
            request.case,
            analysis,
            name=request.name,
            desired_outcome=request.desired_outcome,
            draft_type=expected_type,
        )
        usage = provider.last_usage
        if usage is None:
            raise AnalysisProviderError("Draft usage was unavailable.", code="usage_unavailable")
        draft = DraftResponse(
            case_id=request.case.case_id,
            case_fingerprint=current_fingerprint,
            **content.model_dump(),
            provider="anthropic",
            simulated=False,
            model=settings.anthropic_model,
            usage=UsageMetadata(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                estimated_cost_usd=usage.estimated_cost_usd,
                status=usage.status,
            ),
        )
        validate_draft_references(request.case, draft)
        return draft
    except AnalysisProviderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from None
    except InvalidSourceReference:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "invalid_draft_citation", "message": "The draft contained an invalid source reference."},
        ) from None
@router.post(
    "/documents/extract",
    response_model=DocumentExtractionResponse,
    tags=["documents"],
    summary="Extract source passages from a local PDF or UTF-8 text upload",
    description=(
        "Extraction is local and temporary. It does not automatically send the "
        "uploaded document to /analysis; simulated analysis remains limited to "
        "the unchanged authored sample cases."
    ),
)
async def extract_uploaded_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    title: str | None = Form(default=None),
) -> DocumentExtractionResponse:
    filename = file.filename
    try:
        data = await read_upload_limited(file)
        return extract_document(data, filename, document_type, title)
    except ExtractionProblem as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from None
