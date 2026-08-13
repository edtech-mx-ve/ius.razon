from __future__ import annotations

from ius_razon.domain.enums import FactStatus, PartyRole, PartyType
from ius_razon.domain.models import CaseCreate, FactCreate, PartyCreate
from ius_razon.services.case_service import CaseService


def test_update_party_preserves_identity_and_links(
    service: CaseService,
) -> None:
    case = service.create_case(
        CaseCreate(
            title="Caso demo edición",
            description="Expediente hipotético para probar edición de partes.",
            matter="Civil",
            jurisdiction="México",
        )
    )

    party = service.add_party(
        PartyCreate(
            case_id=case.id,
            name_alias="Nombre Demo Original",
            party_type=PartyType.LEGAL_ENTITY,
            legal_role=PartyRole.CLAIMANT,
        )
    )

    fact = service.add_fact(
        FactCreate(
            case_id=case.id,
            description="Hecho vinculado a la parte.",
            actor_party_id=party.id,
            status=FactStatus.ALLEGED,
        )
    )

    updated = service.update_party(
        party.id,
        PartyCreate(
            case_id=case.id,
            name_alias="Compradora demo",
            party_type=party.party_type,
            legal_role=party.legal_role,
            representation=party.representation,
            claim=party.claim,
            position=party.position,
        ),
    )

    assert updated.id == party.id
    assert updated.name_alias == "Compradora demo"

    stored_fact = service.list_facts(case.id)[0]
    assert stored_fact.id == fact.id
    assert stored_fact.actor_party_id == party.id

    events = service.list_audit_events(case.id)
    assert any(
        event.event_type == "party.updated" and event.entity_id == party.id for event in events
    )
