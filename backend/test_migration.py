import json
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

# WS4 migration suite: a pre-boundary (v0.12-shaped) database upgrades
# cleanly through init_db + the startup sequence. Contracts under test:
# additive columns appear, legacy rows stay honestly legacy (NULL facts),
# legacy role names migrate in the MUTABLE registry only, historical
# role_snapshots are never rewritten, the whole sequence is idempotent,
# and startup validation reports (never absorbs) anomalies.

import sqlite3

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_tmpdir = tempfile.mkdtemp(prefix="em_migration_")
DB_PATH = os.path.join(_tmpdir, "legacy.db")


def build_legacy_database():
    """A v0.12-era database: audit/review/revision tables WITHOUT
    identity_fact_id, actor strings everywhere, no identity tables at all,
    plus a policy and connector that pre-date DELEGATED registration."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE audit_events (
        id INTEGER PRIMARY KEY, timestamp DATETIME, actor VARCHAR,
        event_type VARCHAR NOT NULL, target_id VARCHAR, details TEXT)""")
    c.execute("""CREATE TABLE asset_reviews (
        id INTEGER PRIMARY KEY, asset_id INTEGER, reviewer VARCHAR,
        approver VARCHAR, notes TEXT, reviewed_at DATETIME)""")
    c.execute("""CREATE TABLE asset_revisions (
        id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL,
        revision_number INTEGER NOT NULL, status VARCHAR, content TEXT NOT NULL,
        source_hash VARCHAR, content_hash VARCHAR NOT NULL, created_by VARCHAR,
        created_at DATETIME, approved_by VARCHAR, approved_at DATETIME,
        supersedes_revision_id INTEGER, superseded_by_revision_id INTEGER,
        change_reason TEXT)""")
    c.execute("""CREATE TABLE approval_policies (
        id INTEGER PRIMARY KEY, project_id INTEGER, name VARCHAR NOT NULL,
        asset_types_json TEXT NOT NULL, connector_id INTEGER,
        enabled BOOLEAN, version INTEGER, created_by VARCHAR,
        created_at DATETIME, updated_at DATETIME)""")
    c.execute("""CREATE TABLE source_connectors (
        id INTEGER PRIMARY KEY, project_id INTEGER, name VARCHAR NOT NULL,
        type VARCHAR, root_path VARCHAR NOT NULL, include_extensions VARCHAR,
        created_at DATETIME)""")
    # pre-boundary governed history: actor strings, no facts anywhere
    c.execute("INSERT INTO audit_events (timestamp, actor, event_type, target_id, details) "
              "VALUES ('2026-03-01 10:00:00', 'GovernanceOfficer', 'ASSET_APPROVED', '42', 'legacy approval')")
    c.execute("INSERT INTO asset_reviews (asset_id, approver, notes, reviewed_at) "
              "VALUES (42, 'GovernanceOfficer', 'legacy review', '2026-03-01 10:00:00')")
    c.execute("INSERT INTO asset_revisions (asset_id, revision_number, status, content, "
              "content_hash, created_by, approved_by, approved_at) "
              "VALUES (42, 1, 'APPROVED', 'legacy content', 'abc123', 'sop_editor', "
              "'GovernanceOfficer', '2026-03-01 10:00:00')")
    c.execute("INSERT INTO approval_policies (project_id, name, asset_types_json, enabled, version, created_by) "
              "VALUES (1, 'Legacy low-risk docs', '[\"SYSTEM\"]', 1, 1, 'operator')")
    c.execute("INSERT INTO source_connectors (project_id, name, type, root_path) "
              "VALUES (1, 'Legacy Share', 'LOCAL_FOLDER', 'C:/legacy')")
    conn.commit()
    conn.close()


def main():
    print("\nBuilding a pre-boundary (v0.12-shaped) database...")
    build_legacy_database()

    from app import database as db
    db.engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)
    from app import identity

    def run_startup_sequence():
        """Exactly what main.startup_event does to the schema and registry."""
        db.init_db()
        with db.SessionLocal() as session:
            identity.ensure_system_principals(session)
            admin, one_time = identity.bootstrap_admin(session)
            for pol_name, in session.execute(text("SELECT name FROM approval_policies")):
                identity.ensure_delegated_principal(session, f"policy:{pol_name}")
            for conn_name, in session.execute(text("SELECT name FROM source_connectors")):
                identity.ensure_delegated_principal(session, f"connector:{conn_name}")
            identity.migrate_legacy_roles(session)
            findings = identity.validate_boundary(session)
            return admin, one_time, findings

    # Part 1: the upgrade is additive and the boundary boots on legacy data.
    print("\n--- Part 1: Schema upgrade (additive columns, identity tables) ---")
    admin, one_time, findings = run_startup_sequence()
    with db.engine.connect() as conn:
        for table in ("audit_events", "asset_reviews", "asset_revisions"):
            cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            assert "identity_fact_id" in cols, f"{table} must gain identity_fact_id"
        tables = {row[0] for row in conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table'"))}
        assert {"principals", "credentials", "identity_facts"} <= tables
    assert admin is not None and one_time is not None, "empty-of-humans DB bootstraps an admin"
    assert findings == [], f"clean migration must validate clean: {findings}"
    print("Part 1 passed: columns added, identity tables created, admin bootstrapped,")
    print("               boundary validation clean.")

    # Part 2: legacy history is honestly legacy - never retro-fabricated.
    print("\n--- Part 2: Legacy rows keep NULL facts and their actor strings ---")
    with db.SessionLocal() as session:
        ev = session.query(db.AuditEvent).filter_by(event_type="ASSET_APPROVED").first()
        assert ev.actor == "GovernanceOfficer" and ev.identity_fact_id is None, \
            "pre-boundary events mean 'we did not know' - facts are never fabricated (D12)"
        review = session.query(db.AssetReview).filter_by(asset_id=42).first()
        assert review.approver == "GovernanceOfficer" and review.identity_fact_id is None
        rev = session.query(db.AssetRevision).filter_by(asset_id=42).first()
        assert rev.approved_by == "GovernanceOfficer" and rev.identity_fact_id is None
        assert session.query(db.IdentityFact).filter(
            db.IdentityFact.principal_name == "GovernanceOfficer").count() == 0
    print("Part 2 passed: legacy approvals keep their strings; zero retroactive facts.")

    # Part 3: legacy identities migrate - registry only, snapshots untouched.
    print("\n--- Part 3: Legacy role names migrate; history does not ---")
    with db.SessionLocal() as session:
        # seed pre-WS3 principals + a historical fact, as an upgraded WS1/2 site would have
        for name, role in [("officer", "GOVERNANCE_OFFICER"), ("rev", "REVIEWER"), ("vw", "VIEWER")]:
            session.add(db.Principal(name=name, display_name=name, kind="HUMAN", role=role))
        session.add(db.Principal(name="old-agent", display_name="old-agent", kind="AGENT",
                                 clearance="INTERNAL"))
        session.add(db.IdentityFact(principal_id=999, principal_name="officer",
                                    display_name="officer", principal_kind="HUMAN",
                                    role_snapshot="GOVERNANCE_OFFICER",
                                    authentication_method="PASSWORD",
                                    credential_fingerprint="cred_x:000000000000"))
        session.commit()
        identity.migrate_legacy_roles(session)
        roles = {p.name: p.role for p in session.query(db.Principal).all()}
        assert roles["officer"] == "GOVERNANCE_REVIEWER" and roles["rev"] == "GOVERNANCE_REVIEWER"
        assert roles["vw"] == "READ_ONLY"
        assert roles["old-agent"] == "AGENT_CONSUMER", "role-less agents gain AGENT_CONSUMER"
        fact = session.query(db.IdentityFact).filter_by(principal_name="officer").first()
        assert fact.role_snapshot == "GOVERNANCE_OFFICER", \
            "role_snapshot is evidence - vocabulary migration must NEVER touch it"
        mig = session.query(db.AuditEvent).filter_by(event_type="ROLE_VOCABULARY_MIGRATED").order_by(
            db.AuditEvent.id.desc()).first()
        changes = json.loads(mig.details)["changes"]
        assert {c["principal"] for c in changes} == {"officer", "rev", "vw", "old-agent"}
    print("Part 3 passed: registry renamed and audited; the historical snapshot still")
    print("               says GOVERNANCE_OFFICER - history is not revisionist.")

    # Part 4: DELEGATED backfill + full idempotency.
    print("\n--- Part 4: Delegated backfill; the whole sequence is idempotent ---")
    with db.SessionLocal() as session:
        for name in ("policy:Legacy low-risk docs", "connector:Legacy Share"):
            p = identity.get_principal(session, name)
            assert p is not None and p.kind == "DELEGATED", f"missing backfill: {name}"
        before = {
            "principals": session.query(db.Principal).count(),
            "credentials": session.query(db.Credential).count(),
            "facts": session.query(db.IdentityFact).count(),
        }
    admin2, one_time2, findings2 = run_startup_sequence()
    assert admin2 is None and one_time2 is None, "bootstrap must be a one-time event"
    assert findings2 == [], f"re-running startup must stay clean: {findings2}"
    with db.SessionLocal() as session:
        after = {
            "principals": session.query(db.Principal).count(),
            "credentials": session.query(db.Credential).count(),
            "facts": session.query(db.IdentityFact).count(),
        }
    assert before == after, f"startup must be idempotent: {before} != {after}"
    print("Part 4 passed: delegated principals backfilled once; second startup is a no-op.")

    # Part 5: validation REPORTS anomalies (and authorization fails closed).
    print("\n--- Part 5: Boundary validation reports anomalies loudly ---")
    with db.SessionLocal() as session:
        session.add(db.Principal(name="weird", display_name="weird", kind="HUMAN", role="WIZARD"))
        session.commit()
        findings = identity.validate_boundary(session)
        assert any("weird" in f and "WIZARD" in f for f in findings), findings
        weird = identity.get_principal(session, "weird")
        assert not identity.is_authorized(weird, "assets:read"), \
            "unknown roles authorize NOTHING - fail closed"
        ev = session.query(db.AuditEvent).filter_by(event_type="BOUNDARY_VALIDATION").order_by(
            db.AuditEvent.id.desc()).first()
        assert json.loads(ev.details)["ok"] is False
    print("Part 5 passed: anomaly detected, audited, and powerless.")

    print("\nAll migration checks passed.")


if __name__ == "__main__":
    main()
