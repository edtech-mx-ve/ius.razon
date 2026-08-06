from __future__ import annotations

import streamlit as st

from ius_razon.security.privacy_config import PrivacySettings
from ius_razon.security.privacy_scanner import PrivacyReport
from ius_razon.services.privacy_service import PrivacyService


def render_privacy_center(
    case_id: str,
    *,
    privacy_service: PrivacyService,
    settings: PrivacySettings,
) -> None:
    """Muestra controles de privacidad sin revelar los valores detectados."""

    st.subheader("Privacidad y datos de demostración")
    st.caption(
        "El análisis es determinista y solo informa categorías, ubicación "
        "y huellas irreversibles; no muestra ni registra el dato encontrado."
    )

    summary = settings.safe_summary()
    metrics = st.columns(4)
    metrics[0].metric("Modo", str(summary["mode"]))
    metrics[1].metric(
        "Cargas",
        "Habilitadas" if settings.uploads_enabled else "Bloqueadas",
    )
    metrics[2].metric(
        "Rutas",
        "Visibles" if settings.display_storage_paths else "Ocultas",
    )
    metrics[3].metric(
        "Gate de exportación",
        (
            "Activo"
            if settings.require_clean_scan_for_export
            else "Informativo"
        ),
    )

    if settings.public_demo:
        st.warning(
            "Modo de demostración pública: use únicamente datos sintéticos. "
            "Las cargas están bloqueadas y las rutas locales están ocultas."
        )
    else:
        st.info(
            "Modo local: el análisis no sustituye una evaluación jurídica "
            "o de protección de datos."
        )

    report_key = f"privacy_report_{case_id}"
    if st.button(
        "Ejecutar análisis de privacidad",
        type="primary",
        key=f"privacy_scan_{case_id}",
        help=(
            "Analiza patrones sensibles sin mostrar ni almacenar "
            "los valores detectados."
        ),
    ):
        try:
            with st.spinner(
                "Analizando el expediente sin revelar valores sensibles..."
            ):
                st.session_state[report_key] = privacy_service.scan_case(
                    case_id
                )
        except Exception as exc:
            st.error(f"No fue posible analizar el expediente: {exc}")

    report = st.session_state.get(report_key)
    if not isinstance(report, PrivacyReport):
        st.info("Ejecute el análisis antes de preparar una demostración.")
        return

    _render_report(report, privacy_service)


def _render_report(
    report: PrivacyReport,
    privacy_service: PrivacyService,
) -> None:
    metrics = st.columns(5)
    metrics[0].metric("Entidades", report.scanned_entities)
    metrics[1].metric("Campos", report.scanned_fields)
    metrics[2].metric("Críticos", report.critical_count)
    metrics[3].metric("Altos", report.high_count)
    metrics[4].metric("Medios", report.medium_count)

    if report.is_demo_safe:
        st.success(
            "No se detectaron patrones bloqueantes para una demostración."
        )
    else:
        st.error(
            "El expediente no está listo para exposición pública. "
            "Revise los hallazgos antes de exportar o desplegar."
        )

    if report.truncated:
        st.warning(
            "El análisis alcanzó el límite configurado de hallazgos; "
            "el resultado no puede considerarse completo."
        )

    if report.findings:
        st.caption(
            "La tabla contiene ubicaciones y huellas irreversibles; "
            "no incluye los valores originales."
        )
        st.dataframe(
            [
                {
                    "gravedad": finding.severity.value,
                    "categoría": finding.category.value,
                    "entidad": finding.location.entity_type,
                    "código": finding.location.entity_code,
                    "campo": finding.location.field_name,
                    "huella": finding.fingerprint,
                    "acción": finding.message,
                }
                for finding in report.findings
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption("Sin hallazgos para las reglas deterministas activas.")

    st.download_button(
        "Descargar reporte seguro de privacidad",
        data=privacy_service.export_report_json(report),
        file_name=f"ius_razon_privacidad_{report.case_id[:8]}.json",
        mime="application/json",
        key=f"privacy_report_download_{report.case_id}",
    )
