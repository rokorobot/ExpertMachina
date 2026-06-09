# ExpertMachina

**Governed Knowledge Transformation Factory**

ExpertMachina transforms company documents into governed, auditable, AI-ready expert systems.

Instead of allowing AI models to directly consume uncontrolled document collections, ExpertMachina introduces a structured governance layer where extracted knowledge is reviewed, approved, audited, and packaged before it can be used by AI agents.

---

## Problem

Most AI knowledge systems ingest documents directly into vector databases and immediately expose them to retrieval and generation systems.

This creates several risks:

* Unverified knowledge enters production systems.
* Outdated information remains accessible.
* Sensitive content can be surfaced unintentionally.
* There is no approval workflow.
* Provenance and traceability are often lost.

Organizations require governance, accountability, and reproducibility.

---

## Solution

ExpertMachina introduces a governed knowledge lifecycle:

```text
Document
    ↓
Parsing & Indexing
    ↓
Knowledge Asset Extraction
    ↓
Human Governance Review
    ↓
Approved Knowledge Assets
    ↓
Expert Models
    ↓
Agent Packages
```

Only approved knowledge can cross the governance boundary.

---

## Core Principles

### Governance First

Knowledge must be reviewed before it becomes available to expert systems.

### Provenance Preservation

Every knowledge asset retains:

* Source document
* Source page
* Source section
* Source hash
* Extraction method

### Reproducibility

Identical approved assets produce identical expert packages.

### Auditability

All governance actions are recorded in an immutable audit ledger.

---

## MVP 0.2 Features

### Document Ingestion

* PDF
* DOCX
* TXT

### Parsing & Indexing

* Docling
* LlamaIndex
* Local Qdrant

### Knowledge Asset Extraction

* Policy extraction
* Procedure extraction
* System extraction
* Rule-based extraction
* LLM-assisted extraction

### Governance Workflow

Asset states:

* CANDIDATE
* APPROVED
* ARCHIVED

Document lifecycle:

* INGESTED
* PARSED
* ASSETS_EXTRACTED
* PARTIALLY_APPROVED
* APPROVED
* ALL_ASSETS_REJECTED
* DELETED

### Expert Builder

Approved assets can be grouped into Expert Models.

### Agent Package Compiler

Expert Models can be compiled into reproducible Agent Packages.

### Governance Audit Controls

* Provenance verification
* Lifecycle auditing
* Governance bypass protection
* Package reproducibility validation

---

## Governance Boundary

The most important rule in ExpertMachina:

```text
Only APPROVED assets may enter Expert Models and Agent Packages.
```

Attempts to bypass governance controls are blocked and recorded in the audit ledger.

---

## Technology Stack

Backend

* FastAPI
* SQLAlchemy
* SQLite
* Pydantic

Knowledge Layer

* Docling
* LlamaIndex
* Qdrant

Frontend

* Next.js
* React
* Tailwind CSS

---

## Running Locally

Backend

```bash
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Roadmap

### MVP 0.3

Evidence-Backed Ask Expert Console

```text
Question
    ↓
Approved Assets Only
    ↓
Evidence Retrieval
    ↓
Answer + Citations
```

Rule:

```text
No evidence = no answer
```

---

## License

See LICENSE file.

---

Built by ExpertMachina Labs.
