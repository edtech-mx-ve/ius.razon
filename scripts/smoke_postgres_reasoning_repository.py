from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from ius_razon.domain.models import CaseCreate, LegalIssueCreate
from ius_razon.domain.reasoning_models import (
    AssertionValue,
    ConclusionStatus,
    ConditionRole,
    ReasoningAssertionCreate,
    ReasoningAssertionUpdate,
    ReasoningRuleCreate,
    ReasoningRuleUpdate,
    RuleConditionCreate,
    RuleKind,
    SupportLevel,
    TraceOutcome,
)
from ius_razon.persistence.postgres_reasoning_repository import (
    PostgresReasoningRepository,
    ReasoningConflictError,
)
from ius_razon.persistence.postgres_repository import PostgresRepository
from ius_razon.persistence.postgres_runtime import load_postgres_settings

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
    core = PostgresRepository(settings.database_url)
    reasoning = PostgresReasoningRepository(settings.database_url)

    core.initialize()
    reasoning.initialize()

    case_id: str | None = None
    try:
        case = core.create_case(
            CaseCreate(
                title="SMOKE Reasoning PostgreSQL Sprint 5.4",
                description=(
                    "Expediente sintético temporal para validar razonamiento Neon."
                ),
                matter="Mercantil",
                jurisdiction="México",
            )
        )
        case_id = case.id

        issue = core.add_legal_issue(
            LegalIssueCreate(
                case_id=case.id,
                title="Incumplimiento sintético",
                question="¿La obligación sintética fue incumplida?",
            )
        )

        reasoning.validate_case_issue(case.id, issue.id)

        assertion = reasoning.add_assertion(
            ReasoningAssertionCreate(
                case_id=case.id,
                issue_id=issue.id,
                predicate_key="plazo_vencido",
                statement="El plazo sintético se encuentra vencido.",
                value=AssertionValue.TRUE,
                basis="Premisa sintética controlada para smoke PostgreSQL.",
                support_codes=[],
            )
        )
        assert assertion.code == "A-001"

        rule = reasoning.add_rule(
            ReasoningRuleCreate(
                case_id=case.id,
                issue_id=issue.id,
                name="Regla sintética de mora",
                kind=RuleKind.DEFAULT,
                conclusion_key="mora_presunta",
                conclusion_statement="Existe una mora sintética provisional.",
                conclusion_value=AssertionValue.TRUE,
                priority=100,
                active=True,
                legal_basis_codes=[],
                explanation="Regla sintética controlada para smoke PostgreSQL.",
                conditions=[
                    RuleConditionCreate(
                        role=ConditionRole.PREREQUISITE,
                        predicate_key="plazo_vencido",
                        expected_value=AssertionValue.TRUE,
                    )
                ],
            )
        )
        assert rule.code == "R-001"

        try:
            reasoning.delete_assertion(
                assertion.id,
                confirmation=assertion.code,
            )
        except ReasoningConflictError:
            pass
        else:
            raise AssertionError(
                "La protección de dependencia premisa-regla no se aplicó."
            )

        updated_assertion = reasoning.update_assertion(
            assertion.id,
            ReasoningAssertionUpdate(
                predicate_key="plazo_vencido",
                statement="El plazo sintético continúa vencido.",
                value=AssertionValue.TRUE,
                basis="Premisa sintética actualizada para validar versionado.",
                support_codes=[],
            ),
        )
        assert updated_assertion.code == "A-001"
        assert len(
            reasoning.list_assertion_versions(
                case_id=case.id,
                entity_id=assertion.id,
            )
        ) == 1

        updated_rule = reasoning.update_rule(
            rule.id,
            ReasoningRuleUpdate(
                name="Regla sintética de mora actualizada",
                kind=RuleKind.DEFAULT,
                conclusion_key="mora_presunta",
                conclusion_statement="Persiste una mora sintética provisional.",
                conclusion_value=AssertionValue.TRUE,
                priority=150,
                active=True,
                legal_basis_codes=[],
                explanation="Regla sintética actualizada para validar versionado.",
                conditions=[
                    RuleConditionCreate(
                        role=ConditionRole.PREREQUISITE,
                        predicate_key="plazo_vencido",
                        expected_value=AssertionValue.TRUE,
                    )
                ],
            ),
        )
        assert updated_rule.code == "R-001"
        assert len(
            reasoning.list_rule_versions(
                case_id=case.id,
                entity_id=rule.id,
            )
        ) == 1

        run = reasoning.create_run(
            case_id=case.id,
            issue_id=issue.id,
            engine_version="smoke-postgres-1",
            input_hash="synthetic-input-hash",
            input_snapshot={
                "assertions": [updated_assertion.model_dump(mode="json")],
                "rules": [updated_rule.model_dump(mode="json")],
            },
        )

        report = reasoning.complete_run(
            run_id=run.id,
            summary={
                "smoke": True,
                "conclusions": 1,
                "traces": 1,
            },
            conclusions=[
                {
                    "predicate_key": "mora_presunta",
                    "statement": "Existe una mora sintética provisional.",
                    "value": AssertionValue.TRUE.value,
                    "status": ConclusionStatus.PROVISIONAL.value,
                    "support_level": SupportLevel.HIGH.value,
                    "rule_codes": [updated_rule.code],
                    "supporting_assertion_codes": [updated_assertion.code],
                    "source_codes": [],
                }
            ],
            traces=[
                {
                    "rule_id": updated_rule.id,
                    "rule_code": updated_rule.code,
                    "outcome": TraceOutcome.FIRED_DEFAULT.value,
                    "detail": {"smoke": True},
                }
            ],
        )

        assert report.run.status.value == "Completada"
        assert len(report.conclusions) == 1
        assert len(report.traces) == 1
        assert report.conclusions[0].predicate_key == "mora_presunta"

        recovered = reasoning.get_run_report(run.id)
        assert recovered.run.input_hash == "synthetic-input-hash"
        assert recovered.run.input_snapshot["assertions"]

        codes = reasoning.known_codes(case.id)
        assert assertion.code in codes
        assert rule.code in codes
        assert issue.code in codes

        reasoning.delete_rule(
            rule.id,
            confirmation=rule.code,
        )
        reasoning.delete_assertion(
            assertion.id,
            confirmation=assertion.code,
        )

        assert len(
            reasoning.list_rule_versions(
                case_id=case.id,
                entity_id=rule.id,
            )
        ) == 2
        assert len(
            reasoning.list_assertion_versions(
                case_id=case.id,
                entity_id=assertion.id,
            )
        ) == 2

        events = core.list_audit_events(case.id)
        reasoning_events = [
            event
            for event in events
            if event.event_type.startswith("reasoning.")
        ]
        assert len(reasoning_events) >= 6

        print(
            "PostgresReasoningRepository Neon: OK | "
            "premisas=OK | reglas=OK | dependencias=OK | "
            "versionado=OK | ejecuciones=OK | trazas=OK | "
            "auditoría=OK | códigos=OK"
        )
    finally:
        if case_id is not None:
            cleanup(case_id, settings.direct_database_url)
            print("Datos sintéticos de razonamiento eliminados de Neon.")


def main() -> int:
    try:
        run_smoke()
    except Exception as exc:
        print(
            f"Smoke PostgresReasoningRepository falló: {exc}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
