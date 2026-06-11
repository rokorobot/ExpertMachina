import datetime
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import crud
from app import identity

# Identity Boundary v1.0 product suite - the Alice test
# (docs/identity-boundary-v1.md). The acceptance question: six months
# after Alice approved asset 42 - after renames, role changes, password
# rotation, deactivation - can the system still prove who Alice WAS,
# what role she held at that moment, and which credential authenticated
# her? If any assertion here needs today's principal row to answer a
# historical question, the boundary has failed.


def main():
    print("\nInitializing test database for Identity Boundary checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = TestingSessionLocal
    session = TestingSessionLocal()
    crud.get_or_create_default_customer(session)

    # Part 1: bootstrap - SYSTEM principals seeded, admin created once.
    print("\n--- Part 1: Bootstrap (system principals + one-time admin) ---")
    identity.ensure_system_principals(session)
    for name in identity.SYSTEM_PRINCIPAL_NAMES:
        p = identity.get_principal(session, name)
        assert p is not None and p.kind == "SYSTEM" and p.role is None, name
    identity.ensure_system_principals(session)  # idempotent
    assert session.query(db.Principal).filter_by(kind="SYSTEM").count() == len(identity.SYSTEM_PRINCIPAL_NAMES)
    admin, one_time = identity.bootstrap_admin(session)
    assert admin is not None and one_time is not None and admin.must_change_password
    again, none_pw = identity.bootstrap_admin(session)
    assert again is None and none_pw is None, "bootstrap must be a one-time event"
    token, who = identity.authenticate_password(session, "admin", one_time)
    assert token is not None and who.id == admin.id, "one-time password must authenticate"
    print("Part 1 passed: system principals seeded, admin bootstrapped exactly once.")

    # Part 2: the Alice test - facts survive every later mutation.
    print("\n--- Part 2: The Alice test (evidence survives principal mutation) ---")
    alice = identity.create_principal(session, name="alice", display_name="Alice Novak",
                                      kind="HUMAN", role="GOVERNANCE_OFFICER", created_by="admin")
    identity.set_password(session, alice, "correct horse battery staple", actor="alice")
    alice_token, _ = identity.authenticate_password(session, "alice", "correct horse battery staple")
    assert alice_token is not None
    principal, cred = identity.resolve_token(session, alice_token)
    assert principal.id == alice.id and cred.kind == "SESSION"
    fact = identity.mint_fact(session, principal, method="PASSWORD",
                              credential=cred)
    # the governed write: approval evidence lands on the landing pads
    event = crud.log_audit_event(session, actor=principal.display_name,
                                 event_type="ASSET_APPROVED", target_id="42",
                                 details='{"test": "alice approves asset 42"}',
                                 identity_fact_id=fact.id)
    review = db.AssetReview(asset_id=42, approver=principal.display_name,
                            identity_fact_id=fact.id)
    session.add(review)
    session.commit()
    session_fingerprint = cred.fingerprint

    # six months pass: everything about Alice changes
    alice.display_name = "Alice Svoboda"      # married name
    alice.role = "VIEWER"                      # demoted
    session.commit()
    identity.set_password(session, alice, "new password entirely", actor="alice")  # rotation
    alice.active = False                       # offboarded
    session.commit()

    # the historical question, answered from evidence alone
    recorded = session.query(db.IdentityFact).filter_by(id=event.identity_fact_id).first()
    assert recorded.display_name == "Alice Novak", "name AT ACTION TIME, not today's"
    assert recorded.role_snapshot == "GOVERNANCE_OFFICER", "role AT ACTION TIME, not today's"
    assert recorded.authentication_method == "PASSWORD"
    assert recorded.credential_fingerprint == session_fingerprint, "which credential, provably"
    assert recorded.principal_kind == "HUMAN"
    linked_review = session.query(db.AssetReview).filter_by(asset_id=42).first()
    assert linked_review.identity_fact_id == recorded.id, "review carries the same evidence"
    print("Part 2 passed: who/role/method/credential all answer at action time after rename,")
    print("               demotion, rotation, and deactivation.")

    # Part 3: credential lineage - rotation revokes, sessions trace, closed fails closed.
    print("\n--- Part 3: Credential lineage (revoke-never-delete, fail closed) ---")
    password_creds = session.query(db.Credential).filter_by(
        principal_id=alice.id, kind="PASSWORD").order_by(db.Credential.id).all()
    assert len(password_creds) == 2, "rotation creates lineage, never replaces"
    assert password_creds[0].revoked_at is not None and password_creds[1].revoked_at is None
    session_cred = session.query(db.Credential).filter_by(fingerprint=session_fingerprint).first()
    assert session_cred.issued_by_credential_id == password_creds[0].id, \
        "the session records WHICH password generation authenticated it"
    p, c = identity.resolve_token(session, alice_token)
    assert p is None and c is None, "deactivated principal fails closed"
    revoked_events = session.query(db.AuditEvent).filter_by(event_type="CREDENTIAL_REVOKED").all()
    assert any(json.loads(e.details)["reason"] == "rotated" for e in revoked_events)
    print("Part 3 passed: lineage intact, session traces to password generation,")
    print("               deactivated principals fail closed.")

    # Part 4: structural purity - the design-review watchpoint as CI.
    print("\n--- Part 4: Structural purity (IdentityFact stays an identity fact) ---")
    identity_vocabulary = {
        "id", "principal_id", "principal_name", "display_name", "principal_kind",
        "role_snapshot", "authentication_method", "credential_fingerprint",
        "on_behalf_of_fact_id", "created_at",
    }
    actual = {col.name for col in db.IdentityFact.__table__.columns}
    assert actual == identity_vocabulary, (
        "IdentityFact column creep detected: "
        f"{actual ^ identity_vocabulary}. "
        "Request-context responsibilities belong on a RequestFact, never here "
        "(design review ruling, docs/identity-boundary-v1.md).")
    fact_cols = actual
    assert not {"status", "reviewer", "reviewed_at"} & fact_cols, "facts are never workflow objects (D3)"
    credential_cols = {col.name for col in db.Credential.__table__.columns}
    assert "secret_hash" in credential_cols
    assert not {"secret", "token", "password", "plaintext"} & credential_cols, \
        "credentials store hashes only - hashes verify, they don't reveal (D19)"
    print("Part 4 passed: fact column set is exactly the identity vocabulary;")
    print("               no plaintext-shaped column exists on credentials.")

    # Part 5: boundary refusals - proposals that must not become actors.
    print("\n--- Part 5: Boundary refusals ---")
    bad_token, bad_who = identity.authenticate_password(session, "alice", "wrong password")
    assert bad_token is None and bad_who is None
    ghost_token, ghost = identity.authenticate_password(session, "mallory", "anything")
    assert ghost_token is None and ghost is None
    failures = session.query(db.AuditEvent).filter_by(event_type="LOGIN_FAILED").all()
    assert len(failures) >= 2
    assert all(e.actor == "identity_boundary" for e in failures), \
        "a failed proposal is recorded as a proposal, never as an actor"
    assert any(json.loads(e.details)["proposed_name"] == "mallory" for e in failures)
    p, c = identity.resolve_token(session, "emk_completely-made-up")
    assert p is None and c is None
    bob = identity.create_principal(session, name="bob", display_name="Bob", kind="HUMAN",
                                    role="REVIEWER", created_by="admin")
    expired_plain, expired_cred = identity.issue_token(
        session, bob, kind="API_TOKEN", label="expired",
        expires_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=1))
    p, c = identity.resolve_token(session, expired_plain)
    assert p is None and c is None, "expired tokens fail closed"
    live_plain, live_cred = identity.issue_token(session, bob, kind="API_TOKEN", label="live")
    identity.revoke_credential(session, live_cred, actor="admin", reason="compromised")
    p, c = identity.resolve_token(session, live_plain)
    assert p is None and c is None, "revoked tokens fail closed"
    try:
        identity.mint_fact(session, bob, method="PASSWORD", credential=None)
        raise AssertionError("authenticated methods must record their credential")
    except ValueError:
        pass
    print("Part 5 passed: bad logins, unknown names, garbage/expired/revoked tokens")
    print("               all refused; refusals audited as proposals.")

    # Part 6: delegated chains - identity delegation only, auto-registered.
    print("\n--- Part 6: DELEGATED chains (on_behalf_of carries WHO, not WHY) ---")
    carol = identity.create_principal(session, name="carol", display_name="Carol",
                                      kind="HUMAN", role="GOVERNANCE_OFFICER", created_by="admin")
    identity.set_password(session, carol, "carols password here", actor="carol")
    carol_token, _ = identity.authenticate_password(session, "carol", "carols password here")
    carol_p, carol_c = identity.resolve_token(session, carol_token)
    carol_fact = identity.mint_fact(session, carol_p, method="PASSWORD", credential=carol_c)
    connector_fact = identity.delegated_fact(session, "connector:HR-Share",
                                             on_behalf_of=carol_fact)
    policy_fact = identity.delegated_fact(session, "policy:Low-risk docs",
                                          on_behalf_of=connector_fact)
    assert connector_fact.authentication_method == "DELEGATED"
    assert connector_fact.credential_fingerprint is None, "no fabricated lineage (D12)"
    assert connector_fact.on_behalf_of_fact_id == carol_fact.id
    assert policy_fact.on_behalf_of_fact_id == connector_fact.id
    chain = []
    cursor = policy_fact
    while cursor is not None:
        chain.append(cursor.principal_name)
        cursor = (session.query(db.IdentityFact).filter_by(id=cursor.on_behalf_of_fact_id).first()
                  if cursor.on_behalf_of_fact_id else None)
    assert chain == ["policy:Low-risk docs", "connector:HR-Share", "carol"], chain
    registered = identity.get_principal(session, "connector:HR-Share")
    assert registered.kind == "DELEGATED" and registered.role is None
    again = identity.ensure_delegated_principal(session, "connector:HR-Share")
    assert again.id == registered.id, "auto-registration is idempotent"
    try:
        identity.mint_fact(session, registered, method="DELEGATED", credential=carol_c)
        raise AssertionError("delegated actors must not carry credentials")
    except ValueError:
        pass
    sys_fact = identity.system_fact(session, "conflict_engine")
    assert sys_fact.authentication_method == "INTERNAL" and sys_fact.credential_fingerprint is None
    print("Part 6 passed: who-chains resolve end to end; delegated/system actors")
    print("               carry no credentials and auto-register exactly once.")

    print("\nAll Identity Boundary checks passed.")


if __name__ == "__main__":
    main()
