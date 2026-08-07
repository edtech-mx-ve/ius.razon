from __future__ import annotations

import hmac
import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ACCESS_PASSWORD_KEY = "IUS_RAZON_ACCESS_PASSWORD"
MIN_PASSWORD_LENGTH = 12


class AccessConfigurationError(ValueError):
    """Configuración inválida del acceso protegido."""


@dataclass(frozen=True, slots=True)
class AccessSettings:
    """Configuración del acceso protegido."""

    password: str

    def validate(self) -> None:
        if len(self.password) < MIN_PASSWORD_LENGTH:
            raise AccessConfigurationError(
                f"{ACCESS_PASSWORD_KEY} debe tener al menos "
                f"{MIN_PASSWORD_LENGTH} caracteres."
            )


def _local_secret_source(project_root: Path) -> dict[str, str]:
    """Lee el secreto local sin imprimir ni registrar su valor."""

    secrets_path = project_root / ".streamlit" / "secrets.toml"
    if not secrets_path.is_file():
        return {}

    try:
        payload = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise AccessConfigurationError(
            "No fue posible leer la configuración local de acceso."
        ) from exc

    value = payload.get(ACCESS_PASSWORD_KEY)
    return {ACCESS_PASSWORD_KEY: str(value)} if value is not None else {}


def load_access_settings(
    project_root: Path,
    environ: Mapping[str, str] | None = None,
) -> AccessSettings:
    """Carga la contraseña desde entorno o secrets.toml local."""

    environment = os.environ if environ is None else environ
    environment_value = environment.get(ACCESS_PASSWORD_KEY, "").strip()

    if environment_value:
        settings = AccessSettings(password=environment_value)
        settings.validate()
        return settings

    local_source = _local_secret_source(project_root)
    local_value = local_source.get(ACCESS_PASSWORD_KEY, "").strip()
    if not local_value:
        raise AccessConfigurationError(
            "El acceso protegido no está configurado."
        )

    settings = AccessSettings(password=local_value)
    settings.validate()
    return settings


def password_matches(candidate: str, expected: str) -> bool:
    """Compara contraseñas en tiempo constante."""

    return hmac.compare_digest(
        candidate.encode("utf-8"),
        expected.encode("utf-8"),
    )
