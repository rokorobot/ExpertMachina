# ExpertMachina

**Governed Enterprise Knowledge for AI Agents**

ExpertMachina transforms unstructured enterprise knowledge into **governed, auditable, evidence-backed** expert systems that can be safely consumed by AI agents.

Unlike traditional knowledge bases, ExpertMachina is designed around governance, provenance, trust, and human oversight. The platform creates a controlled knowledge layer between enterprise information and autonomous AI systems.

```text
Enterprise Documents
    ↓
Document Ingestion
    ↓
Knowledge Extraction
    ↓
Governance Review
    ↓
Approved Knowledge Assets
    ↓
Trust & Provenance Layer
    ↓
Governed Knowledge Base
    ↓
Agent Gateway (MCP)
    ↓
AI Agents
```

**Core rule: AI agents consume governed knowledge, not raw documents.**

---

## Why ExpertMachina Exists

Organizations possess vast amounts of knowledge: policies, procedures, SOPs, manuals, reports, research documents, compliance records, institutional knowledge.

Modern AI systems can *read* these documents but cannot reliably determine:

- which information is approved
- which version is current
- which statements conflict
- who approved a claim
- whether a source can be trusted

Most AI knowledge systems ingest documents directly into vector databases and expose them immediately to retrieval and generation. The result: unverified knowledge in production, outdated information that never expires, sensitive content surfaced unintentionally, no approval workflow, and lost provenance.

ExpertMachina solves this through **governance-first knowledge management**: extracted knowledge passes through semantic verification, conflict analysis, immutable revision governance, and publication gates before any AI system is allowed to consume it. Only `APPROVED` assets cross the governance boundary into Expert Models and Agent Packages. Answers without evidence are refused: **no evidence = no answer**.

---

## Major Capabilities

### Knowledge Governance

Human review before publication. Knowledge assets move through governed states — `CANDIDATE → REVIEWED → APPROVED` (or `ARCHIVED`) — and no AI-extracted knowledge becomes authoritative automatically. Deterministic, versioned **approval policies** may auto-approve declared low-risk asset classes at ingestion, with full audit provenance; revisions of already-approved knowledge always wait for a human.

### Revision Workbench

Knowledge evolves safely. When source documents change, change detection generates candidate revisions, differences are displayed side by side, and human reviewers approve or reject. Approved knowledge is never edited in place and never changes silently — the revision chain is immutable history.

### Provenance System

Every asset carries its chain of custody: source document, page and section, content hashes, approver identity, approval timestamp, and revision lineage. Every fact can be traced to its origin, indefinitely.

### Conflict Detection

Semantic (NLI-based) conflict analysis surfaces contradictory knowledge — *"remote work allowed three days"* vs. *"remote work allowed four days"* — for human review, and unresolved blocking conflicts **close the compile gate**: a conflicted Expert Model cannot be published as an Agent Package.

### Trust Layer

Knowledge quality is measurable. Trust scores aggregate five explainable components (evaluation reliability, evidence coverage, conflict integrity, governance health, revision freshness). Components without data report `NOT_MEASURED` — never fabricated.

### Source Connectors

Enterprise content synchronizes from managed sources through a provider framework (local folders today; the framework — not the provider — decides what is new, duplicate, or changed, by content hash). Recursive discovery, duplicate detection, incremental sync, and per-file ingestion reporting; source changes become governed candidate revisions, never silent updates.

---

## Governance & Identity Platform (v1.0)

ExpertMachina includes a governance-grade identity boundary — significantly beyond traditional authentication. The operating principle:

> **Every human, service, and agent is a governed principal whose permissions are explicitly granted, auditable, and revocable.**

### Identity Registry

All system actors are governed identities, in five kinds:

- **HUMAN** — interactive users (administrators, governance reviewers, knowledge operators)
- **SERVICE** — non-human integrations (connector services, scheduled jobs, pipelines)
- **AGENT** — AI systems operating through the MCP gateway
- **DELEGATED** — governed automation acting on someone's behalf (`policy:X`, `connector:Y`), whose identity chains to the actor who triggered it
- **SYSTEM** — the platform's own engines

### Authentication & Credentials

Password login with forced rotation of one-time credentials, session tokens, API tokens for services and agents, token revocation that takes effect on a live session's next call, account deactivation that fails sessions closed, and admin-driven password resets. Credentials are stored as hashes only, shown in plaintext exactly once at issuance, and **revoked, never deleted** — credential lineage is permanent evidence.

### Role-Based Access Control

A small, code-resident permission matrix (11 permissions × 5 roles: `ADMIN`, `GOVERNANCE_REVIEWER`, `KNOWLEDGE_OPERATOR`, `AGENT_CONSUMER`, `READ_ONLY`) enforced on **every** route. Authenticated identity is powerless until authorized. The backend is authoritative; the user interface only hides what would be refused.

### Identity Facts (immutable evidence)

Every governed action records an **identity fact**: who acted, what role they held *at that moment*, how they authenticated, and which credential. Facts are never updated and never reconstructed from the user table — six months later, the system can prove who an actor *was* when the action occurred, even after renames, role changes, password rotations, or deactivation. Authorization decisions (grants and denials) are themselves audit events carrying these facts.

### Agent Governance

AI agents are first-class identities: they possess unique principals, authenticate with dedicated governed tokens (`EM_AGENT_TOKEN`), receive their clearance from the registry (never from their own configuration), cannot impersonate humans, and cannot use the REST surface at all — agents consume knowledge exclusively through the clearance-checked MCP gateway. Unauthenticated agents are refused, and every refusal is audited.

### Security Model

Least privilege, explicit permissions, human accountability, machine identity governance, complete auditability. No actor receives implicit authority. Recovery is a **documented procedure, never a bypass mechanism**.

---

## Agent Gateway

Governed knowledge is exposed through the MCP gateway: evidence-backed Q&A (`ask_expert`), trust scores, compile-gate status, provenance inspection, conflict review, and revision history — all read-only, all clearance-checked, all audited. Exported `.empkg` Agent Packages provide the portable channel: hash-chained, clearance-filtered, provider-agnostic.

---

## Documentation

| Document | Contents |
| :--- | :--- |
| [Architecture](docs/architecture.md) | The layered pipeline: ingestion, indexing, extraction, governance boundary, query engine, packaging |
| [Identity Boundary v1.0](docs/identity-boundary-v1.md) | The identity/authorization design contract: principals, credentials, identity facts, roles, recovery |
| [User & Identity Administration](docs/user-management.md) | **Admin guide**: creating users, services, and agents; roles, tokens, resets, audit |
| [Governance Contract v1](docs/governance-contract-v1.md) | **Normative spec** of the frozen governance semantics the MCP gateway exposes |
| [Governance](docs/governance.md) | Core governance principles, lifecycle state machines, boundary rules |
| [Provenance](docs/provenance.md) | Knowledge chain of custody, trace metadata, integrity rules, citations |
| [Assurance](docs/assurance.md) | Evidence validation, answer verification, coverage/confidence scoring, benchmarks |
| [Decision Register](docs/DECISIONS.md) | Binding architectural rulings D1–D21 |
| [Roadmap](docs/roadmap.md) | Milestones through v1.0.0 (Governance Core Complete) and the consumption arc ahead |
| [Walkthrough](docs/walkthrough.md) | End-to-end usage scenario from document upload to evidence-backed answers |

---

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite, Pydantic
- **Knowledge Layer**: Docling, LlamaIndex, Qdrant (local), local NLI cross-encoder
- **Frontend**: Next.js, React, Tailwind CSS
- **Agent Channel**: MCP (Model Context Protocol)

Works out of the box with no API keys — a deterministic rule-based fallback handles extraction locally. Set `OPENAI_API_KEY` to enable live LLM extraction.

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

**First run:** the backend prints a one-time `admin` password to its console at startup. Sign in at <http://localhost:3000>, set your own password at the rotation banner, then administer identities via **Settings → Users & Tokens**. Backend health check: <http://localhost:8000/api/health>.

---

## Long-Term Direction

The governance core (v1.0.0) is the foundation for the strategic arc: versioned Expert Packages → per-package model evaluation → best-model selection → deployable Expert Agents — governed organizational memory that AI-driven organizations can actually trust. Model evaluation is a means of selecting the best engine for governed knowledge, never an end in itself.

## Philosophy

Most AI systems focus on making models smarter. ExpertMachina focuses on **making knowledge trustworthy**. The future of enterprise AI depends less on model intelligence and more on governed organizational knowledge — ExpertMachina exists to provide that foundation.

---

## License

See LICENSE file.

Built by ExpertMachina Labs.
