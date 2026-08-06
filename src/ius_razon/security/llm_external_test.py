from __future__ import annotations

from dataclasses import dataclass

from ius_razon.domain.llm_models import (
    AssistantRequest,
    ContextPreview,
    ProviderMode,
)


class ControlledExternalTestError(ValueError):
    """Incumplimiento del perfil seguro de prueba externa."""

    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True)
class ControlledExternalTestPolicy:
    """Límites inmutables para probar el flujo externo sin usar red."""

    max_input_tokens: int = 2048
    max_output_tokens: int = 256
    max_cost_usd: float = 0.01
    max_timeout_seconds: int = 15
    required_max_retries: int = 0
    require_fallback: bool = True

    def safe_summary(self) -> dict[str, object]:
        """Expone el perfil sin secretos ni contenido del expediente."""

        return {
            "provider_name": "Externo falso de integración",
            "model": "ius-razon-external-test-v1",
            "network_enabled": False,
            "api_key_required": False,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_cost_usd": self.max_cost_usd,
            "timeout_seconds": self.max_timeout_seconds,
            "max_retries": self.required_max_retries,
            "fallback_required": self.require_fallback,
        }

    def validate(
        self,
        request: AssistantRequest,
        preview: ContextPreview,
    ) -> None:
        """Valida consentimiento y límites antes de ejecutar una sola prueba."""

        if request.provider_mode is not ProviderMode.EXTERNAL_TEST:
            raise ControlledExternalTestError(
                "La política solo aplica al modo de prueba externa controlada.",
                error_code="invalid_test_mode",
            )
        if not request.anonymize_parties:
            raise ControlledExternalTestError(
                "La prueba controlada exige anonimización de partes.",
                error_code="anonymization_required",
            )
        consent = request.external_consent
        if consent is None or not consent.complete:
            raise ControlledExternalTestError(
                "La prueba controlada requiere las tres confirmaciones de consentimiento.",
                error_code="consent_incomplete",
            )
        if not request.confirm_single_call:
            raise ControlledExternalTestError(
                "Debes confirmar que se ejecutará una sola invocación de prueba.",
                error_code="single_call_not_confirmed",
            )
        if preview.risk_flags and not request.acknowledge_risk_flags:
            raise ControlledExternalTestError(
                "Revisa y confirma las señales de instrucciones incrustadas.",
                error_code="risk_flags_not_acknowledged",
            )
        if preview.estimated_input_tokens > min(
            request.max_input_tokens,
            self.max_input_tokens,
        ):
            raise ControlledExternalTestError(
                "El contexto supera el límite de entrada de la prueba.",
                error_code="test_input_token_limit",
            )
        if request.max_output_tokens > self.max_output_tokens:
            raise ControlledExternalTestError(
                "La salida solicitada supera el límite de la prueba.",
                error_code="test_output_token_limit",
            )
        if request.max_cost_usd > self.max_cost_usd:
            raise ControlledExternalTestError(
                "El presupuesto supera el máximo permitido para la prueba.",
                error_code="test_cost_limit",
            )
        if request.timeout_seconds > self.max_timeout_seconds:
            raise ControlledExternalTestError(
                "El tiempo máximo supera el perfil de prueba.",
                error_code="test_timeout_limit",
            )
        if request.max_retries != self.required_max_retries:
            raise ControlledExternalTestError(
                "La prueba controlada exige cero reintentos.",
                error_code="test_retries_must_be_zero",
            )
        if self.require_fallback and not request.allow_fallback:
            raise ControlledExternalTestError(
                "La prueba controlada exige fallback local.",
                error_code="test_fallback_required",
            )
