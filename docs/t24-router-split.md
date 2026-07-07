# T2.4 — main.py Router Split

> Audit task T2.4 (docs/audit-2026-07-07.md, Theme 4 structural risk).
> **THE RULING (user-ratified): the router split is a PURE RELOCATION.** No
> endpoint semantics, model schemas, dependency behavior, path names, status
> codes, or audit events may change.

## What changed

`app/main.py` went from **1805 lines / 87 inline routes** to **274 lines**:
infrastructure (imports, app, CORS, request-id middleware, `startup_event`)
plus router includes and a backward-compatible re-export surface. The 87
route handlers + 4 domain helpers were relocated **verbatim** into 12
`app/routers/*.py` modules by domain.

- **`app/deps.py`** — the four shared dependencies (`get_db`,
  `require_actor`, `require_perm`, `_authorize_or_403`) moved here so main and
  every router share ONE object identity per dependency (test suites override
  `app.dependency_overrides[get_db]` and import these by name — identity must
  not change). `main.py` re-exports them.
- **`app/routers/`** — `system`, `identity_admin`, `projects`, `sources`,
  `policies`, `projections`, `settings`, `assets`, `experts`, `packages`,
  `evaluations`, `insights`. Each is `APIRouter()` + its relocated handlers
  (only `@app.<m>` → `@router.<m>`); `main.py` calls `include_router` for each.
- **Backward-compatible surface** — `main.py` re-imports every relocated
  handler, so the ~15 suites doing `from app.main import <handler>` (and
  `from app.main import get_db`) keep working unchanged.

Deliberately unchanged: `startup_event` stays in `main.py` (app lifecycle);
main's now-broader import block is left intact (pruning unused imports is a
T3.x quality concern, not part of a pure relocation).

## The proof (before == after)

- **`tools/route_manifest.py`** rebuilds the live route contract from the
  FastAPI app — per route: method, path, name, tags, status_code,
  full-fidelity response_model, and the resolved security dependency chain
  (with `require_perm` guards resolved to `require_perm:<permission>` via
  closure introspection, so an auth change cannot hide behind a renamed
  closure).
- Baseline captured at f90bb25 (pre-split): **87 routes, sha256
  `a9558682…`**. After the split the manifest is **byte-identical**.
- **`test_route_manifest.py`** pins `FROZEN_DIGEST` permanently (a named CI
  guard beside the D24 schema snapshot). A future contract change updates the
  digest in the same commit, with the reason — a silent drift fails CI.

Two suites (`test_package_selection`, `test_expert_agent_binding`) asserted a
route's auth tier by grepping `main.py`'s `@app.<verb>(...)` source text; they
were retargeted to the new module (`routers/packages.py`, `@router.`) — the
assertion is unchanged, only the file it reads moved.

## Gates

- Route manifest byte-identical (87 routes, `a9558682…`).
- Full harness **65/65 green** (64 + the new manifest guard).
- App boots via TestClient: startup sequence runs, `/api/health` 200,
  unauthenticated `/api/projects` 401 (auth preserved).
- D24 held at 28t/305c; the six constitutional guards untouched; no schema
  change; frontend untouched.
