# Finance & Cost Leakage — corpus map (v2.3)

v2.3 is REUSE-FIRST (WS0 ruling 7). The runtime corpus is the
existing procurement corpus (contract cost/payment/renewal material)
plus the v2.1 register and v2.2 calendar substrate. The WS1
corpus-gap scan proved three real gaps the existing corpora cannot
carry; per WS0 ruling 7 and the user-ratified mid-WS1 stop
(2026-07-09), the plants below land in this `corpus_finance/`
extension folder — the ratified v2.2 `corpus_deadline/` pattern: only
the v2.3 suites ingest it, so the shipped corpora's doc-count
assertions stay byte-untouched.

## Reused WITHOUT plants (recorded so nobody re-plants what exists)

- Procurement corpus: payment terms 21/60 days vs. the procurement
  policy's ≥45-day floor (a live payment_terms mismatch); the 7%
  anniversary fee escalator; the "one fifth" paraphrase trap; the
  cloudhost MSA late-payment language; dated renewal/termination
  clauses (2026-08-15 etc.) for THE SECOND HARVEST.

## The corpus_finance/ plants (WS1, user-ratified 2026-07-09)

| Document | Plants |
|---|---|
| `finance-policy.md` | **Spend-approval thresholds** (5,000 / 50,000 EUR tiers) — the spend_thresholds comparison axis + the spend_approval requirement class; a **payment-terms floor** (≥30 days) — the payment_terms axis; **budget discipline** (>10% renewal re-approval) — policy_coverage + the renewal_cost exposure comparison. Gap (a): no finance-policy document existed. |
| `datacenter-colocation-agreement.md` | **Verbatim currency amount** (12,000 EUR/month) — gap (b), enables declared-arithmetic material; **penalty/surcharge clause** (1.5%/month late surcharge) — gap (c), the penalty_fee exposure class; **8% anniversary escalator** (price_increase); **minimum commitment / true-up / non-refundable** (leakage); **90-day auto-renewal** (renewal_cost + THE SECOND HARVEST window). |
| `vendor-invoice-4471.md` | **THE INVOICE PLANT (adversarial)** — an invoice-shaped TRANSACTIONAL RECORD carrying SETTLED-ACCOUNT vocabulary ("was paid", "payment cleared", "was issued", "amount due"). Gap (d): the adversarial forbidden-input case cannot exist in a document corpus by accident — it must be planted. THE UNOPENED LEDGER requires it: even human-approved, it must be DECLINED as exposure evidence with a declared [OE] skip. |

## Seeding notes for the suites

- Scan the procurement corpus + `corpus_finance/` through PRIMARY-lane
  LocalFolder connectors; approve all as a human; the finance domain.
- THE INVOICE PLANT is approved as a DOCUMENT but must never become an
  exposure INPUT — the runner (WS2) declines it with a declared skip
  naming [OE]; the precondition proof (WS1) proves it is distinguishable
  (it carries transactional-truth markers no contract clause carries).
- The register/calendar substrate is a runtime input (WS2/WS3); at WS1
  the precondition proof uses a register-style anchor to prove the
  harvest citation resolves BY id before any runner exists.
