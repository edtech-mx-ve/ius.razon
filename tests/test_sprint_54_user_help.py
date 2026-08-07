from __future__ import annotations

from ius_razon.ui.navigation import navigation_items
from ius_razon.ui.user_help import SECTION_HELP, WORKFLOW


def test_every_navigation_page_has_contextual_help() -> None:
    page_ids = {item.page_id for item in navigation_items()}
    assert set(SECTION_HELP) == page_ids


def test_all_help_entries_are_complete() -> None:
    for item in SECTION_HELP.values():
        assert item.purpose.strip()
        assert item.steps
        assert all(step.strip() for step in item.steps)
        assert item.result.strip()
        assert item.caution.strip()


def test_manual_defines_complete_workflow() -> None:
    assert len(WORKFLOW) >= 8
    assert WORKFLOW[0].startswith("Crear o seleccionar")
    assert "privacidad" in WORKFLOW[-1].lower()
