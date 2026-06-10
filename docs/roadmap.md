# ExpertMachina Product Roadmap

## Milestone Status

| Milestone | Theme | Status |
| :--- | :--- | :--- |
| MVP 0.2 | Governance & Lifecycle Control | ✅ Completed |
| MVP 0.3 | Evidence-Backed Ask Expert Console | ✅ Completed |
| MVP 0.4 | Expert Model Evaluation & Trust Scorecards | 🔄 In Progress |
| MVP 0.5 | Integrity Fixes | ✅ Completed |
| MVP 0.6 | Semantic Verification (Knowledge Integrity Engine) | ✅ Completed |
| MVP 0.7 | Knowledge QA | 🔄 In Progress (Sprint 1 done) |

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

## MVP 0.7 — Knowledge QA (In Progress)

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

### Sprint 4 — Asset Revision Workflow

Model `Asset → Revision` with `supersedes` / `superseded_by` relationships: editing an approved asset creates a new `CANDIDATE` revision that replaces the original through re-review, preserving immutable history.

---

## Future Direction (Post 0.7 / Phase 2)

- **Agent Consumption API** — a hardened, read-only endpoint surface (MCP) for autonomous agent consumption of compiled packages, with per-agent access controls. Deliberately deferred until the knowledge compilation pipeline is trustworthy.
- **Consensus verification** — NLI + LLM evidence judge + provenance + thresholds combined for difficult cases.
- **Knowledge freshness policies** — expiry and re-review schedules per asset class.
- **Multi-operator roles** — reviewer / approver separation of duties.
