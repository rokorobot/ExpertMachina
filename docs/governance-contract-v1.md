# ExpertMachina Governance Contract v1

**Status: Normative. Frozen as of MVP 0.8.**

This document defines the governance semantics that external consumers — AI agents (via the MCP gateway), auditors, and integrators — may depend on. Everything specified here is implemented, tested, and versioned. Once the MCP gateway ships, this contract is the public API surface.

The key words MUST, MUST NOT, SHALL, and MAY are to be interpreted as in RFC 2119.

---

## 1. Versioning & Stability Policy

- Each scored or gated artifact carries an explicit version tag: `trust-score-v1`, `conflict-score-v1`, `nli-v1`. Responses include the version that produced them.
- **v1 fields SHALL NOT be removed or renamed.** Changes are additive only. Breaking changes require a v2 published alongside v1, never replacing it silently.
- Model-based verdicts MUST be reproducible: the verifier identity records the model ID, HF snapshot revision, SHA256 of the model weight files, engine version, thresholds, and claim-decomposition method that produced each verdict.
- Threshold and weight constants below are the v1 defaults. Deployments MAY tune them via environment variables; every verdict records the values actually used.

## 2. Universal Guarantees

These hold across every interface:

1. **Governance boundary**: only `APPROVED` knowledge is retrievable, citable, compilable, or consumable. Enforced in the backend.
2. **No fabricated data**: missing provenance, unrecorded approvals, and unmeasured score components are reported as `null` / `NOT_MEASURED` with a reason — never backfilled with invented defaults.
3. **Explainability**: every score ships with a human-readable summary and an itemized breakdown. "Why not 100?" is always answerable from the response.
4. **Auditability**: every governance action and verdict emits an event in the append-only audit ledger (event registry in §9).

---

## 3. Access Model v1

Assets carry an `access_level`; callers carry a clearance. Both use a strict total order:

```text
PUBLIC (0) < INTERNAL (1) < RESTRICTED (2) < EXECUTIVE (3)
```

- A caller SHALL only retrieve assets whose level is **≤** the caller's clearance.
- Unknown or missing levels default to `INTERNAL`.
- Assets excluded by clearance are recorded (by ID) in the retrieval audit log — exclusion is observable, not silent.
- Operator-initiated evaluation batches run at `EXECUTIVE` clearance by definition.

## 4. Revision Model v1

**Core rule: approved knowledge is never edited in place.**

- `knowledge_assets` is the **stable logical identity**; `asset_revisions` holds **immutable content records**. The asset row is always a projection of the active approved revision.
- Revision statuses: `CANDIDATE → APPROVED | REJECTED`; an approved revision later replaced becomes `ARCHIVED` with `superseded_by_revision_id` set ("superseded" is the pointer, not a status).
- Any content edit reaching an `APPROVED` asset — through any API path — SHALL be diverted into a new `CANDIDATE` revision. The active revision keeps serving until the candidate passes review.
- **Strictly linear**: at most one pending candidate per asset. No branching in v1.
- **Lazy adoption**: revision 1 is created from the asset's current state on first approval or first edit. Assets predating the revision model are valid until touched.
- Every revision records: `revision_number`, `content`, `content_hash` (SHA256), `source_hash` (chunk provenance at revision time), creator, approver, timestamps, `supersedes`/`superseded_by` links, and a `change_reason`.
- **Integrity invariant**: live asset content MUST match the active revision's `content_hash`. Evidence validation fails the asset (`REVISION_CONTENT_MISMATCH`) on divergence — tampering around the workflow is detectable at query time.
- **Content-bound verdicts** (governance principle): operator conflict verdicts pertain to *Asset A Revision X vs Asset B Revision Y*, not *Asset A forever*. Approving a revision SHALL invalidate conflict verdicts involving the revised asset (they are re-judged); verdicts on unrelated pairs survive.
- Approving a revision SHALL automatically rescan conflicts in every Expert Model containing the asset; conflict scores and compile gates refresh as a consequence (self-healing). Rescan results are recorded in the `ASSET_REVISION_APPROVED` audit event.

## 5. Conflict Model & Conflict Score v1

### Detection

- Pairwise NLI across an Expert Model's approved assets, judged **in both directions** (NLI is asymmetric); the stronger signal wins.
- Stored relationship types: `CONFLICTS_WITH`, `SUPPORTS` (source = the entailing asset). `RELATED` is reserved.
- Scan thresholds default to **0.90** (stricter than answer verification's 0.80: unrelated-pair priors are low; empirically true conflicts score ≥ 0.99 while cross-domain noise sits ≈ 0.82).
- Conflict classification (`RULE_METADATA_V1`, most-specific structural explanation wins):
  - `TEMPORAL_SUPERSESSION` — same policy name and type across different documents
  - `SCOPE_CONFLICT` — source documents from different departments
  - `ACCESS_CONFLICT` — different access tiers
  - `DIRECT_CONTRADICTION` — none of the above
- Review states: `DETECTED → CONFIRMED | DISMISSED`. Review requires an operator identity; the decision reason is recorded in the audit ledger. Reviewed verdicts survive rescans (until invalidated by a content change, per §4).
- Scans above the pair cap apply an embedding pre-filter and MUST report exactly how many pairs were dropped. No silent truncation.

### Score

```text
semantic_conflict_score = max(0, 100 − Σ penalty)
penalty(conflict) = classification_weight × status_multiplier
```

| Classification | Weight | | Status | Multiplier |
| :--- | :--- | :--- | :--- | :--- |
| DIRECT_CONTRADICTION | 10 | | CONFIRMED | 1.2 |
| ACCESS_CONFLICT | 8 | | DETECTED | 1.0 |
| SCOPE_CONFLICT | 5 | | DISMISSED | 0.1 |
| TEMPORAL_SUPERSESSION | 3 | | | |

- Two fields always: `semantic_conflict_score` and `semantic_conflict_summary` (the reason string), plus an itemized breakdown.
- The score is **standalone**: it SHALL NOT be silently averaged into any other metric. The Trust Score (§7) consumes it as an explicit, visible component.

## 6. Compile Gate v1

Package publication is a governance event.

| Condition | Verdict |
| :--- | :--- |
| Unreviewed (`DETECTED`) conflict of a blocking classification (default: `DIRECT_CONTRADICTION`, `ACCESS_CONFLICT`) | **BLOCKED** |
| `DISMISSED` conflict | Allowed — never blocks |
| `CONFIRMED` conflict (any classification) | Configurable; default **BLOCKED** |
| Unreviewed non-blocking classification | Advisory — reported, does not block |
| Model never conflict-scanned | Allowed by default; BLOCKED if `require_scan` is enabled |

- A blocked compile returns HTTP **409** with an operator-actionable reason, persists nothing, and emits `GOVERNANCE_BLOCKED_UNRESOLVED_CONFLICTS` with the blocking list and active policy.
- A successful compile records the **full gate verdict** (policy, scan status, advisory and dismissed counts) inside `AGENT_PACKAGE_CREATED` — every published package permanently carries proof of the gate it passed.
- The verdict is previewable without side effects (`compile-gate` read endpoint).

## 7. Trust Score v1

A hierarchical, first-class object — never a single opaque number.

| Component | Weight | Source |
| :--- | :--- | :--- |
| `evaluation_reliability` | 0.25 | Pass rate of the latest completed benchmark run |
| `evidence_coverage` | 0.20 | Average claim coverage of the latest run |
| `conflict_integrity` | 0.25 | Conflict Score v1 (§5) |
| `governance_health` | 0.20 | 100 − penalties: unreviewed conflicts (−8 each), pending revisions (−5 each), blocked compile gate (−15), missing provenance (−4 each, capped at −20) |
| `revision_freshness` | 0.10 | Days since last governance review: ≤30→100, ≤90→85, ≤180→70, ≤365→50, else 25 |

- Every component carries `score`, `weight`, `measured`, a human-readable `reason`, and machine-readable `details`.
- Components without underlying data report **`NOT_MEASURED`** with an actionable reason and are excluded from the aggregate; remaining weights are renormalized. A trust score is never fabricated from absent data.
- Governance Health aggregates *governance signals*, deliberately distinct from knowledge signals.
- The heuristic `quality_score` (pre-v1) remains a separate field; the two SHALL NOT be merged.

## 8. Verified Answer v1

The `ask_expert` response semantics (consumed by Tier 1 agents):

- Retrieval is scoped to one Expert Model, `APPROVED` assets only, filtered by caller clearance (§3), with per-asset evidence validation: status, expert-model membership, chunk existence, source-hash integrity, document presence, page/section presence, archival, and revision integrity (§4). Failing assets are discarded and the discard is logged.
- The answer is decomposed into **atomic claims** (condition clauses preserved on every claim they govern; the compiler extracts and verifies — it never synthesizes new policy statements). Each claim receives a three-way NLI verdict: `ENTAILED` / `UNSUPPORTED` / `CONTRADICTED`, with per-claim confidence.
- `coverage_score` = supported claims / total claims. Status mapping: ≥0.95 `VERIFIED`, ≥0.80 `PARTIALLY_VERIFIED`, else `INSUFFICIENT_EVIDENCE`.
- **Contradiction hard-fail**: any `CONTRADICTED` claim forces `INSUFFICIENT_EVIDENCE` and blocks the answer regardless of coverage. No evidence = no answer.
- Citations carry: `asset_id`, **`revision`** (active revision number), source document / page / section / hash, asset status, and the recorded approver identity and timestamp — `null` where unrecorded, never fabricated.
- Every response includes the **verifier identity** (§1) and the claim-decomposition method.
- Cross-lingual verification is in scope: claims and evidence MAY be in different languages (validated: EN, CS, DE, FR).

## 9. Audit Event Registry (v1)

External consumers MAY rely on these event types existing with these meanings:

| Event | Emitted when |
| :--- | :--- |
| `DOCUMENT_UPLOADED` / `DOCUMENT_PARSED` / `DOCUMENT_STATUS_UPDATED` | Document lifecycle transitions |
| `ASSET_GENERATED` / `ASSET_REVIEWED` / `ASSET_APPROVED` / `ASSET_UPDATED` | Asset lifecycle; approval writes a review row with the real approver |
| `ASSET_REVISION_CREATED` / `ASSET_REVISION_APPROVED` / `ASSET_REVISION_REJECTED` | Revision workflow; approval details include post-approval rescan results and invalidated-verdict counts |
| `KNOWLEDGE_CONFLICT_DETECTED` / `KNOWLEDGE_CONFLICT_CONFIRMED` / `KNOWLEDGE_CONFLICT_DISMISSED` | Conflict engine and operator review (with reasons) |
| `CONFLICT_SCAN_COMPLETED` | Per scan, with counts and the refreshed conflict score |
| `GOVERNANCE_BLOCKED_NON_APPROVED_ASSET` | Attempt to put non-approved assets into an Expert Model |
| `GOVERNANCE_BLOCKED_UNRESOLVED_CONFLICTS` | Compile gate block, with blocking list and policy |
| `AGENT_PACKAGE_CREATED` | Successful compile, with the full gate verdict |
| `ASK_EXPERT_QUERY` / `ASK_EXPERT_BLOCKED_*` | Query telemetry: retrieved/validated assets, hashes, verdicts, verifier identity, caller access level, blocked-asset IDs |

## 10. MCP Gateway Mapping (MVP 0.9 — read-only)

The gateway exposes this contract; it adds no semantics of its own.

**Tier 1 — Core Agent Surface** (read-only):

| Tool | Returns |
| :--- | :--- |
| `ask_expert(expert_model_id, question)` | Verified Answer v1 (§8) |
| `get_trust_score(expert_model_id)` | Trust Score v1 (§7) |
| `check_gate_status(expert_model_id)` | Compile Gate v1 verdict (§6) |

**Tier 2 — Governance Surface** (read-only):

| Tool | Returns |
| :--- | :--- |
| `get_provenance(asset_id)` | Chain of custody: document, page, section, hashes, approver, revision |
| `get_conflicts(expert_model_id)` | Conflict relationships with classification, confidence, review state (§5) |
| `get_revision_history(asset_id)` | Immutable revision chain (§4) |

**Explicitly NOT exposed in v0.9**: `approve_revision`, `dismiss_conflict`, `publish_package`, or any other write action. The governance core MUST be observable before it becomes agent-writable. Progression: read-only (0.9) → human-supervised writes (1.1) → autonomous governance workflows (1.2+), each gated on operational experience with the previous stage.

All gateway calls are subject to the Access Model (§3) under a per-agent clearance, and every call is audit-logged.

---

*Implementation traceability: §3–§4 `backend/app/query_engine.py`, `backend/app/revisions.py`; §5–§6 `backend/app/conflict_engine.py`; §7 `backend/app/trust.py`; §8 `backend/app/query_engine.py`, `backend/app/verification_engine.py`, `backend/app/claims.py`. Behavioral guarantees are pinned by the backend test suite (17 test files).*
