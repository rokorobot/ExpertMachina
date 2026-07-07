"""Schema fingerprint tool (T2.3 Alembic migration spine).

Emits a deterministic, DB-level fingerprint of a SQLite database's schema:
for every user table, the ordered PRAGMA table_info (name, type, notnull,
default, pk). This is the convergence target for T2.3's dual-path gate -
fresh model create_all, Alembic baseline upgrade, and pre-Alembic adoption
must all produce the SAME fingerprint (and match the D24 count 28t/305c).

Usage:
    python tools/schema_fingerprint.py            # fingerprint a fresh create_all
    python tools/schema_fingerprint.py <db_path>  # fingerprint an existing DB
"""
import hashlib
import json
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("EM_NLI_VERIFICATION", "off")
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine, text


# alembic_version is Alembic's bookkeeping table, never governed schema -
# excluded so fresh-model and Alembic-managed DBs compare equal.
IGNORE_TABLES = {"alembic_version", "sqlite_sequence"}


def fingerprint(engine):
    with engine.connect() as conn:
        tables = sorted(
            row[0] for row in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"))
            if row[0] not in IGNORE_TABLES
        )
        schema = {}
        for t in tables:
            cols = []
            for row in conn.execute(text(f"PRAGMA table_info({t})")):
                # (cid, name, type, notnull, dflt_value, pk)
                cols.append({
                    "name": row[1], "type": row[2], "notnull": row[3],
                    "default": row[4], "pk": row[5],
                })
            cols.sort(key=lambda c: c["name"])
            schema[t] = cols
    return schema


def summarize(schema):
    table_count = len(schema)
    column_count = sum(len(c) for c in schema.values())
    blob = json.dumps(schema, sort_keys=True).encode()
    return table_count, column_count, hashlib.sha256(blob).hexdigest()


def main():
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        engine = create_engine(f"sqlite:///{db_path}",
                               connect_args={"check_same_thread": False})
        label = db_path
    else:
        from app import database as db
        tmp = os.path.join(tempfile.mkdtemp(prefix="em_fp_"), "fresh.db")
        engine = create_engine(f"sqlite:///{tmp}",
                               connect_args={"check_same_thread": False})
        db.Base.metadata.create_all(bind=engine)
        label = "fresh model create_all"

    schema = fingerprint(engine)
    tcount, ccount, digest = summarize(schema)
    print(json.dumps(schema, indent=2, sort_keys=True))
    print(f"\n# {label}")
    print(f"# tables={tcount} columns={ccount} sha256={digest}")


if __name__ == "__main__":
    main()
