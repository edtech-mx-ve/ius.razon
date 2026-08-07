from __future__ import annotations

import logging

from ius_razon.config import AppConfig
from ius_razon.domain.enums import LegalSourceType
from ius_razon.domain.models import (
    AuditEventRecord,
    CaseCreate,
    CaseRecord,
    CaseSummary,
    DoctrineCreate,
    DoctrineRecord,
    EvidenceCreate,
    EvidenceRecord,
    FactCreate,
    FactEvidenceLinkView,
    FactRecord,
    IssueSourceLinkCreate,
    IssueSourceLinkView,
    JurisprudenceCreate,
    JurisprudenceRecord,
    LegalIssueCreate,
    LegalIssueRecord,
    NormCreate,
    NormRecord,
    PartyCreate,
    PartyRecord,
)
from ius_razon.persistence.case_repository import CaseRepository
from ius_razon.persistence.mutation_backup import MutationBackup
from ius_razon.security.files import StoredFile, store_uploaded_file

LOGGER = logging.getLogger(__name__)


class CaseService:
    """Orquesta casos de uso sin exponer detalles de persistencia a la interfaz."""

    def __init__(
        self,
        repository: CaseRepository,
        config: AppConfig,
        mutation_backup: MutationBackup,
    ) -> None:
        self._repository = repository
        self._config = config
        self._mutation_backup = mutation_backup

    def create_case(self, payload: CaseCreate) -> CaseRecord:
        record = self._repository.create_case(payload)
        LOGGER.info("Expediente creado. case_id=%s", record.id)
        return record

    def list_cases(self) -> list[CaseRecord]:
        return self._repository.list_cases()

    def get_case_summary(self, case_id: str) -> CaseSummary:
        case = self._repository.get_case(case_id)
        return CaseSummary(
            case=case,
            party_count=self._repository.count_by_case("parties", case_id),
            fact_count=self._repository.count_by_case("facts", case_id),
            evidence_count=self._repository.count_by_case("evidence", case_id),
            link_count=self._repository.count_links(case_id),
            legal_issue_count=self._repository.count_by_case("legal_issues", case_id),
            norm_count=self._repository.count_by_case("norms", case_id),
            jurisprudence_count=self._repository.count_by_case(
                "jurisprudence",
                case_id,
            ),
            doctrine_count=self._repository.count_by_case("doctrine", case_id),
            issue_source_link_count=self._repository.count_issue_source_links(case_id),
        )

    def update_case(
        self,
        case_id: str,
        payload: CaseCreate,
    ) -> CaseRecord:
        self._backup_before_mutation()
        record = self._repository.update_case(case_id, payload)
        LOGGER.info("Expediente actualizado. case_id=%s", case_id)
        return record

    def add_party(self, payload: PartyCreate) -> PartyRecord:
        record = self._repository.add_party(payload)
        LOGGER.info("Parte agregada. case_id=%s party_id=%s", payload.case_id, record.id)
        return record

    def list_parties(self, case_id: str) -> list[PartyRecord]:
        return self._repository.list_parties(case_id)

    def add_fact(self, payload: FactCreate) -> FactRecord:
        record = self._repository.add_fact(payload)
        LOGGER.info("Hecho agregado. case_id=%s fact_id=%s", payload.case_id, record.id)
        return record

    def list_facts(self, case_id: str) -> list[FactRecord]:
        return self._repository.list_facts(case_id)

    def add_evidence(
        self,
        payload: EvidenceCreate,
        *,
        original_file_name: str | None,
        file_content: bytes | None,
    ) -> EvidenceRecord:
        stored = self._store_optional_file(
            case_id=payload.case_id,
            original_file_name=original_file_name,
            file_content=file_content,
        )
        record = self._repository.add_evidence(
            payload,
            original_file_name=stored.original_name if stored else None,
            stored_file_name=stored.stored_name if stored else None,
            file_sha256=stored.sha256 if stored else None,
            file_size=stored.size if stored else None,
        )
        LOGGER.info(
            "Prueba agregada. case_id=%s evidence_id=%s has_file=%s",
            payload.case_id,
            record.id,
            stored is not None,
        )
        return record

    def list_evidence(self, case_id: str) -> list[EvidenceRecord]:
        return self._repository.list_evidence(case_id)

    def link_fact_evidence(
        self,
        *,
        case_id: str,
        fact_id: str,
        evidence_id: str,
        purpose: str | None,
    ) -> None:
        self._repository.link_fact_evidence(
            case_id=case_id,
            fact_id=fact_id,
            evidence_id=evidence_id,
            purpose=purpose,
        )
        LOGGER.info(
            "Vínculo hecho-prueba creado. case_id=%s fact_id=%s evidence_id=%s",
            case_id,
            fact_id,
            evidence_id,
        )

    def list_fact_evidence_links(self, case_id: str) -> list[FactEvidenceLinkView]:
        return self._repository.list_fact_evidence_links(case_id)

    def add_legal_issue(self, payload: LegalIssueCreate) -> LegalIssueRecord:
        record = self._repository.add_legal_issue(payload)
        LOGGER.info(
            "Problema jurídico agregado. case_id=%s issue_id=%s",
            payload.case_id,
            record.id,
        )
        return record

    def list_legal_issues(self, case_id: str) -> list[LegalIssueRecord]:
        return self._repository.list_legal_issues(case_id)

    def add_norm(
        self,
        payload: NormCreate,
        *,
        original_file_name: str | None,
        file_content: bytes | None,
    ) -> NormRecord:
        stored = self._store_optional_file(
            case_id=payload.case_id,
            original_file_name=original_file_name,
            file_content=file_content,
        )
        record = self._repository.add_norm(
            payload,
            original_file_name=stored.original_name if stored else None,
            stored_file_name=stored.stored_name if stored else None,
            file_sha256=stored.sha256 if stored else None,
            file_size=stored.size if stored else None,
        )
        LOGGER.info(
            "Norma agregada. case_id=%s norm_id=%s has_file=%s",
            payload.case_id,
            record.id,
            stored is not None,
        )
        return record

    def list_norms(self, case_id: str) -> list[NormRecord]:
        return self._repository.list_norms(case_id)

    def add_jurisprudence(
        self,
        payload: JurisprudenceCreate,
        *,
        original_file_name: str | None,
        file_content: bytes | None,
    ) -> JurisprudenceRecord:
        stored = self._store_optional_file(
            case_id=payload.case_id,
            original_file_name=original_file_name,
            file_content=file_content,
        )
        record = self._repository.add_jurisprudence(
            payload,
            original_file_name=stored.original_name if stored else None,
            stored_file_name=stored.stored_name if stored else None,
            file_sha256=stored.sha256 if stored else None,
            file_size=stored.size if stored else None,
        )
        LOGGER.info(
            "Jurisprudencia agregada. case_id=%s jurisprudence_id=%s has_file=%s",
            payload.case_id,
            record.id,
            stored is not None,
        )
        return record

    def list_jurisprudence(self, case_id: str) -> list[JurisprudenceRecord]:
        return self._repository.list_jurisprudence(case_id)

    def add_doctrine(
        self,
        payload: DoctrineCreate,
        *,
        original_file_name: str | None,
        file_content: bytes | None,
    ) -> DoctrineRecord:
        stored = self._store_optional_file(
            case_id=payload.case_id,
            original_file_name=original_file_name,
            file_content=file_content,
        )
        record = self._repository.add_doctrine(
            payload,
            original_file_name=stored.original_name if stored else None,
            stored_file_name=stored.stored_name if stored else None,
            file_sha256=stored.sha256 if stored else None,
            file_size=stored.size if stored else None,
        )
        LOGGER.info(
            "Doctrina agregada. case_id=%s doctrine_id=%s has_file=%s",
            payload.case_id,
            record.id,
            stored is not None,
        )
        return record

    def list_doctrine(self, case_id: str) -> list[DoctrineRecord]:
        return self._repository.list_doctrine(case_id)

    def link_issue_source(self, payload: IssueSourceLinkCreate) -> None:
        self._backup_before_mutation()
        self._repository.link_issue_source(payload)
        LOGGER.info(
            "Fuente vinculada a problema. case_id=%s issue_id=%s source_id=%s",
            payload.case_id,
            payload.issue_id,
            payload.source_id,
        )

    def list_issue_source_links(self, case_id: str) -> list[IssueSourceLinkView]:
        return self._repository.list_issue_source_links(case_id)


    def update_legal_issue(
        self,
        issue_id: str,
        payload: LegalIssueCreate,
    ) -> LegalIssueRecord:
        self._backup_before_mutation()
        record = self._repository.update_legal_issue(issue_id, payload)
        LOGGER.info(
            "Problema jurídico actualizado. case_id=%s issue_id=%s",
            payload.case_id,
            issue_id,
        )
        return record

    def delete_legal_issue(
        self,
        *,
        issue_id: str,
        case_id: str,
        confirmation_code: str,
    ) -> None:
        record = self._repository.get_legal_issue(issue_id)
        self._validate_confirmation(record.code, confirmation_code)
        self._backup_before_mutation()
        self._repository.delete_legal_issue(issue_id, case_id)
        LOGGER.info(
            "Problema jurídico eliminado. case_id=%s issue_id=%s",
            case_id,
            issue_id,
        )

    def update_norm(
        self,
        norm_id: str,
        payload: NormCreate,
        *,
        original_file_name: str | None,
        file_content: bytes | None,
    ) -> NormRecord:
        existing = self._repository.get_norm(norm_id)
        self._backup_before_mutation()
        stored = self._store_optional_file(
            case_id=payload.case_id,
            original_file_name=original_file_name,
            file_content=file_content,
        )
        (
            original_name,
            stored_name,
            sha256,
            size,
        ) = self._replacement_metadata(existing, stored)
        try:
            record = self._repository.update_norm(
                norm_id,
                payload,
                original_file_name=original_name,
                stored_file_name=stored_name,
                file_sha256=sha256,
                file_size=size,
            )
        except Exception:
            self._remove_stored_upload(payload.case_id, stored.stored_name if stored else None)
            raise
        self._remove_replaced_upload(
            payload.case_id,
            existing.stored_file_name,
            stored.stored_name if stored else None,
        )
        LOGGER.info("Norma actualizada. case_id=%s norm_id=%s", payload.case_id, norm_id)
        return record

    def update_jurisprudence(
        self,
        jurisprudence_id: str,
        payload: JurisprudenceCreate,
        *,
        original_file_name: str | None,
        file_content: bytes | None,
    ) -> JurisprudenceRecord:
        existing = self._repository.get_jurisprudence(jurisprudence_id)
        self._backup_before_mutation()
        stored = self._store_optional_file(
            case_id=payload.case_id,
            original_file_name=original_file_name,
            file_content=file_content,
        )
        (
            original_name,
            stored_name,
            sha256,
            size,
        ) = self._replacement_metadata(existing, stored)
        try:
            record = self._repository.update_jurisprudence(
                jurisprudence_id,
                payload,
                original_file_name=original_name,
                stored_file_name=stored_name,
                file_sha256=sha256,
                file_size=size,
            )
        except Exception:
            self._remove_stored_upload(payload.case_id, stored.stored_name if stored else None)
            raise
        self._remove_replaced_upload(
            payload.case_id,
            existing.stored_file_name,
            stored.stored_name if stored else None,
        )
        LOGGER.info(
            "Jurisprudencia actualizada. case_id=%s jurisprudence_id=%s",
            payload.case_id,
            jurisprudence_id,
        )
        return record

    def update_doctrine(
        self,
        doctrine_id: str,
        payload: DoctrineCreate,
        *,
        original_file_name: str | None,
        file_content: bytes | None,
    ) -> DoctrineRecord:
        existing = self._repository.get_doctrine(doctrine_id)
        self._backup_before_mutation()
        stored = self._store_optional_file(
            case_id=payload.case_id,
            original_file_name=original_file_name,
            file_content=file_content,
        )
        (
            original_name,
            stored_name,
            sha256,
            size,
        ) = self._replacement_metadata(existing, stored)
        try:
            record = self._repository.update_doctrine(
                doctrine_id,
                payload,
                original_file_name=original_name,
                stored_file_name=stored_name,
                file_sha256=sha256,
                file_size=size,
            )
        except Exception:
            self._remove_stored_upload(payload.case_id, stored.stored_name if stored else None)
            raise
        self._remove_replaced_upload(
            payload.case_id,
            existing.stored_file_name,
            stored.stored_name if stored else None,
        )
        LOGGER.info(
            "Doctrina actualizada. case_id=%s doctrine_id=%s",
            payload.case_id,
            doctrine_id,
        )
        return record

    def delete_norm(
        self,
        *,
        norm_id: str,
        case_id: str,
        confirmation_code: str,
    ) -> None:
        record = self._repository.get_norm(norm_id)
        self._delete_source_record(
            case_id=case_id,
            source_type=LegalSourceType.NORM,
            source_id=norm_id,
            source_code=record.code,
            stored_file_name=record.stored_file_name,
            confirmation_code=confirmation_code,
        )

    def delete_jurisprudence(
        self,
        *,
        jurisprudence_id: str,
        case_id: str,
        confirmation_code: str,
    ) -> None:
        record = self._repository.get_jurisprudence(jurisprudence_id)
        self._delete_source_record(
            case_id=case_id,
            source_type=LegalSourceType.JURISPRUDENCE,
            source_id=jurisprudence_id,
            source_code=record.code,
            stored_file_name=record.stored_file_name,
            confirmation_code=confirmation_code,
        )

    def delete_doctrine(
        self,
        *,
        doctrine_id: str,
        case_id: str,
        confirmation_code: str,
    ) -> None:
        record = self._repository.get_doctrine(doctrine_id)
        self._delete_source_record(
            case_id=case_id,
            source_type=LegalSourceType.DOCTRINE,
            source_id=doctrine_id,
            source_code=record.code,
            stored_file_name=record.stored_file_name,
            confirmation_code=confirmation_code,
        )

    def update_issue_source_link(self, payload: IssueSourceLinkCreate) -> None:
        self._backup_before_mutation()
        self._repository.update_issue_source_link(payload)
        LOGGER.info(
            "Vínculo problema-fuente actualizado. case_id=%s issue_id=%s source_id=%s",
            payload.case_id,
            payload.issue_id,
            payload.source_id,
        )

    def unlink_issue_source(
        self,
        *,
        case_id: str,
        issue_id: str,
        source_type: LegalSourceType,
        source_id: str,
        confirmation_code: str,
    ) -> None:
        _, source_code, _ = self._repository.get_source_identity(source_type, source_id)
        expected = f"{source_code}"
        self._validate_confirmation(expected, confirmation_code)
        self._backup_before_mutation()
        self._repository.unlink_issue_source(
            case_id=case_id,
            issue_id=issue_id,
            source_type=source_type,
            source_id=source_id,
        )
        LOGGER.info(
            "Vínculo problema-fuente eliminado. case_id=%s issue_id=%s source_id=%s",
            case_id,
            issue_id,
            source_id,
        )

    def _delete_source_record(
        self,
        *,
        case_id: str,
        source_type: LegalSourceType,
        source_id: str,
        source_code: str,
        stored_file_name: str | None,
        confirmation_code: str,
    ) -> None:
        self._validate_confirmation(source_code, confirmation_code)
        self._backup_before_mutation()
        self._repository.delete_source(
            case_id=case_id,
            source_type=source_type,
            source_id=source_id,
        )
        self._archive_stored_upload(case_id, stored_file_name)
        LOGGER.info(
            "Fuente jurídica eliminada. case_id=%s source_type=%s source_id=%s",
            case_id,
            source_type.value,
            source_id,
        )

    def _backup_before_mutation(self) -> None:
        self._mutation_backup.before_mutation()
        LOGGER.info("Política de respaldo previo completada.")

    @staticmethod
    def _validate_confirmation(expected_code: str, confirmation_code: str) -> None:
        if confirmation_code.strip() != expected_code:
            raise ValueError(f"Escribe exactamente {expected_code} para confirmar.")

    @staticmethod
    def _replacement_metadata(
        existing: NormRecord | JurisprudenceRecord | DoctrineRecord,
        stored: StoredFile | None,
    ) -> tuple[str | None, str | None, str | None, int | None]:
        if stored is not None:
            return (
                stored.original_name,
                stored.stored_name,
                stored.sha256,
                stored.size,
            )
        return (
            existing.original_file_name,
            existing.stored_file_name,
            existing.file_sha256,
            existing.file_size,
        )

    def _remove_replaced_upload(
        self,
        case_id: str,
        previous_stored_name: str | None,
        new_stored_name: str | None,
    ) -> None:
        if (
            previous_stored_name
            and new_stored_name
            and previous_stored_name != new_stored_name
        ):
            self._archive_stored_upload(case_id, previous_stored_name)

    def _archive_stored_upload(
        self,
        case_id: str,
        stored_file_name: str | None,
    ) -> None:
        if not stored_file_name:
            return
        case_dir = (self._config.upload_dir / case_id).resolve()
        source = (case_dir / stored_file_name).resolve()
        if case_dir not in source.parents or not source.is_file():
            return

        archive_dir = (
            self._config.data_dir / "archived_uploads" / case_id
        ).resolve()
        archive_dir.mkdir(parents=True, exist_ok=True)
        destination = (archive_dir / stored_file_name).resolve()
        if archive_dir not in destination.parents:
            LOGGER.warning("Se evitó archivar un archivo fuera del expediente.")
            return
        try:
            source.replace(destination)
        except OSError as exc:
            LOGGER.warning("No fue posible archivar el archivo reemplazado: %s", exc)

    def _remove_stored_upload(
        self,
        case_id: str,
        stored_file_name: str | None,
    ) -> None:
        if not stored_file_name:
            return
        case_dir = (self._config.upload_dir / case_id).resolve()
        target = (case_dir / stored_file_name).resolve()
        if case_dir not in target.parents:
            LOGGER.warning("Se evitó eliminar un archivo fuera del expediente.")
            return
        try:
            target.unlink(missing_ok=True)
        except OSError as exc:
            LOGGER.warning("No fue posible eliminar el archivo reemplazado: %s", exc)

    def list_audit_events(self, case_id: str, limit: int = 50) -> list[AuditEventRecord]:
        return self._repository.list_audit_events(case_id, limit=limit)

    def _store_optional_file(
        self,
        *,
        case_id: str,
        original_file_name: str | None,
        file_content: bytes | None,
    ) -> StoredFile | None:
        if original_file_name is None and file_content is None:
            return None
        if original_file_name is None or file_content is None:
            raise ValueError(
                "El nombre y el contenido del archivo deben proporcionarse juntos."
            )
        return store_uploaded_file(
            case_id=case_id,
            original_name=original_file_name,
            content=file_content,
            upload_root=self._config.upload_dir,
            max_size_bytes=self._config.max_upload_bytes,
        )
