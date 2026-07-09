# v2.3 — Finance & Cost Leakage — Build Contract

> Scoped 2026-07-09 (the v2.3 scoping session, post-v2.2.0 release;
> baseline main `500c2a5`, tag `v2.2.0` = `7040cda`, harness 83/83,
> D24 at 28/305, route manifest 88, MCP 9, seven guard families,
> [OE]/[PMD] unminted). Input briefs: PROJECT_STATE.md, DECISIONS.md
> (through D32), docs/workbench-skill-registry.md (workbench 2 —
> "document-bound until [OE]"), and the gate records of
> v1.7/v1.8/v2.1/v2.2 (the register + calendar substrate). The FIFTH
> commercial workbench and the SECOND consumer of the earned
> substrate. **WS0 RATIFIED by the user on 2026-07-09** — the rulings
> below stand as written; gate records are appended per workstream.

## The milestone identity (the spine, carried verbatim into every gate)

**v2.3 is document-governed cost exposure intelligence, not finance
operations.** *"v2.3 diagnoses governed cost exposure from approved
documents, register facts, and declared-clock windows. It does not
determine transactional financial truth."*

## Ruling 1 — The boundary (registry #2 ratified as binding)

INCLUDED: contract terms vs. finance policy; fee/penalty/renewal/
termination/notice/surcharge/escalation/discount/credit/leakage
exposure AS STATED in approved documents; register-fed exposure
windows; declared-clock cost windows; governed "what could this
cost?" diagnostics; declared arithmetic; labeled scenarios;
diagnostics exposing risk/evidence/assumptions/exclusions/next review
action. EXCLUDED (all [OE]): invoices/POs/payments as records; bank
status; ERP balances; ledger truth; actual spend; every "was it paid
/ issued / did it happen / is the balance wrong" question.
**THE INVOICE-SENTENCE DISTINCTION**: a document statement ABOUT
invoices ("payable within 21 days") is governed evidence, in-scope;
an invoice AS A RECORD is [OE]. The boundary is on assertions about
transactional truth, never on the word "invoice" — the corpora
already contain contract sentences about invoices and the
forbidden-inputs sweep must not false-positive on them.

## Ruling 2 — THE ACTIVE FIVE (consolidation map; sweep numbers pinned at WS1)

| ACTIVE (v2.3) | Consolidates | Kind · basis |
|---|---|---|
| `detect_cost_exposure` [now] | #2 drafts 3+4+9+13 | COST_EXPOSURE · EXCERPT_BACKED + declared-clock/declared-formula arithmetic; declared exposure_classes (price_increase, renewal_cost, penalty_fee, leakage, pricing_review); register clauses + calendar windows first-class inputs BY governed asset id |
| `compare_terms_vs_finance_policy` [now] | drafts 2+7+10 | FINANCE_POLICY_MISMATCH · CONFLICT/EXCERPT_BACKED; declared comparison axes (payment_terms, spend_thresholds, pricing_discipline) |
| `detect_missing_finance_evidence` [now] | drafts 5(document-bound half)+6+14 | MISSING_FINANCE_EVIDENCE · REFUSAL_BACKED; declared requirement classes |
| `prepare_cost_exposure_scenario` [assist, synth] | draft 8 (renamed) | THE LABELED-ESTIMATE discipline lives here |
| `prepare_finance_evidence_pack` [assist] | draft 12 + absorbs 11 as a declared section | known/exposed/conflicting/estimated clearly separated |

**Two cross-workbench consolidations (a FIRST — ratified openly):**
draft 1 `extract_payment_terms` → CONSOLIDATED into the v2.1 register
(`extract_contract_clauses` — the shared-engine principle: nothing
re-extracts); draft 15 `detect_outdated_finance_policies` →
CONSOLIDATED into the shipped v1.7 `identify_outdated_policies`
(same mechanism, domain-scoped at runtime). Draft 16 stays
[ES]-gated; the six Future-[OE] drafts stay FUTURE.

## Ruling 3 — THE MONEY DOCTRINE: NO INVENTED MONEY (three tiers)

Every money value in any v2.3 output is exactly one of: (1)
**verbatim** from an approved document/register fact, cited by asset
id; (2) **declared arithmetic** — the formula stated in the finding,
over cited verbatim values and declared clock parameters (the v1.8
CLAUSE ARITHMETIC lineage; "one fifth" never becomes "20%"); (3) a
**labeled estimate/scenario** — the non-authoritative label IN THE
SAME OUTPUT UNIT as the number, confined to [assist, synth], never a
finding fact, never a governed number.
**THE CARDINAL SIN — THE INVENTED MONEY**: presenting an invented,
inferred, approximated, or scenario value as governed financial
fact. **Its twin — THE SETTLED ACCOUNT**: asserting transactional
truth (paid, spent, booked, balanced) from any evidence at all. Both
swept on every written byte (forbidden vocabulary + a money-token
sweep).

## Ruling 4 — Forbidden inputs (exhaustive)

Invoices as transactional records · POs as operational records ·
payments/payment status · bank status · ERP balances ·
accounting-ledger state · actual-spend records · receivables/
payables state · any "did it happen?" record — plus the standing
base (ungoverned sources; candidate/held content; other skills'
pending findings; wall-clock time). **THE INVOICE PLANT
(adversarial)**: an invoice-shaped document ingested through the
pipeline must be DECLINED as exposure evidence with a declared skip
naming [OE] — approved-document status does not launder
transactional records into exposure inputs.

## Ruling 5 — Allowed / disallowed outputs

ALLOWED: COST_EXPOSURE / FINANCE_POLICY_MISMATCH /
MISSING_FINANCE_EVIDENCE findings through the unchanged valve; the
07-confined scenario brief and evidence pack. Every diagnosis exposes
evidence (by id, DERIVED as DERIVED), arithmetic (formula verbatim),
assumptions, exclusions, uncertainty. DISALLOWED: any assertion of
actual spend/payment/balance/booking/completion; unlabeled
estimates; non-tier-1/2 governed numbers; accounting-truth phrasing;
anything [OE]/[PMD]; schedules/reminders/tracking (v2.2 carries).

## Ruling 6 — The named proofs

- **THE UNOPENED LEDGER** (the distinctive WS3 stage): the full
  diagnosis completes citing only approved documents + register facts
  BY ID + calendar windows at the declared clock, and the forbidden
  inputs were never read, proven three ways — structurally (no door
  exists), adversarially (THE INVOICE PLANT declined, [OE] named),
  and on the bytes (THE SETTLED ACCOUNT sweep).
- **THE EXPOSURE ARITHMETIC PROOF**: every statement-number
  verbatim-cited or declared-formula arithmetic at the declared clock.
- **THE INVENTED MONEY SWEEP**: every money token in every byte
  resolves to tier 1/2/3 — nothing else exists.
- **THE SECOND HARVEST PROOF**: exposure findings citing v2.1
  register clauses and v2.2-computed windows BY governed asset id —
  nothing re-extracted.
- **THE LABELED SCENARIO PROOF**: every estimate wears its label
  in-unit; an unlabeled estimate refused pre-write; scenarios never
  enter knowledge.
- **THE COMMERCIAL VERDICT** (user-ratified, never automated) — the
  finance reader (CFO/controller): *"Would you put this governed
  cost-exposure diagnosis in front of your monthly finance review —
  every figure quoted from an approved document or computed by
  declared arithmetic you can check, every estimate labeled as an
  estimate, every exposure window on a declared clock — knowing it
  will never tell you what was actually paid, spent, or booked until
  an operational evidence realm is deliberately minted?"*

## Ruling 7 — The corpus decision (ruling-10 shape, empirically pre-informed)

REUSE FIRST: the procurement corpus carries real exposure material
(payment terms 21/60 days vs. the policy ≥45-day floor — a live
mismatch; the 7% anniversary fee escalator; the "one fifth"
paraphrase trap; late-payment language) + the register/calendar
substrate. **Pre-registered likely gaps (from the 2026-07-09 scan,
to be PROVEN at WS1 before any plant lands)**: (a) no explicit
finance-policy document (spend-approval thresholds, budget
discipline); (b) no verbatim currency amount anywhere for exposure
arithmetic; (c) no penalty/surcharge clause material; (d) THE
INVOICE PLANT's adversarial document. If proven, plants land in a
**`corpus_finance/` extension folder** (the ratified v2.2 pattern —
shipped doc-count assertions byte-untouched), plant map appended,
user-ratified at the mid-WS1 stop.

## Ruling 8 — Zero new surface, zero new law

New bundle `workbench/finance_cost_leakage/` (a NEW workbench — #2
is unshipped — not an extension) on `common.py` (zero shared-module
edits, the sixth reuse target). No D33, no eighth guard, no new
decision kinds, route manifest 88, MCP 9, D24 28/305, Guard 7
untouched, [OE]/[PMD] refused live and named.

## The gate checklist (each claim testable)

cites register+calendar BY ID · declared arithmetic with the formula
on the bytes · estimates labeled in-unit · CANNOT read
invoices/POs/payments/ERP/ledger/bank status (structural +
adversarial + byte-level) · CANNOT assert actual
spend/payment/balance/completion · CANNOT present estimates as
governed numbers · every diagnosis exposes
evidence/arithmetic/assumptions/exclusions/uncertainty · zero new
routes/tables/tools/guards/law · [OE]/[PMD] refused live · Guard 7
untouched · shipped suites byte-untouched · the valve holds; one
human acceptance stays DERIVED.

## The WS sequence + the Opus handoff note

- **WS0** — these rulings. **RATIFIED 2026-07-09.**
- **WS1** (Opus per routing) — the five contracts + registry #2
  promotion (incl. the two cross-workbench consolidations, drafts
  with `consolidated_into` + resolving `ratified_path`; sweep
  constants move from 29/44 — pinned at WS1) + the corpus-gap stop
  (state the gap, user ratifies the plants) + THE PRECONDITION PROOF
  (84th suite) BEFORE any runner.
- **WS2** — the runner on `common.py` + THE DIAGNOSIS PROOF (85th).
- **WS3** — THE MILESTONE GATE (86th) + the five named proofs +
  browser before/after (the Workbench Catalog panel gains its
  Finance card via ONE `WORKBENCH_CATALOG_INFO` row — presentation
  only) + THE COMMERCIAL VERDICT.
- **The v2.2 lessons apply verbatim** (recorded in the memory
  playbook): extension maps for any constant a shipped suite derives
  dynamically; gates refuse first, parameter refusals second and
  targeted-only; the three operational-evidence fingerprint
  exclusions (audit_events / credentials / identity_facts); a
  verbatim quote containing money is NOT invented money — sweep
  against full cited source content, never truncated excerpts;
  extension-corpus folders keep shipped assertions byte-untouched.

## Standing boundaries

Generated draft ≠ executable skill; ratified contract ≠ global
permission; plant map ≠ runtime evidence; runner output ≠ canonical
knowledge. Every gate re-runs the D25 sweep and closes on the D24
snapshot. Guard 5 sweeps the new bundle the moment it exists; Guard
6 holds the vault seam; Guard 7 holds stewardship. EM never launches
the workbench (D22). Language per Ruling 3/5 and D29/D30.

---

## WS1 — the contracts, the promotion, and THE PRECONDITION PROOF (2026-07-09)

**The corpus-gap stop (mid-WS1, user-ratified):** the scan proved the
existing corpora carry real exposure material (the procurement
payment-terms 21/60 vs ≥45 mismatch; percentage escalators; the
paraphrase trap; late-payment language) but three gaps were real: no
finance-policy document with spend thresholds, no clean
penalty/surcharge clause with a verbatim rate and no verbatim
currency amount for arithmetic, and no invoice-shaped record (THE
INVOICE PLANT is adversarial — it cannot exist by accident). The user
ratified **`corpus_finance/`** (the v2.2 extension-folder pattern; only
v2.3 suites ingest it): `finance-policy.md` (5,000/50,000 EUR
approval tiers, a ≥30-day payment floor, the >10% renewal
re-approval), `datacenter-colocation-agreement.md` (12,000 EUR/month
verbatim fee, the 8% escalator, the 1.5%/month late surcharge, the
120,000 EUR minimum-commitment/true-up leakage clause, the 90-day
auto-renewal), and `vendor-invoice-4471.md` (**THE INVOICE PLANT** —
a transactional record carrying SETTLED-ACCOUNT vocabulary, planted
to be DECLINED). Plant map in `workbench/finance_cost_leakage/CORPUS.md`.

**The five ratified contracts**
(`workbench/finance_cost_leakage/skills/`): `detect_cost_exposure`
(declared exposure_classes + class_markers + money_value_rule +
window_rule + the_second_harvest + forbidden_vocabulary — NO INVENTED
MONEY in the bytes), `compare_terms_vs_finance_policy` (declared
comparison_axes + axis_markers; document-vs-document only),
`detect_missing_finance_evidence` (REFUSAL_BACKED; declared
requirement classes; the "did it happen?" half refused naming [OE]),
`prepare_cost_exposure_scenario` ([assist, synth]; the
estimate_label "[ESTIMATE, non-authoritative]" IN-UNIT — THE
LABELED-ESTIMATE discipline), `prepare_finance_evidence_pack`
(known/exposed/conflicting/estimated; absorbs the monthly exception
report as a declared section). The manifest carries the spine
verbatim, THE INVOICE-SENTENCE DISTINCTION, the SETTLED-ACCOUNT
forbidden_vocabulary, the named forbidden-input classes, and
the_unopened_ledger declaration.

**The promotion:** registry #2 → 5 ACTIVE / 14 CONSOLIDATED / 7
FUTURE ([ES]+the six [OE]); **the catalog's first two CROSS-WORKBENCH
consolidations** (`extract_payment_terms` → the v2.1 register;
`detect_outdated_finance_policies` → the shipped v1.7
`identify_outdated_policies`) — **the sweep's
basename(ratified_path)==consolidated_into assertion handles
cross-workbench targets unchanged** (it compares filenames, not
directories; both paths resolve; NO doctrine weakening was needed).
Global sweep constants re-pinned **29→34 ACTIVE / 44→58 CONSOLIDATED**
across the three pinning suites.

**THE PRECONDITION PROOF** (`backend/test_finance_corpus.py`, the
84th suite, six parts green): THE BUNDLE SHAPE (manifest + 5
contracts agree; **NO runner, NO UI, NO transactional door** — the
doors block and every allowed_inputs swept for transactional terms;
THE INVOICE PLANT declared); 15 documents (12 procurement UNTOUCHED +
3 corpus_finance) → 55 approved PRIMARY facts; THE EXPOSURE MATERIAL
REPORT (the contract's OWN parsed class_markers fire:
price_increase 7 / renewal_cost 10 / penalty_fee 2 / leakage 2; 5
currency + 5 percentage facts); THE POLICY-COMPARISON precondition
(both sides of every declared axis are approved facts); THE SECOND
HARVEST precondition (a dated register-class clause citable BY id;
the v2.1 taxonomy classifies it); THE UNOPENED LEDGER precondition
(the plant is ingested as a document but SEPARABLE — it carries
transactional-truth markers while ZERO approved facts carry any
SETTLED-ACCOUNT vocabulary, so the WS2 sweep has teeth; the two
cross-workbench consolidations resolve; global sweep 34/58; zero
stewardship events; D24 at exactly 28/305).

**Two honest WS1 fixes recorded:** the colocation plant's fee sentence
needed a trigger word in the dated/priced sentence (the recorded
extractor discipline), and the invoice-plant separability check moved
from fact-level to document-level + byte-level (the plant's
transactional sentences correctly do NOT extract — the pipeline
itself refuses non-obligation prose; the one "paid" fact is the
legitimate penalty CLAUSE "not paid by its due date", a conditional
term, which is exactly THE INVOICE-SENTENCE DISTINCTION working).

**Harness: 84/84 green (9:23).** NO runner, NO UI, NO PR. The
doctrine wording is intact: NO INVENTED MONEY, THE SETTLED ACCOUNT,
THE INVOICE-SENTENCE DISTINCTION, THE UNOPENED LEDGER.
