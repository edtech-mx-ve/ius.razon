from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from ius_razon.domain.argumentation_models import (
    ArgumentRelationCreate,
    ArgumentRelationRecord,
    ArgumentScenarioCreate,
    ArgumentScenarioRecord,
    ArgumentScenarioUpdate,
    LegalArgumentCreate,
    LegalArgumentRecord,
    LegalArgumentUpdate,
)


@runtime_checkable
class ArgumentationRepositoryProtocol(Protocol):
    """Contrato de persistencia requerido por ArgumentationService."""

    def validate_case_issue(self, case_id: str, issue_id: str) -> None: ...

    def conclusion_context(
        self,
        conclusion_id: str,
    ) -> dict[str, str | list[str]]: ...

    def list_conclusion_contexts(
        self,
        case_id: str,
        issue_id: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, str | list[str]]]: ...

    def add_argument(
        self,
        payload: LegalArgumentCreate,
    ) -> LegalArgumentRecord: ...

    def get_argument(self, argument_id: str) -> LegalArgumentRecord: ...

    def list_arguments(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        include_discarded: bool = False,
    ) -> list[LegalArgumentRecord]: ...

    def update_argument(
        self,
        argument_id: str,
        payload: LegalArgumentUpdate,
    ) -> LegalArgumentRecord: ...

    def delete_argument(
        self,
        argument_id: str,
        *,
        confirmation: str,
    ) -> None: ...

    def add_relation(
        self,
        payload: ArgumentRelationCreate,
    ) -> ArgumentRelationRecord: ...

    def get_relation(self, relation_id: str) -> ArgumentRelationRecord: ...

    def list_relations(
        self,
        case_id: str,
        issue_id: str | None = None,
    ) -> list[ArgumentRelationRecord]: ...

    def delete_relation(
        self,
        relation_id: str,
        *,
        confirmation: str,
    ) -> None: ...

    def add_scenario(
        self,
        payload: ArgumentScenarioCreate,
    ) -> ArgumentScenarioRecord: ...

    def get_scenario(self, scenario_id: str) -> ArgumentScenarioRecord: ...

    def list_scenarios(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        include_archived: bool = False,
    ) -> list[ArgumentScenarioRecord]: ...

    def update_scenario(
        self,
        scenario_id: str,
        payload: ArgumentScenarioUpdate,
    ) -> ArgumentScenarioRecord: ...

    def delete_scenario(
        self,
        scenario_id: str,
        *,
        confirmation: str,
    ) -> None: ...

    def known_codes(self, case_id: str, issue_id: str) -> set[str]: ...

    def snapshot_timestamp(
        self,
        case_id: str,
        issue_id: str,
    ) -> datetime: ...

    def issue_metadata(
        self,
        case_id: str,
        issue_id: str,
    ) -> dict[str, str]: ...
