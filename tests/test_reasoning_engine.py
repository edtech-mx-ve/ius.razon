from __future__ import annotations

from datetime import UTC, datetime

from ius_razon.domain.reasoning_models import (
    AssertionValue,
    ConclusionStatus,
    ConditionRole,
    ReasoningAssertionRecord,
    ReasoningRuleRecord,
    RuleConditionCreate,
    RuleKind,
    TraceOutcome,
)
from ius_razon.services.reasoning_engine import ReasoningEngine

NOW = datetime.now(UTC)


def assertion(
    code: str,
    key: str,
    value: AssertionValue,
    *,
    support: list[str] | None = None,
) -> ReasoningAssertionRecord:
    return ReasoningAssertionRecord(
        id=code,
        case_id="case-1",
        issue_id="issue-1",
        code=code,
        predicate_key=key,
        statement=f"Premisa {key}",
        value=value,
        basis="Base de prueba suficientemente detallada.",
        support_codes=support or [],
        created_at=NOW,
        updated_at=NOW,
    )


def rule(
    code: str,
    *,
    kind: RuleKind,
    prerequisites: list[tuple[str, AssertionValue]],
    conclusion_key: str,
    conclusion_value: AssertionValue = AssertionValue.TRUE,
    exceptions: list[tuple[str, AssertionValue]] | None = None,
    priority: int = 100,
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
        conclusion_statement=f"Conclusión {conclusion_key}",
        conclusion_value=conclusion_value,
        priority=priority,
        active=True,
        legal_basis_codes=["N-001"],
        explanation="Explicación de prueba suficientemente detallada.",
        conditions=conditions,
        created_at=NOW,
        updated_at=NOW,
    )


def test_strict_rule_derives_traceable_conclusion() -> None:
    result = ReasoningEngine().evaluate(
        [
            assertion("A-001", "obligacion_exigible", AssertionValue.TRUE, support=["N-001"]),
            assertion("A-002", "entrega_realizada", AssertionValue.FALSE, support=["H-002"]),
        ],
        [
            rule(
                "R-001",
                kind=RuleKind.STRICT,
                prerequisites=[
                    ("obligacion_exigible", AssertionValue.TRUE),
                    ("entrega_realizada", AssertionValue.FALSE),
                ],
                conclusion_key="incumplimiento_entrega",
            )
        ],
    )

    assert len(result.conclusions) == 1
    conclusion = result.conclusions[0]
    assert conclusion["status"] == ConclusionStatus.STRICT.value
    assert conclusion["supporting_assertion_codes"] == ["A-001", "A-002"]
    assert result.traces[0]["outcome"] == TraceOutcome.FIRED_STRICT.value


def test_default_rule_is_blocked_by_exception() -> None:
    result = ReasoningEngine().evaluate(
        [
            assertion("A-001", "plazo_vencido", AssertionValue.TRUE),
            assertion("A-002", "prorroga_acordada", AssertionValue.TRUE),
        ],
        [
            rule(
                "R-001",
                kind=RuleKind.DEFAULT,
                prerequisites=[("plazo_vencido", AssertionValue.TRUE)],
                exceptions=[("prorroga_acordada", AssertionValue.TRUE)],
                conclusion_key="incumplimiento_entrega",
            )
        ],
    )

    assert result.conclusions == []
    assert result.traces[0]["outcome"] == TraceOutcome.BLOCKED_EXCEPTION.value


def test_opposite_strict_conclusions_with_equal_rank_are_suspended() -> None:
    result = ReasoningEngine().evaluate(
        [assertion("A-001", "contrato_valido", AssertionValue.TRUE)],
        [
            rule(
                "R-001",
                kind=RuleKind.STRICT,
                prerequisites=[("contrato_valido", AssertionValue.TRUE)],
                conclusion_key="obligacion_exigible",
                conclusion_value=AssertionValue.TRUE,
            ),
            rule(
                "R-002",
                kind=RuleKind.STRICT,
                prerequisites=[("contrato_valido", AssertionValue.TRUE)],
                conclusion_key="obligacion_exigible",
                conclusion_value=AssertionValue.FALSE,
            ),
        ],
    )

    assert result.conclusions == []
    assert all(
        item["outcome"] == TraceOutcome.TIED_CONFLICT.value
        for item in result.traces
    )
    assert result.summary["unresolved_conflict_count"] == 1


def test_strict_rule_based_on_default_result_remains_provisional() -> None:
    result = ReasoningEngine().evaluate(
        [assertion("A-001", "plazo_vencido", AssertionValue.TRUE)],
        [
            rule(
                "R-001",
                kind=RuleKind.DEFAULT,
                prerequisites=[("plazo_vencido", AssertionValue.TRUE)],
                conclusion_key="mora_presunta",
            ),
            rule(
                "R-002",
                kind=RuleKind.STRICT,
                prerequisites=[("mora_presunta", AssertionValue.TRUE)],
                conclusion_key="incumplimiento_provisional",
            ),
        ],
    )

    statuses = {
        item["predicate_key"]: item["status"]
        for item in result.conclusions
    }
    assert statuses["mora_presunta"] == ConclusionStatus.PROVISIONAL.value
    assert statuses["incumplimiento_provisional"] == ConclusionStatus.PROVISIONAL.value


def test_missing_premise_is_reported_without_conclusion() -> None:
    result = ReasoningEngine().evaluate(
        [assertion("A-001", "pago_acreditado", AssertionValue.TRUE)],
        [
            rule(
                "R-001",
                kind=RuleKind.STRICT,
                prerequisites=[
                    ("pago_acreditado", AssertionValue.TRUE),
                    ("plazo_vencido", AssertionValue.TRUE),
                ],
                conclusion_key="incumplimiento_entrega",
            )
        ],
    )

    assert result.conclusions == []
    assert result.traces[0]["outcome"] == TraceOutcome.MISSING_PREMISES.value
    assert result.traces[0]["detail"]["missing"] == ["plazo_vencido"]
