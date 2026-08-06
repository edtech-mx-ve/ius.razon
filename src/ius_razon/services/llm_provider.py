from __future__ import annotations

import re
from collections.abc import Callable
from typing import Protocol

from ius_razon.domain.llm_models import (
    AssistantTask,
    ContextCategory,
    ContextItem,
    ProviderRequest,
    ProviderResponse,
)


class LLMProvider(Protocol):
    """Interfaz sustituible para proveedores asistivos."""

    @property
    def provider_name(self) -> str:
        """Nombre estable del proveedor."""

        ...

    @property
    def model_name(self) -> str:
        """Nombre estable del modelo."""

        ...

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Genera una respuesta sin modificar el expediente."""

        ...


class DeterministicMockProvider:
    """Proveedor local reproducible para probar el flujo sin consumir API."""

    def __init__(self, model_name: str = "ius-razon-mock-v1") -> None:
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "Simulado local"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Construye un borrador determinista y completamente referenciado."""

        builders: dict[
            AssistantTask,
            Callable[[list[ContextItem]], str],
        ] = {
            AssistantTask.CASE_SUMMARY: self._summary,
            AssistantTask.ARGUMENT_DRAFT: self._argument,
            AssistantTask.CONCLUSION_EXPLANATION: self._conclusion_explanation,
            AssistantTask.MISSING_INFORMATION: self._missing_information,
            AssistantTask.REPORT_SECTION: self._report_section,
        }
        text = builders[request.task](request.context_items)
        if request.instructions:
            referenced = request.context_items[0].code
            instruction = self._compact(request.instructions, 240)
            text = (
                f"{text}\n\n"
                f"Control de contexto: la indicación del usuario fue «{instruction}». "
                f"No se incorporaron hechos nuevos [{referenced}]."
            )
        text = self._limit_output(text, request.max_output_chars)
        return ProviderResponse(
            text=text,
            provider_name=self.provider_name,
            model_name=self.model_name,
        )

    def _summary(self, items: list[ContextItem]) -> str:
        lines = [
            "## Resumen estructurado",
            "Borrador simulado: síntesis construida únicamente con el contexto seleccionado.",
        ]
        for item in items[:8]:
            lines.append(
                f"- {item.title}: {self._compact(item.content)} [{item.code}]"
            )
        lines.append(
            "Revisión humana: confirma autenticidad, vigencia y suficiencia antes de usar el texto."
        )
        return "\n".join(lines)

    def _argument(self, items: list[ContextItem]) -> str:
        issue = self._first(items, ContextCategory.ISSUE) or items[0]
        lines = [
            "## Borrador de argumento",
            (
                "Tesis de trabajo: el problema debe analizarse con base en los "
                f"elementos trazables seleccionados [{issue.code}]."
            ),
        ]
        for category, label in (
            (ContextCategory.FACT, "Hecho relevante"),
            (ContextCategory.EVIDENCE, "Apoyo probatorio"),
            (ContextCategory.SOURCE, "Fundamento jurídico registrado"),
            (ContextCategory.CONCLUSION, "Resultado determinista"),
            (ContextCategory.ARGUMENT, "Posición argumental"),
        ):
            item = self._first(items, category)
            if item is not None:
                lines.append(
                    f"- {label}: {self._compact(item.content)} [{item.code}]"
                )
        lines.append(
            "Revisión humana: el texto es un borrador y no sustituye la valoración jurídica."
        )
        return "\n".join(lines)

    def _conclusion_explanation(self, items: list[ContextItem]) -> str:
        conclusions = [
            item for item in items if item.category is ContextCategory.CONCLUSION
        ]
        selected = conclusions or items[:1]
        lines = [
            "## Explicación de conclusión",
            "Borrador simulado: la explicación no altera el resultado del motor.",
        ]
        for item in selected[:5]:
            lines.append(
                f"- {item.title}: {self._compact(item.content)} [{item.code}]"
            )
        lines.append(
            "Revisión humana: verifica que las premisas y reglas sigan siendo válidas."
        )
        return "\n".join(lines)

    def _missing_information(self, items: list[ContextItem]) -> str:
        issue = self._first(items, ContextCategory.ISSUE) or items[0]
        present = {item.category for item in items}
        expected = (
            ContextCategory.FACT,
            ContextCategory.EVIDENCE,
            ContextCategory.SOURCE,
            ContextCategory.CONCLUSION,
            ContextCategory.ARGUMENT,
        )
        lines = [
            "## Información faltante",
            (
                "Control de contexto: revisión estructural de las categorías "
                "seleccionadas, sin inferir hechos nuevos."
            ),
        ]
        missing = [category for category in expected if category not in present]
        if missing:
            for category in missing:
                lines.append(
                    f"- Falta incorporar al menos un elemento de «{category.value}» "
                    f"para revisar el problema [{issue.code}]."
                )
        else:
            lines.append(
                "Todas las categorías estructurales están representadas, pero su "
                f"autenticidad y suficiencia requieren revisión [{issue.code}]."
            )
        lines.append(
            "Revisión humana: documenta cualquier vacío antes de aprobar el borrador."
        )
        return "\n".join(lines)

    def _report_section(self, items: list[ContextItem]) -> str:
        issue = self._first(items, ContextCategory.ISSUE) or items[0]
        lines = [
            "## Borrador de sección del informe",
            (
                "El análisis parte del problema jurídico registrado y conserva "
                f"su alcance provisional [{issue.code}]."
            ),
        ]
        for item in items:
            if item.code == issue.code:
                continue
            lines.append(
                f"- {item.category.value}: {self._compact(item.content)} [{item.code}]"
            )
            if len(lines) >= 9:
                break
        lines.append(
            "Revisión humana: valida el contenido y edítalo antes de aprobarlo."
        )
        return "\n".join(lines)

    @staticmethod
    def _first(
        items: list[ContextItem],
        category: ContextCategory,
    ) -> ContextItem | None:
        return next(
            (item for item in items if item.category is category),
            None,
        )

    @staticmethod
    def _compact(value: str, limit: int = 280) -> str:
        compact = re.sub(r"\s+", " ", value).strip()
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 1].rstrip()}…"

    @staticmethod
    def _limit_output(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        kept: list[str] = []
        used = 0
        for line in text.splitlines():
            additional = len(line) + (1 if kept else 0)
            if used + additional > max_chars:
                break
            kept.append(line)
            used += additional
        if not kept:
            raise ValueError("El límite de salida es insuficiente.")
        return "\n".join(kept)
