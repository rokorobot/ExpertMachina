# Bridge Relations — Cross-Layer Knowledge (D34 proposed) — Scoping

> Drafted 2026-11-04 from an external prompt (A. Belin, "How many
> ontologies does an enterprise need?": Domain / Process / Application /
> Capability ontologies joined by a Bridge Ontology into one Enterprise
> Knowledge Graph). **Docs only — no code until WS0 is ratified.**
> Version number and D-number are owner rulings, proposed here, not
> assumed. Not scheduled ahead of v2.6 (catalog #8 commercial verdict).

## The problem in one sentence

EM can answer questions *inside* one piece of governed knowledge, but not
questions that cross layers — "which capabilities are affected if we
replace application X?" — because cross-layer links (process step →
application, process → capability) are not governed facts today; at best
they sit as prose inside asset content.

## What the code already has (measured, not assumed)

| Belin's layer | EM today | Gap |
|---|---|---|
| Domain ontology (classification) | D27 `knowledge_assets.domain` — one governed path, `classification.py` | none for classification; concepts like Customer/Invoice are asset content, not a model — **and stay that way** (see "Refused") |
| Process ontology | asset types `PROCEDURE`, `WORKFLOW` (`policy.py:41`) | no step-level structure, no links out |
| Application ontology | asset type `SYSTEM` | no links to the processes it supports |
| Capability ontology | **absent** | no type, no links |
| Organization (implicit in the post) | `ROLE`, `DEPARTMENT` | ownership is a string (`owner`), not a link |
| Bridge ontology | `asset_relationships` exists, but holds only **engine verdicts** (`CONFLICTS_WITH`/`SUPPORTS`/`RELATED`, NLI-detected, `conflict_engine.py:250-270`) | no human-governed, evidence-backed cross-layer relation |
| Graph | projection engine already renders every `asset_relationships` row as an edge (`projections/engine.py:278-293`); MCP has `get_graph_neighbors`, `get_domain_subgraph` | nothing to traverse yet |

**Correction to the first-pass idea.** The first sketch proposed several
classification axes (domain / capability / process / application columns
on each asset). The code says otherwise: processes and applications are
already *assets* (typed), not *axes*. An asset is not "classified under"
an application; a process step is *supported by* one. The missing piece
is governed **relations between assets**, plus one missing type
(`CAPABILITY`). D27 stays the single classification axis, unchanged.

## A trap found while scoping (binding on any design)

Reusing `asset_relationships` as-is would silently corrupt the conflict
engine:

- `conflict_engine.py:204-207` deletes **every** `DETECTED` row of the
  expert model on rescan — not type-filtered. Pending bridge relations
  would vanish on the next scan.
- `conflict_engine.py:196-201` skips conflict detection for any pair
  with a `CONFIRMED`/`DISMISSED` row — not type-filtered. A confirmed
  "step A is supported by system B" would **suppress conflict
  detection between A and B forever.**

Both are fine today only because the engine is the table's sole writer.

## Proposed rulings (WS0, for ratification)

1. **D34 — Bridge relations are governed facts, never inferred
   structure.** A cross-layer relation exists in EM only if it is
   (a) stated by an `APPROVED` evidence asset that cites it, and
   (b) accepted by a human. No evidence = no edge. Traversal, impact
   analysis, and the graph see only accepted relations whose endpoints
   and evidence are `APPROVED` and inside the caller's clearance.
   *(D28's sibling: the graph renders relations; it never creates them.)*

2. **Own table, not a new `relationship_type` — recommended.**
   `bridge_relations(id, project_id, source_asset_id, target_asset_id,
   relation, evidence_asset_id NOT NULL, status, proposed_by,
   reviewed_by, reviewed_at, created_at)`. Same reason
   `ClassificationPolicy` is not `ApprovalPolicy` (D27): an engine
   verdict and a human-accepted fact are different outcome species;
   their provenance must never blur, and the conflict engine's sweeps
   must be unable to touch them by construction.
   Cost: schema 28/305 → 29/316 (D24 snapshot updated deliberately).
   *Alternative (not recommended):* reuse `asset_relationships` + add
   `evidence_asset_id` + type-filter both conflict-engine queries + a
   guard that the engine writes only its own types. Zero new table,
   but the safety rests on filters every future writer must remember.

3. **Closed, small relation vocabulary.** Start with exactly what the
   gate question needs; extend only by ratification:
   - `SUPPORTED_BY` — PROCEDURE/WORKFLOW → SYSTEM
     (process step uses application function)
   - `REALIZES` — PROCEDURE/WORKFLOW → CAPABILITY
   - `PART_OF` — PROCEDURE → WORKFLOW; CAPABILITY → CAPABILITY
   - `OWNED_BY` — any → ROLE/DEPARTMENT
   Endpoint types are checked on write; a mistyped relation is rejected,
   not stored.

4. **`CAPABILITY` becomes an allowed asset type.** Extracted and governed
   like every other asset (capability maps are ordinary documents).
   Capability ≠ domain: domain classifies *where knowledge belongs*;
   capability is *a thing the company can do*, a node with relations.

5. **Ingress: the existing lanes, no new authority.**
   - Extraction may *propose* bridge relations (status `PROPOSED`) with
     the asset that states them as evidence — never `ACCEPTED`.
   - Agents propose through the D29 proposal lane; accepted agent
     relations are DERIVED-class by channel (D30), primary prevails.
   - Acceptance is a human act under `assets:approve`, audited
     (`BRIDGE_RELATION_PROPOSED` / `_ACCEPTED` / `_REJECTED`). No new
     permission; the 12-permission matrix is unchanged.
   - Archiving the evidence asset or an endpoint takes the relation out
     of every traversal (computed, never stored — D24 posture).

6. **Consumption.** The projection engine adds accepted relations as
   edges (renderers unchanged except the style map). One read-only MCP
   tool, `trace_impact(asset_id, relations, max_hops)`, returns paths
   where **every hop carries its evidence asset id**; a hop the caller
   cannot see is declared excluded (D12), never silently dropped.
   Impact analysis as a product is a workbench skill over that tool,
   not engine code.

## Refused (deliberately)

- **A separate ontology stack (OWL/RDF store, five ontologies).** Would
  be a second knowledge system beside the governed store — D28's
  violation by construction. Layers are asset types; the "bridge" is a
  governed table. Five models emerge, if ever, from real validation
  pressure, not as a target (Belin's own rule).
- **Instance data ("real entities" — this customer, that invoice).**
  D27 companion: transactional records are not knowledge assets. EM
  governs what the company *knows* (its processes, systems,
  capabilities), not every record it holds.
- **LLM-inferred edges**, at any confidence. The projection-engine
  scope already refused graphify's LLM extraction; this holds.

## Build contract (proposed workstreams)

- **WS0 — ratify** D34 and rulings 1–6; pick table vs reuse (ruling 2).
- **WS1 — model + governance:** table, `CAPABILITY` type, endpoint-type
  check, propose/accept/reject with audit events; D24 snapshot bumped
  deliberately.
- **WS2 — ingress:** extraction proposes relations with evidence; the
  proposal lane carries them; source-class by channel.
- **WS3 — consumption:** projection edges, `trace_impact` MCP tool,
  clearance + exclusion declaration.
- **WS4 — the gate proof (below).**

## The gate proof — "replace the application"

A small corpus (new, 6–10 documents): a capability map, two process
documents, an application inventory, one IT change memo.

1. **Positive:** `trace_impact(SYSTEM:"HR Suite", [SUPPORTED_BY,
   REALIZES, PART_OF])` returns exactly the planted capabilities, every
   hop with its evidence asset id.
2. **No evidence = no edge:** a link only implied (both names in one
   paragraph, never stated) is not proposed — or, if proposed, cannot
   be accepted without an evidence asset; the trace declares the gap.
3. **Archive cascade:** archive the evidence asset → the hop disappears
   from the trace with no write to `bridge_relations`.
4. **Clearance:** an EXECUTIVE capability is excluded for an INTERNAL
   caller and the exclusion is declared, not silent.
5. **Conflict-engine isolation (the trap above):** a full rescan after
   acceptance leaves every bridge relation intact, and conflict
   detection between the two linked assets still runs.
6. **Projection law:** delete every render → zero governed change;
   re-render → identical manifest at the same cursor.
7. **Adversarial self-proof:** plant an edge written without evidence
   and an engine sweep that drops bridge rows — both must be caught.

## Open questions for the owner

- Ruling 2: new table (recommended) or reuse with filters?
- Version slot: after v2.6 as v2.7, or held until a customer corpus
  actually asks a cross-layer question? (D27's rule: earned by real
  pressure.) My view: hold the build, ratify the law now — it costs
  nothing and stops anyone from adding a typed edge the wrong way.
- Is `OWNED_BY` in scope now, or does the string `owner` column stay
  until a workbench needs ownership traversal?
