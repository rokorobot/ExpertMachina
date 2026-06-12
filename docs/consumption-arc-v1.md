# Expert Package Consumption & Model Binding — v1.1 Design

> Ratified scope from the v1.1 scoping session (June 2026, post-v1.0.0).
> This is the build contract for the v1.1 release. D22 is recorded in
> docs/DECISIONS.md; the binding ships with evidence per the WS4 gate.

## The strategic read this milestone is built on

The consumption loop (`Agent → Question → Governed Retrieval → Evidence →
Answer → Trust → Provenance`) already exists on the **live channel**:
`query_engine.py` does governed retrieval, evidence-grounded generation, and
claim verification; the MCP gateway exposes it under v1.0 identity. What does
NOT exist is that loop on the **portable channel** — the .empkg consumer is a
~110-line example script hardwired to one provider, outside the governed
codebase. The arc is therefore not "build agent answers"; it is:

> Make the portable package channel real, evaluable, and bindable.

```
Package → Question → Retrieval → Model Answer → Evidence
        → Evaluation → Model Selection → Governed Binding
```

## Milestone name

**v1.1 — Expert Package Consumption & Model Binding.**
Not "agent deployment": deployment implies runtime operations; *binding* is
what actually ships. Enterprise extensions (SSO/SAML/SCIM, stored
provider credentials) move to a later milestone — they are hardening, not
the differentiator. Env-based provider keys under D19 suffice for this arc.

## Ratified rulings (scoping session)

1. **Sequencing: arc-first.** The consumption arc precedes enterprise
   extensions. Multi-provider evaluation uses env-based keys
   (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) per D19; stored credentials slot
   in later without reshaping anything.
2. **Anthropic SDK approved, with a boundary.** Anthropic enters ONLY as a
   provider adapter behind the D19 model resolver. The pattern:
   `Consumer / Evaluation → D19 resolver → provider adapter → response`.
   No direct SDK imports in evaluation, package consumer, routes, or UI —
   this supersedes the "no Anthropic SDK without asking" clause of D11
   (the asking happened; the resolver boundary is the answer).
3. **WS2 evaluates the package channel.** "This Expert Package version
   performs best on this model" is the honest claim. Live-channel evaluation
   already exists and is untouched; the channels are never blurred (D10).
4. **Live answers remain ephemeral-but-audited.** Persisting live answers as
   governed facts is a separate future decision (RequestFact territory —
   answer lineage, retention of possibly confidential content). It is NOT
   part of this arc.
5. **D22 — Expert Agent Binding** (full text in docs/DECISIONS.md): an
   Expert Agent is a governed binding of package version + selected model +
   AGENT principal + clearance + issuing evidence. It is not a runtime.

## The hard boundary for this arc

**No agent orchestration.** No tasks, no planner, no tool autonomy, no
multi-agent flows, no background execution, no autonomous remediation.
The agentic layer is CONSUMPTION, not orchestration (roadmap ruling,
reaffirmed at scoping). Anything shaped like
`Agent → plans work → uses tools → changes system` is out of scope.

Also out of scope for this arc: persisted live answers, new
connector/storage credentials, and any change to the governed channels'
semantics (D10, D13).

## Workstreams and acceptance gates

### WS1 — First-class Package Consumer

`backend/app/package_consumer.py`: load a .empkg, verify the full hash
chain (every file against manifest.json; the manifest itself as the package
hash; no unmanifested extras), refuse packages whose compile-gate snapshot
is not PASSED, retrieve evidence **package-locally** (deterministic lexical
scoring over `knowledge.json` — no Qdrant, no DB, no network), and generate
the answer through the D19 resolver via a new `PACKAGE_CONSUMER` LLM
function. The provider adapter seam lands in `llm.py` — the abstraction
D11/D19 deferred until a second provider existed; Anthropic is that second
provider.

**Pass condition:**
> Given the same .empkg and same question, different approved model engines
> can be swapped through D19, and the consumer returns answer + evidence +
> package provenance without using live database retrieval.

Evidence: `backend/test_package_consumer.py` — hash-chain verification and
tamper detection; gate refusal; engine swap via the adapter seam (D18-style
fake adapters); a consumption run against an EMPTY database proving the
evidence can only have come from the package; structural purity assertion
that the consumer module imports no database/retrieval machinery.

Package-local retrieval at v1 is declared lexical scoring
(`LEXICAL_OVERLAP_V1`) with counts reported (D12). Shipping an embedding
index inside the .empkg is a future format decision, not an interpretation
of this one.

**Gate: PASSED (accepted June 2026, commits 3ad2ccb + 3e096aa).**

### WS2 — Package Evaluation

EvaluationRun gains coordinates `(package_version, consumer_model)`; the
existing benchmark harness runs against the WS1 consumer. The referee is
unchanged and independent of every model under test (local NLI
cross-encoder, deterministic checks) — the credibility property is
inherited, not designed. ClaimVerdict immutability (D3) untouched.

**Pass condition:**
> EvaluationRun records package_version + consumer_model. Unrun models are
> absent, not zero. ClaimVerdicts remain immutable. Judge/referee is not one
> of the compared player models.

**Gate: PASSED (accepted June 2026, commit ff2133c).** Shape ruled at
acceptance: ONE EvaluationRun table — `run_type = LIVE | PACKAGE` plus
nullable coordinates (`package_version`, `package_hash`,
`consumer_model_provider`, `consumer_model_name`); evaluation is one
concept, the channel is a property, never a sibling table. LIVE runs
carry no package coordinates; PACKAGE runs require them.

**WS2 ratified rulings (binding):**
- The PACKAGE evaluation model is resolved through governed D19 config at
  run creation — no caller-supplied per-run model overrides; the
  config-flip workflow is the comparison workflow.
- Recorded model coordinates are binding. Config drift or package drift
  between creation and execution FAILS the run, never mislabels it.
- Failed PACKAGE runs keep no partial verdicts.
- `coverage_trend` remains LIVE-only (the trend tracks the governed
  knowledge base; PACKAGE runs measure a frozen artifact).
- `package_model_comparison` remains computed, never persisted.

Evidence: `backend/test_package_evaluation.py` (in CI).

### WS3 — Governed Model Selection

**Attachment ruling:** selection attaches to the **AgentPackage** — not the
ExpertModel, not the WS4 binding. The layering:

```
ExpertModel  = knowledge design / domain abstraction
AgentPackage = frozen portable artifact
Binding      = deployment of package + model + principal
```

Model selection answers *"which model is selected for this package version,
based on these evaluation runs?"* — a property of the artifact layer.

The object: `PackageModelSelection` (agent_package_id, package_version,
package_hash, selected_provider, selected_model_name,
supporting_evaluation_run_ids, rationale, selected_by_principal_id,
selected_at). ONE current selection per package, updated in place;
history lives in PACKAGE_MODEL_SELECTED audit events — lifecycle
deliberately not overbuilt. Comparison views remain computed, never
persisted (D1 — no leaderboard table); the selection decision is D17's
provenance pattern applied to model choice.

**Pass condition:**
> Given at least two successful PACKAGE evaluation runs for the same
> AgentPackage, an admin/operator with permission can select one model for
> that package. The selection is audited and references the supporting
> EvaluationRun ids. The selected model must have a successful PACKAGE run
> for that exact package_hash. Changing the selection creates a new audited
> decision; old audit remains. Comparison view remains computed. No
> ExpertAgent binding yet. No orchestration. No persisted live answers.

**Gate: PASSED (accepted June 2026, commit 8377361).** Ratified at
acceptance: PUT selection at `assets:approve`, GET selection/comparison at
`assets:read`; supporting evidence may — and for comparative decisions
should — include the losing model's runs.

Evidence: `backend/test_package_selection.py` (in CI).

### WS4 — Expert Agent Binding

The object is **ExpertAgentBinding** — not ExpertAgentRuntime. A governed,
append-only binding of the package's CURRENT model selection to an existing
active AGENT principal, with every field a snapshot at issue time.

**WS4 rulings (binding):**
- The binding model must equal the current PackageModelSelection at issue
  time — otherwise selection is not load-bearing.
- The binding references an existing AGENT principal and does NOT mint a
  token: token issuance is already a governed identity operation and is
  never hidden inside package binding.
- Changing the package selection later does not rewrite existing bindings —
  a binding is historical evidence of what was deployed.

The binding snapshots: agent_package_id, package_version, package_hash,
selected provider/model, AGENT principal id, principal clearance at issue
time, the supporting PackageModelSelection evidence, and the issuing
actor's identity fact.

**Pass condition:**
> Given an approved AgentPackage with a current PackageModelSelection, an
> authorized operator can create an ExpertAgent binding to an existing
> active AGENT principal. Creation refuses: no current model selection;
> selected model mismatch; inactive/non-AGENT principal; principal
> clearance below package clearance; revoked/missing package artifact;
> package hash drift. The binding is audited. The binding does not execute
> anything, does not mint tokens, does not orchestrate tools. Changing the
> package selection later does not rewrite existing bindings.

## Build order

WS1 first, alone, to its gate. WS2–WS4 each start only after the prior
gate passes. The design contract is regenerated only if a gate forces a
scope change, and any reversal of a ruling above is recorded as a
supersession in docs/DECISIONS.md.
