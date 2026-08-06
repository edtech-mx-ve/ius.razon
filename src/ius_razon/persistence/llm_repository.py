from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

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


class LLMRepository:
    """Persistencia local de borradores, auditoría y decisiones humanas."""

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
            raise LLMRepositoryError(
                "La operación del asistente no pudo completarse."
            ) from exc
        finally:
            connection.close()

    def initialize(self) -> None:
        """Aplica migraciones aditivas para borradores y auditoría externa."""

        schema = """
        CREATE TABLE IF NOT EXISTS llm_draft_sequences (
            case_id TEXT PRIMARY KEY REFERENCES cases(id) ON DELETE CASCADE,
            last_value INTEGER NOT NULL CHECK(last_value >= 0)
        );

        CREATE TABLE IF NOT EXISTS llm_drafts (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            task TEXT NOT NULL,
            status TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            model_name TEXT NOT NULL,
            request_json TEXT NOT NULL,
            context_json TEXT NOT NULL,
            response_text TEXT NOT NULL,
            edited_text TEXT,
            reference_codes_json TEXT NOT NULL,
            invalid_reference_codes_json TEXT NOT NULL,
            unsupported_claims_json TEXT NOT NULL,
            risk_flags_json TEXT NOT NULL,
            citation_coverage REAL NOT NULL,
            input_hash TEXT NOT NULL,
            output_hash TEXT NOT NULL,
            provider_mode TEXT NOT NULL DEFAULT 'Simulado local',
            external_call INTEGER NOT NULL DEFAULT 0,
            fallback_used INTEGER NOT NULL DEFAULT 0,
            fallback_reason TEXT,
            provider_request_id TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            estimated_cost_usd REAL,
            reviewer_note TEXT,
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS llm_provider_calls (
            id TEXT PRIMARY KEY,
            draft_id TEXT REFERENCES llm_drafts(id) ON DELETE SET NULL,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            provider_mode TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            model_name TEXT NOT NULL,
            status TEXT NOT NULL,
            selected_codes_json TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            output_hash TEXT,
            external_call INTEGER NOT NULL,
            fallback_used INTEGER NOT NULL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            estimated_cost_usd REAL,
            error_code TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_llm_drafts_case_issue
            ON llm_drafts(case_id, issue_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_llm_drafts_status
            ON llm_drafts(status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_llm_calls_case_issue
            ON llm_provider_calls(case_id, issue_id, created_at DESC);
        """
        with self._connection() as connection:
            connection.executescript(schema)
            self._ensure_draft_columns(connection)

    @staticmethod
    def _ensure_draft_columns(connection: sqlite3.Connection) -> None:
        """Amplía bases creadas por v0.5.x sin reconstruir ni perder datos."""

        existing = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(llm_drafts)")
        }
        columns = {
            "provider_mode": "TEXT NOT NULL DEFAULT 'Simulado local'",
            "external_call": "INTEGER NOT NULL DEFAULT 0",
            "fallback_used": "INTEGER NOT NULL DEFAULT 0",
            "fallback_reason": "TEXT",
            "provider_request_id": "TEXT",
            "input_tokens": "INTEGER",
            "output_tokens": "INTEGER",
            "estimated_cost_usd": "REAL",
        }
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(
                    f"ALTER TABLE llm_drafts ADD COLUMN {name} {definition}"
                )

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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL)
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
                ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                SET draft_id = ?
                WHERE id = ?
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
                "SELECT * FROM llm_provider_calls WHERE id = ?",
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
        query = "SELECT * FROM llm_provider_calls WHERE case_id = ?"
        parameters: list[object] = [case_id]
        if issue_id is not None:
            query += " AND issue_id = ?"
            parameters.append(issue_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        parameters.append(bounded_limit)
        with self._connection() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [self._row_to_provider_call(row) for row in rows]

    def get_draft(self, draft_id: str) -> AssistantDraftRecord:
        """Recupera un borrador por identificador."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM llm_drafts WHERE id = ?",
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
        query = "SELECT * FROM llm_drafts WHERE case_id = ?"
        parameters: list[object] = [case_id]
        if issue_id is not None:
            query += " AND issue_id = ?"
            parameters.append(issue_id)
        query += " ORDER BY created_at DESC LIMIT ?"
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
                SET status = ?, edited_text = ?, reviewer_note = ?,
                    reference_codes_json = ?,
                    invalid_reference_codes_json = ?,
                    unsupported_claims_json = ?,
                    citation_coverage = ?, output_hash = ?, reviewed_at = ?
                WHERE id = ? AND status = ?
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

    @staticmethod
    def _next_code(
        connection: sqlite3.Connection,
        case_id: str,
    ) -> str:
        connection.execute(
            """
            INSERT INTO llm_draft_sequences (case_id, last_value)
            VALUES (?, 0)
            ON CONFLICT(case_id) DO NOTHING
            """,
            (case_id,),
        )
        connection.execute(
            """
            UPDATE llm_draft_sequences
            SET last_value = last_value + 1
            WHERE case_id = ?
            """,
            (case_id,),
        )
        row = connection.execute(
            """
            SELECT last_value
            FROM llm_draft_sequences
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()
        if row is None:
            raise LLMRepositoryError("No fue posible asignar código al borrador.")
        return f"IA-{int(row['last_value']):03d}"

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
        row: sqlite3.Row,
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
        row: sqlite3.Row,
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
