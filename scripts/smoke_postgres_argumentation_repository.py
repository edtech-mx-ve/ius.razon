from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from ius_razon.domain.argumentation_models import (
    ArgumentPosition,
    ArgumentRelationCreate,
    ArgumentRelationType,
    ArgumentScenarioCreate,
    ArgumentScenarioUpdate,
    ArgumentStatus,
    LegalArgumentCreate,
    LegalArgumentUpdate,
    ScenarioStatus,
)
from ius_razon.domain.models import CaseCreate, LegalIssueCreate
from ius_razon.domain.reasoning_models import (
    AssertionValue,
    ConclusionStatus,
    ConditionRole,
    ReasoningAssertionCreate,
    ReasoningRuleCreate,
    RuleConditionCreate,
    RuleKind,
    SupportLevel,
    TraceOutcome,
)
from ius_razon.persistence.postgres_argumentation_repository import (
    ArgumentationConflictError,
    PostgresArgumentationRepository,
)
from ius_razon.persistence.postgres_reasoning_repository import (
    PostgresReasoningRepository,
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
    argumentation = PostgresArgumentationRepository(settings.database_url)

    core.initialize()
    reasoning.initialize()
    argumentation.initialize()

    case_id: str | None = None
    try:
        case = core.create_case(
            CaseCreate(
                title="SMOKE Argumentation PostgreSQL Sprint 5.4",
                description=(
                    "Expediente sintético temporal para validar argumentación Neon."
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
                question="¿Existe incumplimiento sintético?",
            )
        )

        assertion = reasoning.add_assertion(
            ReasoningAssertionCreate(
                case_id=case.id,
                issue_id=issue.id,
                predicate_key="plazo_vencido",
                statement="El plazo sintético se encuentra vencido.",
                value=AssertionValue.TRUE,
                basis="Premisa sintética para argumentación PostgreSQL.",
                support_codes=[],
            )
        )
        rule = reasoning.add_rule(
            ReasoningRuleCreate(
                case_id=case.id,
                issue_id=issue.id,
                name="Regla sintética de incumplimiento",
                kind=RuleKind.DEFAULT,
                conclusion_key="incumplimiento_presunto",
                conclusion_statement="Existe incumplimiento sintético provisional.",
                conclusion_value=AssertionValue.TRUE,
                priority=100,
                active=True,
                legal_basis_codes=[],
                explanation="Regla sintética para smoke de argumentación.",
                conditions=[
                    RuleConditionCreate(
                        role=ConditionRole.PREREQUISITE,
                        predicate_key="plazo_vencido",
                        expected_value=AssertionValue.TRUE,
                    )
                ],
            )
        )

        run = reasoning.create_run(
            case_id=case.id,
            issue_id=issue.id,
            engine_version="smoke-argumentation-1",
            input_hash="argumentation-smoke-hash",
            input_snapshot={},
        )
        report = reasoning.complete_run(
            run_id=run.id,
            summary={"smoke": True, "conclusions": 1, "traces": 1},
            conclusions=[
                {
                    "predicate_key": "incumplimiento_presunto",
                    "statement": "Existe incumplimiento sintético provisional.",
                    "value": AssertionValue.TRUE.value,
                    "status": ConclusionStatus.PROVISIONAL.value,
                    "support_level": SupportLevel.MEDIUM.value,
                    "rule_codes": [rule.code],
                    "supporting_assertion_codes": [assertion.code],
                    "source_codes": [],
                }
            ],
            traces=[
                {
                    "rule_id": rule.id,
                    "rule_code": rule.code,
                    "outcome": TraceOutcome.FIRED_DEFAULT.value,
                    "detail": {"smoke": True},
                }
            ],
        )
        conclusion = report.conclusions[0]

        context = argumentation.conclusion_context(conclusion.id)
        assert context["case_id"] == case.id
        assert context["issue_id"] == issue.id
        assert context["rule_codes"] == [rule.code]
        assert context["assertion_codes"] == [assertion.code]

        contexts = argumentation.list_conclusion_contexts(case.id, issue.id)
        assert any(item["id"] == conclusion.id for item in contexts)

        favorable = argumentation.add_argument(
            LegalArgumentCreate(
                case_id=case.id,
                issue_id=issue.id,
                title="Argumento sintético favorable",
                position=ArgumentPosition.FAVORABLE,
                thesis_key="incumplimiento_presunto",
                thesis_statement="Existe incumplimiento sintético provisional.",
                thesis_value=AssertionValue.TRUE,
                claim="Debe reconocerse el incumplimiento sintético para esta prueba.",
                reasoning=(
                    "La premisa y la regla sintéticas sostienen la conclusión "
                    "utilizada por este argumento."
                ),
                status=ArgumentStatus.SUPPORTED,
                conclusion_id=conclusion.id,
                rule_codes=[rule.code],
                assertion_codes=[assertion.code],
            )
        )
        assert favorable.code == "ARG-001"

        adverse = argumentation.add_argument(
            LegalArgumentCreate(
                case_id=case.id,
                issue_id=issue.id,
                title="Argumento sintético adverso",
                position=ArgumentPosition.ADVERSE,
                thesis_key="incumplimiento_presunto",
                thesis_statement="No debe tenerse por definitivo el incumplimiento.",
                thesis_value=AssertionValue.FALSE,
                claim="La conclusión provisional puede ser controvertida.",
                reasoning=(
                    "La prueba sintética registra una posición adversa para "
                    "validar relaciones argumentales."
                ),
                status=ArgumentStatus.OBJECTED,
            )
        )
        assert adverse.code == "ARG-002"

        updated = argumentation.update_argument(
            adverse.id,
            LegalArgumentUpdate(
                title="Argumento sintético adverso actualizado",
                position=ArgumentPosition.ADVERSE,
                thesis_key="incumplimiento_presunto",
                thesis_statement="El incumplimiento sigue siendo controvertible.",
                thesis_value=AssertionValue.FALSE,
                claim="La conclusión provisional continúa admitiendo controversia.",
                reasoning=(
                    "Actualización sintética para validar persistencia PostgreSQL."
                ),
                status=ArgumentStatus.WEAKENED,
            ),
        )
        assert updated.code == "ARG-002"

        relation = argumentation.add_relation(
            ArgumentRelationCreate(
                case_id=case.id,
                issue_id=issue.id,
                source_argument_id=adverse.id,
                target_argument_id=favorable.id,
                relation_type=ArgumentRelationType.ATTACKS,
                rationale="Ataque sintético para validar la relación dirigida.",
            )
        )
        assert relation.code == "REL-001"

        try:
            argumentation.add_relation(
                ArgumentRelationCreate(
                    case_id=case.id,
                    issue_id=issue.id,
                    source_argument_id=adverse.id,
                    target_argument_id=favorable.id,
                    relation_type=ArgumentRelationType.ATTACKS,
                    rationale="Relación duplicada que debe rechazarse.",
                )
            )
        except ArgumentationConflictError:
            pass
        else:
            raise AssertionError("La relación argumental duplicada no fue rechazada.")

        scenario = argumentation.add_scenario(
            ArgumentScenarioCreate(
                case_id=case.id,
                issue_id=issue.id,
                name="Escenario sintético principal",
                description=(
                    "Escenario temporal para validar persistencia argumental Neon."
                ),
                status=ScenarioStatus.ACTIVE,
                argument_ids=[favorable.id, adverse.id],
                assumptions=["Supuesto sintético controlado."],
            )
        )
        assert scenario.code == "SCN-001"

        scenario = argumentation.update_scenario(
            scenario.id,
            ArgumentScenarioUpdate(
                name="Escenario sintético actualizado",
                description=(
                    "Escenario actualizado para validar mutación PostgreSQL."
                ),
                status=ScenarioStatus.ACTIVE,
                argument_ids=[favorable.id, adverse.id],
                assumptions=[
                    "Supuesto sintético controlado.",
                    "Segundo supuesto sintético.",
                ],
            ),
        )
        assert scenario.code == "SCN-001"

        assert len(argumentation.list_arguments(case.id, issue.id)) == 2
        assert len(argumentation.list_relations(case.id, issue.id)) == 1
        assert len(argumentation.list_scenarios(case.id, issue.id)) == 1

        known = argumentation.known_codes(case.id, issue.id)
        assert assertion.code in known
        assert rule.code in known
        assert conclusion.code in known

        metadata = argumentation.issue_metadata(case.id, issue.id)
        assert metadata["issue_code"] == issue.code
        assert argumentation.snapshot_timestamp(case.id, issue.id)

        try:
            argumentation.delete_argument(
                favorable.id,
                confirmation=favorable.code,
            )
        except ArgumentationConflictError:
            pass
        else:
            raise AssertionError(
                "No se protegió un argumento con dependencias argumentales."
            )

        argumentation.delete_relation(
            relation.id,
            confirmation=relation.code,
        )

        try:
            argumentation.delete_argument(
                favorable.id,
                confirmation=favorable.code,
            )
        except ArgumentationConflictError:
            pass
        else:
            raise AssertionError(
                "No se protegió un argumento incluido en un escenario."
            )

        argumentation.delete_scenario(
            scenario.id,
            confirmation=scenario.code,
        )
        argumentation.delete_argument(
            adverse.id,
            confirmation=adverse.code,
        )
        argumentation.delete_argument(
            favorable.id,
            confirmation=favorable.code,
        )

        events = core.list_audit_events(case.id)
        argumentation_events = [
            event
            for event in events
            if event.event_type.startswith("argumentation.")
        ]
        assert len(argumentation_events) >= 8

        print(
            "PostgresArgumentationRepository Neon: OK | "
            "argumentos=OK | relaciones=OK | escenarios=OK | "
            "conclusiones=OK | dependencias=OK | auditoría=OK | códigos=OK"
        )
    finally:
        if case_id is not None:
            cleanup(case_id, settings.direct_database_url)
            print("Datos sintéticos de argumentación eliminados de Neon.")


def main() -> int:
    try:
        run_smoke()
    except Exception as exc:
        print(
            f"Smoke PostgresArgumentationRepository falló: {exc}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
