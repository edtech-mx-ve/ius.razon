from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ius_razon.config import AppConfig
from ius_razon.domain.argumentation_models import (
    ArgumentPosition,
    ArgumentRelationCreate,
    ArgumentRelationType,
    ArgumentScenarioCreate,
    ArgumentScenarioUpdate,
    ArgumentStatus,
    LegalArgumentCreate,
    ScenarioStatus,
)
from ius_razon.domain.enums import (
    CaseStatus,
    ConfidentialityLevel,
    LegalIssueStatus,
)
from ius_razon.domain.models import CaseCreate, LegalIssueCreate
from ius_razon.domain.reasoning_models import AssertionValue
from ius_razon.persistence.argumentation_repository import (
    ArgumentationConflictError,
    ArgumentationRepository,
)
from ius_razon.persistence.mutation_backup import SQLiteMutationBackup
from ius_razon.persistence.reasoning_repository import ReasoningRepository
from ius_razon.persistence.sqlite_repository import SQLiteRepository
from ius_razon.services.argumentation_service import ArgumentationService
from ius_razon.services.case_service import CaseService


def build_services(tmp_path: Path) -> tuple[CaseService, ArgumentationService]:
    data_dir = tmp_path / "data"
    config = AppConfig(
        project_root=tmp_path,
        data_dir=data_dir,
        db_path=data_dir / "test.db",
        upload_dir=data_dir / "uploads",
        log_dir=data_dir / "logs",
        max_upload_bytes=1024 * 1024,
        log_level="INFO",
    )
    config.upload_dir.mkdir(parents=True)
    config.log_dir.mkdir(parents=True)
    case_repository = SQLiteRepository(config.db_path)
    case_repository.initialize()
    reasoning_repository = ReasoningRepository(config.db_path)
    reasoning_repository.initialize()
    argumentation_repository = ArgumentationRepository(config.db_path)
    argumentation_repository.initialize()
    return (
        CaseService(
            case_repository,
            config,
            mutation_backup=SQLiteMutationBackup(
                config.db_path,
                config.data_dir / "backups",
                keep=20,
            ),
        ),
        ArgumentationService(
            argumentation_repository,
            mutation_backup=SQLiteMutationBackup(
                argumentation_repository.db_path,
                data_dir / "backups",
                keep=20,
            ),
        ),
    )


def create_case_issue(
    case_service: CaseService,
) -> tuple[str, str]:
    case = case_service.create_case(
        CaseCreate(
            title="Caso para escenarios",
            description="Expediente sintético para validar el grafo argumental.",
            matter="Mercantil",
            jurisdiction="México",
            opened_on=date.today(),
            status=CaseStatus.OPEN,
            confidentiality=ConfidentialityLevel.PUBLIC_DEMO,
        )
    )
    issue = case_service.add_legal_issue(
        LegalIssueCreate(
            case_id=case.id,
            title="Problema argumental",
            question="¿Qué estructura argumental resulta aplicable?",
            description="Problema sintético para escenarios alternativos.",
            status=LegalIssueStatus.OPEN,
        )
    )
    return case.id, issue.id


def add_argument(
    service: ArgumentationService,
    *,
    case_id: str,
    issue_id: str,
    title: str,
    position: ArgumentPosition,
    value: AssertionValue,
) -> object:
    return service.add_argument(
        LegalArgumentCreate(
            case_id=case_id,
            issue_id=issue_id,
            title=title,
            position=position,
            thesis_key="incumplimiento",
            thesis_statement="Tesis controlada para el escenario.",
            thesis_value=value,
            claim="La pretensión argumental se formula para la prueba.",
            reasoning=(
                "El razonamiento se registra de forma controlada para validar "
                "el grafo y los escenarios alternativos."
            ),
            status=ArgumentStatus.SUPPORTED,
            fact_codes=[],
            evidence_codes=[],
            source_codes=[],
            rule_codes=[],
            assertion_codes=[],
        )
    )


def create_three_arguments(
    service: ArgumentationService,
    case_id: str,
    issue_id: str,
) -> tuple[object, object, object]:
    favorable = add_argument(
        service,
        case_id=case_id,
        issue_id=issue_id,
        title="Argumento favorable principal",
        position=ArgumentPosition.FAVORABLE,
        value=AssertionValue.TRUE,
    )
    adverse = add_argument(
        service,
        case_id=case_id,
        issue_id=issue_id,
        title="Objeción adversa principal",
        position=ArgumentPosition.ADVERSE,
        value=AssertionValue.FALSE,
    )
    reply = add_argument(
        service,
        case_id=case_id,
        issue_id=issue_id,
        title="Réplica favorable complementaria",
        position=ArgumentPosition.FAVORABLE,
        value=AssertionValue.TRUE,
    )
    return favorable, adverse, reply


def test_scenario_is_created_with_persistent_code(tmp_path: Path) -> None:
    case_service, service = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    favorable, adverse, _ = create_three_arguments(
        service,
        case_id,
        issue_id,
    )

    scenario = service.add_scenario(
        ArgumentScenarioCreate(
            case_id=case_id,
            issue_id=issue_id,
            name="Escenario base contradictorio",
            description="Incluye la tesis favorable y la objeción principal.",
            status=ScenarioStatus.ACTIVE,
            argument_ids=[favorable.id, adverse.id],
            assumptions=["No se incorporan hechos posteriores."],
        )
    )

    assert scenario.code == "SCN-001"
    assert scenario.argument_ids == [favorable.id, adverse.id]
    assert service.list_scenarios(case_id, issue_id)[0].code == "SCN-001"


def test_cross_issue_argument_is_rejected_from_scenario(tmp_path: Path) -> None:
    case_service, service = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    favorable, _, _ = create_three_arguments(service, case_id, issue_id)
    second_issue = case_service.add_legal_issue(
        LegalIssueCreate(
            case_id=case_id,
            title="Problema separado",
            question="¿Existe otra consecuencia?",
            description="Problema distinto para validar aislamiento.",
            status=LegalIssueStatus.OPEN,
        )
    )
    foreign = add_argument(
        service,
        case_id=case_id,
        issue_id=second_issue.id,
        title="Argumento de otro problema",
        position=ArgumentPosition.NEUTRAL,
        value=AssertionValue.TRUE,
    )

    with pytest.raises(ValueError, match="no pertenecen"):
        service.add_scenario(
            ArgumentScenarioCreate(
                case_id=case_id,
                issue_id=issue_id,
                name="Escenario inválido cruzado",
                description="Intenta mezclar argumentos de dos problemas.",
                argument_ids=[favorable.id, foreign.id],
            )
        )


def test_scenario_graph_keeps_only_internal_relations(tmp_path: Path) -> None:
    case_service, service = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    favorable, adverse, reply = create_three_arguments(
        service,
        case_id,
        issue_id,
    )
    attack = service.add_relation(
        ArgumentRelationCreate(
            case_id=case_id,
            issue_id=issue_id,
            source_argument_id=adverse.id,
            target_argument_id=favorable.id,
            relation_type=ArgumentRelationType.ATTACKS,
            rationale="La objeción ataca la tesis favorable.",
        )
    )
    service.add_relation(
        ArgumentRelationCreate(
            case_id=case_id,
            issue_id=issue_id,
            source_argument_id=reply.id,
            target_argument_id=adverse.id,
            relation_type=ArgumentRelationType.REPLIES,
            rationale="La réplica responde a la objeción.",
        )
    )
    scenario = service.add_scenario(
        ArgumentScenarioCreate(
            case_id=case_id,
            issue_id=issue_id,
            name="Escenario sin réplica",
            description="Excluye la réplica para revisar la objeción pendiente.",
            argument_ids=[favorable.id, adverse.id],
        )
    )

    graph = service.build_graph(case_id, issue_id, scenario.id)

    assert [node.code for node in graph.nodes] == ["ARG-001", "ARG-002"]
    assert [edge.code for edge in graph.edges] == [attack.code]
    assert graph.unresolved_objection_codes == ["ARG-002"]
    assert graph.summary["component_count"] == 1


def test_reply_resolves_objection_in_full_graph(tmp_path: Path) -> None:
    case_service, service = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    favorable, adverse, reply = create_three_arguments(
        service,
        case_id,
        issue_id,
    )
    service.add_relation(
        ArgumentRelationCreate(
            case_id=case_id,
            issue_id=issue_id,
            source_argument_id=adverse.id,
            target_argument_id=favorable.id,
            relation_type=ArgumentRelationType.ATTACKS,
            rationale="La objeción ataca la tesis favorable.",
        )
    )
    service.add_relation(
        ArgumentRelationCreate(
            case_id=case_id,
            issue_id=issue_id,
            source_argument_id=reply.id,
            target_argument_id=adverse.id,
            relation_type=ArgumentRelationType.REPLIES,
            rationale="La réplica responde a la objeción.",
        )
    )

    graph = service.build_graph(case_id, issue_id)

    assert graph.unresolved_objection_codes == []
    assert graph.summary["reply_edge_count"] == 1
    assert graph.summary["component_count"] == 1


def test_scenario_comparison_reports_added_and_removed_items(
    tmp_path: Path,
) -> None:
    case_service, service = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    favorable, adverse, reply = create_three_arguments(
        service,
        case_id,
        issue_id,
    )
    service.add_relation(
        ArgumentRelationCreate(
            case_id=case_id,
            issue_id=issue_id,
            source_argument_id=adverse.id,
            target_argument_id=favorable.id,
            relation_type=ArgumentRelationType.ATTACKS,
            rationale="La objeción ataca la tesis favorable.",
        )
    )
    service.add_relation(
        ArgumentRelationCreate(
            case_id=case_id,
            issue_id=issue_id,
            source_argument_id=reply.id,
            target_argument_id=adverse.id,
            relation_type=ArgumentRelationType.REPLIES,
            rationale="La réplica responde a la objeción.",
        )
    )
    scenario = service.add_scenario(
        ArgumentScenarioCreate(
            case_id=case_id,
            issue_id=issue_id,
            name="Escenario reducido favorable",
            description="Mantiene únicamente la tesis favorable principal.",
            argument_ids=[favorable.id],
        )
    )

    comparison = service.compare_scenarios(
        case_id,
        issue_id,
        scenario.id,
        None,
    )

    assert comparison.added_argument_codes == ["ARG-002", "ARG-003"]
    assert comparison.removed_argument_codes == []
    assert comparison.added_relation_codes == ["REL-001", "REL-002"]
    assert comparison.metric_deltas["node_count"] == 2


def test_graph_exports_are_deterministic_and_dot_is_safe(tmp_path: Path) -> None:
    case_service, service = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    favorable = add_argument(
        service,
        case_id=case_id,
        issue_id=issue_id,
        title='Argumento "favorable" principal',
        position=ArgumentPosition.FAVORABLE,
        value=AssertionValue.TRUE,
    )

    first = service.build_graph(case_id, issue_id)
    second = service.build_graph(case_id, issue_id)

    assert first.input_hash == second.input_hash
    assert service.export_graph_json(case_id, issue_id) == service.export_graph_json(
        case_id,
        issue_id,
    )
    parsed = json.loads(service.export_graph_json(case_id, issue_id))
    assert parsed["graph"]["nodes"][0]["code"] == favorable.code
    assert r'\"favorable\"' in service.export_graph_dot(case_id, issue_id)
    assert "Grafo argumental" in service.export_graph_markdown(
        case_id,
        issue_id,
    )


def test_update_preserves_code_and_delete_requires_confirmation(
    tmp_path: Path,
) -> None:
    case_service, service = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    favorable, adverse, _ = create_three_arguments(
        service,
        case_id,
        issue_id,
    )
    scenario = service.add_scenario(
        ArgumentScenarioCreate(
            case_id=case_id,
            issue_id=issue_id,
            name="Escenario editable inicial",
            description="Escenario creado para probar edición y eliminación.",
            argument_ids=[favorable.id],
        )
    )

    updated = service.update_scenario(
        scenario.id,
        ArgumentScenarioUpdate(
            name="Escenario editable actualizado",
            description="El escenario conserva su código después de editarse.",
            status=ScenarioStatus.ACTIVE,
            argument_ids=[favorable.id, adverse.id],
            assumptions=["Se incorpora la objeción principal."],
        ),
    )

    assert updated.code == scenario.code
    assert len(updated.argument_ids) == 2
    with pytest.raises(ValueError, match=scenario.code):
        service.delete_scenario(scenario.id, confirmation="SCN-999")

    service.delete_scenario(scenario.id, confirmation=scenario.code)
    assert service.list_scenarios(case_id, issue_id) == []


def test_argument_in_scenario_cannot_be_deleted(tmp_path: Path) -> None:
    case_service, service = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    favorable = add_argument(
        service,
        case_id=case_id,
        issue_id=issue_id,
        title="Argumento protegido por escenario",
        position=ArgumentPosition.FAVORABLE,
        value=AssertionValue.TRUE,
    )
    service.add_scenario(
        ArgumentScenarioCreate(
            case_id=case_id,
            issue_id=issue_id,
            name="Escenario que protege argumento",
            description="Mantiene una referencia al argumento seleccionado.",
            argument_ids=[favorable.id],
        )
    )

    with pytest.raises(ArgumentationConflictError, match="escenarios"):
        service.delete_argument(
            favorable.id,
            confirmation=favorable.code,
        )
