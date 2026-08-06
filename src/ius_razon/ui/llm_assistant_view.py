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

    if assistant_service.ollama_configuration_error:
        st.error(
            "Configuración local de Ollama inválida: "
            + assistant_service.ollama_configuration_error
        )

    provider_options = [ProviderMode.SIMULATED]
    if assistant_service.ollama_available:
        provider_options.append(ProviderMode.OLLAMA)
    if assistant_service.integration_test_available:
        provider_options.append(ProviderMode.EXTERNAL_TEST)

    provider_value = st.selectbox(
        "Proveedor",
        options=[mode.value for mode in provider_options],
        key=f"llm_provider_{case_id}",
    )
    provider_mode = ProviderMode(provider_value)
    controlled_mode = provider_mode is ProviderMode.EXTERNAL_TEST
    local_llm_mode = provider_mode is ProviderMode.OLLAMA
    anonymization_required = controlled_mode or local_llm_mode
    preview_required = controlled_mode or local_llm_mode

    if provider_mode is ProviderMode.SIMULATED:
        st.info(
            "Modo simulado local: no se realizan llamadas externas ni se usan claves API."
        )
        st.caption(
            f"Proveedor: {assistant_service.provider_name} · "
            f"Modelo: {assistant_service.model_name}"
        )
    elif provider_mode is ProviderMode.OLLAMA:
        summary = assistant_service.ollama_safe_summary
        st.success(
            "Ollama local gratuito: el modelo se ejecuta en este equipo, "
            "sin clave API y sin enviar el expediente a Internet."
        )
        st.caption(
            f"Proveedor: {summary.get('provider_name', '')} · "
            f"Modelo: {summary.get('model', '')} · "
            f"Endpoint: {summary.get('endpoint', '')} · "
            "Costo por solicitud: USD 0"
        )
        _render_ollama_diagnostics(
            case_id,
            assistant_service=assistant_service,
        )
    else:
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

    if not assistant_service.ollama_available:
        st.caption(
            "Ollama local está desactivado por configuración. "
            "El modo simulado continúa disponible."
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
        disabled=anonymization_required,
        help="Ollama local y la prueba controlada exigen anonimización.",
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

    if provider_mode is ProviderMode.OLLAMA:
        profile = assistant_service.ollama_safe_summary
        max_input_tokens = cast(int, profile.get("max_input_tokens", 3072))
        max_output_tokens = cast(int, profile.get("max_output_tokens", 512))
        max_cost_usd = 0.0
        timeout_seconds = cast(int, profile.get("timeout_seconds", 120))
        max_retries = 0
        allow_fallback = True
        st.markdown("### Perfil local gratuito")
        profile_metrics = st.columns(5)
        profile_metrics[0].metric("Entrada", f"{max_input_tokens} tokens")
        profile_metrics[1].metric("Salida", f"{max_output_tokens} tokens")
        profile_metrics[2].metric("Costo", "USD 0")
        profile_metrics[3].metric("Tiempo", f"{timeout_seconds} s")
        profile_metrics[4].metric("Reintentos", max_retries)
        st.caption(
            "Solo loopback local · think=false · sin clave API · "
            "fallback simulado disponible"
        )
    elif provider_mode is ProviderMode.EXTERNAL_TEST:
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
        anonymize_parties=True if anonymization_required else anonymize,
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

    if preview_required:
        if provider_mode is ProviderMode.OLLAMA:
            title = "### Vista previa de la generación local"
        else:
            title = "### Vista previa de la prueba controlada"
        st.markdown(title)
        metrics = st.columns(4)
        metrics[0].metric("Elementos", len(preview.items))
        metrics[1].metric("Caracteres", preview.char_count)
        metrics[2].metric(
            "Tokens estimados",
            preview.estimated_input_tokens,
        )
        metrics[3].metric(
            "Costo estimado",
            "USD 0" if provider_mode is ProviderMode.OLLAMA else (
                f"USD {preview.estimated_max_cost_usd:.6f}"
            ),
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

        if provider_mode is ProviderMode.EXTERNAL_TEST:
            reviewed_context = st.checkbox(
                "Confirmo que revisé el contexto y los códigos seleccionados",
                value=False,
            )
            authorized_external = st.checkbox(
                "Autorizo esta prueba específica sin red",
                value=False,
            )
            accepted_cost = st.checkbox(
                "Acepto el límite de costo mostrado",
                value=False,
            )
            confirm_single_call = st.checkbox(
                "Confirmo una sola invocación de prueba y cero reintentos",
                value=False,
            )
            consent = ExternalConsent(
                reviewed_context=reviewed_context,
                authorized_external_call=authorized_external,
                accepted_cost_limit=accepted_cost,
            )
        else:
            st.caption(
                "La generación usa únicamente el servicio local de Ollama. "
                "No se solicita consentimiento de envío externo porque no hay salida del equipo."
            )

    request = preview_request.model_copy(
        update={
            "external_consent": consent,
            "acknowledge_risk_flags": acknowledge_risks,
            "confirm_single_call": confirm_single_call,
        }
    )

    if provider_mode is ProviderMode.OLLAMA:
        button_label = "Generar con Ollama local"
    elif provider_mode is ProviderMode.EXTERNAL_TEST:
        button_label = "Ejecutar prueba externa controlada"
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


def _render_ollama_diagnostics(
    case_id: str,
    *,
    assistant_service: LLMAssistantService,
) -> None:
    """Muestra disponibilidad, versión y modelo sin enviar datos jurídicos."""

    state_key = f"ollama_health_summary_{case_id}"
    refresh = st.button(
        "Actualizar diagnóstico de Ollama",
        key=f"ollama_health_refresh_{case_id}",
    )
    if refresh or state_key not in st.session_state:
        report = assistant_service.check_ollama_health()
        st.session_state[state_key] = report.safe_summary()

    raw_summary = st.session_state.get(state_key, {})
    summary = (
        cast(dict[str, object], raw_summary)
        if isinstance(raw_summary, dict)
        else {}
    )
    ready = bool(summary.get("ready", False))
    message = str(summary.get("message", "Diagnóstico no disponible."))
    if ready:
        st.success(message)
    else:
        st.warning(
            message
            + " Si se genera un borrador, se conservará el fallback local controlado."
        )

    metrics = st.columns(4)
    metrics[0].metric(
        "Servicio",
        "Disponible"
        if bool(summary.get("service_available", False))
        else "No disponible",
    )
    metrics[1].metric(
        "Modelo",
        "Instalado"
        if bool(summary.get("model_installed", False))
        else "No verificado",
    )
    metrics[2].metric(
        "Versión",
        str(summary.get("version") or "No disponible"),
    )
    installed_model_count = summary.get("installed_model_count", 0)
    metrics[3].metric(
        "Modelos locales",
        (
            installed_model_count
            if isinstance(installed_model_count, int)
            else 0
        ),
    )
    error_code = summary.get("error_code")
    if error_code:
        st.caption(f"Diagnóstico seguro: {error_code}")


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
