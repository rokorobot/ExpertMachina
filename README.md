# ExpertMachina

**Governed Knowledge Transformation Factory**

ExpertMachina transforms unstructured enterprise knowledge — documents, SOPs, policies, procedures, manuals — into governed, auditable, evidence-backed Expert Models that serve as the authoritative knowledge layer for AI agents.

ExpertMachina is not a chatbot, a document repository, or a traditional RAG system. It is a **Knowledge Governance Platform**: extracted knowledge is reviewed, approved, audited, and packaged before any AI system is allowed to consume it.

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
| [Governance](docs/governance.md) | Document and asset lifecycle state machines, boundary rules, operator workflow controls |
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
