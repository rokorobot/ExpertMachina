# ExpertMachina — PROJECT STATE

> Session-reload artifact. Load this (plus `docs/DECISIONS.md` and `docs/roadmap.md`)
> into a fresh AI session to continue work with full project context.
> Regenerate at every milestone release.

**Snapshot:** 2026-06-11 · current version **v0.11.1** (transport hardening) · HEAD `c3c0d16` · branch `main`
**Repo:** https://github.com/rokorobot/ExpertMachina

## What ExpertMachina is

A knowledge governance and compilation platform: transforms unstructured enterprise
documents into governed, auditable, evidence-backed Expert Models that AI agents can
safely consume. Category framing: "Knowledge Governance Infrastructure" /
"Governed Knowledge Quality Assurance". Pitch: semantically verified, conflict-checked,
revision-controlled.

## The value chain (all segments working end-to-end)

```
Source (Connector Framework)      v0.11.0  provider plugins; LocalFolderProvider first (D18)
  ↓ scan-now ingestion            v0.10.0  bulk ingestion, dedup, per-file status
  ↓ change detection              v0.10.1  changed source → candidate revision
Documents → CANDIDATE assets               existing extraction pipeline (OpenAI gpt-4o-mini or rules)
  ↓ policy auto-approval          v0.10.2  versioned per-project rules, new candidates only (D17)
  ↓ human approval                         review queue (bulk + hotkeys); revisions ALWAYS human-gated
APPROVED assets                            revision-controlled (never edited in place)
  ↓ governance engines                     conflicts (NLI), claims, verification, trust
Expert Model                               trust score (5 explainable components)
  ↓ compile gate                           blocks on unresolved blocking conflicts
.empkg Expert Package             v0.9.4   hash-chained, clearance-filtered, provider-agnostic
  ↓                                        consumed by external agents (examples/consume_package.py)
MCP Gateway (live channel)        v0.9     6 read-only tools, clearance-checked, audited
```

Operator surface: **Governance Inbox** (v0.9.1) — computed work queue + Compile
Readiness per model; deep links into specialized workbenches; URL-addressable.

## Backend module map (`backend/app/`)

| Module | Role |
|---|---|
| `main.py` | FastAPI monolith, all routes |
| `database.py` | SQLAlchemy models + `_ensure_columns()` additive SQLite migrations |
| `crud.py` | CRUD + `log_audit_event` + agent package creation (gate-checked) |
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
| `connectors/framework.py` | generic sync/reconciliation engine: job lifecycle, URI identity, hash verdicts, dedup, change→revisions, policy hook, audit (zero source-side filesystem ops) |
| `connectors/models.py` | provider contract: ConnectorItem, ConnectorFetchResult, ConnectorProvider (validate/describe/discover/fetch) |
| `connectors/providers/local_folder.py` | LocalFolderProvider: walk, URIs, read, stat — nothing else (~85 lines) |
| `policy.py` | Policy-Based Auto Approval engine: deterministic type+scope match, policy snapshot provenance |
| `mcp_gateway.py` + `mcp_server.py` | MCP read-only tools over Governance Contract v1 |
| `query_engine.py` | retrieval + validation + generation + claim verification; `ACCESS_RANK` |

Key tables: Project, Document(+content_hash), DocumentChunk, KnowledgeAsset,
AssetRevision, AssetReview, AssetRelationship (conflicts, per expert model),
ExpertModel, AgentPackage(+clearance/file/hash/manifest), AuditEvent,
BenchmarkQuestion, EvaluationRun, EvaluationQuestionResult, ClaimVerdict (immutable),
SourceConnector, IngestionJob, SourceDocument (per-scan version history),
ApprovalPolicy (versioned governed fact: asset_types JSON, optional connector
scope, enabled flag, version; no delete — disable preserves audit history).

Auto-approval mechanics (v0.10.2, ruling D17): `policy.apply_auto_approval`
runs after extraction in all three ingestion paths (connector scan — newly
INGESTED files only, manual upload, manual extract), approves matching
CANDIDATE assets via the SAME `crud.update_knowledge_asset` path a human uses,
actor `policy:<name>`. Never touches CHANGED files / candidate revisions.
Audit event types: POLICY_CREATED / POLICY_UPDATED (version bump) /
POLICY_ENABLED / POLICY_DISABLED (no bump), ASSET_AUTO_APPROVED (per-asset
policy snapshot provenance incl. approved_without_human), and
POLICY_AUTOAPPROVAL_COMPLETED (per-run summary incl. declared skips).

## Frontend (`frontend/src/app/page.tsx` + `src/store/index.ts`)

Single-page Next.js + Zustand. Tabs: dashboard, **inbox**, documents (upload + **Scan
Folder** + **Approval Policies** panel + ingestion jobs), assets (review queue with
"Policy: <name>" badge + policy-approved spot-check filter), experts (+trust explainer,
package compiler/export), evaluations (+coverage trend, claim verdicts), conflicts,
revisions, console (mock), agents, audit. Governance workflows are URL-addressable
(`?tab=conflicts&expert=11&relationship=42` etc. hydrate on cold load).

## Release log (this development line)

| Version | Commit | Delivered |
|---|---|---|
| v0.9.1 | `33f23d5` | Governance Inbox & Readiness Console (computed, deep links, URL state) |
| v0.9.2 | `070d535` | Persisted Verification Verdicts (ClaimVerdict, EVIDENCE_GAP items) |
| v0.9.2a | `8afad1d` | Background revision rescan (approval ~0.2s, async recompute) |
| v0.9.3 | `b0e844b` | Answer Coverage Governance (trend endpoint+panel, trust explainer) |
| v0.9.4 | `cc097b5` | Agent Package Builder (.empkg, hash chain, clearance, consumer demo) |
| — | `ef1a424` | Consumer example switched to OpenAI API (provider directive) |
| v0.10.0 | `e9dfb56` | Local Folder Connector (scan-now, dedup, per-file status) |
| — | `05ef588` | Folder ingestion folded into Document Inventory (UI ruling) |
| v0.10.1 | `a66c83d` | Change Detection → candidate revisions via existing machinery |
| v0.10.2 | `051d00a` | Policy-Based Auto Approval (versioned policies, snapshot provenance, D17) |
| v0.11.0 | `77e1408` | Source Connector Framework — LocalFolder retrofitted as a thin provider, behavior identical (zero assertion edits), seam tests, D18 ratified |
| v0.11.1 | `c3c0d16` | Transport hardening (audit): bulk route unshadowed + unified through crud (revision parity — D17 generalized to HTTP), filename sanitization, CORS narrowed, HTTP smoke layer (3rd regression layer), CI enforcement |

## How to run

- Servers defined in `.claude/launch.json`: backend = `backend/.venv/Scripts/python -m
  uvicorn app.main:app --port 8000` (cwd `backend`), frontend = `npm run dev` (cwd
  `frontend`, port 3000). Backend venv: `backend/.venv`.
- DB: SQLite `backend/expert_machina.db` (live demo data, project 1 = Clinical QA
  Automation). Schema migrates additively on startup via `database._ensure_columns`.
  Note: the demo DB contains a DISABLED test policy (id 1, "Low-risk descriptive
  docs") from v0.10.2 live verification — harmless; remove via SQL if a clean
  demo is wanted (there is deliberately no delete endpoint).
- Frontend checks: `npx tsc --noEmit` is clean; `npx eslint src` reports 0 errors /
  17 warnings (exhaustive-deps + one unused var) — both run in CI. (The old claim
  that the build fails on any-type lint errors was STALE — corrected 2026-06-11
  per audit; zero any-types exist in page.tsx/store.)
- Tests: standalone scripts in `backend/`, run with the venv python. THREE layers
  (each catches what the others structurally cannot):
  1. PRODUCT regression — user-visible behavior;
  2. ARCHITECTURAL regression — `test_connector_seam.py` protects the D18
     provider/framework boundary with a fake `fake://` provider;
  3. TRANSPORT regression — `test_http_api.py` drives the real FastAPI app over
     HTTP (route ordering, params, serialization): the function-level suites all
     passed for years while /api/assets/bulk was unreachable; only this layer
     catches that class. CI (.github/workflows/ci.yml) enforces all three on
     every push plus frontend tsc + eslint. Product suites:
  (`test_auto_approval.py`,
  `test_local_connector.py`, `test_claim_verdicts.py`, `test_package_builder.py`,
  `test_governance_inbox.py`, `test_compile_gates.py`, `test_revision_workflow.py`,
  `test_conflict_engine.py` (loads NLI), `test_trust_score.py`, ...). Tests that touch
  ingestion must set their own `ingestion.QDRANT_DIR` (dev server locks `./qdrant_db`).
- Env knobs: `EM_GATE_*` (gate policy), `EM_NLI_*` / `EM_CONFLICT_*` (verifier
  thresholds), `EM_PACKAGE_DIR`, `OPENAI_API_KEY` (+`OPENAI_MODEL`).
- Verification tooling note: `preview_screenshot` times out on this machine — verify
  via accessibility snapshot / DOM eval instead.

## Next milestones (agreed order)

1. **LLM Provider Settings** (small utility milestone; model-per-function; needs a
   config store — app currently has env-vars only). Framing ruling (June 2026):
   future model evaluation is a MEANS — select the best engine for a governed
   Expert Package's deployment — never an LLM-benchmarking end in itself; the
   knowledge and its expert representation are the primary asset, the agent is
   the delivery mechanism.
2. **v1.0 — Identity, roles, credentials, enterprise deployment** (auth deferred until
   here by explicit decision)

A second credential-free provider (Slack/Notion export, git working copy) is
backlog, not scheduled — chosen for a different enumeration shape when wanted;
the "Sources & Connectors" UI area arrives with it (D8).

Deprioritized/deferred: semantic/condition-based auto-approval (formatting-only
diffs, NLI contradiction checks) and revision auto-approval (a separate explicit
decision per D17, phased validation: deterministic → NLI → LLM), AI Governance
Analyst, trust history, grouped conflict API, asset-claim coverage batch engine +
heatmap, notifications, cloud connectors (blocked on credentials), agent
runtime/orchestration (explicitly out of scope).

Read `docs/DECISIONS.md` for the binding architectural rulings before changing anything.
