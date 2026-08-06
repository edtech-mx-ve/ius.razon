from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ius_razon.domain.argumentation_models import (
    ArgumentPosition,
    ArgumentRelationCreate,
    ArgumentRelationRecord,
    ArgumentRelationType,
    ArgumentScenarioCreate,
    ArgumentScenarioRecord,
    ArgumentScenarioUpdate,
    ArgumentStatus,
    LegalArgumentCreate,
    LegalArgumentRecord,
    LegalArgumentUpdate,
    ScenarioStatus,
)
from ius_razon.domain.models import utc_now
from ius_razon.domain.reasoning_models import AssertionValue


class ArgumentationRepositoryError(RuntimeError):
    """Error controlado de persistencia argumental."""


class ArgumentationNotFoundError(ArgumentationRepositoryError):
    """Entidad argumental inexistente."""


class ArgumentationConflictError(ArgumentationRepositoryError):
    """Operación rechazada para preservar relaciones argumentales."""


class ArgumentationRepository:
    """Persistencia de argumentos, contraargumentos y relaciones."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path.resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        """Ruta absoluta de la base activa."""

        return self._db_path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise ArgumentationRepositoryError(
                "La operación argumental no pudo completarse."
            ) from exc
        finally:
            connection.close()

    def initialize(self) -> None:
        """Aplica las migraciones aditivas de argumentación y escenarios."""

        schema = """
        CREATE TABLE IF NOT EXISTS legal_arguments (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            title TEXT NOT NULL,
            position TEXT NOT NULL,
            thesis_key TEXT NOT NULL,
            thesis_statement TEXT NOT NULL,
            thesis_value TEXT NOT NULL,
            claim TEXT NOT NULL,
            reasoning TEXT NOT NULL,
            status TEXT NOT NULL,
            conclusion_id TEXT
                REFERENCES reasoning_conclusions(id) ON DELETE SET NULL,
            fact_codes_json TEXT NOT NULL,
            evidence_codes_json TEXT NOT NULL,
            source_codes_json TEXT NOT NULL,
            rule_codes_json TEXT NOT NULL,
            assertion_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS argument_relations (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            source_argument_id TEXT NOT NULL
                REFERENCES legal_arguments(id) ON DELETE CASCADE,
            target_argument_id TEXT NOT NULL
                REFERENCES legal_arguments(id) ON DELETE CASCADE,
            relation_type TEXT NOT NULL,
            rationale TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(case_id, code),
            UNIQUE(source_argument_id, target_argument_id, relation_type)
        );

        CREATE TABLE IF NOT EXISTS argument_sequences (
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            entity_name TEXT NOT NULL,
            last_value INTEGER NOT NULL CHECK(last_value >= 0),
            PRIMARY KEY(case_id, entity_name)
        );

        CREATE TABLE IF NOT EXISTS argument_scenarios (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            argument_ids_json TEXT NOT NULL,
            assumptions_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE INDEX IF NOT EXISTS idx_legal_arguments_case
            ON legal_arguments(case_id, issue_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_argument_relations_case
            ON argument_relations(case_id, issue_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_argument_relations_source
            ON argument_relations(source_argument_id);
        CREATE INDEX IF NOT EXISTS idx_argument_relations_target
            ON argument_relations(target_argument_id);
        CREATE INDEX IF NOT EXISTS idx_argument_scenarios_case
            ON argument_scenarios(case_id, issue_id, updated_at);
        """
        with self._connection() as connection:
            connection.executescript(schema)

    def validate_case_issue(self, case_id: str, issue_id: str) -> None:
        """Confirma que el problema pertenece al expediente."""

        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM legal_issues
                WHERE id = ? AND case_id = ?
                """,
                (issue_id, case_id),
            ).fetchone()
        if row is None:
            raise ArgumentationNotFoundError(
                "El problema jurídico no pertenece al expediente activo."
            )

    def conclusion_context(
        self,
        conclusion_id: str,
    ) -> dict[str, str | list[str]]:
        """Recupera una conclusión persistida y su contexto de soporte."""

        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT
                    conclusion.id,
                    conclusion.code,
                    conclusion.predicate_key,
                    conclusion.statement,
                    conclusion.value,
                    conclusion.rule_codes_json,
                    conclusion.assertion_codes_json,
                    conclusion.source_codes_json,
                    run.case_id,
                    run.issue_id,
                    run.id AS run_id
                FROM reasoning_conclusions AS conclusion
                JOIN reasoning_runs AS run ON run.id = conclusion.run_id
                WHERE conclusion.id = ?
                """,
                (conclusion_id,),
            ).fetchone()
        if row is None:
            raise ArgumentationNotFoundError(
                "La conclusión seleccionada no existe."
            )
        return {
            "id": str(row["id"]),
            "code": str(row["code"]),
            "predicate_key": str(row["predicate_key"]),
            "statement": str(row["statement"]),
            "value": str(row["value"]),
            "case_id": str(row["case_id"]),
            "issue_id": str(row["issue_id"]),
            "run_id": str(row["run_id"]),
            "rule_codes": self._json_string_list(str(row["rule_codes_json"])),
            "assertion_codes": self._json_string_list(
                str(row["assertion_codes_json"])
            ),
            "source_codes": self._json_string_list(
                str(row["source_codes_json"])
            ),
        }

    def list_conclusion_contexts(
        self,
        case_id: str,
        issue_id: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, str | list[str]]]:
        """Lista conclusiones disponibles para construir argumentos."""

        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT conclusion.id
                FROM reasoning_conclusions AS conclusion
                JOIN reasoning_runs AS run ON run.id = conclusion.run_id
                WHERE run.case_id = ? AND run.issue_id = ?
                ORDER BY run.started_at DESC, conclusion.code
                LIMIT ?
                """,
                (case_id, issue_id, limit),
            ).fetchall()
        return [
            self.conclusion_context(str(row["id"]))
            for row in rows
        ]

    def add_argument(
        self,
        payload: LegalArgumentCreate,
    ) -> LegalArgumentRecord:
        """Persiste un argumento con código estable ARG-###."""

        record_id = str(uuid4())
        now = utc_now()
        with self._connection() as connection:
            code = self._next_code(
                connection,
                payload.case_id,
                "argument",
                "ARG",
            )
            connection.execute(
                """
                INSERT INTO legal_arguments (
                    id, case_id, issue_id, code, title, position,
                    thesis_key, thesis_statement, thesis_value, claim,
                    reasoning, status, conclusion_id, fact_codes_json,
                    evidence_codes_json, source_codes_json, rule_codes_json,
                    assertion_codes_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    payload.case_id,
                    payload.issue_id,
                    code,
                    payload.title,
                    payload.position.value,
                    payload.thesis_key,
                    payload.thesis_statement,
                    payload.thesis_value.value,
                    payload.claim,
                    payload.reasoning,
                    payload.status.value,
                    payload.conclusion_id,
                    self._json_list(payload.fact_codes),
                    self._json_list(payload.evidence_codes),
                    self._json_list(payload.source_codes),
                    self._json_list(payload.rule_codes),
                    self._json_list(payload.assertion_codes),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="argumentation.argument.created",
                entity_type="legal_argument",
                entity_id=record_id,
                detail={
                    "code": code,
                    "position": payload.position.value,
                    "thesis_key": payload.thesis_key,
                },
            )
        return self.get_argument(record_id)

    def get_argument(self, argument_id: str) -> LegalArgumentRecord:
        """Recupera un argumento por identificador interno."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM legal_arguments WHERE id = ?",
                (argument_id,),
            ).fetchone()
        if row is None:
            raise ArgumentationNotFoundError("El argumento no existe.")
        return self._row_to_argument(row)

    def list_arguments(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        include_discarded: bool = False,
    ) -> list[LegalArgumentRecord]:
        """Lista argumentos en orden estable."""

        clauses = ["case_id = ?"]
        parameters: list[object] = [case_id]
        if issue_id is not None:
            clauses.append("issue_id = ?")
            parameters.append(issue_id)
        if not include_discarded:
            clauses.append("status <> ?")
            parameters.append(ArgumentStatus.DISCARDED.value)
        where = " AND ".join(clauses)
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM legal_arguments
                WHERE {where}
                ORDER BY code
                """,
                tuple(parameters),
            ).fetchall()
        return [self._row_to_argument(row) for row in rows]

    def update_argument(
        self,
        argument_id: str,
        payload: LegalArgumentUpdate,
    ) -> LegalArgumentRecord:
        """Actualiza un argumento preservando su código."""

        current = self.get_argument(argument_id)
        now = utc_now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE legal_arguments
                SET title = ?, position = ?, thesis_key = ?,
                    thesis_statement = ?, thesis_value = ?, claim = ?,
                    reasoning = ?, status = ?, conclusion_id = ?,
                    fact_codes_json = ?, evidence_codes_json = ?,
                    source_codes_json = ?, rule_codes_json = ?,
                    assertion_codes_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.title,
                    payload.position.value,
                    payload.thesis_key,
                    payload.thesis_statement,
                    payload.thesis_value.value,
                    payload.claim,
                    payload.reasoning,
                    payload.status.value,
                    payload.conclusion_id,
                    self._json_list(payload.fact_codes),
                    self._json_list(payload.evidence_codes),
                    self._json_list(payload.source_codes),
                    self._json_list(payload.rule_codes),
                    self._json_list(payload.assertion_codes),
                    now.isoformat(),
                    argument_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ArgumentationNotFoundError("El argumento no existe.")
            self._insert_audit(
                connection,
                case_id=current.case_id,
                event_type="argumentation.argument.updated",
                entity_type="legal_argument",
                entity_id=argument_id,
                detail={"code": current.code},
            )
        return self.get_argument(argument_id)

    def delete_argument(
        self,
        argument_id: str,
        *,
        confirmation: str,
    ) -> None:
        """Elimina solo argumentos sin relaciones y con confirmación exacta."""

        current = self.get_argument(argument_id)
        if confirmation.strip().upper() != current.code:
            raise ValueError(
                f"Escribe exactamente {current.code} para confirmar."
            )
        with self._connection() as connection:
            count_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM argument_relations
                WHERE source_argument_id = ? OR target_argument_id = ?
                """,
                (argument_id, argument_id),
            ).fetchone()
            dependency_count = (
                int(count_row["total"]) if count_row is not None else 0
            )
            if dependency_count:
                raise ArgumentationConflictError(
                    "El argumento tiene relaciones. Elimínalas primero."
                )
            scenario_rows = connection.execute(
                """
                SELECT code, argument_ids_json
                FROM argument_scenarios
                WHERE case_id = ? AND issue_id = ?
                """,
                (current.case_id, current.issue_id),
            ).fetchall()
            scenario_codes = [
                str(row["code"])
                for row in scenario_rows
                if argument_id
                in self._json_string_list(str(row["argument_ids_json"]))
            ]
            if scenario_codes:
                raise ArgumentationConflictError(
                    "El argumento está incluido en escenarios: "
                    + ", ".join(scenario_codes)
                    + ". Retíralo de esos escenarios antes de eliminarlo."
                )
            connection.execute(
                "DELETE FROM legal_arguments WHERE id = ?",
                (argument_id,),
            )
            self._insert_audit(
                connection,
                case_id=current.case_id,
                event_type="argumentation.argument.deleted",
                entity_type="legal_argument",
                entity_id=argument_id,
                detail={"code": current.code},
            )

    def add_relation(
        self,
        payload: ArgumentRelationCreate,
    ) -> ArgumentRelationRecord:
        """Crea una relación dirigida entre dos argumentos."""

        source = self.get_argument(payload.source_argument_id)
        target = self.get_argument(payload.target_argument_id)
        if (
            source.case_id != payload.case_id
            or target.case_id != payload.case_id
            or source.issue_id != payload.issue_id
            or target.issue_id != payload.issue_id
        ):
            raise ArgumentationConflictError(
                "Los argumentos deben pertenecer al mismo problema jurídico."
            )
        record_id = str(uuid4())
        now = utc_now()
        with self._connection() as connection:
            code = self._next_code(
                connection,
                payload.case_id,
                "relation",
                "REL",
            )
            try:
                connection.execute(
                    """
                    INSERT INTO argument_relations (
                        id, case_id, issue_id, code, source_argument_id,
                        target_argument_id, relation_type, rationale, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        payload.case_id,
                        payload.issue_id,
                        code,
                        payload.source_argument_id,
                        payload.target_argument_id,
                        payload.relation_type.value,
                        payload.rationale,
                        now.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ArgumentationConflictError(
                    "La relación argumental ya existe."
                ) from exc
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="argumentation.relation.created",
                entity_type="argument_relation",
                entity_id=record_id,
                detail={
                    "code": code,
                    "type": payload.relation_type.value,
                    "source": source.code,
                    "target": target.code,
                },
            )
        return self.get_relation(record_id)

    def get_relation(self, relation_id: str) -> ArgumentRelationRecord:
        """Recupera una relación por identificador."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM argument_relations WHERE id = ?",
                (relation_id,),
            ).fetchone()
        if row is None:
            raise ArgumentationNotFoundError(
                "La relación argumental no existe."
            )
        return self._row_to_relation(row)

    def list_relations(
        self,
        case_id: str,
        issue_id: str | None = None,
    ) -> list[ArgumentRelationRecord]:
        """Lista relaciones argumentales."""

        clauses = ["case_id = ?"]
        parameters: list[object] = [case_id]
        if issue_id is not None:
            clauses.append("issue_id = ?")
            parameters.append(issue_id)
        where = " AND ".join(clauses)
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM argument_relations
                WHERE {where}
                ORDER BY code
                """,
                tuple(parameters),
            ).fetchall()
        return [self._row_to_relation(row) for row in rows]

    def delete_relation(
        self,
        relation_id: str,
        *,
        confirmation: str,
    ) -> None:
        """Elimina una relación con confirmación exacta."""

        current = self.get_relation(relation_id)
        if confirmation.strip().upper() != current.code:
            raise ValueError(
                f"Escribe exactamente {current.code} para confirmar."
            )
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM argument_relations WHERE id = ?",
                (relation_id,),
            )
            self._insert_audit(
                connection,
                case_id=current.case_id,
                event_type="argumentation.relation.deleted",
                entity_type="argument_relation",
                entity_id=relation_id,
                detail={"code": current.code},
            )

    def add_scenario(
        self,
        payload: ArgumentScenarioCreate,
    ) -> ArgumentScenarioRecord:
        """Crea un escenario argumental con código persistente."""

        self.validate_case_issue(payload.case_id, payload.issue_id)
        record_id = str(uuid4())
        now = utc_now()
        with self._connection() as connection:
            code = self._next_code(
                connection,
                payload.case_id,
                "scenario",
                "SCN",
            )
            connection.execute(
                """
                INSERT INTO argument_scenarios (
                    id, case_id, issue_id, code, name, description, status,
                    argument_ids_json, assumptions_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    payload.case_id,
                    payload.issue_id,
                    code,
                    payload.name,
                    payload.description,
                    payload.status.value,
                    self._json_list(payload.argument_ids),
                    self._json_list(payload.assumptions),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="argumentation.scenario.created",
                entity_type="argument_scenario",
                entity_id=record_id,
                detail={
                    "code": code,
                    "argument_count": len(payload.argument_ids),
                },
            )
        return self.get_scenario(record_id)

    def get_scenario(self, scenario_id: str) -> ArgumentScenarioRecord:
        """Recupera un escenario por identificador."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM argument_scenarios WHERE id = ?",
                (scenario_id,),
            ).fetchone()
        if row is None:
            raise ArgumentationNotFoundError(
                "El escenario argumental no existe."
            )
        return self._row_to_scenario(row)

    def list_scenarios(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        include_archived: bool = False,
    ) -> list[ArgumentScenarioRecord]:
        """Lista escenarios argumentales del expediente."""

        clauses = ["case_id = ?"]
        parameters: list[object] = [case_id]
        if issue_id is not None:
            clauses.append("issue_id = ?")
            parameters.append(issue_id)
        if not include_archived:
            clauses.append("status != ?")
            parameters.append(ScenarioStatus.ARCHIVED.value)
        where = " AND ".join(clauses)
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM argument_scenarios
                WHERE {where}
                ORDER BY code
                """,
                tuple(parameters),
            ).fetchall()
        return [self._row_to_scenario(row) for row in rows]

    def update_scenario(
        self,
        scenario_id: str,
        payload: ArgumentScenarioUpdate,
    ) -> ArgumentScenarioRecord:
        """Actualiza un escenario sin cambiar su código."""

        current = self.get_scenario(scenario_id)
        now = utc_now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE argument_scenarios
                SET name = ?, description = ?, status = ?,
                    argument_ids_json = ?, assumptions_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.name,
                    payload.description,
                    payload.status.value,
                    self._json_list(payload.argument_ids),
                    self._json_list(payload.assumptions),
                    now.isoformat(),
                    scenario_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ArgumentationNotFoundError(
                    "El escenario argumental no existe."
                )
            self._insert_audit(
                connection,
                case_id=current.case_id,
                event_type="argumentation.scenario.updated",
                entity_type="argument_scenario",
                entity_id=scenario_id,
                detail={
                    "code": current.code,
                    "argument_count": len(payload.argument_ids),
                },
            )
        return self.get_scenario(scenario_id)

    def delete_scenario(
        self,
        scenario_id: str,
        *,
        confirmation: str,
    ) -> None:
        """Elimina un escenario con confirmación exacta."""

        current = self.get_scenario(scenario_id)
        if confirmation.strip().upper() != current.code:
            raise ValueError(
                f"Escribe exactamente {current.code} para confirmar."
            )
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM argument_scenarios WHERE id = ?",
                (scenario_id,),
            )
            self._insert_audit(
                connection,
                case_id=current.case_id,
                event_type="argumentation.scenario.deleted",
                entity_type="argument_scenario",
                entity_id=scenario_id,
                detail={"code": current.code},
            )

    def known_codes(self, case_id: str, issue_id: str) -> set[str]:
        """Devuelve soportes del expediente y razonamiento del problema."""

        queries: tuple[tuple[str, tuple[str, ...]], ...] = (
            (
                "SELECT code FROM facts WHERE case_id = ?",
                (case_id,),
            ),
            (
                "SELECT code FROM evidence WHERE case_id = ?",
                (case_id,),
            ),
            (
                "SELECT code FROM norms WHERE case_id = ?",
                (case_id,),
            ),
            (
                "SELECT code FROM jurisprudence WHERE case_id = ?",
                (case_id,),
            ),
            (
                "SELECT code FROM doctrine WHERE case_id = ?",
                (case_id,),
            ),
            (
                """
                SELECT code
                FROM reasoning_assertions
                WHERE case_id = ? AND issue_id = ?
                """,
                (case_id, issue_id),
            ),
            (
                """
                SELECT code
                FROM reasoning_rules
                WHERE case_id = ? AND issue_id = ?
                """,
                (case_id, issue_id),
            ),
            (
                """
                SELECT conclusion.code
                FROM reasoning_conclusions AS conclusion
                JOIN reasoning_runs AS run ON run.id = conclusion.run_id
                WHERE run.case_id = ? AND run.issue_id = ?
                """,
                (case_id, issue_id),
            ),
        )
        codes: set[str] = set()
        with self._connection() as connection:
            for query, parameters in queries:
                rows = connection.execute(query, parameters).fetchall()
                codes.update(str(row["code"]).upper() for row in rows)
        return codes


    def snapshot_timestamp(
        self,
        case_id: str,
        issue_id: str,
    ) -> datetime:
        """Devuelve una marca determinista para la instantánea argumental."""

        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT MAX(stamp) AS snapshot_at
                FROM (
                    SELECT updated_at AS stamp
                    FROM legal_issues
                    WHERE id = ? AND case_id = ?
                    UNION ALL
                    SELECT updated_at AS stamp
                    FROM legal_arguments
                    WHERE issue_id = ? AND case_id = ?
                    UNION ALL
                    SELECT created_at AS stamp
                    FROM argument_relations
                    WHERE issue_id = ? AND case_id = ?
                    UNION ALL
                    SELECT updated_at AS stamp
                    FROM argument_scenarios
                    WHERE issue_id = ? AND case_id = ?
                )
                """,
                (
                    issue_id,
                    case_id,
                    issue_id,
                    case_id,
                    issue_id,
                    case_id,
                    issue_id,
                    case_id,
                ),
            ).fetchone()
        if row is None or row["snapshot_at"] is None:
            raise ArgumentationNotFoundError(
                "No fue posible determinar la instantánea argumental."
            )
        return datetime.fromisoformat(str(row["snapshot_at"]))

    def issue_metadata(self, case_id: str, issue_id: str) -> dict[str, str]:
        """Recupera datos mínimos del expediente y problema."""

        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT
                    cases.title AS case_title,
                    cases.jurisdiction,
                    legal_issues.code AS issue_code,
                    legal_issues.title AS issue_title,
                    legal_issues.question
                FROM legal_issues
                JOIN cases ON cases.id = legal_issues.case_id
                WHERE legal_issues.id = ? AND legal_issues.case_id = ?
                """,
                (issue_id, case_id),
            ).fetchone()
        if row is None:
            raise ArgumentationNotFoundError(
                "El problema jurídico no pertenece al expediente activo."
            )
        return {
            "case_title": str(row["case_title"]),
            "jurisdiction": str(row["jurisdiction"]),
            "issue_code": str(row["issue_code"]),
            "issue_title": str(row["issue_title"]),
            "question": str(row["question"]),
        }

    @staticmethod
    def _next_code(
        connection: sqlite3.Connection,
        case_id: str,
        entity_name: str,
        prefix: str,
    ) -> str:
        connection.execute(
            """
            INSERT INTO argument_sequences (case_id, entity_name, last_value)
            VALUES (?, ?, 0)
            ON CONFLICT(case_id, entity_name) DO NOTHING
            """,
            (case_id, entity_name),
        )
        connection.execute(
            """
            UPDATE argument_sequences
            SET last_value = last_value + 1
            WHERE case_id = ? AND entity_name = ?
            """,
            (case_id, entity_name),
        )
        row = connection.execute(
            """
            SELECT last_value
            FROM argument_sequences
            WHERE case_id = ? AND entity_name = ?
            """,
            (case_id, entity_name),
        ).fetchone()
        if row is None:
            raise ArgumentationRepositoryError(
                "No fue posible generar el código argumental."
            )
        return f"{prefix}-{int(row['last_value']):03d}"

    @staticmethod
    def _insert_audit(
        connection: sqlite3.Connection,
        *,
        case_id: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        detail: Mapping[str, object],
    ) -> None:
        connection.execute(
            """
            INSERT INTO audit_events (
                id, case_id, event_type, entity_type, entity_id,
                detail_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
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
    def _json_list(values: list[str]) -> str:
        return json.dumps(values, ensure_ascii=False)

    @staticmethod
    def _json_string_list(value: str) -> list[str]:
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed]

    @classmethod
    def _row_to_argument(cls, row: sqlite3.Row) -> LegalArgumentRecord:
        return LegalArgumentRecord(
            id=str(row["id"]),
            case_id=str(row["case_id"]),
            issue_id=str(row["issue_id"]),
            code=str(row["code"]),
            title=str(row["title"]),
            position=ArgumentPosition(str(row["position"])),
            thesis_key=str(row["thesis_key"]),
            thesis_statement=str(row["thesis_statement"]),
            thesis_value=AssertionValue(str(row["thesis_value"])),
            claim=str(row["claim"]),
            reasoning=str(row["reasoning"]),
            status=ArgumentStatus(str(row["status"])),
            conclusion_id=(
                str(row["conclusion_id"])
                if row["conclusion_id"] is not None
                else None
            ),
            fact_codes=cls._json_string_list(str(row["fact_codes_json"])),
            evidence_codes=cls._json_string_list(
                str(row["evidence_codes_json"])
            ),
            source_codes=cls._json_string_list(
                str(row["source_codes_json"])
            ),
            rule_codes=cls._json_string_list(str(row["rule_codes_json"])),
            assertion_codes=cls._json_string_list(
                str(row["assertion_codes_json"])
            ),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    @classmethod
    def _row_to_scenario(cls, row: sqlite3.Row) -> ArgumentScenarioRecord:
        return ArgumentScenarioRecord(
            id=str(row["id"]),
            case_id=str(row["case_id"]),
            issue_id=str(row["issue_id"]),
            code=str(row["code"]),
            name=str(row["name"]),
            description=str(row["description"]),
            status=ScenarioStatus(str(row["status"])),
            argument_ids=cls._json_string_list(
                str(row["argument_ids_json"])
            ),
            assumptions=cls._json_string_list(
                str(row["assumptions_json"])
            ),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    @staticmethod
    def _row_to_relation(row: sqlite3.Row) -> ArgumentRelationRecord:
        return ArgumentRelationRecord(
            id=str(row["id"]),
            case_id=str(row["case_id"]),
            issue_id=str(row["issue_id"]),
            code=str(row["code"]),
            source_argument_id=str(row["source_argument_id"]),
            target_argument_id=str(row["target_argument_id"]),
            relation_type=ArgumentRelationType(str(row["relation_type"])),
            rationale=str(row["rationale"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )
