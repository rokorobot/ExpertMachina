# ExpertMachina — PROJECT STATE

> Session-reload artifact. Load this (plus `docs/DECISIONS.md` and `docs/roadmap.md`)
> into a fresh AI session to continue work with full project context.
> Regenerate at every milestone release.

**Snapshot:** 2026-06-12 · current version **v1.0.0** (Governance Core Complete) · branch `main`
**Repo:** https://github.com/rokorobot/ExpertMachina

## What ExpertMachina is

A knowledge governance and compilation platform: transforms unstructured enterprise
documents into governed, auditable, evidence-backed Expert Models that AI agents can
safely consume. Category framing: "Knowledge Governance Infrastructure" /
"Governed Knowledge Quality Assurance". Pitch: semantically verified, conflict-checked,
revision-controlled — and as of v1.0, every human, service, and agent is a governed
principal whose permissions are explicitly granted, auditable, and revocable.

## The value chain (all segments working end-to-end)

```
Identity Boundary (v1.0)                   every caller authenticates; the boundary
  callers propose, the boundary decides    decides actors (D20); roles authorize;
  ↓                                        every decision is identity-fact evidence
Source (Connector Framework)      v0.11.0  provider plugins; LocalFolderProvider first (D18)
  ↓ scan-now ingestion            v0.10.0  bulk ingestion, dedup, per-file status
  ↓ change detection              v0.10.1  changed source → candidate revision
Documents → CANDIDATE assets               existing extraction pipeline (OpenAI gpt-4o-mini or rules)
  ↓ policy auto-approval          v0.10.2  versioned per-project rules, new candidates only (D17);
                                           policy facts chain to the triggering actor (WHO) while
                                           D17 provenance carries the WHY — independent by design
  ↓ human approval                         review queue (bulk + hotkeys); revisions ALWAYS human-gated
APPROVED assets                            revision-controlled (never edited in place)
  ↓ governance engines                     conflicts (NLI), claims, verification, trust
Expert Model                               trust score (5 explainable components)
  ↓ compile gate                           blocks on unresolved blocking conflicts
.empkg Expert Package             v0.9.4   hash-chained, clearance-filtered, provider-agnostic
  ↓                                        consumed by external agents (examples/consume_package.py)
MCP Gateway (live channel)        v0.9     6 read-only tools; v1.0: governed AGENT tokens
                                           (EM_AGENT_TOKEN), registry clearance, per-call
                                           resolution (live revocation), refusals audited
```

Operator surface: **Governance Inbox** (v0.9.1) + role-aware UI (v1.0): login gate,
the interface hides what the backend would refuse; Settings → Users & Tokens is the
ADMIN identity-administration surface.

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
  chain. Purity rule enforced in CI: identity vocabulary only — request context
  belongs to a future RequestFact. Landing pads: identity_fact_id on
  AuditEvent / AssetReview / AssetRevision. NULL = pre-boundary legacy, never
  retro-fabricated (D12).
- **Authorization** (WS3): 11 permissions × 5 roles (ADMIN, GOVERNANCE_REVIEWER,
  KNOWLEDGE_OPERATOR, AGENT_CONSUMER, READ_ONLY), code-resident matrix in
  `identity.ROLE_PERMISSIONS`, enforced by `require_perm` on EVERY route (reads
  included). Asset status transitions resolve review-vs-approve. AUTHZ_DENIED
  always audited; write grants audited; read grants follow EM_READ_AUDIT_MODE
  (OFF default / SAMPLED / FULL — the enterprise "who viewed this?" hook).
- **Recovery** (D21): documented manual procedure, no bypass mechanism;
  in-app password resets for everything except root-admin lockout.
- Binding text and evidence: **D20 (ratified) and D21** in docs/DECISIONS.md;
  full design contract in docs/identity-boundary-v1.md.

## Backend module map (`backend/app/`)

| Module | Role |
|---|---|
| `main.py` | FastAPI monolith: routes + require_actor/require_perm guards, auth endpoints, identity administration, startup bootstrap/migration/validation |
| `identity.py` | THE BOUNDARY: principals, credentials, facts, Actor, authorize(), role matrix, legacy migration, validate_boundary |
| `database.py` | SQLAlchemy models + `_ensure_columns()` additive SQLite migrations |
| `crud.py` | CRUD + `log_audit_event(identity_fact_id=...)` + agent package creation (gate-checked); governed writes take identity.Actor, refuse strings |
| `ingestion.py` | parse (txt/md/pdf/docx) → chunks → Qdrant index |
| `extraction.py` | per-chunk asset extraction (LLM `gpt-4o-mini` or rule-based fallback) |
| `claims.py` | atomic claim decomposition (LLM_ATOMIC / RULE_COORDINATION) |
| `verification_engine.py` | NLI three-way verdicts (mDeBERTa-v3), weight fingerprints |
| `conflict_engine.py` | pairwise NLI conflict scan, classifications, conflict score, **compile gate** (`relationship_gate_disposition` = single severity source of truth) |
| `revisions.py` | strictly-linear revision workflow; `run_post_approval_rescan` background task |
| `trust.py` | 5-component trust score, weights renormalized over measured components |
| `evaluation.py` | benchmark runs (background), persists **ClaimVerdict** rows, `coverage_trend` |
| `governance_inbox.py` | computed inbox + readiness (NO work-item table by design) |
| `package_builder.py` | .empkg compiler: manifest hash chain, clearance filtering |
| `connectors/framework.py` | generic sync/reconciliation engine; connector acts as DELEGATED actor chaining to the scheduling actor's fact |
| `connectors/models.py` | provider contract (D18) |
| `connectors/providers/local_folder.py` | LocalFolderProvider (~85 lines) |
| `policy.py` | Policy-Based Auto Approval; firing policies act as DELEGATED actors with on_behalf_of chains |
| `llm.py` | model-per-function resolver (v0.12): DB config → OPENAI_MODEL env → gpt-4o-mini (D19) |
| `mcp_gateway.py` + `mcp_server.py` | MCP read-only tools; EM_AGENT_TOKEN per-call resolution, registry clearance, mcp:consume, MCP_AUTH_REFUSED auditing |
| `query_engine.py` | retrieval + validation + generation + claim verification; `ACCESS_RANK` |

Key tables: Project, Document(+content_hash), DocumentChunk, KnowledgeAsset,
AssetRevision(+identity_fact_id), AssetReview(+identity_fact_id),
AssetRelationship, ExpertModel, AgentPackage, AuditEvent(+identity_fact_id),
BenchmarkQuestion, EvaluationRun, EvaluationQuestionResult, ClaimVerdict (immutable),
SourceConnector, IngestionJob, SourceDocument, ApprovalPolicy (versioned, no delete),
LLMFunctionConfig (selection only, D19), **Principal, Credential, IdentityFact** (v1.0).

## Frontend (`frontend/src/app/page.tsx` + `src/store/index.ts`)

Single-page Next.js + Zustand. **Login gate** (session restore, bearer via one
apiFetch wrapper, 401 re-gates); header shows the authenticated principal +
sign-out; forced-rotation banner while must_change_password. Role-aware: tabs
and action surfaces hidden per `can(user, permission)` mirror (backend remains
the source of truth). Tabs: dashboard, inbox, documents, assets, experts,
evaluations, conflicts, revisions, console (mock), agents¹, audit¹, settings²
(¹ audit:read, ² settings:manage; settings holds LLM Models + **Users & Tokens**:
principal registry, role/clearance edits, password resets, token lineage).
Governance workflows remain URL-addressable.

## Release log (this development line)

| Version | Commit | Delivered |
|---|---|---|
| v0.9.1–v0.12.0 | `33f23d5`…`413c02a` | see git log / previous snapshot: inbox, verdicts, coverage, .empkg, connectors, change detection, auto-approval, framework (D18), transport hardening, LLM settings (D19) |
| — | `55a28a1` | v1.0 scoping ratified — identity boundary design contract |
| — | `2c4f056` | design review: IdentityFact purity, ActionContext separation, credential lineage |
| WS1 | `eea76e5` | identity core: Principal/Credential/IdentityFact + the Alice test |
| WS1c | `6aef4ae` | the boundary decides actors: require_actor, auth endpoints, all ingress converted, delegated chains, login UI |
| WS2b | `675ca12` | governed agent tokens: identity admin endpoints, MCP EM_AGENT_TOKEN, env assertion dead |
| WS3 | `decb173` | authorization: 11×5 matrix, route guards everywhere, role-aware UI, Users & Tokens, least-privilege proofs |
| **v1.0.0** | WS4 | migration verification, boundary self-validation, READ_AUDIT_MODE hook, recovery ruling (D21), D20 ratified |

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
  (`test_connector_seam.py` — D18; structural purity assertions — D20),
  TRANSPORT (`test_http_api.py` over real HTTP), **IDENTITY/AUTHZ**
  (`test_identity_boundary.py` the Alice test, `test_identity_tokens.py`,
  `test_authorization.py` least privilege + READ_AUDIT_MODE,
  `test_mcp_gateway.py` governed agents, `test_migration.py` pre-boundary
  upgrades). CI enforces all on every push. `test_support.governed_actor`
  is the only way suites obtain actors — no bypass exists.
- Env knobs: `EM_GATE_*`, `EM_NLI_*` / `EM_CONFLICT_*`, `EM_PACKAGE_DIR`,
  `OPENAI_API_KEY` (+`OPENAI_MODEL`), `EM_CORS_ORIGINS`, **`EM_AGENT_TOKEN`**
  (MCP), **`EM_READ_AUDIT_MODE`** (OFF/SAMPLED/FULL).
- Verification tooling note: `preview_screenshot` times out on this machine —
  verify via accessibility snapshot / DOM eval instead.

## Next milestones

1. **v1.1 — Enterprise extensions** (integrations, not boundary shape):
   OIDC / SAML / SSO / SCIM / LDAP / Azure AD / Google Workspace; stored
   provider/connector credentials (the D19/D14 cloud-connector unblock);
   enterprise read-audit defaults. None of these change what the boundary
   records or decides.
2. **The strategic differentiator** (the consumption arc, post-boundary):
   transforming unstructured enterprise knowledge into governed, auditable,
   evidence-backed expert systems safely consumable by AI agents — versioned
   Expert Package → per-package model evaluation → best-model selection →
   deployable Expert Agents. Model evaluation is a MEANS, never the end
   (June 2026 purpose ruling; see roadmap Future Direction).

Deprioritized/deferred: unchanged from v0.12 snapshot (semantic auto-approval,
revision auto-approval, AI Governance Analyst, trust history, grouped conflict
API, coverage heatmap, notifications, agent runtime/orchestration).

Read `docs/DECISIONS.md` (now through **D21**) for the binding architectural
rulings before changing anything.
