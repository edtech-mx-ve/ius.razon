from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from ius_razon.domain.models import utc_now
from ius_razon.domain.reasoning_models import (
    AssertionValue,
    ConclusionStatus,
    ConditionRole,
    ReasoningAssertionCreate,
    ReasoningAssertionRecord,
    ReasoningAssertionUpdate,
    ReasoningConclusionRecord,
    ReasoningRuleCreate,
    ReasoningRuleRecord,
    ReasoningRuleUpdate,
    ReasoningRunRecord,
    ReasoningRunReport,
    ReasoningRunStatus,
    ReasoningTraceRecord,
    ReasoningVersionRecord,
    RuleConditionCreate,
    RuleKind,
    SupportLevel,
    TraceOutcome,
    VersionAction,
)


class ReasoningRepositoryError(RuntimeError):
    """Error controlado de persistencia del motor de razonamiento."""


class ReasoningNotFoundError(ReasoningRepositoryError):
    """Registro de razonamiento inexistente."""


class ReasoningConflictError(ReasoningRepositoryError):
    """Operación rechazada para preservar dependencias del razonamiento."""


class ReasoningRepository:
    """Persistencia aislada para premisas, reglas, ejecuciones y trazas."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path.resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        """Ruta absoluta de la base para respaldos consistentes."""

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
            raise ReasoningRepositoryError(
                "La operación del motor de razonamiento no pudo completarse."
            ) from exc
        finally:
            connection.close()

    def initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS reasoning_assertions (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            predicate_key TEXT NOT NULL,
            statement TEXT NOT NULL,
            value TEXT NOT NULL,
            basis TEXT NOT NULL,
            support_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS reasoning_rules (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            conclusion_key TEXT NOT NULL,
            conclusion_statement TEXT NOT NULL,
            conclusion_value TEXT NOT NULL,
            priority INTEGER NOT NULL CHECK(priority BETWEEN 0 AND 1000),
            active INTEGER NOT NULL CHECK(active IN (0, 1)),
            legal_basis_codes_json TEXT NOT NULL,
            explanation TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS reasoning_rule_conditions (
            id TEXT PRIMARY KEY,
            rule_id TEXT NOT NULL REFERENCES reasoning_rules(id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            role TEXT NOT NULL,
            predicate_key TEXT NOT NULL,
            expected_value TEXT NOT NULL,
            UNIQUE(rule_id, position)
        );

        CREATE TABLE IF NOT EXISTS reasoning_assertion_versions (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            entity_code TEXT NOT NULL,
            version_number INTEGER NOT NULL CHECK(version_number >= 1),
            action TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(entity_id, version_number)
        );

        CREATE TABLE IF NOT EXISTS reasoning_rule_versions (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            entity_code TEXT NOT NULL,
            version_number INTEGER NOT NULL CHECK(version_number >= 1),
            action TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(entity_id, version_number)
        );

        CREATE TABLE IF NOT EXISTS reasoning_runs (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            status TEXT NOT NULL,
            engine_version TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            summary_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reasoning_conclusions (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES reasoning_runs(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            predicate_key TEXT NOT NULL,
            statement TEXT NOT NULL,
            value TEXT NOT NULL,
            status TEXT NOT NULL,
            support_level TEXT NOT NULL,
            rule_codes_json TEXT NOT NULL,
            assertion_codes_json TEXT NOT NULL,
            source_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(run_id, code)
        );

        CREATE TABLE IF NOT EXISTS reasoning_traces (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES reasoning_runs(id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL,
            rule_id TEXT NOT NULL,
            rule_code TEXT NOT NULL,
            outcome TEXT NOT NULL,
            detail_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(run_id, sequence)
        );

        CREATE TABLE IF NOT EXISTS reasoning_sequences (
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            entity_name TEXT NOT NULL,
            last_value INTEGER NOT NULL CHECK(last_value >= 0),
            PRIMARY KEY(case_id, entity_name)
        );

        CREATE INDEX IF NOT EXISTS idx_reasoning_assertions_case
            ON reasoning_assertions(case_id, issue_id);
        CREATE INDEX IF NOT EXISTS idx_reasoning_rules_case
            ON reasoning_rules(case_id, issue_id);
        CREATE INDEX IF NOT EXISTS idx_reasoning_assertion_versions
            ON reasoning_assertion_versions(case_id, entity_code, version_number);
        CREATE INDEX IF NOT EXISTS idx_reasoning_rule_versions
            ON reasoning_rule_versions(case_id, entity_code, version_number);
        CREATE INDEX IF NOT EXISTS idx_reasoning_runs_case
            ON reasoning_runs(case_id, issue_id, started_at);
        CREATE INDEX IF NOT EXISTS idx_reasoning_conclusions_run
            ON reasoning_conclusions(run_id);
        CREATE INDEX IF NOT EXISTS idx_reasoning_traces_run
            ON reasoning_traces(run_id);
        """
        with self._connection() as connection:
            connection.executescript(schema)
            self._ensure_column(
                connection,
                table_name="reasoning_runs",
                column_name="input_snapshot_json",
                definition="TEXT NOT NULL DEFAULT '{}'",
            )

    def add_assertion(
        self,
        payload: ReasoningAssertionCreate,
    ) -> ReasoningAssertionRecord:
        record_id = str(uuid4())
        now = utc_now()
        with self._connection() as connection:
            code = self._next_code(connection, payload.case_id, "assertion", "A")
            connection.execute(
                """
                INSERT INTO reasoning_assertions (
                    id, case_id, issue_id, code, predicate_key, statement, value,
                    basis, support_codes_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    payload.case_id,
                    payload.issue_id,
                    code,
                    payload.predicate_key,
                    payload.statement,
                    payload.value.value,
                    payload.basis,
                    json.dumps(payload.support_codes, ensure_ascii=False),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="reasoning.assertion.created",
                entity_type="reasoning_assertion",
                entity_id=record_id,
                detail={"code": code, "predicate_key": payload.predicate_key},
            )
        return self.get_assertion(record_id)

    def get_assertion(self, assertion_id: str) -> ReasoningAssertionRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM reasoning_assertions WHERE id = ?",
                (assertion_id,),
            ).fetchone()
        if row is None:
            raise ReasoningNotFoundError("La premisa de razonamiento no existe.")
        return self._row_to_assertion(row)

    def list_assertions(
        self,
        case_id: str,
        issue_id: str | None = None,
    ) -> list[ReasoningAssertionRecord]:
        query = "SELECT * FROM reasoning_assertions WHERE case_id = ?"
        parameters: list[str] = [case_id]
        if issue_id is not None:
            query += " AND issue_id = ?"
            parameters.append(issue_id)
        query += " ORDER BY code"
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._row_to_assertion(row) for row in rows]

    def update_assertion(
        self,
        assertion_id: str,
        payload: ReasoningAssertionUpdate,
    ) -> ReasoningAssertionRecord:
        """Actualiza una premisa conservando código y una versión del estado previo."""

        now = utc_now()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM reasoning_assertions WHERE id = ?",
                (assertion_id,),
            ).fetchone()
            if row is None:
                raise ReasoningNotFoundError("La premisa de razonamiento no existe.")
            current = self._row_to_assertion(row)
            if current.predicate_key != payload.predicate_key:
                dependencies = self._assertion_dependency_count(
                    connection,
                    issue_id=current.issue_id,
                    predicate_key=current.predicate_key,
                )
                if dependencies:
                    raise ReasoningConflictError(
                        "La clave lógica no puede cambiar porque aparece en "
                        f"{dependencies} condición(es) de reglas. Corrige primero "
                        "esas reglas o conserva la clave actual."
                    )
            version = self._insert_version(
                connection,
                table_name="reasoning_assertion_versions",
                entity_type="reasoning_assertion",
                entity_id=current.id,
                case_id=current.case_id,
                issue_id=current.issue_id,
                entity_code=current.code,
                action=VersionAction.UPDATED,
                snapshot=current.model_dump(mode="json"),
            )
            connection.execute(
                """
                UPDATE reasoning_assertions
                SET predicate_key = ?, statement = ?, value = ?, basis = ?,
                    support_codes_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.predicate_key,
                    payload.statement,
                    payload.value.value,
                    payload.basis,
                    json.dumps(payload.support_codes, ensure_ascii=False),
                    now.isoformat(),
                    assertion_id,
                ),
            )
            self._insert_audit(
                connection,
                case_id=current.case_id,
                event_type="reasoning.assertion.updated",
                entity_type="reasoning_assertion",
                entity_id=assertion_id,
                detail={
                    "code": current.code,
                    "version": version,
                    "predicate_key": payload.predicate_key,
                },
            )
        return self.get_assertion(assertion_id)

    def delete_assertion(self, assertion_id: str, *, confirmation: str) -> None:
        """Elimina una premisa sin reutilizar su código y preserva su última versión."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM reasoning_assertions WHERE id = ?",
                (assertion_id,),
            ).fetchone()
            if row is None:
                raise ReasoningNotFoundError("La premisa de razonamiento no existe.")
            current = self._row_to_assertion(row)
            if confirmation.strip().upper() != current.code:
                raise ValueError(
                    f"Escribe exactamente {current.code} para confirmar la eliminación."
                )
            dependencies = self._assertion_dependency_count(
                connection,
                issue_id=current.issue_id,
                predicate_key=current.predicate_key,
            )
            if dependencies:
                raise ReasoningConflictError(
                    "La premisa no puede eliminarse porque su clave lógica aparece "
                    f"en {dependencies} condición(es) de reglas. Corrige o elimina "
                    "primero esas reglas."
                )
            version = self._insert_version(
                connection,
                table_name="reasoning_assertion_versions",
                entity_type="reasoning_assertion",
                entity_id=current.id,
                case_id=current.case_id,
                issue_id=current.issue_id,
                entity_code=current.code,
                action=VersionAction.DELETED,
                snapshot=current.model_dump(mode="json"),
            )
            connection.execute(
                "DELETE FROM reasoning_assertions WHERE id = ?",
                (assertion_id,),
            )
            self._insert_audit(
                connection,
                case_id=current.case_id,
                event_type="reasoning.assertion.deleted",
                entity_type="reasoning_assertion",
                entity_id=assertion_id,
                detail={"code": current.code, "version": version},
            )

    def list_assertion_versions(
        self,
        *,
        case_id: str,
        entity_id: str | None = None,
    ) -> list[ReasoningVersionRecord]:
        query = """
            SELECT * FROM reasoning_assertion_versions
            WHERE case_id = ?
        """
        parameters: list[str] = [case_id]
        if entity_id is not None:
            query += " AND entity_id = ?"
            parameters.append(entity_id)
        query += " ORDER BY created_at DESC, version_number DESC"
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [
            self._row_to_version(row, "reasoning_assertion")
            for row in rows
        ]

    def add_rule(self, payload: ReasoningRuleCreate) -> ReasoningRuleRecord:
        rule_id = str(uuid4())
        now = utc_now()
        with self._connection() as connection:
            code = self._next_code(connection, payload.case_id, "rule", "R")
            connection.execute(
                """
                INSERT INTO reasoning_rules (
                    id, case_id, issue_id, code, name, kind, conclusion_key,
                    conclusion_statement, conclusion_value, priority, active,
                    legal_basis_codes_json, explanation, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rule_id,
                    payload.case_id,
                    payload.issue_id,
                    code,
                    payload.name,
                    payload.kind.value,
                    payload.conclusion_key,
                    payload.conclusion_statement,
                    payload.conclusion_value.value,
                    payload.priority,
                    int(payload.active),
                    json.dumps(payload.legal_basis_codes, ensure_ascii=False),
                    payload.explanation,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            for position, condition in enumerate(payload.conditions, start=1):
                connection.execute(
                    """
                    INSERT INTO reasoning_rule_conditions (
                        id, rule_id, position, role, predicate_key, expected_value
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        rule_id,
                        position,
                        condition.role.value,
                        condition.predicate_key,
                        condition.expected_value.value,
                    ),
                )
            self._insert_audit(
                connection,
                case_id=payload.case_id,
                event_type="reasoning.rule.created",
                entity_type="reasoning_rule",
                entity_id=rule_id,
                detail={"code": code, "kind": payload.kind.value},
            )
        return self.get_rule(rule_id)

    def get_rule(self, rule_id: str) -> ReasoningRuleRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM reasoning_rules WHERE id = ?",
                (rule_id,),
            ).fetchone()
            if row is None:
                raise ReasoningNotFoundError("La regla de razonamiento no existe.")
            conditions = self._load_conditions(connection, rule_id)
        return self._row_to_rule(row, conditions)

    def list_rules(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        active_only: bool = False,
    ) -> list[ReasoningRuleRecord]:
        query = "SELECT * FROM reasoning_rules WHERE case_id = ?"
        parameters: list[str | int] = [case_id]
        if issue_id is not None:
            query += " AND issue_id = ?"
            parameters.append(issue_id)
        if active_only:
            query += " AND active = 1"
        query += " ORDER BY priority DESC, code"
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
            records = [
                self._row_to_rule(row, self._load_conditions(connection, str(row["id"])))
                for row in rows
            ]
        return records

    def update_rule(
        self,
        rule_id: str,
        payload: ReasoningRuleUpdate,
    ) -> ReasoningRuleRecord:
        """Actualiza una regla, conserva su código y versiona el estado previo."""

        now = utc_now()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM reasoning_rules WHERE id = ?",
                (rule_id,),
            ).fetchone()
            if row is None:
                raise ReasoningNotFoundError("La regla de razonamiento no existe.")
            current = self._row_to_rule(
                row,
                self._load_conditions(connection, rule_id),
            )
            if current.conclusion_key != payload.conclusion_key:
                dependencies = self._rule_dependency_count(
                    connection,
                    issue_id=current.issue_id,
                    conclusion_key=current.conclusion_key,
                    excluded_rule_id=current.id,
                )
                if dependencies:
                    raise ReasoningConflictError(
                        "La clave de conclusión no puede cambiar porque aparece "
                        f"en {dependencies} condición(es) de otras reglas."
                    )
            version = self._insert_version(
                connection,
                table_name="reasoning_rule_versions",
                entity_type="reasoning_rule",
                entity_id=current.id,
                case_id=current.case_id,
                issue_id=current.issue_id,
                entity_code=current.code,
                action=VersionAction.UPDATED,
                snapshot=current.model_dump(mode="json"),
            )
            connection.execute(
                """
                UPDATE reasoning_rules
                SET name = ?, kind = ?, conclusion_key = ?,
                    conclusion_statement = ?, conclusion_value = ?,
                    priority = ?, active = ?, legal_basis_codes_json = ?,
                    explanation = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.name,
                    payload.kind.value,
                    payload.conclusion_key,
                    payload.conclusion_statement,
                    payload.conclusion_value.value,
                    payload.priority,
                    int(payload.active),
                    json.dumps(payload.legal_basis_codes, ensure_ascii=False),
                    payload.explanation,
                    now.isoformat(),
                    rule_id,
                ),
            )
            connection.execute(
                "DELETE FROM reasoning_rule_conditions WHERE rule_id = ?",
                (rule_id,),
            )
            for position, condition in enumerate(payload.conditions, start=1):
                connection.execute(
                    """
                    INSERT INTO reasoning_rule_conditions (
                        id, rule_id, position, role, predicate_key, expected_value
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        rule_id,
                        position,
                        condition.role.value,
                        condition.predicate_key,
                        condition.expected_value.value,
                    ),
                )
            self._insert_audit(
                connection,
                case_id=current.case_id,
                event_type="reasoning.rule.updated",
                entity_type="reasoning_rule",
                entity_id=rule_id,
                detail={
                    "active": payload.active,
                    "code": current.code,
                    "priority": payload.priority,
                    "version": version,
                },
            )
        return self.get_rule(rule_id)

    def delete_rule(self, rule_id: str, *, confirmation: str) -> None:
        """Elimina una regla si ninguna otra regla depende de su conclusión."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM reasoning_rules WHERE id = ?",
                (rule_id,),
            ).fetchone()
            if row is None:
                raise ReasoningNotFoundError("La regla de razonamiento no existe.")
            current = self._row_to_rule(
                row,
                self._load_conditions(connection, rule_id),
            )
            if confirmation.strip().upper() != current.code:
                raise ValueError(
                    f"Escribe exactamente {current.code} para confirmar la eliminación."
                )
            dependencies = self._rule_dependency_count(
                connection,
                issue_id=current.issue_id,
                conclusion_key=current.conclusion_key,
                excluded_rule_id=current.id,
            )
            if dependencies:
                raise ReasoningConflictError(
                    "La regla no puede eliminarse porque su conclusión aparece "
                    f"en {dependencies} condición(es) de otras reglas. Corrige o "
                    "elimina primero esas dependencias."
                )
            version = self._insert_version(
                connection,
                table_name="reasoning_rule_versions",
                entity_type="reasoning_rule",
                entity_id=current.id,
                case_id=current.case_id,
                issue_id=current.issue_id,
                entity_code=current.code,
                action=VersionAction.DELETED,
                snapshot=current.model_dump(mode="json"),
            )
            connection.execute(
                "DELETE FROM reasoning_rules WHERE id = ?",
                (rule_id,),
            )
            self._insert_audit(
                connection,
                case_id=current.case_id,
                event_type="reasoning.rule.deleted",
                entity_type="reasoning_rule",
                entity_id=rule_id,
                detail={"code": current.code, "version": version},
            )

    def list_rule_versions(
        self,
        *,
        case_id: str,
        entity_id: str | None = None,
    ) -> list[ReasoningVersionRecord]:
        query = """
            SELECT * FROM reasoning_rule_versions
            WHERE case_id = ?
        """
        parameters: list[str] = [case_id]
        if entity_id is not None:
            query += " AND entity_id = ?"
            parameters.append(entity_id)
        query += " ORDER BY created_at DESC, version_number DESC"
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._row_to_version(row, "reasoning_rule") for row in rows]

    def create_run(
        self,
        *,
        case_id: str,
        issue_id: str,
        engine_version: str,
        input_hash: str,
        input_snapshot: Mapping[str, object],
    ) -> ReasoningRunRecord:
        run_id = str(uuid4())
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO reasoning_runs (
                    id, case_id, issue_id, status, engine_version, input_hash,
                    input_snapshot_json, started_at, completed_at, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    run_id,
                    case_id,
                    issue_id,
                    ReasoningRunStatus.RUNNING.value,
                    engine_version,
                    input_hash,
                    json.dumps(
                        input_snapshot,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    now.isoformat(),
                    json.dumps({}, ensure_ascii=False),
                ),
            )
        return self.get_run(run_id)

    def complete_run(
        self,
        *,
        run_id: str,
        summary: dict[str, int | str | bool],
        conclusions: list[dict[str, object]],
        traces: list[dict[str, object]],
    ) -> ReasoningRunReport:
        completed_at = utc_now()
        with self._connection() as connection:
            run_row = connection.execute(
                "SELECT case_id FROM reasoning_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if run_row is None:
                raise ReasoningNotFoundError("La ejecución de razonamiento no existe.")

            connection.execute(
                """
                UPDATE reasoning_runs
                SET completed_at = ?, summary_json = ?, status = ?
                WHERE id = ?
                """,
                (
                    completed_at.isoformat(),
                    json.dumps(summary, ensure_ascii=False, sort_keys=True),
                    ReasoningRunStatus.COMPLETED.value,
                    run_id,
                ),
            )
            for index, conclusion in enumerate(conclusions, start=1):
                connection.execute(
                    """
                    INSERT INTO reasoning_conclusions (
                        id, run_id, code, predicate_key, statement, value, status,
                        support_level, rule_codes_json, assertion_codes_json,
                        source_codes_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        run_id,
                        f"C-{index:03d}",
                        str(conclusion["predicate_key"]),
                        str(conclusion["statement"]),
                        str(conclusion["value"]),
                        str(conclusion["status"]),
                        str(conclusion["support_level"]),
                        json.dumps(conclusion["rule_codes"], ensure_ascii=False),
                        json.dumps(
                            conclusion["supporting_assertion_codes"],
                            ensure_ascii=False,
                        ),
                        json.dumps(conclusion["source_codes"], ensure_ascii=False),
                        completed_at.isoformat(),
                    ),
                )
            for index, trace in enumerate(traces, start=1):
                connection.execute(
                    """
                    INSERT INTO reasoning_traces (
                        id, run_id, sequence, rule_id, rule_code, outcome,
                        detail_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        run_id,
                        index,
                        str(trace["rule_id"]),
                        str(trace["rule_code"]),
                        str(trace["outcome"]),
                        json.dumps(trace["detail"], ensure_ascii=False, sort_keys=True),
                        completed_at.isoformat(),
                    ),
                )
            self._insert_audit(
                connection,
                case_id=str(run_row["case_id"]),
                event_type="reasoning.run.completed",
                entity_type="reasoning_run",
                entity_id=run_id,
                detail=summary,
            )
        return self.get_run_report(run_id)

    def fail_run(self, run_id: str, error_message: str) -> None:
        completed_at = utc_now()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT case_id FROM reasoning_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                raise ReasoningNotFoundError(
                    "La ejecución de razonamiento no existe."
                )
            summary: dict[str, int | str | bool] = {
                "error": error_message[:500],
                "engine_failed": True,
            }
            connection.execute(
                """
                UPDATE reasoning_runs
                SET completed_at = ?, summary_json = ?, status = ?
                WHERE id = ?
                """,
                (
                    completed_at.isoformat(),
                    json.dumps(summary, ensure_ascii=False),
                    ReasoningRunStatus.FAILED.value,
                    run_id,
                ),
            )
            self._insert_audit(
                connection,
                case_id=str(row["case_id"]),
                event_type="reasoning.run.failed",
                entity_type="reasoning_run",
                entity_id=run_id,
                detail=summary,
            )

    def get_run(self, run_id: str) -> ReasoningRunRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM reasoning_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise ReasoningNotFoundError("La ejecución de razonamiento no existe.")
        return self._row_to_run(row)

    def list_runs(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        limit: int = 20,
    ) -> list[ReasoningRunRecord]:
        query = "SELECT * FROM reasoning_runs WHERE case_id = ?"
        parameters: list[str | int] = [case_id]
        if issue_id is not None:
            query += " AND issue_id = ?"
            parameters.append(issue_id)
        query += " ORDER BY started_at DESC LIMIT ?"
        parameters.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._row_to_run(row) for row in rows]

    def get_run_report(self, run_id: str) -> ReasoningRunReport:
        run = self.get_run(run_id)
        with self._connection() as connection:
            conclusion_rows = connection.execute(
                """
                SELECT * FROM reasoning_conclusions
                WHERE run_id = ? ORDER BY code
                """,
                (run_id,),
            ).fetchall()
            trace_rows = connection.execute(
                """
                SELECT * FROM reasoning_traces
                WHERE run_id = ? ORDER BY sequence
                """,
                (run_id,),
            ).fetchall()
        return ReasoningRunReport(
            run=run,
            conclusions=[
                self._row_to_conclusion(row) for row in conclusion_rows
            ],
            traces=[self._row_to_trace(row) for row in trace_rows],
        )

    def validate_case_issue(self, case_id: str, issue_id: str) -> None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM legal_issues
                WHERE id = ? AND case_id = ?
                """,
                (issue_id, case_id),
            ).fetchone()
        if row is None:
            raise ReasoningNotFoundError(
                "El problema jurídico no pertenece al expediente activo."
            )

    def known_codes(self, case_id: str) -> set[str]:
        table_queries = (
            "SELECT code FROM facts WHERE case_id = ?",
            "SELECT code FROM evidence WHERE case_id = ?",
            "SELECT code FROM legal_issues WHERE case_id = ?",
            "SELECT code FROM norms WHERE case_id = ?",
            "SELECT code FROM jurisprudence WHERE case_id = ?",
            "SELECT code FROM doctrine WHERE case_id = ?",
            "SELECT code FROM reasoning_assertions WHERE case_id = ?",
            "SELECT code FROM reasoning_rules WHERE case_id = ?",
        )
        codes: set[str] = set()
        with self._connection() as connection:
            for query in table_queries:
                rows = connection.execute(query, (case_id,)).fetchall()
                codes.update(str(row["code"]).upper() for row in rows)
        return codes

    @staticmethod
    def _assertion_dependency_count(
        connection: sqlite3.Connection,
        *,
        issue_id: str,
        predicate_key: str,
    ) -> int:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM reasoning_rule_conditions AS condition
            JOIN reasoning_rules AS rule ON rule.id = condition.rule_id
            WHERE rule.issue_id = ? AND condition.predicate_key = ?
            """,
            (issue_id, predicate_key),
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    @staticmethod
    def _rule_dependency_count(
        connection: sqlite3.Connection,
        *,
        issue_id: str,
        conclusion_key: str,
        excluded_rule_id: str,
    ) -> int:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM reasoning_rule_conditions AS condition
            JOIN reasoning_rules AS rule ON rule.id = condition.rule_id
            WHERE rule.issue_id = ?
              AND rule.id <> ?
              AND condition.predicate_key = ?
            """,
            (issue_id, excluded_rule_id, conclusion_key),
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    @staticmethod
    def _insert_version(
        connection: sqlite3.Connection,
        *,
        table_name: str,
        entity_type: str,
        entity_id: str,
        case_id: str,
        issue_id: str,
        entity_code: str,
        action: VersionAction,
        snapshot: Mapping[str, object],
    ) -> int:
        allowed_tables = {
            "reasoning_assertion_versions",
            "reasoning_rule_versions",
        }
        if table_name not in allowed_tables:
            raise ValueError("Tabla de versiones no permitida.")
        row = connection.execute(
            f"""
            SELECT COALESCE(MAX(version_number), 0) AS current_version
            FROM {table_name}
            WHERE entity_id = ?
            """,
            (entity_id,),
        ).fetchone()
        version_number = (
            int(row["current_version"]) + 1 if row is not None else 1
        )
        connection.execute(
            f"""
            INSERT INTO {table_name} (
                id, entity_id, case_id, issue_id, entity_code,
                version_number, action, snapshot_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                entity_id,
                case_id,
                issue_id,
                entity_code,
                version_number,
                action.value,
                json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                utc_now().isoformat(),
            ),
        )
        return version_number

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection,
        *,
        table_name: str,
        column_name: str,
        definition: str,
    ) -> None:
        allowed_tables = {"reasoning_runs"}
        allowed_columns = {"input_snapshot_json"}
        if table_name not in allowed_tables or column_name not in allowed_columns:
            raise ValueError("Migración de columna no permitida.")
        columns = connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
        if any(str(row["name"]) == column_name for row in columns):
            return
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )

    def _load_conditions(
        self,
        connection: sqlite3.Connection,
        rule_id: str,
    ) -> list[RuleConditionCreate]:
        rows = connection.execute(
            """
            SELECT role, predicate_key, expected_value
            FROM reasoning_rule_conditions
            WHERE rule_id = ?
            ORDER BY position
            """,
            (rule_id,),
        ).fetchall()
        return [
            RuleConditionCreate(
                role=ConditionRole(str(row["role"])),
                predicate_key=str(row["predicate_key"]),
                expected_value=AssertionValue(str(row["expected_value"])),
            )
            for row in rows
        ]

    def _next_code(
        self,
        connection: sqlite3.Connection,
        case_id: str,
        entity_name: str,
        prefix: str,
    ) -> str:
        row = connection.execute(
            """
            SELECT last_value FROM reasoning_sequences
            WHERE case_id = ? AND entity_name = ?
            """,
            (case_id, entity_name),
        ).fetchone()
        next_value = 1 if row is None else int(row["last_value"]) + 1
        connection.execute(
            """
            INSERT INTO reasoning_sequences (case_id, entity_name, last_value)
            VALUES (?, ?, ?)
            ON CONFLICT(case_id, entity_name)
            DO UPDATE SET last_value = excluded.last_value
            """,
            (case_id, entity_name, next_value),
        )
        return f"{prefix}-{next_value:03d}"

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
    def _json_string_list(value: str) -> list[str]:
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed]

    @staticmethod
    def _json_object(value: str) -> dict[str, object]:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            return {}
        return cast(dict[str, object], parsed)

    @staticmethod
    def _json_summary(value: str) -> dict[str, int | str | bool]:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            return {}
        result: dict[str, int | str | bool] = {}
        for key, item in parsed.items():
            if isinstance(item, (int, str, bool)):
                result[str(key)] = item
        return result

    @classmethod
    def _row_to_assertion(cls, row: sqlite3.Row) -> ReasoningAssertionRecord:
        return ReasoningAssertionRecord(
            id=str(row["id"]),
            case_id=str(row["case_id"]),
            issue_id=str(row["issue_id"]),
            code=str(row["code"]),
            predicate_key=str(row["predicate_key"]),
            statement=str(row["statement"]),
            value=AssertionValue(str(row["value"])),
            basis=str(row["basis"]),
            support_codes=cls._json_string_list(str(row["support_codes_json"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    @classmethod
    def _row_to_rule(
        cls,
        row: sqlite3.Row,
        conditions: list[RuleConditionCreate],
    ) -> ReasoningRuleRecord:
        return ReasoningRuleRecord(
            id=str(row["id"]),
            case_id=str(row["case_id"]),
            issue_id=str(row["issue_id"]),
            code=str(row["code"]),
            name=str(row["name"]),
            kind=RuleKind(str(row["kind"])),
            conclusion_key=str(row["conclusion_key"]),
            conclusion_statement=str(row["conclusion_statement"]),
            conclusion_value=AssertionValue(str(row["conclusion_value"])),
            priority=int(row["priority"]),
            active=bool(row["active"]),
            legal_basis_codes=cls._json_string_list(
                str(row["legal_basis_codes_json"])
            ),
            explanation=str(row["explanation"]),
            conditions=conditions,
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    @classmethod
    def _row_to_run(cls, row: sqlite3.Row) -> ReasoningRunRecord:
        completed_raw = row["completed_at"]
        available_columns = set(row.keys())
        return ReasoningRunRecord(
            id=str(row["id"]),
            case_id=str(row["case_id"]),
            issue_id=str(row["issue_id"]),
            status=ReasoningRunStatus(str(row["status"])),
            engine_version=str(row["engine_version"]),
            input_hash=str(row["input_hash"]),
            input_snapshot=cls._json_object(
                str(row["input_snapshot_json"])
                if "input_snapshot_json" in available_columns
                else "{}"
            ),
            started_at=datetime.fromisoformat(str(row["started_at"])),
            completed_at=(
                datetime.fromisoformat(str(completed_raw))
                if completed_raw is not None
                else None
            ),
            summary=cls._json_summary(str(row["summary_json"])),
        )

    @classmethod
    def _row_to_conclusion(cls, row: sqlite3.Row) -> ReasoningConclusionRecord:
        return ReasoningConclusionRecord(
            id=str(row["id"]),
            run_id=str(row["run_id"]),
            code=str(row["code"]),
            predicate_key=str(row["predicate_key"]),
            statement=str(row["statement"]),
            value=AssertionValue(str(row["value"])),
            status=ConclusionStatus(str(row["status"])),
            support_level=SupportLevel(str(row["support_level"])),
            rule_codes=cls._json_string_list(str(row["rule_codes_json"])),
            supporting_assertion_codes=cls._json_string_list(
                str(row["assertion_codes_json"])
            ),
            source_codes=cls._json_string_list(str(row["source_codes_json"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )

    @classmethod
    def _row_to_version(
        cls,
        row: sqlite3.Row,
        entity_type: str,
    ) -> ReasoningVersionRecord:
        return ReasoningVersionRecord(
            id=str(row["id"]),
            entity_type=entity_type,
            entity_id=str(row["entity_id"]),
            entity_code=str(row["entity_code"]),
            version_number=int(row["version_number"]),
            action=VersionAction(str(row["action"])),
            snapshot=cls._json_object(str(row["snapshot_json"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )

    @staticmethod
    def _row_to_trace(row: sqlite3.Row) -> ReasoningTraceRecord:
        parsed = json.loads(str(row["detail_json"]))
        detail = cast(dict[str, object], parsed if isinstance(parsed, dict) else {})
        return ReasoningTraceRecord(
            id=str(row["id"]),
            run_id=str(row["run_id"]),
            sequence=int(row["sequence"]),
            rule_id=str(row["rule_id"]),
            rule_code=str(row["rule_code"]),
            outcome=TraceOutcome(str(row["outcome"])),
            detail=detail,
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )
