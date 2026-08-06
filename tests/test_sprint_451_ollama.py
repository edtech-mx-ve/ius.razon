from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_sprint_43 import assistant_request, build_assistant

from ius_razon.domain.llm_models import (
    AssistantRequest,
    AssistantTask,
    ContextCategory,
    ContextItem,
    ProviderMode,
    ProviderRequest,
)
from ius_razon.security.llm_ollama_config import (
    OLLAMA_CHAT_ENDPOINT,
    OllamaProviderConfigurationError,
    OllamaProviderSettings,
)
from ius_razon.services.llm_provider import (
    ExternalProviderError,
    OllamaLocalProvider,
)


class FakeOllamaTransport:
    """Transporte local inyectable que nunca abre sockets."""

    def __init__(
        self,
        response: dict[str, object] | None = None,
        error: ExternalProviderError | None = None,
    ) -> None:
        self.response = response or {
            "model": "qwen3:1.7b",
            "created_at": "2026-08-06T10:00:00Z",
            "message": {
                "role": "assistant",
                "content": (
                    "## Resumen local\n"
                    "- El pago fue registrado [H-001].\n"
                    "- El plazo venció sin entrega [H-002]."
                ),
            },
            "done": True,
            "prompt_eval_count": 240,
            "eval_count": 48,
        }
        self.error = error
        self.calls: list[dict[str, object]] = []

    def post_json(
        self,
        endpoint: str,
        *,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: int,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "endpoint": endpoint,
                "headers": dict(headers),
                "payload": dict(payload),
                "timeout_seconds": timeout_seconds,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


def ollama_settings(
    *,
    max_input_tokens: int = 3072,
    max_output_tokens: int = 512,
) -> OllamaProviderSettings:
    return OllamaProviderSettings(
        enabled=True,
        model="qwen3:1.7b",
        endpoint=OLLAMA_CHAT_ENDPOINT,
        timeout_seconds=120,
        max_input_tokens=max_input_tokens,
        max_output_tokens=max_output_tokens,
        context_window=4096,
        temperature=0.0,
        max_retries=0,
    )


def provider_request() -> ProviderRequest:
    return ProviderRequest(
        task=AssistantTask.CASE_SUMMARY,
        instructions="Resume pago y vencimiento.",
        context_items=[
            ContextItem(
                code="H-001",
                category=ContextCategory.FACT,
                title="Pago",
                content="La parte compradora pagó.",
            ),
            ContextItem(
                code="H-002",
                category=ContextCategory.FACT,
                title="Vencimiento",
                content="El plazo venció sin entrega.",
            ),
        ],
        allowed_codes=["H-001", "H-002"],
        max_output_chars=4000,
        system_instruction=(
            "Usa solo los elementos proporcionados y conserva las citas internas."
        ),
        max_output_tokens=128,
        timeout_seconds=60,
        max_retries=0,
        max_cost_usd=0.0,
    )


def test_ollama_settings_defaults_are_local_and_free() -> None:
    settings = OllamaProviderSettings.from_env({})

    assert settings.configured is True
    assert settings.endpoint == OLLAMA_CHAT_ENDPOINT
    assert settings.model == "qwen3:1.7b"
    assert settings.max_retries == 0
    assert settings.safe_summary()["api_key_required"] is False
    assert settings.safe_summary()["cost_per_request_usd"] == 0.0


def test_ollama_settings_reject_remote_host() -> None:
    with pytest.raises(
        OllamaProviderConfigurationError,
        match="solo puede conectarse",
    ):
        OllamaProviderSettings.from_env(
            {
                "IUS_RAZON_OLLAMA_ENDPOINT": (
                    "http://example.com:11434/api/chat"
                )
            }
        )


def test_ollama_settings_reject_wrong_port() -> None:
    with pytest.raises(
        OllamaProviderConfigurationError,
        match="puerto local 11434",
    ):
        OllamaProviderSettings.from_env(
            {
                "IUS_RAZON_OLLAMA_ENDPOINT": (
                    "http://127.0.0.1:8080/api/chat"
                )
            }
        )


def test_ollama_settings_reject_invalid_path() -> None:
    with pytest.raises(
        OllamaProviderConfigurationError,
        match="/api/chat",
    ):
        OllamaProviderSettings.from_env(
            {
                "IUS_RAZON_OLLAMA_ENDPOINT": (
                    "http://127.0.0.1:11434/api/generate"
                )
            }
        )


def test_ollama_settings_reject_nonzero_retries() -> None:
    with pytest.raises(
        OllamaProviderConfigurationError,
        match="entre 0 y 0",
    ):
        OllamaProviderSettings.from_env(
            {"IUS_RAZON_OLLAMA_MAX_RETRIES": "1"}
        )


def test_ollama_mode_requires_anonymization() -> None:
    with pytest.raises(
        ValidationError,
        match="requieren anonimización",
    ):
        AssistantRequest(
            case_id="case",
            issue_id="issue",
            task=AssistantTask.CASE_SUMMARY,
            selected_categories=[ContextCategory.FACT],
            anonymize_parties=False,
            provider_mode=ProviderMode.OLLAMA,
        )


def test_ollama_provider_builds_safe_local_payload() -> None:
    transport = FakeOllamaTransport()
    provider = OllamaLocalProvider(
        ollama_settings(),
        transport=transport,
    )

    response = provider.generate(provider_request())

    assert response.external_call is False
    assert response.estimated_cost_usd == 0.0
    assert response.input_tokens == 240
    assert response.output_tokens == 48
    call = transport.calls[0]
    assert call["endpoint"] == OLLAMA_CHAT_ENDPOINT
    headers = call["headers"]
    assert isinstance(headers, dict)
    assert "Authorization" not in headers
    payload = call["payload"]
    assert isinstance(payload, dict)
    assert payload["stream"] is False
    assert payload["think"] is False
    options = payload["options"]
    assert isinstance(options, dict)
    assert options["temperature"] == 0.0
    assert options["num_predict"] == 128


def test_ollama_provider_uses_system_and_user_messages() -> None:
    transport = FakeOllamaTransport()
    provider = OllamaLocalProvider(
        ollama_settings(),
        transport=transport,
    )

    provider.generate(provider_request())

    payload = transport.calls[0]["payload"]
    assert isinstance(payload, dict)
    messages = payload["messages"]
    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert '"allowed_codes":["H-001","H-002"]' in messages[1]["content"]


def test_ollama_provider_rejects_empty_content() -> None:
    transport = FakeOllamaTransport(
        response={
            "message": {"role": "assistant", "content": "   "},
            "done": True,
        }
    )
    provider = OllamaLocalProvider(
        ollama_settings(),
        transport=transport,
    )

    with pytest.raises(
        ExternalProviderError,
        match="no devolvió texto",
    ):
        provider.generate(provider_request())


def test_ollama_service_exposes_safe_summary(tmp_path: Path) -> None:
    assistant, *_ = build_assistant(tmp_path)
    settings = ollama_settings()
    assistant._ollama_settings = settings
    assistant._ollama_provider = OllamaLocalProvider(
        settings,
        transport=FakeOllamaTransport(),
    )

    assert assistant.ollama_available is True
    summary = assistant.ollama_safe_summary
    assert summary["network_scope"] == "Solo equipo local"
    assert summary["api_key_required"] is False
    assert summary["think"] is False


def test_ollama_service_generates_audited_local_draft(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    settings = ollama_settings()
    assistant._ollama_settings = settings
    assistant._ollama_provider = OllamaLocalProvider(
        settings,
        transport=FakeOllamaTransport(
            response={
                "model": "qwen3:1.7b",
                "created_at": "2026-08-06T10:00:00Z",
                "message": {
                    "role": "assistant",
                    "content": (
                        "## Resumen local\n"
                        "- El pago fue registrado [H-001].\n"
                        "- El comprobante respalda el pago [P-001]."
                    ),
                },
                "done": True,
                "prompt_eval_count": 240,
                "eval_count": 48,
            }
        ),
    )
    request = assistant_request(case_id, issue_id, run_id).model_copy(
        update={
            "provider_mode": ProviderMode.OLLAMA,
            "selected_codes": ["H-001", "P-001"],
            "max_input_tokens": 4096,
            "max_output_tokens": 128,
            "max_cost_usd": 0.0,
            "timeout_seconds": 60,
            "max_retries": 0,
            "allow_fallback": True,
        }
    )

    draft = assistant.generate_draft(request)
    calls = assistant.list_provider_calls(case_id, issue_id=issue_id)

    assert draft.provider_mode is ProviderMode.OLLAMA
    assert draft.provider_name == "Ollama local gratuito"
    assert draft.external_call is False
    assert draft.estimated_cost_usd == 0.0
    assert draft.citation_coverage == 1.0
    assert calls[0].external_call is False
    assert calls[0].estimated_cost_usd == 0.0


def test_ollama_service_falls_back_to_deterministic_provider(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    settings = ollama_settings()
    assistant._ollama_settings = settings
    assistant._ollama_provider = OllamaLocalProvider(
        settings,
        transport=FakeOllamaTransport(
            error=ExternalProviderError(
                "Ollama no disponible.",
                error_code="network_error",
            )
        ),
    )
    request = assistant_request(case_id, issue_id, run_id).model_copy(
        update={
            "provider_mode": ProviderMode.OLLAMA,
            "selected_codes": ["H-001"],
            "max_input_tokens": 4096,
            "max_output_tokens": 128,
            "max_cost_usd": 0.0,
            "timeout_seconds": 60,
            "max_retries": 0,
            "allow_fallback": True,
        }
    )

    draft = assistant.generate_draft(request)

    assert draft.fallback_used is True
    assert draft.fallback_reason == "network_error"
    assert draft.external_call is False
    assert draft.provider_name == "Simulado local"


def test_ollama_service_blocks_output_limit(tmp_path: Path) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    settings = ollama_settings(max_output_tokens=64)
    assistant._ollama_settings = settings
    assistant._ollama_provider = OllamaLocalProvider(
        settings,
        transport=FakeOllamaTransport(),
    )
    request = assistant_request(case_id, issue_id, run_id).model_copy(
        update={
            "provider_mode": ProviderMode.OLLAMA,
            "max_input_tokens": 4096,
            "max_output_tokens": 128,
            "max_cost_usd": 0.0,
            "timeout_seconds": 60,
            "max_retries": 0,
            "allow_fallback": True,
        }
    )

    with pytest.raises(ValueError, match="salida supera"):
        assistant.generate_draft(request)

    calls = assistant.list_provider_calls(case_id, issue_id=issue_id)
    assert calls[0].status.value == "Bloqueada"
    assert calls[0].error_code == "output_token_limit"


def test_active_app_wires_ollama_and_not_openai() -> None:
    app_source = Path("app.py").read_text(encoding="utf-8")
    view_source = Path(
        "src/ius_razon/ui/llm_assistant_view.py"
    ).read_text(encoding="utf-8")

    assert "OllamaLocalProvider" in app_source
    assert "OpenAIResponsesProvider" not in app_source
    assert "ExternalHTTPProvider" not in app_source
    assert "ProviderMode.OLLAMA" in view_source
    assert "ProviderMode.OPENAI" not in view_source
