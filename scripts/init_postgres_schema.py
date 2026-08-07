from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from ius_razon.persistence.postgres_runtime import load_postgres_settings
from ius_razon.persistence.postgres_schema import (
    SCHEMA_VERSION,
    schema_statements,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def initialize_schema() -> None:
    settings = load_postgres_settings(PROJECT_ROOT)
    with psycopg.connect(
        settings.direct_database_url,
        connect_timeout=20,
    ) as connection, connection.transaction():
        for statement in schema_statements(PROJECT_ROOT):
            connection.execute(statement)

        connection.execute(
            """
                INSERT INTO ius_schema_metadata (key, value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = EXCLUDED.updated_at
                """,
            (
                "schema_version",
                SCHEMA_VERSION,
                datetime.now(UTC).isoformat(),
            ),
        )


def main() -> int:
    try:
        initialize_schema()
    except Exception as exc:
        print(
            f"No fue posible inicializar PostgreSQL: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        "Esquema PostgreSQL de IUS-Razón inicializado correctamente. "
        f"versión={SCHEMA_VERSION}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
