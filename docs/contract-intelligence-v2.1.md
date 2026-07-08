# v2.1.0 — The Contract Intelligence Workbench — Build Contract (the shared engine)

> Scoped 2026-07-08 (post-v2.0.0; baseline main `59444ed`, tag `v2.0.0`
> = `caa6d73`, harness 77/77, D24 at 28 tables / 305 columns, route
> manifest 88 routes frozen at digest `d8d4eaa5…`, MCP frozen at 9
> tools, seven permanent guard families). Catalog #16, the FOURTH
> commercial workbench — **earned, not anticipated**: two consumer
> workbenches exist (Compliance v1.7, Procurement v1.8), which is what
> the registry's `[next]` marker demanded. The scoping goal, ruled at
> the session that opened it: **harvest governed knowledge already
> present; mint no new realm; expand no constitutional surface unless
> a proof shows the existing laws are insufficient.** Gate records are
> appended as each workstream closes.

## The milestone in one sentence

One extraction engine turns contracts the governed pipeline already
holds into a **clause register** — verbatim, class-declared,
human-accepted DERIVED facts — that the EXISTING consumer workbenches
cite as evidence through the valve, proving one extraction can feed
many readers with zero drift and no shared fact store.

## The sensitivity posture (the cardinal sin)

**THE PARAPHRASED CLAUSE.** A shared engine amplifies its own errors:
a clause fact that re-words the contract poisons every downstream
consumer at once — procurement renegotiates on it, compliance attests
on it, the briefing repeats it. Every clause fact's statement is the
VERBATIM excerpt; parties, dates, amounts, percentages, and notice
periods appear exactly as the contract wrote them (THE INVENTED
NUMBER posture inherited whole from v1.8); the extraction adds ONLY
declared structure (clause_class, contract, party labels quoted from
the text). Its twin: **THE LEGAL CONCLUSION** — the engine states what
the contract SAYS, never what is legally true, enforceable, or
advisable. Forbidden vocabulary (swept over every written byte):
"is enforceable", "is unenforceable", "is legally binding", "is void",
"breaches", "violates the law", "you should sign", "you should
terminate", "we recommend accepting", "legal advice", "this clause is
valid", "this clause is invalid".

## The opening question (evidence-first, per tradition)

"Can one governed clause register — every clause verbatim, every gap
declared — become the single upstream source that procurement and
compliance reviews BOTH cite, provably the same fact under both
readers, without building any new door, table, or law?"

## What exists today (the grounding, verified)

- v1.8 already ships contract detection for its OWN reader:
  `extract_vendor_terms`, `detect_renewal_window`,
  `detect_price_increase_clauses`, `detect_vendor_policy_conflict` —
  registry #16 items 21–23 live THERE. v1.7 ships
  `extract_compliance_obligations`. #16 must not re-claim them.
- The composition machinery is proven three ways: within one workbench
  (v1.7 THE COMPOSITION PROOF), self-consuming (v1.9 the briefing
  citing its own accepted gap), and the class/origin conventions
  travel everywhere (D30; the v1.9 `provenance.source_document` origin
  derivation). **What has never been proven: workbench A's accepted
  facts cited by workbenches B and C — the cross-workbench feed.**
  That is this milestone's distinctive turn.
- The registry's own closing note on #16 already rules the
  architecture: *"Cross-workbench feeding stays behind the valve: an
  extraction skill's output is a candidate for the consuming
  workbench's human gate, never a shared internal fact store."*
- The procurement corpus (12 documents) IS a contract corpus; the
  compliance corpus holds the DPA template. The fixture exists.

## Scoping rulings (proposed for ratification)

1. **THE ACTIVE SET (consolidations in the standing style; absorbed
   drafts gain `consolidated_into` + `ratified_path`):**
   - `extract_contract_clauses` [now] — THE ENGINE: consolidates
     registry subtasks 2–16 (parties / effective_date / expiry_date /
     renewal / termination / payment / sla / reporting_obligation /
     certification_obligation / notification_obligation / data_access
     / confidentiality / liability_indemnity / audit_rights /
     approval_requirements) as declared `clause_class` values with
     marker rules PARSED from the contract YAML — the v1.7
     `obligation_type` / v1.8 `term_class` precedent, applied at full
     width. One CONTRACT_CLAUSE finding per detected clause,
     EXCERPT_BACKED, one proposal per finding to /08_proposals.
   - `detect_missing_contract_metadata` [now] — the missing-evidence
     pattern per contract: a declared REQUIRED metadata set (parties;
     an effective or expiry date; payment terms) with no detectable
     clause produces one CONTRACT_METADATA_GAP finding — absence
     declared per contract, never guessed, never a fact about the
     world. ABSENCE_BACKED (the declared basis; the v1.7
     missing-evidence lineage).
   - `prepare_contract_review_brief` [assist] — consolidates
     `summarize_contract` (1) + `prepare_contract_review_brief` (25):
     the per-contract assist brief composed from accepted facts,
     written to /07_agent_workspaces, never a proposal, never
     knowledge (the v1.8 renegotiation-brief shape).
   - **The feeder subtasks 28–30 are not runtime skills — they are
     the milestone itself**: consolidated into
     `extract_contract_clauses`, whose accepted output IS the
     candidate every consuming workbench's gate receives. Feeding is
     structural (governed facts in packages), never an API between
     runners.

2. **Cross-workbench consolidations, recorded not re-claimed**:
   registry items 21 (`compare_vendor_contract_vs_procurement_policy`),
   22 (`detect_auto_renewal_risk`), 23 (`detect_price_increase_risk`)
   are CONSOLIDATED → the shipped v1.8 procurement contracts (the
   skill lives where its reader lives); their drafts annotate
   accordingly. Item 24 (`detect_contract_owner_gaps`) stays **[ES]
   per-workbench gated** exactly as D32's minting ruled.

3. **SEQUENCED (deferred, not gated)**: the compare family 19–20
   (contract-vs-policy generalization — v1.8 already covers the
   commercial case; a general comparison engine deserves its own
   evidence rule); `detect_conflicting_contract_clauses` (18 — the
   platform NLI conflict engine owns cross-asset contradiction;
   same-contract clause conflict needs its own ruling);
   `prepare_renewal_decision_brief` (26) and `prepare_negotiation_points`
   (27, [synth] — negotiation synthesis is a posture question of its
   own).

4. **THE REGISTER DISTINCTION (a genuine ruling — reconciling with
   v1.9's restatement refusal):** v1.9 ruled that read-compose
   SUMMARIES never re-enter knowledge (circular derivation). A clause
   fact is NOT that: it is a verbatim excerpt plus declared structure
   (clause_class, contract, party), citing its PRIMARY source, entering
   ONLY through the valve as a human-accepted DERIVED fact — the
   structured, citable, class-visible register entry that IS this
   workbench's product. The distinction, ruled: **narrative synthesis
   of accepted facts may never become a fact; verbatim structure
   extraction may — through the valve, with the source cited.**
   Tradeoff accepted openly: an accepted clause fact textually
   overlaps its PRIMARY source; the register is deliberate structured
   restatement THROUGH the human gate, and D30 keeps the derivation
   visible forever.

5. **THE SHARED ENGINE PROOF (the distinctive proof — a named WS3
   stage, preconditions at WS1):**
   - **one extraction contract**: every clause class detected by ONE
     ratified skill contract driving the runner at runtime;
   - **two consumers, UNCHANGED**: the v1.7 compliance runner and the
     v1.8 procurement runner — with ZERO edits to either — each
     produce at least one finding citing a #16 accepted clause fact
     AS DERIVED (`[DERIVED]` flagged in proposal bytes, origin
     `contract-intelligence` derivable via the v1.9 filename
     convention) after the register enters the recompiled package;
   - **zero drift, defined on ids not strings**: for a shared clause
     (the payment-terms clause of one contract), the compliance-side
     citation and the procurement-side citation resolve to the SAME
     governed asset id — the register entry — and get_provenance
     walks both to the same source document;
   - **no shared fact store**: D24 byte-identical at 28/305; the
     runners share no imports beyond `workbench/common.py` (Guard 5's
     sweep); deleting every #16 workspace artifact changes neither
     consumer's behavior — the feed lives in governed facts alone;
   - the sentinel disciplines inherited: a held (never-accepted)
     clause proposal appears in NO package byte and NO consumer
     finding; the EXECUTIVE sentinels appear in no written byte.

6. **The fixture: no corpus of its own.** The clause register is
   proven over the EXISTING procurement corpus (the contract set) plus
   the compliance DPA in one project — the v1.9 cross-workbench
   fixture pattern, now pointed at the harvest claim. If extraction
   preconditions demand a plant no existing document carries, the
   ruling is to ADD one document to the #16 fixture flow via a
   fixture-local file, never to edit a shipped corpus (shipped corpora
   are v1.7/v1.8 gate evidence).

7. **Zero new surface, zero new law — asserted, not assumed.** No new
   route (manifest stays 88 at digest `d8d4eaa5…`), no new table or
   column (D24 at 28/305), no new event type, no new MCP tool (9), no
   new UI area (D8), no eighth guard family (Guard 5 sweeps
   `workbench/contract_intelligence/` the moment it lands; the valve,
   class, origin, and register seams are D29/D30/D32 + standing
   guards), **no D33** — the milestone's thesis is that the laws
   already paid for are sufficient, and THE SHARED ENGINE PROOF is the
   evidence. If any WS gate finds a genuine new seam, the milestone
   PAUSES for its own scoping ruling rather than quietly minting.
   `workbench/common.py` expected unchanged (fourth reuse).
   **[OE] and [PMD] remain explicitly unminted** — pricing-vs-invoice
   verification (the registry's #16 v2 column) stays behind [OE];
   agent visibility of pipeline state stays behind [PMD].

8. **Model routing (recorded)**: WS0/WS1/WS3 → Fable; WS2 → Opus 4.8
   after ratification; release choreography → Sonnet 5.

9. **THE COMMERCIAL VERDICT (user-ratified, never automated)** — the
   reader is GENERAL COUNSEL / the procurement owner: *"As general
   counsel: would you let this clause register be the single upstream
   source your procurement and compliance reviews both cite — every
   clause verbatim, every gap declared per contract, and provably the
   same governed fact under both readers?"*

10. **The honest slots carry**: the ONE real-model diagnostic run (a
    narrated clause extraction over a real contract is a strong
    vehicle when a key exists) and the v1.2.0 live-SharePoint scan.

## The nine scoping questions, answered

1. **First commercial jobs**: the clause register (15 clause classes,
   one skill), per-contract metadata-gap detection, the contract
   review brief. Nothing else in v1.
2. **Reads**: the `.empkg` at binding clearance + the 9 frozen MCP
   tools — the same doors as every workbench. Nothing new.
3. **Derived outputs**: CONTRACT_CLAUSE and CONTRACT_METADATA_GAP
   proposals; accepted → DERIVED register entries with origin
   `contract-intelligence`. The brief is assist-only.
4. **Non-authoritative, permanently**: every proposal until the human
   gate; the brief; every register entry visibly DERIVED and
   non-canonical wherever it travels (D30).
5. **Evidence per answer**: the verbatim excerpt + the cited PRIMARY
   asset id on every clause; the declared required-metadata set on
   every gap; numbers and dates verbatim or absent.
6. **Human review**: everything, through the one valve (D29) — no new
   review species.
7. **New route/table/event/projection**: NONE. Projections and views
   already carry DERIVED class and origin.
8. **New guard family**: NO — and ruling 7 makes the pause-don't-mint
   fallback explicit.
9. **Smallest sequence**: four workstreams, three suites (CI 77→80),
   one bundle directory, zero platform edits.

## Module map (planned)

| Location | Role |
|---|---|
| `workbench/contract_intelligence/workbench.yaml` | canonical #16, THE PARAPHRASED CLAUSE posture + the legal-conclusion forbidden vocabulary, the clause_class taxonomy, the required-metadata set, the SEQUENCED/gated lists |
| `workbench/contract_intelligence/skills/*.yaml` | the three ratified 13-field contracts |
| `workbench/contract_intelligence/runner.py` | on common.py (zero shared-module edits expected, fourth reuse); clause classes/markers/required-metadata PARSED from the YAMLs; declared as_of clock; one proposal per finding |
| *(no corpus/ directory)* | ruling 6 — the fixture is the existing procurement corpus + the compliance DPA |
| `backend/test_contract_corpus.py` (WS1) | THE EXTRACTION PRECONDITION PROOF (every clause class detectable in approved facts before any runner; the consumer-marker precondition: accepted register text still triggers the UNCHANGED v1.7/v1.8 detectors; the draft≠ratified sweep constants move) |
| `backend/test_contract_workbench.py` (WS2) | THE DIAGNOSIS PROOF |
| `backend/test_contract_acceptance.py` (WS3) | THE MILESTONE GATE + THE SHARED ENGINE PROOF |

CI grows 77 → 80 suites. No changes under `backend/app/`. Route
manifest stays 88; MCP stays 9; D24 stays 28/305.

## Workstreams

**WS0 — this document.** Gate: user ratification of rulings 1–10;
77/77 standing. On ratification: this contract committed as the
scoping commit on `feat/v21-contract-intelligence`.

**WS1 — the contracts + the registry promotion + THE EXTRACTION
PRECONDITION PROOF** (the 15-class consolidation recorded, never
silent; the sweep constants move from 23/18 with exact counts recorded
at this gate; the consumer-marker precondition proven BEFORE any
runner — if an accepted register entry's verbatim text would NOT
trigger the unchanged consumer detectors, that is discovered here, not
at WS3). Gate: user ratifies the contracts and the precondition
evidence.

**WS2 — the runner + THE DIAGNOSIS PROOF** (Opus; contracts drive
runtime; the posture enforced pre-write; byte-identical at the
declared clock; gated/SEQUENCED refused live naming the ruling). Gate:
user ratifies the runner.

**WS3 — THE MILESTONE GATE + THE SHARED ENGINE PROOF + THE COMMERCIAL
VERDICT** (the in-browser before/after per the standing pattern;
release closeout: tag v2.1.0, PROJECT_STATE/roadmap regen).

## Explicitly out of scope (refused deliberately, not omitted)

Pricing-vs-invoice or spend verification ([OE], unminted); agent
visibility of pipeline state ([PMD], unminted); contract owner
assignment ([ES] per-workbench, gated); the general contract-vs-policy
comparison engine (sequenced — v1.8 owns the commercial case); clause
conflict detection (sequenced); negotiation synthesis (sequenced,
[synth]); legal conclusions of any kind (the twin sin); a clause
REGISTER TABLE or any persisted register view (the register IS
accepted DERIVED facts in the knowledge system — D1/D24/D32's lesson
applied); new corpora, routes, tables, events, tools, UI areas, guards,
or D-numbers.

## Gate records

*(appended as workstreams close)*

### WS0 — SCOPING RATIFICATION: PASSED (2026-07-08, user-ratified)

Ratified verbatim: rulings 1–10, with both consequential calls ruled
explicitly:
- **Ruling 1 (the 15→1 consolidation width): RATIFIED** — "the
  milestone's claim is the shared clause register, not fifteen
  separate micro-skills … as long as the class vocabulary is
  closed/pinned and every extracted item is verbatim + cited."
- **Ruling 4 (THE REGISTER DISTINCTION): RATIFIED** — "this does not
  violate v1.9's restatement refusal. v1.9 refused narrative synthesis
  becoming fact. v2.1 allows verbatim structure extraction through the
  valve. That distinction is clean, necessary, and testable."

The load-bearing principle, ruled at the gate (user, verbatim): **"A
clause register may become governed derived structure only when it is
verbatim, source-cited, valve-approved, and non-advisory. A contract
brief may synthesize for a reader, but that synthesis never becomes a
fact."**

The boundaries, fixed for the whole milestone: no new law; no D33; no
[OE]; no [PMD]; no new table; no new route; no new MCP tool; no eighth
guard family; route manifest stays 88; D24 stays 28/305; MCP stays 9;
Contract Intelligence must harvest governed knowledge already earned;
a genuine new seam PAUSES the milestone for its own ruling, never a
quiet mint. No new corpus unless WS1 proves the existing
procurement/compliance fixtures insufficient — in which case the
limitation is surfaced, not papered over.

Sequence: this scoping commit → WS1 on Fable (the three contracts, the
registry promotion, the pinned clause_class vocabulary, the forbidden
vocabulary, THE EXTRACTION PRECONDITION PROOF — no runner in WS1).

**Verdict: v2.1.0 WS0 PASSED.** WS1 may proceed.

### WS1 — The contracts + the registry promotion + THE EXTRACTION PRECONDITION PROOF: evidence recorded, gate pending ratification (2026-07-08)

Delivered:
- **The bundle** (`workbench/contract_intelligence/`): the manifest
  (canonical #16, THE PARAPHRASED CLAUSE posture + the 12-phrase
  legal-conclusion forbidden vocabulary, the shared-engine ruling, THE
  REGISTER DISTINCTION in the manifest bytes) + the THREE ratified
  13-field contracts. `extract_contract_clauses` pins the CLOSED
  fifteen-class `clause_class` taxonomy in a declared first-match
  order with two marker regimes (commitment classes need explicit
  markers; structural classes need a concrete anchor token) and the
  contract_document_rule; `detect_missing_contract_metadata` declares
  the required-metadata groups (term_boundary any-of; payment) and
  ABSENCE_DECLARED honesty; `prepare_contract_review_brief` [assist]
  carries THE REGISTER DISTINCTION as its operative rule.
- **The registry promotion**: #16 ACTIVE (v2.1) with all thirty
  subtasks annotated (the 15→1 engine consolidation; summarize →
  brief; feeders 28–30 consolidated into the engine — the feed IS its
  accepted output; 21–23 consolidated → the shipped v1.8 skills, "the
  skill lives where its reader lives"; 24 stays [ES]-gated per D32;
  five SEQUENCED). Drafts at exactly **3 ACTIVE / 22 CONSOLIDATED / 5
  SEQUENCED / 1 FUTURE**, every ratified_path resolving; the global
  sweep constants moved **23→26 ACTIVE / 18→40 CONSOLIDATED** (the
  recorded-assertion-edit pattern, fourth occurrence) in
  test_compliance_corpus.py, test_procurement_corpus.py, and
  test_executive_fixture.py — all re-run green.

**THE EXTRACTION PRECONDITION PROOF**
(`backend/test_contract_corpus.py`, the 78th suite — six parts green;
full harness 78/78):
1. THE BUNDLE SHAPE: manifest ↔ contracts agree; the taxonomy pinned
   + closed at 15 in the ratified order; the two regimes partition it;
   the 16_ drafts at 3/22/5/1.
2. Both corpora through the real pipeline: 24 documents → 86 PRIMARY
   facts.
3. **THE COVERAGE REPORT (empirical, honest)**: the declared rules
   fire for 7/15 classes over 9 contract documents (12 clause
   candidates); the load-bearing floor holds (payment, sla,
   data_access, certification, approval + the term_boundary group).
   **Declared fixture-uncovered, never papered over**: termination
   (first-match SHADOWED — this corpus's termination sentences ride
   under "Term and renewal" headings, so `renewal` legitimately wins),
   notification_obligation (shadowed by data_access/renewal
   vocabulary), expiry_date, audit_rights, reporting_obligation,
   confidentiality, liability_indemnity, parties. **No new corpus is
   needed for the load-bearing set** (ruling 7 satisfied); the
   uncovered classes stay in the pinned taxonomy and produce no
   register entry over this fixture.
4. The register plants + the valve: 3 register proposals in the
   ratified shape (the v1.9 filename convention) held DERIVED; 2
   accepted by a human with VERIFIED provenance citing their PRIMARY
   sources; the held plant stays CANDIDATE.
5. **THE CONSUMER-MARKER PRECONDITION + THE CONVERGENCE (the
   milestone's premise, proven before any runner)**: the accepted
   CloudHost-SLA register entry is cited BY ASSET ID by findings of
   BOTH unchanged consumers — the v1.7 compliance runner
   (COMPLIANCE_OBLIGATION) and the v1.8 procurement runner
   (VENDOR_TERM) — zero edits to either; the citation is
   [DERIVED]-flagged in consumer proposal bytes; origin
   `contract-intelligence` derivable from provenance; the held plant
   reaches no package byte and no consumer finding.
6. NO SHARED FACT STORE: neither consumer's source names the engine
   (the feed is governed facts alone); the bundle ships NO runner at
   WS1; route manifest 88 at its ratified digest; MCP 9; D24 28/305.

**THE GATE (per WS0): user ratification of the three contracts, the
pinned taxonomy (including the declared first-match shadowing), the
registry promotion, and THE CONVERGENCE evidence is now requested. WS2
(the runner, on Opus per the recorded routing) starts only on
ratification.**
