from __future__ import annotations

import pytest

from ius_razon.domain.enums import PartyRole, PartyType
from ius_razon.domain.models import CaseCreate, PartyCreate
from ius_razon.persistence.sqlite_repository import NotFoundError
from ius_razon.services.case_service import CaseService


def test_missing_case_is_rejected(service: CaseService) -> None:
    with pytest.raises(NotFoundError):
        service.add_party(
            PartyCreate(
                case_id="missing",
                name_alias="Parte inexistente",
                party_type=PartyType.NATURAL_PERSON,
                legal_role=PartyRole.OTHER,
            )
        )


def test_cases_are_listed(service: CaseService) -> None:
    service.create_case(
        CaseCreate(
            title="Caso uno",
            description="Descripción suficientemente extensa para el expediente uno.",
            matter="Civil",
            jurisdiction="México",
        )
    )
    service.create_case(
        CaseCreate(
            title="Caso dos",
            description="Descripción suficientemente extensa para el expediente dos.",
            matter="Mercantil",
            jurisdiction="México",
        )
    )

    assert len(service.list_cases()) == 2
