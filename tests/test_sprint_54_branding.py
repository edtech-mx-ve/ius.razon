from __future__ import annotations

from pathlib import Path

from ius_razon.ui.branding import (
    FOOTER_TEXT,
    HEADER_COLUMN_RATIOS,
    PRODUCT_LOGO_NAME,
    branding_css,
    resolve_branding_assets,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_product_logo_is_a_valid_png_file() -> None:
    assets = resolve_branding_assets(PROJECT_ROOT)

    assert assets.product_logo.name == PRODUCT_LOGO_NAME
    assert assets.product_logo.read_bytes()[:8] == PNG_SIGNATURE


def test_product_logo_remains_inside_assets_directory() -> None:
    assets = resolve_branding_assets(PROJECT_ROOT)

    assert assets.product_logo.parent == (PROJECT_ROOT / "assets").resolve()


def test_header_uses_half_width_center_column() -> None:
    assert HEADER_COLUMN_RATIOS == (1, 2, 1)
    assert HEADER_COLUMN_RATIOS[1] / sum(HEADER_COLUMN_RATIOS) == 0.5


def test_skepsis_logo_is_not_part_of_branding_assets() -> None:
    assets = resolve_branding_assets(PROJECT_ROOT)

    assert not hasattr(assets, "studio_logo")
    assert not (PROJECT_ROOT / "assets" / "logo_skepsis_apps.png").exists()


def test_institutional_footer_text_is_exact() -> None:
    assert FOOTER_TEXT == "Powered by Sképsis Apps · © 2026 Sképsis Apps"


def test_branding_css_defines_text_only_footer() -> None:
    css = branding_css()

    assert ".ius-brand-footer" in css
    assert ".ius-brand-footer-text" in css
    assert "text-align: center" in css