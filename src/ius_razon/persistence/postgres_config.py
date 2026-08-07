from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class PostgresSettings:
    """Configuración validada para Neon PostgreSQL."""

    database_url: str
    direct_database_url: str

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> PostgresSettings:
        """Carga las dos conexiones sin imprimir credenciales."""

        source = environ if environ is not None else os.environ
        database_url = source.get("DATABASE_URL", "").strip()
        direct_database_url = source.get("DIRECT_DATABASE_URL", "").strip()
        settings = cls(
            database_url=database_url,
            direct_database_url=direct_database_url,
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Comprueba esquema, host y modalidad de conexión."""

        self._validate_url(
            self.database_url,
            variable_name="DATABASE_URL",
            expect_pooler=True,
        )
        self._validate_url(
            self.direct_database_url,
            variable_name="DIRECT_DATABASE_URL",
            expect_pooler=False,
        )

    @property
    def database_name(self) -> str:
        """Devuelve el nombre de base sin exponer otras partes de la URL."""

        return urlsplit(self.direct_database_url).path.lstrip("/")

    @property
    def pooled_host(self) -> str:
        """Devuelve únicamente el host agrupado."""

        return urlsplit(self.database_url).hostname or ""

    @property
    def direct_host(self) -> str:
        """Devuelve únicamente el host directo."""

        return urlsplit(self.direct_database_url).hostname or ""

    @staticmethod
    def _validate_url(
        value: str,
        *,
        variable_name: str,
        expect_pooler: bool,
    ) -> None:
        if not value:
            raise ValueError(f"{variable_name} no está configurada.")

        parsed = urlsplit(value)
        if parsed.scheme not in {"postgresql", "postgres"}:
            raise ValueError(
                f"{variable_name} debe comenzar con postgresql:// o postgres://."
            )
        if not parsed.hostname:
            raise ValueError(f"{variable_name} no contiene un host.")
        if parsed.username is None or parsed.password is None:
            raise ValueError(f"{variable_name} no contiene credenciales.")
        if not parsed.path or parsed.path == "/":
            raise ValueError(f"{variable_name} no contiene una base de datos.")

        pooled = "-pooler" in parsed.hostname
        if expect_pooler and not pooled:
            raise ValueError(
                "DATABASE_URL debe utilizar el host agrupado con -pooler."
            )
        if not expect_pooler and pooled:
            raise ValueError(
                "DIRECT_DATABASE_URL debe utilizar el host directo."
            )