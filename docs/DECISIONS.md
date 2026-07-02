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
  decides release and writes `EXTERNAL_CREDENTIAL_USED` (per scan, not
  per HTTP request; the event family is `EXTERNAL_CREDENTIAL_*` because
  `CREDENTIAL_*` already names v1.0 inbound lineage events).
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
**Evidence:** recorded at the four WS gates, all PASSED
(docs/credentials-cloud-connector-v1.2.md):
backend/test_credential_custody.py (WS0 sentinel sweep + adversarial
self-proof; WS1 Alice test for secrets, route-level sweep, master-key
re-wrap with byte-identical ciphertexts), test_authorization.py (the
12-permission grid), test_sharepoint_provider.py (WS2
unchanged-framework proof over a fake Graph tenant; the live-tenant run
is an honest pending append), and the WS3 in-browser verification
(surface-level sentinel discipline; secret entered once, never
displayed). v1.2.0 released with all guards in CI permanently.

## D26 — Review by Exception (v1.2.1 scoping, RATIFIED)
> Ingestion automation approves only by declared policy conditions over
> recorded evidence: source-authority metadata the company already
> validated (Tier-0), or engine verdicts (Tier-2). Coverage is
> deny-by-default — a policy names the asset types, sources, and domains
> it covers, never "everything else". Every document that does not reach
> APPROVED automatically is a declared, severity-ranked exception; no
> document is silently held.
>
> Automation applies to new CANDIDATE assets only, through the one
> approval transition path. Candidate revisions are never auto-approved.

D5 ("gate deployment, never ingestion") supplied the principle; this
milestone supplies the machinery. The honest hierarchy of the tiers,
ruled at scoping: **Tier-0 inherits an authority the company already
paid for; Tier-2 can only report absence of alarm** — engines refuse to
approve, only humans refuse content. A contradicted candidate is a
declared exception holding for review, never an engine rejection. The
≥90%-untouched target is a mature-corpus target carried by Tier-0;
Tier-2 widens its reach, never replaces it.

Companion rulings (binding, recorded in
docs/ingestion-automation-v1.2.1.md):
- **Tier-0 evidence must survive**: verbatim provider discovery metadata
  is persisted per scan on SourceDocument (a genuine D1 fact — it
  survives nowhere else; legacy rows honestly NULL, never backfilled).
  Tier-0 provenance quotes the matched authority metadata VERBATIM;
  conditions referencing absent metadata never fire — absence is not
  satisfaction (D12).
- **Tier-2 consults the candidate-contradiction check only** this
  milestone: NLI of the candidate against the approved corpus, async per
  D4, conflict-engine calibration discipline, dropped pairs declared.
  Claim decomposition/verification of candidates is deferred — it has no
  honest evidence target. Engine verdicts live in event provenance, never
  as AssetRelationship rows — candidate checks must not pollute the
  approved-conflict surfaces or the conflict score.
- **NULL-condition invariant** (the D19 shape): approval policies without
  Tier-0/Tier-2 conditions behave exactly as v0.10.2 — new condition
  machinery changes nothing by existing.
- **Exceptions are computed inbox items** (D1/D24, no dismiss), MEDIUM at
  most — ingestion exceptions never block the compile gate, so they are
  never HIGH (D2).

**Why:** per-document human validation is a non-workable barrier at
enterprise corpus scale, but automation that infers authority (rather
than inheriting or evidencing it) would reintroduce the "trust me" the
platform exists to remove. The company paid the validation cost once in
its source system; EM must not charge it twice — and must be able to
prove, indefinitely, exactly which recorded evidence carried each
automatic approval.
**Tradeoff accepted:** the framework persists discovery metadata for
every scanned item whether or not any policy consumes it; Tier-2 buys
safety with NLI compute at ingestion time; messy corpora without source
authority metadata start well below the target and climb by policy
tuning, never by loosened discipline.
**Enforcement:** structural, in CI, permanent —
`backend/test_ingestion_automation_guard.py`: exactly one approval
transition path (every auto-approval resolves to
`crud.update_knowledge_asset`), and the adversarial sentinel: a candidate
REVISION under the most permissive policy set constructible is still
pending after all background tasks complete. Adversarially self-proven at
the WS0 gate (planted second path + planted revision auto-approval must
both be caught).
**Evidence:** recorded at the WS gates in
docs/ingestion-automation-v1.2.1.md as each is accepted.

## D27 — Domain Taxonomy (v1.2.1 scoping, RATIFIED)
> Assets carry a governed hierarchical domain path, assigned at ingestion
> by versioned classification policies and correctable by humans through
> the normal review surface. Domains are business dimensions, orthogonal
> to asset types — never siblings in any hierarchy. Reorganizations nest
> by default; replacement is an explicit audited taxonomy operation
> recording the old→new mapping. The taxonomy lives in the database as
> governed metadata; folders, graphs, and vaults only ever render it —
> moving a rendered file never reclassifies anything.

Companion rulings (binding, recorded in
docs/ingestion-automation-v1.2.1.md):
- **Path column + audited operations, no registry table** (D1): domain
  assignments live on assets; reorg mappings live in
  TAXONOMY_REORGANIZED audit events; a registry is earned later by real
  validation pressure, if ever. Unclassified is honestly NULL (D12),
  never fabricated as "general".
- **ClassificationPolicy is its own governed object** (the D17 shape:
  versioned, no delete, audited enable/disable), separate from
  ApprovalPolicy — assigning a domain and granting APPROVED are different
  outcome species; their provenance and version counters never blur.
- **Deterministic assignment**: enabled policies in id order, first
  matching rule assigns; every assignment writes ASSET_CLASSIFIED with
  the policy snapshot that fired; human corrections are governed acts
  (ASSET_DOMAIN_CORRECTED), not edits.
- **No new permission**: classification-policy administration and
  taxonomy operations ride under `assets:approve`, which already governs
  approval policies. The 12-permission matrix is unchanged.
- **Transactional records are not knowledge assets** — EM governs what
  the company knows, not every record it has; the scope trap is refused
  deliberately, not accidentally.

**Why:** every later consumer of the taxonomy — Tier-2 sensitivity
coverage (this milestone), graph groupings (v1.3), workbench scopes
(v1.4), vault folders (v1.5) — needs a single authoritative business
dimension that renderings can never mutate. Prefix-path semantics make
nesting reorganizations free, so future scopes and clearances survive
splits by construction (D24 posture applied to taxonomy).
**Tradeoff accepted:** no referential validation of domain values in this
milestone — a typo'd correction creates a new leaf rather than an error;
the audited reorg operation is the repair path.
**Evidence:** the WS1 taxonomy-proof gate in
docs/ingestion-automation-v1.2.1.md (split `finances` by policy change +
reorg operation alone; provenance intact, content and history untouched,
prefix queries still resolve the parent).

## D28 — The Projection Rule (v1.3.0 scoping, RATIFIED)
> A projection is a governed lens over the knowledge system, never
> another knowledge system.
>
> No projection is ever authoritative. Every rendered artifact
> regenerates entirely from governed facts, and every rendered artifact
> may be deleted without losing any governed fact. Every render is
> stamped with `rendered_at` and the audit cursor it projected, is
> clearance-filtered before rendering with exclusions declared, and has
> its manifest hash recorded in the ledger — a render is verifiable
> evidence of what was projected, never a source of what is true.
> Staleness is computed, detectable, never silent.
>
> Nothing flows back. Editing, moving, or deleting a rendered artifact
> changes no governed fact; rendered files re-enter the system only as
> ordinary documents through connectors, never through any projection
> path. Renderers present; the projection engine decides: a renderer
> receives a completed, clearance-filtered projection and chooses only
> its shape on disk — it never queries governed state, never filters,
> never decides content.

The family principle's sixth instance (D17/D18/D19/D20/D25): *renderers
propose presentation; the projection engine decides content.* D24
extended past the process boundary — D24 governed computed views that
live in memory; D28 governs projections that become files and therefore
outlive the request, travel, and tempt someone to treat them as truth.
D27 stated the special case ("folders, graphs, and vaults only ever
render the taxonomy"); D28 is the general law.

Companion rulings made at the same scoping session (binding, recorded in
docs/projection-engine-v1.3.md):
- **Zero schema change** — renders are recorded as `PROJECTION_RENDERED`
  audit events (renderer, scope, status set, clearance, cursor, counts,
  manifest hash); no ProjectionRun table, no render registry. The D24
  snapshot survives the milestone byte-identical, asserted at the gate.
- **File renders ride `assets:approve`** (the .empkg act-class); live
  graph queries ride `assets:read` / `mcp:consume`. The 12-permission
  matrix is unchanged.
- **Nodes carry metadata + a bounded excerpt, never full content** —
  the .empkg is the content artifact, the graph is the structure
  artifact (D9 posture; the species never blur).
- **Status scope is a declared render parameter, default APPROVED-only**
  — the inclusion set recorded in manifest + event, never silent (D12).
- **The D10 split extends to projections**: MCP graph tools = GOVERNED
  channel (live, per-node clearance, audited refusals); rendered files =
  PORTABLE channel (verifiable snapshot, no live enforcement).
- **Domains are the grouping dimension** (D27 consumed): no community
  detection, no LLM labeling; graphify's LLM extraction is explicitly
  not adopted.
- **Renders are self-contained**: vendored vis-network, no CDN, no
  network access from a rendered artifact (deviation from graphify
  as-is, which loads from unpkg).
- **UI inside existing areas**; a top-level Projections surface is
  earned at v1.5 by the second renderer (D8).

**Why:** the Operations Realm (v1.4+) needs relational, renderable
access to governed knowledge — but every rendered file is an invitation
to treat the copy as the truth. A rule + structural guard at the first
renderer closes that door before workbenches and vaults multiply the
temptation, exactly as D24 closed it for the operator UI.
**Tradeoff accepted:** every render recomputes from governed facts — no
incremental render cache, no persisted graph; performance is bought with
query work. A lost render is regenerated, never restored.
**Enforcement:** structural, in CI, permanent —
`backend/test_projection_guard.py`: projection modules cannot write
governed state (AST sweep), renderers import stdlib + the projection
contract only, rendered artifacts cannot flow back (read-back sentinel),
stamps are mandatory; adversarially self-proven at the WS0 gate.
**Evidence:** recorded at the WS gates in docs/projection-engine-v1.3.md
as each is accepted.

## D29 — The One-Way Valve (v1.4.0 scoping, RATIFIED)
> Agent outputs cannot become canonical facts directly. Everything an
> agent diagnoses, recommends, synthesizes, or infers enters governed
> knowledge only through the proposal lane: agent finding → proposal
> document → connector ingestion → CANDIDATE → human gate → DERIVED
> fact. There is no second door: no agent principal, workbench result,
> diagnostic output, or MCP/tool return can write APPROVED knowledge or
> any canonical fact state.
>
> The valve constrains agents, not people. Human decisions enter as
> ordinary documents and become PRIMARY facts; the valve adds no
> friction to human authorship.
>
> Proposal-lane candidates are never auto-approved. No policy tier —
> Tier-0, Tier-2, or any future tier — applies to them; the human gate
> on agent-proposed knowledge is constitutional, not configurable.

The family principle's seventh instance (D17/D18/D19/D20/D25/D28):
*agents propose knowledge; the human gate decides facts.* D15 stays
absolute in the Knowledge Realm — extract and verify, never synthesize.
Synthesis is the workbench's product, and the valve is what lets D15
and synthesis coexist: EM extracts and verifies the proposal *document*
exactly as it would any document; the proposal is evidence, not truth,
until a human rules. The Operations Realm opens through this valve, or
not at all.

The lane-sentinel clause (third paragraph) is the heart of the ruling:
it forecloses the dangerous future shortcut — "trusted agent
auto-accept." If agent-proposed knowledge is ever to be auto-approved,
that requires an explicit superseding decision recorded in this
register, never a policy configuration change. The known configuration
hole it closes: approval policies with `connector_id = NULL` apply to
all connectors, so without the sentinel a global permissive policy
would silently delete the human gate on agent output.

Companion rulings made at the same scoping session (binding, recorded
in docs/diagnostic-workbench-v1.4.md):
- **The workbench is a reference consumer, never a subsystem** (D22
  held): it lives at top-level `workbench/`, outside `backend/`
  entirely. Its only doors are the existing ones — the .empkg via
  `package_consumer`, the MCP server as a real client at a real AGENT
  token's clearance, and file writes into the vault. Nothing under
  `backend/app/` imports workbench code.
- **Vault skeleton** under `EM_VAULT_DIR` (the EM_PACKAGE_DIR /
  EM_PROJECTION_DIR pattern): `/00_system` is static, repo-versioned
  contract material this milestone — NOT a projection render
  (vault-as-renderer is v1.5; folders 01–06 are reserved for it);
  `/07_agent_workspaces` is ungoverned scratch, never scanned;
  `/08_proposals` is the only agent-writable governed ingress, watched
  by ONE PROPOSAL-lane LocalFolderProvider connector — the existing
  pipeline, zero new ingestion channels.
- **Language rulings**: "proposal", "finding", "accepted as DERIVED",
  "held for review", "primary prevails", "agent-synthesized", "human
  accepted" — never "agent-approved", "auto-accepted", "derived is
  wrong", "rejected by the engine", "synced into knowledge", or "agent
  wrote a fact".

**Why:** the Operations Realm's product is synthesis, and synthesis
that can write itself into canon is self-reinforcement — the "trust
me" the platform exists to remove, re-entering through agents. Six
months after an agent's finding becomes an APPROVED fact, the system
must prove which agent synthesized it, under which binding, from which
package hash, citing which governed evidence, and which human accepted
it — and prove no path existed by which the finding could have entered
without that human.
**Tradeoff accepted:** the valve is enforced at EM's boundary. An
agent given filesystem write access to a PRIMARY-lane watched folder
defeats it at deployment level — exactly as filesystem access to
SQLite defeats the identity boundary (D21 posture: workspace
discipline is deployment contract, documented in /00_system; EM proves
everything within its boundary). And every agent finding pays the full
document pipeline plus human-gate latency — the friction is the
feature, never an optimization target.
**Enforcement:** structural, in CI, permanent —
`backend/test_agent_authorship_guard.py` (Guard 5, the fifth permanent
guard family, built at WS0 before any workbench code exists): AGENT
principals frozen to `AGENT_CONSUMER` = `{mcp:consume}` with every
write route refused and audited; the MCP surface writes nothing (AST
sweep); THE LANE SENTINEL — under the most permissive policy
environment constructible (global NULL-connector policy, satisfied
Tier-0 conditions, a live approve-everything Tier-2 engine), a
proposal-lane candidate is still PENDING after all background tasks
complete; no cross-lane mutation (a proposal colliding by (type, name)
with a PRIMARY asset creates a new CANDIDATE, never a candidate
revision of it); workbench isolation swept the moment `workbench/`
exists; adversarially self-proven.
**Evidence:** recorded at the WS gates in
docs/diagnostic-workbench-v1.4.md as each is accepted.

## D30 — Derived Source Class (v1.4.0 scoping, RATIFIED)
> Every knowledge asset carries a source class: PRIMARY (human-authored
> or human-adopted knowledge) or DERIVED (agent-synthesized knowledge
> accepted by a human through the proposal lane). The class is decided
> by the ingestion channel, never claimed by document content: assets
> extracted from a proposal-lane connector are DERIVED; everything else
> is PRIMARY. A DERIVED fact carries complete synthesis provenance —
> agent principal, binding, package hash, cited governed evidence,
> accepting human — verified against governed records at the gate,
> never trusted from the claim.
>
> Primary prevails over derived: a conflict between a PRIMARY and a
> DERIVED fact is never resolved in favor of the DERIVED side by any
> automatic mechanism, and the class asymmetry is declared wherever the
> conflict is surfaced. DERIVED facts are ordinary APPROVED knowledge in
> every other respect — retrievable, packageable, renderable — and their
> class travels with them into every package, projection, citation, and
> MCP response, so derivation is always visible to every consumer.

D29 governs how agent output may re-enter governed knowledge; D30
governs what accepted agent-synthesized knowledge becomes. They are
deliberately separate laws: a future change to DERIVED handling must
not weaken the valve, and a future valve hardening must not require
redefining source classes.

The channel-decides-class rule is the D20 shape applied to authorship:
the proposal document *proposes* its provenance in frontmatter; the
lane and the gate *decide* the class and verify the provenance. A
proposal claiming to be PRIMARY is still DERIVED; a PRIMARY-lane
document claiming agent provenance stays PRIMARY.

Companion rulings made at the same scoping session (binding, recorded
in docs/diagnostic-workbench-v1.4.md):
- **Exactly two columns** — `KnowledgeAsset.source_class TEXT NOT NULL
  DEFAULT 'PRIMARY'` and `SourceConnector.lane TEXT NOT NULL DEFAULT
  'PRIMARY'` (`PRIMARY` | `PROPOSAL`). The D24 frozen snapshot moves
  28 tables / 303 columns → 28 tables / 305 columns in the WS0 commit,
  citing D29+D30 — a real schema milestone, recorded openly (the
  deliberate contrast with v1.3.0's zero).
- **Legacy is PRIMARY by construction, not reconstruction**: before
  v1.4 no agent-writable ingress existed, so the default is a
  derivable truth, never a backfilled guess (D12 satisfied).
- **Synthesis provenance needs no columns** (D1): the proposal
  document is immutable evidence (the frontmatter lives inside the
  content-hashed document), verification results and the
  verbatim-quoted provenance ride the approval event (the D26 Tier-0
  pattern), and the accepting human is already the AssetReview +
  IdentityFact.
- **Provenance is verified, never trusted**: the claimed binding must
  exist, belong to the claimed agent principal, and match the claimed
  package hash, checked against governed records at ingestion and
  quoted verbatim at approval. Unverifiable provenance is a computed
  exception (`PROPOSAL_PROVENANCE_UNVERIFIED`, MEDIUM at most per D2,
  no dismiss) — held loudly, never silently, never rejected by the
  engine.
- **Primary-prevails mechanics**: the class asymmetry is declared on
  every PRIMARY×DERIVED conflict pair; review surfaces present the
  DERIVED side as the presumptive review target; nothing auto-resolves
  — humans confirm/dismiss exactly as today; the compile gate treats
  these conflicts identically (a blocking contradiction blocks, no
  special case).
- **Class-travels-everywhere is the anti-inbreeding measure**: an
  agent reading a DERIVED fact and synthesizing atop it cannot be
  prevented — but every DERIVED fact cites the governed evidence it
  drew from, so derivation depth is computable and second-generation
  synthesis is visible at the gate. Discipline through provenance,
  never through access denial.

**Why:** accepted synthesis must never be mistakable for
human-authored knowledge — at the review gate, in a package, in a
graph, or in an agent's citation. The alternative failure mode is
knowledge inbreeding: agent output laundered into canon, consumed by
agents, and re-synthesized with its origin erased.
**Tradeoff accepted:** a two-value vocabulary (no CURATED/SECONDARY
classes until real pressure earns them); DERIVED facts are not
access-restricted — the control is visible derivation, not denial.
**Enforcement:** structural, in CI, permanent — Guard 5 sweeps
`source_class` assignment (only the allowlisted channel-derivation
path may write it; frontmatter-decided class is a planted-and-caught
violation); the D24 snapshot asserts the two-column shape; class-travel
asserted at the WS2 gate on every consumer channel.
**Evidence:** recorded at the WS gates in
docs/diagnostic-workbench-v1.4.md as each is accepted.

## D31 — Render Authority Dies at Ingress (v1.5 scoping, RATIFIED)
> Render authority dies at ingress. Rendered knowledge may be copied,
> moved, or submitted, but no property of a render — its stamps, its
> manifest, its provenance annotations, its placement in the vault —
> survives as authority when its content re-enters the governed system.
> A rendered file re-enters only as an ordinary document through an
> ingestion channel; through the proposal lane it becomes at most a
> held DERIVED candidate whose provenance is verified or honestly
> declared unverifiable — never a PRIMARY fact, never auto-approved,
> never canonical by accident.
>
> The vault is one tree with two natures, and they never blur. Folders
> the renderer manages are disposable projection output: deleted and
> regenerated wholesale, never read back, never inputs. Folders agents
> and humans write are inputs: never touched by any renderer. No path
> exists by which regeneration destroys an input or ingestion trusts
> an output.

D28 protects the output direction (rendered files never flow back);
D29 protects the input direction (agent findings enter only through
the proposal lane and human gate). D31 governs the ground where the
two directions become adjacent: the EM Vault, one tree holding
projection output (managed folders 01–06) beside governed ingress
(08_proposals) and ungoverned scratch (07_agent_workspaces). The law
forecloses the laundering path — a projection re-entering the system
dressed as knowledge — and the destruction path — a wholesale render
regeneration deleting an agent's pending proposal.

Companion rulings made at the same scoping session (binding, recorded
in docs/em-vault-v1.5.md):
- **The vault is a content artifact** — an explicit amendment to v1.3
  scoping ruling 3: the vault joins the .empkg as a content species
  (a workspace of excerpts is not human-readable knowledge); the graph
  remains the structure artifact. The projection contract grows ONE
  declared field for content mode; a renderer must declare that it
  needs full content, the declaration appears in the manifest and the
  PROJECTION_RENDERED event, and clearance filtering applies before
  content reaches notes.
- **The vault renderer writes directly into its managed folders** —
  `EM_VAULT_DIR/01_start · 02_knowledge · 03_experts · 04_packages ·
  05_conflicts · 06_governance` — never render-elsewhere-and-copy (a
  copy step is an ungoverned transfer path, weaker on exactly the
  laundering axis this milestone closes). Each managed folder is
  deleted and regenerated wholesale per render.
- **The untouchable floor is constitutional**: `00_system`,
  `07_agent_workspaces`, `08_proposals` — no render path may delete,
  overwrite, scan-as-render-state, or manage those folders.
- **The sixth permanent guard family**:
  `backend/test_render_ingress_guard.py`, deliberately NOT folded into
  the D28 or D29 guards — new seam territory earns its own boundary.
  Its cornerstone plant: render a file → drop it into /08_proposals →
  scan under permissive policies → it becomes only a held DERIVED
  candidate with unverifiable or declared provenance — never PRIMARY,
  never auto-approved, never replaying manifest authority, never
  generating projection authority from its stamps.
- **Obsidian compatibility means plain Markdown, YAML frontmatter,
  wikilinks, deterministic bytes** — no `.obsidian`, no plugins, no
  Git machinery (Git-trackability is a property of determinism, not a
  feature).
- **Language rulings**: "rendered note", "vault render", "managed
  folders", "untouchable folders", "render authority dies at ingress",
  "ordinary proposal evidence", "held DERIVED candidate",
  "unverifiable provenance" — never "sync back", "vault source",
  "rendered truth", "trusted note", "promoted from vault", or
  "Obsidian database".

**Why:** every rendered file is an invitation to treat the copy as
the truth (D28's warning), and the vault multiplies the temptation by
putting thousands of readable, movable knowledge notes one folder away
from the governed ingress. Without D31, the valve could be defeated by
a file move — no agent privilege required, no guard tripped, just a
projection re-entering as if it were knowledge. The law makes the file
move safe instead of forbidden: whatever enters 08 is ordinary
proposal evidence behind the valve, full stop.
**Tradeoff accepted:** rendered knowledge is deliberately easy to
re-submit — a human quoting a vault note into a proposal is a
legitimate workflow, and it costs the full document pipeline plus the
human gate every time; no fast path exists or will. The vault renderer
pays the managed-folder discipline (wholesale regeneration confined to
01–06), and one vault renders FOR one declared clearance per render.
**Enforcement:** structural, in CI, permanent —
`backend/test_render_ingress_guard.py` (the sixth guard family, built
at WS0 before the vault renderer exists): THE LAUNDERING PLANT
end-to-end; regeneration isolation (planted files in the untouchable
folders survive wholesale regeneration); path discipline (within
backend/app, EM_VAULT_DIR and the untouchable folder names are
confined to the projection package's floor machinery); authority death
(ingested stamps and cursor claims are inert, verification treats them
as unrecognized claims); adversarially self-proven.
**Evidence:** recorded at the WS gates in docs/em-vault-v1.5.md as
each is accepted.
