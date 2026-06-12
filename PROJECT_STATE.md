# ExpertMachina — PROJECT STATE

> Session-reload artifact. Load this (plus `docs/DECISIONS.md` and `docs/roadmap.md`)
> into a fresh AI session to continue work with full project context.
> Regenerate at every milestone release.

**Snapshot:** 2026-06-12 · current version **v1.1.1** (Consumption Operations Workbench) · branch `main`
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
inspectable without adding new governed state (D24).

## The value chain (all segments working end-to-end)

```
Identity Boundary (v1.0)                   every caller authenticates; the boundary
  callers propose, the boundary decides    decides actors (D20); roles authorize;
  ↓                                        every decision is identity-fact evidence
Source (Connector Framework)      v0.11.0  provider plugins; LocalFolderProvider first (D18)
  ↓ scan-now ingestion            v0.10.0  bulk ingestion, dedup, per-file status
  ↓ change detection              v0.10.1  changed source → candidate revision
Documents → CANDIDATE assets               existing extraction pipeline (LLM or rules)
  ↓ policy auto-approval          v0.10.2  versioned per-project rules, new candidates only (D17)
  ↓ human approval                         review queue (bulk + hotkeys); revisions ALWAYS human-gated
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
- **Authorization** (WS3): 11 permissions × 5 roles, code-resident matrix in
  `identity.ROLE_PERMISSIONS`, enforced by `require_perm` on EVERY route.
  AUTHZ_DENIED always audited; read grants follow EM_READ_AUDIT_MODE.
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
| `governance_inbox.py` | computed inbox + readiness (NO work-item table by design) |
| `consumption_inbox.py` | **v1.1.1 WS2**: computed consumption inbox — nine ratified drift/hygiene conditions over packages/selections/runs/bindings/identity; ONE shared severity function; pure projection, no dismiss (D24) |
| `binding_lineage.py` | **v1.1.1 WS3**: server-composed binding lineage — backwards to source documents, sideways into identity; every hop resolves or is declared missing (D12); warnings ARE the inbox items |
| `package_builder.py` | .empkg compiler: manifest hash chain, clearance filtering |
| `package_consumer.py` | **v1.1 WS1**: first-class portable-channel consumer — verify, refuse, retrieve package-locally, generate via the D19 adapter seam; imports stdlib + llm ONLY (CI-enforced) |
| `connectors/framework.py` | generic sync/reconciliation engine (D18) |
| `connectors/models.py` | provider contract (D18) |
| `connectors/providers/local_folder.py` | LocalFolderProvider (~85 lines) |
| `policy.py` | Policy-Based Auto Approval (D17) |
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
**PackageModelSelection, ExpertAgentBinding** (v1.1).

## Frontend (`frontend/src/app/page.tsx` + `src/store/index.ts`)

Single-page Next.js + Zustand. **Login gate** (session restore, bearer via one
apiFetch wrapper, 401 re-gates); role-aware: tabs and action surfaces hidden per
`can(user, permission)` mirror (backend remains the source of truth). Tabs:
dashboard, inbox, documents, assets, experts, evaluations, conflicts, revisions,
console (mock), **consumption** (v1.1.1: Selection Workbench / Consumption Inbox /
Binding Explorer — assets:read; selection controls assets:approve; history panel
audit:read; sidebar HIGH badge), agents¹, audit¹, settings² (¹ audit:read,
² settings:manage; settings holds LLM Models + Users & Tokens). Consumption is
URL-addressable: ?tab=consumption&package=N&view=inbox|bindings&binding=M.
Language rulings: "Select model" never "Deploy model"; "binding"/"serving
package" never "deployed agent".

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
  `test_consumption_inbox.py`, `test_binding_lineage.py`. CI enforces all on
  every push. `test_support.governed_actor` is the only way suites obtain actors.
- Env knobs: `EM_GATE_*`, `EM_NLI_*` / `EM_CONFLICT_*`, `EM_PACKAGE_DIR`,
  `OPENAI_API_KEY` (+`OPENAI_MODEL`), **`ANTHROPIC_API_KEY`** (the v1.1
  adapter; keys stay env-based per D19), `EM_CORS_ORIGINS`,
  `EM_AGENT_TOKEN` (MCP), `EM_READ_AUDIT_MODE` (OFF/SAMPLED/FULL).
- Verification tooling note: `preview_screenshot` times out on this machine —
  verify via accessibility snapshot / DOM eval instead.

## Next milestones

1. **Enterprise extensions** (integrations, not boundary shape):
   OIDC / SAML / SSO / SCIM / LDAP / Azure AD / Google Workspace; stored
   provider/connector credentials (the D19/D14 cloud-connector unblock);
   enterprise read-audit defaults.
2. **Open consumption-direction items**: more provider adapters (Gemini /
   open models — adapter additions behind the D19 seam), binding lifecycle
   (**D23, deferred — held again at v1.1.1**: no withdrawal mechanics; the
   likely shape is deactivate / never delete / never mutate history —
   discuss before building), embedding index inside .empkg (a format
   decision, not an interpretation of WS1).

Deprioritized/deferred: unchanged (semantic auto-approval, revision
auto-approval, AI Governance Analyst, trust history, grouped conflict API,
coverage heatmap, notifications, agent runtime/orchestration — the last is
out of scope by D22, not by omission).

Read `docs/DECISIONS.md` (now through **D24**) for the binding architectural
rulings before changing anything. Any schema change must update the frozen
snapshot in `test_workbench_projection.py` alongside its ratified decision.
