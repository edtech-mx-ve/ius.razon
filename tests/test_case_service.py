from __future__ import annotations

from ius_razon.domain.enums import (
    EvidenceEvaluationStatus,
    EvidenceType,
    FactStatus,
    PartyRole,
    PartyType,
)
from ius_razon.domain.models import CaseCreate, EvidenceCreate, FactCreate, PartyCreate
from ius_razon.services.case_service import CaseService


def create_case(service: CaseService):
    return service.create_case(
        CaseCreate(
            title="Incumplimiento de entrega",
            description="La parte compradora afirma que pagó y no recibió el equipo.",
            matter="Mercantil",
            jurisdiction="México",
        )
    )


def test_complete_sprint_one_flow(service: CaseService) -> None:
    case = create_case(service)

    party = service.add_party(
        PartyCreate(
            case_id=case.id,
            name_alias="Compradora A",
            party_type=PartyType.LEGAL_ENTITY,
            legal_role=PartyRole.CLAIMANT,
        )
    )

    fact = service.add_fact(
        FactCreate(
            case_id=case.id,
            description="La compradora realizó el pago total convenido.",
            actor_party_id=party.id,
            status=FactStatus.ALLEGED,
            controversy_level=3,
        )
    )

    evidence = service.add_evidence(
        EvidenceCreate(
            case_id=case.id,
            evidence_type=EvidenceType.RECEIPT,
            description="Comprobante de transferencia bancaria.",
            offering_party_id=party.id,
            evaluation_status=EvidenceEvaluationStatus.OFFERED,
        ),
        original_file_name="comprobante.txt",
        file_content=b"contenido de prueba",
    )

    service.link_fact_evidence(
        case_id=case.id,
        fact_id=fact.id,
        evidence_id=evidence.id,
        purpose="Acreditar el pago.",
    )

    summary = service.get_case_summary(case.id)
    assert summary.party_count == 1
    assert summary.fact_count == 1
    assert summary.evidence_count == 1
    assert summary.link_count == 1

    links = service.list_fact_evidence_links(case.id)
    assert links[0].fact_code == "H-001"
    assert links[0].evidence_code == "P-001"
    assert links[0].purpose == "Acreditar el pago."

    events = service.list_audit_events(case.id)
    assert len(events) >= 5


def test_file_upload_rejects_executable(service: CaseService) -> None:
    case = create_case(service)
    try:
        service.add_evidence(
            EvidenceCreate(
                case_id=case.id,
                evidence_type=EvidenceType.OTHER,
                description="Archivo ejecutable no permitido.",
            ),
            original_file_name="malware.exe",
            file_content=b"MZ",
        )
    except ValueError as exc:
        assert "Extensión no permitida" in str(exc)
    else:
        raise AssertionError("El archivo ejecutable debió ser rechazado.")
