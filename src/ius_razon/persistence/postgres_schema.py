from __future__ import annotations

from pathlib import Path

SCHEMA_VERSION = "5.4.1"
SCHEMA_FILE_NAME = "postgres_schema_v5_4.sql"
METADATA_TABLE = "ius_schema_metadata"

APPLICATION_TABLES = frozenset(
    {
        "cases",
        "parties",
        "facts",
        "evidence",
        "fact_evidence",
        "legal_issues",
        "norms",
        "jurisprudence",
        "doctrine",
        "issue_source_links",
        "code_sequences",
        "audit_events",
        "reasoning_assertions",
        "reasoning_rules",
        "reasoning_rule_conditions",
        "reasoning_assertion_versions",
        "reasoning_rule_versions",
        "reasoning_runs",
        "reasoning_conclusions",
        "reasoning_traces",
        "reasoning_sequences",
        "legal_arguments",
        "argument_relations",
        "argument_sequences",
        "argument_scenarios",
        "llm_draft_sequences",
        "llm_drafts",
        "llm_provider_calls",
    }
)


def schema_path(project_root: Path) -> Path:
    return project_root.resolve() / "sql" / SCHEMA_FILE_NAME


def load_schema_text(project_root: Path) -> str:
    path = schema_path(project_root)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el esquema PostgreSQL: {path.name}")
    return path.read_text(encoding="utf-8")


def schema_statements(project_root: Path) -> tuple[str, ...]:
    statements = tuple(
        statement.strip()
        for statement in load_schema_text(project_root).split(";")
        if statement.strip()
    )
    if not statements:
        raise ValueError("El esquema PostgreSQL está vacío.")
    return statements
