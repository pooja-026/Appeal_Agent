"""Source documents for clearly fictional sample cases.

These are authored examples, not real customer cases.
"""

from datetime import datetime, timezone

from ..models import Case, Document, DocumentType, Passage


def _case_a() -> Case:
    return Case(
        case_id="case-a-damaged-sale",
        title="Damaged sale item with timely report",
        created_at=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
        documents=[
            Document(
                document_id="a-denial",
                document_type=DocumentType.DENIAL,
                title="Fictional retailer denial email",
                passages=[Passage(
                    passage_id="a-denial-p1",
                    text="BrightCart denied order BC-1042 because the ceramic lamp was purchased during a sale. The message says sale items are not eligible for refunds.",
                )],
            ),
            Document(
                document_id="a-policy",
                document_type=DocumentType.POLICY,
                title="BrightCart fictional refund policy",
                passages=[
                    Passage(
                        passage_id="a-policy-p1",
                        text="BrightCart accepts claims for items damaged in transit within 30 calendar days of delivery, including items purchased at a sale price.",
                    ),
                    Passage(
                        passage_id="a-policy-p2",
                        text="A customer should contact support with a description of the damage and photographs of the item and packaging.",
                    ),
                ],
            ),
            Document(
                document_id="a-receipt",
                document_type=DocumentType.RECEIPT,
                title="Fictional BrightCart receipt",
                passages=[Passage(
                    passage_id="a-receipt-p1",
                    text="Order BC-1042 was placed by Maya Chen for one ceramic lamp at the sale price of 48 dollars. Delivery was recorded on September 1, 2026.",
                )],
            ),
            Document(
                document_id="a-correspondence",
                document_type=DocumentType.CORRESPONDENCE,
                title="Fictional support correspondence",
                passages=[Passage(
                    passage_id="a-correspondence-p1",
                    text="Maya Chen reported on September 5, 2026 that the lamp arrived with a cracked base and attached photographs of the lamp and shipping box.",
                )],
            ),
        ],
    )


def _case_b() -> Case:
    return Case(
        case_id="case-b-missing-dates",
        title="Damaged item with missing delivery and report dates",
        created_at=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
        documents=[
            Document(
                document_id="b-denial",
                document_type=DocumentType.DENIAL,
                title="Fictional retailer denial email",
                passages=[Passage(
                    passage_id="b-denial-p1",
                    text="Northstar Home denied order NH-7781 because the customer did not provide information showing when the damage was reported.",
                )],
            ),
            Document(
                document_id="b-policy",
                document_type=DocumentType.POLICY,
                title="Northstar Home fictional damage policy",
                passages=[Passage(
                    passage_id="b-policy-p1",
                    text="Damage must be reported within 14 calendar days after delivery. The customer must provide the order number and a description of the damage.",
                )],
            ),
            Document(
                document_id="b-receipt",
                document_type=DocumentType.RECEIPT,
                title="Fictional Northstar Home receipt",
                passages=[Passage(
                    passage_id="b-receipt-p1",
                    text="Order NH-7781 was placed by Jordan Ellis for a walnut desk. The receipt does not show a delivery date.",
                )],
            ),
            Document(
                document_id="b-correspondence",
                document_type=DocumentType.CORRESPONDENCE,
                title="Fictional support correspondence",
                passages=[Passage(
                    passage_id="b-correspondence-p1",
                    text="Jordan Ellis wrote that the desk arrived damaged and asked Northstar Home for help. The message has no sent date.",
                )],
            ),
        ],
    )


def _case_c() -> Case:
    return Case(
        case_id="case-c-final-sale-change-mind",
        title="Final-sale change-of-mind request",
        created_at=datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc),
        documents=[
            Document(
                document_id="c-denial",
                document_type=DocumentType.DENIAL,
                title="Fictional retailer denial email",
                passages=[Passage(
                    passage_id="c-denial-p1",
                    text="Willow & Pine denied order WP-3309 because the customer requested a refund after changing their mind about a final-sale item.",
                )],
            ),
            Document(
                document_id="c-policy",
                document_type=DocumentType.POLICY,
                title="Willow & Pine fictional final-sale policy",
                passages=[Passage(
                    passage_id="c-policy-p1",
                    text="Final-sale merchandise is not eligible for return or refund when the customer changes their mind.",
                )],
            ),
            Document(
                document_id="c-receipt",
                document_type=DocumentType.RECEIPT,
                title="Fictional Willow & Pine receipt",
                passages=[Passage(
                    passage_id="c-receipt-p1",
                    text="Order WP-3309 was placed by Priya Shah for a final-sale wool blanket.",
                )],
            ),
            Document(
                document_id="c-correspondence",
                document_type=DocumentType.CORRESPONDENCE,
                title="Fictional support correspondence",
                passages=[Passage(
                    passage_id="c-correspondence-p1",
                    text="Priya Shah wrote that the blanket was unused but that she had changed her mind and wanted a refund.",
                )],
            ),
        ],
    )


SAMPLE_CASES: dict[str, Case] = {
    case.case_id: case for case in (_case_a(), _case_b(), _case_c())
}
