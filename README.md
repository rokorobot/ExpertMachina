# ExpertMachina

**Knowledge Compiler & Integrity Platform**

ExpertMachina compiles enterprise knowledge — documents, SOPs, policies, procedures, manuals — into **semantically verified, conflict-checked, revision-controlled** Expert Models that can be consumed safely by AI agents.

ExpertMachina is not a chatbot, a document repository, or a traditional RAG system. Most knowledge systems help agents *find* information; ExpertMachina answers a harder question: **how do we know the knowledge itself is trustworthy before any agent uses it?** Extracted knowledge passes through semantic verification, conflict analysis, immutable revision governance, and publication gates before any AI system is allowed to consume it — and the governance semantics agents depend on (revision, conflict, provenance, trust, gate status, access level) are frozen, versioned contracts.

```text
Company Knowledge
    ↓
Governance
    ↓
Expert Models
    ↓
Agent Consumption
```

**Core Rule: AI agents consume governed knowledge, not raw documents.**

---

## Why

Most AI knowledge systems ingest documents directly into vector databases and expose them immediately to retrieval and generation. The result: unverified knowledge in production, outdated information that never expires, sensitive content surfaced unintentionally, no approval workflow, and lost provenance.

ExpertMachina introduces a governed knowledge lifecycle instead:

```text
Document → Parsing & Indexing → Knowledge Asset Extraction
    → Human Governance Review → Approved Knowledge Assets
    → Expert Models → Agent Packages → Evidence-Backed Answers
```

Only `APPROVED` assets may cross the governance boundary into Expert Models and Agent Packages. Bypass attempts are blocked and recorded in an immutable audit ledger. Answers without evidence are refused: **no evidence = no answer**.

---

## Documentation

| Document | Contents |
| :--- | :--- |
| [Architecture](docs/architecture.md) | The layered pipeline: ingestion, indexing, extraction, governance boundary, query engine, packaging |
| [Governance Contract v1](docs/governance-contract-v1.md) | **Normative spec** of the frozen governance semantics: Access, Revision, Conflict Score, Compile Gate, Trust Score, Verified Answer — the contract the MCP gateway exposes |
| [Governance](docs/governance.md) | Core governance principles, document and asset lifecycle state machines, boundary rules, operator workflow controls |
| [Provenance](docs/provenance.md) | Knowledge chain of custody, trace metadata, formal integrity rules, answer citations |
| [Assurance](docs/assurance.md) | Evidence validation, answer verification, coverage/confidence scoring, benchmark evaluation |
| [Roadmap](docs/roadmap.md) | Completed milestones (MVP 0.2, 0.3) and current work (MVP 0.4 evaluation framework) |
| [Walkthrough](docs/walkthrough.md) | End-to-end usage scenario from document upload to evidence-backed answers |

---

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite, Pydantic
- **Knowledge Layer**: Docling, LlamaIndex, Qdrant (local)
- **Frontend**: Next.js, React, Tailwind CSS

Works out of the box with no API keys — a deterministic mock LLM/embedding fallback handles parsing and extraction locally. Set `OPENAI_API_KEY` to enable live LLM extraction and embeddings.

---

## Running Locally

Backend:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Backend health check: <http://localhost:8000/api/health> — Frontend: <http://localhost:3000>

---

## License

See LICENSE file.

Built by ExpertMachina Labs.
