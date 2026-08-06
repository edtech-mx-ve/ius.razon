from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ius_razon.domain.reasoning_models import AssertionValue, PredicateKey


class ArgumentPosition(StrEnum):
    FAVORABLE = "Favorable"
    ADVERSE = "Adverso"
    NEUTRAL = "Neutral"


class ArgumentStatus(StrEnum):
    DRAFT = "Borrador"
    SUPPORTED = "Sustentado"
    VALIDATED = "Validado"
    OBJECTED = "Objetado"
    ANSWERED = "Respondido"
    WEAKENED = "Debilitado"
    DEFEATED = "Derrotado"
    UNRESOLVED = "No resuelto"
    DISCARDED = "Descartado"


class ArgumentSupportLevel(StrEnum):
    INSUFFICIENT = "Insuficiente"
    LOW = "Bajo"
    MEDIUM = "Medio"
    HIGH = "Alto"


class ArgumentRelationType(StrEnum):
    SUPPORTS = "Apoya"
    ATTACKS = "Ataca"
    REPLIES = "Responde"


class ScenarioStatus(StrEnum):
    DRAFT = "Borrador"
    ACTIVE = "Activo"
    ARCHIVED = "Archivado"


class ArgumentationModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class LegalArgumentFields(ArgumentationModel):
    title: Annotated[str, Field(min_length=5, max_length=240)]
    position: ArgumentPosition
    thesis_key: PredicateKey
    thesis_statement: Annotated[str, Field(min_length=5, max_length=2000)]
    thesis_value: AssertionValue
    claim: Annotated[str, Field(min_length=10, max_length=5000)]
    reasoning: Annotated[str, Field(min_length=10, max_length=8000)]
    status: ArgumentStatus = ArgumentStatus.DRAFT
    conclusion_id: str | None = None
    fact_codes: list[str] = Field(default_factory=list, max_length=40)
    evidence_codes: list[str] = Field(default_factory=list, max_length=40)
    source_codes: list[str] = Field(default_factory=list, max_length=40)
    rule_codes: list[str] = Field(default_factory=list, max_length=40)
    assertion_codes: list[str] = Field(default_factory=list, max_length=40)

    @field_validator(
        "fact_codes",
        "evidence_codes",
        "source_codes",
        "rule_codes",
        "assertion_codes",
    )
    @classmethod
    def normalize_codes(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            code = value.strip().upper()
            if code and code not in normalized:
                normalized.append(code)
        return normalized

    @model_validator(mode="after")
    def validate_argument(self) -> LegalArgumentFields:
        if self.thesis_value is AssertionValue.UNKNOWN:
            raise ValueError("La tesis argumental no puede tener valor Desconocido.")
        return self


class LegalArgumentCreate(LegalArgumentFields):
    case_id: Annotated[str, Field(min_length=1, max_length=300)]
    issue_id: Annotated[str, Field(min_length=1, max_length=300)]


class LegalArgumentUpdate(LegalArgumentFields):
    """Campos editables; el código y el expediente se conservan."""


class LegalArgumentRecord(LegalArgumentCreate):
    id: str
    code: str
    created_at: datetime
    updated_at: datetime


class ArgumentRelationCreate(ArgumentationModel):
    case_id: Annotated[str, Field(min_length=1, max_length=300)]
    issue_id: Annotated[str, Field(min_length=1, max_length=300)]
    source_argument_id: Annotated[str, Field(min_length=1, max_length=300)]
    target_argument_id: Annotated[str, Field(min_length=1, max_length=300)]
    relation_type: ArgumentRelationType
    rationale: Annotated[str, Field(min_length=5, max_length=4000)]

    @model_validator(mode="after")
    def reject_self_relation(self) -> ArgumentRelationCreate:
        if self.source_argument_id == self.target_argument_id:
            raise ValueError("Un argumento no puede relacionarse consigo mismo.")
        return self


class ArgumentRelationRecord(ArgumentRelationCreate):
    id: str
    code: str
    created_at: datetime


class ArgumentSupportAssessment(ArgumentationModel):
    argument_code: str
    level: ArgumentSupportLevel
    score: int = Field(ge=0, le=5)
    missing_components: list[str]


class ArgumentScenarioFields(ArgumentationModel):
    name: Annotated[str, Field(min_length=5, max_length=240)]
    description: Annotated[str, Field(min_length=10, max_length=4000)]
    status: ScenarioStatus = ScenarioStatus.DRAFT
    argument_ids: list[str] = Field(min_length=1, max_length=100)
    assumptions: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("argument_ids")
    @classmethod
    def normalize_argument_ids(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip()
            if item and item not in normalized:
                normalized.append(item)
        if not normalized:
            raise ValueError("El escenario debe incluir al menos un argumento.")
        return normalized

    @field_validator("assumptions")
    @classmethod
    def normalize_assumptions(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip()
            if item and item not in normalized:
                if len(item) > 500:
                    raise ValueError("Cada supuesto admite hasta 500 caracteres.")
                normalized.append(item)
        return normalized


class ArgumentScenarioCreate(ArgumentScenarioFields):
    case_id: Annotated[str, Field(min_length=1, max_length=300)]
    issue_id: Annotated[str, Field(min_length=1, max_length=300)]


class ArgumentScenarioUpdate(ArgumentScenarioFields):
    """Campos editables del escenario."""


class ArgumentScenarioRecord(ArgumentScenarioCreate):
    id: str
    code: str
    created_at: datetime
    updated_at: datetime


class ArgumentGraphNode(ArgumentationModel):
    argument_id: str
    code: str
    title: str
    position: ArgumentPosition
    status: ArgumentStatus
    thesis_key: str
    thesis_value: AssertionValue
    support_level: ArgumentSupportLevel
    support_score: int = Field(ge=0, le=5)


class ArgumentGraphEdge(ArgumentationModel):
    relation_id: str
    code: str
    source_argument_id: str
    source_code: str
    target_argument_id: str
    target_code: str
    relation_type: ArgumentRelationType
    rationale: str


class ArgumentGraphSnapshot(ArgumentationModel):
    case_id: str
    issue_id: str
    scenario_id: str | None
    scenario_code: str | None
    scenario_name: str
    generated_at: datetime
    input_hash: str
    nodes: list[ArgumentGraphNode]
    edges: list[ArgumentGraphEdge]
    summary: dict[str, int | str | bool | float]
    unresolved_objection_codes: list[str]
    orphan_argument_codes: list[str]
    warnings: list[str]
    assumptions: list[str]
    dot_source: str


class ScenarioComparison(ArgumentationModel):
    first_scenario_code: str
    second_scenario_code: str
    same_input: bool
    first_input_hash: str
    second_input_hash: str
    added_argument_codes: list[str]
    removed_argument_codes: list[str]
    added_relation_codes: list[str]
    removed_relation_codes: list[str]
    metric_deltas: dict[str, int | float]


class ArgumentationDossier(ArgumentationModel):
    case_id: str
    issue_id: str
    generated_at: datetime
    input_hash: str
    arguments: list[LegalArgumentRecord]
    relations: list[ArgumentRelationRecord]
    support_assessments: list[ArgumentSupportAssessment]
    summary: dict[str, int | str | bool]
    unresolved_objection_codes: list[str]
    orphan_argument_codes: list[str]
    missing_information: list[str]
