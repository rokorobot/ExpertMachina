# Provenance Verification & Traceability

In ExpertMachina, **provenance preservation** is built directly into every layer of the system. We guarantee that any piece of knowledge used by a compiled agent can be traced back to its exact document source page, section, and cryptographic block hash.

---

## 1. The Provenance Chain

Every knowledge asset created in ExpertMachina carries a complete citation trace object:

```text
Document (Name, Cryptographic SHA256 Hash)
    ↓
Chunk (Line Reference, Page Range, Section Title)
    ↓
Asset (UUID, Extracted Fact, Quality Score Metrics)
    ↓
Expert Model (Aggregated Approved Assets)
    ↓
Agent Package Manifest (Serialized Metadata & Signatures)
```

---

## 2. Granular Trace Metadata Fields

Each asset object in the database and compiled package contains the following fields:

- **`source_document`**: The filename or database ID of the original source document (e.g. `SOP-001_Deviation_Management.pdf`).
- **`source_page`**: The specific page number or range where the raw text is located.
- **`source_section`**: The closest header or structural section identified during Docling layout parsing (e.g. `Section 4.2: Handling Critical Outages`).
- **`source_hash`**: A SHA256 cryptographic hash generated from the raw chunk text content. This ensures block-level integrity and prevents silent tampering.
- **`extraction_method`**: A categorization marker indicating how the asset was derived:
  - `MOCK_RULE_BASED`
  - `LOCAL_RULE_BASED`
  - `LLM_ASSISTED`
  - `HUMAN_CREATED`

---

## 3. Serialization inside Agent Package Manifests

When an Expert Model is compiled into an **Agent Package**, all approved assets are bundled into a standardized, deterministic JSON manifest file.

### Deterministic & Reproducible Compilations
To verify that identical assets always produce identical expert packages (critical for reproducibility audits), the compilation logic:
1. Filters and extracts only `APPROVED` assets.
2. Sorts the asset records lexicographically by their unique UUID.
3. Serializes the sorted asset array together with their provenance fields into the JSON payload.
4. Generates a deterministic package digest hash.

### Sample Manifest Entry:
```json
{
  "package_id": "pkg_9a3f8c-231b-4cd1",
  "version": "0.1.0",
  "compiled_at": "2026-06-10T00:30:00Z",
  "assets": [
    {
      "asset_id": "asset_018b321a-4d2c-7431-a8e1-5bc4123490aa",
      "name": "Deviation Classification Policy",
      "content": "All critical deviations must be logged in the quality management system within 24 hours.",
      "provenance": {
        "source_document": "SOP-001_Deviation_Management.pdf",
        "source_page": 3,
        "source_section": "4.1 Classification of Deviations",
        "source_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "extraction_method": "LLM_ASSISTED"
      }
    }
  ]
}
```
If any asset content or its source hash changes, the package digest hash changes, immediately alerting audit systems to a change in the knowledge footprint.
