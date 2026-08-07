from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from ius_razon.persistence.postgres_config import PostgresSettings


def load_postgres_settings(project_root: Path) -> PostgresSettings:
    """Carga variables o secretos locales sin imprimir credenciales."""

    secrets_path = project_root / ".streamlit" / "secrets.toml"
    local: dict[str, str] = {}

    if secrets_path.is_file():
        payload: dict[str, Any]
        with secrets_path.open("rb") as handle:
            payload = tomllib.load(handle)

        for key in ("DATABASE_URL", "DIRECT_DATABASE_URL"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                local[key] = value.strip()

    return PostgresSettings.from_env(
        {
            "DATABASE_URL": os.getenv(
                "DATABASE_URL",
                local.get("DATABASE_URL", ""),
            ),
            "DIRECT_DATABASE_URL": os.getenv(
                "DIRECT_DATABASE_URL",
                local.get("DIRECT_DATABASE_URL", ""),
            ),
        }
    )
