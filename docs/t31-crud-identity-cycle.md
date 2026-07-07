# T3.1 — crud↔identity Import Cycle

> Audit task T3.1 (docs/audit-2026-07-07.md, Theme 4 structural risk).
> **RULING (user-ratified): remove or explicitly narrow the cycle WITHOUT
> changing identity semantics, audit behavior, route behavior, database
> schema, or package outputs.** Graph first, hinge second, smallest neutral
> move third.

## The before-state graph (the hinge)

The audit flagged a "crud↔identity circular import via ~18 lazy imports."
The inventory found the reality is sharper:

- **crud → identity** is a single *top-level* import (`crud.py`:
  `from app import identity`), used for `identity.Actor` /
  `identity.require_actor_object`.
- **identity → crud** was a single *lazy* import — one edge, in one function:
  `identity._audit()` did `from app import crud` to call
  `crud.log_audit_event`. That lone edge closed the cycle.
- The "~18" is the number of *callers* of `crud.log_audit_event` across the
  app — the surface to preserve, not the number of cycle edges.

So the entire hinge was one function, `log_audit_event`, which depends on
**nothing but the ORM models and `datetime`** — no identity, no other crud.

## The smallest neutral move

- **`app/audit.py`** (new, neutral) — `log_audit_event` moved here verbatim;
  imports only `app.database` + `datetime`, so it depends on neither crud nor
  identity.
- **`app/crud.py`** — re-exports it (`from app.audit import log_audit_event`);
  the definition is gone but `crud.log_audit_event` and every bare in-module
  call are unchanged, so all ~18 callers are untouched.
- **`app/identity.py`** — imports `app.audit` at module top and calls
  `audit.log_audit_event`; the lazy `from app import crud` is deleted. The
  top-level import is safe precisely because audit is neutral.

Result: crud → identity remains (one direction = no cycle); identity → crud
is **gone**; identity → audit and crud → audit both point at a leaf. The
crud↔identity cycle is removed, not merely narrowed.

## The proof (nothing semantic moved)

- **`test_import_cycle.py`** (new permanent guard, AST-based): asserts
  `app/identity.py` imports crud **by no means, top-level or lazy**;
  crud still imports identity (one-directional); `app/audit.py` stays neutral;
  and `crud.log_audit_event is app.audit.log_audit_event` (surface preserved).
  A re-introduced lazy `from app import crud` fails CI.
- **Route manifest** byte-identical: 87 routes, sha256 `a9558682…`
  (unchanged from the T2.4 baseline).
- **D24** held: 28 tables / 305 columns (no schema change).
- **Full harness 66/66 green** (65 + the new guard) — the audit-writing
  suites (identity boundary, migration, custody, authorship) all pass, so the
  append-only audit-write behavior is unchanged and there is no import-order
  regression.

## Deliberately out of scope (T3.1 is only the cycle)

No import pruning, no Pydantic polish, no service-layer typing, no
opportunistic refactors. `crud.py`'s now-possibly-unused `datetime`/`import`
lines are left untouched — pruning is a separate, clearly-marked polish step.
