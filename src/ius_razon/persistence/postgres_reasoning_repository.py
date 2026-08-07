from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from typing import Any, cast
from uuid import uuid4

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

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


class PostgresReasoningRepository:
    """Persistencia aislada para premisas, reglas, ejecuciones y trazas."""

    _SEQUENCE_TABLES = {
        "assertion": ("reasoning_assertions", "A"),
        "rule": ("reasoning_rules", "R"),
    }

    def __init__(self, database_url: str) -> None:
        cleaned = database_url.strip()
        if not cleaned:
            raise ValueError("database_url no puede estar vacía.")
        self._database_url = cleaned

    @property
    def database_url(self) -> str:
        """URL de runtime; no debe registrarse ni mostrarse."""

        return self._database_url

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
            raise ReasoningRepositoryError(
                "La operación del motor de razonamiento no pudo completarse."
            ) from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        required_tables = (
            "cases",
            "legal_issues",
            "audit_events",
            "reasoning_assertions",
            "reasoning_rules",
            "reasoning_rule_conditions",
            "reasoning_assertion_versions",
            "reasoning_rule_versions",
            "reasoning_runs",
            "reasoning_conclusions",
            "reasoning_traces",
            "reasoning_sequences",
        )
        with self._connection() as connection:
            missing: list[str] = []
            for table_name in required_tables:
                row = connection.execute(
                    "SELECT to_regclass(%s) AS table_name",
                    (f"public.{table_name}",),
                ).fetchone()
                if row is None or row["table_name"] is None:
                    missing.append(table_name)

            if missing:
                raise ReasoningRepositoryError(
                    "El esquema PostgreSQL de razonamiento está incompleto."
                )

            column = connection.execute(
                """
                SELECT 1 AS present
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'reasoning_runs'
                  AND column_name = 'input_snapshot_json'
                """
            ).fetchone()
            if column is None:
                raise ReasoningRepositoryError(
                    "Falta reasoning_runs.input_snapshot_json en PostgreSQL."
                )

            self._seed_reasoning_sequences(connection)

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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                "SELECT * FROM reasoning_assertions WHERE id = %s",
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
        query = "SELECT * FROM reasoning_assertions WHERE case_id = %s"
        parameters: list[str] = [case_id]
        if issue_id is not None:
            query += " AND issue_id = %s"
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
                "SELECT * FROM reasoning_assertions WHERE id = %s",
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
                SET predicate_key = %s, statement = %s, value = %s, basis = %s,
                    support_codes_json = %s, updated_at = %s
                WHERE id = %s
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
                "SELECT * FROM reasoning_assertions WHERE id = %s",
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
                "DELETE FROM reasoning_assertions WHERE id = %s",
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
            WHERE case_id = %s
        """
        parameters: list[str] = [case_id]
        if entity_id is not None:
            query += " AND entity_id = %s"
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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    ) VALUES (%s, %s, %s, %s, %s, %s)
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
                "SELECT * FROM reasoning_rules WHERE id = %s",
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
        query = "SELECT * FROM reasoning_rules WHERE case_id = %s"
        parameters: list[str | int] = [case_id]
        if issue_id is not None:
            query += " AND issue_id = %s"
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
                "SELECT * FROM reasoning_rules WHERE id = %s",
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
                SET name = %s, kind = %s, conclusion_key = %s,
                    conclusion_statement = %s, conclusion_value = %s,
                    priority = %s, active = %s, legal_basis_codes_json = %s,
                    explanation = %s, updated_at = %s
                WHERE id = %s
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
                "DELETE FROM reasoning_rule_conditions WHERE rule_id = %s",
                (rule_id,),
            )
            for position, condition in enumerate(payload.conditions, start=1):
                connection.execute(
                    """
                    INSERT INTO reasoning_rule_conditions (
                        id, rule_id, position, role, predicate_key, expected_value
                    ) VALUES (%s, %s, %s, %s, %s, %s)
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
                "SELECT * FROM reasoning_rules WHERE id = %s",
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
                "DELETE FROM reasoning_rules WHERE id = %s",
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
            WHERE case_id = %s
        """
        parameters: list[str] = [case_id]
        if entity_id is not None:
            query += " AND entity_id = %s"
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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)
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
                "SELECT case_id FROM reasoning_runs WHERE id = %s",
                (run_id,),
            ).fetchone()
            if run_row is None:
                raise ReasoningNotFoundError("La ejecución de razonamiento no existe.")

            connection.execute(
                """
                UPDATE reasoning_runs
                SET completed_at = %s, summary_json = %s, status = %s
                WHERE id = %s
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
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
                "SELECT case_id FROM reasoning_runs WHERE id = %s",
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
                SET completed_at = %s, summary_json = %s, status = %s
                WHERE id = %s
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
                "SELECT * FROM reasoning_runs WHERE id = %s",
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
        query = "SELECT * FROM reasoning_runs WHERE case_id = %s"
        parameters: list[str | int] = [case_id]
        if issue_id is not None:
            query += " AND issue_id = %s"
            parameters.append(issue_id)
        query += " ORDER BY started_at DESC LIMIT %s"
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
                WHERE run_id = %s ORDER BY code
                """,
                (run_id,),
            ).fetchall()
            trace_rows = connection.execute(
                """
                SELECT * FROM reasoning_traces
                WHERE run_id = %s ORDER BY sequence
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
                WHERE id = %s AND case_id = %s
                """,
                (issue_id, case_id),
            ).fetchone()
        if row is None:
            raise ReasoningNotFoundError(
                "El problema jurídico no pertenece al expediente activo."
            )

    def known_codes(self, case_id: str) -> set[str]:
        table_queries = (
            "SELECT code FROM facts WHERE case_id = %s",
            "SELECT code FROM evidence WHERE case_id = %s",
            "SELECT code FROM legal_issues WHERE case_id = %s",
            "SELECT code FROM norms WHERE case_id = %s",
            "SELECT code FROM jurisprudence WHERE case_id = %s",
            "SELECT code FROM doctrine WHERE case_id = %s",
            "SELECT code FROM reasoning_assertions WHERE case_id = %s",
            "SELECT code FROM reasoning_rules WHERE case_id = %s",
        )
        codes: set[str] = set()
        with self._connection() as connection:
            for query in table_queries:
                rows = connection.execute(query, (case_id,)).fetchall()
                codes.update(str(row["code"]).upper() for row in rows)
        return codes

    @staticmethod
    def _assertion_dependency_count(
        connection: Connection[dict[str, Any]],
        *,
        issue_id: str,
        predicate_key: str,
    ) -> int:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM reasoning_rule_conditions AS condition
            JOIN reasoning_rules AS rule ON rule.id = condition.rule_id
            WHERE rule.issue_id = %s AND condition.predicate_key = %s
            """,
            (issue_id, predicate_key),
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    @staticmethod
    def _rule_dependency_count(
        connection: Connection[dict[str, Any]],
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
            WHERE rule.issue_id = %s
              AND rule.id <> %s
              AND condition.predicate_key = %s
            """,
            (issue_id, excluded_rule_id, conclusion_key),
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    @staticmethod
    def _insert_version(
        connection: Connection[dict[str, Any]],
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

        lock_key = f"ius_razon:reasoning_version:{table_name}:{entity_id}"
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (lock_key,),
        )
        row = connection.execute(
            f"""
            SELECT COALESCE(MAX(version_number), 0) AS current_version
            FROM {table_name}
            WHERE entity_id = %s
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
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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

    def _load_conditions(
        self,
        connection: Connection[dict[str, Any]],
        rule_id: str,
    ) -> list[RuleConditionCreate]:
        rows = connection.execute(
            """
            SELECT role, predicate_key, expected_value
            FROM reasoning_rule_conditions
            WHERE rule_id = %s
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

    def _seed_reasoning_sequences(
        self,
        connection: Connection[dict[str, Any]],
    ) -> None:
        case_rows = connection.execute("SELECT id FROM cases").fetchall()
        for case_row in case_rows:
            case_id = str(case_row["id"])
            for entity_name, (table_name, prefix) in self._SEQUENCE_TABLES.items():
                last_value = self._max_existing_code(
                    connection,
                    table_name,
                    case_id,
                    prefix,
                )
                connection.execute(
                    """
                    INSERT INTO reasoning_sequences (
                        case_id, entity_name, last_value
                    ) VALUES (%s, %s, %s)
                    ON CONFLICT (case_id, entity_name)
                    DO UPDATE SET last_value = GREATEST(
                        reasoning_sequences.last_value,
                        EXCLUDED.last_value
                    )
                    """,
                    (case_id, entity_name, last_value),
                )

    @staticmethod
    def _max_existing_code(
        connection: Connection[dict[str, Any]],
        table_name: str,
        case_id: str,
        prefix: str,
    ) -> int:
        allowed_tables = {
            "reasoning_assertions",
            "reasoning_rules",
        }
        if table_name not in allowed_tables:
            raise ValueError("Tabla no permitida para secuencia de razonamiento.")

        rows = connection.execute(
            f"SELECT code FROM {table_name} WHERE case_id = %s",
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

    def _next_code(
        self,
        connection: Connection[dict[str, Any]],
        case_id: str,
        entity_name: str,
        prefix: str,
    ) -> str:
        sequence = self._SEQUENCE_TABLES.get(entity_name)
        if sequence is None or sequence[1] != prefix:
            raise ValueError("Entidad no permitida para generar código.")

        table_name = sequence[0]
        lock_key = f"ius_razon:reasoning:{case_id}:{entity_name}"
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (lock_key,),
        )
        row = connection.execute(
            """
            SELECT last_value FROM reasoning_sequences
            WHERE case_id = %s AND entity_name = %s
            """,
            (case_id, entity_name),
        ).fetchone()

        if row is None:
            last_value = self._max_existing_code(
                connection,
                table_name,
                case_id,
                prefix,
            )
            connection.execute(
                """
                INSERT INTO reasoning_sequences (
                    case_id, entity_name, last_value
                ) VALUES (%s, %s, %s)
                """,
                (case_id, entity_name, last_value),
            )
        else:
            last_value = int(row["last_value"])

        next_value = last_value + 1
        connection.execute(
            """
            UPDATE reasoning_sequences
            SET last_value = %s
            WHERE case_id = %s AND entity_name = %s
            """,
            (next_value, case_id, entity_name),
        )
        return f"{prefix}-{next_value:03d}"

    @staticmethod
    def _insert_audit(
        connection: Connection[dict[str, Any]],
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
    def _row_to_assertion(cls, row: dict[str, Any]) -> ReasoningAssertionRecord:
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
        row: dict[str, Any],
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
    def _row_to_run(cls, row: dict[str, Any]) -> ReasoningRunRecord:
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
    def _row_to_conclusion(cls, row: dict[str, Any]) -> ReasoningConclusionRecord:
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
        row: dict[str, Any],
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
    def _row_to_trace(row: dict[str, Any]) -> ReasoningTraceRecord:
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
