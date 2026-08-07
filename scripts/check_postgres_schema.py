from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from ius_razon.persistence.postgres_runtime import load_postgres_settings
from ius_razon.persistence.postgres_schema import (
    APPLICATION_TABLES,
    METADATA_TABLE,
    SCHEMA_VERSION,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def validate_schema() -> None:
    settings = load_postgres_settings(PROJECT_ROOT)
    with psycopg.connect(
        settings.direct_database_url,
        connect_timeout=20,
    ) as connection:
        rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        ).fetchall()
        tables = {str(row[0]) for row in rows}

        missing = APPLICATION_TABLES - tables
        if missing:
            raise RuntimeError(
                "Faltan tablas: " + ", ".join(sorted(missing))
            )

        metadata_row = connection.execute(
            """
            SELECT value
            FROM ius_schema_metadata
            WHERE key = %s
            """,
            ("schema_version",),
        ).fetchone()

    if METADATA_TABLE not in tables:
        raise RuntimeError("Falta la tabla de metadatos del esquema.")
    if metadata_row is None:
        raise RuntimeError("No existe la versión del esquema.")
    if str(metadata_row[0]) != SCHEMA_VERSION:
        raise RuntimeError(
            f"Versión inesperada: {metadata_row[0]} != {SCHEMA_VERSION}"
        )


def main() -> int:
    try:
        validate_schema()
    except Exception as exc:
        print(
            f"Verificación del esquema PostgreSQL fallida: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        "Esquema Neon: OK | "
        f"tablas_aplicacion={len(APPLICATION_TABLES)} | "
        f"version={SCHEMA_VERSION}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
