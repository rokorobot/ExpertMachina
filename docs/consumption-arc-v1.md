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

### WS3 — Governed Model Selection

Comparison views are computed, never persisted (D1 — no leaderboard table).
Selecting a model for an expert is an audited decision referencing the
evaluation runs that justified it — D17's provenance pattern applied to
model choice.

**Pass condition:**
> Selecting a model creates an audited decision referencing evaluation runs.
> Comparison remains computed, not persisted as a leaderboard table.

### WS4 — Expert Agent Binding

A binding of approved package version + selected model + AGENT principal +
clearance, carrying its issuing evidence (identity fact, selection decision).
Deployment means issuing/referencing a governed token — everything needed
already exists from v1.0.

**Pass condition:**
> A binding can be created only from approved package version + selected
> model + AGENT principal. The binding issues or references a governed
> token. The system can answer: why this package, why this model, why this
> agent, why this clearance?

## Build order

WS1 first, alone, to its gate. WS2–WS4 each start only after the prior
gate passes. The design contract is regenerated only if a gate forces a
scope change, and any reversal of a ruling above is recorded as a
supersession in docs/DECISIONS.md.
