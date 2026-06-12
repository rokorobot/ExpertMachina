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

**Candidate invariant to formalize at scoping (D24 candidate):**

> No workbench view may become authoritative.

Comparisons stay computed; selections and bindings stay governed facts;
dashboards are projections only. The moment a workbench screen starts
owning state, D1 starts to erode — the UI door is where leaderboard
disease would re-enter.

## The opening question for the scoping session

Not tables, APIs, or schemas. First:

> What are the three most common operator decisions in the consumption
> lifecycle, and how can each be completed using only projections of
> existing governed facts?

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
