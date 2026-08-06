from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import streamlit as st

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
    EvidenceEvaluationStatus,
    EvidenceType,
    FactStatus,
    JurisprudenceAuthority,
    LegalIssueStatus,
    LegalSourceType,
    NormHierarchy,
    PartyRole,
    PartyType,
    SourceOrientation,
)
from ius_razon.domain.models import (
    CaseCreate,
    DoctrineCreate,
    EvidenceCreate,
    FactCreate,
    IssueSourceLinkCreate,
    JurisprudenceCreate,
    LegalIssueCreate,
    NormCreate,
    PartyCreate,
)
from ius_razon.domain.reasoning_models import (
    AssertionValue,
    ConditionRole,
    ReasoningAssertionCreate,
    ReasoningAssertionUpdate,
    ReasoningRuleCreate,
    ReasoningRuleUpdate,
    RuleConditionCreate,
    RuleKind,
)
from ius_razon.domain.report_models import IntegralReportRequest
from ius_razon.logging_config import configure_logging
from ius_razon.persistence.argumentation_repository import (
    ArgumentationRepository,
)
from ius_razon.persistence.backup import create_database_backup
from ius_razon.persistence.llm_repository import LLMRepository
from ius_razon.persistence.reasoning_repository import ReasoningRepository
from ius_razon.persistence.sqlite_repository import SQLiteRepository
from ius_razon.services.argumentation_service import ArgumentationService
from ius_razon.services.case_service import CaseService
from ius_razon.services.legal_report_service import LegalReportService
from ius_razon.services.llm_assistant_service import LLMAssistantService
from ius_razon.services.llm_provider import DeterministicMockProvider
from ius_razon.services.reasoning_service import ReasoningService
from ius_razon.ui.llm_assistant_view import render_llm_assistant

PROJECT_ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="IUS-Razón",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def build_services() -> tuple[
    CaseService,
    ReasoningService,
    ArgumentationService,
    LegalReportService,
    LLMAssistantService,
    AppConfig,
    Path | None,
]:
    """Construye recursos compartidos y ejecuta las migraciones aditivas."""

    config = AppConfig.from_env(PROJECT_ROOT)
    configure_logging(config)
    backup_path = create_database_backup(
        config.db_path,
        config.data_dir / "backups",
    )
    repository = SQLiteRepository(config.db_path)
    repository.initialize()
    reasoning_repository = ReasoningRepository(config.db_path)
    reasoning_repository.initialize()
    argumentation_repository = ArgumentationRepository(config.db_path)
    argumentation_repository.initialize()
    llm_repository = LLMRepository(config.db_path)
    llm_repository.initialize()
    case_service = CaseService(repository=repository, config=config)
    reasoning = ReasoningService(
        repository=reasoning_repository,
        backup_dir=config.data_dir / "backups",
    )
    argumentation = ArgumentationService(
        repository=argumentation_repository,
        backup_dir=config.data_dir / "backups",
    )
    report_service = LegalReportService(
        case_service=case_service,
        reasoning_service=reasoning,
        argumentation_service=argumentation,
    )
    llm_assistant = LLMAssistantService(
        case_service=case_service,
        reasoning_service=reasoning,
        argumentation_service=argumentation,
        provider=DeterministicMockProvider(),
        repository=llm_repository,
        backup_dir=config.data_dir / "backups",
    )
    return (
        case_service,
        reasoning,
        argumentation,
        report_service,
        llm_assistant,
        config,
        backup_path,
    )


(
    service,
    reasoning_service,
    argumentation_service,
    legal_report_service,
    llm_assistant_service,
    app_config,
    startup_backup,
) = build_services()


def enum_options(enum_type: type[Any]) -> list[str]:
    """Devuelve los valores visibles de un enumerado."""

    return [item.value for item in enum_type]


def optional_upload(uploaded: Any) -> tuple[str | None, bytes | None]:
    """Convierte una carga Streamlit en nombre y bytes opcionales."""

    if uploaded is None:
        return None, None
    return str(uploaded.name), bytes(uploaded.getvalue())


def render_notice() -> None:
    st.warning(
        "Prototipo académico. No constituye asesoría jurídica, dictamen ni predicción judicial. "
        "Toda fuente, vigencia, aplicabilidad y conclusión debe ser verificada por una persona "
        "profesional del Derecho."
    )


def create_case_form() -> None:
    with st.form("create_case_form", clear_on_submit=True):
        st.subheader("Nuevo expediente")
        title = st.text_input("Título *", max_chars=160)
        description = st.text_area("Descripción *", max_chars=4000)
        col1, col2 = st.columns(2)
        with col1:
            matter = st.selectbox("Materia", ["Civil", "Mercantil"])
            jurisdiction = st.text_input("Jurisdicción *", value="México")
            location = st.text_input("Ubicación")
            opened_on = st.date_input("Fecha de apertura", value=date.today())
        with col2:
            status = st.selectbox("Estado", enum_options(CaseStatus))
            objective = st.text_area("Objetivo del análisis", max_chars=1000)
            user_role = st.text_input("Rol del usuario", value="Analista")
            confidentiality = st.selectbox(
                "Confidencialidad",
                enum_options(ConfidentialityLevel),
            )

        if st.form_submit_button("Crear expediente", type="primary"):
            try:
                record = service.create_case(
                    CaseCreate(
                        title=title,
                        description=description,
                        matter=matter,
                        jurisdiction=jurisdiction,
                        location=location or None,
                        opened_on=opened_on,
                        status=CaseStatus(status),
                        objective=objective or None,
                        user_role=user_role or None,
                        confidentiality=ConfidentialityLevel(confidentiality),
                    )
                )
                st.success(f"Expediente creado: {record.id}")
                st.session_state["selected_case_id"] = record.id
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible crear el expediente: {exc}")


def case_selector() -> str | None:
    records = service.list_cases()
    if not records:
        st.info("Aún no existen expedientes.")
        return None

    labels = {f"{case.title} · {case.id[:8]}": case.id for case in records}
    current_id = st.session_state.get("selected_case_id")
    default_index = 0
    if current_id:
        values = list(labels.values())
        if current_id in values:
            default_index = values.index(current_id)

    label = st.selectbox("Expediente activo", list(labels), index=default_index)
    selected_id = labels[label]
    st.session_state["selected_case_id"] = selected_id
    return selected_id


def render_summary(case_id: str) -> None:
    summary = service.get_case_summary(case_id)
    case = summary.case

    st.header(case.title)
    st.caption(f"ID: {case.id}")
    row1 = st.columns(5)
    row1[0].metric("Partes", summary.party_count)
    row1[1].metric("Hechos", summary.fact_count)
    row1[2].metric("Pruebas", summary.evidence_count)
    row1[3].metric("Vínculos probatorios", summary.link_count)
    row1[4].metric("Problemas jurídicos", summary.legal_issue_count)

    row2 = st.columns(4)
    row2[0].metric("Normas", summary.norm_count)
    row2[1].metric("Jurisprudencia", summary.jurisprudence_count)
    row2[2].metric("Doctrina", summary.doctrine_count)
    row2[3].metric("Vínculos problema–fuente", summary.issue_source_link_count)

    st.markdown("### Ficha")
    st.write(
        {
            "materia": case.matter,
            "jurisdicción": case.jurisdiction,
            "ubicación": case.location,
            "fecha_apertura": case.opened_on.isoformat(),
            "estado": case.status.value,
            "confidencialidad": case.confidentiality.value,
            "objetivo": case.objective,
        }
    )
    st.markdown("### Descripción")
    st.write(case.description)

    recent = service.list_audit_events(case_id, limit=12)
    st.markdown("### Actividad reciente")
    if recent:
        st.dataframe(
            [
                {
                    "fecha": row.created_at.isoformat(timespec="seconds"),
                    "evento": row.event_type,
                    "entidad": row.entity_type,
                    "id": row.entity_id[:8] if row.entity_id else "",
                }
                for row in recent
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Sin actividad registrada.")


def render_parties(case_id: str) -> None:
    st.subheader("Partes")
    with st.form("party_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name_alias = st.text_input("Nombre o seudónimo *", max_chars=200)
            party_type = st.selectbox("Tipo de persona", enum_options(PartyType))
            legal_role = st.selectbox("Rol jurídico", enum_options(PartyRole))
        with col2:
            representation = st.text_input("Representación", max_chars=300)
            claim = st.text_area("Pretensión", max_chars=1500)
            position = st.text_area("Posición inicial", max_chars=1500)
        if st.form_submit_button("Agregar parte", type="primary"):
            try:
                service.add_party(
                    PartyCreate(
                        case_id=case_id,
                        name_alias=name_alias,
                        party_type=PartyType(party_type),
                        legal_role=PartyRole(legal_role),
                        representation=representation or None,
                        claim=claim or None,
                        position=position or None,
                    )
                )
                st.success("Parte agregada.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible agregar la parte: {exc}")

    parties = service.list_parties(case_id)
    if parties:
        st.dataframe(
            [
                {
                    "id": party.id[:8],
                    "nombre/seudónimo": party.name_alias,
                    "tipo": party.party_type.value,
                    "rol": party.legal_role.value,
                    "pretensión": party.claim or "",
                }
                for party in parties
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay partes registradas.")


def render_facts(case_id: str) -> None:
    st.subheader("Hechos")
    parties = service.list_parties(case_id)
    party_labels = {"Sin actor vinculado": None}
    party_labels.update({f"{p.name_alias} · {p.id[:8]}": p.id for p in parties})

    with st.form("fact_form", clear_on_submit=True):
        description = st.text_area("Descripción del hecho *", max_chars=3000)
        col1, col2, col3 = st.columns(3)
        with col1:
            event_date = st.date_input("Fecha del hecho", value=None)
            actor_label = st.selectbox("Actor", list(party_labels))
            action = st.text_input("Acción", max_chars=250)
        with col2:
            object_text = st.text_input("Objeto", max_chars=250)
            place = st.text_input("Lugar", max_chars=250)
            source = st.text_input("Fuente de la alegación", max_chars=500)
        with col3:
            status = st.selectbox("Estado", enum_options(FactStatus))
            controversy_level = st.slider("Nivel de controversia", 0, 5, 2)
        if st.form_submit_button("Agregar hecho", type="primary"):
            try:
                service.add_fact(
                    FactCreate(
                        case_id=case_id,
                        description=description,
                        event_date=event_date,
                        actor_party_id=party_labels[actor_label],
                        action=action or None,
                        object_text=object_text or None,
                        place=place or None,
                        source=source or None,
                        status=FactStatus(status),
                        controversy_level=controversy_level,
                    )
                )
                st.success("Hecho agregado.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible agregar el hecho: {exc}")

    facts = service.list_facts(case_id)
    if facts:
        st.dataframe(
            [
                {
                    "código": fact.code,
                    "fecha": fact.event_date.isoformat() if fact.event_date else "",
                    "descripción": fact.description,
                    "estado": fact.status.value,
                    "controversia": fact.controversy_level,
                }
                for fact in facts
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay hechos registrados.")


def render_evidence(case_id: str) -> None:
    st.subheader("Pruebas")
    parties = service.list_parties(case_id)
    party_labels = {"Sin oferente vinculado": None}
    party_labels.update({f"{p.name_alias} · {p.id[:8]}": p.id for p in parties})

    with st.form("evidence_form", clear_on_submit=True):
        description = st.text_area("Descripción de la prueba *", max_chars=3000)
        uploaded = st.file_uploader(
            "Archivo opcional",
            type=["pdf", "txt", "docx", "png", "jpg", "jpeg"],
        )
        col1, col2 = st.columns(2)
        with col1:
            evidence_type = st.selectbox("Tipo", enum_options(EvidenceType))
            origin = st.text_input("Origen", max_chars=500)
            evidence_date = st.date_input("Fecha de la prueba", value=None)
            offering_label = st.selectbox("Parte oferente", list(party_labels))
        with col2:
            integrity_statement = st.text_area(
                "Declaración de integridad",
                max_chars=1000,
            )
            objections = st.text_area("Objeciones", max_chars=1500)
            observations = st.text_area("Observaciones", max_chars=1500)
            evaluation_status = st.selectbox(
                "Estado de valoración",
                enum_options(EvidenceEvaluationStatus),
            )
        if st.form_submit_button("Agregar prueba", type="primary"):
            try:
                file_name, content = optional_upload(uploaded)
                service.add_evidence(
                    EvidenceCreate(
                        case_id=case_id,
                        evidence_type=EvidenceType(evidence_type),
                        description=description,
                        origin=origin or None,
                        evidence_date=evidence_date,
                        integrity_statement=integrity_statement or None,
                        offering_party_id=party_labels[offering_label],
                        objections=objections or None,
                        observations=observations or None,
                        evaluation_status=EvidenceEvaluationStatus(evaluation_status),
                    ),
                    original_file_name=file_name,
                    file_content=content,
                )
                st.success("Prueba agregada.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible agregar la prueba: {exc}")

    evidence = service.list_evidence(case_id)
    if evidence:
        st.dataframe(
            [
                {
                    "código": item.code,
                    "tipo": item.evidence_type.value,
                    "descripción": item.description,
                    "valoración": item.evaluation_status.value,
                    "archivo": item.original_file_name or "",
                    "sha256": (item.file_sha256 or "")[:12],
                }
                for item in evidence
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay pruebas registradas.")


def render_fact_evidence_links(case_id: str) -> None:
    st.subheader("Relación entre hechos y pruebas")
    facts = service.list_facts(case_id)
    evidence = service.list_evidence(case_id)
    if not facts or not evidence:
        st.info("Se requiere al menos un hecho y una prueba.")
        return

    fact_labels = {f"{f.code} · {f.description[:70]}": f.id for f in facts}
    evidence_labels = {f"{e.code} · {e.description[:70]}": e.id for e in evidence}

    with st.form("fact_evidence_link_form", clear_on_submit=True):
        fact_label = st.selectbox("Hecho", list(fact_labels))
        evidence_label = st.selectbox("Prueba", list(evidence_labels))
        purpose = st.text_input("Finalidad probatoria", max_chars=800)
        if st.form_submit_button("Vincular", type="primary"):
            try:
                service.link_fact_evidence(
                    case_id=case_id,
                    fact_id=fact_labels[fact_label],
                    evidence_id=evidence_labels[evidence_label],
                    purpose=purpose or None,
                )
                st.success("Vínculo creado o actualizado.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible crear el vínculo: {exc}")

    links = service.list_fact_evidence_links(case_id)
    st.dataframe(
        [
            {
                "hecho": link.fact_code,
                "prueba": link.evidence_code,
                "finalidad": link.purpose or "",
            }
            for link in links
        ],
        width="stretch",
        hide_index=True,
    )


def render_legal_issues(case_id: str) -> None:
    st.subheader("Problemas jurídicos")
    st.caption(
        "Formula preguntas que conecten los hechos controvertidos con las fuentes jurídicas."
    )
    with st.form("legal_issue_form", clear_on_submit=True):
        title = st.text_input("Título *", max_chars=240)
        question = st.text_area(
            "Pregunta jurídica *",
            max_chars=1500,
            placeholder="¿La obligación de entrega era exigible en la fecha pactada?",
        )
        description = st.text_area("Contexto y delimitación", max_chars=3000)
        status = st.selectbox("Estado", enum_options(LegalIssueStatus))
        if st.form_submit_button("Agregar problema jurídico", type="primary"):
            try:
                service.add_legal_issue(
                    LegalIssueCreate(
                        case_id=case_id,
                        title=title,
                        question=question,
                        description=description or None,
                        status=LegalIssueStatus(status),
                    )
                )
                st.success("Problema jurídico agregado.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible agregar el problema jurídico: {exc}")

    issues = service.list_legal_issues(case_id)
    if issues:
        st.dataframe(
            [
                {
                    "código": issue.code,
                    "título": issue.title,
                    "pregunta": issue.question,
                    "estado": issue.status.value,
                }
                for issue in issues
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay problemas jurídicos registrados.")


def render_norms(case_id: str) -> None:
    st.subheader("Normas")
    st.caption("Registra la versión y vigencia; la aplicación no las verifica automáticamente.")
    case = service.get_case_summary(case_id).case
    with st.form("norm_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            jurisdiction = st.text_input("Jurisdicción *", value=case.jurisdiction)
            matter = st.text_input("Materia *", value=case.matter)
            instrument = st.text_input("Ordenamiento o instrumento *", max_chars=300)
            article = st.text_input("Artículo o disposición *", max_chars=120)
            hierarchy = st.selectbox("Jerarquía", enum_options(NormHierarchy))
        with col2:
            publication_date = st.date_input("Fecha de publicación", value=None)
            valid_from = st.date_input("Inicio de vigencia", value=None)
            valid_to = st.date_input("Fin de vigencia", value=None)
            version_label = st.text_input("Versión o reforma", max_chars=200)
            source_reference = st.text_input(
                "Fuente o referencia",
                max_chars=1000,
            )
        text = st.text_area("Texto normativo *", max_chars=20000)
        notes = st.text_area("Notas de aplicabilidad", max_chars=3000)
        uploaded = st.file_uploader(
            "Documento de respaldo opcional",
            type=["pdf", "txt", "docx"],
            key="norm_file",
        )
        if st.form_submit_button("Agregar norma", type="primary"):
            try:
                file_name, content = optional_upload(uploaded)
                service.add_norm(
                    NormCreate(
                        case_id=case_id,
                        jurisdiction=jurisdiction,
                        matter=matter,
                        instrument=instrument,
                        article=article,
                        text=text,
                        hierarchy=NormHierarchy(hierarchy),
                        publication_date=publication_date,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        version_label=version_label or None,
                        source_reference=source_reference or None,
                        notes=notes or None,
                    ),
                    original_file_name=file_name,
                    file_content=content,
                )
                st.success("Norma agregada.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible agregar la norma: {exc}")

    norms = service.list_norms(case_id)
    if norms:
        st.dataframe(
            [
                {
                    "código": item.code,
                    "instrumento": item.instrument,
                    "artículo": item.article,
                    "jerarquía": item.hierarchy.value,
                    "versión": item.version_label or "",
                    "vigente_desde": item.valid_from.isoformat() if item.valid_from else "",
                    "vigente_hasta": item.valid_to.isoformat() if item.valid_to else "",
                    "archivo": item.original_file_name or "",
                }
                for item in norms
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay normas registradas.")


def render_jurisprudence(case_id: str) -> None:
    st.subheader("Jurisprudencia")
    st.caption(
        "La obligatoriedad y aplicabilidad deben verificarse en la fuente oficial correspondiente."
    )
    case = service.get_case_summary(case_id).case
    with st.form("jurisprudence_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            court = st.text_input("Órgano jurisdiccional *", max_chars=400)
            identifier = st.text_input("Identificador o registro *", max_chars=240)
            jurisdiction = st.text_input(
                "Jurisdicción *",
                value=case.jurisdiction,
                key="jurisdiction_jurisprudence",
            )
            matter = st.text_input(
                "Materia *",
                value=case.matter,
                key="matter_jurisprudence",
            )
            decision_date = st.date_input("Fecha de resolución", value=None)
        with col2:
            authority = st.selectbox(
                "Carácter declarado",
                enum_options(JurisprudenceAuthority),
            )
            source_reference = st.text_input("Fuente o referencia", max_chars=1000)
            interpreted_norms = st.text_area("Normas interpretadas", max_chars=3000)
            decision = st.text_area("Decisión", max_chars=5000)
        relevant_facts = st.text_area("Hechos relevantes *", max_chars=8000)
        legal_question = st.text_area("Problema jurídico del precedente *", max_chars=3000)
        criterion = st.text_area("Criterio o razón decisoria *", max_chars=12000)
        similarities = st.text_area("Similitudes con el expediente", max_chars=4000)
        differences = st.text_area("Diferencias con el expediente", max_chars=4000)
        uploaded = st.file_uploader(
            "Resolución o documento opcional",
            type=["pdf", "txt", "docx"],
            key="jurisprudence_file",
        )
        if st.form_submit_button("Agregar jurisprudencia", type="primary"):
            try:
                file_name, content = optional_upload(uploaded)
                service.add_jurisprudence(
                    JurisprudenceCreate(
                        case_id=case_id,
                        court=court,
                        identifier=identifier,
                        jurisdiction=jurisdiction,
                        matter=matter,
                        decision_date=decision_date,
                        relevant_facts=relevant_facts,
                        legal_question=legal_question,
                        criterion=criterion,
                        decision=decision or None,
                        interpreted_norms=interpreted_norms or None,
                        authority=JurisprudenceAuthority(authority),
                        source_reference=source_reference or None,
                        similarities=similarities or None,
                        differences=differences or None,
                    ),
                    original_file_name=file_name,
                    file_content=content,
                )
                st.success("Jurisprudencia agregada.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible agregar la jurisprudencia: {exc}")

    precedents = service.list_jurisprudence(case_id)
    if precedents:
        st.dataframe(
            [
                {
                    "código": item.code,
                    "identificador": item.identifier,
                    "órgano": item.court,
                    "fecha": item.decision_date.isoformat() if item.decision_date else "",
                    "carácter": item.authority.value,
                    "similitudes": item.similarities or "",
                    "diferencias": item.differences or "",
                    "archivo": item.original_file_name or "",
                }
                for item in precedents
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay jurisprudencia registrada.")


def render_doctrine(case_id: str) -> None:
    st.subheader("Doctrina")
    with st.form("doctrine_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            author = st.text_input("Autor *", max_chars=300)
            work_title = st.text_input("Obra *", max_chars=500)
            edition = st.text_input("Edición", max_chars=120)
            publication_year_raw = st.number_input(
                "Año",
                min_value=0,
                max_value=2100,
                value=0,
                step=1,
                help="Usa 0 cuando no se conozca.",
            )
            concept = st.text_input("Concepto jurídico *", max_chars=300)
        with col2:
            citation = st.text_area("Referencia bibliográfica *", max_chars=1500)
            source_reference = st.text_input("Fuente o ubicación", max_chars=1000)
            argumentative_function = st.text_area(
                "Función dentro del argumento",
                max_chars=2000,
            )
        position_summary = st.text_area("Síntesis de la posición doctrinal *", max_chars=10000)
        excerpt = st.text_area("Fragmento o paráfrasis", max_chars=5000)
        uploaded = st.file_uploader(
            "Documento de respaldo opcional",
            type=["pdf", "txt", "docx"],
            key="doctrine_file",
        )
        if st.form_submit_button("Agregar doctrina", type="primary"):
            try:
                file_name, content = optional_upload(uploaded)
                publication_year = int(publication_year_raw) or None
                service.add_doctrine(
                    DoctrineCreate(
                        case_id=case_id,
                        author=author,
                        work_title=work_title,
                        edition=edition or None,
                        publication_year=publication_year,
                        concept=concept,
                        position_summary=position_summary,
                        excerpt=excerpt or None,
                        citation=citation,
                        argumentative_function=argumentative_function or None,
                        source_reference=source_reference or None,
                    ),
                    original_file_name=file_name,
                    file_content=content,
                )
                st.success("Doctrina agregada.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible agregar la doctrina: {exc}")

    doctrine = service.list_doctrine(case_id)
    if doctrine:
        st.dataframe(
            [
                {
                    "código": item.code,
                    "autor": item.author,
                    "obra": item.work_title,
                    "año": item.publication_year or "",
                    "concepto": item.concept,
                    "función": item.argumentative_function or "",
                    "archivo": item.original_file_name or "",
                }
                for item in doctrine
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay doctrina registrada.")


def source_options(case_id: str, source_type: LegalSourceType) -> dict[str, str]:
    if source_type is LegalSourceType.NORM:
        return {
            f"{item.code} · {item.instrument}, {item.article}": item.id
            for item in service.list_norms(case_id)
        }
    if source_type is LegalSourceType.JURISPRUDENCE:
        return {
            f"{item.code} · {item.identifier}": item.id
            for item in service.list_jurisprudence(case_id)
        }
    return {
        f"{item.code} · {item.author}: {item.work_title}": item.id
        for item in service.list_doctrine(case_id)
    }


def render_issue_source_matrix(case_id: str) -> None:
    st.subheader("Matriz problema–fuente")
    issues = service.list_legal_issues(case_id)
    if not issues:
        st.info("Primero registra al menos un problema jurídico.")
        return

    issue_labels = {f"{item.code} · {item.title}": item.id for item in issues}
    source_type_value = st.selectbox(
        "Tipo de fuente a vincular",
        enum_options(LegalSourceType),
        key="matrix_source_type",
    )
    source_type = LegalSourceType(source_type_value)
    sources = source_options(case_id, source_type)
    if not sources:
        st.info(f"No hay fuentes del tipo {source_type.value}.")
    else:
        with st.form("issue_source_link_form", clear_on_submit=True):
            issue_label = st.selectbox("Problema jurídico", list(issue_labels))
            source_label = st.selectbox("Fuente", list(sources))
            orientation = st.selectbox("Orientación", enum_options(SourceOrientation))
            applicability = st.text_area(
                "Razón de aplicabilidad *",
                max_chars=3000,
                placeholder=(
                    "Explica qué supuesto, criterio o concepto de la fuente se relaciona "
                    "con el problema jurídico."
                ),
            )
            notes = st.text_area("Notas", max_chars=2000)
            if st.form_submit_button("Vincular fuente", type="primary"):
                try:
                    service.link_issue_source(
                        IssueSourceLinkCreate(
                            case_id=case_id,
                            issue_id=issue_labels[issue_label],
                            source_type=source_type,
                            source_id=sources[source_label],
                            orientation=SourceOrientation(orientation),
                            applicability=applicability,
                            notes=notes or None,
                        )
                    )
                    st.success("Vínculo creado o actualizado.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible vincular la fuente: {exc}")

    links = service.list_issue_source_links(case_id)
    if links:
        st.dataframe(
            [
                {
                    "problema": f"{link.issue_code} · {link.issue_title}",
                    "tipo": link.source_type.value,
                    "fuente": f"{link.source_code} · {link.source_title}",
                    "orientación": link.orientation.value,
                    "aplicabilidad": link.applicability,
                    "notas": link.notes or "",
                }
                for link in links
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay vínculos problema–fuente registrados.")


def selected_enum_index(enum_type: type[Any], value: Any) -> int:
    """Obtiene el índice visible de un valor de enumerado."""

    options = enum_options(enum_type)
    return options.index(value.value)


def render_delete_confirmation(
    *,
    form_key: str,
    entity_label: str,
    code: str,
    delete_action: Any,
) -> None:
    with st.expander(f"Eliminar {entity_label}", expanded=False):
        st.warning(
            "La eliminación es permanente en la base activa. Se creará un respaldo "
            "automático antes de ejecutar la operación."
        )
        with st.form(form_key):
            confirmation = st.text_input(
                f"Escribe {code} para confirmar",
                key=f"{form_key}_confirmation",
            )
            submitted = st.form_submit_button(
                f"Eliminar {code}",
                type="secondary",
            )
            if submitted:
                try:
                    delete_action(confirmation)
                    st.success(f"{code} fue eliminado.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible eliminar {code}: {exc}")


def render_legal_issue_correction(case_id: str) -> None:
    issues = service.list_legal_issues(case_id)
    if not issues:
        st.info("No hay problemas jurídicos para corregir.")
        return

    labels = {f"{item.code} · {item.title}": item for item in issues}
    selected_label = st.selectbox(
        "Problema jurídico",
        list(labels),
        key="correction_issue_selector",
    )
    item = labels[selected_label]
    with st.form("correction_issue_form"):
        title = st.text_input("Título *", value=item.title, max_chars=240)
        question = st.text_area(
            "Pregunta jurídica *",
            value=item.question,
            max_chars=1500,
        )
        description = st.text_area(
            "Contexto y delimitación",
            value=item.description or "",
            max_chars=3000,
        )
        status = st.selectbox(
            "Estado",
            enum_options(LegalIssueStatus),
            index=selected_enum_index(LegalIssueStatus, item.status),
        )
        if st.form_submit_button("Guardar corrección", type="primary"):
            try:
                service.update_legal_issue(
                    item.id,
                    LegalIssueCreate(
                        case_id=case_id,
                        title=title,
                        question=question,
                        description=description or None,
                        status=LegalIssueStatus(status),
                    ),
                )
                st.success(f"{item.code} fue actualizado sin cambiar su código.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible actualizar {item.code}: {exc}")

    render_delete_confirmation(
        form_key="delete_legal_issue_form",
        entity_label="problema jurídico",
        code=item.code,
        delete_action=lambda confirmation: service.delete_legal_issue(
            issue_id=item.id,
            case_id=case_id,
            confirmation_code=confirmation,
        ),
    )


def render_norm_correction(case_id: str) -> None:
    norms = service.list_norms(case_id)
    if not norms:
        st.info("No hay normas para corregir.")
        return

    labels = {f"{item.code} · {item.instrument}, {item.article}": item for item in norms}
    selected_label = st.selectbox(
        "Norma",
        list(labels),
        key="correction_norm_selector",
    )
    item = labels[selected_label]
    st.caption(
        f"Documento actual: {item.original_file_name or 'sin archivo'}. "
        "Una nueva carga reemplaza el archivo; dejarla vacía conserva el actual."
    )
    with st.form("correction_norm_form"):
        col1, col2 = st.columns(2)
        with col1:
            jurisdiction = st.text_input(
                "Jurisdicción *",
                value=item.jurisdiction,
                max_chars=250,
            )
            matter = st.text_input("Materia *", value=item.matter, max_chars=120)
            instrument = st.text_input(
                "Ordenamiento o instrumento *",
                value=item.instrument,
                max_chars=300,
            )
            article = st.text_input(
                "Artículo o disposición *",
                value=item.article,
                max_chars=120,
            )
            hierarchy = st.selectbox(
                "Jerarquía",
                enum_options(NormHierarchy),
                index=selected_enum_index(NormHierarchy, item.hierarchy),
            )
        with col2:
            publication_date = st.date_input(
                "Fecha de publicación",
                value=item.publication_date,
                key="correction_norm_publication_date",
            )
            valid_from = st.date_input(
                "Inicio de vigencia",
                value=item.valid_from,
                key="correction_norm_valid_from",
            )
            valid_to = st.date_input(
                "Fin de vigencia",
                value=item.valid_to,
                key="correction_norm_valid_to",
            )
            version_label = st.text_input(
                "Versión o reforma",
                value=item.version_label or "",
                max_chars=200,
            )
            source_reference = st.text_input(
                "Fuente o referencia",
                value=item.source_reference or "",
                max_chars=1000,
            )
        text = st.text_area(
            "Texto normativo *",
            value=item.text,
            max_chars=20000,
        )
        notes = st.text_area(
            "Notas de aplicabilidad",
            value=item.notes or "",
            max_chars=3000,
        )
        uploaded = st.file_uploader(
            "Nuevo documento de respaldo opcional",
            type=["pdf", "txt", "docx"],
            key=f"correction_norm_file_{item.id}",
        )
        if st.form_submit_button("Guardar corrección", type="primary"):
            try:
                file_name, content = optional_upload(uploaded)
                service.update_norm(
                    item.id,
                    NormCreate(
                        case_id=case_id,
                        jurisdiction=jurisdiction,
                        matter=matter,
                        instrument=instrument,
                        article=article,
                        text=text,
                        hierarchy=NormHierarchy(hierarchy),
                        publication_date=publication_date,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        version_label=version_label or None,
                        source_reference=source_reference or None,
                        notes=notes or None,
                    ),
                    original_file_name=file_name,
                    file_content=content,
                )
                st.success(f"{item.code} fue actualizada sin cambiar su código.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible actualizar {item.code}: {exc}")

    render_delete_confirmation(
        form_key="delete_norm_form",
        entity_label="norma",
        code=item.code,
        delete_action=lambda confirmation: service.delete_norm(
            norm_id=item.id,
            case_id=case_id,
            confirmation_code=confirmation,
        ),
    )


def render_jurisprudence_correction(case_id: str) -> None:
    precedents = service.list_jurisprudence(case_id)
    if not precedents:
        st.info("No hay jurisprudencia para corregir.")
        return

    labels = {f"{item.code} · {item.identifier}": item for item in precedents}
    selected_label = st.selectbox(
        "Jurisprudencia",
        list(labels),
        key="correction_jurisprudence_selector",
    )
    item = labels[selected_label]
    st.caption(
        f"Documento actual: {item.original_file_name or 'sin archivo'}. "
        "Una nueva carga reemplaza el archivo; dejarla vacía conserva el actual."
    )
    with st.form("correction_jurisprudence_form"):
        col1, col2 = st.columns(2)
        with col1:
            court = st.text_input(
                "Órgano jurisdiccional *",
                value=item.court,
                max_chars=400,
            )
            identifier = st.text_input(
                "Identificador o registro *",
                value=item.identifier,
                max_chars=240,
            )
            jurisdiction = st.text_input(
                "Jurisdicción *",
                value=item.jurisdiction,
                max_chars=250,
            )
            matter = st.text_input("Materia *", value=item.matter, max_chars=120)
            decision_date = st.date_input(
                "Fecha de resolución",
                value=item.decision_date,
                key="correction_jurisprudence_date",
            )
        with col2:
            authority = st.selectbox(
                "Carácter declarado",
                enum_options(JurisprudenceAuthority),
                index=selected_enum_index(JurisprudenceAuthority, item.authority),
            )
            source_reference = st.text_input(
                "Fuente o referencia",
                value=item.source_reference or "",
                max_chars=1000,
            )
            interpreted_norms = st.text_area(
                "Normas interpretadas",
                value=item.interpreted_norms or "",
                max_chars=3000,
            )
            decision = st.text_area(
                "Decisión",
                value=item.decision or "",
                max_chars=5000,
            )
        relevant_facts = st.text_area(
            "Hechos relevantes *",
            value=item.relevant_facts,
            max_chars=8000,
        )
        legal_question = st.text_area(
            "Problema jurídico del precedente *",
            value=item.legal_question,
            max_chars=3000,
        )
        criterion = st.text_area(
            "Criterio o razón decisoria *",
            value=item.criterion,
            max_chars=12000,
        )
        similarities = st.text_area(
            "Similitudes con el expediente",
            value=item.similarities or "",
            max_chars=4000,
        )
        differences = st.text_area(
            "Diferencias con el expediente",
            value=item.differences or "",
            max_chars=4000,
        )
        uploaded = st.file_uploader(
            "Nueva resolución o documento opcional",
            type=["pdf", "txt", "docx"],
            key=f"correction_jurisprudence_file_{item.id}",
        )
        if st.form_submit_button("Guardar corrección", type="primary"):
            try:
                file_name, content = optional_upload(uploaded)
                service.update_jurisprudence(
                    item.id,
                    JurisprudenceCreate(
                        case_id=case_id,
                        court=court,
                        identifier=identifier,
                        jurisdiction=jurisdiction,
                        matter=matter,
                        decision_date=decision_date,
                        relevant_facts=relevant_facts,
                        legal_question=legal_question,
                        criterion=criterion,
                        decision=decision or None,
                        interpreted_norms=interpreted_norms or None,
                        authority=JurisprudenceAuthority(authority),
                        source_reference=source_reference or None,
                        similarities=similarities or None,
                        differences=differences or None,
                    ),
                    original_file_name=file_name,
                    file_content=content,
                )
                st.success(f"{item.code} fue actualizada sin cambiar su código.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible actualizar {item.code}: {exc}")

    render_delete_confirmation(
        form_key="delete_jurisprudence_form",
        entity_label="jurisprudencia",
        code=item.code,
        delete_action=lambda confirmation: service.delete_jurisprudence(
            jurisprudence_id=item.id,
            case_id=case_id,
            confirmation_code=confirmation,
        ),
    )


def render_doctrine_correction(case_id: str) -> None:
    doctrine = service.list_doctrine(case_id)
    if not doctrine:
        st.info("No hay doctrina para corregir.")
        return

    labels = {f"{item.code} · {item.author}: {item.work_title}": item for item in doctrine}
    selected_label = st.selectbox(
        "Doctrina",
        list(labels),
        key="correction_doctrine_selector",
    )
    item = labels[selected_label]
    st.caption(
        f"Documento actual: {item.original_file_name or 'sin archivo'}. "
        "Una nueva carga reemplaza el archivo; dejarla vacía conserva el actual."
    )
    with st.form("correction_doctrine_form"):
        col1, col2 = st.columns(2)
        with col1:
            author = st.text_input("Autor *", value=item.author, max_chars=300)
            work_title = st.text_input(
                "Obra *",
                value=item.work_title,
                max_chars=500,
            )
            edition = st.text_input(
                "Edición",
                value=item.edition or "",
                max_chars=120,
            )
            publication_year_raw = st.number_input(
                "Año",
                min_value=0,
                max_value=2100,
                value=item.publication_year or 0,
                step=1,
            )
            concept = st.text_input(
                "Concepto jurídico *",
                value=item.concept,
                max_chars=300,
            )
        with col2:
            citation = st.text_area(
                "Referencia bibliográfica *",
                value=item.citation,
                max_chars=1500,
            )
            source_reference = st.text_input(
                "Fuente o ubicación",
                value=item.source_reference or "",
                max_chars=1000,
            )
            argumentative_function = st.text_area(
                "Función dentro del argumento",
                value=item.argumentative_function or "",
                max_chars=2000,
            )
        position_summary = st.text_area(
            "Síntesis de la posición doctrinal *",
            value=item.position_summary,
            max_chars=10000,
        )
        excerpt = st.text_area(
            "Fragmento o paráfrasis",
            value=item.excerpt or "",
            max_chars=5000,
        )
        uploaded = st.file_uploader(
            "Nuevo documento de respaldo opcional",
            type=["pdf", "txt", "docx"],
            key=f"correction_doctrine_file_{item.id}",
        )
        if st.form_submit_button("Guardar corrección", type="primary"):
            try:
                file_name, content = optional_upload(uploaded)
                service.update_doctrine(
                    item.id,
                    DoctrineCreate(
                        case_id=case_id,
                        author=author,
                        work_title=work_title,
                        edition=edition or None,
                        publication_year=int(publication_year_raw) or None,
                        concept=concept,
                        position_summary=position_summary,
                        excerpt=excerpt or None,
                        citation=citation,
                        argumentative_function=argumentative_function or None,
                        source_reference=source_reference or None,
                    ),
                    original_file_name=file_name,
                    file_content=content,
                )
                st.success(f"{item.code} fue actualizada sin cambiar su código.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible actualizar {item.code}: {exc}")

    render_delete_confirmation(
        form_key="delete_doctrine_form",
        entity_label="doctrina",
        code=item.code,
        delete_action=lambda confirmation: service.delete_doctrine(
            doctrine_id=item.id,
            case_id=case_id,
            confirmation_code=confirmation,
        ),
    )


def render_link_correction(case_id: str) -> None:
    links = service.list_issue_source_links(case_id)
    if not links:
        st.info("No hay vínculos problema–fuente para corregir.")
        return

    labels = {
        (
            f"{item.issue_code} ↔ {item.source_code} · "
            f"{item.source_type.value}"
        ): item
        for item in links
    }
    selected_label = st.selectbox(
        "Vínculo",
        list(labels),
        key="correction_link_selector",
    )
    item = labels[selected_label]
    st.info(
        f"Identidad protegida: {item.issue_code} ↔ {item.source_code}. "
        "Para cambiar la fuente, elimina el vínculo y crea uno nuevo."
    )
    with st.form("correction_link_form"):
        orientation = st.selectbox(
            "Orientación",
            enum_options(SourceOrientation),
            index=selected_enum_index(SourceOrientation, item.orientation),
        )
        applicability = st.text_area(
            "Razón de aplicabilidad *",
            value=item.applicability,
            max_chars=3000,
        )
        notes = st.text_area(
            "Notas",
            value=item.notes or "",
            max_chars=2000,
        )
        if st.form_submit_button("Guardar corrección", type="primary"):
            try:
                service.update_issue_source_link(
                    IssueSourceLinkCreate(
                        case_id=case_id,
                        issue_id=item.issue_id,
                        source_type=item.source_type,
                        source_id=item.source_id,
                        orientation=SourceOrientation(orientation),
                        applicability=applicability,
                        notes=notes or None,
                    )
                )
                st.success("El vínculo fue actualizado sin duplicarse.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible actualizar el vínculo: {exc}")

    render_delete_confirmation(
        form_key="delete_issue_source_link_form",
        entity_label="vínculo",
        code=item.source_code,
        delete_action=lambda confirmation: service.unlink_issue_source(
            case_id=case_id,
            issue_id=item.issue_id,
            source_type=item.source_type,
            source_id=item.source_id,
            confirmation_code=confirmation,
        ),
    )


def render_safe_correction(case_id: str) -> None:
    st.subheader("Corrección segura")
    st.caption(
        "Edita registros conservando sus códigos. Las eliminaciones requieren "
        "confirmación exacta, respaldo previo y ausencia de vínculos protegidos."
    )
    record_type = st.selectbox(
        "Tipo de registro",
        [
            "Problema jurídico",
            "Norma",
            "Jurisprudencia",
            "Doctrina",
            "Vínculo problema–fuente",
        ],
        key="safe_correction_record_type",
    )
    if record_type == "Problema jurídico":
        render_legal_issue_correction(case_id)
    elif record_type == "Norma":
        render_norm_correction(case_id)
    elif record_type == "Jurisprudencia":
        render_jurisprudence_correction(case_id)
    elif record_type == "Doctrina":
        render_doctrine_correction(case_id)
    else:
        render_link_correction(case_id)


def parse_codes(raw_value: str) -> list[str]:
    """Convierte una lista separada por comas en códigos normalizados."""

    return [
        value.strip().upper()
        for value in raw_value.split(",")
        if value.strip()
    ]


def parse_lines(raw_value: str) -> list[str]:
    """Convierte líneas no vacías en una lista ordenada y sin duplicados."""

    values: list[str] = []
    for raw_line in raw_value.splitlines():
        value = raw_line.strip()
        if value and value not in values:
            values.append(value)
    return values


def parse_rule_conditions(
    raw_value: str,
    role: ConditionRole,
) -> list[RuleConditionCreate]:
    """Interpreta líneas con formato predicado=Verdadero|Falso."""

    conditions: list[RuleConditionCreate] = []
    for line_number, raw_line in enumerate(raw_value.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError(
                f"Línea {line_number}: usa el formato predicado=Verdadero."
            )
        predicate_key, expected_raw = (
            value.strip() for value in line.split("=", maxsplit=1)
        )
        try:
            expected = AssertionValue(expected_raw.capitalize())
        except ValueError as exc:
            raise ValueError(
                f"Línea {line_number}: el valor debe ser Verdadero o Falso."
            ) from exc
        conditions.append(
            RuleConditionCreate(
                role=role,
                predicate_key=predicate_key,
                expected_value=expected,
            )
        )
    return conditions


def reasoning_issue_options(case_id: str) -> dict[str, str]:
    """Devuelve problemas jurídicos disponibles para el motor."""

    return {
        f"{issue.code} · {issue.title}": issue.id
        for issue in service.list_legal_issues(case_id)
    }


def render_reasoning_assertions(case_id: str) -> None:
    st.subheader("Premisas de razonamiento")
    st.caption(
        "Cada premisa es una afirmación atómica confirmada por el usuario. "
        "Los códigos de soporte deben existir en el expediente."
    )
    issues = reasoning_issue_options(case_id)
    if not issues:
        st.info("Primero registra un problema jurídico.")
        return

    with st.form("reasoning_assertion_form", clear_on_submit=True):
        issue_label = st.selectbox("Problema jurídico", list(issues))
        predicate_key = st.text_input(
            "Clave lógica *",
            placeholder="pago_acreditado",
            help="Minúsculas, números y guion bajo; sin espacios.",
        )
        statement = st.text_area(
            "Enunciado de la premisa *",
            placeholder="La compradora acreditó el pago total.",
            max_chars=2000,
        )
        value = st.selectbox("Valor", enum_options(AssertionValue))
        basis = st.text_area(
            "Justificación de la valoración *",
            max_chars=4000,
            placeholder=(
                "Explica por qué se asigna este valor y qué límites tiene "
                "la valoración."
            ),
        )
        support_codes_raw = st.text_input(
            "Códigos de soporte",
            placeholder="H-001, P-001, N-004",
            help="Hechos, pruebas o fuentes ya registradas.",
        )
        if st.form_submit_button("Agregar premisa", type="primary"):
            try:
                record = reasoning_service.add_assertion(
                    ReasoningAssertionCreate(
                        case_id=case_id,
                        issue_id=issues[issue_label],
                        predicate_key=predicate_key,
                        statement=statement,
                        value=AssertionValue(value),
                        basis=basis,
                        support_codes=parse_codes(support_codes_raw),
                    )
                )
                st.success(f"Premisa creada: {record.code}")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible agregar la premisa: {exc}")

    assertions = reasoning_service.list_assertions(case_id)
    if assertions:
        st.dataframe(
            [
                {
                    "código": item.code,
                    "clave": item.predicate_key,
                    "enunciado": item.statement,
                    "valor": item.value.value,
                    "soporte": ", ".join(item.support_codes),
                    "justificación": item.basis,
                }
                for item in assertions
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay premisas registradas.")


def render_reasoning_rules(case_id: str) -> None:
    st.subheader("Reglas de razonamiento")
    st.caption(
        "Las reglas rivales se resuelven de forma reproducible. El motor "
        "compara prioridad, tipo y especificidad estructural antes de aceptar "
        "una conclusión."
    )
    st.info(
        "Política de derrota: mayor prioridad numérica; en empate, regla "
        "estricta sobre provisional; en nuevo empate, mayor número de "
        "prerrequisitos distintos. Un empate exacto suspende ambas "
        "conclusiones para revisión humana."
    )
    issues = reasoning_issue_options(case_id)
    if not issues:
        st.info("Primero registra un problema jurídico.")
        return

    with st.form("reasoning_rule_form", clear_on_submit=True):
        issue_label = st.selectbox("Problema jurídico", list(issues))
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nombre de la regla *", max_chars=240)
            kind_value = st.selectbox("Tipo de regla", enum_options(RuleKind))
            priority = st.number_input(
                "Prioridad",
                min_value=0,
                max_value=1000,
                value=100,
                step=10,
                help=(
                    "Una prioridad mayor derrota a una regla rival con la "
                    "misma clave de conclusión y valor opuesto."
                ),
            )
            active = st.checkbox("Regla activa", value=True)
        with col2:
            conclusion_key = st.text_input(
                "Clave de conclusión *",
                placeholder="incumplimiento_entrega",
            )
            conclusion_statement = st.text_area(
                "Enunciado de conclusión *",
                max_chars=2000,
            )
            conclusion_value = st.selectbox(
                "Valor de conclusión",
                [
                    AssertionValue.TRUE.value,
                    AssertionValue.FALSE.value,
                ],
            )

        st.markdown("#### Condiciones")
        prerequisites_raw = st.text_area(
            "Prerrequisitos *",
            placeholder=(
                "obligacion_entrega_valida=Verdadero\n"
                "obligacion_exigible=Verdadero\n"
                "entrega_realizada=Falso"
            ),
            help="Una condición por línea: clave=Verdadero o clave=Falso.",
        )
        exceptions_raw = st.text_area(
            "Excepciones",
            placeholder=(
                "causa_justificante=Verdadero\n"
                "prorroga_acordada=Verdadero"
            ),
            help="Solo se admiten en reglas provisionales.",
        )
        legal_basis_raw = st.text_input(
            "Fundamentos jurídicos",
            placeholder="N-001, N-003, J-001, D-001",
            help="Solo normas, jurisprudencia y doctrina registradas.",
        )
        explanation = st.text_area(
            "Explicación de la regla *",
            max_chars=4000,
            placeholder=(
                "Describe el puente entre las premisas, las fuentes y la "
                "conclusión."
            ),
        )
        if st.form_submit_button("Agregar regla", type="primary"):
            try:
                conditions = parse_rule_conditions(
                    prerequisites_raw,
                    ConditionRole.PREREQUISITE,
                )
                conditions.extend(
                    parse_rule_conditions(
                        exceptions_raw,
                        ConditionRole.EXCEPTION,
                    )
                )
                record = reasoning_service.add_rule(
                    ReasoningRuleCreate(
                        case_id=case_id,
                        issue_id=issues[issue_label],
                        name=name,
                        kind=RuleKind(kind_value),
                        conclusion_key=conclusion_key,
                        conclusion_statement=conclusion_statement,
                        conclusion_value=AssertionValue(conclusion_value),
                        priority=int(priority),
                        active=active,
                        legal_basis_codes=parse_codes(legal_basis_raw),
                        explanation=explanation,
                        conditions=conditions,
                    )
                )
                st.success(f"Regla creada: {record.code}")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible agregar la regla: {exc}")

    rules = reasoning_service.list_rules(case_id)
    if rules:
        st.dataframe(
            [
                {
                    "código": item.code,
                    "nombre": item.name,
                    "tipo": item.kind.value,
                    "prioridad": item.priority,
                    "especificidad": item.specificity_score,
                    "activa": item.active,
                    "conclusión": (
                        f"{item.conclusion_key}={item.conclusion_value.value}"
                    ),
                    "condiciones": "; ".join(
                        f"{condition.role.value}: "
                        f"{condition.predicate_key}="
                        f"{condition.expected_value.value}"
                        for condition in item.conditions
                    ),
                    "fundamentos": ", ".join(item.legal_basis_codes),
                }
                for item in rules
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay reglas registradas.")


def rule_conditions_text(
    conditions: list[RuleConditionCreate],
    role: ConditionRole,
) -> str:
    """Serializa condiciones para edición sin modificar su significado."""

    return "\n".join(
        f"{condition.predicate_key}={condition.expected_value.value}"
        for condition in conditions
        if condition.role is role
    )


def render_reasoning_management(case_id: str) -> None:
    """Edita, versiona y elimina de forma segura premisas y reglas."""

    st.subheader("Gestión segura del razonamiento")
    st.caption(
        "Cada edición conserva el código visible, crea una versión del estado "
        "anterior y genera un respaldo SQLite consistente."
    )
    issues = reasoning_issue_options(case_id)
    if not issues:
        st.info("Primero registra un problema jurídico.")
        return

    issue_label = st.selectbox(
        "Problema jurídico",
        list(issues),
        key="reasoning_management_issue",
    )
    issue_id = issues[issue_label]
    assertion_tab, rule_tab, history_tab = st.tabs(
        ["Premisas", "Reglas", "Historial de cambios"]
    )

    with assertion_tab:
        assertions = reasoning_service.list_assertions(case_id, issue_id)
        if not assertions:
            st.info("No hay premisas disponibles para corregir.")
        else:
            labels = {
                f"{item.code} · {item.predicate_key}": item
                for item in assertions
            }
            selected_label = st.selectbox(
                "Premisa a gestionar",
                list(labels),
                key="reasoning_management_assertion",
            )
            selected = labels[selected_label]
            value_options = enum_options(AssertionValue)
            with st.form(f"reasoning_assertion_edit_{selected.id}"):
                predicate_key = st.text_input(
                    "Clave lógica *",
                    value=selected.predicate_key,
                    max_chars=80,
                )
                statement = st.text_area(
                    "Enunciado *",
                    value=selected.statement,
                    max_chars=2000,
                )
                value = st.selectbox(
                    "Valor",
                    value_options,
                    index=value_options.index(selected.value.value),
                )
                basis = st.text_area(
                    "Justificación *",
                    value=selected.basis,
                    max_chars=4000,
                )
                support_codes_raw = st.text_input(
                    "Códigos de soporte",
                    value=", ".join(selected.support_codes),
                )
                if st.form_submit_button(
                    "Guardar cambios de premisa",
                    type="primary",
                ):
                    try:
                        record = reasoning_service.update_assertion(
                            selected.id,
                            ReasoningAssertionUpdate(
                                predicate_key=predicate_key,
                                statement=statement,
                                value=AssertionValue(value),
                                basis=basis,
                                support_codes=parse_codes(support_codes_raw),
                            ),
                        )
                        st.success(
                            f"Premisa {record.code} actualizada y versionada."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"No fue posible actualizar la premisa: {exc}")

            with st.expander("Eliminar premisa", expanded=False):
                st.warning(
                    "La eliminación se bloquea si la clave lógica aparece en "
                    "alguna condición de regla."
                )
                confirmation = st.text_input(
                    f"Escribe {selected.code} para confirmar",
                    key=f"delete_assertion_confirmation_{selected.id}",
                )
                if st.button(
                    "Eliminar premisa definitivamente",
                    key=f"delete_assertion_button_{selected.id}",
                ):
                    try:
                        reasoning_service.delete_assertion(
                            selected.id,
                            confirmation=confirmation,
                        )
                        st.success(
                            f"Premisa {selected.code} eliminada con historial."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"No fue posible eliminar la premisa: {exc}")

            versions = reasoning_service.list_assertion_versions(
                case_id=case_id,
                entity_id=selected.id,
            )
            st.markdown("#### Versiones de esta premisa")
            if versions:
                st.dataframe(
                    [
                        {
                            "versión": item.version_number,
                            "acción": item.action.value,
                            "fecha": item.created_at.isoformat(timespec="seconds"),
                            "clave anterior": item.snapshot.get("predicate_key", ""),
                            "valor anterior": item.snapshot.get("value", ""),
                        }
                        for item in versions
                    ],
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("La premisa todavía no tiene versiones anteriores.")

    with rule_tab:
        rules = reasoning_service.list_rules(case_id, issue_id)
        if not rules:
            st.info("No hay reglas disponibles para corregir.")
        else:
            rule_labels = {
                (
                    f"{item.code} · {item.name} · "
                    f"{'Activa' if item.active else 'Inactiva'}"
                ): item
                for item in rules
            }
            selected_rule_label = st.selectbox(
                "Regla a gestionar",
                list(rule_labels),
                key="reasoning_management_rule",
            )
            selected_rule = rule_labels[selected_rule_label]
            st.caption(
                "Especificidad actual: "
                f"{selected_rule.specificity_score} prerrequisito(s) distinto(s)."
            )
            kind_options = enum_options(RuleKind)
            conclusion_options = [
                AssertionValue.TRUE.value,
                AssertionValue.FALSE.value,
            ]
            with st.form(f"reasoning_rule_edit_{selected_rule.id}"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input(
                        "Nombre *",
                        value=selected_rule.name,
                        max_chars=240,
                    )
                    kind_value = st.selectbox(
                        "Tipo",
                        kind_options,
                        index=kind_options.index(selected_rule.kind.value),
                    )
                    priority = st.number_input(
                        "Prioridad",
                        min_value=0,
                        max_value=1000,
                        value=selected_rule.priority,
                        step=10,
                        help=(
                            "Orden de derrota: prioridad, tipo de regla y "
                            "especificidad estructural."
                        ),
                    )
                    active = st.checkbox(
                        "Regla activa",
                        value=selected_rule.active,
                    )
                with col2:
                    conclusion_key = st.text_input(
                        "Clave de conclusión *",
                        value=selected_rule.conclusion_key,
                        max_chars=80,
                    )
                    conclusion_statement = st.text_area(
                        "Enunciado de conclusión *",
                        value=selected_rule.conclusion_statement,
                        max_chars=2000,
                    )
                    conclusion_value = st.selectbox(
                        "Valor de conclusión",
                        conclusion_options,
                        index=conclusion_options.index(
                            selected_rule.conclusion_value.value
                        ),
                    )
                prerequisites_raw = st.text_area(
                    "Prerrequisitos *",
                    value=rule_conditions_text(
                        selected_rule.conditions,
                        ConditionRole.PREREQUISITE,
                    ),
                    help="Una condición por línea: clave=Verdadero o clave=Falso.",
                )
                exceptions_raw = st.text_area(
                    "Excepciones",
                    value=rule_conditions_text(
                        selected_rule.conditions,
                        ConditionRole.EXCEPTION,
                    ),
                    help="Solo se admiten en reglas provisionales.",
                )
                legal_basis_raw = st.text_input(
                    "Fundamentos jurídicos",
                    value=", ".join(selected_rule.legal_basis_codes),
                )
                explanation = st.text_area(
                    "Explicación *",
                    value=selected_rule.explanation,
                    max_chars=4000,
                )
                if st.form_submit_button(
                    "Guardar cambios de regla",
                    type="primary",
                ):
                    try:
                        conditions = parse_rule_conditions(
                            prerequisites_raw,
                            ConditionRole.PREREQUISITE,
                        )
                        conditions.extend(
                            parse_rule_conditions(
                                exceptions_raw,
                                ConditionRole.EXCEPTION,
                            )
                        )
                        record = reasoning_service.update_rule(
                            selected_rule.id,
                            ReasoningRuleUpdate(
                                name=name,
                                kind=RuleKind(kind_value),
                                conclusion_key=conclusion_key,
                                conclusion_statement=conclusion_statement,
                                conclusion_value=AssertionValue(
                                    conclusion_value
                                ),
                                priority=int(priority),
                                active=active,
                                legal_basis_codes=parse_codes(
                                    legal_basis_raw
                                ),
                                explanation=explanation,
                                conditions=conditions,
                            ),
                        )
                        st.success(
                            f"Regla {record.code} actualizada y versionada."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"No fue posible actualizar la regla: {exc}")

            with st.expander("Eliminar regla", expanded=False):
                st.warning(
                    "La eliminación se bloquea si otra regla depende de su "
                    "clave de conclusión."
                )
                confirmation = st.text_input(
                    f"Escribe {selected_rule.code} para confirmar",
                    key=f"delete_rule_confirmation_{selected_rule.id}",
                )
                if st.button(
                    "Eliminar regla definitivamente",
                    key=f"delete_rule_button_{selected_rule.id}",
                ):
                    try:
                        reasoning_service.delete_rule(
                            selected_rule.id,
                            confirmation=confirmation,
                        )
                        st.success(
                            f"Regla {selected_rule.code} eliminada con historial."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"No fue posible eliminar la regla: {exc}")

            rule_versions = reasoning_service.list_rule_versions(
                case_id=case_id,
                entity_id=selected_rule.id,
            )
            st.markdown("#### Versiones de esta regla")
            if rule_versions:
                st.dataframe(
                    [
                        {
                            "versión": item.version_number,
                            "acción": item.action.value,
                            "fecha": item.created_at.isoformat(timespec="seconds"),
                            "nombre anterior": item.snapshot.get("name", ""),
                            "prioridad anterior": item.snapshot.get(
                                "priority",
                                "",
                            ),
                            "activa anteriormente": item.snapshot.get(
                                "active",
                                "",
                            ),
                        }
                        for item in rule_versions
                    ],
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("La regla todavía no tiene versiones anteriores.")

    with history_tab:
        assertion_versions = reasoning_service.list_assertion_versions(
            case_id=case_id
        )
        rule_versions = reasoning_service.list_rule_versions(case_id=case_id)
        history_rows = [
            {
                "fecha": item.created_at.isoformat(timespec="seconds"),
                "entidad": "Premisa",
                "código": item.entity_code,
                "versión": item.version_number,
                "acción": item.action.value,
            }
            for item in assertion_versions
        ]
        history_rows.extend(
            {
                "fecha": item.created_at.isoformat(timespec="seconds"),
                "entidad": "Regla",
                "código": item.entity_code,
                "versión": item.version_number,
                "acción": item.action.value,
            }
            for item in rule_versions
        )
        history_rows.sort(key=lambda item: str(item["fecha"]), reverse=True)
        if history_rows:
            st.dataframe(
                history_rows,
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Todavía no existen cambios versionados.")


def render_reasoning_report(run_id: str) -> None:
    report = reasoning_service.get_run_report(run_id)
    summary = report.run.summary
    st.markdown("### Resultado de la ejecución")
    metrics = st.columns(4)
    metrics[0].metric("Reglas aplicadas", summary.get("fired_rule_count", 0))
    metrics[1].metric("Conclusiones", summary.get("conclusion_count", 0))
    metrics[2].metric("Contradicciones", summary.get("contradiction_count", 0))
    metrics[3].metric("Motor", report.run.engine_version)

    conflict_metrics = st.columns(4)
    conflict_metrics[0].metric(
        "Reglas derrotadas",
        summary.get("defeated_rule_count", 0),
    )
    conflict_metrics[1].metric(
        "Empates",
        summary.get("tied_rule_count", 0),
    )
    conflict_metrics[2].metric(
        "Retiradas",
        summary.get("withdrawn_rule_count", 0),
    )
    conflict_metrics[3].metric(
        "Conflictos",
        summary.get("conflict_count", 0),
    )

    st.caption(
        f"Huella de entrada: {report.run.input_hash[:16]}… · "
        f"Ejecución: {report.run.started_at.isoformat(timespec='seconds')}"
    )
    if bool(summary.get("has_contradictions", False)):
        st.error(
            "Se detectaron afirmaciones o conclusiones opuestas. "
            "Revise la traza antes de utilizar el resultado."
        )
    if bool(summary.get("has_unresolved_conflicts", False)):
        st.error(
            "Existe al menos un empate exacto entre reglas rivales. "
            "Las conclusiones opuestas fueron suspendidas para revisión humana."
        )
    if report.run.engine_version == "3.2.0":
        st.caption(
            "Política aplicada: prioridad > tipo de regla > especificidad. "
            "La especificidad cuenta prerrequisitos distintos."
        )

    st.markdown("#### Conclusiones inferidas")
    if report.conclusions:
        st.dataframe(
            [
                {
                    "código": item.code,
                    "clave": item.predicate_key,
                    "conclusión": item.statement,
                    "valor": item.value.value,
                    "estado": item.status.value,
                    "soporte": item.support_level.value,
                    "reglas": ", ".join(item.rule_codes),
                    "premisas": ", ".join(item.supporting_assertion_codes),
                    "fuentes": ", ".join(item.source_codes),
                }
                for item in report.conclusions
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info(
            "Ninguna regla produjo una conclusión. Revise las premisas "
            "faltantes y la traza."
        )

    st.markdown("#### Traza de reglas")
    st.dataframe(
        [
            {
                "secuencia": item.sequence,
                "regla": item.rule_code,
                "resultado": item.outcome.value,
                "detalle": str(item.detail),
            }
            for item in report.traces
        ],
        width="stretch",
        hide_index=True,
    )

    st.markdown("#### Exportación reproducible")
    export_columns = st.columns(2)
    export_columns[0].download_button(
        "Descargar JSON",
        data=reasoning_service.export_run_json(run_id),
        file_name=f"ius_razon_{run_id[:8]}.json",
        mime="application/json",
        key=f"download_reasoning_json_{run_id}",
    )
    export_columns[1].download_button(
        "Descargar Markdown",
        data=reasoning_service.export_run_markdown(run_id),
        file_name=f"ius_razon_{run_id[:8]}.md",
        mime="text/markdown",
        key=f"download_reasoning_markdown_{run_id}",
    )
    if report.run.input_snapshot:
        with st.expander("Entradas exactas de esta ejecución"):
            st.json(report.run.input_snapshot)
    else:
        st.info(
            "Esta ejecución fue creada antes de Sprint 3.1 y solo conserva "
            "la huella, no la instantánea completa de entrada."
        )


def render_reasoning_inference(case_id: str) -> None:
    st.subheader("Inferencia y trazabilidad")
    st.warning(
        "El resultado depende únicamente de las premisas y reglas registradas. "
        "No verifica de forma automática la vigencia, autenticidad ni "
        "aplicabilidad jurídica de las fuentes."
    )
    issues = reasoning_issue_options(case_id)
    if not issues:
        st.info("Primero registra un problema jurídico.")
        return

    issue_label = st.selectbox(
        "Problema jurídico a analizar",
        list(issues),
        key="reasoning_run_issue",
    )
    issue_id = issues[issue_label]
    assertion_count = len(
        reasoning_service.list_assertions(case_id, issue_id)
    )
    rule_count = len(
        reasoning_service.list_rules(
            case_id,
            issue_id,
            active_only=True,
        )
    )
    col1, col2 = st.columns(2)
    col1.metric("Premisas", assertion_count)
    col2.metric("Reglas activas", rule_count)

    if st.button(
        "Ejecutar razonamiento",
        type="primary",
        disabled=assertion_count == 0 or rule_count == 0,
    ):
        try:
            report = reasoning_service.run(
                case_id=case_id,
                issue_id=issue_id,
            )
            st.session_state["selected_reasoning_run_id"] = report.run.id
            st.success("Razonamiento completado y trazado.")
            st.rerun()
        except Exception as exc:
            st.error(f"No fue posible ejecutar el razonamiento: {exc}")

    runs = reasoning_service.list_runs(case_id, issue_id)
    if not runs:
        st.info("Todavía no existen ejecuciones para este problema.")
        return

    run_labels = {
        (
            f"{run.started_at.isoformat(timespec='seconds')} · "
            f"{run.id[:8]} · {run.summary.get('conclusion_count', 0)} conclusiones"
        ): run.id
        for run in runs
    }
    selected_run_id = st.session_state.get("selected_reasoning_run_id")
    default_index = 0
    if selected_run_id in run_labels.values():
        default_index = list(run_labels.values()).index(selected_run_id)
    run_label = st.selectbox(
        "Ejecución a revisar",
        list(run_labels),
        index=default_index,
    )
    render_reasoning_report(run_labels[run_label])

    if len(runs) >= 2:
        with st.expander("Comparar ejecuciones", expanded=False):
            comparison_labels = list(run_labels)
            first_label = st.selectbox(
                "Ejecución base",
                comparison_labels,
                index=min(1, len(comparison_labels) - 1),
                key="reasoning_compare_first",
            )
            second_label = st.selectbox(
                "Ejecución comparada",
                comparison_labels,
                index=0,
                key="reasoning_compare_second",
            )
            if st.button(
                "Comparar resultados",
                key="reasoning_compare_button",
            ):
                try:
                    comparison = reasoning_service.compare_runs(
                        run_labels[first_label],
                        run_labels[second_label],
                    )
                    st.json(comparison)
                except Exception as exc:
                    st.error(f"No fue posible comparar las ejecuciones: {exc}")


def render_argument_graph_and_scenarios(
    case_id: str,
    issue_id: str,
    arguments: list[Any],
) -> None:
    """Muestra escenarios alternativos, comparación y grafo dirigido."""

    st.markdown("### Grafo argumental y escenarios alternativos")
    st.caption(
        "Los escenarios seleccionan subconjuntos de argumentos y relaciones. "
        "Sus métricas describen estructura y trazabilidad, no probabilidad de éxito."
    )
    argument_labels = {
        f"{argument.code} · {argument.title}": argument.id
        for argument in arguments
    }
    label_by_id = {
        argument_id: label for label, argument_id in argument_labels.items()
    }

    with (
        st.expander("Crear escenario alternativo", expanded=False),
        st.form("argument_scenario_create_form", clear_on_submit=True),
    ):
        scenario_name = st.text_input(
            "Nombre del escenario *",
            max_chars=240,
        )
        scenario_description = st.text_area(
            "Descripción *",
            max_chars=4000,
            placeholder=(
                "Explica qué cambia, qué permanece y qué objetivo comparativo "
                "tiene el escenario."
            ),
        )
        scenario_status = st.selectbox(
            "Estado",
            enum_options(ScenarioStatus),
        )
        selected_argument_labels = st.multiselect(
            "Argumentos incluidos *",
            list(argument_labels),
            default=list(argument_labels),
        )
        assumptions_raw = st.text_area(
            "Supuestos adicionales",
            max_chars=8000,
            placeholder="Un supuesto por línea.",
        )
        if st.form_submit_button(
            "Crear escenario",
            type="primary",
        ):
            try:
                record = argumentation_service.add_scenario(
                    ArgumentScenarioCreate(
                        case_id=case_id,
                        issue_id=issue_id,
                        name=scenario_name,
                        description=scenario_description,
                        status=ScenarioStatus(scenario_status),
                        argument_ids=[
                            argument_labels[label]
                            for label in selected_argument_labels
                        ],
                        assumptions=parse_lines(assumptions_raw),
                    )
                )
                st.success(f"Escenario creado: {record.code}")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible crear el escenario: {exc}")

    scenarios = argumentation_service.list_scenarios(
        case_id,
        issue_id,
        include_archived=True,
    )
    if scenarios:
        st.dataframe(
            [
                {
                    "código": scenario.code,
                    "nombre": scenario.name,
                    "estado": scenario.status.value,
                    "argumentos": len(scenario.argument_ids),
                    "supuestos": len(scenario.assumptions),
                    "actualizado": scenario.updated_at.isoformat(),
                }
                for scenario in scenarios
            ],
            width="stretch",
            hide_index=True,
        )

        with st.expander("Editar o eliminar escenario", expanded=False):
            scenario_labels = {
                f"{scenario.code} · {scenario.name}": scenario.id
                for scenario in scenarios
            }
            selected_scenario_label = st.selectbox(
                "Escenario",
                list(scenario_labels),
                key="scenario_management_selector",
            )
            selected_scenario = next(
                scenario
                for scenario in scenarios
                if scenario.id == scenario_labels[selected_scenario_label]
            )
            editable_name = st.text_input(
                "Nombre",
                value=selected_scenario.name,
                max_chars=240,
                key=f"scenario_name_{selected_scenario.id}",
            )
            editable_description = st.text_area(
                "Descripción",
                value=selected_scenario.description,
                max_chars=4000,
                key=f"scenario_description_{selected_scenario.id}",
            )
            editable_status = st.selectbox(
                "Estado",
                enum_options(ScenarioStatus),
                index=enum_options(ScenarioStatus).index(
                    selected_scenario.status.value
                ),
                key=f"scenario_status_{selected_scenario.id}",
            )
            editable_arguments = st.multiselect(
                "Argumentos incluidos",
                list(argument_labels),
                default=[
                    label_by_id[argument_id]
                    for argument_id in selected_scenario.argument_ids
                    if argument_id in label_by_id
                ],
                key=f"scenario_arguments_{selected_scenario.id}",
            )
            editable_assumptions = st.text_area(
                "Supuestos",
                value="\n".join(selected_scenario.assumptions),
                max_chars=8000,
                key=f"scenario_assumptions_{selected_scenario.id}",
            )
            if st.button(
                "Guardar cambios del escenario",
                key=f"scenario_update_{selected_scenario.id}",
            ):
                try:
                    updated = argumentation_service.update_scenario(
                        selected_scenario.id,
                        ArgumentScenarioUpdate(
                            name=editable_name,
                            description=editable_description,
                            status=ScenarioStatus(editable_status),
                            argument_ids=[
                                argument_labels[label]
                                for label in editable_arguments
                            ],
                            assumptions=parse_lines(editable_assumptions),
                        ),
                    )
                    st.success(
                        f"Escenario {updated.code} actualizado sin cambiar su código."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible actualizar el escenario: {exc}")

            confirmation = st.text_input(
                f"Escribe {selected_scenario.code} para eliminar",
                key=f"scenario_delete_confirmation_{selected_scenario.id}",
            )
            if st.button(
                "Eliminar escenario",
                key=f"scenario_delete_{selected_scenario.id}",
            ):
                try:
                    argumentation_service.delete_scenario(
                        selected_scenario.id,
                        confirmation=confirmation,
                    )
                    st.success(
                        f"Escenario {selected_scenario.code} eliminado."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible eliminar el escenario: {exc}")
    else:
        st.info(
            "Todavía no hay escenarios guardados. La vista completa permanece disponible."
        )

    view_options: dict[str, str | None] = {"Vista completa": None}
    view_options.update(
        {
            f"{scenario.code} · {scenario.name}": scenario.id
            for scenario in scenarios
            if scenario.status is not ScenarioStatus.ARCHIVED
        }
    )
    selected_view_label = st.selectbox(
        "Vista argumental",
        list(view_options),
        key="argument_graph_view",
    )
    selected_scenario_id = view_options[selected_view_label]
    try:
        graph = argumentation_service.build_graph(
            case_id,
            issue_id,
            selected_scenario_id,
        )
    except Exception as exc:
        st.error(f"No fue posible construir el grafo: {exc}")
        return

    graph_metrics = st.columns(5)
    graph_metrics[0].metric("Argumentos", graph.summary["node_count"])
    graph_metrics[1].metric("Relaciones", graph.summary["edge_count"])
    graph_metrics[2].metric("Ataques", graph.summary["attack_edge_count"])
    graph_metrics[3].metric(
        "Objeciones pendientes",
        graph.summary["unresolved_objection_count"],
    )
    graph_metrics[4].metric(
        "Componentes",
        graph.summary["component_count"],
    )
    st.graphviz_chart(graph.dot_source, width="stretch")
    st.caption(
        f"Huella del grafo: {graph.input_hash} · "
        f"soporte medio {graph.summary['support_score_average']}/5"
    )
    if graph.assumptions:
        with st.expander("Supuestos del escenario", expanded=False):
            for assumption in graph.assumptions:
                st.write(f"- {assumption}")
    for warning in graph.warnings:
        st.warning(warning)

    graph_exports = st.columns(3)
    graph_exports[0].download_button(
        "Descargar grafo JSON",
        data=argumentation_service.export_graph_json(
            case_id,
            issue_id,
            selected_scenario_id,
        ),
        file_name=f"ius_razon_grafo_{issue_id[:8]}.json",
        mime="application/json",
        key=f"graph_json_{issue_id}_{selected_scenario_id}",
    )
    graph_exports[1].download_button(
        "Descargar grafo Markdown",
        data=argumentation_service.export_graph_markdown(
            case_id,
            issue_id,
            selected_scenario_id,
        ),
        file_name=f"ius_razon_grafo_{issue_id[:8]}.md",
        mime="text/markdown",
        key=f"graph_markdown_{issue_id}_{selected_scenario_id}",
    )
    graph_exports[2].download_button(
        "Descargar DOT",
        data=argumentation_service.export_graph_dot(
            case_id,
            issue_id,
            selected_scenario_id,
        ),
        file_name=f"ius_razon_grafo_{issue_id[:8]}.dot",
        mime="text/vnd.graphviz",
        key=f"graph_dot_{issue_id}_{selected_scenario_id}",
    )

    if len(view_options) >= 2:
        st.markdown("#### Comparar escenarios")
        comparison_columns = st.columns(2)
        first_label = comparison_columns[0].selectbox(
            "Escenario base",
            list(view_options),
            key="scenario_comparison_first",
        )
        second_label = comparison_columns[1].selectbox(
            "Escenario comparado",
            list(view_options),
            index=1,
            key="scenario_comparison_second",
        )
        if st.button(
            "Comparar escenarios",
            key="scenario_comparison_button",
        ):
            try:
                comparison = argumentation_service.compare_scenarios(
                    case_id,
                    issue_id,
                    view_options[first_label],
                    view_options[second_label],
                )
                st.json(comparison.model_dump(mode="json"))
            except Exception as exc:
                st.error(f"No fue posible comparar los escenarios: {exc}")


def render_argumentation(case_id: str) -> None:
    """Construye argumentos, contraargumentos, relaciones y reportes."""

    st.subheader("Argumentación jurídica")
    st.warning(
        "El módulo organiza tesis y relaciones registradas por el usuario. "
        "No verifica automáticamente autenticidad, vigencia, aplicabilidad "
        "ni suficiencia jurídica."
    )
    issues = reasoning_issue_options(case_id)
    if not issues:
        st.info("Primero registra un problema jurídico.")
        return

    issue_label = st.selectbox(
        "Problema jurídico",
        list(issues),
        key="argumentation_issue",
    )
    issue_id = issues[issue_label]
    conclusion_contexts = argumentation_service.list_conclusion_contexts(
        case_id,
        issue_id,
    )

    st.markdown("### Crear desde una conclusión")
    if conclusion_contexts:
        conclusion_labels = {
            (
                f"{context['code']} · {context['predicate_key']}="
                f"{context['value']} · ejecución {str(context['run_id'])[:8]}"
            ): str(context["id"])
            for context in conclusion_contexts
        }
        with st.form("argument_from_conclusion_form", clear_on_submit=True):
            conclusion_label = st.selectbox(
                "Conclusión trazada",
                list(conclusion_labels),
            )
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input(
                    "Título del argumento *",
                    max_chars=240,
                )
                position = st.selectbox(
                    "Posición",
                    enum_options(ArgumentPosition),
                )
                status = st.selectbox(
                    "Estado",
                    enum_options(ArgumentStatus),
                )
            with col2:
                claim = st.text_area(
                    "Pretensión argumental *",
                    max_chars=5000,
                    placeholder=(
                        "Explica qué se sostiene a partir de la conclusión "
                        "seleccionada."
                    ),
                )
                reasoning = st.text_area(
                    "Desarrollo del argumento *",
                    max_chars=8000,
                    placeholder=(
                        "Conecta premisas, regla, hechos, pruebas y fuentes, "
                        "e indica límites y objeciones previsibles."
                    ),
                )
            if st.form_submit_button(
                "Crear argumento trazable",
                type="primary",
            ):
                try:
                    record = argumentation_service.create_from_conclusion(
                        conclusion_id=conclusion_labels[conclusion_label],
                        position=ArgumentPosition(position),
                        title=title,
                        claim=claim,
                        reasoning=reasoning,
                        status=ArgumentStatus(status),
                    )
                    st.success(f"Argumento creado: {record.code}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible crear el argumento: {exc}")
    else:
        st.info(
            "Ejecuta primero el razonamiento para disponer de conclusiones "
            "trazadas."
        )

    with (
        st.expander("Crear argumento manual", expanded=False),
        st.form("manual_argument_form", clear_on_submit=True),
    ):
        title = st.text_input(
            "Título *",
            max_chars=240,
            key="manual_argument_title",
        )
        col1, col2 = st.columns(2)
        with col1:
            position = st.selectbox(
                "Posición",
                enum_options(ArgumentPosition),
                key="manual_argument_position",
            )
            thesis_key = st.text_input(
                "Clave de tesis *",
                placeholder="incumplimiento_entrega",
            )
            thesis_statement = st.text_area(
                "Enunciado de tesis *",
                max_chars=2000,
            )
            thesis_value = st.selectbox(
                "Valor de tesis",
                [
                    AssertionValue.TRUE.value,
                    AssertionValue.FALSE.value,
                ],
            )
            status = st.selectbox(
                "Estado",
                enum_options(ArgumentStatus),
                key="manual_argument_status",
            )
        with col2:
            claim = st.text_area(
                "Pretensión argumental *",
                max_chars=5000,
                key="manual_argument_claim",
            )
            reasoning = st.text_area(
                "Desarrollo argumental *",
                max_chars=8000,
                key="manual_argument_reasoning",
            )
        st.markdown("#### Trazabilidad")
        fact_codes = st.text_input(
            "Hechos",
            placeholder="H-001, H-002",
        )
        evidence_codes = st.text_input(
            "Pruebas",
            placeholder="P-001",
        )
        source_codes = st.text_input(
            "Fuentes jurídicas",
            placeholder="N-001, J-001, D-001",
        )
        rule_codes = st.text_input(
            "Reglas",
            placeholder="R-001",
        )
        assertion_codes = st.text_input(
            "Premisas",
            placeholder="A-001, A-002",
        )
        if st.form_submit_button("Crear argumento manual"):
            try:
                record = argumentation_service.add_argument(
                    LegalArgumentCreate(
                        case_id=case_id,
                        issue_id=issue_id,
                        title=title,
                        position=ArgumentPosition(position),
                        thesis_key=thesis_key,
                        thesis_statement=thesis_statement,
                        thesis_value=AssertionValue(thesis_value),
                        claim=claim,
                        reasoning=reasoning,
                        status=ArgumentStatus(status),
                        fact_codes=parse_codes(fact_codes),
                        evidence_codes=parse_codes(evidence_codes),
                        source_codes=parse_codes(source_codes),
                        rule_codes=parse_codes(rule_codes),
                        assertion_codes=parse_codes(assertion_codes),
                    )
                )
                st.success(f"Argumento creado: {record.code}")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible crear el argumento: {exc}")

    arguments = argumentation_service.list_arguments(case_id, issue_id)
    dossier = argumentation_service.build_dossier(case_id, issue_id)
    support_by_code = {
        item.argument_code: item for item in dossier.support_assessments
    }
    st.markdown("### Argumentos registrados")
    if arguments:
        st.dataframe(
            [
                {
                    "código": argument.code,
                    "título": argument.title,
                    "posición": argument.position.value,
                    "tesis": (
                        f"{argument.thesis_key}="
                        f"{argument.thesis_value.value}"
                    ),
                    "estado": argument.status.value,
                    "soporte": (
                        f"{support_by_code[argument.code].level.value} "
                        f"({support_by_code[argument.code].score}/5)"
                    ),
                    "hechos": ", ".join(argument.fact_codes),
                    "pruebas": ", ".join(argument.evidence_codes),
                    "fuentes": ", ".join(argument.source_codes),
                    "reglas": ", ".join(argument.rule_codes),
                    "premisas": ", ".join(argument.assertion_codes),
                }
                for argument in arguments
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay argumentos registrados para este problema.")
        return

    if len(arguments) >= 2:
        st.markdown("### Relacionar argumentos")
        argument_labels = {
            f"{argument.code} · {argument.title}": argument.id
            for argument in arguments
        }
        with st.form("argument_relation_form", clear_on_submit=True):
            source_label = st.selectbox(
                "Argumento de origen",
                list(argument_labels),
            )
            target_label = st.selectbox(
                "Argumento de destino",
                list(argument_labels),
                index=min(1, len(argument_labels) - 1),
            )
            relation_type = st.selectbox(
                "Tipo de relación",
                enum_options(ArgumentRelationType),
            )
            rationale = st.text_area(
                "Justificación de la relación *",
                max_chars=4000,
            )
            if st.form_submit_button("Crear relación"):
                try:
                    relation = argumentation_service.add_relation(
                        ArgumentRelationCreate(
                            case_id=case_id,
                            issue_id=issue_id,
                            source_argument_id=argument_labels[source_label],
                            target_argument_id=argument_labels[target_label],
                            relation_type=ArgumentRelationType(
                                relation_type
                            ),
                            rationale=rationale,
                        )
                    )
                    st.success(f"Relación creada: {relation.code}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible crear la relación: {exc}")

    relations = argumentation_service.list_relations(case_id, issue_id)
    argument_by_id = {
        argument.id: argument.code for argument in arguments
    }
    st.markdown("### Red argumental")
    if relations:
        st.dataframe(
            [
                {
                    "código": relation.code,
                    "origen": argument_by_id.get(
                        relation.source_argument_id,
                        relation.source_argument_id[:8],
                    ),
                    "relación": relation.relation_type.value,
                    "destino": argument_by_id.get(
                        relation.target_argument_id,
                        relation.target_argument_id[:8],
                    ),
                    "justificación": relation.rationale,
                }
                for relation in relations
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Todavía no hay apoyos, ataques ni réplicas.")

    render_argument_graph_and_scenarios(
        case_id,
        issue_id,
        arguments,
    )

    st.markdown("### Diagnóstico argumental")
    metrics = st.columns(5)
    metrics[0].metric(
        "Argumentos",
        dossier.summary["argument_count"],
    )
    metrics[1].metric(
        "Relaciones",
        dossier.summary["relation_count"],
    )
    metrics[2].metric(
        "Favorables",
        dossier.summary["favorable_count"],
    )
    metrics[3].metric(
        "Adversos",
        dossier.summary["adverse_count"],
    )
    metrics[4].metric(
        "Objeciones pendientes",
        dossier.summary["unresolved_objection_count"],
    )
    st.caption(f"Huella argumental: {dossier.input_hash}")
    if dossier.unresolved_objection_codes:
        st.warning(
            "Argumentos adversos sin réplica: "
            + ", ".join(dossier.unresolved_objection_codes)
        )
    if dossier.orphan_argument_codes:
        st.info(
            "Argumentos sin relaciones: "
            + ", ".join(dossier.orphan_argument_codes)
        )
    if dossier.missing_information:
        with st.expander("Información faltante detectada", expanded=False):
            for item in dossier.missing_information:
                st.write(f"- {item}")
    else:
        st.success(
            "No se detectaron vacíos estructurales en la trazabilidad."
        )

    st.markdown("### Exportación")
    export_columns = st.columns(3)
    export_columns[0].download_button(
        "Descargar JSON",
        data=argumentation_service.export_json(case_id, issue_id),
        file_name=f"ius_razon_argumentacion_{issue_id[:8]}.json",
        mime="application/json",
        key=f"argumentation_json_{issue_id}",
    )
    export_columns[1].download_button(
        "Descargar Markdown",
        data=argumentation_service.export_markdown(case_id, issue_id),
        file_name=f"ius_razon_argumentacion_{issue_id[:8]}.md",
        mime="text/markdown",
        key=f"argumentation_markdown_{issue_id}",
    )
    export_columns[2].download_button(
        "Descargar DOCX",
        data=argumentation_service.export_docx(case_id, issue_id),
        file_name=f"ius_razon_argumentacion_{issue_id[:8]}.docx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        key=f"argumentation_docx_{issue_id}",
    )


def render_integral_report(case_id: str) -> None:
    """Configura, genera y exporta el informe jurídico integral."""

    st.subheader("Informe jurídico integral")
    st.warning(
        "El informe integra información registrada y resultados deterministas. "
        "No verifica fuentes externas, no predice decisiones y requiere revisión humana."
    )
    issues = reasoning_issue_options(case_id)
    if not issues:
        st.info("Primero registra un problema jurídico.")
        return

    issue_label = st.selectbox(
        "Problema jurídico",
        list(issues),
        key="integral_report_issue",
    )
    issue_id = issues[issue_label]
    runs = reasoning_service.list_runs(case_id, issue_id, limit=50)
    completed_runs = [
        run for run in runs if run.status.value == "Completada"
    ]
    if not completed_runs:
        st.info(
            "Ejecuta primero el razonamiento para seleccionar una instantánea."
        )
        return

    run_labels = {
        (
            f"{run.started_at.isoformat()} · {run.id[:8]} · "
            f"{run.summary.get('conclusion_count', 0)} conclusiones"
        ): run.id
        for run in completed_runs
    }
    scenarios = argumentation_service.list_scenarios(
        case_id,
        issue_id,
        include_archived=False,
    )
    scenario_options: dict[str, str | None] = {"Vista completa": None}
    scenario_options.update(
        {
            f"{scenario.code} · {scenario.name}": scenario.id
            for scenario in scenarios
        }
    )
    compared_options: dict[str, str | None] = {"Sin comparación": None}
    compared_options.update(
        {
            f"{scenario.code} · {scenario.name}": scenario.id
            for scenario in scenarios
        }
    )

    with st.form("integral_report_form"):
        run_label = st.selectbox(
            "Ejecución de inferencia *",
            list(run_labels),
        )
        columns = st.columns(2)
        base_label = columns[0].selectbox(
            "Escenario base",
            list(scenario_options),
        )
        compared_label = columns[1].selectbox(
            "Escenario comparado",
            list(compared_options),
        )
        title = st.text_input(
            "Título del informe *",
            value=f"Informe jurídico integral · {issue_label.split(' · ')[0]}",
            max_chars=240,
        )
        purpose = st.text_area(
            "Objeto y alcance *",
            value=(
                "Integrar los hechos, pruebas, fuentes, inferencia, argumentos "
                "y escenarios registrados para apoyar una revisión jurídica "
                "humana del problema seleccionado."
            ),
            max_chars=4000,
        )
        executive_summary = st.text_area(
            "Resumen ejecutivo opcional",
            placeholder=(
                "Déjalo vacío para generar un resumen descriptivo a partir "
                "de la instantánea seleccionada."
            ),
            max_chars=6000,
        )
        analyst_conclusions = st.text_area(
            "Conclusiones del analista",
            placeholder="Una conclusión por línea.",
        )
        recommendations = st.text_area(
            "Recomendaciones de revisión",
            placeholder=(
                "Una recomendación por línea. Déjalo vacío para usar "
                "recomendaciones técnicas de revisión."
            ),
        )
        additional_limitations = st.text_area(
            "Limitaciones adicionales",
            placeholder="Una limitación por línea.",
        )
        option_columns = st.columns(3)
        include_full_arguments = option_columns[0].checkbox(
            "Incluir desarrollo completo",
            value=True,
        )
        include_source_details = option_columns[1].checkbox(
            "Incluir detalle de fuentes",
            value=True,
        )
        include_traceability = option_columns[2].checkbox(
            "Incluir matriz de trazabilidad",
            value=True,
        )
        submitted = st.form_submit_button(
            "Generar informe integral",
            type="primary",
        )

    request_key = f"integral_report_request_{case_id}_{issue_id}"
    if submitted:
        try:
            request = IntegralReportRequest(
                case_id=case_id,
                issue_id=issue_id,
                reasoning_run_id=run_labels[run_label],
                title=title,
                purpose=purpose,
                executive_summary=executive_summary or None,
                base_scenario_id=scenario_options[base_label],
                compared_scenario_id=compared_options[compared_label],
                analyst_conclusions=parse_lines(analyst_conclusions),
                recommendations=parse_lines(recommendations),
                additional_limitations=parse_lines(additional_limitations),
                include_full_arguments=include_full_arguments,
                include_source_details=include_source_details,
                include_traceability_appendix=include_traceability,
            )
            report = legal_report_service.build_report(request)
            st.session_state[request_key] = request.model_dump(mode="json")
            st.success(
                "Informe generado. Huella: "
                f"{report.input_hash[:16]}…"
            )
        except Exception as exc:
            st.error(f"No fue posible generar el informe: {exc}")

    stored_request = st.session_state.get(request_key)
    if not isinstance(stored_request, dict):
        return

    try:
        request = IntegralReportRequest.model_validate(stored_request)
        report = legal_report_service.build_report(request)
    except Exception as exc:
        st.error(f"No fue posible reconstruir el informe: {exc}")
        return

    st.markdown("### Vista previa")
    metrics = st.columns(5)
    metrics[0].metric(
        "Conclusiones",
        len(report.reasoning.conclusions),
    )
    metrics[1].metric(
        "Argumentos",
        len(report.argumentation.arguments),
    )
    metrics[2].metric(
        "Relaciones",
        len(report.argumentation.relations),
    )
    metrics[3].metric(
        "Objeciones pendientes",
        len(report.argumentation.unresolved_objection_codes),
    )
    metrics[4].metric(
        "Limitaciones",
        len(report.limitations),
    )
    st.caption(
        f"Versión {report.report_version} · "
        f"instantánea {report.generated_at.isoformat()} · "
        f"huella {report.input_hash}"
    )
    st.markdown("#### Resumen ejecutivo")
    st.write(report.executive_summary)
    st.markdown("#### Hallazgos")
    for finding in report.findings:
        st.write(f"- {finding}")
    if report.scenario_narrative is not None:
        with st.expander("Comparación narrativa de escenarios", expanded=True):
            st.write(
                f"**Base:** {report.scenario_narrative.base_label}"
            )
            st.write(
                f"**Comparado:** {report.scenario_narrative.compared_label}"
            )
            for statement in report.scenario_narrative.statements:
                st.write(f"- {statement}")
    with st.expander("Limitaciones e información faltante", expanded=False):
        for limitation in report.limitations:
            st.write(f"- {limitation}")

    st.markdown("### Exportación integral")
    exports = st.columns(3)
    exports[0].download_button(
        "Descargar JSON integral",
        data=legal_report_service.export_json(request),
        file_name=f"ius_razon_informe_integral_{issue_id[:8]}.json",
        mime="application/json",
        key=f"integral_json_{issue_id}_{report.input_hash[:8]}",
    )
    exports[1].download_button(
        "Descargar Markdown integral",
        data=legal_report_service.export_markdown(request),
        file_name=f"ius_razon_informe_integral_{issue_id[:8]}.md",
        mime="text/markdown",
        key=f"integral_markdown_{issue_id}_{report.input_hash[:8]}",
    )
    exports[2].download_button(
        "Descargar DOCX integral",
        data=legal_report_service.export_docx(request),
        file_name=f"ius_razon_informe_integral_{issue_id[:8]}.docx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        key=f"integral_docx_{issue_id}_{report.input_hash[:8]}",
    )


def main() -> None:
    st.title("⚖️ IUS-Razón")
    st.caption("Sistema de Análisis, Argumentación y Estrategia Jurídica · Sprint 4.3.1 v0.5.1")
    render_notice()

    with st.sidebar:
        st.header("Expedientes")
        selected_case_id = case_selector()
        with st.expander("Crear expediente", expanded=selected_case_id is None):
            create_case_form()
        with st.expander("Persistencia", expanded=False):
            st.caption("Base SQLite activa")
            st.code(str(app_config.db_path))
            st.caption("Directorio de datos")
            st.code(str(app_config.data_dir))
            if startup_backup is not None:
                st.success(f"Respaldo creado: {startup_backup.name}")
            else:
                st.info("No se creó respaldo porque la base era nueva o estaba vacía.")

    if selected_case_id is None:
        st.markdown(
            """
            ### Comienza creando un expediente

            Sprint 4.3.1 conserva el asistente IA controlado en modo
            simulado local, con selección explícita de contexto, anonimización,
            referencias internas, detección de afirmaciones sin respaldo y
            revisión humana obligatoria.
            """
        )
        return

    tabs = st.tabs(
        [
            "Resumen",
            "Partes",
            "Hechos",
            "Pruebas",
            "Hecho–prueba",
            "Problemas jurídicos",
            "Normas",
            "Jurisprudencia",
            "Doctrina",
            "Matriz problema–fuente",
            "Premisas",
            "Reglas",
            "Inferencia",
            "Argumentación",
            "Informe integral",
            "Asistente IA",
            "Gestión razonamiento",
            "Corrección segura",
        ]
    )
    with tabs[0]:
        render_summary(selected_case_id)
    with tabs[1]:
        render_parties(selected_case_id)
    with tabs[2]:
        render_facts(selected_case_id)
    with tabs[3]:
        render_evidence(selected_case_id)
    with tabs[4]:
        render_fact_evidence_links(selected_case_id)
    with tabs[5]:
        render_legal_issues(selected_case_id)
    with tabs[6]:
        render_norms(selected_case_id)
    with tabs[7]:
        render_jurisprudence(selected_case_id)
    with tabs[8]:
        render_doctrine(selected_case_id)
    with tabs[9]:
        render_issue_source_matrix(selected_case_id)
    with tabs[10]:
        render_reasoning_assertions(selected_case_id)
    with tabs[11]:
        render_reasoning_rules(selected_case_id)
    with tabs[12]:
        render_reasoning_inference(selected_case_id)
    with tabs[13]:
        render_argumentation(selected_case_id)
    with tabs[14]:
        render_integral_report(selected_case_id)
    with tabs[15]:
        render_llm_assistant(
            selected_case_id,
            case_service=service,
            reasoning_service=reasoning_service,
            assistant_service=llm_assistant_service,
        )
    with tabs[16]:
        render_reasoning_management(selected_case_id)
    with tabs[17]:
        render_safe_correction(selected_case_id)


if __name__ == "__main__":
    main()
