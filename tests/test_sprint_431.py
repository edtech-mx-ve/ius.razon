from __future__ import annotations

from ius_razon.domain.llm_models import ContextCategory, ContextItem
from ius_razon.security.llm_guardrails import (
    anonymize_context_items,
    anonymize_text,
)


def test_anonymization_does_not_consume_following_word_prefix() -> None:
    mapping = {"Compradora A": "PARTE-001"}

    result = anonymize_text(
        "La parte compradora afirma y la compradora acredita el pago.",
        mapping,
    )

    assert result == (
        "La parte compradora afirma y la compradora acredita el pago."
    )


def test_anonymization_preserves_space_after_complete_alias() -> None:
    result = anonymize_text(
        "Compradora A afirma que realizó el pago.",
        {"Compradora A": "PARTE-001"},
    )

    assert result == "PARTE-001 afirma que realizó el pago."


def test_anonymization_matches_only_complete_words() -> None:
    result = anonymize_text(
        "Ana compareció; la analista revisó una banana.",
        {"Ana": "PARTE-001"},
    )

    assert result == "PARTE-001 compareció; la analista revisó una banana."


def test_anonymization_is_case_insensitive_and_preserves_punctuation() -> None:
    result = anonymize_text(
        "COMPRADORA A, pagó; Compradora A. solicitó la entrega.",
        {"Compradora A": "PARTE-001"},
    )

    assert result == "PARTE-001, pagó; PARTE-001. solicitó la entrega."


def test_anonymization_is_idempotent_with_generic_aliases() -> None:
    mapping = {
        "Compradora A": "PARTE-001",
        "Parte": "PARTE-002",
    }

    first = anonymize_text("Compradora A afirma.", mapping)
    second = anonymize_text(first, mapping)

    assert first == "PARTE-001 afirma."
    assert second == first


def test_anonymization_deduplicates_alias_case_variants() -> None:
    item = ContextItem(
        code="H-001",
        category=ContextCategory.FACT,
        title="Compradora A",
        content="compradora a pagó.",
    )

    anonymized, mapping = anonymize_context_items(
        [item],
        ["Compradora A", "compradora a"],
    )

    assert mapping == {"Compradora A": "PARTE-001"}
    assert anonymized[0].title == "PARTE-001"
    assert anonymized[0].content == "PARTE-001 pagó."
