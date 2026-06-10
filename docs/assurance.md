# Knowledge Assurance & Verification Engine

ExpertMachina guarantees response reliability through a dual-stage **Knowledge Assurance Framework**. While standard RAG systems feed unchecked vector results directly to a generative model, ExpertMachina validates input evidence *before* generation and verifies factual claims *after* generation.

---

## 1. Dual-Stage Verification Architecture

```text
Evidence Retrieval
       ↓
[Stage 1: Evidence Validation Engine]  ── (Filters out Stale, Invalid, or Unapproved Assets)
       ↓
Validated Evidence Context
       ↓
Answer Generation (LLM)
       ↓
[Stage 2: Answer Verification Engine]  ── (Extracts claims & matches back to source assets)
       ↓
Factual Coverage & Confidence Scoring
       ↓
Strict Threshold Check  ─── (Fail? ──> "INSUFFICIENT EVIDENCE")
       ↓
[Verified Answer + Citations]
```

---

## 2. Stage 1: Evidence Validation Engine

Before retrieved context is ever visible to the language model, each asset must pass an automated audit check. Any asset that fails a check is immediately discarded:

- **Status Check**: Verifies that the database record is currently set to `APPROVED`.
- **Archive Check**: Verifies that the asset has not been archived since compiling.
- **Integrity Check**: Re-calculates the cryptographic hash of the source chunk text and asserts that it matches the recorded `source_hash`.
- **Provenance Check**: Validates that all metadata parameters (`source_document`, `source_page`, and `source_section`) are populated.

---

## 3. Stage 2: Answer Verification Engine

Once the language model returns a candidate response, the system executes an automated claim-matching validation:

1. **Claim Extraction**: The response is broken down into atomic factual assertions.
2. **Evidence Mapping**: Every atomic claim is cross-referenced against the validated evidence assets.
3. **Coverage Calculation**: The system measures how much of the answer is explicitly backed by the retrieved assets.

### Atomic Claim Decomposition

Before judgment, the answer is decomposed into atomic claims. A compound policy sentence — *"Critical deviations must be logged within 24 hours and reviewed weekly by the quality manager unless escalated"* — yields separately verified claims, with condition clauses preserved on every claim they govern. Decomposition is LLM-assisted when an API key is present (`LLM_ATOMIC`) and falls back to deterministic coordination splitting (`RULE_COORDINATION`); the method used is recorded in every verification report, making claim granularity a reproducible part of each verdict.

### Verifier Hierarchy

Claim-to-evidence judgment runs through a tiered verifier chain — the strongest available method is used, and each verification report records the **verifier identity** (method, model ID, HF snapshot revision, SHA256 weights hash, engine version, thresholds, claim decomposition method) so any historical verdict can be reproduced against the exact model weights that produced it:

| Tier | Method | Semantics |
| :--- | :--- | :--- |
| 1 (primary) | **Local NLI entailment** (multilingual mDeBERTa-v3 XNLI cross-encoder by default, CPU, no API key; English-optimized DeBERTa-v3 MNLI via `EM_NLI_MODEL_ID`) | Three-way verdict per claim/evidence pair: `ENTAILED`, `CONTRADICTED`, `UNSUPPORTED`, each with the model probability as a per-claim confidence score. An embedding pre-filter selects top-k candidate evidence per claim before cross-encoding. Validated on English, Czech, and cross-lingual evidence/claim pairs. |
| 2 (fallback) | LLM judge (`OPENAI_API_KEY` present) | Binary supported/unsupported per claim. |
| 3 (fallback) | Keyword overlap | Lexical match only — blind to negation; retained solely as a zero-dependency fallback. |

### Contradiction Hard-Fail Rule

NLI distinguishes a claim the evidence *doesn't mention* (`UNSUPPORTED`) from a claim the evidence *disproves* (`CONTRADICTED`). A contradicted claim means the answer inverted approved knowledge — or approved assets conflict with each other — and is strictly worse than a coverage gap. **Any contradicted claim forces `INSUFFICIENT_EVIDENCE` and blocks the answer, regardless of coverage score.** Contradicted claims are reported separately from unsupported claims in both the API response and the audit log.

---

## 4. Assurance & Governance Metrics

To quantify knowledge trust, the console calculates and exposes two primary metrics:

### Coverage Score
The ratio of generated factual assertions that are fully backed by approved assets:
$$\text{Coverage Score} = \frac{\text{Number of Verified Claims}}{\text{Total Claims in Answer}}$$
- If a response makes 10 claims and only 8 can be traced back to approved assets, the **Coverage Score** is `0.80`.

### Confidence Score
A calculated metric representing the structural match and vector similarity strength between the original question and the retrieved evidence:
- Synthesizes semantic proximity, source document freshness, and asset verification attributes.

---

## 5. Verification Status & Threshold Rules

ExpertMachina classifies response validity by mapping the **Coverage Score** to defined compliance states:

| Coverage Score Range | Verification Status | Action |
| :--- | :--- | :--- |
| **0.95 – 1.00** | `VERIFIED` | Allow answer; display full verification trace. |
| **0.80 – <0.95** | `PARTIALLY_VERIFIED` | Allow answer; warn operator of partially ungrounded claims. |
| **< 0.80** | `INSUFFICIENT_EVIDENCE` | **Block candidate answer** and return fallback alert string. |

### Insufficient Evidence Action
If the **Coverage Score** drops below `0.80`, the candidate answer is discarded entirely, preventing unverified model assumptions from leaking. The console returns:
- **`INSUFFICIENT EVIDENCE`**

---

## 6. Verifiable Answer Schema

All successful client responses return the complete verification payload containing telemetry scores and status classifications:

```json
{
  "answer": "Deviation reports must be filed within 24 hours.",
  "confidence_score": 0.88,
  "coverage_score": 0.92,
  "verification_status": "PARTIALLY_VERIFIED",
  "citations": [
    {
      "asset_id": "asset_018b321a-4d2c-7431-a8e1-5bc4123490aa",
      "source_document": "SOP-001_Deviation_Management.pdf",
      "source_page": 3,
      "source_section": "4.1 Classification of Deviations",
      "source_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "asset_status": "APPROVED",
      "approved_by": "operator_admin_02",
      "approved_at": "2026-06-10T00:30:00Z"
    }
  ]
}
```
This data structure completes the **Knowledge Chain of Custody**, linking the client's answer back to the exact approval event in the factory database.

---

## 7. Benchmark Evaluation & Trust Scorecards (MVP 0.4)

Beyond per-query verification, ExpertMachina quantifies the trustworthiness of an entire Expert Model through reproducible benchmark evaluation runs.

### Benchmark Datasets

Operators define per-project benchmark questions, each specifying:

- **`question`**: The natural-language query to evaluate.
- **`expected_claims`**: The factual assertions a correct answer must contain.
- **`expected_answer_type`**: `FACTUAL` | `PROCEDURAL` | `POLICY` | `REFUSAL`.
- **`min_required_coverage`**: Minimum coverage score for a pass (default `0.95`).
- **`required_citation_count`**: Minimum number of citations the answer must carry.
- **`severity`**: `LOW` | `MEDIUM` | `HIGH` | `CRITICAL` — the business impact of a failure.

`REFUSAL`-type benchmarks invert the pass condition: they pass **only** when the console correctly returns `INSUFFICIENT EVIDENCE`. This verifies that the grounding rule holds — the model must refuse questions its approved knowledge cannot answer.

### Snapshot-Based Reproducibility

Each evaluation run freezes three snapshots at creation time:

1. The Expert Model's **approved asset IDs**.
2. The **source hashes** of those assets (tamper baseline).
3. The **benchmark question set**.

The batch then executes the full Ask Expert pipeline (retrieval → evidence validation → grounded generation → answer verification) against the snapshot, so results remain reproducible even if governance state changes after the run was created. Runs progress through `PENDING` → `RUNNING` → `COMPLETED` / `FAILED`.

### Scorecard Metrics

Each completed run produces an aggregate scorecard:

- **`pass_rate`**: Fraction of benchmark questions that met their pass conditions.
- **`average_coverage_score`**: Mean claim-coverage across all questions.
- **`average_confidence_score`**: Mean confidence across all questions.
- **Failed question list**: Per-question drill-down with the generated answer, unsupported claims, and citations for every failure.

These scorecards turn "do we trust this Expert Model?" from a subjective judgment into a measurable, auditable, and regression-trackable metric.
