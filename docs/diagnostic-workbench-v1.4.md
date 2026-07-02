# v1.4.0 — First Diagnostic Workbench Pilot: Build Contract

> Scoped and ratified July 2026 (rulings **D29 — The One-Way Valve** and
> **D30 — Derived Source Class** in docs/DECISIONS.md). Input briefs:
> PROJECT_STATE.md, docs/DECISIONS.md (through D28), docs/roadmap.md
> ("The road to the Operations Realm"), and the gate records in
> docs/projection-engine-v1.3.md. This is the build contract:
> workstreams, gates, and the boundaries that hold. Gate records are
> appended here as each workstream is accepted.

## The milestone in one sentence

The Operations Realm opens: a bound agent diagnoses a real corpus
through existing doors and its finding re-enters the Knowledge Realm as
a DERIVED fact — through the proposal lane, past a human gate, with
complete verifiable provenance — while a permanent guard proves no
agent output can ever become canonical any other way.

## The opening question (evidence-first, per tradition)

> Six months after an agent's finding becomes an APPROVED fact, the
> system must prove: which agent synthesized it, under which binding,
> from which package hash, citing which governed evidence, and which
> human accepted it — and must prove that no path existed by which the
> finding could have entered without that human. If any link is "the
> agent said so," the model is too shallow.

The answer is D29 + D30: agent findings enter only through the proposal
lane past a human gate (the valve), and what they become is a DERIVED
fact whose class is channel-decided and whose synthesis provenance is
verified against governed records, never trusted from the claim.

## Scoping rulings (settled at the session, user-ratified)

1. **Two laws, deliberately separate.** D29 governs how agent output
   may re-enter governed knowledge; D30 governs what accepted
   agent-synthesized knowledge becomes. A future change to DERIVED
   handling must not weaken the valve; a future valve hardening must
   not require redefining source classes.
2. **The lane sentinel is constitutional, not configurable.**
   Proposal-lane candidates are never auto-approved; no policy tier —
   Tier-0, Tier-2, or any future tier — applies to them. "Trusted
   agent auto-accept" can only ever arrive as an explicit superseding
   decision in the register, never as a policy configuration change.
   The known hole this closes: approval policies with
   `connector_id = NULL` apply to ALL connectors (policy.py), so a
   global permissive policy would otherwise silently delete the human
   gate on agent output.
3. **A real schema milestone, recorded openly** (the deliberate
   contrast with v1.3.0's zero): exactly two columns —
   `KnowledgeAsset.source_class TEXT NOT NULL DEFAULT 'PRIMARY'` and
   `SourceConnector.lane TEXT NOT NULL DEFAULT 'PRIMARY'`
   (`PRIMARY` | `PROPOSAL`). The D24 frozen snapshot moves
   28 tables / 303 columns → **28 tables / 305 columns** in the WS0
   commit, citing D29+D30. Legacy assets are PRIMARY **by
   construction, not reconstruction** — before v1.4 no agent-writable
   ingress existed (D12 satisfied without backfill guesswork).
4. **Channel decides class** (the D20 shape applied to authorship):
   frontmatter proposes provenance; the lane and the gate decide. A
   proposal claiming `source_class: PRIMARY` is still DERIVED; a
   PRIMARY-lane document claiming agent provenance stays PRIMARY.
5. **Synthesis provenance needs no columns** (D1): the proposal
   document is immutable evidence (frontmatter lives inside the
   content-hashed document); verification results and verbatim-quoted
   provenance ride the approval event (the D26 Tier-0 pattern); the
   accepting human is already the AssetReview + IdentityFact.
   Unverifiable provenance is a computed exception
   (`PROPOSAL_PROVENANCE_UNVERIFIED`, MEDIUM at most per D2, no
   dismiss) — held loudly, never silently, never rejected by the
   engine.
6. **Primary prevails over derived**: class asymmetry declared on
   every PRIMARY×DERIVED conflict pair; the DERIVED side is the
   presumptive review target; nothing auto-resolves (humans
   confirm/dismiss exactly as today); the compile gate treats these
   conflicts identically — a blocking contradiction blocks, no special
   case.
7. **Class travels everywhere** — .empkg asset records, projection
   nodes, MCP tool responses, citations — so derivation depth is
   computable and second-generation synthesis is visible at the gate.
   Anti-inbreeding through provenance, never through access denial.
8. **The workbench is a reference consumer, never a subsystem** (D22
   held): top-level `workbench/`, outside `backend/` entirely. Doors:
   the .empkg via `package_consumer`, the MCP server as a real client
   at a real AGENT token's clearance, file writes into the vault.
   Nothing under `backend/app/` imports workbench code. EM binds;
   customers execute; this pilot is the reference consumer.
9. **Vault skeleton** under `EM_VAULT_DIR` (the EM_PACKAGE_DIR /
   EM_PROJECTION_DIR pattern): `/00_system` = static, repo-versioned
   contract material (NOT a projection render; vault-as-renderer is
   v1.5, folders 01–06 reserved); `/07_agent_workspaces` = ungoverned
   scratch, never scanned; `/08_proposals` = the only agent-writable
   governed ingress, watched by ONE PROPOSAL-lane LocalFolderProvider
   connector — the existing pipeline, zero new ingestion channels.
10. **Deterministic CI, honest live slot** (the D18 `fake://` / D26
    fake-engine / D25 live-tenant pattern): the workbench's synthesis
    sits behind an injectable seam; CI runs a deterministic fake
    diagnosis; the ONE real-model diagnostic run (D19 resolver; the
    Anthropic adapter is legal since v1.1) is recorded at the WS4 gate
    — pending honestly if it cannot run at acceptance, never silently
    skipped.
11. **UI inside existing areas** (D8): one workbench earns no
    top-level Workbenches area. DERIVED badge + synthesis provenance
    on asset cards, class asymmetry on conflict cards, the new
    exception kind in the Governance Inbox.
12. **Language rulings**: "proposal", "finding", "accepted as
    DERIVED", "held for review", "primary prevails",
    "agent-synthesized", "human accepted" — never "agent-approved",
    "auto-accepted", "derived is wrong", "rejected by the engine",
    "synced into knowledge", "agent wrote a fact".

## Key discovered facts (grounding, pre-contract)

- **AGENT principals are already structurally powerless over REST**:
  kind-locked to `AGENT_CONSUMER` (`ALLOWED_ROLES_BY_KIND`), which
  holds exactly `{mcp:consume}` (identity.py). Guard 5 freezes this —
  the valve's REST half is proven structure, not new machinery.
- **The one open hole is policy scope**: `policies_for_scope` applies
  `connector_id = NULL` policies to every connector (policy.py) — a
  global permissive policy would auto-approve proposal-lane
  candidates today. The lane sentinel closes it at WS0.
- **D7 reconciliation is connector-scoped**: a proposal document
  cannot reach the revision machinery of a PRIMARY asset through
  (type, name) collision — asserted by Guard 5, not assumed.
- **The proposal lane already exists as infrastructure**:
  LocalFolderProvider + scan-now ingestion + CANDIDATE review is the
  v0.10/D6 pipeline unchanged; v1.4 adds a lane declaration and a
  human-gate constitution on top, no new ingestion channel.
- **The workbench's read doors already exist**: the .empkg consumer
  (v1.1 WS1), MCP graph tools (v1.3 WS3 — the agents' relational
  access), and D27 domain prefixes (their scoping dimension).

## Schema changes

Two columns, both genuine D1 facts (queryable dimensions consumed by
conflict discipline, packages, projections, MCP):

| Table | Column | Shape |
|---|---|---|
| `knowledge_assets` | `source_class` | TEXT NOT NULL DEFAULT `'PRIMARY'` (`PRIMARY` \| `DERIVED`) |
| `source_connectors` | `lane` | TEXT NOT NULL DEFAULT `'PRIMARY'` (`PRIMARY` \| `PROPOSAL`) |

D24 snapshot: 28 tables / 303 columns → **28 tables / 305 columns**,
updated in the WS0 commit citing D29+D30. Any further column or table
discovered "necessary" during build is a design failure to be
escalated, not a gate-recorded addition.

## Module map (planned)

| Module | Role |
|---|---|
| `app/policy.py` | grows the lane sentinel floor (WS0): proposal-lane candidates are structurally outside every policy tier — declared, never silent |
| `app/proposals.py` (WS1) | the proposal lane: frontmatter parsing, governed provenance verification (binding exists, belongs to the claimed principal, package hash matches), channel-derived `source_class` assignment — the ONLY writer of the class |
| `app/governance_inbox.py` | grows `PROPOSAL_PROVENANCE_UNVERIFIED` (sixth ingestion-exception kind, MEDIUM at most, no dismiss) |
| `app/conflict_engine.py` | class asymmetry on PRIMARY×DERIVED pairs (WS2); no scoring change — declaration, not weight |
| `app/package_builder.py` / `app/projections/engine.py` / `app/mcp_gateway.py` / `app/query_engine.py` | class travels: .empkg records, projection nodes, MCP responses, citations (WS2) |
| `workbench/onboarding_diagnostic.py` (top-level, outside backend/) | the reference consumer: consumes .empkg + MCP at AGENT clearance, synthesizes behind an injectable seam, writes proposal documents with provenance frontmatter to /08_proposals ONLY |
| `vault/00_system/` (repo-versioned material) | the vault contract: the valve, the lanes, workspace discipline — deployed to EM_VAULT_DIR by a bootstrap helper |

## Workstreams

### WS0 — D29 + D30 + Guard 5 + schema (before any workbench code)

One commit: the two columns (additive `_ensure_columns` migration),
the D24 snapshot update to 28/305 citing D29+D30, the lane-sentinel
floor in policy.py (proposal-lane candidates structurally outside
every tier, their holds declared), and the fifth permanent guard:

`backend/test_agent_authorship_guard.py` — the sweep inventory:

- **AGENT powerlessness frozen**: AGENT kind → `AGENT_CONSUMER` →
  exactly `{mcp:consume}`; any widening of the kind-role lock or the
  role's permission set fails CI. An AGENT token attempting EVERY
  write route in the app → 403 + AUTHZ_DENIED audited (the grid,
  exhaustively, discovered from the route table — new write routes
  are swept the moment they exist).
- **The MCP surface writes nothing**: the frozen 9-tool assertion +
  AST sweep of the gateway functions the tools call (no
  governed-model construction, no status writes, no session mutation
  — the D26/D28 sweep pattern).
- **THE LANE SENTINEL (the constitutional core)**: under the most
  permissive policy environment constructible — a global
  `connector_id = NULL` policy covering all types and domains, Tier-0
  conditions satisfied by planted metadata, a live approve-everything
  Tier-2 fake engine — a proposal-lane CANDIDATE is **still PENDING**
  after all background tasks complete, and its hold is declared,
  never silent.
- **Class is channel-decided, structurally**: the only permitted
  writer of `source_class` is the allowlisted channel-derivation path
  (app-wide AST sweep; the allowlist names the WS1 module before it
  exists — covered the moment it lands). No route, tool, or surface
  accepts a caller-supplied class.
- **No cross-lane mutation**: a proposal document engineered to
  collide by (type, name) with an existing PRIMARY asset creates a
  new CANDIDATE, never a candidate revision of the PRIMARY asset.
- **Workbench isolation**: nothing under `backend/app/` imports
  workbench code; modules under `workbench/` import only the declared
  doors — swept the moment `workbench/` exists (the D28
  registry-sweep pattern).
- **Adversarial self-proof** (all planted, all caught, recorded at
  the gate): a write-capable MCP tool; a widened AGENT role; an
  auto-approval of a proposal-lane candidate; a frontmatter-decided
  source class; a direct APPROVED write from workbench code; a
  proposal colliding with PRIMARY asset identity reaching the
  revision machinery; fake provenance trusted from content without
  governed verification.

**Gate:** the guard self-proof + the D24 snapshot at exactly 28/305 +
all 31 pre-existing suites green (the snapshot edit is the one ratified
assertion change) + the D25 custody sweep unchanged.

### WS1 — The proposal lane

- Connector `lane` declaration on the existing governed connector
  routes (create/update; audited like any connector change).
- `source_class` assignment at extraction, channel-derived — the one
  allowlisted writer.
- Proposal frontmatter parsing + **governed provenance verification at
  ingestion**: claimed binding exists, belongs to the claimed agent
  principal, package hash matches the binding's coordinates, principal
  active. Verified against governed records; quoted verbatim in the
  approval event when the human accepts (the D26 Tier-0 pattern —
  evidence for acceptance, not acceptance itself).
- `PROPOSAL_PROVENANCE_UNVERIFIED` computed exception kind (MEDIUM at
  most, no dismiss, most-specific-wins in the existing exception
  ranking).

**Gate (the lane proof):** a seeded proposal with valid provenance
flows scan → CANDIDATE (held: the sentinel live) → human accept →
DERIVED fact whose provenance chain answers the opening question from
governed records alone; a forged binding claim is a declared exception,
held for review, never rejected by the engine; a proposal claiming
PRIMARY is still DERIVED.

### WS2 — Primary-over-derived conflict discipline + class travels

- Conflict engine declares class asymmetry on PRIMARY×DERIVED pairs;
  review surfaces present the DERIVED side as the presumptive review
  target ("primary prevails unless a human rules otherwise"); nothing
  auto-resolves; compile gate unchanged.
- Class flows into: .empkg asset records, projection nodes (the graph
  lens shows derivation), MCP tool responses, citations.

**Gate (the discipline proof):** a DERIVED fact contradicting a PRIMARY
fact surfaces with declared asymmetry on every surface that shows the
conflict; the class is present in every consumer channel's output
(package bytes, graph.json, MCP response, citation); nothing was
auto-resolved; the compile gate verdict is identical to the same
conflict between two PRIMARY facts.

### WS3 — The workbench pilot + vault skeleton

- `workbench/onboarding_diagnostic.py` at repo top level: consumes the
  .empkg via `package_consumer`, queries MCP graph tools as a real
  client at a real AGENT token's clearance (D27 domain prefixes as its
  scope), synthesizes a diagnosis behind an injectable seam
  (deterministic fake in CI; D19 resolver for the real run), writes a
  proposal document with provenance frontmatter (agent principal,
  binding id, package hash, cited governed asset ids/hashes) to
  `/08_proposals` ONLY.
- Vault skeleton bootstrap under `EM_VAULT_DIR`: `/00_system` (static
  contract material, repo-versioned), `/07_agent_workspaces`
  (ungoverned scratch, never scanned), `/08_proposals` (the return
  path).

**Gate (the diagnosis proof):** the runner produces an evidence-backed
diagnosis from a seeded corpus deterministically in CI — every finding
cites governed asset ids/hashes it consumed — and writes it to /08 with
valid frontmatter; the runner's imports pass the Guard 5 door sweep;
the runner at AGENT clearance cannot read above its tier (the v1.0
clearance discipline holds at the workbench door).

### WS4 — Operator surface + THE MILESTONE GATE

- DERIVED badge + synthesis provenance panel on asset cards; class
  asymmetry on conflict cards; the exception kind ranked in the
  Governance Inbox — all inside existing areas (D8).
- In-browser verification against a seeded throwaway DB (the v1.2.1 /
  v1.3.0 WS4 pattern), live demo DB untouched.
- **The milestone gate** (`backend/test_workbench_acceptance.py`):
  corpus in through the real pipeline → bound agent diagnoses through
  package + MCP → proposal lands in /08 → scan → CANDIDATE held (lane
  sentinel live under a permissive policy) → human accepts → DERIVED
  fact with complete verified provenance → the fact is retrievable,
  packageable, renderable, and MCP-queryable with class declared → a
  PRIMARY contradiction surfaces with asymmetry declared → closing
  assertions: **the ledger alone proves no agent principal wrote any
  canonical fact directly**, and the D24 snapshot matches the
  WS0-ratified 28/305 exactly.
- The ONE real-model diagnostic run recorded at the gate (honest slot:
  pending if it cannot run at acceptance, never silently skipped).

## Explicitly out of scope (refused deliberately, not omitted)

- **Agent runtime, orchestration, scheduling, multi-agent flows** (D22
  — the pilot runner is a reference consumer, not an execution
  environment EM governs).
- **The workbench catalog** (HR / compliance / process optimization) —
  one workbench proves the loop; plurality is earned.
- **The full vault renderer**, folders 01–06, Obsidian compatibility —
  v1.5 (the projection engine's second renderer; the top-level
  Projections UI area is earned there).
- **DERIVED→PRIMARY promotion mechanics** — the natural path already
  exists: a human who adopts a finding authors it as an ordinary
  document (the valve constrains agents, not people). No mechanic
  until real pressure.
- **Proposal negotiation/iteration workflow** (comments, pending-
  proposal revisions) — a proposal is a document; the existing
  document lifecycle is the workflow.
- **Domain-scoped clearances or bindings** — v1.4 consumes D27
  prefixes as workbench scope, nothing more.
- **Revision auto-approval** (D17) and **D23** (binding lifecycle) —
  still deferred, held through a fourth milestone.

## Standing boundaries

The three disciplines hold (no orchestration creep, no leaderboard
disease, no rewriting history). Every gate re-runs the D25 custody
sweep (the vault and proposal documents are new surfaces; the sentinel
must never appear in one) and the D28 projection guard (class on
projection nodes must not tempt a governed write from projection code).
The D26 automation guard's AUTOMATION_MODULES declaration grows if any
new module emits automation events. Language rulings per scoping ruling
12 — nothing may imply an agent authored a fact or an engine rejected
content.

## Gate records

### WS0 — D29/D30 Schema + Agent Authorship Guard: ACCEPTED (2026-07-02, user-ratified)

Commit: `a9e672a`. **Gate verdict: PASSED.**

**Gate wording (user-ratified at acceptance):** WS0 is accepted as the
constitutional boundary for v1.4.0. The milestone begins with D29 —
The One-Way Valve and D30 — Derived Source Class implemented as
schema, policy floor, and permanent CI guard before any diagnostic
workbench code exists.

The D24 frozen schema is amended by ratified decision from 28 tables /
303 columns to 28 tables / 305 columns. The two added columns are
KnowledgeAsset.source_class and SourceConnector.lane, both TEXT NOT
NULL DEFAULT 'PRIMARY'. Legacy assets are PRIMARY by construction
because no proposal-lane agent ingress existed before v1.4.

Guard 5 is accepted as the fifth permanent guard family. It proves
that no agent principal, workbench result, diagnostic output, MCP/tool
return, or proposal-lane automation path can write APPROVED knowledge
or canonical fact state except through the proposal lane and human
gate.

The structural powerlessness proof holds: AGENT principals remain
kind-locked to AGENT_CONSUMER with exactly mcp:consume. REST write
routes refuse AGENT bearer tokens. MCP tools remain read-only, with
the frozen nine-tool surface and gateway AST sweep preventing governed
writes.

The lane sentinel passed. Under the most permissive policy environment
constructible — global connector policies, empty-condition policies,
Tier-2 approval, and an approve-everything fake engine — proposal-lane
candidates remain CANDIDATE and are declared as held by both policy
tiers. Human approval through the ordinary gate remains valid. The
valve constrains agents, not people.

Source class is channel-decided. Proposal-lane content becomes DERIVED
only through the proposal lane and human gate; source_class cannot be
caller-supplied, frontmatter-decided, or trusted from document
content. A proposal colliding with an existing PRIMARY asset creates a
separate held candidate and cannot mutate PRIMARY revision history.

Workbench isolation is enforced. backend/app does not import workbench
code, and future workbench modules are restricted to declared consumer
doors. Provenance verification is guarded so that verified synthesis
provenance cannot be claimed without consulting governed
ExpertAgentBinding records.

The guard is adversarially self-proven. Planted violations for
write-capable MCP tools, widened AGENT roles, caller-supplied source
class, frontmatter-decided class, workbench CRUD imports,
content-trusted provenance, auto-approved proposal candidates, and
proposal-to-PRIMARY collision are caught.

All 32 CI suites pass. WS1 may proceed: proposal lane, connector lane
declaration, channel-derived source_class assignment, proposal
frontmatter parsing, governed synthesis provenance verification, and
PROPOSAL_PROVENANCE_UNVERIFIED exception handling.

Evidence (`backend/test_agent_authorship_guard.py`, 9 parts, in CI
permanently — the fifth guard): frozen powerlessness (kind-role lock +
exact permission set, both widening shapes caught in self-proof); the
MCP AST sweep + the frozen nine-tool surface; the dynamic REST grid
(40 write routes enumerated from the live route table, 40 explicit 403
refusals, zero 2xx — new routes swept the moment they exist); the
app-wide source_class writer sweep (allowlist: database.py +
proposals.py, covered the moment WS1 lands) + the write-schema sweep;
workbench isolation in both directions (auto-activates when
`workbench/` exists); the provenance tripwire; THE LANE SENTINEL
end-to-end with holds declared as `proposal_lane_held_ids` by both
tiers' summary events, the human gate proven open, the sentinel
self-proof (7b), and the cross-lane collision proof (7c); seven
adversarial plants all caught with canonical clean shapes passing.
Ratified ripple recorded: the D28 guard's Part 6 and the v1.3
acceptance closing line now assert the CURRENT ratified D24 snapshot
(28/305) — projection work may never be the reason FROZEN_SCHEMA
changes.
