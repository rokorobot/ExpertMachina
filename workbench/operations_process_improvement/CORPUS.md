# Operations / Process Improvement — corpus map (v1.0)

The runtime corpus is `corpus_operations/` — six SHORT synthetic
process documents for the fictional "Meridian Operations Ltd". ALL
content is fabricated; no real company process data appears anywhere.
This file is the non-runtime oracle (the plant map): it records what
each document seeds so the suites can assert the runner detects it. The
runner never reads this file.

Corpus dir naming follows the newest shipped convention (finance uses
`corpus_finance/`, so this bundle uses `corpus_operations/`).

## The documents

| Document | Role | Plants |
|---|---|---|
| `employee-onboarding-sop.md` | SOP (OPS-ON-01) | An **access-approval timing** statement ("approved within 2 business days") — the contradiction side vs the access-request procedure. A **terminal step with an undefined handoff**: the onboarding buddy programme "is complete after the two-week period" with no next owner / receiving procedure. Ordered process steps for the process-map assist. |
| `access-request-procedure.md` | Procedure (OPS-AC-02) | An **access-approval timing** statement ("approved within 5 business days") — the OTHER contradiction side (same subject: access / approved / request / business days). A **handoff GAP** in Revocation: the marked record "is then closed out" with no owner / receiver. Ordered steps for the assist. |
| `change-management-policy.md` | Governing policy (POL-CM-01) | An **approval-authority** rule: every production change "must be approved by the Change Advisory Board"; "No production change may be deployed on the authority of a single approver" — the policy side of the SOP-vs-policy mismatch. A **declared review cadence** ("every 12 months", last review 2024-01-15) — overdue-by-own-interval staleness material. |
| `change-management-sop.md` | SOP (OPS-CM-03) | An **approval-authority** procedure: "A production change may be approved by the team lead alone" — the SOP side of the SOP-vs-policy mismatch (approval_authority axis). A **declared review cadence** ("every 6 months", last review 2024-02-01) — overdue-by-own-interval staleness material. |
| `remote-access-sop.md` | SOP (OPS-RA-04) | A remote-access rule using a **shared team VPN credential** — the SUPERSEDED document (no supersession notice of its own, no recent review date). |
| `access-governance-policy.md` | Governing policy (POL-AG-02) | An explicit **supersession notice**: "This policy supersedes the shared-credential remote access rule stated in the Remote Access SOP (OPS-RA-04)"; the newer rule ("personal individually issued VPN credential"; "Shared team VPN credentials are prohibited"). Carries a recent review date (2026-05-01). The supersession side of the outdated-document finding. |

## The seeded defects (one per [now] skill, plus assist material)

- **detect_process_contradictions** — onboarding SOP ("within 2
  business days") vs access-request procedure ("within 5 business
  days") for access approval: a cross-document contradiction on a
  shared subject (access / approved / request).
- **compare_sop_vs_policy** — change-management SOP ("approved by the
  team lead alone") vs change-management policy ("must be approved by
  the Change Advisory Board" / "single approver" prohibited): an
  SOP-vs-policy mismatch on the `approval_authority` axis.
- **detect_missing_handoffs** — the access-request procedure Revocation
  step ("is then closed out") and the onboarding buddy programme ("is
  complete after the two-week period") each terminate with no defined
  next owner / receiving procedure.
- **detect_outdated_process_documents** — the Remote Access SOP is
  superseded by the Access Governance Policy's explicit supersession
  notice (revision-backed). The change-management documents are also
  overdue by their own declared review cadence against a declared
  as_of.
- **prepare_process_map_projection** — the onboarding SOP and the
  access-request procedure carry ordered, citable steps sufficient to
  compose a cited, non-authoritative process map with declared absences.

## Seeding notes for the suites

- The suites drive the runner over these six documents as governed
  PRIMARY facts (the acceptance suite uses a lightweight in-process
  package + injected answerer/graph seams, exactly as the shipped
  reference suites inject their CI seams — no execution/operational door
  is ever opened).
- There is deliberately NO execution-record plant in the runtime
  corpus: the adversarial "decline an execution record naming [OE]"
  case is exercised by an INJECTED execution-record fixture in the
  acceptance suite (an execution record cannot exist in a
  process-document corpus by accident — it must be injected), mirroring
  the finance INVOICE PLANT fixture discipline.
