import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import database as db

# D24 structural guard (v1.1.x WS0, docs/workbench-v1.1x.md).
#
# The Workbench Projection Rule: workbench views may project, aggregate,
# filter, sort, and derive existing governed facts - they may not become
# authoritative sources of governed state. The enforceable form ruled at
# scoping:
#
#   The workbench milestone adds NO new tables and NO new writable columns.
#
# This suite freezes the schema - every table, every column - and fails
# on ANY divergence, additions and removals alike. It is permanent, not a
# diff check: a future milestone that legitimately changes the schema
# updates FROZEN_SCHEMA below alongside the ratified decision that
# justifies the change (docs/DECISIONS.md), in the same commit - never
# silently. The UI door is where leaderboard disease would re-enter (D1);
# this is the lock on that door, guarding it the way test_connector_seam.py
# guards D18 and the purity assertions guard D20.
#
# Snapshot history (every amendment names its ratified decision):
#   v1.1.0 baseline (D24, this guard's founding commit) - 26 tables,
#     271 columns; survived the entire v1.1.1 milestone untouched.
#   v1.2.0 WS0 (D25, docs/credentials-cloud-connector-v1.2.md): adds the
#     external_credentials custody table and
#     source_connectors.external_credential_id (connectors reference
#     outbound credentials by id, never by value).
#   v1.2.1 WS0 (D26 + D27, docs/ingestion-automation-v1.2.1.md): adds
#     source_documents.source_metadata_json (Tier-0 source-authority
#     evidence, preserved not merely observed), knowledge_assets.domain
#     (governed hierarchical domain path, NULL = honestly unclassified),
#     the classification_policies governed object, and the
#     approval_policies condition columns (source_conditions_json /
#     engine_conditions_json / domains_json - NULL preserves v0.10.2
#     behavior exactly).
#   v1.3.0 (D28, docs/projection-engine-v1.3.md): NO amendment - the
#     milestone's constitutional claim; the snapshot survived
#     byte-identical at 28 tables / 303 columns.
#   v1.4.0 WS0 (D29 + D30, docs/diagnostic-workbench-v1.4.md): adds
#     knowledge_assets.source_class (PRIMARY | DERIVED - what accepted
#     agent-synthesized knowledge becomes; channel-decided, never
#     content-claimed; legacy rows PRIMARY by construction) and
#     source_connectors.lane (PRIMARY | PROPOSAL - the channel
#     declaration the class derives from; proposal-lane candidates are
#     constitutionally outside every policy tier). 28 tables /
#     305 columns.

FROZEN_SCHEMA = {
    "agent_packages": [
        "asset_references", "clearance_level", "created_at",
        "expert_model_id", "file_path", "governance_version", "id",
        "manifest_json", "name", "package_hash", "project_id",
        "quality_score",
    ],
    "approval_policies": [
        "asset_types_json", "connector_id", "created_at", "created_by",
        "domains_json",  # v1.2.1 WS0 (D26): domain-prefix coverage narrowing
        "enabled",
        "engine_conditions_json",  # v1.2.1 WS0 (D26): Tier-2 engine conditions
        "id", "name", "project_id",
        "source_conditions_json",  # v1.2.1 WS0 (D26): Tier-0 authority matches
        "updated_at", "version",
    ],
    "asset_relationships": [
        "classification", "confidence", "detected_at", "expert_model_id",
        "id", "notes", "project_id", "relationship_type", "reviewed_at",
        "reviewed_by", "source_asset_id", "status", "target_asset_id",
        "verifier_json",
    ],
    "asset_reviews": [
        "approver", "asset_id", "id", "identity_fact_id", "notes",
        "reviewed_at", "reviewer",
    ],
    "asset_revisions": [
        "approved_at", "approved_by", "asset_id", "change_reason",
        "content", "content_hash", "created_at", "created_by", "id",
        "identity_fact_id", "revision_number", "source_hash", "status",
        "superseded_by_revision_id", "supersedes_revision_id",
    ],
    "audit_events": [
        "actor", "details", "event_type", "id", "identity_fact_id",
        "target_id", "timestamp",
    ],
    "benchmark_questions": [
        "created_at", "expected_answer_type", "expected_claims_json", "id",
        "min_required_coverage", "project_id", "question",
        "required_citation_count", "severity", "tags",
    ],
    "claim_verdicts": [
        "benchmark_question_id", "claim", "confidence",
        "contradicting_asset_ids_json", "created_at", "evaluation_run_id",
        "evaluator_id", "evaluator_type", "expert_model_id", "id",
        "project_id", "question_result_id", "supporting_asset_ids_json",
        "verdict", "verifier_json",
    ],
    "credentials": [
        "created_at", "expires_at", "fingerprint", "id",
        "issued_by_credential_id", "kind", "label", "last_used_at",
        "principal_id", "revoked_at", "secret_hash",
    ],
    # v1.2.1 WS0 (D27): domain classification is its own governed object -
    # assigning a domain and granting APPROVED are different outcome
    # species; provenance and version counters never blur.
    "classification_policies": [
        "connector_id", "created_at", "created_by", "enabled", "id",
        "name", "project_id", "rules_json", "updated_at", "version",
    ],
    "customers": [
        "api_key", "id", "name",
    ],
    "document_chunks": [
        "chunk_index", "docling_json", "document_id", "embedding_ref",
        "id", "table_count", "text",
    ],
    "documents": [
        "content_hash", "created_at", "department", "file_path",
        "file_type", "filename", "id", "modified_at", "owner",
        "project_id", "status", "version",
    ],
    "evaluation_question_results": [
        "benchmark_question_id", "citations_json", "confidence_score",
        "coverage_score", "evaluation_run_id", "generated_answer", "id",
        "passed", "question_text", "unsupported_claims_json",
        "verification_status",
    ],
    "evaluation_runs": [
        "asset_hashes_snapshot", "asset_ids_snapshot",
        "average_confidence_score", "average_coverage_score",
        "benchmark_question_ids_snapshot", "completed_at",
        "consumer_model_name", "consumer_model_provider",
        "expert_model_id", "expert_model_version",
        "failed_question_ids_json", "id", "package_hash",
        "package_version", "pass_rate", "project_id", "run_type",
        "started_at", "status",
    ],
    "expert_agent_bindings": [
        "agent_package_id", "agent_principal_id", "created_at", "id",
        "identity_fact_id", "package_hash", "package_version",
        "principal_clearance_at_issue", "selected_model_name",
        "selected_provider", "selection_evidence_json",
    ],
    "expert_models": [
        "asset_count", "asset_ids_json", "coverage_score", "created_at",
        "description", "id", "name", "project_id", "quality_score",
    ],
    # v1.2.0 WS0 (D25): outbound credential custody. Encrypted secret
    # material + custody lineage; NO plaintext-shaped column may ever
    # appear here (test_credential_custody.py asserts the shape).
    "external_credentials": [
        "ciphertext", "coordinates_json", "created_at",
        "created_identity_fact_id", "fingerprint", "granted_scopes_json",
        "id", "key_id", "name", "owner_principal_id", "purpose",
        "replaces_credential_id", "revoked_at", "revoked_identity_fact_id",
        "status", "wrapped_data_key",
    ],
    "identity_facts": [
        "authentication_method", "created_at", "credential_fingerprint",
        "display_name", "id", "on_behalf_of_fact_id", "principal_id",
        "principal_kind", "principal_name", "role_snapshot",
    ],
    "ingestion_jobs": [
        "completed_at", "connector_id", "error", "files_changed",
        "files_discovered", "files_duplicate", "files_failed",
        "files_ingested", "id", "project_id", "started_at", "status",
    ],
    "knowledge_assets": [
        "access_level", "chunk_id", "condition", "content", "created_at",
        "document_id",
        "domain",  # v1.2.1 WS0 (D27): governed hierarchical domain path
        "extraction_method", "id", "name", "owner",
        "project_id", "source_citation",
        "source_class",  # v1.4.0 WS0 (D30): PRIMARY | DERIVED, channel-decided
        "source_hash", "source_page",
        "source_section", "status", "type",
    ],
    "llm_function_configs": [
        "function", "id", "model", "provider", "updated_at", "updated_by",
    ],
    "package_model_selections": [
        "agent_package_id", "id", "package_hash", "package_version",
        "rationale", "selected_at", "selected_by_principal_id",
        "selected_model_name", "selected_provider",
        "supporting_evaluation_run_ids_json",
    ],
    "principals": [
        "active", "clearance", "created_at", "created_by", "display_name",
        "id", "kind", "must_change_password", "name", "role",
    ],
    "projects": [
        "customer_id", "description", "id", "name", "status",
    ],
    "quality_scores": [
        "asset_id", "conflict_score", "coverage_score", "freshness_score",
        "id", "overall_score", "recorded_at", "verification_score",
    ],
    "source_connectors": [
        "created_at", "external_credential_id",  # v1.2.0 WS0 (D25): by reference, never by value
        "id", "include_extensions",
        "lane",  # v1.4.0 WS0 (D29/D30): PRIMARY | PROPOSAL channel declaration
        "name", "project_id",
        "root_path", "type",
    ],
    "source_documents": [
        "connector_id", "created_at", "details_json", "document_id",
        "error", "file_hash", "id", "ingestion_job_id", "project_id",
        "size_bytes", "source_metadata_json",  # v1.2.1 WS0 (D26): Tier-0 evidence
        "source_modified_at", "source_uri", "status",
    ],
}

GUIDANCE = ("If this change is justified by a ratified decision, record it "
            "in docs/DECISIONS.md and update FROZEN_SCHEMA in the same "
            "commit - never silently.")


def main():
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}

    frozen_tables = set(FROZEN_SCHEMA)
    live_tables = set(live)

    added = sorted(live_tables - frozen_tables)
    assert not added, (
        f"D24 violation: new table(s) {added}. Workbench views project "
        f"existing governed facts; they never persist their own state. "
        f"{GUIDANCE}")

    removed = sorted(frozen_tables - live_tables)
    assert not removed, (
        f"Schema regression: table(s) {removed} disappeared from the "
        f"frozen schema. Governed facts are never dropped. "
        f"{GUIDANCE}")

    for table in sorted(frozen_tables):
        frozen_cols = set(FROZEN_SCHEMA[table])
        live_cols = set(live[table])
        added_cols = sorted(live_cols - frozen_cols)
        assert not added_cols, (
            f"D24 violation: new column(s) {added_cols} on '{table}'. "
            f"No new writable columns - staleness, rankings, and dashboard "
            f"state stay computed, never persisted. {GUIDANCE}")
        removed_cols = sorted(frozen_cols - live_cols)
        assert not removed_cols, (
            f"Schema regression: column(s) {removed_cols} dropped from "
            f"'{table}' in the frozen schema. {GUIDANCE}")

    table_count = len(frozen_tables)
    column_count = sum(len(cols) for cols in FROZEN_SCHEMA.values())
    print(f"D24 projection guard passed: live schema is identical to the "
          f"frozen snapshot ({table_count} tables, "
          f"{column_count} columns; v1.1.0 baseline + the D25 custody, "
          f"D26/D27 automation, and D29/D30 derived-source-class "
          f"amendments). No new tables, no new writable columns beyond "
          f"ratified decisions.")


if __name__ == "__main__":
    main()
