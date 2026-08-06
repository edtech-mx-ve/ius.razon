from __future__ import annotations

import streamlit as st

from ius_razon.domain.llm_models import (
    AssistantRequest,
    AssistantTask,
    ContextCategory,
    DraftStatus,
)
from ius_razon.services.case_service import CaseService
from ius_razon.services.llm_assistant_service import LLMAssistantService
from ius_razon.services.reasoning_service import ReasoningService


def render_llm_assistant(
    case_id: str,
    *,
    case_service: CaseService,
    reasoning_service: ReasoningService,
    assistant_service: LLMAssistantService,
) -> None:
    """Renderiza generación asistiva, evaluación y revisión humana."""

    st.subheader("Asistente IA controlado")
    st.warning(
        "Modo simulado local: no se realizan llamadas externas ni se usan claves API. "
        "El borrador no modifica hechos, fuentes, conclusiones ni argumentos."
    )
    st.caption(
        f"Proveedor: {assistant_service.provider_name} · "
        f"Modelo: {assistant_service.model_name}"
    )

    issues = case_service.list_legal_issues(case_id)
    if not issues:
        st.info("Primero registra un problema jurídico.")
        return

    issue_labels = {
        f"{issue.code} · {issue.title}": issue.id
        for issue in issues
    }
    issue_label = st.selectbox(
        "Problema jurídico",
        list(issue_labels),
        key=f"llm_issue_{case_id}",
    )
    issue_id = issue_labels[issue_label]

    runs = [
        run
        for run in reasoning_service.list_runs(case_id, issue_id, limit=50)
        if run.status.value == "Completada"
    ]
    run_labels: dict[str, str | None] = {"Sin ejecución de inferencia": None}
    run_labels.update(
        {
            (
                f"{run.started_at.isoformat()} · {run.id[:8]} · "
                f"{run.summary.get('conclusion_count', 0)} conclusiones"
            ): run.id
            for run in runs
        }
    )
    run_label = st.selectbox(
        "Ejecución para incluir conclusiones",
        list(run_labels),
        key=f"llm_run_{case_id}_{issue_id}",
    )
    run_id = run_labels[run_label]

    all_categories = list(ContextCategory)
    default_categories = [
        category
        for category in all_categories
        if category is not ContextCategory.CONCLUSION or run_id is not None
    ]
    selected_values = st.multiselect(
        "Categorías permitidas",
        options=[category.value for category in all_categories],
        default=[category.value for category in default_categories],
        key=f"llm_categories_{case_id}_{issue_id}",
    )
    selected_categories = [
        ContextCategory(value)
        for value in selected_values
    ]
    if not selected_categories:
        st.info("Selecciona al menos una categoría.")
        return

    try:
        available_items = assistant_service.list_context_items(
            case_id,
            issue_id,
            run_id,
        )
    except Exception as exc:
        st.error(f"No fue posible preparar el contexto: {exc}")
        return

    filtered_items = [
        item
        for item in available_items
        if item.category in selected_categories
    ]
    item_labels = {
        f"[{item.code}] {item.category.value} · {item.title}": item.code
        for item in filtered_items
    }
    selected_item_labels = st.multiselect(
        "Elementos exactos que puede usar el asistente",
        options=list(item_labels),
        default=list(item_labels),
        key=f"llm_items_{case_id}_{issue_id}_{run_id}",
    )
    selected_codes = [
        item_labels[label]
        for label in selected_item_labels
    ]
    if not selected_codes:
        st.info("Selecciona al menos un elemento de contexto.")
        return

    with st.form(f"llm_generate_{case_id}_{issue_id}"):
        task_value = st.selectbox(
            "Tarea",
            options=[task.value for task in AssistantTask],
        )
        instructions = st.text_area(
            "Indicación adicional opcional",
            placeholder=(
                "Ejemplo: prioriza la relación entre el pago, el vencimiento "
                "y la conclusión provisional."
            ),
            max_chars=3000,
        )
        controls = st.columns(3)
        anonymize = controls[0].checkbox(
            "Anonimizar partes",
            value=True,
            help="Sustituye alias de las partes antes de construir el contexto.",
        )
        max_context = controls[1].number_input(
            "Máximo de contexto",
            min_value=1000,
            max_value=50000,
            value=12000,
            step=1000,
        )
        max_output = controls[2].number_input(
            "Máximo de salida",
            min_value=500,
            max_value=20000,
            value=8000,
            step=500,
        )
        submitted = st.form_submit_button(
            "Generar borrador controlado",
            type="primary",
        )

    state_key = f"llm_current_draft_{case_id}_{issue_id}"
    if submitted:
        try:
            request = AssistantRequest(
                case_id=case_id,
                issue_id=issue_id,
                reasoning_run_id=run_id,
                task=AssistantTask(task_value),
                instructions=instructions or None,
                selected_categories=selected_categories,
                selected_codes=selected_codes,
                anonymize_parties=anonymize,
                max_context_chars=int(max_context),
                max_output_chars=int(max_output),
            )
            preview = assistant_service.preview_context(request)
            record = assistant_service.generate_draft(request)
            st.session_state[state_key] = record.id
            st.success(
                f"Borrador {record.code} generado. "
                f"Cobertura de citas: {record.citation_coverage:.0%}."
            )
            if preview.risk_flags:
                st.warning(
                    "Se detectaron señales de instrucciones incrustadas; "
                    "se trataron únicamente como datos."
                )
        except Exception as exc:
            st.error(f"No fue posible generar el borrador: {exc}")

    draft_id = st.session_state.get(state_key)
    if isinstance(draft_id, str):
        _render_current_draft(
            draft_id,
            case_id=case_id,
            issue_id=issue_id,
            assistant_service=assistant_service,
        )

    _render_history(
        case_id,
        issue_id=issue_id,
        assistant_service=assistant_service,
    )


def _render_current_draft(
    draft_id: str,
    *,
    case_id: str,
    issue_id: str,
    assistant_service: LLMAssistantService,
) -> None:
    """Muestra evaluación y controles de revisión del borrador actual."""

    try:
        record = assistant_service.get_draft(draft_id)
    except Exception as exc:
        st.error(f"No fue posible recuperar el borrador: {exc}")
        return

    st.markdown("### Borrador actual")
    metrics = st.columns(4)
    metrics[0].metric("Código", record.code)
    metrics[1].metric("Estado", record.status.value)
    metrics[2].metric("Cobertura", f"{record.citation_coverage:.0%}")
    metrics[3].metric("Referencias", len(record.reference_codes))
    st.caption(
        f"Entrada {record.input_hash[:16]}… · "
        f"salida {record.output_hash[:16]}…"
    )

    if record.risk_flags:
        with st.expander("Señales de riesgo detectadas", expanded=True):
            for flag in record.risk_flags:
                st.write(f"- {flag}")
    if record.invalid_reference_codes:
        st.error(
            "Referencias no permitidas: "
            + ", ".join(record.invalid_reference_codes)
        )
    if record.unsupported_claims:
        with st.expander(
            "Afirmaciones sin cita interna",
            expanded=True,
        ):
            for claim in record.unsupported_claims:
                st.write(f"- {claim}")

    st.markdown(record.response_text)

    if record.status is not DraftStatus.GENERATED:
        st.info(
            f"Revisión finalizada: {record.status.value}. "
            "El texto original permanece conservado."
        )
        if record.edited_text:
            with st.expander("Texto final aprobado", expanded=True):
                st.markdown(record.edited_text)
        return

    edited_text = st.text_area(
        "Texto revisado por una persona",
        value=record.response_text,
        height=320,
        key=f"llm_edit_{record.id}",
    )
    reviewer_note = st.text_area(
        "Nota de revisión opcional",
        max_chars=2000,
        key=f"llm_note_{record.id}",
    )
    actions = st.columns(2)
    if actions[0].button(
        "Aprobar versión revisada",
        type="primary",
        key=f"llm_approve_{record.id}",
    ):
        try:
            reviewed = assistant_service.approve_draft(
                record.id,
                edited_text=edited_text,
                reviewer_note=reviewer_note or None,
            )
            st.success(f"{reviewed.code} aprobado y guardado.")
            st.rerun()
        except Exception as exc:
            st.error(f"No fue posible aprobar: {exc}")

    if actions[1].button(
        "Rechazar borrador",
        key=f"llm_reject_{record.id}",
    ):
        try:
            reviewed = assistant_service.reject_draft(
                record.id,
                reviewer_note=reviewer_note or None,
            )
            st.info(f"{reviewed.code} rechazado.")
            st.rerun()
        except Exception as exc:
            st.error(f"No fue posible rechazar: {exc}")


def _render_history(
    case_id: str,
    *,
    issue_id: str,
    assistant_service: LLMAssistantService,
) -> None:
    """Presenta historial de borradores sin mostrar contenido sensible en logs."""

    records = assistant_service.list_drafts(
        case_id,
        issue_id,
        limit=30,
    )
    with st.expander("Historial asistivo", expanded=False):
        if not records:
            st.caption("Aún no existen borradores para este problema.")
            return
        st.dataframe(
            [
                {
                    "Código": record.code,
                    "Tarea": record.task.value,
                    "Estado": record.status.value,
                    "Proveedor": record.provider_name,
                    "Modelo": record.model_name,
                    "Cobertura": f"{record.citation_coverage:.0%}",
                    "Creado": record.created_at.isoformat(),
                    "Revisado": (
                        record.reviewed_at.isoformat()
                        if record.reviewed_at
                        else ""
                    ),
                }
                for record in records
            ],
            use_container_width=True,
            hide_index=True,
        )
