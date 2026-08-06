from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel

from ius_razon.security.privacy_config import PrivacySettings
from ius_razon.security.privacy_scanner import (
    PrivacyReport,
    build_privacy_report,
    export_allowed,
)

LOGGER = logging.getLogger(__name__)


class PrivacyCaseSource(Protocol):
    """Interfaz mínima requerida para construir el inventario de privacidad."""

    def get_case_summary(self, case_id: str) -> object: ...
    def list_parties(self, case_id: str) -> Sequence[BaseModel]: ...
    def list_facts(self, case_id: str) -> Sequence[BaseModel]: ...
    def list_evidence(self, case_id: str) -> Sequence[BaseModel]: ...
    def list_legal_issues(self, case_id: str) -> Sequence[BaseModel]: ...
    def list_norms(self, case_id: str) -> Sequence[BaseModel]: ...
    def list_jurisprudence(self, case_id: str) -> Sequence[BaseModel]: ...
    def list_doctrine(self, case_id: str) -> Sequence[BaseModel]: ...


class PrivacyService:
    """Orquesta inventario, análisis y política de exportación."""

    def __init__(
        self,
        *,
        case_source: PrivacyCaseSource,
        settings: PrivacySettings,
    ) -> None:
        self._case_source = case_source
        self._settings = settings

    @property
    def settings(self) -> PrivacySettings:
        return self._settings

    def scan_case(self, case_id: str) -> PrivacyReport:
        """Analiza un expediente sin registrar sus contenidos."""

        records = self._collect_records(case_id)
        report = build_privacy_report(
            case_id=case_id,
            records=records,
            max_findings=self._settings.max_findings,
        )
        LOGGER.info(
            "Análisis de privacidad completado. case_id=%s "
            "entities=%s fields=%s findings=%s demo_safe=%s",
            case_id,
            report.scanned_entities,
            report.scanned_fields,
            len(report.findings),
            report.is_demo_safe,
        )
        return report

    def can_export(self, case_id: str) -> tuple[bool, PrivacyReport]:
        """Evalúa el gate de exportación y devuelve su evidencia."""

        report = self.scan_case(case_id)
        allowed = export_allowed(
            report,
            public_demo=self._settings.public_demo,
            require_clean_scan=(
                self._settings.require_clean_scan_for_export
            ),
        )
        return allowed, report

    def export_report_json(self, report: PrivacyReport) -> str:
        """Exporta solo metadatos de hallazgos, nunca valores sensibles."""

        return json.dumps(
            report.to_public_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    def _collect_records(
        self,
        case_id: str,
    ) -> list[tuple[str, str, BaseModel]]:
        summary = self._case_source.get_case_summary(case_id)
        case_record = getattr(summary, "case", None)
        if not isinstance(case_record, BaseModel):
            raise TypeError(
                "La fuente de expedientes no devolvió un caso válido."
            )

        records: list[tuple[str, str, BaseModel]] = [
            ("Expediente", "CASO", case_record),
        ]
        records.extend(
            self._typed_records(
                "Parte",
                self._case_source.list_parties(case_id),
            )
        )
        records.extend(
            self._typed_records(
                "Hecho",
                self._case_source.list_facts(case_id),
            )
        )
        records.extend(
            self._typed_records(
                "Prueba",
                self._case_source.list_evidence(case_id),
            )
        )
        records.extend(
            self._typed_records(
                "Problema jurídico",
                self._case_source.list_legal_issues(case_id),
            )
        )
        records.extend(
            self._typed_records(
                "Norma",
                self._case_source.list_norms(case_id),
            )
        )
        records.extend(
            self._typed_records(
                "Jurisprudencia",
                self._case_source.list_jurisprudence(case_id),
            )
        )
        records.extend(
            self._typed_records(
                "Doctrina",
                self._case_source.list_doctrine(case_id),
            )
        )
        return records

    @staticmethod
    def _typed_records(
        entity_type: str,
        records: Sequence[BaseModel],
    ) -> list[tuple[str, str, BaseModel]]:
        result: list[tuple[str, str, BaseModel]] = []
        for record in records:
            code = getattr(record, "code", None)
            entity_id = getattr(record, "id", None)
            label = (
                str(code)
                if code
                else str(entity_id)[:8]
                if entity_id
                else entity_type
            )
            result.append((entity_type, label, record))
        return result
