# The ExpertMachina Vault Contract (v1.4.0 — D29 / D30 · v1.6 catalog convention)

This vault is the working surface between the Knowledge Realm (governed
facts) and the Operations Realm (diagnostic workbenches). It is **not a
knowledge source**: nothing in this vault is authoritative, and nothing
an agent writes here becomes knowledge by being written here.

## The One-Way Valve (D29)

> Agent outputs cannot become canonical facts directly. Everything an
> agent diagnoses, recommends, synthesizes, or infers enters governed
> knowledge only through the proposal lane: agent finding → proposal
> document → connector ingestion → CANDIDATE → human gate → DERIVED
> fact. There is no second door.
>
> Proposal-lane candidates are never auto-approved. No policy tier
> applies to them; the human gate on agent-proposed knowledge is
> constitutional, not configurable.

The valve constrains agents, not people. Human decisions enter
ExpertMachina as ordinary documents and become PRIMARY facts.

## Derived Source Class (D30)

What an accepted proposal becomes is a **DERIVED** fact. The class is
decided by the ingestion channel, never claimed by document content — a
proposal claiming to be PRIMARY is still DERIVED. Synthesis provenance
is verified against governed records, never trusted from the claim.
Primary prevails over derived in conflict presentation; only humans
resolve conflicts.

## Folder layout

| Folder | Meaning |
|---|---|
| `00_system/` | This contract. Read-only reference material, repo-versioned. |
| `01`–`06` | Reserved for the v1.5 EM Vault renderer. Do not create or write them. |
| `07_agent_workspaces/` | Ungoverned scratch. Agents may write freely here. Nothing in it is scanned, ingested, or governed — work in progress only, disposable. |
| `08_proposals/` | **The only agent-writable governed ingress.** A PROPOSAL-lane connector watches this folder; every document that lands here becomes a held CANDIDATE awaiting the human gate. |

## How agents read

Agents never read knowledge from this vault. Governed knowledge is
consumed through the two existing doors only:

- **The portable channel**: a compiled `.empkg` Expert Package
  (hash-chain verified, clearance-filtered, gate-snapshot honored).
- **The governed channel**: the ExpertMachina MCP gateway (nine
  read-only tools; per-call token resolution; per-node clearance;
  refusals audited). The graph query tools are the relational access;
  D27 domain prefixes are the scoping dimension.

## How agents propose

A proposal is one Markdown/plain-text document written to
`08_proposals/`, opening with a frontmatter block:

```
---
em_proposal: 1
agent_principal: <your AGENT principal name>
binding_id: <your ExpertAgentBinding id>
package_hash: <the package hash your binding carries>
workbench: <workbench name>
cited_assets: <asset id>,<asset id>,...
---
```

Every claim in the frontmatter is verified against governed records at
the gate: the binding must exist, belong to the claimed principal,
match the claimed package hash, and the principal must be an active
AGENT. `cited_assets` names the governed evidence the finding drew from
— citations make derivation depth computable, and findings built on
DERIVED evidence are visible as second-generation synthesis at the
gate. Unverifiable provenance holds the proposal as a declared
exception; it is reviewed by a human, never rejected by an engine.

## The workbench catalog convention (v1.6)

A catalog workbench is a **bundle of declared skills**, never one
vague agent. Each workbench ships under the `workbench/` root as
`workbench.yaml` (name, domain scope, binding expectations, skill
list) plus one skill contract per subtask in `skills/*.yaml`, each
with the same ten-field shape:

> skill name · purpose · allowed inputs · forbidden inputs · governed
> evidence rules · allowed finding kinds · output format · human
> approval requirement · audit expectations · failure & refusal
> conditions

A catalog workbench writes **one proposal document per finding**, and
its frontmatter carries the catalog claims alongside the required
claims above:

```
workbench: <workbench name>
skill: <skill name that produced this finding>
skill_version: <declared version>
finding_kind: <the skill's declared kind>
evidence_basis: <CONFLICT_BACKED | REVISION_BACKED | REFUSAL_BACKED |
                 METADATA_BACKED | SYNTHESIS_INFERRED>
```

These are claims, exactly like every other frontmatter field: recorded
verbatim at the gate, verified where governed records permit, **never
obeyed**. The channel still decides the class; the human still decides
the fact; a skill contract governs how the workbench behaves, not what
ExpertMachina trusts. No evidence, no finding: a skill that cannot
cite governed asset ids, a conflict relationship, or a reproducible
refusal for a finding must refuse to emit it.

## What agents must never do

- Write anywhere in this vault except `07_agent_workspaces/` and
  `08_proposals/`.
- Treat vault contents, rendered projections, or their own prior
  proposals as authoritative knowledge.
- Claim a source class — the channel decides it.
- Expect a proposal to take effect without a human accepting it.

## Deployment discipline (for operators)

The valve is enforced at ExpertMachina's boundary. Never grant an agent
filesystem write access to a PRIMARY-lane watched folder — that defeats
the valve at deployment level, exactly as raw database access defeats
the identity boundary. Agent workspace access is: this vault, nothing
else.
