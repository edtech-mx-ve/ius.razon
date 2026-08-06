from __future__ import annotations

import hashlib
import html
import json
import re
from collections.abc import Iterable, Mapping

from ius_razon.domain.llm_models import (
    ContextItem,
    DraftEvaluation,
)

_REFERENCE_PATTERN = re.compile(r"\[([A-Z]{1,6}-\d{3})\]")
_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "intento de ignorar instrucciones",
        re.compile(
            r"\b(ignore|disregard|forget|ignora|omite)\b.{0,60}"
            r"\b(instructions?|instrucciones|reglas|prompt)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "referencia a instrucciones internas",
        re.compile(
            r"\b(system prompt|developer message|mensaje del sistema|"
            r"instrucciones internas)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "solicitud potencial de secretos",
        re.compile(
            r"\b(api[_ -]?key|token|contraseña|password|secreto|secret)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "solicitud potencial de ejecución",
        re.compile(
            r"\b(ejecuta|execute|run|borra|delete)\b.{0,50}"
            r"\b(comando|command|archivo|file|datos|database|base)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)

_NON_CLAIM_PREFIXES = (
    "advertencia:",
    "control de contexto:",
    "revisión humana:",
    "borrador simulado:",
)


def sanitize_text(value: str) -> str:
    """Normaliza texto externo sin ejecutar ni interpretar su contenido."""

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = "".join(
        character
        if character in {"\n", "\t"} or ord(character) >= 32
        else " "
        for character in normalized
    )
    return re.sub(r"[ \t]+", " ", cleaned).strip()


def detect_prompt_injection(items: Iterable[ContextItem]) -> list[str]:
    """Detecta señales heurísticas de instrucciones incrustadas en datos."""

    flags: list[str] = []
    for item in items:
        text = f"{item.title}\n{item.content}"
        for label, pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                flags.append(f"{item.code}: {label}")
    return sorted(set(flags))


def anonymize_text(
    value: str,
    mapping: Mapping[str, str],
) -> str:
    """Sustituye alias completos sin alterar palabras vecinas ni marcadores."""

    anonymized = sanitize_text(value)
    normalized_pairs = sorted(
        (
            (sanitize_text(alias), sanitize_text(replacement))
            for alias, replacement in mapping.items()
            if sanitize_text(alias) and sanitize_text(replacement)
        ),
        key=lambda pair: (-len(pair[0]), pair[0].casefold(), pair[1]),
    )
    if not normalized_pairs:
        return anonymized

    replacements: dict[str, str] = {}
    ordered_aliases: list[str] = []
    for alias, replacement in normalized_pairs:
        folded = alias.casefold()
        if folded not in replacements:
            replacements[folded] = replacement
            ordered_aliases.append(alias)

    alternatives = "|".join(re.escape(alias) for alias in ordered_aliases)
    pattern = re.compile(
        rf"(?<!\w)(?:{alternatives})(?!\w)(?!-\d{{3}}\b)",
        re.IGNORECASE,
    )

    def replace_alias(match: re.Match[str]) -> str:
        return replacements[match.group(0).casefold()]

    return pattern.sub(replace_alias, anonymized)


def anonymize_context_items(
    items: Iterable[ContextItem],
    aliases: Iterable[str],
) -> tuple[list[ContextItem], dict[str, str]]:
    """Sustituye alias completos por identificadores neutros y reproducibles."""

    candidates = sorted(
        {
            sanitized
            for alias in aliases
            if (sanitized := sanitize_text(alias))
        },
        key=lambda value: (value.casefold(), value),
    )
    aliases_by_fold: dict[str, str] = {}
    for alias in candidates:
        aliases_by_fold.setdefault(alias.casefold(), alias)

    cleaned_aliases = sorted(
        aliases_by_fold.values(),
        key=lambda value: (-len(value), value.casefold(), value),
    )
    mapping = {
        alias: f"PARTE-{index:03d}"
        for index, alias in enumerate(cleaned_aliases, start=1)
    }
    anonymized: list[ContextItem] = []
    for item in items:
        title = sanitize_text(item.title)
        content = sanitize_text(item.content)
        title = anonymize_text(title, mapping)
        content = anonymize_text(content, mapping)
        anonymized.append(
            item.model_copy(
                update={
                    "title": title,
                    "content": content,
                }
            )
        )
    return anonymized, mapping


def truncate_context_items(
    items: Iterable[ContextItem],
    max_chars: int,
) -> list[ContextItem]:
    """Limita el contexto de forma determinista sin dividir códigos."""

    if max_chars < 1000:
        raise ValueError("El límite de contexto debe ser de al menos 1000 caracteres.")

    selected: list[ContextItem] = []
    used = 0
    for item in items:
        prefix_size = len(item.code) + len(item.category.value) + len(item.title) + 16
        remaining = max_chars - used - prefix_size
        if remaining <= 0:
            break
        content = sanitize_text(item.content)
        if len(content) > remaining:
            if remaining < 80:
                break
            content = f"{content[: max(0, remaining - 1)].rstrip()}…"
        selected.append(item.model_copy(update={"content": content}))
        used += prefix_size + len(content)
        if used >= max_chars:
            break

    if not selected:
        raise ValueError("La selección no cabe en el límite de contexto.")
    return selected


def render_context(items: Iterable[ContextItem]) -> str:
    """Serializa contexto como datos delimitados y escapados."""

    parts = ["<expediente_contexto>"]
    for item in items:
        parts.extend(
            [
                (
                    f'<item code="{html.escape(item.code)}" '
                    f'category="{html.escape(item.category.value)}">'
                ),
                f"<title>{html.escape(item.title)}</title>",
                f"<content>{html.escape(item.content)}</content>",
                "</item>",
            ]
        )
    parts.append("</expediente_contexto>")
    return "\n".join(parts)


def stable_input_hash(
    request_payload: Mapping[str, object],
    items: Iterable[ContextItem],
) -> str:
    """Calcula una huella reproducible de solicitud y contexto."""

    payload = {
        "request": dict(request_payload),
        "items": [item.model_dump(mode="json") for item in items],
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def text_hash(value: str) -> str:
    """Calcula SHA-256 del texto normalizado."""

    return hashlib.sha256(sanitize_text(value).encode("utf-8")).hexdigest()


def extract_reference_codes(text: str) -> list[str]:
    """Extrae referencias internas en formato ``[COD-000]``."""

    return sorted(set(_REFERENCE_PATTERN.findall(text)))


def evaluate_draft(
    text: str,
    allowed_codes: Iterable[str],
) -> DraftEvaluation:
    """Evalúa referencias inválidas y afirmaciones sin respaldo explícito."""

    allowed = set(allowed_codes)
    references = extract_reference_codes(text)
    invalid = sorted(code for code in references if code not in allowed)

    claim_lines = [
        line.strip(" -*\t")
        for line in sanitize_text(text).splitlines()
        if _is_claim_line(line)
    ]
    supported_count = 0
    unsupported: list[str] = []
    for line in claim_lines:
        line_references = set(extract_reference_codes(line))
        if line_references & allowed:
            supported_count += 1
        else:
            unsupported.append(line[:500])

    coverage = (
        1.0
        if not claim_lines
        else round(supported_count / len(claim_lines), 4)
    )
    passed = not invalid and not unsupported and coverage == 1.0
    return DraftEvaluation(
        reference_codes=references,
        invalid_reference_codes=invalid,
        unsupported_claims=unsupported,
        citation_coverage=coverage,
        passed=passed,
    )


def _is_claim_line(raw_line: str) -> bool:
    """Determina si una línea requiere cita según una heurística conservadora."""

    line = raw_line.strip()
    if not line:
        return False
    if line.startswith("#") or line.endswith(":"):
        return False
    lowered = line.casefold().lstrip("-* ")
    if lowered.startswith(_NON_CLAIM_PREFIXES):
        return False
    words = re.findall(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b", line)
    return len(words) >= 4
