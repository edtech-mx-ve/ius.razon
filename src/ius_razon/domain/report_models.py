from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ius_razon.domain.argumentation_models import (
    ArgumentationDossier,
    ArgumentGraphSnapshot,
    ScenarioComparison,
)
from ius_razon.domain.models import (
    CaseRecord,
    DoctrineRecord,
    EvidenceRecord,
    FactEvidenceLinkView,
    FactRecord,
    IssueSourceLinkView,
    JurisprudenceRecord,
    LegalIssueRecord,
    NormRecord,
    PartyRecord,
)
from ius_razon.domain.reasoning_models import ReasoningRunReport


class ReportModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class IntegralReportRequest(ReportModel):
    case_id: Annotated[str, Field(min_length=1, max_length=300)]
    issue_id: Annotated[str, Field(min_length=1, max_length=300)]
    reasoning_run_id: Annotated[str, Field(min_length=1, max_length=300)]
    title: Annotated[str, Field(min_length=5, max_length=240)]
    purpose: Annotated[str, Field(min_length=10, max_length=4000)]
    executive_summary: str | None = Field(default=None, max_length=6000)
    base_scenario_id: str | None = Field(default=None, max_length=300)
    compared_scenario_id: str | None = Field(default=None, max_length=300)
    analyst_conclusions: list[str] = Field(default_factory=list, max_length=30)
    recommendations: list[str] = Field(default_factory=list, max_length=30)
    additional_limitations: list[str] = Field(default_factory=list, max_length=30)
    include_full_arguments: bool = True
    include_source_details: bool = True
    include_traceability_appendix: bool = True

    @field_validator(
        "analyst_conclusions",
        "recommendations",
        "additional_limitations",
    )
    @classmethod
    def normalize_lines(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip()
            if not item or item in normalized:
                continue
            if len(item) > 1200:
                raise ValueError("Cada elemento admite hasta 1200 caracteres.")
            normalized.append(item)
        return normalized

    @model_validator(mode="after")
    def validate_scenario_pair(self) -> IntegralReportRequest:
        if (
            self.base_scenario_id is not None
            and self.compared_scenario_id is not None
            and self.base_scenario_id == self.compared_scenario_id
        ):
            raise ValueError("Los escenarios base y comparado deben ser distintos.")
        return self


class TraceabilityRow(ReportModel):
    argument_code: str
    position: str
    thesis: str
    conclusion_code: str | None
    origin: str
    fact_codes: list[str]
    evidence_codes: list[str]
    source_codes: list[str]
    rule_codes: list[str]
    assertion_codes: list[str]
    support_level: str
    support_score: int = Field(ge=0, le=5)


class ScenarioNarrative(ReportModel):
    base_label: str
    compared_label: str
    statements: list[str]


class IntegralLegalReport(ReportModel):
    report_version: str
    generated_at: datetime
    input_hash: str
    request: IntegralReportRequest
    case: CaseRecord
    issue: LegalIssueRecord
    parties: list[PartyRecord]
    facts: list[FactRecord]
    evidence: list[EvidenceRecord]
    fact_evidence_links: list[FactEvidenceLinkView]
    norms: list[NormRecord]
    jurisprudence: list[JurisprudenceRecord]
    doctrine: list[DoctrineRecord]
    issue_source_links: list[IssueSourceLinkView]
    reasoning: ReasoningRunReport
    argumentation: ArgumentationDossier
    base_graph: ArgumentGraphSnapshot
    compared_graph: ArgumentGraphSnapshot | None
    scenario_comparison: ScenarioComparison | None
    scenario_narrative: ScenarioNarrative | None
    executive_summary: str
    methodology: list[str]
    findings: list[str]
    limitations: list[str]
    recommendations: list[str]
    traceability_rows: list[TraceabilityRow]
    section_index: list[str]
    warning: str
