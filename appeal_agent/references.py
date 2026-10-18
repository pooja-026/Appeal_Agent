"""Source-reference validation for evidence-grounded analyses."""

import re

from .models import Analysis, Case, SourceReference


class InvalidSourceReference(ValueError):
    """Raised when an analysis cites a missing source or fabricated quotation."""


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


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
