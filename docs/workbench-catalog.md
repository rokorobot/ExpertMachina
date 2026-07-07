# The ExpertMachina Workbench Catalog

> Ratified 2026-07-03 (the v1.6 scoping session; normalized to 16
> workbenches at the WS0 gate). This is a **product roadmap artifact,
> not register law**: the commercial map — layers, sequence, boundary
> audit, packaging, and the named-but-not-minted future decisions.
> **The catalog holds the map; the registry holds the contracts**: the
> complete master subtask inventory (every workbench, every subtask as
> a named skill contract) lives in
> [workbench-skill-registry.md](workbench-skill-registry.md).
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

## The canonical 16 workbenches

Normalized at the WS0 gate from the original 14 (Customer Support and
Customer Success split; Contract Intelligence added as the shared
contract-analysis engine):

| # | Workbench | Layer / status |
|---|---|---|
| 1 | Executive / CEO | Layer 2 — two-stage (v1 now; decision queue behind [PMD]) |
| 2 | Finance & Cost Leakage | Layer 2 — document-bound until [OE] |
| 3 | Procurement & Vendor Intelligence | Layer 2 — SEQUENCED third (document slice) |
| 4 | Sales & Account Growth | Layer 3 — FUTURE |
| 5 | Customer Support (= Customer Operations, v1.6) | Layer 2 — **ACTIVE, first** |
| 6 | Customer Success / Retention | Layer 3 — FUTURE |
| 7 | HR / People Operations | Layer 3 — FUTURE (positioning-sensitive) |
| 8 | Operations / Process Improvement | Layer 3 — FUTURE (document-first) |
| 9 | Compliance / Obligation Tracking | Layer 2 — **ACTIVE, second (v1.7)** |
| 10 | Document / Knowledge Quality | Layer 1 — PLATFORM |
| 11 | Project / Delivery | Layer 3 — FUTURE |
| 12 | Internal IT / SaaS | Layer 3 — FUTURE |
| 13 | Meeting Intelligence / Decision Follow-up | Layer 1 — PLATFORM-adjacent (deferred surface) |
| 14 | Ask Company Expert | Layer 1 — PLATFORM (shipped) |
| 15 | Risk & Exception | Layer 1 — PLATFORM + [ES] |
| 16 | Contract Intelligence | FUTURE — the shared engine (feeds 2, 3, 6, 9, 1) |

**Layer 1 = platform primitives, already shipped as EM itself** — Ask
Company Expert (the Ask Expert console + `ask_expert` MCP tool),
Document/Knowledge Quality (the governance engine: conflicts,
revisions, trust, dedup, inbox), Risk & Exception (the computed
Governance Inbox + Operations Proposal Pipeline — existence computed,
never persisted), Meeting Intelligence's authorship path (human
decisions enter as ordinary documents → PRIMARY facts). They are
included in every deployment and presented as the platform they are;
re-badging them as separate workbenches would blur EM-governing-itself
with business diagnosis.

**The ratified build sequence:** Customer Operations (v1.6.0) →
Compliance & Obligation → Procurement Document Intelligence
(superseding the v1.5-closeout ordering, by user ruling). The
Executive Briefing is two-stage; Finance is document-bound until [OE].

## Customer Operations v1.6 — the ACTIVE set (amended at the WS0 gate)

Lead with customer-outcome skills built from the same D27-clean base
patterns, not abstract knowledge-quality skills. The wedge:
*"ExpertMachina finds where customer promises, support procedures,
SLA obligations, and customer-facing guidance do not line up — before
customers are harmed."*

| ACTIVE skill | Base pattern | Finding kind · evidence basis |
|---|---|---|
| `detect_customer_promise_conflict` | contradictory-guidance | CUSTOMER_PROMISE_CONFLICT · CONFLICT_BACKED |
| `detect_missing_support_playbook` | coverage-gap | MISSING_SUPPORT_PLAYBOOK · REFUSAL_BACKED |
| `detect_outdated_customer_guidance` | outdated-guidance | OUTDATED_CUSTOMER_GUIDANCE · REVISION_BACKED |
| `detect_sla_obligation_gap` | extract-candidates + missing-evidence | SLA_OBLIGATION_GAP · REFUSAL_BACKED |
| `prepare_customer_policy_brief` | assist | [assist] — evidence-backed topic brief |

The original four skills survive as named base patterns;
`detect_process_inconsistency` is deferred until a corpus carries
enough procedural material. Full contracts: the registry, workbench 5.

## The boundary audit (D27 applied to the catalog)

**Every commercial workbench is its document-governed slice until the
Operational Evidence decision is minted.** Tickets, invoices, POs,
payments, CRM activity, process logs, and usage data are transactional
records; D27 rules they are not knowledge assets. Per-skill tags live
in the registry; the summary:

| Workbench | v1 (document-governed, buildable now) | v2 (behind Operational Evidence) |
|---|---|---|
| 5 Customer Support | policies, refund rules, SLAs, procedures, macros — promise conflicts, missing playbooks, outdated guidance, obligation gaps | ticket streams: complaints, SLA breaches, customer-risk scoring, live-case work |
| 9 Compliance | obligations, deadlines, evidence gaps from contracts/policies/certifications | policy-vs-practice against operational records |
| 3 Procurement | contracts, terms, renewals, certifications, clause analysis | invoice/PO/payment reconciliation, supplier performance |
| 1 Executive | accepted facts + governance health (v1); decision queue is [PMD] | month-vs-month operational comparisons |
| 2 Finance | contract/payment-term/renewal-clause/budget-policy leakage | transaction mining, receivables, ledger anomalies |
| 4 Sales | proposal-vs-documentation mismatch, meeting packs | CRM activity, opportunity/stall detection |
| 6 Customer Success | custom SLA terms, renewal obligations, playbook gaps | activity/usage/churn signals |
| 7 HR | policy conflicts, FAQ, onboarding packs, certification expiry | training records, role-vs-actual |
| 8 Ops / Process | SOP-vs-SOP, handoffs, undocumented processes | process mining over logs and traces |
| 11 Project / Delivery | scope-vs-contract, commitments from ingested notes | live task/deadline states |
| 12 Internal IT | policy-vs-approved-tools, contract renewals | license/account/usage data |
| 16 Contract Intelligence | extraction, clause risk, contract-vs-policy — fully document-side | pricing-vs-invoice verification |

## Named future decisions (named here, minted only by their own scoping sessions)

1. **The Operational Evidence Realm [OE].** A second evidence species —
   transactional records consumed as evidence for findings, never as
   knowledge assets — with its own D-number, its own scoping session,
   and likely its own guard family. Until minted, D27 holds unchanged
   and every workbench stays in its document slice.
2. **Exception Stewardship [ES].** The cross-workbench operating
   queue's human layer. The ruled shape: **the exception never becomes
   a row; the human decisions about it do.** Exception existence is
   always computed from governed facts at read time; what may persist
   are human stewardship decisions — assigned, acknowledged, risk
   accepted, dismissed with reason, escalated, owner, due date — as
   governed identity-backed events (the D3 / conflict-review pattern),
   keyed to the exception's stable computed identity. The queue is the
   join. A work-item row whose OPEN/CLOSED mirrors governed state is
   the two-state-machine drift bug D1 names, and is refused.
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
subtasks, each with its own declared skill contract** in the ten-field
shape (name · purpose · allowed inputs · forbidden inputs · governed
evidence rules · allowed finding kinds · output format · human
approval requirement · audit expectations · failure & refusal
conditions). The registry holds every contract; each workbench ships
as a bundle under the guard-swept `workbench/` root (ONE root,
deliberately — Guard 5 Part 5 auto-sweeps it):

```
workbench/
  customer_operations/
    workbench.yaml          # manifest: name, domain scope, binding
                            # expectations, skill list
    skills/*.yaml           # one contract per skill (13-field YAML)
    runner.py               # the reference consumer (doors only)
    corpus/                 # fixture corpus for gates/demos
```

**Skill contracts are convention + claims, not constitution.** EM
cannot enforce behavior on code it does not execute (D22); the
contracts govern the reference runner, and proposal frontmatter
carries the workbench + skill (+ version) claims — recorded verbatim,
verified where governed records permit, never obeyed. **Skills compose
ACROSS the valve, never inside it**: a skill consumes another skill's
ACCEPTED DERIVED facts, never its pending proposals.

The architecture, end to end:

```
Workbench Catalog → Workbench → Subtask List → Skill Contract
  → YAML implementation → Tests → UI/API surface → Findings
    → Human approval → APPROVED DERIVED fact
```

## The controlled task pattern (every skill of every workbench)

Read governed knowledge (the doors) → retrieve approved evidence →
detect → produce finding → attach evidence (no evidence, no finding)
→ estimate impact [synth-declared, never a governed number] →
recommend action → per-finding proposals to /08_proposals → the human
gate → DERIVED facts → audit trail throughout. The agent is a
**governed analyst**, never an uncontrolled actor. No skill modifies a
canonical source, structurally (Guard 5).

## The commercial package vs the build sequence

The sellable v1 package ("money, risk, customers, leadership, trust"):

1. **Customer Operations Workbench** — built at v1.6.0.
2. **Compliance & Obligation Workbench** — built second.
3. **Procurement Document Intelligence** — built third.
4. **Executive Operations Briefing v1** — accepted facts + governance
   health; the decision-queue stage follows the [PMD] ruling.
5. **The Layer 1 platform primitives** (Ask Company Expert, Knowledge
   Quality, the Exception queue) — included in every deployment,
   presented as the platform they are.

Full Finance Leakage joins only when the Operational Evidence Realm is
minted — never as a quiet stretch of D27. Contract Intelligence is
earned as a standalone workbench once two of its consumer workbenches
exist.

## No D32, deliberately

The skill-contract convention lives in
`vault/00_system/agent-contract.md`, the registry, and this document.
It is convention, not constitution: the v1.6 scoping deliberately
minted **no D32** — D22 + D29/D30/D31 and the six standing guard
families already wall every erosion path a catalog opens. A
workbench-species ruling is earned the moment any governed surface
must DECIDE differently based on workbench or skill identity — the
sharpest named pressure being **skill-aware acceptance**: if the gate
ever VALIDATES a proposal against its claimed skill contract, that is
the ruling moment. None of that exists, and none is built.
