from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

OLLAMA_CHAT_ENDPOINT = "http://127.0.0.1:11434/api/chat"
_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}
_TRUE_VALUES = {"1", "true", "yes", "on", "sí", "si"}
_FALSE_VALUES = {"0", "false", "no", "off", ""}
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:+-]{0,159}$")
_CLOUD_MODEL_PATTERN = re.compile(
    r"(?:^|[:/_-])cloud(?:$|[:/_-])",
    flags=re.IGNORECASE,
)


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


def _validate_model_name(value: str, *, key: str) -> str:
    model = value.strip()
    if not _MODEL_PATTERN.fullmatch(model):
        raise OllamaProviderConfigurationError(
            f"{key} contiene caracteres no permitidos."
        )
    if _CLOUD_MODEL_PATTERN.search(model):
        raise OllamaProviderConfigurationError(
            f"{key} no puede seleccionar modelos cloud."
        )
    return model


def _parse_allowed_models(
    values: Mapping[str, str],
) -> tuple[str, ...]:
    raw = values.get(
        "IUS_RAZON_OLLAMA_ALLOWED_MODELS",
        "qwen3:1.7b",
    )
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        raise OllamaProviderConfigurationError(
            "IUS_RAZON_OLLAMA_ALLOWED_MODELS debe incluir al menos un modelo."
        )
    if len(parts) > 8:
        raise OllamaProviderConfigurationError(
            "IUS_RAZON_OLLAMA_ALLOWED_MODELS admite como máximo 8 modelos."
        )
    validated = tuple(
        _validate_model_name(
            part,
            key="IUS_RAZON_OLLAMA_ALLOWED_MODELS",
        )
        for part in parts
    )
    if len(set(validated)) != len(validated):
        raise OllamaProviderConfigurationError(
            "IUS_RAZON_OLLAMA_ALLOWED_MODELS no admite duplicados."
        )
    return validated


def is_cloud_model_name(value: str) -> bool:
    """Detecta identificadores que declaran ejecución cloud."""

    return bool(_CLOUD_MODEL_PATTERN.search(value.strip()))


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


def _replace_api_path(endpoint: str, path: str) -> str:
    parsed = urlparse(endpoint)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            path,
            "",
            "",
            "",
        )
    )


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
    health_timeout_seconds: int = 5
    allowed_models: tuple[str, ...] = ("qwen3:1.7b",)

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
            f"max_retries={self.max_retries!r}, "
            f"health_timeout_seconds={self.health_timeout_seconds!r}, "
            f"allowed_models={self.allowed_models!r})"
        )

    @property
    def configured(self) -> bool:
        """Indica si la integración local está habilitada y validada."""

        return self.enabled and bool(self.model.strip())

    @property
    def version_endpoint(self) -> str:
        """Endpoint local para consultar la versión de Ollama."""

        return _replace_api_path(self.endpoint, "/api/version")

    @property
    def tags_endpoint(self) -> str:
        """Endpoint local para consultar los modelos instalados."""

        return _replace_api_path(self.endpoint, "/api/tags")

    def validate(self) -> None:
        """Valida modelo, endpoint, allowlist y límites estrictamente locales."""

        _normalize_local_endpoint(self.endpoint)
        model = _validate_model_name(
            self.model,
            key="IUS_RAZON_OLLAMA_MODEL",
        )
        allowed_models = tuple(
            _validate_model_name(
                item,
                key="IUS_RAZON_OLLAMA_ALLOWED_MODELS",
            )
            for item in self.allowed_models
        )
        if not allowed_models:
            raise OllamaProviderConfigurationError(
                "Debe existir al menos un modelo local permitido."
            )
        if len(set(allowed_models)) != len(allowed_models):
            raise OllamaProviderConfigurationError(
                "La lista de modelos permitidos no admite duplicados."
            )
        if model not in allowed_models:
            raise OllamaProviderConfigurationError(
                "El modelo configurado no pertenece a la lista local permitida."
            )
        if self.max_retries != 0:
            raise OllamaProviderConfigurationError(
                "La integración local exige cero reintentos."
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
        allowed_models = _parse_allowed_models(values)
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
            health_timeout_seconds=_parse_int(
                values,
                "IUS_RAZON_OLLAMA_HEALTH_TIMEOUT_SECONDS",
                default=5,
                minimum=1,
                maximum=15,
            ),
            allowed_models=allowed_models,
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
            "health_timeout_seconds": self.health_timeout_seconds,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "context_window": self.context_window,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "fallback_required": True,
            "allowed_models": list(self.allowed_models),
            "cloud_models_blocked": True,
        }
