from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from ius_razon.domain.llm_models import (
    AssistantDraftCreate,
    AssistantTask,
    ContextCategory,
    ContextItem,
    DraftStatus,
    ProviderCallAuditCreate,
    ProviderCallStatus,
    ProviderMode,
)
from ius_razon.domain.models import CaseCreate, LegalIssueCreate
from ius_razon.persistence.postgres_llm_repository import (
    LLMReviewConflictError,
    PostgresLLMRepository,
)
from ius_razon.persistence.postgres_repository import PostgresRepository
from ius_razon.persistence.postgres_runtime import load_postgres_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def cleanup(case_id: str, direct_database_url: str) -> None:
    with psycopg.connect(
        direct_database_url,
        connect_timeout=20,
    ) as connection:
        connection.execute(
            "DELETE FROM cases WHERE id = %s",
            (case_id,),
        )
        connection.commit()


def run_smoke() -> None:
    settings = load_postgres_settings(PROJECT_ROOT)
    core = PostgresRepository(settings.database_url)
    repository = PostgresLLMRepository(settings.database_url)

    core.initialize()
    repository.initialize()

    case_id: str | None = None
    try:
        case = core.create_case(
            CaseCreate(
                title="SMOKE LLM PostgreSQL Sprint 5.4",
                description=(
                    "Expediente sintético temporal para validar persistencia "
                    "LLM en Neon."
                ),
                matter="Mercantil",
                jurisdiction="México",
            )
        )
        case_id = case.id

        issue = core.add_legal_issue(
            LegalIssueCreate(
                case_id=case.id,
                title="Problema sintético LLM",
                question="¿La persistencia LLM conserva revisión y auditoría?",
            )
        )

        context = ContextItem(
            code=issue.code,
            category=ContextCategory.ISSUE,
            title="Problema jurídico sintético",
            content=(
                "Contexto sintético controlado para validar únicamente "
                "persistencia PostgreSQL."
            ),
            source_id=issue.id,
        )

        input_hash = "a" * 64
        output_hash = "b" * 64

        provider_call = repository.add_provider_call(
            ProviderCallAuditCreate(
                case_id=case.id,
                issue_id=issue.id,
                provider_mode=ProviderMode.SIMULATED,
                provider_name="Proveedor sintético",
                model_name="modelo-sintetico",
                status=ProviderCallStatus.SUCCEEDED,
                selected_codes=[issue.code],
                input_hash=input_hash,
                output_hash=output_hash,
                external_call=False,
                fallback_used=False,
                input_tokens=120,
                output_tokens=45,
                estimated_cost_usd=0.0,
            )
        )
        assert provider_call.draft_id is None

        first = repository.add_draft(
            AssistantDraftCreate(
                case_id=case.id,
                issue_id=issue.id,
                task=AssistantTask.CASE_SUMMARY,
                provider_name="Proveedor sintético",
                model_name="modelo-sintetico",
                request_snapshot={
                    "task": AssistantTask.CASE_SUMMARY.value,
                    "selected_codes": [issue.code],
                },
                context_items=[context],
                response_text=(
                    f"Resumen sintético persistido con referencia [{issue.code}]."
                ),
                reference_codes=[issue.code],
                invalid_reference_codes=[],
                unsupported_claims=[],
                risk_flags=[],
                citation_coverage=1.0,
                input_hash=input_hash,
                output_hash=output_hash,
                provider_mode=ProviderMode.SIMULATED,
                external_call=False,
                fallback_used=False,
                input_tokens=120,
                output_tokens=45,
                estimated_cost_usd=0.0,
            )
        )
        assert first.code == "IA-001"
        assert first.status is DraftStatus.GENERATED

        linked = repository.link_provider_call_to_draft(
            provider_call.id,
            first.id,
        )
        assert linked.draft_id == first.id

        reviewed = repository.review_draft(
            first.id,
            status=DraftStatus.APPROVED,
            edited_text=(
                f"Resumen sintético revisado con referencia [{issue.code}]."
            ),
            reviewer_note="Revisión humana sintética.",
            reference_codes=[issue.code],
            invalid_reference_codes=[],
            unsupported_claims=[],
            citation_coverage=1.0,
            output_hash="c" * 64,
        )
        assert reviewed.status is DraftStatus.APPROVED
        assert reviewed.reviewed_at is not None

        try:
            repository.review_draft(
                first.id,
                status=DraftStatus.REJECTED,
                edited_text=None,
                reviewer_note="Segunda revisión que debe rechazarse.",
                reference_codes=[issue.code],
                invalid_reference_codes=[],
                unsupported_claims=[],
                citation_coverage=1.0,
                output_hash="d" * 64,
            )
        except LLMReviewConflictError:
            pass
        else:
            raise AssertionError(
                "No se protegió un borrador ya revisado."
            )

        second = repository.add_draft(
            AssistantDraftCreate(
                case_id=case.id,
                issue_id=issue.id,
                task=AssistantTask.MISSING_INFORMATION,
                provider_name="Proveedor sintético",
                model_name="modelo-sintetico",
                request_snapshot={
                    "task": AssistantTask.MISSING_INFORMATION.value,
                    "selected_codes": [issue.code],
                },
                context_items=[context],
                response_text=(
                    f"Información sintética faltante [{issue.code}]."
                ),
                reference_codes=[issue.code],
                invalid_reference_codes=[],
                unsupported_claims=[],
                risk_flags=[],
                citation_coverage=1.0,
                input_hash="e" * 64,
                output_hash="f" * 64,
                provider_mode=ProviderMode.SIMULATED,
                external_call=False,
                fallback_used=True,
                fallback_reason="Fallback sintético controlado.",
                input_tokens=90,
                output_tokens=30,
                estimated_cost_usd=0.0,
            )
        )
        assert second.code == "IA-002"

        rejected = repository.review_draft(
            second.id,
            status=DraftStatus.REJECTED,
            edited_text=None,
            reviewer_note="Rechazo humano sintético.",
            reference_codes=[issue.code],
            invalid_reference_codes=[],
            unsupported_claims=[],
            citation_coverage=1.0,
            output_hash=second.output_hash,
        )
        assert rejected.status is DraftStatus.REJECTED

        drafts = repository.list_drafts(case.id, issue.id)
        assert [item.code for item in drafts] == ["IA-002", "IA-001"]

        calls = repository.list_provider_calls(case.id, issue.id)
        assert len(calls) == 1
        assert calls[0].draft_id == first.id
        assert calls[0].status is ProviderCallStatus.SUCCEEDED

        assert repository.get_draft(first.id).code == "IA-001"
        assert repository.get_provider_call(provider_call.id).id == provider_call.id

        print(
            "PostgresLLMRepository Neon: OK | "
            "borradores=OK | revisión=OK | conflicto=OK | "
            "auditoría=OK | vínculo=OK | códigos=OK"
        )
    finally:
        if case_id is not None:
            cleanup(case_id, settings.direct_database_url)
            print("Datos sintéticos LLM eliminados de Neon.")


def main() -> int:
    try:
        run_smoke()
    except Exception as exc:
        print(
            f"Smoke PostgresLLMRepository falló: {exc}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
