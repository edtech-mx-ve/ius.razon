from __future__ import annotations

import hashlib
import json
import logging

from ius_razon.domain.reasoning_models import (
    ReasoningAssertionCreate,
    ReasoningAssertionRecord,
    ReasoningAssertionUpdate,
    ReasoningRuleCreate,
    ReasoningRuleRecord,
    ReasoningRuleUpdate,
    ReasoningRunRecord,
    ReasoningRunReport,
    ReasoningVersionRecord,
)
from ius_razon.persistence.mutation_backup import MutationBackup
from ius_razon.persistence.reasoning_repository_protocol import (
    ReasoningRepositoryProtocol,
)
from ius_razon.services.reasoning_engine import ReasoningEngine

LOGGER = logging.getLogger(__name__)


class ReasoningService:
    """Orquesta validación, mutaciones seguras y ejecución del razonamiento."""

    def __init__(
        self,
        repository: ReasoningRepositoryProtocol,
        engine: ReasoningEngine | None = None,
        *,
        mutation_backup: MutationBackup,
    ) -> None:
        self._repository = repository
        self._engine = engine or ReasoningEngine()
        self._mutation_backup = mutation_backup

    def add_assertion(
        self,
        payload: ReasoningAssertionCreate,
    ) -> ReasoningAssertionRecord:
        self._repository.validate_case_issue(payload.case_id, payload.issue_id)
        self._validate_codes(
            payload.case_id,
            payload.support_codes,
            label="referencias de soporte",
        )
        record = self._repository.add_assertion(payload)
        LOGGER.info(
            "Premisa de razonamiento agregada. case_id=%s assertion_id=%s",
            payload.case_id,
            record.id,
        )
        return record

    def update_assertion(
        self,
        assertion_id: str,
        payload: ReasoningAssertionUpdate,
    ) -> ReasoningAssertionRecord:
        current = self._repository.get_assertion(assertion_id)
        self._validate_codes(
            current.case_id,
            payload.support_codes,
            label="referencias de soporte",
        )
        self._backup_before_mutation("actualizar premisa")
        record = self._repository.update_assertion(assertion_id, payload)
        LOGGER.info(
            "Premisa actualizada. case_id=%s assertion_id=%s",
            current.case_id,
            assertion_id,
        )
        return record

    def delete_assertion(self, assertion_id: str, *, confirmation: str) -> None:
        current = self._repository.get_assertion(assertion_id)
        self._backup_before_mutation("eliminar premisa")
        self._repository.delete_assertion(
            assertion_id,
            confirmation=confirmation,
        )
        LOGGER.info(
            "Premisa eliminada. case_id=%s assertion_id=%s code=%s",
            current.case_id,
            assertion_id,
            current.code,
        )

    def list_assertions(
        self,
        case_id: str,
        issue_id: str | None = None,
    ) -> list[ReasoningAssertionRecord]:
        return self._repository.list_assertions(case_id, issue_id)

    def list_assertion_versions(
        self,
        *,
        case_id: str,
        entity_id: str | None = None,
    ) -> list[ReasoningVersionRecord]:
        return self._repository.list_assertion_versions(
            case_id=case_id,
            entity_id=entity_id,
        )

    def add_rule(self, payload: ReasoningRuleCreate) -> ReasoningRuleRecord:
        self._repository.validate_case_issue(payload.case_id, payload.issue_id)
        self._validate_codes(
            payload.case_id,
            payload.legal_basis_codes,
            label="fundamentos jurídicos",
            allowed_prefixes=("N-", "J-", "D-"),
        )
        record = self._repository.add_rule(payload)
        LOGGER.info(
            "Regla de razonamiento agregada. case_id=%s rule_id=%s",
            payload.case_id,
            record.id,
        )
        return record

    def update_rule(
        self,
        rule_id: str,
        payload: ReasoningRuleUpdate,
    ) -> ReasoningRuleRecord:
        current = self._repository.get_rule(rule_id)
        self._validate_codes(
            current.case_id,
            payload.legal_basis_codes,
            label="fundamentos jurídicos",
            allowed_prefixes=("N-", "J-", "D-"),
        )
        self._backup_before_mutation("actualizar regla")
        record = self._repository.update_rule(rule_id, payload)
        LOGGER.info(
            "Regla actualizada. case_id=%s rule_id=%s active=%s",
            current.case_id,
            rule_id,
            payload.active,
        )
        return record

    def delete_rule(self, rule_id: str, *, confirmation: str) -> None:
        current = self._repository.get_rule(rule_id)
        self._backup_before_mutation("eliminar regla")
        self._repository.delete_rule(rule_id, confirmation=confirmation)
        LOGGER.info(
            "Regla eliminada. case_id=%s rule_id=%s code=%s",
            current.case_id,
            rule_id,
            current.code,
        )

    def list_rules(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        active_only: bool = False,
    ) -> list[ReasoningRuleRecord]:
        return self._repository.list_rules(
            case_id,
            issue_id,
            active_only=active_only,
        )

    def list_rule_versions(
        self,
        *,
        case_id: str,
        entity_id: str | None = None,
    ) -> list[ReasoningVersionRecord]:
        return self._repository.list_rule_versions(
            case_id=case_id,
            entity_id=entity_id,
        )

    def run(self, *, case_id: str, issue_id: str) -> ReasoningRunReport:
        self._repository.validate_case_issue(case_id, issue_id)
        assertions = self._repository.list_assertions(case_id, issue_id)
        rules = self._repository.list_rules(
            case_id,
            issue_id,
            active_only=True,
        )
        if not assertions:
            raise ValueError(
                "Registra al menos una premisa antes de ejecutar el razonamiento."
            )
        if not rules:
            raise ValueError(
                "Registra al menos una regla activa antes de ejecutar el razonamiento."
            )

        input_snapshot = self._input_payload(assertions, rules)
        input_hash = self._hash_payload(input_snapshot)
        run = self._repository.create_run(
            case_id=case_id,
            issue_id=issue_id,
            engine_version=self._engine.VERSION,
            input_hash=input_hash,
            input_snapshot=input_snapshot,
        )
        try:
            result = self._engine.evaluate(assertions, rules)
            report = self._repository.complete_run(
                run_id=run.id,
                summary=result.summary,
                conclusions=[dict(item) for item in result.conclusions],
                traces=[dict(item) for item in result.traces],
            )
        except Exception as exc:
            self._repository.fail_run(run.id, str(exc))
            raise
        LOGGER.info(
            "Razonamiento ejecutado. case_id=%s run_id=%s conclusions=%s",
            case_id,
            run.id,
            len(report.conclusions),
        )
        return report

    def list_runs(
        self,
        case_id: str,
        issue_id: str | None = None,
        *,
        limit: int = 20,
    ) -> list[ReasoningRunRecord]:
        return self._repository.list_runs(case_id, issue_id, limit=limit)

    def get_run_report(self, run_id: str) -> ReasoningRunReport:
        return self._repository.get_run_report(run_id)

    def export_run_json(self, run_id: str) -> str:
        """Exporta entradas, conclusiones y traza en JSON reproducible."""

        report = self.get_run_report(run_id)
        return json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    def export_run_markdown(self, run_id: str) -> str:
        """Genera un reporte Markdown legible sin alterar el resultado persistido."""

        report = self.get_run_report(run_id)
        lines = [
            "# IUS-Razón · Reporte de inferencia",
            "",
            f"- Ejecución: `{report.run.id}`",
            f"- Fecha UTC: `{report.run.started_at.isoformat()}`",
            f"- Motor: `{report.run.engine_version}`",
            f"- Huella SHA-256: `{report.run.input_hash}`",
            f"- Estado: `{report.run.status.value}`",
            "",
            "## Resumen",
            "",
        ]
        for key, value in sorted(report.run.summary.items()):
            lines.append(f"- {key}: `{value}`")
        lines.extend(["", "## Conclusiones", ""])
        if not report.conclusions:
            lines.append("No se derivaron conclusiones.")
        for conclusion in report.conclusions:
            lines.extend(
                [
                    f"### {conclusion.code} · {conclusion.predicate_key}",
                    "",
                    conclusion.statement,
                    "",
                    f"- Valor: **{conclusion.value.value}**",
                    f"- Estado: {conclusion.status.value}",
                    f"- Soporte: {conclusion.support_level.value}",
                    f"- Reglas: {', '.join(conclusion.rule_codes) or 'Ninguna'}",
                    (
                        "- Premisas: "
                        f"{', '.join(conclusion.supporting_assertion_codes) or 'Ninguna'}"
                    ),
                    f"- Fuentes: {', '.join(conclusion.source_codes) or 'Ninguna'}",
                    "",
                ]
            )
        lines.extend(["## Resolución de conflictos", ""])
        conflict_outcomes = {
            "Derrotada por menor prioridad",
            "Derrotada por regla estricta rival",
            "Derrotada por menor especificidad",
            "Empate entre reglas rivales",
            "Retirada por dependencia derrotada",
            "Ciclo no convergente",
        }
        conflict_traces = [
            trace
            for trace in report.traces
            if trace.outcome.value in conflict_outcomes
        ]
        if not conflict_traces:
            lines.append("No se registraron derrotas, empates ni retiradas.")
            lines.append("")
        for trace in conflict_traces:
            lines.extend(
                [
                    f"- {trace.rule_code}: **{trace.outcome.value}**",
                    (
                        "  - Detalle: "
                        f"`{json.dumps(trace.detail, ensure_ascii=False)}`"
                    ),
                ]
            )
        if conflict_traces:
            lines.append("")

        lines.extend(["## Traza", ""])
        for trace in report.traces:
            lines.extend(
                [
                    f"### {trace.sequence}. {trace.rule_code}",
                    "",
                    f"- Resultado: {trace.outcome.value}",
                    f"- Detalle: `{json.dumps(trace.detail, ensure_ascii=False)}`",
                    "",
                ]
            )
        lines.extend(
            [
                "## Advertencia",
                "",
                (
                    "Este resultado depende únicamente de los datos registrados. "
                    "No constituye asesoría jurídica ni verifica automáticamente "
                    "autenticidad, vigencia o aplicabilidad."
                ),
                "",
            ]
        )
        return "\n".join(lines)

    def compare_runs(
        self,
        first_run_id: str,
        second_run_id: str,
    ) -> dict[str, object]:
        """Compara dos ejecuciones por clave y valor de conclusión."""

        first = self.get_run_report(first_run_id)
        second = self.get_run_report(second_run_id)
        if first.run.case_id != second.run.case_id:
            raise ValueError("Las ejecuciones pertenecen a expedientes distintos.")
        if first.run.issue_id != second.run.issue_id:
            raise ValueError("Las ejecuciones pertenecen a problemas jurídicos distintos.")

        first_map = {
            (item.predicate_key, item.value.value): item.status.value
            for item in first.conclusions
        }
        second_map = {
            (item.predicate_key, item.value.value): item.status.value
            for item in second.conclusions
        }
        added = sorted(
            f"{key}={value}"
            for key, value in second_map.keys() - first_map.keys()
        )
        removed = sorted(
            f"{key}={value}"
            for key, value in first_map.keys() - second_map.keys()
        )
        changed = sorted(
            f"{key}={value}: {first_map[(key, value)]} → {second_map[(key, value)]}"
            for key, value in first_map.keys() & second_map.keys()
            if first_map[(key, value)] != second_map[(key, value)]
        )
        first_trace_map = {
            trace.rule_code: trace.outcome.value
            for trace in first.traces
        }
        second_trace_map = {
            trace.rule_code: trace.outcome.value
            for trace in second.traces
        }
        changed_rule_outcomes = sorted(
            (
                f"{code}: {first_trace_map[code]} → "
                f"{second_trace_map[code]}"
            )
            for code in first_trace_map.keys() & second_trace_map.keys()
            if first_trace_map[code] != second_trace_map[code]
        )
        return {
            "same_input": first.run.input_hash == second.run.input_hash,
            "first_input_hash": first.run.input_hash,
            "second_input_hash": second.run.input_hash,
            "added_conclusions": added,
            "removed_conclusions": removed,
            "changed_statuses": changed,
            "changed_rule_outcomes": changed_rule_outcomes,
        }

    def _validate_codes(
        self,
        case_id: str,
        codes: list[str],
        *,
        label: str,
        allowed_prefixes: tuple[str, ...] | None = None,
    ) -> None:
        if allowed_prefixes is not None:
            invalid_type = [
                code for code in codes if not code.startswith(allowed_prefixes)
            ]
            if invalid_type:
                raise ValueError(
                    f"Los {label} solo admiten códigos "
                    f"{', '.join(allowed_prefixes)}. Inválidos: "
                    f"{', '.join(invalid_type)}"
                )
        known = self._repository.known_codes(case_id)
        missing = [code for code in codes if code not in known]
        if missing:
            raise ValueError(
                f"No existen en el expediente los siguientes {label}: "
                f"{', '.join(missing)}"
            )

    def _backup_before_mutation(self, operation: str) -> None:
        self._mutation_backup.before_mutation()
        LOGGER.info(
            "Política de respaldo previo completada. operation=%s",
            operation,
        )

    @staticmethod
    def _input_payload(
        assertions: list[ReasoningAssertionRecord],
        rules: list[ReasoningRuleRecord],
    ) -> dict[str, object]:
        return {
            "assertions": [
                assertion.model_dump(mode="json")
                for assertion in assertions
            ],
            "rules": [rule.model_dump(mode="json") for rule in rules],
        }

    @staticmethod
    def _hash_payload(payload: dict[str, object]) -> str:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    @classmethod
    def _input_hash(
        cls,
        assertions: list[ReasoningAssertionRecord],
        rules: list[ReasoningRuleRecord],
    ) -> str:
        """Compatibilidad: calcula la huella a partir de registros actuales."""

        return cls._hash_payload(cls._input_payload(assertions, rules))
