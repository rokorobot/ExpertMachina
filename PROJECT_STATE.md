# ExpertMachina — PROJECT STATE

> Session-reload artifact. Load this (plus `docs/DECISIONS.md` and `docs/roadmap.md`)
> into a fresh AI session to continue work with full project context.
> Regenerate at every milestone release.

**Snapshot:** 2026-07-02 · current version **v1.2.1** (Ingestion Automation &
Domain Classification — all five gates PASSED; the automation ladder is live
and operator-visible) · branch `main` · D26 + D27 ratified (register through
D27)
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

**The mission, stated fully (July 2026 strategy sessions): ExpertMachina is a
two-realm system.** The Knowledge Realm (built, v0.x–v1.1.1) preserves company
knowledge as immutable evidence and compiles it into trusted, agent-ready
packages — D15 absolute: extract and verify, never synthesize. The Operations
Realm (the goal) is diagnostic and improvement workbenches — bound agents over
expert packages — where synthesis IS the product. The border is the v1.1
consumption arc, and the authorship rule that keeps it honest: **humans author
facts; agents propose them** (human decisions enter as ordinary documents →
PRIMARY facts; agent findings re-enter only via the proposal lane → human
gate → DERIVED facts). The knowledge lifecycle is a closed loop; drift is the
normal operating rhythm. Full arc: roadmap.md "The road to the Operations
Realm" + docs/scoping-1.2-credentials-cloud-connector.md.

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
MCP Gateway (live channel)        v0.9     6 read-only tools; v1.0: governed AGENT tokens
                                           (EM_AGENT_TOKEN), registry clearance, per-call
                                           resolution (live revocation), refusals audited
```

The two consumption channels stay honest (D10): MCP = GOVERNED (live
enforcement), .empkg = PORTABLE (verifiable snapshot) — v1.1 made the
portable channel first-class without blurring them.

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
| `main.py` | FastAPI monolith: routes + require_actor/require_perm guards, auth endpoints, identity administration, startup bootstrap/migration/validation; v1.1: package model-comparison/-selection/bindings routes |
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
| `governance_inbox.py` | computed inbox + readiness (NO work-item table by design); **v1.2.1 WS4 (D26)**: ingestion exceptions projected from ledger + current facts — five kinds (TIER2_CONTRADICTION_HELD / SOURCE_AUTHORITY_HELD / TIER2_UNVERIFIED / NOT_COVERED / UNCLASSIFIED), most-specific-wins, one severity function loud on unknown kinds, never HIGH (D2), no dismiss |
| `consumption_inbox.py` | **v1.1.1 WS2**: computed consumption inbox — nine ratified drift/hygiene conditions over packages/selections/runs/bindings/identity; ONE shared severity function; pure projection, no dismiss (D24) |
| `binding_lineage.py` | **v1.1.1 WS3**: server-composed binding lineage — backwards to source documents, sideways into identity; every hop resolves or is declared missing (D12); warnings ARE the inbox items |
| `package_builder.py` | .empkg compiler: manifest hash chain, clearance filtering |
| `package_consumer.py` | **v1.1 WS1**: first-class portable-channel consumer — verify, refuse, retrieve package-locally, generate via the D19 adapter seam; imports stdlib + llm ONLY (CI-enforced) |
| `custody.py` | **v1.2.0 (D25)**: outbound credential custody — envelope encryption (EM_SECRET_KEY wraps per-credential data keys), create/rotate/revoke lineage, `release()` (the propose/decide seam, per-scan EXTERNAL_CREDENTIAL_USED), master-key re-wrap (env-only key material, no secret re-entry) |
| `connectors/framework.py` | generic sync/reconciliation engine (D18); v1.2.0: provider registry dispatch + custody release on scan when a credential is bound |
| `connectors/models.py` | provider contract (D18) |
| `connectors/providers/local_folder.py` | LocalFolderProvider (~85 lines) |
| `connectors/providers/sharepoint.py` | **v1.2.0 WS2**: SharePointProvider — four-method contract over Microsoft Graph (client-credentials), injectable transport (fake Graph in CI), verbatim metadata, policy-free; structural purity asserted (stdlib + contract only) |
| `policy.py` | Policy-Based Auto Approval (D17); **v1.2.1 (D26)**: Tier-0 source_conditions evaluation (equals/in, dotted keys, absence never satisfies), domain_covered deny-by-default, deferred_to_tier2 honesty, held exceptions declared with ids |
| `classification.py` | **v1.2.1 WS1 (D27)**: governed domain classification — deterministic first-match assignment (ASSET_CLASSIFIED with policy snapshot + matched values), taxonomy reorganize (rename prefix-rewrite + policy-driven reclassify, TAXONOMY_REORGANIZED with old→new mapping); writes ONLY the domain column |
| `tier2.py` | **v1.2.1 WS3 (D26)**: async candidate-contradiction check — refusal-to-approve, never rejection; background pass owns its session (D4), verdicts in event provenance ONLY (never AssetRelationship rows), injectable verifier seam (identity always in provenance), drain() hook for suites |
| `llm.py` | D19 resolver (DB config → OPENAI_MODEL env → gpt-4o-mini) + **v1.1 provider adapters** (OPENAI/ANTHROPIC) + `generate()` boundary; PACKAGE_CONSUMER function added |
| `mcp_gateway.py` + `mcp_server.py` | MCP read-only tools; EM_AGENT_TOKEN per-call resolution, registry clearance |
| `query_engine.py` | LIVE-channel retrieval + validation + generation + claim verification; `ACCESS_RANK` |

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
(D26; NULL preserves v0.10.2 behavior — the D19 invariant). D24 snapshot:
28 tables / 303 columns.

## Frontend (`frontend/src/app/page.tsx` + `src/store/index.ts`)

Single-page Next.js + Zustand. **Login gate** (session restore, bearer via one
apiFetch wrapper, 401 re-gates); role-aware: tabs and action surfaces hidden per
`can(user, permission)` mirror (backend remains the source of truth). Tabs:
dashboard, inbox, documents, **sources** (v1.2.0 WS3: Sources & Connectors —
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
  zero revisions / north-star from events alone). CI enforces all on
  every push. `test_support.governed_actor` is the only way suites obtain actors.
- Env knobs: `EM_GATE_*`, `EM_NLI_*` / `EM_CONFLICT_*`, `EM_PACKAGE_DIR`,
  `OPENAI_API_KEY` (+`OPENAI_MODEL`), **`ANTHROPIC_API_KEY`** (the v1.1
  adapter; keys stay env-based per D19), `EM_CORS_ORIGINS`,
  `EM_AGENT_TOKEN` (MCP), `EM_READ_AUDIT_MODE` (OFF/SAMPLED/FULL),
  **`EM_SECRET_KEY`** (v1.2.0: the custody master key — REQUIRED for any
  outbound-credential operation; missing key = loud refusal, no fallback;
  rotation: set `EM_SECRET_KEY_PREVIOUS`=old + `EM_SECRET_KEY`=new, then
  POST /api/credentials/rotate-master-key — key material never transits
  request bodies).
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

**NEXT: v1.3.0 — Projection Engine + Graph Renderer.** Open a fresh
scoping session per D16 from this file + DECISIONS.md + roadmap.md
(+ the "road to the Operations Realm" arc). It ratifies the projection
rule (the decision number is assigned THERE — deliberately not D25/D26/
D27): no projection is ever authoritative; every render regenerates
from governed facts and is stamped rendered_at + audit cursor.
graphify's export layer is the reference implementation (graph.json +
self-contained graph.html, vendored JS, clearance-filtered before
rendering) + MCP graph query tools — lineage as a path query. The
v1.2.x taxonomy (domain paths) is a ready-made grouping dimension.

The arc onward (v1.3+ directional — see roadmap.md
"The road to the Operations Realm"):
v1.3 renderer-agnostic projection engine + graph renderer (ratifies the
projection rule; graphify's export layer is the reference implementation) →
v1.4 first diagnostic workbench pilot (ratifies derived-source-class
PRIMARY/DERIVED + the one-way valve; vault skeleton: /00_system,
/07_agent_workspaces, /08_proposals) → v1.5 EM Vault (full human-readable
rendered workspace). The acquisition-ladder narrative: v0.10 proved local
acquisition, v0.11 provider abstraction, v1.0 identity, v1.1
consumption+binding, **v1.2 credentialed enterprise acquisition — and
v1.2.1 makes that acquisition workable at scale: humans review by
exception, never by document.**

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

Read `docs/DECISIONS.md` (now through **D27**) for the binding architectural
rulings before changing anything. Any schema change must update the frozen
snapshot in `test_workbench_projection.py` alongside its ratified decision.
Any new automation module must be declared in the D26 guard's
AUTOMATION_MODULES (the event-family sweep fails loudly otherwise).
