from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"

_TRUE_VALUES = {"1", "true", "yes", "on", "sí", "si"}
_FALSE_VALUES = {"0", "false", "no", "off", ""}


class OpenAIProviderConfigurationError(ValueError):
    """Configuración inválida del adaptador específico de OpenAI."""


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().casefold()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise OpenAIProviderConfigurationError(
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
        raise OpenAIProviderConfigurationError(
            f"{key} debe ser un entero."
        ) from exc
    if not minimum <= parsed <= maximum:
        raise OpenAIProviderConfigurationError(
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
        raise OpenAIProviderConfigurationError(
            f"{key} debe ser numérico."
        ) from exc
    if not minimum <= parsed <= maximum:
        raise OpenAIProviderConfigurationError(
            f"{key} debe estar entre {minimum} y {maximum}."
        )
    return parsed


@dataclass(frozen=True, repr=False)
class OpenAIProviderSettings:
    """Configuración segura y de límites para OpenAI Responses API."""

    enabled: bool = False
    api_key: str = ""
    model: str = "gpt-5.5"
    endpoint: str = OPENAI_RESPONSES_ENDPOINT
    timeout_seconds: int = 20
    max_retries: int = 0
    max_input_tokens: int = 2048
    max_output_tokens: int = 256
    max_cost_usd: float = 0.02
    input_cost_per_million_usd: float = 0.0
    output_cost_per_million_usd: float = 0.0

    def __repr__(self) -> str:
        return (
            "OpenAIProviderSettings("
            f"enabled={self.enabled!r}, "
            "api_key=<redacted>, "
            f"model={self.model!r}, "
            f"endpoint={self.endpoint!r}, "
            f"timeout_seconds={self.timeout_seconds!r}, "
            f"max_retries={self.max_retries!r}, "
            f"max_input_tokens={self.max_input_tokens!r}, "
            f"max_output_tokens={self.max_output_tokens!r}, "
            f"max_cost_usd={self.max_cost_usd!r})"
        )

    @property
    def api_key_configured(self) -> bool:
        """Expone solamente si existe una clave."""

        return bool(self.api_key)

    @property
    def pricing_configured(self) -> bool:
        """Indica si la estimación de costo usa tarifas explícitas."""

        return (
            self.input_cost_per_million_usd > 0
            and self.output_cost_per_million_usd > 0
        )

    @property
    def configured(self) -> bool:
        """Indica si el adaptador puede habilitar una llamada real."""

        return bool(
            self.enabled
            and self.api_key
            and self.model
            and self.pricing_configured
        )

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> OpenAIProviderSettings:
        """Lee variables de entorno sin imprimir ni persistir secretos."""

        values = os.environ if environ is None else environ
        settings = cls(
            enabled=_parse_bool(
                values.get("IUS_RAZON_OPENAI_ENABLED"),
                default=False,
            ),
            api_key=values.get("OPENAI_API_KEY", "").strip(),
            model=values.get(
                "IUS_RAZON_OPENAI_MODEL",
                "gpt-5.5",
            ).strip(),
            timeout_seconds=_parse_int(
                values,
                "IUS_RAZON_OPENAI_TIMEOUT_SECONDS",
                default=20,
                minimum=5,
                maximum=60,
            ),
            max_retries=_parse_int(
                values,
                "IUS_RAZON_OPENAI_MAX_RETRIES",
                default=0,
                minimum=0,
                maximum=0,
            ),
            max_input_tokens=_parse_int(
                values,
                "IUS_RAZON_OPENAI_MAX_INPUT_TOKENS",
                default=2048,
                minimum=256,
                maximum=16000,
            ),
            max_output_tokens=_parse_int(
                values,
                "IUS_RAZON_OPENAI_MAX_OUTPUT_TOKENS",
                default=256,
                minimum=64,
                maximum=2048,
            ),
            max_cost_usd=_parse_float(
                values,
                "IUS_RAZON_OPENAI_MAX_COST_USD",
                default=0.02,
                minimum=0.000001,
                maximum=1.0,
            ),
            input_cost_per_million_usd=_parse_float(
                values,
                "IUS_RAZON_OPENAI_INPUT_COST_PER_1M_USD",
                default=0.0,
                minimum=0.0,
                maximum=1000.0,
            ),
            output_cost_per_million_usd=_parse_float(
                values,
                "IUS_RAZON_OPENAI_OUTPUT_COST_PER_1M_USD",
                default=0.0,
                minimum=0.0,
                maximum=1000.0,
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Valida requisitos solo cuando el adaptador está habilitado."""

        if self.endpoint != OPENAI_RESPONSES_ENDPOINT:
            raise OpenAIProviderConfigurationError(
                "El endpoint de OpenAI es fijo y no puede modificarse."
            )
        if not self.enabled:
            return
        if not self.api_key:
            raise OpenAIProviderConfigurationError(
                "OPENAI_API_KEY es obligatoria al habilitar OpenAI."
            )
        if not self.model:
            raise OpenAIProviderConfigurationError(
                "IUS_RAZON_OPENAI_MODEL no puede estar vacío."
            )
        if self.max_retries != 0:
            raise OpenAIProviderConfigurationError(
                "La primera integración real exige cero reintentos."
            )
        if not self.pricing_configured:
            raise OpenAIProviderConfigurationError(
                "Configura las tarifas de entrada y salida para controlar el costo."
            )

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estima costo según tarifas declaradas por el usuario."""

        cost = (
            input_tokens * self.input_cost_per_million_usd
            + output_tokens * self.output_cost_per_million_usd
        ) / 1_000_000
        return round(cost, 8)

    def safe_summary(self) -> dict[str, object]:
        """Devuelve estado visible sin clave ni contenido sensible."""

        return {
            "enabled": self.enabled,
            "configured": self.configured,
            "endpoint_host": "api.openai.com",
            "model": self.model,
            "api_key_configured": self.api_key_configured,
            "pricing_configured": self.pricing_configured,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_cost_usd": self.max_cost_usd,
        }
