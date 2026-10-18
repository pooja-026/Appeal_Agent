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


class SampleCaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    description: str
