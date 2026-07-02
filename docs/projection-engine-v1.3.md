# v1.3.0 — Projection Engine + Graph Renderer: Build Contract

> Scoped and ratified July 2026 (ruling **D28 — The Projection Rule** in
> docs/DECISIONS.md). Input briefs: PROJECT_STATE.md, docs/roadmap.md
> ("The road to the Operations Realm"), and the v1.3 foreclosure notes in
> docs/scoping-1.2-credentials-cloud-connector.md. Reference
> implementation: graphify (https://github.com/rokorobot/graphify, MIT)
> — its export layer only; its LLM extraction is explicitly not adopted.
> This is the build contract: workstreams, gates, and the boundaries
> that hold. Gate records are appended here as each workstream is
> accepted.

## The milestone in one sentence

Governed facts become renderable: a renderer-agnostic projection engine
composes clearance-filtered, cursor-stamped views of knowledge, lineage,
domains, exceptions, packages, and consumption — and the first renderer
draws them as a self-contained interactive graph — without any
projection ever becoming a source of truth.

## The opening question (evidence-first, per tradition)

> What must be true of every rendered artifact so that, six months
> later, the system can prove exactly which governed facts it projected,
> for whom, at which ledger moment — and prove that nothing ever flowed
> back from the render into governed state?

The answer is D28: a render is verifiable evidence of what was
projected, never a source of what is true. Every render regenerates
from governed facts, is stamped `rendered_at` + audit cursor, is
clearance-filtered with exclusions declared, and has its manifest hash
recorded in the ledger. Nothing flows back.

## Scoping rulings (settled at the session)

1. **Zero schema change — the constitutional claim of the milestone.**
   No ProjectionRun table, no render registry: the ledger records
   renders (`PROJECTION_RENDERED` events carrying renderer, scope,
   status-inclusion set, clearance, audit cursor, node/edge/exclusion
   counts, manifest hash, output location). The D24 frozen snapshot
   (28 tables / 303 columns) survives the entire milestone
   byte-identical, asserted at the WS4 gate. A projection engine that
   needed schema would be another knowledge system — the proof and the
   rule are the same fact (D1 applied at full strength).
2. **File renders ride `assets:approve`** — producing a portable
   artifact of governed knowledge is the same act-class as compiling a
   .empkg, which already rides `assets:approve`. Live graph queries
   (UI/REST) ride `assets:read`; MCP graph tools ride `mcp:consume`
   under per-node clearance. The 12-permission matrix is unchanged
   (D8's "earned by plurality" applied to permissions).
3. **Nodes carry metadata + a bounded excerpt, never full content**:
   title, type, status, domain path, trust/conflict summary, provenance
   references, and a short content excerpt for the inspect panel. The
   .empkg remains the content artifact; the graph is the structure
   artifact — two artifact species, never blurred (D9 posture).
4. **Status scope is a declared render parameter, default
   APPROVED-only.** The inclusion set is recorded in the manifest and
   the event; an operator may explicitly render a governance view
   including candidates and held exceptions, and the render says so.
   Nothing is included silently (D12).
5. **The D10 split extends to projections**: MCP graph query tools are
   the GOVERNED channel (computed live per call, clearance enforced per
   node, refusals audited); rendered files are the PORTABLE channel
   (verifiable snapshot, stamped, tamper-evident, no live enforcement).
   Never conflated in docs or UI.
6. **Domains are the grouping dimension.** graphify's community slot is
   filled by governed D27 domain paths; no community detection (no
   Louvain), no LLM labeling. The taxonomy investment of v1.2.1 is the
   graph's organizing principle by construction.
7. **Renders are self-contained**: vis-network is vendored (MIT) and
   inlined into graph.html — no CDN, no network access from a rendered
   artifact. This is a deliberate deviation from graphify-as-is, which
   loads vis-network from unpkg.
8. **UI lives inside existing areas** (render controls + history on the
   surfaces where the facts live; staleness in the existing inbox). A
   top-level Projections area is earned at v1.5 when the vault renderer
   creates plurality — the D8 discipline exactly as applied to
   connectors.
9. **Determinism**: same facts, same scope, same clearance →
   byte-identical graph.json. `rendered_at` lives in the manifest, not
   in projected content, so content-hash comparison detects real drift
   (graphify precedent: the un-annotated render is byte-identical).
10. **graphify port scope**: `to_json` (node-link graph.json) and
    `to_html` (interactive vis-network viz: search, click-to-inspect,
    group filter, aggregated meta-graph fallback above a node limit) —
    with MIT attribution preserved in the ported module. `extract.py`,
    `llm.py`, community detection, Obsidian/Cypher/Canvas/Neo4j writers:
    not adopted (the Obsidian writer becomes reference material for the
    v1.5 vault renderer, not code in this milestone).

## Key discovered facts (grounding, pre-contract)

- **graphify already stamps renders with `built_at_commit`** — the
  exact analog of the audit-cursor stamp, independently invented. The
  cursor discipline is proven practice, not speculation.
- **graphify's graph.html is NOT self-contained** (unpkg CDN script
  tag); vendoring is a porting requirement, not an option.
- **graphify's backup machinery (`backup_if_protected`) is unnecessary
  by construction here**: it protects artifacts that cost LLM tokens or
  human curation to produce. EM renders are always regenerable from
  governed facts — that regenerability IS the rule (D28).
- **EM already has three pure projections** (`governance_inbox.py`,
  `consumption_inbox.py`, `binding_lineage.py`). The projection engine
  generalizes what `binding_lineage` does for one binding — walk
  backwards to documents, sideways into identity, every hop resolves or
  is declared missing — to a whole-project graph. And `package_builder.py`
  (D9) already models the artifact discipline: compiled FOR a clearance,
  exclusions declared, manifest hash chain, creation event in the ledger.

## Schema changes

**None.** This section exists to record that its emptiness is the
milestone's central structural claim. Any column or table discovered
"necessary" during build is a design failure to be escalated, not a
gate-recorded addition — the D24 snapshot is asserted unchanged at the
WS4 gate.

## Module map (planned)

| Module | Role |
|---|---|
| `projections/engine.py` | THE DECIDER: composes the projection model (nodes/edges/groups) from governed facts; scope + status parameters; clearance filtering with declared exclusions; cursor + stamps; manifest; `PROJECTION_RENDERED` emission |
| `projections/contract.py` | the projection model contract renderers receive (the D18 `connectors/models.py` pattern applied to output) |
| `projections/renderers/graph.py` | first renderer: graph.json + self-contained graph.html (ported from graphify export layer, MIT attribution; vendored vis-network); imports stdlib + the contract ONLY |
| `mcp_gateway.py` / `mcp_server.py` | grows graph query tools (governed channel): lineage path, neighbors, domain subgraph |

Renders land under `EM_PROJECTION_DIR` (the `EM_PACKAGE_DIR` pattern).

## Workstreams

### WS0 — D28 + the projection guard (before the door, permanent in CI)

`backend/test_projection_guard.py`, the D24/D25/D26 pattern applied a
fourth time:

- **Structural purity (the decider)**: projection modules perform no
  governed writes — AST sweep (the D26 guard pattern): no `.status`
  writes, no governed-model construction, no session mutation; ledger
  access only through `log_audit_event`.
- **Structural purity (renderers)**: renderer modules import stdlib +
  the projection contract ONLY (the `package_consumer` purity pattern)
  — a renderer that can reach the database can decide content.
- **The read-back sentinel**: adversarially edit a rendered graph.json
  and graph.html, then run every ingestion and projection path — zero
  governed facts changed; no code path reads rendered artifacts back
  into governed state. Rendered files re-enter only as ordinary
  documents through connectors, and then they are documents, not
  projections.
- **Stamp enforcement**: a render missing `rendered_at`, the audit
  cursor, or the ledger event is a guard failure, not a warning.
- **Self-proof**: plant a governed write in a renderer, plant an
  unstamped render, plant a schema column — all three caught; the proof
  is recorded here.

**Gate (user-ratified wording, at scoping acceptance):** Projection
code may read governed facts and emit render artifacts/audit events,
but it must not write governed state or create new canonical projection
state. The guard establishes the permanent CI constraint before the
engine exists:

- Projection modules cannot write governed state.
- Renderers can import only the projection contract, not
  persistence/write services.
- No schema changes allowed.
- `PROJECTION_RENDERED` is the only allowed durable trace.
- A read-back sentinel proves that deleting all render artifacts loses
  no governed knowledge.
- The D24 snapshot remains unchanged.

The guard adversarially self-proves that it fails when any of these
rules is violated. All pre-existing suites pass unchanged.

### WS1 — The projection engine (D28 made executable)

- The projection model: nodes (documents, assets, expert models,
  packages, selections, bindings, AGENT principals), edges (provenance
  document→asset, membership asset→expert→package, AssetRelationship
  CONFLICTS_WITH/SUPPORTS with classification + confidence, revision
  supersession, the consumption chain selection→binding→principal),
  groups (domain paths, honest NULL for unclassified).
- Scope parameters: project (required); optional domain-prefix
  narrowing (the D27 prefix guarantee consumed for the first time);
  status-inclusion set (ruling 4, default APPROVED-only, always
  declared).
- Clearance filtering before rendering (D9): the render is compiled FOR
  a declared clearance; excluded node/edge counts declared in manifest
  + event, never silent (D12).
- Stamps: `rendered_at`, audit cursor (max audit event id at
  composition time), engine version. Manifest: sha256 per file + the
  manifest hash recorded in `PROJECTION_RENDERED`.
- Determinism (ruling 9) proven as a test, not promised.
- Staleness: computed, never stored — ledger head moved past a render's
  cursor for facts in scope; surfaced as a LOW inbox condition (D2:
  never blocks compile, so never HIGH; hygiene, so LOW).

**Gate (the engine proof):** a projection over a seeded corpus contains
exactly the governed facts in scope; an EXECUTIVE asset is absent from
an INTERNAL-clearance projection with the exclusion declared; the same
inputs produce byte-identical graph.json twice; a new approval after a
render makes staleness computable and visible; `PROJECTION_RENDERED`
answers "what was projected, for whom, at which ledger moment" from the
event alone.

### WS2 — The graph renderer (the graphify port)

- `graph.json`: node-link shape (ported `to_json`), domain groups,
  edge relations + confidence, the cursor stamp in the manifest.
- `graph.html`: self-contained interactive visualization (ported
  `to_html`): vendored vis-network inlined, search, click-to-inspect
  (metadata + bounded excerpt), domain-group filter, conflict edges
  visually distinct, aggregated domain-level meta-graph above the node
  limit (graphify's fallback, with domains where it had communities).
- MIT attribution preserved in the ported module header.
- No network access of any kind from a rendered artifact.

**Gate (the lens proof):** render a real corpus; delete every rendered
artifact — no governed fact lost (the D24 disappearance test applied to
files); re-render reproduces content-identical artifacts; a tampered
render is detectable from ledger + manifest alone; the EXECUTIVE/INTERNAL
clearance proof repeated on the rendered files themselves; graph.html
opens air-gapped (no external requests).

### WS3 — MCP graph query tools (the governed channel)

- `get_lineage_path` (lineage as a path query — the binding_lineage
  walk generalized to any node pair), `get_graph_neighbors`,
  `get_domain_subgraph` (prefix-scoped). Read-only; per-node clearance
  with `MCP_ACCESS_DENIED` audited; computed live from governed facts —
  NEVER reading rendered files (ruling 5).
- The gateway grows 6 → 9 tools; `MCP_TOOL_CALLED` discipline
  unchanged.

**Gate (the agent proof):** an agent walks document→asset→package→
binding as one path query with every hop resolving or declared missing
(D12); a PUBLIC-clearance agent is denied a RESTRICTED node and the
denial is ledger evidence; the tools return identical structure to what
the engine projects (one composition, two channels).

### WS4 — Operator surface + the milestone gate

- Render controls + render history projected from `PROJECTION_RENDERED`
  events + staleness badge, inside existing areas (ruling 8) —
  governance cockpit, never a database viewer.
- In-browser verification against a seeded throwaway DB (the v1.2.1
  WS4 pattern), live demo DB untouched.
- **The milestone gate**: the full acceptance run — corpus in, render
  out, tamper/edit sentinel, delete-and-regenerate, clearance proof,
  staleness proof, MCP path query — closing with the assertion that the
  D24 frozen snapshot is byte-identical to v1.2.1's (28 tables / 303
  columns): the projection engine shipped as a lens, structurally
  incapable of being a second knowledge system.

## Explicitly out of scope (refused deliberately, not omitted)

- **graphify's LLM extraction** (`extract.py`, `llm.py`) — EM's nodes
  and edges are governed facts, never inferred structure.
- **Community detection / LLM labeling** — domains are the grouping
  (ruling 6).
- **The vault/Obsidian renderer** — v1.5, the second renderer on this
  seam; graphify's `to_obsidian` is reference material only.
- **Neo4j/Cypher/GraphML/Canvas writers** — later renderers if ever
  earned; the seam makes them additions, not redesigns.
- **Any graph database** — facts stay in SQLite; the graph is computed.
- **Editing anything via the graph** — the lens never writes.
- **Domain-scoped clearances, bindings, or workbench scopes** — v1.4+
  consumes what this milestone only renders.
- **D23** (binding lifecycle) — still deferred.

## Standing boundaries

The three disciplines hold (no orchestration creep, no leaderboard
disease, no rewriting history). Language rulings: a render is
"regenerated", never "synced"; artifacts are "stale", never "wrong";
"projection"/"render", never "export of record" — nothing may imply a
rendered file is authoritative. Every gate re-runs the D25 custody
sweep (renders are a new export surface; the sentinel must never
appear in one) — `test_credential_custody.py` already sweeps
projections by design; the graph renderer joins its swept surfaces.

## Gate records

### WS0 — Projection Guard: ACCEPTED (2026-07-02, user-ratified)

Commit: `077c2be`. **Gate verdict: PASSED.**

**Gate wording (user-ratified at acceptance):** The projection guard is
accepted as the constitutional boundary for v1.3 projection work. It
proves that projection modules cannot mutate governed state, renderers
cannot import persistence or application internals, no schema changes
are introduced, and the D24 frozen schema remains unchanged at 28
tables / 303 columns.

The only permitted durable trace of projection activity is
`PROJECTION_RENDERED` in the audit ledger. Projection artifacts are
disposable render outputs and are not a source of governed knowledge.
The read-back sentinel proves that hostile, corrupted, or deleted
render artifacts cannot alter governed state, computed read surfaces,
or ledger history.

WS1 and WS2 may now proceed under this guard. Projection engine and
renderer code must remain inside the guarded contract: generated from
governed facts, stamped with `rendered_at`, `audit_cursor`,
`clearance`, `status_inclusion`, and `files`, with no schema writes, no
governed model construction, no renderer persistence imports, and no
artifact read-back path.

Evidence (`backend/test_projection_guard.py`, in CI permanently — the
fourth guard):

- **No governed writes (dynamic, registry-aware)**: every module under
  `app/projections/` swept by AST — session mutators, governed-model
  construction (class list discovered from the live `db.Base` registry;
  `AuditEvent` included — the ledger is reached only through
  `crud.log_audit_event`), non-self attribute assignment, and schema
  definition (`__tablename__` / `Table` / `Base` subclass) all
  forbidden. WS1's `engine.py` is covered the moment it exists.
- **Renderer isolation**: modules under `projections/renderers/` import
  the stdlib (`sys.stdlib_module_names`) + `projections.contract` only,
  relative imports included.
- **Ledger-only durability, both directions**: inside the package, any
  event emission not prefixed `PROJECTION_` is a violation (keyword and
  positional `log_audit_event` forms); app-wide, the family may
  originate only inside the package, and `EM_PROJECTION_DIR` may be
  named nowhere else.
- **Write-only file access**: `open()` requires an explicit `w`/`x`
  mode; `.read()`/`.read_text()`/`json.load()` forbidden (`json.loads`
  on governed column text stays legal — `load` reads files, `loads`
  parses strings).
- **Read-back sentinel (end-to-end)**: hostile render artifacts (a
  graph.json claiming a HOSTILE fact as APPROVED, a manifest claiming
  ledger cursor 999999, a scripted graph.html) planted at
  `EM_PROJECTION_DIR` — governed snapshot of all 28 tables and the
  computed read surfaces byte-identical with the hostile renders
  present, after deleting them entirely, and a subsequent rescan
  ingests zero hostile content and replays zero manifest events.
- **Adversarial self-proof**: nine plants all caught (session write in
  a renderer, governed-model construction, status write, foreign event
  family, schema definition, read-mode open + `json.load` read-back,
  persistence import in a renderer, unstamped manifest,
  `PROJECTION_RENDERED` emitted outside the package); the canonical
  clean renderer shape passes both checkers; the sentinel's detectors
  proven non-vacuous against a simulated read-back (Part 5b).
- **Stamps structural**: `contract.py` frozen dataclasses; the stamp
  fields are guard-checked contract fields — a render without
  `rendered_at` + audit cursor cannot exist.
- **Accepted WS1/WS2 constraints (recorded at the gate)**: no
  `set.add()` in projection modules (the blunt mutator sweep is
  preferred over a clever permissive one); vendored vis-network is
  inlined as a module constant at build time — WS2 must not read render
  assets back from disk at runtime.
- **All 26 pre-existing suites green with zero assertion edits.**

### WS1 — Projection Engine: ACCEPTED (2026-07-02, user-ratified)

Commit: `18725e0`. **Gate verdict: PASSED.**

**Gate wording (user-ratified at acceptance):** The projection engine
is accepted as the governed composition layer for v1.3 projections. It
composes projection content from governed facts in scope, applies
clearance and domain filters, declares exclusions, bounds excerpts,
drops out-of-scope relationship edges, and emits deterministic
projection content.

The engine preserves the D28 rule: projections are rendered lenses over
the governed knowledge system, never another knowledge system.
Projection content identity is based only on the governed facts
projected. Render identity fields such as `rendered_at` and
`audit_cursor` live in the manifest and PROJECTION_RENDERED audit
event, not in projection.json, preventing false drift across identical
renders.

Staleness is computed by deterministic recomposition and hash
comparison. A projection can become stale after approved governed facts
change, but it is treated as a LOW-severity stale render, never as a
wrong canonical fact. Regeneration clears staleness without introducing
dismissal state.

The PROJECTION_RENDERED event is self-sufficient: it records renderer,
clearance, status inclusion, domain scope, audit cursor, counts,
exclusions, projection hash, manifest hash, file hashes, and actor
identity. Render files are tamper-evident but non-authoritative.

Implementation ruling accepted: **revisions render as asset metadata,
not as graph nodes.** Graph nodes represent current governed living
identities. Revision and supersession history remain in the existing
revision and Binding Explorer surfaces.

**COMPILED_FROM** is added to the projection edge vocabulary for
package-to-expert lineage.

WS2 may proceed under the WS0/WS1 guard boundary using the RENDERERS
registry and the Projection contract.

Evidence (`backend/test_projection_engine.py`, 8 parts, in CI):
exact-inventory proof (10 nodes / 11 edges / exact relation counts /
3 domain groups / bounded excerpts / conflict evidence on edges); D9
clearance proof on the composed projection AND the written files, with
both exclusions declared; domain-prefix scope resolving `finances/*`
children (D27 consumed); byte-identical determinism across renders with
the cursor advancing in the manifest only; the staleness lifecycle
(fresh → drift → LOW item → regeneration clears, no dismiss); the
self-sufficient ledger event with every disk byte hash-accounted;
route refusals (assets:approve render / assets:read history,
metadata-only responses); the D25 sentinel sweep over the new export
surface. All 26 pre-existing suites green with zero assertion edits;
tsc clean; eslint 0 errors.
