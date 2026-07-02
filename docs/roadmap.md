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
| MVP 0.9.1 | Governance Inbox & Readiness Console | ✅ Completed |
| MVP 0.9.2 / 0.9.2a | Persisted Verification Verdicts / Background Rescan | ✅ Completed |
| MVP 0.9.3 | Answer Coverage Governance | ✅ Completed |
| MVP 0.9.4 | Agent Package Builder (.empkg) | ✅ Completed |
| MVP 0.10.0 | Local Folder Connector | ✅ Completed |
| MVP 0.10.1 | Change Detection / Incremental Sync | ✅ Completed |
| MVP 0.10.2 | Policy-Based Auto Approval | ✅ Completed |
| MVP 0.11 | Source Connector Framework | ✅ Completed |
| MVP 0.11.1 | Transport Hardening (audit) + CI enforcement | ✅ Completed |
| MVP 0.12 | LLM Provider Settings (governed model-per-function config) | ✅ Completed |
| MVP 1.0 | Enterprise Platform — Identity Boundary (one constitutional release) | ✅ Completed — Governance Core Complete (D20 ratified, D21) |
| v1.1.0 | Expert Package Consumption & Model Binding (the consumption arc) | ✅ Completed — all four WS gates passed (D22, D23 deferred) |
| v1.1.1 | Consumption Operations Workbench | ✅ Completed — D24 ratified, schema projection guard permanent |
| v1.2.0 | Governed Credential Store + First Cloud Connector (SharePoint) | ✅ Completed (July 2026, D25 ratified) — live SharePoint tenant verification pending availability |
| v1.2.1 | Ingestion Automation (policy tiers) + Domain Classification | 🛠 Scoping ratified (July 2026, D26 + D27) — build contract: [ingestion-automation-v1.2.1.md](ingestion-automation-v1.2.1.md) |
| v1.3.0 | Projection Engine + Graph Renderer (agent-facing export) | 🧭 Directional |
| v1.4.0 | First Diagnostic Workbench Pilot (Operations Realm opens) | 🧭 Directional |
| v1.5 | EM Vault (human-readable rendered workspace) | 🧭 Directional |

---

## The 0.9.x line — Governance Operationalization (Completed)

v0.9.0 proved knowledge can be governed; the 0.9.x releases made governance
*operational* and gave it an exit door:

- **0.9.1 Governance Inbox & Readiness Console** — one prioritized operating view
  computed from existing reviewable records (no work-item table); Compile
  Readiness per Expert Model; deep links into the specialized workbenches;
  URL-addressable governance workflows.
- **0.9.2 Persisted Verification Verdicts** — `ClaimVerdict` immutable evaluation
  artifacts (verdict, confidence, evidence assets, verifier weight fingerprint);
  EVIDENCE_GAP inbox items from the latest completed run; human review =
  `VERIFICATION_REVIEWED` audit event, artifact untouched.
- **0.9.2a Background Revision Rescan** — approvals return instantly; NLI
  recomputation runs as a background task with its own session and audit events.
- **0.9.3 Answer Coverage Governance** — coverage/pass-rate/verdict-mix trend
  over evaluation runs; trust explainer with weighted contributions that sum
  exactly to the score.
- **0.9.4 Agent Package Builder** — the compile gate finally guards a real
  artifact: hash-chained, clearance-filtered, provider-agnostic `.empkg` with a
  portable answering contract; external consumer example (OpenAI API).

## The 0.10.x line — Enterprise Knowledge Acquisition (In Progress)

The bottleneck shifted from "can we govern knowledge?" to "can we acquire and
maintain it at enterprise scale?":

- **0.10.0 Local Folder Connector (✅)** — scan-now bulk ingestion over local or
  mounted folders: recursive walk, extension filter, sha256 dedup, per-file
  status, background job with live progress. Connector output becomes ordinary
  documents and CANDIDATE assets — no connector-specific review flow. UI lives
  inside Document Inventory.
- **0.10.1 Change Detection (✅)** — a changed source file becomes a candidate
  revision through the existing revision machinery; per-scan source rows retain
  the full hash history; approved content never changes until a human approves.
- **0.10.2 Policy-Based Auto Approval (✅)** — deterministic, versioned
  per-project rules (asset types, optional connector scope) auto-approve
  low-risk CANDIDATE assets at ingestion through the same transition path a
  human approval uses; every auto-approval carries machine-verifiable policy
  snapshot provenance (`ASSET_AUTO_APPROVED`) and declined assets are declared,
  never silent. Candidate revisions of approved assets remain human-gated by
  ruling (D17). **Explicitly deferred**: semantic/condition-based rules
  (formatting-only diffs, NLI contradiction checks) and revision auto-approval
  — those belong to the phased validation track (deterministic → NLI → LLM).
- **0.11 Source Connector Framework (✅)** — NOT a new connector: an
  architecture extraction. `connectors.py` became a generic
  sync/reconciliation framework plus a thin LocalFolderProvider (~85 lines:
  walk, URIs, read, stat — nothing else) speaking the four-method contract
  (validate / describe / discover / fetch). Behavior identical: all
  pre-existing suites pass with ZERO assertion edits; the framework holds
  zero source-side filesystem operations and processed `fake://` URIs
  end-to-end in the new seam suite (test_connector_seam.py — architectural
  regression, now part of the named contract). D18 ratified on that
  evidence: providers describe, the framework decides. Design contract +
  Phase 1 concern map: [scoping-0.11-connector-framework.md](scoping-0.11-connector-framework.md).
  Future providers (SharePoint / Drive / Confluence / exports) plug in
  without framework changes; credential-requiring ones still wait for v1.x
  identity; the "Sources & Connectors" UI area arrives with the second
  provider type (D8).

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

## MVP 1.0 — Enterprise Agent Knowledge Platform (✅ COMPLETED — Governance Core Complete)

The defensible position: agents consume *semantically verified, conflict-checked, revision-controlled, audit-traceable* company knowledge.

**DELIVERED (June 2026) — D20 ratified with evidence, D21 ruled.** The
boundary shipped as one constitutional release in four workstreams:

- **WS1** (`eea76e5`, `6aef4ae`): Principal/Credential/IdentityFact + the
  Alice test; the actor resolution dependency; every caller-supplied actor
  ingress removed (`?actor=Mallory` proven inert); delegated WHO-chains
  (human → connector → policy) with D17 ActionContext independent; login UI.
- **WS2b** (`675ca12`): governed agent identity — MCP resolves
  EM_AGENT_TOKEN per call (live revocation, registry clearance);
  env-asserted identity refused explicitly; token lifecycle endpoints
  (plaintext once, revoke-never-delete lineage).
- **WS3** (`decb173`): authorization — 11 permissions × 5 roles,
  code-resident, enforced on every route; authenticated identity is
  powerless until authorized; AUTHZ decisions are audit evidence carrying
  identity facts; role-aware UI + Users & Tokens; least-privilege Alice
  story proven (the denial fact keeps READ_ONLY forever after promotion).
- **WS4**: migration verification (pre-boundary databases upgrade, legacy
  rows honestly legacy, snapshots never rewritten, idempotent startup);
  boundary self-validation at startup; EM_READ_AUDIT_MODE hook
  (OFF/SAMPLED/FULL); recovery ruled as documented procedure (D21).

The operating principle achieved: **every human, service, and agent is a
governed principal whose permissions are explicitly granted, auditable,
and revocable** — the architecture rejects "AI can access everything
because it is trusted."

Development then shifted to the strategic differentiator: transforming
unstructured enterprise knowledge into governed, auditable,
evidence-backed expert systems safely consumable by AI agents — ruled
arc-first at the v1.1 scoping session and DELIVERED as v1.1.0 (see the
v1.1.0 section below). SSO-family integrations and stored provider
credentials moved to a later enterprise-extensions milestone without
changing the boundary's shape.

---

### Original scoping record (June 2026, preserved)

**SCOPING RATIFIED (June 2026 session, post-v0.12.0) — full build contract
in `docs/identity-boundary-v1.md`.** The rulings:

1. **One constitutional release, not phased releases.** Identity evidence,
   authentication, roles, and API tokens ship together as v1.0.0 with four
   internal workstreams (evidence → authentication → authorization →
   migration/hardening). An evidence-only release (`authentication_method =
   ASSERTED` everywhere) would be technically honest but operationally still
   let any local browser claim to be GovernanceOfficer — the false assurance
   D14 forbids. A boundary either exists or it doesn't; the milestone is the
   boundary, not its ingredients.
2. **v1.0.0 core**: Principal registry, IdentityFact, password
   authentication, API tokens, role assignment, authorization checks, actor
   resolution dependency, migration of existing actor strings.
3. **v1.1 enterprise extensions**: OIDC/SAML/SSO/SCIM/LDAP/Azure AD/Google
   Workspace — integrations that provide alternative ways to establish
   identity without changing the boundary's shape. Stored provider/connector
   credentials (the D19/D14 cloud-connector unblock) also land here, after
   the boundary exists.
4. **IdentityFact is a real table** (D1): immutable evidence in the
   ClaimVerdict pattern. "Who approved revision 42?" resolves to
   `IdentityFact #183`, never to details-JSON parsing or today's users
   table. The symmetry: Principal changes; IdentityFact never changes —
   mirroring KnowledgeAsset / AssetRevision.
5. **Five principal kinds**: HUMAN, DELEGATED (policy:X, connector:Y —
   authority from a governed object + causal chain), SYSTEM (the engines),
   SERVICE (webhooks/CI/schedulers — credentialed automation), AGENT (MCP
   consumers — tokens + governed clearance).

Evidence base: the v0.12.0 actor-flow audit found 11 routes accepting
caller-supplied actor strings, frontend-hardcoded names, env-asserted MCP
identity, and zero authentication — the precise ingress inventory the
boundary closes.

**Framing (agreed June 2026, at v0.12.0 release): v1.0 is the enterprise
BOUNDARY milestone, not "add login."** The central question it answers:

> Who is allowed to do what, with which credentials, against which
> sources and expert packages?

That one question connects identity, roles, credential storage, cloud
connectors (D14), provider keys (D19), agent access (Access Model v1),
audit actor integrity (today: caller-supplied strings, accepted
limitation), and enterprise deployment.

**Hard warning for the scoping session: do not bolt auth onto routes.
Build the identity model as a governed platform boundary** — the fourth
instance of the D17/D18/D19 shape: callers propose actors; the identity
boundary decides who they are.

**The family principle these articles share** (named at v0.12.0 release,
ratification earned per-instance, never as abstract philosophy):

> Proposal and Decision must be separated.
> Convenience proposes. Governance decides.

D17: policy proposes approval → the transition path decides.
D18: provider proposes source state → reconciliation decides.
D19: configuration proposes a model → resolver precedence decides.
**D20 (candidate, earned at v1.0): caller proposes identity → the
identity boundary decides the actor.**

The real v1.0 question is not "how do users sign in?" but **"how does
the system establish who performed a governed action?"** — today
`"GovernanceOfficer"`, `"policy:X"`, `"connector:Y"` are caller-supplied
strings; after v1.0, actor identity is a governed fact
(authenticated → authorized → audited), touching AuditEvent.actor,
approvals, revisions, policy administration, connector ownership, LLM
settings changes, package compilation, and MCP access at once.

**Candidate acceptance test (start scoping from this, not from a
schema):** Operator Alice approves asset 42; six months later the system
can prove who Alice was, what role she had at that moment, what action
she performed, and which credential authenticated her. If the answer is
only `user_id = 7`, the model is too shallow — a mutable users table
resolves to TODAY'S Alice, not the Alice who acted. Identity facts must
be recorded the way this platform records everything else it trusts:
immutable at action time (the ClaimVerdict/AssetRevision pattern applied
to actors). Until v1.0 ships, D14 remains correct: single operator,
actor strings, no false assurance.

**Refined D20 candidate text** (June 2026 — ratify with evidence when
v1.0 ships):

> Callers propose identity. The identity boundary decides actor.
> Governed actions must record identity facts as immutable historical
> evidence at action time. Future user-table state must never be
> required to explain past governed actions.
> Identity evidence records authentication at action time; authorization
> and user state may change later without altering historical identity
> facts.

Rationale: **governance distrusts reconstruction, not users.**
`user_id = 7` answers "who is Alice today?" — a governed action must
answer "who was Alice when the approval occurred?" Conceptual sketch of
what an approval carries (shape to be discovered in scoping, not
prescribed):

```
IdentityFact: actor_id, display_name, role-at-action-time,
              authentication_method, credential_fingerprint, timestamp
```

**Scoping order (evidence-first, not login-first):** the first question
is "what identity evidence must exist for a governed action to be
explainable six months later?" — then identity facts → authentication →
roles → credential storage → authorization → enterprise deployment, in
that order, not the reverse.

**Existing landing pads** (D14 made new schemas identity-ready on
purpose): ClaimVerdict.evaluator_type/evaluator_id,
AssetRevision.approved_by/approved_at, AssetReview.reviewer/approver,
AuditEvent.actor. v1.0 upgrades these from caller-supplied strings to
boundary-decided evidence.

The milestone arc this completes: v0.10.2 governed approval, v0.11
governed acquisition, v0.12 governed model selection, v1.0 governs
identity — each removes a category of "trust me" and replaces it with
evidence recorded when the action occurred.

---

## v1.1.0 — Expert Package Consumption & Model Binding (Completed)

The consumption arc (build contract: `docs/consumption-arc-v1.md`; ruling
D22; lifecycle question deferred as D23). The strategic read that shaped
it: the consumption loop already existed on the LIVE governed channel
(query_engine + MCP gateway); v1.1 made the PORTABLE package channel
real, evaluable, and bindable. Four workstreams, each accepted at its
gate before the next began:

- **WS1 — First-class Package Consumer** (`app/package_consumer.py`):
  load a .empkg, verify the full hash chain (no unmanifested extras),
  refuse non-PASSED gate snapshots, retrieve package-locally
  (deterministic LEXICAL_OVERLAP_V1, counts declared), generate through
  the D19 resolver. The provider-adapter seam D11 deferred landed in
  `llm.py` with the second provider (ANTHROPIC) behind it — no provider
  SDK imports outside the adapters, ever.
- **WS2 — Package-channel evaluation**: evaluation is ONE concept; the
  channel is a property (`EvaluationRun.run_type = LIVE | PACKAGE` +
  package/consumer-model coordinates). The consumer model is resolved
  through governed D19 config at creation; recorded coordinates are
  binding — config or artifact drift FAILS the run, never mislabels it.
  The referee (NLI / deterministic verification) is never one of the
  player models. `package_model_comparison` is computed, never persisted;
  unrun models are absent, not zero.
- **WS3 — Governed model selection**: `PackageModelSelection` attaches to
  the AgentPackage (ExpertModel = knowledge design, AgentPackage = frozen
  artifact, binding = deployment). One current selection per package;
  every change is a PACKAGE_MODEL_SELECTED audit event with old/new,
  supporting run ids (the losing model's runs included — that IS the
  comparison), rationale, and identity fact. The selected model must have
  a successful PACKAGE run for the exact package_hash.
- **WS4 — ExpertAgentBinding** (never ExpertAgentRuntime): an append-only
  snapshot binding of the CURRENT selection to an existing active AGENT
  principal — package coordinates, model, principal clearance at issue,
  selection evidence, issuing identity fact. Refuses stale selections,
  drifted artifacts, clearance violations, inactive/non-AGENT principals.
  Mints no tokens (identity governance stays in the identity subsystem),
  executes nothing, orchestrates nothing. Later selection changes never
  rewrite issued bindings.

The governed chain achieved, every transition evidence-backed:

```
Knowledge → Expert Model → Agent Package → Package Evaluation
          → Model Comparison → Model Selection → ExpertAgentBinding
```

v1.0 proved *who may access knowledge*; v1.1 proves *which model should
consume a portable expert package, based on evidence, and how that
choice is bound to an agent*. Operator UI for the arc (selection
workbench, binding explorer, comparison dashboard) is deliberately NOT
in v1.1.0 — the backend capability is the product, the UI is visibility;
it follows as a v1.1.x "Consumption Operations Workbench" milestone.

---

## v1.1.1 — Consumption Operations Workbench (Completed)

**v1.1.1 turns governed consumption from backend capability into
operator-visible evidence: selection decisions, computed drift, and
binding lineage are now inspectable without adding new governed state.**

A *product design* milestone, not an architecture milestone (build
contract: `docs/workbench-v1.1x.md`; ruling **D24 — Workbench Projection
Rule**). The acceptance verdict: *the workbench made governed facts
visible without becoming a new source of truth — exactly D24 doing its
job.* Four gates, each accepted before the next workstream began:

- **WS0 — D24 + the schema projection guard**
  (`test_workbench_projection.py`, in CI permanently): freezes the
  v1.1.0 schema — every table, every column — and fails on ANY
  divergence. Adversarially proven against the two most likely
  regressions (a persisted inbox table, an `is_stale` column). The
  snapshot survived the entire milestone untouched: 26 tables, 271
  columns, zero schema change across four workstreams of UI.
- **WS1 — Selection Workbench**: a decision workspace, NOT a
  leaderboard, inside a new top-level **Consumption** area
  (package/model/binding-facing; Agent Center stays
  identity/MCP-facing). Computed comparison, run drill-down, rationale
  history projected from PACKAGE_MODEL_SELECTED audit events, and the
  one write of the whole milestone: the pre-existing model-selection
  PUT. Zero backend endpoints added — every panel projects existing
  reads. Language ruling: "Select model", never "Deploy model".
- **WS2 — Computed Consumption Inbox** (`consumption_inbox.py` + the
  milestone's ONE new endpoint, `GET /api/consumption/inbox`): the
  v0.9.1 inbox pattern applied to consumption. Nine ratified conditions;
  severity from ONE shared function (D2 discipline); no dismiss and no
  mark-resolved — items appear when governed facts drift and leave when
  the facts change. **Family-hash semantics ratified at acceptance**:
  package artifacts are append-only, so drift means *this
  binding/selection points to an older artifact while a newer artifact
  exists in the same package family*.
- **WS3 — Binding Explorer + lineage projection**
  (`binding_lineage.py`, `GET /api/bindings/{id}` + `/lineage`): the
  flagship. From one binding, walk backwards (package snapshot → family
  status → model snapshot → frozen selection evidence → supporting runs
  → packaged assets → source documents) and sideways (AGENT principal →
  credentials summary → provenance events), composed server-side —
  the chain is a product claim, tested as one artifact. Every expected
  hop resolves or is **declared missing** (proven under adversarial
  raw-SQL deletion); issuance evidence is immutable (the Alice test
  applied to bindings); explorer warnings ARE the inbox items (shared
  severity function, the surfaces cannot disagree). Language ruling:
  "binding" and "serving package", never "deployed agent".

Boundaries held for the whole milestone: no new tables, no new writable
columns, no binding status field, no persisted views, no withdrawal
mechanics (**D23 stays DEFERRED**), no orchestration surface (D22).
Found and fixed along the way: the evaluations list 500'd on any
project with PACKAGE runs (PACKAGE citations carry no live
`asset_status` — now honestly None, D12).

## The road to the Operations Realm (v1.2 → v1.5) — Planned

**The two-realm framing (July 2026 strategy sessions).** ExpertMachina's
mission was always larger than the knowledge base: the knowledge base is
the *substrate* for a system of agents and workbenches that diagnose and
improve the company. Formally:

- **Knowledge Realm** (built): preserves original knowledge as immutable
  evidence, governs meaning, compiles agent-ready packages. D15 absolute:
  extract and verify, never synthesize.
- **Operations Realm** (the goal): diagnostic and improvement workbenches —
  bound agents over expert packages — where synthesis IS the product.
  Standard workbench catalog (HR, compliance, onboarding, process
  optimization) instantiated per company.

The border is the v1.1 consumption arc, and the authorship rule that keeps
it honest: **humans author facts; agents propose them.** Human decisions
enter as ordinary documents → PRIMARY facts; agent findings re-enter only
through the proposal lane → human gate → DERIVED facts. The knowledge
lifecycle is a closed loop, and drift (recompile → re-evaluate → re-bind)
becomes the platform's normal operating rhythm.

**The planned arc** (v1.2 detailed, v1.3+ directional — anticipation
discipline; full rationale and dependency chain in
[scoping-1.2-credentials-cloud-connector.md](scoping-1.2-credentials-cloud-connector.md)):

- **v1.2.0 — Governed Credential Store + SharePoint connector
  (✅ COMPLETED July 2026; D25 ratified; live-tenant verification pending
  availability).** The D19/D14 unblock, delivered in four gated
  workstreams (build contract:
  [credentials-cloud-connector-v1.2.md](credentials-cloud-connector-v1.2.md)):
  WS0 the custody guard before the door (`test_credential_custody.py` in
  CI permanently — sentinel sweep + adversarial self-proof; D24 snapshot
  amended in the same commit); WS1 the custody lifecycle (envelope
  encryption under `EM_SECRET_KEY`, ADMIN-only `credentials:manage` as
  the 12th permission, per-scan `EXTERNAL_CREDENTIAL_USED`, the Alice
  test for secrets — the ledger alone proves which generation
  authenticated which scan; rotation re-points bound connectors without
  rewriting history); WS2 SharePointProvider on the unchanged D18 seam
  (fake Graph in CI: auth failure, throttling, pagination, hash-only
  change verdicts; framework decision logic untouched; the one manual
  live-tenant run recorded honestly as pending); WS3 the Sources &
  Connectors area (secret entered once and never displayed again,
  custody history projected from the ledger, role-aware controls —
  "governance cockpit, never a database viewer"). The acquisition
  ladder: **v1.2 proves credentialed enterprise acquisition.**
- **v1.2.1 — Ingestion Automation + Domain Classification (scoping
  ratified July 2026 — D26 Review by Exception + D27 Domain Taxonomy;
  build contract:
  [ingestion-automation-v1.2.1.md](ingestion-automation-v1.2.1.md)).**
  Humans review by exception, never by document (D5
  applied): Tier-0 source-authority inheritance ("approved in the source
  system → approved here, by audited policy"), Tier-2 engine-verified
  auto-approval (the v0.10.2 deferred item), exceptions severity-ranked in
  the inbox. The ≥90%-untouched-by-humans figure is a **mature-corpus
  target**, not a universal acceptance threshold — messy first deployments
  will start lower and climb as policies are tuned. Assets gain a governed
  hierarchical domain
  path (policy-assigned, human-correctable; reorgs nest by default).
  Revision auto-approval stays forbidden (D17) — the known living-KB
  tension, documented and deliberately unresolved.
- **v1.3.0 — Projection Engine + Graph Renderer.** Renderer-agnostic
  export of governed facts (facts → renderer → files); first renderer:
  graph.json + self-contained graph.html (ported from graphify's export
  layer, vendored JS, clearance-filtered before rendering) + MCP graph
  query tools — lineage as a path query. Ratifies the projection rule:
  no projection is ever authoritative; every render regenerates and is
  stamped with `rendered_at` + audit cursor; staleness is computed,
  detectable, never silent.
- **v1.4.0 — First Diagnostic Workbench Pilot.** The Operations Realm
  opens: one workbench (onboarding diagnostic the candidate) on a real
  corpus, its agents bound consumers using existing doors (package +
  MCP). Ratifies derived-source-class (PRIMARY vs DERIVED, synthesis
  provenance, primary-over-derived conflict discipline) and the one-way
  valve. Vault skeleton arrives (/00_system contract, /07 workspaces,
  /08_proposals). Gate: the full loop once, end to end — corpus in,
  evidence-backed diagnosis out, one accepted finding re-entering as a
  DERIVED fact with complete provenance.
- **v1.5 — EM Vault.** The full human-readable rendered workspace
  (Obsidian-compatible, Git-trackable) as the projection engine's second
  renderer; domain-first/type-second asset folders rendering the v1.2.x
  taxonomy; all orientation files generated; D24 disappearance test as
  the gate.

## Future Direction

- **Consensus verification** — NLI + LLM evidence judge + provenance + thresholds combined for difficult cases.
- **Knowledge freshness policies** — expiry and re-review schedules per asset class.
- **Multi-operator roles** — reviewer / approver separation of duties.
- **Expert Agent consumption arc — DELIVERED as v1.1.0** (see the v1.1.0
  milestone section above; purpose and credibility rulings below remain
  binding). The agentic layer is CONSUMPTION, not orchestration
  (autonomous multi-agent systems, swarms, and agent runtimes stay
  explicitly out of scope). As shipped: versioned Expert Package →
  **per-package model evaluation** (the benchmark harness over the
  package channel, OPENAI + ANTHROPIC adapters behind the D19 resolver;
  further providers are adapter additions) → governed model selection
  ("this Expert Package performs best on Model X" — a claim
  one-model-fits-all RAG cannot make) → ExpertAgentBinding. Remaining in
  this direction: more provider adapters (Gemini / open models), the
  consumption operations UI (v1.1.x), and binding lifecycle (D23,
  deferred).
  **Purpose ruling (June 2026): model evaluation is a MEANS, never the end.**
  ExpertMachina is a knowledge-to-agent system, not an LLM evaluation
  platform: the governed knowledge and its expert representation are the
  primary asset, the agent is the delivery mechanism, and model selection is
  the optimization layer that picks the engine. The question is never "which
  LLM won?" but "which model enables THIS Expert Package to deliver the
  highest-quality answers for THIS customer's use case?" The benchmark serves
  deployment; deployment never serves the benchmark.
  **Credibility note — the referee is not one of the players**: unlike
  LLM-as-judge evaluation products, the verdict mechanism here is independent
  of every model under test (local NLI cross-encoder with reproducible weight
  fingerprints, deterministic conflict/coverage checks, governed expectations
  — the D11 rationale). Per-package rankings are therefore reproducible and
  free of judge-family bias. This capability was not designed for
  benchmarking; it is inherited from governance decisions (evidence first,
  provenance first, reproducible verdicts) — which is why it is defensible.
