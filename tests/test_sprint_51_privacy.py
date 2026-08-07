from __future__ import annotations

import json
from datetime import date

import pytest
from pydantic import BaseModel

from ius_razon.domain.enums import (
    CaseStatus,
    ConfidentialityLevel,
    PartyRole,
    PartyType,
)
from ius_razon.domain.models import CaseCreate, PartyCreate
from ius_razon.security.privacy_config import (
    PrivacyConfigurationError,
    PrivacySettings,
)
from ius_razon.security.privacy_scanner import (
    PrivacyCategory,
    PrivacyLocation,
    TextField,
    build_privacy_report,
    export_allowed,
    scan_text_field,
)
from ius_razon.services.case_service import CaseService
from ius_razon.services.privacy_service import PrivacyService


class SampleRecord(BaseModel):
    id: str = "record-1"
    code: str = "X-001"
    description: str


def _field(value: str, *, field_name: str = "description") -> TextField:
    return TextField(
        location=PrivacyLocation(
            entity_type="Prueba",
            entity_code="P-001",
            field_name=field_name,
        ),
        value=value,
    )


@pytest.mark.parametrize(
    ("value", "category"),
    [
        ("Contacto: persona@example.com", PrivacyCategory.EMAIL),
        (
            "CURP: GODE561231HDFRRN09",
            PrivacyCategory.CURP,
        ),
        ("RFC: GODE561231GR8", PrivacyCategory.RFC),
        (
            "CLABE 032180000118359719",
            PrivacyCategory.CLABE,
        ),
        (
            "Teléfono +52 55 6574 1576",
            PrivacyCategory.PHONE,
        ),
        (
            r"Ruta D:\Casos\expediente\archivo.pdf",
            PrivacyCategory.LOCAL_PATH,
        ),
        (
            "Clave " + "sk-" + "proyecto_super_secreta_123456789",
            PrivacyCategory.SECRET,
        ),
        (
            "Tarjeta 4111 1111 1111 1111",
            PrivacyCategory.PAYMENT_CARD,
        ),
    ],
)
def test_scan_text_field_detects_sensitive_patterns(
    value: str,
    category: PrivacyCategory,
) -> None:
    findings = scan_text_field(_field(value))
    assert category in {finding.category for finding in findings}
    assert all(value not in finding.message for finding in findings)


def test_scan_text_field_flags_possible_real_party_name() -> None:
    findings = scan_text_field(
        TextField(
            location=PrivacyLocation(
                entity_type="Parte",
                entity_code="PARTE-1",
                field_name="name_alias",
            ),
            value="Juan Carlos Pérez",
        )
    )
    assert PrivacyCategory.POSSIBLE_REAL_NAME in {
        finding.category for finding in findings
    }


def test_scan_text_field_accepts_generic_demo_alias() -> None:
    findings = scan_text_field(
        TextField(
            location=PrivacyLocation(
                entity_type="Parte",
                entity_code="PARTE-1",
                field_name="name_alias",
            ),
            value="Parte demandada A",
        )
    )
    assert PrivacyCategory.POSSIBLE_REAL_NAME not in {
        finding.category for finding in findings
    }


def test_privacy_report_never_exports_detected_value() -> None:
    secret = "persona@example.com"
    report = build_privacy_report(
        case_id="case-1",
        records=[
            (
                "Prueba",
                "P-001",
                SampleRecord(description=f"Contacto {secret}"),
            )
        ],
        max_findings=20,
    )
    exported = json.dumps(report.to_public_dict(), ensure_ascii=False)
    assert secret not in exported
    assert report.high_count == 1
    assert not report.is_demo_safe


def test_privacy_report_truncates_safely() -> None:
    report = build_privacy_report(
        case_id="case-1",
        records=[
            (
                "Prueba",
                "P-001",
                SampleRecord(
                    description=(
                        "a@example.com b@example.com c@example.com"
                    )
                ),
            )
        ],
        max_findings=2,
    )
    assert len(report.findings) == 2
    assert report.truncated
    assert not report.is_demo_safe


def test_export_policy_is_informative_in_local_mode() -> None:
    report = build_privacy_report(
        case_id="case-1",
        records=[
            (
                "Prueba",
                "P-001",
                SampleRecord(description="persona@example.com"),
            )
        ],
        max_findings=20,
    )
    assert export_allowed(
        report,
        public_demo=False,
        require_clean_scan=False,
    )
    assert not export_allowed(
        report,
        public_demo=True,
        require_clean_scan=True,
    )


def test_public_demo_forces_secure_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IUS_RAZON_PUBLIC_DEMO", "true")
    monkeypatch.setenv("IUS_RAZON_UPLOADS_ENABLED", "true")
    monkeypatch.setenv("IUS_RAZON_DISPLAY_STORAGE_PATHS", "true")
    monkeypatch.setenv(
        "IUS_RAZON_REQUIRE_CLEAN_PRIVACY_SCAN_FOR_EXPORT",
        "false",
    )
    settings = PrivacySettings.from_env()
    assert settings.public_demo
    assert not settings.uploads_enabled
    assert not settings.display_storage_paths
    assert settings.require_clean_scan_for_export


def test_privacy_settings_reject_invalid_boolean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IUS_RAZON_PUBLIC_DEMO", "quizá")
    with pytest.raises(PrivacyConfigurationError):
        PrivacySettings.from_env()


def test_privacy_service_scans_case_without_logging_values(
    service: CaseService,
) -> None:
    case = service.create_case(
        CaseCreate(
            title="DEMO-001 Controversia contractual",
            description=(
                "Expediente sintético para validar privacidad sin datos reales."
            ),
            matter="Mercantil",
            jurisdiction="México",
            opened_on=date(2026, 1, 1),
            status=CaseStatus.OPEN,
            confidentiality=ConfidentialityLevel.INTERNAL,
        )
    )
    service.add_party(
        PartyCreate(
            case_id=case.id,
            name_alias="Parte compradora A",
            party_type=PartyType.LEGAL_ENTITY,
            legal_role=PartyRole.CLAIMANT,
        )
    )
    privacy = PrivacyService(
        case_source=service,
        settings=PrivacySettings(),
    )
    report = privacy.scan_case(case.id)
    assert report.scanned_entities == 2
    assert report.is_demo_safe
    exported = privacy.export_report_json(report)
    assert "Parte compradora A" not in exported


def test_privacy_service_blocks_real_name_in_public_demo(
    service: CaseService,
) -> None:
    case = service.create_case(
        CaseCreate(
            title="DEMO-002 Caso sintético",
            description="Descripción sintética suficientemente extensa.",
            matter="Mercantil",
            jurisdiction="México",
            status=CaseStatus.OPEN,
            confidentiality=ConfidentialityLevel.INTERNAL,
        )
    )
    service.add_party(
        PartyCreate(
            case_id=case.id,
            name_alias="María Fernanda López",
            party_type=PartyType.NATURAL_PERSON,
            legal_role=PartyRole.CLAIMANT,
        )
    )
    privacy = PrivacyService(
        case_source=service,
        settings=PrivacySettings(
            public_demo=True,
            uploads_enabled=False,
            display_storage_paths=False,
            require_clean_scan_for_export=True,
        ),
    )
    allowed, report = privacy.can_export(case.id)
    assert not allowed
    assert not report.is_demo_safe
    assert any(
        finding.category is PrivacyCategory.POSSIBLE_REAL_NAME
        for finding in report.findings
    )
