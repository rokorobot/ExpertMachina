"""D25 custody guard (v1.2.0 WS0, docs/credentials-cloud-connector-v1.2.md).

    Outbound credential plaintext is not a governed fact;
    custody events are governed facts.

This suite is the structural, permanent enforcement of D25 - the
schema-guard pattern applied to secrecy, in CI on every push, the way
test_workbench_projection.py guards D24. It seeds a known sentinel
secret through the REAL creation path and adversarially sweeps every
surface for it: every table, every row, every column, the raw database
file bytes, audit event payloads, ORM reprs, and forced failure paths.
Any hit fails CI.

Sentinels here are synthetic BY RULE, never real: the contract's hard
boundary forbids any live tenant secret from entering CI, fixtures,
snapshots, or artifacts. WS1 extends this sweep to the custody routes
(API responses) when they exist; the sweep itself never leaves CI.

Part 5 is the adversarial self-proof (the WS0 acceptance pattern): the
guard demonstrably CATCHES the two most likely regressions - encryption
silently disabled, and a plaintext-shaped column on the custody table -
rather than merely passing while they happen to be absent.
"""
import os
import sys
import json
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ.pop("EM_SECRET_KEY", None)  # Part 2 proves the loud failure first

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import custody
import test_support

# Synthetic sentinel - deliberately shaped like nothing real. If this
# string is ever readable on any surface, custody is broken.
SENTINEL = "SENTINEL-OUTBOUND-SECRET-a9f3c17e-MUST-NEVER-SURFACE"

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

    # Internal decrypt round-trips (release() in WS1 is its only governed
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


def part4_adversarial_sweep(session, engine, db_path, cred):
    """The custody proof: sweep EVERY surface for the sentinel. Any hit
    anywhere - a column, a payload, the raw file, a repr, an error
    message - fails CI."""
    # Every table, every row, every column (including external_credentials
    # itself: ciphertext is encrypted, so the sentinel is absent there too).
    with engine.connect() as conn:
        for table in db.Base.metadata.sorted_tables:
            for row in conn.execute(table.select()):
                for value in row:
                    assert SENTINEL not in str(value), (
                        f"D25 violation: sentinel readable in "
                        f"{table.name}: {value!r}")

    # Audit payloads explicitly: custody events carry metadata, never
    # contents.
    for event in session.query(db.AuditEvent).all():
        blob = f"{event.event_type} {event.details} {event.target_id} {event.actor}"
        assert SENTINEL not in blob, (
            f"D25 violation: sentinel in audit event {event.id}")

    # ORM repr / str.
    assert SENTINEL not in repr(cred) and SENTINEL not in str(cred.__dict__)

    # Forced failure path: a different master key must refuse without
    # echoing anything secret.
    os.environ["EM_SECRET_KEY"] = "a-different-master-key-generation"
    try:
        custody._decrypt_secret(cred)
        raise AssertionError("decrypt succeeded under the wrong master key")
    except RuntimeError as e:
        assert SENTINEL not in str(e)
        assert "generation" in str(e)
    finally:
        os.environ["EM_SECRET_KEY"] = MASTER

    # The strongest form: the raw database file bytes. Flush everything
    # first so the sweep sees the durable artifact, not a cache.
    session.close()
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


MASTER = "test-master-key-for-custody-suite"


def main():
    tmp = tempfile.mkdtemp(prefix="em_custody_test_")
    db_path = os.path.join(tmp, "custody_test.db")
    engine = create_engine(f"sqlite:///{db_path}",
                           connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    part1_structure()
    part2_loud_failure_without_master_key()
    os.environ["EM_SECRET_KEY"] = MASTER
    cred = part3_creation_path(session)
    part4_adversarial_sweep(session, engine, db_path, cred)
    part5_the_guard_guards()

    print("\nD25 custody guard passed: the sentinel secret entered through "
          "the real creation path and is readable on NO surface - and the "
          "guard provably fails when custody regresses. Custody events are "
          "governed facts; the plaintext never was.")


if __name__ == "__main__":
    main()
