"""Generate draft skill contracts for the whole Workbench Skill Registry.

One 13-field YAML contract per skill, for every subtask of every
workbench in docs/workbench-skill-registry.md (the master subtask
inventory, ratified 2026-07-03 at the v1.6 WS0 gate).

Output tree:  docs/skill-contracts/<NN>_<workbench_id>/<skill_id>.yaml

These are catalog-level DRAFTS: the binding, versioned contracts are
ratified at each workbench's own scoping session and live in
workbench/<name>/skills/ (registry rule 1). Ratified ACTIVE contracts
(the v1.6 Customer Operations five, the v1.7 Compliance & Obligation
six) carry a ratified_path pointer in their drafts. CONSOLIDATED
drafts (the v1.7 consolidation ruling) carry consolidated_into AND
ratified_path - consolidation never becomes silent promotion.

Deterministic and stdlib-only: rerun after editing INVENTORY; output
is stable byte-for-byte for a fixed inventory.
"""
import os
import shutil

# ---------------------------------------------------------------- inventory
# Each skill: (skill_id, tags, pattern)
#   tags:    comma-joined from {now, OE, PMD, ES, assist, synth}
#   pattern: conflict | coverage | revision | extract | missing_evidence
#          | deadline | compare | finding | assist | platform | stewardship

INVENTORY = [
    (1, "executive_ceo", "Executive / CEO Workbench", "TWO-STAGE (v1 now; decision queue behind [PMD])", [
        ("generate_weekly_ceo_briefing", "assist", "assist"),
        ("summarize_company_status", "now,assist", "assist"),
        ("identify_major_operational_risks", "now", "finding"),
        ("detect_unresolved_blockers_by_department", "now,PMD", "finding"),
        ("compare_period_vs_previous", "now", "compare"),
        ("identify_decisions_needing_approval", "PMD", "finding"),
        ("identify_unsupported_claims", "now", "finding"),
        ("summarize_unresolved_conflicts", "now,assist", "assist"),
        ("summarize_accepted_findings", "now,assist", "assist"),
        ("summarize_governance_health", "now,assist", "assist"),
        ("prepare_board_report", "assist", "assist"),
        ("answer_what_changed_since", "now,assist", "assist"),
        ("produce_executive_decision_queue", "PMD", "finding"),
        ("produce_cross_functional_risk_register", "now,synth", "finding"),
        ("produce_recommended_next_actions", "assist,synth", "assist"),
        ("generate_unknowns_evidence_gaps_report", "now", "coverage"),
    ]),
    (2, "finance_cost_leakage", "Finance & Cost Leakage Workbench", "DOCUMENT-BOUND until [OE]", [
        ("extract_payment_terms", "now", "extract"),
        ("compare_contract_terms_vs_finance_policy", "now", "compare"),
        ("detect_contract_price_increases", "now", "finding"),
        ("detect_renewal_cost_risk", "now", "deadline"),
        ("identify_unused_service_obligations", "now", "finding"),
        ("detect_missing_spend_approval_evidence", "now", "missing_evidence"),
        ("identify_budget_policy_conflicts", "now", "conflict"),
        ("prepare_cfo_cost_reduction_scenario", "assist,synth", "assist"),
        ("detect_pricing_clauses_requiring_review", "now", "finding"),
        ("identify_payment_term_mismatch_risk", "now", "compare"),
        ("generate_monthly_finance_exception_report", "now,assist", "assist"),
        ("prepare_finance_evidence_pack", "assist", "assist"),
        ("identify_leakage_clauses", "now", "finding"),
        ("identify_finance_policy_coverage_gaps", "now", "coverage"),
        ("detect_outdated_finance_policies", "now", "revision"),
        ("identify_missing_finance_obligation_owner", "ES", "stewardship"),
        ("detect_duplicate_invoices", "OE", "finding"),
        ("compare_po_vs_invoices", "OE", "compare"),
        ("detect_unusual_cost_increases", "OE", "finding"),
        ("flag_overdue_receivables", "OE", "finding"),
        ("detect_budget_overrun_from_accounting", "OE", "finding"),
        ("detect_payment_terms_not_followed", "OE", "finding"),
    ]),
    (3, "procurement_vendor_intelligence", "Procurement & Vendor Intelligence Workbench", "SEQUENCED (third, document slice)", [
        ("summarize_vendor_contracts", "assist", "assist"),
        ("extract_vendor_terms", "now", "extract"),
        ("detect_expiring_contracts", "now", "deadline"),
        ("detect_auto_renewal_clauses", "now", "deadline"),
        ("detect_price_increase_clauses", "now", "finding"),
        ("identify_missing_supplier_certifications", "now", "missing_evidence"),
        ("extract_sla_obligations", "now", "extract"),
        ("compare_vendor_terms_vs_procurement_policy", "now", "compare"),
        ("prepare_renegotiation_brief", "assist,synth", "assist"),
        ("detect_single_supplier_dependency", "now", "finding"),
        ("propose_vendor_consolidation", "synth", "finding"),
        ("identify_missing_vendor_approval_evidence", "now", "missing_evidence"),
        ("identify_vendor_data_access_obligations", "now", "extract"),
        ("detect_outdated_supplier_documents", "now", "revision"),
        ("prepare_vendor_risk_list", "now,synth", "assist"),
        ("prepare_contract_evidence_package", "assist", "assist"),
        ("generate_negotiation_points", "assist,synth", "assist"),
        ("identify_owner_gaps", "ES", "stewardship"),
        ("detect_vendor_contract_vs_policy_conflict", "now", "conflict"),
        ("identify_vendor_obligations_next_period", "now", "deadline"),
        ("compare_sla_obligations_vs_service_records", "OE", "compare"),
        ("compare_contract_pricing_vs_invoices", "OE", "compare"),
        ("detect_vendor_usage_vs_license_count", "OE", "finding"),
        ("detect_supplier_performance_gaps", "OE", "finding"),
    ]),
    (4, "sales_account_growth", "Sales & Account Growth Workbench", "FUTURE (Layer 3)", [
        ("prepare_customer_account_briefing", "assist", "assist"),
        ("summarize_customer_contract_obligations", "now,assist", "assist"),
        ("summarize_customer_history_documents", "assist", "assist"),
        ("detect_missing_proposal_evidence", "now", "missing_evidence"),
        ("compare_customer_needs_vs_documentation", "now", "compare"),
        ("identify_unsupported_sales_claims", "now", "finding"),
        ("detect_unbacked_proposal_promises", "now", "compare"),
        ("prepare_meeting_talking_points", "assist", "assist"),
        ("generate_proposal_checklist", "assist", "assist"),
        ("identify_customer_sla_terms", "now", "extract"),
        ("detect_outdated_sales_collateral", "now", "revision"),
        ("detect_sales_vs_policy_contradictions", "now", "conflict"),
        ("prepare_followup_email_draft", "assist", "assist"),
        ("identify_customer_risk_obligations", "now", "extract"),
        ("generate_account_evidence_pack", "assist", "assist"),
        ("identify_approval_required_commitments", "now", "finding"),
        ("detect_stalled_opportunities", "OE", "finding"),
        ("identify_upsell_from_activity", "OE,synth", "finding"),
        ("detect_declining_activity", "OE", "finding"),
        ("summarize_recent_orders", "OE,assist", "assist"),
        ("compare_crm_history_vs_obligations", "OE", "compare"),
    ]),
    (5, "customer_operations", "Customer Support Workbench (= Customer Operations, v1.6)", "ACTIVE (v1.6.0)", [
        ("answer_support_questions", "assist", "assist"),
        ("suggest_customer_replies", "assist", "assist"),
        ("detect_macro_vs_policy_contradictions", "now", "conflict"),
        ("detect_customer_promise_conflict", "now", "conflict"),
        ("detect_missing_support_playbook", "now", "coverage"),
        ("detect_outdated_customer_guidance", "now", "revision"),
        ("detect_refund_policy_conflicts", "now", "conflict"),
        ("detect_escalation_path_gaps", "now", "coverage"),
        ("detect_sla_obligation_gap", "now", "missing_evidence"),
        ("compare_help_docs_vs_internal_sops", "now", "compare"),
        ("prepare_customer_policy_brief", "assist,synth", "assist"),
        ("identify_unsupported_customer_claims", "now", "finding"),
        ("identify_documentation_gaps_by_category", "now", "coverage"),
        ("generate_escalation_recommendation", "assist", "assist"),
        ("prepare_support_training_pack", "assist", "assist"),
        ("detect_inconsistent_terminology", "now,synth", "finding"),
        ("detect_missing_procedure_owner", "ES", "stewardship"),
        ("produce_approved_answer_pack", "now", "platform"),
        ("flag_unapproved_content", "PMD", "finding"),
        ("review_weekly_tickets", "OE", "finding"),
        ("detect_repeated_complaints", "OE", "finding"),
        ("identify_product_issues_from_tickets", "OE", "finding"),
        ("detect_sla_breaches_from_timestamps", "OE", "finding"),
        ("escalate_high_risk_customers", "OE,ES", "finding"),
        ("summarize_open_cases", "OE,assist", "assist"),
    ]),
    (6, "customer_success_retention", "Customer Success / Retention Workbench", "FUTURE (split at the WS0 gate)", [
        ("summarize_customer_success_obligations", "now,assist", "assist"),
        ("identify_customer_renewal_obligations", "now", "deadline"),
        ("detect_missing_customer_success_playbooks", "now", "coverage"),
        ("detect_customer_obligations_without_owner", "ES", "stewardship"),
        ("detect_cs_policy_vs_contract_contradiction", "now", "conflict"),
        ("prepare_customer_retention_brief", "assist", "assist"),
        ("identify_unbacked_promised_outcomes", "now", "compare"),
        ("detect_missing_qbr_reporting_procedure", "now", "coverage"),
        ("extract_customer_communication_obligations", "now", "extract"),
        ("identify_strategic_customer_escalation_rules", "now", "extract"),
        ("detect_outdated_cs_documentation", "now", "revision"),
        ("generate_customer_success_evidence_pack", "assist", "assist"),
        ("prepare_renewal_readiness_checklist", "assist", "assist"),
        ("detect_missing_service_commitment_evidence", "now", "missing_evidence"),
        ("identify_unbacked_customer_health_assumptions", "now", "finding"),
        ("prepare_internal_customer_risk_briefing", "assist,synth", "assist"),
        ("detect_declining_activity", "OE", "finding"),
        ("detect_low_usage", "OE", "finding"),
        ("detect_unresolved_customer_issues", "OE", "finding"),
        ("score_customer_risk", "OE,synth", "finding"),
        ("cluster_recurring_complaints", "OE", "finding"),
        ("identify_churn_signals", "OE", "finding"),
    ]),
    (7, "hr_people_operations", "HR / People Operations Workbench", "FUTURE (Layer 3, positioning-sensitive)", [
        ("generate_onboarding_package", "assist", "assist"),
        ("answer_hr_policy_questions", "assist", "assist"),
        ("detect_hr_policy_contradictions", "now", "conflict"),
        ("detect_outdated_hr_documents", "now", "revision"),
        ("detect_missing_training_requirements", "now", "coverage"),
        ("detect_missing_onboarding_steps", "now", "coverage"),
        ("compare_job_descriptions_vs_role_documentation", "now", "compare"),
        ("identify_hr_policy_coverage_gaps", "now", "coverage"),
        ("prepare_role_handover_package", "assist", "assist"),
        ("detect_expired_certification_requirements", "now", "deadline"),
        ("generate_internal_hr_faq", "now,synth", "finding"),
        ("identify_missing_hr_process_owner", "ES", "stewardship"),
        ("detect_benefits_vs_employment_policy_contradiction", "now", "conflict"),
        ("prepare_hiring_manager_briefing", "assist", "assist"),
        ("detect_key_person_dependency", "now,synth", "finding"),
        ("prepare_workforce_scenario", "synth", "finding"),
        ("detect_equipment_access_policy_gaps", "now", "coverage"),
        ("detect_training_evidence_gaps", "now", "missing_evidence"),
    ]),
    (8, "operations_process_improvement", "Operations / Process Improvement Workbench", "FUTURE (Layer 3, document-first)", [
        ("map_documented_business_process", "now,synth", "extract"),
        ("detect_missing_handoffs", "now", "finding"),
        ("detect_duplicated_process_steps", "now", "finding"),
        ("compare_sop_vs_policy", "now", "compare"),
        ("detect_process_contradictions", "now", "conflict"),
        ("detect_missing_approval_steps", "now", "coverage"),
        ("detect_undocumented_process_areas", "now", "coverage"),
        ("identify_process_variants_across_departments", "now", "compare"),
        ("generate_process_improvement_backlog", "now,synth", "finding"),
        ("propose_automation_candidates", "synth", "finding"),
        ("identify_missing_process_stage_owner", "ES", "stewardship"),
        ("detect_outdated_process_documents", "now", "revision"),
        ("prepare_process_map_projection", "assist", "assist"),
        ("detect_rework_risk_from_conflicting_instructions", "now", "conflict"),
        ("identify_required_approvals_for_process_changes", "now", "extract"),
        ("prepare_improvement_proposal", "now,synth", "finding"),
        ("estimate_improvement_impact", "synth", "finding"),
        ("detect_customer_impacting_process_gaps", "now", "finding"),
        ("compare_sop_vs_execution_logs", "OE", "compare"),
        ("detect_stage_delays", "OE", "finding"),
        ("detect_bottlenecks_from_traces", "OE", "finding"),
        ("process_mining_from_operational_systems", "OE", "finding"),
    ]),
    (9, "compliance_obligation_tracking", "Compliance / Obligation Tracking Workbench", "ACTIVE (v1.7.0, second)", [
        ("extract_compliance_obligations", "now", "extract"),
        ("extract_obligations_from_contracts", "now", "extract"),
        ("extract_obligations_from_policies", "now", "extract"),
        ("extract_obligations_from_certifications", "now", "extract"),
        ("extract_obligations_from_regulatory_documents", "now", "extract"),
        ("classify_obligation_type", "now", "extract"),
        ("track_explicit_deadlines", "now", "deadline"),
        ("track_recurrence_rules", "now", "deadline"),
        ("detect_missing_evidence", "now", "missing_evidence"),
        ("identify_outdated_policies", "now", "revision"),
        ("detect_undocumented_obligation_owner", "now", "missing_evidence"),
        ("detect_conflicting_compliance_statements", "now", "conflict"),
        ("compare_policy_vs_policy", "now", "compare"),
        ("compare_contract_obligation_vs_procedure", "now", "compare"),
        ("prepare_audit_readiness_pack", "assist", "assist"),
        ("detect_unapproved_compliance_guidance", "PMD", "finding"),
        ("generate_compliance_evidence_binder", "assist", "assist"),
        ("answer_auditor_questions", "assist", "assist"),
        ("identify_obligation_owner_gaps", "ES", "stewardship"),
        ("identify_upcoming_obligations_30_60_90", "now", "deadline"),
        ("detect_certification_expiry_risk", "now", "deadline"),
        ("detect_reporting_obligation_gaps", "now", "coverage"),
        ("detect_notification_obligation_gaps", "now", "coverage"),
        ("detect_sla_evidence_gaps", "now", "missing_evidence"),
        ("prepare_compliance_risk_register", "now,synth", "assist"),
        ("generate_obligation_approval_queue", "now,PMD", "platform"),
        ("refuse_unsupported_compliance_claims", "now", "platform"),
        ("compare_policy_vs_practice", "OE", "compare"),
        ("verify_obligations_against_operational_records", "OE", "compare"),
        ("detect_missed_operational_reporting_events", "OE", "finding"),
        ("detect_practice_evidence_from_logs_tickets_payments", "OE", "finding"),
    ]),
    (10, "document_knowledge_quality", "Document / Knowledge Quality Workbench", "PLATFORM (Layer 1)", [
        ("detect_outdated_documents", "now", "platform"),
        ("detect_contradictory_instructions", "now", "platform"),
        ("detect_missing_document_owner", "ES", "stewardship"),
        ("detect_documents_without_approval", "PMD", "platform"),
        ("detect_duplicate_knowledge", "now", "platform"),
        ("detect_undocumented_processes", "now", "coverage"),
        ("recommend_documents_needing_review", "now", "platform"),
        ("compile_department_knowledge_package", "now", "platform"),
        ("create_approved_answer_packs", "now", "platform"),
        ("detect_conflicting_sops", "now", "conflict"),
        ("detect_policy_vs_training_conflicts", "now", "conflict"),
        ("detect_stale_customer_facing_documents", "now", "revision"),
        ("detect_missing_provenance", "now", "platform"),
        ("detect_weak_evidence_claims", "now", "finding"),
        ("detect_unsupported_claims", "now", "finding"),
        ("detect_broken_internal_references", "now", "finding"),
        ("detect_missing_domain_classification", "now", "platform"),
        ("detect_ambiguous_terminology", "now,synth", "finding"),
        ("detect_multiple_active_policy_versions", "now", "finding"),
        ("detect_governance_status_mismatch", "now", "finding"),
        ("prepare_knowledge_quality_scorecard", "assist", "assist"),
        ("generate_review_owner_recommendation", "ES", "stewardship"),
        ("prepare_proposed_resolution_draft", "now,synth", "finding"),
        ("surface_unresolved_conflict_clusters", "now", "platform"),
    ]),
    (11, "project_delivery", "Project / Delivery Workbench", "FUTURE (Layer 3)", [
        ("summarize_project_status", "assist", "assist"),
        ("extract_project_commitments", "now", "extract"),
        ("detect_missed_deliverables_from_plans", "now", "missing_evidence"),
        ("compare_contract_scope_vs_project_plan", "now", "compare"),
        ("identify_scope_creep_risk", "now", "finding"),
        ("prepare_client_update_draft", "assist", "assist"),
        ("detect_missing_deliverables", "now", "missing_evidence"),
        ("identify_deadline_risk_from_plans", "now,synth", "finding"),
        ("compare_project_plan_vs_meeting_notes", "now", "compare"),
        ("prepare_handover_package", "assist", "assist"),
        ("generate_lessons_learned_draft", "now,synth", "finding"),
        ("identify_unresolved_risks", "now", "extract"),
        ("extract_owner_deadline_action_from_notes", "now", "extract"),
        ("detect_commitment_without_owner", "now", "finding"),
        ("detect_decision_without_evidence", "now", "finding"),
        ("detect_dependency_gaps", "now", "finding"),
        ("prepare_internal_action_list", "assist", "assist"),
        ("generate_project_evidence_pack", "assist", "assist"),
        ("detect_contract_obligation_not_in_plan", "now", "compare"),
        ("detect_outdated_project_documentation", "now", "revision"),
        ("compare_plan_vs_task_system", "OE", "compare"),
        ("detect_blocked_tasks_from_task_systems", "OE", "finding"),
        ("detect_deadline_risk_from_execution_data", "OE", "finding"),
        ("detect_delivery_delays_from_logs", "OE", "finding"),
    ]),
    (12, "internal_it_saas", "Internal IT / SaaS Workbench", "FUTURE (Layer 3)", [
        ("build_saas_inventory_from_documents", "now", "extract"),
        ("extract_saas_owners", "now", "extract"),
        ("extract_renewal_dates", "now", "extract"),
        ("extract_vendor_cost_terms", "now", "extract"),
        ("identify_unsupported_systems", "now", "finding"),
        ("detect_renewal_risk", "now", "deadline"),
        ("detect_shadow_it_risk_from_documents", "now", "finding"),
        ("compare_security_policy_vs_approved_tools", "now", "compare"),
        ("generate_it_helpdesk_answers", "assist", "assist"),
        ("prepare_migration_plan", "assist,synth", "assist"),
        ("identify_missing_it_system_owner", "ES", "stewardship"),
        ("detect_outdated_it_policies", "now", "revision"),
        ("detect_missing_data_access_approvals", "now", "missing_evidence"),
        ("detect_missing_vendor_security_certification", "now", "missing_evidence"),
        ("prepare_it_asset_register_projection", "assist", "assist"),
        ("detect_access_policy_gaps", "now", "coverage"),
        ("identify_saas_consolidation_candidates", "synth", "finding"),
        ("prepare_it_renewal_calendar", "assist", "assist"),
        ("detect_it_policy_vs_vendor_contract_contradiction", "now", "conflict"),
        ("generate_it_risk_list", "now,synth", "assist"),
        ("detect_unused_accounts", "OE", "finding"),
        ("detect_unused_licenses", "OE", "finding"),
        ("compare_user_count_vs_license_count", "OE", "compare"),
        ("summarize_incidents", "OE,assist", "assist"),
        ("detect_access_right_violations", "OE", "finding"),
    ]),
    (13, "meeting_intelligence", "Meeting Intelligence / Decision Follow-up Workbench", "PLATFORM-ADJACENT (Layer 1, deferred surface)", [
        ("extract_decisions_from_meeting_notes", "now", "extract"),
        ("extract_action_items", "now", "extract"),
        ("extract_owners", "now", "extract"),
        ("extract_deadlines", "now", "extract"),
        ("extract_unresolved_risks", "now", "extract"),
        ("link_decisions_to_evidence", "now", "extract"),
        ("detect_decisions_without_evidence", "now", "missing_evidence"),
        ("detect_unresolved_action_items", "ES", "stewardship"),
        ("compare_meeting_claims_vs_knowledge", "now", "conflict"),
        ("prepare_next_meeting_briefing", "assist", "assist"),
        ("track_decision_history", "now", "platform"),
        ("generate_followup_email_draft", "assist", "assist"),
        ("detect_repeated_unresolved_decisions", "now", "finding"),
        ("detect_missing_action_owner", "now", "finding"),
        ("detect_deadline_ambiguity", "now", "deadline"),
        ("convert_accepted_decisions_into_governed_facts", "now", "platform"),
        ("generate_meeting_evidence_pack", "assist", "assist"),
        ("detect_meeting_decision_vs_policy_contradiction", "now", "conflict"),
        ("prepare_management_decision_queue", "PMD", "finding"),
        ("identify_claims_requiring_governance_review", "now", "finding"),
    ]),
    (14, "ask_company_expert", "Ask Company Expert Workbench", "PLATFORM (Layer 1, shipped)", [
        ("answer_from_approved_knowledge", "now", "platform"),
        ("cite_evidence_for_every_claim", "now", "platform"),
        ("refuse_unsupported_answers", "now", "platform"),
        ("warn_on_contradictions", "now", "platform"),
        ("explain_what_is_known", "now", "platform"),
        ("explain_what_is_unknown", "now", "platform"),
        ("explain_what_is_contradictory", "now", "platform"),
        ("compare_multiple_approved_sources", "now", "compare"),
        ("produce_short_answer", "assist", "assist"),
        ("produce_detailed_answer", "assist", "assist"),
        ("produce_action_recommendation", "assist", "assist"),
        ("identify_needed_escalation", "assist", "assist"),
        ("identify_missing_evidence", "now", "missing_evidence"),
        ("identify_related_policies_contracts_sops", "now", "platform"),
        ("generate_approved_answer_pack", "now", "platform"),
        ("answer_role_specific_questions", "now", "platform"),
        ("answer_customer_specific_questions", "now", "platform"),
        ("answer_vendor_specific_questions", "now", "platform"),
        ("answer_auditor_questions", "now", "platform"),
        ("produce_confidence_and_limitation_statement", "now", "platform"),
    ]),
    (15, "risk_exception", "Risk & Exception Workbench", "PLATFORM (Layer 1) + [ES]", [
        ("surface_high_risk_findings", "now", "platform"),
        ("classify_risk_by_impact_urgency", "synth", "finding"),
        ("identify_missing_approvals", "now,PMD", "platform"),
        ("identify_unresolved_conflicts", "now", "platform"),
        ("identify_overdue_reviews", "now", "platform"),
        ("generate_investigation_brief", "assist", "assist"),
        ("track_unresolved_risks", "now,ES", "platform"),
        ("compare_risk_trend_over_time", "now", "platform"),
        ("route_to_responsible_owner", "ES", "stewardship"),
        ("record_human_acknowledgement", "ES", "stewardship"),
        ("record_risk_acceptance", "ES", "stewardship"),
        ("record_dismissal_with_reason", "ES", "stewardship"),
        ("record_escalation", "ES", "stewardship"),
        ("produce_exception_queue", "now", "platform"),
        ("produce_department_owner_view", "ES", "stewardship"),
        ("produce_evidence_pack", "assist", "assist"),
        ("produce_recommended_action", "assist,synth", "assist"),
        ("produce_approval_status_summary", "now,PMD", "platform"),
        ("produce_audit_trail", "now", "platform"),
        ("generate_weekly_exception_digest", "assist", "assist"),
    ]),
    (16, "contract_intelligence", "Contract Intelligence Workbench", "FUTURE (the shared engine)", [
        ("summarize_contract", "assist", "assist"),
        ("extract_parties", "now", "extract"),
        ("extract_effective_date", "now", "extract"),
        ("extract_expiry_date", "now", "extract"),
        ("extract_renewal_terms", "now", "extract"),
        ("extract_termination_terms", "now", "extract"),
        ("extract_payment_terms", "now", "extract"),
        ("extract_sla_terms", "now", "extract"),
        ("extract_reporting_obligations", "now", "extract"),
        ("extract_certification_obligations", "now", "extract"),
        ("extract_notification_obligations", "now", "extract"),
        ("extract_data_access_clauses", "now", "extract"),
        ("extract_confidentiality_obligations", "now", "extract"),
        ("extract_liability_indemnity_clauses", "now", "extract"),
        ("extract_audit_rights", "now", "extract"),
        ("extract_approval_requirements", "now", "extract"),
        ("detect_missing_contract_metadata", "now", "missing_evidence"),
        ("detect_conflicting_contract_clauses", "now", "conflict"),
        ("compare_contract_vs_internal_policy", "now", "compare"),
        ("compare_customer_contract_vs_support_sop", "now", "compare"),
        ("compare_vendor_contract_vs_procurement_policy", "now", "compare"),
        ("detect_auto_renewal_risk", "now", "deadline"),
        ("detect_price_increase_risk", "now", "finding"),
        ("detect_contract_owner_gaps", "ES", "stewardship"),
        ("prepare_contract_review_brief", "assist", "assist"),
        ("prepare_renewal_decision_brief", "assist", "assist"),
        ("prepare_negotiation_points", "assist,synth", "assist"),
        ("generate_obligation_candidates_for_compliance", "now", "extract"),
        ("generate_vendor_intelligence_for_procurement", "now", "extract"),
        ("generate_customer_obligation_inputs_for_cs", "now", "extract"),
    ]),
]

# The ratified ACTIVE contracts (drafts point at them): the v1.6
# Customer Operations five + the v1.7 Compliance & Obligation six.
RATIFIED = {
    ("customer_operations", "detect_customer_promise_conflict"),
    ("customer_operations", "detect_missing_support_playbook"),
    ("customer_operations", "detect_outdated_customer_guidance"),
    ("customer_operations", "detect_sla_obligation_gap"),
    ("customer_operations", "prepare_customer_policy_brief"),
    ("compliance_obligation_tracking", "extract_compliance_obligations"),
    ("compliance_obligation_tracking", "detect_missing_evidence"),
    ("compliance_obligation_tracking", "identify_outdated_policies"),
    ("compliance_obligation_tracking", "detect_undocumented_obligation_owner"),
    ("compliance_obligation_tracking", "detect_conflicting_compliance_statements"),
    ("compliance_obligation_tracking", "prepare_audit_readiness_pack"),
}

# Bundle folder per workbench (ratified_path targets). The registry
# id and the bundle folder may differ (compliance's bundle is
# workbench/compliance_obligation/ per the v1.7 build contract).
BUNDLE_DIR = {
    "customer_operations": "customer_operations",
    "compliance_obligation_tracking": "compliance_obligation",
}

# The v1.7 consolidation ruling (WS0 gate): consolidated drafts carry
# ratified_path AND consolidated_into, so consolidation never becomes
# silent promotion. status: CONSOLIDATED, never ACTIVE, never DRAFT.
CONSOLIDATED = {
    ("compliance_obligation_tracking", "extract_obligations_from_contracts"): "extract_compliance_obligations",
    ("compliance_obligation_tracking", "extract_obligations_from_policies"): "extract_compliance_obligations",
    ("compliance_obligation_tracking", "extract_obligations_from_certifications"): "extract_compliance_obligations",
    ("compliance_obligation_tracking", "extract_obligations_from_regulatory_documents"): "extract_compliance_obligations",
    ("compliance_obligation_tracking", "classify_obligation_type"): "extract_compliance_obligations",
    ("compliance_obligation_tracking", "detect_sla_evidence_gaps"): "detect_missing_evidence",
    ("compliance_obligation_tracking", "detect_reporting_obligation_gaps"): "detect_missing_evidence",
    ("compliance_obligation_tracking", "detect_notification_obligation_gaps"): "detect_missing_evidence",
}

# The v1.7 deadline deferral (WS0 gate): document-side in theory, but
# persistent deadline stewardship risks a second operational state
# machine before [ES] is scoped. These stay SEQUENCED, deliberately.
DEFERRED_SEQUENCED = {
    ("compliance_obligation_tracking", "track_explicit_deadlines"),
    ("compliance_obligation_tracking", "track_recurrence_rules"),
    ("compliance_obligation_tracking", "identify_upcoming_obligations_30_60_90"),
    ("compliance_obligation_tracking", "detect_certification_expiry_risk"),
}

# The v1.7 owner split ruling: detection is ratified as
# detect_undocumented_obligation_owner; assignment/routing/stewardship
# remains [ES]-gated in the draft named here.
SPLIT_NOTES = {
    ("compliance_obligation_tracking", "identify_obligation_owner_gaps"):
        "detection ratified as detect_undocumented_obligation_owner (v1.7); "
        "owner assignment, routing, and stewardship remain [ES]-gated here",
}

OUT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "docs", "skill-contracts")

# ------------------------------------------------------------- composition
ALLOWED_BY_PATTERN = {
    "conflict": "governed conflict relationships and their classifications\n    (MCP get_conflicts / get_domain_subgraph) at binding clearance",
    "coverage": "approved documents in scope (the situations/questions they\n    explicitly name) and the derived questions run through package\n    consume() under the packaged answering contract",
    "revision": "governed revision chains (MCP get_revision_history),\n    supersession classifications, and declared review-interval\n    statements inside governed documents",
    "extract": "approved documents in scope - explicit statements only (the\n    extract-candidates discipline)",
    "missing_evidence": "accepted obligation/requirement facts and the approved evidence\n    assets that should satisfy them",
    "deadline": "explicit dates and date rules inside governed sources",
    "compare": "the two governed document sets under comparison, at binding\n    clearance",
    "finding": "the compiled expert package and the MCP graph/read tools at\n    binding clearance",
    "assist": "approved knowledge in scope and ACCEPTED findings (DERIVED\n    facts) - never pending proposals",
    "platform": "the shipped platform surface this skill maps to (see the\n    registry's PLATFORM mapping)",
    "stewardship": "the computed exception queue (existence recomputed from\n    governed facts at read time)",
}

EVIDENCE_BY_PATTERN = {
    "conflict": "A finding requires a governed CONFLICTS_WITH relationship cited\n  with both asset ids and the relevant excerpts.\n  evidence_basis: CONFLICT_BACKED.",
    "coverage": "A finding requires the triggering governed excerpt (asset id +\n  quote) AND the reproducible INSUFFICIENT EVIDENCE refusal for the\n  derived question, with nearest partial evidence declared.\n  evidence_basis: REFUSAL_BACKED.",
    "revision": "A finding requires revision-chain evidence: supersession, guidance\n  aligned with a superseded revision, or a document overdue by its\n  OWN declared review interval. Never age alone.\n  evidence_basis: REVISION_BACKED.",
    "extract": "Explicit statements only - never invented, never inferred; every\n  candidate cites its source asset, excerpt, and section reference;\n  uncertain extraction is marked NEEDS_REVIEW.\n  evidence_basis: METADATA_BACKED (extraction).",
    "missing_evidence": "Absence becomes a finding, never a fact: the requirement's source\n  excerpt is cited together with the declared absence of approved\n  covering evidence. evidence_basis: REFUSAL_BACKED (absence).",
    "deadline": "Explicit dates and date rules only; fixed dates distinguished from\n  inferred recurrence; ambiguity flagged, never assumed; no silent\n  calendar or work items (ownership/due-date assignment is [ES]).\n  evidence_basis: METADATA_BACKED (explicit dates).",
    "compare": "Doc-vs-doc: both governed documents cited with the compared\n  excerpts; differences stated, never characterized beyond evidence.\n  evidence_basis: CONFLICT_BACKED or METADATA_BACKED per finding.",
    "finding": "Every finding cites the governed asset ids/hashes, relationship\n  ids, or reproducible refusals it rests on. No evidence, no finding.",
    "assist": "Every statement cited to governed assets; conflicts and gaps\n  referenced by their governed evidence; narrative framing declared\n  SYNTHESIS_INFERRED where tagged [synth].",
    "platform": "Inherited from the shipped platform surface (provenance, verifier\n  fingerprints, ledger events) - this skill adds no evidence rules of\n  its own.",
    "stewardship": "Exception existence is computed from governed facts; the human\n  decision (owner, acknowledgment, acceptance, dismissal reason,\n  escalation) persists as a governed identity-backed event keyed to\n  the exception's stable computed identity.",
}

GATE_TEXT = {
    "OE": "the Operational Evidence Realm decision is not minted - refuse\n    the task and name the gate",
    "PMD": "the Pipeline Metadata Door decision is not minted - refuse the\n    task and name the gate (and never candidate CONTENT, only\n    metadata, once it is)",
    "ES": "the Exception Stewardship decision is not minted - refuse the\n    task and name the gate (the exception never becomes a row; the\n    human decisions about it do)",
}


def prettify(skill_id):
    words = skill_id.replace("_vs_", " vs ").split("_")
    text = " ".join(words).replace(" vs ", " vs. ")
    return text[0].upper() + text[1:] + "."


def contract(wb_num, wb_id, wb_name, wb_status, skill_id, tags, pattern):
    tag_list = tags.split(",")
    gates = [t for t in tag_list if t in ("OE", "PMD", "ES")]
    is_assist = pattern == "assist" or "assist" in tag_list
    is_platform = pattern == "platform"
    is_stewardship = pattern == "stewardship"
    is_finding = not (is_assist or is_platform or is_stewardship)

    if (wb_id, skill_id) in CONSOLIDATED:
        status = "CONSOLIDATED"
    elif gates:
        status = "FUTURE"
    elif (wb_id, skill_id) in RATIFIED:
        status = "ACTIVE"
    elif (wb_id, skill_id) in DEFERRED_SEQUENCED:
        status = "SEQUENCED (deliberately deferred to after the [ES] scoping - the v1.7 deadline deferral)"
    elif wb_status.startswith("ACTIVE"):
        status = "DRAFT (workbench ACTIVE; this skill not in the ratified ACTIVE set)"
    elif wb_status.startswith("SEQUENCED"):
        status = "SEQUENCED"
    elif wb_status.startswith("PLATFORM"):
        status = "PLATFORM"
    else:
        status = "FUTURE"

    lines = []
    lines.append("# DRAFT skill contract - generated from the master subtask")
    lines.append("# inventory (docs/workbench-skill-registry.md) by")
    lines.append("# tools/generate_skill_contracts.py. Refined and ratified at the")
    lines.append("# workbench's own scoping session before entering")
    lines.append("# workbench/<name>/skills/ (registry rule 1).")
    lines.append("skill_id: %s" % skill_id)
    lines.append("workbench: %s   # %d. %s" % (wb_id, wb_num, wb_name))
    lines.append("status: %s" % status)
    if (wb_id, skill_id) in RATIFIED:
        lines.append("ratified_path: workbench/%s/skills/%s.yaml"
                     % (BUNDLE_DIR[wb_id], skill_id))
    if (wb_id, skill_id) in CONSOLIDATED:
        target = CONSOLIDATED[(wb_id, skill_id)]
        lines.append("consolidated_into: %s" % target)
        lines.append("ratified_path: workbench/%s/skills/%s.yaml"
                     % (BUNDLE_DIR[wb_id], target))
    if (wb_id, skill_id) in SPLIT_NOTES:
        lines.append("split_note: >")
        lines.append("  %s" % SPLIT_NOTES[(wb_id, skill_id)])
    lines.append("boundary_tags: [%s]" % ", ".join(tag_list))
    lines.append("pattern: %s" % pattern)
    lines.append("purpose: >")
    lines.append("  %s" % prettify(skill_id))
    lines.append("allowed_inputs: >")
    lines.append("  The four doors (.empkg at binding clearance; the MCP read tools")
    lines.append("  at the AGENT token's clearance); specifically: %s." % ALLOWED_BY_PATTERN[pattern])
    lines.append("forbidden_inputs: >")
    lines.append("  Ungoverned sources; unapproved/candidate/held content;")
    lines.append("  transactional records (until [OE]); other skills' pending")
    lines.append("  (ungated) findings; rendered vault notes as authority (D31).")
    lines.append("evidence_rules: >")
    lines.append("  %s" % EVIDENCE_BY_PATTERN[pattern])
    if is_finding:
        lines.append("allowed_finding_kinds: [%s]" % skill_id.upper())
    else:
        lines.append("allowed_finding_kinds: []   # %s output - never a finding"
                     % ("assist" if is_assist else ("platform" if is_platform else "stewardship")))
    lines.append("output_format: >")
    if is_finding:
        lines.append("  One proposal document per finding to /08_proposals with the D30 +")
        lines.append("  catalog frontmatter claims (workbench, skill, skill_version,")
        lines.append("  finding_kind, evidence_basis); body = business statement,")
        lines.append("  evidence, proposed action, impact [synth-declared] if any.")
    elif is_assist:
        lines.append("  A cited brief/draft/pack for humans - never written to")
        lines.append("  /08_proposals, never enters knowledge.")
    elif is_platform:
        lines.append("  The shipped platform surface's existing output; this skill is a")
        lines.append("  mapping, not new machinery.")
    else:
        lines.append("  A governed stewardship decision event (once [ES] is minted);")
        lines.append("  the queue remains the computed join.")
    lines.append("human_approval_requirement: >")
    if is_finding:
        lines.append("  The valve (D29): every finding is a held CANDIDATE until a human")
        lines.append("  accepts it as a DERIVED fact; no policy tier ever applies.")
    elif is_assist:
        lines.append("  None - the output never enters knowledge. Content meant to become")
        lines.append("  knowledge is authored by a human (PRIMARY) or proposed through")
        lines.append("  the valve.")
    elif is_platform:
        lines.append("  Inherited from the platform surface's own governance.")
    else:
        lines.append("  The human decision IS the governed act - identity-backed,")
        lines.append("  audited, never automated.")
    lines.append("audit_event: >")
    lines.append("  MCP calls audited per call; scan/hold/gate events are the ledger")
    lines.append("  trail; approvals quote verified provenance verbatim.")
    lines.append("refusal_conditions:")
    lines.append("  - evidence cannot be cited from governed records -> refuse to emit")
    lines.append("  - uncertain or ambiguous input -> NEEDS_REVIEW, never guess")
    for gate in gates:
        lines.append("  - %s" % GATE_TEXT[gate])
    if "synth" in tag_list:
        lines.append("  - synthesized content not declared SYNTHESIS_INFERRED -> refuse")
    return "\n".join(lines) + "\n"


def main():
    if os.path.isdir(OUT_ROOT):
        shutil.rmtree(OUT_ROOT)
    total = 0
    for wb_num, wb_id, wb_name, wb_status, skills in INVENTORY:
        folder = os.path.join(OUT_ROOT, "%02d_%s" % (wb_num, wb_id))
        os.makedirs(folder)
        for skill_id, tags, pattern in skills:
            path = os.path.join(folder, "%s.yaml" % skill_id)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(contract(wb_num, wb_id, wb_name, wb_status, skill_id, tags, pattern))
            total += 1
        print("%02d %-36s %3d skills" % (wb_num, wb_id, len(skills)))
    print("TOTAL: %d skill contracts -> %s" % (total, OUT_ROOT))


if __name__ == "__main__":
    main()
