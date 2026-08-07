CREATE TABLE IF NOT EXISTS ius_schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            matter TEXT NOT NULL,
            jurisdiction TEXT NOT NULL,
            location TEXT,
            opened_on TEXT NOT NULL,
            status TEXT NOT NULL,
            objective TEXT,
            user_role TEXT,
            confidentiality TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS parties (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            name_alias TEXT NOT NULL,
            party_type TEXT NOT NULL,
            legal_role TEXT NOT NULL,
            representation TEXT,
            claim TEXT,
            position TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS facts (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            description TEXT NOT NULL,
            event_date TEXT,
            actor_party_id TEXT REFERENCES parties(id) ON DELETE SET NULL,
            action TEXT,
            object_text TEXT,
            place TEXT,
            source TEXT,
            status TEXT NOT NULL,
            controversy_level INTEGER NOT NULL CHECK (controversy_level BETWEEN 0 AND 5),
            created_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS evidence (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            description TEXT NOT NULL,
            origin TEXT,
            evidence_date TEXT,
            integrity_statement TEXT,
            offering_party_id TEXT REFERENCES parties(id) ON DELETE SET NULL,
            objections TEXT,
            observations TEXT,
            evaluation_status TEXT NOT NULL,
            original_file_name TEXT,
            stored_file_name TEXT,
            file_sha256 TEXT,
            file_size INTEGER,
            created_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS fact_evidence (
            fact_id TEXT NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
            evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
            purpose TEXT,
            PRIMARY KEY (fact_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS legal_issues (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            title TEXT NOT NULL,
            question TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS norms (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            jurisdiction TEXT NOT NULL,
            matter TEXT NOT NULL,
            instrument TEXT NOT NULL,
            article TEXT NOT NULL,
            text TEXT NOT NULL,
            hierarchy TEXT NOT NULL,
            publication_date TEXT,
            valid_from TEXT,
            valid_to TEXT,
            version_label TEXT,
            source_reference TEXT,
            notes TEXT,
            original_file_name TEXT,
            stored_file_name TEXT,
            file_sha256 TEXT,
            file_size INTEGER,
            created_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS jurisprudence (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            court TEXT NOT NULL,
            identifier TEXT NOT NULL,
            jurisdiction TEXT NOT NULL,
            matter TEXT NOT NULL,
            decision_date TEXT,
            relevant_facts TEXT NOT NULL,
            legal_question TEXT NOT NULL,
            criterion TEXT NOT NULL,
            decision TEXT,
            interpreted_norms TEXT,
            authority TEXT NOT NULL,
            source_reference TEXT,
            similarities TEXT,
            differences TEXT,
            original_file_name TEXT,
            stored_file_name TEXT,
            file_sha256 TEXT,
            file_size INTEGER,
            created_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS doctrine (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            author TEXT NOT NULL,
            work_title TEXT NOT NULL,
            edition TEXT,
            publication_year INTEGER,
            concept TEXT NOT NULL,
            position_summary TEXT NOT NULL,
            excerpt TEXT,
            citation TEXT NOT NULL,
            argumentative_function TEXT,
            source_reference TEXT,
            original_file_name TEXT,
            stored_file_name TEXT,
            file_sha256 TEXT,
            file_size INTEGER,
            created_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS issue_source_links (
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            orientation TEXT NOT NULL,
            applicability TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (issue_id, source_type, source_id)
        );

        CREATE TABLE IF NOT EXISTS code_sequences (
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            table_name TEXT NOT NULL,
            last_value INTEGER NOT NULL CHECK(last_value >= 0),
            PRIMARY KEY (case_id, table_name)
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY,
            case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            detail_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_parties_case_id ON parties(case_id);
        CREATE INDEX IF NOT EXISTS idx_facts_case_id ON facts(case_id);
        CREATE INDEX IF NOT EXISTS idx_evidence_case_id ON evidence(case_id);
        CREATE INDEX IF NOT EXISTS idx_issues_case_id ON legal_issues(case_id);
        CREATE INDEX IF NOT EXISTS idx_norms_case_id ON norms(case_id);
        CREATE INDEX IF NOT EXISTS idx_jurisprudence_case_id ON jurisprudence(case_id);
        CREATE INDEX IF NOT EXISTS idx_doctrine_case_id ON doctrine(case_id);
        CREATE INDEX IF NOT EXISTS idx_issue_source_issue_id
            ON issue_source_links(issue_id);
        CREATE INDEX IF NOT EXISTS idx_audit_case_id ON audit_events(case_id);

CREATE TABLE IF NOT EXISTS reasoning_assertions (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            predicate_key TEXT NOT NULL,
            statement TEXT NOT NULL,
            value TEXT NOT NULL,
            basis TEXT NOT NULL,
            support_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS reasoning_rules (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            conclusion_key TEXT NOT NULL,
            conclusion_statement TEXT NOT NULL,
            conclusion_value TEXT NOT NULL,
            priority INTEGER NOT NULL CHECK(priority BETWEEN 0 AND 1000),
            active INTEGER NOT NULL CHECK(active IN (0, 1)),
            legal_basis_codes_json TEXT NOT NULL,
            explanation TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS reasoning_rule_conditions (
            id TEXT PRIMARY KEY,
            rule_id TEXT NOT NULL REFERENCES reasoning_rules(id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            role TEXT NOT NULL,
            predicate_key TEXT NOT NULL,
            expected_value TEXT NOT NULL,
            UNIQUE(rule_id, position)
        );

        CREATE TABLE IF NOT EXISTS reasoning_assertion_versions (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            entity_code TEXT NOT NULL,
            version_number INTEGER NOT NULL CHECK(version_number >= 1),
            action TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(entity_id, version_number)
        );

        CREATE TABLE IF NOT EXISTS reasoning_rule_versions (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            entity_code TEXT NOT NULL,
            version_number INTEGER NOT NULL CHECK(version_number >= 1),
            action TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(entity_id, version_number)
        );

        CREATE TABLE IF NOT EXISTS reasoning_runs (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            status TEXT NOT NULL,
            engine_version TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            summary_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reasoning_conclusions (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES reasoning_runs(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            predicate_key TEXT NOT NULL,
            statement TEXT NOT NULL,
            value TEXT NOT NULL,
            status TEXT NOT NULL,
            support_level TEXT NOT NULL,
            rule_codes_json TEXT NOT NULL,
            assertion_codes_json TEXT NOT NULL,
            source_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(run_id, code)
        );

        CREATE TABLE IF NOT EXISTS reasoning_traces (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES reasoning_runs(id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL,
            rule_id TEXT NOT NULL,
            rule_code TEXT NOT NULL,
            outcome TEXT NOT NULL,
            detail_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(run_id, sequence)
        );

        CREATE TABLE IF NOT EXISTS reasoning_sequences (
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            entity_name TEXT NOT NULL,
            last_value INTEGER NOT NULL CHECK(last_value >= 0),
            PRIMARY KEY(case_id, entity_name)
        );

        CREATE INDEX IF NOT EXISTS idx_reasoning_assertions_case
            ON reasoning_assertions(case_id, issue_id);
        CREATE INDEX IF NOT EXISTS idx_reasoning_rules_case
            ON reasoning_rules(case_id, issue_id);
        CREATE INDEX IF NOT EXISTS idx_reasoning_assertion_versions
            ON reasoning_assertion_versions(case_id, entity_code, version_number);
        CREATE INDEX IF NOT EXISTS idx_reasoning_rule_versions
            ON reasoning_rule_versions(case_id, entity_code, version_number);
        CREATE INDEX IF NOT EXISTS idx_reasoning_runs_case
            ON reasoning_runs(case_id, issue_id, started_at);
        CREATE INDEX IF NOT EXISTS idx_reasoning_conclusions_run
            ON reasoning_conclusions(run_id);
        CREATE INDEX IF NOT EXISTS idx_reasoning_traces_run
            ON reasoning_traces(run_id);

ALTER TABLE reasoning_runs
ADD COLUMN IF NOT EXISTS input_snapshot_json TEXT NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS legal_arguments (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            title TEXT NOT NULL,
            position TEXT NOT NULL,
            thesis_key TEXT NOT NULL,
            thesis_statement TEXT NOT NULL,
            thesis_value TEXT NOT NULL,
            claim TEXT NOT NULL,
            reasoning TEXT NOT NULL,
            status TEXT NOT NULL,
            conclusion_id TEXT
                REFERENCES reasoning_conclusions(id) ON DELETE SET NULL,
            fact_codes_json TEXT NOT NULL,
            evidence_codes_json TEXT NOT NULL,
            source_codes_json TEXT NOT NULL,
            rule_codes_json TEXT NOT NULL,
            assertion_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS argument_relations (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            source_argument_id TEXT NOT NULL
                REFERENCES legal_arguments(id) ON DELETE CASCADE,
            target_argument_id TEXT NOT NULL
                REFERENCES legal_arguments(id) ON DELETE CASCADE,
            relation_type TEXT NOT NULL,
            rationale TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(case_id, code),
            UNIQUE(source_argument_id, target_argument_id, relation_type)
        );

        CREATE TABLE IF NOT EXISTS argument_sequences (
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            entity_name TEXT NOT NULL,
            last_value INTEGER NOT NULL CHECK(last_value >= 0),
            PRIMARY KEY(case_id, entity_name)
        );

        CREATE TABLE IF NOT EXISTS argument_scenarios (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            argument_ids_json TEXT NOT NULL,
            assumptions_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(case_id, code)
        );

        CREATE INDEX IF NOT EXISTS idx_legal_arguments_case
            ON legal_arguments(case_id, issue_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_argument_relations_case
            ON argument_relations(case_id, issue_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_argument_relations_source
            ON argument_relations(source_argument_id);
        CREATE INDEX IF NOT EXISTS idx_argument_relations_target
            ON argument_relations(target_argument_id);
        CREATE INDEX IF NOT EXISTS idx_argument_scenarios_case
            ON argument_scenarios(case_id, issue_id, updated_at);

CREATE TABLE IF NOT EXISTS llm_draft_sequences (
            case_id TEXT PRIMARY KEY REFERENCES cases(id) ON DELETE CASCADE,
            last_value INTEGER NOT NULL CHECK(last_value >= 0)
        );

        CREATE TABLE IF NOT EXISTS llm_drafts (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            code TEXT NOT NULL,
            task TEXT NOT NULL,
            status TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            model_name TEXT NOT NULL,
            request_json TEXT NOT NULL,
            context_json TEXT NOT NULL,
            response_text TEXT NOT NULL,
            edited_text TEXT,
            reference_codes_json TEXT NOT NULL,
            invalid_reference_codes_json TEXT NOT NULL,
            unsupported_claims_json TEXT NOT NULL,
            risk_flags_json TEXT NOT NULL,
            citation_coverage REAL NOT NULL,
            input_hash TEXT NOT NULL,
            output_hash TEXT NOT NULL,
            provider_mode TEXT NOT NULL DEFAULT 'Simulado local',
            external_call INTEGER NOT NULL DEFAULT 0,
            fallback_used INTEGER NOT NULL DEFAULT 0,
            fallback_reason TEXT,
            provider_request_id TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            estimated_cost_usd REAL,
            reviewer_note TEXT,
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            UNIQUE(case_id, code)
        );

        CREATE TABLE IF NOT EXISTS llm_provider_calls (
            id TEXT PRIMARY KEY,
            draft_id TEXT REFERENCES llm_drafts(id) ON DELETE SET NULL,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
            provider_mode TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            model_name TEXT NOT NULL,
            status TEXT NOT NULL,
            selected_codes_json TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            output_hash TEXT,
            external_call INTEGER NOT NULL,
            fallback_used INTEGER NOT NULL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            estimated_cost_usd REAL,
            error_code TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_llm_drafts_case_issue
            ON llm_drafts(case_id, issue_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_llm_drafts_status
            ON llm_drafts(status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_llm_calls_case_issue
            ON llm_provider_calls(case_id, issue_id, created_at DESC);
