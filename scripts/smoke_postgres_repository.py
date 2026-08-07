from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from ius_razon.domain.enums import (
    EvidenceEvaluationStatus,
    EvidenceType,
    FactStatus,
    JurisprudenceAuthority,
    LegalIssueStatus,
    LegalSourceType,
    NormHierarchy,
    PartyRole,
    PartyType,
    SourceOrientation,
)
from ius_razon.domain.models import (
    CaseCreate,
    DoctrineCreate,
    EvidenceCreate,
    FactCreate,
    IssueSourceLinkCreate,
    JurisprudenceCreate,
    LegalIssueCreate,
    NormCreate,
    PartyCreate,
)
from ius_razon.persistence.postgres_repository import PostgresRepository
from ius_razon.persistence.postgres_runtime import load_postgres_settings
from ius_razon.persistence.sqlite_repository import ConflictError

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def cleanup(case_id: str, direct_database_url: str) -> None:
    with psycopg.connect(
        direct_database_url,
        connect_timeout=20,
    ) as connection:
        connection.execute(
            "DELETE FROM cases WHERE id = %s",
            (case_id,),
        )
        connection.commit()


def run_smoke() -> None:
    settings = load_postgres_settings(PROJECT_ROOT)
    repository = PostgresRepository(settings.database_url)
    repository.initialize()

    case_id: str | None = None
    try:
        case = repository.create_case(
            CaseCreate(
                title="SMOKE PostgreSQL Sprint 5.4",
                description=(
                    "Expediente sintético temporal para validar persistencia Neon."
                ),
                matter="Mercantil",
                jurisdiction="México",
            )
        )
        case_id = case.id

        party = repository.add_party(
            PartyCreate(
                case_id=case.id,
                name_alias="Parte sintética A",
                party_type=PartyType.LEGAL_ENTITY,
                legal_role=PartyRole.CLAIMANT,
            )
        )

        fact = repository.add_fact(
            FactCreate(
                case_id=case.id,
                description="La parte sintética realizó el pago pactado.",
                actor_party_id=party.id,
                status=FactStatus.ALLEGED,
                controversy_level=2,
            )
        )

        evidence = repository.add_evidence(
            EvidenceCreate(
                case_id=case.id,
                evidence_type=EvidenceType.RECEIPT,
                description="Comprobante sintético sin archivo.",
                offering_party_id=party.id,
                evaluation_status=EvidenceEvaluationStatus.OFFERED,
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )

        repository.link_fact_evidence(
            case_id=case.id,
            fact_id=fact.id,
            evidence_id=evidence.id,
            purpose="Validar vínculo PostgreSQL.",
        )

        issue = repository.add_legal_issue(
            LegalIssueCreate(
                case_id=case.id,
                title="Exigibilidad sintética",
                question="¿La obligación sintética era exigible?",
            )
        )

        norm = repository.add_norm(
            NormCreate(
                case_id=case.id,
                jurisdiction="México",
                matter="Mercantil",
                instrument="Código sintético",
                article="Artículo 1",
                text="Las obligaciones sintéticas deben cumplirse.",
                hierarchy=NormHierarchy.FEDERAL_LAW,
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )

        precedent = repository.add_jurisprudence(
            JurisprudenceCreate(
                case_id=case.id,
                court="Tribunal sintético",
                identifier="SMOKE-001",
                jurisdiction="México",
                matter="Mercantil",
                relevant_facts="Hechos sintéticos controlados.",
                legal_question="¿Existe incumplimiento sintético?",
                criterion="La exigibilidad depende del vencimiento.",
                authority=JurisprudenceAuthority.PENDING_VERIFICATION,
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )

        doctrine = repository.add_doctrine(
            DoctrineCreate(
                case_id=case.id,
                author="Autor sintético",
                work_title="Obligaciones sintéticas",
                concept="Incumplimiento",
                position_summary="La obligación debe ser válida y exigible.",
                citation="Autor sintético. (2026). Obligaciones sintéticas.",
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )

        repository.link_issue_source(
            IssueSourceLinkCreate(
                case_id=case.id,
                issue_id=issue.id,
                source_type=LegalSourceType.NORM,
                source_id=norm.id,
                orientation=SourceOrientation.SUPPORTS,
                applicability="Aplicación sintética directa.",
            )
        )

        assert repository.count_by_case("parties", case.id) == 1
        assert repository.count_by_case("facts", case.id) == 1
        assert repository.count_by_case("evidence", case.id) == 1
        assert repository.count_by_case("legal_issues", case.id) == 1
        assert repository.count_by_case("norms", case.id) == 1
        assert repository.count_by_case("jurisprudence", case.id) == 1
        assert repository.count_by_case("doctrine", case.id) == 1
        assert repository.count_links(case.id) == 1
        assert repository.count_issue_source_links(case.id) == 1

        fact_links = repository.list_fact_evidence_links(case.id)
        assert len(fact_links) == 1
        assert fact_links[0].fact_code == "H-001"
        assert fact_links[0].evidence_code == "P-001"

        source_links = repository.list_issue_source_links(case.id)
        assert len(source_links) == 1
        assert source_links[0].source_code == "N-001"

        updated_issue = repository.update_legal_issue(
            issue.id,
            LegalIssueCreate(
                case_id=case.id,
                title="Exigibilidad sintética corregida",
                question="¿La obligación sintética continúa siendo exigible?",
                status=LegalIssueStatus.UNDER_ANALYSIS,
            ),
        )
        assert updated_issue.code == "PJ-001"

        updated_norm = repository.update_norm(
            norm.id,
            NormCreate(
                case_id=case.id,
                jurisdiction="México",
                matter="Mercantil",
                instrument="Código sintético corregido",
                article="Artículo 1",
                text="Las obligaciones sintéticas exigibles deben cumplirse.",
                hierarchy=NormHierarchy.FEDERAL_LAW,
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )
        assert updated_norm.code == "N-001"

        updated_precedent = repository.update_jurisprudence(
            precedent.id,
            JurisprudenceCreate(
                case_id=case.id,
                court="Tribunal sintético corregido",
                identifier="SMOKE-001-C",
                jurisdiction="México",
                matter="Mercantil",
                relevant_facts=precedent.relevant_facts,
                legal_question=precedent.legal_question,
                criterion="Criterio sintético corregido.",
                authority=JurisprudenceAuthority.ORIENTATIVE,
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )
        assert updated_precedent.code == "J-001"

        updated_doctrine = repository.update_doctrine(
            doctrine.id,
            DoctrineCreate(
                case_id=case.id,
                author="Autor sintético corregido",
                work_title=doctrine.work_title,
                concept=doctrine.concept,
                position_summary="Posición sintética corregida.",
                citation="Autor sintético corregido. (2026).",
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )
        assert updated_doctrine.code == "D-001"

        repository.update_issue_source_link(
            IssueSourceLinkCreate(
                case_id=case.id,
                issue_id=issue.id,
                source_type=LegalSourceType.NORM,
                source_id=norm.id,
                orientation=SourceOrientation.CONTEXTUAL,
                applicability="Aplicación sintética revisada.",
                notes="Smoke PostgreSQL.",
            )
        )

        try:
            repository.delete_source(
                case_id=case.id,
                source_type=LegalSourceType.NORM,
                source_id=norm.id,
            )
        except ConflictError:
            pass
        else:
            raise AssertionError(
                "La protección de fuente vinculada no se aplicó."
            )

        repository.unlink_issue_source(
            case_id=case.id,
            issue_id=issue.id,
            source_type=LegalSourceType.NORM,
            source_id=norm.id,
        )
        repository.delete_source(
            case_id=case.id,
            source_type=LegalSourceType.NORM,
            source_id=norm.id,
        )
        repository.delete_source(
            case_id=case.id,
            source_type=LegalSourceType.JURISPRUDENCE,
            source_id=precedent.id,
        )
        repository.delete_source(
            case_id=case.id,
            source_type=LegalSourceType.DOCTRINE,
            source_id=doctrine.id,
        )
        repository.delete_legal_issue(issue.id, case.id)

        events = repository.list_audit_events(case.id)
        assert len(events) >= 10

        print(
            "PostgresRepository Neon: OK | "
            "CRUD núcleo=OK | vínculos=OK | auditoría=OK | "
            "protecciones=OK | códigos=OK"
        )
    finally:
        if case_id is not None:
            cleanup(case_id, settings.direct_database_url)
            print("Datos sintéticos de smoke eliminados de Neon.")


def main() -> int:
    try:
        run_smoke()
    except Exception as exc:
        print(f"Smoke PostgresRepository falló: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
