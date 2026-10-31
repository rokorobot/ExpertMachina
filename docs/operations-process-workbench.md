# v1.0 — Operations / Process Improvement — Build Record

> Built 2026-07-09 by the AgenticTeam Builder (opus) from the ratified
> scope contract `handoffs/current-scope.json`
> (WS-operations-process-workbench), validated against ExpertMachina
> `origin/main` @ `7c2203b` (re-verified after fetch at build start;
> unchanged). Branch `feat/operations-process-workbench`, rollback anchor
> tag `ws-operations-process-baseline` created before the first edit.
> Reference bundle: `workbench/finance_cost_leakage/` (v2.3, the newest
> shipped convention). `workbench/common.py` reused BY IMPORT only,
> unchanged.
>
> Titling/versioning note: the shipped `docs/finance-cost-leakage-v2.3.md`
> is a WS0 build CONTRACT (scoping rulings, gate records appended per
> workstream). This file is a Builder BUILD RECORD for a single clean
> first run, so it is titled `v1.0` and structured as an
> implementation record rather than a rulings ledger. The deviation is
> intentional and noted here per the scope contract's instruction.

## The milestone identity (the spine, carried verbatim into every gate)

**v1.0 is document-governed process-improvement intelligence, not
process execution.** *"The Operations workbench diagnoses governed
process documents — contradictions across process documents,
SOP-vs-policy mismatches, undefined handoffs, and outdated process
documents. It reports what the documents SAY and where they DISAGREE,
MISS a handoff, or are SUPERSEDED. It never determines
process-execution truth."*

## The boundary

INCLUDED: contradictions across process documents (doc-vs-doc conflicts
on a shared subject); SOP content vs. governing policy on declared axes
(approval_authority, approval_timing, control_requirement); process
steps whose handoff (next owner, trigger, or receiving procedure) is
undefined; documents superseded/stale by revision-backed evidence
(explicit supersession notice, superseded-revision tracking, or overdue
by the document's OWN declared review interval against a declared
`as_of`); a cited, visibly NON-AUTHORITATIVE process-map projection.

EXCLUDED (all [OE]/[ES]/SYNTHESIS_INFERRED, refused live naming the
gate): execution/run-log analysis and every "did the step actually
run?" question; process-mining over traces; missing stage-OWNER
assignment ([ES]); estimated improvement impact (SYNTHESIS_INFERRED);
the valve-synth backlog/proposal generators.

**THE INSTRUCTION-EXECUTION DISTINCTION**: a document sentence about a
step ("the IT team provisions the laptop") is a governed INSTRUCTION,
in scope; an execution RECORD ("the laptop was provisioned on
2026-05-02", "the run completed") is [OE], refused. The boundary is on
assertions about execution truth, never on the presence of a step
description.

## THE ACTIVE FIVE

| ACTIVE (v1.0) | Tag | Kind · basis |
|---|---|---|
| `detect_process_contradictions` | now | PROCESS_CONTRADICTION · CONFLICT_BACKED; cross-document, declared same-subject rule (>= 2 shared subject tokens) |
| `compare_sop_vs_policy` | now | SOP_POLICY_MISMATCH · CONFLICT_BACKED; declared comparison axes + policy markers, cross-document |
| `detect_missing_handoffs` | now | MISSING_HANDOFF · REFUSAL_BACKED; completion marker present, handoff marker absent, reproducible refusal of the handoff question |
| `detect_outdated_process_documents` | now | OUTDATED_PROCESS_DOCUMENT · REVISION_BACKED; supersession notice / superseded-revision / overdue-by-own-interval, never age alone |
| `prepare_process_map_projection` | assist, synth | THE PROJECTION DISCIPLINE; cited, non-authoritative, gaps declared not filled |

Excluded-by-design (out of scope for the first clean run, each requires
machinery a first end-to-end run should not carry):
`generate_process_improvement_backlog`, `prepare_improvement_proposal`
(valve-synth), `identify_missing_process_stage_owner` ([ES]),
`estimate_improvement_impact` (SYNTHESIS_INFERRED), and the [OE]
execution/trace family.

## The two cardinal sins (the sensitivity posture)

- **THE INVENTED PROCESS**: every owner, trigger, step, date, or handoff
  in a finding is verbatim from a cited approved document, or the finding
  explicitly reports its ABSENCE. A handoff gap is reported as an absence
  with the triggering step cited verbatim — never filled with an invented
  owner or receiver.
- **THE COMPLETED RUN**: the runner never asserts a step was performed,
  executed, or completed by anyone. The manifest's `forbidden_vocabulary`
  is swept over every written byte before emission (proven with teeth in
  `test_operations_workbench.py`).

## The corpus (synthetic — Meridian Operations Ltd)

Six SHORT synthetic process documents in `corpus_operations/` (naming
follows the newest shipped convention — finance uses `corpus_finance/`).
All content fabricated; every document visibly synthetic. Seeded defects,
one per [now] skill plus assist material, are mapped in `CORPUS.md`:

- contradiction — onboarding SOP ("within 2 business days") vs
  access-request procedure ("within 5 business days") for system-access
  approval (cross-document, shared subject);
- SOP-vs-policy — change SOP ("approved by the team lead alone") vs
  change policy ("Change Advisory Board" / single-approver prohibited),
  `approval_authority` axis;
- missing handoff — the access-request Revocation step ("is then closed
  out") and the onboarding buddy programme ("is complete after the
  two-week period"), each with no defined receiver;
- outdated — the Remote Access SOP superseded by the Access Governance
  Policy's explicit supersession notice; the change documents also overdue
  by their own declared review cadence;
- process map — the onboarding SOP and access-request procedure carry
  ordered, citable steps.

There is deliberately NO execution-record plant in the runtime corpus:
the adversarial "decline an execution record naming [OE]" case is an
INJECTED fixture in the acceptance suite (mirroring the finance INVOICE
PLANT discipline — an execution record cannot exist in a
process-document corpus by accident).

## Doors and projection-only posture

The runner is a consumer, never a subsystem (D22): `.empkg` via
`app.package_consumer`, the MCP gateway at a real AGENT token's
clearance, and file writes into the vault only — one proposal per finding
into `08_proposals`, the process-map projection into
`07_agent_workspaces`. Zero direct canonical writes (D29 One-Way Valve);
findings and suggested improvements re-enter only through the proposal
lane (CANDIDATE → human gate → DERIVED). `common.py` is reused by
relative import, unchanged (Guard 5 sweeps the runner clean).

## Tests (proofs)

- `backend/test_operations_corpus.py` — bundle shape, five ACTIVE
  contracts parse, manifest agreement, six synthetic docs load, seeded
  defect markers fire, a non-ACTIVE contract is refused.
- `backend/test_operations_acceptance.py` — each skill produces
  evidence-cited findings on the seeded corpus; refusal-first (>= 1 per
  skill, `-k refusal`); a denied-access case (`-k denied`) degrading to
  explicit refusal; THE EXECUTION PLANT declined naming [OE];
  projection-only writes; the COMPLETED-RUN sweep; determinism.
- `backend/test_operations_workbench.py` — Guard 5 door sweep,
  common.py reuse-by-import, only runner.py in the bundle, manifest
  agreement, no execution-door leak, the gated list refused naming the
  gate, the COMPLETED-RUN dictionary has teeth.

These suites are pytest-native (`def test_*`, so `-k` selection works and
`pytest <file>` collects them) AND run standalone under the suite harness
(`python <file>`), a deliberate deviation from the shipped `main()`-only
convention required by the scope contract's `-k refusal` / `-k denied`
proof commands. See the Builder handoff
(`handoffs/2026-07-09-ws-operations-process-builder.md`) for the literal
proof evidence, the baseline regression line, and the noted proof-command
correction for the `main()`-style constitutional guard files.
