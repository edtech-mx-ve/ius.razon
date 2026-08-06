from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from ius_razon.ui.accessibility import accessibility_css
from ius_razon.ui.branding import render_brand_footer, render_brand_header
from ius_razon.ui.navigation import (
    NavigationItem,
    get_navigation_item,
    navigation_groups,
    navigation_items_for_group,
    normalize_page_id,
)


def render_accessibility_foundation() -> None:
    """Inyecta estilos de foco, tacto, reducción de movimiento y móvil."""

    st.markdown(
        f"<style>{accessibility_css()}</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<a class="ier-skip-link" href="#ius-main-content">'
            "Saltar al contenido principal"
            "</a>"
        ),
        unsafe_allow_html=True,
    )


def render_app_header(
    *,
    version: str,
    sprint: str,
    public_demo: bool,
    project_root: Path,
) -> None:
    """Muestra la identidad principal y el estado del entorno."""

    st.markdown(
        '<div id="ius-main-content" tabindex="-1"></div>',
        unsafe_allow_html=True,
    )
    render_brand_header(project_root)
    st.caption(
        "Sistema de Análisis, Argumentación y Estrategia Jurídica "
        f"· Sprint {sprint} v{version}"
    )
    if public_demo:
        st.info(
            "Demostración pública: cargas bloqueadas, rutas ocultas "
            "y gate de privacidad activo."
        )


def render_app_footer(*, project_root: Path) -> None:
    """Muestra la firma institucional al final del contenido."""

    render_brand_footer(project_root)

def render_sidebar_navigation(case_id: str) -> NavigationItem:
    """Renderiza navegación agrupada y devuelve una única vista activa."""

    if not case_id.strip():
        raise ValueError("case_id no puede estar vacío.")

    active_key = f"ius_active_page_{case_id}"
    current_page_id = normalize_page_id(st.session_state.get(active_key))
    current_item = get_navigation_item(current_page_id)

    st.header("Navegación")
    group_key = f"ius_navigation_group_{case_id}"
    if group_key not in st.session_state:
        st.session_state[group_key] = current_item.group

    selected_group = str(
        st.selectbox(
            "Área de trabajo",
            options=list(navigation_groups()),
            key=group_key,
            help=(
                "Agrupa las funciones para evitar una barra extensa de "
                "pestañas y cargar únicamente la vista seleccionada."
            ),
        )
    )

    group_items = navigation_items_for_group(selected_group)
    page_ids = [item.page_id for item in group_items]
    radio_key = (
        "ius_navigation_page_"
        f"{case_id}_{_slugify(selected_group)}"
    )
    if radio_key not in st.session_state:
        st.session_state[radio_key] = (
            current_page_id
            if current_item.group == selected_group
            else page_ids[0]
        )

    selected_page_id = str(
        st.radio(
            "Sección",
            options=page_ids,
            format_func=_navigation_label,
            key=radio_key,
        )
    )
    st.session_state[active_key] = selected_page_id
    selected_item = get_navigation_item(selected_page_id)
    st.caption(selected_item.description)
    return selected_item


def render_section_context(item: NavigationItem) -> None:
    """Muestra ubicación y propósito de la vista activa."""

    st.markdown(
        (
            '<div class="ier-section-context" role="note">'
            f"<strong>{item.group}</strong> · {item.label}<br>"
            f"{item.description}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _navigation_label(page_id: str) -> str:
    """Devuelve la etiqueta visible de una vista."""

    return get_navigation_item(page_id).label


def _slugify(value: str) -> str:
    """Genera una clave estable de sesión a partir de una etiqueta visible."""

    normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold())
    return normalized.strip("_") or "grupo"
