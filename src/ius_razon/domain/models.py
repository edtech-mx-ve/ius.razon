from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ius_razon.domain.enums import (
    CaseStatus,
    ConfidentialityLevel,
    EvidenceEvaluationStatus,
    EvidenceType,
    FactStatus,
    JurisprudenceAuthority,
    LegalIssueStatus,
    LegalSourceType,
    NormHierarchy,
    PartyRole,
    PartyType,
    SourceOrientation,
)

NonEmptyShort = Annotated[str, Field(min_length=1, max_length=300)]


def utc_now() -> datetime:
    """Devuelve la fecha y hora actual en UTC."""

    return datetime.now(UTC)


class DomainModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class CaseCreate(DomainModel):
    title: Annotated[str, Field(min_length=3, max_length=160)]
    description: Annotated[str, Field(min_length=10, max_length=4000)]
    matter: Annotated[str, Field(min_length=3, max_length=120)]
    jurisdiction: Annotated[str, Field(min_length=2, max_length=250)]
    location: str | None = Field(default=None, max_length=250)
    opened_on: date = Field(default_factory=date.today)
    status: CaseStatus = CaseStatus.OPEN
    objective: str | None = Field(default=None, max_length=1000)
    user_role: str | None = Field(default=None, max_length=120)
    confidentiality: ConfidentialityLevel = ConfidentialityLevel.INTERNAL


class CaseRecord(CaseCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class PartyCreate(DomainModel):
    case_id: NonEmptyShort
    name_alias: Annotated[str, Field(min_length=2, max_length=200)]
    party_type: PartyType
    legal_role: PartyRole
    representation: str | None = Field(default=None, max_length=300)
    claim: str | None = Field(default=None, max_length=1500)
    position: str | None = Field(default=None, max_length=1500)


class PartyRecord(PartyCreate):
    id: str
    created_at: datetime


class FactCreate(DomainModel):
    case_id: NonEmptyShort
    description: Annotated[str, Field(min_length=5, max_length=3000)]
    event_date: date | None = None
    actor_party_id: str | None = None
    action: str | None = Field(default=None, max_length=250)
    object_text: str | None = Field(default=None, max_length=250)
    place: str | None = Field(default=None, max_length=250)
    source: str | None = Field(default=None, max_length=500)
    status: FactStatus = FactStatus.ALLEGED
    controversy_level: int = Field(default=2, ge=0, le=5)


class FactRecord(FactCreate):
    id: str
    code: str
    created_at: datetime


class EvidenceCreate(DomainModel):
    case_id: NonEmptyShort
    evidence_type: EvidenceType
    description: Annotated[str, Field(min_length=5, max_length=3000)]
    origin: str | None = Field(default=None, max_length=500)
    evidence_date: date | None = None
    integrity_statement: str | None = Field(default=None, max_length=1000)
    offering_party_id: str | None = None
    objections: str | None = Field(default=None, max_length=1500)
    observations: str | None = Field(default=None, max_length=1500)
    evaluation_status: EvidenceEvaluationStatus = EvidenceEvaluationStatus.PENDING


class EvidenceRecord(EvidenceCreate):
    id: str
    code: str
    original_file_name: str | None = None
    stored_file_name: str | None = None
    file_sha256: str | None = None
    file_size: int | None = None
    created_at: datetime


class FactEvidenceLink(DomainModel):
    fact_id: str
    evidence_id: str
    purpose: str | None = Field(default=None, max_length=800)


class FactEvidenceLinkView(FactEvidenceLink):
    fact_code: str
    evidence_code: str


class LegalIssueCreate(DomainModel):
    case_id: NonEmptyShort
    title: Annotated[str, Field(min_length=3, max_length=240)]
    question: Annotated[str, Field(min_length=8, max_length=1500)]
    description: str | None = Field(default=None, max_length=3000)
    status: LegalIssueStatus = LegalIssueStatus.OPEN


class LegalIssueRecord(LegalIssueCreate):
    id: str
    code: str
    created_at: datetime
    updated_at: datetime


class SourceFileMetadata(DomainModel):
    original_file_name: str | None = None
    stored_file_name: str | None = None
    file_sha256: str | None = None
    file_size: int | None = None


class NormCreate(DomainModel):
    case_id: NonEmptyShort
    jurisdiction: Annotated[str, Field(min_length=2, max_length=250)]
    matter: Annotated[str, Field(min_length=2, max_length=120)]
    instrument: Annotated[str, Field(min_length=3, max_length=300)]
    article: Annotated[str, Field(min_length=1, max_length=120)]
    text: Annotated[str, Field(min_length=5, max_length=20000)]
    hierarchy: NormHierarchy = NormHierarchy.OTHER
    publication_date: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    version_label: str | None = Field(default=None, max_length=200)
    source_reference: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def validate_validity_period(self) -> NormCreate:
        """Impide intervalos normativos invertidos."""

        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("La fecha final de vigencia no puede ser anterior a la inicial.")
        return self


class NormRecord(NormCreate, SourceFileMetadata):
    id: str
    code: str
    created_at: datetime


class JurisprudenceCreate(DomainModel):
    case_id: NonEmptyShort
    court: Annotated[str, Field(min_length=2, max_length=400)]
    identifier: Annotated[str, Field(min_length=2, max_length=240)]
    jurisdiction: Annotated[str, Field(min_length=2, max_length=250)]
    matter: Annotated[str, Field(min_length=2, max_length=120)]
    decision_date: date | None = None
    relevant_facts: Annotated[str, Field(min_length=5, max_length=8000)]
    legal_question: Annotated[str, Field(min_length=5, max_length=3000)]
    criterion: Annotated[str, Field(min_length=5, max_length=12000)]
    decision: str | None = Field(default=None, max_length=5000)
    interpreted_norms: str | None = Field(default=None, max_length=3000)
    authority: JurisprudenceAuthority = JurisprudenceAuthority.PENDING_VERIFICATION
    source_reference: str | None = Field(default=None, max_length=1000)
    similarities: str | None = Field(default=None, max_length=4000)
    differences: str | None = Field(default=None, max_length=4000)


class JurisprudenceRecord(JurisprudenceCreate, SourceFileMetadata):
    id: str
    code: str
    created_at: datetime


class DoctrineCreate(DomainModel):
    case_id: NonEmptyShort
    author: Annotated[str, Field(min_length=2, max_length=300)]
    work_title: Annotated[str, Field(min_length=2, max_length=500)]
    edition: str | None = Field(default=None, max_length=120)
    publication_year: int | None = Field(default=None, ge=1000, le=2100)
    concept: Annotated[str, Field(min_length=2, max_length=300)]
    position_summary: Annotated[str, Field(min_length=5, max_length=10000)]
    excerpt: str | None = Field(default=None, max_length=5000)
    citation: Annotated[str, Field(min_length=5, max_length=1500)]
    argumentative_function: str | None = Field(default=None, max_length=2000)
    source_reference: str | None = Field(default=None, max_length=1000)


class DoctrineRecord(DoctrineCreate, SourceFileMetadata):
    id: str
    code: str
    created_at: datetime


class IssueSourceLinkCreate(DomainModel):
    case_id: NonEmptyShort
    issue_id: NonEmptyShort
    source_type: LegalSourceType
    source_id: NonEmptyShort
    orientation: SourceOrientation = SourceOrientation.NEUTRAL
    applicability: Annotated[str, Field(min_length=5, max_length=3000)]
    notes: str | None = Field(default=None, max_length=2000)


class IssueSourceLinkView(IssueSourceLinkCreate):
    issue_code: str
    issue_title: str
    source_code: str
    source_title: str


class AuditEventRecord(DomainModel):
    id: str
    case_id: str | None
    event_type: str
    entity_type: str
    entity_id: str | None
    detail_json: str
    created_at: datetime


class CaseSummary(DomainModel):
    case: CaseRecord
    party_count: int
    fact_count: int
    evidence_count: int
    link_count: int
    legal_issue_count: int
    norm_count: int
    jurisprudence_count: int
    doctrine_count: int
    issue_source_link_count: int
