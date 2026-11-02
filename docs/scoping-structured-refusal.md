# v2.5.0 — The Structured Refusal (D33) — Scoping + Build Contract

> Drafted 2026-11-01 from the real-model diagnostic evidence
> (docs/customer-ops-workbench-v1.6.md, "Post-release honest-slot
> evidence" + "Owner-frame sharpening"; PRs #35, #36, #39). **Docs only —
> no code until WS0 is ratified.** Version number and D-number are
> rulings for the owner (proposed below, not assumed).

## The problem in one sentence

Every refusal-backed finding in the catalog rests on detecting that
`consume()` refused, and today that detection parses the model's prose
for the marker `INSUFFICIENT EVIDENCE` — which a real model does not
emit reliably, so findings depend on phrasing rather than on the corpus.

## The evidence (8 real runs, Anthropic claude-opus-5-5, customer-ops corpus)

| Rule tried | Planted P2 procedure gap refused | False refusal observed |
|---|---|---|
| marker anywhere (shipped) | 7/8 | yes — "which playbook" frame, 2/5 (a mid-text "For those details: INSUFFICIENT EVIDENCE") |
| marker leads the answer (option b, dropped) | 0/5 | — |
| marker begins a line | 4/5 | — |

- The model gives **scoped refusals**: context first, then "For the
  step-by-step procedure: INSUFFICIENT EVIDENCE…". The answering
  contract ("reply exactly", `app/package_builder.py` rule 3) is binary;
  the corpus is not — partial evidence is the normal case for a gap.
- Run 8 refused **in substance with no marker at all** ("They do not
  contain the playbook's actual steps… outside the governed knowledge
  of this expert package"). No lexical rule can catch it.
- Frame sharpening (PRs #36, #39) fixed what was a *question* problem
  (owner = contracting party; playbook *named* but empty) and is
  correct regardless. The residual noise (~1 in 8) is a *detection*
  problem.

## Blast radius (measured, not estimated)

- **Six runners** test the marker by substring: customer_operations,
  compliance_obligation (×2), executive_briefing, finance_cost_leakage,
  procurement_intelligence, operations_process_improvement.
- **The product path too**: `app/evaluation.py:240` (package evaluation)
  uses `answer.startswith("INSUFFICIENT EVIDENCE")` to skip claim
  judging. A scoped or paraphrased refusal is judged as a knowledge
  claim — the junk-verdict case its own comment (D12) exists to prevent.
- **CI**: 19 suites inject deterministic answerers at the `answerer`
  seam; 26 suites reference the marker. All currently pass only
  because CI answerers emit the marker first — CI cannot distinguish
  detection rules (option b passed 92/92 while failing real runs 5/5).
- **The package**: the answering policy is compiled into every
  `.empkg` (`PACKAGE_FORMAT_VERSION = "empkg-v1"`); changing it changes
  new package bytes and hashes. Existing packages must keep working
  with their compiled policy (D12: never backfilled).

## Proposed rulings (WS0, for ratification)

1. **Refusal becomes a structured field, decided at the answering step,
   never parsed downstream.** `consume()` returns
   `answer_status ∈ {ANSWERED, REFUSED, PARTIAL}` plus, for PARTIAL, a
   verbatim `refused_scope` string from the model. Runners and
   `evaluation.py` read the field; no consumer greps prose.

2. **Mechanism — recommended: the answering envelope.** The packaged
   answering policy (rule 3) is amended to require a one-line status
   header the consumer parses deterministically
   (`STATUS: ANSWERED|REFUSED|PARTIAL`, then for PARTIAL
   `REFUSED_SCOPE: …`), followed by the cited answer. One call, no new
   D19 function, status declared by the same generation that read the
   evidence.
   *Alternative (not recommended):* a second classifier call (a new D19
   function `REFUSAL_JUDGE`). No package change, but doubles calls and
   puts a second, unevidenced model judgement between the evidence and
   the finding.
   *Rejected on evidence:* any lexical rule over free prose.

3. **PARTIAL is the honest middle, and the finding rule is explicit.**
   A refusal-backed finding fires iff `answer_status ≠ ANSWERED`. A
   PARTIAL finding carries the model's `refused_scope` verbatim and the
   partial evidence ids, so the human at the gate sees exactly what was
   and was not answered. Refusal-first still cuts both ways: ANSWERED ⇒
   no finding.

4. **Malformed or missing header ⇒ declared, never guessed.** If the
   envelope is absent or unparseable, status is `UNDETERMINED`; the
   runner records a skip with that reason (no finding, no silent
   default). The run summary counts UNDETERMINED answers so a model
   that ignores the contract is visible, not absorbed.

5. **Legacy packages keep their compiled contract.** Packages compiled
   before the amendment carry no envelope rule; for them the consumer
   applies the shipped substring rule and labels the status
   `source: LEGACY_LEXICAL` in the result. No backfill, no rewrite of
   existing packages (D12).

6. **Package format.** The amendment ships as `empkg-v1.1` (additive:
   the policy text changes; the archive layout does not). WS0 confirms
   whether the consumer's format check needs a new accepted value or a
   minor-version rule.

7. **CI answerers emit the envelope.** The deterministic contract-
   followers return `answer_status` directly; one new adversarial
   fixture per workbench returns a scoped refusal *without* the
   leading marker and one returns an answer *with* a mid-text marker —
   CI must now be able to tell detection rules apart.

## The proof (defined before any code, per tradition)

- **Real-model, both corpora:** 5 runs each on the customer-ops and
  compliance corpora. Pass = every planted refusal-backed gap found
  5/5 AND every covered control (e.g. P4c, the Compliance Officer)
  silent 5/5 AND UNDETERMINED = 0.
- **CI:** all suites green; the new adversarial fixtures prove the
  runners read the field, not the prose; customer-ops gate still 6
  proposals, compliance still 20, byte-identical at pinned `as_of`.
- **Legacy:** an `empkg-v1` package from the current fixtures still
  consumes, labelled `LEGACY_LEXICAL`.
- **`evaluation.py`:** a PARTIAL answer is never sent to claim judging
  as if it were a full knowledge claim.

## Standing boundaries this must hold

Zero schema (D24 at 28 tables / 305 columns — the status travels in
the consume() result and proposal frontmatter, not a column). D19
unchanged in recommended form (no new function). The valve (D29)
unchanged: status decides whether a *candidate* exists, never whether
anything is accepted. Guard 5 sweeps the runner edits unchanged. No
new guard family.

## Decisions for the owner

- **D-number:** this amends the binding packaged answering contract that
  every consuming agent is held to. I propose it is law-level — **D33,
  The Structured Refusal** — rather than an implementation detail. The
  owner rules.
- **Version:** a minor release (it changes package bytes and a
  cross-workbench contract), sequenced after the pending release
  decision for catalog #8.
- **Mechanism:** envelope (recommended) vs. classifier call.
- **PARTIAL semantics:** ratify ruling 3 as written, or require PARTIAL
  findings to carry a distinct finding-kind suffix.

## WS0 record

### Owner rulings — RATIFIED (2026-11-02, user)

1. **Law-level: D33, The Structured Refusal** (recorded in
   docs/DECISIONS.md).
2. **Mechanism: the status header.** The model that read the evidence
   states `STATUS: ANSWERED | REFUSED | PARTIAL` in a required first
   line. No classifier call.
3. **PARTIAL semantics:** a finding fires whenever the answer is not
   fully ANSWERED; PARTIAL carries the model's own wording of what it
   could not answer, verbatim. No new finding kinds.
4. **Version:** v2.5.0; catalog #8's release becomes v2.6.0.

### Remaining WS0 items — RATIFIED as written (2026-11-02, user)

All five ratified as written:
- **(4) Malformed or missing header ⇒ UNDETERMINED**: skipped with that
  reason, never guessed; counted in the run summary.
- **(5) Legacy packages** keep their compiled contract: the shipped
  substring rule, labelled `source: LEGACY_LEXICAL`; no backfill (D12).
- **(6) Package format** `empkg-v1.1` (policy text changes; archive
  layout does not); WS1 confirms the consumer's format-check rule.
- **(7) CI answerers emit the status**, plus two adversarial fixtures
  per refusal-backed workbench (a scoped refusal without the leading
  marker; an answer with a mid-text marker).
- **The proof** as defined above (5 real runs × 2 corpora: planted
  gaps 5/5, covered controls silent 5/5, UNDETERMINED = 0; CI green,
  gates still 6 / 20 proposals; legacy package consumes; evaluation.py
  never claim-judges a PARTIAL as a full claim).

**Verdict: v2.5.0 WS0 PASSED (2026-11-02, user-ratified).** WS1 may
proceed.

## Workstreams

- **WS1 — the contract + the format rule + the adversarial fixtures**
  (no runner change): the amended answering policy (rule 3 → the status
  line), `PACKAGE_FORMAT_VERSION = "empkg-v1.1"`, the pure
  `package_consumer.parse_answer_status()` (HEADER for v1.1 /
  LEGACY_LEXICAL for v1 / UNDETERMINED for malformed), and
  `backend/test_structured_refusal.py` proving it over the adversarial
  fixtures, a freshly built v1.1 package, and a legacy v1 package.
- **WS2 — the wiring:** `consume()` returns `answer_status` /
  `refused_scope` / `status_source`; the six runners and
  `evaluation.py` read the field; every CI answerer emits the status;
  per-workbench adversarial fixtures; UNDETERMINED counted in run
  summaries.
- **WS3 — the real-model proof** (as ratified) + release.

## Gate records

### WS1 — the contract, the format rule, the adversarial fixtures: RATIFIED (2026-11-02, user)

- **The contract:** `app/package_builder.py` answering policy rule 3
  replaced — every answer begins with `STATUS: ANSWERED | REFUSED |
  PARTIAL`; REFUSED is followed by the INSUFFICIENT EVIDENCE sentence;
  PARTIAL's next line is `REFUSED_SCOPE: <the model's own words>`. The
  v1 "reply exactly" wording is gone from new packages.
- **The format rule:** `PACKAGE_FORMAT_VERSION = "empkg-v1.1"` (archive
  layout unchanged). The consumer had no format check before; the rule
  is now explicit in `package_consumer.parse_answer_status()`: v1.1 →
  HEADER (or UNDETERMINED), anything else → LEGACY_LEXICAL (the shipped
  substring rule, labelled).
- **The parser** (pure, no I/O): first non-empty line must be a clean
  status line; markdown dressing and case ignored; PARTIAL requires a
  non-empty REFUSED_SCOPE line, carried in the model's words (markdown
  dressing stripped — found by the suite: `**REFUSED_SCOPE:** x`).
  Anything else is UNDETERMINED, never guessed.
- **`backend/test_structured_refusal.py`** (the 93rd suite): Part 1 —
  the three statuses, dressing, "the header decides, never the prose"
  (ANSWERED + mid-text marker = answer; REFUSED needs no marker), 11
  malformed/missing shapes UNDETERMINED **including the three recorded
  real-model shapes** (scoped refusal, marker-less refusal, mid-text
  mention), legacy LEGACY_LEXICAL; Part 2 — a freshly built package
  declares empkg-v1.1 with the status-line policy and verifies; Part 3 —
  a legacy empkg-v1 package still loads, read LEGACY_LEXICAL.
- **Regression:** full harness 93 passed — the format bump changes new
  package bytes, and no suite pinned them; no runner, consume(), or
  evaluation.py change (WS2).
- **Held:** zero schema (28/305), D19 unchanged (no new function), no
  new guard family.

- **Early real-model signal (one run, 4 calls, not the WS3 proof):**
  Anthropic claude-opus-5-5 on the customer-ops corpus with an
  empkg-v1.1 package complied **4/4** — a clean `STATUS:` first line and
  a well-formed `REFUSED_SCOPE:` on every answer; all four planted gaps
  (both P2 playbook frames, both P4 reporting frames) returned PARTIAL
  with a scope naming the gap exactly. **Risk named for WS3: PARTIAL
  inflation** — with "fires whenever not fully ANSWERED", a model that
  hedges PARTIAL on a *covered* control would mint a false finding; the
  ratified "covered controls silent 5/5" (compliance P4c) is the test.

**Verdict: v2.5.0 WS1 PASSED (2026-11-02, user-ratified).** WS2 (the
wiring) may proceed.

### WS2 — the wiring: RATIFIED (2026-11-02, user — incl. the three WS2 choices)

- **`consume()`** returns `answer_status`, `refused_scope`,
  `status_source`, plus `answer_body` (the answer without its status
  lines — what a claim verifier may judge).
- **One ledger, six runners** (`workbench/common.py` `StatusLedger`):
  customer_operations, compliance_obligation (×2 walks),
  executive_briefing, finance_cost_leakage, procurement_intelligence,
  operations_process_improvement. Each reads the status (from the
  consume() result, or an injected answerer's text through the SAME
  parser under the package's declared format); REFUSED or PARTIAL fires
  the finding; UNDETERMINED is skipped with its reason; every run
  summary carries `answer_status_counts`. No runner tests the marker by
  substring any more. REFUSED findings keep their evidence line
  byte-for-byte; PARTIAL findings state "returned STATUS: PARTIAL" and
  carry the refused scope in the answering model's own words.
- **`evaluation.py`**: REFUSED → refusal recognized (unchanged);
  **PARTIAL and UNDETERMINED are never claim-judged** — recorded as
  `verification_status` PARTIAL / UNDETERMINED, coverage 0, the question
  fails (neither the full answer nor the full refusal a benchmark
  expects; an UNDETERMINED answer broke the binding contract); ANSWERED
  is judged on `answer_body`, never the status line; legacy packages keep
  this path's own `startswith` rule.
- **CI answerers emit the status line**: 44 answers across 22 suites,
  plus the generation-level fake in `test_package_evaluation.py`. The
  operations suites' fake package door now declares `empkg-v1.1` and
  reads statuses with the real parser (it would otherwise have fallen
  silently to LEGACY_LEXICAL).
- **THE D33 ADVERSARIAL PROOF, per workbench** (`test_support.
  d33_adversarial_proof`, wired into all six refusal-backed suites):
  *scoped* — every REFUSED answer rewritten as PARTIAL with NO marker
  anywhere, every ANSWERED one given a mid-text marker → **exactly the
  baseline refusal-backed findings**, each carrying the declared scope,
  none extra; *headless* — status lines stripped → **zero**
  refusal-backed findings, every answer UNDETERMINED. 13 findings
  reproduced (customer-ops 4, compliance 2, executive 3, finance 1,
  procurement 1, operations 2). CI can now tell detection rules apart —
  option (b) or the shipped substring rule would fail these.
- **`test_structured_refusal.py`** grows Part 4 (consume() fields; a
  headless real-model shape is UNDETERMINED) and Part 5 (evaluation never
  claim-judges PARTIAL / UNDETERMINED / REFUSED; ANSWERED is; legacy
  keeps startswith).
- **Found by the posture guards on the way (fixed):** the executive
  briefing's UNSOURCED SENTENCE guard rejected a PARTIAL gap line — a
  declared `STATUS: PARTIAL` is now a governed source token exactly as
  the refusal marker is.
- **Regression:** full harness 93 passed; customer-ops gate 6
  proposals, compliance gate 20 (both byte-identical across runs).
  Zero schema (28/305); D19 unchanged; Guard 5 swept the runner edits
  and the new common.py ledger with zero guard edits; no new guard
  family.

**For ratification (choices made in WS2, not pre-ruled):** the
evaluation semantics (PARTIAL / UNDETERMINED fail, never judged); the
executive source token; `answer_body`.

**Verdict: v2.5.0 WS2 PASSED (2026-11-02, user-ratified).** WS3 may
proceed.

## Explicitly out of scope

Changing any finding kind, contract, or corpus beyond the fixtures
named above; the OpenAI run (blocked on account credit); the
live-SharePoint scan; any change to how humans accept findings.
