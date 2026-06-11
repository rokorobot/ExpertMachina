# ExpertMachina — PROJECT STATE

> Session-reload artifact. Load this (plus `docs/DECISIONS.md` and `docs/roadmap.md`)
> into a fresh AI session to continue work with full project context.
> Regenerate at every milestone release.

**Snapshot:** 2026-06-11 · current version **v0.10.1** · HEAD `a66c83d` · branch `main`
**Repo:** https://github.com/rokorobot/ExpertMachina

## What ExpertMachina is

A knowledge governance and compilation platform: transforms unstructured enterprise
documents into governed, auditable, evidence-backed Expert Models that AI agents can
safely consume. Category framing: "Knowledge Governance Infrastructure" /
"Governed Knowledge Quality Assurance". Pitch: semantically verified, conflict-checked,
revision-controlled.

## The value chain (all segments working end-to-end)

```
Folder (Local Connector)          v0.10.0  scan-now bulk ingestion, dedup, per-file status
  ↓ change detection              v0.10.1  changed source → candidate revision
Documents → CANDIDATE assets               existing extraction pipeline (OpenAI gpt-4o-mini or rules)
  ↓ human approval                         review queue (bulk + hotkeys)
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
| `connectors.py` | LOCAL_FOLDER scan worker: dedup, change detection → revisions |
| `mcp_gateway.py` + `mcp_server.py` | MCP read-only tools over Governance Contract v1 |
| `query_engine.py` | retrieval + validation + generation + claim verification; `ACCESS_RANK` |

Key tables: Project, Document(+content_hash), DocumentChunk, KnowledgeAsset,
AssetRevision, AssetReview, AssetRelationship (conflicts, per expert model),
ExpertModel, AgentPackage(+clearance/file/hash/manifest), AuditEvent,
BenchmarkQuestion, EvaluationRun, EvaluationQuestionResult, ClaimVerdict (immutable),
SourceConnector, IngestionJob, SourceDocument (per-scan version history).

## Frontend (`frontend/src/app/page.tsx` + `src/store/index.ts`)

Single-page Next.js + Zustand. Tabs: dashboard, **inbox**, documents (upload + **Scan
Folder** + ingestion jobs), assets, experts (+trust explainer, package compiler/export),
evaluations (+coverage trend, claim verdicts), conflicts, revisions, console (mock),
agents, audit. Governance workflows are URL-addressable
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

## How to run

- Servers defined in `.claude/launch.json`: backend = `backend/.venv/Scripts/python -m
  uvicorn app.main:app --port 8000` (cwd `backend`), frontend = `npm run dev` (cwd
  `frontend`, port 3000). Backend venv: `backend/.venv`.
- DB: SQLite `backend/expert_machina.db` (live demo data, project 1 = Clinical QA
  Automation). Schema migrates additively on startup via `database._ensure_columns`.
- `npm run build` fails on PRE-EXISTING lint errors (any-types, unescaped quotes);
  dev mode works. `npx tsc --noEmit` is clean — use it as the frontend check.
- Tests: standalone scripts in `backend/`, run with the venv python
  (`test_local_connector.py`, `test_claim_verdicts.py`, `test_package_builder.py`,
  `test_governance_inbox.py`, `test_compile_gates.py`, `test_revision_workflow.py`,
  `test_conflict_engine.py` (loads NLI), `test_trust_score.py`, ...). Tests that touch
  ingestion must set their own `ingestion.QDRANT_DIR` (dev server locks `./qdrant_db`).
- Env knobs: `EM_GATE_*` (gate policy), `EM_NLI_*` / `EM_CONFLICT_*` (verifier
  thresholds), `EM_PACKAGE_DIR`, `OPENAI_API_KEY` (+`OPENAI_MODEL`).
- Verification tooling note: `preview_screenshot` times out on this machine — verify
  via accessibility snapshot / DOM eval instead.

## Next milestones (agreed order)

1. **v0.10.2 — Policy-Based Auto Approval** (auto-approve low-risk document classes,
   audit-logged "approved by policy: X"; deterministic class rules first)
2. **v0.11.0 — Source Connector Framework** (multi-source; "Sources & Connectors"
   becomes a first-class UI area only then)
3. **LLM Provider Settings** (small utility milestone; model-per-function; needs a
   config store — app currently has env-vars only)
4. **v1.0 — Identity, roles, credentials, enterprise deployment** (auth deferred until
   here by explicit decision)

Deprioritized/deferred: AI Governance Analyst, trust history, grouped conflict API,
asset-claim coverage batch engine + heatmap, notifications, cloud connectors (blocked
on credentials), agent runtime/orchestration (explicitly out of scope).

Read `docs/DECISIONS.md` for the binding architectural rulings before changing anything.
