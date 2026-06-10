# ExpertMachina Product Roadmap

## Milestone Status

| Milestone | Theme | Status |
| :--- | :--- | :--- |
| MVP 0.2 | Governance & Lifecycle Control | ✅ Completed |
| MVP 0.3 | Evidence-Backed Ask Expert Console | ✅ Completed |
| MVP 0.4 | Expert Model Evaluation & Trust Scorecards | 🔄 In Progress |

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

## Future Direction (Post 0.4)

- **Agent Consumption API** — a hardened, read-only endpoint surface designed for autonomous agent consumption of compiled packages, with per-agent access controls.
- **Knowledge freshness policies** — expiry and re-review schedules per asset class.
- **Multi-operator roles** — reviewer / approver separation of duties.
