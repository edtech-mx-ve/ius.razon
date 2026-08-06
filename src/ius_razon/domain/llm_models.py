from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ius_razon.domain.models import utc_now


class AssistantTask(StrEnum):
    """Tipos de borrador asistivo disponibles."""

    CASE_SUMMARY = "Resumen del expediente"
    ARGUMENT_DRAFT = "Borrador de argumento"
    CONCLUSION_EXPLANATION = "Explicación de conclusión"
    MISSING_INFORMATION = "Información faltante"
    REPORT_SECTION = "Borrador de sección de informe"


class ContextCategory(StrEnum):
    """Categorías de contexto que pueden enviarse al proveedor."""

    ISSUE = "Problema jurídico"
    FACT = "Hecho"
    EVIDENCE = "Prueba"
    SOURCE = "Fuente jurídica"
    CONCLUSION = "Conclusión"
    ARGUMENT = "Argumento"


class DraftStatus(StrEnum):
    """Estados del flujo de revisión humana."""

    GENERATED = "Generado"
    APPROVED = "Aprobado"
    REJECTED = "Rechazado"


class AssistantModel(BaseModel):
    """Configuración base para modelos del asistente."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ContextItem(AssistantModel):
    """Unidad estructurada de contexto trazable."""

    code: Annotated[str, Field(min_length=2, max_length=40)]
    category: ContextCategory
    title: Annotated[str, Field(min_length=2, max_length=1000)]
    content: Annotated[str, Field(min_length=1, max_length=50000)]
    source_id: str | None = Field(default=None, max_length=120)


class AssistantRequest(AssistantModel):
    """Solicitud controlada para generar un borrador."""

    case_id: Annotated[str, Field(min_length=1, max_length=120)]
    issue_id: Annotated[str, Field(min_length=1, max_length=120)]
    reasoning_run_id: str | None = Field(default=None, max_length=120)
    task: AssistantTask
    instructions: str | None = Field(default=None, max_length=3000)
    selected_categories: list[ContextCategory] = Field(min_length=1, max_length=6)
    selected_codes: list[str] = Field(default_factory=list, max_length=100)
    anonymize_parties: bool = True
    max_context_chars: int = Field(default=12000, ge=1000, le=50000)
    max_output_chars: int = Field(default=8000, ge=500, le=20000)

    @model_validator(mode="after")
    def validate_unique_selections(self) -> AssistantRequest:
        """Evita selecciones duplicadas y ambiguas."""

        if len(set(self.selected_categories)) != len(self.selected_categories):
            raise ValueError("Las categorías seleccionadas no pueden repetirse.")
        if len(set(self.selected_codes)) != len(self.selected_codes):
            raise ValueError("Los códigos seleccionados no pueden repetirse.")
        return self


class ContextPreview(AssistantModel):
    """Vista previa del contexto antes de invocar al proveedor."""

    items: list[ContextItem] = Field(min_length=1)
    risk_flags: list[str] = Field(default_factory=list)
    anonymization_map: dict[str, str] = Field(default_factory=dict)
    char_count: int = Field(ge=1)
    input_hash: Annotated[str, Field(min_length=64, max_length=64)]


class ProviderRequest(AssistantModel):
    """Contrato de entrada independiente del proveedor."""

    task: AssistantTask
    instructions: str | None = None
    context_items: list[ContextItem] = Field(min_length=1)
    allowed_codes: list[str] = Field(min_length=1)
    max_output_chars: int = Field(ge=500, le=20000)
    system_instruction: Annotated[str, Field(min_length=20, max_length=4000)]


class ProviderResponse(AssistantModel):
    """Respuesta normalizada de un proveedor asistivo."""

    text: Annotated[str, Field(min_length=1, max_length=20000)]
    provider_name: Annotated[str, Field(min_length=2, max_length=120)]
    model_name: Annotated[str, Field(min_length=2, max_length=160)]
    generated_at: datetime = Field(default_factory=utc_now)


class DraftEvaluation(AssistantModel):
    """Resultado de evaluar trazabilidad y cobertura de citas."""

    reference_codes: list[str] = Field(default_factory=list)
    invalid_reference_codes: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    citation_coverage: float = Field(ge=0.0, le=1.0)
    passed: bool


class AssistantDraftCreate(AssistantModel):
    """Datos persistibles de un borrador generado."""

    case_id: str
    issue_id: str
    task: AssistantTask
    provider_name: str
    model_name: str
    request_snapshot: dict[str, object]
    context_items: list[ContextItem]
    response_text: str
    reference_codes: list[str]
    invalid_reference_codes: list[str]
    unsupported_claims: list[str]
    risk_flags: list[str]
    citation_coverage: float = Field(ge=0.0, le=1.0)
    input_hash: Annotated[str, Field(min_length=64, max_length=64)]
    output_hash: Annotated[str, Field(min_length=64, max_length=64)]


class AssistantDraftRecord(AssistantDraftCreate):
    """Registro persistido con estado de revisión."""

    id: str
    code: str
    status: DraftStatus
    edited_text: str | None = None
    reviewer_note: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None


class DraftReview(AssistantModel):
    """Decisión humana sobre un borrador."""

    decision: DraftStatus
    edited_text: str | None = Field(default=None, max_length=20000)
    reviewer_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_decision(self) -> DraftReview:
        """Exige texto final para aprobar y prohíbe reutilizar Generado."""

        if self.decision is DraftStatus.GENERATED:
            raise ValueError("La revisión debe aprobar o rechazar el borrador.")
        if self.decision is DraftStatus.APPROVED and not self.edited_text:
            raise ValueError("La aprobación requiere un texto final revisado.")
        return self
