from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Final

from ius_razon.domain.enums import (
    CaseStatus,
    ConfidentialityLevel,
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
from ius_razon.persistence.sqlite_repository import SQLiteRepository

DEFAULT_DEMO_DB: Final = Path("data/ius_razon_demo.db")
DEMO_CASE_TITLE: Final = "DEMO-001 | Incumplimiento contractual sintético"


@dataclass(frozen=True, slots=True)
class DemoDatabaseResult:
    """Resumen no sensible de una base de demostración generada."""

    database_name: str
    case_title: str
    counts: dict[str, int]

    def as_dict(self) -> dict[str, object]:
        """Convierte el resultado en una estructura serializable."""

        return asdict(self)


def _sqlite_sidecars(path: Path) -> tuple[Path, Path, Path]:
    return path, Path(f"{path}-wal"), Path(f"{path}-shm")


def _remove_sqlite_files(path: Path) -> None:
    for candidate in _sqlite_sidecars(path):
        candidate.unlink(missing_ok=True)


def _checkpoint(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode = DELETE")
    finally:
        connection.close()


def build_demo_database(
    output_path: Path = DEFAULT_DEMO_DB,
    *,
    force: bool = False,
) -> DemoDatabaseResult:
    """Genera una base SQLite sintética sin datos personales ni adjuntos."""

    target = output_path.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        raise FileExistsError(
            f"La base demo ya existe: {output_path}. Use --force para reconstruirla."
        )

    temporary = target.with_name(f".{target.name}.building")
    _remove_sqlite_files(temporary)
    repository = SQLiteRepository(temporary)

    try:
        repository.initialize()
        case = repository.create_case(
            CaseCreate(
                title=DEMO_CASE_TITLE,
                description=(
                    "Escenario ficticio para demostrar análisis jurídico estructurado, "
                    "trazabilidad y revisión humana en IUS-Razón."
                ),
                matter="Obligaciones contractuales",
                jurisdiction="México (escenario sintético)",
                location="Entorno de demostración",
                opened_on=date(2026, 1, 15),
                status=CaseStatus.UNDER_REVIEW,
                objective=(
                    "Organizar hechos, pruebas, problemas jurídicos y fuentes sintéticas "
                    "sin formular asesoría jurídica real."
                ),
                user_role="Analista jurídico de demostración",
                confidentiality=ConfidentialityLevel.PUBLIC_DEMO,
            )
        )

        claimant = repository.add_party(
            PartyCreate(
                case_id=case.id,
                name_alias="Persona Consumidora Demo A",
                party_type=PartyType.NATURAL_PERSON,
                legal_role=PartyRole.CLAIMANT,
                representation="Representación ficticia para pruebas",
                claim="Solicita el cumplimiento simulado y la devolución de un anticipo.",
                position="Afirma que el servicio no fue entregado en la fecha acordada.",
            )
        )
        respondent = repository.add_party(
            PartyCreate(
                case_id=case.id,
                name_alias="Proveedor Digital Demo B",
                party_type=PartyType.LEGAL_ENTITY,
                legal_role=PartyRole.RESPONDENT,
                representation="Representación ficticia para pruebas",
                claim=None,
                position="Sostiene que existió una reprogramación aceptada verbalmente.",
            )
        )

        fact_contract = repository.add_fact(
            FactCreate(
                case_id=case.id,
                description=(
                    "Las partes celebraron un acuerdo sintético para desarrollar un servicio "
                    "digital con fecha de entrega definida."
                ),
                event_date=date(2026, 1, 10),
                actor_party_id=claimant.id,
                action="Contratar servicio",
                object_text="Servicio digital de demostración",
                place="Plataforma ficticia",
                source="Registro sintético DEMO-F1",
                status=FactStatus.ADMITTED,
                controversy_level=1,
            )
        )
        fact_payment = repository.add_fact(
            FactCreate(
                case_id=case.id,
                description=(
                    "La parte promovente realizó un anticipo ficticio equivalente al cincuenta "
                    "por ciento del precio acordado."
                ),
                event_date=date(2026, 1, 12),
                actor_party_id=claimant.id,
                action="Realizar anticipo",
                object_text="Pago sintético",
                place="Medio de pago simulado",
                source="Registro sintético DEMO-F2",
                status=FactStatus.SUPPORTED,
                controversy_level=1,
            )
        )
        fact_delay = repository.add_fact(
            FactCreate(
                case_id=case.id,
                description=(
                    "La fecha de entrega transcurrió sin que el servicio figurara como concluido "
                    "en el entorno de demostración."
                ),
                event_date=date(2026, 2, 15),
                actor_party_id=respondent.id,
                action="Omitir entrega en fecha",
                object_text="Servicio digital de demostración",
                place="Plataforma ficticia",
                source="Registro sintético DEMO-F3",
                status=FactStatus.DISPUTED,
                controversy_level=4,
            )
        )

        evidence_contract = repository.add_evidence(
            EvidenceCreate(
                case_id=case.id,
                evidence_type=EvidenceType.CONTRACT,
                description="Ficha contractual sintética sin archivo ni firmas reales.",
                origin="Generador de datos demo",
                evidence_date=date(2026, 1, 10),
                integrity_statement="Contenido creado solo para demostración pública.",
                offering_party_id=claimant.id,
                objections=None,
                observations="No constituye contrato ni documento jurídico real.",
                evaluation_status=EvidenceEvaluationStatus.SUPPORTED,
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )
        evidence_payment = repository.add_evidence(
            EvidenceCreate(
                case_id=case.id,
                evidence_type=EvidenceType.RECEIPT,
                description="Comprobante sintético representado únicamente como metadato.",
                origin="Generador de datos demo",
                evidence_date=date(2026, 1, 12),
                integrity_statement="No contiene cuentas ni identificadores reales.",
                offering_party_id=claimant.id,
                objections=None,
                observations="Valor demostrativo, no probatorio.",
                evaluation_status=EvidenceEvaluationStatus.SUPPORTED,
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )
        evidence_message = repository.add_evidence(
            EvidenceCreate(
                case_id=case.id,
                evidence_type=EvidenceType.COMMUNICATION,
                description=(
                    "Resumen sintético de una comunicación sobre la supuesta reprogramación "
                    "de la entrega."
                ),
                origin="Generador de datos demo",
                evidence_date=date(2026, 2, 10),
                integrity_statement="Texto ficticio sin teléfonos, correos ni personas reales.",
                offering_party_id=respondent.id,
                objections="La aceptación de la reprogramación permanece controvertida.",
                observations="No se almacena conversación ni archivo original.",
                evaluation_status=EvidenceEvaluationStatus.OBJECTED,
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )

        repository.link_fact_evidence(
            case_id=case.id,
            fact_id=fact_contract.id,
            evidence_id=evidence_contract.id,
            purpose="Representar de forma sintética la existencia del acuerdo.",
        )
        repository.link_fact_evidence(
            case_id=case.id,
            fact_id=fact_payment.id,
            evidence_id=evidence_payment.id,
            purpose="Representar el anticipo ficticio asociado con el acuerdo.",
        )
        repository.link_fact_evidence(
            case_id=case.id,
            fact_id=fact_delay.id,
            evidence_id=evidence_message.id,
            purpose="Mostrar una fuente controvertida sobre la posible reprogramación.",
        )

        issue_breach = repository.add_legal_issue(
            LegalIssueCreate(
                case_id=case.id,
                title="Configuración demostrativa del incumplimiento",
                question=(
                    "¿Los hechos sintéticos permiten ensayar un análisis de incumplimiento "
                    "contractual sin emitir una conclusión jurídica real?"
                ),
                description=(
                    "Problema diseñado para probar relaciones entre hechos, pruebas y fuentes "
                    "expresamente sintéticas."
                ),
                status=LegalIssueStatus.UNDER_ANALYSIS,
            )
        )
        issue_remedy = repository.add_legal_issue(
            LegalIssueCreate(
                case_id=case.id,
                title="Consecuencia contractual demostrativa",
                question=(
                    "¿Qué consecuencias hipotéticas podrían organizarse si el incumplimiento "
                    "simulado llegara a acreditarse?"
                ),
                description="Ejercicio de estructura argumentativa, no asesoría jurídica.",
                status=LegalIssueStatus.OPEN,
            )
        )

        norm_performance = repository.add_norm(
            NormCreate(
                case_id=case.id,
                jurisdiction="Escenario sintético",
                matter="Obligaciones contractuales",
                instrument="Regla contractual sintética DEMO-R1",
                article="Cláusula demo 4",
                text=(
                    "Regla ficticia: el servicio deberá marcarse como entregado en la fecha "
                    "establecida, salvo modificación documentada por ambas partes."
                ),
                hierarchy=NormHierarchy.CONTRACTUAL,
                publication_date=None,
                valid_from=date(2026, 1, 10),
                valid_to=None,
                version_label="Versión demo 1",
                source_reference="DEMO-R1; no corresponde a legislación vigente",
                notes="Fuente sintética para probar el motor de relaciones.",
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )
        norm_refund = repository.add_norm(
            NormCreate(
                case_id=case.id,
                jurisdiction="Escenario sintético",
                matter="Obligaciones contractuales",
                instrument="Regla contractual sintética DEMO-R2",
                article="Cláusula demo 7",
                text=(
                    "Regla ficticia: ante una falta de entrega acreditada, el anticipo podrá "
                    "marcarse para revisión y eventual devolución simulada."
                ),
                hierarchy=NormHierarchy.CONTRACTUAL,
                publication_date=None,
                valid_from=date(2026, 1, 10),
                valid_to=None,
                version_label="Versión demo 1",
                source_reference="DEMO-R2; no corresponde a legislación vigente",
                notes="No usar como fundamento jurídico real.",
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )
        jurisprudence = repository.add_jurisprudence(
            JurisprudenceCreate(
                case_id=case.id,
                court="Órgano jurisdiccional sintético",
                identifier="DEMO-JUR-001",
                jurisdiction="Escenario sintético",
                matter="Obligaciones contractuales",
                decision_date=date(2025, 11, 20),
                relevant_facts="Supuesto ficticio sobre entrega tardía y modificación discutida.",
                legal_question=(
                    "Cómo organizar la valoración de una modificación contractual controvertida."
                ),
                criterion=(
                    "Criterio ficticio: distinguir el acuerdo original, la modificación alegada "
                    "y la evidencia disponible antes de formular una conclusión."
                ),
                decision="Resultado completamente sintético y sin efecto jurídico.",
                interpreted_norms="DEMO-R1 y DEMO-R2",
                authority=JurisprudenceAuthority.PENDING_VERIFICATION,
                source_reference="DEMO-JUR-001; fuente inexistente fuera de la demostración",
                similarities="Entrega tardía y discusión sobre modificación del plazo.",
                differences="No existen personas, documentos ni procedimiento reales.",
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )
        doctrine = repository.add_doctrine(
            DoctrineCreate(
                case_id=case.id,
                author="Autoría Sintética Demo",
                work_title="Manual ficticio de organización argumentativa",
                edition="Edición demo",
                publication_year=2026,
                concept="Trazabilidad argumentativa",
                position_summary=(
                    "Una conclusión demostrativa debe conservar vínculos explícitos con los "
                    "hechos, las pruebas y las fuentes que la sostienen."
                ),
                excerpt="Fragmento generado; no procede de una obra publicada.",
                citation="Autoría Sintética Demo (2026), referencia ficticia.",
                argumentative_function=(
                    "Mostrar cómo una fuente doctrinal contextualiza el método sin sustituir "
                    "la revisión humana."
                ),
                source_reference="DEMO-DOC-001; fuente sintética",
            ),
            original_file_name=None,
            stored_file_name=None,
            file_sha256=None,
            file_size=None,
        )

        repository.link_issue_source(
            IssueSourceLinkCreate(
                case_id=case.id,
                issue_id=issue_breach.id,
                source_type=LegalSourceType.NORM,
                source_id=norm_performance.id,
                orientation=SourceOrientation.SUPPORTS,
                applicability="Modela el plazo y la exigencia de modificación documentada.",
                notes="Aplicación estrictamente demostrativa.",
            )
        )
        repository.link_issue_source(
            IssueSourceLinkCreate(
                case_id=case.id,
                issue_id=issue_breach.id,
                source_type=LegalSourceType.JURISPRUDENCE,
                source_id=jurisprudence.id,
                orientation=SourceOrientation.CONTEXTUAL,
                applicability="Ilustra la separación entre acuerdo, alegación y evidencia.",
                notes="Criterio sintético pendiente de verificación por definición.",
            )
        )
        repository.link_issue_source(
            IssueSourceLinkCreate(
                case_id=case.id,
                issue_id=issue_breach.id,
                source_type=LegalSourceType.DOCTRINE,
                source_id=doctrine.id,
                orientation=SourceOrientation.CONTEXTUAL,
                applicability="Apoya la trazabilidad metodológica del análisis.",
                notes="No reemplaza una fuente jurídica real.",
            )
        )
        repository.link_issue_source(
            IssueSourceLinkCreate(
                case_id=case.id,
                issue_id=issue_remedy.id,
                source_type=LegalSourceType.NORM,
                source_id=norm_refund.id,
                orientation=SourceOrientation.SUPPORTS,
                applicability="Permite ensayar una consecuencia contractual hipotética.",
                notes="Regla ficticia para demostración pública.",
            )
        )

        counts = {
            "cases": len(repository.list_cases()),
            "parties": len(repository.list_parties(case.id)),
            "facts": len(repository.list_facts(case.id)),
            "evidence": len(repository.list_evidence(case.id)),
            "fact_evidence_links": len(repository.list_fact_evidence_links(case.id)),
            "legal_issues": len(repository.list_legal_issues(case.id)),
            "norms": len(repository.list_norms(case.id)),
            "jurisprudence": len(repository.list_jurisprudence(case.id)),
            "doctrine": len(repository.list_doctrine(case.id)),
            "issue_source_links": len(repository.list_issue_source_links(case.id)),
        }
        _checkpoint(temporary)
        if target.exists():
            _remove_sqlite_files(target)
        os.replace(temporary, target)
        _remove_sqlite_files(temporary)
    except Exception:
        _remove_sqlite_files(temporary)
        raise

    return DemoDatabaseResult(
        database_name=output_path.name,
        case_title=case.title,
        counts=counts,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera una base SQLite sintética para la demo pública de IUS-Razón."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DEMO_DB,
        help="Ruta de salida. Predeterminado: data/ius_razon_demo.db",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reconstruye la base aunque el archivo de salida ya exista.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecuta el generador y muestra únicamente un resumen no sensible."""

    args = _build_parser().parse_args(argv)
    try:
        result = build_demo_database(args.output, force=args.force)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0
