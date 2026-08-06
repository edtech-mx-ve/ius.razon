from __future__ import annotations

from enum import StrEnum


class CaseStatus(StrEnum):
    OPEN = "Abierto"
    UNDER_REVIEW = "En revisión"
    CLOSED = "Cerrado"
    ARCHIVED = "Archivado"


class ConfidentialityLevel(StrEnum):
    PUBLIC_DEMO = "Demo pública"
    INTERNAL = "Uso interno"
    CONFIDENTIAL = "Confidencial"


class PartyType(StrEnum):
    NATURAL_PERSON = "Persona física"
    LEGAL_ENTITY = "Persona moral"
    PUBLIC_AUTHORITY = "Autoridad"
    OTHER = "Otro"


class PartyRole(StrEnum):
    CLAIMANT = "Promovente / actora"
    RESPONDENT = "Demandada / contraparte"
    REPRESENTATIVE = "Representante"
    THIRD_PARTY = "Tercero"
    INTERESTED_PARTY = "Interesado"
    OTHER = "Otro"


class FactStatus(StrEnum):
    ALLEGED = "Alegado"
    ADMITTED = "Admitido"
    DISPUTED = "Controvertido"
    SUPPORTED = "Acreditado"
    UNSUPPORTED = "No acreditado"
    INFERRED = "Inferido"
    DISCARDED = "Descartado"
    UNKNOWN = "Desconocido"


class EvidenceType(StrEnum):
    CONTRACT = "Contrato"
    DOCUMENT = "Documento"
    COMMUNICATION = "Comunicación"
    RECEIPT = "Comprobante"
    TESTIMONY = "Testimonio registrado"
    EXPERT_REPORT = "Dictamen"
    IMAGE = "Imagen"
    DIGITAL_RECORD = "Evidencia digital"
    OTHER = "Otra"


class EvidenceEvaluationStatus(StrEnum):
    PENDING = "Pendiente"
    OFFERED = "Ofrecida"
    OBJECTED = "Objetada"
    SUPPORTED = "Con soporte inicial"
    INSUFFICIENT = "Insuficiente"
    DISCARDED = "Descartada"


class LegalIssueStatus(StrEnum):
    OPEN = "Abierto"
    UNDER_ANALYSIS = "En análisis"
    RESOLVED = "Resuelto"
    DISCARDED = "Descartado"


class LegalSourceType(StrEnum):
    NORM = "Norma"
    JURISPRUDENCE = "Jurisprudencia"
    DOCTRINE = "Doctrina"


class NormHierarchy(StrEnum):
    CONSTITUTIONAL = "Constitucional"
    TREATY = "Tratado internacional"
    FEDERAL_LAW = "Ley federal"
    LOCAL_LAW = "Ley local"
    REGULATION = "Reglamento"
    ADMINISTRATIVE_RULE = "Disposición administrativa"
    CONTRACTUAL = "Disposición contractual"
    OTHER = "Otra"


class JurisprudenceAuthority(StrEnum):
    BINDING = "Obligatoria"
    ORIENTATIVE = "Orientadora"
    PENDING_VERIFICATION = "Pendiente de verificar"


class SourceOrientation(StrEnum):
    SUPPORTS = "Favorable"
    OPPOSES = "Adversa"
    NEUTRAL = "Neutral"
    CONTEXTUAL = "Contextual"
