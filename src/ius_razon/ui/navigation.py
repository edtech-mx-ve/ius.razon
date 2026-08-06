from __future__ import annotations

from dataclasses import dataclass

DEFAULT_PAGE_ID = "summary"


@dataclass(frozen=True, slots=True)
class NavigationItem:
    """Describe una vista navegable de la aplicación."""

    page_id: str
    label: str
    group: str
    description: str


_NAVIGATION_ITEMS: tuple[NavigationItem, ...] = (
    NavigationItem(
        page_id="summary",
        label="Resumen",
        group="Inicio",
        description="Estado general del expediente y actividad reciente.",
    ),
    NavigationItem(
        page_id="parties",
        label="Partes",
        group="Expediente",
        description="Registro de partes, roles y posiciones.",
    ),
    NavigationItem(
        page_id="facts",
        label="Hechos",
        group="Expediente",
        description="Hechos alegados, controvertidos y acreditados.",
    ),
    NavigationItem(
        page_id="evidence",
        label="Pruebas",
        group="Expediente",
        description="Pruebas, origen, integridad y valoración.",
    ),
    NavigationItem(
        page_id="fact_evidence",
        label="Hecho–prueba",
        group="Expediente",
        description="Vínculos trazables entre hechos y pruebas.",
    ),
    NavigationItem(
        page_id="issues",
        label="Problemas jurídicos",
        group="Fuentes jurídicas",
        description="Preguntas jurídicas delimitadas para el análisis.",
    ),
    NavigationItem(
        page_id="norms",
        label="Normas",
        group="Fuentes jurídicas",
        description="Normas, versiones y referencias registradas.",
    ),
    NavigationItem(
        page_id="jurisprudence",
        label="Jurisprudencia",
        group="Fuentes jurídicas",
        description="Precedentes y comparación con el expediente.",
    ),
    NavigationItem(
        page_id="doctrine",
        label="Doctrina",
        group="Fuentes jurídicas",
        description="Fuentes doctrinales y tesis relevantes.",
    ),
    NavigationItem(
        page_id="source_matrix",
        label="Matriz problema–fuente",
        group="Fuentes jurídicas",
        description="Relación entre problemas y fuentes jurídicas.",
    ),
    NavigationItem(
        page_id="assertions",
        label="Premisas",
        group="Razonamiento",
        description="Premisas y valores usados por el motor determinista.",
    ),
    NavigationItem(
        page_id="rules",
        label="Reglas",
        group="Razonamiento",
        description="Reglas estructuradas y condiciones de inferencia.",
    ),
    NavigationItem(
        page_id="inference",
        label="Inferencia",
        group="Razonamiento",
        description="Ejecuciones, conclusiones y trazabilidad.",
    ),
    NavigationItem(
        page_id="reasoning_management",
        label="Gestión del razonamiento",
        group="Razonamiento",
        description="Edición y administración segura de premisas y reglas.",
    ),
    NavigationItem(
        page_id="safe_correction",
        label="Corrección segura",
        group="Razonamiento",
        description="Correcciones controladas con respaldo y auditoría.",
    ),
    NavigationItem(
        page_id="argumentation",
        label="Argumentación",
        group="Argumentación e informes",
        description="Argumentos, objeciones, respuestas y escenarios.",
    ),
    NavigationItem(
        page_id="integral_report",
        label="Informe integral",
        group="Argumentación e informes",
        description="Informe jurídico trazable con revisión humana.",
    ),
    NavigationItem(
        page_id="assistant",
        label="Asistente IA",
        group="Argumentación e informes",
        description="Borradores locales controlados y auditables.",
    ),
    NavigationItem(
        page_id="privacy",
        label="Privacidad y demo",
        group="Seguridad",
        description="Análisis de privacidad y preparación de datos sintéticos.",
    ),
)


def navigation_items() -> tuple[NavigationItem, ...]:
    """Devuelve el registro inmutable de vistas."""

    return _NAVIGATION_ITEMS


def navigation_groups() -> tuple[str, ...]:
    """Devuelve los grupos en el orden de presentación."""

    return tuple(dict.fromkeys(item.group for item in _NAVIGATION_ITEMS))


def navigation_items_for_group(group: str) -> tuple[NavigationItem, ...]:
    """Devuelve las vistas que pertenecen al grupo indicado."""

    return tuple(item for item in _NAVIGATION_ITEMS if item.group == group)


def get_navigation_item(page_id: str) -> NavigationItem:
    """Obtiene una vista por identificador o lanza un error explícito."""

    for item in _NAVIGATION_ITEMS:
        if item.page_id == page_id:
            return item
    raise KeyError(f"Vista desconocida: {page_id}")


def normalize_page_id(value: object) -> str:
    """Normaliza un valor de sesión a un identificador navegable válido."""

    if isinstance(value, str):
        for item in _NAVIGATION_ITEMS:
            if item.page_id == value:
                return value
    return DEFAULT_PAGE_ID
