from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AssertionValue(StrEnum):
    TRUE = "Verdadero"
    FALSE = "Falso"
    UNKNOWN = "Desconocido"


class RuleKind(StrEnum):
    STRICT = "Estricta"
    DEFAULT = "Provisional"


class ConditionRole(StrEnum):
    PREREQUISITE = "Prerrequisito"
    EXCEPTION = "Excepción"


class ReasoningRunStatus(StrEnum):
    RUNNING = "En ejecución"
    COMPLETED = "Completada"
    FAILED = "Fallida"


class ConclusionStatus(StrEnum):
    STRICT = "Estricta dentro del modelo"
    PROVISIONAL = "Provisional"
    CONTRADICTED = "Controvertida"
    INSUFFICIENT = "Insuficientemente sustentada"


class SupportLevel(StrEnum):
    INSUFFICIENT = "Insuficiente"
    LOW = "Bajo"
    MEDIUM = "Medio"
    HIGH = "Alto"


class TraceOutcome(StrEnum):
    FIRED_STRICT = "Regla estricta aplicada"
    FIRED_DEFAULT = "Regla provisional aplicada"
    BLOCKED_EXCEPTION = "Bloqueada por excepción"
    BLOCKED_CONTRARY = "Bloqueada por conclusión contraria"
    DEFEATED_PRIORITY = "Derrotada por menor prioridad"
    DEFEATED_KIND = "Derrotada por regla estricta rival"
    DEFEATED_SPECIFICITY = "Derrotada por menor especificidad"
    TIED_CONFLICT = "Empate entre reglas rivales"
    WITHDRAWN_DEPENDENCY = "Retirada por dependencia derrotada"
    NON_CONVERGENT = "Ciclo no convergente"
    MISSING_PREMISES = "Premisas faltantes"
    CONTRADICTORY_PREMISES = "Premisas contradictorias"
    NOT_SATISFIED = "Premisas no satisfechas"


class VersionAction(StrEnum):
    UPDATED = "Actualizada"
    DELETED = "Eliminada"


PredicateKey = Annotated[
    str,
    Field(
        min_length=3,
        max_length=80,
        pattern=r"^[a-z][a-z0-9_]*$",
    ),
]


class ReasoningModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class ReasoningAssertionFields(ReasoningModel):
    predicate_key: PredicateKey
    statement: Annotated[str, Field(min_length=5, max_length=2000)]
    value: AssertionValue
    basis: Annotated[str, Field(min_length=5, max_length=4000)]
    support_codes: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("support_codes")
    @classmethod
    def normalize_support_codes(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            code = value.strip().upper()
            if code and code not in normalized:
                normalized.append(code)
        return normalized


class ReasoningAssertionCreate(ReasoningAssertionFields):
    case_id: Annotated[str, Field(min_length=1, max_length=300)]
    issue_id: Annotated[str, Field(min_length=1, max_length=300)]


class ReasoningAssertionUpdate(ReasoningAssertionFields):
    """Campos editables de una premisa; su código y expediente se preservan."""


class ReasoningAssertionRecord(ReasoningAssertionCreate):
    id: str
    code: str
    created_at: datetime
    updated_at: datetime


class RuleConditionCreate(ReasoningModel):
    role: ConditionRole
    predicate_key: PredicateKey
    expected_value: AssertionValue

    @model_validator(mode="after")
    def reject_unknown_expectation(self) -> RuleConditionCreate:
        if self.expected_value is AssertionValue.UNKNOWN:
            raise ValueError("Una condición no puede esperar el valor Desconocido.")
        return self


class ReasoningRuleFields(ReasoningModel):
    name: Annotated[str, Field(min_length=3, max_length=240)]
    kind: RuleKind
    conclusion_key: PredicateKey
    conclusion_statement: Annotated[str, Field(min_length=5, max_length=2000)]
    conclusion_value: AssertionValue
    priority: int = Field(default=100, ge=0, le=1000)
    active: bool = True
    legal_basis_codes: list[str] = Field(default_factory=list, max_length=30)
    explanation: Annotated[str, Field(min_length=5, max_length=4000)]
    conditions: list[RuleConditionCreate] = Field(min_length=1, max_length=20)

    @field_validator("legal_basis_codes")
    @classmethod
    def normalize_legal_basis_codes(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            code = value.strip().upper()
            if code and code not in normalized:
                normalized.append(code)
        return normalized

    @model_validator(mode="after")
    def validate_rule(self) -> ReasoningRuleFields:
        if self.conclusion_value is AssertionValue.UNKNOWN:
            raise ValueError("La conclusión de una regla no puede ser Desconocido.")
        prerequisites = [
            condition
            for condition in self.conditions
            if condition.role is ConditionRole.PREREQUISITE
        ]
        if not prerequisites:
            raise ValueError("La regla necesita al menos un prerrequisito.")
        if self.kind is RuleKind.STRICT and any(
            condition.role is ConditionRole.EXCEPTION for condition in self.conditions
        ):
            raise ValueError("Las excepciones solo se admiten en reglas provisionales.")
        return self


class ReasoningRuleCreate(ReasoningRuleFields):
    case_id: Annotated[str, Field(min_length=1, max_length=300)]
    issue_id: Annotated[str, Field(min_length=1, max_length=300)]


class ReasoningRuleUpdate(ReasoningRuleFields):
    """Campos editables de una regla; su código y expediente se preservan."""


class ReasoningRuleRecord(ReasoningRuleCreate):
    id: str
    code: str
    created_at: datetime
    updated_at: datetime

    @property
    def specificity_score(self) -> int:
        """Número de prerrequisitos distintos usados como especificidad estructural."""

        return len(
            {
                (condition.predicate_key, condition.expected_value)
                for condition in self.conditions
                if condition.role is ConditionRole.PREREQUISITE
            }
        )


class ReasoningVersionRecord(ReasoningModel):
    id: str
    entity_type: str
    entity_id: str
    entity_code: str
    version_number: int
    action: VersionAction
    snapshot: dict[str, object]
    created_at: datetime


class ReasoningRunRecord(ReasoningModel):
    id: str
    case_id: str
    issue_id: str
    status: ReasoningRunStatus
    engine_version: str
    input_hash: str
    input_snapshot: dict[str, object] = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime | None = None
    summary: dict[str, int | str | bool] = Field(default_factory=dict)


class ReasoningConclusionRecord(ReasoningModel):
    id: str
    run_id: str
    code: str
    predicate_key: str
    statement: str
    value: AssertionValue
    status: ConclusionStatus
    support_level: SupportLevel
    rule_codes: list[str]
    supporting_assertion_codes: list[str]
    source_codes: list[str]
    created_at: datetime


class ReasoningTraceRecord(ReasoningModel):
    id: str
    run_id: str
    sequence: int
    rule_id: str
    rule_code: str
    outcome: TraceOutcome
    detail: dict[str, object]
    created_at: datetime


class ReasoningRunReport(ReasoningModel):
    run: ReasoningRunRecord
    conclusions: list[ReasoningConclusionRecord]
    traces: list[ReasoningTraceRecord]
