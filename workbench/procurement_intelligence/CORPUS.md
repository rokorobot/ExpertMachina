# The Procurement Document Intelligence corpus — plant map

> This file lives OUTSIDE `corpus/` deliberately: the suites scan
> `corpus/` through a PRIMARY-lane connector, and the plant map must
> never be ingested. It is the **non-runtime oracle** for test
> expectations (the standing protected boundary: plant map ≠ runtime
> evidence).

Knowledge-only by design (D27): vendor agreements, an SLA schedule,
the procurement policy, supplier records, a certification copy, a
vendor standard, and an executive memo. No invoices, POs, payments, or
transactional records. Domain scope: `procurement`.

## The declared clock

The suites pin `as_of = 2026-06-01` and `window_days = 90` (window end
2026-08-30). Both are declared run parameters, never wall-clock.

## The plants

| # | Plant | Document | Detected by |
|---|---|---|---|
| P1 | Renewal window POSITIVE: "terminates on 2026-08-15" — inside the window (75 days from as_of) | cloudhost-master-services-agreement.md | detect_renewal_window |
| P1c | Renewal window NEGATIVE: "terminates on 2027-09-30" — outside the window, NO finding | officesupply-agreement.md | covered control |
| P2 | Auto-renewal clause with the verbatim 60-day notice period | cloudhost-master-services-agreement.md | detect_renewal_window (facet) |
| P3 | Explicit price increase: "increases by 7% on each anniversary" | translient-consulting-agreement.md | detect_price_increase_clauses |
| P3t | THE PARAPHRASE TRAP: "increases by one fifth at renewal" — quoted as text, NEVER "20%" | printworks-framework-agreement.md | THE CLAUSE ARITHMETIC PROOF |
| P4 | Missing supplier certification: DataFlow processes customer data; no certificate document exists | dataflow-processing-addendum.md + procurement-policy.md (the requirement) | identify_missing_supplier_certifications |
| P4c | COVERED certification: SecureStore processes customer data AND its ISO 27001 certificate is on file — NO finding | securestore-data-services-agreement.md + securestore-iso-certificate.md | covered control |
| P5 | Vendor-policy conflict: "payable within 21 days" (CloudHost) vs "must be at least 45 days" (Procurement Policy) — cross-document, same subject | cloudhost-master-services-agreement.md × procurement-policy.md | detect_vendor_policy_conflict |
| P5c | CONFORMING control: "payable within 60 days" — meets the policy, NO finding | officesupply-agreement.md | covered control |
| P6 | UNPARSEABLE DATE: "renews at the start of the fiscal year of the customer" — renewal context, no parseable date, REFUSED declared | legacy-datacenter-agreement.md | the refusal proof |
| P7 | EXECUTIVE sentinel `EM-EXEC-SENTINEL-4V8P` — never in any INTERNAL-clearance byte | executive-vendor-strategy-memo.md | the clearance sweep |
| P8 | The noisy contract: address "4501 Commerce Park, Suite 210", phone "+1 555 0142", "clause 12.3", the "700000" PO range — numbers that must NEVER be promoted into findings | officesupply-agreement.md | THE CLAUSE ARITHMETIC PROOF |
| T1 | Term extraction: "99.9% monthly service availability" (sla class), the subprocessor notice term (data_access class) | cloudhost-sla-schedule.md | extract_vendor_terms |

Everything else is healthy context. Healthy documents deliberately do
NOT provide a DataFlow certificate, do NOT name a shorter-terms
exception for CloudHost, and do NOT state "20%" anywhere in the
corpus.

## Seeding notes for the suites

- Scan `corpus/` through a PRIMARY-lane LocalFolder connector into a
  project; approve all candidates as a human; classify into the
  `procurement` domain.
- Seed the executive memo's extracted assets EXECUTIVE before
  compiling the INTERNAL package (the P7 sentinel proof runs on
  package bytes).
- The pinned clock: `as_of = 2026-06-01`, `window_days = 90`, declared
  in every suite that computes a window — never sampled.
