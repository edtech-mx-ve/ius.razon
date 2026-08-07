from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any
from uuid import uuid4

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

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
    AuditEventRecord,
    CaseCreate,
    CaseRecord,
    DoctrineCreate,
    DoctrineRecord,
    EvidenceCreate,
    EvidenceRecord,
    FactCreate,
    FactEvidenceLinkView,
    FactRecord,
    IssueSourceLinkCreate,
    IssueSourceLinkView,
    JurisprudenceCreate,
    JurisprudenceRecord,
    LegalIssueCreate,
    LegalIssueRecord,
    NormCreate,
    NormRecord,
    PartyCreate,
    PartyRecord,
    utc_now,
)
from ius_razon.persistence.sqlite_repository import (
    ConflictError,
    NotFoundError,
    RepositoryError,
)


class PostgresRepository:
    """Repositorio SQLite con transacciones, auditoría y claves foráneas."""

    _CODE_TABLES = {
        "facts": "H",
        "evidence": "P",
        "legal_issues": "PJ",
        "norms": "N",
        "jurisprudence": "J",
        "doctrine": "D",
    }

    def __init__(self, database_url: str) -> None:
        cleaned = database_url.strip()
        if not cleaned:
            raise ValueError("database_url no puede estar vacía.")
        self._database_url = cleaned

    @contextmanager
    def _connection(self) -> Iterator[Connection[dict[str, Any]]]:
        connection: Connection[dict[str, Any]] = psycopg.connect(
            self._database_url,
            row_factory=dict_row,
            connect_timeout=20,
        )
        try:
            yield connection
            connection.commit()
        except psycopg.Error as exc:
            connection.rollback()
            raise RepositoryError(
                "La operación de base de datos no pudo completarse."
            ) from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT to_regclass('public.cases') AS table_name"
            ).fetchone()
            if row is None or row["table_name"] is None:
                raise RepositoryError(
                    "El esquema PostgreSQL de IUS-Razón no está inicializado."
                )
            self._seed_code_sequences(connection)

    def create_case(self, payload: CaseCreate) -> CaseRecord:
        case_id = str(uuid4())
        now = utc_now()
        values = (
            case_id,
            payload.title,
            payload.description,
            payload.matter,
            payload.jurisdiction,
            payload.location,
            payload.opened_on.isoformat(),
            payload.status.value,
            payload.objective,
            payload.user_role,
            payload.confidentiality.value,
            now.isoformat(),
            now.isoformat(),
        )
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO cases (
                    id, title, description, matter, jurisdiction, location, opened_on,
                    status, objective, user_role, confidentiality, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                values,
            )
            self._insert_audit(
                connection,
                case_id=case_id,
                event_type="case.created",
                entity_type="case",
                entity_id=case_id,
                detail={"matter": payload.matter, "status": payload.status.value},
            )
        return self.get_case(case_id)

    def list_cases(self) -> list[CaseRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM cases ORDER BY updated_at DESC"
            ).fetchall()
        return [self._row_to_case(row) for row in rows]

    def get_case(self, case_id: str) -> CaseRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM cases WHERE id = %s", (case_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("El expediente no existe.")
        return self._row_to_case(row)

    def add_party(self, payload: PartyCreate) -> PartyRecord:
        self.get_case(payload.case_id)
        party_id = str(uuid4())
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO parties (
                    id, case_id, name_alias, party_type, legal_role, representation,
                    claim, position, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    party_id,
                    payload.case_id,
                    payload.name_alias,
                    payload.party_type.value,
                    payload.legal_role.value,
                    payload.representation,
                    payload.claim,
                    payload.position,
                    now.isoformat(),
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="party.created",
                entity_type="party",
                entity_id=party_id,
                detail={"role": payload.legal_role.value},
            )
        return self.get_party(party_id)

    def get_party(self, party_id: str) -> PartyRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM parties WHERE id = %s", (party_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("La parte no existe.")
        return self._row_to_party(row)

    def list_parties(self, case_id: str) -> list[PartyRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM parties WHERE case_id = %s ORDER BY created_at",
                (case_id,),
            ).fetchall()
        return [self._row_to_party(row) for row in rows]

    def add_fact(self, payload: FactCreate) -> FactRecord:
        self.get_case(payload.case_id)
        if payload.actor_party_id:
            party = self.get_party(payload.actor_party_id)
            if party.case_id != payload.case_id:
                raise RepositoryError("La parte actora pertenece a otro expediente.")

        fact_id = str(uuid4())
        code = self._next_code("facts", payload.case_id)
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO facts (
                    id, case_id, code, description, event_date, actor_party_id, action,
                    object_text, place, source, status, controversy_level, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    fact_id,
                    payload.case_id,
                    code,
                    payload.description,
                    payload.event_date.isoformat() if payload.event_date else None,
                    payload.actor_party_id,
                    payload.action,
                    payload.object_text,
                    payload.place,
                    payload.source,
                    payload.status.value,
                    payload.controversy_level,
                    now.isoformat(),
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="fact.created",
                entity_type="fact",
                entity_id=fact_id,
                detail={"code": code, "status": payload.status.value},
            )
        return self.get_fact(fact_id)

    def get_fact(self, fact_id: str) -> FactRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM facts WHERE id = %s", (fact_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("El hecho no existe.")
        return self._row_to_fact(row)

    def list_facts(self, case_id: str) -> list[FactRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM facts
                WHERE case_id = %s
                ORDER BY event_date IS NULL, event_date, created_at
                """,
                (case_id,),
            ).fetchall()
        return [self._row_to_fact(row) for row in rows]

    def add_evidence(
        self,
        payload: EvidenceCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> EvidenceRecord:
        self.get_case(payload.case_id)
        if payload.offering_party_id:
            party = self.get_party(payload.offering_party_id)
            if party.case_id != payload.case_id:
                raise RepositoryError("La parte oferente pertenece a otro expediente.")

        evidence_id = str(uuid4())
        code = self._next_code("evidence", payload.case_id)
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO evidence (
                    id, case_id, code, evidence_type, description, origin, evidence_date,
                    integrity_statement, offering_party_id, objections, observations,
                    evaluation_status, original_file_name, stored_file_name, file_sha256,
                    file_size, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    evidence_id,
                    payload.case_id,
                    code,
                    payload.evidence_type.value,
                    payload.description,
                    payload.origin,
                    payload.evidence_date.isoformat() if payload.evidence_date else None,
                    payload.integrity_statement,
                    payload.offering_party_id,
                    payload.objections,
                    payload.observations,
                    payload.evaluation_status.value,
                    original_file_name,
                    stored_file_name,
                    file_sha256,
                    file_size,
                    now.isoformat(),
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="evidence.created",
                entity_type="evidence",
                entity_id=evidence_id,
                detail={
                    "code": code,
                    "type": payload.evidence_type.value,
                    "has_file": stored_file_name is not None,
                },
            )
        return self.get_evidence(evidence_id)

    def get_evidence(self, evidence_id: str) -> EvidenceRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM evidence WHERE id = %s", (evidence_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("La prueba no existe.")
        return self._row_to_evidence(row)

    def list_evidence(self, case_id: str) -> list[EvidenceRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM evidence WHERE case_id = %s ORDER BY created_at",
                (case_id,),
            ).fetchall()
        return [self._row_to_evidence(row) for row in rows]

    def link_fact_evidence(
        self,
        *,
        case_id: str,
        fact_id: str,
        evidence_id: str,
        purpose: str | None,
    ) -> None:
        fact = self.get_fact(fact_id)
        evidence = self.get_evidence(evidence_id)
        if fact.case_id != case_id or evidence.case_id != case_id:
            raise RepositoryError("El hecho y la prueba deben pertenecer al expediente activo.")

        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO fact_evidence (fact_id, evidence_id, purpose)
                VALUES (%s, %s, %s)
                ON CONFLICT(fact_id, evidence_id) DO UPDATE SET purpose = excluded.purpose
                """,
                (fact_id, evidence_id, purpose),
            )
            self._touch_case(connection, case_id)
            self._insert_audit(
                connection,
                case_id=case_id,
                event_type="fact_evidence.linked",
                entity_type="fact_evidence",
                entity_id=None,
                detail={"fact_id": fact_id, "evidence_id": evidence_id},
            )

    def list_fact_evidence_links(self, case_id: str) -> list[FactEvidenceLinkView]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT fe.fact_id, fe.evidence_id, fe.purpose,
                       f.code AS fact_code, e.code AS evidence_code
                FROM fact_evidence fe
                JOIN facts f ON f.id = fe.fact_id
                JOIN evidence e ON e.id = fe.evidence_id
                WHERE f.case_id = %s AND e.case_id = %s
                ORDER BY f.code, e.code
                """,
                (case_id, case_id),
            ).fetchall()
        return [
            FactEvidenceLinkView(
                fact_id=row["fact_id"],
                evidence_id=row["evidence_id"],
                purpose=row["purpose"],
                fact_code=row["fact_code"],
                evidence_code=row["evidence_code"],
            )
            for row in rows
        ]

    def add_legal_issue(self, payload: LegalIssueCreate) -> LegalIssueRecord:
        self.get_case(payload.case_id)
        issue_id = str(uuid4())
        code = self._next_code("legal_issues", payload.case_id)
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO legal_issues (
                    id, case_id, code, title, question, description, status,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    issue_id,
                    payload.case_id,
                    code,
                    payload.title,
                    payload.question,
                    payload.description,
                    payload.status.value,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="legal_issue.created",
                entity_type="legal_issue",
                entity_id=issue_id,
                detail={"code": code, "status": payload.status.value},
            )
        return self.get_legal_issue(issue_id)

    def get_legal_issue(self, issue_id: str) -> LegalIssueRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM legal_issues WHERE id = %s", (issue_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("El problema jurídico no existe.")
        return self._row_to_legal_issue(row)

    def list_legal_issues(self, case_id: str) -> list[LegalIssueRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM legal_issues WHERE case_id = %s ORDER BY code",
                (case_id,),
            ).fetchall()
        return [self._row_to_legal_issue(row) for row in rows]

    def add_norm(
        self,
        payload: NormCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> NormRecord:
        self.get_case(payload.case_id)
        norm_id = str(uuid4())
        code = self._next_code("norms", payload.case_id)
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO norms (
                    id, case_id, code, jurisdiction, matter, instrument, article, text,
                    hierarchy, publication_date, valid_from, valid_to, version_label,
                    source_reference, notes, original_file_name, stored_file_name,
                    file_sha256, file_size, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    norm_id,
                    payload.case_id,
                    code,
                    payload.jurisdiction,
                    payload.matter,
                    payload.instrument,
                    payload.article,
                    payload.text,
                    payload.hierarchy.value,
                    self._date_to_text(payload.publication_date),
                    self._date_to_text(payload.valid_from),
                    self._date_to_text(payload.valid_to),
                    payload.version_label,
                    payload.source_reference,
                    payload.notes,
                    original_file_name,
                    stored_file_name,
                    file_sha256,
                    file_size,
                    now.isoformat(),
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="norm.created",
                entity_type="norm",
                entity_id=norm_id,
                detail={"code": code, "instrument": payload.instrument},
            )
        return self.get_norm(norm_id)

    def get_norm(self, norm_id: str) -> NormRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM norms WHERE id = %s", (norm_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("La norma no existe.")
        return self._row_to_norm(row)

    def list_norms(self, case_id: str) -> list[NormRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM norms WHERE case_id = %s ORDER BY code",
                (case_id,),
            ).fetchall()
        return [self._row_to_norm(row) for row in rows]

    def add_jurisprudence(
        self,
        payload: JurisprudenceCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> JurisprudenceRecord:
        self.get_case(payload.case_id)
        jurisprudence_id = str(uuid4())
        code = self._next_code("jurisprudence", payload.case_id)
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO jurisprudence (
                    id, case_id, code, court, identifier, jurisdiction, matter,
                    decision_date, relevant_facts, legal_question, criterion, decision,
                    interpreted_norms, authority, source_reference, similarities,
                    differences, original_file_name, stored_file_name, file_sha256,
                    file_size, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    jurisprudence_id,
                    payload.case_id,
                    code,
                    payload.court,
                    payload.identifier,
                    payload.jurisdiction,
                    payload.matter,
                    self._date_to_text(payload.decision_date),
                    payload.relevant_facts,
                    payload.legal_question,
                    payload.criterion,
                    payload.decision,
                    payload.interpreted_norms,
                    payload.authority.value,
                    payload.source_reference,
                    payload.similarities,
                    payload.differences,
                    original_file_name,
                    stored_file_name,
                    file_sha256,
                    file_size,
                    now.isoformat(),
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="jurisprudence.created",
                entity_type="jurisprudence",
                entity_id=jurisprudence_id,
                detail={"code": code, "identifier": payload.identifier},
            )
        return self.get_jurisprudence(jurisprudence_id)

    def get_jurisprudence(self, jurisprudence_id: str) -> JurisprudenceRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM jurisprudence WHERE id = %s",
                (jurisprudence_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError("La jurisprudencia no existe.")
        return self._row_to_jurisprudence(row)

    def list_jurisprudence(self, case_id: str) -> list[JurisprudenceRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM jurisprudence WHERE case_id = %s ORDER BY code",
                (case_id,),
            ).fetchall()
        return [self._row_to_jurisprudence(row) for row in rows]

    def add_doctrine(
        self,
        payload: DoctrineCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> DoctrineRecord:
        self.get_case(payload.case_id)
        doctrine_id = str(uuid4())
        code = self._next_code("doctrine", payload.case_id)
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO doctrine (
                    id, case_id, code, author, work_title, edition, publication_year,
                    concept, position_summary, excerpt, citation, argumentative_function,
                    source_reference, original_file_name, stored_file_name, file_sha256,
                    file_size, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    doctrine_id,
                    payload.case_id,
                    code,
                    payload.author,
                    payload.work_title,
                    payload.edition,
                    payload.publication_year,
                    payload.concept,
                    payload.position_summary,
                    payload.excerpt,
                    payload.citation,
                    payload.argumentative_function,
                    payload.source_reference,
                    original_file_name,
                    stored_file_name,
                    file_sha256,
                    file_size,
                    now.isoformat(),
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="doctrine.created",
                entity_type="doctrine",
                entity_id=doctrine_id,
                detail={"code": code, "author": payload.author},
            )
        return self.get_doctrine(doctrine_id)

    def get_doctrine(self, doctrine_id: str) -> DoctrineRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM doctrine WHERE id = %s", (doctrine_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("La fuente doctrinal no existe.")
        return self._row_to_doctrine(row)

    def list_doctrine(self, case_id: str) -> list[DoctrineRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM doctrine WHERE case_id = %s ORDER BY code",
                (case_id,),
            ).fetchall()
        return [self._row_to_doctrine(row) for row in rows]

    def link_issue_source(self, payload: IssueSourceLinkCreate) -> None:
        issue = self.get_legal_issue(payload.issue_id)
        source_case_id, _, _ = self._source_identity(
            payload.source_type,
            payload.source_id,
        )
        if issue.case_id != payload.case_id or source_case_id != payload.case_id:
            raise RepositoryError(
                "El problema jurídico y la fuente deben pertenecer al expediente activo."
            )

        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO issue_source_links (
                    issue_id, source_type, source_id, orientation, applicability,
                    notes, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(issue_id, source_type, source_id) DO UPDATE SET
                    orientation = excluded.orientation,
                    applicability = excluded.applicability,
                    notes = excluded.notes,
                    created_at = excluded.created_at
                """,
                (
                    payload.issue_id,
                    payload.source_type.value,
                    payload.source_id,
                    payload.orientation.value,
                    payload.applicability,
                    payload.notes,
                    utc_now().isoformat(),
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="issue_source.linked",
                entity_type="issue_source",
                entity_id=None,
                detail={
                    "issue_id": payload.issue_id,
                    "source_type": payload.source_type.value,
                    "source_id": payload.source_id,
                },
            )

    def list_issue_source_links(self, case_id: str) -> list[IssueSourceLinkView]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT isl.issue_id, isl.source_type, isl.source_id, isl.orientation,
                       isl.applicability, isl.notes, li.code AS issue_code,
                       li.title AS issue_title
                FROM issue_source_links isl
                JOIN legal_issues li ON li.id = isl.issue_id
                WHERE li.case_id = %s
                ORDER BY li.code, isl.source_type, isl.created_at
                """,
                (case_id,),
            ).fetchall()

        result: list[IssueSourceLinkView] = []
        for row in rows:
            source_type = LegalSourceType(row["source_type"])
            source_case_id, source_code, source_title = self._source_identity(
                source_type,
                row["source_id"],
            )
            if source_case_id != case_id:
                continue
            result.append(
                IssueSourceLinkView(
                    case_id=case_id,
                    issue_id=row["issue_id"],
                    source_type=source_type,
                    source_id=row["source_id"],
                    orientation=SourceOrientation(row["orientation"]),
                    applicability=row["applicability"],
                    notes=row["notes"],
                    issue_code=row["issue_code"],
                    issue_title=row["issue_title"],
                    source_code=source_code,
                    source_title=source_title,
                )
            )
        return result


    def update_legal_issue(
        self,
        issue_id: str,
        payload: LegalIssueCreate,
    ) -> LegalIssueRecord:
        existing = self.get_legal_issue(issue_id)
        if existing.case_id != payload.case_id:
            raise RepositoryError("El problema jurídico no pertenece al expediente activo.")

        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE legal_issues
                SET title = %s, question = %s, description = %s, status = %s, updated_at = %s
                WHERE id = %s
                """,
                (
                    payload.title,
                    payload.question,
                    payload.description,
                    payload.status.value,
                    now.isoformat(),
                    issue_id,
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="legal_issue.updated",
                entity_type="legal_issue",
                entity_id=issue_id,
                detail={"code": existing.code, "status": payload.status.value},
            )
        return self.get_legal_issue(issue_id)

    def delete_legal_issue(self, issue_id: str, case_id: str) -> None:
        existing = self.get_legal_issue(issue_id)
        if existing.case_id != case_id:
            raise RepositoryError("El problema jurídico no pertenece al expediente activo.")
        if self._issue_link_count(issue_id) > 0:
            raise ConflictError(
                "No se puede eliminar el problema jurídico porque conserva fuentes vinculadas."
            )

        with self._connection() as connection:
            connection.execute("DELETE FROM legal_issues WHERE id = %s", (issue_id,))
            self._touch_case(connection, case_id)
            self._insert_audit(
                connection,
                case_id=case_id,
                event_type="legal_issue.deleted",
                entity_type="legal_issue",
                entity_id=issue_id,
                detail={"code": existing.code},
            )

    def update_norm(
        self,
        norm_id: str,
        payload: NormCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> NormRecord:
        existing = self.get_norm(norm_id)
        if existing.case_id != payload.case_id:
            raise RepositoryError("La norma no pertenece al expediente activo.")

        with self._connection() as connection:
            connection.execute(
                """
                UPDATE norms
                SET jurisdiction = %s, matter = %s, instrument = %s, article = %s, text = %s,
                    hierarchy = %s, publication_date = %s, valid_from = %s, valid_to = %s,
                    version_label = %s, source_reference = %s, notes = %s,
                    original_file_name = %s, stored_file_name = %s, file_sha256 = %s,
                    file_size = %s
                WHERE id = %s
                """,
                (
                    payload.jurisdiction,
                    payload.matter,
                    payload.instrument,
                    payload.article,
                    payload.text,
                    payload.hierarchy.value,
                    self._date_to_text(payload.publication_date),
                    self._date_to_text(payload.valid_from),
                    self._date_to_text(payload.valid_to),
                    payload.version_label,
                    payload.source_reference,
                    payload.notes,
                    original_file_name,
                    stored_file_name,
                    file_sha256,
                    file_size,
                    norm_id,
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="norm.updated",
                entity_type="norm",
                entity_id=norm_id,
                detail={"code": existing.code, "instrument": payload.instrument},
            )
        return self.get_norm(norm_id)

    def update_jurisprudence(
        self,
        jurisprudence_id: str,
        payload: JurisprudenceCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> JurisprudenceRecord:
        existing = self.get_jurisprudence(jurisprudence_id)
        if existing.case_id != payload.case_id:
            raise RepositoryError("La jurisprudencia no pertenece al expediente activo.")

        with self._connection() as connection:
            connection.execute(
                """
                UPDATE jurisprudence
                SET court = %s, identifier = %s, jurisdiction = %s, matter = %s,
                    decision_date = %s, relevant_facts = %s, legal_question = %s,
                    criterion = %s, decision = %s, interpreted_norms = %s, authority = %s,
                    source_reference = %s, similarities = %s, differences = %s,
                    original_file_name = %s, stored_file_name = %s, file_sha256 = %s,
                    file_size = %s
                WHERE id = %s
                """,
                (
                    payload.court,
                    payload.identifier,
                    payload.jurisdiction,
                    payload.matter,
                    self._date_to_text(payload.decision_date),
                    payload.relevant_facts,
                    payload.legal_question,
                    payload.criterion,
                    payload.decision,
                    payload.interpreted_norms,
                    payload.authority.value,
                    payload.source_reference,
                    payload.similarities,
                    payload.differences,
                    original_file_name,
                    stored_file_name,
                    file_sha256,
                    file_size,
                    jurisprudence_id,
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="jurisprudence.updated",
                entity_type="jurisprudence",
                entity_id=jurisprudence_id,
                detail={"code": existing.code, "identifier": payload.identifier},
            )
        return self.get_jurisprudence(jurisprudence_id)

    def update_doctrine(
        self,
        doctrine_id: str,
        payload: DoctrineCreate,
        *,
        original_file_name: str | None,
        stored_file_name: str | None,
        file_sha256: str | None,
        file_size: int | None,
    ) -> DoctrineRecord:
        existing = self.get_doctrine(doctrine_id)
        if existing.case_id != payload.case_id:
            raise RepositoryError("La doctrina no pertenece al expediente activo.")

        with self._connection() as connection:
            connection.execute(
                """
                UPDATE doctrine
                SET author = %s, work_title = %s, edition = %s, publication_year = %s,
                    concept = %s, position_summary = %s, excerpt = %s, citation = %s,
                    argumentative_function = %s, source_reference = %s,
                    original_file_name = %s, stored_file_name = %s, file_sha256 = %s,
                    file_size = %s
                WHERE id = %s
                """,
                (
                    payload.author,
                    payload.work_title,
                    payload.edition,
                    payload.publication_year,
                    payload.concept,
                    payload.position_summary,
                    payload.excerpt,
                    payload.citation,
                    payload.argumentative_function,
                    payload.source_reference,
                    original_file_name,
                    stored_file_name,
                    file_sha256,
                    file_size,
                    doctrine_id,
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="doctrine.updated",
                entity_type="doctrine",
                entity_id=doctrine_id,
                detail={"code": existing.code, "author": payload.author},
            )
        return self.get_doctrine(doctrine_id)

    def delete_source(
        self,
        *,
        case_id: str,
        source_type: LegalSourceType,
        source_id: str,
    ) -> None:
        source_case_id, source_code, source_title = self._source_identity(
            source_type,
            source_id,
        )
        if source_case_id != case_id:
            raise RepositoryError("La fuente no pertenece al expediente activo.")
        if self._source_link_count(source_type, source_id) > 0:
            raise ConflictError(
                "No se puede eliminar la fuente porque conserva problemas jurídicos vinculados."
            )

        table = {
            LegalSourceType.NORM: "norms",
            LegalSourceType.JURISPRUDENCE: "jurisprudence",
            LegalSourceType.DOCTRINE: "doctrine",
        }[source_type]
        with self._connection() as connection:
            connection.execute(f"DELETE FROM {table} WHERE id = %s", (source_id,))
            self._touch_case(connection, case_id)
            self._insert_audit(
                connection,
                case_id=case_id,
                event_type="legal_source.deleted",
                entity_type=source_type.value.lower(),
                entity_id=source_id,
                detail={
                    "code": source_code,
                    "source_type": source_type.value,
                    "title": source_title,
                },
            )

    def update_issue_source_link(self, payload: IssueSourceLinkCreate) -> None:
        issue = self.get_legal_issue(payload.issue_id)
        source_case_id, _, _ = self._source_identity(
            payload.source_type,
            payload.source_id,
        )
        if issue.case_id != payload.case_id or source_case_id != payload.case_id:
            raise RepositoryError(
                "El problema jurídico y la fuente deben pertenecer al expediente activo."
            )

        with self._connection() as connection:
            existing = connection.execute(
                """
                SELECT 1 FROM issue_source_links
                WHERE issue_id = %s AND source_type = %s AND source_id = %s
                """,
                (
                    payload.issue_id,
                    payload.source_type.value,
                    payload.source_id,
                ),
            ).fetchone()
            if existing is None:
                raise NotFoundError("El vínculo problema–fuente no existe.")
            connection.execute(
                """
                UPDATE issue_source_links
                SET orientation = %s, applicability = %s, notes = %s, created_at = %s
                WHERE issue_id = %s AND source_type = %s AND source_id = %s
                """,
                (
                    payload.orientation.value,
                    payload.applicability,
                    payload.notes,
                    utc_now().isoformat(),
                    payload.issue_id,
                    payload.source_type.value,
                    payload.source_id,
                ),
            )
            self._touch_case(connection, payload.case_id)
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="issue_source.updated",
                entity_type="issue_source",
                entity_id=None,
                detail={
                    "issue_id": payload.issue_id,
                    "source_type": payload.source_type.value,
                    "source_id": payload.source_id,
                },
            )

    def unlink_issue_source(
        self,
        *,
        case_id: str,
        issue_id: str,
        source_type: LegalSourceType,
        source_id: str,
    ) -> None:
        issue = self.get_legal_issue(issue_id)
        source_case_id, _, _ = self._source_identity(source_type, source_id)
        if issue.case_id != case_id or source_case_id != case_id:
            raise RepositoryError(
                "El problema jurídico y la fuente deben pertenecer al expediente activo."
            )

        with self._connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM issue_source_links
                WHERE issue_id = %s AND source_type = %s AND source_id = %s
                """,
                (issue_id, source_type.value, source_id),
            )
            if cursor.rowcount == 0:
                raise NotFoundError("El vínculo problema–fuente no existe.")
            self._touch_case(connection, case_id)
            self._insert_audit(
                connection,
                case_id=case_id,
                event_type="issue_source.unlinked",
                entity_type="issue_source",
                entity_id=None,
                detail={
                    "issue_id": issue_id,
                    "source_type": source_type.value,
                    "source_id": source_id,
                },
            )

    def _issue_link_count(self, issue_id: str) -> int:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM issue_source_links WHERE issue_id = %s",
                (issue_id,),
            ).fetchone()
        if row is None:
            raise RepositoryError(
                "No fue posible obtener el contador solicitado."
            )
        return int(row["total"])

    def _source_link_count(
        self,
        source_type: LegalSourceType,
        source_id: str,
    ) -> int:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total FROM issue_source_links
                WHERE source_type = %s AND source_id = %s
                """,
                (source_type.value, source_id),
            ).fetchone()
        if row is None:
            raise RepositoryError(
                "No fue posible obtener el contador solicitado."
            )
        return int(row["total"])

    def count_by_case(self, table: str, case_id: str) -> int:
        allowed = {
            "parties",
            "facts",
            "evidence",
            "legal_issues",
            "norms",
            "jurisprudence",
            "doctrine",
        }
        if table not in allowed:
            raise ValueError("Tabla no permitida.")
        with self._connection() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS total FROM {table} WHERE case_id = %s",
                (case_id,),
            ).fetchone()
        if row is None:
            raise RepositoryError(
                "No fue posible obtener el contador solicitado."
            )
        return int(row["total"])

    def count_links(self, case_id: str) -> int:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM fact_evidence fe
                JOIN facts f ON f.id = fe.fact_id
                WHERE f.case_id = %s
                """,
                (case_id,),
            ).fetchone()
        if row is None:
            raise RepositoryError(
                "No fue posible obtener el contador solicitado."
            )
        return int(row["total"])

    def count_issue_source_links(self, case_id: str) -> int:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM issue_source_links isl
                JOIN legal_issues li ON li.id = isl.issue_id
                WHERE li.case_id = %s
                """,
                (case_id,),
            ).fetchone()
        if row is None:
            raise RepositoryError(
                "No fue posible obtener el contador solicitado."
            )
        return int(row["total"])

    def list_audit_events(self, case_id: str, limit: int = 50) -> list[AuditEventRecord]:
        safe_limit = max(1, min(limit, 200))
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM audit_events
                WHERE case_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (case_id, safe_limit),
            ).fetchall()
        return [
            AuditEventRecord(
                id=row["id"],
                case_id=row["case_id"],
                event_type=row["event_type"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                detail_json=row["detail_json"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def get_source_identity(
        self,
        source_type: LegalSourceType,
        source_id: str,
    ) -> tuple[str, str, str]:
        """Devuelve expediente, código y título visible de una fuente."""

        return self._source_identity(source_type, source_id)

    def _source_identity(
        self,
        source_type: LegalSourceType,
        source_id: str,
    ) -> tuple[str, str, str]:
        if source_type is LegalSourceType.NORM:
            norm = self.get_norm(source_id)
            return norm.case_id, norm.code, f"{norm.instrument}, {norm.article}"
        if source_type is LegalSourceType.JURISPRUDENCE:
            precedent = self.get_jurisprudence(source_id)
            return precedent.case_id, precedent.code, precedent.identifier
        if source_type is LegalSourceType.DOCTRINE:
            doctrine = self.get_doctrine(source_id)
            return doctrine.case_id, doctrine.code, f"{doctrine.author}: {doctrine.work_title}"
        raise ValueError("Tipo de fuente no soportado.")

    def _next_code(self, table: str, case_id: str) -> str:
        prefix = self._CODE_TABLES.get(table)
        if prefix is None:
            raise ValueError("Tabla no permitida para generar códigos.")

        lock_key = f"ius_razon:{case_id}:{table}"
        with self._connection() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (lock_key,),
            )
            row = connection.execute(
                '''
                SELECT last_value FROM code_sequences
                WHERE case_id = %s AND table_name = %s
                ''',
                (case_id, table),
            ).fetchone()

            if row is None:
                last_value = self._max_existing_code(
                    connection,
                    table,
                    case_id,
                    prefix,
                )
                connection.execute(
                    '''
                    INSERT INTO code_sequences (
                        case_id, table_name, last_value
                    ) VALUES (%s, %s, %s)
                    ''',
                    (case_id, table, last_value),
                )
            else:
                last_value = int(row["last_value"])

            next_value = last_value + 1
            connection.execute(
                '''
                UPDATE code_sequences
                SET last_value = %s
                WHERE case_id = %s AND table_name = %s
                ''',
                (next_value, case_id, table),
            )

        return f"{prefix}-{next_value:03d}"

    def _seed_code_sequences(
        self,
        connection: Connection[dict[str, Any]],
    ) -> None:
        case_rows = connection.execute("SELECT id FROM cases").fetchall()
        for case_row in case_rows:
            case_id = str(case_row["id"])
            for table, prefix in self._CODE_TABLES.items():
                last_value = self._max_existing_code(
                    connection,
                    table,
                    case_id,
                    prefix,
                )
                connection.execute(
                    '''
                    INSERT INTO code_sequences (
                        case_id, table_name, last_value
                    ) VALUES (%s, %s, %s)
                    ON CONFLICT (case_id, table_name) DO NOTHING
                    ''',
                    (case_id, table, last_value),
                )

    @staticmethod
    def _max_existing_code(
        connection: Connection[dict[str, Any]],
        table: str,
        case_id: str,
        prefix: str,
    ) -> int:
        rows = connection.execute(
            f"SELECT code FROM {table} WHERE case_id = %s",
            (case_id,),
        ).fetchall()
        maximum = 0
        marker = f"{prefix}-"
        for row in rows:
            code = str(row["code"])
            if not code.startswith(marker):
                continue
            suffix = code[len(marker) :]
            if suffix.isdigit():
                maximum = max(maximum, int(suffix))
        return maximum

    @staticmethod
    def _touch_case(connection: Connection[dict[str, Any]], case_id: str) -> None:
        connection.execute(
            "UPDATE cases SET updated_at = %s WHERE id = %s",
            (utc_now().isoformat(), case_id),
        )

    @staticmethod
    def _insert_audit(
        connection: Connection[dict[str, Any]],
        *,
        case_id: str | None,
        event_type: str,
        entity_type: str,
        entity_id: str | None,
        detail: dict[str, Any],
    ) -> None:
        connection.execute(
            """
            INSERT INTO audit_events (
                id, case_id, event_type, entity_type, entity_id, detail_json, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid4()),
                case_id,
                event_type,
                entity_type,
                entity_id,
                json.dumps(detail, ensure_ascii=False, sort_keys=True),
                utc_now().isoformat(),
            ),
        )

    @staticmethod
    def _date_to_text(value: date | None) -> str | None:
        return value.isoformat() if value else None

    @staticmethod
    def _text_to_date(value: str | None) -> date | None:
        return date.fromisoformat(value) if value else None

    @staticmethod
    def _row_to_case(row: dict[str, Any]) -> CaseRecord:
        return CaseRecord(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            matter=row["matter"],
            jurisdiction=row["jurisdiction"],
            location=row["location"],
            opened_on=date.fromisoformat(row["opened_on"]),
            status=CaseStatus(row["status"]),
            objective=row["objective"],
            user_role=row["user_role"],
            confidentiality=ConfidentialityLevel(row["confidentiality"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_party(row: dict[str, Any]) -> PartyRecord:
        return PartyRecord(
            id=row["id"],
            case_id=row["case_id"],
            name_alias=row["name_alias"],
            party_type=PartyType(row["party_type"]),
            legal_role=PartyRole(row["legal_role"]),
            representation=row["representation"],
            claim=row["claim"],
            position=row["position"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_fact(row: dict[str, Any]) -> FactRecord:
        return FactRecord(
            id=row["id"],
            case_id=row["case_id"],
            code=row["code"],
            description=row["description"],
            event_date=PostgresRepository._text_to_date(row["event_date"]),
            actor_party_id=row["actor_party_id"],
            action=row["action"],
            object_text=row["object_text"],
            place=row["place"],
            source=row["source"],
            status=FactStatus(row["status"]),
            controversy_level=int(row["controversy_level"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_evidence(row: dict[str, Any]) -> EvidenceRecord:
        return EvidenceRecord(
            id=row["id"],
            case_id=row["case_id"],
            code=row["code"],
            evidence_type=EvidenceType(row["evidence_type"]),
            description=row["description"],
            origin=row["origin"],
            evidence_date=PostgresRepository._text_to_date(row["evidence_date"]),
            integrity_statement=row["integrity_statement"],
            offering_party_id=row["offering_party_id"],
            objections=row["objections"],
            observations=row["observations"],
            evaluation_status=EvidenceEvaluationStatus(row["evaluation_status"]),
            original_file_name=row["original_file_name"],
            stored_file_name=row["stored_file_name"],
            file_sha256=row["file_sha256"],
            file_size=row["file_size"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_legal_issue(row: dict[str, Any]) -> LegalIssueRecord:
        return LegalIssueRecord(
            id=row["id"],
            case_id=row["case_id"],
            code=row["code"],
            title=row["title"],
            question=row["question"],
            description=row["description"],
            status=LegalIssueStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_norm(row: dict[str, Any]) -> NormRecord:
        return NormRecord(
            id=row["id"],
            case_id=row["case_id"],
            code=row["code"],
            jurisdiction=row["jurisdiction"],
            matter=row["matter"],
            instrument=row["instrument"],
            article=row["article"],
            text=row["text"],
            hierarchy=NormHierarchy(row["hierarchy"]),
            publication_date=PostgresRepository._text_to_date(row["publication_date"]),
            valid_from=PostgresRepository._text_to_date(row["valid_from"]),
            valid_to=PostgresRepository._text_to_date(row["valid_to"]),
            version_label=row["version_label"],
            source_reference=row["source_reference"],
            notes=row["notes"],
            original_file_name=row["original_file_name"],
            stored_file_name=row["stored_file_name"],
            file_sha256=row["file_sha256"],
            file_size=row["file_size"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_jurisprudence(row: dict[str, Any]) -> JurisprudenceRecord:
        return JurisprudenceRecord(
            id=row["id"],
            case_id=row["case_id"],
            code=row["code"],
            court=row["court"],
            identifier=row["identifier"],
            jurisdiction=row["jurisdiction"],
            matter=row["matter"],
            decision_date=PostgresRepository._text_to_date(row["decision_date"]),
            relevant_facts=row["relevant_facts"],
            legal_question=row["legal_question"],
            criterion=row["criterion"],
            decision=row["decision"],
            interpreted_norms=row["interpreted_norms"],
            authority=JurisprudenceAuthority(row["authority"]),
            source_reference=row["source_reference"],
            similarities=row["similarities"],
            differences=row["differences"],
            original_file_name=row["original_file_name"],
            stored_file_name=row["stored_file_name"],
            file_sha256=row["file_sha256"],
            file_size=row["file_size"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_doctrine(row: dict[str, Any]) -> DoctrineRecord:
        return DoctrineRecord(
            id=row["id"],
            case_id=row["case_id"],
            code=row["code"],
            author=row["author"],
            work_title=row["work_title"],
            edition=row["edition"],
            publication_year=row["publication_year"],
            concept=row["concept"],
            position_summary=row["position_summary"],
            excerpt=row["excerpt"],
            citation=row["citation"],
            argumentative_function=row["argumentative_function"],
            source_reference=row["source_reference"],
            original_file_name=row["original_file_name"],
            stored_file_name=row["stored_file_name"],
            file_sha256=row["file_sha256"],
            file_size=row["file_size"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
