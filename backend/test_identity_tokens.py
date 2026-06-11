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
                                                 kind="HUMAN", role="GOVERNANCE_REVIEWER", created_by="test-suite")
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
                        json={"name": "ci-pipeline", "kind": "SERVICE", "role": "KNOWLEDGE_OPERATOR"},
                        headers=ADMIN)
        assert r.status_code == 200 and r.json()["clearance"] is None, r.text
        assert r.json()["role"] == "KNOWLEDGE_OPERATOR"
        r = client.post("/api/identity/principals",
                        json={"name": "ro-service", "kind": "SERVICE"}, headers=ADMIN)
        assert r.status_code == 200 and r.json()["role"] == "READ_ONLY", \
            "SERVICE defaults to least privilege, never a quiet super-user"
        r = client.post("/api/identity/principals",
                        json={"name": "claude-desktop-rk", "kind": "AGENT"}, headers=ADMIN)
        assert r.status_code == 400, "Duplicate principal must 400 (never deleted, so never reused)"
        r = client.post("/api/identity/principals",
                        json={"name": "eve", "kind": "HUMAN", "role": "GOVERNANCE_REVIEWER"},
                        headers=ADMIN)
        assert r.status_code == 200, r.text
        eve = r.json()
        assert eve["one_time_password"], "HUMAN creation returns a one-time password exactly once"
        r = client.post("/api/auth/login", json={"name": "eve", "password": eve["one_time_password"]})
        assert r.status_code == 200 and r.json()["must_change_password"] is True
        r = client.post("/api/identity/principals",
                        json={"name": "rogue-svc", "kind": "SERVICE", "role": "ADMIN"}, headers=ADMIN)
        assert r.status_code == 400, "SERVICE may never hold ADMIN (quiet super-user guard)"
        r = client.post("/api/identity/principals",
                        json={"name": "svc2", "kind": "SERVICE", "clearance": "EXECUTIVE"}, headers=ADMIN)
        assert r.status_code == 400, "clearance is an AGENT concept"
        r = client.get("/api/identity/principals", headers=ADMIN)
        names = {p["name"] for p in r.json()}
        assert {"root", "reviewer", "claude-desktop-rk", "ci-pipeline", "ro-service", "eve"} <= names
        print("Part 1 passed: AGENT/SERVICE/HUMAN created (one-time password, least-privilege")
        print("               defaults); duplicates, SERVICE-ADMIN, and stray clearance refused.")

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

        # Part 4: the REST/gateway split + WS3 role scoping - AGENT tokens
        # are gateway-only; SERVICE tokens hold exactly their role's
        # permissions, never a quiet super-user.
        print("\n--- Part 4: AGENT tokens MCP-only; SERVICE tokens scoped by role ---")
        r = client.post("/api/projects", json={"name": "T", "description": "", "customer_id": 1},
                        headers={"Authorization": f"Bearer {agent_token}"})
        assert r.status_code == 403 and "MCP gateway" in r.json()["detail"], r.text
        r = client.post("/api/projects", json={"name": "Service Project", "description": "", "customer_id": 1},
                        headers={"Authorization": f"Bearer {service_token}"})
        assert r.status_code == 200, f"KNOWLEDGE_OPERATOR service holds documents:ingest: {r.text}"
        with db.SessionLocal() as check:
            ev = check.query(db.AuditEvent).filter_by(event_type="PROJECT_CREATED").order_by(
                db.AuditEvent.id.desc()).first()
            fact = check.query(db.IdentityFact).filter_by(id=ev.identity_fact_id).first()
            assert fact.principal_kind == "SERVICE" and fact.authentication_method == "API_TOKEN"
            assert fact.role_snapshot == "KNOWLEDGE_OPERATOR"
        # the same service may NOT approve or manage identity (role-scoped)
        r = client.post("/api/identity/tokens", json={"principal_name": "ro-service"},
                        headers={"Authorization": f"Bearer {service_token}"})
        assert r.status_code == 403, "KNOWLEDGE_OPERATOR lacks tokens:manage"
        # a READ_ONLY service cannot ingest - no quiet super-user category
        r = client.post("/api/identity/tokens", json={"principal_name": "ro-service"}, headers=ADMIN)
        ro_token = r.json()["token"]
        r = client.post("/api/projects", json={"name": "Nope", "description": "", "customer_id": 1},
                        headers={"Authorization": f"Bearer {ro_token}"})
        assert r.status_code == 403, "READ_ONLY service must not ingest"
        r = client.get("/api/projects", headers={"Authorization": f"Bearer {ro_token}"})
        assert r.status_code == 200, "READ_ONLY service may read"
        with db.SessionLocal() as check:
            denied = check.query(db.AuditEvent).filter_by(event_type="AUTHZ_DENIED").order_by(
                db.AuditEvent.id.desc()).first()
            assert denied is not None and denied.identity_fact_id is not None
            d = json.loads(denied.details)
            assert d["permission"] == "documents:ingest" and d["role"] == "READ_ONLY"
        print("Part 4 passed: AGENT 403s on REST; SERVICE scoped to its role's permissions;")
        print("               denial audited with permission, role, and identity fact.")

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

        # Part 6: forced rotation flow (live bug, June 2026): a WRONG current
        # password must be a 400 field error - the session stays alive - and
        # never a 401 that the frontend's session-expiry handler turns into
        # a logout. A correct rotation kills the old password.
        print("\n--- Part 6: change-password - wrong current is a field error, not a logout ---")
        r = client.post("/api/auth/login", json={"name": "eve", "password": eve["one_time_password"]})
        EVE = {"Authorization": f"Bearer {r.json()['token']}"}
        r = client.post("/api/auth/change-password",
                        json={"current_password": "eve-NEW-password-99",
                              "new_password": "eve-NEW-password-99"},  # the new-pw-typed-twice mistake
                        headers=EVE)
        assert r.status_code == 400, f"Wrong current password must be 400, got {r.status_code}"
        r = client.get("/api/auth/me", headers=EVE)
        assert r.status_code == 200, "The session must SURVIVE a wrong current password"
        assert r.json()["must_change_password"] is True, "Rotation must not have happened"
        r = client.post("/api/auth/change-password",
                        json={"current_password": eve["one_time_password"],
                              "new_password": "eve-NEW-password-99"},
                        headers=EVE)
        assert r.status_code == 200 and r.json()["must_change_password"] is False, r.text
        r = client.get("/api/auth/me", headers=EVE)
        assert r.status_code == 200, "The session survives a successful rotation too"
        r = client.post("/api/auth/login", json={"name": "eve", "password": eve["one_time_password"]})
        assert r.status_code == 401, "The one-time password must be dead after rotation"
        r = client.post("/api/auth/login", json={"name": "eve", "password": "eve-NEW-password-99"})
        assert r.status_code == 200, "The new password must work"
        print("Part 6 passed: wrong current -> 400 + session intact; rotation kills the")
        print("               one-time password and the session stays signed in.")

    print("\nAll identity administration checks passed.")


if __name__ == "__main__":
    main_test()
