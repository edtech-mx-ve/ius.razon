from __future__ import annotations

from pathlib import Path

import pytest
from test_sprint_43 import assistant_request, build_assistant
from test_sprint_451_ollama import (
    FakeOllamaTransport,
    ollama_settings,
    provider_request,
)

from ius_razon.domain.llm_models import ProviderMode
from ius_razon.security.llm_guardrails import (
    normalize_context_control_statements,
)
from ius_razon.security.llm_ollama_config import (
    OllamaProviderConfigurationError,
    OllamaProviderSettings,
)
from ius_razon.services.llm_ollama_health import (
    OllamaDiagnosticError,
    OllamaHealthProbe,
)
from ius_razon.services.llm_provider import (
    ExternalProviderError,
    OllamaLocalProvider,
)


class FakeHealthTransport:
    """Transporte GET local inyectable que nunca abre sockets."""

    def __init__(
        self,
        *,
        models: tuple[str, ...] = ("qwen3:1.7b",),
        version: str = "0.32.6",
        error: OllamaDiagnosticError | None = None,
    ) -> None:
        self.models = models
        self.version = version
        self.error = error
        self.calls: list[dict[str, object]] = []

    def get_json(
        self,
        endpoint: str,
        *,
        timeout_seconds: int,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "endpoint": endpoint,
                "timeout_seconds": timeout_seconds,
            }
        )
        if self.error is not None:
            raise self.error
        if endpoint.endswith("/api/version"):
            return {"version": self.version}
        if endpoint.endswith("/api/tags"):
            return {
                "models": [
                    {
                        "name": model,
                        "model": model,
                        "size": 1_000,
                    }
                    for model in self.models
                ]
            }
        raise AssertionError(f"Endpoint inesperado: {endpoint}")


def test_settings_expose_health_endpoints_and_allowlist() -> None:
    settings = OllamaProviderSettings.from_env({})

    assert settings.version_endpoint.endswith("/api/version")
    assert settings.tags_endpoint.endswith("/api/tags")
    assert settings.allowed_models == ("qwen3:1.7b",)
    assert settings.safe_summary()["cloud_models_blocked"] is True


def test_settings_parse_multiple_allowed_local_models() -> None:
    settings = OllamaProviderSettings.from_env(
        {
            "IUS_RAZON_OLLAMA_MODEL": "qwen3:4b",
            "IUS_RAZON_OLLAMA_ALLOWED_MODELS": (
                "qwen3:1.7b,qwen3:4b"
            ),
        }
    )

    assert settings.model == "qwen3:4b"
    assert settings.allowed_models == ("qwen3:1.7b", "qwen3:4b")


def test_settings_reject_model_outside_allowlist() -> None:
    with pytest.raises(
        OllamaProviderConfigurationError,
        match="no pertenece",
    ):
        OllamaProviderSettings.from_env(
            {
                "IUS_RAZON_OLLAMA_MODEL": "qwen3:4b",
                "IUS_RAZON_OLLAMA_ALLOWED_MODELS": "qwen3:1.7b",
            }
        )


@pytest.mark.parametrize(
    "model",
    [
        "gpt-oss:120b-cloud",
        "modelo:cloud",
        "cloud/modelo",
    ],
)
def test_settings_reject_cloud_model_names(model: str) -> None:
    with pytest.raises(
        OllamaProviderConfigurationError,
        match="modelos cloud",
    ):
        OllamaProviderSettings.from_env(
            {
                "IUS_RAZON_OLLAMA_MODEL": model,
                "IUS_RAZON_OLLAMA_ALLOWED_MODELS": model,
            }
        )


def test_health_probe_reports_ready_local_model() -> None:
    settings = ollama_settings()
    transport = FakeHealthTransport()

    report = OllamaHealthProbe(
        settings,
        transport=transport,
    ).check()

    assert report.ready is True
    assert report.service_available is True
    assert report.model_installed is True
    assert report.version == "0.32.6"
    assert report.installed_models == ("qwen3:1.7b",)
    assert len(transport.calls) == 2


def test_health_probe_reports_missing_model() -> None:
    settings = ollama_settings()
    report = OllamaHealthProbe(
        settings,
        transport=FakeHealthTransport(models=("qwen3:4b",)),
    ).check()

    assert report.ready is False
    assert report.service_available is True
    assert report.model_installed is False
    assert report.error_code == "ollama_model_not_installed"


def test_health_probe_reports_safe_unavailable_error() -> None:
    settings = ollama_settings()
    report = OllamaHealthProbe(
        settings,
        transport=FakeHealthTransport(
            error=OllamaDiagnosticError(
                "Servicio local no disponible.",
                error_code="ollama_unavailable",
            )
        ),
    ).check()

    assert report.ready is False
    assert report.service_available is False
    assert report.error_code == "ollama_unavailable"
    assert "Servicio local" in report.message


def test_provider_rejects_incomplete_response() -> None:
    provider = OllamaLocalProvider(
        ollama_settings(),
        transport=FakeOllamaTransport(
            response={
                "message": {
                    "role": "assistant",
                    "content": "Texto [H-001].",
                },
                "done": False,
            }
        ),
    )

    with pytest.raises(
        ExternalProviderError,
        match="respuesta incompleta",
    ):
        provider.generate(provider_request())


def test_provider_requests_control_prefix_for_context_absence() -> None:
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
    assert "Control de contexto:" in messages[1]["content"]


def test_normalizer_marks_uncited_context_absence() -> None:
    original = (
        "## Resumen\n"
        "- El pago fue acreditado [P-001].\n"
        "No se proporcionó una conclusión de inferencia."
    )

    normalized = normalize_context_control_statements(original)

    assert (
        "Control de contexto: no se proporcionó una conclusión de inferencia."
        in normalized
    )


def test_normalizer_does_not_exempt_substantive_negative_claim() -> None:
    original = "No se acreditó el incumplimiento."

    assert normalize_context_control_statements(original) == original


def test_service_normalizes_ollama_absence_before_evaluation(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    settings = ollama_settings()
    assistant._ollama_settings = settings
    assistant._ollama_health_probe = OllamaHealthProbe(
        settings,
        transport=FakeHealthTransport(),
    )
    assistant._ollama_provider = OllamaLocalProvider(
        settings,
        transport=FakeOllamaTransport(
            response={
                "model": "qwen3:1.7b",
                "created_at": "2026-08-06T11:00:00Z",
                "message": {
                    "role": "assistant",
                    "content": (
                        "## Resumen\n"
                        "Pago acreditado [P-001].\n"
                        "No se proporcionó una conclusión de inferencia."
                    ),
                },
                "done": True,
                "prompt_eval_count": 100,
                "eval_count": 30,
            }
        ),
    )
    request = assistant_request(case_id, issue_id, run_id).model_copy(
        update={
            "provider_mode": ProviderMode.OLLAMA,
            "selected_codes": ["P-001"],
            "max_input_tokens": 4096,
            "max_output_tokens": 128,
            "max_cost_usd": 0.0,
            "timeout_seconds": 60,
            "max_retries": 0,
            "allow_fallback": True,
        }
    )

    draft = assistant.generate_draft(request)

    assert draft.citation_coverage == 1.0
    assert draft.unsupported_claims == []
    assert "Control de contexto:" in draft.response_text


def test_service_uses_fallback_when_health_check_fails(
    tmp_path: Path,
) -> None:
    assistant, _, _, case_id, issue_id, run_id = build_assistant(tmp_path)
    settings = ollama_settings()
    provider_transport = FakeOllamaTransport()
    assistant._ollama_settings = settings
    assistant._ollama_health_probe = OllamaHealthProbe(
        settings,
        transport=FakeHealthTransport(
            error=OllamaDiagnosticError(
                "Ollama detenido.",
                error_code="ollama_unavailable",
            )
        ),
    )
    assistant._ollama_provider = OllamaLocalProvider(
        settings,
        transport=provider_transport,
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
    assert draft.fallback_reason == "ollama_unavailable"
    assert draft.provider_name == "Simulado local"
    assert provider_transport.calls == []


def test_active_app_wires_ollama_health_probe() -> None:
    app_source = Path("app.py").read_text(encoding="utf-8")
    view_source = Path(
        "src/ius_razon/ui/llm_assistant_view.py"
    ).read_text(encoding="utf-8")

    assert "OllamaHealthProbe" in app_source
    assert "ollama_health_probe=ollama_health_probe" in app_source
    assert "check_ollama_health" in view_source


def test_diagnostic_script_is_present() -> None:
    source = Path("scripts/diagnose_ollama.py").read_text(
        encoding="utf-8"
    )

    assert "OllamaHealthProbe" in source
    assert "OPENAI_API_KEY" not in source
