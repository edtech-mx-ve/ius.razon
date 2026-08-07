from __future__ import annotations

from pathlib import Path

import pytest

from ius_razon.ui.access_control import (
    ACCESS_PASSWORD_KEY,
    AccessConfigurationError,
    load_access_settings,
    password_matches,
)


def _password() -> str:
    return "correct-" + "password-123"


def test_access_password_from_environment(tmp_path: Path) -> None:
    settings = load_access_settings(
        tmp_path,
        {ACCESS_PASSWORD_KEY: _password()},
    )
    assert settings.password == _password()


def test_access_password_from_local_secrets(tmp_path: Path) -> None:
    secrets_dir = tmp_path / ".streamlit"
    secrets_dir.mkdir()
    (secrets_dir / "secrets.toml").write_text(
        f'{ACCESS_PASSWORD_KEY} = "{_password()}"\n',
        encoding="utf-8",
    )

    settings = load_access_settings(tmp_path, {})
    assert settings.password == _password()


def test_environment_overrides_local_secret(tmp_path: Path) -> None:
    secrets_dir = tmp_path / ".streamlit"
    secrets_dir.mkdir()
    (secrets_dir / "secrets.toml").write_text(
        f'{ACCESS_PASSWORD_KEY} = "local-password-456"\n',
        encoding="utf-8",
    )

    settings = load_access_settings(
        tmp_path,
        {ACCESS_PASSWORD_KEY: _password()},
    )
    assert settings.password == _password()


def test_missing_access_password_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(AccessConfigurationError, match="no está configurado"):
        load_access_settings(tmp_path, {})


def test_short_access_password_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(AccessConfigurationError, match="al menos"):
        load_access_settings(
            tmp_path,
            {ACCESS_PASSWORD_KEY: "short"},
        )


def test_password_comparison_is_exact() -> None:
    expected = _password()
    assert password_matches(expected, expected)
    assert not password_matches("wrong-" + "password-123", expected)


def test_public_portal_has_no_persistence_dependencies() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ius_razon"
        / "ui"
        / "public_portal.py"
    ).read_text(encoding="utf-8")

    assert "ius_razon.persistence" not in source
    assert "ius_razon.services" not in source
