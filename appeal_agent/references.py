"""Source-reference validation for evidence-grounded analyses."""

import hashlib
import json
import re

from .models import Analysis, Case, DraftResponse, SourceReference


class InvalidSourceReference(ValueError):
    """Raised when an analysis cites a missing source or fabricated quotation."""


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def case_fingerprint(case: Case) -> str:
    """Return a stable digest for this exact structured document version."""

    canonical = json.dumps(
        case.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_source_reference(case: Case, reference: SourceReference) -> None:
    documents = {document.document_id: document for document in case.documents}
    document = documents.get(reference.document_id)
    if document is None:
        raise InvalidSourceReference(
            f"Referenced document {reference.document_id!r} does not exist"
        )

    passages = {passage.passage_id: passage for passage in document.passages}
    passage = passages.get(reference.passage_id)
    if passage is None:
        raise InvalidSourceReference(
            f"Referenced passage {reference.passage_id!r} does not exist in "
            f"document {reference.document_id!r}"
        )

    quoted = _normalize_whitespace(reference.quoted_text)
    passage_text = _normalize_whitespace(passage.text)
    if quoted not in passage_text:
        raise InvalidSourceReference(
            f"Quoted text is not present in passage {reference.passage_id!r}"
        )


def validate_analysis_references(case: Case, analysis: Analysis) -> Analysis:
    """Validate every citation, including clauses and documented deadlines.

    These checks establish only that a source and quotation exist in the
    submitted case; they do not prove that an interpretation is correct.
    """

    if analysis.case_id != case.case_id:
        raise InvalidSourceReference(
            f"Analysis case ID {analysis.case_id!r} does not match {case.case_id!r}"
        )

    for finding in analysis.findings:
        for source in finding.sources:
            validate_source_reference(case, source)
    for clause in [
        *analysis.supporting_policy_clauses,
        *analysis.conflicting_policy_clauses,
    ]:
        validate_source_reference(case, clause.source)
    if analysis.documented_deadline is not None:
        validate_source_reference(case, analysis.documented_deadline.source)
    return analysis


def validate_draft_references(case: Case, draft: DraftResponse) -> DraftResponse:
    """Validate every source attached to a generated draft paragraph."""

    if draft.case_id != case.case_id:
        raise InvalidSourceReference(
            f"Draft case ID {draft.case_id!r} does not match {case.case_id!r}"
        )
    for paragraph in draft.paragraphs:
        for source in paragraph.sources:
            validate_source_reference(case, source)
    if draft.recipient_source is not None:
        validate_source_reference(case, draft.recipient_source)
    return draft
