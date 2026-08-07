from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import uuid4

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from ius_razon.domain.llm_models import (
    AssistantDraftCreate,
    AssistantDraftRecord,
    AssistantTask,
    ContextItem,
    DraftStatus,
    ProviderCallAuditCreate,
    ProviderCallAuditRecord,
    ProviderCallStatus,
    ProviderMode,
)
from ius_razon.domain.models import utc_now


class LLMRepositoryError(RuntimeError):
    """Error controlado de persistencia del asistente."""


class LLMDraftNotFoundError(LLMRepositoryError):
    """Borrador inexistente."""


class LLMReviewConflictError(LLMRepositoryError):
    """Revisión incompatible con el estado actual."""


class PostgresLLMRepository:
    """Persistencia PostgreSQL de borradores, auditoría y decisiones humanas."""

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
            raise LLMRepositoryError(
                "La operación del asistente no pudo completarse."
            ) from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Verifica el esquema PostgreSQL LLM y sincroniza su secuencia."""

        required_tables = (
            "cases",
            "legal_issues",
            "llm_draft_sequences",
            "llm_drafts",
            "llm_provider_calls",
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
                raise LLMRepositoryError(
                    "El esquema PostgreSQL LLM está incompleto."
                )

            self._seed_draft_sequences(connection)

    def _seed_draft_sequences(
        self,
        connection: Connection[dict[str, Any]],
    ) -> None:
        case_rows = connection.execute("SELECT id FROM cases").fetchall()
        for case_row in case_rows:
            case_id = str(case_row["id"])
            last_value = self._max_existing_code(connection, case_id)
            connection.execute(
                """
                INSERT INTO llm_draft_sequences (case_id, last_value)
                VALUES (%s, %s)
                ON CONFLICT (case_id)
                DO UPDATE SET last_value = GREATEST(
                    llm_draft_sequences.last_value,
                    EXCLUDED.last_value
                )
                """,
                (case_id, last_value),
            )

    @staticmethod
    def _max_existing_code(
        connection: Connection[dict[str, Any]],
        case_id: str,
    ) -> int:
        rows = connection.execute(
            "SELECT code FROM llm_drafts WHERE case_id = %s",
            (case_id,),
        ).fetchall()
        maximum = 0
        for row in rows:
            code = str(row["code"])
            if not code.startswith("IA-"):
                continue
            suffix = code[3:]
            if suffix.isdigit():
                maximum = max(maximum, int(suffix))
        return maximum

    def validate_case_issue(self, case_id: str, issue_id: str) -> None:
        """Confirma que el problema pertenece al expediente."""

        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM legal_issues
                WHERE id = %s AND case_id = %s
                """,
                (issue_id, case_id),
            ).fetchone()
        if row is None:
            raise LLMDraftNotFoundError(
                "El problema jurídico no pertenece al expediente activo."
            )

    def add_draft(self, payload: AssistantDraftCreate) -> AssistantDraftRecord:
        """Persiste una respuesta generada con código estable IA-###."""

        self.validate_case_issue(payload.case_id, payload.issue_id)
        record_id = str(uuid4())
        now = utc_now()
        with self._connection() as connection:
            code = self._next_code(connection, payload.case_id)
            connection.execute(
                """
                INSERT INTO llm_drafts (
                    id, case_id, issue_id, code, task, status,
                    provider_name, model_name, request_json, context_json,
                    response_text, edited_text, reference_codes_json,
                    invalid_reference_codes_json, unsupported_claims_json,
                    risk_flags_json, citation_coverage, input_hash, output_hash,
                    provider_mode, external_call, fallback_used, fallback_reason,
                    provider_request_id, input_tokens, output_tokens,
                    estimated_cost_usd, reviewer_note, created_at, reviewed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, NULL)
                """,
                (
                    record_id,
                    payload.case_id,
                    payload.issue_id,
                    code,
                    payload.task.value,
                    DraftStatus.GENERATED.value,
                    payload.provider_name,
                    payload.model_name,
                    self._json_object(payload.request_snapshot),
                    self._json_context(payload.context_items),
                    payload.response_text,
                    self._json_list(payload.reference_codes),
                    self._json_list(payload.invalid_reference_codes),
                    self._json_list(payload.unsupported_claims),
                    self._json_list(payload.risk_flags),
                    payload.citation_coverage,
                    payload.input_hash,
                    payload.output_hash,
                    payload.provider_mode.value,
                    int(payload.external_call),
                    int(payload.fallback_used),
                    payload.fallback_reason,
                    payload.provider_request_id,
                    payload.input_tokens,
                    payload.output_tokens,
                    payload.estimated_cost_usd,
                    now.isoformat(),
                ),
            )
        return self.get_draft(record_id)

    def add_provider_call(
        self,
        payload: ProviderCallAuditCreate,
    ) -> ProviderCallAuditRecord:
        """Registra metadatos de una llamada sin almacenar prompt ni secreto."""

        self.validate_case_issue(payload.case_id, payload.issue_id)
        call_id = str(uuid4())
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO llm_provider_calls (
                    id, draft_id, case_id, issue_id, provider_mode,
                    provider_name, model_name, status, selected_codes_json,
                    input_hash, output_hash, external_call, fallback_used,
                    input_tokens, output_tokens, estimated_cost_usd,
                    error_code, created_at
                ) VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    call_id,
                    payload.case_id,
                    payload.issue_id,
                    payload.provider_mode.value,
                    payload.provider_name,
                    payload.model_name,
                    payload.status.value,
                    self._json_list(payload.selected_codes),
                    payload.input_hash,
                    payload.output_hash,
                    int(payload.external_call),
                    int(payload.fallback_used),
                    payload.input_tokens,
                    payload.output_tokens,
                    payload.estimated_cost_usd,
                    payload.error_code,
                    now.isoformat(),
                ),
            )
        return self.get_provider_call(call_id)

    def link_provider_call_to_draft(
        self,
        call_id: str,
        draft_id: str,
    ) -> ProviderCallAuditRecord:
        """Vincula el evento de auditoría con el borrador persistido."""

        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE llm_provider_calls
                SET draft_id = %s
                WHERE id = %s
                """,
                (draft_id, call_id),
            )
            if cursor.rowcount != 1:
                raise LLMRepositoryError("La llamada auditada no existe.")
        return self.get_provider_call(call_id)

    def get_provider_call(self, call_id: str) -> ProviderCallAuditRecord:
        """Recupera un evento de auditoría."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM llm_provider_calls WHERE id = %s",
                (call_id,),
            ).fetchone()
        if row is None:
            raise LLMRepositoryError("La llamada auditada no existe.")
        return self._row_to_provider_call(row)

    def list_provider_calls(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        limit: int = 50,
    ) -> list[ProviderCallAuditRecord]:
        """Lista auditoría reciente sin contenido ni secretos."""

        bounded_limit = max(1, min(limit, 200))
        query = "SELECT * FROM llm_provider_calls WHERE case_id = %s"
        parameters: list[object] = [case_id]
        if issue_id is not None:
            query += " AND issue_id = %s"
            parameters.append(issue_id)
        query += " ORDER BY created_at DESC LIMIT %s"
        parameters.append(bounded_limit)
        with self._connection() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [self._row_to_provider_call(row) for row in rows]

    def get_draft(self, draft_id: str) -> AssistantDraftRecord:
        """Recupera un borrador por identificador."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM llm_drafts WHERE id = %s",
                (draft_id,),
            ).fetchone()
        if row is None:
            raise LLMDraftNotFoundError("El borrador asistivo no existe.")
        return self._row_to_record(row)

    def list_drafts(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        limit: int = 50,
    ) -> list[AssistantDraftRecord]:
        """Lista historial reciente sin exponer secretos."""

        bounded_limit = max(1, min(limit, 200))
        query = "SELECT * FROM llm_drafts WHERE case_id = %s"
        parameters: list[object] = [case_id]
        if issue_id is not None:
            query += " AND issue_id = %s"
            parameters.append(issue_id)
        query += " ORDER BY created_at DESC LIMIT %s"
        parameters.append(bounded_limit)
        with self._connection() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [self._row_to_record(row) for row in rows]

    def review_draft(
        self,
        draft_id: str,
        *,
        status: DraftStatus,
        edited_text: str | None,
        reviewer_note: str | None,
        reference_codes: list[str],
        invalid_reference_codes: list[str],
        unsupported_claims: list[str],
        citation_coverage: float,
        output_hash: str,
    ) -> AssistantDraftRecord:
        """Registra aprobación o rechazo preservando el texto original."""

        if status is DraftStatus.GENERATED:
            raise ValueError("El estado de revisión debe ser aprobado o rechazado.")

        current = self.get_draft(draft_id)
        if current.status is not DraftStatus.GENERATED:
            raise LLMReviewConflictError(
                "El borrador ya fue revisado y no puede sobrescribirse."
            )

        reviewed_at = utc_now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE llm_drafts
                SET status = %s, edited_text = %s, reviewer_note = %s,
                    reference_codes_json = %s,
                    invalid_reference_codes_json = %s,
                    unsupported_claims_json = %s,
                    citation_coverage = %s, output_hash = %s, reviewed_at = %s
                WHERE id = %s AND status = %s
                """,
                (
                    status.value,
                    edited_text,
                    reviewer_note,
                    self._json_list(reference_codes),
                    self._json_list(invalid_reference_codes),
                    self._json_list(unsupported_claims),
                    citation_coverage,
                    output_hash,
                    reviewed_at.isoformat(),
                    draft_id,
                    DraftStatus.GENERATED.value,
                ),
            )
            if cursor.rowcount != 1:
                raise LLMReviewConflictError(
                    "El borrador cambió durante la revisión."
                )
        return self.get_draft(draft_id)

    def _next_code(
        self,
        connection: Connection[dict[str, Any]],
        case_id: str,
    ) -> str:
        lock_key = f"ius_razon:llm:{case_id}:draft"
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (lock_key,),
        )

        sequence_row = connection.execute(
            """
            SELECT last_value
            FROM llm_draft_sequences
            WHERE case_id = %s
            """,
            (case_id,),
        ).fetchone()
        sequence_value = (
            int(sequence_row["last_value"])
            if sequence_row is not None
            else 0
        )
        existing_value = self._max_existing_code(connection, case_id)
        next_value = max(sequence_value, existing_value) + 1

        connection.execute(
            """
            INSERT INTO llm_draft_sequences (case_id, last_value)
            VALUES (%s, %s)
            ON CONFLICT (case_id)
            DO UPDATE SET last_value = EXCLUDED.last_value
            """,
            (case_id, next_value),
        )
        return f"IA-{next_value:03d}"

    @staticmethod
    def _json_list(values: list[str]) -> str:
        return json.dumps(values, ensure_ascii=False)

    @staticmethod
    def _json_object(value: dict[str, object]) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _json_context(items: list[ContextItem]) -> str:
        return json.dumps(
            [item.model_dump(mode="json") for item in items],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _parse_string_list(value: str) -> list[str]:
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed]

    @staticmethod
    def _parse_object(value: str) -> dict[str, object]:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            return {}
        return {str(key): item for key, item in parsed.items()}

    @staticmethod
    def _parse_context(value: str) -> list[ContextItem]:
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            return []
        return [ContextItem.model_validate(item) for item in parsed]

    @classmethod
    def _row_to_record(
        cls,
        row: dict[str, Any],
    ) -> AssistantDraftRecord:
        return AssistantDraftRecord(
            id=str(row["id"]),
            case_id=str(row["case_id"]),
            issue_id=str(row["issue_id"]),
            code=str(row["code"]),
            task=AssistantTask(str(row["task"])),
            status=DraftStatus(str(row["status"])),
            provider_name=str(row["provider_name"]),
            model_name=str(row["model_name"]),
            request_snapshot=cls._parse_object(str(row["request_json"])),
            context_items=cls._parse_context(str(row["context_json"])),
            response_text=str(row["response_text"]),
            edited_text=(
                str(row["edited_text"])
                if row["edited_text"] is not None
                else None
            ),
            reference_codes=cls._parse_string_list(
                str(row["reference_codes_json"])
            ),
            invalid_reference_codes=cls._parse_string_list(
                str(row["invalid_reference_codes_json"])
            ),
            unsupported_claims=cls._parse_string_list(
                str(row["unsupported_claims_json"])
            ),
            risk_flags=cls._parse_string_list(str(row["risk_flags_json"])),
            citation_coverage=float(row["citation_coverage"]),
            input_hash=str(row["input_hash"]),
            output_hash=str(row["output_hash"]),
            provider_mode=ProviderMode(str(row["provider_mode"])),
            external_call=bool(row["external_call"]),
            fallback_used=bool(row["fallback_used"]),
            fallback_reason=(
                str(row["fallback_reason"])
                if row["fallback_reason"] is not None
                else None
            ),
            provider_request_id=(
                str(row["provider_request_id"])
                if row["provider_request_id"] is not None
                else None
            ),
            input_tokens=(
                int(row["input_tokens"])
                if row["input_tokens"] is not None
                else None
            ),
            output_tokens=(
                int(row["output_tokens"])
                if row["output_tokens"] is not None
                else None
            ),
            estimated_cost_usd=(
                float(row["estimated_cost_usd"])
                if row["estimated_cost_usd"] is not None
                else None
            ),
            reviewer_note=(
                str(row["reviewer_note"])
                if row["reviewer_note"] is not None
                else None
            ),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            reviewed_at=(
                datetime.fromisoformat(str(row["reviewed_at"]))
                if row["reviewed_at"] is not None
                else None
            ),
        )

    @classmethod
    def _row_to_provider_call(
        cls,
        row: dict[str, Any],
    ) -> ProviderCallAuditRecord:
        return ProviderCallAuditRecord(
            id=str(row["id"]),
            draft_id=(
                str(row["draft_id"])
                if row["draft_id"] is not None
                else None
            ),
            case_id=str(row["case_id"]),
            issue_id=str(row["issue_id"]),
            provider_mode=ProviderMode(str(row["provider_mode"])),
            provider_name=str(row["provider_name"]),
            model_name=str(row["model_name"]),
            status=ProviderCallStatus(str(row["status"])),
            selected_codes=cls._parse_string_list(
                str(row["selected_codes_json"])
            ),
            input_hash=str(row["input_hash"]),
            output_hash=(
                str(row["output_hash"])
                if row["output_hash"] is not None
                else None
            ),
            external_call=bool(row["external_call"]),
            fallback_used=bool(row["fallback_used"]),
            input_tokens=(
                int(row["input_tokens"])
                if row["input_tokens"] is not None
                else None
            ),
            output_tokens=(
                int(row["output_tokens"])
                if row["output_tokens"] is not None
                else None
            ),
            estimated_cost_usd=(
                float(row["estimated_cost_usd"])
                if row["estimated_cost_usd"] is not None
                else None
            ),
            error_code=(
                str(row["error_code"])
                if row["error_code"] is not None
                else None
            ),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )
