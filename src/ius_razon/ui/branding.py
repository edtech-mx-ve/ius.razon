from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

FOOTER_TEXT = "Powered by Sképsis Apps · © 2026 Sképsis Apps"
PRODUCT_LOGO_NAME = "logo_ius_razon.png"
HEADER_COLUMN_RATIOS = (1, 2, 1)


@dataclass(frozen=True, slots=True)
class BrandingAssets:
    """Ruta inmutable del recurso visual principal."""

    product_logo: Path


def resolve_branding_assets(project_root: Path) -> BrandingAssets:
    """Resuelve el logo de IUS-Razón dentro de la carpeta de recursos."""

    assets_dir = (project_root.resolve() / "assets").resolve()
    return BrandingAssets(
        product_logo=assets_dir / PRODUCT_LOGO_NAME,
    )


def branding_css() -> str:
    """Devuelve estilos mínimos para el encabezado y el pie institucional."""

    return """
    .ius-brand-footer {
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(49, 51, 63, 0.18);
    }
    .ius-brand-footer-text {
        padding-top: 0.65rem;
        color: rgba(49, 51, 63, 0.72);
        font-size: 0.92rem;
        line-height: 1.5;
        text-align: center;
    }
    """


def render_brand_header(project_root: Path) -> None:
    """Muestra el logo de IUS-Razón al 50 % del ancho disponible."""

    assets = resolve_branding_assets(project_root)
    if not assets.product_logo.is_file():
        st.title("⚖️ IUS-Razón")
        return

    _, logo_column, _ = st.columns(HEADER_COLUMN_RATIOS)
    with logo_column:
        st.image(
            str(assets.product_logo),
            use_container_width=True,
        )


def render_brand_footer(project_root: Path) -> None:
    """Muestra solamente la firma textual de Sképsis Apps."""

    del project_root
    st.markdown(
        f"<style>{branding_css()}</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<div class="ius-brand-footer">'
            f'<div class="ius-brand-footer-text">{FOOTER_TEXT}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )