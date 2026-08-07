from __future__ import annotations

from pathlib import Path

import streamlit as st

from ius_razon.ui.access_control import (
    AccessConfigurationError,
    load_access_settings,
    password_matches,
)
from ius_razon.ui.branding import render_brand_footer, render_brand_header
from ius_razon.ui.user_help import render_user_manual

_AUTH_KEY = "ius_access_authenticated"
_VIEW_KEY = "ius_public_view"

WELCOME = "welcome"
MANUAL = "manual"
ACCESS = "access"
PROTECTED = "protected"


def _set_view(view: str) -> None:
    st.session_state[_VIEW_KEY] = view


def _authenticated() -> bool:
    return bool(st.session_state.get(_AUTH_KEY, False))


def _header(project_root: Path) -> None:
    render_brand_header(project_root)
    st.caption("Sistema de Análisis, Argumentación y Estrategia Jurídica")


def _welcome(project_root: Path) -> None:
    _header(project_root)
    st.markdown(
        """
        ## Análisis jurídico estructurado y trazable

        **IUS-Razón** organiza expedientes, hechos, pruebas, problemas jurídicos,
        fuentes, reglas, argumentos y conclusiones dentro de un flujo explícito
        de análisis.

        Su propósito es apoyar la organización sistemática de información
        jurídica y conservar trazabilidad entre los elementos que intervienen
        en el razonamiento y la argumentación.
        """
    )

    columns = st.columns(3)
    columns[0].markdown(
        "**Expediente y prueba**\n\nPartes, hechos, pruebas y vínculos probatorios."
    )
    columns[1].markdown(
        "**Fuentes y razonamiento**\n\n"
        "Problemas jurídicos, fuentes, premisas, reglas e inferencia."
    )
    columns[2].markdown(
        "**Argumentación e informes**\n\n"
        "Argumentos, escenarios, informes trazables y asistencia controlada."
    )

    st.warning(
        "Prototipo académico. No constituye asesoría jurídica, dictamen ni "
        "predicción judicial. Toda fuente, vigencia, aplicabilidad y conclusión "
        "debe ser verificada por una persona profesional del Derecho."
    )

    actions = st.columns(2)
    if actions[0].button(
        "Acceder a IUS-Razón",
        type="primary",
        use_container_width=True,
    ):
        _set_view(ACCESS)
        st.rerun()

    if actions[1].button("Manual de usuario", use_container_width=True):
        _set_view(MANUAL)
        st.rerun()

    render_brand_footer(project_root)


def _manual(project_root: Path) -> None:
    _header(project_root)
    render_user_manual()

    actions = st.columns(2)
    back_label = (
        "Volver al área de trabajo"
        if _authenticated()
        else "Volver a bienvenida"
    )
    if actions[0].button(back_label, use_container_width=True):
        _set_view(PROTECTED if _authenticated() else WELCOME)
        st.rerun()

    if (
        not _authenticated()
        and actions[1].button(
            "Acceder a IUS-Razón",
            type="primary",
            use_container_width=True,
        )
    ):
        _set_view(ACCESS)
        st.rerun()

    render_brand_footer(project_root)


def _access(project_root: Path) -> None:
    _header(project_root)
    st.subheader("Acceso protegido")
    st.write(
        "El área de trabajo contiene las funciones operativas de IUS-Razón "
        "y requiere autenticación."
    )

    try:
        settings = load_access_settings(project_root)
    except AccessConfigurationError as exc:
        st.error(str(exc))
        st.info(
            "La página pública y el manual continúan disponibles, pero el área "
            "de trabajo permanecerá cerrada hasta configurar el secreto."
        )
        if st.button("Volver a bienvenida"):
            _set_view(WELCOME)
            st.rerun()
        render_brand_footer(project_root)
        return

    with st.form("ius_access_form", clear_on_submit=True):
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button(
            "Entrar",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if password_matches(password, settings.password):
            st.session_state[_AUTH_KEY] = True
            _set_view(PROTECTED)
            st.rerun()
        else:
            st.error("Acceso no autorizado.")

    if st.button("Volver a bienvenida"):
        _set_view(WELCOME)
        st.rerun()

    render_brand_footer(project_root)


def render_public_portal(project_root: Path) -> bool:
    """Devuelve True solo cuando el área protegida puede cargarse."""

    if _VIEW_KEY not in st.session_state:
        _set_view(PROTECTED if _authenticated() else WELCOME)

    view = str(st.session_state[_VIEW_KEY])

    if view == PROTECTED:
        if _authenticated():
            return True
        _set_view(ACCESS)
        view = ACCESS

    if view == MANUAL:
        _manual(project_root)
        return False

    if view == ACCESS:
        _access(project_root)
        return False

    _welcome(project_root)
    return False


def render_protected_sidebar_controls() -> None:
    """Muestra manual y cierre de sesión dentro del área protegida."""

    st.caption("Área protegida")

    if st.button(
        "📘 Manual de usuario",
        key="ius_sidebar_manual",
        use_container_width=True,
    ):
        _set_view(MANUAL)
        st.rerun()

    if st.button(
        "Cerrar sesión",
        key="ius_sidebar_logout",
        use_container_width=True,
    ):
        st.session_state.clear()
        st.session_state[_VIEW_KEY] = WELCOME
        st.rerun()

    st.divider()
