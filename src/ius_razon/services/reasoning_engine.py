from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from ius_razon.domain.reasoning_models import (
    AssertionValue,
    ConclusionStatus,
    ConditionRole,
    ReasoningAssertionRecord,
    ReasoningRuleRecord,
    RuleKind,
    SupportLevel,
    TraceOutcome,
)


class ConclusionPayload(TypedDict):
    predicate_key: str
    statement: str
    value: str
    status: str
    support_level: str
    rule_codes: list[str]
    supporting_assertion_codes: list[str]
    source_codes: list[str]


class TracePayload(TypedDict):
    rule_id: str
    rule_code: str
    outcome: str
    detail: dict[str, object]


@dataclass(frozen=True)
class EngineResult:
    conclusions: list[ConclusionPayload]
    traces: list[TracePayload]
    summary: dict[str, int | str | bool]


@dataclass(frozen=True)
class _Claim:
    predicate_key: str
    value: AssertionValue
    statement: str
    origin_code: str
    origin_rule_id: str | None
    provisional: bool
    assertion_codes: tuple[str, ...]
    source_codes: tuple[str, ...]


@dataclass(frozen=True)
class _Evaluation:
    outcome: TraceOutcome
    detail: dict[str, object]
    supporting_claims: tuple[_Claim, ...]


@dataclass(frozen=True)
class _Resolution:
    accepted_rule_ids: frozenset[str]
    overrides: dict[str, _Evaluation]
    conflict_keys: frozenset[str]
    unresolved_keys: frozenset[str]


class ReasoningEngine:
    """Motor determinista y no monotónico de encadenamiento hacia adelante.

    Sprint 3.2 resuelve reglas rivales mediante una política explícita y
    reproducible: mayor prioridad numérica, luego regla estricta sobre
    provisional y, por último, mayor especificidad estructural. La
    especificidad es el número de prerrequisitos distintos. Un empate exacto
    suspende las conclusiones opuestas para revisión humana.

    Las conclusiones se reconstruyen desde cero en cada iteración. Por ello,
    cuando una regla pierde frente a una rival, también se retiran las
    conclusiones que dependían exclusivamente de ella.
    """

    VERSION = "3.2.0"
    MAX_ITERATIONS = 50

    def evaluate(
        self,
        assertions: list[ReasoningAssertionRecord],
        rules: list[ReasoningRuleRecord],
    ) -> EngineResult:
        active_rules = sorted(
            (rule for rule in rules if rule.active),
            key=lambda item: (-item.priority, item.code),
        )
        base_claims = self._initial_claims(assertions)
        claims = list(base_claims)
        accepted_previous: frozenset[str] = frozenset()
        state_history: list[frozenset[str]] = []
        ever_accepted: set[str] = set()
        derived_values_seen: set[tuple[str, AssertionValue]] = set()
        final_evaluations: dict[str, _Evaluation] = {}
        final_resolution = _Resolution(
            accepted_rule_ids=frozenset(),
            overrides={},
            conflict_keys=frozenset(),
            unresolved_keys=frozenset(),
        )
        non_convergent_rules: set[str] = set()

        for _ in range(self.MAX_ITERATIONS):
            evaluations = {
                rule.id: self._evaluate_rule(rule, claims)
                for rule in active_rules
            }
            resolution = self._resolve_candidates(
                active_rules,
                evaluations,
                base_claims,
            )
            accepted = resolution.accepted_rule_ids
            ever_accepted.update(accepted)

            next_claims = self._claims_for_accepted(
                base_claims,
                active_rules,
                evaluations,
                accepted,
            )
            derived_values_seen.update(
                (claim.predicate_key, claim.value)
                for claim in next_claims
                if claim.origin_rule_id is not None
            )

            final_evaluations = evaluations
            final_resolution = resolution
            if accepted == accepted_previous and self._claim_signature(
                next_claims
            ) == self._claim_signature(claims):
                claims = next_claims
                break

            if accepted in state_history:
                first_index = state_history.index(accepted)
                cycle_states = [*state_history[first_index:], accepted]
                stable: set[str] = set(cycle_states[0])
                cycle_union: set[str] = set()
                for state in cycle_states:
                    stable.intersection_update(state)
                    cycle_union.update(state)
                unstable = cycle_union - stable
                non_convergent_rules.update(unstable)
                stable_ids = self._prune_unsupported_rules(
                    base_claims,
                    active_rules,
                    evaluations,
                    frozenset(stable),
                )
                claims = self._claims_for_accepted(
                    base_claims,
                    active_rules,
                    evaluations,
                    stable_ids,
                )
                final_resolution = _Resolution(
                    accepted_rule_ids=stable_ids,
                    overrides=resolution.overrides,
                    conflict_keys=resolution.conflict_keys,
                    unresolved_keys=resolution.unresolved_keys,
                )
                break

            state_history.append(accepted)
            accepted_previous = accepted
            claims = next_claims
        else:
            non_convergent_rules.update(final_resolution.accepted_rule_ids)

        final_evaluations = {
            rule.id: self._evaluate_rule(rule, claims)
            for rule in active_rules
        }
        final_resolution = self._resolve_candidates(
            active_rules,
            final_evaluations,
            base_claims,
            forced_exclusions=non_convergent_rules,
        )
        final_claims = self._claims_for_accepted(
            base_claims,
            active_rules,
            final_evaluations,
            final_resolution.accepted_rule_ids,
        )

        traces = self._build_traces(
            active_rules,
            final_evaluations,
            final_resolution,
            ever_accepted=ever_accepted,
            derived_values_seen=derived_values_seen,
            final_claims=final_claims,
            non_convergent_rules=non_convergent_rules,
        )
        conclusions = self._build_conclusions(final_claims)
        contradictory_keys = self._contradictory_keys(final_claims)
        defeated_outcomes = {
            TraceOutcome.DEFEATED_PRIORITY.value,
            TraceOutcome.DEFEATED_KIND.value,
            TraceOutcome.DEFEATED_SPECIFICITY.value,
        }
        defeated_count = sum(
            1 for trace in traces if trace["outcome"] in defeated_outcomes
        )
        tied_count = sum(
            1
            for trace in traces
            if trace["outcome"] == TraceOutcome.TIED_CONFLICT.value
        )
        withdrawn_count = sum(
            1
            for trace in traces
            if trace["outcome"] == TraceOutcome.WITHDRAWN_DEPENDENCY.value
        )
        non_convergent_count = sum(
            1
            for trace in traces
            if trace["outcome"] == TraceOutcome.NON_CONVERGENT.value
        )
        summary: dict[str, int | str | bool] = {
            "assertion_count": len(assertions),
            "active_rule_count": len(active_rules),
            "fired_rule_count": len(final_resolution.accepted_rule_ids),
            "conclusion_count": len(conclusions),
            "contradiction_count": len(contradictory_keys),
            "conflict_count": len(final_resolution.conflict_keys),
            "unresolved_conflict_count": len(final_resolution.unresolved_keys),
            "defeated_rule_count": defeated_count,
            "tied_rule_count": tied_count,
            "withdrawn_rule_count": withdrawn_count,
            "non_convergent_rule_count": non_convergent_count,
            "has_contradictions": bool(contradictory_keys),
            "has_unresolved_conflicts": bool(final_resolution.unresolved_keys),
            "engine_version": self.VERSION,
            "defeat_policy": "priority>kind>specificity",
        }
        return EngineResult(
            conclusions=conclusions,
            traces=traces,
            summary=summary,
        )

    @staticmethod
    def _initial_claims(
        assertions: list[ReasoningAssertionRecord],
    ) -> list[_Claim]:
        claims: list[_Claim] = []
        for assertion in assertions:
            if assertion.value is AssertionValue.UNKNOWN:
                continue
            claims.append(
                _Claim(
                    predicate_key=assertion.predicate_key,
                    value=assertion.value,
                    statement=assertion.statement,
                    origin_code=assertion.code,
                    origin_rule_id=None,
                    provisional=False,
                    assertion_codes=(assertion.code,),
                    source_codes=tuple(assertion.support_codes),
                )
            )
        return claims

    def _evaluate_rule(
        self,
        rule: ReasoningRuleRecord,
        claims: list[_Claim],
    ) -> _Evaluation:
        prerequisites = [
            condition
            for condition in rule.conditions
            if condition.role is ConditionRole.PREREQUISITE
        ]
        exceptions = [
            condition
            for condition in rule.conditions
            if condition.role is ConditionRole.EXCEPTION
        ]

        missing: list[str] = []
        mismatched: list[str] = []
        contradictory: list[str] = []
        supporting: list[_Claim] = []

        for condition in prerequisites:
            values = self._values_for(claims, condition.predicate_key)
            if not values:
                missing.append(condition.predicate_key)
                continue
            if len(values) > 1:
                contradictory.append(condition.predicate_key)
                continue
            if condition.expected_value not in values:
                mismatched.append(condition.predicate_key)
                continue
            supporting.extend(
                self._matching_claims(
                    claims,
                    condition.predicate_key,
                    condition.expected_value,
                )
            )

        base_detail = self._base_rule_detail(
            rule,
            missing=missing,
            mismatched=mismatched,
            contradictory=contradictory,
        )
        if contradictory:
            return _Evaluation(
                TraceOutcome.CONTRADICTORY_PREMISES,
                base_detail,
                tuple(supporting),
            )
        if missing:
            return _Evaluation(
                TraceOutcome.MISSING_PREMISES,
                base_detail,
                tuple(supporting),
            )
        if mismatched:
            return _Evaluation(
                TraceOutcome.NOT_SATISFIED,
                base_detail,
                tuple(supporting),
            )

        if rule.kind is RuleKind.DEFAULT:
            active_exceptions: list[str] = []
            for condition in exceptions:
                values = self._values_for(claims, condition.predicate_key)
                if condition.expected_value in values:
                    active_exceptions.append(condition.predicate_key)
            if active_exceptions:
                base_detail["active_exceptions"] = active_exceptions
                return _Evaluation(
                    TraceOutcome.BLOCKED_EXCEPTION,
                    base_detail,
                    tuple(supporting),
                )

        outcome = (
            TraceOutcome.FIRED_STRICT
            if rule.kind is RuleKind.STRICT
            else TraceOutcome.FIRED_DEFAULT
        )
        base_detail["supporting_claims"] = sorted(
            {claim.origin_code for claim in supporting}
        )
        return _Evaluation(outcome, base_detail, tuple(supporting))

    def _resolve_candidates(
        self,
        rules: list[ReasoningRuleRecord],
        evaluations: dict[str, _Evaluation],
        base_claims: list[_Claim],
        *,
        forced_exclusions: set[str] | None = None,
    ) -> _Resolution:
        exclusions: set[str] = forced_exclusions or set()
        candidates: dict[str, ReasoningRuleRecord] = {}
        overrides: dict[str, _Evaluation] = {}

        for rule in rules:
            evaluation = evaluations[rule.id]
            if rule.id in exclusions:
                continue
            if evaluation.outcome not in {
                TraceOutcome.FIRED_STRICT,
                TraceOutcome.FIRED_DEFAULT,
            }:
                continue
            if rule.kind is RuleKind.DEFAULT:
                opposite = self._opposite(rule.conclusion_value)
                contrary_assertions = [
                    claim.origin_code
                    for claim in self._matching_claims(
                        base_claims,
                        rule.conclusion_key,
                        opposite,
                    )
                ]
                if contrary_assertions:
                    detail = dict(evaluation.detail)
                    detail["contrary_claims"] = sorted(contrary_assertions)
                    detail["defeat_reason"] = "premisa confirmada contraria"
                    overrides[rule.id] = _Evaluation(
                        TraceOutcome.BLOCKED_CONTRARY,
                        detail,
                        evaluation.supporting_claims,
                    )
                    continue
            candidates[rule.id] = rule

        grouped: dict[str, list[ReasoningRuleRecord]] = {}
        for rule in candidates.values():
            grouped.setdefault(rule.conclusion_key, []).append(rule)

        accepted: set[str] = set()
        conflict_keys: set[str] = set()
        unresolved_keys: set[str] = set()

        for key, group in grouped.items():
            true_rules = [
                rule
                for rule in group
                if rule.conclusion_value is AssertionValue.TRUE
            ]
            false_rules = [
                rule
                for rule in group
                if rule.conclusion_value is AssertionValue.FALSE
            ]
            if not true_rules or not false_rules:
                accepted.update(rule.id for rule in group)
                continue

            conflict_keys.add(key)
            best_true = max(true_rules, key=self._rank)
            best_false = max(false_rules, key=self._rank)
            true_rank = self._rank(best_true)
            false_rank = self._rank(best_false)

            if true_rank == false_rank:
                unresolved_keys.add(key)
                rival_codes = sorted(
                    {best_true.code, best_false.code}
                )
                for rule in group:
                    detail = dict(evaluations[rule.id].detail)
                    detail.update(
                        {
                            "conflict_key": key,
                            "rival_rules": rival_codes,
                            "rank": self._rank_detail(rule),
                            "resolution": "empate exacto; conclusión suspendida",
                        }
                    )
                    overrides[rule.id] = _Evaluation(
                        TraceOutcome.TIED_CONFLICT,
                        detail,
                        evaluations[rule.id].supporting_claims,
                    )
                continue

            winning_value = (
                AssertionValue.TRUE if true_rank > false_rank else AssertionValue.FALSE
            )
            winner = best_true if winning_value is AssertionValue.TRUE else best_false
            winner_rank = self._rank(winner)
            accepted.update(
                rule.id
                for rule in group
                if rule.conclusion_value is winning_value
            )
            for loser in group:
                if loser.conclusion_value is winning_value:
                    continue
                outcome, reason = self._defeat_outcome(
                    winner_rank,
                    self._rank(loser),
                )
                detail = dict(evaluations[loser.id].detail)
                detail.update(
                    {
                        "conflict_key": key,
                        "defeated_by": winner.code,
                        "winner_rank": self._rank_detail(winner),
                        "loser_rank": self._rank_detail(loser),
                        "defeat_reason": reason,
                    }
                )
                overrides[loser.id] = _Evaluation(
                    outcome,
                    detail,
                    evaluations[loser.id].supporting_claims,
                )

        return _Resolution(
            accepted_rule_ids=frozenset(accepted),
            overrides=overrides,
            conflict_keys=frozenset(conflict_keys),
            unresolved_keys=frozenset(unresolved_keys),
        )

    @staticmethod
    def _rank(rule: ReasoningRuleRecord) -> tuple[int, int, int]:
        kind_strength = 1 if rule.kind is RuleKind.STRICT else 0
        return (
            rule.priority,
            kind_strength,
            rule.specificity_score,
        )

    @staticmethod
    def _rank_detail(rule: ReasoningRuleRecord) -> dict[str, object]:
        return {
            "priority": rule.priority,
            "kind": rule.kind.value,
            "kind_strength": 1 if rule.kind is RuleKind.STRICT else 0,
            "specificity": rule.specificity_score,
            "rule_code": rule.code,
        }

    @staticmethod
    def _defeat_outcome(
        winner_rank: tuple[int, int, int],
        loser_rank: tuple[int, int, int],
    ) -> tuple[TraceOutcome, str]:
        if winner_rank[0] != loser_rank[0]:
            return TraceOutcome.DEFEATED_PRIORITY, "mayor prioridad numérica"
        if winner_rank[1] != loser_rank[1]:
            return TraceOutcome.DEFEATED_KIND, "regla estricta sobre provisional"
        return (
            TraceOutcome.DEFEATED_SPECIFICITY,
            "mayor número de prerrequisitos distintos",
        )

    def _claims_for_accepted(
        self,
        base_claims: list[_Claim],
        rules: list[ReasoningRuleRecord],
        evaluations: dict[str, _Evaluation],
        accepted_rule_ids: frozenset[str],
    ) -> list[_Claim]:
        claims = list(base_claims)
        by_id = {rule.id: rule for rule in rules}
        for rule_id in sorted(
            accepted_rule_ids,
            key=lambda item: (-by_id[item].priority, by_id[item].code),
        ):
            evaluation = evaluations[rule_id]
            if evaluation.outcome not in {
                TraceOutcome.FIRED_STRICT,
                TraceOutcome.FIRED_DEFAULT,
            }:
                continue
            claim = self._claim_from_rule(
                by_id[rule_id],
                evaluation.supporting_claims,
            )
            if not self._claim_exists(claims, claim):
                claims.append(claim)
        return claims

    def _prune_unsupported_rules(
        self,
        base_claims: list[_Claim],
        rules: list[ReasoningRuleRecord],
        evaluations: dict[str, _Evaluation],
        candidate_ids: frozenset[str],
    ) -> frozenset[str]:
        accepted = set(candidate_ids)
        by_id = {rule.id: rule for rule in rules}
        while True:
            claims = self._claims_for_accepted(
                base_claims,
                rules,
                evaluations,
                frozenset(accepted),
            )
            supported = {
                rule_id
                for rule_id in accepted
                if self._evaluate_rule(by_id[rule_id], claims).outcome
                in {TraceOutcome.FIRED_STRICT, TraceOutcome.FIRED_DEFAULT}
            }
            if supported == accepted:
                return frozenset(supported)
            accepted = supported

    def _build_traces(
        self,
        rules: list[ReasoningRuleRecord],
        evaluations: dict[str, _Evaluation],
        resolution: _Resolution,
        *,
        ever_accepted: set[str],
        derived_values_seen: set[tuple[str, AssertionValue]],
        final_claims: list[_Claim],
        non_convergent_rules: set[str],
    ) -> list[TracePayload]:
        traces: list[TracePayload] = []
        accepted = resolution.accepted_rule_ids

        for rule in rules:
            evaluation = evaluations[rule.id]
            if rule.id in non_convergent_rules:
                detail = dict(evaluation.detail)
                detail["resolution"] = (
                    "La regla participó en una oscilación y fue suspendida "
                    "conservadoramente."
                )
                evaluation = _Evaluation(
                    TraceOutcome.NON_CONVERGENT,
                    detail,
                    evaluation.supporting_claims,
                )
            elif rule.id in resolution.overrides:
                evaluation = resolution.overrides[rule.id]
            elif rule.id in accepted:
                pass
            elif rule.id in ever_accepted:
                withdrawn_dependencies = self._withdrawn_dependencies(
                    rule,
                    final_claims,
                    derived_values_seen,
                )
                if withdrawn_dependencies:
                    detail = dict(evaluation.detail)
                    detail["withdrawn_dependencies"] = withdrawn_dependencies
                    detail["resolution"] = (
                        "La conclusión de esta regla se retiró porque perdió "
                        "soporte derivado tras la derrota de una regla anterior."
                    )
                    evaluation = _Evaluation(
                        TraceOutcome.WITHDRAWN_DEPENDENCY,
                        detail,
                        evaluation.supporting_claims,
                    )

            traces.append(
                TracePayload(
                    rule_id=rule.id,
                    rule_code=rule.code,
                    outcome=evaluation.outcome.value,
                    detail=evaluation.detail,
                )
            )
        return traces

    @staticmethod
    def _withdrawn_dependencies(
        rule: ReasoningRuleRecord,
        final_claims: list[_Claim],
        derived_values_seen: set[tuple[str, AssertionValue]],
    ) -> list[str]:
        withdrawn: list[str] = []
        for condition in rule.conditions:
            if condition.role is not ConditionRole.PREREQUISITE:
                continue
            pair = (condition.predicate_key, condition.expected_value)
            if pair not in derived_values_seen:
                continue
            currently_available = any(
                claim.predicate_key == condition.predicate_key
                and claim.value is condition.expected_value
                for claim in final_claims
            )
            if not currently_available:
                withdrawn.append(
                    f"{condition.predicate_key}={condition.expected_value.value}"
                )
        return sorted(set(withdrawn))

    @staticmethod
    def _base_rule_detail(
        rule: ReasoningRuleRecord,
        *,
        missing: list[str],
        mismatched: list[str],
        contradictory: list[str],
    ) -> dict[str, object]:
        return {
            "rule_name": rule.name,
            "kind": rule.kind.value,
            "priority": rule.priority,
            "specificity": rule.specificity_score,
            "conclusion": rule.conclusion_key,
            "conclusion_value": rule.conclusion_value.value,
            "missing": missing,
            "mismatched": mismatched,
            "contradictory": contradictory,
            "ranking_policy": "priority>kind>specificity",
        }

    @staticmethod
    def _claim_from_rule(
        rule: ReasoningRuleRecord,
        supporting_claims: tuple[_Claim, ...],
    ) -> _Claim:
        assertion_codes = sorted(
            {
                code
                for claim in supporting_claims
                for code in claim.assertion_codes
            }
        )
        source_codes = sorted(
            {
                *rule.legal_basis_codes,
                *[
                    code
                    for claim in supporting_claims
                    for code in claim.source_codes
                ],
            }
        )
        provisional = rule.kind is RuleKind.DEFAULT or any(
            claim.provisional for claim in supporting_claims
        )
        return _Claim(
            predicate_key=rule.conclusion_key,
            value=rule.conclusion_value,
            statement=rule.conclusion_statement,
            origin_code=rule.code,
            origin_rule_id=rule.id,
            provisional=provisional,
            assertion_codes=tuple(assertion_codes),
            source_codes=tuple(source_codes),
        )

    def _build_conclusions(
        self,
        claims: list[_Claim],
    ) -> list[ConclusionPayload]:
        derived = [claim for claim in claims if claim.origin_rule_id is not None]
        groups: dict[tuple[str, AssertionValue], list[_Claim]] = {}
        for claim in derived:
            groups.setdefault((claim.predicate_key, claim.value), []).append(claim)

        contradictory_keys = self._contradictory_keys(claims)
        conclusions: list[ConclusionPayload] = []
        for (predicate_key, value), group in sorted(
            groups.items(),
            key=lambda item: (item[0][0], item[0][1].value),
        ):
            rule_codes = sorted({claim.origin_code for claim in group})
            assertion_codes = sorted(
                {
                    code
                    for claim in group
                    for code in claim.assertion_codes
                }
            )
            source_codes = sorted(
                {
                    code
                    for claim in group
                    for code in claim.source_codes
                }
            )
            provisional = all(claim.provisional for claim in group)
            if predicate_key in contradictory_keys:
                status = ConclusionStatus.CONTRADICTED
            elif provisional:
                status = ConclusionStatus.PROVISIONAL
            else:
                status = ConclusionStatus.STRICT
            support_level = self._support_level(
                status=status,
                assertion_count=len(assertion_codes),
                source_count=len(source_codes),
            )
            conclusions.append(
                ConclusionPayload(
                    predicate_key=predicate_key,
                    statement=group[0].statement,
                    value=value.value,
                    status=status.value,
                    support_level=support_level.value,
                    rule_codes=rule_codes,
                    supporting_assertion_codes=assertion_codes,
                    source_codes=source_codes,
                )
            )
        return conclusions

    @staticmethod
    def _support_level(
        *,
        status: ConclusionStatus,
        assertion_count: int,
        source_count: int,
    ) -> SupportLevel:
        if status is ConclusionStatus.CONTRADICTED:
            return SupportLevel.INSUFFICIENT
        if status is ConclusionStatus.STRICT:
            if assertion_count >= 2 and source_count >= 1:
                return SupportLevel.HIGH
            return SupportLevel.MEDIUM
        if assertion_count >= 2 and source_count >= 1:
            return SupportLevel.MEDIUM
        return SupportLevel.LOW

    @staticmethod
    def _values_for(
        claims: list[_Claim],
        predicate_key: str,
    ) -> set[AssertionValue]:
        return {
            claim.value
            for claim in claims
            if claim.predicate_key == predicate_key
        }

    @staticmethod
    def _matching_claims(
        claims: list[_Claim],
        predicate_key: str,
        value: AssertionValue,
    ) -> list[_Claim]:
        return [
            claim
            for claim in claims
            if claim.predicate_key == predicate_key and claim.value is value
        ]

    @staticmethod
    def _claim_exists(claims: list[_Claim], candidate: _Claim) -> bool:
        return any(
            claim.origin_code == candidate.origin_code
            and claim.predicate_key == candidate.predicate_key
            and claim.value is candidate.value
            for claim in claims
        )

    @staticmethod
    def _claim_signature(
        claims: list[_Claim],
    ) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            sorted(
                (
                    claim.predicate_key,
                    claim.value.value,
                    claim.origin_code,
                )
                for claim in claims
            )
        )

    @classmethod
    def _contradictory_keys(cls, claims: list[_Claim]) -> set[str]:
        keys = {claim.predicate_key for claim in claims}
        return {
            key
            for key in keys
            if cls._values_for(claims, key)
            == {AssertionValue.TRUE, AssertionValue.FALSE}
        }

    @staticmethod
    def _opposite(value: AssertionValue) -> AssertionValue:
        if value is AssertionValue.TRUE:
            return AssertionValue.FALSE
        return AssertionValue.TRUE
