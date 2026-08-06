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
    ExternalConsent,
    ProviderCallStatus,
    ProviderMode,
    ProviderRequest,
)
from ius_razon.security.llm_external_config import (
    ExternalProviderConfigurationError,
    ExternalProviderSettings,
)
from ius_razon.services.llm_assistant_service import LLMAssistantService
from ius_razon.services.llm_provider import (
    ExternalHTTPProvider,
    ExternalProviderError,
)


class FakeTransport:
    """Transporte controlado que nunca usa red."""

    def __init__(
        self,
        response: dict[str, object] | None = None,
        error: ExternalProviderError | None = None,
    ) -> None:
        self.response = response or {
            "output_text": "## Resumen\n- Pago acreditado [H-001].",
            "request_id": "req-test-001",
            "usage": {
                "input_tokens": 120,
                "output_tokens": 32,
            },
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


def external_settings(
    *,
    max_input_tokens: int = 16000,
    max_output_tokens: int = 2000,
    max_cost_usd: float = 0.10,
    input_rate: float = 1.0,
    output_rate: float = 2.0,
) -> ExternalProviderSettings:
    return ExternalProviderSettings(
        enabled=True,
        endpoint="https://llm.example.test/generate",
        api_key="secret-test-key",
        model="test-model",
        timeout_seconds=20,
        max_retries=1,
        max_input_tokens=max_input_tokens,
        max_output_tokens=max_output_tokens,
        max_cost_usd=max_cost_usd,
        input_cost_per_million_usd=input_rate,
        output_cost_per_million_usd=output_rate,
    )


def external_request(
    case_id: str,
    issue_id: str,
    run_id: str,
    *,
    consent: bool = True,
    allow_fallback: bool = True,
    max_cost_usd: float = 0.10,
    max_output_tokens: int = 1000,
):
    request = assistant_request(case_id, issue_id, run_id)
    return request.model_copy(
        update={
            "provider_mode": ProviderMode.EXTERNAL,
            "external_consent": ExternalConsent(
                reviewed_context=consent,
                authorized_external_call=consent,
                accepted_cost_limit=consent,
            ),
            "anonymize_parties": True,
            "allow_fallback": allow_fallback,
            "max_cost_usd": max_cost_usd,
            "max_output_tokens": max_output_tokens,
        }
    )


def configure_external(
    assistant: LLMAssistantService,
    settings: ExternalProviderSettings,
    transport: FakeTransport,
) -> None:
    provider = ExternalHTTPProvider(
        settings,
        transport=transport,
        sleep=lambda _: None,
    )
    assistant._external_settings = settings
    assistant._external_provider = provider


def test_external_provider_is_disabled_by_default() -> None:
    settings = ExternalProviderSettings.from_env({})

    assert settings.enabled is False
    assert settings.configured is False
    assert settings.api_key_configured is False


def test_secret_is_redacted_from_repr_and_summary() -> None:
    settings = external_settings()

    assert "secret-test-key" not in repr(settings)
    assert "secret-test-key" not in str(settings.safe_summary())
    assert settings.safe_summary()["api_key_configured"] is True


def test_enabled_provider_requires_https_endpoint() -> None:
    with pytest.raises(
        ExternalProviderConfigurationError,
        match="HTTPS",
    ):
        ExternalProviderSettings.from_env(
            {
                "IUS_RAZON_LLM_EXTERNAL_ENABLED": "true",
                "IUS_RAZON_LLM_ENDPOINT": "http://example.test",
                "IUS_RAZON_LLM_API_KEY": "secret",
            }
        )


def test_endpoint_cannot_embed_credentials() -> None:
    with pytest.raises(
        ExternalProviderConfigurationError,
        match="credenciales",
    ):
        ExternalProviderSettings.from_env(
            {
                "IUS_RAZON_LLM_EXTERNAL_ENABLED": "true",
                "IUS_RAZON_LLM_ENDPOINT": "https://user:pass@example.test",
                "IUS_RAZON_LLM_API_KEY": "secret",
            }
        )


def test_external_request_requires_anonymization() -> None:
    with pytest.raises(ValidationError, match="anonimización"):
        AssistantRequest(
            case_id="case",
            issue_id="issue",
            task=AssistantTask.CASE_SUMMARY,
            selected_categories=[ContextCategory.FACT],
            provider_mode=ProviderMode.EXTERNAL,
            anonymize_parties=False,
        )


def test_external_provider_sends_key_only_in_header() -> None:
    settings = external_settings()
    transport = FakeTransport()
    provider = ExternalHTTPProvider(
        settings,
        transport=transport,
        sleep=lambda _: None,
    )
    response = provider.generate(
        ProviderRequest(
            task=AssistantTask.CASE_SUMMARY,
            context_items=[
                ContextItem(
                    code="H-001",
                    category=ContextCategory.FACT,
                    title="Hecho",
                    content="Pago acreditado.",
                )
            ],
            allowed_codes=["H-001"],
            max_output_chars=2000,
            system_instruction="Usa solo contexto y conserva referencias internas.",
        )
    )

    call = transport.calls[0]
    assert call["headers"]["Authorization"] == "Bearer secret-test-key"
    assert "secret-test-key" not in str(call["payload"])
    assert response.external_call is True
    assert response.input_tokens == 120
    assert response.output_tokens == 32


def test_incomplete_consent_is_blocked_and_audited(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    settings = external_settings()
    transport = FakeTransport()
    configure_external(assistant, settings, transport)

    with pytest.raises(ValueError, match="confirmaciones"):
        assistant.generate_draft(
            external_request(
                case_id,
                issue_id,
                run_id,
                consent=False,
            )
        )

    calls = assistant.list_provider_calls(case_id, issue_id)
    assert calls[0].status is ProviderCallStatus.BLOCKED
    assert calls[0].error_code == "consent_incomplete"
    assert transport.calls == []


def test_external_success_persists_usage_without_secret(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    settings = external_settings()
    transport = FakeTransport()
    configure_external(assistant, settings, transport)

    record = assistant.generate_draft(
        external_request(case_id, issue_id, run_id)
    )

    assert record.provider_mode is ProviderMode.EXTERNAL
    assert record.external_call is True
    assert record.fallback_used is False
    assert record.input_tokens == 120
    assert record.output_tokens == 32
    calls = assistant.list_provider_calls(case_id, issue_id)
    assert calls[0].status is ProviderCallStatus.SUCCEEDED
    assert calls[0].draft_id == record.id
    assert b"secret-test-key" not in assistant._repository.db_path.read_bytes()


def test_external_failure_uses_local_fallback(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    settings = external_settings()
    transport = FakeTransport(
        error=ExternalProviderError(
            "fallo controlado",
            error_code="network_error",
        )
    )
    configure_external(assistant, settings, transport)

    record = assistant.generate_draft(
        external_request(case_id, issue_id, run_id)
    )

    assert record.fallback_used is True
    assert record.external_call is True
    assert record.provider_name == "Simulado local"
    assert record.fallback_reason == "network_error"
    calls = assistant.list_provider_calls(case_id, issue_id)
    assert calls[0].status is ProviderCallStatus.FALLBACK


def test_external_failure_without_fallback_is_audited(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    settings = external_settings()
    transport = FakeTransport(
        error=ExternalProviderError(
            "fallo controlado",
            error_code="network_error",
        )
    )
    configure_external(assistant, settings, transport)

    with pytest.raises(ExternalProviderError):
        assistant.generate_draft(
            external_request(
                case_id,
                issue_id,
                run_id,
                allow_fallback=False,
            )
        )

    calls = assistant.list_provider_calls(case_id, issue_id)
    assert calls[0].status is ProviderCallStatus.FAILED
    assert calls[0].external_call is True
    assert calls[0].error_code == "network_error"


def test_cost_limit_blocks_before_transport(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    settings = external_settings(
        max_cost_usd=0.000001,
        input_rate=100.0,
        output_rate=100.0,
    )
    transport = FakeTransport()
    configure_external(assistant, settings, transport)

    with pytest.raises(ValueError, match="costo"):
        assistant.generate_draft(
            external_request(
                case_id,
                issue_id,
                run_id,
                max_cost_usd=0.000001,
            )
        )

    assert transport.calls == []
    assert (
        assistant.list_provider_calls(case_id, issue_id)[0].error_code
        == "cost_limit"
    )


def test_output_token_cap_blocks_before_transport(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    settings = external_settings(max_output_tokens=128)
    transport = FakeTransport()
    configure_external(assistant, settings, transport)

    with pytest.raises(ValueError, match="salida"):
        assistant.generate_draft(
            external_request(
                case_id,
                issue_id,
                run_id,
                max_output_tokens=256,
            )
        )

    assert transport.calls == []
    assert (
        assistant.list_provider_calls(case_id, issue_id)[0].error_code
        == "output_token_limit"
    )
