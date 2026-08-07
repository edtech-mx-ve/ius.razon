from __future__ import annotations

from datetime import date
from pathlib import Path

from ius_razon.domain.enums import (
    CaseStatus,
    ConfidentialityLevel,
    PartyRole,
    PartyType,
)
from ius_razon.domain.models import CaseCreate, PartyCreate
from ius_razon.services.case_service import CaseService


def test_update_case_preserves_identity_and_related_data(
    service: CaseService,
) -> None:
    original = service.create_case(
        CaseCreate(
            title="Título inicial",
            description="Descripción inicial suficientemente extensa.",
            matter="Civil",
            jurisdiction="Ciudad de México",
        )
    )
    party = service.add_party(
        PartyCreate(
            case_id=original.id,
            name_alias="Parte demostrativa",
            party_type=PartyType.NATURAL_PERSON,
            legal_role=PartyRole.CLAIMANT,
        )
    )

    updated = service.update_case(
        original.id,
        CaseCreate(
            title="Título corregido del expediente",
            description="Descripción actualizada del expediente demostrativo.",
            matter="Civil",
            jurisdiction="Ciudad de México",
            location="Ciudad de México",
            opened_on=date(2026, 8, 7),
            status=CaseStatus.UNDER_REVIEW,
            objective="Validar la edición persistente del expediente.",
            user_role="Analista jurídico",
            confidentiality=ConfidentialityLevel.PUBLIC_DEMO,
        ),
    )

    assert updated.id == original.id
    assert updated.created_at == original.created_at
    assert updated.updated_at >= original.updated_at
    assert updated.title == "Título corregido del expediente"
    assert updated.description == (
        "Descripción actualizada del expediente demostrativo."
    )
    assert updated.location == "Ciudad de México"
    assert updated.opened_on == date(2026, 8, 7)
    assert updated.status is CaseStatus.UNDER_REVIEW
    assert updated.objective == (
        "Validar la edición persistente del expediente."
    )
    assert updated.user_role == "Analista jurídico"
    assert updated.confidentiality is ConfidentialityLevel.PUBLIC_DEMO

    parties = service.list_parties(original.id)
    assert len(parties) == 1
    assert parties[0].id == party.id

    events = service.list_audit_events(original.id)
    assert any(event.event_type == "case.updated" for event in events)


def test_app_exposes_edit_case_form() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")

    assert "def edit_case_form(case_id: str) -> None:" in source
    assert 'with st.expander("Editar expediente"' in source
    assert "service.update_case(" in source
