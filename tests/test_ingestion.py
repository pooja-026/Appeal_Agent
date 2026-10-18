from datetime import datetime, timezone
from io import BytesIO
import asyncio

import pytest
from starlette.datastructures import UploadFile
from pypdf import PdfWriter

from appeal_agent.ingestion import (
    ExtractionLimits,
    ExtractionProblem,
    extract_document,
    read_upload_limited,
)
from appeal_agent.models import Case, DocumentType, SourceReference
from appeal_agent.references import validate_source_reference


def _pdf_bytes(pages: list[list[str]]) -> bytes:
    """Build a tiny text PDF without adding a PDF-generation dependency."""

    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    kids: list[str] = []
    for index, lines in enumerate(pages):
        page_number = 4 + index * 2
        content_number = page_number + 1
        kids.append(f"{page_number} 0 R")
        commands = ["BT", "/F1 14 Tf", "72 720 Td"]
        for line_index, line in enumerate(lines):
            if line_index:
                commands.append("0 -24 Td")
            commands.append(f"({escape(line)}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("ascii")
        objects[page_number] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_number} 0 R >>"
        ).encode("ascii")
        objects[content_number] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
    objects[2] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode(
        "ascii"
    )

    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(pdf)
        pdf += f"{number} 0 obj\n".encode("ascii") + objects[number] + b"\nendobj\n"
    xref = len(pdf)
    size = max(objects) + 1
    pdf += f"xref\n0 {size}\n0000000000 65535 f \n".encode("ascii")
    for number in range(1, size):
        pdf += f"{offsets[number]:010d} 00000 n \n".encode("ascii")
    pdf += (
        f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return pdf


def _password_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("fictional-password")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_utf8_text_extraction_has_null_page_numbers() -> None:
    result = extract_document(
        "FICTIONAL\nCafé item arrived damaged.".encode("utf-8"),
        "fictional.txt",
        DocumentType.CORRESPONDENCE,
    )

    assert result.metadata.format == "txt"
    assert result.metadata.page_count == 1
    assert all(passage.page_number is None for passage in result.document.passages)
    assert "Café" in result.document.passages[0].text


def test_two_page_pdf_keeps_pages_separate_and_ids_stable() -> None:
    data = _pdf_bytes([["FICTIONAL PAGE ONE", "Order HF-2048"], ["FICTIONAL PAGE TWO"]])

    first = extract_document(data, "fictional.pdf", DocumentType.RECEIPT)
    second = extract_document(data, "fictional.pdf", DocumentType.RECEIPT)

    assert first.metadata.page_count == 2
    assert [p.page_number for p in first.document.passages] == [1, 2]
    assert [p.passage_id for p in first.document.passages] == [
        p.passage_id for p in second.document.passages
    ]
    assert len(first.document.passages) == 2


def test_partial_pdf_text_returns_page_warning() -> None:
    result = extract_document(
        _pdf_bytes([["FICTIONAL TEXT"], []]),
        "partial.pdf",
        DocumentType.OTHER,
    )

    assert result.metadata.page_count == 2
    assert result.warnings == [
        "PDF page 2 contains no extractable text; it may be blank or image-based."
    ]


def test_empty_unsupported_corrupt_and_invalid_utf8_inputs_fail() -> None:
    cases = [
        (b"", "empty.txt", "empty_upload"),
        (b"not a pdf", "document.pdf", "invalid_pdf"),
        (b"not utf8 \xff", "document.txt", "invalid_utf8"),
    ]
    for data, filename, code in cases:
        with pytest.raises(ExtractionProblem) as error:
            extract_document(data, filename, DocumentType.OTHER)
        assert error.value.code == code

    with pytest.raises(ExtractionProblem) as error:
        extract_document(b"content", "document.docx", DocumentType.OTHER)
    assert error.value.code == "unsupported_file_type"


def test_password_protected_and_no_text_pdfs_fail_without_ocr_claims() -> None:
    with pytest.raises(ExtractionProblem, match="Password-protected"):
        extract_document(_password_pdf(), "locked.pdf", DocumentType.OTHER)

    with pytest.raises(ExtractionProblem, match="OCR is not supported"):
        extract_document(_pdf_bytes([[]]), "scanned.pdf", DocumentType.OTHER)


def test_limits_reject_without_silent_truncation() -> None:
    with pytest.raises(ExtractionProblem) as page_error:
        extract_document(
            _pdf_bytes([["PAGE ONE"], ["PAGE TWO"]]),
            "too-many-pages.pdf",
            DocumentType.OTHER,
            limits=ExtractionLimits(max_pdf_pages=1),
        )
    assert page_error.value.code == "pdf_page_limit_exceeded"

    with pytest.raises(ExtractionProblem) as text_error:
        extract_document(
            b"ABCDEFGHIJ",
            "too-long.txt",
            DocumentType.OTHER,
            limits=ExtractionLimits(max_extracted_characters=5),
        )
    assert text_error.value.code == "extracted_text_limit_exceeded"

    with pytest.raises(ExtractionProblem) as upload_error:
        extract_document(
            b"123456",
            "too-large.txt",
            DocumentType.OTHER,
            limits=ExtractionLimits(max_upload_bytes=5),
        )
    assert upload_error.value.code == "upload_size_limit_exceeded"


def test_upload_reader_enforces_limit_while_reading_and_closes_upload() -> None:
    upload = UploadFile(filename="fictional.txt", file=BytesIO(b"123456"))

    with pytest.raises(ExtractionProblem) as error:
        asyncio.run(read_upload_limited(upload, max_upload_bytes=5))

    assert error.value.code == "upload_size_limit_exceeded"
    assert upload.file.closed is True


def test_extracted_passages_work_with_existing_reference_validation() -> None:
    result = extract_document(b"FICTIONAL receipt passage", "receipt.txt", DocumentType.RECEIPT)
    case = Case(
        case_id="fictional-extracted-case",
        title="Fictional extracted case",
        created_at=datetime.now(timezone.utc),
        documents=[result.document],
    )

    validate_source_reference(
        case,
        SourceReference(
            document_id=result.document.document_id,
            passage_id=result.document.passages[0].passage_id,
            quoted_text="FICTIONAL receipt passage",
        ),
    )
