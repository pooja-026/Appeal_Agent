"""Expected deterministic analyses kept separate from source documents."""

from ..models import (
    Analysis,
    Assessment,
    DocumentedDeadline,
    Finding,
    FindingClassification,
    MissingEvidence,
    PolicyClause,
    SourceReference,
)
from .source_documents import SAMPLE_CASES


def _source(document_id: str, passage_id: str, quoted_text: str) -> SourceReference:
    return SourceReference(
        document_id=document_id,
        passage_id=passage_id,
        quoted_text=quoted_text,
    )


EXPECTED_ANALYSES: dict[str, Analysis] = {
    "case-a-damaged-sale": Analysis(
        case_id="case-a-damaged-sale",
        findings=[
            Finding(
                classification=FindingClassification.DOCUMENTED_FACT,
                statement="The denial says the item was refused because it was purchased during a sale.",
                sources=[_source("a-denial", "a-denial-p1", "purchased during a sale")],
            ),
            Finding(
                classification=FindingClassification.DOCUMENTED_FACT,
                statement="The policy expressly includes sale-price purchases in damaged-in-transit claims.",
                sources=[_source("a-policy", "a-policy-p1", "including items purchased at a sale price")],
            ),
            Finding(
                classification=FindingClassification.DOCUMENTED_FACT,
                statement="The correspondence reports the damage on September 5, 2026 and says photographs were attached.",
                sources=[_source("a-correspondence", "a-correspondence-p1", "reported on September 5, 2026")],
            ),
            Finding(
                classification=FindingClassification.INTERPRETATION,
                statement="The supplied documents potentially support asking BrightCart to reconsider because the stated sale-item reason conflicts with the supplied damaged-item policy clause.",
                sources=[
                    _source("a-denial", "a-denial-p1", "sale items are not eligible for refunds"),
                    _source("a-policy", "a-policy-p1", "including items purchased at a sale price"),
                ],
            ),
        ],
        supporting_policy_clauses=[PolicyClause(
            statement="The damaged-in-transit rule includes items purchased at a sale price.",
            source=_source("a-policy", "a-policy-p1", "including items purchased at a sale price"),
        )],
        conflicting_policy_clauses=[],
        missing_evidence=[],
        follow_up_questions=[],
        assessment=Assessment.POTENTIALLY_SUPPORTED,
        explanation="The supplied policy and correspondence support a potentially supported request, but a reviewer should confirm the photographs and delivery record before responding.",
        documented_deadline=DocumentedDeadline(
            description="Damage claims must be made within 30 calendar days of delivery.",
            source=_source("a-policy", "a-policy-p1", "within 30 calendar days of delivery"),
        ),
        provider="mock",
        simulated=True,
    ),
    "case-b-missing-dates": Analysis(
        case_id="case-b-missing-dates",
        findings=[
            Finding(
                classification=FindingClassification.DOCUMENTED_FACT,
                statement="The policy requires reporting damage within 14 calendar days after delivery.",
                sources=[_source("b-policy", "b-policy-p1", "within 14 calendar days after delivery")],
            ),
            Finding(
                classification=FindingClassification.DOCUMENTED_FACT,
                statement="The supplied receipt does not show a delivery date.",
                sources=[_source("b-receipt", "b-receipt-p1", "does not show a delivery date")],
            ),
            Finding(
                classification=FindingClassification.DOCUMENTED_FACT,
                statement="The supplied correspondence has no sent date.",
                sources=[_source("b-correspondence", "b-correspondence-p1", "has no sent date")],
            ),
            Finding(
                classification=FindingClassification.INTERPRETATION,
                statement="Eligibility cannot be assessed because the delivery date and report date are unknown.",
                sources=[
                    _source("b-policy", "b-policy-p1", "within 14 calendar days after delivery"),
                    _source("b-receipt", "b-receipt-p1", "does not show a delivery date"),
                ],
            ),
        ],
        supporting_policy_clauses=[],
        conflicting_policy_clauses=[],
        missing_evidence=[
            MissingEvidence(
                item="Delivery date",
                why_needed="It is the starting point for the policy's 14-day reporting period.",
            ),
            MissingEvidence(
                item="Damage-report date",
                why_needed="It is needed to compare the report timing with the policy period.",
            ),
        ],
        follow_up_questions=[
            "What date was the desk delivered, and what document or tracking record shows that date?",
            "What date did you first report the damage to Northstar Home, and can you provide the sent message or ticket record?",
        ],
        assessment=Assessment.INSUFFICIENT_EVIDENCE,
        explanation="The policy provides a reporting period, but the supplied documents do not establish either date needed to apply it. Do not assume that the request was timely.",
        documented_deadline=None,
        provider="mock",
        simulated=True,
    ),
    "case-c-final-sale-change-mind": Analysis(
        case_id="case-c-final-sale-change-mind",
        findings=[
            Finding(
                classification=FindingClassification.DOCUMENTED_FACT,
                statement="The correspondence says the customer changed their mind and wanted a refund for an unused item.",
                sources=[_source("c-correspondence", "c-correspondence-p1", "changed her mind and wanted a refund")],
            ),
            Finding(
                classification=FindingClassification.DOCUMENTED_FACT,
                statement="The receipt identifies the item as final-sale merchandise.",
                sources=[_source("c-receipt", "c-receipt-p1", "final-sale wool blanket")],
            ),
            Finding(
                classification=FindingClassification.INTERPRETATION,
                statement="The supplied documents do not provide a supported basis for a change-of-mind refund under the supplied policy.",
                sources=[_source("c-policy", "c-policy-p1", "not eligible for return or refund when the customer changes their mind")],
            ),
        ],
        supporting_policy_clauses=[],
        conflicting_policy_clauses=[PolicyClause(
            statement="The supplied policy excludes refunds for final-sale merchandise when the customer changes their mind.",
            source=_source("c-policy", "c-policy-p1", "Final-sale merchandise is not eligible for return or refund when the customer changes their mind."),
        )],
        missing_evidence=[],
        follow_up_questions=[],
        assessment=Assessment.NO_SUPPORTED_BASIS,
        explanation="The supplied policy directly excludes the documented change-of-mind request for this final-sale item. No exception is stated in the supplied documents.",
        documented_deadline=None,
        provider="mock",
        simulated=True,
    ),
}

assert set(SAMPLE_CASES) == set(EXPECTED_ANALYSES)
