from __future__ import annotations

import pytest
from pydantic import ValidationError

from ius_razon.domain.models import CaseCreate, FactCreate


def test_case_rejects_short_description() -> None:
    with pytest.raises(ValidationError):
        CaseCreate(
            title="Caso válido",
            description="corta",
            matter="Civil",
            jurisdiction="México",
        )


def test_fact_rejects_out_of_range_controversy() -> None:
    with pytest.raises(ValidationError):
        FactCreate(
            case_id="case-1",
            description="Hecho suficientemente descrito.",
            controversy_level=6,
        )
