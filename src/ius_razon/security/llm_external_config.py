from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse


class ExternalProviderConfigurationError(ValueError):
    """Configuración externa inválida o incompleta."""


_TRUE_VALUES = {"1", "true", "yes", "on", "sí", "si"}
_FALSE_VALUES = {"0", "false", "no", "off", ""}


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().casefold()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ExternalProviderConfigurationError(
        f"Valor booleano inválido: {value!r}."
    )


def _parse_int(
    values: Mapping[str, str],
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = values.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ExternalProviderConfigurationError(
            f"{key} debe ser un entero."
        ) from exc
    if not minimum <= parsed <= maximum:
        raise ExternalProviderConfigurationError(
            f"{key} debe estar entre {minimum} y {maximum}."
        )
    return parsed


def _parse_float(
    values: Mapping[str, str],
    key: str,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw = values.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        parsed = float(raw)
    except ValueError as exc:
        raise ExternalProviderConfigurationError(
            f"{key} debe ser numérico."
        ) from exc
    if not minimum <= parsed <= maximum:
        raise ExternalProviderConfigurationError(
            f"{key} debe estar entre {minimum} y {maximum}."
        )
    return parsed


@dataclass(frozen=True, repr=False)
class ExternalProviderSettings:
    """Configuración segura para un endpoint JSON externo."""

    enabled: bool = False
    endpoint: str = ""
    api_key: str = ""
    model: str = "external-model"
    timeout_seconds: int = 30
    max_retries: int = 1
    max_input_tokens: int = 16000
    max_output_tokens: int = 2000
    max_cost_usd: float = 0.10
    input_cost_per_million_usd: float = 0.0
    output_cost_per_million_usd: float = 0.0

    def __repr__(self) -> str:
        return (
            "ExternalProviderSettings("
            f"enabled={self.enabled!r}, "
            f"endpoint={self.endpoint!r}, "
            "api_key=<redacted>, "
            f"model={self.model!r}, "
            f"timeout_seconds={self.timeout_seconds!r}, "
            f"max_retries={self.max_retries!r}, "
            f"max_input_tokens={self.max_input_tokens!r}, "
            f"max_output_tokens={self.max_output_tokens!r}, "
            f"max_cost_usd={self.max_cost_usd!r})"
        )

    @property
    def configured(self) -> bool:
        """Indica si la llamada externa está lista para habilitarse."""

        return bool(
            self.enabled
            and self.endpoint
            and self.api_key
            and self.model
        )

    @property
    def api_key_configured(self) -> bool:
        """Expone solo la presencia del secreto."""

        return bool(self.api_key)

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> ExternalProviderSettings:
        """Lee variables de entorno sin registrar ni devolver secretos en texto."""

        values = os.environ if environ is None else environ
        enabled = _parse_bool(
            values.get("IUS_RAZON_LLM_EXTERNAL_ENABLED"),
            default=False,
        )
        endpoint = values.get("IUS_RAZON_LLM_ENDPOINT", "").strip()
        api_key = values.get("IUS_RAZON_LLM_API_KEY", "").strip()
        model = values.get("IUS_RAZON_LLM_MODEL", "external-model").strip()
        settings = cls(
            enabled=enabled,
            endpoint=endpoint,
            api_key=api_key,
            model=model,
            timeout_seconds=_parse_int(
                values,
                "IUS_RAZON_LLM_TIMEOUT_SECONDS",
                default=30,
                minimum=5,
                maximum=180,
            ),
            max_retries=_parse_int(
                values,
                "IUS_RAZON_LLM_MAX_RETRIES",
                default=1,
                minimum=0,
                maximum=3,
            ),
            max_input_tokens=_parse_int(
                values,
                "IUS_RAZON_LLM_MAX_INPUT_TOKENS",
                default=16000,
                minimum=256,
                maximum=200000,
            ),
            max_output_tokens=_parse_int(
                values,
                "IUS_RAZON_LLM_MAX_OUTPUT_TOKENS",
                default=2000,
                minimum=64,
                maximum=32000,
            ),
            max_cost_usd=_parse_float(
                values,
                "IUS_RAZON_LLM_MAX_COST_USD",
                default=0.10,
                minimum=0.0,
                maximum=100.0,
            ),
            input_cost_per_million_usd=_parse_float(
                values,
                "IUS_RAZON_LLM_INPUT_COST_PER_1M_USD",
                default=0.0,
                minimum=0.0,
                maximum=1000.0,
            ),
            output_cost_per_million_usd=_parse_float(
                values,
                "IUS_RAZON_LLM_OUTPUT_COST_PER_1M_USD",
                default=0.0,
                minimum=0.0,
                maximum=1000.0,
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Valida únicamente requisitos exigibles para el modo externo."""

        if not self.enabled:
            return
        if not self.endpoint:
            raise ExternalProviderConfigurationError(
                "IUS_RAZON_LLM_ENDPOINT es obligatorio al habilitar el proveedor."
            )
        parsed = urlparse(self.endpoint)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ExternalProviderConfigurationError(
                "El endpoint externo debe ser una URL HTTPS absoluta."
            )
        if parsed.username or parsed.password:
            raise ExternalProviderConfigurationError(
                "El endpoint no puede incluir credenciales."
            )
        if not self.api_key:
            raise ExternalProviderConfigurationError(
                "IUS_RAZON_LLM_API_KEY es obligatoria al habilitar el proveedor."
            )
        if not self.model:
            raise ExternalProviderConfigurationError(
                "IUS_RAZON_LLM_MODEL no puede estar vacío."
            )

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estima costo según tarifas configuradas por el usuario."""

        cost = (
            input_tokens * self.input_cost_per_million_usd
            + output_tokens * self.output_cost_per_million_usd
        ) / 1_000_000
        return round(cost, 8)

    def safe_summary(self) -> dict[str, object]:
        """Devuelve estado visible sin secreto."""

        return {
            "enabled": self.enabled,
            "configured": self.configured,
            "endpoint_host": urlparse(self.endpoint).hostname or "",
            "model": self.model,
            "api_key_configured": self.api_key_configured,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_cost_usd": self.max_cost_usd,
        }
