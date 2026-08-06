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
from ius_razon.security.llm_openai_config import (
    OPENAI_RESPONSES_ENDPOINT,
    OpenAIProviderConfigurationError,
    OpenAIProviderSettings,
)
from ius_razon.services.llm_assistant_service import LLMAssistantService
from ius_razon.services.llm_provider import (
    ExternalProviderError,
    OpenAIResponsesProvider,
)


class FakeOpenAITransport:
    """Transporte inyectable que nunca utiliza red."""

    def __init__(
        self,
        response: dict[str, object] | None = None,
        error: ExternalProviderError | None = None,
    ) -> None:
        self.response = response or {
            "id": "resp-test-001",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "## Resumen\n- Pago acreditado [H-001].",
                        }
                    ],
                }
            ],
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


def openai_settings(
    *,
    max_input_tokens: int = 16000,
    max_output_tokens: int = 512,
    max_cost_usd: float = 0.10,
    input_rate: float = 1.0,
    output_rate: float = 2.0,
) -> OpenAIProviderSettings:
    return OpenAIProviderSettings(
        enabled=True,
        api_key="openai-test-secret",
        model="gpt-test",
        timeout_seconds=20,
        max_retries=0,
        max_input_tokens=max_input_tokens,
        max_output_tokens=max_output_tokens,
        max_cost_usd=max_cost_usd,
        input_cost_per_million_usd=input_rate,
        output_cost_per_million_usd=output_rate,
    )


def provider_request() -> ProviderRequest:
    return ProviderRequest(
        task=AssistantTask.CASE_SUMMARY,
        instructions="Prioriza el pago.",
        context_items=[
            ContextItem(
                code="H-001",
                category=ContextCategory.FACT,
                title="Pago",
                content="La parte compradora pagó el precio.",
            )
        ],
        allowed_codes=["H-001"],
        max_output_chars=2000,
        max_output_tokens=256,
        timeout_seconds=20,
        max_retries=0,
        max_cost_usd=0.10,
        system_instruction=(
            "Usa únicamente el contexto y conserva referencias internas."
        ),
    )


def openai_request(
    case_id: str,
    issue_id: str,
    run_id: str,
    **updates: object,
) -> AssistantRequest:
    request = assistant_request(case_id, issue_id, run_id)
    values: dict[str, object] = {
        "provider_mode": ProviderMode.OPENAI,
        "external_consent": ExternalConsent(
            reviewed_context=True,
            authorized_external_call=True,
            accepted_cost_limit=True,
        ),
        "anonymize_parties": True,
        "max_input_tokens": 16000,
        "max_output_tokens": 256,
        "max_cost_usd": 0.10,
        "timeout_seconds": 20,
        "max_retries": 0,
        "allow_fallback": True,
        "confirm_single_call": True,
    }
    values.update(updates)
    return request.model_copy(update=values)


def configure_openai(
    assistant: LLMAssistantService,
    settings: OpenAIProviderSettings,
    transport: FakeOpenAITransport,
) -> None:
    assistant._openai_settings = settings
    assistant._openai_provider = OpenAIResponsesProvider(
        settings,
        transport=transport,
    )


def test_openai_is_disabled_by_default() -> None:
    settings = OpenAIProviderSettings.from_env({})

    assert settings.enabled is False
    assert settings.configured is False
    assert settings.api_key_configured is False
    assert settings.endpoint == OPENAI_RESPONSES_ENDPOINT


def test_openai_enabled_requires_api_key() -> None:
    with pytest.raises(
        OpenAIProviderConfigurationError,
        match="OPENAI_API_KEY",
    ):
        OpenAIProviderSettings.from_env(
            {
                "IUS_RAZON_OPENAI_ENABLED": "true",
                "IUS_RAZON_OPENAI_INPUT_COST_PER_1M_USD": "1",
                "IUS_RAZON_OPENAI_OUTPUT_COST_PER_1M_USD": "2",
            }
        )


def test_openai_enabled_requires_explicit_pricing() -> None:
    with pytest.raises(
        OpenAIProviderConfigurationError,
        match="tarifas",
    ):
        OpenAIProviderSettings.from_env(
            {
                "IUS_RAZON_OPENAI_ENABLED": "true",
                "OPENAI_API_KEY": "secret",
            }
        )


def test_openai_secret_is_redacted_and_endpoint_is_fixed() -> None:
    settings = openai_settings()

    assert "openai-test-secret" not in repr(settings)
    assert "openai-test-secret" not in str(settings.safe_summary())
    assert settings.safe_summary()["endpoint_host"] == "api.openai.com"
    assert settings.safe_summary()["pricing_configured"] is True


def test_openai_request_requires_anonymization() -> None:
    with pytest.raises(ValidationError, match="anonimización"):
        AssistantRequest(
            case_id="case",
            issue_id="issue",
            task=AssistantTask.CASE_SUMMARY,
            selected_categories=[ContextCategory.FACT],
            provider_mode=ProviderMode.OPENAI,
            anonymize_parties=False,
        )


def test_openai_provider_uses_responses_contract_without_store() -> None:
    settings = openai_settings()
    transport = FakeOpenAITransport()
    provider = OpenAIResponsesProvider(settings, transport=transport)

    response = provider.generate(provider_request())

    call = transport.calls[0]
    payload = call["payload"]
    assert call["endpoint"] == OPENAI_RESPONSES_ENDPOINT
    assert call["headers"]["Authorization"] == "Bearer openai-test-secret"
    assert payload["model"] == "gpt-test"
    assert payload["store"] is False
    assert payload["max_output_tokens"] == 256
    assert "tools" not in payload
    assert "openai-test-secret" not in str(payload)
    assert response.external_call is True


def test_openai_provider_extracts_output_usage_and_cost() -> None:
    settings = openai_settings(input_rate=1.0, output_rate=2.0)
    provider = OpenAIResponsesProvider(
        settings,
        transport=FakeOpenAITransport(),
    )

    response = provider.generate(provider_request())

    assert response.text.endswith("[H-001].")
    assert response.request_id == "resp-test-001"
    assert response.input_tokens == 120
    assert response.output_tokens == 32
    assert response.estimated_cost_usd == 0.000184


def test_openai_provider_accepts_direct_output_text() -> None:
    provider = OpenAIResponsesProvider(
        openai_settings(),
        transport=FakeOpenAITransport(
            response={
                "id": "resp-direct",
                "output_text": "Texto directo [H-001].",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
        ),
    )

    response = provider.generate(provider_request())

    assert response.text == "Texto directo [H-001]."
    assert response.request_id == "resp-direct"


def test_openai_preflight_requires_complete_consent(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_openai(assistant, openai_settings(), FakeOpenAITransport())

    with pytest.raises(ValueError, match="confirmaciones"):
        assistant.generate_draft(
            openai_request(
                case_id,
                issue_id,
                run_id,
                external_consent=ExternalConsent(),
            )
        )

    audit = assistant.list_provider_calls(case_id, issue_id, limit=1)[0]
    assert audit.status is ProviderCallStatus.BLOCKED
    assert audit.error_code == "consent_incomplete"


def test_openai_preflight_requires_single_call_confirmation(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_openai(assistant, openai_settings(), FakeOpenAITransport())

    with pytest.raises(ValueError, match="una sola llamada"):
        assistant.generate_draft(
            openai_request(
                case_id,
                issue_id,
                run_id,
                confirm_single_call=False,
            )
        )

    audit = assistant.list_provider_calls(case_id, issue_id, limit=1)[0]
    assert audit.error_code == "single_call_not_confirmed"


def test_openai_preflight_rejects_retries(tmp_path: Path) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_openai(assistant, openai_settings(), FakeOpenAITransport())

    with pytest.raises(ValueError, match="cero reintentos"):
        assistant.generate_draft(
            openai_request(
                case_id,
                issue_id,
                run_id,
                max_retries=1,
            )
        )


def test_openai_preflight_requires_fallback(tmp_path: Path) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_openai(assistant, openai_settings(), FakeOpenAITransport())

    with pytest.raises(ValueError, match="fallback local"):
        assistant.generate_draft(
            openai_request(
                case_id,
                issue_id,
                run_id,
                allow_fallback=False,
            )
        )


def test_openai_success_is_audited_without_secret(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    transport = FakeOpenAITransport()
    configure_openai(assistant, openai_settings(), transport)

    record = assistant.generate_draft(
        openai_request(case_id, issue_id, run_id)
    )

    assert record.provider_mode is ProviderMode.OPENAI
    assert record.external_call is True
    assert record.fallback_used is False
    audit = assistant.list_provider_calls(case_id, issue_id, limit=1)[0]
    assert audit.status is ProviderCallStatus.SUCCEEDED
    assert audit.external_call is True
    assert audit.draft_id == record.id
    assert b"openai-test-secret" not in assistant._repository.db_path.read_bytes()


def test_openai_failure_uses_local_fallback(tmp_path: Path) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_openai(
        assistant,
        openai_settings(),
        FakeOpenAITransport(
            error=ExternalProviderError(
                "Fallo controlado.",
                error_code="network_error",
            )
        ),
    )

    record = assistant.generate_draft(
        openai_request(case_id, issue_id, run_id)
    )

    assert record.provider_mode is ProviderMode.OPENAI
    assert record.external_call is True
    assert record.fallback_used is True
    assert record.provider_name == "Simulado local"
    audit = assistant.list_provider_calls(case_id, issue_id, limit=1)[0]
    assert audit.status is ProviderCallStatus.FALLBACK
    assert audit.error_code == "network_error"


def test_openai_cost_limit_blocks_before_transport(tmp_path: Path) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    transport = FakeOpenAITransport()
    settings = openai_settings(
        max_cost_usd=0.000001,
        input_rate=100.0,
        output_rate=100.0,
    )
    configure_openai(assistant, settings, transport)

    with pytest.raises(ValueError, match="costo"):
        assistant.generate_draft(
            openai_request(
                case_id,
                issue_id,
                run_id,
                max_cost_usd=0.000001,
            )
        )

    assert transport.calls == []
    audit = assistant.list_provider_calls(case_id, issue_id, limit=1)[0]
    assert audit.error_code == "cost_limit"


def test_openai_audit_contains_no_prompt_content_or_secret(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_openai(assistant, openai_settings(), FakeOpenAITransport())

    assistant.generate_draft(openai_request(case_id, issue_id, run_id))
    audit = assistant.list_provider_calls(case_id, issue_id, limit=1)[0]
    serialized = audit.model_dump_json()

    assert "system_instruction" not in serialized
    assert "response_text" not in serialized
    assert "openai-test-secret" not in serialized
    assert "Compradora A" not in serialized
