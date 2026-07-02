# v1.2.1 — Ingestion Automation & Domain Classification: Build Contract

> Scoped and ratified July 2026 (rulings **D26 — Review by Exception**,
> **D27 — Domain Taxonomy** in docs/DECISIONS.md). Input brief:
> docs/scoping-1.2-credentials-cloud-connector.md (the v1.2.x half).
> This is the build contract: workstreams, gates, schema changes, and
> the boundaries that hold. Gate records are appended here as each
> workstream is accepted.

## The milestone in one sentence

Humans review by exception, never by document (D5 applied): documents the
company already validated in their source system reach APPROVED by audited
policy (Tier-0), engine-clean documents reach APPROVED with engine-verdict
provenance (Tier-2), every exception is declared and severity-ranked in
the existing inbox — and assets gain a governed hierarchical domain path
so policies, workbenches, and future renderers can scope by business
dimension.

## The opening question (evidence-first, per tradition)

> Which classes of documents can reach APPROVED with zero human attention
> while every exception is declared, ranked, and audit-explained — and
> what is the honest ceiling of that percentage for a real corpus?

The honest answer, ruled at scoping: **Tier-0 is the only tier that can
carry the ≥90% mature-corpus target**, because it inherits a validation
the company already performed — authority, not inference. Tier-2 can only
ever say "nothing contradicts this," which is absence of alarm, not
presence of authority; its honest role is widening Tier-0's reach, never
replacing it. ≥90% untouched-by-humans is a mature-corpus target, not a
universal acceptance threshold — a messy first corpus starts lower and
climbs as policies are tuned (already worded this way in roadmap.md).

## Scoping rulings (settled at the session)

1. **One milestone**, not a split: Tier-2's "not a sensitive class"
   condition needs domains to exist, and the corpus acceptance test needs
   both automation and classification. Classification is WS1, before
   Tier-2.
2. **Tier-2 consults the conflict check only** this milestone: a
   candidate-contradiction check (NLI of the candidate against the
   approved corpus). Claim decomposition/verification of candidates is
   deferred — verifying a candidate's claims has no honest evidence
   target, and the verification engine's semantics are not bent to
   pretend otherwise.
3. **Taxonomy = path column + audited operations, no registry table**
   (D1): domain assignments live on assets, reorg mappings live in audit
   events. A registry can be earned later by real validation pressure.
4. **ClassificationPolicy is its own governed object**, not a kind flag
   on ApprovalPolicy: assigning a domain and granting APPROVED are
   different outcome species; their provenance and version counters never
   blur.
5. **No new permission**: classification-policy administration and
   taxonomy operations ride under `assets:approve`, the permission that
   already governs approval policies. The 12-permission matrix is
   unchanged.

## The key discovered fact (grounding, pre-contract)

The Tier-0 input does not survive today: providers report verbatim
discovery metadata on `ConnectorItem.metadata` (SharePoint:
`list_item_fields` with content type / approval status,
`last_modified_by`, `parent_path`, …) but the framework persists only
`size_bytes`, `source_modified_at`, and the content hash. **The verbatim
discovery metadata is discarded after the scan.** A Tier-0 policy firing
on "approved in SharePoint library X" needs that metadata at approval
time, and `ASSET_AUTO_APPROVED` provenance must quote it six months
later. Persisting it per scan row on `SourceDocument` is a genuine D1
fact (it survives nowhere else) and is the first schema change of the
milestone. Legacy rows are honestly NULL, never backfilled (D12/D20
posture).

## Schema changes (all land in WS0, one commit, with the D24 snapshot update citing D26/D27)

| Change | Justification |
|---|---|
| `source_documents.source_metadata_json` (Text, nullable) — verbatim `ConnectorItem.metadata` at scan time | D26 Tier-0 evidence: the described source state that carried authority must survive per scan (per-scan rows are already the permanent version history, D7) |
| `knowledge_assets.domain` (String, nullable) — hierarchical path, e.g. `finances/accounting` | D27: governed business dimension; NULL = honestly unclassified (D12), never fabricated as "general" |
| `classification_policies` (new table, the D17 governed-object shape: project_id, name, rules_json, connector_id nullable, enabled, version, created_by, timestamps) | D27: versioned classification rules; definition changes bump version; no delete endpoint, disable instead; enable/disable audited |
| `approval_policies.source_conditions_json` (Text, nullable) — Tier-0 metadata-match conditions | D26: NULL preserves v0.10.2 behavior exactly (the D19 empty-config invariant); presence makes the policy Tier-0 |
| `approval_policies.engine_conditions_json` (Text, nullable) — Tier-2 engine conditions | D26: same NULL invariant; presence makes the policy Tier-2 |
| `approval_policies.domains_json` (Text, nullable) — optional domain-prefix coverage narrowing | D26 deny-by-default coverage: asset types remain mandatory; domains narrow further; NULL = all domains (existing behavior preserved) |

Any additional column discovered necessary during build lands only with a
gate-recorded justification citing D26 or D27 — never silently (the D24
guard enforces this structurally).

## Workstreams

### WS0 — The automation guard (before the door, permanent in CI)

`backend/test_ingestion_automation_guard.py`, the D24/D25 pattern applied
a third time:

- **Structural**: exactly one approval transition path exists — every
  auto-approval call site resolves to `crud.update_knowledge_asset`; the
  policy module contains no direct status write, no direct AssetReview
  construction, no second path.
- **Adversarial sentinel (the D17 hard line)**: a CHANGED source file
  producing a candidate revision, under the most permissive policy set
  constructible (every tier, every type, every domain, every condition
  satisfied), is STILL pending human review after ingestion + all
  background tasks complete. Auto-approving a revision must be
  structurally impossible, not merely untested.
- **Self-proof**: the guard is adversarially proven at the gate — plant a
  second approval path and a revision auto-approval in a scratch branch;
  the guard must catch both; the proof is recorded here.
- Schema changes above + D24 frozen-snapshot update land in this commit,
  citing D26/D27.

**Gate (user-ratified wording, post-scoping):** The automation guard is
permanent in CI. It proves auto-approval has exactly one governed
transition path, proves revisions are never auto-approved, and
adversarially self-proves that the guard fails when either rule is
violated. All schema changes land in the same commit as the D24 snapshot
update, citing D26/D27. All pre-existing suites pass unchanged.

WS0 is not "add columns" — it is the structural safety gate before
automation can start approving at scale. The `source_metadata_json`
addition is what makes Tier-0 honest rather than fake: source metadata is
not just observed during scan; it is preserved as evidence for later
approval provenance. Without it, the system would claim source-authority
inheritance without preserving the source-authority evidence.

### WS1 — Domain classification (D27)

- `knowledge_assets.domain` + `ClassificationPolicy` CRUD
  (create/list/patch under `assets:approve`; no delete; version bumps on
  definition change; enable/disable audited — the ApprovalPolicy API
  shape mirrored).
- Deterministic assignment at ingestion, after extraction: enabled
  policies in id order, first matching rule assigns; rules match
  connector scope, source URI prefix, and/or source-metadata keys.
  Every assignment writes `ASSET_CLASSIFIED` with the policy snapshot
  that fired (D17 provenance discipline).
- Human correction through the normal asset-update surface, audited
  (`ASSET_DOMAIN_CORRECTED`) — a correction is a governed act, not an
  edit.
- **Taxonomy reorganization**: one endpoint (`assets:approve`) taking an
  explicit old→new prefix mapping; bulk-reassigns `domain` with ONE
  `TAXONOMY_REORGANIZED` audit event carrying the mapping and affected
  asset ids; content, revisions, and history untouched. Nesting
  (deepening a path) needs no operation — prefix queries already resolve
  the parent.
- Domains and asset types stay orthogonal everywhere: no UI or API ever
  renders them as siblings in one hierarchy.

**Gate (the taxonomy proof):** split `finances` →
`finances/accounting` + `finances/treasury` by policy change + reorg
operation alone — assets reassigned with audit provenance, no content or
history touched, prefix queries still resolve the parent domain;
classification provenance answers "why is this asset in this domain?"
from the event alone.

### WS2 — Tier-0 source-authority policies (D26)

- Verbatim discovery metadata persisted per scan (`source_metadata_json`,
  wired in `framework.py` at SourceDocument creation).
- `source_conditions_json`: a deterministic condition list evaluated
  against the source metadata of the document the asset came from —
  `{"key": "list_item_fields.ApprovalStatus", "equals": "Approved"}`
  shape; operators `equals` and `in` only (the deterministic tier; no
  regex, no LLM). Dotted keys traverse nested metadata. A Tier-0 policy
  whose conditions reference absent metadata does not fire — absence is
  never treated as satisfaction (D12).
- Provenance: `ASSET_AUTO_APPROVED` for a Tier-0 firing quotes the
  matched keys and values VERBATIM — the inherited authority is named in
  the event, indefinitely answerable.
- Policy CRUD: condition changes are definition changes → version bump
  (D17).

**Gate (the Tier-0 proof):** a fake-Graph SharePoint corpus where some
items carry tenant approval status — approved-in-source documents reach
APPROVED here with provenance quoting the source authority;
unapproved-in-source documents from the same scan are declared
exceptions; a policy edit bumps the version and past events still point
at the rule text that fired; NULL-condition policies behave exactly as
v0.10.2 (the empty-config invariant, tested).

### WS3 — Tier-2 engine-verified conditions (D26)

- **The candidate-contradiction check** (the one new engine capability):
  NLI contradiction scan of a CANDIDATE asset against the APPROVED assets
  of the same project — the conflict engine's calibration discipline
  (strict thresholds, embedding pre-filter above a pair cap, dropped
  pairs counted and declared, D12). Scoped by the policy's domain
  coverage when present.
- **Async per D4**: ingestion returns immediately; the check + Tier-2
  policy application run as a background task owning its session; the
  ingestion summary records "Tier-2 scheduled", never results it doesn't
  have.
- Verdict recording: the engine-verdict snapshot (verifier fingerprint,
  pairs checked, dropped count, per-pair scores for contradictions) lives
  in event provenance — `ASSET_AUTO_APPROVED` on approval, the exception
  event on refusal. **No AssetRelationship rows for candidate pairs**:
  candidate checks never pollute the approved-conflict surfaces or the
  conflict score.
- A contradicted candidate is NOT rejected — it is a declared exception
  holding for human review, with the contradicting approved asset named.
  Engines refuse to approve; only humans refuse content.

**Gate (the Tier-2 proof):** a candidate contradicting an approved asset
is held with the contradiction declared and the approved asset named; a
clean candidate under a satisfied Tier-2 policy is approved with the full
engine-verdict provenance; approvals happen in the background task, never
inline (D4 asserted); dropped pairs are declared (D12); the WS0 sentinel
still passes with Tier-2 policies active.

### WS4 — Exception surface + the corpus acceptance test

- **Ingestion exceptions as computed inbox conditions** (D1/D24: no new
  state, no dismiss): (a) policy-declined candidates from a scan where
  policies were in scope, (b) Tier-2 contradiction holds, (c) candidates
  with no policy in scope at all (unautomated, honestly declared). One
  shared severity function; per D2, ingestion exceptions are MEDIUM at
  most — they never block the compile gate, so they are never HIGH.
- UI (governance cockpit, never a database viewer): policy administration
  grows condition editors (Tier-0 metadata conditions, Tier-2 toggle,
  domain coverage); asset cards and the review queue show the domain
  path with inline correction; the inbox shows ranked exceptions with
  "why held" from provenance.
- **The corpus test (the milestone gate)**: a realistic mixed synthetic
  corpus (mature-corpus profile: most items carrying source authority,
  some engine-clean, some contradicting, some uncovered) through a
  Tier-0 + Tier-2 + classification policy set — **≥90% auto-approved,
  every approval carrying machine-verifiable provenance, 100% of
  exceptions present and severity-ranked in the inbox, zero revisions
  auto-approved, zero assets silently held.**

**Gate:** the corpus test in CI; in-browser verification of the three UI
surfaces; the north-star metric (document arrival → usable expert model)
derivable from audit events alone for an auto-approved document.

## Explicitly out of scope (refused deliberately, not omitted)

- **Revision auto-approval** — D17 holds absolutely; the living-KB
  tension (revision review is where human load will accumulate) stays
  documented and unresolved until a real deployment shows the pressure.
- **LLM-advisory classification or approval** — the deterministic → NLI
  ladder discipline holds; LLM tiers are a later explicit decision.
- **Domain registry table / taxonomy administration UI** — earned later
  by validation pressure, if ever (scoping ruling 3).
- **Domain-scoped clearances, bindings, or workbench scopes** — v1.3+
  consumes prefix scopes; this milestone only guarantees prefixes survive
  reorganizations.
- **Transactional-records mirroring** (invoices, wage records) — EM
  governs what the company knows, not every record it has. The named
  scope trap, refused.
- **D23** (binding lifecycle) — still deferred.

## Standing boundaries

The three disciplines (no orchestration creep, no leaderboard disease, no
rewriting history) hold. Language rulings: "held for review" /
"exception", never "rejected by the engine"; "classified" / "corrected",
never "moved" (files move; assets are reclassified). Every schema change
in this milestone lands with the D24 snapshot update in the same commit,
citing D26 or D27.

## Gate records

### WS0 — PASSED (2026-07-02, user-accepted)

The automation guard (`backend/test_ingestion_automation_guard.py`) is
permanent in CI, one step after the D25 custody guard. Evidence against
the ratified gate wording:

- **One governed transition path (structural, AST-based)**: automation
  modules (`AUTOMATION_MODULES`, currently `policy.py`) contain no direct
  `.status` write, no direct AssetReview/AssetRevision construction, and
  every APPROVED grant sits inside a `crud.update_knowledge_asset` call.
  App-wide sweep: the `ASSET_AUTO_APPROVED` event family may originate
  only from declared automation modules — WS3's Tier-2 module must be
  declared there or CI fails loudly.
- **Revisions never auto-approved (end-to-end sentinel)**: the most
  permissive policy set constructible (raw rows bypassing API validation:
  all 7 asset types unscoped + every v1.2.1 condition column populated
  maximally permissively — inert today, exercised automatically when
  WS2/WS3 give them semantics) auto-approves the corpus; the changed
  source file yields revision 2 CANDIDATE, approved content untouched.
  Binding note in the suite: WS3 must drain the async Tier-2 pass inside
  `run_scan` before the sentinel judges.
- **Adversarial self-proof (both rules)**: three planted structural
  violations (direct status write, direct AssetReview row, APPROVED
  outside the path) all caught, canonical shape clean; a simulated
  policy-approved revision with promoted content caught with 3 findings,
  clean after restore.
- **Accepted sentinel interpretation (user-ratified at the gate)**:
  revision 1 may be created as the legitimate lazy baseline during
  initial approval; only revisions > 1 approved by a policy actor are
  violations. The forbidden case is automation promoting a later
  candidate revision and changing trusted content without human review.
- **Schema, atomic**: `source_documents.source_metadata_json` (source
  authority evidence survives the scan), `knowledge_assets.domain`,
  `classification_policies`, ApprovalPolicy condition columns
  (`source_conditions_json` / `engine_conditions_json` / `domains_json`),
  `_ensure_columns` additive migrations, and the D24 frozen-snapshot
  amendment citing D26/D27 — one commit. D24 guard reports 28 tables /
  303 columns.
- **All 19 pre-existing CI suites green with zero assertion edits.**

### WS1 — PASSED (2026-07-02, user-accepted)

**Gate wording (user-ratified at acceptance):** WS1 PASSED. Domain
classification is now a governed taxonomy layer, not an asset rewriting
feature. Classification policies deterministically assign domains before
approval automation, human corrections remain explicit governed
asset-domain corrections, and taxonomy reorganization changes
classification paths without mutating asset content, provenance, status,
or revision history. The split from `finances` into `finances/accounting`
and `finances/treasury` was proven by policy change plus taxonomy
reorganization alone, with prefix queries still resolving the parent
domain.

Evidence (`backend/test_domain_classification.py`, in CI):

- **Governed CRUD**: `assets:approve`; POST/GET/PATCH only (no
  DELETE/PUT, asserted against the live route table); version bumps only
  on definition changes; enable/disable audited without a bump;
  malformed rules rejected at definition time — a bad rule is a rejected
  definition, never a rule that silently never fires.
- **Assignment semantics**: enabled policies in stable id order, rules in
  list order, first match wins (proven adversarially against a competing
  later policy); only fills NULL domains — never overwrites an earlier
  assignment or a human correction; unmatched stays honestly NULL (D12).
- **Audit quality**: ASSET_CLASSIFIED carries the policy snapshot, rule
  index, and exact matched values quoted verbatim;
  DOMAIN_CLASSIFICATION_COMPLETED declares unmatched;
  ASSET_DOMAIN_CORRECTED is distinct from generic asset update (and a
  domain-only correction emits no ASSET_UPDATED); TAXONOMY_REORGANIZED
  carries reason, operations, the complete old→new mapping, and the
  policy version that decided each reclassify move.
- **The split proof**: content SHA, status, provenance columns, and the
  full revision tuple list byte-identical before/after (the guardrail is
  a structural assertion, not a promise); prefix query for `finances`
  resolves both children; `rename` proven to nest a subtree by prefix
  rewrite with deeper paths preserved.
- **Metadata rules proven ahead of WS2**: a seeded scan-row
  `source_metadata_json` drives an `in`-list match with values quoted in
  provenance; a rule requiring absent metadata placed first does NOT
  fire — absence is never satisfaction (D12). WS2 only wires
  persistence; the consumer is already tested.
- **Ordering**: classification runs BEFORE `apply_auto_approval` at all
  three ingestion sites (connector scan, upload, manual extract) — the
  preparation WS2/WS3 approval conditions consume.
- **Accepted implementation rulings**: the DELEGATED actor is
  `classification:<name>` (species separation in the ledger, D27's
  "never blur" applied to actors); `classification.py` is declared in the
  D26 guard's AUTOMATION_MODULES (classification is automation and is
  structurally prevented from writing status); `classification_engine`
  joined SYSTEM_PRINCIPAL_NAMES (the missing principal surfaced a
  swallowed audit-path failure — found and fixed at the gate).
- All 21 suites green (both guards, the new 6-part gate suite, every
  pre-existing suite with zero assertion edits).

### WS2 — PASSED (2026-07-02, user-accepted)

**Gate wording (user-ratified at acceptance):** WS2 PASSED. Tier-0
source authority is now usable as governed approval evidence, not as
approval itself. Connector metadata is persisted as immutable scan
evidence, approval policies may evaluate source_conditions through
explicit versioned rules, and auto-approval provenance quotes the
matched source authority metadata verbatim. Documents approved in the
source can reach APPROVED only through a governed policy firing;
documents from the same scan that are draft, unapproved, or missing
authority metadata remain held and explicitly declared. Condition-less
policies preserve prior behavior, and historical approval events
continue pointing to the exact rule snapshot that fired even after
later policy edits.

Evidence (`backend/test_tier0_source_authority.py`, in CI — the
fake-Graph Tier-0 proof over the real SharePointProvider):

- **Metadata persistence**: `ConnectorItem.metadata` persisted verbatim
  into `source_documents.source_metadata_json` at scan-row creation;
  providers that describe nothing stay honestly NULL; the D18 meaning
  preserved (described context, never a change verdict). **No editable
  API surface**: structurally proven — no route path and no Pydantic
  input schema accepts source metadata; it exists only as recorded scan
  evidence.
- **Condition evaluator**: `equals`/`in`, dotted keys through the shared
  metadata-traversal vocabulary (one evaluator language across both
  policy species), conditions AND-ed, absence never satisfies (D12);
  NULL and `[]` preserve condition-less behavior exactly (the D19
  invariant, tested both at the API and against a raw `[]` row).
- **Tier-0 provenance**: ASSET_AUTO_APPROVED carries the policy snapshot
  including the exact source_conditions rule text, the matched authority
  values quoted verbatim, and the source URI; condition-less policies
  carry NO source_authority claim — they never claim authority they did
  not use.
- **Exception behavior**: one scan, three authority postures —
  approved-in-source → APPROVED; draft-in-source → held;
  tenant-exposes-nothing → held (absence never satisfies). Held assets
  declared via `skipped_source_conditions_unmet` and
  `source_condition_held_ids` in POLICY_AUTOAPPROVAL_COMPLETED — the
  projection WS4's exception inbox consumes.
- **Versioning**: a condition edit bumps the version; POLICY_UPDATED
  carries old/new condition snapshots; the historical v1 approval event
  still quotes the v1 rule after the edit.
- **WS0 sentinel did its job**: the `source_conditions_json="[]"`
  sentinel policy now exercises the live evaluator automatically; empty
  conditions preserve prior behavior; the revision sentinel still holds.
- **Custody discipline carried over**: the D25 sweep runs at the end of
  the gate suite — no secret material readable anywhere after the run.
- All 22 suites green; zero assertion edits to pre-existing suites.
