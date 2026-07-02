# ExpertMachina

**Governed Enterprise Knowledge for AI Agents**

ExpertMachina is a governed enterprise knowledge transformation platform. It takes the knowledge a company already has — policies, procedures, manuals, reports, operational documents, expert notes — and compiles it into a **governed, auditable, evidence-backed** knowledge layer that humans, applications, and AI agents can safely consume.

The goal is not to store documents. The goal is to turn existing organizational knowledge into a **trusted, permission-aware, revision-controlled, semantically verified** knowledge system — the substrate for intelligent workbenches and agents that diagnose, answer, compare, and improve the company.

**Core rule: no evidence = no answer.** AI agents consume governed knowledge, not raw documents.

```text
Company documents / knowledge sources
        ↓
Document ingestion (uploads · connectors · cloud sources)
        ↓
Asset extraction & domain classification
        ↓
Governance review (human, or audited policy automation)
        ↓
Semantic verification & conflict detection
        ↓
APPROVED knowledge assets (revision-controlled)
        ↓
Compile gate → Expert Packages (.empkg)
        ↓
Evaluation → model selection → agent binding
        ↓
Governed consumption: MCP gateway · portable packages · workbenches
        ↓
Projection engine → graph lens (rendered views: disposable,
tamper-evident, agent-queryable — never a second source of truth)
        ↓
Diagnostic workbenches (agents over packages + graph queries)
        ↓
The proposal lane: agent findings → /08_proposals → held CANDIDATE
→ human gate → DERIVED facts (verified synthesis provenance;
never auto-approved — the one-way valve closes the loop)
```

---

## Why ExpertMachina Exists

Most enterprise AI systems fail at the same point: **they answer before the organization has defined what is approved, current, contradictory, outdated, permissioned, or trustworthy.**

Modern AI can *read* company documents but cannot reliably determine:

- which information is approved,
- which version is current,
- which statements conflict,
- who approved a claim,
- whether a source can be trusted,
- which agent is allowed to see it.

Typical systems ingest documents straight into a vector database and expose them to retrieval and generation. The result: unverified knowledge in production, outdated information that never expires, sensitive content surfaced unintentionally, no approval workflow, and lost provenance.

ExpertMachina inserts a **controlled knowledge layer** between raw company information and AI consumption. Extracted knowledge passes through semantic verification, conflict analysis, immutable revision governance, and publication gates before any AI system is allowed to consume it. Only `APPROVED` assets cross the governance boundary. Answers without approved evidence are refused — the system prefers *"I do not have approved evidence"* over a confident hallucination.

---

## Strategic Mission: Two Realms

ExpertMachina is a **two-realm system**:

- **Knowledge Realm** (built): preserves company knowledge as immutable evidence, extracts and governs meaning, resolves trust/conflict/approval, and compiles portable expert packages. The hard rule here: **extract and verify, never synthesize** — the platform never invents policy statements.
- **Operations Realm** (open as of v1.4): diagnostic and improvement workbenches — bound agents over expert packages — where synthesis *is* the product, but authority is not.

The border between the realms is governed consumption, and the authorship rule that keeps it honest is now law (D29/D30):

> **Humans author facts; agents propose them.**

Human decisions enter as ordinary documents and become **PRIMARY** facts. Agent-synthesized findings re-enter only through the proposal lane and a human gate, becoming **DERIVED** facts with verified synthesis provenance — which agent, under which binding, from which package, citing which governed evidence, accepted by which human. Proposal-lane candidates are never auto-approved; the class is decided by the channel, never claimed by content; and primary prevails over derived in every conflict surface. The one-way valve constrains agents, not people.

---

## Key Capabilities

### Governed Knowledge Assets

Documents are transformed into structured knowledge assets, each carrying lifecycle status (`CANDIDATE → REVIEWED → APPROVED / ARCHIVED`), provenance (source document, page, section, content hashes), approval history, an immutable revision chain, a governed domain classification, permission-aware visibility, and a full audit trail. No AI-extracted knowledge becomes authoritative automatically.

### Human-in-the-Loop Governance, Automated by Exception

Humans review knowledge assets, revisions, conflicts, and compiled packages. Deterministic, **versioned approval policies** may auto-approve declared low-risk asset classes at ingestion — every automatic approval carries machine-verifiable policy provenance, flows through the same transition path a human approval uses, and is structurally prevented (by a permanent CI guard) from ever touching a revision of already-trusted content. Exceptions are declared and ranked, never silent.

### Provenance and Auditability

Every important action lands in the audit ledger: who acted, what changed, when, why, which source or policy justified it, and which model or agent consumed the result. Every governed action records an **identity fact** — who the actor *was at that moment* (role, authentication method, credential fingerprint) — immutable evidence that survives renames, role changes, and deactivations.

### Semantic Verification & Conflict Detection

A local NLI cross-encoder verifies claims against approved evidence with three-way verdicts (`ENTAILED / UNSUPPORTED / CONTRADICTED`) — contradiction is a hard fail. The same engine scans the knowledge base itself for contradictions (direct, temporal, scope, access), classifies them, and exposes them for governed resolution. Unresolved blocking conflicts **close the compile gate**: a conflicted Expert Model cannot be published.

**Cross-lingual semantic verification is a first-class capability**: a Czech policy contradicting an English retention policy is detected; an English SOP answers a Czech operator's question with verified evidence.

### Domain Classification & Taxonomy Governance

Assets carry a governed hierarchical domain path (`finances/accounting`, `hr/remote-work`), assigned deterministically at ingestion by versioned classification policies and correctable by humans as an explicit governed act. Taxonomy reorganization is an audited operation that records the old→new mapping and changes classification paths **without mutating asset content, provenance, status, or revision history**. Folders and graphs only ever *render* the taxonomy — moving a rendered file never reclassifies anything.

### Trust Layer

Knowledge quality is measurable. Trust scores aggregate five explainable components (evaluation reliability, evidence coverage, conflict integrity, governance health, revision freshness); every component carries a human-readable reason, and components without data report `NOT_MEASURED` — never fabricated.

### Enterprise Source Connectors & Credential Custody

Enterprise content synchronizes through a provider framework — local folders and **SharePoint (Microsoft Graph)** today — where *providers describe and the framework decides*: identity is the source URI, the content hash is the only change verdict, and source changes become governed candidate revisions, never silent updates.

Outbound credentials (a SharePoint client secret, a provider key) live in a **governed credential store**: encrypted at rest, never returned by any API or surface, revoked-never-deleted lineage, and every use recorded as custody evidence. *The secret's plaintext is not a governed fact; its custody events are.*

### Two Consumption Channels, Stated Honestly

- **MCP gateway — the GOVERNED channel**: read-only, clearance-checked, per-question verified, live revocation, every call audited.
- **`.empkg` Expert Packages — the PORTABLE channel**: hash-chained, tamper-evident, clearance-filtered, provider-agnostic snapshots with a portable answering contract. Verifiable provenance without live enforcement.

The two are never conflated.

### Evaluation, Model Selection & Agent Binding

Expert Packages are evaluated per model over the portable channel — *"this package version performs best on this model"* is a reproducible, evidence-backed claim. **The referee is never one of the players**: verdicts come from the local NLI engine and deterministic checks, independent of every model under test, so rankings are free of judge-family bias. A governed model selection (with supporting runs and rationale) can then be bound to an AGENT principal as an **Expert Agent Binding** — an append-only snapshot of package version, selected model, clearance, and issuing evidence.

A binding is **not** a runtime: ExpertMachina hands you a governed, evaluated, revocable binding; you bring your own execution.

### Diagnostic Workbenches & the One-Way Valve

A workbench is a **reference consumer, never a privileged subsystem**: it lives outside the governed backend and reaches ExpertMachina only through the existing doors — the verified `.empkg`, the MCP gateway at a real agent token's clearance, and file writes into the vault's proposal folder. The first workbench (onboarding diagnostic) produces a deterministic, evidence-backed diagnosis in which every finding cites the governed assets it drew from — and what the agent *couldn't* see is declared, not hidden.

Its findings re-enter through the **proposal lane**: a `PROPOSAL`-lane connector ingests the proposal as held candidates that **no policy tier can auto-approve** — the human gate on agent-proposed knowledge is constitutional, not configurable. On acceptance, the finding becomes a **DERIVED** fact whose synthesis provenance is verified against governed binding records and quoted verbatim in the approval event. The class travels everywhere — packages, graphs, citations, MCP responses — so derivation is visible to every consumer, forever: the structural answer to knowledge inbreeding.

### Identity and Permissions

Every actor is a governed principal — **HUMAN, SERVICE, AGENT, DELEGATED** (automation acting on someone's behalf, e.g. `policy:X`, `connector:Y`), and **SYSTEM** (the platform's own engines). A small, code-resident permission matrix (12 permissions × 5 roles) is enforced on every route; authenticated identity is powerless until authorized; all denials are audited. Agents cannot impersonate humans, cannot use the REST surface at all, and receive clearance from the registry — never from their own configuration. Recovery is a documented procedure, never a bypass mechanism.

---

## Architectural Principles

1. **Approved knowledge only.** Agents consume governed knowledge, never raw unreviewed documents.
2. **Evidence before answer.** No approved evidence, no answer.
3. **Canonical records are never silently rewritten.** Approved content changes only through governed revisions; measurements are immutable; history is never edited.
4. **Proposal and decision are separated.** Policies propose approvals, providers propose source state, configuration proposes models, callers propose identity, scans propose credential use — a governance layer decides, every time.
5. **Governance before automation.** Automation gets power only after structural guardrails exist — and the guardrails are permanent CI tests, not conventions.
6. **Persist facts, compute views.** Inboxes, rankings, dashboards, and drift are computed from governed facts at read time — never stored, so they can never drift from the truth.
7. **Honest measurement.** `NOT_MEASURED` is never fabricated; caps, exclusions, and skipped work are always declared.
8. **Agents are governed consumers, not magical users.** Identities, permissions, lineage, audit — the architecture rejects "AI can access everything because it is trusted."
9. **Model-agnostic by design.** The governance spine (NLI verdicts, deterministic gates, hashes) is LLM-independent; providers sit behind an adapter seam and the platform survives the loss or replacement of any single model.

These principles are not aspirations — they are **binding architectural decisions** (D1–D30) recorded in the [decision register](docs/DECISIONS.md), enforced by **five permanent guard families in CI**: a frozen schema snapshot guard, a credential custody sweep, a single-approval-path guard, a projection guard proving rendered views can never write governed state, and an agent-authorship guard proving no agent principal, workbench result, or MCP return can write canonical facts except through the proposal lane and human gate.

---

## Conceptual Architecture

```text
┌─────────────────────────────────────────────┐
│              Enterprise Sources             │
│  Documents · Policies · SharePoint · Shares │
└──────────────────────┬──────────────────────┘
                       ▼
┌─────────────────────────────────────────────┐
│              Ingestion Layer                │
│  Uploads · Connector Framework · Custody    │
└──────────────────────┬──────────────────────┘
                       ▼
┌─────────────────────────────────────────────┐
│          Knowledge Transformation           │
│  Extraction · Classification · Revisions    │
└──────────────────────┬──────────────────────┘
                       ▼
┌─────────────────────────────────────────────┐
│              Governance Core                │
│  Approval · Verification · Conflicts ·      │
│  Identity · Permissions · Audit Ledger      │
└──────────────────────┬──────────────────────┘
                       ▼
┌─────────────────────────────────────────────┐
│               Compile Layer                 │
│  Compile Gate · Expert Packages · Trust     │
└──────────────────────┬──────────────────────┘
                       ▼
┌─────────────────────────────────────────────┐
│             Consumption Layer               │
│  MCP Gateway · Package Evaluation · Model   │
│  Selection · Agent Bindings · Workbenches   │
└──────────────────────┬──────────────────────┘
                       ▼
┌─────────────────────────────────────────────┐
│             Projection Layer                │
│  Graph Lens · Rendered Views · MCP Graph    │
│  Queries — governed lenses, never a source  │
└──────────────────────┬──────────────────────┘
                       ▼
┌─────────────────────────────────────────────┐
│      Operations Realm (the return loop)     │
│  Diagnostic Workbenches · The Vault ·       │
│  Proposal Lane → Human Gate → DERIVED facts │
│  — agents propose; humans decide            │
└─────────────────────────────────────────────┘
```

## Operator Console

A role-aware single-page console (the interface hides what the backend would refuse; the backend remains authoritative):

- **Dashboard** (with the Projections panel: render controls, ledger-projected history, computed staleness badges) and **Governance Inbox** (prioritized, computed work view)
- **Document Inventory** and **Sources & Connectors** (connector administration, credential custody, scan history)
- **Knowledge Assets** (with DERIVED chips: agent-synthesized knowledge is never mistakable for human-authored), **Experts & Packages**, **Knowledge Conflicts** (PRIMARY×DERIVED conflicts declare "Primary prevails" with the presumptive review target), **Revision Reviews**
- **Ask Expert Console** (evidence-backed Q&A with citations)
- **Evaluations** (benchmarks, scorecards, refusal tests as first-class results)
- **Consumption** (Selection Workbench, Consumption Inbox, Binding Explorer with full lineage)
- **Operations** (the Operations Realm surface: Workbenches — bound agents and their governed record; Proposal Pipeline — held proposals with recomputed provenance verdicts and the Accept-as-DERIVED human gate; Lanes & Vault — the proposal-lane connectors and the `08_proposals` return path. ExpertMachina never launches agents; execution stays outside the boundary)
- **Agent Center** (MCP activity, clearances, denials) and **Audit Ledger Explorer** (including the structured synthesis-provenance trace for DERIVED acceptances)
- **Settings** (LLM model-per-function selection, Users & Tokens)

---

## Example Use Cases

- Convert internal policy libraries into governed, AI-ready knowledge.
- Build evidence-backed internal expert agents that cite their sources.
- Detect contradictions across departments, languages, and document versions.
- Compile approved knowledge packages scoped to a clearance level.
- Prove which AI model consumes which approved knowledge snapshot — and why it was selected.
- Track drift: a newer package exists, a binding points at an older artifact, a selection needs review.
- Run a diagnostic workbench over governed knowledge and accept its findings as visibly DERIVED facts — the full agent-proposes-human-decides loop.
- Prepare a company's existing knowledge base for safe agentic automation.

## What ExpertMachina Is Not

- Not a chatbot, and not a generic vector-search wrapper.
- Not a document dump or a model playground.
- Not an autonomous agent runtime — no planners, no orchestration, no background workers acting on your systems. Consumption is governed; execution is yours.
- Not a replacement for human governance — it is the machinery that makes human governance scale.

---

## Repository Structure

```text
backend/
  app/
    main.py                  # FastAPI routes + authorization guards
    identity.py              # the identity boundary: principals, credentials, identity facts
    database.py              # SQLAlchemy models + additive migrations
    ingestion.py             # parsing, chunking, indexing
    extraction.py            # knowledge asset extraction (LLM or rule-based)
    classification.py        # governed domain classification & taxonomy operations
    policy.py                # policy-based auto-approval
    revisions.py             # immutable revision workflow
    verification_engine.py   # NLI semantic verification
    conflict_engine.py       # conflict scan, classification, compile gate
    trust.py                 # explainable trust scores
    custody.py               # outbound credential custody (encrypted, never revealed)
    connectors/              # provider framework + LocalFolder / SharePoint providers
    package_builder.py       # .empkg compiler (hash chain, clearance filtering)
    package_consumer.py      # portable-channel consumer
    evaluation.py            # benchmark runs over both channels
    governance_inbox.py      # computed operational views (never persisted)
    consumption_inbox.py     # computed consumption drift view
    binding_lineage.py       # server-composed binding lineage
    mcp_gateway.py           # governed MCP tool surface (incl. graph queries)
    proposals.py             # the proposal lane (D29/D30): channel-decided class, verified provenance
    projections/             # projection engine + graph renderer (D28: lenses, never sources)
  mcp_server.py              # stdio MCP server
  test_*.py                  # product, architectural, transport, identity + 5 guard suites (CI)
frontend/                    # Next.js + Zustand operator console
workbench/                   # reference diagnostic workbench — a consumer, outside the backend (D29/D22)
vault/                       # vault skeleton: agent contract, scratch, /08_proposals return path
docs/                        # decision register, build contracts, admin & governance guides
```

## Documentation

| Document | Contents |
| :--- | :--- |
| [Decision Register](docs/DECISIONS.md) | Binding architectural rulings D1–D30 |
| [Roadmap](docs/roadmap.md) | Every milestone, v0.2 → v1.4.0, and the road to the EM Vault |
| [Architecture](docs/architecture.md) | The layered pipeline |
| [Governance Contract v1](docs/governance-contract-v1.md) | Normative spec of the frozen governance semantics |
| [Identity Boundary v1.0](docs/identity-boundary-v1.md) | Principals, credentials, identity facts, roles, recovery |
| [User & Identity Administration](docs/user-management.md) | Admin guide: users, services, agents, tokens |
| [Governance](docs/governance.md) · [Provenance](docs/provenance.md) · [Assurance](docs/assurance.md) | Core principles, chain of custody, verification scoring |
| Build contracts | [Consumption Arc](docs/consumption-arc-v1.md) · [Workbench](docs/workbench-v1.1x.md) · [Credentials & Cloud Connector](docs/credentials-cloud-connector-v1.2.md) · [Ingestion Automation](docs/ingestion-automation-v1.2.1.md) · [Projection Engine](docs/projection-engine-v1.3.md) · [Diagnostic Workbench](docs/diagnostic-workbench-v1.4.md) |
| [Walkthrough](docs/walkthrough.md) | End-to-end scenario: upload → evidence-backed answers |

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite, Pydantic
- **Knowledge layer**: Docling, LlamaIndex, Qdrant (local), local multilingual NLI cross-encoder (mDeBERTa-v3)
- **Frontend**: Next.js, React, Tailwind CSS
- **Agent channel**: MCP (Model Context Protocol)
- **LLM providers**: OpenAI and Anthropic behind a governed adapter seam; the governance spine works with no API key at all (deterministic rule-based fallback)

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

## Development Status

ExpertMachina is under active development. Shipped and stable:

- the full governance foundation (ingestion, asset lifecycle, approvals, revisions, audit ledger, semantic verification, conflict detection, compile gate, trust scores) — **v0.x, frozen contract**;
- the identity boundary (principals, credentials, identity facts, 12×5 authorization, governed agent tokens) — **v1.0**;
- the consumption arc (package consumer, per-package model evaluation, governed model selection, agent bindings) and its operations workbench — **v1.1.x**;
- the governed credential store and the first credentialed cloud connector (SharePoint) — **v1.2.0**;
- ingestion automation and domain classification (review by exception: source-authority and engine-verified approval tiers, governed taxonomy, the ranked exception inbox) — **v1.2.1**;
- the projection engine and graph lens (clearance-filtered, cursor-stamped, deterministic rendered views; a self-contained air-gapped interactive graph; agent graph queries with lineage as a path query — delivered with **zero schema change**: a projection is a governed lens over the knowledge system, never another knowledge system) — **v1.3.0**;
- the first diagnostic workbench pilot — **the Operations Realm opens** with the one-way valve and derived source class (D29/D30): a reference workbench outside the backend diagnoses through the existing doors, its findings re-enter only through the proposal lane and human gate as DERIVED facts with verified synthesis provenance, primary prevails over derived in every conflict surface, and the fifth permanent CI guard proves from the ledger alone that no agent can write canonical facts directly — **v1.4.0**; plus the **Operations area** (Workbenches, Proposal Pipeline, Lanes & Vault — a pure computed operator surface where humans work the gate; ExpertMachina never launches agents) — **v1.4.1**.

**The road ahead** (directional): the EM Vault — a full human-readable, Obsidian-compatible rendered workspace as the projection engine's second renderer, filling the vault folders v1.4 reserved (v1.5).

## Guiding Rule

ExpertMachina exists to answer one question, indefinitely and with evidence:

> **What does the company officially know, what evidence supports it, who approved it, who can use it, and which agents are acting on it?**

Most AI systems focus on making models smarter. ExpertMachina focuses on **making knowledge trustworthy** — the future of enterprise AI depends less on model intelligence and more on governed organizational knowledge.

## License

License information will be added before public release.

## Maintainer

ExpertMachina is developed by **Robert Konecny** as part of a broader effort to build governed AI systems for enterprise knowledge, agentic workbenches, and controlled automation.
