# Customer Success Intelligence — corpus map (v2.4)

v2.4 is REUSE-FIRST (WS0 ruling 7). The runtime corpus is the
existing customer-operations corpus (customer-facing promises, SLAs,
procedures) plus the v2.1 register substrate. The WS1 corpus-gap scan
proved four real gaps the existing corpora cannot carry; per WS0
ruling 7 and the user-ratified mid-WS1 stop (2026-07-09), the plants
below land in this `corpus_customer_success/` extension folder — the
ratified v2.2/v2.3 extension pattern: only the v2.4 suites ingest it,
so the shipped corpora's doc-count assertions stay byte-untouched.

## Reused WITHOUT plants (recorded so nobody re-plants what exists)

- Customer-operations corpus (12 documents): the
  `sales-enterprise-brochure.md` QBR PROMISE ("Enterprise
  subscriptions include quarterly business reviews...") — the promise
  side of the qbr_procedure coverage gap already exists governed, and
  NO QBR procedure exists anywhere (the gap is real in the shipped
  corpus); `support-escalation-procedure.md` — the COVERED side
  (escalation obligations have approved coverage, so the covered case
  stays silent); the enterprise MSA template's standard values
  (monthly report / five business days / ninety-day notice), echoed
  by the planted baseline so no manufactured conflicts exist.

## The corpus_customer_success/ plants (WS1, user-ratified 2026-07-09)

| Document | Plants |
|---|---|
| `customer-success-standard-terms.md` | **The load-bearing governed baseline** (gap a). Every axis sentence self-identifies with the declared baseline marker ("standard terms") AND extracts (trigger words in-sentence): monthly performance report within five business days (reporting_cadence axis); ninety-day notice on twelve-month terms (renewal_notice axis); escalations deferred to the approved procedure. THE BASELINE DOCTRINE rests here: no standard baseline, no deviation diagnosis. |
| `acme-service-agreement.md` | **The DEVIATING named customer** (gap b) — Acme Industrial: WEEKLY report within TWO business days (deviates from monthly/five); SIXTY-day notice (deviates from ninety); the current term ends 2026-09-30 with sixty-day notice in ONE sentence (THE COMPUTED RENEWAL WINDOW anchor: 2026-09-30 − 60 days = 2026-08-01 by declared arithmetic); a QBR obligation (the qbr_procedure coverage gap fires — no QBR procedure exists); a ten-business-day maintenance notification obligation; escalations deferred to the approved procedure (covered → silent). |
| `northwind-service-agreement.md` | **The CONFORMING named customer** (gap c) — Northwind Logistics: monthly report within five business days (conforms); ninety-day notice (conforms); term ends 2027-03-31 (outside the declared window). **Its silence is the other half of THE CUSTOM TERMS PROOF** — the workbench is a diagnosis, not a report generator. |
| `acme-account-plan.md` | **THE HEALTH-SCORE PLANT (adversarial)** (gap d) — an internal account plan carrying a health-score table AND assertion-shaped relationship-state claims ("adoption is healthy", "churn risk is low", "customer is satisfied", "likely to renew", "health score ... 82") with NO governed evidence. THE HEALTH-SENTENCE DISTINCTION requires it: even human-approved, it may surface ONLY as quoted unsupported assumptions (THE QUOTE FRAME) — never as customer health truth, never as telemetry. The WS1 separability precondition: the manifest's forbidden vocabulary appears in NO approved fact except the facts extracted from THIS document. |

## Seeding notes for the suites

- Scan the customer-operations corpus + `corpus_customer_success/`
  through PRIMARY-lane LocalFolder connectors (12 + 4 = 16
  documents); approve all as a human; the customer-success domain.
- THE HEALTH-SCORE PLANT is approved as a DOCUMENT but its claims
  must never become relationship-state findings — the runner (WS2)
  surfaces them only inside THE QUOTE FRAME as unsupported
  assumptions; the precondition proof (WS1) proves byte-level
  separability (no other approved fact carries the forbidden
  vocabulary).
- The register substrate is a runtime input (WS2/WS3); at WS1 the
  precondition proof uses the dated Acme renewal clause as the
  harvest anchor citable BY governed asset id before any runner
  exists.
- Declared run parameters for the proofs: as_of 2026-07-10, window 90
  days, customers "Acme Industrial" / "Northwind Logistics", baseline
  marker "standard terms".
