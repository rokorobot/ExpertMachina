# The Customer Operations corpus — plant map and choreography

> This file lives OUTSIDE `corpus/` deliberately: the PROPOSAL-side
> suites scan `corpus/` through a PRIMARY-lane connector, and the
> plant map must never be ingested as a document. `corpus_seed/`
> holds prior-revision content and is likewise never scanned as-is.

The corpus is knowledge-only by design (D27): support policies,
refund rules, SLA documents, procedures, macros, sales collateral.
No tickets, no customer records, no transaction exports.

## The plants (one per ACTIVE finding skill)

| # | Plant | Documents | Detected by |
|---|---|---|---|
| P1 | The 24h/48h promise conflict: sales collateral guarantees enterprise first response within 24 hours; the escalation SOP sets a 48-hour first-response target | `sales-enterprise-brochure.md` × `support-escalation-procedure.md` | `detect_customer_promise_conflict` (governed DIRECT_CONTRADICTION; real NLI ~0.97) |
| P2 | The missing enterprise refund-exception playbook: the refund policy names it; no such document exists | `refund-policy.md` (the reference); the playbook deliberately absent | `detect_missing_support_playbook` (consume() refusal) |
| P3 | The outdated FAQ: still states the 30-day refund window; the approved refund policy is revision 2 (14 days) | `support-faq.md` × `refund-policy.md` (+ `corpus_seed/refund-policy.md` = revision 1) | `detect_outdated_customer_guidance` (revision chain + conflict) |
| P4 | The unfulfillable reporting obligation: the MSA requires a monthly service performance report; no procedure or owner is documented | `enterprise-master-service-agreement.md`; the procedure deliberately absent | `detect_sla_obligation_gap` (obligation excerpt + refusal) |
| P5 | The clearance sentinel: the refund authority matrix is seeded EXECUTIVE; its sentinel string must never appear in any INTERNAL-clearance proposal byte | `refund-authority-matrix.md` (sentinel `EM-EXEC-SENTINEL-9Q4Z`) | the WS2 clearance-honesty assertion |

Everything else is healthy context, so the diagnosis is not shooting
fish in a barrel. Healthy documents deliberately do NOT cover the P2
playbook or the P4 reporting procedure.

## Revision choreography (P3)

1. Copy `corpus_seed/refund-policy.md` (revision 1: 30 days) into the
   scan folder → scan → human-approve.
2. Overwrite with `corpus/refund-policy.md` (revision 2: 14 days, the
   playbook reference) → rescan → CHANGED → candidate revision →
   human-approve the revision (D7/D17: revisions are always
   human-gated).
3. `support-faq.md` (still 30 days) now both conflicts with the
   current policy and matches the superseded revision — the
   REVISION_BACKED evidence for P3.

## Seeding notes for the suites

- Scan `corpus/` through a PRIMARY-lane LocalFolder connector into a
  throwaway project; classify into the `customer_operations` domain;
  human-approve.
- Seed `refund-authority-matrix.md`'s asset to EXECUTIVE access level
  after extraction (the P5 sentinel).
- Compile the package FOR INTERNAL clearance; bind to a real AGENT
  principal; the workbench runs at that binding.
