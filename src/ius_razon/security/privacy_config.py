from __future__ import annotations

import os
from dataclasses import dataclass


class PrivacyConfigurationError(ValueError):
    """Indica que la configuración de privacidad contiene valores inválidos."""


def _parse_bool(raw_value: str, *, variable_name: str) -> bool:
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on", "sí", "si"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise PrivacyConfigurationError(
        f"{variable_name} debe ser un booleano válido."
    )


@dataclass(frozen=True, slots=True)
class PrivacySettings:
    """Configura controles de privacidad para uso local y demostraciones públicas."""

    public_demo: bool = False
    uploads_enabled: bool = True
    display_storage_paths: bool = True
    require_clean_scan_for_export: bool = False
    max_findings: int = 200

    @classmethod
    def from_env(cls) -> PrivacySettings:
        """Construye la configuración sin exponer rutas ni contenidos sensibles."""

        public_demo = _parse_bool(
            os.getenv("IUS_RAZON_PUBLIC_DEMO", "false"),
            variable_name="IUS_RAZON_PUBLIC_DEMO",
        )
        requested_uploads = _parse_bool(
            os.getenv("IUS_RAZON_UPLOADS_ENABLED", "true"),
            variable_name="IUS_RAZON_UPLOADS_ENABLED",
        )
        requested_paths = _parse_bool(
            os.getenv("IUS_RAZON_DISPLAY_STORAGE_PATHS", "true"),
            variable_name="IUS_RAZON_DISPLAY_STORAGE_PATHS",
        )
        requested_scan_gate = _parse_bool(
            os.getenv(
                "IUS_RAZON_REQUIRE_CLEAN_PRIVACY_SCAN_FOR_EXPORT",
                "true" if public_demo else "false",
            ),
            variable_name=(
                "IUS_RAZON_REQUIRE_CLEAN_PRIVACY_SCAN_FOR_EXPORT"
            ),
        )
        raw_max_findings = os.getenv(
            "IUS_RAZON_PRIVACY_MAX_FINDINGS",
            "200",
        )
        try:
            max_findings = int(raw_max_findings)
        except ValueError as exc:
            raise PrivacyConfigurationError(
                "IUS_RAZON_PRIVACY_MAX_FINDINGS debe ser un entero."
            ) from exc
        if not 1 <= max_findings <= 1000:
            raise PrivacyConfigurationError(
                "IUS_RAZON_PRIVACY_MAX_FINDINGS debe estar entre 1 y 1000."
            )

        return cls(
            public_demo=public_demo,
            uploads_enabled=requested_uploads and not public_demo,
            display_storage_paths=requested_paths and not public_demo,
            require_clean_scan_for_export=(
                requested_scan_gate or public_demo
            ),
            max_findings=max_findings,
        )

    def safe_summary(self) -> dict[str, bool | int | str]:
        """Devuelve un resumen apto para interfaz y logs técnicos."""

        return {
            "mode": "Demostración pública" if self.public_demo else "Local",
            "public_demo": self.public_demo,
            "uploads_enabled": self.uploads_enabled,
            "display_storage_paths": self.display_storage_paths,
            "require_clean_scan_for_export": (
                self.require_clean_scan_for_export
            ),
            "max_findings": self.max_findings,
        }
