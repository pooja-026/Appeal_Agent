"""Bounded local extraction of text files and text-based PDFs."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re

from fastapi import UploadFile
from pypdf import PdfReader

from .models import (
    Document,
    DocumentExtractionResponse,
    DocumentType,
    ExtractionFormat,
    ExtractionMetadata,
    Passage,
)


@dataclass(frozen=True)
class ExtractionLimits:
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 30
    max_extracted_characters: int = 100_000
    max_passage_characters: int = 1_600


DEFAULT_LIMITS = ExtractionLimits()
UPLOAD_CHUNK_SIZE = 64 * 1024


class ExtractionProblem(ValueError):
    """A sanitized, client-facing extraction failure."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _filename_extension(filename: str | None) -> str:
    if not filename:
        return ""
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    return Path(name).suffix.lower()


def _default_title(filename: str | None) -> str:
    if not filename:
        return "Uploaded document"
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    title = Path(name).stem.strip()
    return title or "Uploaded document"


def _normalize_extracted_text(text: str) -> str:
    """Normalize line endings and trailing line whitespace only.

    Internal wording, punctuation, paragraph breaks, and repeated spaces are
    otherwise preserved. Citation validation may separately collapse
    whitespace when comparing a quotation with a source passage.
    """

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def _split_long_paragraph(text: str, limit: int) -> list[str]:
    pieces: list[str] = []
    remaining = text.strip()
    while len(remaining) > limit:
        split_at = remaining.rfind(" ", 0, limit + 1)
        if split_at <= 0:
            split_at = limit
        pieces.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        pieces.append(remaining)
    return pieces


def _split_passages(text: str, page_number: int | None, limit: int) -> list[Passage]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        chunks.extend(_split_long_paragraph(paragraph, limit))

    passages: list[Passage] = []
    for index, chunk in enumerate(chunks, start=1):
        identity = f"{page_number or 'text'}:{index}:{chunk}".encode("utf-8")
        stable_suffix = sha256(identity).hexdigest()[:12]
        passages.append(
            Passage(
                passage_id=f"p-{page_number or 'text'}-{index:04d}-{stable_suffix}",
                text=chunk,
                page_number=page_number,
            )
        )
    return passages


def _read_pdf_pages(
    data: bytes, limits: ExtractionLimits
) -> tuple[list[tuple[int, str]], list[str], int]:
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise ExtractionProblem(
                "password_protected_pdf",
                "Password-protected PDFs are not supported.",
                422,
            )
        page_count = len(reader.pages)
        if page_count > limits.max_pdf_pages:
            raise ExtractionProblem(
                "pdf_page_limit_exceeded",
                f"PDF exceeds the maximum of {limits.max_pdf_pages} pages.",
                413,
            )
    except ExtractionProblem:
        raise
    except Exception as exc:
        raise ExtractionProblem(
            "invalid_pdf",
            "The uploaded file is not a readable PDF.",
            422,
        ) from None

    pages: list[tuple[int, str]] = []
    warnings: list[str] = []
    total_characters = 0
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            page_text = _normalize_extracted_text(page.extract_text() or "")
        except Exception:
            page_text = ""
        if not page_text:
            warnings.append(
                f"PDF page {page_number} contains no extractable text; it may be blank or image-based."
            )
            continue
        total_characters += len(page_text)
        if total_characters > limits.max_extracted_characters:
            raise ExtractionProblem(
                "extracted_text_limit_exceeded",
                f"Extracted text exceeds the maximum of {limits.max_extracted_characters} characters.",
                413,
            )
        pages.append((page_number, page_text))

    if not pages:
        raise ExtractionProblem(
            "pdf_has_no_extractable_text",
            "The PDF contains no usable extractable text. OCR is not supported yet.",
            422,
        )
    return pages, warnings, page_count


def _build_document(
    *,
    data: bytes,
    extension: str,
    document_type: DocumentType,
    title: str | None,
    limits: ExtractionLimits,
) -> DocumentExtractionResponse:
    if not data:
        raise ExtractionProblem("empty_upload", "The uploaded file is empty.", 400)
    if len(data) > limits.max_upload_bytes:
        raise ExtractionProblem(
            "upload_size_limit_exceeded",
            f"Upload exceeds the maximum size of {limits.max_upload_bytes // (1024 * 1024)} MiB.",
            413,
        )

    warnings: list[str] = []
    if extension == ".txt":
        try:
            text = _normalize_extracted_text(data.decode("utf-8"))
        except UnicodeDecodeError:
            raise ExtractionProblem(
                "invalid_utf8",
                "Text files must be valid UTF-8.",
                422,
            ) from None
        if not text:
            raise ExtractionProblem("empty_text", "The text file contains no usable text.", 422)
        if len(text) > limits.max_extracted_characters:
            raise ExtractionProblem(
                "extracted_text_limit_exceeded",
                f"Extracted text exceeds the maximum of {limits.max_extracted_characters} characters.",
                413,
            )
        pages = [(0, text)]
        extraction_format = ExtractionFormat.TEXT
        page_count = 1
    else:
        pages, warnings, page_count = _read_pdf_pages(data, limits)
        extraction_format = ExtractionFormat.PDF

    passages = [
        passage
        for page_number, page_text in pages
        for passage in _split_passages(
            page_text,
            None if extraction_format is ExtractionFormat.TEXT else page_number,
            limits.max_passage_characters,
        )
    ]
    if not passages:
        raise ExtractionProblem("no_passages", "No usable text passages were extracted.", 422)

    document_id = f"doc-{sha256(data).hexdigest()[:16]}"
    document = Document(
        document_id=document_id,
        document_type=document_type,
        title=(title or _default_title(None)).strip() or "Uploaded document",
        passages=passages,
    )
    character_count = sum(len(page_text) for _, page_text in pages)
    return DocumentExtractionResponse(
        document=document,
        metadata=ExtractionMetadata(
            format=extraction_format,
            page_count=page_count,
            character_count=character_count,
            passage_count=len(passages),
        ),
        warnings=warnings,
    )


def extract_document(
    data: bytes,
    filename: str | None,
    document_type: DocumentType,
    title: str | None = None,
    limits: ExtractionLimits = DEFAULT_LIMITS,
) -> DocumentExtractionResponse:
    """Extract a bounded local document without retaining the original upload."""

    extension = _filename_extension(filename)
    if extension not in {".pdf", ".txt"}:
        raise ExtractionProblem(
            "unsupported_file_type",
            "Only .pdf and UTF-8 .txt files are supported.",
            415,
        )
    return _build_document(
        data=data,
        extension=extension,
        document_type=document_type,
        title=title or _default_title(filename),
        limits=limits,
    )


async def read_upload_limited(
    upload: UploadFile,
    max_upload_bytes: int = DEFAULT_LIMITS.max_upload_bytes,
) -> bytes:
    """Read an UploadFile in bounded chunks and close it on every path."""

    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = await upload.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > max_upload_bytes:
                raise ExtractionProblem(
                    "upload_size_limit_exceeded",
                    f"Upload exceeds the maximum size of {max_upload_bytes // (1024 * 1024)} MiB.",
                    413,
                )
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        await upload.close()
