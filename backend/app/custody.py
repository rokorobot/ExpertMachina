"""Credential custody layer (v1.2.0, D25 - docs/DECISIONS.md,
build contract docs/credentials-cloud-connector-v1.2.md).

Outbound credentials are the species the v1.0 boundary deliberately
excluded: secrets ExpertMachina HOLDS and presents outward (a SharePoint
client secret, later LLM provider keys) - as opposed to inbound
credentials it issues and verifies (hash-only, `credentials` table,
untouched). The constitutional rule:

    Outbound credential plaintext is not a governed fact;
    custody events are governed facts.

    Routes and connectors propose credential use;
    the custody layer decides release.

Storage is envelope encryption under the env master key EM_SECRET_KEY:
the master key wraps a per-credential data key; the data key encrypts
the secret. Master-key rotation re-wraps data keys - no secret is ever
re-entered. Plaintext exists only (a) in the operator's hands at
creation and (b) in memory at release time, on its way to a provider
adapter. No API surface, audit event, export, projection, or log ever
contains it - enforced structurally by test_credential_custody.py,
in CI permanently.

WS0 shipped the storage core (key handling, envelope encryption, the
creation path). WS1 adds the custody operations: release() - the
propose/decide seam (a scan under connectors:manage PROPOSES use; this
layer DECIDES, and every decision is a custody event) - plus rotation,
revocation, and master-key re-wrap. Language ruling: "release" is
internal seam vocabulary only; operator-facing surfaces say "use
credential for scan" - release never means reveal.
"""
import base64
import datetime
import hashlib
import json
import os
import secrets

from sqlalchemy.orm import Session

from app import database as db
from app import identity

CREDENTIAL_PURPOSES = {"CONNECTOR", "PROVIDER"}

MISSING_KEY_MESSAGE = (
    "EM_SECRET_KEY is not set. The credential custody layer cannot operate "
    "without the master key: outbound secrets are stored encrypted at rest "
    "(D25) and there is deliberately no fallback. Set EM_SECRET_KEY in the "
    "environment; if the key is lost, stored secrets are unrecoverable by "
    "design - re-enter them via rotation "
    "(docs/credentials-cloud-connector-v1.2.md)."
)


# --------------------------------------------------------------- keys

def _derive_fernet_key(master: str) -> bytes:
    """A urlsafe-base64 32-byte key derived from the operator's master
    key string. Deriving (rather than requiring a Fernet-formatted env
    value) keeps EM_SECRET_KEY an ordinary secret string."""
    return base64.urlsafe_b64encode(hashlib.sha256(master.encode("utf-8")).digest())


def _master_fernet():
    from cryptography.fernet import Fernet
    master = os.environ.get("EM_SECRET_KEY")
    if not master:
        raise RuntimeError(MISSING_KEY_MESSAGE)
    derived = _derive_fernet_key(master)
    return Fernet(derived), master_key_id(master)


def master_key_id(master: str) -> str:
    """Public identifier of a master-key GENERATION - safe to store on
    rows and in custody events. Identifies which master wrapped a data
    key (rotation bookkeeping); reveals nothing about the key."""
    return "mk_" + hashlib.sha256(_derive_fernet_key(master)).hexdigest()[:12]


# ----------------------------------------------------------- envelope

def encrypt_secret(plaintext: str):
    """Envelope-encrypt one secret: fresh random data key per credential,
    wrapped by the master key. Returns (ciphertext, wrapped_data_key,
    key_id) - all safe at rest; none derivable back without the master."""
    from cryptography.fernet import Fernet
    if not plaintext:
        raise ValueError("An outbound credential requires a non-empty secret")
    fernet, key_id = _master_fernet()
    data_key = Fernet.generate_key()
    ciphertext = Fernet(data_key).encrypt(plaintext.encode("utf-8")).decode("ascii")
    wrapped_data_key = fernet.encrypt(data_key).decode("ascii")
    return ciphertext, wrapped_data_key, key_id


def _decrypt_secret(credential: db.ExternalCredential) -> str:
    """INTERNAL: unwrap and decrypt. The only governed caller is the WS1
    release() seam (scan proposes use, custody decides release and writes
    EXTERNAL_CREDENTIAL_USED); nothing route- or projection-shaped calls this.
    Error paths never echo secret material - there is none to echo until
    decryption succeeds, and the plaintext is never interpolated."""
    from cryptography.fernet import Fernet, InvalidToken
    fernet, key_id = _master_fernet()
    if credential.key_id != key_id:
        raise RuntimeError(
            f"Credential {credential.fingerprint} was wrapped by master-key "
            f"generation {credential.key_id}, but the active EM_SECRET_KEY "
            f"is generation {key_id}. Rotate the master key properly "
            f"(re-wrap) instead of replacing it.")
    try:
        data_key = fernet.decrypt(credential.wrapped_data_key.encode("ascii"))
        return Fernet(data_key).decrypt(credential.ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken:
        raise RuntimeError(
            f"Credential {credential.fingerprint} could not be decrypted "
            f"with the active master key. No secret material is recoverable "
            f"or displayed.")


# ----------------------------------------------------------- creation

def mint_fingerprint() -> str:
    """Random public identifier for one credential GENERATION. Deliberately
    NOT derived from the plaintext - a derived fingerprint would be an
    oracle. Two credentials holding the same secret get different
    fingerprints; that is a feature."""
    return "excred_" + secrets.token_hex(8)


def create_external_credential(session: Session, *, name: str, purpose: str,
                               secret: str, actor,
                               granted_scopes: list = None,
                               coordinates: dict = None,
                               owner_principal_id: int = None,
                               replaces: db.ExternalCredential = None) -> db.ExternalCredential:
    """The creation path - a governed write (D20: boundary-decided Actor
    only). The secret is supplied BY the operator, encrypted immediately,
    and never returned by anything: unlike inbound credentials (plaintext
    once at issuance), outbound reveal is "never", not "once".

    granted_scopes is custody evidence (D25): what this credential was
    ALLOWED to reach, recorded at creation, carried on use events, never
    inferred. coordinates holds non-secret identifiers (tenant id, client
    id) - metadata, not secret material."""
    actor = identity.require_actor_object(actor)
    if purpose not in CREDENTIAL_PURPOSES:
        raise ValueError(f"Unknown credential purpose '{purpose}' "
                         f"(expected one of {sorted(CREDENTIAL_PURPOSES)})")
    if not name or not name.strip():
        raise ValueError("An outbound credential requires a name")
    ciphertext, wrapped_data_key, key_id = encrypt_secret(secret)
    owner_id = owner_principal_id if owner_principal_id is not None else actor.principal.id
    credential = db.ExternalCredential(
        name=name.strip(),
        purpose=purpose,
        owner_principal_id=owner_id,
        fingerprint=mint_fingerprint(),
        granted_scopes_json=json.dumps(granted_scopes) if granted_scopes else None,
        coordinates_json=json.dumps(coordinates) if coordinates else None,
        ciphertext=ciphertext,
        wrapped_data_key=wrapped_data_key,
        key_id=key_id,
        status="ACTIVE",
        replaces_credential_id=replaces.id if replaces else None,
        created_identity_fact_id=actor.fact(session).id,
    )
    session.add(credential)
    session.commit()
    session.refresh(credential)
    # EXTERNAL_CREDENTIAL_*, not CREDENTIAL_*: the v1.0 boundary already
    # emits CREDENTIAL_CREATED/REVOKED for inbound credentials - the two
    # species stay distinguishable in the ledger, exactly as in storage.
    _custody_event(session, actor, "EXTERNAL_CREDENTIAL_CREATED", credential, {
        "name": credential.name,
        "purpose": credential.purpose,
        "owner_principal_id": credential.owner_principal_id,
        "granted_scopes": granted_scopes or [],
        "key_id": credential.key_id,
        "replaces_fingerprint": replaces.fingerprint if replaces else None,
    })
    return credential


def _custody_event(session: Session, actor, event_type: str,
                   credential: db.ExternalCredential, details: dict):
    """Every custody action is a governed fact: metadata always, contents
    never. The fingerprint rides on every event so the ledger joins by
    credential generation."""
    from app import crud
    return crud.log_audit_event(
        session, actor=actor.display, event_type=event_type,
        target_id=str(credential.id),
        details=json.dumps({"fingerprint": credential.fingerprint, **details}),
        identity_fact_id=actor.fact(session).id)


def get_external_credential(session: Session, credential_id: int) -> db.ExternalCredential:
    return session.query(db.ExternalCredential).filter_by(id=credential_id).first()


# ------------------------------------------------------------- custody ops

def rotate_external_credential(session: Session, credential: db.ExternalCredential,
                               *, new_secret: str, actor,
                               granted_scopes: list = None,
                               coordinates: dict = None) -> db.ExternalCredential:
    """Rotation = revoke the old generation + create a new one, linked -
    the same lineage rule as inbound credentials. The old generation's
    history stays answerable forever via its fingerprint; the new secret
    is the ONLY thing the operator re-enters (a lost secret is replaced,
    never recovered - there is no reveal)."""
    actor = identity.require_actor_object(actor)
    if credential.status != "ACTIVE":
        raise ValueError(
            f"Credential {credential.fingerprint} is {credential.status}; "
            f"only an ACTIVE credential rotates. Create a new credential "
            f"instead.")
    successor = create_external_credential(
        session, name=credential.name, purpose=credential.purpose,
        secret=new_secret, actor=actor,
        granted_scopes=granted_scopes if granted_scopes is not None else credential.granted_scopes,
        coordinates=coordinates if coordinates is not None else (credential.coordinates or None),
        owner_principal_id=credential.owner_principal_id,
        replaces=credential)
    credential.status = "REVOKED"
    credential.revoked_at = datetime.datetime.utcnow()
    credential.revoked_identity_fact_id = actor.fact(session).id
    # Connectors bind the LOGICAL credential; generations are custody
    # lineage. Rotation re-points bound connectors to the successor so
    # scans continue under the new generation - recorded in the event.
    # Historical USED events keep the old fingerprint: which generation
    # authenticated which scan stays provable forever.
    rebound = session.query(db.SourceConnector).filter_by(
        external_credential_id=credential.id).all()
    for conn in rebound:
        conn.external_credential_id = successor.id
    session.commit()
    _custody_event(session, actor, "EXTERNAL_CREDENTIAL_ROTATED", credential, {
        "successor_fingerprint": successor.fingerprint,
        "successor_id": successor.id,
        "old_generation_revoked": True,
        "rebound_connector_ids": [c.id for c in rebound],
    })
    return successor


def revoke_external_credential(session: Session, credential: db.ExternalCredential,
                               *, actor, reason: str = None) -> db.ExternalCredential:
    """Revoke, never delete: the row stays as custody history; release()
    refuses it from now on. Connectors referencing it fail their next
    scan loudly - an honest failure, never a silent skip (D12)."""
    actor = identity.require_actor_object(actor)
    if credential.status == "REVOKED":
        raise ValueError(f"Credential {credential.fingerprint} is already revoked")
    credential.status = "REVOKED"
    credential.revoked_at = datetime.datetime.utcnow()
    credential.revoked_identity_fact_id = actor.fact(session).id
    session.commit()
    _custody_event(session, actor, "EXTERNAL_CREDENTIAL_REVOKED", credential,
                   {"reason": reason})
    return credential


def release(session: Session, credential: db.ExternalCredential, *,
            purpose: str, actor, connector: db.SourceConnector = None,
            job: db.IngestionJob = None) -> str:
    """THE SEAM (D25, the family shape's fifth instance): callers propose
    credential use; this function decides release. A refusal is itself a
    custody event. On release, the plaintext goes to the caller in memory
    only - its sole legitimate destination is a provider adapter
    authenticating outward. Internal vocabulary only: operator surfaces
    say "use credential for scan", never "release".

    Every release is one EXTERNAL_CREDENTIAL_USED event (per scan, not
    per HTTP request) carrying: fingerprint, key generation, granted
    scopes (what the credential was ALLOWED to reach), connector/source
    context, the scan/job id, and the acting identity fact. Never
    contents."""
    actor = identity.require_actor_object(actor)
    context = {
        "purpose": purpose,
        "connector_id": connector.id if connector else None,
        "connector_name": connector.name if connector else None,
        "connector_type": connector.type if connector else None,
        "ingestion_job_id": job.id if job else None,
    }
    refusal = None
    if credential is None:
        raise ValueError("No credential to release")
    elif credential.status != "ACTIVE":
        refusal = f"credential is {credential.status}"
    elif credential.purpose != purpose:
        refusal = (f"credential purpose is {credential.purpose}, "
                   f"proposed use is {purpose}")
    if refusal:
        _custody_event(session, actor, "EXTERNAL_CREDENTIAL_RELEASE_REFUSED",
                       credential, {**context, "refusal": refusal})
        raise PermissionError(
            f"Credential {credential.fingerprint} not released: {refusal}. "
            f"The custody layer decides release; the refusal is audited.")
    plaintext = _decrypt_secret(credential)
    _custody_event(session, actor, "EXTERNAL_CREDENTIAL_USED", credential, {
        **context,
        "key_id": credential.key_id,
        "granted_scopes": credential.granted_scopes,
    })
    return plaintext


def release_for_scan(session: Session, connector: db.SourceConnector,
                     job: db.IngestionJob, actor) -> str:
    """The connector use-path: a scan (authorized by connectors:manage)
    proposes use of the connector's bound credential; custody decides.
    Scanning never requires the custody permission - administering a
    credential and using one are separate layers by ruling."""
    credential = get_external_credential(session, connector.external_credential_id)
    if credential is None:
        raise ValueError(
            f"Connector '{connector.name}' references credential id "
            f"{connector.external_credential_id}, which does not exist")
    return release(session, credential, purpose="CONNECTOR", actor=actor,
                   connector=connector, job=job)


# ---------------------------------------------------- master-key rotation

def rewrap_master_key(session: Session, *, old_master: str, new_master: str,
                      actor) -> dict:
    """Master-key rotation re-wraps every data key under the new master -
    ciphertexts are untouched and NO secret is ever re-entered (the
    scheme's design constraint, ruled at scoping). Key material arrives
    via the environment only (EM_SECRET_KEY / EM_SECRET_KEY_PREVIOUS);
    it never transits request bodies, responses, or events."""
    from cryptography.fernet import Fernet, InvalidToken
    actor = identity.require_actor_object(actor)
    if not old_master or not new_master:
        raise RuntimeError(
            "Master-key rotation needs both generations: EM_SECRET_KEY "
            "(new) and EM_SECRET_KEY_PREVIOUS (old), environment-provided.")
    old_id, new_id = master_key_id(old_master), master_key_id(new_master)
    if old_id == new_id:
        raise ValueError("The old and new master keys are identical - "
                         "nothing to rotate.")
    old_fernet = Fernet(_derive_fernet_key(old_master))
    new_fernet = Fernet(_derive_fernet_key(new_master))
    rewrapped = 0
    rows = session.query(db.ExternalCredential).filter_by(key_id=old_id).all()
    for row in rows:
        try:
            data_key = old_fernet.decrypt(row.wrapped_data_key.encode("ascii"))
        except InvalidToken:
            raise RuntimeError(
                f"Credential {row.fingerprint} claims key generation "
                f"{old_id} but EM_SECRET_KEY_PREVIOUS cannot unwrap it. "
                f"Rotation aborted; nothing was changed.")
        row.wrapped_data_key = new_fernet.encrypt(data_key).decode("ascii")
        row.key_id = new_id
        rewrapped += 1
    session.commit()
    from app import crud
    crud.log_audit_event(
        session, actor=actor.display, event_type="CUSTODY_MASTER_KEY_ROTATED",
        target_id=None,
        details=json.dumps({"old_key_id": old_id, "new_key_id": new_id,
                            "credentials_rewrapped": rewrapped}),
        identity_fact_id=actor.fact(session).id)
    return {"old_key_id": old_id, "new_key_id": new_id,
            "credentials_rewrapped": rewrapped}
