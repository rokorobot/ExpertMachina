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

WS0 ships the storage core (this module: key handling, envelope
encryption, the creation path). WS1 adds the governed routes
(credentials:manage), rotation/revocation lineage, and release().
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
    from app import crud
    crud.log_audit_event(
        session, actor=actor.display, event_type="EXTERNAL_CREDENTIAL_CREATED",
        target_id=str(credential.id),
        details=json.dumps({
            "fingerprint": credential.fingerprint,
            "name": credential.name,
            "purpose": credential.purpose,
            "owner_principal_id": credential.owner_principal_id,
            "granted_scopes": granted_scopes or [],
            "key_id": credential.key_id,
            "replaces_fingerprint": replaces.fingerprint if replaces else None,
        }),
        identity_fact_id=actor.fact(session).id)
    return credential
