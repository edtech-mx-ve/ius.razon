from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter

LOGGER = logging.getLogger(__name__)


class RenderPerformanceLevel(StrEnum):
    """Clasificación simple para el tiempo de renderizado de una vista."""

    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class RenderPerformanceBudget:
    """Umbrales de observabilidad para una vista de Streamlit."""

    warning_ms: float = 1500.0
    critical_ms: float = 5000.0

    def validate(self) -> None:
        """Valida que los umbrales sean positivos y crecientes."""

        if self.warning_ms <= 0:
            raise ValueError("warning_ms debe ser mayor que cero.")
        if self.critical_ms <= self.warning_ms:
            raise ValueError(
                "critical_ms debe ser mayor que warning_ms."
            )


def classify_render_duration(
    duration_ms: float,
    *,
    budget: RenderPerformanceBudget | None = None,
) -> RenderPerformanceLevel:
    """Clasifica una duración sin modificar estado global."""

    selected_budget = budget or RenderPerformanceBudget()
    selected_budget.validate()
    if duration_ms < 0:
        raise ValueError("duration_ms no puede ser negativo.")
    if duration_ms >= selected_budget.critical_ms:
        return RenderPerformanceLevel.CRITICAL
    if duration_ms >= selected_budget.warning_ms:
        return RenderPerformanceLevel.WARNING
    return RenderPerformanceLevel.OK


@contextmanager
def measure_view_render(
    page_id: str,
    *,
    budget: RenderPerformanceBudget | None = None,
) -> Iterator[None]:
    """Mide una vista activa y registra solo metadatos técnicos."""

    if not page_id.strip():
        raise ValueError("page_id no puede estar vacío.")
    selected_budget = budget or RenderPerformanceBudget()
    selected_budget.validate()
    started = perf_counter()
    try:
        yield
    finally:
        duration_ms = max((perf_counter() - started) * 1000, 0.0)
        level = classify_render_duration(
            duration_ms,
            budget=selected_budget,
        )
        message = (
            "Vista renderizada. page=%s duration_ms=%.2f level=%s"
        )
        if level is RenderPerformanceLevel.CRITICAL:
            LOGGER.error(message, page_id, duration_ms, level.value)
        elif level is RenderPerformanceLevel.WARNING:
            LOGGER.warning(message, page_id, duration_ms, level.value)
        else:
            LOGGER.info(message, page_id, duration_ms, level.value)
