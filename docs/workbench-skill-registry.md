# The Workbench Skill Registry

> Companion to **docs/workbench-catalog.md** (ratified 2026-07-03).
> This registry combines the full catalog into one artifact: every
> workbench, every subtask, each as a named **agent skill contract**
> in the ten-field pattern. A workbench is never a screen or a broad
> agent — it is a catalog of governed subtasks, and each subtask has
> its own skill contract.
>
> **Status of this document:** the registry is the catalog-level
> DRAFT of every contract. The binding, versioned `skills/*.yaml`
> contracts are ratified at each workbench's own scoping session and
> live in `workbench/<name>/skills/`. Only the Customer Operations
> v1.6 skills are ACTIVE (being built). Statuses: **ACTIVE** (v1.6) ·
> **SEQUENCED** (Compliance second, Procurement third) · **PLATFORM**
> (Layer 1, already shipped as EM itself) · **FUTURE** (Layer 3 or
> gated on a named decision).
>
> Boundary tags (from the catalog): **[now]** buildable on the four
> doors today · **[OE]** Operational Evidence Realm · **[PMD]**
> Pipeline Metadata Door · **[ES]** Exception Stewardship ·
> **[assist]** consumption output, not a finding · **[synth]**
> declared SYNTHESIS_INFERRED content.

## The ten-field skill contract shape

> skill name · purpose · allowed inputs · forbidden inputs · governed
> evidence rules · allowed finding kinds · output format · human
> approval requirement · audit expectations · failure & refusal
> conditions

## The base contract (inherited by EVERY skill; skills below declare only their specifics)

- **Forbidden inputs (always):** ungoverned sources; unapproved /
  candidate / held content (until [PMD] is minted, and then metadata
  only); transactional records (until [OE] is minted); other skills'
  raw, ungated findings (skills compose ACROSS the valve — a skill may
  consume another skill's ACCEPTED DERIVED facts, never its pending
  proposals); rendered vault notes as authority (readable as a lens;
  never citable as truth — D31).
- **Governed evidence rules (always):** evidence = governed asset
  ids/hashes, conflict relationship ids, revision chains, or
  reproducible refusals, obtained through the doors (.empkg at binding
  clearance, the 9 MCP tools at token clearance). **No evidence, no
  finding.** Clearance exclusions declared inside the output. DERIVED
  evidence cited as DERIVED (derivation depth stays computable, D30).
- **Output format (always, for finding skills):** one proposal
  document per finding to `/08_proposals`, frontmatter carrying the
  D30 claims (agent principal, binding id, package hash, cited assets)
  plus the catalog claims (workbench, skill, skill_version,
  finding_kind, evidence_basis); body = business statement, evidence,
  proposed action, impact estimate [synth-declared] if any.
- **Human approval requirement (always):** the valve (D29). Every
  finding is a held CANDIDATE; a human accepts it into a DERIVED fact
  or does not; no policy tier ever applies. [assist] outputs are the
  exception by species: drafts and briefings never enter knowledge at
  all.
- **Audit expectations (always):** MCP calls audited per call; the
  scan, hold, and gate events are the finding's ledger trail; the
  approval event quotes verified provenance verbatim.
- **Failure & refusal conditions (always):** cannot cite governed
  evidence → refuse to emit; uncertain extraction or ambiguous rule →
  emit marked `NEEDS_REVIEW`, never guess; input requires a tag whose
  decision is not minted ([OE]/[PMD]/[ES]) → refuse the task, name the
  gate.

**The worked example shape** (from the compliance decomposition —
every finding reads like this):

```
Obligation candidate:
Customer contract requires quarterly SLA reporting.
Source: Customer_Master_Agreement.pdf, section 6.2 (asset #214)
Owner suggested: Customer Success
Deadline rule: quarterly
Status: needs human review
```

---

## 1. Customer Operations Workbench — ACTIVE (v1.6.0)

Build contract: docs/customer-ops-workbench-v1.6.md.

#### `detect_contradictory_guidance` [now] — ACTIVE
- Purpose: two approved customer-ops assets give different answers
  (refund window 14 vs 30 days).
- Allowed inputs: domain subgraph + `get_conflicts`
  (DIRECT_CONTRADICTION pairs) at binding clearance.
- Evidence rules: the governed CONFLICTS_WITH relationship + both
  asset ids; evidence_basis CONFLICT_BACKED.
- Finding kinds: CONTRADICTORY_GUIDANCE.
- Refuses when: no governed conflict relationship exists (a suspected
  contradiction without one belongs to `detect_process_inconsistency`).

#### `detect_outdated_guidance` [now] — ACTIVE
- Purpose: approved guidance still tracks a superseded revision of a
  policy.
- Allowed inputs: conflicts classified TEMPORAL_SUPERSESSION +
  `get_revision_history` chains.
- Evidence rules: the classification + the revision chain;
  evidence_basis REVISION_BACKED.
- Finding kinds: OUTDATED_GUIDANCE.
- Refuses when: recency cannot be established from governed revision
  or supersession evidence — never from document age alone.

#### `detect_coverage_gap` [now] — ACTIVE
- Purpose: a question the customer-ops function must answer that the
  governed corpus cannot.
- Allowed inputs: the skill's declared question frame, run through
  package `consume()` under the packaged answering contract.
- Evidence rules: the question + the reproducible INSUFFICIENT
  EVIDENCE refusal + nearest partial evidence ids; evidence_basis
  REFUSAL_BACKED.
- Finding kinds: COVERAGE_GAP.
- Refuses when: the corpus answers the question (a live-proven refusal
  condition at the WS2 gate) or the question is outside the declared
  frame.

#### `detect_process_inconsistency` [now, synth] — ACTIVE
- Purpose: escalation/procedure steps that do not align across assets
  without an NLI-visible contradiction.
- Allowed inputs: procedure/escalation assets in scope; the synthesis
  seam (D19).
- Evidence rules: cited asset ids + quoted passages; evidence_basis
  SYNTHESIS_INFERRED, declared as model-inferred.
- Finding kinds: PROCESS_INCONSISTENCY.
- Refuses when: the inference cannot quote the passages it rests on.
  (The one v1.6 skill genuinely requiring a model; CI exercises its
  plumbing; its real proof is the real-model slot.)

#### `answer_support_questions` / `suggest_reply` [assist] — PLATFORM POSTURE
- Purpose: evidence-backed answer or reply draft from approved
  customer-ops knowledge (the Ask Expert posture, domain-scoped).
- Output: an answer/draft with citations and refusals — never a
  finding, never enters knowledge.

#### Customer Ops v2 — FUTURE, behind [OE]
`detect_repeated_complaints` · `identify_product_issues_from_tickets`
· `detect_sla_breaches` · `escalate_high_risk_customers` [also ES] ·
`summarize_open_cases` [assist] · `propose_retention_actions` [synth]
· `customer_risk_score` [synth]. All consume ticket streams —
operational evidence, not knowledge assets. "Review this week's
tickets" stays a refused demo question until [OE] is minted.

---

## 2. Compliance / Obligation Tracking Workbench — SEQUENCED (second)

The most defensible EM-native workbench; scoped fully at its own
session. Contracts drafted:

#### `extract_obligations` [now]
- Purpose: identify obligations from approved contracts, policies,
  certifications, SOPs, regulatory documents.
- Allowed inputs: approved governed sources in the compliance scope.
- Evidence rules: explicit obligations only — **never invent an
  obligation**; source asset + excerpt + section reference attached.
- Finding kinds: OBLIGATION_CANDIDATE, type-classified: reporting,
  renewal, certification, notification, SLA, audit, approval,
  training, retention, security, payment, delivery.
- Output: an obligation candidate (the worked example above) —
  canonical only after acceptance.
- Refuses when: the obligation is implied rather than explicit →
  NEEDS_REVIEW.

#### `track_deadlines` [now]
- Purpose: identify time-bound obligations and compute upcoming
  deadlines.
- Allowed inputs: accepted obligation facts + governed sources with
  explicit dates or date rules.
- Evidence rules: explicit dates/rules only; fixed dates distinguished
  from inferred recurrence; confidence declared with its reason
  ("recurrence explicit but owner missing").
- Finding kinds: DEADLINE_FINDING.
- Refuses when: recurrence is ambiguous → flagged, never assumed; and
  it **never silently creates calendar or work items** (ownership and
  due-date assignment are [ES]).

#### `detect_missing_evidence` [now]
- Purpose: obligations that require proof but have no approved
  evidence attached.
- Allowed inputs: accepted obligation facts vs approved evidence
  assets.
- Evidence rules: evidence must be governed and approved; **absence
  becomes a finding, never a fact**; the obligation source and the
  missing-evidence reason attached.
- Finding kinds: MISSING_EVIDENCE.

#### `identify_outdated_policies` [now]
- Purpose: stale policies, SOPs, certifications, compliance documents.
- Allowed inputs: approved review dates, expiry dates, supersession
  markers, conflicting newer documents.
- Evidence rules: **never infer "outdated" from age alone** unless the
  policy defines a review interval.
- Finding kinds: OUTDATED_POLICY, classified expired /
  overdue-for-review / superseded / potentially-stale.

#### `compare_policy_vs_practice` [now — document-side only]
- Purpose: contradiction, missing procedure, or unsupported promise
  between governed documents: policy vs SOP, contract obligation vs
  internal procedure, customer promise vs approved playbook.
- Forbidden inputs (v1): tickets, logs, payments, operational records
  — practice-as-records is [OE].
- Finding kinds: CONTRADICTORY_GUIDANCE / MISSING_PROCEDURE /
  UNSUPPORTED_PROMISE.

#### `prepare_audit_pack` [now, assist-shaped projection]
- Purpose: compile evidence for an auditor or internal reviewer.
- Evidence rules: approved evidence only; grouped by obligation,
  evidence, owner, deadline, gap; **known, missing, contradictory, and
  unverified material clearly separated**; no unsupported narrative;
  every claim cited.
- Output sections: obligations identified · evidence available ·
  evidence gaps · outdated documents · contradictions · human
  decisions required · audit trail references. A projection, never
  canonical.

#### `detect_unapproved_changes` [PMD] — FUTURE
- Purpose: documents or claims used operationally but not approved
  (candidate FAQ referencing a rule absent from the approved policy).
- Gate: requires agent visibility into candidate/held status — ruled
  at this workbench's session via the Pipeline Metadata Door, never
  absorbed silently. Governance status is the source of truth;
  unapproved content is a governance-risk finding, never knowledge.

#### `generate_evidence_binder` [now, assist-shaped projection]
- Purpose: structured export of approved evidence per obligation
  domain.
- Evidence rules: the binder is a projection, not canonical knowledge;
  every section links back to governed facts/assets; missing items
  remain visibly missing; **no generated legal conclusion** unless
  backed by accepted facts.

#### `answer_auditor_questions` [now, assist]
- Purpose: answer direct auditor questions safely.
- Evidence rules: approved evidence only; refuse unsupported answers;
  warn on contradiction; escalate on missing evidence ("No approved
  evidence found for current ISO renewal. The latest approved
  certificate expired 2025-12-31.").

---

## 3. Procurement & Vendor Intelligence Workbench — SEQUENCED (third, document slice)

#### `extract_vendor_terms` [now]
- Purpose: pricing clauses, payment terms, SLA obligations, renewal
  and termination clauses from approved vendor contracts.
- Finding kinds: VENDOR_TERM_CANDIDATE (the extract_obligations
  pattern, vendor-scoped).

#### `summarize_vendor_contracts` [now, assist]
- Purpose: contract summaries for humans; citations mandatory; never a
  finding.

#### `compare_vendor_offers` [now]
- Purpose: doc-vs-doc comparison of governed offer documents;
  differences cited clause by clause.
- Finding kinds: OFFER_COMPARISON.

#### `detect_expiring_contracts` [now]
- Purpose: contracts expiring inside a declared window (e.g. 90 days).
- Evidence rules: explicit contract dates only (the track_deadlines
  pattern).
- Finding kinds: EXPIRY_RISK.

#### `flag_auto_renewals` [now]
- Purpose: auto-renewal clauses with their notice windows.
- Finding kinds: AUTO_RENEWAL_RISK.

#### `identify_price_increase_clauses` [now]
- Purpose: clause-level price escalation across contract revisions
  ("price clause increased 22% vs prior approved contract").
- Forbidden (v1): actual prices PAID — invoices are [OE].
- Finding kinds: PRICE_INCREASE_CLAUSE.

#### `detect_missing_certifications` [now]
- Purpose: required supplier certifications with no approved evidence
  document (the detect_missing_evidence pattern, vendor-scoped).
- Finding kinds: MISSING_CERTIFICATION.

#### `detect_single_supplier_dependency` [now]
- Purpose: categories where governed contracts show one supplier.
- Finding kinds: SUPPLIER_DEPENDENCY_RISK.

#### `prepare_renegotiation_brief` [now, assist + synth]
- Purpose: negotiation package per vendor — contract evidence,
  expiring terms, price clauses, certification gaps, recommended
  negotiation points [synth-declared].

#### `propose_vendor_consolidation` [synth]
- Purpose: consolidation opportunities across governed contracts;
  every claim cites the contracts it rests on; impact [synth].
- Finding kinds: CONSOLIDATION_OPPORTUNITY.

#### `compare_sla_obligations_vs_service_records` [OE] — FUTURE
Service records are operational evidence.

Refused in v1 (all [OE]): invoice mining, PO/payment reconciliation,
duplicate invoice detection, ledger anomalies.

---

## 4. Executive Operations Briefing (Management / CEO) — two-stage by ruling

**Stage v1 [now] — accepted facts + governance health, zero door
growth:**

#### `summarize_company_status` [now]
- Allowed inputs: approved knowledge incl. accepted DERIVED findings
  (class always visible, D30), trust scores, gate status.
- Output: evidence-backed status interpretation [assist-shaped brief +
  optional findings].

#### `detect_operational_risks` [now]
- Allowed inputs: unresolved conflicts, blocked compile gates, trust
  components, accepted risk findings from feeder workbenches.
- Finding kinds: OPERATIONAL_RISK.

#### `whats_changed_since` [now]
- Allowed inputs: revision histories, render/ledger history, newly
  accepted DERIVED facts since a declared moment.
- Output: the change brief, every item citing its governed event.

#### `detect_unsupported_claims` [now]
- Purpose: claims in governed documents lacking evidence backing
  (the evidence-gap posture at executive scope).
- Finding kinds: UNSUPPORTED_CLAIM.

#### `generate_executive_brief` / `prepare_board_report` [assist]
- Weekly CEO briefing / board pack composed from the above — trusted
  operational interpretation, not another dashboard; citations
  mandatory; never enters knowledge.

**Stage v2 — FUTURE, behind [PMD] (+[ES]/[OE] where tagged):**

`list_decisions_needing_approval` [PMD — held proposals, aging,
verdict summaries; metadata only, candidate content stays human-only]
· `identify_department_blockers` [PMD] · `risk_register_with_owners`
[ES] · `compare_periods` over operational metrics [OE].

---

## 5. Finance & Cost Leakage Workbench — document-bound until [OE]

**v1 document slice — Finance Policy & Contract Leakage [now]:**

#### `detect_payment_term_policy_mismatch` [now]
- Purpose: contract payment terms contradicting approved payment
  policies ("contract says 60 days; approved policy says 30") —
  doc-vs-doc, both governed.
- Finding kinds: PAYMENT_TERM_MISMATCH.

#### `detect_renewal_clause_leakage` [now]
- Purpose: renewal/escalation clauses that create spend without
  approval checkpoints, vs approved budget/approval policies.
- Finding kinds: RENEWAL_LEAKAGE_RISK.

#### `detect_budget_policy_gaps` [now]
- Purpose: spend categories governed contracts create that no approved
  budget policy covers.
- Finding kinds: BUDGET_POLICY_GAP.

#### `detect_missing_approval_evidence` [now]
- Purpose: contracts/commitments requiring approval evidence that has
  no approved counterpart (the missing-evidence pattern).
- Finding kinds: MISSING_APPROVAL_EVIDENCE.

**v2 — FUTURE, all [OE]** (the agent never changes canonical
accounting data; it creates findings): `detect_duplicate_invoices` ·
`detect_unusual_cost_increases` · `compare_contracts_vs_invoices`
("contract says 60 days, invoice applied 30") ·
`flag_overdue_receivables` · `identify_budget_overruns` ·
`detect_po_invoice_contract_mismatch` ·
`identify_unused_subscriptions` · `detect_payment_term_violations` ·
`monthly_finance_exception_report` · `prepare_cost_reduction_scenarios`
[synth].

---

## 6. Sales & Account Growth Workbench — FUTURE (Layer 3)

The governed intelligence layer above CRM, never a CRM replacement.

**Doc-side [now]:** `detect_proposal_vs_documentation_mismatch` (a
sales proposal promising something absent from approved product
documentation — doc-vs-doc; finding kind UNSUPPORTED_PROMISE) ·
`compare_customer_needs_vs_offering` (governed needs docs vs governed
product docs) · `prepare_meeting_pack` [assist — contract obligations,
approved history, risks, talking points, all cited] ·
`prepare_followup_email` / `draft_proposal_checklist` [assist].

**Behind [OE]:** `summarize_crm_history` · `detect_stalled_opportunities`
· `identify_upsell_candidates` [synth] · `identify_declining_activity`
· `next_best_action` [synth].

---

## 7. HR / People Operations Workbench — FUTURE (Layer 3, positioning-sensitive)

Positioned as "the system identifies role overlap, bottlenecks,
missing skills, and scenario options — human leadership decides."
Never "AI fires people."

**Doc-side [now]:** `detect_policy_contradictions` (HR policy vs
handbook vs onboarding docs) · `generate_hr_faq` [now — synthesis via
the valve: FAQ → proposal → human gate → DERIVED] ·
`detect_expired_certifications` (the missing/expired-evidence pattern)
· `detect_key_person_dependency` [synth — from governed role/process
docs] · `prepare_onboarding_package` / `prepare_role_handover` /
`prepare_hiring_manager_briefing` [assist].

**Behind [OE]:** `detect_missing_training` (training records) ·
`compare_job_descriptions_vs_responsibilities` (actual-responsibility
evidence) · `suggest_workforce_scenarios` [synth, human leadership
decides — approval queue mandatory].

---

## 8. Operations / Process Improvement Workbench — FUTURE (Layer 3, document-first)

**Doc-side [now]:** `detect_sop_conflicts` (SOP vs SOP, SOP vs
training material) · `detect_missing_handoffs` (a process step whose
upstream/downstream is documented nowhere) ·
`find_process_variants_across_teams` (two teams' documents describing
the same process differently) · `identify_undocumented_processes` (a
step appearing in narrative documents but in no approved procedure) ·
`generate_improvement_backlog` [synth, via the valve] ·
`propose_automation_candidates` [synth].

**Behind [OE]:** `map_processes_from_logs` · `detect_bottlenecks` ·
`detect_stage_delays` · `compare_sop_vs_actual_execution` ·
`identify_repeated_manual_steps` — process mining over traces;
estimated impact stays [synth] even then.

---

## 9. Document / Knowledge Quality Workbench — PLATFORM (Layer 1)

Substantially the governance engine itself; not sold as a separate
workbench. The subtask→capability mapping:

`detect_outdated_documents` → revision freshness + supersession
(shipped) · `detect_cross_document_contradictions` → the conflict
engine + domain scoping (shipped; "find all conflicting refund
instructions across policies, sales materials, macros" is a scoped
conflict scan) · `identify_duplicate_knowledge` → content-hash dedup
(shipped) · `find_documents_without_approval` → the review queue
(shipped, human surface; agent visibility is [PMD]) ·
`compile_department_packages` / `create_answer_packs` → the .empkg
compiler (shipped) · `recommend_review_candidates` → the computed
inbox (shipped; owner recommendation is [ES]) · `find_missing_owners`
[ES] · `identify_undocumented_processes` → see workbench 7.

Two thin agent skills may be earned later over the primitive:
`propose_resolution_draft` [now — a proposal through the valve, never
a resolution] and `recommend_review_owner` [ES].

---

## 10. Project / Delivery Workbench — FUTURE (Layer 3)

**Doc-side [now]:** `compare_contract_scope_vs_project_docs` (scope
creep as doc-vs-doc; finding kind SCOPE_CREEP / UNCONTRACTED_SCOPE) ·
`extract_open_commitments` (from ingested meeting notes and status
documents — the extract_obligations pattern, project-scoped) ·
`compare_plan_vs_meeting_notes` · `detect_missing_deliverables`
(contracted deliverable with no approved evidence — the
missing-evidence pattern) · `prepare_client_update` /
`prepare_handover_package` [assist] · `generate_lessons_learned` [now,
via the valve].

**Behind [OE]:** `detect_blocked_tasks` · `identify_deadline_risk`
[synth] — live task/deadline states from project systems. Commitment
ownership/deadlines are [ES].

---

## 11. Internal IT / Software / Systems Workbench — FUTURE (Layer 3)

Starts knowledge-governed; never autonomous infrastructure control
(the D22 posture).

**Doc-side [now]:** `compare_security_policy_vs_approved_tools`
(policy vs the governed approved-tool register, doc-vs-doc) ·
`detect_contract_renewal_risk` (the procurement pattern, IT-scoped) ·
`identify_unsupported_systems` (systems named in governed docs whose
support/lifecycle documents say end-of-life) · `prepare_it_asset_register`
[assist-shaped projection over governed documents] ·
`generate_helpdesk_answers` [assist] · `prepare_migration_plan`
[assist + synth].

**Behind [OE]:** `optimize_licenses` · `detect_unused_accounts` ·
`review_access` · `detect_shadow_it` · SaaS spend/usage analysis.

---

## 12. Meeting Intelligence / Decision Follow-up Workbench — PLATFORM-ADJACENT (Layer 1, deferred surface)

The authorship path is already ruled: meeting notes enter as ordinary
documents; human decisions become PRIMARY facts.

**Doc-side [now]:** `extract_decisions_from_notes` (explicit decisions
with owners/deadlines where stated — the extract_obligations pattern;
uncertain = NEEDS_REVIEW) · `detect_unevidenced_decisions` (a decision
with no cited evidence and no assigned owner — finding kind
UNEVIDENCED_DECISION) · `compare_meeting_claims_vs_knowledge` (claims
in notes contradicting approved knowledge — the conflict posture) ·
`link_decisions_to_evidence` · `track_decision_history` (ledger
projection) · `prepare_meeting_briefing` / `generate_followup_emails`
[assist].

**Behind [ES]:** `detect_unresolved_actions` / `action_tracker` —
owners and due dates are stewardship decisions.

---

## 13. Ask Company Expert — PLATFORM (Layer 1, shipped)

The universal daily layer: `answer_from_approved_knowledge` ·
`cite_evidence` · `refuse_unsupported_answers` (INSUFFICIENT EVIDENCE
is first-class) · `compare_sources` · `explain_known_unknown_contradictory`
· `prepare_action_recommendation` [assist; a recommendation intended
to become knowledge goes through the valve like any finding]. Shipped
as the Ask Expert console + `ask_expert` MCP tool with conflict
warnings, confidence, and clearance. The bigger client value comes
connected to workbenches, not sold alone.

---

## 14. Risk & Exception Workbench — PLATFORM (Layer 1) + [ES]

The cross-department queue, shipped as computation: `surface_exceptions`
→ the Governance Inbox + Operations Proposal Pipeline (computed from
governed facts, never persisted — D1/D24) · `identify_missing_approvals`
→ the inbox exception kinds (agent visibility is [PMD]) ·
`compare_risk_trends` [now — ledger history] ·
`generate_investigation_brief` [assist] · `classify_risk_by_impact`
[synth].

**Behind [ES]:** `route_to_responsible_owner` · `track_unresolved_risks`
· approval-status workflow. The ruled shape: **the exception never
becomes a row; the human decisions about it do** — existence computed,
stewardship decisions persisted as identity-backed events, the queue
is the join.

---

## Registry rules

1. **A skill enters `workbench/<name>/skills/` only at that
   workbench's ratified scoping session** — this registry is the
   draft; the YAML is the versioned contract the runner honors and
   the frontmatter claims.
2. **A tag is a gate, not a preference.** [OE]/[PMD]/[ES] skills are
   refused — by the runner, per contract — until their decision is
   minted in the register. Building one without the decision is a
   design failure to escalate, never a quiet stretch.
3. **[assist] outputs never enter knowledge**; anything intended to
   become knowledge is a finding and pays the valve.
4. **Shared patterns are named, reused, and stay identical across
   workbenches**: the extract-candidates pattern
   (obligations/terms/commitments/decisions), the missing-evidence
   pattern (absence is a finding, never a fact), the deadline pattern
   (explicit dates only, no silent work items), the doc-vs-doc
   comparison pattern, and the assist pattern (cited drafts, no valve
   implications).
5. **No skill modifies a canonical source, structurally** — no skill
   has that door (Guard 5), and no skill contract may claim one.
