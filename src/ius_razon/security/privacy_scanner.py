from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class PrivacySeverity(StrEnum):
    """Gravedad de un posible dato sensible."""

    CRITICAL = "Crítica"
    HIGH = "Alta"
    MEDIUM = "Media"
    LOW = "Baja"


class PrivacyCategory(StrEnum):
    """Categorías detectables sin conservar el valor encontrado."""

    SECRET = "Secreto o token"
    EMAIL = "Correo electrónico"
    CURP = "CURP"
    RFC = "RFC"
    CLABE = "CLABE"
    PAYMENT_CARD = "Tarjeta de pago"
    PHONE = "Teléfono"
    LOCAL_PATH = "Ruta local"
    POSSIBLE_REAL_NAME = "Posible nombre real"


@dataclass(frozen=True, slots=True)
class PrivacyLocation:
    """Ubicación trazable de un campo analizado."""

    entity_type: str
    entity_code: str
    field_name: str


@dataclass(frozen=True, slots=True)
class PrivacyFinding:
    """Hallazgo seguro: no contiene el dato sensible en texto claro."""

    category: PrivacyCategory
    severity: PrivacySeverity
    location: PrivacyLocation
    fingerprint: str
    message: str

    def to_public_dict(self) -> dict[str, str]:
        """Serializa el hallazgo sin incluir el valor detectado."""

        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "entity_type": self.location.entity_type,
            "entity_code": self.location.entity_code,
            "field_name": self.location.field_name,
            "fingerprint": self.fingerprint,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class PrivacyReport:
    """Resultado inmutable de un análisis de privacidad."""

    case_id: str
    generated_at: datetime
    scanned_entities: int
    scanned_fields: int
    findings: tuple[PrivacyFinding, ...]
    truncated: bool = False

    @property
    def critical_count(self) -> int:
        return self._count(PrivacySeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        return self._count(PrivacySeverity.HIGH)

    @property
    def medium_count(self) -> int:
        return self._count(PrivacySeverity.MEDIUM)

    @property
    def low_count(self) -> int:
        return self._count(PrivacySeverity.LOW)

    @property
    def is_demo_safe(self) -> bool:
        """Exige ausencia de hallazgos críticos, altos y medios."""

        return (
            self.critical_count == 0
            and self.high_count == 0
            and self.medium_count == 0
            and not self.truncated
        )

    def to_public_dict(self) -> dict[str, Any]:
        """Construye un reporte exportable sin datos originales."""

        return {
            "case_id": self.case_id,
            "generated_at": self.generated_at.isoformat(),
            "scanned_entities": self.scanned_entities,
            "scanned_fields": self.scanned_fields,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "is_demo_safe": self.is_demo_safe,
            "truncated": self.truncated,
            "findings": [
                finding.to_public_dict() for finding in self.findings
            ],
        }

    def _count(self, severity: PrivacySeverity) -> int:
        return sum(
            finding.severity == severity for finding in self.findings
        )


@dataclass(frozen=True, slots=True)
class TextField:
    """Campo textual normalizado para el pipeline de análisis."""

    location: PrivacyLocation
    value: str


@dataclass(frozen=True, slots=True)
class _PatternRule:
    category: PrivacyCategory
    severity: PrivacySeverity
    pattern: re.Pattern[str]
    message: str


_PATTERN_RULES: tuple[_PatternRule, ...] = (
    _PatternRule(
        PrivacyCategory.SECRET,
        PrivacySeverity.CRITICAL,
        re.compile(
            r"(?i)\b(?:sk|ghp|xox[baprs])-[A-Za-z0-9_-]{16,}\b"
        ),
        "Se detectó un patrón compatible con una credencial.",
    ),
    _PatternRule(
        PrivacyCategory.EMAIL,
        PrivacySeverity.HIGH,
        re.compile(
            r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
        ),
        "Se detectó un correo electrónico.",
    ),
    _PatternRule(
        PrivacyCategory.CURP,
        PrivacySeverity.HIGH,
        re.compile(
            r"\b[A-Z][AEIOU][A-Z]{2}\d{2}"
            r"(?:0[1-9]|1[0-2])"
            r"(?:0[1-9]|[12]\d|3[01])"
            r"[HM][A-Z]{5}[A-Z0-9]\d\b"
        ),
        "Se detectó un patrón compatible con CURP.",
    ),
    _PatternRule(
        PrivacyCategory.RFC,
        PrivacySeverity.HIGH,
        re.compile(
            r"\b(?:[A-ZÑ&]{3}|[A-ZÑ&]{4})\d{6}[A-Z0-9]{3}\b"
        ),
        "Se detectó un patrón compatible con RFC.",
    ),
    _PatternRule(
        PrivacyCategory.CLABE,
        PrivacySeverity.HIGH,
        re.compile(r"(?<!\d)(?:\d[\s-]?){18}(?!\d)"),
        "Se detectó un patrón compatible con CLABE.",
    ),
    _PatternRule(
        PrivacyCategory.PHONE,
        PrivacySeverity.HIGH,
        re.compile(
            r"(?<!\w)(?:\+52[\s.-]?)"
            r"(?:\(?\d{2,3}\)?[\s.-]?){2,3}\d{4}(?!\d)"
        ),
        "Se detectó un número telefónico.",
    ),
    _PatternRule(
        PrivacyCategory.LOCAL_PATH,
        PrivacySeverity.MEDIUM,
        re.compile(
            r"(?:\b[A-Za-z]:\\[^\r\n]+|"
            r"/(?:home|Users|mnt|var|tmp)/[^\s\r\n]+)"
        ),
        "Se detectó una ruta local que puede revelar el entorno.",
    ),
)

_GENERIC_ALIAS_TERMS = {
    "actor",
    "actora",
    "demandado",
    "demandada",
    "parte",
    "empresa",
    "persona",
    "cliente",
    "proveedor",
    "contratante",
    "contratista",
    "demo",
    "anónimo",
    "anonimo",
}


def _fingerprint(value: str) -> str:
    normalized = value.strip().casefold().encode()
    return hashlib.sha256(normalized).hexdigest()[:16]


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _luhn_valid(value: str) -> bool:
    digits = _digits(value)
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    parity = len(digits) % 2
    for index, character in enumerate(digits):
        number = int(character)
        if index % 2 == parity:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0


def _looks_like_real_name(value: str) -> bool:
    normalized = " ".join(value.split())
    words = normalized.split()
    if not 2 <= len(words) <= 5:
        return False
    lowered = {word.casefold().strip(".,") for word in words}
    if lowered & _GENERIC_ALIAS_TERMS:
        return False
    if any(character.isdigit() for character in normalized):
        return False
    capitalized = sum(
        bool(word) and word[0].isupper()
        for word in words
        if word[0].isalpha()
    )
    return capitalized >= 2


def flatten_text_fields(
    record: BaseModel,
    *,
    entity_type: str,
    entity_code: str,
) -> list[TextField]:
    """Extrae campos textuales sin modificar el modelo original."""

    payload = record.model_dump(mode="python")
    excluded = {
        "id",
        "case_id",
        "created_at",
        "updated_at",
        "file_sha256",
        "stored_file_name",
    }
    fields: list[TextField] = []
    for field_name, value in payload.items():
        if field_name in excluded or not isinstance(value, str):
            continue
        normalized = value.strip()
        if not normalized:
            continue
        fields.append(
            TextField(
                location=PrivacyLocation(
                    entity_type=entity_type,
                    entity_code=entity_code,
                    field_name=field_name,
                ),
                value=normalized,
            )
        )
    return fields


def scan_text_field(field: TextField) -> list[PrivacyFinding]:
    """Analiza un campo con reglas deterministas y sin conservar coincidencias."""

    findings: list[PrivacyFinding] = []
    seen: set[tuple[PrivacyCategory, str]] = set()

    for rule in _PATTERN_RULES:
        for match in rule.pattern.finditer(field.value):
            matched = match.group(0)
            if (
                rule.category is PrivacyCategory.CLABE
                and len(_digits(matched)) != 18
            ):
                continue
            key = (rule.category, _fingerprint(matched))
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                PrivacyFinding(
                    category=rule.category,
                    severity=rule.severity,
                    location=field.location,
                    fingerprint=key[1],
                    message=rule.message,
                )
            )

    for match in re.finditer(r"(?<!\d)(?:\d[\s-]?){13,19}(?!\d)", field.value):
        candidate = match.group(0)
        if not _luhn_valid(candidate):
            continue
        fingerprint = _fingerprint(candidate)
        key = (PrivacyCategory.PAYMENT_CARD, fingerprint)
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            PrivacyFinding(
                category=PrivacyCategory.PAYMENT_CARD,
                severity=PrivacySeverity.HIGH,
                location=field.location,
                fingerprint=fingerprint,
                message="Se detectó un patrón compatible con tarjeta de pago.",
            )
        )

    if (
        field.location.entity_type == "Parte"
        and field.location.field_name == "name_alias"
        and _looks_like_real_name(field.value)
    ):
        findings.append(
            PrivacyFinding(
                category=PrivacyCategory.POSSIBLE_REAL_NAME,
                severity=PrivacySeverity.HIGH,
                location=field.location,
                fingerprint=_fingerprint(field.value),
                message=(
                    "El alias parece contener un nombre completo; "
                    "revíselo antes de una demostración pública."
                ),
            )
        )

    return findings


def build_privacy_report(
    *,
    case_id: str,
    records: list[tuple[str, str, BaseModel]],
    max_findings: int,
) -> PrivacyReport:
    """Ejecuta el pipeline puro de extracción, detección y reporte."""

    if not case_id.strip():
        raise ValueError("case_id no puede estar vacío.")
    if max_findings < 1:
        raise ValueError("max_findings debe ser mayor que cero.")

    fields: list[TextField] = []
    for entity_type, entity_code, record in records:
        fields.extend(
            flatten_text_fields(
                record,
                entity_type=entity_type,
                entity_code=entity_code,
            )
        )

    findings: list[PrivacyFinding] = []
    truncated = False
    for field in fields:
        for finding in scan_text_field(field):
            if len(findings) >= max_findings:
                truncated = True
                break
            findings.append(finding)
        if truncated:
            break

    ordered = tuple(
        sorted(
            findings,
            key=lambda item: (
                -_severity_rank(item.severity),
                item.location.entity_type,
                item.location.entity_code,
                item.location.field_name,
                item.category.value,
            ),
        )
    )
    return PrivacyReport(
        case_id=case_id,
        generated_at=datetime.now(UTC),
        scanned_entities=len(records),
        scanned_fields=len(fields),
        findings=ordered,
        truncated=truncated,
    )


def export_allowed(
    report: PrivacyReport,
    *,
    public_demo: bool,
    require_clean_scan: bool,
) -> bool:
    """Decide de forma pura si una exportación puede habilitarse."""

    return (
        not public_demo
        and not require_clean_scan
    ) or report.is_demo_safe


def _severity_rank(severity: PrivacySeverity) -> int:
    return {
        PrivacySeverity.CRITICAL: 4,
        PrivacySeverity.HIGH: 3,
        PrivacySeverity.MEDIUM: 2,
        PrivacySeverity.LOW: 1,
    }[severity]
