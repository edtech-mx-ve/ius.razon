from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from ius_razon.config import AppConfig
from ius_razon.domain.enums import (
    CaseStatus,
    ConfidentialityLevel,
    LegalIssueStatus,
)
from ius_razon.domain.models import CaseCreate, LegalIssueCreate
from ius_razon.domain.reasoning_models import (
    AssertionValue,
    ConditionRole,
    ReasoningAssertionCreate,
    ReasoningAssertionRecord,
    ReasoningRuleCreate,
    ReasoningRuleRecord,
    RuleConditionCreate,
    RuleKind,
    TraceOutcome,
)
from ius_razon.persistence.reasoning_repository import ReasoningRepository
from ius_razon.persistence.sqlite_repository import SQLiteRepository
from ius_razon.services.case_service import CaseService
from ius_razon.services.reasoning_engine import EngineResult, ReasoningEngine
from ius_razon.services.reasoning_service import ReasoningService

NOW = datetime.now(UTC)


def assertion(
    code: str,
    key: str,
    value: AssertionValue,
) -> ReasoningAssertionRecord:
    return ReasoningAssertionRecord(
        id=code,
        case_id="case-1",
        issue_id="issue-1",
        code=code,
        predicate_key=key,
        statement=f"Premisa {key}.",
        value=value,
        basis="Fundamento suficientemente detallado para la prueba.",
        support_codes=[],
        created_at=NOW,
        updated_at=NOW,
    )


def rule(
    code: str,
    *,
    prerequisites: list[tuple[str, AssertionValue]],
    conclusion_key: str,
    conclusion_value: AssertionValue,
    priority: int = 100,
    kind: RuleKind = RuleKind.STRICT,
    exceptions: list[tuple[str, AssertionValue]] | None = None,
) -> ReasoningRuleRecord:
    conditions = [
        RuleConditionCreate(
            role=ConditionRole.PREREQUISITE,
            predicate_key=key,
            expected_value=value,
        )
        for key, value in prerequisites
    ]
    conditions.extend(
        RuleConditionCreate(
            role=ConditionRole.EXCEPTION,
            predicate_key=key,
            expected_value=value,
        )
        for key, value in (exceptions or [])
    )
    return ReasoningRuleRecord(
        id=code,
        case_id="case-1",
        issue_id="issue-1",
        code=code,
        name=f"Regla {code}",
        kind=kind,
        conclusion_key=conclusion_key,
        conclusion_statement=f"Conclusión {conclusion_key}.",
        conclusion_value=conclusion_value,
        priority=priority,
        active=True,
        legal_basis_codes=[],
        explanation="Puente inferencial suficientemente explicado.",
        conditions=conditions,
        created_at=NOW,
        updated_at=NOW,
    )


def trace_map(result: EngineResult) -> dict[str, str]:
    return {
        item["rule_code"]: item["outcome"]
        for item in result.traces
    }


def test_higher_priority_rule_defeats_rival() -> None:
    rules = [
        rule(
            "R-001",
            prerequisites=[("premisa_base", AssertionValue.TRUE)],
            conclusion_key="resultado_rival",
            conclusion_value=AssertionValue.TRUE,
            priority=100,
        ),
        rule(
            "R-002",
            prerequisites=[("premisa_base", AssertionValue.TRUE)],
            conclusion_key="resultado_rival",
            conclusion_value=AssertionValue.FALSE,
            priority=200,
        ),
    ]

    result = ReasoningEngine().evaluate(
        [assertion("A-001", "premisa_base", AssertionValue.TRUE)],
        rules,
    )

    assert [
        (item["predicate_key"], item["value"])
        for item in result.conclusions
    ] == [("resultado_rival", AssertionValue.FALSE.value)]
    traces = trace_map(result)
    assert traces["R-001"] == TraceOutcome.DEFEATED_PRIORITY.value
    assert traces["R-002"] == TraceOutcome.FIRED_STRICT.value
    assert result.summary["defeated_rule_count"] == 1


def test_strict_rule_defeats_default_at_equal_priority() -> None:
    rules = [
        rule(
            "R-001",
            prerequisites=[("premisa_base", AssertionValue.TRUE)],
            conclusion_key="resultado_rival",
            conclusion_value=AssertionValue.TRUE,
            kind=RuleKind.DEFAULT,
        ),
        rule(
            "R-002",
            prerequisites=[("premisa_base", AssertionValue.TRUE)],
            conclusion_key="resultado_rival",
            conclusion_value=AssertionValue.FALSE,
            kind=RuleKind.STRICT,
        ),
    ]

    result = ReasoningEngine().evaluate(
        [assertion("A-001", "premisa_base", AssertionValue.TRUE)],
        rules,
    )

    traces = trace_map(result)
    assert traces["R-001"] == TraceOutcome.DEFEATED_KIND.value
    assert traces["R-002"] == TraceOutcome.FIRED_STRICT.value
    assert result.conclusions[0]["value"] == AssertionValue.FALSE.value


def test_more_specific_rule_defeats_equal_priority_and_kind() -> None:
    assertions = [
        assertion("A-001", "premisa_base", AssertionValue.TRUE),
        assertion("A-002", "hecho_adicional", AssertionValue.TRUE),
    ]
    rules = [
        rule(
            "R-001",
            prerequisites=[("premisa_base", AssertionValue.TRUE)],
            conclusion_key="resultado_rival",
            conclusion_value=AssertionValue.TRUE,
        ),
        rule(
            "R-002",
            prerequisites=[
                ("premisa_base", AssertionValue.TRUE),
                ("hecho_adicional", AssertionValue.TRUE),
            ],
            conclusion_key="resultado_rival",
            conclusion_value=AssertionValue.FALSE,
        ),
    ]

    result = ReasoningEngine().evaluate(assertions, rules)

    traces = trace_map(result)
    assert traces["R-001"] == TraceOutcome.DEFEATED_SPECIFICITY.value
    assert traces["R-002"] == TraceOutcome.FIRED_STRICT.value
    assert result.conclusions[0]["value"] == AssertionValue.FALSE.value


def test_dependent_conclusion_is_withdrawn_after_late_defeat() -> None:
    rules = [
        rule(
            "R-001",
            prerequisites=[("premisa_base", AssertionValue.TRUE)],
            conclusion_key="resultado_intermedio",
            conclusion_value=AssertionValue.TRUE,
            priority=100,
        ),
        rule(
            "R-004",
            prerequisites=[("premisa_base", AssertionValue.TRUE)],
            conclusion_key="activador_rival",
            conclusion_value=AssertionValue.TRUE,
        ),
        rule(
            "R-002",
            prerequisites=[("activador_rival", AssertionValue.TRUE)],
            conclusion_key="resultado_intermedio",
            conclusion_value=AssertionValue.FALSE,
            priority=200,
        ),
        rule(
            "R-003",
            prerequisites=[("resultado_intermedio", AssertionValue.TRUE)],
            conclusion_key="resultado_dependiente",
            conclusion_value=AssertionValue.TRUE,
        ),
    ]

    result = ReasoningEngine().evaluate(
        [assertion("A-001", "premisa_base", AssertionValue.TRUE)],
        rules,
    )

    conclusion_keys = {
        item["predicate_key"] for item in result.conclusions
    }
    assert "resultado_dependiente" not in conclusion_keys
    assert "resultado_intermedio" in conclusion_keys
    traces = trace_map(result)
    assert traces["R-001"] == TraceOutcome.DEFEATED_PRIORITY.value
    assert traces["R-003"] == TraceOutcome.WITHDRAWN_DEPENDENCY.value
    assert result.summary["withdrawn_rule_count"] == 1


def test_default_rule_is_blocked_by_confirmed_contrary_assertion() -> None:
    rules = [
        rule(
            "R-001",
            prerequisites=[("premisa_base", AssertionValue.TRUE)],
            conclusion_key="resultado_rival",
            conclusion_value=AssertionValue.TRUE,
            kind=RuleKind.DEFAULT,
        )
    ]
    assertions = [
        assertion("A-001", "premisa_base", AssertionValue.TRUE),
        assertion("A-002", "resultado_rival", AssertionValue.FALSE),
    ]

    result = ReasoningEngine().evaluate(assertions, rules)

    assert result.conclusions == []
    assert result.traces[0]["outcome"] == TraceOutcome.BLOCKED_CONTRARY.value


def test_engine_result_is_deterministic_and_reports_policy() -> None:
    assertions = [assertion("A-001", "premisa_base", AssertionValue.TRUE)]
    rules = [
        rule(
            "R-001",
            prerequisites=[("premisa_base", AssertionValue.TRUE)],
            conclusion_key="resultado_final",
            conclusion_value=AssertionValue.TRUE,
        )
    ]

    first = ReasoningEngine().evaluate(assertions, rules)
    second = ReasoningEngine().evaluate(assertions, list(reversed(rules)))

    assert first == second
    assert first.summary["engine_version"] == "3.2.0"
    assert first.summary["defeat_policy"] == "priority>kind>specificity"


def build_services(tmp_path: Path) -> tuple[CaseService, ReasoningService]:
    data_dir = tmp_path / "data"
    config = AppConfig(
        project_root=tmp_path,
        data_dir=data_dir,
        db_path=data_dir / "test.db",
        upload_dir=data_dir / "uploads",
        log_dir=data_dir / "logs",
        max_upload_bytes=1024 * 1024,
        log_level="INFO",
    )
    config.upload_dir.mkdir(parents=True)
    config.log_dir.mkdir(parents=True)
    case_repository = SQLiteRepository(config.db_path)
    case_repository.initialize()
    reasoning_repository = ReasoningRepository(config.db_path)
    reasoning_repository.initialize()
    return (
        CaseService(case_repository, config),
        ReasoningService(
            reasoning_repository,
            backup_dir=data_dir / "backups",
        ),
    )


def test_defeat_trace_is_persisted_and_exported(tmp_path: Path) -> None:
    case_service, reasoning_service = build_services(tmp_path)
    case_record = case_service.create_case(
        CaseCreate(
            title="Caso de rivalidad",
            description="Expediente sintético para persistencia de derrota.",
            matter="Mercantil",
            jurisdiction="México",
            opened_on=date.today(),
            status=CaseStatus.OPEN,
            confidentiality=ConfidentialityLevel.PUBLIC_DEMO,
        )
    )
    issue = case_service.add_legal_issue(
        LegalIssueCreate(
            case_id=case_record.id,
            title="Rivalidad de reglas",
            question="¿Qué regla debe prevalecer?",
            description="Problema sintético de prioridad.",
            status=LegalIssueStatus.OPEN,
        )
    )
    reasoning_service.add_assertion(
        ReasoningAssertionCreate(
            case_id=case_record.id,
            issue_id=issue.id,
            predicate_key="premisa_base",
            statement="La premisa base está confirmada.",
            value=AssertionValue.TRUE,
            basis="Valoración controlada para la prueba de persistencia.",
            support_codes=[],
        )
    )
    for code_value, conclusion_value, priority in [
        ("regla_favorable", AssertionValue.TRUE, 100),
        ("regla_contraria", AssertionValue.FALSE, 200),
    ]:
        reasoning_service.add_rule(
            ReasoningRuleCreate(
                case_id=case_record.id,
                issue_id=issue.id,
                name=code_value,
                kind=RuleKind.STRICT,
                conclusion_key="resultado_rival",
                conclusion_statement="Conclusión rival persistida.",
                conclusion_value=conclusion_value,
                priority=priority,
                active=True,
                legal_basis_codes=[],
                explanation="Explicación suficiente para persistir la regla.",
                conditions=[
                    RuleConditionCreate(
                        role=ConditionRole.PREREQUISITE,
                        predicate_key="premisa_base",
                        expected_value=AssertionValue.TRUE,
                    )
                ],
            )
        )

    report = reasoning_service.run(
        case_id=case_record.id,
        issue_id=issue.id,
    )
    recovered = reasoning_service.get_run_report(report.run.id)

    assert recovered.run.engine_version == "3.2.0"
    assert recovered.run.summary["defeated_rule_count"] == 1
    assert any(
        trace.outcome is TraceOutcome.DEFEATED_PRIORITY
        for trace in recovered.traces
    )
    markdown = reasoning_service.export_run_markdown(report.run.id)
    assert "Derrotada por menor prioridad" in markdown
    assert "## Resolución de conflictos" in markdown



def test_non_convergent_cycle_is_suspended_conservatively() -> None:
    rules = [
        rule(
            "R-001",
            prerequisites=[("premisa_base", AssertionValue.TRUE)],
            conclusion_key="resultado_intermedio",
            conclusion_value=AssertionValue.TRUE,
            priority=100,
        ),
        rule(
            "R-002",
            prerequisites=[("activador_ciclo", AssertionValue.TRUE)],
            conclusion_key="resultado_intermedio",
            conclusion_value=AssertionValue.FALSE,
            priority=200,
        ),
        rule(
            "R-003",
            prerequisites=[("resultado_intermedio", AssertionValue.TRUE)],
            conclusion_key="activador_ciclo",
            conclusion_value=AssertionValue.TRUE,
            priority=100,
        ),
    ]

    result = ReasoningEngine().evaluate(
        [assertion("A-001", "premisa_base", AssertionValue.TRUE)],
        rules,
    )

    assert result.conclusions == []
    assert result.summary["non_convergent_rule_count"] >= 1
    assert any(
        trace["outcome"] == TraceOutcome.NON_CONVERGENT.value
        for trace in result.traces
    )
