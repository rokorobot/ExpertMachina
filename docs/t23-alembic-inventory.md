# T2.3 — Alembic Migration Spine: Inventory Pass

> Audit task T2.3 (docs/audit-2026-07-07.md, Theme 4 structural risk).
> Step 1 of the ratified 5-step arc. **Inventory first, like T2.6.**
> GUIDING PRINCIPLE (user-ratified): *"Alembic may formalize the schema
> history, but it must not IMPROVE the schema during this task."* Effective
> schema and the D24 fingerprint (28 tables / 305 columns) stay byte-identical.

## The goal, restated

Retire the hand-rolled `database._ensure_columns` additive-migration engine
and replace it with a governed Alembic path — **without changing the effective
schema or the D24 fingerprint.** Formalize the history; improve nothing.

## 1. Every schema create / mutate path (the surface T2.3 governs)

### 1.1 Production entry point — `app/database.py::init_db()`

The ONE production schema path. Called by `main.py::startup_event()` (line 151),
inside the startup registry sequence. Two operations, in order:

1. `Base.metadata.create_all(bind=engine)` — creates any missing tables from
   the ORM models. Never adds columns to existing tables (SQLAlchemy limitation).
2. `_ensure_columns()` — the hand-rolled additive migration that fills the gap.

### 1.2 The engine to retire — `app/database.py::_ensure_columns()` (lines 741–821)

Additive-only. For each table it PRAGMAs `table_info`, then `ALTER TABLE … ADD
COLUMN` for any column in its `additions` map not already present. Idempotent
(re-running is a no-op). **This map IS the de-facto migration history** — the
record of every column added after its table first shipped:

| Table | Post-ship columns (the history) | Ratified by |
|---|---|---|
| `agent_packages` | clearance_level, file_path, package_hash, manifest_json | MVP 0.9.4 |
| `documents` | content_hash | MVP 0.10.0 |
| `ingestion_jobs` | files_changed | MVP 0.10.1 |
| `evaluation_runs` | run_type, package_version, package_hash, consumer_model_provider, consumer_model_name | v1.1 WS2 |
| `source_documents` | details_json, source_metadata_json | MVP 0.10.1 / D26 |
| `knowledge_assets` | domain, **source_class¹** | D27 / D30 |
| `approval_policies` | source_conditions_json, engine_conditions_json, domains_json | D26 |
| `source_connectors` | external_credential_id, **lane¹** | D25 / D29-D30 |
| `audit_events` | identity_fact_id | v1.0 |
| `asset_reviews` | identity_fact_id | v1.0 |
| `asset_revisions` | identity_fact_id | v1.0 |

¹ **The two NOT-NULL-with-default columns** — `knowledge_assets.source_class`
(`TEXT NOT NULL DEFAULT 'PRIMARY'`) and `source_connectors.lane`
(`TEXT NOT NULL DEFAULT 'PRIMARY'`). Both also carry `server_default="PRIMARY"`
in the ORM. Legacy rows become PRIMARY *by construction* (D30) — this behavior
is constitutional and any Alembic baseline/migration must reproduce it exactly.

### 1.3 The existing migration proof — `test_migration.py`

The closest analog to what Alembic must preserve, and the **"existing /
pre-baseline DB path"** the plan's dual-path gate demands. It hand-builds a
v0.12-shaped SQLite DB with raw `CREATE TABLE` (no post-ship columns, no
identity tables), then runs `db.init_db()` + the startup registry sequence and
asserts: additive columns appear, legacy rows stay honestly legacy (NULL facts,
D12), the sequence is idempotent, validation reports (never absorbs) anomalies.
**This suite is the acceptance bar for the migrated path.**

### 1.4 The freeze reference — `test_workbench_projection.py` (D24)

The 28-table / 305-column fingerprint. **Computed from
`db.Base.metadata.sorted_tables` — MODEL-based, not DB-based.** Because Alembic
must not touch the ORM models, this guard stays byte-identical automatically.
It is the invariant, not a task deliverable.

### 1.5 Test-suite DB setup — two idioms, ~66 suites

- **`db.Base.metadata.create_all(bind=engine)`** (≈40 suites) — a fresh
  model-based create on the suite's own temp/in-memory engine. **Bypasses
  `_ensure_columns` entirely** (models already carry every column). These do
  NOT touch Alembic and must not need to.
- **`db.init_db()`** (≈16 suites) — the full production path incl.
  `_ensure_columns`. These exercise whatever `init_db()` becomes.
- Both idioms rebind `db.engine`/`db.SessionLocal` at import (the harness runs
  each suite as an isolated subprocess precisely because of this global rebind).

## 2. Table classification (canonical / derived / audit / projection)

All 28 tables are **canonical governed state** persisted through the ORM. Key
finding for scoping:

- **Projection-only tables: NONE.** Projections and renders (graph, vault) live
  in the audit ledger as `PROJECTION_RENDERED` events and as disposable files
  (D28/D31) — never as rows. Alembic's scope is the full 28 and nothing is
  "derived state parked in a table."
- **Audit / immutable-evidence:** `audit_events` (append-only ledger),
  `identity_facts` (immutable), `claim_verdicts` (immutable), `asset_revisions`
  (immutable content records). Structure is still ordinary schema to Alembic.
- **Vestigial:** `customers` (present, minimally used) — stays; removing it
  would "improve" the schema, which this task forbids.

## 3. Environment facts

- **Alembic is not yet a dependency**; no `alembic/` dir or config exists.
  Adding it edits `requirements.txt` → both hash-locks must be regenerated
  (`uv pip compile --universal --generate-hashes` — `uv 0.11.18` confirmed
  present) for BASE (`requirements.lock`) and NLI (`requirements-nli.lock`).
  **pip-audit must stay ZERO-vuln / ZERO-ignore** on base (the T2.6 win) —
  Alembic pulls `Mako` + `MarkupSafe` (both already transitive via nothing
  today; verify no new advisory).
- **`DATABASE_URL`** is hardcoded `sqlite:///./expert_machina.db` in
  `database.py:6` and used only by the module-global `engine`. Alembic's
  `env.py` must read the SAME URL from `app.database` (never a second source of
  truth). Adding an env override would be an improvement — **out of scope.**
- **CI** (`.github/workflows/ci.yml`): the pytest harness sweep + 8 named
  constitutional guard steps. A new `test_alembic_migration.py` auto-joins the
  harness the moment the file exists (no YAML edit needed).

## 4. The one hard design fork (needs ratification before step 3)

Everything above is mechanical. The single genuine decision: **how does a
pre-Alembic database get onto the Alembic timeline?** A real deployment's
`expert_machina.db` already has every column (it has run `_ensure_columns` many
times) but has **no `alembic_version` table**. Alembic must adopt it without a
destructive re-create and without an `_ensure_columns` fallback (the plan says
*remove/neutralize* it). Candidate approaches to put to the user:

- **(A) Single baseline + adopt-by-stamp.** One baseline revision = the full
  current 28/305 schema. `init_db()`: if no tables → `upgrade head`; if tables
  exist but no `alembic_version` → `stamp head` (adopt in place). Simple; but a
  genuinely *older* DB (missing post-ship columns) would be stamped without
  getting them. Mitigated because the migrated-path gate (test_migration's v0.12
  builder) is the only pre-current DB we claim to support — it needs the columns.
- **(B) Historical chain.** Baseline = earliest shipped schema, then one
  migration per `_ensure_columns` entry (faithfully replaying §1.2). Any legacy
  DB stamped at baseline upgrades forward correctly. Truest to "formalize the
  history," more migrations to author, and the auto-detect-current-shape problem
  remains for un-stamped current DBs.
- **(C) Baseline + one reconciliation step, then stamp.** `init_db()` on an
  un-stamped DB runs the additive reconciliation ONCE (as an Alembic migration,
  not `_ensure_columns`) then stamps head. Neutralizes `_ensure_columns` while
  preserving its safety for the exact legacy shape test_migration builds.

**Recommendation to discuss: (A) for production adoption + (B)'s faithful column
history expressed as the baseline's provenance**, with test_migration's v0.12
builder as the migrated-path gate. The dual-path convergence gate (fresh-create
fingerprint == migrated fingerprint == 28/305) decides correctness either way.

## 4a. RATIFIED + DELIVERED (2026-07-07)

The user ratified **choice A: baseline + adopt-by-stamp.** Delivered:

- **Alembic introduced** — `alembic==1.16.5` (base + NLI hash-locks
  regenerated with `uv`; base pip-audit stays **ZERO-vuln / ZERO-ignore**).
  `alembic.ini` + `alembic/env.py` (binds to `app.database` metadata AND the
  live engine — honors the harness's per-suite rebind; no second DATABASE_URL).
- **Baseline migration** `fc4ba7fed054` — autogenerated from the models and
  **frozen**. Two proofs: applying it to an empty DB reproduces the create_all
  fingerprint **byte-for-byte (28t/305c, sha256 `97537bd4…`)**, and
  autogenerate against a head DB detects **no changes** (empty diff → baseline
  == models, no drift, no improvement).
- **`init_db()` rewritten** to the adopt-by-stamp path; **`_ensure_columns`
  deleted.** Empty DB → `upgrade head`; pre-Alembic head-shape DB → `stamp
  head` (adopt in place, data preserved); versioned DB → `upgrade head` (no-op).
- **Loud-refusal hardening** — a pre-Alembic DB that is *not* at head shape is
  refused with a named deficiency rather than stamped with a false version
  (the project's "loud refusals, never silent" rule). **The accepted cost of A
  over C:** an intermediate-shape pre-Alembic DB is no longer auto-upgraded; the
  v0.12→v1.0 column back-fill that `_ensure_columns` performed is retired.
- **Gates** — new `test_alembic_migration.py` (FRESH / CONVERGENCE / ADOPT /
  REFUSE / IDEMPOTENT, all green); `test_migration.py` reconciled to choice A
  (Part 1 now proves adopt-by-stamp; the identity-registry Parts 2–5 preserved
  intact); **full harness 64/64 green**; D24 held at 28t/305c; the six
  constitutional guards untouched.

## 5. Proposed remaining sequence (steps 2–5, unchanged from the plan)

2. **FREEZE baseline** — record the current live fingerprint; confirm D24
   still represents canonical structure; green `origin/main` (2f1eb58,
   `post-audit-hardening`) is the authoritative start.
3. **INTRODUCE Alembic, no semantic change** — config + `env.py` (reusing
   `app.database` URL/metadata) + baseline migration; assert fresh-create and
   migrated-create converge to the SAME fingerprint (empty autogenerate diff
   against the models is the proof the baseline matches).
4. **REPLACE startup mutation** — `init_db()` runs the Alembic path; remove /
   neutralize `_ensure_columns`; startup no longer silently mutates.
5. **DUAL-PATH GATES** — fresh DB path + pre-baseline DB path + fingerprint
   equivalence, as a new `test_alembic_migration.py`; the 63-suite harness stays
   green; D24 and the 8 constitutional guards untouched.
