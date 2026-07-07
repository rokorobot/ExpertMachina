"""The Alembic migration spine gate (audit T2.3 -
docs/t23-alembic-inventory.md). The dual-path + convergence proof for the
governed schema path that retired database._ensure_columns.

THE PRINCIPLE: Alembic formalizes the schema history; it does not IMPROVE
the schema. The effective schema and the D24 fingerprint (28 tables /
305 columns) are unchanged. Every path a database can take through
init_db() converges to the SAME DB-level fingerprint.

Stages:
  1. FRESH        empty DB -> upgrade head builds the full schema, stamped
                  at head; fingerprint is the D24 count.
  2. CONVERGENCE  the Alembic baseline and the ORM create_all produce a
                  byte-identical DB-level fingerprint (baseline == models,
                  no drift, no improvement).
  3. ADOPT        a pre-Alembic head-shape DB (create_all, no version) is
                  adopted in place - stamped at head, data preserved,
                  fingerprint unchanged (choice A, ratified).
  4. REFUSE       a column/table-deficient pre-Alembic DB is refused LOUDLY,
                  never stamped with a false version (the retired
                  _ensure_columns back-fill is gone, by design).
  5. IDEMPOTENT   re-running init_db over a stamped DB is a clean no-op.
"""
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app import database as db
from tools.schema_fingerprint import fingerprint, summarize

D24_TABLES, D24_COLUMNS = 28, 305


def _rebind(path):
    db.engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)


def _fp(path):
    eng = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    try:
        return summarize(fingerprint(eng))
    finally:
        eng.dispose()


def _alembic_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    cfg = Config(os.path.join(db._BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(db._BACKEND_DIR, "alembic"))
    return ScriptDirectory.from_config(cfg).get_current_head()


def main():
    d = tempfile.mkdtemp(prefix="em_alembic_")
    head = _alembic_head()
    assert head, "the baseline revision must exist"

    # Stage 1: FRESH.
    print("\n--- Stage 1: FRESH empty DB -> upgrade head ---")
    p1 = os.path.join(d, "fresh.db")
    _rebind(p1)
    db.init_db()
    t, c, digest = _fp(p1)
    assert (t, c) == (D24_TABLES, D24_COLUMNS), f"fresh: {t}t/{c}c (want 28/305)"
    with db.engine.connect() as conn:
        ver = list(conn.execute(text("SELECT version_num FROM alembic_version")))
    assert ver and ver[0][0] == head, f"fresh must stamp head {head}, got {ver}"
    print(f"Stage 1 passed: {t}t/{c}c, stamped at head ({head}).")

    # Stage 2: CONVERGENCE - Alembic baseline == ORM create_all, byte-identical.
    print("\n--- Stage 2: CONVERGENCE (baseline == models) ---")
    p_model = os.path.join(d, "model_createall.db")
    meng = create_engine(f"sqlite:///{p_model}", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=meng)
    meng.dispose()
    mt, mc, mdigest = _fp(p_model)
    assert (mt, mc) == (D24_TABLES, D24_COLUMNS), f"models: {mt}t/{mc}c"
    assert mdigest == digest, (
        "baseline drift: the Alembic-built schema is not byte-identical to the "
        f"ORM models (create_all={mdigest} vs baseline={digest}). The baseline "
        "must formalize the models, never improve them.")
    # metadata-level cross-check against the D24 count (test_workbench_projection).
    meta_tables = len(db.Base.metadata.tables)
    meta_cols = sum(len(t.columns) for t in db.Base.metadata.tables.values())
    assert (meta_tables, meta_cols) == (D24_TABLES, D24_COLUMNS), \
        f"metadata is {meta_tables}t/{meta_cols}c - the D24 fingerprint moved"
    print(f"Stage 2 passed: baseline and create_all agree byte-for-byte "
          f"(sha256 {digest[:16]}...), and the model metadata is 28t/305c.")

    # Stage 3: ADOPT-BY-STAMP - pre-Alembic head-shape DB, data preserved.
    print("\n--- Stage 3: ADOPT-BY-STAMP (pre-Alembic head-shape DB) ---")
    p3 = os.path.join(d, "preexisting.db")
    pre = create_engine(f"sqlite:///{p3}", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=pre)
    with pre.begin() as conn:
        conn.execute(text("INSERT INTO projects (name, status) VALUES ('keep me', 'NEW')"))
    pre.dispose()
    assert "alembic_version" not in set(inspect(
        create_engine(f"sqlite:///{p3}")).get_table_names()), "premise: no version yet"
    _rebind(p3)
    db.init_db()
    with db.engine.connect() as conn:
        ver = list(conn.execute(text("SELECT version_num FROM alembic_version")))
        rows = list(conn.execute(text("SELECT name FROM projects")))
    assert ver and ver[0][0] == head, f"adopt must stamp head, got {ver}"
    assert rows == [("keep me",)], f"adopt must NOT drop data: {rows}"
    t3, c3, d3 = _fp(p3)
    assert (t3, c3, d3) == (D24_TABLES, D24_COLUMNS, digest), \
        f"adopt changed the schema: {t3}t/{c3}c {d3}"
    print("Stage 3 passed: adopted in place, stamped at head, data kept, "
          "fingerprint unchanged.")

    # Stage 4: REFUSE - a deficient pre-Alembic DB is refused, never stamped.
    print("\n--- Stage 4: REFUSE a deficient pre-Alembic DB (loud, no false stamp) ---")
    p4 = os.path.join(d, "deficient.db")
    dfe = create_engine(f"sqlite:///{p4}", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=dfe)
    with dfe.begin() as conn:
        conn.execute(text("DROP TABLE quality_scores"))  # now not at head shape
    dfe.dispose()
    _rebind(p4)
    refused = False
    try:
        db.init_db()
    except RuntimeError as e:
        refused = True
        assert "adopt-by-stamp refused" in str(e), f"wrong error: {e}"
        assert "quality_scores" in str(e), f"error must name the deficiency: {e}"
    assert refused, "a deficient pre-Alembic DB MUST be refused, not stamped"
    with db.engine.connect() as conn:
        tbls = set(inspect(conn).get_table_names())
    assert "alembic_version" not in tbls, "refusal must NOT write a false version"
    print("Stage 4 passed: deficiency named, refusal loud, no false version stamped.")

    # Stage 5: IDEMPOTENT.
    print("\n--- Stage 5: IDEMPOTENT (re-run over a stamped DB) ---")
    _rebind(p1)
    db.init_db()
    db.init_db()
    t5, c5, d5 = _fp(p1)
    assert (t5, c5, d5) == (D24_TABLES, D24_COLUMNS, digest), "re-run drifted the schema"
    print("Stage 5 passed: repeated init_db is a clean no-op.")

    print("\nAll Alembic migration-spine checks passed. Formalize the history; "
          "improve nothing.")


if __name__ == "__main__":
    main()
