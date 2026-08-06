from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from test_sprint_43 import assistant_request, build_assistant

from ius_razon.domain.llm_models import (
    AssistantRequest,
    AssistantTask,
    ContextCategory,
    ContextItem,
    DraftStatus,
    ExternalConsent,
    ProviderCallStatus,
    ProviderMode,
    ProviderRequest,
)
from ius_razon.security.llm_external_test import ControlledExternalTestPolicy
from ius_razon.services.llm_assistant_service import LLMAssistantService
from ius_razon.services.llm_provider import ControlledExternalTestProvider


def configure_integration_test(
    assistant: LLMAssistantService,
) -> None:
    assistant._integration_test_provider = ControlledExternalTestProvider()
    assistant._integration_test_policy = ControlledExternalTestPolicy()


def controlled_request(
    case_id: str,
    issue_id: str,
    run_id: str,
    **updates: object,
) -> AssistantRequest:
    request = assistant_request(case_id, issue_id, run_id)
    values: dict[str, object] = {
        "provider_mode": ProviderMode.EXTERNAL_TEST,
        "external_consent": ExternalConsent(
            reviewed_context=True,
            authorized_external_call=True,
            accepted_cost_limit=True,
        ),
        "anonymize_parties": True,
        "max_input_tokens": 2048,
        "max_output_tokens": 256,
        "max_cost_usd": 0.01,
        "timeout_seconds": 15,
        "max_retries": 0,
        "allow_fallback": True,
        "confirm_single_call": True,
    }
    values.update(updates)
    return request.model_copy(update=values)


def provider_request() -> ProviderRequest:
    return ProviderRequest(
        task=AssistantTask.CASE_SUMMARY,
        context_items=[
            ContextItem(
                code="PJ-001",
                category=ContextCategory.ISSUE,
                title="Incumplimiento",
                content="Revisar el pago y la falta de entrega.",
            )
        ],
        allowed_codes=["PJ-001"],
        max_output_chars=2000,
        max_output_tokens=256,
        max_retries=0,
        timeout_seconds=15,
        max_cost_usd=0.01,
        system_instruction=(
            "Usa únicamente el contexto y conserva referencias internas."
        ),
    )


def test_controlled_profile_has_safe_fixed_limits() -> None:
    summary = ControlledExternalTestPolicy().safe_summary()

    assert summary["network_enabled"] is False
    assert summary["api_key_required"] is False
    assert summary["max_output_tokens"] == 256
    assert summary["max_retries"] == 0
    assert summary["fallback_required"] is True


def test_integration_provider_is_deterministic_and_offline() -> None:
    provider = ControlledExternalTestProvider()

    first = provider.generate(provider_request())
    second = provider.generate(provider_request())

    assert first.text == second.text
    assert first.request_id == second.request_id
    assert first.external_call is False
    assert first.estimated_cost_usd == 0.0
    assert first.provider_name == "Externo falso de integración"
    assert "[PJ-001]" in first.text


def test_controlled_mode_requires_anonymization() -> None:
    with pytest.raises(ValidationError):
        AssistantRequest(
            case_id="case",
            issue_id="issue",
            task=AssistantTask.CASE_SUMMARY,
            selected_categories=[ContextCategory.ISSUE],
            provider_mode=ProviderMode.EXTERNAL_TEST,
            anonymize_parties=False,
        )


def test_controlled_test_requires_complete_consent(tmp_path: Path) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_integration_test(assistant)
    request = controlled_request(
        case_id,
        issue_id,
        run_id,
        external_consent=ExternalConsent(),
    )

    with pytest.raises(ValueError, match="tres confirmaciones"):
        assistant.generate_draft(request)

    audit = assistant.list_provider_calls(case_id, issue_id, limit=1)[0]
    assert audit.status is ProviderCallStatus.BLOCKED
    assert audit.error_code == "consent_incomplete"


def test_controlled_test_requires_single_call_confirmation(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_integration_test(assistant)
    request = controlled_request(
        case_id,
        issue_id,
        run_id,
        confirm_single_call=False,
    )

    with pytest.raises(ValueError, match="una sola invocación"):
        assistant.generate_draft(request)

    audit = assistant.list_provider_calls(case_id, issue_id, limit=1)[0]
    assert audit.error_code == "single_call_not_confirmed"


def test_controlled_test_rejects_retries(tmp_path: Path) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_integration_test(assistant)
    request = controlled_request(
        case_id,
        issue_id,
        run_id,
        max_retries=1,
    )

    with pytest.raises(ValueError, match="cero reintentos"):
        assistant.generate_draft(request)


def test_controlled_test_rejects_excess_output_tokens(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_integration_test(assistant)
    request = controlled_request(
        case_id,
        issue_id,
        run_id,
        max_output_tokens=512,
    )

    with pytest.raises(ValueError, match="límite de la prueba"):
        assistant.generate_draft(request)


def test_controlled_test_rejects_excess_timeout(tmp_path: Path) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_integration_test(assistant)
    request = controlled_request(
        case_id,
        issue_id,
        run_id,
        timeout_seconds=30,
    )

    with pytest.raises(ValueError, match="tiempo máximo"):
        assistant.generate_draft(request)


def test_controlled_test_requires_local_fallback(tmp_path: Path) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_integration_test(assistant)
    request = controlled_request(
        case_id,
        issue_id,
        run_id,
        allow_fallback=False,
    )

    with pytest.raises(ValueError, match="fallback local"):
        assistant.generate_draft(request)


def test_controlled_test_generates_audited_unapproved_draft(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_integration_test(assistant)

    record = assistant.generate_draft(
        controlled_request(case_id, issue_id, run_id)
    )

    assert record.status is DraftStatus.GENERATED
    assert record.provider_mode is ProviderMode.EXTERNAL_TEST
    assert record.external_call is False
    assert record.fallback_used is False
    assert record.citation_coverage == 1.0
    assert record.invalid_reference_codes == []

    audit = assistant.list_provider_calls(case_id, issue_id, limit=1)[0]
    assert audit.status is ProviderCallStatus.SUCCEEDED
    assert audit.provider_mode is ProviderMode.EXTERNAL_TEST
    assert audit.external_call is False
    assert audit.fallback_used is False
    assert audit.draft_id == record.id


def test_controlled_test_does_not_auto_approve(tmp_path: Path) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_integration_test(assistant)

    record = assistant.generate_draft(
        controlled_request(case_id, issue_id, run_id)
    )
    stored = assistant.get_draft(record.id)

    assert stored.status is DraftStatus.GENERATED
    assert stored.reviewed_at is None
    assert stored.edited_text is None


def test_controlled_audit_contains_no_prompt_or_secret(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    configure_integration_test(assistant)

    assistant.generate_draft(
        controlled_request(case_id, issue_id, run_id)
    )
    audit = assistant.list_provider_calls(case_id, issue_id, limit=1)[0]
    serialized = audit.model_dump_json()

    assert "system_instruction" not in serialized
    assert "response_text" not in serialized
    assert "api_key" not in serialized
    assert "Compradora A" not in serialized
