# The Workbench Skill Registry — the Master Subtask Inventory

> Companion to **docs/workbench-catalog.md**. Ratified 2026-07-03 at
> the v1.6 WS0 gate (amended the same day: the complete 16-workbench
> master subtask inventory entered by user ruling). This registry is
> the operating inventory of the whole commercial catalog: **every
> workbench, every subtask, each as a named agent skill.** A workbench
> is never a screen or a broad agent — it is a catalog of governed
> subtasks, and each subtask has its own skill contract.
>
> The architecture this registry serves:
>
> ```
> Workbench Catalog
>   → Workbench
>     → Subtask List
>       → Skill Contract
>         → YAML implementation
>           → Tests
>             → UI/API surface
>               → Findings
>                 → Human approval
>                   → APPROVED DERIVED fact
> ```
>
> The 16 workbenches give the commercial map. The subtasks give the
> operating inventory. The skill contracts give the agent execution
> discipline.
>
> **Status of this document:** the registry is the catalog-level DRAFT
> of every contract. The binding, versioned `skills/*.yaml` contracts
> are ratified at each workbench's own scoping session and live in
> `workbench/<name>/skills/`. Statuses: **ACTIVE** (v1.6, being
> built) · **SEQUENCED** (drafted, waits for its workbench scope) ·
> **PLATFORM** (maps to already-shipped machinery) · **FUTURE**
> (roadmap only).
>
> **The canonical 16 workbenches** (normalized at the WS0 gate from
> the original 14: Customer Support and Customer Success split;
> Contract Intelligence added): 1 Executive/CEO · 2 Finance & Cost
> Leakage · 3 Procurement & Vendor Intelligence · 4 Sales & Account
> Growth · 5 Customer Support (= the v1.6 Customer Operations
> Workbench) · 6 Customer Success/Retention · 7 HR/People Operations ·
> 8 Operations/Process Improvement · 9 Compliance/Obligation Tracking
> · 10 Document/Knowledge Quality · 11 Project/Delivery · 12 Internal
> IT/SaaS · 13 Meeting Intelligence/Decision Follow-up · 14 Ask
> Company Expert · 15 Risk & Exception · 16 Contract Intelligence.

## Boundary tags — tags are gates, not preferences

- **[now]** — buildable today on the four doors over governed
  documents. D27-clean.
- **[OE]** — requires the **Operational Evidence Realm** (tickets,
  invoices, POs, payments, CRM activity, logs, usage data). Refused
  until minted.
- **[PMD]** — requires the **Pipeline Metadata Door** (agent-readable
  metadata about ungated material). Refused until minted.
- **[ES]** — requires **Exception Stewardship** (owners, due dates,
  acknowledgments — human decisions persisted, existence computed).
  **MINTED as D32 at v2.0** (docs/exception-stewardship-v2.0.md): the
  platform HUMAN SURFACE is delivered — stewardship decisions are
  append-only `STEWARDSHIP_DECISION` ledger events keyed to the
  computed exception identity; the queue is the join. The tag now
  reads: the human surface exists; **[ES]-tagged skills in other
  workbenches remain gated per-workbench** (they are agent-side
  owner/routing questions — stewardship pens stay in human hands, and
  each workbench ratifies its own [ES] slice at its own scoping).
- **[assist]** — a consumption output (brief, draft, pack, answer),
  not a finding: never enters knowledge, no valve implications.
- **[synth]** — declared SYNTHESIS_INFERRED content (scenarios,
  estimates, proposals), never a governed number or fact.

## The skill contract — ten fields, one YAML shape

Ten-field contract shape:

> skill name · purpose · allowed inputs · forbidden inputs · governed
> evidence rules · allowed finding kinds · output format · human
> approval requirement · audit expectations · failure & refusal
> conditions

The YAML implementation shape (`workbench/<name>/skills/<skill>.yaml`):

```yaml
skill_id:
workbench:
status:            # ACTIVE | SEQUENCED | PLATFORM | FUTURE
boundary_tags:     # [now] / [OE] / [PMD] / [ES] / [assist] / [synth]
purpose:
allowed_inputs:
forbidden_inputs:
evidence_rules:
allowed_finding_kinds:
output_format:
human_approval_requirement:
audit_event:
refusal_conditions:
```

## The base contract (inherited by EVERY skill; entries below add only specifics)

- **Forbidden inputs (always):** ungoverned sources; unapproved /
  candidate / held content (until [PMD], and then metadata only);
  transactional records (until [OE]); other skills' raw ungated
  findings (skills compose ACROSS the valve — a skill may consume
  another skill's ACCEPTED DERIVED facts, never its pending
  proposals); rendered vault notes as authority (readable lens,
  never citable truth — D31).
- **Evidence rules (always):** evidence = governed asset ids/hashes,
  conflict relationship ids, revision chains, or reproducible
  refusals, obtained through the doors at clearance. **No evidence,
  no finding.** Exclusions declared. DERIVED evidence cited as
  DERIVED (D30 derivation depth).
- **Output format (always, finding skills):** one proposal document
  per finding to `/08_proposals`; frontmatter = the D30 claims
  (agent principal, binding, package hash, cited assets) + the
  catalog claims (workbench, skill, skill_version, finding_kind,
  evidence_basis); body = business statement, evidence, proposed
  action, impact [synth-declared] if any.
- **Human approval (always):** the valve (D29). Every finding is a
  held CANDIDATE until a human accepts it as a DERIVED fact; no
  policy tier ever applies. [assist] outputs never enter knowledge
  at all.
- **Audit (always):** MCP calls audited per call; scan, hold, and
  gate events are the ledger trail; approval quotes verified
  provenance verbatim.
- **Refusal (always):** no citable evidence → refuse to emit;
  uncertain/ambiguous → `NEEDS_REVIEW`, never guess; unminted tag
  ([OE]/[PMD]/[ES]) → refuse the task and name the gate.

---

## 1. Executive / CEO Workbench — two-stage by ruling (v1 [now], decision queue behind [PMD])

Purpose: governed leadership view of company health, decisions,
blockers, risks, and evidence gaps — trusted operational
interpretation, not another dashboard.

1. `generate_weekly_ceo_briefing` [assist]
2. `summarize_company_status` [now, assist]
3. `identify_major_operational_risks` [now]
4. `detect_unresolved_blockers_by_department` [now for conflicts/gates; held proposals PMD]
5. `compare_period_vs_previous` [now for governance history; operational metrics OE]
6. `identify_decisions_needing_approval` [PMD]
7. `identify_unsupported_claims` [now]
8. `summarize_unresolved_conflicts` [now]
9. `summarize_accepted_findings` [now — accepted DERIVED facts, class visible per D30]
10. `summarize_governance_health` [now — missing approvals, stale documents, unresolved reviews]
11. `prepare_board_report` [assist]
12. `answer_what_changed_since` [now — revision/render/ledger history]
13. `produce_executive_decision_queue` [PMD]
14. `produce_cross_functional_risk_register` [now; owners ES]
15. `produce_recommended_next_actions` [assist, synth]
16. `generate_unknowns_evidence_gaps_report` [now]

Boundary note: executive briefing over accepted facts is possible
now. Decision-queue visibility over pending proposals requires the
metadata-only Pipeline Metadata Door — never candidate-content
exposure.

---

## 2. Finance & Cost Leakage Workbench — document-bound until [OE]

Purpose: detect cost leakage and finance exceptions; v1 stays
document-bound. The agent never changes canonical accounting data —
it creates findings.

1. `extract_payment_terms` [now]
2. `compare_contract_terms_vs_finance_policy` [now]
3. `detect_contract_price_increases` [now — clause-level]
4. `detect_renewal_cost_risk` [now — renewal/auto-renewal clauses]
5. `identify_unused_service_obligations` [now — from contracts]
6. `detect_missing_spend_approval_evidence` [now]
7. `identify_budget_policy_conflicts` [now]
8. `prepare_cfo_cost_reduction_scenario` [assist, synth]
9. `detect_pricing_clauses_requiring_review` [now]
10. `identify_payment_term_mismatch_risk` [now]
11. `generate_monthly_finance_exception_report` [now — over governed findings]
12. `prepare_finance_evidence_pack` [assist]
13. `identify_leakage_clauses` [now]
14. `identify_finance_policy_coverage_gaps` [now]
15. `detect_outdated_finance_policies` [now]
16. `identify_missing_finance_obligation_owner` [ES]

Future [OE]: `detect_duplicate_invoices` · `compare_po_vs_invoices` ·
`detect_unusual_cost_increases` · `flag_overdue_receivables` ·
`detect_budget_overrun_from_accounting` ·
`detect_payment_terms_not_followed`.

Boundary note: invoice, PO, payment, and accounting-ledger analysis
belongs behind the future Operational Evidence decision.

---

## 3. Procurement & Vendor Intelligence Workbench — SEQUENCED (third)

Purpose: vendor contract, obligation, renewal, certification, and
renegotiation intelligence.

1. `summarize_vendor_contracts` [assist]
2. `extract_vendor_terms` [now]
3. `detect_expiring_contracts` [now — explicit dates]
4. `detect_auto_renewal_clauses` [now]
5. `detect_price_increase_clauses` [now]
6. `identify_missing_supplier_certifications` [now — missing-evidence pattern]
7. `extract_sla_obligations` [now]
8. `compare_vendor_terms_vs_procurement_policy` [now]
9. `prepare_renegotiation_brief` [assist, synth]
10. `detect_single_supplier_dependency` [now — from contracts]
11. `propose_vendor_consolidation` [synth]
12. `identify_missing_vendor_approval_evidence` [now]
13. `identify_vendor_data_access_obligations` [now]
14. `detect_outdated_supplier_documents` [now]
15. `prepare_vendor_risk_list` [now, synth]
16. `prepare_contract_evidence_package` [assist]
17. `generate_negotiation_points` [assist, synth]
18. `identify_owner_gaps` [ES]
19. `detect_vendor_contract_vs_policy_conflict` [now]
20. `identify_vendor_obligations_next_period` [now — deadline pattern]

Future [OE]: `compare_sla_obligations_vs_service_records` ·
`compare_contract_pricing_vs_invoices` ·
`detect_vendor_usage_vs_license_count` ·
`detect_supplier_performance_gaps`.

---

## 4. Sales & Account Growth Workbench — FUTURE (Layer 3)

Purpose: governed customer/account intelligence — the intelligence
layer above CRM, never a CRM replacement.

1. `prepare_customer_account_briefing` [assist]
2. `summarize_customer_contract_obligations` [now]
3. `summarize_customer_history_documents` [assist]
4. `detect_missing_proposal_evidence` [now]
5. `compare_customer_needs_vs_documentation` [now]
6. `identify_unsupported_sales_claims` [now]
7. `detect_unbacked_proposal_promises` [now — proposal-vs-docs, doc-vs-doc]
8. `prepare_meeting_talking_points` [assist]
9. `generate_proposal_checklist` [assist]
10. `identify_customer_sla_terms` [now]
11. `detect_outdated_sales_collateral` [now]
12. `detect_sales_vs_policy_contradictions` [now]
13. `prepare_followup_email_draft` [assist]
14. `identify_customer_risk_obligations` [now]
15. `generate_account_evidence_pack` [assist]
16. `identify_approval_required_commitments` [now]

Future [OE]: `detect_stalled_opportunities` ·
`identify_upsell_from_activity` · `detect_declining_activity` ·
`summarize_recent_orders` · `compare_crm_history_vs_obligations`.

---

## 5. Customer Support Workbench (= Customer Operations, v1.6) — ACTIVE

Purpose: support teams with approved guidance, contradictions, gaps,
escalation logic, and safe answer drafting. Build contract:
docs/customer-ops-workbench-v1.6.md. The wedge: *"ExpertMachina finds
where customer promises, support procedures, SLA obligations, and
customer-facing guidance do not line up — before customers are
harmed."*

1. `answer_support_questions` [assist — platform posture]
2. `suggest_customer_replies` [assist]
3. `detect_macro_vs_policy_contradictions` [now — promise-conflict scope]
4. **`detect_missing_support_playbook` [now] — ACTIVE (v1.6)**
5. **`detect_outdated_customer_guidance` [now] — ACTIVE (v1.6)**
6. `detect_refund_policy_conflicts` [now — promise-conflict scope]
7. `detect_escalation_path_gaps` [now]
8. **`detect_sla_obligation_gap` [now] — ACTIVE (v1.6)**
9. `compare_help_docs_vs_internal_sops` [now]
10. **`prepare_customer_policy_brief` [assist, synth] — ACTIVE (v1.6)**
11. `identify_unsupported_customer_claims` [now]
12. `identify_documentation_gaps_by_category` [now]
13. `generate_escalation_recommendation` [assist]
14. `prepare_support_training_pack` [assist]
15. `detect_inconsistent_terminology` [now, synth]
16. `detect_missing_procedure_owner` [ES]
17. `produce_approved_answer_pack` [now — the .empkg platform door]
18. `flag_unapproved_content` [PMD]

Plus the umbrella ACTIVE skill:
**`detect_customer_promise_conflict` [now] — ACTIVE (v1.6)** — the
customer-outcome specialization covering subtasks 3 and 6 (and every
customer-facing-promise vs internal-guidance pair).

Future [OE]: `review_weekly_tickets` · `detect_repeated_complaints` ·
`identify_product_issues_from_tickets` ·
`detect_sla_breaches_from_timestamps` ·
`escalate_high_risk_customers` [also ES] · `summarize_open_cases`.
"Review this week's tickets" stays a refused demo question until [OE]
is minted.

### The five ACTIVE contracts (v1.6, in full)

#### `detect_customer_promise_conflict` [now] — ACTIVE
- Base pattern: contradictory-guidance (doc-vs-doc conflict).
- Purpose: contradictions between customer-facing promises and what
  the company can deliver — sales materials, contracts, refund rules,
  SLA documents vs support policies and internal procedures. ("Sales
  material promises 24-hour response for enterprise customers, but
  the support SOP defines 48-hour escalation.")
- Allowed inputs: domain subgraph + `get_conflicts` at binding
  clearance, scoped to customer-facing ↔ internal pairs.
- Evidence rules: the governed CONFLICTS_WITH relationship + both
  asset ids + the promise excerpt; evidence_basis CONFLICT_BACKED.
- Finding kinds: CUSTOMER_PROMISE_CONFLICT.
- Refuses when: no governed conflict relationship exists (a suspected
  misalignment without one is deferred
  `detect_process_inconsistency` territory).

#### `detect_missing_support_playbook` [now] — ACTIVE
- Base pattern: coverage-gap (refusal-backed).
- Purpose: customer situations that approved contracts/policies
  create but no approved support procedure covers. ("Refund policy
  allows exceptions for enterprise customers, but no approved
  escalation playbook exists.")
- Allowed inputs: policy/contract assets in scope (the situations
  they name) + the derived procedure questions through package
  `consume()`.
- Evidence rules: the triggering policy excerpt (asset id + quote) +
  the reproducible INSUFFICIENT EVIDENCE refusal + nearest partial
  evidence; evidence_basis REFUSAL_BACKED.
- Finding kinds: MISSING_SUPPORT_PLAYBOOK.
- Refuses when: the corpus answers the procedure question (live-proven
  refusal condition), or the "situation" is not explicitly named by a
  governed document.

#### `detect_outdated_customer_guidance` [now] — ACTIVE
- Base pattern: outdated-guidance (revision-backed).
- Purpose: customer-facing or support-facing guidance that is
  superseded, tracks a superseded revision, or is overdue by its own
  declared review cycle. ("The support FAQ still states the 30-day
  refund window; the approved refund policy has been revision 2 —
  14 days — since March.")
- Allowed inputs: conflicts + classifications, `get_revision_history`
  chains, declared review-interval statements in governed documents.
- Evidence rules: revision chain / supersession classification / the
  document's own declared review interval; **never age alone**;
  evidence_basis REVISION_BACKED.
- Finding kinds: OUTDATED_CUSTOMER_GUIDANCE.
- Refuses when: recency cannot be established from governed revision,
  supersession, or self-declared review-cycle evidence.

#### `detect_sla_obligation_gap` [now] — ACTIVE
- Base patterns: extract-candidates + missing-evidence.
- Purpose: SLA and customer-obligation statements in approved
  documents with no internal procedure explaining fulfillment.
  ("Customer contract requires monthly service reporting, but no
  approved reporting procedure or owner is documented.")
- Allowed inputs: approved contracts/SLA documents (explicit
  obligation statements only) + the derived fulfillment questions
  through `consume()`.
- Evidence rules: the obligation excerpt (asset id + quote, explicit
  only, never inferred) + the reproducible refusal / absence of any
  covering procedure; **absence becomes a finding, never a fact**;
  evidence_basis REFUSAL_BACKED with the obligation excerpt cited.
- Finding kinds: SLA_OBLIGATION_GAP.
- Refuses when: the obligation is implied rather than explicit
  (NEEDS_REVIEW), or a covering procedure exists.

#### `prepare_customer_policy_brief` [assist, synth] — ACTIVE
- Base pattern: assist (cited drafts, no valve implications).
- Purpose: an evidence-backed internal brief for a named
  customer-operations topic (refunds, escalations, response times,
  complaint handling): approved guidance + the conflicts, gaps, and
  escalation points the finding skills surfaced.
- Allowed inputs: approved knowledge in scope + ACCEPTED findings
  (DERIVED facts — never pending proposals).
- Evidence rules: every statement cited; conflicts/gaps referenced by
  their governed evidence; narrative framing declared [synth].
- Output: a brief for humans — never a finding, never enters
  knowledge. (With finding narration, the vehicle for the real-model
  honest slot.)
- Refuses when: the topic has no approved coverage — it says so
  rather than composing an unsupported narrative.

### Base patterns (the original four — named, kept, reused)

`detect_contradictory_guidance` → behind
`detect_customer_promise_conflict` · `detect_coverage_gap` → behind
`detect_missing_support_playbook` · `detect_outdated_guidance` →
specialized as `detect_outdated_customer_guidance` ·
`detect_process_inconsistency` [now, synth] → **DEFERRED** (drafted,
not ACTIVE) until a corpus carries enough procedural material.

---

## 6. Customer Success / Retention Workbench — FUTURE (split at the WS0 gate)

Purpose: customer obligations, retention risks, renewal needs, and
customer-success actions from governed knowledge.

1. `summarize_customer_success_obligations` [now]
2. `identify_customer_renewal_obligations` [now — deadline pattern]
3. `detect_missing_customer_success_playbooks` [now — coverage-gap pattern]
4. `detect_customer_obligations_without_owner` [ES]
5. `detect_cs_policy_vs_contract_contradiction` [now]
6. `prepare_customer_retention_brief` [assist]
7. `identify_unbacked_promised_outcomes` [now — promise vs delivery process, doc-vs-doc]
8. `detect_missing_qbr_reporting_procedure` [now]
9. `extract_customer_communication_obligations` [now]
10. `identify_strategic_customer_escalation_rules` [now]
11. `detect_outdated_cs_documentation` [now]
12. `generate_customer_success_evidence_pack` [assist]
13. `prepare_renewal_readiness_checklist` [assist]
14. `detect_missing_service_commitment_evidence` [now — missing-evidence pattern]
15. `identify_unbacked_customer_health_assumptions` [now]
16. `prepare_internal_customer_risk_briefing` [assist, synth]

Future [OE]: `detect_declining_activity` · `detect_low_usage` ·
`detect_unresolved_customer_issues` · `score_customer_risk` [synth] ·
`cluster_recurring_complaints` · `identify_churn_signals`.

---

## 7. HR / People Operations Workbench — FUTURE (Layer 3, positioning-sensitive)

Purpose: governed HR knowledge clarity, onboarding, training gaps,
policy conflicts, role/process documentation. The safe posture: role
clarity, training, onboarding, gaps, and human-reviewed scenarios —
never "AI fires people."

1. `generate_onboarding_package` [assist]
2. `answer_hr_policy_questions` [assist — Ask Expert posture]
3. `detect_hr_policy_contradictions` [now]
4. `detect_outdated_hr_documents` [now]
5. `detect_missing_training_requirements` [now — from governed documents]
6. `detect_missing_onboarding_steps` [now — coverage-gap pattern]
7. `compare_job_descriptions_vs_role_documentation` [now — doc-vs-doc]
8. `identify_hr_policy_coverage_gaps` [now]
9. `prepare_role_handover_package` [assist]
10. `detect_expired_certification_requirements` [now]
11. `generate_internal_hr_faq` [now — via the valve: synthesis → proposal → DERIVED]
12. `identify_missing_hr_process_owner` [ES]
13. `detect_benefits_vs_employment_policy_contradiction` [now]
14. `prepare_hiring_manager_briefing` [assist]
15. `detect_key_person_dependency` [now, synth — from documented responsibilities]
16. `prepare_workforce_scenario` [synth — SYNTHESIS_INFERRED, never fact; human leadership decides]
17. `detect_equipment_access_policy_gaps` [now]
18. `detect_training_evidence_gaps` [now — missing-evidence pattern over governed records]

---

## 8. Operations / Process Improvement Workbench — FUTURE (Layer 3, document-first)

Purpose: process gaps, bottlenecks, handoff failures, SOP
inconsistencies, and automation candidates.

1. `map_documented_business_process` [now, synth]
2. `detect_missing_handoffs` [now]
3. `detect_duplicated_process_steps` [now]
4. `compare_sop_vs_policy` [now]
5. `detect_process_contradictions` [now]
6. `detect_missing_approval_steps` [now]
7. `detect_undocumented_process_areas` [now]
8. `identify_process_variants_across_departments` [now — doc-vs-doc]
9. `generate_process_improvement_backlog` [now, synth — via the valve]
10. `propose_automation_candidates` [synth]
11. `identify_missing_process_stage_owner` [ES]
12. `detect_outdated_process_documents` [now]
13. `prepare_process_map_projection` [assist]
14. `detect_rework_risk_from_conflicting_instructions` [now]
15. `identify_required_approvals_for_process_changes` [now]
16. `prepare_improvement_proposal` [now, synth — evidence-backed, via the valve]
17. `estimate_improvement_impact` [synth — SYNTHESIS_INFERRED only]
18. `detect_customer_impacting_process_gaps` [now]

Future [OE]: `compare_sop_vs_execution_logs` ·
`detect_stage_delays` · `detect_bottlenecks_from_traces` ·
`process_mining_from_operational_systems`.

---

## 9. Compliance / Obligation Tracking Workbench — ACTIVE (v1.7, second)

Purpose: extract, track, evidence, and answer obligations from
governed documents. The most defensible EM-native workbench — the
"no evidence = no answer" founding story, productized. Build
contract: docs/compliance-workbench-v1.7.md. **The sensitivity
posture (v1.7 WS0, ratified): compliance overclaiming is the cardinal
sin — the workbench says what approved documents state, omit,
contradict, supersede, or cannot answer, never what the company does.
Document-grounded, or refused.**

**THE ACTIVE SIX (v1.7, ratified — bundle:
`workbench/compliance_obligation/`):**

| ACTIVE skill (v1.7) | Base pattern | Finding kind · evidence basis |
|---|---|---|
| `extract_compliance_obligations` | extract-candidates | COMPLIANCE_OBLIGATION · EXCERPT_BACKED (verbatim must/shall excerpt + declared source_type + obligation_type, UNCLASSIFIED when unsupported) |
| `detect_missing_evidence` | missing-evidence | MISSING_COMPLIANCE_EVIDENCE · REFUSAL_BACKED (declared requirement classes; covered controls produce NO finding) |
| `identify_outdated_policies` | outdated-guidance | OUTDATED_POLICY · REVISION_BACKED (supersession OR the document's OWN declared review interval overdue at a declared as_of — never age alone) |
| `detect_undocumented_obligation_owner` | missing-evidence (owner axis) | UNDOCUMENTED_OBLIGATION_OWNER · REFUSAL_BACKED (THE SPLIT RULING: detection [now]; assignment/routing stays [ES]) |
| `detect_conflicting_compliance_statements` | contradictory-guidance | CONFLICTING_COMPLIANCE_STATEMENTS · CONFLICT_BACKED (the v1.6 evidence rules inherited wholesale) |
| `prepare_audit_readiness_pack` | assist | [assist] — known/missing/contradictory/unverified clearly separated; never a finding |

**The consolidation ruling (v1.7 WS0):** subtasks 1–5 below
consolidate into `extract_compliance_obligations` (declared
`source_type`; `classify_obligation_type` folded in as
`obligation_type`); subtasks 19–21 consolidate into
`detect_missing_evidence` (declared requirement classes). Their
drafts carry `status: CONSOLIDATED` + `consolidated_into` + a
resolving `ratified_path` — consolidation is never silent promotion.
**The deadline deferral (v1.7 WS0) — RESOLVED at v2.2:** subtasks 6,
7, 17, 18 stayed SEQUENCED through five milestones because persistent
deadline stewardship risked a second operational state machine before
[ES] was scoped. D32 answered the fear by name (*decisions persist;
existence never does*), and the v2.2 WS0 gate
(docs/deadline-obligation-v2.2.md) ratified the family as detection
at a declared clock: 6, 17, 18 CONSOLIDATE into
`detect_obligation_deadlines`; 7 into `extract_recurrence_rules`; the
snapshot brief ships as `prepare_obligation_calendar_brief` [assist].
The tracking verb died at scoping — no deadline table, no calendar
store, no reminder; THE INVENTED DATE and THE PRESUMED COMPLETION are
the extension's cardinal sins.

1. `extract_obligations_from_contracts` [now — CONSOLIDATED → extract_compliance_obligations]
2. `extract_obligations_from_policies` [now — CONSOLIDATED → extract_compliance_obligations]
3. `extract_obligations_from_certifications` [now — CONSOLIDATED → extract_compliance_obligations]
4. `extract_obligations_from_regulatory_documents` [now — CONSOLIDATED → extract_compliance_obligations]
5. `classify_obligation_type` [now — CONSOLIDATED → extract_compliance_obligations (the obligation_type field)]
6. `track_explicit_deadlines` [now — CONSOLIDATED → detect_obligation_deadlines (v2.2; detection at a declared clock, never tracking)]
7. `track_recurrence_rules` [now — CONSOLIDATED → extract_recurrence_rules (v2.2; verbatim, never expanded; ambiguity flagged, never assumed)]
8. `detect_missing_evidence` [now — **ACTIVE (v1.7)**; absence is a finding, never a fact]
9. `identify_outdated_policies` [now — **ACTIVE (v1.7)**; never age alone]
10. `compare_policy_vs_policy` [now]
11. `compare_contract_obligation_vs_procedure` [now]
12. `prepare_audit_readiness_pack` [assist — **ACTIVE (v1.7)**; approved evidence only; known/missing/contradictory/unverified clearly separated]
13. `detect_unapproved_compliance_guidance` [PMD]
14. `generate_compliance_evidence_binder` [assist — every section links to governed facts; no generated legal conclusion]
15. `answer_auditor_questions` [assist — approved evidence only, refusals first-class]
16. `identify_obligation_owner_gaps` [ES — THE SPLIT RULING: detection ratified as `detect_undocumented_obligation_owner` (**ACTIVE, v1.7**); assignment/routing/stewardship stays gated here]
17. `identify_upcoming_obligations_30_60_90` [now — CONSOLIDATED → detect_obligation_deadlines (v2.2; the declared window_days facet)]
18. `detect_certification_expiry_risk` [now — CONSOLIDATED → detect_obligation_deadlines (v2.2; the certification_expiry class)]
19. `detect_reporting_obligation_gaps` [now — CONSOLIDATED → detect_missing_evidence]
20. `detect_notification_obligation_gaps` [now — CONSOLIDATED → detect_missing_evidence]
21. `detect_sla_evidence_gaps` [now — CONSOLIDATED → detect_missing_evidence]
22. `prepare_compliance_risk_register` [now, synth; owners ES]
23. `generate_obligation_approval_queue` [now — the human gate surface; agent-side visibility PMD]
24. `refuse_unsupported_compliance_claims` [now — a refusal discipline, contract-mandatory]

Plus the two v1.7-minted skills: **`extract_compliance_obligations`
[now] — ACTIVE** (the consolidating extraction contract) and
**`detect_undocumented_obligation_owner` [now] — ACTIVE** (the
detection half of the owner split); and
**`detect_conflicting_compliance_statements` [now] — ACTIVE** (the
compliance specialization of the conflict pattern).

Plus the three v2.2-minted skills (the deadline extension —
docs/deadline-obligation-v2.2.md): **`detect_obligation_deadlines`
[now] — ACTIVE (v2.2)** (explicit deadlines inside a declared window
at a declared as_of; DEADLINE_AMBIGUITY flagged, never dated; accepted
v2.1 register clauses are first-class inputs BY ID — THE HARVEST),
**`extract_recurrence_rules` [now] — ACTIVE (v2.2)** (verbatim
recurrence language; never expanded into occurrences), and
**`prepare_obligation_calendar_brief` [assist, synth] — ACTIVE
(v2.2)** (the point-in-time snapshot brief; THE COMPUTED CALENDAR —
persistence refused, the v1.8 refusal carried).

Future [OE]: `compare_policy_vs_practice` ·
`verify_obligations_against_operational_records` ·
`detect_missed_operational_reporting_events` ·
`detect_practice_evidence_from_logs_tickets_payments` — exactly the
practice claims the sensitivity posture refuses today.

(The nine originally worked contract examples — extract_obligations,
track_deadlines, detect_missing_evidence, identify_outdated_policies,
compare_policy_vs_practice, prepare_audit_pack,
detect_unapproved_changes, generate_evidence_binder,
answer_auditor_questions — stand as the reference decomposition;
their disciplines were distributed across the inventory above and
ratified at the v1.7 scoping session exactly as registry rule 1
prescribes.)

---

## 10. Document / Knowledge Quality Workbench — PLATFORM (Layer 1)

Purpose: improve governed knowledge quality before agents rely on it.
Boundary note: partly platform primitive already — positioning must
not blur "ExpertMachina governing itself" with "business workbench."

1. `detect_outdated_documents` [now — platform: revision freshness]
2. `detect_contradictory_instructions` [now — platform: conflict engine]
3. `detect_missing_document_owner` [ES]
4. `detect_documents_without_approval` [PMD for agents; shipped human surface]
5. `detect_duplicate_knowledge` [now — platform: content-hash dedup]
6. `detect_undocumented_processes` [now]
7. `recommend_documents_needing_review` [now — computed inbox posture]
8. `compile_department_knowledge_package` [now — the .empkg compiler]
9. `create_approved_answer_packs` [now — platform]
10. `detect_conflicting_sops` [now]
11. `detect_policy_vs_training_conflicts` [now]
12. `detect_stale_customer_facing_documents` [now]
13. `detect_missing_provenance` [now — platform: honest-provenance discipline]
14. `detect_weak_evidence_claims` [now]
15. `detect_unsupported_claims` [now]
16. `detect_broken_internal_references` [now]
17. `detect_missing_domain_classification` [now — platform: D27 NULL domains]
18. `detect_ambiguous_terminology` [now, synth]
19. `detect_multiple_active_policy_versions` [now]
20. `detect_governance_status_mismatch` [now]
21. `prepare_knowledge_quality_scorecard` [assist — projection]
22. `generate_review_owner_recommendation` [ES]
23. `prepare_proposed_resolution_draft` [now — via the valve, never a resolution]
24. `surface_unresolved_conflict_clusters` [now — platform]

---

## 11. Project / Delivery Workbench — FUTURE (Layer 3)

Purpose: project status, commitments, scope, risks, deliverables, and
client update intelligence.

1. `summarize_project_status` [assist]
2. `extract_project_commitments` [now — extract-candidates pattern]
3. `detect_missed_deliverables_from_plans` [now]
4. `compare_contract_scope_vs_project_plan` [now]
5. `identify_scope_creep_risk` [now]
6. `prepare_client_update_draft` [assist]
7. `detect_missing_deliverables` [now — missing-evidence pattern]
8. `identify_deadline_risk_from_plans` [now, synth]
9. `compare_project_plan_vs_meeting_notes` [now]
10. `prepare_handover_package` [assist]
11. `generate_lessons_learned_draft` [now, synth — via the valve]
12. `identify_unresolved_risks` [now]
13. `extract_owner_deadline_action_from_notes` [now]
14. `detect_commitment_without_owner` [now; stewardship ES]
15. `detect_decision_without_evidence` [now]
16. `detect_dependency_gaps` [now]
17. `prepare_internal_action_list` [assist]
18. `generate_project_evidence_pack` [assist]
19. `detect_contract_obligation_not_in_plan` [now]
20. `detect_outdated_project_documentation` [now]

Future [OE]: `compare_plan_vs_task_system` ·
`detect_blocked_tasks_from_task_systems` ·
`detect_deadline_risk_from_execution_data` ·
`detect_delivery_delays_from_logs`.

---

## 12. Internal IT / SaaS Workbench — FUTURE (Layer 3)

Purpose: IT knowledge, SaaS/vendor governance, renewal risk, access
policy, license documentation, helpdesk guidance. Never autonomous
infrastructure control (the D22 posture).

1. `build_saas_inventory_from_documents` [now]
2. `extract_saas_owners` [now; owner GAPS are ES]
3. `extract_renewal_dates` [now]
4. `extract_vendor_cost_terms` [now]
5. `identify_unsupported_systems` [now — from approved policy/lifecycle docs]
6. `detect_renewal_risk` [now]
7. `detect_shadow_it_risk_from_documents` [now; live discovery OE]
8. `compare_security_policy_vs_approved_tools` [now]
9. `generate_it_helpdesk_answers` [assist]
10. `prepare_migration_plan` [assist, synth]
11. `identify_missing_it_system_owner` [ES]
12. `detect_outdated_it_policies` [now]
13. `detect_missing_data_access_approvals` [now — missing-evidence pattern]
14. `detect_missing_vendor_security_certification` [now]
15. `prepare_it_asset_register_projection` [assist]
16. `detect_access_policy_gaps` [now — policy-vs-policy]
17. `identify_saas_consolidation_candidates` [synth — from contracts]
18. `prepare_it_renewal_calendar` [assist]
19. `detect_it_policy_vs_vendor_contract_contradiction` [now]
20. `generate_it_risk_list` [now, synth]

Future [OE]: `detect_unused_accounts` · `detect_unused_licenses` ·
`compare_user_count_vs_license_count` · `summarize_incidents` ·
`detect_access_right_violations`.

---

## 13. Meeting Intelligence / Decision Follow-up Workbench — PLATFORM-ADJACENT (Layer 1, deferred surface)

Purpose: turn meeting records into governed decisions, actions,
risks, and evidence gaps — governed company memory.

1. `extract_decisions_from_meeting_notes` [now — extract-candidates pattern]
2. `extract_action_items` [now]
3. `extract_owners` [now — as stated in notes; stewardship ES]
4. `extract_deadlines` [now — explicit only]
5. `extract_unresolved_risks` [now]
6. `link_decisions_to_evidence` [now]
7. `detect_decisions_without_evidence` [now]
8. `detect_unresolved_action_items` [ES]
9. `compare_meeting_claims_vs_knowledge` [now — conflict posture]
10. `prepare_next_meeting_briefing` [assist]
11. `track_decision_history` [now — ledger projection]
12. `generate_followup_email_draft` [assist]
13. `detect_repeated_unresolved_decisions` [now]
14. `detect_missing_action_owner` [now; stewardship ES]
15. `detect_deadline_ambiguity` [now — flagged, never assumed]
16. `convert_accepted_decisions_into_governed_facts` [now — the ruled PRIMARY path: human decisions enter as ordinary documents]
17. `generate_meeting_evidence_pack` [assist]
18. `detect_meeting_decision_vs_policy_contradiction` [now]
19. `prepare_management_decision_queue` [PMD]
20. `identify_claims_requiring_governance_review` [now]

Boundary note: accepted meeting decisions enter as ordinary governed
documents / PRIMARY facts. Pending or unaccepted decision content
does not become agent-readable without the ruled Pipeline Metadata
Door.

---

## 14. Ask Company Expert Workbench — PLATFORM (Layer 1, shipped)

Purpose: universal evidence-backed question-answering over approved
company knowledge. Maps strongly to the existing Ask Expert console
and MCP `ask_expert` tool.

1. `answer_from_approved_knowledge` [now — platform]
2. `cite_evidence_for_every_claim` [now — platform]
3. `refuse_unsupported_answers` [now — platform: INSUFFICIENT EVIDENCE]
4. `warn_on_contradictions` [now — platform]
5. `explain_what_is_known` [now]
6. `explain_what_is_unknown` [now]
7. `explain_what_is_contradictory` [now]
8. `compare_multiple_approved_sources` [now]
9. `produce_short_answer` [assist]
10. `produce_detailed_answer` [assist]
11. `produce_action_recommendation` [assist; via the valve if meant to become knowledge]
12. `identify_needed_escalation` [assist]
13. `identify_missing_evidence` [now]
14. `identify_related_policies_contracts_sops` [now — graph tools]
15. `generate_approved_answer_pack` [now — platform .empkg]
16. `answer_role_specific_questions` [now — clearance-scoped]
17. `answer_customer_specific_questions` [now — from approved facts]
18. `answer_vendor_specific_questions` [now — from approved facts]
19. `answer_auditor_questions` [now — approved evidence only]
20. `produce_confidence_and_limitation_statement` [now]

---

## 15. Risk & Exception Workbench — PLATFORM (Layer 1) + [ES]

Purpose: cross-workbench findings, risks, exceptions, missing
approvals, and human stewardship. Boundary note: **exception
existence must remain computed. Human stewardship decisions may
persist. The strongest rule: the exception never becomes a row; the
human decisions about it do.** — **the rule became LAW (D32) at
v2.0**; the [ES] entries below are delivered as the platform HUMAN
SURFACE (`status: HUMAN_SURFACE`, ratified_path
docs/exception-stewardship-v2.0.md): they are human acts on the
governed queue, never agent skill contracts — promoting them into a
runner would put the stewardship pen in the agent's hand, which D32
exists to refuse.

1. `surface_high_risk_findings` [now — computed inbox/pipeline, platform]
2. `classify_risk_by_impact_urgency` [synth]
3. `identify_missing_approvals` [now — platform; agent visibility PMD]
4. `identify_unresolved_conflicts` [now — platform]
5. `identify_overdue_reviews` [now — platform]
6. `generate_investigation_brief` [assist]
7. `track_unresolved_risks` [now — the computed queue itself; its persistence question is ANSWERED by D32: decisions persist, existence never does]
8. `compare_risk_trend_over_time` [now — ledger history]
9. `route_to_responsible_owner` [ES — HUMAN_SURFACE at v2.0: the OWNER_ASSIGNED decision (owner_label required; owner_principal optional)]
10. `record_human_acknowledgement` [ES — HUMAN_SURFACE at v2.0: the ACKNOWLEDGED decision]
11. `record_risk_acceptance` [ES — HUMAN_SURFACE at v2.0: the RISK_ACCEPTED decision (reason required; severity and gate verdict unchanged — THE SILENT VETO refused)]
12. `record_dismissal_with_reason` [ES — HUMAN_SURFACE at v2.0: the DISMISSED decision (reason required; presentation moves, existence stays computed)]
13. `record_escalation` [ES — HUMAN_SURFACE at v2.0: the ESCALATED decision (reason + escalated_to required)]
14. `produce_exception_queue` [now — computed, platform; at v2.0 the queue is the JOIN: existence from facts, stewardship from decisions]
15. `produce_department_owner_view` [ES — HUMAN_SURFACE at v2.0: the owner filter on the queue, presentation only]
16. `produce_evidence_pack` [assist]
17. `produce_recommended_action` [assist, synth]
18. `produce_approval_status_summary` [now — human surface; agent-side PMD]
19. `produce_audit_trail` [now — platform ledger]
20. `generate_weekly_exception_digest` [assist]

*(v2.0 also delivers `DUE_DATE_SET` (declared date; overdue COMPUTED
at read, never stored) and `CLEARED` (the append-only undo) — decision
kinds without registry-skill ancestors, ruled at scoping. The
deadline-extraction family elsewhere in this registry UNLOCKS after
[ES] but stays sequenced for its own session.)*

---

## 16. Contract Intelligence Workbench — **ACTIVE (v2.1)** (the shared engine)

Purpose: contract extraction, obligation mapping, clause risk,
renewal intelligence, and contract-to-policy comparison across
customer/vendor/partner contracts. Boundary note: potentially the
strongest shared engine — it feeds Procurement (3), Compliance (9),
Customer Success (6), Finance (2), and the Executive briefing (1).
**Ratified at the v2.1 WS0 gate** (docs/contract-intelligence-v2.1.md):
the ACTIVE set is THREE skills — the fifteen extract_* subtasks
consolidate into ONE `extract_contract_clauses` engine with a pinned,
closed fifteen-class `clause_class` taxonomy (the 15→1 consolidation,
ratified); THE REGISTER DISTINCTION rules that verbatim structure
extraction may become governed DERIVED fact through the valve while
narrative synthesis never does.

1. `summarize_contract` [assist — CONSOLIDATED → prepare_contract_review_brief (v2.1)]
2. `extract_parties` [now — CONSOLIDATED → extract_contract_clauses (the `parties` clause_class)]
3. `extract_effective_date` [now — CONSOLIDATED → extract_contract_clauses (`effective_date`)]
4. `extract_expiry_date` [now — CONSOLIDATED → extract_contract_clauses (`expiry_date`)]
5. `extract_renewal_terms` [now — CONSOLIDATED → extract_contract_clauses (`renewal`)]
6. `extract_termination_terms` [now — CONSOLIDATED → extract_contract_clauses (`termination`)]
7. `extract_payment_terms` [now — CONSOLIDATED → extract_contract_clauses (`payment`)]
8. `extract_sla_terms` [now — CONSOLIDATED → extract_contract_clauses (`sla`)]
9. `extract_reporting_obligations` [now — CONSOLIDATED → extract_contract_clauses (`reporting_obligation`)]
10. `extract_certification_obligations` [now — CONSOLIDATED → extract_contract_clauses (`certification_obligation`)]
11. `extract_notification_obligations` [now — CONSOLIDATED → extract_contract_clauses (`notification_obligation`)]
12. `extract_data_access_clauses` [now — CONSOLIDATED → extract_contract_clauses (`data_access`)]
13. `extract_confidentiality_obligations` [now — CONSOLIDATED → extract_contract_clauses (`confidentiality`)]
14. `extract_liability_indemnity_clauses` [now — CONSOLIDATED → extract_contract_clauses (`liability_indemnity`)]
15. `extract_audit_rights` [now — CONSOLIDATED → extract_contract_clauses (`audit_rights`)]
16. `extract_approval_requirements` [now — CONSOLIDATED → extract_contract_clauses (`approval_requirements`)]
17. `detect_missing_contract_metadata` [now — **ACTIVE (v2.1)**: absence declared per contract under the pinned taxonomy, never a fact about the world]
18. `detect_conflicting_contract_clauses` [now — SEQUENCED (v2.1 ruling 3): the platform NLI conflict engine owns cross-asset contradiction; same-contract clause conflict needs its own ruling]
19. `compare_contract_vs_internal_policy` [now — SEQUENCED (v2.1 ruling 3): v1.8 owns the shipped commercial case; a general comparison engine deserves its own evidence rule]
20. `compare_customer_contract_vs_support_sop` [now — SEQUENCED (v2.1 ruling 3)]
21. `compare_vendor_contract_vs_procurement_policy` [now — CONSOLIDATED → the shipped v1.8 `detect_vendor_policy_conflict` (the skill lives where its reader lives)]
22. `detect_auto_renewal_risk` [now — CONSOLIDATED → the shipped v1.8 `detect_renewal_window`]
23. `detect_price_increase_risk` [now — CONSOLIDATED → the shipped v1.8 `detect_price_increase_clauses`]
24. `detect_contract_owner_gaps` [ES — stays per-workbench gated exactly as D32's minting ruled]
25. `prepare_contract_review_brief` [assist — **ACTIVE (v2.1)**: THE REGISTER DISTINCTION — the brief may synthesize for a reader; that synthesis never becomes a fact]
26. `prepare_renewal_decision_brief` [assist — SEQUENCED (v2.1 ruling 3)]
27. `prepare_negotiation_points` [assist, synth — SEQUENCED (v2.1 ruling 3): negotiation synthesis is a posture question of its own]
28. `generate_obligation_candidates_for_compliance` [now — CONSOLIDATED → extract_contract_clauses: the feed IS the engine's accepted output entering packages (v2.1: feeders are milestone behavior, not standalone skills)]
29. `generate_vendor_intelligence_for_procurement` [now — CONSOLIDATED → extract_contract_clauses]
30. `generate_customer_obligation_inputs_for_cs` [now — CONSOLIDATED → extract_contract_clauses]

Cross-workbench feeding stays behind the valve: an extraction skill's
output is a candidate for the consuming workbench's human gate, never
a shared internal fact store. **v2.1 makes this the milestone proof
itself (THE SHARED ENGINE PROOF): one extraction contract, two
UNCHANGED consumers (the v1.7 and v1.8 runners with zero edits), zero
drift by asset id, no shared fact store.**

---

## The generated draft contracts — every skill has its contract file

Every skill listed above has a full 13-field DRAFT contract file under
**`docs/skill-contracts/<NN>_<workbench_id>/<skill_id>.yaml`** — 364
contracts across the 16 workbenches (361 at v1.6; +3 at the v1.7
scoping: the consolidating `extract_compliance_obligations`, the
split-ruling `detect_undocumented_obligation_owner`, and
`detect_conflicting_compliance_statements`), generated deterministically by
**`tools/generate_skill_contracts.py`** (the master inventory lives as
data inside the generator; edit it and rerun — output is stable
byte-for-byte). Each draft composes the base contract with the skill's
pattern (conflict / coverage / revision / extract / missing_evidence /
deadline / compare / finding / assist / platform / stewardship) and
its boundary tags; gated skills ([OE]/[PMD]/[ES]) carry their refusal
condition naming the unminted decision. The ratified ACTIVE contracts
— the five Customer Operations contracts in
`workbench/customer_operations/skills/` (v1.6) and the six Compliance
& Obligation contracts in `workbench/compliance_obligation/skills/`
(v1.7) — remain the binding versions; their drafts carry a
`ratified_path` pointer. CONSOLIDATED drafts (the v1.7 consolidation
ruling) carry `consolidated_into` AND a `ratified_path` to the
consolidating contract — consolidation is never silent promotion.
Promotion path: draft → refined + ratified at the workbench's
scoping session → `workbench/<name>/skills/` → runner + tests.

## Registry rules

1. **A skill enters `workbench/<name>/skills/` only at that
   workbench's ratified scoping session** — this registry is the
   master draft; the YAML is the versioned contract the runner honors
   and the frontmatter claims.
2. **A tag is a gate, not a preference.** [OE]/[PMD]/[ES] skills are
   refused — by the runner, per contract — until their decision is
   minted in the register. Building one without the decision is a
   design failure to escalate, never a quiet stretch.
3. **[assist] outputs never enter knowledge**; anything intended to
   become knowledge is a finding and pays the valve.
4. **Shared patterns are named, reused, and stay identical across
   workbenches**: extract-candidates (obligations / terms /
   commitments / decisions), missing-evidence (absence is a finding,
   never a fact), deadline (explicit dates only, no silent work
   items), doc-vs-doc comparison, coverage-gap (refusal-backed), and
   assist (cited drafts, no valve implications).
5. **No skill modifies a canonical source, structurally** — no skill
   has that door (Guard 5), and no skill contract may claim one.
6. **Cross-workbench composition happens across the valve**: a skill
   consumes another workbench's ACCEPTED DERIVED facts, never its
   pending proposals; second-generation synthesis stays visible
   through D30 citation depth.
## The scoped roadmap layer (added at the v1.8 selection scoping, 2026-07-07)

Normalization over the 16-workbench inventory above: proof names, commercial-verdict
readers, and sequence markers. Statuses: [now] buildable in its document slice ·
[next] named prerequisite first · [gated] requires minting [OE]/[ES]/[PMD] ·
[deferred] deliberate · [shipped].

| # | Workbench (enterprise-facing name) | Status | Distinctive proof | Verdict reader | Milestone |
|---|---|---|---|---|---|
| 3 | Procurement Document Intelligence | [now] | THE CLAUSE ARITHMETIC PROOF — every number/percentage verbatim + cited; only computed values are date windows over verbatim dates at the declared as_of | procurement/finance owner | v1.8 (SELECTED) |
| 1 | Executive Operations Briefing | [now] (decision queue [gated: PMD]) | THE BRIEFING PROOF — every sentence cited or SYNTHESIS_INFERRED-declared; byte-identical per ledger cursor; zero door growth | CEO | v1.9 (recommended) |
| 15 | Risk & Exception Stewardship | [gated: ES] (queue [shipped]) | THE STEWARDSHIP PROOF — queue recomputes identically from the ledger; decisions persist as events; no exception row exists | governance officer | v2.0 (the [ES] minting milestone) |
| 16 | Contract Intelligence | [now] (**v2.1 SELECTED** — scoped at docs/contract-intelligence-v2.1.md) | THE SHARED ENGINE PROOF — one extraction contract, two UNCHANGED consumers, zero drift by asset id, no shared fact store | general counsel / procurement | v2.1 (in flight) |
| 4 | Sales & Commitments Intelligence | [next: the diagnostic-subject ruling] | THE UNBACKED PROMISE PROOF — the unbacked promise found; the backed one silent; proposal claims never become knowledge | sales director | v2.1 candidate |
| 6 | Customer Success / Retention | [next] | THE CUSTOM TERMS PROOF — per-customer deviation from standard terms found; conforming customer silent | CS lead | pull-driven |
| 11 | Project / Delivery Intelligence | [next] | THE SCOPE DRIFT PROOF — contract obligation absent from the plan found from documents alone | delivery lead | pull-driven |
| 12 | Internal IT & SaaS Governance | [next] | THE UNAPPROVED TOOL PROOF — policy-vs-approved-tools deviation found; renewal window on the declared clock | IT manager | pull-driven |
| 8 | Operations & SOP Intelligence | [next: procedural corpus + evidence rules] | THE HANDOFF PROOF — the missing cross-SOP handoff found; the covered handoff silent | operations lead | pull-driven |
| 2 | Finance & Cost Leakage | [now: doc slice; full scope gated: OE] | THE LEAKAGE LEDGER PROOF — every leak clause-cited, never transaction-inferred | CFO | fold into #3/#16 |
| 7 | HR / People Operations | [deferred: positioning-sensitive] | THE POLICY-ONLY PROOF — structurally incapable of person-level findings | HR director | on demand, Fable-only |
| 13 | Meeting & Decision Intelligence | [deferred surface] | THE DECISION EVIDENCE PROOF — the unevidenced, unowned decision surfaces; PRIMARY authorship path unchanged | chief of staff | after [PMD] / pull |
| 5 | Customer Operations | [shipped v1.6.0] | THE DIAGNOSIS PROOF + Commercial Verdict | customer-ops manager | done |
| 9 | Compliance & Obligation | [shipped v1.7.0] | THE COMPOSITION PROOF + Commercial Verdict | audit-facing reader | done |
| 10 | Document / Knowledge Quality | [shipped platform] | the six standing guard families | — | platform |
| 14 | Ask Company Expert | [shipped platform] | "no evidence = no answer" (constitutional) | — | platform |

Standing roadmap rules ratified with this layer: every milestone keeps the WS0→WS3
gate pattern with a named distinctive proof and a user commercial verdict; [OE]/[ES]/
[PMD] are minted only at their own scoping sessions ([ES] targeted at v2.0); the
sensitivity posture is named per workbench at WS0 (v1.8's cardinal sin: the invented
number); model routing — Fable for scoping/gates/proof design, Opus for post-
ratification implementation, Sonnet for mechanical closeout.
