"""Validated domain schemas for retailer refund denial analysis."""

from datetime import date as date_type
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DocumentType(StrEnum):
    DENIAL = "denial"
    POLICY = "policy"
    RECEIPT = "receipt"
    CORRESPONDENCE = "correspondence"
    OTHER = "other"


class FindingClassification(StrEnum):
    DOCUMENTED_FACT = "documented_fact"
    INTERPRETATION = "interpretation"


class Assessment(StrEnum):
    POTENTIALLY_SUPPORTED = "potentially_supported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NO_SUPPORTED_BASIS = "no_supported_basis"


class Passage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passage_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    document_type: DocumentType
    title: str = Field(min_length=1)
    passages: list[Passage] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_passage_ids(self) -> "Document":
        ids = [passage.passage_id for passage in self.passages]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Document {self.document_id!r} has duplicate passage IDs")
        return self


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    created_at: datetime
    documents: list[Document] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_document_and_passage_ids(self) -> "Case":
        document_ids = [document.document_id for document in self.documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError(f"Case {self.case_id!r} has duplicate document IDs")

        passage_ids = [
            passage.passage_id
            for document in self.documents
            for passage in document.passages
        ]
        if len(passage_ids) != len(set(passage_ids)):
            raise ValueError(f"Case {self.case_id!r} has duplicate passage IDs")
        return self


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    passage_id: str = Field(min_length=1)
    quoted_text: str = Field(min_length=1)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification: FindingClassification
    statement: str = Field(min_length=1)
    sources: list[SourceReference] = Field(min_length=1)


class PolicyClause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1)
    source: SourceReference


class MissingEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: str = Field(min_length=1)
    why_needed: str = Field(min_length=1)


class DocumentedDeadline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    source: SourceReference
    date: date_type | None = None


class ExtractionFormat(StrEnum):
    PDF = "pdf"
    TEXT = "txt"


class ExtractionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: ExtractionFormat
    page_count: int = Field(ge=1)
    character_count: int = Field(ge=1)
    passage_count: int = Field(ge=1)


class DocumentExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: Document
    metadata: ExtractionMetadata
    warnings: list[str]


class Analysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    findings: list[Finding]
    supporting_policy_clauses: list[PolicyClause]
    conflicting_policy_clauses: list[PolicyClause]
    missing_evidence: list[MissingEvidence]
    follow_up_questions: list[str]
    assessment: Assessment
    explanation: str = Field(min_length=1)
    documented_deadline: DocumentedDeadline | None = None
    provider: str = Field(min_length=1)
    simulated: bool
    model: str | None = None
    case_fingerprint: str | None = None


class AnalysisContent(BaseModel):
    """Model-generated fields, excluding application-owned metadata."""

    model_config = ConfigDict(extra="forbid")

    findings: list[Finding]
    supporting_policy_clauses: list[PolicyClause]
    conflicting_policy_clauses: list[PolicyClause]
    missing_evidence: list[MissingEvidence]
    follow_up_questions: list[str]
    assessment: Assessment
    explanation: str = Field(min_length=1)
    documented_deadline: DocumentedDeadline | None = None


class DesiredOutcome(StrEnum):
    REFUND = "refund"
    REPLACEMENT = "replacement"
    EITHER = "either"


class DraftType(StrEnum):
    RECONSIDERATION_REQUEST = "reconsideration_request"
    CLARIFICATION_REQUEST = "clarification_request"
    GOODWILL_REQUEST = "goodwill_request"


class UsageMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    status: str = Field(min_length=1)


class DraftParagraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    sources: list[SourceReference]


class EvidenceChecklistItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: str = Field(min_length=1)
    why_consider: str = Field(min_length=1)


class DraftContent(BaseModel):
    """Model-generated draft fields, excluding application-owned metadata."""

    model_config = ConfigDict(extra="forbid")

    draft_type: DraftType
    subject: str = Field(min_length=1)
    recipient_name: str | None = Field(default=None, max_length=200)
    recipient_source: SourceReference | None = None
    paragraphs: list[DraftParagraph] = Field(min_length=1)
    evidence_checklist: list[EvidenceChecklistItem]
    confirmation_items: list[str]

    @model_validator(mode="after")
    def recipient_must_have_source(self) -> "DraftContent":
        if (self.recipient_name is None) != (self.recipient_source is None):
            raise ValueError("recipient_name and recipient_source must be provided together")
        return self


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case: Case
    analysis: Analysis
    name: str | None = Field(default=None, max_length=120)
    desired_outcome: DesiredOutcome
    reviewed_findings: bool
    goodwill_requested: bool = False


class DraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    case_fingerprint: str = Field(min_length=64, max_length=64)
    draft_type: DraftType
    subject: str = Field(min_length=1)
    recipient_name: str | None = Field(default=None, max_length=200)
    recipient_source: SourceReference | None = None
    paragraphs: list[DraftParagraph] = Field(min_length=1)
    evidence_checklist: list[EvidenceChecklistItem]
    confirmation_items: list[str]
    provider: str = Field(min_length=1)
    simulated: bool
    model: str | None = None
    usage: UsageMetadata


class SampleCaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    description: str
