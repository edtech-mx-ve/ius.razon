from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

OLLAMA_CHAT_ENDPOINT = "http://127.0.0.1:11434/api/chat"
_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}
_TRUE_VALUES = {"1", "true", "yes", "on", "sí", "si"}
_FALSE_VALUES = {"0", "false", "no", "off", ""}
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:+-]{0,159}$")


class OllamaProviderConfigurationError(ValueError):
    """Configuración inválida del proveedor Ollama local."""


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().casefold()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise OllamaProviderConfigurationError(
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
        raise OllamaProviderConfigurationError(
            f"{key} debe ser un entero."
        ) from exc
    if not minimum <= parsed <= maximum:
        raise OllamaProviderConfigurationError(
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
        raise OllamaProviderConfigurationError(
            f"{key} debe ser numérico."
        ) from exc
    if not minimum <= parsed <= maximum:
        raise OllamaProviderConfigurationError(
            f"{key} debe estar entre {minimum} y {maximum}."
        )
    return parsed


def _normalize_local_endpoint(value: str) -> str:
    endpoint = value.strip().rstrip("/")
    parsed = urlparse(endpoint)
    if parsed.scheme != "http":
        raise OllamaProviderConfigurationError(
            "Ollama debe usar HTTP local; HTTPS y otros esquemas no están permitidos."
        )
    if parsed.hostname not in _ALLOWED_HOSTS:
        raise OllamaProviderConfigurationError(
            "Ollama solo puede conectarse a localhost, 127.0.0.1 o ::1."
        )
    if parsed.username is not None or parsed.password is not None:
        raise OllamaProviderConfigurationError(
            "El endpoint local no admite credenciales incrustadas."
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise OllamaProviderConfigurationError(
            "El puerto del endpoint de Ollama es inválido."
        ) from exc
    if port != 11434:
        raise OllamaProviderConfigurationError(
            "Ollama debe usar exclusivamente el puerto local 11434."
        )
    if parsed.path != "/api/chat" or parsed.params or parsed.query or parsed.fragment:
        raise OllamaProviderConfigurationError(
            "El endpoint de Ollama debe terminar exactamente en /api/chat."
        )
    return endpoint


@dataclass(frozen=True, repr=False)
class OllamaProviderSettings:
    """Configuración local, gratuita y sin secretos para Ollama."""

    enabled: bool = True
    model: str = "qwen3:1.7b"
    endpoint: str = OLLAMA_CHAT_ENDPOINT
    timeout_seconds: int = 120
    max_input_tokens: int = 3072
    max_output_tokens: int = 512
    context_window: int = 4096
    temperature: float = 0.0
    max_retries: int = 0

    def __repr__(self) -> str:
        return (
            "OllamaProviderSettings("
            f"enabled={self.enabled!r}, "
            f"model={self.model!r}, "
            f"endpoint={self.endpoint!r}, "
            f"timeout_seconds={self.timeout_seconds!r}, "
            f"max_input_tokens={self.max_input_tokens!r}, "
            f"max_output_tokens={self.max_output_tokens!r}, "
            f"context_window={self.context_window!r}, "
            f"temperature={self.temperature!r}, "
            f"max_retries={self.max_retries!r})"
        )

    @property
    def configured(self) -> bool:
        """Indica si la integración local está habilitada y validada."""

        return self.enabled and bool(self.model.strip())

    def validate(self) -> None:
        """Valida modelo, endpoint y límites estrictamente locales."""

        _normalize_local_endpoint(self.endpoint)
        if not _MODEL_PATTERN.fullmatch(self.model):
            raise OllamaProviderConfigurationError(
                "IUS_RAZON_OLLAMA_MODEL contiene caracteres no permitidos."
            )
        if self.max_retries != 0:
            raise OllamaProviderConfigurationError(
                "La integración local inicial exige cero reintentos."
            )
        if self.max_input_tokens + self.max_output_tokens > self.context_window:
            raise OllamaProviderConfigurationError(
                "La suma de entrada y salida no puede superar la ventana de contexto."
            )

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> OllamaProviderSettings:
        """Construye la configuración desde variables de entorno no secretas."""

        values = dict(os.environ if environ is None else environ)
        settings = cls(
            enabled=_parse_bool(
                values.get("IUS_RAZON_OLLAMA_ENABLED"),
                default=True,
            ),
            model=values.get(
                "IUS_RAZON_OLLAMA_MODEL",
                "qwen3:1.7b",
            ).strip(),
            endpoint=values.get(
                "IUS_RAZON_OLLAMA_ENDPOINT",
                OLLAMA_CHAT_ENDPOINT,
            ).strip(),
            timeout_seconds=_parse_int(
                values,
                "IUS_RAZON_OLLAMA_TIMEOUT_SECONDS",
                default=120,
                minimum=5,
                maximum=300,
            ),
            max_input_tokens=_parse_int(
                values,
                "IUS_RAZON_OLLAMA_MAX_INPUT_TOKENS",
                default=3072,
                minimum=256,
                maximum=32768,
            ),
            max_output_tokens=_parse_int(
                values,
                "IUS_RAZON_OLLAMA_MAX_OUTPUT_TOKENS",
                default=512,
                minimum=64,
                maximum=4096,
            ),
            context_window=_parse_int(
                values,
                "IUS_RAZON_OLLAMA_CONTEXT_WINDOW",
                default=4096,
                minimum=512,
                maximum=32768,
            ),
            temperature=_parse_float(
                values,
                "IUS_RAZON_OLLAMA_TEMPERATURE",
                default=0.0,
                minimum=0.0,
                maximum=1.0,
            ),
            max_retries=_parse_int(
                values,
                "IUS_RAZON_OLLAMA_MAX_RETRIES",
                default=0,
                minimum=0,
                maximum=0,
            ),
        )
        settings.validate()
        return settings

    def safe_summary(self) -> dict[str, object]:
        """Devuelve información visible sin secretos ni contenido jurídico."""

        return {
            "enabled": self.enabled,
            "configured": self.configured,
            "provider_name": "Ollama local gratuito",
            "model": self.model,
            "endpoint": self.endpoint,
            "network_scope": "Solo equipo local",
            "api_key_required": False,
            "cost_per_request_usd": 0.0,
            "think": False,
            "stream": False,
            "timeout_seconds": self.timeout_seconds,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "context_window": self.context_window,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "fallback_required": True,
        }
