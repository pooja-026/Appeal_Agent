"""HTTP routes for sample cases and deterministic local analysis."""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from .config import get_settings
from .fixtures.expected_findings import EXPECTED_ANALYSES
from .fixtures.source_documents import SAMPLE_CASES
from .ingestion import extract_document, read_upload_limited
from .models import (
    Analysis,
    Case,
    DocumentExtractionResponse,
    DocumentType,
    SampleCaseSummary,
)
from .providers import MockAnalysisProvider, MockAnalysisUnavailable
from .references import InvalidSourceReference
from .ingestion import ExtractionProblem

router = APIRouter()

_SAMPLE_DESCRIPTIONS = {
    "case-a-damaged-sale": "A damaged sale item with timely reporting and supporting correspondence.",
    "case-b-missing-dates": "A damaged item whose delivery and reporting dates are missing.",
    "case-c-final-sale-change-mind": "A final-sale change-of-mind request covered by an explicit exclusion.",
}


def _provider() -> MockAnalysisProvider:
    settings = get_settings()
    if settings.ai_provider != "mock":
        raise RuntimeError(f"Unsupported AI provider: {settings.ai_provider}")
    return MockAnalysisProvider(SAMPLE_CASES, EXPECTED_ANALYSES)


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
        return _provider().analyze(case)
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
