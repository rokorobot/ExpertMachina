# Consumption Operations Workbench — v1.1.x Design

> Ratified scope from the v1.1.x scoping session (June 2026, post-v1.1.0).
> This is the build contract for the workbench milestone. Its input was the
> pre-scoping brief (docs/scoping-1.1x-consumption-workbench.md); the brief's
> candidate rulings were confirmed or refined here. **D24** is recorded in
> docs/DECISIONS.md and enforced structurally (WS0).

## The milestone's nature

v1.0 and v1.1 were architecture milestones; the workbench is a **product
design** milestone. The backend capability IS the v1.1.0 product — the
workbench converts that capability into operational usability **without
changing the architecture**. It is a projection layer, almost entirely:
everything it shows already exists as governed facts
(EvaluationRun, PackageModelSelection, ExpertAgentBinding, AuditEvent,
IdentityFact).

**The design test (applies to every screen):**

> If a workbench screen disappears entirely, no governed fact may be lost.

## The three operator decisions (confirmed at scoping)

The pre-scoping candidates were confirmed unchanged. Each maps to one
screen, and each is completable using only projections of existing
governed facts:

1. **"Which model should serve this package?"** — the selection decision
   → **Selection Workbench** (WS1).
2. **"Something changed — does my selection still stand?"** — the
   re-evaluation decision → **Consumption Inbox** (WS2).
3. **"What is this agent actually serving, and can I prove it?"** — the
   lineage decision; the flagship → **Binding Explorer** (WS3).

## Ratified rulings (scoping session)

### 1. Navigation: a top-level Consumption area

A new top-level **Consumption** area containing Selection Workbench,
Consumption Inbox, and Binding Explorer. NOT hidden under Agent Center:
v1.1 made consumption a first-class lifecycle, not an agent settings
subpage. The dividing line:

- **Agent Center** remains identity/MCP/tool-facing.
- **Consumption** is package/model/binding-facing.

D8 is satisfied, not bent — plurality genuinely exists (comparison,
selection, inbox, bindings are four surfaces of one lifecycle).

### 2. Consumption Inbox taxonomy — D2 discipline, one shared severity function

Severity derives from ONE shared function, exactly as D2 ruled for the
Governance Inbox, so no two surfaces can ever disagree. The taxonomy:

```
HIGH — a binding is currently unsafe or unverifiable:
- package hash drift
- selected evidence no longer matches package
- AGENT principal inactive
- AGENT clearance below bound package clearance

MEDIUM — a selection may need review:
- newer successful PACKAGE evaluations exist for the same package
- selected model no longer appears among latest successful runs
- selection hash differs from current package hash

LOW — informational consumption hygiene:
- package has evaluations but no selection
- package has selection but no binding
- AGENT principal has no active credential
```

Every item is computed at read time from governed facts and never stored —
the v0.9.1 Governance Inbox pattern (D1) applied to consumption. The
moment an `is_stale` column appears, a second truth source exists.

### 3. Lineage is one server-composed endpoint

The lineage chain is a **product claim, not a UI convenience** — it must
be testable server-side, so the server composes it; the frontend never
stitches it from separate reads. The rule:

> Every expected hop either resolves or is explicitly declared missing.
> No silent gaps.

That is the D12 posture applied to lineage traversal.

### 4. D24 — Workbench Projection Rule (ratified; full text in docs/DECISIONS.md)

Workbench views project, aggregate, filter, sort, and derive governed
facts; they never become authoritative sources of state. New computed
read endpoints are permitted. Enforcement is structural and permanent:
the **schema snapshot guard** (WS0) — stronger than checking a diff.

## The hard boundary for this milestone

> **The existing model-selection PUT is the only write permitted in the
> milestone.**

- No binding withdrawal — D23 stays DEFERRED; the workbench displays
  bindings, it does not grow lifecycle mechanics ahead of that ruling.
- No new lifecycle. No persisted inbox. No cached leaderboard.
- No new tables. No new writable columns.
- No new permissions: the existing matrix governs (PUT selection at
  `assets:approve`; reads at `assets:read` / `audit:read` as routed today).

The three disciplines named at v1.1.0 acceptance remain invariants:
no orchestration creep (D22), no leaderboard disease (D1/D24), no
rewriting history.

## Workstreams and acceptance gates

### WS0 — D24 + schema projection guard

D24 recorded in docs/DECISIONS.md; the structural guard lands BEFORE any
screen is built, the way D18's seam suite and D20's purity assertions
protect their boundaries.

**Pass condition:**
> `backend/test_workbench_projection.py` freezes the v1.1.0 schema —
> every table, every column — and fails on ANY divergence, additions and
> removals alike. It runs in CI on every push. The guard is permanent,
> not a diff check: a future milestone that legitimately changes the
> schema updates the snapshot alongside the ratified decision that
> justifies it, in the same commit — never silently.

Evidence: `backend/test_workbench_projection.py` (in CI).

**Gate: PASSED (accepted June 2026, commits b309b34 + 5914792).** Accepted
with the adversarial proof noted as the load-bearing part: CI demonstrably
catches the two most likely regressions — a `consumption_inbox_items`
table and an `is_stale` column. That is D24 made operational.

### WS1 — Selection Workbench

A **decision workspace, NOT a leaderboard**. Purpose: help a human make a
governed decision — never "tell the human which model won." That
distinction is the screen.

The operator sees: package · current selection · candidate models (the
computed comparison) · evaluation evidence · trust/coverage metrics ·
supporting-run drill-down · selection rationale history. Rationale
history is projected from `PACKAGE_MODEL_SELECTED` audit events — never
a history table.

**Pass condition (gate text ratified at WS0 acceptance):**
> A top-level Consumption area exists.
>
> The Selection Workbench lets an authorized operator:
> - choose an AgentPackage
> - view current selection
> - view computed model comparison
> - view successful PACKAGE evaluation runs
> - view rationale/audit history
> - submit a new selection through the existing PUT only
>
> The UI must not:
> - add new writes
> - persist comparison state
> - persist selected view state
> - create dashboard-owned status
> - bypass `assets:approve`
> - show selection controls to users without permission
>
> Backend may add read-only projection endpoints only.
> D24 schema guard remains green.
> Full frontend checks pass.

**Language ruling:** the screen says **"Select model"**, never "Deploy
model". Deployment belongs to binding; selection belongs to evaluation
evidence.

Evidence: the WS0 guard holding across the WS1 diff; selection-history
projection covered by extending `test_http_api.py` /
`test_package_selection.py`. Unrun models display as absent, never zero
(D12).

**Gate: PASSED (accepted June 2026, commits a470dbb + 4e778ed + 5d1c4e6).**
Accepted with the strongest signal named at acceptance: WS1 added no new
projection endpoints and no new state, yet delivered the operator
workflow — exactly D24 working. Verified in-browser end-to-end including
the boundary-refusal path and READ_ONLY gating. Also accepted: the
`CitationModel.asset_status` fix (PACKAGE citation → frozen package
content, LIVE citation → live asset status; None is the honest D12
value, not a missing implementation).

### WS2 — Computed Consumption Inbox

A new computed module — the `governance_inbox.py` pattern applied to
consumption — plus one read endpoint. Note this is the first
**cross-package** consumption read: the v1.1 API surface is
package-scoped; the inbox spans packages by nature.

**Pass condition (gate text ratified at WS1 acceptance):**
> A Consumption Inbox appears inside the top-level Consumption area.
>
> It is fully computed from existing governed facts.
>
> It produces items for:
> - HIGH: package hash drift affecting a binding
> - HIGH: binding whose AGENT principal is inactive
> - HIGH: bound agent clearance now below package clearance
> - MEDIUM: current selection hash differs from current package hash
> - MEDIUM: newer successful PACKAGE evaluations exist after current selection
> - MEDIUM: selected model absent from latest successful PACKAGE evaluations
> - LOW: package has evaluations but no selection
> - LOW: package has selection but no binding
> - LOW: bound AGENT principal has no active credential
>
> One shared severity function assigns severity.
>
> Items deep-link into the Selection Workbench or future Binding Explorer
> target.
>
> No inbox item is persisted. No is_stale field. No new tables. No new
> writable columns. No dashboard-owned status. No new writes. D24 schema
> guard remains green. READ_ONLY can view inbox items but cannot take
> selection actions.

**Endpoint ruling:** backend may add ONE read-only endpoint —
`GET /api/consumption/inbox` — and it must declare every missing hop
rather than silently dropping it.

**Lifecycle ruling:** NO "dismiss" and NO "mark resolved". Those would
create inbox-owned state and violate the milestone spirit. An item
disappears the way it appeared: the underlying governed facts change
(re-evaluate, re-select, re-bind, fix identity), and the next compute
reflects them.

Evidence: `backend/test_consumption_inbox.py` (in CI).

**Gate: PASSED (accepted June 2026, commits a846cb3 + d77d8b2 + 2f736bf).**
Accepted with the family-hash interpretation ratified: packages are
append-only artifacts, so "drift" means *this binding / selection points
to an older package artifact while a newer artifact exists in the same
package family*. That is the semantic model going forward.

### WS3 — Binding Explorer + lineage projection

The flagship. A binding-centric read (`GET /api/bindings/{id}`) plus ONE
composed lineage projection walking **backwards**:

```
Binding → Selected model → Selection evidence → Evaluation runs
        → Package → Package contents → Approved assets → Source documents
```

and **sideways** into identity:

```
Binding → AGENT principal → Credentials → Authorization → Audit history
```

This screen is the differentiation sentence made visible: *ExpertMachina
can prove why a particular model was selected to consume a particular
governed expert package, and exactly what evidence justified that
decision.*

**Pass condition (gate text ratified at WS2 acceptance):**
> A Binding Explorer exists inside the top-level Consumption area.
>
> It lists ExpertAgentBindings and lets the operator inspect one binding.
>
> Backend may add read-only projection endpoints only:
> - `GET /api/bindings/{id}`
> - `GET /api/bindings/{id}/lineage`
>
> The lineage projection must compose:
> binding → package snapshot → current package-family status
> → selected model snapshot → selection evidence
> → supporting evaluation runs → package assets → source documents,
> and sideways:
> binding → AGENT principal → active credentials summary
> → relevant audit events.
>
> Every expected hop must either resolve or be declared missing.
> No silent gaps.
>
> The UI must:
> - render why-package, why-model, why-agent, why-clearance,
>   issued-by-whom
> - show superseded/stale/unverifiable warnings computed from facts
> - deep-link from Consumption Inbox items into the relevant binding
> - expose no withdrawal, deactivate, revoke, runtime, or deploy controls
>
> Boundaries: no new writes; no new tables; no new writable columns; no
> binding status field; no persisted lineage snapshot; no
> orchestration/runtime surface; D24 schema guard remains green;
> READ_ONLY can view lineage but cannot mutate anything.

**Language ruling:** the screen says **"binding"** and **"serving
package"**, never "deployed agent" — "deployed agent" invites runtime
assumptions (D22).

Evidence: `backend/test_binding_lineage.py` (in CI).

**Gate: PASSED (accepted June 2026, commits 428b6a3 + f130d93 + 2e05a67).**

## Milestone closed — v1.1.1 (June 2026)

All four gates PASSED. The acceptance verdict, recorded verbatim:

> The workbench made governed facts visible without becoming a new
> source of truth. That is exactly D24 doing its job.

The release narrative sentence: *v1.1.1 turns governed consumption from
backend capability into operator-visible evidence: selection decisions,
computed drift, and binding lineage are now inspectable without adding
new governed state.* D23 (binding lifecycle) remains DEFERRED — no
withdrawal mechanics shipped, by ruling. The D24 schema guard remains
in CI permanently; the v1.1.0 schema snapshot survived the entire
milestone untouched (26 tables, 271 columns).

## Build order

WS0 first, alone, before any UI work — the lock goes on the door before
the door is opened. Then WS1 → WS2 → WS3, each starting only after the
prior gate passes. The design contract is regenerated only if a gate
forces a scope change, and any reversal of a ruling above is recorded as
a supersession in docs/DECISIONS.md.
