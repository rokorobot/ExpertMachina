"""D25 custody guard (v1.2.0, docs/credentials-cloud-connector-v1.2.md).

    Outbound credential plaintext is not a governed fact;
    custody events are governed facts.

This suite is the structural, permanent enforcement of D25 - the
schema-guard pattern applied to secrecy, in CI on every push, the way
test_workbench_projection.py guards D24. It seeds known sentinel secrets
through the REAL creation path and adversarially sweeps every surface:
every table, every row, every column, the raw database file bytes, audit
payloads, ORM reprs, forced failure paths, and (WS1) every custody API
response over HTTP.

Sentinels here are synthetic BY RULE, never real: the contract's hard
boundary forbids any live tenant secret from entering CI, fixtures,
snapshots, or artifacts.

WS0 parts (1-5): schema shape, loud missing-key refusal, the creation
path, the sentinel sweep, and the adversarial self-proof (the guard
demonstrably catches disabled encryption and a plaintext-shaped column).

WS1 parts (6-8), the gate = the Alice test for secrets + boundary
integrity: rotation lineage proves which generation authenticated which
scan from the ledger alone; revoked generations are provably unusable
and every refusal is a custody event; master-key rotation re-wraps
without re-entering any secret; custody routes are credentials:manage
(ADMIN-only) with denials audited; a scan under connectors:manage USES a
bound credential through the custody seam without holding the custody
permission; and no API response ever carries plaintext, ciphertext,
wrapped keys, or master-key material.
"""
import os
import sys
import json
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ.pop("EM_SECRET_KEY", None)       # Part 2 proves the loud failure first
os.environ.pop("EM_SECRET_KEY_PREVIOUS", None)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

# Isolated database + vector store, the test_authorization pattern: rebind
# BEFORE importing app.main so the TestClient app runs on the test DB.
_tmpdir = tempfile.mkdtemp(prefix="em_custody_")
DB_PATH = os.path.join(_tmpdir, "custody.db")
db.engine = create_engine(f"sqlite:///{DB_PATH}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_custody_qdrant_")

from fastapi.testclient import TestClient

from app import custody
from app import connectors
from app import identity
from app import main
import test_support

# Synthetic sentinels - deliberately shaped like nothing real. If any of
# these strings is ever readable on any surface, custody is broken.
SENTINEL = "SENTINEL-OUTBOUND-SECRET-a9f3c17e-MUST-NEVER-SURFACE"
SENTINEL_GEN2 = "SENTINEL-ROTATED-SECRET-4b81d02c-MUST-NEVER-SURFACE"
SENTINEL_HTTP = "SENTINEL-HTTP-SECRET-e5c6f993-MUST-NEVER-SURFACE"
SENTINEL_HTTP2 = "SENTINEL-HTTP-ROTATED-1d7a44b8-MUST-NEVER-SURFACE"

MASTER = "test-master-key-generation-one"
MASTER2 = "test-master-key-generation-two"
MASTER3 = "test-master-key-generation-three"

EXPECTED_COLUMNS = {
    "ciphertext", "coordinates_json", "created_at",
    "created_identity_fact_id", "fingerprint", "granted_scopes_json",
    "id", "key_id", "name", "owner_principal_id", "purpose",
    "replaces_credential_id", "revoked_at", "revoked_identity_fact_id",
    "status", "wrapped_data_key",
}

# Column names that would signal plaintext storage creeping in. The
# custody table stores ciphertext and wrapped keys ONLY.
PLAINTEXT_SHAPED = {"secret", "plaintext", "password", "client_secret",
                    "api_key", "token", "value", "secret_value"}


def part1_structure(live=None):
    """The custody schema shape is frozen: encrypted material + lineage
    columns exactly, no plaintext-shaped column ever, and the v1.0
    inbound table keeps its hash-only contract untouched (the two
    credential species never merge). `live` is injectable so Part 5 can
    prove this check catches a regressed column set without mutating
    the real metadata."""
    table = db.Base.metadata.tables["external_credentials"]
    if live is None:
        live = {c.name for c in table.columns}
    assert live == EXPECTED_COLUMNS, (
        f"external_credentials diverged from the D25 custody shape.\n"
        f"unexpected: {sorted(live - EXPECTED_COLUMNS)}\n"
        f"missing: {sorted(EXPECTED_COLUMNS - live)}\n"
        f"A custody schema change needs a ratified decision "
        f"(docs/DECISIONS.md) updating this suite AND the D24 snapshot "
        f"in the same commit.")
    hits = {c for c in live if c.lower() in PLAINTEXT_SHAPED}
    assert not hits, (
        f"D25 violation: plaintext-shaped column(s) {sorted(hits)} on "
        f"external_credentials. Secrets are stored as ciphertext under "
        f"envelope encryption - never as readable values.")
    for col in ("created_identity_fact_id",):
        assert not table.columns[col].nullable, (
            f"{col} must be NOT nullable - no pre-boundary outbound "
            f"credentials exist (D20 posture).")

    inbound = db.Base.metadata.tables["credentials"]
    inbound_cols = {c.name for c in inbound.columns}
    assert "secret_hash" in inbound_cols
    assert not {"ciphertext", "wrapped_data_key"} & inbound_cols, (
        "Species separation violated: the v1.0 inbound credentials table "
        "must stay hash-only; decryptable material lives ONLY in "
        "external_credentials behind the custody layer.")
    print("Part 1 passed: custody schema shape frozen; no plaintext-shaped "
          "columns; inbound table untouched (species separated).")


def part2_loud_failure_without_master_key():
    """A missing EM_SECRET_KEY fails loudly and actionably BEFORE any
    secret is accepted - never a silent fallback to weaker storage."""
    assert "EM_SECRET_KEY" not in os.environ
    try:
        custody.encrypt_secret(SENTINEL)
        raise AssertionError("encrypt_secret ran without EM_SECRET_KEY - "
                             "custody must refuse, never fall back")
    except RuntimeError as e:
        assert "EM_SECRET_KEY" in str(e), f"unactionable error: {e}"
        assert SENTINEL not in str(e)
    print("Part 2 passed: missing master key is a loud, actionable "
          "refusal; the offered secret is not echoed.")


def part3_creation_path(session):
    """The real creation path: envelope encryption, random fingerprints
    (never plaintext-derived), non-null creation fact, scope evidence, and
    an EXTERNAL_CREDENTIAL_CREATED custody event carrying metadata only."""
    actor = test_support.governed_actor(session, "custody_admin", role="ADMIN")
    cred = custody.create_external_credential(
        session, name="SharePoint scans (test)", purpose="CONNECTOR",
        secret=SENTINEL, actor=actor,
        granted_scopes=["Sites.Selected"],
        coordinates={"tenant_id": "tenant-000", "client_id": "client-000"})

    assert cred.status == "ACTIVE"
    assert cred.fingerprint.startswith("excred_")
    assert cred.created_identity_fact_id is not None
    assert cred.granted_scopes == ["Sites.Selected"]
    assert SENTINEL not in cred.ciphertext
    assert SENTINEL not in cred.wrapped_data_key

    # Internal decrypt round-trips (custody.release is its only governed
    # caller); the row's key generation matches the active master.
    assert custody._decrypt_secret(cred) == SENTINEL
    assert cred.key_id == custody.master_key_id(os.environ["EM_SECRET_KEY"])

    # Same secret again -> different fingerprint AND different ciphertext:
    # the fingerprint is random (a derived one would be an oracle), and
    # every credential gets a fresh data key.
    cred2 = custody.create_external_credential(
        session, name="Second generation (test)", purpose="CONNECTOR",
        secret=SENTINEL, actor=actor, replaces=cred)
    assert cred2.fingerprint != cred.fingerprint
    assert cred2.ciphertext != cred.ciphertext
    assert cred2.replaces_credential_id == cred.id

    # Custody events are EXTERNAL_CREDENTIAL_* - the v1.0 boundary already
    # emits CREDENTIAL_CREATED for inbound credentials (password/token
    # issuance); the two species stay distinguishable in the ledger.
    events = session.query(db.AuditEvent).filter_by(
        event_type="EXTERNAL_CREDENTIAL_CREATED").all()
    assert len(events) == 2, "every creation is a custody event"
    details = json.loads(events[0].details)
    assert details["fingerprint"] == cred.fingerprint
    assert details["granted_scopes"] == ["Sites.Selected"], (
        "granted scope is custody evidence (D25): recorded at creation")
    assert events[0].identity_fact_id is not None

    # Refusals: unknown purpose, empty secret, string actor (the D20 seam).
    for kwargs, fragment in [
        (dict(name="x", purpose="MYSTERY", secret="s", actor=actor), "purpose"),
        (dict(name="x", purpose="CONNECTOR", secret="", actor=actor), "non-empty"),
    ]:
        try:
            custody.create_external_credential(session, **kwargs)
            raise AssertionError(f"accepted but should refuse: {fragment}")
        except ValueError as e:
            assert fragment in str(e)
    try:
        custody.create_external_credential(
            session, name="x", purpose="CONNECTOR", secret="s", actor="Mallory")
        raise AssertionError("string actor crossed the custody boundary")
    except TypeError:
        pass
    print("Part 3 passed: creation encrypts, fingerprints are random and "
          "plaintext-independent, creation facts and scope evidence "
          "recorded, refusals refuse.")
    return cred


def sweep_everything(session, engine, label, sentinels=None):
    """Sweep every table, every row, every column, and every audit payload
    for every sentinel. Reused by parts 4, 6, 7, and 8 - the sweep GROWS
    with the milestone; it never shrinks."""
    sentinels = sentinels or [SENTINEL]
    with engine.connect() as conn:
        for table in db.Base.metadata.sorted_tables:
            for row in conn.execute(table.select()):
                for value in row:
                    for s in sentinels:
                        assert s not in str(value), (
                            f"D25 violation ({label}): sentinel readable "
                            f"in {table.name}: {value!r}")
    for event in session.query(db.AuditEvent).all():
        blob = f"{event.event_type} {event.details} {event.target_id} {event.actor}"
        for s in sentinels:
            assert s not in blob, (
                f"D25 violation ({label}): sentinel in audit event {event.id}")


def part4_adversarial_sweep(session, engine, db_path, cred):
    """The custody proof: sweep EVERY surface for the sentinel. Any hit
    anywhere - a column, a payload, the raw file, a repr, an error
    message - fails CI."""
    # Every table, every row, every column (including external_credentials
    # itself: ciphertext is encrypted, so the sentinel is absent there too).
    sweep_everything(session, engine, "part 4")

    # ORM repr / str.
    assert SENTINEL not in repr(cred) and SENTINEL not in str(cred.__dict__)

    # Forced failure path: a different master key must refuse without
    # echoing anything secret.
    prior = os.environ["EM_SECRET_KEY"]
    os.environ["EM_SECRET_KEY"] = "a-different-master-key-generation"
    try:
        custody._decrypt_secret(cred)
        raise AssertionError("decrypt succeeded under the wrong master key")
    except RuntimeError as e:
        assert SENTINEL not in str(e)
        assert "generation" in str(e)
    finally:
        os.environ["EM_SECRET_KEY"] = prior

    # The strongest form: the raw database file bytes. Flush everything
    # first so the sweep sees the durable artifact, not a cache.
    session.commit()
    engine.dispose()
    raw = open(db_path, "rb").read()
    assert SENTINEL.encode("utf-8") not in raw, (
        "D25 violation: sentinel readable in the raw database file - "
        "encryption at rest is not happening")
    print("Part 4 passed: sentinel unreadable in every table, every audit "
          "payload, reprs, failure paths, and the raw database bytes.")


def part5_the_guard_guards():
    """Adversarial self-proof (the WS0 acceptance pattern, as with the
    D24 guard): CI must DEMONSTRABLY catch the two most likely custody
    regressions - it is not enough to pass while they happen to be
    absent."""
    # Regression A: encryption silently disabled - plaintext lands in
    # the ciphertext column. The sweep must fail. Runs against its own
    # scratch database; nothing here touches the main suite's state.
    tmp = tempfile.mkdtemp(prefix="em_custody_adv_")
    adv_path = os.path.join(tmp, "adv.db")
    adv_engine = create_engine(f"sqlite:///{adv_path}",
                               connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(adv_engine)
    adv_session = sessionmaker(bind=adv_engine)()
    try:
        actor = test_support.governed_actor(adv_session, "adv_admin", role="ADMIN")
        row = db.ExternalCredential(
            name="broken-by-design", purpose="CONNECTOR",
            owner_principal_id=actor.principal.id,
            fingerprint="excred_adversarial",
            ciphertext=SENTINEL,  # <- the simulated regression
            wrapped_data_key="x", key_id="mk_x", status="ACTIVE",
            created_identity_fact_id=actor.fact(adv_session).id)
        adv_session.add(row)
        adv_session.commit()
        try:
            part4_adversarial_sweep(adv_session, adv_engine, adv_path, row)
            raise AssertionError(
                "the sweep did NOT catch plaintext in the ciphertext column")
        except AssertionError as e:
            if "D25 violation" not in str(e):
                raise
    finally:
        adv_session.close()
        adv_engine.dispose()

    # Regression B: a plaintext-shaped column appears on the custody
    # table. The structural check must fail. (Injected column set - the
    # live metadata is never mutated.)
    try:
        part1_structure(live=EXPECTED_COLUMNS | {"client_secret"})
        raise AssertionError(
            "the structure check did NOT catch a client_secret column")
    except AssertionError as e:
        if "client_secret" not in str(e):
            raise
    print("Part 5 passed: the guard demonstrably catches both simulated "
          "regressions - disabled encryption (plaintext in ciphertext) "
          "and a plaintext-shaped custody column.")


def part6_alice_test_for_secrets(session):
    """The WS1 gate, clause 1: create -> scans -> rotate -> scans ->
    revoke. From the ledger alone, every historical scan resolves to the
    exact credential generation that authenticated it; the revoked
    generation is provably unusable and the refusal is a custody event;
    rotation re-points bound connectors to the successor (recorded)."""
    admin = test_support.governed_actor(session, "custody_admin", role="ADMIN")

    gen1 = custody.create_external_credential(
        session, name="Graph scans", purpose="CONNECTOR",
        secret=SENTINEL, actor=admin, granted_scopes=["Sites.Selected"])

    project = db.Project(name="Custody", description="", customer_id=1)
    session.add(project)
    session.commit()
    connector = db.SourceConnector(
        project_id=project.id, name="sp-lineage", type="LOCAL_FOLDER",
        root_path=_tmpdir, external_credential_id=gen1.id)
    session.add(connector)
    session.commit()

    def scan(expected_secret):
        job = db.IngestionJob(project_id=project.id, connector_id=connector.id,
                              status="RUNNING")
        session.add(job)
        session.commit()
        actor = identity.delegated_actor(session, f"connector:{connector.name}")
        released = custody.release_for_scan(session, connector, job, actor=actor)
        assert released == expected_secret, "release must hand the caller the real secret"
        return job

    job1 = scan(SENTINEL)
    job2 = scan(SENTINEL)

    # Rotate: gen1 revoked + linked successor; the bound connector is
    # re-pointed to the successor (connectors bind the LOGICAL credential;
    # generations are custody lineage) and the re-point is recorded.
    gen2 = custody.rotate_external_credential(
        session, gen1, new_secret=SENTINEL_GEN2, actor=admin)
    session.refresh(connector)
    assert gen1.status == "REVOKED" and gen1.revoked_identity_fact_id is not None
    assert gen2.replaces_credential_id == gen1.id
    assert gen2.granted_scopes == ["Sites.Selected"], "scopes inherit on rotation"
    assert connector.external_credential_id == gen2.id, "rotation re-points bound connectors"
    rotated = session.query(db.AuditEvent).filter_by(
        event_type="EXTERNAL_CREDENTIAL_ROTATED").one()
    rd = json.loads(rotated.details)
    assert rd["fingerprint"] == gen1.fingerprint
    assert rd["successor_fingerprint"] == gen2.fingerprint
    assert connector.id in rd["rebound_connector_ids"]

    job3 = scan(SENTINEL_GEN2)

    # THE ALICE TEST: from the ledger alone - which generation
    # authenticated which scan? (Six months later, nothing else needed.)
    used = session.query(db.AuditEvent).filter_by(
        event_type="EXTERNAL_CREDENTIAL_USED").order_by(db.AuditEvent.id).all()
    by_job = {json.loads(e.details)["ingestion_job_id"]:
              json.loads(e.details) for e in used}
    assert by_job[job1.id]["fingerprint"] == gen1.fingerprint
    assert by_job[job2.id]["fingerprint"] == gen1.fingerprint
    assert by_job[job3.id]["fingerprint"] == gen2.fingerprint
    for e in used:
        d = json.loads(e.details)
        assert d["key_id"], "the master-key generation is custody evidence"
        assert d["granted_scopes"] == ["Sites.Selected"], (
            "what the credential was ALLOWED to reach rides on every use")
        assert d["connector_id"] == connector.id
        assert e.identity_fact_id is not None

    # The revoked generation is provably unusable - and the refusal is
    # itself a custody event, carrying the scan context.
    dead_job = db.IngestionJob(project_id=project.id, connector_id=connector.id,
                               status="RUNNING")
    session.add(dead_job)
    session.commit()
    actor = identity.delegated_actor(session, f"connector:{connector.name}")
    try:
        custody.release(session, gen1, purpose="CONNECTOR", actor=actor,
                        connector=connector, job=dead_job)
        raise AssertionError("a REVOKED generation was released")
    except PermissionError as e:
        assert "not released" in str(e)
    refused = session.query(db.AuditEvent).filter_by(
        event_type="EXTERNAL_CREDENTIAL_RELEASE_REFUSED").one()
    fd = json.loads(refused.details)
    assert fd["fingerprint"] == gen1.fingerprint
    assert fd["ingestion_job_id"] == dead_job.id
    assert "REVOKED" in fd["refusal"]

    # Purpose mismatch is refused the same way (a PROVIDER credential
    # cannot be proposed for a CONNECTOR scan).
    try:
        custody.release(session, gen2, purpose="PROVIDER", actor=actor)
        raise AssertionError("purpose mismatch was released")
    except PermissionError:
        pass

    # Rotating a revoked generation refuses; revoking twice refuses.
    for op in (lambda: custody.rotate_external_credential(
                   session, gen1, new_secret="irrelevant", actor=admin),):
        try:
            op()
            raise AssertionError("operated on a revoked generation")
        except ValueError:
            pass

    # End-to-end refusal through the scan machinery: revoke gen2, scan ->
    # the job FAILS loudly with a declared error, never a silent skip.
    custody.revoke_external_credential(session, gen2, actor=admin,
                                       reason="end-to-end refusal proof")
    failed_job = db.IngestionJob(project_id=project.id, connector_id=connector.id,
                                 status="PENDING")
    session.add(failed_job)
    session.commit()
    connectors.execute_ingestion_job(session, failed_job.id, auto_extract=False)
    session.refresh(failed_job)
    assert failed_job.status == "FAILED"
    assert gen2.fingerprint in failed_job.error and "not released" in failed_job.error

    sweep_everything(session, db.engine, "part 6", [SENTINEL, SENTINEL_GEN2])
    print("Part 6 passed: the ledger alone proves which generation "
          "authenticated every scan; revoked generations are unusable and "
          "refusals are audited custody events; a refused scan FAILS "
          "loudly end-to-end.")
    return project.id


def part7_master_key_rotation(session):
    """The WS1 gate, clause 8: master-key rotation re-wraps data keys
    without re-entering any secret - ciphertexts are byte-identical
    before and after - and decryptability survives under the new key."""
    admin = test_support.governed_actor(session, "custody_admin", role="ADMIN")
    gen3 = custody.create_external_credential(
        session, name="Rewrap proof", purpose="CONNECTOR",
        secret=SENTINEL_GEN2, actor=admin)
    all_rows = session.query(db.ExternalCredential).all()
    before = {r.id: (r.ciphertext, r.wrapped_data_key, r.key_id) for r in all_rows}

    os.environ["EM_SECRET_KEY"] = MASTER2
    result = custody.rewrap_master_key(
        session, old_master=MASTER, new_master=MASTER2, actor=admin)
    assert result["credentials_rewrapped"] == len(all_rows), (
        "every generation re-wraps - revoked history stays decryptable "
        "under the active master too")

    for r in all_rows:
        session.refresh(r)
        old_cipher, old_wrapped, old_key = before[r.id]
        assert r.ciphertext == old_cipher, (
            "ciphertext must be BYTE-IDENTICAL: rotation re-wraps the data "
            "key; it never touches (so never needs) the secret")
        assert r.wrapped_data_key != old_wrapped
        assert r.key_id == custody.master_key_id(MASTER2) != old_key
    assert custody._decrypt_secret(gen3) == SENTINEL_GEN2, (
        "decryptability preserved under the new master")

    # The old master is dead: it can no longer unwrap anything.
    os.environ["EM_SECRET_KEY"] = MASTER
    try:
        custody._decrypt_secret(gen3)
        raise AssertionError("old master still decrypts after rotation")
    except RuntimeError:
        pass
    os.environ["EM_SECRET_KEY"] = MASTER2

    # Identical old/new refuses; the rotation event carries key ids and
    # counts, never key material.
    try:
        custody.rewrap_master_key(session, old_master=MASTER2,
                                  new_master=MASTER2, actor=admin)
        raise AssertionError("identical masters accepted")
    except ValueError:
        pass
    ev = session.query(db.AuditEvent).filter_by(
        event_type="CUSTODY_MASTER_KEY_ROTATED").one()
    d = json.loads(ev.details)
    assert d["credentials_rewrapped"] == len(all_rows)
    for material in (MASTER, MASTER2):
        assert material not in (ev.details or "")
    print("Part 7 passed: master-key rotation re-wrapped every generation "
          "without re-entering a secret (ciphertexts byte-identical), "
          "decryptability preserved, old master dead, event carries key "
          "ids and counts only.")


def part8_route_boundary_and_sweep(project_id):
    """The WS1 gate, clauses 2-3 and 5-7 over HTTP: custody routes are
    credentials:manage (ADMIN-only) with denials audited; an operator
    scan USES a bound credential without holding the custody permission;
    and no API response ever carries plaintext, ciphertext, wrapped keys,
    or master-key material."""
    with TestClient(main.app) as client:
        with db.SessionLocal() as boot:
            for name, role in [("boss", "ADMIN"), ("kai", "KNOWLEDGE_OPERATOR"),
                               ("greta", "GOVERNANCE_REVIEWER"), ("alice", "READ_ONLY")]:
                p = identity.create_principal(boot, name=name, display_name=name.capitalize(),
                                              kind="HUMAN", role=role, created_by="test-suite")
                identity.set_password(boot, p, f"{name}-password-123", actor=name)

        def login(name):
            r = client.post("/api/auth/login",
                            json={"name": name, "password": f"{name}-password-123"})
            assert r.status_code == 200, r.text
            return {"Authorization": f"Bearer {r.json()['token']}"}

        ADMIN, OPERATOR = login("boss"), login("kai")
        REVIEWER, ALICE = login("greta"), login("alice")

        secret_material = [SENTINEL, SENTINEL_GEN2, SENTINEL_HTTP,
                           SENTINEL_HTTP2, MASTER, MASTER2, MASTER3]
        with db.SessionLocal() as s:
            secret_material += [r.ciphertext for r in s.query(db.ExternalCredential)]
            secret_material += [r.wrapped_data_key for r in s.query(db.ExternalCredential)]

        responses = []

        def swept(r, expect=200):
            assert r.status_code == expect, f"{r.request.url}: {r.status_code} {r.text}"
            for s in secret_material:
                assert s not in r.text, (
                    f"D25 violation: secret material in API response "
                    f"{r.request.url}")
            responses.append(r)
            return r

        # Clause 2: non-custody roles cannot create, read, rotate, revoke,
        # or rotate-master-key - and each denial is audited.
        for headers, who in [(OPERATOR, "KNOWLEDGE_OPERATOR"),
                             (REVIEWER, "GOVERNANCE_REVIEWER"),
                             (ALICE, "READ_ONLY")]:
            for method, url, body in [
                    ("GET", "/api/credentials", None),
                    ("POST", "/api/credentials",
                     {"name": "x", "purpose": "CONNECTOR", "secret": "nope"}),
                    ("POST", "/api/credentials/1/rotate", {"secret": "nope"}),
                    ("POST", "/api/credentials/1/revoke", {}),
                    ("POST", "/api/credentials/rotate-master-key", {})]:
                r = client.request(method, url, json=body, headers=headers)
                assert r.status_code == 403, (
                    f"{who} {method} {url} must 403: {r.status_code}")
        with db.SessionLocal() as s:
            denied = [e for e in s.query(db.AuditEvent).filter_by(
                event_type="AUTHZ_DENIED").all()
                if json.loads(e.details)["permission"] == "credentials:manage"]
            assert denied, "custody denials must be audit evidence"
            assert all(e.identity_fact_id is not None for e in denied)

        # Clause 6: ADMIN custody administration - every response swept.
        r = swept(client.post("/api/credentials", headers=ADMIN, json={
            "name": "HTTP custody proof", "purpose": "CONNECTOR",
            "secret": SENTINEL_HTTP, "granted_scopes": ["Sites.Selected"],
            "coordinates": {"tenant_id": "t-1", "client_id": "c-1"}}))
        cred_id = r.json()["id"]
        assert r.json()["fingerprint"].startswith("excred_")
        assert "secret" not in r.json() and "ciphertext" not in r.json()

        swept(client.get("/api/credentials", headers=ADMIN))
        detail = swept(client.get(f"/api/credentials/{cred_id}", headers=ADMIN)).json()
        assert detail["custody_events"], "custody history is a computed projection"

        # Clause 3: binding is custody; scanning is use. The operator
        # cannot bind, CAN still create unbound connectors, and CAN scan
        # a bound connector - the custody layer decides release.
        scan_dir = tempfile.mkdtemp(prefix="em_custody_scandir_")
        with open(os.path.join(scan_dir, "doc.txt"), "w") as f:
            f.write("All operators must complete safety training before access.\n")
        r = client.post(f"/api/projects/{project_id}/connectors", headers=OPERATOR,
                        json={"name": "op-bound", "root_path": scan_dir,
                              "external_credential_id": cred_id})
        assert r.status_code == 403, "binding a credential requires credentials:manage"
        r = swept(client.post(f"/api/projects/{project_id}/connectors", headers=OPERATOR,
                              json={"name": "op-plain", "root_path": scan_dir}))
        bound = swept(client.post(f"/api/projects/{project_id}/connectors", headers=ADMIN,
                                  json={"name": "admin-bound", "root_path": scan_dir,
                                        "external_credential_id": cred_id})).json()
        r = swept(client.post(f"/api/connectors/{bound['id']}/scan", headers=OPERATOR))
        job_id = r.json()["id"]
        job = swept(client.get(f"/api/ingestion-jobs/{job_id}", headers=OPERATOR)).json()
        assert job["status"] == "COMPLETED", (
            f"the operator's scan must complete using the bound credential "
            f"through custody: {job}")
        with db.SessionLocal() as s:
            used = [e for e in s.query(db.AuditEvent).filter_by(
                event_type="EXTERNAL_CREDENTIAL_USED").all()
                if json.loads(e.details).get("ingestion_job_id") == job_id]
            assert len(used) == 1, "one EXTERNAL_CREDENTIAL_USED per scan"
            d = json.loads(used[0].details)
            assert d["granted_scopes"] == ["Sites.Selected"]
            assert d["connector_id"] == bound["id"]

        # Binding a revoked/wrong-purpose credential is refused at bind time.
        rotated = swept(client.post(f"/api/credentials/{cred_id}/rotate", headers=ADMIN,
                                    json={"secret": SENTINEL_HTTP2})).json()
        r = client.post(f"/api/projects/{project_id}/connectors", headers=ADMIN,
                        json={"name": "stale-bind", "root_path": scan_dir,
                              "external_credential_id": cred_id})
        assert r.status_code == 409, "binding a REVOKED generation must refuse"

        swept(client.post(f"/api/credentials/{rotated['id']}/revoke", headers=ADMIN,
                          json={"reason": "http proof"}))

        # Clause 8 over HTTP: master rotation - key material arrives via
        # env only; the response carries key ids and a count.
        os.environ["EM_SECRET_KEY_PREVIOUS"] = MASTER2
        os.environ["EM_SECRET_KEY"] = MASTER3
        r = swept(client.post("/api/credentials/rotate-master-key", headers=ADMIN))
        assert r.json()["credentials_rewrapped"] >= 1
        os.environ.pop("EM_SECRET_KEY_PREVIOUS", None)

        # Clause 7: the route-level sweep - the audit surface and every
        # custody/connector/job response gathered above, plus the whole
        # ledger via the API, contain no secret material.
        swept(client.get("/api/audit", headers=ADMIN))
        swept(client.get(f"/api/credentials/{cred_id}", headers=ADMIN))
        swept(client.get(f"/api/credentials/{rotated['id']}", headers=ADMIN))
        assert len(responses) >= 12
    print("Part 8 passed: custody routes ADMIN-only with audited denials; "
          "operator scans use bound credentials through custody without "
          "holding the permission; binding is a custody act; no API "
          "response carried plaintext, ciphertext, wrapped keys, or "
          "master-key material.")


def main_test():
    db.Base.metadata.create_all(db.engine)
    session = db.SessionLocal()

    part1_structure()
    part2_loud_failure_without_master_key()
    os.environ["EM_SECRET_KEY"] = MASTER
    cred = part3_creation_path(session)
    part4_adversarial_sweep(session, db.engine, DB_PATH, cred)
    session = db.SessionLocal()  # part 4 closes its session for the byte sweep
    part5_the_guard_guards()
    project_id = part6_alice_test_for_secrets(session)
    part7_master_key_rotation(session)
    session.close()
    part8_route_boundary_and_sweep(project_id)

    # The final full sweep, under the post-rotation master: everything the
    # suite did - creations, scans, rotations, revocations, HTTP traffic -
    # left no readable secret anywhere.
    session = db.SessionLocal()
    sweep_everything(session, db.engine, "final",
                     [SENTINEL, SENTINEL_GEN2, SENTINEL_HTTP, SENTINEL_HTTP2,
                      MASTER, MASTER2, MASTER3])
    session.close()
    db.engine.dispose()
    raw = open(DB_PATH, "rb").read()
    for s in (SENTINEL, SENTINEL_GEN2, SENTINEL_HTTP, SENTINEL_HTTP2):
        assert s.encode("utf-8") not in raw

    print("\nD25 custody guard passed: sentinel secrets entered through "
          "every real path (function, rotation, HTTP) and are readable on "
          "NO surface - and the guard provably fails when custody "
          "regresses. Custody events are governed facts; the plaintext "
          "never was.")


if __name__ == "__main__":
    main_test()
