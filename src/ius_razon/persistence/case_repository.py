from __future__ import annotations

from typing import Protocol, runtime_checkable

from ius_razon.domain.enums import LegalSourceType
from ius_razon.domain.models import (
    AuditEventRecord,
    CaseCreate,
    CaseRecord,
    DoctrineCreate,
    DoctrineRecord,
    EvidenceCreate,
    EvidenceRecord,
    FactCreate,
    FactEvidenceLinkView,
    FactRecord,
    IssueSourceLinkCreate,
    IssueSourceLinkView,
    JurisprudenceCreate,
    JurisprudenceRecord,
    LegalIssueCreate,
    LegalIssueRecord,
    NormCreate,
    NormRecord,
    PartyCreate,
    PartyRecord,
)


@runtime_checkable
class CaseRepository(Protocol):
    """Contrato de persistencia requerido por CaseService."""

    def create_case(self, payload: CaseCreate) -> CaseRecord: ...

    def list_cases(self) -> list[CaseRecord]: ...

    def get_case(self, case_id: str) -> CaseRecord: ...

    def update_case(
        self,
        case_id: str,
        payload: CaseCreate,
    ) -> CaseRecord: ...

    def add_party(self, payload: PartyCreate) -> PartyRecord: ...

    def list_parties(self, case_id: str) -> list[PartyRecord]: ...

    def add_fact(self, payload: FactCreate) -> FactRecord: ...

    def list_facts(self, case_id: str) -> list[FactRecord]: ...

    def add_evidence(
        self,
        payload: EvidenceCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> EvidenceRecord: ...

    def list_evidence(self, case_id: str) -> list[EvidenceRecord]: ...

    def link_fact_evidence(
        self,
        *,
        case_id: str,
        fact_id: str,
        evidence_id: str,
        purpose: str | None,
    ) -> None: ...

    def list_fact_evidence_links(
        self,
        case_id: str,
    ) -> list[FactEvidenceLinkView]: ...

    def add_legal_issue(
        self,
        payload: LegalIssueCreate,
    ) -> LegalIssueRecord: ...

    def get_legal_issue(self, issue_id: str) -> LegalIssueRecord: ...

    def list_legal_issues(
        self,
        case_id: str,
    ) -> list[LegalIssueRecord]: ...

    def update_legal_issue(
        self,
        issue_id: str,
        payload: LegalIssueCreate,
    ) -> LegalIssueRecord: ...

    def delete_legal_issue(
        self,
        issue_id: str,
        case_id: str,
    ) -> None: ...

    def add_norm(
        self,
        payload: NormCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> NormRecord: ...

    def get_norm(self, norm_id: str) -> NormRecord: ...

    def list_norms(self, case_id: str) -> list[NormRecord]: ...

    def update_norm(
        self,
        norm_id: str,
        payload: NormCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> NormRecord: ...

    def add_jurisprudence(
        self,
        payload: JurisprudenceCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> JurisprudenceRecord: ...

    def get_jurisprudence(
        self,
        jurisprudence_id: str,
    ) -> JurisprudenceRecord: ...

    def list_jurisprudence(
        self,
        case_id: str,
    ) -> list[JurisprudenceRecord]: ...

    def update_jurisprudence(
        self,
        jurisprudence_id: str,
        payload: JurisprudenceCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> JurisprudenceRecord: ...

    def add_doctrine(
        self,
        payload: DoctrineCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> DoctrineRecord: ...

    def get_doctrine(self, doctrine_id: str) -> DoctrineRecord: ...

    def list_doctrine(self, case_id: str) -> list[DoctrineRecord]: ...

    def update_doctrine(
        self,
        doctrine_id: str,
        payload: DoctrineCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> DoctrineRecord: ...

    def link_issue_source(
        self,
        payload: IssueSourceLinkCreate,
    ) -> None: ...

    def list_issue_source_links(
        self,
        case_id: str,
    ) -> list[IssueSourceLinkView]: ...

    def update_issue_source_link(
        self,
        payload: IssueSourceLinkCreate,
    ) -> None: ...

    def unlink_issue_source(
        self,
        *,
        case_id: str,
        issue_id: str,
        source_type: LegalSourceType,
        source_id: str,
    ) -> None: ...

    def delete_source(
        self,
        *,
        case_id: str,
        source_type: LegalSourceType,
        source_id: str,
    ) -> None: ...

    def get_source_identity(
        self,
        source_type: LegalSourceType,
        source_id: str,
    ) -> tuple[str, str, str]: ...

    def count_by_case(self, table: str, case_id: str) -> int: ...

    def count_links(self, case_id: str) -> int: ...

    def count_issue_source_links(self, case_id: str) -> int: ...

    def list_audit_events(
        self,
        case_id: str,
        limit: int = 50,
    ) -> list[AuditEventRecord]: ...
