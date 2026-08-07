from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from ius_razon.domain.reasoning_models import (
    ReasoningAssertionCreate,
    ReasoningAssertionRecord,
    ReasoningAssertionUpdate,
    ReasoningRuleCreate,
    ReasoningRuleRecord,
    ReasoningRuleUpdate,
    ReasoningRunRecord,
    ReasoningRunReport,
    ReasoningVersionRecord,
)


@runtime_checkable
class ReasoningRepositoryProtocol(Protocol):
    """Contrato de persistencia requerido por ReasoningService."""

    def add_assertion(
        self,
        payload: ReasoningAssertionCreate,
    ) -> ReasoningAssertionRecord: ...

    def get_assertion(
        self,
        assertion_id: str,
    ) -> ReasoningAssertionRecord: ...

    def list_assertions(
        self,
        case_id: str,
        issue_id: str | None = None,
    ) -> list[ReasoningAssertionRecord]: ...

    def update_assertion(
        self,
        assertion_id: str,
        payload: ReasoningAssertionUpdate,
    ) -> ReasoningAssertionRecord: ...

    def delete_assertion(
        self,
        assertion_id: str,
        *,
        confirmation: str,
    ) -> None: ...

    def list_assertion_versions(
        self,
        *,
        case_id: str,
        entity_id: str | None = None,
    ) -> list[ReasoningVersionRecord]: ...

    def add_rule(
        self,
        payload: ReasoningRuleCreate,
    ) -> ReasoningRuleRecord: ...

    def get_rule(
        self,
        rule_id: str,
    ) -> ReasoningRuleRecord: ...

    def list_rules(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        active_only: bool = False,
    ) -> list[ReasoningRuleRecord]: ...

    def update_rule(
        self,
        rule_id: str,
        payload: ReasoningRuleUpdate,
    ) -> ReasoningRuleRecord: ...

    def delete_rule(
        self,
        rule_id: str,
        *,
        confirmation: str,
    ) -> None: ...

    def list_rule_versions(
        self,
        *,
        case_id: str,
        entity_id: str | None = None,
    ) -> list[ReasoningVersionRecord]: ...

    def create_run(
        self,
        *,
        case_id: str,
        issue_id: str,
        engine_version: str,
        input_hash: str,
        input_snapshot: Mapping[str, object],
    ) -> ReasoningRunRecord: ...

    def complete_run(
        self,
        *,
        run_id: str,
        summary: dict[str, int | str | bool],
        conclusions: list[dict[str, object]],
        traces: list[dict[str, object]],
    ) -> ReasoningRunReport: ...

    def fail_run(
        self,
        run_id: str,
        error_message: str,
    ) -> None: ...

    def list_runs(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        limit: int = 20,
    ) -> list[ReasoningRunRecord]: ...

    def get_run_report(
        self,
        run_id: str,
    ) -> ReasoningRunReport: ...

    def validate_case_issue(
        self,
        case_id: str,
        issue_id: str,
    ) -> None: ...

    def known_codes(self, case_id: str) -> set[str]: ...
