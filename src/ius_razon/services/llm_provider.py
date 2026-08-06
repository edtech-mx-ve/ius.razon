from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable, Mapping
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ius_razon.domain.llm_models import (
    AssistantTask,
    ContextCategory,
    ContextItem,
    ProviderRequest,
    ProviderResponse,
)
from ius_razon.security.llm_external_config import ExternalProviderSettings
from ius_razon.security.llm_openai_config import OpenAIProviderSettings


class LLMProvider(Protocol):
    """Interfaz sustituible para proveedores asistivos."""

    @property
    def provider_name(self) -> str:
        """Nombre estable del proveedor."""

        ...

    @property
    def model_name(self) -> str:
        """Nombre estable del modelo."""

        ...

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Genera una respuesta sin modificar el expediente."""

        ...


class ExternalProviderError(RuntimeError):
    """Fallo controlado sin exponer secretos ni contenido sensible."""

    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class JSONTransport(Protocol):
    """Transporte inyectable para aislar red y facilitar pruebas."""

    def post_json(
        self,
        endpoint: str,
        *,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: int,
    ) -> dict[str, object]:
        """Envía JSON y devuelve un objeto JSON."""

        ...


class UrllibJSONTransport:
    """Transporte HTTPS basado únicamente en la biblioteca estándar."""

    def post_json(
        self,
        endpoint: str,
        *,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: int,
    ) -> dict[str, object]:
        encoded = json.dumps(
            dict(payload),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=encoded,
            headers=dict(headers),
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read(2_000_001)
        except HTTPError as exc:
            raise ExternalProviderError(
                "El proveedor externo rechazó la solicitud.",
                error_code=f"http_{exc.code}",
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ExternalProviderError(
                "No fue posible comunicarse con el proveedor externo.",
                error_code="network_error",
            ) from exc
        if len(raw) > 2_000_000:
            raise ExternalProviderError(
                "La respuesta externa excedió el límite permitido.",
                error_code="response_too_large",
            )
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExternalProviderError(
                "El proveedor externo devolvió JSON inválido.",
                error_code="invalid_json",
            ) from exc
        if not isinstance(parsed, dict):
            raise ExternalProviderError(
                "La respuesta externa debe ser un objeto JSON.",
                error_code="invalid_schema",
            )
        return {str(key): value for key, value in parsed.items()}


class ExternalHTTPProvider:
    """Proveedor JSON externo con límites, reintentos y costos controlados."""

    def __init__(
        self,
        settings: ExternalProviderSettings,
        *,
        transport: JSONTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        settings.validate()
        if not settings.configured:
            raise ValueError("El proveedor externo no está habilitado y configurado.")
        self._settings = settings
        self._transport = transport or UrllibJSONTransport()
        self._sleep = sleep

    @property
    def provider_name(self) -> str:
        return "Externo JSON controlado"

    @property
    def model_name(self) -> str:
        return self._settings.model

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Realiza una llamada HTTPS sin persistir ni registrar la clave."""

        timeout_seconds = min(
            request.timeout_seconds,
            self._settings.timeout_seconds,
        )
        max_retries = min(request.max_retries, self._settings.max_retries)
        max_output_tokens = min(
            request.max_output_tokens,
            self._settings.max_output_tokens,
        )
        payload: dict[str, object] = {
            "model": self.model_name,
            "system_instruction": request.system_instruction,
            "task": request.task.value,
            "instructions": request.instructions,
            "context": [
                item.model_dump(mode="json")
                for item in request.context_items
            ],
            "allowed_codes": list(request.allowed_codes),
            "max_output_tokens": max_output_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "IUS-Razon/0.7.0",
        }

        last_error: ExternalProviderError | None = None
        response_payload: dict[str, object] | None = None
        for attempt in range(max_retries + 1):
            try:
                response_payload = self._transport.post_json(
                    self._settings.endpoint,
                    headers=headers,
                    payload=payload,
                    timeout_seconds=timeout_seconds,
                )
                break
            except ExternalProviderError as exc:
                last_error = exc
                if attempt >= max_retries:
                    raise
                self._sleep(min(0.25 * (2**attempt), 1.0))
        if response_payload is None:
            raise last_error or ExternalProviderError(
                "La llamada externa no produjo una respuesta.",
                error_code="empty_response",
            )

        text_value = response_payload.get("output_text")
        if not isinstance(text_value, str):
            text_value = response_payload.get("text")
        if not isinstance(text_value, str) or not text_value.strip():
            raise ExternalProviderError(
                "La respuesta externa no contiene texto utilizable.",
                error_code="missing_output_text",
            )
        text = text_value.strip()
        if len(text) > request.max_output_chars:
            text = text[: request.max_output_chars].rstrip()

        usage = response_payload.get("usage")
        usage_mapping = (
            cast(dict[str, object], usage)
            if isinstance(usage, dict)
            else {}
        )
        input_tokens = self._optional_nonnegative_int(
            usage_mapping.get("input_tokens")
        )
        output_tokens = self._optional_nonnegative_int(
            usage_mapping.get("output_tokens")
        )
        estimated_cost = (
            self._settings.estimate_cost(input_tokens or 0, output_tokens or 0)
            if input_tokens is not None or output_tokens is not None
            else None
        )
        request_id_value = response_payload.get("request_id")
        request_id = (
            str(request_id_value)[:240]
            if request_id_value is not None
            else None
        )
        return ProviderResponse(
            text=text,
            provider_name=self.provider_name,
            model_name=self.model_name,
            request_id=request_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost,
            external_call=True,
        )

    @staticmethod
    def _optional_nonnegative_int(value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int) and value >= 0:
            return value
        return None


class OpenAIResponsesProvider:
    """Adaptador específico para OpenAI Responses API mediante HTTPS."""

    def __init__(
        self,
        settings: OpenAIProviderSettings,
        *,
        transport: JSONTransport | None = None,
    ) -> None:
        settings.validate()
        if not settings.configured:
            raise ValueError("OpenAI no está habilitado y configurado.")
        self._settings = settings
        self._transport = transport or UrllibJSONTransport()

    @property
    def provider_name(self) -> str:
        return "OpenAI Responses API"

    @property
    def model_name(self) -> str:
        return self._settings.model

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Realiza una única llamada sin almacenar el contenido en OpenAI."""

        if request.max_retries != 0:
            raise ExternalProviderError(
                "La integración inicial con OpenAI exige cero reintentos.",
                error_code="retries_not_allowed",
            )
        max_output_tokens = min(
            request.max_output_tokens,
            self._settings.max_output_tokens,
        )
        input_text = self._build_input(request)
        payload: dict[str, object] = {
            "model": self.model_name,
            "instructions": request.system_instruction,
            "input": input_text,
            "max_output_tokens": max_output_tokens,
            "store": False,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "IUS-Razon/0.7.0",
        }
        response_payload = self._transport.post_json(
            self._settings.endpoint,
            headers=headers,
            payload=payload,
            timeout_seconds=min(
                request.timeout_seconds,
                self._settings.timeout_seconds,
            ),
        )
        text = self._extract_output_text(response_payload)
        if len(text) > request.max_output_chars:
            text = text[: request.max_output_chars].rstrip()

        usage = response_payload.get("usage")
        usage_mapping = (
            cast(dict[str, object], usage)
            if isinstance(usage, dict)
            else {}
        )
        input_tokens = ExternalHTTPProvider._optional_nonnegative_int(
            usage_mapping.get("input_tokens")
        )
        output_tokens = ExternalHTTPProvider._optional_nonnegative_int(
            usage_mapping.get("output_tokens")
        )
        estimated_cost = self._settings.estimate_cost(
            input_tokens or 0,
            output_tokens or 0,
        )
        cost_limit = min(
            request.max_cost_usd,
            self._settings.max_cost_usd,
        )
        if estimated_cost > cost_limit:
            raise ExternalProviderError(
                "El costo reportado supera el presupuesto autorizado.",
                error_code="reported_cost_limit_exceeded",
            )
        request_id_value = response_payload.get("id")
        request_id = (
            str(request_id_value)[:240]
            if request_id_value is not None
            else None
        )
        return ProviderResponse(
            text=text,
            provider_name=self.provider_name,
            model_name=self.model_name,
            request_id=request_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost,
            external_call=True,
        )

    @staticmethod
    def _build_input(request: ProviderRequest) -> str:
        context = [
            {
                "code": item.code,
                "category": item.category.value,
                "title": item.title,
                "content": item.content,
            }
            for item in request.context_items
        ]
        payload = {
            "task": request.task.value,
            "user_instruction": request.instructions,
            "allowed_codes": list(request.allowed_codes),
            "context": context,
            "output_requirements": {
                "language": "es",
                "format": "markdown",
                "citations": "Use only bracketed allowed codes.",
                "human_review": "Mandatory.",
            },
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def _extract_output_text(
        cls,
        payload: Mapping[str, object],
    ) -> str:
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        output = payload.get("output")
        fragments: list[str] = []
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "output_text":
                        continue
                    value = block.get("text")
                    if isinstance(value, str) and value.strip():
                        fragments.append(value.strip())
        if fragments:
            return "\n".join(fragments)
        raise ExternalProviderError(
            "OpenAI no devolvió texto utilizable.",
            error_code="missing_output_text",
        )


class DeterministicMockProvider:
    """Proveedor local reproducible para probar el flujo sin consumir API."""

    def __init__(self, model_name: str = "ius-razon-mock-v1") -> None:
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "Simulado local"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Construye un borrador determinista y completamente referenciado."""

        builders: dict[
            AssistantTask,
            Callable[[list[ContextItem]], str],
        ] = {
            AssistantTask.CASE_SUMMARY: self._summary,
            AssistantTask.ARGUMENT_DRAFT: self._argument,
            AssistantTask.CONCLUSION_EXPLANATION: self._conclusion_explanation,
            AssistantTask.MISSING_INFORMATION: self._missing_information,
            AssistantTask.REPORT_SECTION: self._report_section,
        }
        text = builders[request.task](request.context_items)
        if request.instructions:
            referenced = request.context_items[0].code
            instruction = self._compact(request.instructions, 240)
            text = (
                f"{text}\n\n"
                f"Control de contexto: la indicación del usuario fue «{instruction}». "
                f"No se incorporaron hechos nuevos [{referenced}]."
            )
        text = self._limit_output(text, request.max_output_chars)
        return ProviderResponse(
            text=text,
            provider_name=self.provider_name,
            model_name=self.model_name,
        )

    def _summary(self, items: list[ContextItem]) -> str:
        lines = [
            "## Resumen estructurado",
            "Borrador simulado: síntesis construida únicamente con el contexto seleccionado.",
        ]
        for item in items[:8]:
            lines.append(
                f"- {item.title}: {self._compact(item.content)} [{item.code}]"
            )
        lines.append(
            "Revisión humana: confirma autenticidad, vigencia y suficiencia antes de usar el texto."
        )
        return "\n".join(lines)

    def _argument(self, items: list[ContextItem]) -> str:
        issue = self._first(items, ContextCategory.ISSUE) or items[0]
        lines = [
            "## Borrador de argumento",
            (
                "Tesis de trabajo: el problema debe analizarse con base en los "
                f"elementos trazables seleccionados [{issue.code}]."
            ),
        ]
        for category, label in (
            (ContextCategory.FACT, "Hecho relevante"),
            (ContextCategory.EVIDENCE, "Apoyo probatorio"),
            (ContextCategory.SOURCE, "Fundamento jurídico registrado"),
            (ContextCategory.CONCLUSION, "Resultado determinista"),
            (ContextCategory.ARGUMENT, "Posición argumental"),
        ):
            item = self._first(items, category)
            if item is not None:
                lines.append(
                    f"- {label}: {self._compact(item.content)} [{item.code}]"
                )
        lines.append(
            "Revisión humana: el texto es un borrador y no sustituye la valoración jurídica."
        )
        return "\n".join(lines)

    def _conclusion_explanation(self, items: list[ContextItem]) -> str:
        conclusions = [
            item for item in items if item.category is ContextCategory.CONCLUSION
        ]
        selected = conclusions or items[:1]
        lines = [
            "## Explicación de conclusión",
            "Borrador simulado: la explicación no altera el resultado del motor.",
        ]
        for item in selected[:5]:
            lines.append(
                f"- {item.title}: {self._compact(item.content)} [{item.code}]"
            )
        lines.append(
            "Revisión humana: verifica que las premisas y reglas sigan siendo válidas."
        )
        return "\n".join(lines)

    def _missing_information(self, items: list[ContextItem]) -> str:
        issue = self._first(items, ContextCategory.ISSUE) or items[0]
        present = {item.category for item in items}
        expected = (
            ContextCategory.FACT,
            ContextCategory.EVIDENCE,
            ContextCategory.SOURCE,
            ContextCategory.CONCLUSION,
            ContextCategory.ARGUMENT,
        )
        lines = [
            "## Información faltante",
            (
                "Control de contexto: revisión estructural de las categorías "
                "seleccionadas, sin inferir hechos nuevos."
            ),
        ]
        missing = [category for category in expected if category not in present]
        if missing:
            for category in missing:
                lines.append(
                    f"- Falta incorporar al menos un elemento de «{category.value}» "
                    f"para revisar el problema [{issue.code}]."
                )
        else:
            lines.append(
                "Todas las categorías estructurales están representadas, pero su "
                f"autenticidad y suficiencia requieren revisión [{issue.code}]."
            )
        lines.append(
            "Revisión humana: documenta cualquier vacío antes de aprobar el borrador."
        )
        return "\n".join(lines)

    def _report_section(self, items: list[ContextItem]) -> str:
        issue = self._first(items, ContextCategory.ISSUE) or items[0]
        lines = [
            "## Borrador de sección del informe",
            (
                "El análisis parte del problema jurídico registrado y conserva "
                f"su alcance provisional [{issue.code}]."
            ),
        ]
        for item in items:
            if item.code == issue.code:
                continue
            lines.append(
                f"- {item.category.value}: {self._compact(item.content)} [{item.code}]"
            )
            if len(lines) >= 9:
                break
        lines.append(
            "Revisión humana: valida el contenido y edítalo antes de aprobarlo."
        )
        return "\n".join(lines)

    @staticmethod
    def _first(
        items: list[ContextItem],
        category: ContextCategory,
    ) -> ContextItem | None:
        return next(
            (item for item in items if item.category is category),
            None,
        )

    @staticmethod
    def _compact(value: str, limit: int = 280) -> str:
        compact = re.sub(r"\s+", " ", value).strip()
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 1].rstrip()}…"

    @staticmethod
    def _limit_output(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        kept: list[str] = []
        used = 0
        for line in text.splitlines():
            additional = len(line) + (1 if kept else 0)
            if used + additional > max_chars:
                break
            kept.append(line)
            used += additional
        if not kept:
            raise ValueError("El límite de salida es insuficiente.")
        return "\n".join(kept)


class ControlledExternalTestProvider:
    """Proveedor falso que ejercita el contrato externo sin usar red."""

    def __init__(
        self,
        delegate: LLMProvider | None = None,
        model_name: str = "ius-razon-external-test-v1",
    ) -> None:
        self._delegate = delegate or DeterministicMockProvider()
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "Externo falso de integración"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Genera una respuesta local con la misma forma del adaptador externo."""

        effective_request = request.model_copy(
            update={
                "max_output_chars": min(
                    request.max_output_chars,
                    request.max_output_tokens * 4,
                )
            }
        )
        response = self._delegate.generate(effective_request)
        input_chars = sum(
            len(item.code)
            + len(item.category.value)
            + len(item.title)
            + len(item.content)
            for item in request.context_items
        )
        input_tokens = max(1, (input_chars + 3) // 4)
        output_tokens = max(1, (len(response.text) + 3) // 4)
        fingerprint = hashlib.sha256(
            (
                request.task.value
                + "|"
                + "|".join(request.allowed_codes)
                + "|"
                + response.text
            ).encode("utf-8")
        ).hexdigest()[:20]
        return response.model_copy(
            update={
                "provider_name": self.provider_name,
                "model_name": self.model_name,
                "request_id": f"integration-test-{fingerprint}",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": 0.0,
                "external_call": False,
                "fallback_used": False,
                "fallback_reason": None,
            }
        )

