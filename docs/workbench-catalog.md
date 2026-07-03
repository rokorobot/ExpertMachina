# The ExpertMachina Workbench Catalog

> Ratified 2026-07-03 (the v1.6 scoping session). This is a **product
> roadmap artifact, not register law**: it records the full catalog
> (14 workbenches), the layer structure, the commercial sequence, the
> per-skill boundary audit, and the named-but-not-minted future
> decisions, so every later scoping session inherits the map whole.
> Constitutional rulings stay in docs/DECISIONS.md; nothing here
> overrides them.

## Positioning

**Operational workbenches powered by governed company knowledge.**

> ExpertMachina compiles a company's existing knowledge into governed,
> agent-ready packages, then powers operational workbenches that
> detect risks, obligations, contradictions, leakage, and decision
> needs — with evidence attached and humans at the gate.

Not a chatbot. Not raw RAG. Not document storage. Not a generic agent
platform. Not autonomous replacement of employees. The value is not
"AI answers questions" — it is that AI **continuously turns scattered
company knowledge into operational findings**, and every finding
enters company knowledge only through the valve (D29), as a DERIVED
fact (D30), past a human. ExpertMachina is the governed operational
intelligence layer between company knowledge and company action.

The findings clients immediately understand:

> "This vendor contract renews in 18 days and its price clause
> increased 22%." · "This customer has an SLA exception not reflected
> in the support playbook." · "This SOP contradicts the onboarding
> checklist." · "This sales proposal promises something not present in
> the approved product documentation." · "This meeting decision has no
> evidence and no assigned owner." · "This department has three
> versions of the same policy."

The core idea: for a mid-sized company the best workbenches are not
exotic — they target the boring, painful, repeated operational
problems. Where is money leaking? Which customers need attention?
Which documents contradict each other? Which obligations are not
fulfilled? Which decision can be prepared but not executed
automatically?

The operating posture, in the register's language:

> Agents discover, compare, draft, recommend, prioritize, and escalate.
> Humans approve, reject, modify, and execute.
> Canonical facts change only through governed versioning.

## Boundary tags used below

Every candidate skill carries one of these tags — the audit that keeps
the catalog honest against the register:

- **[now]** — buildable today on the four doors (packages, MCP, vault
  lens, proposal lane) over governed documents. D27-clean.
- **[OE]** — requires the **Operational Evidence Realm** (transactional
  records: tickets, invoices, POs, payments, CRM activity, logs, usage
  data). Refused until that decision is minted.
- **[PMD]** — requires the **Pipeline Metadata Door** (agent-readable
  metadata about ungated material: held proposals, verdicts, aging).
- **[ES]** — requires **Exception Stewardship** (owners, due dates,
  acknowledgments — human decisions persisted, existence computed).
- **[assist]** — a consumption output (draft reply, briefing, email),
  not a finding: never enters knowledge, no valve implications, a
  different product motion (assistance, not diagnosis).
- **[synth]** — legitimate synthesis content inside a finding
  (impact estimates, consolidation proposals), always declared
  SYNTHESIS_INFERRED, never a governed number.

## Layer 1 — Platform primitives (already shipped; positioning, not construction)

These exist inside every deployment because they ARE the platform.
They are not sold as separate workbenches — re-badging them would blur
the two realms (EM governing itself vs. agents diagnosing the
business):

**13. Ask Company Expert** — the universal daily layer, shipped: the
Ask Expert console + `ask_expert` MCP tool (v0.3/v0.9). Answers from
approved knowledge only, cites evidence, refuses unsupported answers
(INSUFFICIENT EVIDENCE), warns on contradiction, explains
known/unknown/contradictory. The bigger client value comes when it is
connected to workbenches, not sold alone.

**9. Document / Knowledge Quality** — substantially the governance
engine itself: conflict detection + classification, revision workflow,
trust scores, duplicate/dedup machinery, the Governance Inbox, .empkg
"answer packs" (v0.6–v0.9.4). "Find all conflicting instructions about
customer refunds across policies, sales materials, and macros" is the
conflict engine + domain scoping, shipped. Two thin agent skills may
be earned later over the primitive: `propose_resolution_draft` [now,
via the valve — a proposal, never a resolution] and
`recommend_review_owner` [ES]. Before agents act, the knowledge must
be clean enough to trust — this stays EM's strongest
internal-to-client feature.

**14. Risk & Exception queue** — the cross-department exception
surface, shipped as computation: the Governance Inbox + the Operations
Proposal Pipeline (v0.9.1/v1.4.1), exceptions computed from governed
facts, never persisted (D1/D24). What it deliberately does NOT have
yet: routing to owners, unresolved-risk tracking, impact/urgency
classification with assignees — that is **Exception Stewardship**
[ES], the named future decision. The ruled shape: *the exception never
becomes a row; the human decisions about it do.*

**12. Meeting Intelligence / Decision Follow-up** — the authorship
path is already ruled: meeting notes enter as ordinary documents;
human decisions become PRIMARY facts; "decisions made without
evidence" is the evidence-gap posture; "compare meeting claims against
approved knowledge" is conflict detection over ingested notes [now].
Action tracking with owners/deadlines is [ES]. Deferred as a product
surface — an input stream into the decision queue rather than a first
standalone product.

## Layer 2 — The commercial set (the ratified build sequence)

Build sequence, ratified: **Customer Operations (v1.6.0) → Compliance
& Obligation → Procurement Document Intelligence**, superseding the
v1.5-closeout ordering, by user ruling. Executive Briefing is
two-stage; Finance is document-bound until [OE].

### 1. Customer Operations Workbench — FIRST (v1.6.0)

Build contract: docs/customer-ops-workbench-v1.6.md. The easiest area
to demonstrate value quickly. Diagnoses the governed customer-ops
knowledge layer: support policies, refund rules, SLAs, escalation
procedures, macros, training docs, customer-facing guidance.

Skills, v1.6 (built): `detect_contradictory_guidance` [now] ·
`detect_outdated_guidance` [now] · `detect_coverage_gap` [now] ·
`detect_process_inconsistency` [now, synth].

Assistance (platform posture, not v1.6 findings):
`answer_support_questions` / `suggest_reply` [assist — the Ask Expert
posture over the customer-ops domain].

Customer Ops v2, behind [OE]: `detect_repeated_complaints` ·
`identify_product_issues_from_tickets` · `detect_sla_breaches` ·
`escalate_high_risk_customers` · `summarize_open_cases` ·
`propose_retention_actions` · `customer_risk_score`. "Review this
week's tickets and cluster complaints" is a refused demo question in
v1.6, deliberately.

Outputs: the diagnosis (per-finding proposals), documentation gaps,
policy-contradiction findings; v2 adds SLA risk, issue clusters,
customer-risk scores.

### 2. Compliance / Obligation Tracking Workbench — SECOND

The most defensible EM-native workbench: it inherits governance,
provenance, evidence, decisions, and audit — generic AI tools are weak
here unless the source knowledge is governed. The "no evidence = no
answer" founding story, productized. Scoped fully at its own session;
skills decomposed and boundary-tagged now:

- `extract_obligations` [now] — obligation candidates from approved
  contracts/policies/regulations/certifications; explicit obligations
  only, never invented; type-classified (reporting, renewal,
  certification, notification, SLA, audit, approval, training,
  retention, security, payment, delivery); uncertain = NEEDS_REVIEW;
  a candidate, canonical only after acceptance.
- `track_deadlines` [now] — explicit dates and date rules from
  governed sources only; fixed dates distinguished from inferred
  recurrence; ambiguity flagged; **no silent calendar or work items**
  (deadline ownership is [ES]).
- `detect_missing_evidence` [now] — accepted obligations vs approved
  evidence assets; **absence becomes a finding, never a fact**.
- `identify_outdated_policies` [now] — review intervals, expiry,
  supersession markers, newer conflicting documents; never age alone;
  classified expired / overdue-for-review / superseded / potentially
  stale.
- `compare_policy_vs_practice` [now, document-side only] — policy vs
  SOP, contract obligation vs internal procedure, customer promise vs
  approved playbook. Practice-as-operational-records is [OE].
- `prepare_audit_pack` / `generate_evidence_binder` [now] —
  projections: approved evidence only; grouped by obligation /
  evidence / owner / deadline / gap; known, missing, contradictory,
  and unverified material clearly separated; missing items visibly
  missing; no unsupported narrative; every claim cited.
- `detect_unapproved_changes` [PMD] — comparing approved vs
  candidate/held content requires agent visibility into ungated
  material; ruled at this workbench's session, never absorbed
  silently.
- `answer_auditor_questions` [now/assist] — the Ask Expert posture:
  approved evidence only, refusals first-class, contradictions warned,
  escalation on missing evidence.

Outputs: obligation register (accepted DERIVED facts), evidence gaps,
deadlines, audit pack; risk rating [synth]; responsible owner [ES].

### 3. Procurement & Vendor Intelligence — THIRD (document slice)

Mid-sized companies lose money through unmanaged vendors; this
combines documents, evidence, obligations, time, risk, and
recommendations. The v1 slice is unusually rich because contracts ARE
documents:

`extract_vendor_terms` [now] · `summarize_vendor_contracts`
[now/assist] · `compare_vendor_offers` [now, doc-vs-doc] ·
`detect_expiring_contracts` [now — explicit dates] ·
`flag_auto_renewals` [now — renewal clauses] ·
`identify_price_increase_clauses` [now — clause-level; actual price
paid vs contract is [OE]] · `detect_missing_certifications` [now — the
missing-evidence pattern] · `detect_single_supplier_dependency` [now —
from contracts] · `prepare_renegotiation_brief` [now/assist, synth] ·
`propose_vendor_consolidation` [synth] ·
`compare_sla_obligations_vs_service_records` [OE].

Refused in v1 (each [OE]): invoice transaction mining, PO/payment
reconciliation, duplicate invoice detection, ledger anomaly detection.

Outputs: vendor risk list, renewal calendar, renegotiation package,
contract evidence, negotiation points, approval-required actions.

### 4. Executive Operations Briefing (Management / CEO) — two-stage, by ruling

The flagship executive surface: leadership does not need another
dashboard — they need trusted operational interpretation. Valuable
once the narrower workbenches feed it.

**Stage v1 [now], zero door growth** — accepted facts + governance
health: `summarize_company_status` (approved sources, accepted DERIVED
findings — class always visible, D30) · `detect_operational_risks`
(unresolved conflicts, blocked gates, trust components) ·
`whats_changed_since` (revision/render/ledger history) ·
`generate_executive_brief` [assist] · `prepare_board_report` [assist].

**Stage v2 [PMD]** — the decision queue, the version a CEO pays for:
`what_needs_decision` (held proposals, aging) ·
`departments_with_blockers` · `claims_without_evidence` (verdict
summaries). Plus `risk_register_with_owners` [ES] and month-vs-month
operational comparisons over transactional data [OE].

The ruling this stage forces: **what may an agent know ABOUT ungated
material** — expected landing is metadata-only pipeline state (counts,
kinds, ages, verdict summaries — the operations_view posture), with
candidate CONTENT staying human-only until acceptance, so agents never
reason over unapproved findings. Growing the MCP surface amends
Guard 5's frozen-surface assertion — a ruled change with its own gate.

### 5. Finance & Cost Leakage — document-bound until [OE]

Very strong commercial value, but most of the listed value depends on
transaction records. The agent never changes canonical accounting
data; it creates findings ("contract says payment term 60 days,
invoice applied 30" — that comparison needs the invoice, which is
[OE]).

v1 document slice — **Finance Policy & Contract Leakage**:
`detect_payment_term_policy_mismatch` [now — contract vs approved
policy language] · `detect_renewal_clause_leakage` [now] ·
`detect_budget_policy_gaps` [now — policy-vs-policy] ·
`detect_missing_approval_evidence` [now — the evidence-gap pattern].

v2, behind [OE]: `detect_duplicate_invoices` ·
`detect_unusual_cost_increases` · `compare_contract_vs_invoices` ·
`flag_overdue_receivables` · `identify_budget_overruns` ·
`detect_po_invoice_contract_mismatch` ·
`identify_unused_subscriptions` · `monthly_finance_exception_report` ·
`prepare_cost_reduction_scenarios` [synth].

## Layer 3 — Later expansion (good, deliberately waiting)

**4. Sales & Account Growth** — the governed intelligence layer above
CRM, never a CRM replacement. Doc-side [now]:
`detect_proposal_vs_documentation_mismatch` (a sales proposal
promising something absent from approved product docs — doc-vs-doc),
`compare_customer_needs_vs_offering`, `prepare_meeting_pack` [assist],
`draft_followup` [assist]. Behind [OE]: CRM history summaries, stalled
opportunities, declining-activity detection, upsell candidates,
next-best-action.

**6. HR / People Operations** — sensitive; positioned as "the system
identifies role overlap, bottlenecks, missing skills, and scenario
options — human leadership decides," never "AI fires people."
Doc-side [now]: `detect_policy_contradictions`,
`prepare_onboarding_package` [assist], `generate_hr_faq` [now — via
the valve: synthesis → proposal → human gate → DERIVED],
`detect_expired_certifications` [now — evidence pattern],
`prepare_role_handover` [assist]. Behind [OE]: training-record gaps,
job-description-vs-actual-responsibility comparison, workforce
scenarios [also synth].

**7. Operations / Process Improvement** — the most important
long-term workbench; overlaps process mining. Doc-first [now]:
`detect_sop_conflicts`, `detect_missing_handoffs` (doc-vs-doc),
`find_process_variants_across_teams`, `identify_undocumented_processes`
(a process step appearing in one document's narrative but no approved
procedure). Behind [OE]: SOP-vs-actual-execution, bottleneck/delay
detection from logs and traces, automation candidates with measured
impact.

**10. Project / Delivery** — very commercially understandable for
delivery/consulting companies. Doc-side [now]:
`compare_contract_scope_vs_project_docs` (scope creep as doc-vs-doc),
`extract_open_commitments` (from ingested meeting notes/status docs),
`prepare_client_update` [assist], `generate_lessons_learned` [now, via
the valve]. Behind [OE]: task/deadline states from project systems,
delivery tracking. Commitment/deadline ownership is [ES].

**11. Internal IT / Software / Systems** — starts knowledge-governed,
never autonomous infrastructure control (D22 posture). Doc-side [now]:
`compare_security_policy_vs_approved_tools` (doc-vs-doc),
`detect_contract_renewal_risk`, `prepare_it_asset_register` [now — if
the register is governed documents], `generate_helpdesk_answers`
[assist]. Behind [OE]: license usage, unused accounts, access reviews,
SaaS spend, shadow-IT discovery.

## The boundary audit in one table (D27 applied to the catalog)

**Every commercial workbench is its document-governed slice until the
Operational Evidence decision is minted.** Tickets, invoices, POs,
payments, CRM activity, process logs, and usage data are transactional
records; D27 rules they are not knowledge assets.

| Workbench | v1 (document-governed, buildable now) | v2 (behind Operational Evidence) |
|---|---|---|
| Customer Operations | policies, refund rules, SLAs, procedures, macros — contradictions, outdated guidance, coverage gaps | ticket streams: complaints, SLA breaches, customer-risk scoring, live-case work |
| Compliance & Obligation | obligations, deadlines, evidence gaps from contracts/policies/certifications | policy-vs-practice against operational records |
| Procurement | contracts, terms, renewals, certifications, clause analysis | invoice/PO/payment reconciliation, duplicate invoices |
| Executive Briefing | accepted facts + governance health (v1); decision queue is [PMD] not [OE] | month-vs-month operational comparisons |
| Finance Leakage | contract/payment-term/renewal-clause/budget-policy leakage | transaction mining, subscriptions, ledger anomalies |
| Sales | proposal-vs-documentation mismatch, meeting packs | CRM activity, opportunity/stall detection |
| HR | policy conflicts, FAQ, onboarding packs, certification expiry | training records, role-vs-actual, workforce scenarios |
| Ops / Process | SOP-vs-SOP, handoffs, undocumented processes | process mining over logs and traces |
| Project / Delivery | scope-vs-contract, commitments from ingested notes | live task/deadline states |
| Internal IT | policy-vs-approved-tools, contract renewals | license/account/usage data |

## Named future decisions (named here, minted only by their own scoping sessions)

1. **The Operational Evidence Realm [OE].** A second evidence species —
   transactional records consumed as evidence for findings, never as
   knowledge assets — with its own D-number, its own scoping session,
   and likely its own guard family. Until minted, D27 holds unchanged
   and every workbench stays in its document slice.
2. **Exception Stewardship [ES].** The cross-workbench operating
   queue's human layer. The ruled shape (recorded so it is built this
   way and not as the mirror table): **the exception never becomes a
   row; the human decisions about it do.** Exception existence is
   always computed from governed facts at read time; what may persist
   are human stewardship decisions — assigned, acknowledged, risk
   accepted, escalated, owner, due date, reason — as governed
   identity-backed events (the D3 / conflict-review pattern), keyed to
   the exception's stable computed identity. The queue is the join. A
   work-item row whose OPEN/CLOSED mirrors governed state is the
   two-state-machine drift bug D1 names, and is refused.
3. **The Pipeline Metadata Door [PMD].** Agents consume APPROVED
   knowledge only — held proposals, provenance verdicts on unaccepted
   material, and inbox aging are deliberately not agent-readable today
   (the MCP surface is frozen at 9 tools by Guard 5). The ruling:
   **what may an agent know ABOUT ungated material** — expected
   landing is metadata-only pipeline state, candidate content
   human-only until acceptance. Amends Guard 5's frozen-surface
   assertion; its own gate.

## The skill-contract pattern (how a workbench is defined)

A workbench is not one vague agent — it is a **catalog of governed
subtasks, each with its own declared skill contract**. The product is
never "an agent does compliance"; it is "a governed Compliance
Workbench exposes specific agent skills, each with declared inputs,
evidence rules, refusal rules, output format, and human approval
path." That is more defensible, more testable, and more commercial.

Every skill contract has the same ten-field shape:

> skill name · purpose · allowed inputs · forbidden inputs · governed
> evidence rules · allowed finding kinds · output format · human
> approval requirement · audit expectations · failure & refusal
> conditions

Each workbench ships as a bundle under the guard-swept `workbench/`
root (ONE root, deliberately: Guard 5 Part 5 auto-sweeps `workbench/`;
a second root would sit outside the sweep until a guard amendment):

```
workbench/
  customer_operations/
    workbench.yaml          # the manifest: name, domain scope, binding
                            # expectations, skill list
    skills/
      detect_contradictory_guidance.yaml
      detect_outdated_guidance.yaml
      detect_coverage_gap.yaml
      detect_process_inconsistency.yaml
    runner.py               # the reference consumer (doors only)
    corpus/                 # fixture corpus for gates/demos
  compliance_obligation/    # second in sequence — its own session
  procurement_document_intelligence/   # third in sequence
```

**Skill contracts are convention + claims, not constitution.** EM
cannot enforce behavior on code it does not execute (D22: customers
execute); the contracts govern the reference runner, and the proposal
frontmatter carries the workbench + skill (+ version) that claims to
have produced each finding — recorded verbatim, verified where
governed records permit, never obeyed. The human gate always sees
which skill claimed the finding.

**Skills compose ACROSS the valve, never inside it.** A later skill
(`detect_missing_evidence`) consumes the ACCEPTED outputs of an
earlier skill (`extract_obligations` → human gate → DERIVED obligation
facts) — never another skill's raw, ungated findings.
Second-generation synthesis stays visible at the gate through D30
citation depth.

## The controlled task pattern (every skill of every workbench)

Read governed knowledge (the doors: .empkg + MCP at a real AGENT
token's clearance, the vault as a readable lens) → retrieve approved
evidence → detect → produce finding → attach evidence (governed asset
ids/hashes, conflict ids, reproducible refusals — no evidence, no
finding) → estimate impact [synth, declared, never a governed number]
→ recommend action → write per-finding proposals to /08_proposals →
the human gate → DERIVED facts → audit trail throughout. The agent is
not an uncontrolled actor; it is a **governed analyst**. Never modify
a canonical source directly — no skill has that door, structurally
(Guard 5).

## The commercial package vs the build sequence

The sellable v1 package ("money, risk, customers, leadership, trust")
is five surfaces, and it is honest about what each is:

1. **Customer Operations Workbench** — built at v1.6.0.
2. **Compliance & Obligation Workbench** — built second.
3. **Procurement Document Intelligence** — built third.
4. **Executive Operations Briefing v1** — accepted facts + governance
   health; its decision-queue stage follows the [PMD] ruling.
5. **Knowledge Quality & Conflict + Ask Company Expert + the Exception
   queue** — Layer 1 platform primitives, included in every
   deployment, presented as the platform they are.

Full Finance Leakage joins the package only when the Operational
Evidence Realm is minted — never as a quiet stretch of D27.

## No D32, deliberately

The skill-contract convention (the ten-field shape, the frontmatter
claims, the bundle layout) lives in `vault/00_system/agent-contract.md`
and this document. It is convention, not constitution: the v1.6
scoping deliberately minted **no D32** — D22 + D29/D30/D31 and the six
standing guard families already wall every erosion path a catalog
opens. A workbench-species ruling is earned the moment any governed
surface must DECIDE differently based on workbench or skill identity —
the sharpest named pressure being **skill-aware acceptance**: if the
gate ever VALIDATES a proposal against its claimed skill contract
(e.g. "claims detect_coverage_gap but cites no refusal"), a governed
surface is deciding on skill identity, and that is the ruling moment.
None of that exists, and none is built.
