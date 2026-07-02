# v1.5 — EM Vault: Build Contract

> Scoped and ratified July 2026 (ruling **D31 — Render Authority Dies
> at Ingress** in docs/DECISIONS.md). Input briefs: PROJECT_STATE.md,
> docs/DECISIONS.md (through D30), docs/roadmap.md, and the gate
> records in docs/diagnostic-workbench-v1.4.md — including the
> user-ratified v1.5 opening carried from the v1.4 closeout: "D28
> protects rendered files from flowing back. D29 makes /08_proposals a
> governed ingress. v1.5 must prove that the vault layout cannot
> launder a projection back into knowledge." Reference material:
> graphify's `to_obsidian` (reference only, per the v1.3 ruling). This
> is the build contract: workstreams, gates, and the boundaries that
> hold. Gate records are appended here as each workstream is accepted.

## The milestone in one sentence

The projection engine's second renderer fills the vault: governed
knowledge becomes a full human-readable, Obsidian-compatible,
deterministic workspace — domain-first, clearance-filtered, disposable
— living in the same tree as the proposal lane, with no laundering
path between projection output and governed ingress.

## The opening question (evidence-first, per tradition)

> Six months after a vault render, the system must prove: which
> governed facts each note projected, for whom, at which ledger moment
> — and that no byte of any rendered note ever became governed
> knowledge except by passing the same human gate any agent proposal
> passes. If deleting the entire vault loses anything, or if moving a
> rendered note into 08_proposals gains anything, the design has
> failed.

The first half is D28 doing its job on a second renderer. The second
half is D31 — the new law for the ground where projection output and
governed ingress become adjacent.

## Scoping rulings (settled at the session, user-ratified)

1. **The vault is a content artifact** — an explicit amendment to v1.3
   scoping ruling 3 ("nodes carry metadata + a bounded excerpt, never
   full content"): that ruling protected the GRAPH's species boundary
   (the .empkg is the content artifact, the graph is the structure
   artifact). The vault joins the .empkg as a content species — a
   workspace of excerpts is not human-readable knowledge. The
   projection contract grows **one declared field for content mode**;
   a renderer must declare that it needs full content, the declaration
   appears in the manifest and the PROJECTION_RENDERED event (D12),
   and **clearance filtering applies before content reaches notes**.
   The graph renderer is untouched.
2. **Output root: the vault renderer writes directly into**
   `EM_VAULT_DIR/01_start · 02_knowledge · 03_experts · 04_packages ·
   05_conflicts · 06_governance`. It must not render elsewhere and
   copy — the copy-step alternative creates an unnecessary ungoverned
   transfer path and is weaker on the exact laundering axis v1.5
   exists to close. Each managed folder is deleted and regenerated
   wholesale per render (the D28 rmtree discipline, scoped to the
   managed set).
3. **The untouchable floor is constitutional**: `00_system`,
   `07_agent_workspaces`, `08_proposals`. No render path may delete,
   overwrite, scan-as-render-state, or manage those folders. This is
   the sharpest technical danger of the milestone — a wholesale
   regeneration must never be able to destroy an agent's pending
   proposal — and it is guard-planted, never promised.
4. **The sixth permanent guard family**:
   `backend/test_render_ingress_guard.py`, deliberately NOT folded
   into the D28 or D29 guards — new seam territory earns its own
   boundary. Its cornerstone plant (the WS0 constitutional core):
   render a file → drop it into /08_proposals → scan under permissive
   policies → it becomes only a **held DERIVED candidate** with
   unverifiable or declared provenance — never PRIMARY, never
   auto-approved, never replaying manifest authority, never generating
   projection authority from its stamps.
5. **Folder semantics** (the reserved 01–06, defined):
   - `01_start` — orientation: the generated home note, how to read
     the vault, the index.
   - `02_knowledge` — the main tree: domain-first folders (D27
     rendered) → one note per approved asset — YAML frontmatter (asset
     id, type, status, source_class, domain, provenance references),
     full governed content, wikilinks to related notes; DERIVED notes
     visibly marked.
   - `03_experts` — expert models: member lists, trust snapshot.
   - `04_packages` — the consumption chain: packages, selections,
     bindings.
   - `05_conflicts` — conflict notes with class asymmetry declared.
   - `06_governance` — the render manifest, declared exclusions and
     inclusion set, ledger cursor, staleness explanation. **Stamps
     live here and in the event, never inside knowledge notes** —
     content-hash determinism survives.
6. **Obsidian compatibility means plain Markdown, YAML frontmatter,
   wikilinks, deterministic bytes.** No `.obsidian` config, no
   plugins, no Git machinery — Git-trackability is a property of
   determinism, not a feature.
7. **Zero schema — again a constitutional claim.** Vault renders are
   PROJECTION_RENDERED events exactly as graph renders; staleness
   joins the existing recompose-and-compare machinery and the LOW
   no-dismiss inbox item automatically. The D24 snapshot holds at
   28 tables / 305 columns, asserted at the milestone gate.
8. **The top-level Projections UI area is EARNED here** by renderer
   plurality (graph + vault) — executing the v1.3 scoping ruling (D8).
   The dashboard Projections panel graduates.
9. **Language rulings**: "rendered note", "vault render", "managed
   folders", "untouchable folders", "render authority dies at
   ingress", "ordinary proposal evidence", "held DERIVED candidate",
   "unverifiable provenance" — never "sync back", "vault source",
   "rendered truth", "trusted note", "promoted from vault", "Obsidian
   database".
10. **D23 held** (a fifth milestone). The two honest slots carry
    unchanged: the v1.2.0 live-SharePoint-tenant scan and the v1.4.0
    real-model diagnostic run.

## Key discovered facts (grounding, pre-contract)

- **The seam already exists physically**: v1.4 WS3 created
  EM_VAULT_DIR with 00_system / 07_agent_workspaces / 08_proposals and
  reserved 01–06 for this milestone. The PROPOSAL-lane connector roots
  at `<vault>/08_proposals`.
- **The laundering plant is testable BEFORE the vault renderer
  exists**: the v1.3 graph render's files (graph.json, manifest.json
  with its audit-cursor stamp) are a perfectly good rendered artifact
  to drop into 08_proposals at WS0 — the guard's cornerstone needs no
  vault code.
- **The D30 machinery already handles the authority-death case
  functionally**: an ingested rendered file claims no valid proposal
  frontmatter → provenance honestly unverifiable → held MEDIUM
  exception; a forged frontmatter → verified-or-declared. WS0 proves
  this AT THE SEAM and plants the catastrophes.
- **The D28 guard auto-covers the new renderer**: any module under
  app/projections/renderers/ is swept the moment it exists (no
  governed writes, sibling-only imports, write-only file access,
  vendored assets as constants).
- **The engine's wholesale-regeneration discipline (rmtree) is
  exactly what must be caged**: today it deletes
  EM_PROJECTION_DIR/project_N/<renderer>/ — pointed at the vault it
  would delete whatever it manages, which is why the managed-folder
  floor is WS0 machinery, not WS1.

## Schema changes

**None.** Renders live in the ledger; the vault adds behavior, not
schema. The D24 snapshot (28/305) is asserted at the milestone gate.

## Module map (planned)

| Module | Role |
|---|---|
| `projections/contract.py` | grows the declared content mode (WS0): `ProjectionNode.content` (populated ONLY under a declared FULL_CONTENT composition) + `content_mode` on Projection and RenderManifest, added to the guard-checked stamp sets |
| `projections/engine.py` | WS0: content-mode composition (clearance filters before content by construction — content is populated only on already-included nodes); the per-renderer output-root seam; the managed-folder floor (UNTOUCHABLE_FOLDERS; wholesale regeneration confined to a renderer's declared managed set; unknown or untouchable folders refused loudly) |
| `projections/renderers/vault.py` | WS1/WS2: the second renderer — domain-first knowledge tree, orientation + consumption + conflict + governance folders; plain Markdown + YAML frontmatter + wikilinks; imports stdlib + contract + swept siblings only (D28) |
| `backend/test_render_ingress_guard.py` | WS0: the sixth permanent guard family (D31) |

## Workstreams

### WS0 — D31 + the render-ingress guard + the contract growth (before the vault renderer exists)

One commit: the content-mode field (inert until WS1 — the graph
declares METADATA_EXCERPT and is byte-unaffected in behavior), the
per-renderer output-root seam with the untouchable-folder floor, and
the sixth guard:

`backend/test_render_ingress_guard.py` — the inventory:

- **THE LAUNDERING PLANT (the cornerstone, fully functional at WS0
  using graph-render files)**: render a real corpus with the graph
  renderer; drop the rendered artifacts (including the manifest with
  its audit-cursor stamp, and a variant with forged proposal
  frontmatter prepended) into a vault's 08_proposals; scan through a
  PROPOSAL-lane connector under a permissive policy environment →
  every extracted candidate is a held DERIVED candidate; provenance
  honestly unverifiable (or declared, for the forged variant); zero
  assets APPROVED; zero PROJECTION_* events emitted by ingestion; the
  manifest's cursor claim inert; the governed snapshot unchanged
  except for the ordinary document/candidate rows the pipeline
  legitimately creates.
- **Regeneration isolation (functional at WS0 via an in-test renderer
  spec)**: plant files in 00_system, 07_agent_workspaces, and
  08_proposals; run a vault-rooted render through the engine's new
  managed-folder machinery; every planted byte survives; only the
  managed folders were recreated; the PROJECTION_RENDERED event
  declares the content mode.
- **The floor refuses loudly**: a renderer spec attempting to manage
  an untouchable or undeclared folder is refused before any deletion.
- **Path discipline (structural sweep)**: within backend/app,
  EM_VAULT_DIR is named only inside app/projections; the untouchable
  folder names appear only in the floor's constant — no renderer code
  path can construct a path into them.
- **Authority death**: the ingested rendered files' stamps are
  unrecognized claims (the D30 vocabulary); the forged variant
  surfaces as the existing declared exception.
- **Adversarial self-proofs**: the laundering catastrophe simulated
  (an ingested rendered-note candidate flipped to APPROVED PRIMARY —
  detector fires; an auto-approval planted — caught; a PROJECTION
  event emitted by ingestion simulated — caught); the untouchable
  plant (a spec managing 08_proposals — refused); the sweep plant (a
  renderer-shaped source naming 08_proposals — caught).

**Gate:** the guard self-proof; content_mode present in the manifest +
event of every render (the graph now declares METADATA_EXCERPT); all
37 pre-existing suites green (assertion edits only where the ratified
contract growth surfaces, recorded at the gate); zero schema.

### WS1 — The knowledge tree

`02_knowledge`: domain-first folders (honest `_unclassified` for NULL
domains, D12) → one deterministic Markdown note per approved asset —
YAML frontmatter, full governed content (FULL_CONTENT declared),
wikilinks (related assets via relationships, document provenance,
expert membership), DERIVED notes visibly marked. Registered in
RENDERERS with the vault output root; staleness live automatically.

**Gate:** exact-inventory proof on notes; the D9 clearance proof ON
NOTE BYTES with exclusions declared in 06_governance; byte-identical
determinism; the D27 proof (a taxonomy reorganization re-renders the
folder tree — folder paths move, note content byte-identical, nothing
reclassified by the move); the D25 sweep over the vault surface.

### WS2 — The whole workspace

`01_start` (home note, how-to-read, index), `03_experts`,
`04_packages` (the consumption chain), `05_conflicts` (asymmetry
declared), `06_governance` (manifest, exclusions, cursor, staleness
explanation). Obsidian-compatibility verification: frontmatter parses,
wikilinks resolve within the vault, deterministic bytes.

**Gate (the workspace proof):** a human can navigate corpus → domain →
asset → conflict → package → binding entirely inside the vault;
everything the vault does not show is declared; THE DISAPPEARANCE TEST
first pass — delete every managed folder, no governed fact lost,
re-render reproduces every ledger-recorded file hash.

### WS3 — The top-level Projections area (earned by plurality)

Both renderers with declared parameters (renderer / clearance /
domain prefix / content mode shown), ledger-projected history,
staleness badges; the dashboard panel graduates; language "regenerated"
never "synced". In-browser verification against a seeded throwaway DB.

**Gate:** the area renders both renderers' histories from
PROJECTION_RENDERED events alone; render controls gate on
assets:approve; the v1.3 staleness lifecycle re-verified on the vault
renderer.

### WS4 — THE MILESTONE GATE

`backend/test_vault_acceptance.py`: corpus in through the real
pipeline → vault render (clearance-filtered, stamped) → THE
DISAPPEARANCE TEST (delete the ENTIRE vault including managed folders
→ no governed fact lost → re-render byte-identical to ledger hashes;
untouchable folders' planted content untouched throughout) → THE SEAM
PROOF live (a rendered note dropped into 08_proposals under permissive
policies → held DERIVED only → a human accepts it → an ordinary
DERIVED fact whose provenance honestly declares what it is — no
laundering, no authority survival) → the D25 sweep → closing on the
D24 snapshot at 28 tables / 305 columns.

## Explicitly out of scope (refused deliberately, not omitted)

- **Editing a vault note writing anything back** — the lens never
  writes; humans change knowledge through revisions or by authoring
  documents.
- **Vault watching/sync daemons, git machinery, `.obsidian` config,
  Obsidian plugins.**
- **Per-user vaults or clearance mixing** — one vault renders FOR one
  declared clearance per render (D9).
- **Canvas/Neo4j/Cypher writers** — later renderers if ever earned.
- **D23** (binding lifecycle) — still deferred.

## Standing boundaries

The three disciplines hold. Every gate re-runs the D25 custody sweep
(the vault is the largest export surface yet) and the D28 projection
guard (the vault renderer is swept the moment it exists); Guard 5's
door sweep is unaffected (the renderer lives inside app/projections,
not workbench/). Language rulings per scoping ruling 9.

## Gate records

*Appended as each workstream is accepted.*
