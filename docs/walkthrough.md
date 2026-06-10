# ExpertMachina Walkthrough — Governed Knowledge Transformation Factory

This walkthrough covers the operational platform end-to-end: the governed knowledge factory (MVP 0.2), the evidence-backed Ask Expert console (MVP 0.3), and benchmark evaluation runs (MVP 0.4).

---

## Architectural Breakdown

### 1. Ingestion Infrastructure Layer
- **Docling + LlamaIndex**: Ingests files (PDF, DOCX, TXT), parses structure/metadata, chunks the text, and stores embeddings.
- **Local Qdrant**: Uses a local file-based vector storage (`./backend/qdrant_db`) for vector search/indexing without external service dependencies.
- **Optional Live LLM**: Uses OpenAI API for live LLM ingestion and vector embeddings if `OPENAI_API_KEY` is present. Otherwise, it uses a deterministic mock vector generator and robust native text/PDF extraction so the application works out-of-the-box.

### 2. ExpertMachina Transformation & Governance Layer
- **Workspaces & Projects**: Scopes all document assets, chunk lists, expert models, and agent packages by `project_id` to ensure isolation.
- **Advanced Provenance**: Records where every knowledge asset originated including the `document_id`, `chunk_id`, page number (`source_page`), section header (`source_section`), SHA256 block hash (`source_hash`), and classification marker (`extraction_method`: `MOCK_RULE_BASED`, `LOCAL_RULE_BASED`, `LLM_ASSISTED`, `HUMAN_CREATED`).
- **Quality Score Engine**: Calculates and updates coverage, freshness, verification, and conflict scores (0-100) per asset.
- **Review Queue**: Facilitates manual state changes (`CANDIDATE`, `REVIEWED`, `APPROVED`, `ARCHIVED`) and governance.
- **Expert Builder**: Groups approved assets into target Expert Models.
- **Agent Package Compiler**: Bundles Expert Models into deployable versions with serialized permissions.
- **Immutable Audit Ledger**: Commits an append-only log of all operations to `audit_events`.

---

## Quick Start & Verification

### Running the Services
1. **Backend API**:
   - Directory: `backend/`
   - Start Command: `.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
   - Active URL: [http://localhost:8000/api/health](http://localhost:8000/api/health)

2. **Frontend UI**:
   - Directory: `frontend/`
   - Start Command: `npm run dev`
   - Active URL: [http://localhost:3000](http://localhost:3000)

---

## End-to-End Walkthrough Scenario

1. **Initialize Workspace**: Click **"New"** in the top sidebar to create a project (e.g., *"QA Standard Compliance Project"*).
2. **Ingest Documents**: Go to the **Document Inventory** panel. Click **"Quick-Load 3 Standard SOPs"** to automatically populate and parse:
   - `SOP-001_Deviation_Management.txt`
   - `SOP-002_SLA_Refund_Policy.txt`
   - `SOP-003_Clinical_Monitoring_Plan.txt`
3. **Review Extracted Assets**: Go to **Knowledge Assets**. Inspect the generated policies, procedures, and systems, showing their quality scores and detailed document source hash markers. Click **"Approve Asset"** on the relevant items.
4. **Group into Expert Model**: Go to **Experts & Packages**. Pick the approved assets, name your model (e.g. *"Clinical QA Expert"*), and click **"Build Expert Model"**.
5. **Compile Agent Package**: Choose your model, assign version `0.1.0`, name the package, and click **"Compile Agent Package"** to get a deployable bundle containing governance metadata.
6. **Audit trail**: Switch to the **Audit Ledger** tab to inspect the immutable timeline log of all operations.
7. **Ask the Expert**: Open the **Ask Expert** console, select your Expert Model, and pose a question (e.g. *"Within what timeframe must deviation reports be filed?"*). The engine retrieves only approved assets within the model scope, validates their integrity, generates a grounded answer, verifies every claim against the evidence, and returns the answer with full citations (document, page, section, hash). Questions the approved knowledge cannot support return **`INSUFFICIENT EVIDENCE`** instead of a guess.
8. **Evaluate the Expert Model**: Define benchmark questions for the project (expected claims, answer type, minimum coverage), then start an evaluation run against the Expert Model. The run snapshots the model's approved assets and executes every benchmark through the full query pipeline, producing a scorecard with `pass_rate`, average coverage/confidence scores, and per-question failure drill-downs.

---

## Document-to-Asset Deep Linking (Added in MVP 0.2)

We have implemented dynamic deep-linking from individual ingested documents straight into their extracted knowledge assets.

### How it Works:
1. **Interactive Document Rows**:
   - Every document row on the **Document Inventory** page is now clickable.
   - Hovering over a row shows a cyan border glow indicating interactivity.
2. **Tab Redirection & URL Routing**:
   - Clicking a document row immediately updates the browser URL (e.g. `/knowledge-assets?documentId=1`), navigates to the **Knowledge Assets** review queue tab, and sets the active filter to only show that document.
   - The app also handles filenames directly via the `?document=<filename>` query parameter and maps them to the corresponding ID.
3. **Card Highlights & Smooth Scroll**:
   - When filtered, matching asset cards are rendered with a prominent cyan border glow and shadow.
   - The review queue smoothly scrolls down to position the first matching card centered in the viewport.
4. **Empty State Handlers**:
   - If a document is clicked but does not have any assets extracted from it yet, a dedicated empty state displays: *"No assets extracted from this document yet"* with instructions to run the **Extract Assets** pipeline, and a quick link to clear the filter.
5. **Back Button Support**:
   - Real-time synchronization listens to the HTML5 history `popstate` events, keeping the dashboard's active tab and filter perfectly aligned with browser Back/Forward navigation.

---

## Document Status & Lifecycle Engine (Added in MVP 0.2 Governance Patch)

To transition asset rejection from a visual frontend filter to an enterprise-grade exclusion boundary, we implemented a state-machine-driven **Document Lifecycle Engine**.

### 1. Document States & Transitions
Documents now progress through the following database status states:
- `INGESTED`: Newly uploaded document.
- `PARSED`: Text extracted and stored in chunks/vector collections.
- `ASSETS_EXTRACTED`: Chunks analyzed and candidate assets generated.
- `PARTIALLY_APPROVED`: At least one asset is manual-approved, but others remain candidates.
- `APPROVED`: Every single asset derived from the document has been approved.
- `ALL_ASSETS_REJECTED`: Every single asset derived from the document has been rejected/archived.
- `DELETED`: All assets derived from the document have been hard-deleted from the workspace.

### 2. Governance Exclusion Logic & Filtering
- **Inventory Cleanup**: Documents in `ALL_ASSETS_REJECTED` or `DELETED` state are dynamically hidden from Document Inventory queries on both backend and frontend layers.
- **Bulk Action Performance**: Implemented a `PATCH /api/assets/bulk` endpoint enabling single-request status updates (such as bulk rejections) that performantly recalculate the document lifecycle in a single database commit.
- **Expert Model Guardrails**: Enforced constraints on the backend (`create_expert_model`) ensuring that only `APPROVED` assets can ever be grouped into digital expert models, preventing rejected candidate leakage.

### 3. Document Governance Audit Panel
We added a beautiful **Governance Audit Panel** per document inside the assets review queue.
It displays real-time:
- **Current lifecycle state**: Direct visual indication of the state (e.g. `ASSETS_EXTRACTED`, `PARTIALLY_APPROVED`, `APPROVED`, `ALL_ASSETS_REJECTED`, or `DELETED`).
- **Asset statistics**: Live counts for Approved (`APRV`), Rejected (`REJ`), and Pending (`PEND`) assets.
- **Verification trace**: Last transition timestamp, owner details, and integrity hash check states.

### 4. Usability & Workflow Controls (P1-P5 Refinements)
- **Approve All Candidates (P1 & P3)**: Added a bulk approval button (`Approve All X Assets`) showing the exact candidate count and committing all status updates via a single backend transaction.
- **PARSED → ASSETS_EXTRACTED Fix (P2)**: Patched the extraction pipeline to ensure document lifecycles are correctly calculated even if matching assets already exist.
- **Delete Confirmation Safeguards (P4)**: Integrated browser confirmation prompts to prevent accidental data deletion on bulk asset operations.
- **Keyboard Review Shortcuts (P5)**: Added global keyboard shortcut listeners on the assets page. Pressing `A` automatically approves the first pending candidate asset in the view, while `R` rejects it.

### 5. Governance and Security Audits (MVP 0.2 Review)
We added `backend/test_audit.py` to assert the core governance boundaries of ExpertMachina:
- **Governance Bypass Prevention**: Verified that direct attempts to group unapproved or rejected assets into an Expert Model explicitly fail (throwing a `400 Bad Request` / `ValueError` rather than ignoring silently) and record a `GOVERNANCE_BLOCKED_NON_APPROVED_ASSET` entry in the immutable audit ledger.
- **Provenance Integrity Check**: Verified that the compiled Agent Package manifest includes all granular trace keys: `source_document`, `source_page`, `source_section`, `source_hash`, and `extraction_method`.
- **Package Manifest Reproducibility**: Confirmed that compiling packages sequentially from identical approved assets yields fully deterministic, sorted, and identical package manifests.

All audits run and pass successfully:
```text
=== All MVP 0.2 Governance and Security audits passed successfully! ===
```

### 6. Automated Test Verification
We added `backend/test_lifecycle.py` to assert the correctness of document state-machine transitions and filtering. All tests pass successfully:
```text
Initializing test database for lifecycle checks...
Project created: Lifecycle Test Project
Initial doc status: INGESTED (Expected: INGESTED)
Parsed doc status: PARSED (Expected: PARSED)
Extracted assets doc status: ASSETS_EXTRACTED (Expected: ASSETS_EXTRACTED)
Extracted 2 assets.
One approved asset doc status: PARTIALLY_APPROVED (Expected: PARTIALLY_APPROVED)
All approved assets doc status: APPROVED (Expected: APPROVED)
All rejected assets doc status: ALL_ASSETS_REJECTED (Expected: ALL_ASSETS_REJECTED)
Active documents in project: [] (Expected empty list)
All assets deleted doc status: DELETED (Expected: DELETED)

--- All lifecycle assertions passed successfully! ---
```
