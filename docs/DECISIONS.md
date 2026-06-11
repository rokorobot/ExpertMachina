# ExpertMachina — Architectural Decision Register

Binding rulings made during development. Each decision was made deliberately,
usually after explicit discussion — do not silently reverse one; if a decision
must change, record the supersession here.

## D1 — Persist facts, compute operational views (v0.9.1)
Never persist an operational view. The Governance Inbox, Compile Readiness, and
trust scores are computed at read time from source-of-truth tables
(AssetRelationship, AssetRevision, ClaimVerdict, EvaluationRun). There is NO
GovernanceItem/work-item table — a persisted view is a second state machine that
drifts. New tables are justified only for facts that genuinely don't survive
otherwise (ClaimVerdict, SourceDocument, IngestionJob).

## D2 — HIGH severity means "blocks the compile gate", nothing else (v0.9.1)
The inbox severity hierarchy is HIGH = deployment blocker, MEDIUM = materially
wrong / needs a verdict, LOW = incomplete/informational. Evidence gaps are never
HIGH (they don't block compile). Severity derives from
`conflict_engine.relationship_gate_disposition()` — the same function the compile
gate uses — so the two surfaces can never disagree.

## D3 — Measurements are immutable; humans review causes, not measurements (v0.9.2)
ClaimVerdict rows have no status column and no reviewer fields by design
("observe, record — not negotiate"). A human judgment about a verdict is a
VERIFICATION_REVIEWED AuditEvent; remediation happens on the asset/revision; the
next evaluation run produces fresh verdicts. Never add workflow state to a
measurement artifact.

## D4 — State transition sync, recomputation async (v0.9.2a)
Governance recomputation must not block human governance actions. Approvals
return immediately; heavy work (NLI rescans, future coverage jobs) runs as
background tasks owning their own DB session, and each background job writes its
own audit events. An approval event must never pretend downstream computation
already completed (record "scheduled", not results).

## D5 — Gate deployment, never ingestion
For every governance feature ask: does this slow ingestion or only affect
deployment? Ingestion has zero mandatory checkpoints; the only hard gate is at
agent-package compile time. North-star metric: time from document upload to
usable expert model (derivable from audit events).

## D6 — Connector output becomes ordinary ExpertMachina objects (v0.10.0)
SourceDocument → Document → CANDIDATE KnowledgeAsset → the existing governance
pipeline. No connector-specific approval flows, review queues, or asset states.
Tested as an invariant.

## D7 — Source URI is a file's identity within a connector (v0.10.1)
Same URI + same hash = unchanged duplicate. Same URI + different hash = CHANGED:
re-extract and reconcile by (type, name) — approved & differing → candidate
revision via the existing machinery; non-approved → edited in place; unmatched →
new CANDIDATE; disappeared counterpart → reported `possibly_stale`, untouched.
Old chunks are retained so approved assets keep verifiable provenance until their
revisions are approved. Per-scan SourceDocument rows are the permanent version
history. The strictly-linear revision rule is reported, never silently bypassed.

## D8 — UI areas are earned by plurality, not anticipation (v0.10.0 correction)
One source type does not justify a top-level "Connectors" navigation concept;
folder scanning lives inside Document Inventory. A dedicated "Sources &
Connectors" area arrives only when multiple source types exist (v0.11+). General
rule: don't create a navigation concept for a single instance of a category.

## D9 — The .empkg is a governed artifact, not a prompt format (v0.9.4)
Provider-agnostic (any LLM/agent can consume it), never contains API keys or
provider secrets (may carry `recommended_runtime`/`recommended_model` hints
later). Tamper-evident: every file sha256-hashed in manifest.json; the package
hash is the sha256 of the manifest itself. Compiled FOR a declared clearance
level — assets above it are excluded and the exclusion is declared. Governance
state inside is a snapshot stamped `compiled_at` — verifiable, not enforced.

## D10 — Two consumption channels, stated honestly (v0.9.4)
MCP gateway = the GOVERNED channel (live per-question verification, clearance,
audit). Exported packages = the PORTABLE channel (verifiable provenance, no live
enforcement). Never conflate them in docs or UI.

## D11 — External LLM calls use the OpenAI API with cheap models by default
Default `gpt-4o-mini` via `OPENAI_API_KEY`, overridable via `OPENAI_MODEL`. No
Anthropic SDK calls in app/example code without asking first. This is safe
because the governance spine is LLM-independent (NLI verdicts, deterministic
trust/gates, hashes); the LLM only does extraction, decomposition, fallback
judging, and consumer answering. Future: model-per-function configuration
(extraction / governance analyst / package consumer / claim judge) when the
LLM Provider Settings milestone lands.

## D12 — Honest measurement: NOT_MEASURED is never fabricated
Trust components without data are excluded and weights renormalized. Runs
predating verdict persistence report claim metrics as null, never zero. Caps and
exclusions are always declared (dropped pairs, excluded assets, skipped files).

## D13 — Governance core is frozen (Contract v1)
The 0.7–0.8 semantics (conflict classifications, review states, score formulas,
gate policy, revision linearity) are stable per docs/governance-contract-v1.md.
The MCP gateway and everything since builds on top without changing them.
Calibration note: KB conflict scanning uses stricter NLI thresholds (0.90) than
answer verification (0.80).

## D14 — Identity/auth is a v1.x milestone, deliberately
No user table, no login, actor strings everywhere ("GovernanceOfficer",
"connector:Name"). Acceptable for the local-node MVP; mandatory before
enterprise deployment. New schemas are identity-ready (evaluator_type/
evaluator_id on ClaimVerdict). Half-built auth would give false assurance —
ship it whole at v1.x with roles, permissions, credential storage.

## D15 — Compiler boundary: extract and verify, never synthesize
ExpertMachina never invents policy statements. Claims keep their qualifiers
("unless escalated") rather than generating derived rules. Cross-lingual
semantic verification (CS/DE/FR vs EN evidence) is a product differentiator —
position as "cross-lingual semantic verification".

## D16 — Session/state discipline (meta)
At every milestone release, regenerate PROJECT_STATE.md (+ this file + roadmap)
and start fresh AI sessions from them. Repo-resident state beats chat memory.
