import os
import sys
import json
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"

# Identity administration suite (v1.0 WS2b): AGENT/SERVICE principals and
# API tokens over HTTP. The contracts under test: ADMIN-only administration,
# plaintext shown exactly once, fingerprints (never hashes) in listings,
# revoke-not-delete, and the REST/gateway split for AGENT tokens.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

_tmpdir = tempfile.mkdtemp(prefix="em_tokens_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'tokens.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from fastapi.testclient import TestClient
from app import main
from app import identity


def main_test():
    print("\nStarting identity administration checks over HTTP...")
    with TestClient(main.app) as client:

        with db.SessionLocal() as boot:
            admin = identity.create_principal(boot, name="root", display_name="Root Admin",
                                              kind="HUMAN", role="ADMIN", created_by="test-suite")
            identity.set_password(boot, admin, "root-password-123", actor="root")
            reviewer = identity.create_principal(boot, name="reviewer", display_name="Reviewer",
                                                 kind="HUMAN", role="REVIEWER", created_by="test-suite")
            identity.set_password(boot, reviewer, "reviewer-password-123", actor="reviewer")
        ADMIN = {"Authorization": "Bearer " + client.post(
            "/api/auth/login", json={"name": "root", "password": "root-password-123"}).json()["token"]}
        REVIEWER = {"Authorization": "Bearer " + client.post(
            "/api/auth/login", json={"name": "reviewer", "password": "reviewer-password-123"}).json()["token"]}

        # Part 1: ADMIN creates AGENT/SERVICE principals; invalid kinds refused.
        print("\n--- Part 1: Principal administration (ADMIN only, AGENT/SERVICE only) ---")
        r = client.post("/api/identity/principals",
                        json={"name": "claude-desktop-rk", "kind": "AGENT", "clearance": "INTERNAL"},
                        headers=ADMIN)
        assert r.status_code == 200, r.text
        assert r.json()["kind"] == "AGENT" and r.json()["clearance"] == "INTERNAL"
        r = client.post("/api/identity/principals",
                        json={"name": "ci-pipeline", "kind": "SERVICE"}, headers=ADMIN)
        assert r.status_code == 200 and r.json()["clearance"] is None, r.text
        r = client.post("/api/identity/principals",
                        json={"name": "claude-desktop-rk", "kind": "AGENT"}, headers=ADMIN)
        assert r.status_code == 400, "Duplicate principal must 400 (never deleted, so never reused)"
        r = client.post("/api/identity/principals",
                        json={"name": "eve", "kind": "HUMAN"}, headers=ADMIN)
        assert r.status_code == 400, "HUMAN administration arrives with WS3"
        r = client.post("/api/identity/principals",
                        json={"name": "svc2", "kind": "SERVICE", "clearance": "EXECUTIVE"}, headers=ADMIN)
        assert r.status_code == 400, "clearance is an AGENT concept"
        r = client.get("/api/identity/principals", headers=ADMIN)
        names = {p["name"] for p in r.json()}
        assert {"root", "reviewer", "claude-desktop-rk", "ci-pipeline"} <= names
        print("Part 1 passed: AGENT/SERVICE created; duplicates, HUMAN kind, and stray clearance refused.")

        # Part 2: token issuance - plaintext exactly once, fingerprint thereafter.
        print("\n--- Part 2: Token issuance (plaintext once, hashes never) ---")
        r = client.post("/api/identity/tokens",
                        json={"principal_name": "claude-desktop-rk", "label": "desktop", "expires_days": 90},
                        headers=ADMIN)
        assert r.status_code == 200, r.text
        issued = r.json()
        assert issued["token"].startswith("emk_") and issued["fingerprint"].startswith("cred_")
        assert issued["expires_at"] is not None
        agent_token = issued["token"]
        r = client.post("/api/identity/tokens",
                        json={"principal_name": "ci-pipeline", "label": "ci"}, headers=ADMIN)
        assert r.status_code == 200
        service_token = r.json()["token"]
        r = client.post("/api/identity/tokens", json={"principal_name": "root"}, headers=ADMIN)
        assert r.status_code == 400, "HUMAN principals authenticate with passwords/sessions"
        r = client.post("/api/identity/tokens", json={"principal_name": "ghost"}, headers=ADMIN)
        assert r.status_code == 404
        r = client.get("/api/identity/tokens", headers=ADMIN)
        listing = r.json()
        assert all(set(t) >= {"fingerprint", "principal_name", "label"} for t in listing)
        listing_text = json.dumps(listing)
        assert agent_token not in listing_text and service_token not in listing_text, \
            "Plaintext must never appear after issuance"
        assert "secret_hash" not in listing_text, "Hashes never leave the store"
        print("Part 2 passed: emk_ plaintext returned once; listings carry fingerprints only.")

        # Part 3: ADMIN-only - a REVIEWER is refused everywhere.
        print("\n--- Part 3: Identity administration requires ADMIN ---")
        for method, url, body in [
                ("GET", "/api/identity/principals", None),
                ("POST", "/api/identity/principals", {"name": "x", "kind": "AGENT"}),
                ("GET", "/api/identity/tokens", None),
                ("POST", "/api/identity/tokens", {"principal_name": "ci-pipeline"})]:
            r = client.request(method, url, json=body, headers=REVIEWER)
            assert r.status_code == 403, f"{method} {url} must 403 for non-admin: {r.status_code}"
        print("Part 3 passed: all four admin endpoints 403 for a REVIEWER.")

        # Part 4: the REST/gateway split - AGENT tokens are gateway-only;
        # SERVICE tokens act on REST like operators (role matrix is WS3).
        print("\n--- Part 4: AGENT tokens are MCP-only on the REST surface ---")
        r = client.post("/api/projects", json={"name": "T", "description": "", "customer_id": 1},
                        headers={"Authorization": f"Bearer {agent_token}"})
        assert r.status_code == 403 and "MCP gateway" in r.json()["detail"], r.text
        r = client.post("/api/projects", json={"name": "Service Project", "description": "", "customer_id": 1},
                        headers={"Authorization": f"Bearer {service_token}"})
        assert r.status_code == 200, f"SERVICE tokens act on REST until WS3 scopes them: {r.text}"
        with db.SessionLocal() as check:
            ev = check.query(db.AuditEvent).filter_by(event_type="PROJECT_CREATED").order_by(
                db.AuditEvent.id.desc()).first()
            fact = check.query(db.IdentityFact).filter_by(id=ev.identity_fact_id).first()
            assert fact.principal_kind == "SERVICE" and fact.authentication_method == "API_TOKEN"
        print("Part 4 passed: AGENT token 403s on REST; SERVICE write recorded with an API_TOKEN fact.")

        # Part 5: revocation over HTTP - lineage kept, token dead, all audited.
        print("\n--- Part 5: Revocation (revoke-not-delete, audited with facts) ---")
        fingerprint = issued["fingerprint"]
        r = client.post(f"/api/identity/tokens/{fingerprint}/revoke", headers=ADMIN)
        assert r.status_code == 200 and r.json()["revoked_at"] is not None
        r = client.get("/api/identity/tokens", headers=ADMIN)
        row = next(t for t in r.json() if t["fingerprint"] == fingerprint)
        assert row["revoked_at"] is not None, "Revoked tokens stay listed - lineage, not deletion"
        with db.SessionLocal() as check:
            p, c = identity.resolve_token(check, agent_token)
            assert p is None, "Revoked token must fail closed"
            for et in ("CREDENTIAL_CREATED", "CREDENTIAL_REVOKED", "PRINCIPAL_CREATED"):
                ev = check.query(db.AuditEvent).filter_by(event_type=et).order_by(
                    db.AuditEvent.id.desc()).first()
                assert ev is not None, f"missing {et}"
            revoked_ev = check.query(db.AuditEvent).filter_by(event_type="CREDENTIAL_REVOKED").order_by(
                db.AuditEvent.id.desc()).first()
            assert revoked_ev.identity_fact_id is not None, "Admin revocation carries the admin's fact"
            fact = check.query(db.IdentityFact).filter_by(id=revoked_ev.identity_fact_id).first()
            assert fact.principal_name == "root" and fact.role_snapshot == "ADMIN"
        r = client.post(f"/api/identity/tokens/{fingerprint}/revoke", headers=ADMIN)
        assert r.status_code == 200, "Re-revoking is idempotent"
        print("Part 5 passed: revoked token fails closed, stays in lineage, and the")
        print("               revocation fact answers who/role at action time.")

    print("\nAll identity administration checks passed.")


if __name__ == "__main__":
    main_test()
