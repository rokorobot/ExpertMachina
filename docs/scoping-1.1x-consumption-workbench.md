# v1.1.x — Consumption Operations Workbench: Pre-Scoping Brief

> Design constraints ruled post-v1.1.0 (June 2026), BEFORE the scoping
> session. This is input to scoping, not a build contract — the contract
> is written when the milestone is scoped. Recorded here per D16:
> repo-resident state beats chat memory.

## The milestone's nature

v1.0 and v1.1 were architecture milestones; the workbench is a **product
design** milestone. The question shifts from *"can we govern knowledge?"*
to *"can humans efficiently operate a governed knowledge system?"* The
backend capability now exceeds operator visibility — the workbench
converts capability into operational usability **without changing the
architecture**.

## The constitutional constraint: a projection layer, almost entirely

Everything the workbench shows already exists as governed facts:

```
EvaluationRun · PackageModelSelection · ExpertAgentBinding
Audit Events · Identity Facts
```

The workbench answers:

> What happened? Why did it happen? Who decided? What evidence justified it?

It must never become:

> Store another representation of what happened.

**The design test (apply to every screen):**

> If a workbench screen disappears entirely, no governed fact may be lost.

**Anti-patterns to refuse** — the path by which systems that start with
computed views reintroduce a second source of truth: cached rankings,
saved comparisons, dashboard state tables, selection summaries,
deployment snapshots.

**Candidate invariant to formalize at scoping (D24 candidate — proposed
text, to be ratified with the milestone):**

> **D24 — Workbench Projection Rule**
> Workbench views may project, aggregate, filter, sort, and derive
> existing governed facts. Workbench views may not become an
> authoritative source of state. No workbench screen may require
> persistence of information that is derivable from governed facts.

Enforce it the way D18 and D22 are enforced — structurally, in CI:

> The workbench milestone's diff adds NO new tables and NO new writable
> columns.

That converts a UX philosophy into a regression test. Comparisons stay
computed; selections and bindings stay governed facts; dashboards are
projections only. The moment a workbench screen starts owning state,
D1 starts to erode — the UI door is where leaderboard disease would
re-enter.

## The opening question for the scoping session

Not tables, APIs, or schemas. First:

> What are the three most common operator decisions in the consumption
> lifecycle, and how can each be completed using only projections of
> existing governed facts?

**Candidate answers (endorsed pre-scoping; confirm or replace at the
session) — each maps onto existing governed objects:**

1. **"Which model should serve this package?"** — the selection
   decision. Projections: comparison view, trust/coverage metrics, run
   details, rationale history. Maps to EvaluationRun +
   PackageModelSelection; the existing PUT selection is the only write.
   No new state.
2. **"Something changed — does my selection still stand?"** — the
   re-evaluation decision. **Staleness is COMPUTED, never persisted** —
   the moment an `is_stale` column appears, a second truth source
   exists. Derive it live: current selection package_hash vs current
   package hash; current selection model vs latest successful
   evaluations. Likely shape: a **Computed Consumption Inbox** — the
   workbench's equivalent of the Governance Inbox, every item derived,
   never stored (the v0.9.1 pattern applied to consumption).
3. **"What is this agent actually serving, and can I prove it?"** — the
   lineage decision; likely the flagship workflow. Anyone can build
   Agent → Model → Answer; very few systems can traverse
   Agent → Binding → Selection → Evaluation → Package → Asset → Source
   Document and prove each step. That chain is where the
   differentiation lives.

## Screen direction (ruled, shape to be discovered at scoping)

### Selection Workbench — a decision workspace, NOT a leaderboard

The operator sees: package · current selection · candidate models ·
evaluation evidence · trust/coverage metrics · supporting runs ·
selection rationale history.

Purpose: **help a human make a governed decision** — never "tell the
human which model won." That distinction is the screen.

### Binding Explorer — likely the most differentiated screen

Start at a binding and walk **backwards** through the lineage:

```
Binding → Selected model → Selection evidence → Evaluation runs
        → Package → Package contents → Approved assets → Source documents
```

and **sideways** into identity:

```
Binding → AGENT principal → Credentials → Authorization → Audit history
```

Very few systems expose that complete chain; this screen is the
differentiation sentence made visible: *ExpertMachina can prove why a
particular model was selected to consume a particular governed expert
package, and exactly what evidence justified that decision.*

## Standing boundaries (unchanged by this milestone)

- D1 (facts persisted, views computed), D8 (UI areas earned by
  plurality), D22 (no orchestration), D23 (binding lifecycle DEFERRED —
  the workbench displays bindings; it does not grow withdrawal
  mechanics ahead of the D23 ruling).
- The three disciplines named at v1.1.0 acceptance remain invariants:
  no orchestration creep, no leaderboard disease, no rewriting history.
