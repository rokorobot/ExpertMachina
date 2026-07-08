# ExpertMachina — PROJECT STATE

> Session-reload artifact. Load this (plus `docs/DECISIONS.md` and `docs/roadmap.md`)
> into a fresh AI session to continue work with full project context.
> Regenerate at every milestone release.

**Snapshot:** 2026-07-08 · current version **v1.9.0** (the Executive
Operations Briefing Workbench — the FIRST cross-workbench consumer,
canonical #1: six ratified skill contracts driving the runner at
runtime, THE BRIEFING PROOF executed as the named distinctive WS3
stage, THE COMMERCIAL VERDICT passed by the CEO reader; the briefing
consumes its own human-accepted evidence gap; ZERO door growth — the
nine frozen MCP tools + the `.empkg` were the entire visibility
budget; all four workstreams user-ratified end to end in one
milestone) · branch `main` · tag `v1.9.0` = `a9ded83`; tag `v1.8.0` =
`4bb0033`; checkpoint tag `post-audit-hardening` still at `c2179c2`
(the v1.7 release commit) per the standing release ruling — v1.9
shipped purely as a new workbench bundle, no audit-hardening surface
touched (`frontend/` and `backend/app/` byte-identical to v1.8) ·
register through D31 (**still no D32, deliberately**) ·
**the 2026-07-07 audit-hardening arc is landed** (docs/audit-2026-07-07.md
+ the release log below): pytest harness auto-discovery over every
backend/test_*.py, the nightly full-model NLI workflow, structured
logging with request correlation, hash-locked dependency custody with
pip-audit at ZERO-vuln/ZERO-ignore on base, the llama-index shed
(native openai/anthropic SDKs only), **the Alembic migration spine**
(baseline fc4ba7fed054, adopt-by-stamp, `_ensure_columns` retired,
loud refusal on deficient pre-Alembic DBs), **the main.py router
split** (1805→274 lines, 12 APIRouter modules + app/deps.py, proven
by the route-manifest byte-identity guard: 87 routes, frozen digest),
and **the crud↔identity cycle break** (log_audit_event → neutral
app/audit.py, AST import-cycle guard)
**Repo:** https://github.com/rokorobot/ExpertMachina

## What ExpertMachina is

A knowledge governance and compilation platform: transforms unstructured enterprise
documents into governed, auditable, evidence-backed Expert Models that AI agents can
safely consume. Category framing: "Knowledge Governance Infrastructure" /
"Governed Knowledge Quality Assurance". Pitch: semantically verified, conflict-checked,
revision-controlled — every human, service, and agent is a governed principal (v1.0),
and as of v1.1 the portable package channel is real, evaluable, and bindable:
which model consumes an Expert Package is an evidence-backed, audited decision.
v1.1.1 turns governed consumption from backend capability into operator-visible
evidence: selection decisions, computed drift, and binding lineage are now
inspectable without adding new governed state (D24). v1.2.0 gives the platform
custody of OUTBOUND credentials and its first credentialed enterprise source
(SharePoint): secrets are usable but never visible, every use is evidence
(D25), and cloud scans flow through the same governed pipeline as every other
source — v1.2 proves credentialed enterprise acquisition. v1.2.1 makes bulk
acquisition workable: humans review by exception, never by document (D26) —
Tier-0 inherits source authority the company already paid for, Tier-2
engine-verifies asynchronously (refusal-to-approve, never rejection), assets
carry a governed hierarchical domain path (D27), and every held candidate is
a ranked, provenance-explained exception in the inbox. The corpus gate: a
mature corpus reaches ≥90% auto-approved with machine-verifiable provenance,
100% of exceptions surfaced, zero revisions auto-approved, zero silent holds.
v1.3.0 makes governed facts renderable (D28): a renderer-agnostic projection
engine composes clearance-filtered, cursor-stamped, deterministic views
(knowledge, lineage, domains, packages, consumption), a self-contained
interactive graph renders them (vendored vis-network, air-gap safe), agents
query the same composition live through MCP path/neighbor/subgraph tools,
and staleness is computed exactly by recompose-and-compare — with ZERO
schema change: renders live in the ledger as PROJECTION_RENDERED events,
every render disposable, regenerable, and tamper-evident. A projection is a
governed lens over the knowledge system, never another knowledge system.
v1.4.0 opens the Operations Realm (D29 The One-Way Valve + D30 Derived
Source Class): a reference diagnostic workbench — a consumer outside the
governed backend, using only the existing doors (.empkg + MCP at a real
AGENT token's clearance) — diagnoses a corpus and its finding re-enters
ONLY through the proposal lane (/08_proposals → PROPOSAL-lane connector →
CANDIDATE → human gate → DERIVED fact with verified synthesis provenance).
Proposal-lane candidates are never auto-approved — constitutional, not
configurable; the class is channel-decided, never content-claimed; primary
prevails over derived as presentation and review priority, never automatic
resolution; and the fifth permanent guard proves from the ledger alone that
no agent principal can write canonical facts directly.
v1.5.0 fills the vault (D31 Render Authority Dies at Ingress): the
projection engine's second renderer produces the full human/agent-readable
knowledge tree — plain Markdown, YAML frontmatter, wikilinks, full governed
content after clearance filtering, every note visibly non-canonical —
directly into managed folders (01–06) of the SAME tree that holds the
proposal lane, with the untouchable floor (00_system / 07_agent_workspaces
/ 08_proposals) constitutionally outside every render path. The sixth
permanent guard proved the seam before the renderer existed: a rendered
file re-entering through 08_proposals is ordinary proposal evidence behind
the valve — held DERIVED, never PRIMARY, never replaying projection
authority — and total deletion of the vault loses nothing, with re-renders
byte-identical to ledger-recorded hashes. The top-level Projections area is
earned by renderer plurality. Delete everything, lose nothing; re-submit
anything, launder nothing.
v1.6.0 opens the commercial catalog (Workbench Catalog v1): a
workbench is a **bundle of declared skill contracts**, never a vague
agent — the Customer Operations Workbench ships five ratified skills
(promise conflicts, outdated customer guidance, missing playbooks,
SLA obligation gaps, the assist policy brief) whose contracts drive
the runner at runtime (question frames read from skills/*.yaml,
non-ACTIVE contracts refused, refusal-first, evidence-driven kinding,
declared same-subject/cross-document evidence rules). The catalog
(docs/workbench-catalog.md, 16 workbenches / 3 layers) and the master
skill registry (docs/workbench-skill-registry.md + 361 generated
draft contracts) enter the record as strategy artifacts, not law —
**no D32 and no seventh guard family, deliberately**: D22/D29/D30/D31
and the six standing guards wall every seam, with three future
decisions named but not minted (the Operational Evidence Realm,
Exception Stewardship, the Pipeline Metadata Door). THE COMMERCIAL
VERDICT closed the milestone: a six-finding diagnosis a Customer
Operations manager accepts as useful, bounded, and worth acting on —
agents diagnose and propose; humans accept; the knowledge system
remains governed.
v1.7.0 delivers the second commercial workbench (Compliance &
Obligation, catalog #9): six ratified contracts DRIVE the runner at
runtime (explicit obligation markers, classification rules,
requirement classes, owner frames, and the review-interval marker
pattern are parsed from the contract YAMLs, never hardcoded); the
clock is DECLARED (as_of recorded verbatim, wall-clock never
sampled); the gated [OE]/[PMD]/[ES] list is refused live naming the
unminted decision; the sensitivity posture is enforced at the source
(the manifest's forbidden vocabulary refused on every finding
statement — compliance overclaiming is the cardinal sin, and every
finding states documentation, never practice). The runner is built on
`workbench/common.py` — the catalog's first reuse moment (the v1.6
runner refactored onto it with zero assertion edits). THE COMPOSITION
PROOF executed registry rule 6 live for the first time: a
human-accepted obligation becomes a DERIVED fact, travels into a
recompiled package with its class visible, and supports a
second-generation `detect_missing_evidence` finding that cites
DERIVED evidence — derivation depth visible at the human gate. THE
COMMERCIAL VERDICT (the user as the audit-facing reader) closed the
milestone; the in-browser before/after (seeded throwaway DB, live
Accept-as-DERIVED 0→1, zero console errors) is the recorded release
evidence.
v1.8.0 delivers the THIRD commercial workbench (Procurement Document
Intelligence, catalog #3), completing the ratified sellable trio
(customers → risk/compliance → money). Six ratified contracts DRIVE the
runner (explicit term markers + term_class rules, the date_convention
marker_pattern + auto-renewal + renewal-context markers, increase
markers, the certification requirement + question template, the named
policy, and the forbidden vocabulary all parsed from the YAMLs, never
hardcoded). **THE INVENTED NUMBER is the cardinal sin**: every
monetary figure, percentage, notice period, and date is verbatim-cited;
the ONLY computed value is deterministic date-window arithmetic over a
verbatim date at the DECLARED as_of + window_days (never wall-clock, no
persistent calendar — the two-state-machine drift D1 names, refused by
ruling). The runner is built on `workbench/common.py` with **zero
shared-module edits** — the second proof the catalog's reuse foundation
industrializes. **THE CLAUSE ARITHMETIC PROOF** (the named distinctive
WS3 stage) verified every number in every finding statement traceable
to a governed clause or the declared clock; a declared
`subject_boilerplate_stopwords` refinement (the v1.6/v1.7
signal-to-noise precedent) separates a real cross-document policy
conflict from generic contract boilerplate. The standing composition
machinery (D30 class-travel, second-generation DERIVED citations)
proved unchanged on a third workbench. THE COMMERCIAL VERDICT (the
user as the procurement/finance owner) closed the milestone; the
in-browser before/after (66 held/0 accepted → 65/1 live, zero console
errors) is the recorded release evidence.
v1.9.0 delivers the FIRST cross-workbench consumer (Executive
Operations Briefing, canonical #1): it reads the governed state the
sellable trio produced and composes a leadership briefing with **ZERO
door growth** — the nine frozen MCP tools + the `.empkg` are the
entire visibility budget. Six ratified contracts DRIVE the runner
(the executive question frames, the origin convention, the section
list, the boundary declarations, and the forbidden vocabulary all
parsed from the YAMLs). **THE UNSOURCED SENTENCE is the cardinal
sin**: every briefing sentence is governed-cited, the declared clock
(as_of/since, never wall-clock), or inside an explicitly framed
section (SYNTHESIS_INFERRED / the mandatory "What this briefing cannot
see" boundary); its twin FALSE COMPLETENESS is refused by the boundary
section + the 12-phrase forbidden vocabulary on every written byte.
Read-compose summaries never re-enter knowledge (circular derivation,
refused by ruling); exactly one skill proposes
(`generate_unknowns_evidence_gaps_report` → EXECUTIVE_EVIDENCE_GAP,
because a documented gap is genuinely new information). The
runner-local `BriefingGraphClient` is an adapter over the EXISTING
frozen `get_trust_score` tool (a subclass, not a new door);
`workbench/common.py` is unchanged a third time. **THE BRIEFING PROOF**
(the named distinctive WS3 stage) swept 182 cited-section lines each
carrying a governed token, every DERIVED citation origin-named, the
pending + EXECUTIVE sentinels absent from every written and packaged
byte, the boundary quoting the gateway's exclusion counts verbatim,
and a covered question leaving no gap/proposal/byte. The distinctive
v1.9 turn: **the briefing consumes its own human-accepted evidence
gap** — accept one EXECUTIVE_EVIDENCE_GAP at the valve and the next
briefing cites it `[DERIVED, origin: executive-briefing]` and reports
it in what-changed. THE COMMERCIAL VERDICT (the user as the CEO)
closed the milestone; the in-browser before/after (308 held/2 accepted
→ 307/3 live, zero console errors) is the recorded release evidence.

**The mission, stated fully (July 2026 strategy sessions): ExpertMachina is a
two-realm system.** The Knowledge Realm (built, v0.x–v1.1.1) preserves company
knowledge as immutable evidence and compiles it into trusted, agent-ready
packages — D15 absolute: extract and verify, never synthesize. The Operations
Realm (**OPEN as of v1.4.0**) is diagnostic and improvement workbenches —
bound agents over expert packages — where synthesis IS the product. The
border is the v1.1 consumption arc, and the authorship rule that keeps it
honest is now LAW (D29/D30): **humans author facts; agents propose them**
(human decisions enter as ordinary documents → PRIMARY facts; agent findings
re-enter only via the proposal lane → human gate → DERIVED facts, with
synthesis provenance verified against governed records and the class
channel-decided). D15 and synthesis coexist because of the valve: EM extracts
and verifies the proposal *document* like any document; the proposal is
evidence, not truth, until a human rules. The knowledge lifecycle is a closed
loop; drift is the normal operating rhythm. Full arc: roadmap.md "The road to
the Operations Realm" + docs/diagnostic-workbench-v1.4.md.

## The value chain (all segments working end-to-end)

```
Identity Boundary (v1.0)                   every caller authenticates; the boundary
  callers propose, the boundary decides    decides actors (D20); roles authorize;
  ↓                                        every decision is identity-fact evidence
Credential Custody (D25)          v1.2.0   outbound secrets encrypted (envelope, EM_SECRET_KEY);
  scans propose use, custody decides       per-scan EXTERNAL_CREDENTIAL_USED evidence; rotation
  ↓                                        re-points connectors, never rewrites history
Source (Connector Framework)      v0.11.0  provider plugins; LocalFolderProvider first (D18);
  |                               v1.2.0   SharePointProvider (Graph) — first credentialed provider
  ↓ scan-now ingestion            v0.10.0  bulk ingestion, dedup, per-file status
  ↓ change detection              v0.10.1  changed source → candidate revision
Documents → CANDIDATE assets               existing extraction pipeline (LLM or rules)
  ↓ domain classification         v1.2.1   ClassificationPolicy (D27): deterministic first-match,
  |                                        governed hierarchical domain path, ASSET_CLASSIFIED
  ↓ policy auto-approval          v0.10.2  versioned per-project rules, new candidates only (D17)
  |                               v1.2.1   Tier-0 source-authority conditions (verbatim scan
  |                                        metadata, authority quoted in provenance) + Tier-2
  |                                        async engine verification (D26; refusal-to-approve,
  |                                        never rejection) + deny-by-default domain coverage
  ↓ human approval                         review queue (bulk + hotkeys); revisions ALWAYS human-gated;
  |                                        exceptions ranked + provenance-explained in the inbox
APPROVED assets                            revision-controlled (never edited in place)
  ↓ governance engines                     conflicts (NLI), claims, verification, trust
Expert Model                               trust score (5 explainable components)
  ↓ compile gate                           blocks on unresolved blocking conflicts
.empkg Expert Package             v0.9.4   hash-chained, clearance-filtered, provider-agnostic
  ↓ package consumption           v1.1 WS1 first-class consumer: chain verified, gate-snapshot
  |                                        honored, package-local retrieval, D19 model resolution
  ↓ package evaluation            v1.1 WS2 EvaluationRun run_type=PACKAGE + binding coordinates;
  |                                        referee (NLI/deterministic) never a player model
  ↓ model comparison (computed)   v1.1 WS2 per-model aggregates; unrun models absent, not zero
  ↓ governed model selection      v1.1 WS3 PackageModelSelection on the AgentPackage; audited
  |                                        with supporting run ids + rationale + identity fact
  ↓ ExpertAgentBinding            v1.1 WS4 append-only snapshot binding of current selection to
                                           an active AGENT principal; mints no tokens (D22, D23)
MCP Gateway (live channel)        v0.9     9 read-only tools (v1.3: +graph neighbors, lineage
                                           path, domain subgraph); v1.0: governed AGENT tokens
                                           (EM_AGENT_TOKEN), registry clearance, per-call
                                           resolution (live revocation), refusals audited
  ↓ projection engine (D28)       v1.3.0   compose governed facts → clearance-filtered,
  |                                        cursor-stamped, deterministic projections; ZERO
  |                                        schema — renders recorded as PROJECTION_RENDERED
  ↓ graph renderer                v1.3.0   graph.json + self-contained graph.html (vendored
  |                                        vis-network, air-gapped); D27 domains = the groups;
  |                                        disposable, regenerable, tamper-evident (never a
  |                                        source; staleness computed → LOW inbox item)
  ↓ diagnostic workbench (D29)    v1.4.0   reference consumer OUTSIDE the backend (workbench/):
  |                                        consumes .empkg + MCP graph tools at a real AGENT
  |                                        token's clearance, synthesizes behind the D19 seam,
  |                                        writes ONE proposal to the vault's /08_proposals
  ↓ the proposal lane (D29/D30)   v1.4.0   PROPOSAL-lane connector → CANDIDATE (never
  |                                        auto-approved: no policy tier applies —
  |                                        constitutional) → human gate → DERIVED fact;
  |                                        class channel-decided, synthesis provenance
  |                                        verified against ExpertAgentBinding records and
  |                                        quoted verbatim in the approval event; primary
  |                                        prevails over derived in every conflict surface
  ↓ the EM Vault (D31)            v1.5.0   the second renderer: the knowledge tree as a
                                           deterministic Markdown vault (full content after
                                           clearance, visibly non-canonical, wikilinked)
                                           in managed folders 01–06 BESIDE the proposal
                                           lane; untouchable floor 00/07/08; render
                                           authority dies at ingress — delete everything,
                                           lose nothing; re-submit anything, launder nothing
```

The two consumption channels stay honest (D10): MCP = GOVERNED (live
enforcement), .empkg = PORTABLE (verifiable snapshot) — v1.1 made the
portable channel first-class without blurring them, and v1.3 applied the
same split to projections: MCP graph tools = GOVERNED (computed live,
per-node clearance, audited refusals), rendered files = PORTABLE (stamped
verifiable snapshots, no live enforcement, never read back).

Operator surface: **Governance Inbox** (v0.9.1) + role-aware UI (v1.0): login gate,
the interface hides what the backend would refuse; Settings → Users & Tokens is the
ADMIN identity-administration surface. **v1.1.1 Consumption Operations Workbench**
(build contract docs/workbench-v1.1x.md, ruling **D24**): a top-level Consumption
area with three views — Selection Workbench (decision workspace, never a
leaderboard; the existing selection PUT is its only write), Computed Consumption
Inbox (nine drift/hygiene conditions, one shared severity function, no dismiss —
items leave when governed facts change), and Binding Explorer (server-composed
lineage: every hop resolves or is declared missing). The workbench is a pure
projection layer: the D24 schema guard in CI froze the v1.1.0 schema and it
survived the milestone untouched. Drift semantics (ratified): artifacts are
append-only, so drift = an older artifact is bound/selected while a newer
artifact exists in the same package family.

## The Identity Boundary (v1.0 — THE governance core)

- **Principal** (mutable registry): five kinds — HUMAN, DELEGATED (policy:X /
  connector:Y, auto-registered, never authenticate), SYSTEM (the engines),
  SERVICE (credentialed automation, never ADMIN), AGENT (MCP consumers,
  structurally AGENT_CONSUMER, clearance governed here). No delete — deactivate.
- **Credential** (hash-only lineage): PASSWORD / API_TOKEN / SESSION; revoke,
  never delete; sessions record which password generation authenticated them;
  plaintext shown exactly once at issuance.
- **IdentityFact** (immutable evidence, the ClaimVerdict pattern): who, kind,
  role-at-action-time, method, credential fingerprint, on_behalf_of identity
  chain. Purity rule enforced in CI. Landing pads: identity_fact_id on
  AuditEvent / AssetReview / AssetRevision (nullable, legacy-honest) and on
  ExpertAgentBinding (NOT nullable — no pre-boundary bindings exist).
- **Authorization** (WS3): 12 permissions × 5 roles (v1.2.0 added ADMIN-only
  `credentials:manage` — outbound credential custody, deliberately NOT under
  connectors:manage because SERVICE may hold KNOWLEDGE_OPERATOR), code-resident
  matrix in `identity.ROLE_PERMISSIONS`, enforced by `require_perm` on EVERY
  route. AUTHZ_DENIED always audited; read grants follow EM_READ_AUDIT_MODE.
- **ExternalCredential** (v1.2.0, D25 — the OUTBOUND species, separate table):
  encrypted at rest (envelope under EM_SECRET_KEY), never returned by any
  surface ("never", not "once" — the operator supplied it), revoke-never-delete
  lineage, random fingerprints (never plaintext-derived), granted scopes as
  custody evidence. Custody events: EXTERNAL_CREDENTIAL_CREATED/_ROTATED/
  _REVOKED/_USED/_RELEASE_REFUSED + CUSTODY_MASTER_KEY_ROTATED. The seam:
  routes/connectors propose use; custody.release decides, per scan, audited.
- **Recovery** (D21): documented manual procedure, no bypass mechanism.
- Binding text and evidence: **D20 (ratified), D21** in docs/DECISIONS.md;
  design contract in docs/identity-boundary-v1.md.

## The Consumption Arc (v1.1 — the strategic differentiator)

Build contract: **docs/consumption-arc-v1.md** (gates + ratified rulings);
ruling **D22** (Expert Agent Binding — a binding, never a runtime);
**D23 DEFERRED** (binding lifecycle: can a binding be withdrawn?).

- **WS1 Package Consumer** (`app/package_consumer.py`): verifies the full
  .empkg hash chain (no unmanifested extras), refuses non-PASSED gate
  snapshots, retrieves package-locally (LEXICAL_OVERLAP_V1, counts
  declared), generates via `llm.generate` — the D19 resolver → provider
  adapter boundary. Structural purity in CI: stdlib + the llm seam only.
- **Provider adapters** (`llm.py`): OPENAI + ANTHROPIC behind
  `llm.ADAPTERS`; the env tier stays OPENAI-only — a second provider is
  reachable ONLY through explicit audited config. No provider SDK imports
  in evaluation, consumer, routes, or UI (ruled at v1.1 scoping).
- **WS2 Package evaluation**: `EvaluationRun.run_type = LIVE | PACKAGE` +
  coordinates (package_version, package_hash, consumer_model_provider,
  consumer_model_name). Consumer model resolved through D19 at creation;
  coordinates are BINDING — config/artifact drift FAILS the run (no
  partial verdicts kept). Refusals per the packaged answering contract
  map to INSUFFICIENT_EVIDENCE without junk verdicts. coverage_trend is
  LIVE-only; `package_model_comparison` is computed (D1), absent ≠ zero.
- **WS3 Model selection**: `PackageModelSelection` — ONE current row per
  AgentPackage, history in PACKAGE_MODEL_SELECTED audit events. Evidence
  validated: supporting runs must be COMPLETED PACKAGE runs for the exact
  package_hash; the selected model must appear among them; losing-model
  runs are legitimate (expected) comparative evidence. Rationale required.
- **WS4 ExpertAgentBinding**: append-only snapshots (package coords, model,
  principal clearance at issue, selection evidence, issuing identity
  fact). Binding model MUST equal the current selection at issue. Refuses
  stale selection, hash drift, clearance below package clearance,
  inactive/non-AGENT principals. Mints NO tokens; later selection changes
  never rewrite issued bindings. POST/GET only — no mutation routes.

## Backend module map (`backend/app/`)

| Module | Role |
|---|---|
| `main.py` | **since T2.4 (2026-07-07): 274 lines** — app + CORS + request-id middleware + `startup_event` + `include_router` over the 12 domain routers + the backward-compatible re-export surface (suites import handlers and deps from `app.main` unchanged). The 87 routes' contract is frozen by the route-manifest guard |
| `routers/` | **T2.4: the 12 APIRouter modules** (system, identity_admin, projects, sources, policies, projections, settings, assets, experts, packages, evaluations, insights) — the former inline routes relocated VERBATIM (pure relocation, byte-identical route manifest) |
| `deps.py` | **T2.4: the shared FastAPI dependencies** — `get_db` / `require_actor` / `require_perm` / `_authorize_or_403`, ONE object identity shared by main and every router (suites override `app.dependency_overrides[get_db]`) |
| `audit.py` | **T3.1: the neutral audit-write module** — `log_audit_event` (depends only on database + datetime); crud re-exports it; identity imports it top-level (the crud↔identity cycle removed; `test_import_cycle.py` guards it) |
| `../alembic/` + `alembic.ini` | **T2.3: the migration spine** — baseline `fc4ba7fed054` (frozen; byte-identical to create_all at 28t/305c); `init_db()` = upgrade/stamp/refuse (adopt-by-stamp, ratified); env.py binds to app.database metadata AND the live engine (no second DATABASE_URL) |
| `identity.py` | THE BOUNDARY: principals, credentials, facts, Actor, authorize(), role matrix, legacy migration, validate_boundary |
| `database.py` | SQLAlchemy models + `_ensure_columns()` additive SQLite migrations |
| `crud.py` | CRUD + `log_audit_event(identity_fact_id=...)` + agent package creation (gate-checked) + v1.1 set_package_model_selection / create_expert_agent_binding; governed writes take identity.Actor |
| `ingestion.py` | parse (txt/md/pdf/docx) → chunks → Qdrant index |
| `extraction.py` | per-chunk asset extraction (LLM or rule-based fallback) |
| `claims.py` | atomic claim decomposition (LLM_ATOMIC / RULE_COORDINATION) |
| `verification_engine.py` | NLI three-way verdicts (mDeBERTa-v3), weight fingerprints |
| `conflict_engine.py` | pairwise NLI conflict scan, classifications, conflict score, **compile gate** |
| `revisions.py` | strictly-linear revision workflow; `run_post_approval_rescan` background task |
| `trust.py` | 5-component trust score, weights renormalized over measured components |
| `evaluation.py` | benchmark runs (background) on BOTH channels (run_type LIVE/PACKAGE), persists **ClaimVerdict** rows, `coverage_trend` (LIVE-only), `package_model_comparison` (computed) |
| `governance_inbox.py` | computed inbox + readiness (NO work-item table by design); **v1.2.1 WS4 (D26)**: ingestion exceptions projected from ledger + current facts — five kinds (TIER2_CONTRADICTION_HELD / SOURCE_AUTHORITY_HELD / TIER2_UNVERIFIED / NOT_COVERED / UNCLASSIFIED), most-specific-wins, one severity function loud on unknown kinds, never HIGH (D2), no dismiss; **v1.3.0 WS1 (D28)**: PROJECTION_STALE items (LOW, CAN_WAIT — "stale", never "wrong"; leaves on regeneration alone) |
| `consumption_inbox.py` | **v1.1.1 WS2**: computed consumption inbox — nine ratified drift/hygiene conditions over packages/selections/runs/bindings/identity; ONE shared severity function; pure projection, no dismiss (D24) |
| `binding_lineage.py` | **v1.1.1 WS3**: server-composed binding lineage — backwards to source documents, sideways into identity; every hop resolves or is declared missing (D12); warnings ARE the inbox items |
| `package_builder.py` | .empkg compiler: manifest hash chain, clearance filtering |
| `package_consumer.py` | **v1.1 WS1**: first-class portable-channel consumer — verify, refuse, retrieve package-locally, generate via the D19 adapter seam; imports stdlib + llm ONLY (CI-enforced) |
| `custody.py` | **v1.2.0 (D25)**: outbound credential custody — envelope encryption (EM_SECRET_KEY wraps per-credential data keys), create/rotate/revoke lineage, `release()` (the propose/decide seam, per-scan EXTERNAL_CREDENTIAL_USED), master-key re-wrap (env-only key material, no secret re-entry) |
| `connectors/framework.py` | generic sync/reconciliation engine (D18); v1.2.0: provider registry dispatch + custody release on scan when a credential is bound |
| `connectors/models.py` | provider contract (D18) |
| `connectors/providers/local_folder.py` | LocalFolderProvider (~85 lines) |
| `connectors/providers/sharepoint.py` | **v1.2.0 WS2**: SharePointProvider — four-method contract over Microsoft Graph (client-credentials), injectable transport (fake Graph in CI), verbatim metadata, policy-free; structural purity asserted (stdlib + contract only) |
| `policy.py` | Policy-Based Auto Approval (D17); **v1.2.1 (D26)**: Tier-0 source_conditions evaluation (equals/in, dotted keys, absence never satisfies), domain_covered deny-by-default, deferred_to_tier2 honesty, held exceptions declared with ids; **v1.4.0 (D29)**: `proposal_lane_document_ids` — the lane floor consulted per-document by BOTH tiers; proposal-lane candidates are outside every policy tier, holds declared as `proposal_lane_held_ids` |
| `classification.py` | **v1.2.1 WS1 (D27)**: governed domain classification — deterministic first-match assignment (ASSET_CLASSIFIED with policy snapshot + matched values), taxonomy reorganize (rename prefix-rewrite + policy-driven reclassify, TAXONOMY_REORGANIZED with old→new mapping); writes ONLY the domain column |
| `tier2.py` | **v1.2.1 WS3 (D26)**: async candidate-contradiction check — refusal-to-approve, never rejection; background pass owns its session (D4), verdicts in event provenance ONLY (never AssetRelationship rows), injectable verifier seam (identity always in provenance), drain() hook for suites |
| `proposals.py` | **v1.4.0 WS1 (D29/D30): the proposal lane** — the ONE allowlisted writer of `source_class` (Guard 5 sweeps every other writer): idempotent channel-derivation at scan (PROPOSAL-lane documents → DERIVED assets, INGESTED and CHANGED alike); frontmatter parsing from the stored content-hashed document file (never flattened chunks; claims recorded verbatim, never obeyed); governed provenance verification (binding exists + belongs to the claimed principal + active AGENT + package hash matches; cited assets checked, misses declared, DERIVED citations flagged = derivation depth computable); `approval_provenance` recomputed and quoted verbatim in the ASSET_APPROVED event at the human gate |
| `llm.py` | D19 resolver (DB config → OPENAI_MODEL env → gpt-4o-mini) + **v1.1 provider adapters** (OPENAI/ANTHROPIC) + `generate()` boundary; PACKAGE_CONSUMER function added |
| `mcp_gateway.py` + `mcp_server.py` | MCP read-only tools (9 since v1.3: +get_graph_neighbors / get_lineage_path / get_domain_subgraph — the GOVERNED projection channel, composed live per call, never reading rendered files); EM_AGENT_TOKEN per-call resolution, registry clearance |
| `projections/engine.py` | **v1.3.0 WS1 (D28): THE DECIDER** — compose() governed facts → clearance-filtered deterministic Projection (nodes/edges/domain groups, exclusions counted); render() writes + stamps + emits PROJECTION_RENDERED (the ONLY projection event emitter); is_stale() = recompose-and-compare (exact, no heuristics); render_history() ledger-projected. Content identity excludes stamps: rendered_at + audit_cursor live in manifest + event only. **v1.5.0 WS0 (D31)**: ENGINE_VERSION v2 — the declared content mode (a renderer must declare FULL_CONTENT; the declaration travels in projection + manifest + event; content composed only onto already-included nodes); RENDERERS = spec registry (files/content_mode/output + managed_folders/governance_folder for VAULT); THE FLOOR — `UNTOUCHABLE_FOLDERS` (00_system/07_agent_workspaces/08_proposals, named ONLY here within app/), managed folders confined to the 01–06 window, refusals loud and pre-deletion, output paths refused at write time |
| `projections/contract.py` | **v1.3.0 WS0**: the frozen-dataclass model renderers receive; stamp fields are guard-checked contract fields — an unstamped render structurally cannot exist |
| `projections/renderers/graph.py` | **v1.3.0 WS2**: the graphify port (MIT) — graph.json node-link + self-contained graph.html (search/filter/inspect, conflict edges styled, aggregated fallback above node limit; graph.json never loses detail); imports stdlib + contract + renderer siblings ONLY |
| `projections/renderers/vis_network_js.py` | **v1.3.0 WS2**: vis-network 9.1.6 vendored (gzip+base64 constant, sourceMappingURL stripped, sha256 pinned) — renderers are write-only, so the library lives in code, never in a file to read back |
| `projections/renderers/vault.py` | **v1.5.0 WS1 (D31): the EM Vault renderer** — the second renderer, a CONTENT artifact by ratified amendment (declared FULL_CONTENT mode; clearance filters before content by construction). Six managed folders (01_overview / 02_knowledge / 03_domains / 04_indexes / 05_conflicts / 06_audit): domain-first notes with full governed content, YAML frontmatter (em_rendered/derived/canonical:false + provenance), wikilinks, the VISIBLE "This note is not canonical." line, D30-DERIVED marking; deterministic bytes (volatile stamps live in manifest.json + the ledger event, never in notes — notes link [[render_manifest]]). Deliberately not rendered: summaries/glossary (synthesis, D15), expert/package notes (D9) |
| `operations_view.py` | **v1.4.1 (the D8 amendment)**: the Operations area's pure projection — bound agents + bindings + per-agent proposal stats, the proposal pipeline (provenance verdicts recomputed per read, never stored), PROPOSAL lanes + scan history; ONE endpoint `GET /api/projects/{id}/operations` (assets:read; MCP aggregates stay behind audit:read `/api/agents/activity`); reads write nothing |
| `query_engine.py` | LIVE-channel retrieval + validation + generation + claim verification; `ACCESS_RANK`; v1.4.0: citations carry `source_class` (feeds ask_expert + MCP get_provenance) |

Outside `backend/app/` (deliberately — D29/D22):

| Location | Role |
|---|---|
| `workbench/onboarding_diagnostic.py` | **v1.4.0 WS3: the reference consumer**, never a subsystem — doors ONLY (Guard 5 Part 5 sweeps them in CI permanently): stdlib + `app.package_consumer` + `app.llm` + `mcp`. Verifies the .empkg chain, queries `get_domain_subgraph` (StdioMcpGraphClient = the real stdio door; a graph-client seam lets suites inject an in-process substitute resolving the same token), synthesizes behind an injectable seam (real = `consume()` via D19; CI = deterministic), writes ONE content-hash-named timestamp-free proposal to `/08_proposals` |
| `workbench/customer_operations/` | **v1.6.0: the first commercial workbench bundle** — `workbench.yaml` (manifest: canonical #5, domain scope, binding expectations) + `skills/*.yaml` (the five ratified 13-field contracts) + `runner.py` (doors only, Guard 5-swept: contracts drive runtime behavior — frames read from the YAMLs, non-ACTIVE refused, refusal-first, evidence-driven kinding via `get_revision_history` content, the declared same-subject / cross-document / subject-token evidence rules; ONE proposal per finding to `/08_proposals`, the assist brief to `/07_agent_workspaces`) + `corpus/` (the 12-document plant corpus; `corpus_seed/` = revision-1 content; `CORPUS.md` = the plant map, outside the scanned folder) |
| `workbench/common.py` | **v1.7.0 WS2 (ruling 6): the shared runner plumbing** — the catalog's first reuse moment: door setup, contract loading + ACTIVE gating, the inherited same-subject evidence helpers, the MCP stdio door, content-hashed proposal writing. Stdlib-only, Guard 5-swept. Reuse is by RELATIVE import (`from ..common import …`) — Guard 5 skips relative imports; an absolute `from workbench.common import` trips the doors-only sweep |
| `workbench/compliance_obligation/` | **v1.7.0: the second commercial workbench bundle** — `workbench.yaml` (canonical #9, the sensitivity posture + forbidden_vocabulary, the gated list) + `skills/*.yaml` (six ratified 13-field contracts) + `runner.py` (on common.py; contracts drive runtime — markers/rules/frames/marker_pattern PARSED from the YAMLs; declared as_of clock, refused if absent; gated skills refused live naming the unminted decision; posture enforced pre-write; DERIVED cited as DERIVED) + `corpus/` (12 documents; `CORPUS.md` = the plant map, outside the scanned folder) |
| `workbench/procurement_intelligence/` | **v1.8.0: the third commercial workbench bundle** — `workbench.yaml` (canonical #3, THE INVENTED NUMBER posture + the numeric-overclaim forbidden_vocabulary, the declared clock, the [OE]/[ES]/SEQUENCED lists) + `skills/*.yaml` (six ratified 13-field contracts, incl. the declared `subject_boilerplate_stopwords` evidence-rule refinement) + `runner.py` (on common.py, ZERO shared-module edits; term_class rules/date marker_pattern+auto-renewal+context markers/increase markers/certification requirement+question_template/named policy all PARSED from the YAMLs; date-window arithmetic ONLY from verbatim dates at declared as_of+window_days; the persistent-calendar request refused live) + `corpus/` (12 documents incl. the paraphrase-trap and unparseable-date plants; `CORPUS.md` = the plant map, outside the scanned folder) |
| `workbench/executive_briefing/` | **v1.9.0: the first cross-workbench consumer** — `workbench.yaml` (canonical #1, THE UNSOURCED SENTENCE posture + the 12-phrase forbidden_vocabulary, the visibility budget, the findings ruling, the [PMD]/[OE]/[ES] gated list) + `skills/*.yaml` (six ratified 13-field contracts: five read-compose [now] + one gap [now] + `prepare_executive_briefing` [assist, synth]) + `runner.py` (on common.py, ZERO shared-module edits; the executive frames/origin convention/section list/boundary declarations PARSED from the YAMLs; the declared as_of+since clock, refused if absent; THE UNSOURCED SENTENCE enforced pre-write; exactly one EXECUTIVE_EVIDENCE_GAP proposal kind; the runner-local `BriefingGraphClient` = a subclass adapter over the frozen `get_trust_score`, never a new door). No corpus of its own — the input is the governed state the trio produced |
| `tools/generate_skill_contracts.py` | **v1.6.0: the skill-contract generator** — the master inventory as data (16 workbenches, ~360 subtasks) deterministically emitting one 13-field draft YAML per skill into `docs/skill-contracts/`; drafts are scaffolding, never runtime permission (promotion happens at each workbench's scoping session) |
| `vault/` | **v1.4.0 WS3: the vault skeleton** — `00_system/agent-contract.md` (the operative contract: valve, lanes, frontmatter spec, deployment discipline) + `bootstrap.py` (stdlib-only, idempotent: creates `00_system` / `07_agent_workspaces` (ungoverned scratch, never scanned) / `08_proposals` (the only agent-writable governed ingress); folders 01–06 reserved for the v1.5 vault renderer) |

Key tables: Project, Document(+content_hash), DocumentChunk, KnowledgeAsset,
AssetRevision(+identity_fact_id), AssetReview(+identity_fact_id),
AssetRelationship, ExpertModel, AgentPackage, AuditEvent(+identity_fact_id),
BenchmarkQuestion, EvaluationRun(**+run_type, package coordinates — v1.1**),
EvaluationQuestionResult, ClaimVerdict (immutable), SourceConnector,
IngestionJob, SourceDocument, ApprovalPolicy (versioned, no delete),
LLMFunctionConfig (selection only, D19; provider OPENAI|ANTHROPIC since v1.1),
Principal, Credential, IdentityFact (v1.0),
**PackageModelSelection, ExpertAgentBinding** (v1.1),
**ExternalCredential** (v1.2.0, D25; SourceConnector
+external_credential_id — by reference, never by value),
**ClassificationPolicy** (v1.2.1, D27; the D17 governed shape),
KnowledgeAsset **+domain** (D27, NULL = honestly unclassified),
SourceDocument **+source_metadata_json** (D26, verbatim Tier-0 evidence),
ApprovalPolicy **+source_conditions_json/engine_conditions_json/domains_json**
(D26; NULL preserves v0.10.2 behavior — the D19 invariant),
KnowledgeAsset **+source_class** (D30, TEXT NOT NULL DEFAULT 'PRIMARY' —
PRIMARY | DERIVED, channel-decided; legacy rows PRIMARY by construction,
not reconstruction), SourceConnector **+lane** (D29/D30, TEXT NOT NULL
DEFAULT 'PRIMARY' — PRIMARY | PROPOSAL, the channel declaration the class
derives from). D24 snapshot: **28 tables / 305 columns** (amended
28/303 → 28/305 at the v1.4.0 WS0 gate citing D29+D30 — a real schema
milestone, recorded openly; v1.3.0 held it byte-identical, the D28
constitutional claim). Renders still live in the ledger as
PROJECTION_RENDERED events; proposals persist NO provenance columns —
the proposal document is the immutable evidence, verification rides the
approval event (D1).

## Frontend (`frontend/src/app/page.tsx` + `src/store/index.ts`)

Single-page Next.js + Zustand. **Login gate** (session restore, bearer via one
apiFetch wrapper, 401 re-gates); role-aware: tabs and action surfaces hidden per
`can(user, permission)` mirror (backend remains the source of truth). Tabs:
dashboard (v1.3.0 WS4: the **Projections panel** — declared render parameters
(renderer / compiled-for clearance / optional domain prefix; Render at
assets:approve), history projected from PROJECTION_RENDERED events with the
computed staleness verdict: Current / "Stale — regenerate" / Superseded;
language: "regenerated" never "synced" — no top-level Projections area until
the v1.5 vault renderer creates plurality, D8), inbox (v1.3.0: STALE RENDER
items in Can Wait), documents, **sources** (v1.2.0 WS3: Sources & Connectors —
connector CRUD for LOCAL_FOLDER + SHAREPOINT, credential binding, scan history,
and the credential custody surface: create/rotate/revoke at
credentials:manage, secret entered once and never displayed again, custody
history projected from audit events; LocalFolder administration moved here
from Document Inventory), assets, experts, evaluations, conflicts, revisions,
console (mock), **consumption** (v1.1.1: Selection Workbench / Consumption Inbox /
Binding Explorer — assets:read; selection controls assets:approve; history panel
audit:read; sidebar HIGH badge), agents¹, audit¹, settings² (¹ audit:read,
² settings:manage; settings holds LLM Models + Users & Tokens). Consumption is
URL-addressable: ?tab=consumption&package=N&view=inbox|bindings&binding=M.
Language rulings: "Select model" never "Deploy model"; "binding"/"serving
package" never "deployed agent"; "credential"/"rotate"/"revoke" never
"password"/"delete" — nothing implies a secret can be viewed. UI principle
(v1.2.0 WS3): governance cockpit, never a database viewer — backend stores
the full evidence; the UI shows the actionable projection of it. v1.2.1 WS4:
the approval-policy form (documents tab) grew the Tier-0 source-condition
editor, the Tier-2 engine-verification toggle, and domain coverage — all on
the existing governed route (no separate policy semantics path); asset cards
show the domain path with inline governed correction (ASSET_DOMAIN_CORRECTED,
never a revision); the Governance Inbox ranks ingestion exceptions with
provenance-derived "why held" (language: "held for review"/"exception",
never "rejected by the engine"; "classified"/"corrected", never "moved").
v1.5.0 WS3: the top-level **Projections** area (D8 executed — renderer
plurality graph + vault earned it; the dashboard panel graduated):
render controls built from the metadata-only registry endpoint
(`GET /api/projections/renderers` — name/declared content mode/output
species/managed folders, backend truth never hardcoded), FULL CONTENT
chip on vault history rows, D31 stated in the area header, sidebar
stale badge; language "regenerated", never "synced".
v1.4.1: the top-level **Operations** area (assets:read; sidebar badge =
held candidates) — Workbenches (bound agents: bindings, per-agent
proposal stats, MCP activity merged only for audit:read viewers,
unattributed proposals declared; header states D22: "ExpertMachina never
launches agents"), Proposal Pipeline (verdicts recomputed per read,
verified/unverified chips w/ named reasons, cited evidence w/ missing +
second-generation DERIVED flags, **Accept as DERIVED** = the
pre-existing review PATCH, the area's only write), Lanes & Vault
(PROPOSAL connectors, scan history, scan-now). Sources & Connectors
gained the lane selector (D29 warning on PROPOSAL) + PROPOSAL LANE
badge; the Audit Ledger Explorer gained the synthesis-provenance trace
for DERIVED acceptances. Agent Center stays identity/MCP-facing.
v1.4.0 WS4: the **DERIVED chip** on asset cards with state-dependent truth
(approved: "agent-synthesized, accepted as DERIVED by <human> — synthesis
provenance is on the ASSET_APPROVED event"; candidate: "held for the human
gate (D29) — never auto-approved"); the **"Primary prevails · review #N"**
chip on PRIMARY×DERIVED conflict cards naming the presumptive review target
(presentation only — nothing auto-resolves, the gate is class-blind); the
two proposal exception kinds (PROPOSAL_PROVENANCE_UNVERIFIED MEDIUM /
PROPOSAL_AWAITING_GATE LOW) flow through the existing computed inbox.
Language rulings: "proposal"/"finding"/"accepted as DERIVED"/"held for
review"/"primary prevails"/"agent-synthesized"/"human accepted" — never
"agent-approved", "auto-accepted", "derived is wrong", "rejected by the
engine", or "agent wrote a fact".

## Release log (this development line)

| Version | Commit | Delivered |
|---|---|---|
| v0.9.1–v0.12.0 | `33f23d5`…`413c02a` | see git log: inbox, verdicts, coverage, .empkg, connectors, change detection, auto-approval, framework (D18), transport hardening, LLM settings (D19) |
| v1.0.0 | `55a28a1`…WS4 | identity boundary: Principal/Credential/IdentityFact, the Alice test, authorization matrix, governed agent tokens, migration, recovery (D20 ratified, D21) |
| — | `3ad2ccb` | v1.1 scoping ratified — consumption arc design contract + D22 |
| WS1 | `3e096aa` | first-class package consumer + D19 provider adapters (OPENAI/ANTHROPIC) |
| WS2 | `ff2133c` | package-channel evaluation: run_type + binding coordinates, computed comparison |
| WS3 | `8377361` | governed model selection on the AgentPackage, audited with evidence |
| **v1.1.0** | `5d2a82a` | ExpertAgentBinding — a binding, never a runtime (D22; D23 deferred) |
| — | `b309b34` | v1.1.x workbench scoping ratified — build contract + D24 Workbench Projection Rule |
| WS0 | `5914792` | D24 schema projection guard (adversarially proven, in CI permanently) |
| WS1 | `5d1c4e6` | Consumption area + Selection Workbench (zero new endpoints; + `4e778ed` PACKAGE-citation serialization fix) |
| WS2 | `d77d8b2`+`2f736bf` | Computed Consumption Inbox (nine conditions, one severity function, no dismiss; family-hash drift semantics ratified) |
| **v1.1.1** | `f130d93`+`2e05a67` | Binding Explorer + server-composed lineage — every hop resolves or is declared missing |
| — | `470d08e` | v1.2.0 scoping ratified — build contract + D25 Credential Custody |
| WS0 | `8cfec60` | D25 custody guard (sentinel sweep + adversarial self-proof, in CI permanently); external_credentials schema + D24 snapshot in one commit |
| WS1 | `fe29cd4` | custody lifecycle: credentials:manage (12th permission), release seam, rotation re-points connectors, master-key re-wrap without secret re-entry |
| WS2 | `d368fb4` | SharePointProvider on the unchanged D18 seam (fake Graph in CI; live-tenant evidence slot honestly pending) |
| **v1.2.0** | `b9a20ad` | WS3 Sources & Connectors custody surface — governance cockpit, never a database viewer |
| — | `bcf997e`+`a0db211` | v1.2.1 scoping ratified — build contract + D26 Review by Exception + D27 Domain Taxonomy |
| WS0 | `d73607c` | automation guard (one approval path + revision sentinel, adversarially self-proven, in CI permanently); all D26/D27 schema + D24 snapshot in one commit |
| WS1 | `aaebff2` | domain classification: deterministic assignment, governed correction, audited taxonomy reorganize — the finances-split proof |
| WS2 | `7700cd9` | Tier-0 source authority: verbatim scan metadata persisted, conditions evaluated, authority quoted in provenance — evidence for approval, not approval itself |
| WS3 | `e26e609` | Tier-2 async engine verification: refusal-to-approve never rejection, verdicts in provenance only, deterministic async proof |
| **v1.2.1** | `323cd1d` | WS4 exception surface + the 91.2% corpus acceptance gate — the automation ladder operator-visible |
| — | `8aec538`+`f925ead` | v1.3.0 scoping ratified — build contract + D28 The Projection Rule + user-ratified WS0 gate wording |
| WS0 | `077c2be` | projection guard (4th guard, in CI permanently: no governed writes, renderer purity, PROJECTION_* ledger-only, read-back sentinel, zero schema) + inert contract seam |
| WS1 | `18725e0` | projection engine: deterministic compose/render/history, content identity excludes stamps, staleness = recompose-and-compare, PROJECTION_STALE inbox item |
| WS2 | `2325fdc` | graph renderer (graphify port, MIT): graph.json + self-contained graph.html, vendored vis-network, THE LENS PROOF; guard amendment: renderer siblings allowed, reaching up forbidden |
| WS3 | `0d29f6a` | MCP graph query tools 6→9: lineage as a path query, engine-structure identity, audited denials, hostile-render invisibility |
| **v1.3.0** | `1f6c7c3` | WS4 Projections panel (dashboard, D8) + THE MILESTONE GATE (test_projection_acceptance.py) closing on D24 snapshot byte-identity |
| — | `9dc392e` | v1.4.0 scoping ratified — build contract + D29 The One-Way Valve + D30 Derived Source Class (two separate laws by ruling) |
| WS0 | `a9e672a` | Guard 5 (test_agent_authorship_guard.py, the fifth permanent guard: THE LANE SENTINEL closes the connector_id=NULL hole, 40-route AGENT grid, seven plants) + source_class/lane columns + D24 snapshot 28/305 |
| WS1 | `65c5eb6` | the proposal lane: proposals.py (the one allowlisted class writer), lane on the governed connector route, provenance verified never trusted, quoted verbatim at the human gate; two inbox kinds |
| WS2 | `99728fe` | primary-over-derived discipline (one shared annotator, gate class-blind, nothing auto-resolves) + class travels into packages/projections/MCP/citations |
| WS3 | `0b83a21` | workbench/onboarding_diagnostic.py (reference consumer, doors only) + vault skeleton (00_system contract, 07 scratch, 08_proposals) |
| **v1.4.0** | `3f048e3` | WS4 operator surface (DERIVED chip, Primary-prevails chip, proposal inbox kinds) + THE MILESTONE GATE (test_workbench_acceptance.py: the full loop once, closing on ledger-proves-no-agent-wrote-facts + D24 28/305) |
| **v1.4.1** | `212a0fa` | the Operations area (D8 amendment: earned by Operations-Realm surface plurality; operate = the human gate only, D22 held) + lane selector/badge + audit synthesis-provenance trace; operations_view.py pure projection, ONE read endpoint, 37 CI suites |
| — | `4a93058` | v1.5 scoping ratified — build contract + D31 Render Authority Dies at Ingress |
| WS0 | `c50f99f` | Guard 6 (test_render_ingress_guard.py, the sixth permanent guard: THE LAUNDERING PLANT with real graph-render files, regeneration isolation, the untouchable floor, path discipline) + the declared content mode (ENGINE_VERSION v2) + the managed-folder floor |
| WS1 | `4f87a36` | the vault renderer: six managed folders, domain-first full-content notes, visibly non-canonical, deterministic; WS2 collapsed into WS1 as delivered by ruling |
| WS3 | `7310920` | the top-level Projections area (renderer plurality earned; registry-driven; dashboard panel graduated) |
| **v1.5.0** | `b270994` | WS4 THE MILESTONE GATE (test_vault_acceptance.py: THE DISAPPEARANCE TEST + THE SEAM PROOF, closing at 28/305 — "delete everything, lose nothing; re-submit anything, launder nothing") |
| — | `b53d551` | v1.6 scoping ratified — build contract + the workbench catalog (no D32, no 7th guard, deliberately) |
| WS0 | `f825a9c`+`8694cda` | the skill-contract convention in vault/00_system + THE MASTER SUBTASK INVENTORY (16 workbenches, ~360 skills, boundary-tagged) + 361 generated draft contracts (`f928ebd`) |
| WS1 | `fcfa1d3`+`ce7a270` | the Customer Operations bundle (manifest, five ratified contracts, the plant corpus) + THE CORPUS PROOF (real NLI detects P1 @0.972 / P3 @0.980; consume() refuses before it answers; draft≠ratified swept) |
| WS2 | `c5d08f6` | the runner — a governed skill bundle, not a vague agent (contracts drive runtime, tags are gates, refusal-first, evidence-driven kinding; both modes green) |
| WS3 | `8ecab87`+`9b22926`..`9d56e19` | THE MILESTONE GATE (44th suite, passed first run) + the three declared evidence rules (29→6 findings: same-subject, cross-document, subject-token triggers) |
| **v1.6.0** | `0a8354b`+release | THE COMMERCIAL VERDICT PASSED ("useful, bounded, worth acting on") + the in-browser before/after (Accept-as-DERIVED live, 0→1) + FINAL RATIFICATION at 28/305 |
| — | `a5a6bf3`+`f08445c` | v1.7 scoping ratified (WS0) + WS1: the Compliance & Obligation bundle (6 ratified contracts), the 12-document corpus, THE CORPUS PROOF (45th suite) |
| audit | PRs #1–#9 | the 2026-07-07 audit-hardening block (docs/audit-2026-07-07.md): golden-path e2e restored, H-SEC-1 clearance fix + ROLE_CLEARANCE, pytest harness auto-discovery (H-TEST-1), nightly NLI workflow, quick wins (CORS guard, fail-closed access_level), structured logging (T2.1), hash-locked dependency custody + pip-audit gate (T2.2), NLI/torch split out of base (T2.5), llama-index SHED (T2.6 — base pip-audit ZERO-vuln/ZERO-ignore) |
| T2.3 | PR #10 `f90bb25` | the Alembic migration spine: baseline `fc4ba7fed054` byte-identical to create_all (28t/305c), adopt-by-stamp (ratified), `_ensure_columns` retired, deficient pre-Alembic DBs refused loudly; `test_alembic_migration.py` |
| T2.4 | PR #11 `b55f41f` | main.py router split (pure relocation, ratified): 1805→274 lines, 12 `app/routers/*` + `app/deps.py`; route-manifest BYTE-IDENTITY proven and frozen as a named CI guard (`test_route_manifest.py`, 87 routes) |
| T3.1 | PR #12 `131996c` | the crud↔identity cycle break: `log_audit_event` → neutral `app/audit.py` (crud re-exports; identity's lazy crud import deleted); permanent AST guard `test_import_cycle.py` |
| WS2p1 | PR #13 `2adf29a` | `workbench/common.py` extracted (ruling 6, the catalog's first reuse moment); customer-ops runner refactored onto it, zero assertion edits, zero guard edits |
| WS2 | PR #14 `b00877c` | the Compliance & Obligation runner (contracts drive runtime; declared as_of clock; gated list refused live; posture enforced at source) + THE DIAGNOSIS PROOF (47th suite, first run) + the WS2 gate record (user-ratified; closes the WS1 corpus gate explicitly) |
| **v1.7.0** | PR #15 `c2179c2` (tag v1.7.0) | WS3 THE MILESTONE GATE (48th suite, first run) + THE COMPOSITION PROOF (second-generation DERIVED citations, derivation visible at the gate) + THE COMMERCIAL VERDICT PASSED (the audit-facing reader) + the in-browser before/after (123→122 held, 0→1 accepted DERIVED, zero console errors) |
| — | PR #16 `84c7207` | release: v1.7.0 PROJECT_STATE regeneration (docs-only) |
| WS0 | PR #17 (part of `feat/v18-procurement`) `92db66c` | v1.8 scoping ratified — the ACTIVE SIX consolidations, THE INVENTED NUMBER posture, THE CLAUSE ARITHMETIC PROOF named, the [OE]/[ES]/SEQUENCED lists, the calendar refusal re-affirmed, the 12-doc corpus plan |
| WS1 | `6d0f577` | the six ratified contracts (17 ACTIVE / 13 CONSOLIDATED globally) + the 12-document corpus + THE CORPUS PROOF (69th suite) — clause/date/number extraction preconditions proven before any runner |
| WS2 | `16f0d76` | the Procurement runner on common.py (ZERO shared-module edits) + THE DIAGNOSIS PROOF (70th suite); the declared `subject_boilerplate_stopwords` evidence-rule refinement |
| WS3 | `c58fcba`+`699d57b` | THE MILESTONE GATE (71st suite, first full run) + THE CLAUSE ARITHMETIC PROOF (13 statement-numbers, each verbatim-cited or declared-clock arithmetic) + composition standing + THE COMMERCIAL VERDICT PASSED (the procurement/finance owner) + the in-browser before/after (66→65 held, 0→1 accepted DERIVED, zero console errors) |
| **v1.8.0** | PR #17 `4bb0033` (tag v1.8.0) | the sellable trio complete — customers (v1.6) · risk/compliance (v1.7) · money (v1.8); D24 held 28/305; harness 71/71 |
| — | PR #18 `21fc3d2` | release: v1.8.0 PROJECT_STATE + roadmap regeneration (docs-only) |
| WS0 | `1ae7de1` (part of `feat/v19-executive-briefing`) | v1.9 scoping ratified — the ACTIVE SIX, THE UNSOURCED SENTENCE posture, THE BRIEFING PROOF named, the cross-workbench fixture model, the findings ruling (only EXECUTIVE_EVIDENCE_GAP proposes), the [PMD]/[OE]/[ES] boundary, ZERO door growth |
| WS1 | `9c30871` | the six ratified contracts (23 ACTIVE / 18 CONSOLIDATED globally) + THE CROSS-WORKBENCH FIXTURE + THE FIXTURE PROOF (72nd suite) — both trio corpora in one project, origins derivable, the pending sentinel bounded, the clock discriminating, before any runner |
| WS2 | `7bea282` | the Executive Briefing runner on common.py (ZERO shared-module edits; the `BriefingGraphClient` adapter over the frozen `get_trust_score`) + THE DIAGNOSIS PROOF (73rd suite, eight parts, first run) |
| WS3 | `666ee18`+`84e0827` | THE MILESTONE GATE (74th suite, eight stages) + THE BRIEFING PROOF (182 sourced lines, DERIVED origins named, sentinels/vocabulary on bytes, boundary truthfulness verbatim, the covered question traceless, 13 refusals live, zero door growth) + composition (the briefing consumes its own accepted gap) + THE COMMERCIAL VERDICT PASSED (the CEO reader) + the in-browser before/after (308→307 held, 2→3 accepted DERIVED, zero console errors) |
| **v1.9.0** | PR #19 `a9ded83` (tag v1.9.0) | the first cross-workbench consumer — zero door growth (route manifest byte-identical, MCP frozen at 9 tools); D24 held 28/305; harness 74/74 |

## How to run

- Servers in `.claude/launch.json`: backend = `backend/.venv/Scripts/python -m
  uvicorn app.main:app --port 8000` (cwd `backend`), frontend = `npm run dev`
  (cwd `frontend`, port 3000).
- **First run bootstraps a one-time `admin` password printed to the backend
  console** (flush-guaranteed). Log in, rotate at the banner, then administer
  via Settings → Users & Tokens. MCP agents need an AGENT principal + token
  (`EM_AGENT_TOKEN`); EM_AGENT_ID/EM_AGENT_CLEARANCE are refused explicitly.
- DB: SQLite `backend/expert_machina.db` (live demo data; pre-boundary audit
  rows carry NULL identity_fact_id — honest legacy, never backfilled).
- Frontend checks: `npx tsc --noEmit` clean; `npx eslint src` 0 errors
  (exhaustive-deps warnings baseline) — both in CI.
- Tests: standalone scripts in `backend/`, run with the venv python. FOUR
  layers: PRODUCT (user-visible behavior), ARCHITECTURAL
  (`test_connector_seam.py` — D18; structural purity assertions — D20 and
  v1.1 consumer purity), TRANSPORT (`test_http_api.py` over real HTTP),
  IDENTITY/AUTHZ (`test_identity_boundary.py`, `test_identity_tokens.py`,
  `test_authorization.py`, `test_mcp_gateway.py`, `test_migration.py`).
  **v1.1 consumption suites** (all in CI): `test_package_consumer.py` (WS1),
  `test_package_evaluation.py` (WS2), `test_package_selection.py` (WS3),
  `test_expert_agent_binding.py` (WS4). **v1.1.1 workbench suites** (in CI):
  `test_workbench_projection.py` (the D24 schema guard — update its frozen
  snapshot ONLY alongside a ratified decision, in the same commit),
  `test_consumption_inbox.py`, `test_binding_lineage.py`. **v1.2.0 custody
  suites** (in CI): `test_credential_custody.py` (the D25 guard — sentinel
  sweep across every surface incl. HTTP + adversarial self-proof; permanent),
  `test_sharepoint_provider.py` (fake Graph: auth/throttle/pagination/
  hash-verdict/end-to-end; provider structural purity). **v1.2.1 automation
  suites** (in CI): `test_ingestion_automation_guard.py` (the D26 guard —
  one approval path + revision sentinel under the most permissive policy
  set incl. a live approve-everything Tier-2 fake engine, adversarially
  self-proven; permanent; NOTE: file-based DB + db.SessionLocal override —
  the async Tier-2 pass owns its session, in-memory sqlite breaks threads),
  `test_domain_classification.py` (D27: the finances-split taxonomy proof),
  `test_tier0_source_authority.py` (fake-Graph authority proof, one scan /
  three postures), `test_tier2_engine_verification.py` (deterministic async
  proof via gated fake verifier; verdicts provenance-only),
  `test_automation_corpus.py` (THE milestone gate: 91.2% / 100% exceptions /
  zero revisions / north-star from events alone). **v1.3.0 projection
  suites** (in CI): `test_projection_guard.py` (the D28 guard — the fourth
  permanent guard: projection modules cannot write governed state, renderers
  import stdlib + contract + siblings only and never reach up, PROJECTION_*
  is the only durable trace and only from the package, EM_PROJECTION_DIR
  named nowhere else, write-only file access, read-back sentinel, ten
  planted self-proofs, zero-schema assertion), `test_projection_engine.py`
  (WS1: exact inventory, D9 on composed + written surfaces, byte-identical
  determinism, staleness lifecycle, self-sufficient event, D25 sweep;
  NOTE: its seed() is the shared corpus vocabulary for the WS2/WS3 suites),
  `test_graph_renderer.py` (WS2: THE LENS PROOF — delete everything, lose
  nothing, re-render hash-identical; air-gap; tamper from ledger alone),
  `test_mcp_graph_tools.py` (WS3: the path proof, audited denials,
  hostile-render invisibility), `test_projection_acceptance.py` (THE
  v1.3 MILESTONE GATE: seven stages closing on the ratified D24
  snapshot). **v1.4.0 authorship suites** (in CI):
  `test_agent_authorship_guard.py` (Guard 5, the FIFTH permanent guard —
  AGENT powerlessness frozen, every write route refuses AGENT bearers,
  MCP no-write sweep + frozen 9-tool surface, THE LANE SENTINEL under
  the most permissive policy environment constructible, source_class
  writer allowlist {database.py, proposals.py}, workbench door sweep
  (auto-activated on workbench/), provenance tripwire, seven adversarial
  plants; NOTE: importing this module overrides db.engine — suites
  reusing its checkers import it FIRST, then re-override),
  `test_proposal_lane.py` (WS1: lane on the governed route,
  channel-decided class, the verified chain closing on the opening
  question, four forged postures, the valve live),
  `test_derived_conflict_discipline.py` (WS2: one shared annotator,
  asymmetry on every surface, gate class-blind, class in every consumer
  channel), `test_workbench_pilot.py` (WS3: bootstrap idempotency, door
  sweep, deterministic evidence-backed diagnosis, clearance at both
  doors, the return path), `test_workbench_acceptance.py` (THE v1.4
  MILESTONE GATE: eight stages + the closing lines — every approval
  event carries a non-AGENT identity fact, every APPROVED DERIVED fact
  has a human review, D24 at 28/305), `test_operations_view.py`
  (v1.4.1: the Operations projection — correctness incl. forged
  attribution, purity as deterministic event-free reads, the governed
  route with no write method). **v1.5.0 vault suites** (in CI):
  `test_render_ingress_guard.py` (Guard 6, the SIXTH permanent guard —
  THE LAUNDERING PLANT, regeneration isolation, the untouchable floor's
  loud refusals, path discipline: EM_VAULT_DIR + the untouchable names
  confined to projections/engine.py; adversarially self-proven),
  `test_vault_renderer.py` (WS1: exact inventory,
  clearance-on-note-bytes, marking/frontmatter/wikilinks, determinism
  with manifest.json the one volatile file, the D27 proof both
  directions, regeneration isolation, no-flow-back with a real note,
  D25 sweep), `test_projections_area.py` (WS3: the metadata-only
  registry, the governed render route, the staleness lifecycle on the
  vault), `test_vault_acceptance.py` (THE v1.5 MILESTONE GATE: THE
  DISAPPEARANCE TEST — byte-level 28-table fingerprint identical after
  total deletion, re-render reproducing every ledger hash — + THE SEAM
  PROOF live, closing at 28/305).
  **v1.6.0 customer-ops suites** (in CI): `test_customer_ops_corpus.py`
  (THE CORPUS PROOF — the plants verifiable through EM's own machinery
  before any runner code: real-NLI detection under
  `EM_CORPUS_PROOF_NLI=1` (bare CI skips Part 3 loudly with declared
  fixture conflicts), the revision choreography, reproducible
  consume() refusals via the declared deterministic contract-follower
  at the D19 seam, the draft≠ratified sweep over all 361 generated
  contracts), `test_customer_ops_workbench.py` (THE DIAGNOSIS PROOF —
  plants found + correctly kinded, skill claims conform to the
  ratified contracts, a covered question produces NO finding, a
  SEQUENCED contract refused at runtime, byte-identical, the noise
  plant deferred-declared; NOTE: imports the guard FIRST for its
  door-sweep checker, and the guard import forces
  EM_NLI_VERIFICATION=off — real-NLI mode must restore it after),
  `test_customer_ops_acceptance.py` (THE v1.6 MILESTONE GATE: seven
  stages closing on ledger-proves-no-agent-wrote-facts + 28/305;
  `EM_COMMERCIAL_ARTIFACT_DIR` exports the diagnosis for the business
  reader).
  **Audit-hardening suites (2026-07-07, in CI):** `test_llm_shed.py`
  (T2.6: the mocked native-SDK seam), `test_alembic_migration.py`
  (T2.3: FRESH/CONVERGENCE/ADOPT/REFUSE/IDEMPOTENT — the migration
  spine's dual-path gate), `test_route_manifest.py` (T2.4: the
  route-manifest byte-identity guard, 87 routes, frozen digest —
  update ONLY with a documented contract change, like D24),
  `test_import_cycle.py` (T3.1: identity imports crud by NO means,
  audit stays neutral — AST-based, permanent), plus the restored
  `test_golden_path_e2e.py`. **v1.7.0 compliance suites (in CI):**
  `test_compliance_corpus.py` (WS1 THE CORPUS PROOF — real-NLI P5
  detection under EM_CORPUS_PROOF_NLI=1, the review-interval clock,
  consume() refusing AND answering, the draft≠ratified sweep),
  `test_compliance_workbench.py` (WS2 THE DIAGNOSIS PROOF — contracts
  drive runtime, every plant found/kinded, covered controls silent,
  gated [OE] skill refused live naming the unminted decision, the
  posture sweep over every written byte, byte-identical at pinned
  as_of), `test_compliance_acceptance.py` (WS3 THE MILESTONE GATE +
  THE COMPOSITION PROOF: second-generation DERIVED citations visible
  at the gate; `EM_COMMERCIAL_ARTIFACT_DIR` exports the diagnosis for
  the audit-facing reader). **v1.8.0 procurement suites (in CI):**
  `test_procurement_corpus.py` (WS1 THE CORPUS PROOF — window
  arithmetic from verbatim dates at the pinned as_of both directions,
  the paraphrase-trap non-numeric precondition, the unparseable-date
  refusal precondition, supplier-named consume() refusing AND
  answering, the draft≠ratified sweep at 17/13), `test_procurement_
  workbench.py` (WS2 THE DIAGNOSIS PROOF — six contracts drive
  runtime, every plant found/kinded, covered controls silent incl.
  supplier-named certification coverage, [OE]/[ES]/SEQUENCED refused
  live, the numeric posture swept over every written byte,
  byte-identical at pinned as_of+window_days), `test_procurement_
  acceptance.py` (WS3 THE MILESTONE GATE + THE CLAUSE ARITHMETIC
  PROOF: every number in every finding statement traceable to a
  verbatim clause or the declared clock; `EM_COMMERCIAL_ARTIFACT_DIR`
  exports the diagnosis for the procurement/finance reader).
  **v1.9.0 executive-briefing suites (in CI):**
  `test_executive_fixture.py` (WS1 THE FIXTURE PROOF — the
  cross-workbench governed state is real, origins derivable from
  provenance, the pending sentinel bounded on bytes, the declared
  `since` discriminating, the doors yielding the health signals —
  before any runner; the draft≠ratified sweep at 23/18),
  `test_executive_workbench.py` (WS2 THE DIAGNOSIS PROOF — six
  contracts drive runtime, every sentence sourced, both DERIVED
  origins named, the pending sentinel absent from every byte, the
  boundaries refused live, byte-identical at the declared clock),
  `test_executive_acceptance.py` (WS3 THE MILESTONE GATE + THE
  BRIEFING PROOF: the independent sentence sweep, the boundary quoting
  the gateway's exclusions verbatim, the covered question traceless,
  the briefing consuming its own accepted gap; `EM_COMMERCIAL_ARTIFACT_DIR`
  exports the briefing pack for the CEO reader).
  **CI: the pytest harness auto-discovers EVERY backend/test_*.py**
  (74 suites as of v1.9.0; keeping one out requires an explicit
  NOT_SUITES entry — model-dependent suites run in nightly-nli.yml),
  plus the named constitutional guard steps (D18/D24/route-manifest/
  D25/D26/D28/D29-D30/D31). `test_support.governed_actor` is the
  only way suites obtain actors.
- Env knobs: `EM_GATE_*`, `EM_NLI_*` / `EM_CONFLICT_*`, `EM_PACKAGE_DIR`,
  `OPENAI_API_KEY` (+`OPENAI_MODEL`), **`ANTHROPIC_API_KEY`** (the v1.1
  adapter; keys stay env-based per D19), `EM_CORS_ORIGINS`,
  `EM_AGENT_TOKEN` (MCP), `EM_READ_AUDIT_MODE` (OFF/SAMPLED/FULL),
  **`EM_SECRET_KEY`** (v1.2.0: the custody master key — REQUIRED for any
  outbound-credential operation; missing key = loud refusal, no fallback;
  rotation: set `EM_SECRET_KEY_PREVIOUS`=old + `EM_SECRET_KEY`=new, then
  POST /api/credentials/rotate-master-key — key material never transits
  request bodies), **`EM_PROJECTION_DIR`** (v1.3.0: where renders land;
  default `./projections` cwd-relative — referenced ONLY inside
  app/projections, guard-enforced; renders are disposable: delete freely,
  regenerate identically), **`EM_VAULT_DIR`** (v1.4.0: the vault root —
  consumed by vault/bootstrap.py; the PROPOSAL-lane connector's root_path
  points at `<vault>/08_proposals`), **`EM_BACKEND_DIR`** (v1.4.0: how
  the workbench runner locates app.package_consumer when run outside the
  backend directory).
- Verification tooling note: `preview_screenshot` times out on this machine —
  verify via accessibility snapshot / DOM eval instead.

## Next milestones — the planned arc (ruled July 2026)

**v1.2.0 DELIVERED (July 2026) — all four gates PASSED**; build contract
+ gate records: docs/credentials-cloud-connector-v1.2.md. The one open
item: the ONE manual live-SharePoint-tenant scan — append its evidence to
the WS2 gate record when tenant access exists (custody metadata only,
never secret material; the slot is recorded honestly as pending, never
silently completed). Also deferred by ruling: LLM provider-key migration
into the custody store (touches D19's resolution invariant — its own
explicit later step; D19 holds unchanged, keys env-based).

**v1.2.1 DELIVERED (July 2026) — all five gates PASSED** (build contract
+ gate records: docs/ingestion-automation-v1.2.1.md; D26 Review by
Exception + D27 Domain Taxonomy ratified). The automation ladder is
live: Tier-1 types (v0.10.2), Tier-0 inherited source authority
(quoted verbatim in provenance — evidence for approval, not approval
itself), Tier-2 async engine verification (refusal-to-approve, never
rejection), domain classification with audited taxonomy operations,
and the exception surface (five kinds, ranked, provenance-explained,
computed — no new workflow state). Corpus gate: 91.2% auto-approved,
100% exceptions surfaced, zero revisions auto-approved, zero silent
holds, north-star metric from the ledger alone. Still open from
v1.2.0: the ONE manual live-SharePoint-tenant scan (honest pending
slot in the WS2 gate record of credentials-cloud-connector-v1.2.md).

**v1.3.0 DELIVERED (2026-07-02) — all five gates PASSED** (build
contract + gate records: docs/projection-engine-v1.3.md; **D28 The
Projection Rule** ratified: a projection is a governed lens over the
knowledge system, never another knowledge system). The constitutional
claim held end-to-end: ZERO schema change — the D24 snapshot is
byte-identical to v1.2.1's, asserted in CI permanently. Delivered
guard-before-the-door in five gated workstreams: WS0 the projection
guard (the fourth permanent guard) + the contract seam; WS1 the
engine (deterministic compose, content identity excludes stamps,
staleness = recompose-and-compare, PROJECTION_STALE LOW inbox item);
WS2 the graph renderer (graphify port under MIT, vendored vis-network,
air-gapped single-file graph.html, THE LENS PROOF; guard amendment:
renderer siblings allowed, reaching up forbidden); WS3 MCP graph query
tools (6→9 — lineage as a path query, the ratified surface-assertion
update); WS4 the Projections panel (dashboard per D8) + THE MILESTONE
GATE. Still open from v1.2.0: the ONE manual live-SharePoint-tenant
scan (honest pending slot in credentials-cloud-connector-v1.2.md).

**v1.4.0 DELIVERED (2026-07-02) — all five gates PASSED** (build
contract + gate records: docs/diagnostic-workbench-v1.4.md; **D29 The
One-Way Valve + D30 Derived Source Class** ratified as two separate
laws). The Operations Realm opened guard-before-the-door: WS0 Guard 5
(`test_agent_authorship_guard.py`, the fifth permanent guard family —
THE LANE SENTINEL closed the connector_id=NULL global-policy hole
before any workbench code existed) + the two ratified columns (D24
snapshot 28/303 → 28/305, openly); WS1 the proposal lane (channel
decides class, provenance verified never trusted, quoted verbatim at
the human gate); WS2 primary-over-derived discipline (one shared
annotator, gate class-blind, nothing auto-resolves) + class travels
into every consumer channel; WS3 the reference workbench (outside the
backend, doors only) + the vault skeleton; WS4 the operator surface +
THE MILESTONE GATE — the full loop once, closing on the ledger alone
proving no agent principal wrote canonical facts directly. **TWO open
honest slots**: the ONE manual live-SharePoint-tenant scan (v1.2.0,
still pending) and **the ONE real-model diagnostic run** (v1.4.0 —
no provider key in the release environment; the stdio MCP door and
D19 synthesis path are code-complete in workbench/; append evidence
to the WS4 gate record when a key is available).

**v1.5.0 DELIVERED (2026-07-03) — all gates PASSED** (build contract +
gate records: docs/em-vault-v1.5.md; **D31 Render Authority Dies at
Ingress** ratified). Delivered guard-before-the-door: WS0 Guard 6
(`test_render_ingress_guard.py`, the sixth permanent guard family —
THE LAUNDERING PLANT proven with real graph-render files before the
vault renderer existed) + the declared content mode + the
managed-folder floor; WS1 the vault renderer (WS2 collapsed into it as
delivered, by ruling); WS3 the top-level Projections area (renderer
plurality earned, exactly as the v1.3 scoping ruled); WS4 THE
MILESTONE GATE — THE DISAPPEARANCE TEST + THE SEAM PROOF, closing on
the user's verdict: *"delete everything, lose nothing; re-submit
anything, launder nothing"* and the final line 28 tables / 305
columns. **The planned arc (v1.2 → v1.5, the road to the Operations
Realm) is COMPLETE.**

**v1.6.0 DELIVERED (2026-07-03) — all gates PASSED incl. THE
COMMERCIAL VERDICT** (build contract + all gate records:
docs/customer-ops-workbench-v1.6.md; companion artifacts:
docs/workbench-catalog.md — the 16-workbench commercial map — and
docs/workbench-skill-registry.md — the master subtask inventory +
361 generated draft contracts). **No new law, deliberately**: no D32
(the named ruling moment = skill-aware acceptance) and no seventh
guard family (Guard 5 swept every new module with zero edits). Three
future decisions NAMED, not minted: **the Operational Evidence Realm**
(transactional records as finding evidence — every workbench stays in
its document slice until minted), **Exception Stewardship** ("the
exception never becomes a row; the human decisions about it do"), and
**the Pipeline Metadata Door** (what agents may know ABOUT ungated
material — metadata only, expected). The signal-to-noise arc is a
recorded commercial finding: NLI thresholds cannot separate
parallel-timeframe different-subject false positives; three declared,
contract-backed evidence rules took the diagnosis 29→6 findings.

**v1.7.0 DELIVERED (2026-07-07) — all gates PASSED incl. THE
COMMERCIAL VERDICT** (build contract + all gate records:
docs/compliance-workbench-v1.7.md). The second commercial workbench,
in four user-ratified gates: WS0 the rulings (the ACTIVE SIX, the
split ruling, the gated list, the deadline deferral, the sensitivity
posture); WS1 the contracts + the 12-document corpus + THE CORPUS
PROOF (real-NLI P5 detection, the review-interval clock, consume()
refusing AND answering — before any runner existed); WS2
`workbench/common.py` (the catalog's first reuse moment) + the runner
(contracts drive runtime; declared as_of; gated list refused live;
posture enforced at source) + THE DIAGNOSIS PROOF; WS3 THE MILESTONE
GATE + **THE COMPOSITION PROOF** (registry rule 6 live for the first
time: accepted obligation → DERIVED in the recompiled package →
second-generation finding citing DERIVED evidence, derivation visible
at the gate) + THE COMMERCIAL VERDICT (the audit-facing reader) + the
in-browser before/after. **No new law, again: no D32, no seventh
guard family** — Guard 5 swept common.py and the new runner with zero
edits. The honest slots carried: the real-model diagnostic run
(PENDING, no key — the compliance audit-readiness pack is this
workbench's vehicle) and the v1.2.0 live-SharePoint scan.

**v1.8.0 DELIVERED (2026-07-07) — all gates PASSED incl. THE
COMMERCIAL VERDICT** (build contract + all gate records:
docs/procurement-workbench-v1.8.md). The THIRD commercial workbench —
completing the ratified sellable trio (customers → risk/compliance →
money) — in four user-ratified gates: WS0 the rulings (the ACTIVE SIX
with their consolidations, THE INVENTED NUMBER posture, THE CLAUSE
ARITHMETIC PROOF named, the [OE]/[ES] gated list, the SEQUENCED pair,
the calendar refusal re-affirmed); WS1 the six contracts + the
12-document corpus + THE CORPUS PROOF (clause/date/number extraction
preconditions, the paraphrase-trap and unparseable-date preconditions,
supplier-named consume() refusing AND answering — before any runner
existed; the global draft≠ratified sweep at 17 ACTIVE / 13
CONSOLIDATED); WS2 the runner on `workbench/common.py` with **ZERO
shared-module edits** (the second proof the reuse foundation
industrializes) + THE DIAGNOSIS PROOF, plus a declared
`subject_boilerplate_stopwords` evidence-rule refinement (the
signal-to-noise precedent, third occurrence); WS3 THE MILESTONE GATE +
**THE CLAUSE ARITHMETIC PROOF** (13 statement-numbers, each
verbatim-cited or declared-clock arithmetic; no persistent calendar
anywhere) + composition standing (DERIVED travels + is cited
second-generation, proven unchanged on a third workbench) + THE
COMMERCIAL VERDICT (the procurement/finance owner) + the in-browser
before/after. **No new law, a third time: no D32, no seventh guard
family** — Guard 5 swept the runner with zero edits. The honest slots
carried: the real-model diagnostic run (PENDING, no key — the
renegotiation brief is this workbench's vehicle) and the v1.2.0
live-SharePoint scan.

**v1.9.0 DELIVERED (2026-07-08) — all gates PASSED incl. THE
COMMERCIAL VERDICT** (build contract + all gate records:
docs/executive-briefing-v1.9.md). The FIRST cross-workbench consumer —
it reads the governed state the sellable trio produced — in four
user-ratified gates: WS0 the rulings (the ACTIVE SIX, THE UNSOURCED
SENTENCE posture + FALSE COMPLETENESS twin, THE BRIEFING PROOF named,
the cross-workbench fixture model, the findings ruling — only
EXECUTIVE_EVIDENCE_GAP proposes, summaries never re-enter knowledge —
and the [PMD]/[OE]/[ES] boundary); WS1 the six contracts + THE
CROSS-WORKBENCH FIXTURE + THE FIXTURE PROOF (both trio corpora in one
project, origins derivable from provenance, the pending sentinel
bounded on bytes, the declared `since` discriminating — before any
runner; the global draft≠ratified sweep at 23 ACTIVE / 18
CONSOLIDATED); WS2 the runner on `workbench/common.py` with **ZERO
shared-module edits** (a third industrialization proof; the
`BriefingGraphClient` adapter over the frozen `get_trust_score`, never
a new door) + THE DIAGNOSIS PROOF; WS3 THE MILESTONE GATE + **THE
BRIEFING PROOF** (182 sourced lines, DERIVED origins named, the
pending + EXECUTIVE sentinels absent from every written/packaged byte,
the boundary quoting the gateway's exclusions verbatim, the covered
question traceless, 13 refusals live, zero door growth structural) +
composition standing (**the briefing consumes its own human-accepted
evidence gap** — the next briefing cites it `[DERIVED, origin:
executive-briefing]`) + THE COMMERCIAL VERDICT (the CEO reader) + the
in-browser before/after. **No new law, a fourth time: no D32, no
seventh guard family** — Guard 5 swept the runner with zero edits. One
gate-discovered fix recorded: the empty-note marker is a DECLARED
ABSENCE source token ("mandatory sections, even when empty" was
unwritable as built). The honest slots carried: the real-model
diagnostic run (PENDING, no key — a narrated briefing over real
governed facts is this workbench's vehicle) and the v1.2.0
live-SharePoint scan.

**NEXT: the sellable trio is complete and the first cross-workbench
consumer has shipped.** Per the ratified catalog's full-inventory
scoping: **v2.0 Risk & Exception Stewardship** (the [ES] minting
milestone — its own scoping session, likely the seventh guard family,
the ruled shape "the exception never becomes a row; the human
decisions about it do") is next.
Contract Intelligence (catalog #16, the shared extraction engine) is
now EARNABLE — two consumers exist (Compliance + Procurement). Also on
the table: the three named decisions when their pressure arrives (the
Operational Evidence Realm, Exception Stewardship, the Pipeline
Metadata Door — the deferred deadline family unlocks after [ES]), the
two honest slots above, and the standing backlog (SSO/SAML/SCIM; OS
keystore/KMS; Confluence/Drive providers; Gemini/open-model adapters;
**D23 — deferred through nine milestones**; embedding index inside
.empkg; the remaining T3.x polish — main.py unused-import prune,
Pydantic model_config, _iso dedup, N+1 citation batching; ruff/
Dockerfile/pytest-cov/frontend tests). The narrative: v1.2→v1.5 built
the substrate; v1.6 proved a business reader pays attention; v1.7
proved the pattern repeats; v1.8 proved the pattern industrializes (a
third workbench, zero common.py edits, numbers verbatim); **v1.9
proves the pattern composes — the first consumer that reads what other
workbenches produced, cited every sentence or declared its boundary,
and consumed its own human-accepted finding, all with ZERO door
growth (the nine frozen tools + the .empkg were the whole budget).**

**Backlog unchanged by the arc**: SSO/SAML/SCIM enterprise extensions
(gate sales, not the product loop); OS keystore/KMS for the custody
master key (the ruled successor to the env tier); Confluence/Drive
providers (adapter additions now that SharePoint proved the credentialed
path); more provider adapters (Gemini / open models behind the D19
seam); binding lifecycle (**D23, deferred — held through v1.2.0**: no
withdrawal mechanics; likely shape deactivate / never delete / never
mutate history — discuss before building); embedding index inside .empkg.

Deprioritized/deferred: unchanged (semantic auto-approval, revision
auto-approval, AI Governance Analyst, trust history, grouped conflict API,
coverage heatmap, notifications, agent runtime/orchestration — the last is
out of scope by D22, not by omission).

Read `docs/DECISIONS.md` (now through **D31**) for the binding architectural
rulings before changing anything. Any schema change must update the frozen
snapshot in `test_workbench_projection.py` alongside its ratified decision.
Any new automation module must be declared in the D26 guard's
AUTOMATION_MODULES (the event-family sweep fails loudly otherwise). Any
new projection or renderer module is swept automatically by the D28 guard
the moment it exists under `app/projections/` — projection code cannot
write governed state, renderers present and never decide, and rendered
artifacts are never inputs. Any new workbench module is swept automatically
by the D29/D30 guard the moment it exists under `workbench/` — doors only
(stdlib + app.package_consumer + app.llm + mcp); the only writer of
`source_class` is app/proposals.py; proposal-lane candidates are outside
every policy tier, permanently ("trusted agent auto-accept" requires an
explicit register supersession, never configuration). Any new VAULT
renderer spec is confined by the D31 floor: managed folders only inside
the 01–06 window, the untouchable folders (00_system / 07_agent_workspaces
/ 08_proposals) outside every render path, EM_VAULT_DIR and the untouchable
names confined to projections/engine.py within app/. Six permanent guard
families now stand in CI: D24 schema, D25 custody, D26 automation, D28
projection, D29/D30 authorship, D31 render ingress.
