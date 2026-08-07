from __future__ import annotations

import pytest

from ius_razon.persistence.postgres_config import PostgresSettings

POOLED_URL = (
    "postgresql://ius_owner:secret@"
    "ep-example-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
)
DIRECT_URL = (
    "postgresql://ius_owner:secret@"
    "ep-example.us-east-1.aws.neon.tech/neondb?sslmode=require"
)


def test_postgres_settings_accept_neon_pooled_and_direct_urls() -> None:
    settings = PostgresSettings.from_env(
        {
            "DATABASE_URL": POOLED_URL,
            "DIRECT_DATABASE_URL": DIRECT_URL,
        }
    )

    assert settings.database_name == "neondb"
    assert "-pooler" in settings.pooled_host
    assert "-pooler" not in settings.direct_host


@pytest.mark.parametrize(
    ("database_url", "direct_database_url", "message"),
    [
        ("", DIRECT_URL, "DATABASE_URL"),
        (POOLED_URL, "", "DIRECT_DATABASE_URL"),
        (DIRECT_URL, DIRECT_URL, "agrupado"),
        (POOLED_URL, POOLED_URL, "directo"),
        (
            "sqlite:///data.db",
            DIRECT_URL,
            "postgresql://",
        ),
    ],
)
def test_postgres_settings_reject_invalid_configuration(
    database_url: str,
    direct_database_url: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        PostgresSettings.from_env(
            {
                "DATABASE_URL": database_url,
                "DIRECT_DATABASE_URL": direct_database_url,
            }
        )


def test_validation_error_does_not_expose_password() -> None:
    secret = "never-print-this-password"

    with pytest.raises(ValueError) as captured:
        PostgresSettings.from_env(
            {
                "DATABASE_URL": (
                    "postgresql://user:"
                    f"{secret}@ep-example/neondb"
                ),
                "DIRECT_DATABASE_URL": DIRECT_URL,
            }
        )

    assert secret not in str(captured.value)