from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.client import HTTPConnection, HTTPException
from typing import Protocol
from urllib.parse import urlparse

from ius_razon.security.llm_ollama_config import OllamaProviderSettings

LOGGER = logging.getLogger(__name__)
_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}
_ALLOWED_PATHS = {"/api/version", "/api/tags"}
_MAX_DIAGNOSTIC_RESPONSE_BYTES = 512_000


class OllamaDiagnosticError(RuntimeError):
    """Fallo seguro al consultar el servicio local de Ollama."""

    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class LocalJSONReadTransport(Protocol):
    """Contrato inyectable para consultas GET exclusivamente locales."""

    def get_json(
        self,
        endpoint: str,
        *,
        timeout_seconds: int,
    ) -> dict[str, object]:
        """Consulta un endpoint local y devuelve un objeto JSON."""

        ...


@dataclass(frozen=True)
class OllamaHealthReport:
    """Resultado seguro y auditable del diagnóstico local."""

    ready: bool
    service_available: bool
    model_installed: bool
    configured_model: str
    message: str
    version: str | None = None
    installed_models: tuple[str, ...] = ()
    error_code: str | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def safe_summary(self) -> dict[str, object]:
        """Devuelve un resumen sin contenido jurídico ni secretos."""

        return {
            "ready": self.ready,
            "service_available": self.service_available,
            "model_installed": self.model_installed,
            "configured_model": self.configured_model,
            "version": self.version,
            "installed_models": list(self.installed_models),
            "installed_model_count": len(self.installed_models),
            "error_code": self.error_code,
            "message": self.message,
            "checked_at": self.checked_at.isoformat(),
            "network_scope": "Solo loopback local",
            "api_key_required": False,
            "estimated_cost_usd": 0.0,
        }


def _validate_diagnostic_endpoint(endpoint: str) -> tuple[str, int, str]:
    parsed = urlparse(endpoint)
    if parsed.scheme != "http":
        raise OllamaDiagnosticError(
            "El diagnóstico de Ollama exige HTTP local.",
            error_code="invalid_local_endpoint",
        )
    if parsed.hostname not in _ALLOWED_HOSTS:
        raise OllamaDiagnosticError(
            "El diagnóstico de Ollama solo admite loopback local.",
            error_code="invalid_local_endpoint",
        )
    if parsed.username is not None or parsed.password is not None:
        raise OllamaDiagnosticError(
            "El diagnóstico local no admite credenciales.",
            error_code="invalid_local_endpoint",
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise OllamaDiagnosticError(
            "El puerto local de Ollama es inválido.",
            error_code="invalid_local_endpoint",
        ) from exc
    if port != 11434:
        raise OllamaDiagnosticError(
            "El diagnóstico solo admite el puerto local 11434.",
            error_code="invalid_local_endpoint",
        )
    if (
        parsed.path not in _ALLOWED_PATHS
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise OllamaDiagnosticError(
            "El endpoint de diagnóstico de Ollama no está permitido.",
            error_code="invalid_local_endpoint",
        )
    if parsed.hostname is None:
        raise OllamaDiagnosticError(
            "El host local de Ollama es inválido.",
            error_code="invalid_local_endpoint",
        )
    return parsed.hostname, port, parsed.path


def _diagnostic_http_error(status: int) -> tuple[str, str]:
    if status == 404:
        return (
            "ollama_diagnostic_endpoint_not_found",
            "La instalación de Ollama no expone el endpoint de diagnóstico esperado.",
        )
    if status == 503:
        return (
            "ollama_overloaded",
            "Ollama local está ocupado o no puede atender la consulta.",
        )
    if status >= 500:
        return (
            "ollama_internal_error",
            "Ollama local informó un error interno.",
        )
    return (
        f"ollama_http_{status}",
        "Ollama local rechazó la consulta de diagnóstico.",
    )


class LocalOnlyJSONReadTransport:
    """Transporte GET sin redirecciones y limitado a loopback."""

    def get_json(
        self,
        endpoint: str,
        *,
        timeout_seconds: int,
    ) -> dict[str, object]:
        host, port, path = _validate_diagnostic_endpoint(endpoint)
        connection = HTTPConnection(
            host=host,
            port=port,
            timeout=timeout_seconds,
        )
        status: int | None = None
        raw = b""
        try:
            connection.request(
                "GET",
                path,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "IUS-Razon/0.7.2",
                },
            )
            response = connection.getresponse()
            status = response.status
            raw = response.read(_MAX_DIAGNOSTIC_RESPONSE_BYTES + 1)
        except TimeoutError as exc:
            raise OllamaDiagnosticError(
                "Ollama local no respondió dentro del tiempo permitido.",
                error_code="ollama_timeout",
            ) from exc
        except ConnectionRefusedError as exc:
            raise OllamaDiagnosticError(
                "Ollama local no está disponible en el puerto 11434.",
                error_code="ollama_unavailable",
            ) from exc
        except (HTTPException, OSError) as exc:
            raise OllamaDiagnosticError(
                "No fue posible consultar Ollama local.",
                error_code="ollama_network_error",
            ) from exc
        finally:
            connection.close()

        if status is None:
            raise OllamaDiagnosticError(
                "Ollama local no devolvió un estado HTTP.",
                error_code="missing_http_status",
            )
        if 300 <= status < 400:
            raise OllamaDiagnosticError(
                "Ollama intentó redirigir una consulta local.",
                error_code="redirect_blocked",
            )
        if not 200 <= status < 300:
            error_code, message = _diagnostic_http_error(status)
            raise OllamaDiagnosticError(
                message,
                error_code=error_code,
            )
        if len(raw) > _MAX_DIAGNOSTIC_RESPONSE_BYTES:
            raise OllamaDiagnosticError(
                "La respuesta de diagnóstico excedió el límite permitido.",
                error_code="response_too_large",
            )
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OllamaDiagnosticError(
                "Ollama devolvió JSON inválido durante el diagnóstico.",
                error_code="invalid_json",
            ) from exc
        if not isinstance(parsed, dict):
            raise OllamaDiagnosticError(
                "La respuesta de diagnóstico debe ser un objeto JSON.",
                error_code="invalid_schema",
            )
        return {str(key): value for key, value in parsed.items()}


def _parse_version(payload: Mapping[str, object]) -> str:
    value = payload.get("version")
    if not isinstance(value, str) or not value.strip():
        raise OllamaDiagnosticError(
            "Ollama no informó una versión válida.",
            error_code="invalid_version_schema",
        )
    return value.strip()[:80]


def _parse_installed_models(
    payload: Mapping[str, object],
) -> tuple[str, ...]:
    raw_models = payload.get("models")
    if not isinstance(raw_models, list):
        raise OllamaDiagnosticError(
            "Ollama no informó la lista de modelos instalados.",
            error_code="invalid_models_schema",
        )
    names: set[str] = set()
    for raw_model in raw_models:
        if not isinstance(raw_model, dict):
            continue
        candidate = raw_model.get("name")
        if not isinstance(candidate, str) or not candidate.strip():
            candidate = raw_model.get("model")
        if isinstance(candidate, str) and candidate.strip():
            names.add(candidate.strip()[:160])
    return tuple(sorted(names))


class OllamaHealthProbe:
    """Verifica servicio, versión y presencia del modelo configurado."""

    def __init__(
        self,
        settings: OllamaProviderSettings,
        *,
        transport: LocalJSONReadTransport | None = None,
    ) -> None:
        settings.validate()
        self._settings = settings
        self._transport = transport or LocalOnlyJSONReadTransport()

    def check(self) -> OllamaHealthReport:
        """Ejecuta dos consultas GET locales sin enviar contexto jurídico."""

        try:
            version_payload = self._transport.get_json(
                self._settings.version_endpoint,
                timeout_seconds=self._settings.health_timeout_seconds,
            )
            version = _parse_version(version_payload)
            models_payload = self._transport.get_json(
                self._settings.tags_endpoint,
                timeout_seconds=self._settings.health_timeout_seconds,
            )
            installed_models = _parse_installed_models(models_payload)
        except OllamaDiagnosticError as exc:
            LOGGER.warning(
                "Diagnóstico de Ollama no disponible. error_code=%s",
                exc.error_code,
            )
            return OllamaHealthReport(
                ready=False,
                service_available=False,
                model_installed=False,
                configured_model=self._settings.model,
                message=str(exc),
                error_code=exc.error_code,
            )

        model_installed = self._settings.model in installed_models
        if not model_installed:
            message = (
                "Ollama está operativo, pero el modelo configurado "
                f"{self._settings.model!r} no está instalado localmente."
            )
            LOGGER.warning(
                "Modelo local no instalado. model=%s",
                self._settings.model,
            )
            return OllamaHealthReport(
                ready=False,
                service_available=True,
                model_installed=False,
                configured_model=self._settings.model,
                version=version,
                installed_models=installed_models,
                message=message,
                error_code="ollama_model_not_installed",
            )

        LOGGER.info(
            "Ollama local listo. version=%s model=%s",
            version,
            self._settings.model,
        )
        return OllamaHealthReport(
            ready=True,
            service_available=True,
            model_installed=True,
            configured_model=self._settings.model,
            version=version,
            installed_models=installed_models,
            message="Ollama local y el modelo configurado están listos.",
        )
