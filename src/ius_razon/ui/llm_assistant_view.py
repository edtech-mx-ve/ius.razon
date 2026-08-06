from __future__ import annotations

from typing import cast

import streamlit as st

from ius_razon.domain.llm_models import (
    AssistantRequest,
    AssistantTask,
    ContextCategory,
    DraftStatus,
    ExternalConsent,
    ProviderMode,
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
    """Renderiza generación asistiva, consentimiento y revisión humana."""

    st.subheader("Asistente IA controlado")
    st.caption(
        "Los borradores no modifican hechos, fuentes, conclusiones ni argumentos. "
        "Toda salida requiere revisión humana antes de aprobarse."
    )

    if assistant_service.external_configuration_error:
        st.error(
            "Configuración externa inválida: "
            + assistant_service.external_configuration_error
        )

    if assistant_service.openai_configuration_error:
        st.error(
            "Configuración de OpenAI inválida: "
            + assistant_service.openai_configuration_error
        )

    provider_options = [ProviderMode.SIMULATED]
    if assistant_service.integration_test_available:
        provider_options.append(ProviderMode.EXTERNAL_TEST)
    if assistant_service.openai_available:
        provider_options.append(ProviderMode.OPENAI)
    if assistant_service.external_available:
        provider_options.append(ProviderMode.EXTERNAL)

    provider_value = st.selectbox(
        "Proveedor",
        options=[mode.value for mode in provider_options],
        key=f"llm_provider_{case_id}",
    )
    provider_mode = ProviderMode(provider_value)
    controlled_mode = provider_mode in {
        ProviderMode.EXTERNAL_TEST,
        ProviderMode.OPENAI,
        ProviderMode.EXTERNAL,
    }

    if provider_mode is ProviderMode.SIMULATED:
        st.info(
            "Modo simulado local: no se realizan llamadas externas ni se usan claves API."
        )
        st.caption(
            f"Proveedor: {assistant_service.provider_name} · "
            f"Modelo: {assistant_service.model_name}"
        )
    elif provider_mode is ProviderMode.EXTERNAL_TEST:
        summary = assistant_service.integration_test_safe_summary
        st.info(
            "Prueba externa controlada: ejercita consentimiento, límites y auditoría "
            "con un proveedor falso local. No usa red ni clave API."
        )
        st.caption(
            f"Proveedor: {summary.get('provider_name', '')} · "
            f"Modelo: {summary.get('model', '')} · "
            "Red: desactivada"
        )
    elif provider_mode is ProviderMode.OPENAI:
        summary = assistant_service.openai_safe_summary
        st.warning(
            "OpenAI real: se enviará únicamente el contexto anonimizado y "
            "seleccionado después de cuatro confirmaciones."
        )
        st.caption(
            f"Proveedor: OpenAI Responses API · "
            f"Modelo: {summary.get('model', '')} · "
            f"Host: {summary.get('endpoint_host', '')} · "
            "Almacenamiento solicitado: desactivado"
        )
    else:
        summary = assistant_service.external_safe_summary
        st.warning(
            "Modo externo real: el contexto anonimizado seleccionado será enviado "
            "fuera del equipo únicamente después de tres confirmaciones."
        )
        st.caption(
            f"Modelo: {summary.get('model', '')} · "
            f"Host: {summary.get('endpoint_host', '')} · "
            "Clave configurada: sí"
        )

    if not assistant_service.openai_available:
        st.caption(
            "OpenAI está desactivado. Configúralo únicamente después de validar "
            "el adaptador y las tarifas."
        )
    if not assistant_service.external_available:
        st.caption(
            "El proveedor externo genérico está desactivado. "
            "Los modos locales siguen disponibles."
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

    task_value = st.selectbox(
        "Tarea",
        options=[task.value for task in AssistantTask],
        key=f"llm_task_{case_id}_{issue_id}",
    )
    instructions = st.text_area(
        "Indicación adicional opcional",
        placeholder=(
            "Ejemplo: prioriza la relación entre el pago, el vencimiento "
            "y la conclusión provisional."
        ),
        max_chars=3000,
        key=f"llm_instructions_{case_id}_{issue_id}",
    )

    controls = st.columns(3)
    anonymize = controls[0].checkbox(
        "Anonimizar partes",
        value=True,
        disabled=controlled_mode,
        help="Los modos controlados y externos exigen anonimización.",
        key=f"llm_anonymize_{case_id}_{issue_id}_{provider_mode.value}",
    )
    max_context = controls[1].number_input(
        "Máximo de contexto",
        min_value=1000,
        max_value=50000,
        value=12000,
        step=1000,
        key=f"llm_context_{case_id}_{issue_id}",
    )
    max_output_chars = controls[2].number_input(
        "Máximo de salida en caracteres",
        min_value=500,
        max_value=20000,
        value=8000,
        step=500,
        key=f"llm_output_chars_{case_id}_{issue_id}",
    )

    max_input_tokens = 16000
    max_output_tokens = 2000
    max_cost_usd = 0.10
    timeout_seconds = 30
    max_retries = 1
    allow_fallback = True
    reviewed_context = False
    authorized_external = False
    accepted_cost = False
    acknowledge_risks = False
    confirm_single_call = False

    if provider_mode is ProviderMode.EXTERNAL_TEST:
        profile = assistant_service.integration_test_safe_summary
        max_input_tokens = cast(int, profile.get("max_input_tokens", 2048))
        max_output_tokens = cast(int, profile.get("max_output_tokens", 256))
        max_cost_usd = cast(float, profile.get("max_cost_usd", 0.01))
        timeout_seconds = cast(int, profile.get("timeout_seconds", 15))
        max_retries = cast(int, profile.get("max_retries", 0))
        allow_fallback = cast(bool, profile.get("fallback_required", True))
        st.markdown("### Perfil fijo de prueba")
        profile_metrics = st.columns(5)
        profile_metrics[0].metric("Entrada", f"{max_input_tokens} tokens")
        profile_metrics[1].metric("Salida", f"{max_output_tokens} tokens")
        profile_metrics[2].metric("Costo máximo", f"USD {max_cost_usd:.4f}")
        profile_metrics[3].metric("Tiempo", f"{timeout_seconds} s")
        profile_metrics[4].metric("Reintentos", max_retries)
        st.caption(
            "Fallback local obligatorio · una sola invocación · sin red · sin clave API"
        )
    elif provider_mode is ProviderMode.OPENAI:
        profile = assistant_service.openai_safe_summary
        max_input_tokens = cast(int, profile.get("max_input_tokens", 2048))
        max_output_tokens = cast(int, profile.get("max_output_tokens", 256))
        max_cost_usd = cast(float, profile.get("max_cost_usd", 0.02))
        timeout_seconds = cast(int, profile.get("timeout_seconds", 20))
        max_retries = 0
        allow_fallback = True
        st.markdown("### Perfil fijo de primera llamada OpenAI")
        profile_metrics = st.columns(5)
        profile_metrics[0].metric("Entrada", f"{max_input_tokens} tokens")
        profile_metrics[1].metric("Salida", f"{max_output_tokens} tokens")
        profile_metrics[2].metric("Costo máximo", f"USD {max_cost_usd:.4f}")
        profile_metrics[3].metric("Tiempo", f"{timeout_seconds} s")
        profile_metrics[4].metric("Reintentos", max_retries)
        st.caption(
            "Fallback local obligatorio · una sola llamada · store=false · "
            "sin herramientas externas"
        )
    elif provider_mode is ProviderMode.EXTERNAL:
        limits = st.columns(3)
        max_input_tokens = int(
            limits[0].number_input(
                "Máximo de tokens de entrada",
                min_value=256,
                max_value=200000,
                value=16000,
                step=256,
            )
        )
        max_output_tokens = int(
            limits[1].number_input(
                "Máximo de tokens de salida",
                min_value=64,
                max_value=32000,
                value=2000,
                step=64,
            )
        )
        max_cost_usd = float(
            limits[2].number_input(
                "Presupuesto máximo USD",
                min_value=0.0,
                max_value=100.0,
                value=0.10,
                step=0.01,
                format="%.4f",
            )
        )
        execution = st.columns(3)
        timeout_seconds = int(
            execution[0].number_input(
                "Tiempo máximo en segundos",
                min_value=5,
                max_value=180,
                value=30,
                step=5,
            )
        )
        max_retries = int(
            execution[1].number_input(
                "Reintentos máximos",
                min_value=0,
                max_value=3,
                value=1,
                step=1,
            )
        )
        allow_fallback = execution[2].checkbox(
            "Fallback al modo local",
            value=True,
        )

    consent = (
        ExternalConsent(
            reviewed_context=reviewed_context,
            authorized_external_call=authorized_external,
            accepted_cost_limit=accepted_cost,
        )
        if controlled_mode
        else None
    )

    preview_request = AssistantRequest(
        case_id=case_id,
        issue_id=issue_id,
        reasoning_run_id=run_id,
        task=AssistantTask(task_value),
        instructions=instructions or None,
        selected_categories=selected_categories,
        selected_codes=selected_codes,
        anonymize_parties=True if controlled_mode else anonymize,
        max_context_chars=int(max_context),
        max_output_chars=int(max_output_chars),
        provider_mode=provider_mode,
        external_consent=consent,
        acknowledge_risk_flags=acknowledge_risks,
        max_input_tokens=max_input_tokens,
        max_output_tokens=max_output_tokens,
        max_cost_usd=max_cost_usd,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        allow_fallback=allow_fallback,
        confirm_single_call=confirm_single_call,
    )

    try:
        preview = assistant_service.preview_context(preview_request)
    except Exception as exc:
        st.error(f"No fue posible generar la vista previa: {exc}")
        return

    if controlled_mode:
        if provider_mode is ProviderMode.EXTERNAL_TEST:
            title = "### Vista previa de la prueba controlada"
        elif provider_mode is ProviderMode.OPENAI:
            title = "### Vista previa de la única llamada OpenAI"
        else:
            title = "### Vista previa del envío externo"
        st.markdown(title)
        metrics = st.columns(4)
        metrics[0].metric("Elementos", len(preview.items))
        metrics[1].metric("Caracteres", preview.char_count)
        metrics[2].metric(
            "Tokens estimados",
            preview.estimated_input_tokens,
        )
        metrics[3].metric(
            "Costo máximo estimado",
            f"USD {preview.estimated_max_cost_usd:.6f}",
        )
        st.caption(
            "Códigos autorizados: "
            + ", ".join(item.code for item in preview.items)
        )
        if preview.risk_flags:
            st.warning(
                "Se detectaron señales de instrucciones incrustadas en el contexto."
            )
            for flag in preview.risk_flags:
                st.write(f"- {flag}")
            acknowledge_risks = st.checkbox(
                "Revisé las señales y autorizo tratarlas únicamente como datos",
                value=False,
            )

        reviewed_context = st.checkbox(
            "Confirmo que revisé el contexto y los códigos seleccionados",
            value=False,
        )
        authorized_external = st.checkbox(
            (
                "Autorizo esta prueba específica sin red"
                if provider_mode is ProviderMode.EXTERNAL_TEST
                else (
                    "Autorizo una única llamada real a OpenAI"
                    if provider_mode is ProviderMode.OPENAI
                    else "Autorizo esta llamada externa específica"
                )
            ),
            value=False,
        )
        accepted_cost = st.checkbox(
            "Acepto el límite de costo mostrado",
            value=False,
        )
        if provider_mode in {
            ProviderMode.EXTERNAL_TEST,
            ProviderMode.OPENAI,
        }:
            confirm_single_call = st.checkbox(
                (
                    "Confirmo una sola invocación de prueba y cero reintentos"
                    if provider_mode is ProviderMode.EXTERNAL_TEST
                    else "Confirmo una sola llamada real a OpenAI y cero reintentos"
                ),
                value=False,
            )
        consent = ExternalConsent(
            reviewed_context=reviewed_context,
            authorized_external_call=authorized_external,
            accepted_cost_limit=accepted_cost,
        )

    request = preview_request.model_copy(
        update={
            "external_consent": consent,
            "acknowledge_risk_flags": acknowledge_risks,
            "confirm_single_call": confirm_single_call,
        }
    )

    if provider_mode is ProviderMode.EXTERNAL_TEST:
        button_label = "Ejecutar prueba externa controlada"
    elif provider_mode is ProviderMode.OPENAI:
        button_label = "Ejecutar única llamada OpenAI"
    else:
        button_label = "Generar borrador controlado"
    submitted = st.button(
        button_label,
        type="primary",
        key=f"llm_generate_{case_id}_{issue_id}_{provider_mode.value}",
    )

    state_key = f"llm_current_draft_{case_id}_{issue_id}"
    if submitted:
        try:
            record = assistant_service.generate_draft(request)
            st.session_state[state_key] = record.id
            st.success(
                f"Borrador {record.code} generado. "
                f"Cobertura de citas: {record.citation_coverage:.0%}."
            )
            if record.fallback_used:
                st.warning(
                    "El proveedor seleccionado falló y se utilizó el proveedor local."
                )
        except Exception as exc:
            st.error(f"No fue posible generar el borrador: {exc}")

    draft_id = st.session_state.get(state_key)
    if isinstance(draft_id, str):
        _render_current_draft(
            draft_id,
            assistant_service=assistant_service,
        )

    _render_history(
        case_id,
        issue_id=issue_id,
        assistant_service=assistant_service,
    )
    _render_audit(
        case_id,
        issue_id=issue_id,
        assistant_service=assistant_service,
    )


def _render_current_draft(
    draft_id: str,
    *,
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
        f"Modo: {record.provider_mode.value} · "
        f"Proveedor: {record.provider_name} · Modelo: {record.model_name}"
    )
    st.caption(
        f"Entrada {record.input_hash[:16]}… · "
        f"salida {record.output_hash[:16]}…"
    )
    if record.external_call:
        st.caption(
            f"Tokens reportados: entrada {record.input_tokens or 0}, "
            f"salida {record.output_tokens or 0} · "
            f"Costo estimado: USD {record.estimated_cost_usd or 0.0:.6f}"
        )
    if record.fallback_used:
        st.warning(
            "Fallback local utilizado. Motivo técnico: "
            + (record.fallback_reason or "no disponible")
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
    """Presenta historial de borradores sin mostrar contenido sensible."""

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
                    "Modo": record.provider_mode.value,
                    "Proveedor": record.provider_name,
                    "Modelo": record.model_name,
                    "Fallback": "Sí" if record.fallback_used else "No",
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


def _render_audit(
    case_id: str,
    *,
    issue_id: str,
    assistant_service: LLMAssistantService,
) -> None:
    """Presenta metadatos de auditoría sin prompts ni secretos."""

    calls = assistant_service.list_provider_calls(
        case_id,
        issue_id,
        limit=30,
    )
    with st.expander("Auditoría de proveedores", expanded=False):
        if not calls:
            st.caption("Aún no existen llamadas auditadas.")
            return
        st.dataframe(
            [
                {
                    "Fecha": call.created_at.isoformat(),
                    "Modo": call.provider_mode.value,
                    "Proveedor": call.provider_name,
                    "Modelo": call.model_name,
                    "Estado": call.status.value,
                    "Elementos": len(call.selected_codes),
                    "Externa": "Sí" if call.external_call else "No",
                    "Fallback": "Sí" if call.fallback_used else "No",
                    "Entrada": call.input_tokens or "",
                    "Salida": call.output_tokens or "",
                    "Costo USD": (
                        f"{call.estimated_cost_usd:.6f}"
                        if call.estimated_cost_usd is not None
                        else ""
                    ),
                    "Error": call.error_code or "",
                }
                for call in calls
            ],
            use_container_width=True,
            hide_index=True,
        )
