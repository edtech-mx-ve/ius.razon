from __future__ import annotations

from typing import Protocol, runtime_checkable

from ius_razon.domain.llm_models import (
    AssistantDraftCreate,
    AssistantDraftRecord,
    DraftStatus,
    ProviderCallAuditCreate,
    ProviderCallAuditRecord,
)


@runtime_checkable
class LLMRepositoryProtocol(Protocol):
    """Contrato de persistencia requerido por LLMAssistantService."""

    def validate_case_issue(self, case_id: str, issue_id: str) -> None: ...

    def add_draft(
        self,
        payload: AssistantDraftCreate,
    ) -> AssistantDraftRecord: ...

    def add_provider_call(
        self,
        payload: ProviderCallAuditCreate,
    ) -> ProviderCallAuditRecord: ...

    def link_provider_call_to_draft(
        self,
        call_id: str,
        draft_id: str,
    ) -> ProviderCallAuditRecord: ...

    def get_provider_call(
        self,
        call_id: str,
    ) -> ProviderCallAuditRecord: ...

    def list_provider_calls(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        limit: int = 50,
    ) -> list[ProviderCallAuditRecord]: ...

    def get_draft(self, draft_id: str) -> AssistantDraftRecord: ...

    def list_drafts(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        limit: int = 50,
    ) -> list[AssistantDraftRecord]: ...

    def review_draft(
        self,
        draft_id: str,
        *,
        status: DraftStatus,
        edited_text: str | None,
        reviewer_note: str | None,
        reference_codes: list[str],
        invalid_reference_codes: list[str],
        unsupported_claims: list[str],
        citation_coverage: float,
        output_hash: str,
    ) -> AssistantDraftRecord: ...
