from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from typing import Any

import psycopg

from ius_razon.persistence.postgres_config import PostgresSettings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"


def load_local_secrets() -> dict[str, str]:
    """Carga secretos locales cuando no existen variables de entorno."""

    if not SECRETS_PATH.is_file():
        return {}

    payload: dict[str, Any]
    with SECRETS_PATH.open("rb") as handle:
        payload = tomllib.load(handle)

    result: dict[str, str] = {}
    for key in ("DATABASE_URL", "DIRECT_DATABASE_URL"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            result[key] = value.strip()
    return result


def build_settings() -> PostgresSettings:
    """Combina entorno y secretos locales sin modificar el proceso."""

    local = load_local_secrets()
    values = {
        "DATABASE_URL": os.getenv(
            "DATABASE_URL",
            local.get("DATABASE_URL", ""),
        ),
        "DIRECT_DATABASE_URL": os.getenv(
            "DIRECT_DATABASE_URL",
            local.get("DIRECT_DATABASE_URL", ""),
        ),
    }
    return PostgresSettings.from_env(values)


def check_connection(label: str, connection_url: str) -> None:
    """Verifica una conexión y muestra solo metadatos no sensibles."""

    with psycopg.connect(connection_url, connect_timeout=15) as connection:
        row = connection.execute(
            """
            SELECT
                current_database(),
                current_user,
                current_setting('server_version')
            """
        ).fetchone()

    if row is None:
        raise RuntimeError(f"{label}: PostgreSQL no devolvió metadatos.")

    database_name, database_role, server_version = row
    print(
        f"{label}: OK | base={database_name} | "
        f"rol={database_role} | PostgreSQL={server_version}"
    )


def main() -> int:
    try:
        settings = build_settings()
        check_connection("Conexión agrupada", settings.database_url)
        check_connection("Conexión directa", settings.direct_database_url)
    except Exception as exc:
        print(
            f"Verificación PostgreSQL fallida: {exc}",
            file=sys.stderr,
        )
        return 1

    print("Neon PostgreSQL quedó conectado sin exponer credenciales.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())