from __future__ import annotations

import logging

import pytest

from ius_razon.ui.accessibility import accessibility_css
from ius_razon.ui.navigation import (
    DEFAULT_PAGE_ID,
    get_navigation_item,
    navigation_groups,
    navigation_items,
    navigation_items_for_group,
    normalize_page_id,
)
from ius_razon.ui.performance import (
    RenderPerformanceBudget,
    RenderPerformanceLevel,
    classify_render_duration,
    measure_view_render,
)


def test_navigation_registry_has_unique_identifiers_and_labels() -> None:
    items = navigation_items()
    assert len(items) == 19
    assert len({item.page_id for item in items}) == len(items)
    assert len({item.label for item in items}) == len(items)
    assert all(item.description.strip() for item in items)


def test_navigation_registry_contains_all_expected_routes() -> None:
    assert {item.page_id for item in navigation_items()} == {
        "summary",
        "parties",
        "facts",
        "evidence",
        "fact_evidence",
        "issues",
        "norms",
        "jurisprudence",
        "doctrine",
        "source_matrix",
        "assertions",
        "rules",
        "inference",
        "reasoning_management",
        "safe_correction",
        "argumentation",
        "integral_report",
        "assistant",
        "privacy",
    }


def test_navigation_groups_preserve_declared_order() -> None:
    assert navigation_groups() == (
        "Inicio",
        "Expediente",
        "Fuentes jurídicas",
        "Razonamiento",
        "Argumentación e informes",
        "Seguridad",
    )


def test_each_navigation_group_has_at_least_one_view() -> None:
    for group in navigation_groups():
        group_items = navigation_items_for_group(group)
        assert group_items
        assert all(item.group == group for item in group_items)


def test_navigation_lookup_and_normalization_are_safe() -> None:
    assert get_navigation_item("privacy").label == "Privacidad y demo"
    assert normalize_page_id("assistant") == "assistant"
    assert normalize_page_id("unknown") == DEFAULT_PAGE_ID
    assert normalize_page_id(None) == DEFAULT_PAGE_ID


def test_unknown_navigation_item_raises_explicit_error() -> None:
    with pytest.raises(KeyError, match="Vista desconocida"):
        get_navigation_item("missing")


def test_accessibility_css_contains_required_contracts() -> None:
    css = accessibility_css()
    assert ":focus-visible" in css
    assert "min-height: var(--ius-touch-target)" in css
    assert "@media (max-width: 48rem)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "overflow-x: auto" in css
    assert "44px" in css


@pytest.mark.parametrize(
    ("duration_ms", "expected"),
    [
        (0.0, RenderPerformanceLevel.OK),
        (1499.9, RenderPerformanceLevel.OK),
        (1500.0, RenderPerformanceLevel.WARNING),
        (4999.9, RenderPerformanceLevel.WARNING),
        (5000.0, RenderPerformanceLevel.CRITICAL),
    ],
)
def test_render_duration_classification(
    duration_ms: float,
    expected: RenderPerformanceLevel,
) -> None:
    assert classify_render_duration(duration_ms) is expected


def test_render_duration_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="no puede ser negativo"):
        classify_render_duration(-0.1)


@pytest.mark.parametrize(
    "budget",
    [
        RenderPerformanceBudget(warning_ms=0, critical_ms=10),
        RenderPerformanceBudget(warning_ms=10, critical_ms=10),
        RenderPerformanceBudget(warning_ms=20, critical_ms=10),
    ],
)
def test_render_budget_rejects_invalid_thresholds(
    budget: RenderPerformanceBudget,
) -> None:
    with pytest.raises(ValueError):
        budget.validate()


def test_measure_view_render_logs_only_technical_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        caplog.at_level(
            logging.INFO,
            logger="ius_razon.ui.performance",
        ),
        measure_view_render("summary"),
    ):
        pass

    assert "page=summary" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "level=ok" in caplog.text


def test_measure_view_render_rejects_empty_identifier() -> None:
    with pytest.raises(ValueError, match="no puede estar vacío"), measure_view_render(" "):
        pass
