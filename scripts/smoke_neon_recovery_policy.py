from __future__ import annotations

import sys
from pathlib import Path

from ius_razon.persistence.mutation_backup import NeonPitrMutationBackup
from ius_razon.persistence.postgres_runtime import load_postgres_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        settings = load_postgres_settings(PROJECT_ROOT)
        policy = NeonPitrMutationBackup(
            settings.database_url,
            restore_window_hours=6,
        )
        policy.before_mutation()
    except Exception as exc:
        print(
            f"Smoke de recuperación Neon falló: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        "Neon PITR recovery policy: OK | "
        "wal_marker=OK | configured_window_hours=6 | "
        "credentials=not-logged"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
