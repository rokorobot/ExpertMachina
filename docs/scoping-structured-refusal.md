# Scoping — The Structured Refusal (proposal for ratification)

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

## Explicitly out of scope

Changing any finding kind, contract, or corpus beyond the fixtures
named above; the OpenAI run (blocked on account credit); the
live-SharePoint scan; any change to how humans accept findings.
