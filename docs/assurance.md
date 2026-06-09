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

## 5. Insufficient Evidence Rules

ExpertMachina eliminates hallucinations by enforcing a hard compliance threshold:

```text
If Coverage Score < Threshold (Default: 1.00)
    ↓
Block Candidate Answer
    ↓
Return: "INSUFFICIENT EVIDENCE"
```

If any single claim cannot be mathematically traced to a validated source document, the entire response is rejected, preventing the leakage of unverified model training assumptions.

---

## 6. Verifiable Answer Schema

All successful client responses return the complete verification payload:

```json
{
  "answer": "Deviation reports must be filed within 24 hours.",
  "confidence_score": 0.92,
  "coverage_score": 1.00,
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
