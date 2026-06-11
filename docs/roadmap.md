# ExpertMachina Product Roadmap

## Milestone Status

| Milestone | Theme | Status |
| :--- | :--- | :--- |
| MVP 0.2 | Governance & Lifecycle Control | ✅ Completed |
| MVP 0.3 | Evidence-Backed Ask Expert Console | ✅ Completed |
| MVP 0.4 | Expert Model Evaluation & Trust Scorecards | 🔄 In Progress |
| MVP 0.5 | Integrity Fixes | ✅ Completed |
| MVP 0.6 | Semantic Verification (Knowledge Integrity Engine) | ✅ Completed |
| MVP 0.7 | Knowledge QA | ✅ Completed |
| MVP 0.8 | Governance Enforcement & Trust Framework | ✅ Completed — governance core frozen |
| MVP 0.9 | Agent Gateway (MCP) | ✅ Completed — full read-only surface |
| MVP 1.0 | Enterprise Agent Knowledge Platform | 📋 Planned |

---

## MVP 0.2 — Governance & Lifecycle Control (Completed)

The foundational knowledge factory:

- Document ingestion (PDF, DOCX, TXT) with Docling + LlamaIndex parsing and local Qdrant indexing.
- Rule-based and LLM-assisted knowledge asset extraction with quality scoring.
- Document lifecycle state machine (`INGESTED` → `PARSED` → `ASSETS_EXTRACTED` → `PARTIALLY_APPROVED` / `APPROVED` / `ALL_ASSETS_REJECTED` / `DELETED`).
- Human governance review queue with bulk actions and hotkey acceleration.
- Expert Builder grouping `APPROVED` assets into Expert Models.
- Reproducible Agent Package compiler with deterministic manifests.
- Immutable audit ledger with governance bypass protection.

See [walkthrough.md](walkthrough.md) for the end-to-end scenario and [governance.md](governance.md) for lifecycle details.

---

## MVP 0.3 — Evidence-Backed Ask Expert Console (Completed)

Operators query their knowledge base in natural language, with strict grounding constraints scoped to a selected Expert Model.

```text
Question
    ↓
Expert Model Selection
    ↓
Approved Assets Only (Ignore Candidate, Rejected, Archived)
    ↓
Evidence Retrieval (Vector Similarity Matching within Expert Model scope)
    ↓
Evidence Validation (Verify APPROVED status, source_hash, provenance validity)
    ↓
Answer Generation (Prompt grounded strictly on validated evidence)
    ↓
Answer Verification (Claim extraction and source alignment check)
    ↓
Answer + Citations (Document, Page, Section, Hash)
```

Delivered across six sprints:

1. **Ask Expert Console UI** — interactive query console scoped per Expert Model.
2. **Approved Asset Retrieval Engine** — retrieval boundary enforced at both the SQLite and Qdrant layers; only assets bundled in the selected Expert Model are searchable.
3. **Evidence Validation Engine** — pre-generation checks for `APPROVED` status, `source_hash` integrity (tamper detection), and complete provenance metadata. Failing assets are discarded and the discard is audit-logged.
4. **Answer Generation** — generation prompt grounded strictly on validated evidence.
5. **Answer Verification Engine** — claim extraction, evidence mapping, and coverage thresholding. Below-threshold answers are blocked and replaced with **`INSUFFICIENT EVIDENCE`**.
6. **Audit Logging Expansion** — every query is logged with retrieved asset IDs, evidence hashes, answer hash, operator, and timestamp.

The grounding rule — **no evidence = no answer** — is enforced by the verification layer; see [assurance.md](assurance.md) for thresholds and scoring.

---

## MVP 0.4 — Expert Model Evaluation & Trust Scorecards (In Progress)

The objective: make trust in an Expert Model *measurable*. Operators define benchmark datasets of expected questions and answers, run them in reproducible batches against an Expert Model, and receive scorecard metrics quantifying how reliably the model answers (and refuses).

### Completed Sprints

1. **Benchmark Dataset Schema & CRUD** — benchmark questions with `expected_claims`, `expected_answer_type` (`FACTUAL` | `PROCEDURAL` | `POLICY` | `REFUSAL`), `required_citation_count`, `min_required_coverage`, severity, and tags. Full CRUD API per project.
2. **Snapshot-Based Batch Engine** — each evaluation run snapshots the Expert Model's approved asset IDs, asset hashes, and the benchmark question set at run creation time, guaranteeing reproducible evaluation even as governance state changes afterwards. Runs progress through `PENDING` → `RUNNING` → `COMPLETED` / `FAILED`.
3. **Scorecard Metrics** — per-run aggregates: `pass_rate`, `average_coverage_score`, `average_confidence_score`, and the list of failed questions with per-question results (generated answer, unsupported claims, citations). `REFUSAL`-type benchmarks pass only when the console correctly returns `INSUFFICIENT EVIDENCE`.

### Remaining Work

- Evaluation dashboard UI (run history, scorecard visualization, drill-down into failed questions).
- Run-over-run regression comparison (detect trust degradation between Expert Model versions).
- Scheduled / triggered re-evaluation when governance state changes (asset approved, archived, or re-extracted).

---

## MVP 0.5 — Integrity Fixes (Completed)

Knowledge-base audit integrity hardening, prerequisite to any agent-facing surface:

- **Honest provenance** — removed all fabricated citation fallbacks (default approver identities, placeholder hashes, backfilled pages/sections). Missing provenance is reported as `null`, never invented.
- **Approval recording at source** — approving an asset (single or bulk) now writes a real `AssetReview` row with the actual approver and timestamp, so citations carry recorded provenance.
- **Access-level enforcement** — the query engine enforces the asset `access_level` tier (`PUBLIC` < `INTERNAL` < `RESTRICTED` < `EXECUTIVE`) against the caller's clearance. Blocked asset IDs are recorded in the retrieval audit log.
- **Verifier identity in the audit ledger** — every verification verdict records the method, model ID, engine version, and thresholds that produced it.
- **Transparent fallback** — keyword overlap survives only as a clearly labeled zero-dependency fallback (`verifier.method = KEYWORD_OVERLAP`).

---

## MVP 0.6 — Semantic Verification: Knowledge Integrity Engine (Completed)

Replaces lexical claim matching with semantic entailment:

- `verification_engine.py` — local NLI cross-encoder, CPU, no API key required.
- **Multilingual by default** (`mDeBERTa-v3 XNLI`), benchmark-validated on English, Czech, German, and French claims against English evidence — and German evidence against Czech claims — all at 0.97+ confidence. English-optimized mode available via `EM_NLI_MODEL_ID`. **Cross-lingual semantic verification** (e.g. English SOP, Czech operator question) is a first-class, tested capability.
- Embeddings used **only** for candidate evidence retrieval (top-k pre-filter), never as a verification verdict — bi-encoders are blind to negation.
- Three-way verdicts per claim: `ENTAILED` / `UNSUPPORTED` (neutral) / `CONTRADICTED`, each with the model probability as a confidence score.
- `CONTRADICTED` is a **hard fail**: blocks the answer regardless of coverage score.
- **Atomic claim decomposition** — compound policy sentences ("must be logged within 24 hours and reviewed weekly unless escalated") decompose into individually verified atomic claims with condition clauses preserved on every claim they govern. LLM-assisted when a key is present; deterministic coordination splitting otherwise. The decomposition method is recorded in every verification report.
- **Reproducible verifier identity** — every verdict records the model ID, HF snapshot revision, SHA256 of the model weight files, engine version, and thresholds, so any historical verification decision can be reproduced against the exact weights that produced it.
- Labeled verification benchmark dataset: 11 cases spanning verbatim, paraphrase, negation, semantic inversion, neutral, and cross-lingual (CS/DE/FR) — all passing.

---

## MVP 0.7 — Knowledge QA (Completed)

Contradiction detection applied to the knowledge base itself — the Knowledge Integrity Engine pointed at the knowledge, not just at answers.

### Sprint 1 — Semantic Conflict Engine (Completed)

- **Pairwise NLI scan** across the approved assets of an Expert Model, judged in both directions (NLI is asymmetric). Detected relationships stored explicitly: `CONFLICTS_WITH` (with classification and confidence) and `SUPPORTS`; `RELATED` reserved in the schema.
- **Conflict Classifier** (`RULE_METADATA_V1`) — not every contradiction is a policy error: `DIRECT_CONTRADICTION`, `TEMPORAL_SUPERSESSION` (same policy, different document versions), `SCOPE_CONFLICT` (different departments), `ACCESS_CONFLICT` (different clearance tiers).
- **Operator review states** — `DETECTED` → `CONFIRMED` / `DISMISSED` via API; review verdicts survive rescans and are audit-logged. Policies sometimes legitimately conflict across contexts; the human stays in the loop.
- **Calibrated operating point** — knowledge-base scanning runs at a stricter threshold (0.90) than answer verification (0.80): most asset pairs are unrelated, so the prior of true conflict is low, while empirically true conflicts score 0.99+. Configurable via `EM_CONFLICT_*` env vars.
- **Scale guard** — above a pair cap, an embedding pre-filter keeps the most similar pairs and the scan reports exactly how many were dropped (no silent truncation).
- **Cross-lingual conflict detection verified**: a Czech deletion policy contradicting an English retention policy is detected at 0.999.
- API: `POST /api/experts/{id}/conflict-scan`, `GET /api/experts/{id}/conflicts`, `PATCH /api/conflicts/{id}`.

### Sprint 2 — Conflict Review Workbench (Completed)

Operator-facing **Knowledge Conflicts** tab in the dashboard:

- Expert Model selector with on-demand conflict scan and live summary chips (assets, pairs, conflicts, supports), including NLI-unavailable and dropped-pairs warnings.
- Conflict cards grouped by classification, each showing the relationship, classification badge, confidence, status, and both assets' evidence excerpts with deep links to the source assets.
- Confirm / dismiss actions with an **operator decision reason** captured inline — the reason is stored on the relationship and recorded in the audit ledger, turning each review into an audit artifact.
- Status filters (ALL / DETECTED / CONFIRMED / DISMISSED) with live counts; a sidebar badge shows unreviewed conflict count.
- Verified end-to-end against a live scan: a confirmed conflict shows reviewer, timestamp, and reason; dismissed conflicts survive rescans.

### Sprint 3 — Semantic Conflict Score (Completed)

`semantic_conflict_score = 100 − weighted penalty`, explainable and review-sensitive:

- Penalty weights by classification (`DIRECT_CONTRADICTION` 10 > `ACCESS_CONFLICT` 8 > `SCOPE_CONFLICT` 5 > `TEMPORAL_SUPERSESSION` 3) and review status (`CONFIRMED` ×1.2 > `DETECTED` ×1.0 > `DISMISSED` ×0.1 — operator-contextualized conflicts are nearly free).
- Two fields, never one magic number: `semantic_conflict_score` plus a `semantic_conflict_summary` reason string ("1 confirmed direct contradiction, 1 detected access conflict, …") and a full per-line penalty breakdown.
- **Standalone metric**: displayed in the Conflict Review Workbench with its own panel, summary, and itemized penalty chips. It is *never* silently averaged into `quality_score`; combining into a broader Expert Model Trust Score is a future, explicit step.
- Review-sensitive by construction: confirming a conflict lowers the score; dismissing one with a reason restores it. Verified live in the UI (78 → 87 on dismissal).
- Exposed via `GET /api/experts/{id}/conflict-score`, included in scan summaries and the `CONFLICT_SCAN_COMPLETED` audit event, versioned as `conflict-score-v1`.

### Sprint 4 — Asset Revision Workflow (Completed)

Immutable revision history: `knowledge_assets` is the stable logical identity, `asset_revisions` holds immutable content/version records.

**Core rule: approved assets are never edited in place.** Any content edit reaching an `APPROVED` asset — including via the generic asset-update API — is diverted into a new `CANDIDATE` revision; the active approved revision keeps serving until the candidate passes review.

- The asset row is a projection of the active approved revision, so Expert Models, retrieval, packages, and evaluation snapshots reference `asset_id` + active revision by construction.
- Approval supersedes: old revision becomes `ARCHIVED` with `superseded_by_revision_id` set; the new revision records approver, timestamp, and `change_reason`; an `AssetReview` row is written; audit events `ASSET_REVISION_CREATED` / `_APPROVED` / `_REJECTED`.
- **Lazy adoption**: existing assets get revision 1 created from their current state on first approval or first edit — no aggressive migration.
- **Strictly linear**: one pending candidate at a time; branching deferred.
- **Revision integrity check**: evidence validation verifies live asset content against the active revision's `content_hash` (`REVISION_CONTENT_MISMATCH`) — tampering around the workflow is caught at query time. Citations expose the revision number.
- UI: asset cards show `Rev N · Current` and `Candidate Pending` badges.

API: `GET/POST /api/assets/{id}/revisions`, `POST /api/revisions/{id}/review`.

---

## MVP 0.8 — Governance Enforcement & Trust Framework (Completed)

Closes the loop from *detect* to *detect → review → allow publication*. The governance boundary becomes enforcing, not advisory — deliberately sequenced **before** the MCP gateway so external consumers meet a stable v1 governance core rather than evolving semantics.

### Sprint 1 — Package Compile Gates (Completed)

Package publication is a governance event:

- **Unreviewed `DIRECT_CONTRADICTION` or `ACCESS_CONFLICT` → compile blocked** (HTTP 409 with an operator-actionable reason pointing to the Knowledge Conflicts workbench).
- **Dismissed conflicts → allowed** (operator has contextualized them; never block).
- **Confirmed conflicts → configurable policy** (`EM_GATE_CONFIRMED_POLICY`, default `block`).
- Unreviewed scope/temporal conflicts are advisory; blocking classifications configurable via `EM_GATE_BLOCKING_CLASSIFICATIONS`. Optional `EM_GATE_REQUIRE_SCAN=1` blocks models never conflict-scanned.
- Blocked attempts are recorded as `GOVERNANCE_BLOCKED_UNRESOLVED_CONFLICTS` audit events; successful compiles record the full gate verdict (policy, advisory/dismissed counts, scan status) inside `AGENT_PACKAGE_CREATED`.
- Gate preview endpoint: `GET /api/experts/{id}/compile-gate`. The compiler UI surfaces gate blocks in the error banner.

### Sprint 2 — Revision Review Workbench (Completed)

Operator-facing **Revision Reviews** tab closing the API-only review gap:

- Revision queue with Pending / Approved / Rejected / All chips and a sidebar badge for pending candidates.
- Revision cards: asset identity, `Rev N → Rev N+1`, creator, timestamp, change reason.
- **Side-by-side comparison with colorized word-level diff** (removed text struck through in red, added text highlighted in green) plus the metadata operators reviewing governance changes need: content hash, source hash, revision numbers.
- Approve / Reject actions **require a review reason**, recorded in the audit ledger — consistent with conflict review.
- **Self-healing governance on approval**: promoting a revision automatically (1) invalidates operator conflict verdicts involving the revised asset — verdicts are content-bound and judged text that no longer exists; (2) rescans every affected Expert Model; (3) refreshes the semantic conflict score and compile gate. Rescan results (including invalidated review counts) are recorded inside the `ASSET_REVISION_APPROVED` audit event.
- Verified live with a genuine catch: revising the English retention policy resolved its confirmed conflict (re-judged as SUPPORTS at 0.994) **and surfaced a new contradiction with the now-stale Czech translation (0.986)** — re-closing the compile gate until the translation is reviewed. Cross-lingual translation drift detected autonomously.

### Sprint 3 — Expert Model Trust Score (Completed)

A first-class hierarchical object (`trust-score-v1`), never a single opaque number:

| Component | Weight | Source |
| :--- | :--- | :--- |
| Evaluation Reliability | 0.25 | Pass rate of the latest completed benchmark run |
| Evidence Coverage | 0.20 | Average claim coverage of the latest run |
| Conflict Integrity | 0.25 | The semantic conflict score (`conflict-score-v1`) |
| Governance Health | 0.20 | Penalties for governance debt: unreviewed conflicts (−8 each), pending revisions (−5 each), blocked compile gate (−15), missing provenance (−4 each, capped) |
| Revision Freshness | 0.10 | Days since last governance review (tiered: ≤30d=100 … >365d=25) |

- Every component carries a human-readable **reason** — "why not 100?" is always answerable.
- Components without underlying data report **`NOT_MEASURED`** with an actionable reason and are excluded from the weighted aggregate (weights renormalized) — never fabricated.
- Governance Health treats governance signals as distinct from knowledge signals, exactly as designed.
- Displayed on Expert Model cards with the full component breakdown; the heuristic `quality_score` remains separate — metrics are never silently merged.
- `GET /api/experts/{id}/trust-score` and `GET /api/projects/{id}/trust-scores`.

**With Sprint 3 complete, the v1 governance core is frozen**: provenance, semantic verification, conflict detection + classification, immutable revisions, compile gates, conflict score, and trust score are stable external contracts for the MCP gateway. Core governance principles are codified in [governance.md](governance.md).

---

## MVP 0.9 — Agent Gateway (MCP) (In Progress)

Expose the v1 governance core to agent consumers (Claude, Codex, Cursor, and other MCP clients) as a **read-only** transport over the frozen contract — the gateway adds no semantics of its own.

- **[Governance Contract v1](governance-contract-v1.md) written first** ✅ — the normative specification that is the public API surface.

### Sprint 1 — Tier 1 Read-Only Gateway (Completed)

- **`backend/mcp_server.py`** — stdio MCP server (official `mcp` SDK / FastMCP) exposing exactly three tools: `ask_expert`, `get_trust_score`, `check_gate_status`. Write tools (`approve_revision`, `dismiss_conflict`, `publish_package`) are deliberately absent; the test suite asserts the surface.
- **Transport, not policy**: every tool delegates to the same functions the REST console uses — the Ask Expert pipeline was extracted into a single shared `execute_expert_query` service so the gateway *cannot* drift into semantics of its own.
- **Per-agent identity and clearance** from the MCP connection config (`EM_AGENT_ID`, `EM_AGENT_CLEARANCE`), defaulting to `PUBLIC` (most restrictive). Clearance flows into retrieval under Access Model v1 — verified: an EXECUTIVE asset never reaches an INTERNAL-clearance agent's citations.
- **Mandatory `MCP_TOOL_CALLED` audit event** on every call: agent id, tool name, clearance, expert model, gateway version, timestamp. The underlying query events carry the agent as actor — the gateway is part of the governance boundary.
- **stdio discipline**: engine telemetry is routed to stderr so stdout carries JSON-RPC frames only.
- Verified live over a real stdio MCP client session against the dev knowledge base: tool listing, gate verdict (`BLOCKED` on the stale-translation conflict), trust score (87.1 with components), and an evidence-backed answer with revision-aware citations and the full verifier fingerprint — all audit-logged.

Agent connection config example:

```json
{
  "mcpServers": {
    "expertmachina": {
      "command": "C:\\path\\to\\backend\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\backend\\mcp_server.py"],
      "env": { "EM_AGENT_ID": "claude-desktop-rk", "EM_AGENT_CLEARANCE": "INTERNAL" }
    }
  }
}
```

### Operator Console — UI Workspaces (parallel track)

Prioritized UI work activating backend capabilities, ordered by leverage:

1. **Evaluations Workspace** ✅ — benchmark question CRUD (FACTUAL / PROCEDURAL / POLICY / REFUSAL with severity, citation, and coverage requirements), one-click evaluation runs with live polling, run history, and scorecard drill-down (pass rate, avg coverage/confidence, per-question results with unsupported claims). **REFUSAL tests are first-class and visible**: a passed refusal renders "Expert correctly returned INSUFFICIENT EVIDENCE — it knows when not to answer." Completed runs feed Evaluation Reliability and Evidence Coverage, making the Trust Score structurally complete (5/5 components measurable from the UI).
2. **Audit Ledger Explorer** ✅ — the raw event feed upgraded into an investigation surface: server-side filters (actor/agent, target, date range) plus category views (Answer Traces, Agent Gateway, Compile Gates, Revisions, Conflicts, Assets, Documents), and **structured trace rendering per event family**. The Answer Trace answers the core agent-era audit question — *what did the agent know, cite, and rely on?* — showing who asked, clearance, question, retrieved/blocked assets, validated citations, claim verdicts, verifier identity (model + weights hash + claim decomposition), and answer hash. Gate traces show the blocking conflicts and active policy; revision traces show supersession chains, reasons, and auto-rescan results.
3. **Trust Center** — unified view of the governance objects (trust score, conflict score, compile gate, governance health, freshness) per Expert Model.
4. **Settings** — deferred until an identity model exists (policy knobs are env vars today).

### Sprint 2 — Tier 2 Governance Surface + Agent Center (Completed)

The read-only gateway is complete — six tools, exactly as the Governance Contract maps them:

- **`get_provenance(asset_id)`** — chain of custody: document, page, section, hashes, approver identity, active revision. Clearance-checked: assets above the agent's tier are **denied, and the denial is itself an audit event** (`MCP_ACCESS_DENIED` with agent, tool, and required tier).
- **`get_conflicts(expert_model_id)`** — conflict score + all relationships (classification, confidence, review state, decision reasons, verifier fingerprint). Relationship metadata only; asset content stays behind clearance-checked tools.
- **`get_revision_history(asset_id)`** — the immutable revision chain with supersession links and change reasons. Clearance-checked.
- Answer-trace audit details now include citations with **revision numbers**, completing the trace specification.
- Verified live over stdio: a governance-analyst agent walked the "why is trust only 90?" chain (conflicts → provenance → revision history) against the dev knowledge base, and a PUBLIC-clearance agent was denied INTERNAL provenance with the denial recorded.

**Agent Center** (operator console): MCP gateway operations made visible — connected agents with clearance badges, call counts, access denials, refused answers (the system declining to answer an agent), per-tool usage, models touched, and last-seen times. All derived from the audit ledger; the gateway has no state of its own.

No write actions in 0.9 — delivered as specified. Progression: read-only (0.9 ✅) → human-supervised writes (1.1) → autonomous governance workflows (1.2+).

## MVP 1.0 — Enterprise Agent Knowledge Platform (Planned)

The defensible position: agents consume *semantically verified, conflict-checked, revision-controlled, audit-traceable* company knowledge.

## Future Direction

- **Consensus verification** — NLI + LLM evidence judge + provenance + thresholds combined for difficult cases.
- **Knowledge freshness policies** — expiry and re-review schedules per asset class.
- **Multi-operator roles** — reviewer / approver separation of duties.
