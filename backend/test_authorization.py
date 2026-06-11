import os
import sys
import json
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"

# WS3 acceptance suite: token/session identity is trusted but POWERLESS
# until authorized. Authenticated principals can only perform explicitly
# authorized actions; the matrix is small, code-resident, and enforced at
# the route boundary; every denial (and every non-read grant) is audited
# with the actor's identity fact.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

_tmpdir = tempfile.mkdtemp(prefix="em_authz_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'authz.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_authz_qdrant_")

from fastapi.testclient import TestClient
from app import main
from app import identity

DOC_TEXT = (
    "The platform runs on a PostgreSQL database server cluster.\n"
    "All operators must complete safety training before access is granted.\n"
)


def _login(client, name, password):
    r = client.post("/api/auth/login", json={"name": name, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def main_test():
    print("\nStarting WS3 authorization checks over HTTP...")
    with TestClient(main.app) as client:

        with db.SessionLocal() as boot:
            for name, role in [("boss", "ADMIN"), ("greta", "GOVERNANCE_REVIEWER"),
                               ("kai", "KNOWLEDGE_OPERATOR"), ("alice", "READ_ONLY")]:
                p = identity.create_principal(boot, name=name, display_name=name.capitalize(),
                                              kind="HUMAN", role=role, created_by="test-suite")
                identity.set_password(boot, p, f"{name}-password-123", actor=name)
        ADMIN = _login(client, "boss", "boss-password-123")
        REVIEWER = _login(client, "greta", "greta-password-123")
        OPERATOR = _login(client, "kai", "kai-password-123")
        ALICE = _login(client, "alice", "alice-password-123")

        # seed: admin creates a project; operator ingests a document
        r = client.post("/api/projects", json={"name": "AuthZ", "description": "", "customer_id": 1},
                        headers=ADMIN)
        project_id = r.json()["id"]
        r = client.post(f"/api/projects/{project_id}/documents",
                        files={"file": ("authz.txt", DOC_TEXT.encode(), "text/plain")},
                        headers=OPERATOR)
        assert r.status_code == 200, f"KNOWLEDGE_OPERATOR must be able to ingest: {r.text}"
        assets = client.get(f"/api/projects/{project_id}/assets", headers=ALICE).json()
        assert assets, "READ_ONLY must be able to read assets"
        asset_id = assets[0]["id"]

        # Part 1: the role grid - each role holds exactly its permissions.
        print("\n--- Part 1: Role grid enforced at the boundary ---")
        # READ_ONLY: reads only - no review, no approval, no ingest, no audit
        for method, url, body in [
                ("PATCH", f"/api/assets/{asset_id}", {"status": "REVIEWED"}),
                ("PATCH", f"/api/assets/{asset_id}", {"status": "APPROVED"}),
                ("POST", f"/api/projects/{project_id}/extract", None),
                ("DELETE", f"/api/knowledge-assets/{asset_id}", None),
                ("GET", "/api/audit", None),
                ("GET", "/api/settings/llm", None),
                ("GET", "/api/identity/principals", None)]:
            r = client.request(method, url, json=body, headers=ALICE)
            assert r.status_code == 403, f"READ_ONLY {method} {url} must 403: {r.status_code}"
        # KNOWLEDGE_OPERATOR: ingest yes, governance no
        r = client.patch(f"/api/assets/{asset_id}", json={"status": "REVIEWED"}, headers=OPERATOR)
        assert r.status_code == 403, "KNOWLEDGE_OPERATOR must not review"
        r = client.get("/api/audit", headers=OPERATOR)
        assert r.status_code == 403, "KNOWLEDGE_OPERATOR lacks audit:read"
        # GOVERNANCE_REVIEWER: governance yes, ingest/delete/settings no
        r = client.post(f"/api/projects/{project_id}/documents",
                        files={"file": ("nope.txt", b"x", "text/plain")}, headers=REVIEWER)
        assert r.status_code == 403, "GOVERNANCE_REVIEWER must not ingest"
        r = client.delete(f"/api/knowledge-assets/{asset_id}", headers=REVIEWER)
        assert r.status_code == 403, "GOVERNANCE_REVIEWER must not delete"
        r = client.get("/api/settings/llm", headers=REVIEWER)
        assert r.status_code == 403, "settings are ADMIN-only"
        r = client.get("/api/audit", headers=REVIEWER)
        assert r.status_code == 200, "GOVERNANCE_REVIEWER holds audit:read"
        print("Part 1 passed: READ_ONLY/KNOWLEDGE_OPERATOR/GOVERNANCE_REVIEWER each hold")
        print("               exactly their grid row; nothing more.")

        # Part 2: status-dependent asset permission (review vs approve).
        print("\n--- Part 2: Transition-dependent permissions ---")
        r = client.patch(f"/api/assets/{asset_id}", json={"status": "REVIEWED"}, headers=REVIEWER)
        assert r.status_code == 200, r.text
        r = client.patch(f"/api/assets/{asset_id}", json={"status": "APPROVED"}, headers=REVIEWER)
        assert r.status_code == 200, "GOVERNANCE_REVIEWER holds assets:approve"
        print("Part 2 passed: REVIEWED and APPROVED transitions resolve to their permissions.")

        # Part 3: both identity AND the authorization decision are audited.
        print("\n--- Part 3: Authorization decisions are audit evidence ---")
        with db.SessionLocal() as check:
            denied = check.query(db.AuditEvent).filter_by(event_type="AUTHZ_DENIED").all()
            assert denied, "Denials must be audited"
            for e in denied:
                d = json.loads(e.details)
                assert d["permission"] and d["role"] is not None and e.identity_fact_id is not None
            granted = check.query(db.AuditEvent).filter_by(event_type="AUTHZ_GRANTED").all()
            assert granted, "Non-read grants must be audited"
            sample = json.loads(granted[-1].details)
            assert sample["permission"] not in ("assets:read", "audit:read"), \
                "read grants are deliberately not audited (declared rule)"
        print(f"Part 3 passed: {len(denied)} denials and {len(granted)} write grants on the ledger,")
        print("               each carrying permission, role, and the actor's identity fact.")

        # Part 4: the Alice least-privilege story, end to end.
        print("\n--- Part 4: Alice - least privilege, honest history ---")
        # Alice (READ_ONLY) tries to approve - denied; the denial fact
        # records the role she held AT THE ATTEMPT.
        candidates = [a for a in client.get(f"/api/projects/{project_id}/assets",
                                            headers=ALICE).json() if a["status"] == "CANDIDATE"]
        target = candidates[0]["id"] if candidates else asset_id
        r = client.patch(f"/api/assets/{target}", json={"status": "APPROVED"}, headers=ALICE)
        assert r.status_code == 403
        with db.SessionLocal() as check:
            denial = check.query(db.AuditEvent).filter_by(event_type="AUTHZ_DENIED").order_by(
                db.AuditEvent.id.desc()).first()
            denial_fact = check.query(db.IdentityFact).filter_by(id=denial.identity_fact_id).first()
            assert denial_fact.principal_name == "alice" and denial_fact.role_snapshot == "READ_ONLY"
        # The admin promotes her (governed, audited); she approves; the
        # approval fact records the NEW role; the old denial keeps the old.
        r = client.patch("/api/identity/principals/alice", json={"role": "GOVERNANCE_REVIEWER"},
                         headers=ADMIN)
        assert r.status_code == 200 and r.json()["role"] == "GOVERNANCE_REVIEWER"
        r = client.patch(f"/api/assets/{target}", json={"status": "APPROVED"}, headers=ALICE)
        assert r.status_code == 200, f"Promotion must take effect on the live session: {r.text}"
        with db.SessionLocal() as check:
            approval = check.query(db.AuditEvent).filter_by(event_type="ASSET_APPROVED").order_by(
                db.AuditEvent.id.desc()).first()
            approval_fact = check.query(db.IdentityFact).filter_by(id=approval.identity_fact_id).first()
            assert approval_fact.principal_name == "alice"
            assert approval_fact.role_snapshot == "GOVERNANCE_REVIEWER"
            old_denial_fact = check.query(db.IdentityFact).filter_by(id=denial.identity_fact_id).first()
            assert old_denial_fact.role_snapshot == "READ_ONLY", \
                "history is never rewritten: the denial keeps the role that was true then"
            update_ev = check.query(db.AuditEvent).filter_by(event_type="PRINCIPAL_UPDATED").order_by(
                db.AuditEvent.id.desc()).first()
            assert json.loads(update_ev.details)["changes"]["role"] == {
                "old": "READ_ONLY", "new": "GOVERNANCE_REVIEWER"}
        print("Part 4 passed: denied as READ_ONLY (fact says so forever), promoted by the")
        print("               admin (audited old->new), approved as GOVERNANCE_REVIEWER.")

        # Part 5: administration guard rails.
        print("\n--- Part 5: Admin guard rails ---")
        r = client.patch("/api/identity/principals/boss", json={"role": "READ_ONLY"}, headers=ADMIN)
        assert r.status_code == 400, "Admins cannot change their own role (escalation/lockout guard)"
        r = client.patch("/api/identity/principals/boss", json={"active": False}, headers=ADMIN)
        assert r.status_code == 400, "Admins cannot deactivate themselves"
        r = client.post("/api/identity/principals/alice/reset-password", headers=ADMIN)
        assert r.status_code == 200 and r.json()["one_time_password"]
        r = client.patch(f"/api/assets/{asset_id}", json={"status": "REVIEWED"}, headers=ALICE)
        assert r.status_code == 401, "Password reset revokes live sessions"
        r = client.patch("/api/identity/principals/greta", json={"active": False}, headers=ADMIN)
        assert r.status_code == 200
        r = client.get("/api/projects", headers=REVIEWER)
        assert r.status_code == 401, "Deactivation kills live sessions immediately"
        print("Part 5 passed: self-demotion/self-deactivation refused; reset and deactivation")
        print("               fail live sessions closed.")

        # Part 6: READ_AUDIT_MODE (WS4 architecture hook). OFF by default -
        # the D19 invariant: absent configuration changes nothing. FULL
        # audits read grants for the enterprise "who VIEWED this?" question.
        print("\n--- Part 6: READ_AUDIT_MODE (OFF default, FULL opt-in) ---")
        def read_grant_count():
            with db.SessionLocal() as check:
                return check.query(db.AuditEvent).filter(
                    db.AuditEvent.event_type == "AUTHZ_GRANTED",
                    db.AuditEvent.details.like('%assets:read%')).count()
        baseline = read_grant_count()
        r = client.get(f"/api/projects/{project_id}/assets", headers=ADMIN)
        assert r.status_code == 200
        assert read_grant_count() == baseline, "OFF (default): read grants stay unaudited"
        os.environ["EM_READ_AUDIT_MODE"] = "FULL"
        r = client.get(f"/api/projects/{project_id}/assets", headers=ADMIN)
        assert r.status_code == 200
        assert read_grant_count() == baseline + 1, "FULL: every read grant audited"
        with db.SessionLocal() as check:
            ev = check.query(db.AuditEvent).filter(
                db.AuditEvent.event_type == "AUTHZ_GRANTED",
                db.AuditEvent.details.like('%assets:read%')).order_by(
                db.AuditEvent.id.desc()).first()
            d = json.loads(ev.details)
            assert d["read_audit"]["mode"] == "FULL" and ev.identity_fact_id is not None
        os.environ["EM_READ_AUDIT_MODE"] = "SAMPLED"
        for _ in range(3):
            client.get(f"/api/projects/{project_id}/assets", headers=ADMIN)
        sampled = read_grant_count()
        assert baseline + 1 <= sampled <= baseline + 2, \
            "SAMPLED: roughly 1-in-N, each event declaring its sample rate (D12)"
        os.environ.pop("EM_READ_AUDIT_MODE", None)
        print("Part 6 passed: OFF default preserves behavior; FULL and SAMPLED audit read")
        print("               grants with the mode declared on each event.")

    print("\nAll WS3 authorization checks passed.")


if __name__ == "__main__":
    main_test()
