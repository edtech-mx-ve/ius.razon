from __future__ import annotations

from datetime import date

import pytest

from ius_razon.domain.enums import (
    JurisprudenceAuthority,
    LegalIssueStatus,
    LegalSourceType,
    NormHierarchy,
    SourceOrientation,
)
from ius_razon.domain.models import (
    CaseCreate,
    DoctrineCreate,
    IssueSourceLinkCreate,
    JurisprudenceCreate,
    LegalIssueCreate,
    NormCreate,
)
from ius_razon.persistence.sqlite_repository import RepositoryError
from ius_razon.services.case_service import CaseService


def create_case(service: CaseService, title: str = "Controversia contractual"):
    return service.create_case(
        CaseCreate(
            title=title,
            description="Controversia por pago y falta de entrega de bienes.",
            matter="Mercantil",
            jurisdiction="México",
        )
    )


def test_complete_sprint_two_flow(service: CaseService) -> None:
    case = create_case(service)
    issue = service.add_legal_issue(
        LegalIssueCreate(
            case_id=case.id,
            title="Exigibilidad de la entrega",
            question="¿La obligación de entrega era exigible en la fecha pactada?",
            status=LegalIssueStatus.UNDER_ANALYSIS,
        )
    )
    norm = service.add_norm(
        NormCreate(
            case_id=case.id,
            jurisdiction="México",
            matter="Mercantil",
            instrument="Código de Comercio",
            article="Artículo de prueba",
            text="Texto normativo de prueba suficientemente descriptivo.",
            hierarchy=NormHierarchy.FEDERAL_LAW,
            valid_from=date(2025, 1, 1),
            version_label="Versión de prueba",
        ),
        original_file_name="norma.txt",
        file_content=b"texto normativo",
    )
    precedent = service.add_jurisprudence(
        JurisprudenceCreate(
            case_id=case.id,
            court="Órgano jurisdiccional de prueba",
            identifier="REG-TEST-001",
            jurisdiction="México",
            matter="Mercantil",
            relevant_facts="Incumplimiento de entrega después del pago.",
            legal_question="¿Existe incumplimiento exigible?",
            criterion="La exigibilidad depende del vencimiento y de la obligación acreditada.",
            authority=JurisprudenceAuthority.PENDING_VERIFICATION,
        ),
        original_file_name=None,
        file_content=None,
    )
    doctrine = service.add_doctrine(
        DoctrineCreate(
            case_id=case.id,
            author="Autora de prueba",
            work_title="Teoría general de las obligaciones",
            publication_year=2024,
            concept="Exigibilidad",
            position_summary="La exigibilidad presupone una obligación válida y vencida.",
            citation="Autora de prueba. (2024). Teoría general de las obligaciones.",
        ),
        original_file_name=None,
        file_content=None,
    )

    for source_type, source_id, reason in (
        (LegalSourceType.NORM, norm.id, "Regula el supuesto normativo."),
        (
            LegalSourceType.JURISPRUDENCE,
            precedent.id,
            "Aporta un criterio interpretativo comparable.",
        ),
        (
            LegalSourceType.DOCTRINE,
            doctrine.id,
            "Define el concepto de exigibilidad.",
        ),
    ):
        service.link_issue_source(
            IssueSourceLinkCreate(
                case_id=case.id,
                issue_id=issue.id,
                source_type=source_type,
                source_id=source_id,
                orientation=SourceOrientation.SUPPORTS,
                applicability=reason,
            )
        )

    summary = service.get_case_summary(case.id)
    assert summary.legal_issue_count == 1
    assert summary.norm_count == 1
    assert summary.jurisprudence_count == 1
    assert summary.doctrine_count == 1
    assert summary.issue_source_link_count == 3

    links = service.list_issue_source_links(case.id)
    assert {link.source_code for link in links} == {"N-001", "J-001", "D-001"}
    assert all(link.issue_code == "PJ-001" for link in links)
    assert norm.file_sha256 is not None


def test_cross_case_issue_source_link_is_rejected(service: CaseService) -> None:
    first = create_case(service, "Caso primero")
    second = create_case(service, "Caso segundo")
    issue = service.add_legal_issue(
        LegalIssueCreate(
            case_id=first.id,
            title="Problema del primer caso",
            question="¿La fuente pertenece al mismo expediente jurídico?",
        )
    )
    norm = service.add_norm(
        NormCreate(
            case_id=second.id,
            jurisdiction="México",
            matter="Civil",
            instrument="Código de prueba",
            article="1",
            text="Texto normativo suficiente para la validación.",
        ),
        original_file_name=None,
        file_content=None,
    )

    with pytest.raises(RepositoryError):
        service.link_issue_source(
            IssueSourceLinkCreate(
                case_id=first.id,
                issue_id=issue.id,
                source_type=LegalSourceType.NORM,
                source_id=norm.id,
                applicability="No debe permitirse la relación entre expedientes distintos.",
            )
        )


def test_norm_rejects_inverted_validity_period() -> None:
    with pytest.raises(ValueError, match="vigencia"):
        NormCreate(
            case_id="case",
            jurisdiction="México",
            matter="Civil",
            instrument="Código de prueba",
            article="1",
            text="Texto normativo suficiente para la validación.",
            valid_from=date(2026, 2, 1),
            valid_to=date(2026, 1, 1),
        )
