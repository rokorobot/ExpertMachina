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

## D17 — Approval policies are versioned governed facts; auto-approval applies only to new CANDIDATE assets, never to revisions (v0.10.2)
A policy is a governed object, not a setting. The rules:
- **Versioned**: any definition change (name, asset types, connector scope)
  bumps `version`; enable/disable is operational, not definitional — audited
  (`POLICY_ENABLED`/`POLICY_DISABLED`) but no bump. Past approvals must keep
  pointing at the exact rule text that fired.
- **No delete endpoint**: disable instead. Audit history references policies;
  they must not disappear.
- **Provenance is mandatory**: every auto-approval writes `ASSET_AUTO_APPROVED`
  with the policy id/name/version, the rule snapshot that fired,
  `approved_without_human: true`, and the triggering ingestion job — "why was
  this approved?" must be answerable from the event alone, indefinitely.
- **Same transition path as a human**: auto-approval goes through
  `crud.update_knowledge_asset` (AssetReview row, baseline revision, document
  lifecycle), only the actor (`policy:<name>`) and audit fingerprint differ.
  Policy-approved assets must never become a second species of approved asset.
- **New CANDIDATE assets only, scoped to the triggering ingestion event** —
  never retroactive, and NEVER candidate revisions: a revision changes
  already-trusted content, and that judgment stays human. CHANGED source files
  keep flowing through the D7 revision machinery untouched.
- **D12 applies**: declined assets are counted and declared in
  `POLICY_AUTOAPPROVAL_COMPLETED`; when no policy is in scope, nothing runs
  and nothing claims to have run.
Semantic conditions (formatting-only diffs, NLI contradiction checks) and any
future revision auto-approval are a separate, explicit decision — not an
extension of this one.

## D18 — Providers describe; the framework decides (v0.11)
A source provider may describe source state — reachability (`validate`),
audit context (`describe`), items (`discover`: URI + name + metadata), and
content (`fetch`: bytes + metadata) — and must NOT determine reconciliation
outcomes. Identity is the provider-defined URI (D7 generalized beyond
files); the change verdict is the framework's hash of fetched content;
provider metadata (`modified_at`, `size_bytes`, anything else) is
informational context — recorded, never decisive for NEW / DUPLICATE /
CHANGED / FAILED. One source file need not equal one item; the provider
owns the mapping from its native shape to items.
**Why:** forecloses the classic enterprise-connector bug pair (timestamp
changed → false change; timestamp unchanged → missed content change) and
keeps correctness assumptions out of provider code — every future provider
(SharePoint, Drive, exports) inherits reconciliation, revisions, policy
(D17), and audit instead of reimplementing or subverting them.
**Tradeoff accepted:** the framework always fetches content to hash it —
no metadata-based fetch skipping. If a provider ever wants timestamp-based
optimization, that is a new explicit decision, not an interpretation of
this one.
**Evidence:** backend/test_connector_seam.py — Test C (modified_at changes
+ hash unchanged → DUPLICATE, the new timestamp still recorded as context)
and Test A (the framework classified `fake://` URIs end-to-end, inputs
that could not exist under the original design). The seam suite is part of
the named regression contract: it protects the architecture the way the
product suites protect behavior — user-visible tests can all pass while
"provider decides" quietly returns; only the seam tests catch that.

## D19 — Runtime config stores selection, never credentials; empty config preserves prior behavior (v0.12.0)
Governed runtime configuration (LLMFunctionConfig and any future config
table) stores WHAT was chosen (model, provider name, function mapping) and
never credentials — API keys and secrets stay environment-based until the
v1.x identity/credentials layer exists (D14). Config rows may name which
env var holds a key; never the key itself.
The resolution invariant: explicit config → environment override →
hardcoded default, and an EMPTY config store must preserve the behavior
that existed before the store did. Configuration is opt-in acceleration,
never a migration burden.
**Why:** half-stored credentials would give false assurance exactly as
half-built auth would (D14's reasoning, applied to secrets); and a config
subsystem that changes behavior merely by existing makes every upgrade a
breaking change.
**Tradeoff accepted:** no test-connection buttons or stored multi-provider
keys until v1.x — the Settings UI can select models but cannot validate
provider reachability.
**Evidence:** backend/test_llm_settings.py — six-part precedence suite,
including a structural assertion that no credential-shaped column exists
on the config table; HTTP smoke Part 7 covers the endpoints.

## D20 — Callers propose identity; the identity boundary decides the actor (v1.0.0, RATIFIED)
> Callers propose identity. The identity boundary decides actor.
> Governed actions must record identity facts as immutable historical
> evidence at action time. Future user-table state must never be
> required to explain past governed actions.
> Identity evidence records authentication at action time; authorization
> and user state may change later without altering historical identity
> facts.

The fourth instance of the family principle (D17/D18/D19): *Proposal
and Decision must be separated. Convenience proposes. Governance
decides.* Governance distrusts **reconstruction**, not users.

The shape: Principal (mutable registry — five kinds: HUMAN, DELEGATED,
SYSTEM, SERVICE, AGENT) / Credential (hash-only lineage — revoke, never
delete) / IdentityFact (immutable evidence: who, kind, role-at-action-
time, method, credential fingerprint, on_behalf_of identity chain).
The symmetry: Principal changes; IdentityFact never changes —
KnowledgeAsset/AssetRevision applied to actors. Purity rule:
IdentityFact answers only "who was authenticated?"; request-context
responsibilities go to a future RequestFact, never here (enforced
structurally in CI). Identity delegation (`on_behalf_of`) and causal
ActionContext (D17 provenance) evolve independently. Authorization is a
separate layer: a small code-resident permission matrix enforced at the
route boundary; grants for non-read permissions and ALL denials are
audit events carrying the actor's fact. Legacy records keep their
caller-supplied strings with NULL facts — "we did not know," never
reconstructed (D12); role-vocabulary migrations touch the mutable
registry only, never historical role_snapshots.

**Why:** `user_id = 7` answers "who is Alice today?" — a governed action
must answer "who was Alice when the approval occurred?"
**Tradeoff accepted:** every write requires authentication (no
anonymous local convenience); agents must be re-provisioned with
governed tokens (`EM_AGENT_TOKEN`); env-asserted MCP identity is
refused explicitly rather than silently ignored.
**Evidence:** backend/test_identity_boundary.py (the Alice test: rename,
demotion, rotation, and deactivation cannot change what the fact
answers; structural purity assertions); test_http_api.py Part 8
(?actor=Mallory is inert over HTTP; records point to facts);
test_mcp_gateway.py Part 7 (hostile EM_AGENT_ID/EM_AGENT_CLEARANCE
inert; live revocation); test_authorization.py (least-privilege grid;
the denied-as-READ_ONLY fact survives Alice's promotion);
test_migration.py (pre-boundary databases upgrade with legacy rows
honestly legacy; snapshots never rewritten).

## D21 — Recovery is a documented procedure, never a bypass mechanism (v1.0.0)
Root-admin lockout on a local node is recovered by the DOCUMENTED manual
procedure in docs/identity-boundary-v1.md — filesystem access to the
database is the actual trust anchor of a local deployment, and the
procedure routes through identity.set_password so the rotation stays a
governed, audited credential event with intact lineage. There is
deliberately NO recovery command or backdoor flag: a standing mechanism
whose purpose is to defeat the boundary is a standing attack surface.
Non-lockout resets are ordinary administration (Users & Tokens).
identity_facts are never edited in any recovery scenario — they are
historical evidence. Startup self-validation (identity.validate_boundary)
reports a missing active ADMIN loudly and points at the procedure.

## D22 — Expert Agent Binding (v1.1 scoping, ratified)
> An Expert Agent is a governed binding of:
> - Expert Package version
> - selected model
> - AGENT principal
> - clearance / permissions
> - issuing evidence
>
> It is not a new runtime, orchestrator, autonomous worker, or execution
> environment.

The agentic layer is CONSUMPTION, not orchestration. The v1.1 arc is
`Package → Question → Retrieval → Model Answer → Evidence → Evaluation →
Model Selection → Governed Binding` — never `Agent → plans work → uses
tools → changes system`. Tasks, planners, tool autonomy, multi-agent
flows, background execution, and autonomous remediation are out of scope
by ruling, not by omission.

Companion rulings made at the same scoping session (binding, recorded in
docs/consumption-arc-v1.md):
- **Arc before enterprise extensions** — env-based provider keys under
  D19; stored credentials remain a later milestone.
- **Anthropic is a provider adapter behind the D19 resolver** — the
  adapter abstraction D11 deferred is earned by the second provider.
  No direct provider-SDK imports in evaluation, the package consumer,
  routes, or UI. This resolves D11's "ask first" clause for Anthropic.
- **Per-package model evaluation consumes the PORTABLE channel** (D10) —
  "this Expert Package version performs best on this model" is the honest,
  reproducible claim; the referee (local NLI, deterministic checks) is
  never one of the players.
- **Live agent answers stay ephemeral-but-audited** — persisting them as
  governed facts is a separate future decision (RequestFact territory).

**Why:** "deployment" implies runtime operations ExpertMachina does not
govern; a *binding* of already-governed artifacts is fully answerable from
evidence: why this package, why this model, why this agent, why this
clearance.
**Tradeoff accepted:** no agent runtime ships with v1.1 — customers bring
their own execution; ExpertMachina hands them a governed, evaluated,
revocable binding.
**Evidence:** the WS gates in docs/consumption-arc-v1.md; WS1:
backend/test_package_consumer.py (engine swap through D19, package-local
retrieval against an empty database, structural purity).

## D23 — ExpertAgentBinding Lifecycle (DEFERRED, placeholder — v1.1.0)
Open question, deliberately NOT implemented in v1.1.0:

> Can a binding be withdrawn?

v1.1.0 ships bindings as append-only snapshots with no status column, no
deactivate path, and no delete — "do not overbuild lifecycle" ruled at WS3
and held at WS4. The question becomes real when production deployments
need "this binding is withdrawn" as a governed act. The likely future
answer (recorded so the discussion starts from it, not as a ruling):

> Deactivate. Never delete. Never mutate history.

— mirroring the Principal model (no delete, deactivate; issued evidence
stays untouched). Until decided: withdrawing an agent's access is done
where access actually lives — deactivate the AGENT principal or revoke
its tokens in Users & Tokens (identity governance), not by editing
consumption history. Any implementation of binding lifecycle records the
ruling here first.

## D24 — Workbench Projection Rule (v1.1.x scoping, RATIFIED)
> Workbench views may project, aggregate, filter, sort, and derive
> existing governed facts.
>
> Workbench views may not become authoritative sources of governed state.
>
> No workbench screen may require persistence of information that is
> derivable from existing governed facts.
>
> New computed read endpoints are permitted when they compose or expose
> projections of governed facts.
>
> Workbench implementation must not add tables, writable columns, cached
> rankings, saved comparisons, dashboard-owned status flags, or persisted
> inbox items.
>
> If a workbench screen disappears entirely, no governed fact may be lost.

D1 ("persist facts, compute operational views") applied to the operator
surface. The UI door is where leaderboard disease would re-enter: systems
that start with computed views reintroduce a second source of truth
through cached rankings, saved comparisons, dashboard state tables, and
persisted inbox items. D24 closes that door for the workbench milestone
and every milestone after it.

Companion rulings made at the same scoping session (binding, recorded in
docs/workbench-v1.1x.md):
- **A top-level Consumption area** (Selection Workbench, Consumption
  Inbox, Binding Explorer) — not an Agent Center subpage; consumption is
  a first-class lifecycle. Agent Center stays identity/MCP/tool-facing;
  Consumption is package/model/binding-facing. D8 satisfied by genuine
  plurality.
- **Consumption Inbox severity follows D2 discipline** — one shared
  severity function; HIGH = a binding is currently unsafe or
  unverifiable, MEDIUM = a selection may need review, LOW = consumption
  hygiene. Every item computed at read time, never stored.
- **Lineage is one server-composed endpoint** — the chain is a product
  claim, not a UI convenience. Every expected hop either resolves or is
  explicitly declared missing; no silent gaps (D12 posture).
- **The existing model-selection PUT is the only write permitted in the
  milestone.** No binding withdrawal (D23 stays deferred), no new
  lifecycle, no new permissions.

**Why:** a persisted view is a second state machine that drifts (D1); the
workbench is the surface with the strongest temptation to persist —
rankings, comparisons, staleness flags — and the erosion would be
invisible screen by screen. A structural rule survives where per-screen
judgment would not.
**Tradeoff accepted:** every workbench load recomputes its projections —
no caching layer, no precomputed dashboard state. Performance is bought
with query work, never with persisted copies of governed facts.
**Enforcement:** structural, in CI, permanent — the way D18's seam suite
and D20's purity assertions guard their boundaries:
`backend/test_workbench_projection.py` freezes the v1.1.0 schema (every
table, every column) and fails on ANY divergence, additions and removals
alike. Stronger than checking a milestone diff: a future milestone that
legitimately changes the schema updates the frozen snapshot alongside the
ratified decision that justifies it, in the same commit — never silently.
**Evidence:** backend/test_workbench_projection.py (in CI).

## D25 — Credential Custody (v1.2.0 scoping, RATIFIED)
> Outbound credentials are governed secrets: stored encrypted, never
> returned by any API, never exported in any artifact or projection,
> never written into audit events or logs. The audit ledger records
> custody events — created, rotated, revoked, used — never contents.
> Configuration and connectors reference credentials by id; they never
> contain them. The permission scope granted to a credential is custody
> evidence: recorded at creation, carried on use events, never inferred.
>
> Routes and connectors propose credential use; the custody layer
> decides release.

The D9 hard rule (".empkg never contains keys") generalized to the whole
platform, and the D17/D18/D19/D20 family shape applied a fifth time. The
sharpest statement of the distinction: **outbound credential plaintext is
not a governed fact; custody events are governed facts.** The system
governs the existence, ownership, use, rotation, and revocation of the
secret — never the secret value itself.

The two credential species stay in separate tables: the v1.0
`credentials` table's hash-only contract is a security property and is
never overloaded. Outbound secrets live in `external_credentials`
(encrypted-at-rest, revoke-never-delete lineage, non-nullable creation
identity fact). One asymmetry is constitutional: inbound secrets are
minted by EM and shown once at issuance; outbound secrets are supplied BY
the operator, so no surface ever returns one — "never", not "once".

Companion rulings made at the same scoping session (binding, recorded in
docs/credentials-cloud-connector-v1.2.md):
- **Envelope encryption under an env master key** (`EM_SECRET_KEY`, the
  D19 tier; OS keystore/KMS is a later enterprise extension) — master-key
  rotation re-wraps data keys; no secret is ever re-entered. Recovery
  from key loss is a documented procedure, never a bypass (D21 posture).
- **A new 12th permission, `credentials:manage`, ADMIN-only** — custody
  must not ride on `connectors:manage`, which KNOWLEDGE_OPERATOR (and
  therefore SERVICE principals) may hold. Administering a credential and
  using one are separate layers: a scan proposes use; the custody layer
  decides release and writes `CREDENTIAL_USED` (per scan, not per HTTP
  request).
- **LLM provider keys deferred**: the store is generic
  (`purpose = CONNECTOR | PROVIDER`) but migrating OPENAI/ANTHROPIC keys
  is a separate later step — it touches D19's resolution invariant. D19
  holds unchanged until that explicit decision.
- **SharePoint gate evidence**: fake Graph transport in CI (the D18
  `fake://` pattern) + ONE manual live-tenant scan recorded at the gate.

**Why:** half-governed secrets would give false assurance exactly as
half-built auth would (D14's reasoning, completing what D19 deferred);
and a secret that can be read back through any surface is not in custody
— it is merely stored.
**Tradeoff accepted:** no reveal endpoint means a lost secret is
re-entered by rotation, never recovered; every credential surface pays
the metadata-only discipline; the env master key is a single trust
anchor until the enterprise keystore extension.
**Enforcement:** structural, in CI, permanent —
`backend/test_credential_custody.py` seeds a sentinel secret and
adversarially sweeps every surface (API responses, audit payloads, logs,
exports, projections, error paths); any hit fails CI. Schema changes land
with the D24 frozen-snapshot update in the same commit, citing this
decision.
**Evidence:** to be recorded at the WS gates
(docs/credentials-cloud-connector-v1.2.md): the custody sweep (WS0), the
Alice test for secrets + the 12-permission authorization grid (WS1), the
unchanged-framework SharePoint proof (WS2).
