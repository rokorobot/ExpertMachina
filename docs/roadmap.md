# ExpertMachina Product Roadmap

Having completed MVP 0.2 (Governance & Lifecycle Control), the next milestone centers around transforming ExpertMachina from a knowledge preparation factory into an interactive, trustworthy query console.

---

## MVP 0.3 — Evidence-Backed Ask Expert Console

The primary objective of MVP 0.3 is to allow operators to query their knowledge base using natural language, backed by strict grounding constraints, selected Expert Models, and dual-layer verification.

### Core Architecture

Unlike standard Retrieval-Augmented Generation (RAG) systems that search the entire unstructured corpus, ExpertMachina restricts the context boundary to a selected **Expert Model** containing a curated group of approved assets.

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

---

## 1. Domain Scoping: Expert Model Selection

To support horizontal scaling across thousands of corporate documents, queries must specify an **Expert Model** (e.g. *"Clinical QA Expert"*). 
- Search is scoped only to assets explicitly bundled into that model.
- This prevents noise, crosstalk between domains, and significantly reduces the vector search space (e.g., searching 100 assets in a model instead of 200,000 across the entire corpus).

---

## 2. The Evidence Validation Engine

Before retrieved context is ever exposed to the LLM generation layer, every candidate asset must pass a validation check:
- **Status Verification**: Confirms status is currently `APPROVED`.
- **Integrity Check**: Verifies that a valid `source_hash` and complete `provenance` metadata exist.
- **Archive Filter**: Verifies that the asset has not been archived since compilation.

If any check fails, the asset is discarded from the generation context, and a warning is logged in the audit ledger.

---

## 3. The Answer Verification Layer

After the LLM generates a candidate response, a deterministic post-processing step executes:
1. **Claim Extraction**: The response is parsed into individual factual assertions.
2. **Claim Matching**: Each assertion is mapped back to the validated evidence assets.
3. **Coverage Verification**: Every factual claim must be explicitly supported by at least one approved asset.

### Grounding Rule: "No Evidence = No Answer"
If any factual assertion cannot be mapped to an approved asset, or if retrieval returns insufficient context:
- The candidate answer is blocked.
- The console returns: **`INSUFFICIENT EVIDENCE`**.

---

## 4. Audit Log Expansion

All console queries are logged with high-fidelity telemetry to ensure absolute traceability:

```json
{
  "question": "What is the clinical SLA refund threshold?",
  "expert_model": "Clinical QA Expert",
  "retrieved_assets": [
    "asset_018b321a-4d2c-7431-a8e1-5bc4123490aa"
  ],
  "evidence_hashes": [
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  ],
  "answer_hash": "a4f89d31c4b789a243e8d77f2bc21a4f00d892d131498b2c45eef723d91ca213",
  "operator": "qa_auditor_01",
  "timestamp": "2026-06-10T00:35:00Z"
}
```
This logs the exact state of the assets and evidence hashes at the moment of query evaluation, preserving absolute auditability.
