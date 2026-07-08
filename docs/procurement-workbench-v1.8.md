# v1.8.0 — The Procurement Document Intelligence Workbench — Build Contract

> Scoped 2026-07-07 (the v1.8 selection scoping session, post-v1.7.0
> release; baseline main `84c7207`, tags `v1.7.0` = `post-audit-hardening`
> = c2179c2, harness 68/68, D24 at 28 tables / 305 columns, route manifest
> 87 routes frozen). The THIRD commercial workbench (catalog #3), on the
> twice-proven template: scoping → contracts+corpus → corpus proof BEFORE
> any runner → runner → proposal valve → THE COMMERCIAL VERDICT. Gate
> records are appended to this document as each workstream closes.

## The milestone in one sentence

Renewals, clauses, and vendor obligations — **every number verbatim,
every window computed on the declared clock**: the workbench diagnoses
vendor contracts, renewal exposure, price-increase clauses, supplier
certification gaps, and vendor-vs-policy conflicts from governed
documents, and its findings become knowledge only as human-ACCEPTED
DERIVED facts, their derivation visible at the gate.

## The sensitivity posture (the cardinal sin)

**The invented number.** A hallucinated percentage, an extrapolated
spend figure, or a guessed date is the procurement analog of v1.7's
practice overclaim — it destroys the workbench's commercial credibility
in one finding. The workbench MAY quote clause numbers, percentages,
dates, notice periods, and money figures **only when verbatim present in
governed evidence**, and MAY compute date windows **only from
verbatim-extracted dates at the declared `as_of` clock**. It must NEVER:
estimate spend; infer market rates; convert paraphrased quantities into
numeric values ("one fifth" never becomes "20%"); round, extrapolate,
normalize, or invent figures; treat synthesis as governed numeric fact;
or guess unparseable dates (unparseable → refuse, declared). Impact
estimates in the assist brief are SYNTHESIS_INFERRED-declared, never
governed numbers. The manifest's `forbidden_vocabulary` sweeps
overclaim phrasing; the numeric discipline is enforced by THE CLAUSE
ARITHMETIC PROOF (below) over every finding byte.

## The opening question (evidence-first, per tradition)

"Which of our vendor contracts renews inside the next quarter, on what
terms, at what price movement — and can every number in that answer be
traced to the clause that says it?"

## Scoping rulings (proposed for ratification)

1. **THE ACTIVE SIX** (consolidations in the v1.7 style — each absorbs
   registry drafts without deleting meaning; absorbed drafts gain
   `consolidated_into` + `ratified_path`):
   - `extract_vendor_terms` [now] — EXCERPT_BACKED. Absorbs
     `extract_sla_obligations` + `identify_vendor_data_access_obligations`:
     all three are verbatim term extraction differing only by term class,
     so ONE contract with declared `term_classes` (sla, data_access,
     payment, notice, termination) preserves each draft's meaning as a
     declared class rather than a separate skill.
   - `detect_renewal_window` [now] — the distinctive skill. Absorbs
     `detect_expiring_contracts` + `detect_auto_renewal_clauses` +
     `identify_vendor_obligations_next_period`: all three are
     point-in-time window questions over explicit contract dates; ONE
     contract with a declared `window_days` parameter and an
     auto-renewal flag preserves all three as declared finding facets.
     Runs ONLY at the declared `as_of` (the v1.7 clock discipline).
   - `detect_price_increase_clauses` [now] — EXCERPT_BACKED; the
     percentage/amount quoted verbatim with its clause citation.
   - `identify_missing_supplier_certifications` [now] — REFUSAL_BACKED;
     the v1.7 missing-evidence pattern near-verbatim (declared
     requirement classes; covered control → NO finding).
   - `detect_vendor_policy_conflict` [now] — CONFLICT_BACKED. Absorbs
     `compare_vendor_terms_vs_procurement_policy` +
     `detect_vendor_contract_vs_policy_conflict`: both compare vendor
     terms against the named procurement policy; ONE contract carrying
     BOTH evidence routes — the governed CONFLICTS_WITH relationship
     (v1.6 rules inherited wholesale) AND the new declared
     doc-vs-named-policy rule (ruling 6).
   - `prepare_renegotiation_brief` [assist, synth] — the four-section
     posture pack (known / expiring-or-moving / missing / unverified),
     never a proposal, never enters knowledge.

2. **THE GATED LIST, refused live naming the unminted decision**:
   - **[OE]**: invoice/PO/payment reconciliation, supplier performance,
     spend inference, operational execution, usage-vs-license — the four
     registry [OE] drafts and every transaction-shaped question.
   - **[ES]**: `identify_owner_gaps` — owner assignment, routing,
     stewardship (detection-of-undocumented-owner was ratified at v1.7
     for compliance; procurement's owner skill stays gated until [ES]).

3. **SEQUENCED (deferred, not gated)**: `detect_single_supplier_dependency`
   and `propose_vendor_consolidation` — both need cross-document
   counting/aggregation evidence rules beyond this milestone's scope; a
   dependency claim built on incomplete corpus coverage is a silent
   overclaim. They stay SEQUENCED in the registry, refused at runtime by
   status (tags are gates).

4. **THE CALENDAR REFUSAL (the v1.7 deadline ruling, re-affirmed)**: a
   persistent renewal calendar or recurrence tracker remains refused —
   the two-state-machine drift D1 names. Only point-in-time window
   detection at the declared `as_of` is allowed; the finding records
   `as_of`, the verbatim date, and the computed window verdict, and a
   re-run at a different declared `as_of` is a NEW diagnosis, never an
   update.

5. **THE CLAUSE ARITHMETIC PROOF (the distinctive v1.8 proof — a named
   WS3 stage, with its preconditions proven at WS1)**: every monetary
   figure, percentage, notice period, and date in every finding is
   traceable to a verbatim excerpt with a governed asset citation; the
   ONLY computed values anywhere are deterministic date-window
   calculations over verbatim-extracted dates at the declared `as_of`.
   The proof must include: the byte-identical rerun check; the
   paraphrase-trap plant ("increases by one fifth" quoted as text,
   never becoming "20%"); the unparseable-date refusal (declared, never
   guessed); covered-control silence (a contract outside the window, a
   certification that exists, a conforming policy); policy-conflict
   positive AND negative controls; no canonical writes (Guard 5); no
   Contract Intelligence shared fact store (extractions are candidates
   for THIS workbench's gate only); no pending-proposal or ungated
   material consumed.

6. **THE DOC-VS-NAMED-POLICY RULE (the one new evidence rule)**: a
   vendor-policy conflict finding may cite the named procurement policy
   as one side explicitly (the contract clause vs the policy clause,
   both verbatim, cross-document) — either via a governed CONFLICTS_WITH
   relationship (v1.6 rules wholesale: same-subject ≥2 tokens,
   cross-document, governance vocabulary excluded) or via the declared
   policy comparison route stated in the contract. Pairs failing the
   rules are deferred to the governance conflict review, declared.

7. **THE CORPUS (~12 knowledge-only documents, domain `procurement`)** —
   designed here, implemented at WS1. Required plants:
   | # | Plant | Detected by |
   |---|---|---|
   | P1 | Renewal window POSITIVE: explicit end date inside `window_days` of the pinned `as_of` | `detect_renewal_window` |
   | P1c | Renewal window NEGATIVE: explicit end date outside the window — NO finding | covered control |
   | P2 | Auto-renewal clause (explicit notice period, verbatim) | `detect_renewal_window` (facet) |
   | P3 | Price-increase clause with explicit percentage ("increases by 7% annually") | `detect_price_increase_clauses` |
   | P3t | THE PARAPHRASE TRAP: "increases by one fifth" — quoted as text, never converted | THE CLAUSE ARITHMETIC PROOF |
   | P4 | Missing supplier certification (requirement present, certificate absent) | `identify_missing_supplier_certifications` |
   | P4c | COVERED certification (requirement + the approved certificate document) — NO finding | covered control |
   | P5 | Vendor-terms-vs-procurement-policy conflict (e.g., payment terms 90 days vs policy max 45) | `detect_vendor_policy_conflict` |
   | P5c | Conforming vendor terms — NO finding | covered control |
   | P6 | UNPARSEABLE DATE: "renews at the start of the fiscal year" — refused, declared | the refusal proof |
   | P7 | EXECUTIVE sentinel document (new sentinel string) | the clearance sweep |
   | P8 | The noisy contract: irrelevant numbers (addresses, phone numbers, clause indices) that must never be promoted into findings | THE CLAUSE ARITHMETIC PROOF |
   Plant map (`CORPUS.md`) outside the scanned folder, per the standing
   protected boundary. Pinned `as_of` and `window_days` declared in the
   suites.

8. **INHERITED WHOLESALE (no re-litigation)**: the v1.6 same-subject/
   cross-document conflict evidence rules; the v1.7 missing-evidence,
   declared-clock, proposal-flow, acceptance-as-DERIVED, composition,
   vault-render, browser-proof, and ledger closing-line machinery;
   `workbench/common.py` unchanged (zero shared-module edits expected —
   recorded at the WS2 gate as industrialization evidence).

9. **GENUINELY NEW (the complete list)**: the clause/date/number
   extraction discipline (declared clause patterns + date formats in the
   contracts; refuse unparseable); deterministic date-window arithmetic
   at declared `as_of`; the doc-vs-named-policy rule (ruling 6); the
   numeric posture sweep (no digit in a finding without a verbatim
   source span). Nothing else is new.

10. **Zero schema. Zero backend change. Zero new endpoints, MCP tools,
    or UI areas.** The D24 snapshot holds at **28 tables / 305 columns**
    (verified against the current repo baseline), asserted at the
    milestone gate. No D32; no seventh guard family — Guard 5 sweeps the
    new bundle the moment it lands.

11. **THE COMMERCIAL VERDICT is user-ratified, not automated** — the
    reader is the procurement/finance owner: *"As a procurement or
    finance owner: is every finding accurate, money-relevant, and
    actionable this quarter — with every number and date traceable
    verbatim to a governed clause — such that you would put the
    renegotiation brief in front of your CFO?"*

12. **Model routing (recorded)**: WS0/WS1/WS3 → Fable; WS2 → Opus 4.8
    after ratification, escalating to Fable if DERIVED/canonical
    separation, evidence rules, numeric/date fidelity, or verdict
    framing becomes subtle; release/CI/tag/docs → Sonnet 5 at clean
    mechanical boundaries only.

13. **The honest slots carry**: the real-model diagnostic run (no
    provider key; the renegotiation brief joins the compliance pack as a
    natural vehicle) and the v1.2.0 live-SharePoint scan.

## Registry handling

`docs/workbench-skill-registry.md` (839 lines at main) does NOT yet
contain the scoped-roadmap layer produced at the selection session — it
is added as a docs-only change in the SAME scoping commit as this
contract (the ratification commit), together with the v1.8 consolidation
annotations (`consolidated_into` / `ratified_path` on the absorbed
drafts) at WS1 when the contracts are promoted.

## Workstreams

### WS0 — The rulings (no code) — THIS DOCUMENT
**Gate:** user ratification of rulings 1–13; all 68 suites standing as
released; D24 at 28/305. On ratification: branch created, this contract
+ the registry roadmap layer committed as the scoping commit.

### WS1 — The contracts + the corpus + THE CORPUS PROOF
The six contracts promoted (13-field shape; absorbed drafts annotated);
the ~12-document corpus per ruling 7; `test_procurement_corpus.py`
proving BEFORE any runner: clause/date/percentage extraction
preconditions on governed content; the window arithmetic derivable from
verbatim dates at the pinned `as_of` (P1/P1c both directions); the
paraphrase trap present and non-numeric; consume() refusals AND covered
answers (P4/P4c); the P5 conflict detectable (real-NLI gate-evidence
mode / declared fixture); the unparseable-date refusal; the
draft≠ratified sweep. **Gate:** evidence recorded; user ratifies corpus
+ contracts.

### WS2 — The runner + THE DIAGNOSIS PROOF
The runner on `workbench/common.py` (zero shared-module edits expected —
recorded); contracts drive runtime (term classes, window_days, clause
patterns, date formats, policy-comparison rule all PARSED from the
YAMLs); `test_procurement_workbench.py`: every plant found and kinded;
covered controls silent, declared; the noisy contract's numbers never
promoted; gated/[OE]/[ES]/SEQUENCED refusals live; numeric posture on
every written byte; byte-identical at pinned `as_of`; sentinel absent;
the return path holds everything DERIVED. **Gate:** user ratifies the
runner.

### WS3 — THE MILESTONE GATE + THE CLAUSE ARITHMETIC PROOF + THE COMMERCIAL VERDICT
`test_procurement_acceptance.py`: the full commercial loop (corpus →
human approval into `procurement` → INTERNAL package + binding →
diagnosis at declared `as_of` → valve holds under permissive Tier-1 +
live Tier-2 → human accepts per kind → verified provenance) + **THE
CLAUSE ARITHMETIC PROOF** as a named stage (ruling 5, all eight checks)
+ the composition re-run (an accepted vendor-term DERIVED fact consumed
by a second window/certification pass, DERIVED cited as DERIVED — the
v1.7 machinery, now standing) + the vault before/after + the in-browser
before/after + closing lines (ledger proves no agent wrote canonical
facts; sentinel absent; D24 at exactly 28/305). **Plus THE COMMERCIAL
VERDICT** (ruling 11). **Plus the honest slots** per ruling 13.

## Explicitly out of scope (refused deliberately, not omitted)

Invoice/PO/payment/transaction analysis and supplier performance ([OE],
named at refusal); owner assignment/stewardship ([ES]); persistent
renewal calendars and recurrence tracking (ruling 4); vendor
consolidation and single-supplier dependency (SEQUENCED, ruling 3);
Contract Intelligence as a shared engine (earnable AFTER v1.8 — its own
scoping; nothing here builds a shared fact store); spend/market
estimation of any kind (the cardinal sin).

## Standing boundaries

D22 (EM never launches agents); D29/D30 (valve + class); D31 (render
ingress); Guard 5 sweeps `workbench/procurement_intelligence/` the
moment it exists; corpus plant map ≠ runtime evidence; runner output ≠
canonical knowledge; drafts ≠ ratified contracts.

## Gate records

*(appended as workstreams close; WS0 ratification pending)*

### WS0 — SCOPING RATIFICATION: PASSED (2026-07-07, user-ratified)

Ratified verbatim: rulings 1–13 — the ACTIVE SIX with their
consolidations; cardinal sin THE INVENTED NUMBER; distinctive proof
THE CLAUSE ARITHMETIC PROOF; allowed computation = only deterministic
date-window arithmetic over verbatim-extracted dates at declared
as_of; refused/gated = [OE] transactional/payment/spend/PO/invoice/
supplier-performance inference, [ES] owner assignment/gaps/routing/
stewardship, the persistent renewal calendar, and every inferred/
converted/rounded/estimated number; SEQUENCED = single-supplier
dependency + vendor consolidation; zero schema / zero backend change /
zero new doors, D24 at 28/305. Sequence: this scoping commit → WS1
(contracts + corpus + THE CORPUS PROOF, on Fable). Baseline at
ratification: main 84c7207, tags v1.7.0 = post-audit-hardening =
c2179c2, harness 68/68.

**Verdict: v1.8.0 WS0 PASSED.** WS1 may proceed.

### WS1 — The Contracts, the Corpus, and THE CORPUS PROOF: evidence recorded, gate pending ratification (2026-07-07)

Delivered: the SIX ratified 13-field contracts in
`workbench/procurement_intelligence/skills/` (consolidations per
ruling 1, never silent: extract_vendor_terms absorbs the SLA +
data-access drafts as declared term_classes; detect_renewal_window
absorbs expiring + auto-renewal + next-period as declared window
facets at the declared as_of; detect_vendor_policy_conflict absorbs
both policy-comparison drafts with the dual evidence routes); the
manifest (`workbench.yaml`: canonical #3, THE INVENTED NUMBER posture,
the numeric-overclaim forbidden_vocabulary, the declared clock, the
gated/SEQUENCED lists); the 12-document corpus with `CORPUS.md`
outside the scanned folder; the registry promotion (17 ACTIVE / 13
CONSOLIDATED globally, every ratified_path resolving; two
consolidation-target drafts added; the deferred deadline family
untouched).

**THE CORPUS PROOF** (`backend/test_procurement_corpus.py`, the 69th
suite — all seven parts green, before any runner exists):
1. 12 documents through the real pipeline; every plant sentence in
   governed content.
2. THE CLAUSE ARITHMETIC preconditions: the declared date marker
   extracts exactly the two dated termination clauses; window
   arithmetic at the pinned as_of 2026-06-01 (+90d) verdicts P1 IN
   (2026-08-15) and P1c OUT (2027-09-30); the P6 renewal-context
   sentence has no parseable date (the refusal precondition); the
   paraphrase-trap sentence carries no digit and no percent token and
   "20%" appears nowhere in governed content; the noisy-number
   sentences match no extraction marker.
3. The declared term classes (sla / data_access) and the verbatim P3
   percentage reproduce the plant-map expectations.
4. The P5 payment-terms pair passes the inherited same-subject +
   cross-document rules (real-NLI detection = the gate-evidence run
   under EM_CORPUS_PROOF_NLI=1; declared fixture in bare CI); the
   compile gate blocks then opens by governed human review; the
   INTERNAL package excludes the EXECUTIVE sentinel
   (EM-EXEC-SENTINEL-4V8P).
5. consume() reproducibly REFUSES the DataFlow certificate question
   and ANSWERS the SecureStore one with supplier-named cited evidence
   — SUPPLIER-NAMED COVERAGE recorded in the ratified contract during
   this workstream (an evidence-rule refinement, the v1.6 precedent:
   another supplier's certificate is never evidence).
6. Six 13-field contracts match the manifest; the declared conventions
   live in the contract bytes; the draft≠ratified sweep holds at 17
   ACTIVE / 13 CONSOLIDATED with consolidation never silent.
7. Zero schema: D24 at exactly 28 tables / 305 columns.

**One recorded assertion edit** (the v1.7 precedent, driven by the
ratified promotion): `test_compliance_corpus.py`'s global sweep
constants moved 11→17 ACTIVE and 8→13 CONSOLIDATED. Both prior corpus
proofs re-run green. **One corpus-authoring note**: plant sentences
carry honest extraction-trigger vocabulary (must/required/agreement/
policy) so the rule-based extractor lifts them into governed content —
phrasing only; every plant's meaning unchanged.

**Regression at the gate**: full harness 69/69 green (~4m55s);
Guard 5 unchanged (no new .py under workbench/ this workstream); the
v1.6 and v1.7 corpus proofs green.

**THE GATE (per WS0): user ratification of the corpus as realistic and
the six contracts as the declared product is now requested. WS2 (the
runner, on Opus per the recorded routing) starts only on ratification.**

### WS2 — The Runner + THE DIAGNOSIS PROOF: evidence recorded, gate pending ratification (2026-07-07)

Delivered: `workbench/procurement_intelligence/runner.py` on
`workbench/common.py` (relative import; **zero shared-module edits** —
common.py untouched this milestone, the industrialization evidence).
The six contracts DRIVE runtime: explicit markers + term_class_rules,
the date_convention marker_pattern + auto_renewal + renewal_context
markers, the increase markers, the certification requirement + question
template, the named policy, and the forbidden vocabulary are all PARSED
from the ratified YAMLs. Refusal-first both ways; the declared clock
(as_of + window_days required, else refuse); the gated list refused
live naming the decision; the persistent-calendar refusal (ruling 4);
the numeric posture enforced at the source.

**THE DIAGNOSIS PROOF** (`backend/test_procurement_workbench.py`, the
70th suite — six parts green; full harness 70/70):
1. Guard 5 sweeps 6 workbench modules, zero guard edits.
2. 11 per-finding proposals across all five finding kinds,
   byte-identical re-runs at the pinned as_of 2026-06-01 / +90d;
   writes confined to /08_proposals + one renegotiation brief; the
   EXECUTIVE sentinel, the manifest's forbidden vocabulary, the string
   "20%", and every noisy irrelevant number (address / phone /
   clause-index / PO range) absent from every written byte.
3. THE CLAUSE ARITHMETIC held: P1 renewal window (days-until 75, the
   sole computed value) with the P2 auto-renewal 60-day facet; P1c
   out-of-window and P6 unparseable-date both silent/declared; P3
   explicit 7% numeric vs P3t "one fifth" flagged non_numeric with no
   digit in the excerpt; P4 DataFlow missing vs P4c SecureStore covered
   (SUPPLIER-NAMED coverage); P5 conflict named against the Procurement
   Policy; vendor terms carry declared classes.
4. Contracts drive behavior: no-as_of / no-window /
   persistent-calendar / [OE] / [ES] / SEQUENCED / non-ACTIVE all
   refused live.
5. The return path holds all 11 proposals as DERIVED candidates under
   a live permissive policy, provenance verified against the binding.

**ONE RECORDED EVIDENCE-RULE REFINEMENT (surfaced by the noise plant,
the v1.6 signal-to-noise precedent — flagged for the gate):** the
inherited v1.6 same-subject rule excludes timeframe + governance
vocabulary but NOT generic legal boilerplate ("agreement", "clause",
"party", "this", "date"), which is shared across ALL vendor contracts
and let a cross-topic pair (a renewal date vs a price clause) share 3
tokens and slip the rule. Fix: a DECLARED `subject_boilerplate_stopwords`
list in `detect_vendor_policy_conflict.yaml`, applied in the conflict
walk IN ADDITION to the inherited exclusions — recorded in the contract,
never silent. Proof it separates signal from noise: the real P5 payment
conflict keeps 3 real shared tokens (date/invoice/payment) and fires;
the noise pair drops to 1 (date) and is deferred, declared. This is the
procurement analog of the v1.6 "an important commercial finding, not a
failure" recorded refinement.

**Regression at the gate**: full harness 70/70 green; Guard 5 green
(swept the runner with zero edits); D24 held at 28/305 (asserted in the
WS1 corpus proof; unchanged).

**THE GATE (per WS0): user ratification of the runner as the accepted
Procurement workbench is now requested. WS3 (the milestone gate + THE
CLAUSE ARITHMETIC PROOF stage + the commercial verdict) starts only on
ratification.**

### WS3 — THE MILESTONE GATE + THE CLAUSE ARITHMETIC PROOF: evidence recorded, THE COMMERCIAL VERDICT pending (2026-07-07)

`backend/test_procurement_acceptance.py` (the 71st suite) — nine
stages, all green; full harness 71/71:

1–2. The 12-document corpus through the real pipeline (36 PRIMARY
facts human-approved into the `procurement` domain, the EXECUTIVE memo
seeded above package clearance); INTERNAL package + real AGENT binding.
3–4. THE DIAGNOSIS through the doors at the declared clock (11
proposals, all five kinds); the valve holding 66 candidates DERIVED
under a global permissive Tier-1 policy AND a live approve-everything
Tier-2 engine.
5. A human accepts one finding per kind — 5 APPROVED DERIVED facts,
every approval event quoting VERIFIED synthesis provenance.
6. **THE CLAUSE ARITHMETIC PROOF (the distinctive v1.8 stage): 13
numbers across every Finding statement, each traceable to a
verbatim-cited clause or the declared clock arithmetic** (citation ids
excluded as governed identifiers); "one fifth" stayed text with no
digit; "20%" in no written byte; the unparseable date refused,
declared; the noisy numbers in no proposal; window positive (days-until
75) and negative both correct with the auto-renewal 60-day facet;
supplier-named certification coverage (DataFlow missing / SecureStore
covered); the vendor-policy conflict both directions; NO calendar
artifact anywhere + the persistent-calendar request refused live;
[OE]/[ES]/SEQUENCED refused live naming the decision.
7. Composition standing: the 5 accepted DERIVED facts traveled into
the recompiled package (pending proposals structurally absent); 5
second-generation findings cite DERIVED evidence, flagged [DERIVED] in
the proposal bytes.
8. The vault before/after: all 5 accepted findings as marked DERIVED
notes, visibly non-canonical; the untouchable floor held.
9. THE CLOSING LINES: every approval event non-AGENT; every APPROVED
DERIVED fact human-reviewed; 85 files sentinel-clean; **D24 at exactly
28 tables / 305 columns**.

**The in-browser before/after (recorded 2026-07-07): PASSED.** Seeded
throwaway DB (the `.ui-gate-db` pattern, this branch's code, seed_v18):
login as a governed GOVERNANCE_REVIEWER; Operations BEFORE — 11
proposals, 66 held DERIVED, 0 accepted; ONE live **Accept as DERIVED**
(the pre-existing review PATCH) → AFTER — 65 held, **1 accepted
DERIVED**; zero console errors/warnings; the only non-2xx request is
the pre-login session-restore probe (401 by design — the login gate).

**The honest slots carry:** the ONE real-model diagnostic run (PENDING,
no provider key; the renegotiation brief is this workbench's natural
vehicle) and the v1.2.0 live-SharePoint scan.

**THE GATE: THE COMMERCIAL VERDICT (ruling 11) — the user reads the
exported diagnosis as the procurement/finance owner. The milestone
closes on that verdict or it does not close.**
