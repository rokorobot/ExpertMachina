# The Compliance & Obligation corpus — plant map

> This file lives OUTSIDE `corpus/` deliberately: the suites scan
> `corpus/` through a PRIMARY-lane connector, and the plant map must
> never be ingested as a document. It is the **non-runtime oracle**
> for test expectations (the v1.6 protected boundary: corpus plant
> map ≠ runtime evidence).

The corpus is knowledge-only by design (D27): a data processing
agreement, security and access policies, a certification statement, a
regulatory record-keeping summary, an archiving guideline, incident
response material, an executive risk memo, and a code of conduct. No
operational records, no logs, no tickets, no payments, no filings.
Domain scope: `compliance`.

## The plants (per ACTIVE skill; covered controls included — refusal-first cuts both ways)

| # | Plant | Documents | Detected by |
|---|---|---|---|
| P1 | Explicit obligations across all four declared source types: breach notification within 72 hours + sub-processor approval (contract), annual training + completion summary (policy), maintain ISO 27001 (certification), ten-year contract-record retention (regulatory) | `data-processing-agreement.md`, `security-training-policy.md`, `iso-27001-certification-statement.md`, `regulatory-record-keeping-summary.md` | `extract_compliance_obligations` (explicit must/shall markers, verbatim excerpts, declared source_type + obligation_type) |
| P2 | Missing evidence: the training policy requires a completion summary per cycle; no approved completion-summary record exists | `security-training-policy.md` (the requirement); the evidence deliberately absent | `detect_missing_evidence`, class `training_completion` (consume() refusal) |
| P2c | COVERED control: the incident response plan must be tested annually AND the approved test report exists — NO finding | `incident-response-plan-summary.md` (requirement) + `incident-response-test-report.md` (evidence) | `detect_missing_evidence`, class `incident_response_testing` (consume() answers) |
| P3 | Overdue by its own declared review interval: reviewed every 12 months, last completed review dated 2024-05-02 — overdue at the pinned as_of 2026-06-01 | `acceptable-use-policy.md` | `identify_outdated_policies` (the declared review-interval convention; never age alone) |
| P3c | CURRENT control: same declared convention, last completed review dated 2025-11-10 — current at as_of 2026-06-01, NO finding | `access-control-policy.md` | `identify_outdated_policies` (no finding) |
| P4 | Undocumented owner: no approved document names who is responsible for personal data breach notifications | `data-processing-agreement.md` (the obligation); the owner statement deliberately absent | `detect_undocumented_obligation_owner` (consume() refusal on the owner question) |
| P4c | COVERED control: the Compliance Officer is named responsible for coordinating the annual ISO 27001 surveillance audit — NO finding | `iso-27001-certification-statement.md` | `detect_undocumented_obligation_owner` (consume() answers) |
| P5 | Compliance contradiction, same subject, cross-document: contract records retained TEN years vs destroyed THREE years after termination | `regulatory-record-keeping-summary.md` × `finance-archiving-guideline.md` | `detect_conflicting_compliance_statements` (governed DIRECT_CONTRADICTION; real NLI) |
| P6 | The clearance sentinel: the executive risk memo is seeded EXECUTIVE; its sentinel string must never appear in any INTERNAL-clearance byte | `compliance-risk-acceptance-memo.md` (sentinel `EM-EXEC-SENTINEL-7C2R`) | the WS2 clearance-honesty assertion |
| P7 | The implied-obligation sentinel: "Teams are encouraged to archive completed project files when convenient." carries NO explicit marker and must never be extracted as an obligation | `code-of-business-conduct.md` | `extract_compliance_obligations` (explicit markers only) |

Everything else is healthy context. Healthy documents deliberately do
NOT provide the P2 training completion summary or name the P4 breach
notification owner.

## The declared clock (P3/P3c)

The review-interval rule runs at a DECLARED `as_of` date, never
wall-clock. The suites pin `as_of = 2026-06-01`:

- `acceptable-use-policy.md`: 2024-05-02 + 12 months = 2025-05-02 <
  2026-06-01 → **overdue** (finding).
- `access-control-policy.md`: 2025-11-10 + 12 months = 2026-11-10 ≥
  2026-06-01 → **current** (no finding).

## Seeding notes for the suites

- Scan `corpus/` through a PRIMARY-lane LocalFolder connector into a
  project; approve all candidates as a human; classify into the
  `compliance` domain.
- Seed the risk memo's extracted assets EXECUTIVE before compiling
  the INTERNAL package (the P6 sentinel proof runs on package bytes).
- No revision choreography in this corpus: the outdated-policy plant
  is the review-interval species (the supersession species was proven
  at v1.6).
- The composition proof (WS3) re-enters accepted COMPLIANCE_OBLIGATION
  facts and re-runs `detect_missing_evidence` over the recompiled
  package — second-generation findings cite DERIVED evidence.
