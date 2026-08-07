from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from ius_razon.ui.navigation import (
    navigation_groups,
    navigation_items_for_group,
)


@dataclass(frozen=True, slots=True)
class SectionHelp:
    """Ayuda reutilizable por sección y por el manual."""

    purpose: str
    steps: tuple[str, ...]
    result: str
    caution: str


SECTION_HELP: dict[str, SectionHelp] = {
    "summary": SectionHelp(
        "Presenta el estado general del expediente y su actividad reciente.",
        (
            "Verifica que el expediente activo sea el correcto.",
            "Revisa los conteos para identificar información faltante.",
            "Consulta la actividad reciente antes de continuar.",
        ),
        "Vista ejecutiva del estado del expediente.",
        "El resumen describe lo registrado; no valida su corrección jurídica.",
    ),
    "parties": SectionHelp(
        "Registra partes, roles jurídicos, pretensiones y posiciones.",
        (
            "Usa nombre o seudónimo conforme a la política de privacidad.",
            "Selecciona tipo de persona y rol jurídico.",
            "Registra representación, pretensión y posición cuando procedan.",
        ),
        "Partes disponibles para vincular hechos y pruebas.",
        "Evita incorporar datos personales innecesarios.",
    ),
    "facts": SectionHelp(
        "Estructura los acontecimientos relevantes del análisis jurídico.",
        (
            "Registra cada hecho de forma individual y concreta.",
            "Añade fecha, actor, acción, objeto, lugar y fuente cuando existan.",
            "Indica estado y nivel de controversia.",
        ),
        "Hechos preparados para relacionarse con pruebas.",
        "No confundas valoración jurídica con descripción del hecho.",
    ),
    "evidence": SectionHelp(
        "Registra elementos probatorios, origen, integridad y valoración.",
        (
            "Describe la prueba y selecciona su tipo.",
            "Registra origen, fecha, integridad, objeciones y observaciones.",
            "Vincula la parte oferente cuando corresponda.",
        ),
        "Pruebas disponibles para vincularse con hechos.",
        "La aplicación no determina autenticidad ni valor probatorio por sí sola.",
    ),
    "fact_evidence": SectionHelp(
        "Relaciona hechos y pruebas e indica la finalidad probatoria.",
        (
            "Selecciona un hecho registrado.",
            "Selecciona la prueba relacionada.",
            "Explica qué pretende acreditar, controvertir o contextualizar.",
        ),
        "Relación trazable hecho-prueba.",
        "Un vínculo no equivale a tener por acreditado el hecho.",
    ),
    "issues": SectionHelp(
        "Formula y delimita las preguntas jurídicas del expediente.",
        (
            "Identifica la controversia jurídica concreta.",
            "Formula una pregunta verificable y delimitada.",
            "Añade contexto y estado del problema.",
        ),
        "Problema disponible para asociar fuentes y razonamiento.",
        "Evita preguntas excesivamente amplias o conclusiones disfrazadas de pregunta.",
    ),
    "norms": SectionHelp(
        "Registra normas, disposiciones, texto, jerarquía y vigencia.",
        (
            "Registra la disposición exacta y el texto relevante.",
            "Documenta publicación, vigencia, versión y fuente.",
            "Añade notas sobre aplicabilidad.",
        ),
        "Norma disponible para la matriz problema-fuente.",
        "Vigencia y aplicabilidad requieren verificación profesional.",
    ),
    "jurisprudence": SectionHelp(
        "Registra precedentes y su comparación con el expediente.",
        (
            "Registra órgano, identificador, fecha y materia.",
            "Sintetiza hechos relevantes, problema y criterio.",
            "Documenta similitudes, diferencias y fuente.",
        ),
        "Precedente disponible como fuente trazable.",
        "Verifica autenticidad, vigencia, obligatoriedad y contexto.",
    ),
    "doctrine": SectionHelp(
        "Registra doctrina, posición y función argumentativa.",
        (
            "Identifica autor, obra, edición y concepto.",
            "Resume la posición sin sustituir la fuente original.",
            "Documenta cita, ubicación y función argumentativa.",
        ),
        "Doctrina disponible para relacionarse con problemas.",
        "Distingue cita, paráfrasis y síntesis propia.",
    ),
    "source_matrix": SectionHelp(
        "Relaciona problemas jurídicos con normas, jurisprudencia y doctrina.",
        (
            "Selecciona el problema jurídico.",
            "Selecciona una fuente registrada.",
            "Indica orientación y explica su aplicabilidad.",
        ),
        "Matriz trazable problema-fuente.",
        "La relación expresa una evaluación del usuario, no una validación automática.",
    ),
    "assertions": SectionHelp(
        "Define las premisas explícitas del motor de razonamiento.",
        (
            "Selecciona el problema correspondiente.",
            "Define clave lógica y enunciado.",
            "Asigna valor, justificación y códigos de soporte.",
        ),
        "Premisa disponible para las condiciones de las reglas.",
        "Una premisa incorrecta puede producir conclusiones materialmente erróneas.",
    ),
    "rules": SectionHelp(
        "Modela reglas de inferencia con condiciones, prioridad y conclusión.",
        (
            "Define conclusión y valor.",
            "Registra prerrequisitos y excepciones cuando procedan.",
            "Asocia fundamentos jurídicos y explicación.",
        ),
        "Regla disponible para ejecutar el motor.",
        "Las reglas no se validan jurídicamente de forma automática.",
    ),
    "inference": SectionHelp(
        "Ejecuta el razonamiento y muestra conclusiones y trazabilidad.",
        (
            "Selecciona un problema con premisas y reglas activas.",
            "Ejecuta el razonamiento.",
            "Revisa conclusiones, conflictos y traza antes de usar el resultado.",
        ),
        "Ejecución reproducible con huella y trazabilidad.",
        "El resultado depende de las entradas y reglas registradas.",
    ),
    "reasoning_management": SectionHelp(
        "Administra premisas y reglas conservando versiones e historial.",
        (
            "Selecciona la premisa o regla a corregir.",
            "Modifica solo lo necesario.",
            "Revisa el historial después de guardar.",
        ),
        "Modificaciones versionadas y auditables.",
        "Las eliminaciones pueden bloquearse cuando existen dependencias.",
    ),
    "safe_correction": SectionHelp(
        "Corrige problemas, fuentes y vínculos con controles de integridad.",
        (
            "Selecciona el tipo de registro.",
            "Edita conservando identidad y código.",
            "Confirma exactamente el código para eliminar.",
        ),
        "Corrección trazable y controlada.",
        "Revisa vínculos antes de eliminar registros.",
    ),
    "argumentation": SectionHelp(
        "Construye argumentos, relaciones y escenarios.",
        (
            "Selecciona el problema jurídico.",
            "Crea argumentos trazables o manuales.",
            "Relaciona apoyos, ataques y respuestas y revisa el grafo.",
        ),
        "Red argumental trazable y comparable.",
        "La fuerza jurídica del argumento requiere revisión humana.",
    ),
    "integral_report": SectionHelp(
        "Integra expediente, fuentes, razonamiento y argumentación.",
        (
            "Selecciona problema y escenarios cuando proceda.",
            "Genera el informe y revisa hallazgos y limitaciones.",
            "Exporta solo después de revisar privacidad y contenido.",
        ),
        "Informe reproducible en los formatos disponibles.",
        "El informe no constituye dictamen ni asesoría jurídica.",
    ),
    "assistant": SectionHelp(
        "Asiste en la elaboración de borradores controlados.",
        (
            "Selecciona el contexto necesario.",
            "Genera el borrador y revisa la trazabilidad.",
            "Corrige y valida todo contenido antes de utilizarlo.",
        ),
        "Borrador asistido sujeto a revisión humana.",
        "No aceptes afirmaciones, citas ni conclusiones sin verificación.",
    ),
    "privacy": SectionHelp(
        "Analiza riesgos de privacidad antes de compartir información.",
        (
            "Ejecuta el análisis de privacidad.",
            "Revisa y corrige los hallazgos.",
            "Confirma la política antes de exportar.",
        ),
        "Diagnóstico de privacidad del expediente.",
        "El escáner reduce riesgos, pero no sustituye revisión de protección de datos.",
    ),
}

WORKFLOW: tuple[str, ...] = (
    "Crear o seleccionar un expediente.",
    "Registrar partes y hechos.",
    "Registrar pruebas y relacionarlas con los hechos.",
    "Delimitar problemas jurídicos.",
    "Registrar normas, jurisprudencia y doctrina.",
    "Relacionar problemas con fuentes jurídicas.",
    "Definir premisas y reglas.",
    "Ejecutar la inferencia y revisar su trazabilidad.",
    "Construir la argumentación y sus escenarios.",
    "Generar el informe integral y revisar privacidad antes de exportar.",
)


def render_section_help(page_id: str) -> None:
    """Muestra ayuda breve y contextual para la sección activa."""

    item = SECTION_HELP.get(page_id)
    if item is None:
        return

    with st.expander("ⓘ ¿Cómo utilizar esta sección?", expanded=False):
        st.write(item.purpose)
        st.markdown("**Uso recomendado**")
        for index, step in enumerate(item.steps, start=1):
            st.write(f"{index}. {step}")
        st.markdown(f"**Resultado esperado:** {item.result}")
        st.markdown(f"**Precaución:** {item.caution}")


def render_user_manual() -> None:
    """Renderiza el manual funcional de IUS-Razón."""

    st.title("Manual de usuario")
    st.write(
        "El manual explica el flujo funcional de IUS-Razón y el propósito "
        "de cada área de trabajo."
    )

    st.markdown("## Flujo recomendado")
    for index, step in enumerate(WORKFLOW, start=1):
        st.write(f"{index}. {step}")

    st.markdown("## Creación y selección de expedientes")
    st.write(
        "El expediente es el contenedor principal. Antes de registrar hechos, "
        "pruebas, fuentes o razonamiento, crea un expediente y selecciónalo "
        "como expediente activo."
    )

    st.markdown("## Funcionalidades")
    for group in navigation_groups():
        st.markdown(f"### {group}")
        for nav_item in navigation_items_for_group(group):
            help_item = SECTION_HELP[nav_item.page_id]
            with st.expander(
                f"{nav_item.label} · {nav_item.description}",
                expanded=False,
            ):
                st.write(help_item.purpose)
                st.markdown("**Uso recomendado**")
                for index, step in enumerate(help_item.steps, start=1):
                    st.write(f"{index}. {step}")
                st.markdown(f"**Resultado esperado:** {help_item.result}")
                st.markdown(f"**Precaución:** {help_item.caution}")

    st.warning(
        "IUS-Razón es un prototipo académico. No constituye asesoría jurídica, "
        "dictamen ni predicción judicial. Toda fuente, vigencia, aplicabilidad "
        "y conclusión debe ser verificada por una persona profesional del Derecho."
    )
