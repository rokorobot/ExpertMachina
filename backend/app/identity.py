"""Identity Boundary (v1.0) - docs/identity-boundary-v1.md.

D20 (candidate): callers propose identity; the boundary decides the actor
and records identity facts as immutable historical evidence at action
time. Future user-table state must never be required to explain past
governed actions. Identity evidence records authentication at action
time; authorization and user state may change later without altering
historical identity facts.

This module is the only place that:
- hashes and verifies secrets (stdlib only: pbkdf2 for passwords,
  sha256 for tokens - hashes verify, they don't reveal, D19),
- issues and revokes credentials (lineage: revoke, never delete),
- mints IdentityFacts (one per authenticated request performing a
  governed write; SYSTEM/DELEGATED actors mint per governed action).

Purity rule: IdentityFact answers WHO was authenticated, nothing else.
Request-context responsibilities go to a future RequestFact, never here.
"""
import datetime
import hashlib
import hmac
import secrets as _secrets

from sqlalchemy.orm import Session

from app import database as db

PRINCIPAL_KINDS = {"HUMAN", "DELEGATED", "SYSTEM", "SERVICE", "AGENT"}
ROLES = {"ADMIN", "GOVERNANCE_OFFICER", "REVIEWER", "VIEWER"}
CREDENTIAL_KINDS = {"PASSWORD", "API_TOKEN", "SESSION"}
AUTH_METHODS = {"PASSWORD", "API_TOKEN", "DELEGATED", "INTERNAL"}

# The platform acting as itself (observed vocabulary, v0.12.0 audit).
SYSTEM_PRINCIPAL_NAMES = ["system", "conflict_engine", "verification_engine", "policy_engine"]

PBKDF2_ITERATIONS = 600_000  # OWASP-recommended scale for PBKDF2-HMAC-SHA256
SESSION_TTL = datetime.timedelta(hours=12)
TOKEN_PREFIX = "emk_"  # recognizable in configs, greppable in leaks


# ---------------------------------------------------------------- secrets

def _hash_password(password: str, salt: bytes = None) -> str:
    salt = salt or _secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_hex, digest_hex = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _fingerprint(credential_id: int, secret_hash: str) -> str:
    """Stable PUBLIC identifier for a credential - safe to store on
    IdentityFacts and show in audit details forever."""
    return f"cred_{credential_id}:{hashlib.sha256(secret_hash.encode('utf-8')).hexdigest()[:12]}"


def _audit(session: Session, actor: str, event_type: str, target_id: str = None,
           details: str = None, identity_fact_id: int = None):
    from app import crud  # lazy: crud will import identity in WS1c
    return crud.log_audit_event(session, actor=actor, event_type=event_type,
                                target_id=target_id, details=details,
                                identity_fact_id=identity_fact_id)


# ------------------------------------------------------------- principals

def create_principal(session: Session, name: str, display_name: str, kind: str,
                     role: str = None, clearance: str = None,
                     created_by: str = "system") -> db.Principal:
    if kind not in PRINCIPAL_KINDS:
        raise ValueError(f"Unknown principal kind: {kind}")
    if role is not None and role not in ROLES:
        raise ValueError(f"Unknown role: {role}")
    if kind in ("SYSTEM", "DELEGATED") and role is not None:
        raise ValueError(f"{kind} principals carry no role; authority is structural")
    existing = session.query(db.Principal).filter_by(name=name).first()
    if existing:
        raise ValueError(f"Principal '{name}' already exists (principals are never deleted - reactivate instead)")
    principal = db.Principal(name=name, display_name=display_name, kind=kind,
                             role=role, clearance=clearance, created_by=created_by)
    session.add(principal)
    session.commit()
    session.refresh(principal)
    import json
    _audit(session, actor=created_by, event_type="PRINCIPAL_CREATED", target_id=str(principal.id),
           details=json.dumps({"name": name, "kind": kind, "role": role, "clearance": clearance}))
    return principal


def get_principal(session: Session, name: str) -> db.Principal:
    return session.query(db.Principal).filter_by(name=name).first()


def ensure_system_principals(session: Session):
    """Seed the platform's own actors. Idempotent; runs at startup."""
    for name in SYSTEM_PRINCIPAL_NAMES:
        if not get_principal(session, name):
            create_principal(session, name=name, display_name=name, kind="SYSTEM")


def ensure_delegated_principal(session: Session, name: str, display_name: str = None,
                               created_by: str = "system") -> db.Principal:
    """Auto-registration for DELEGATED actors (policy:X, connector:Y) when
    their governed object is created or first acts. They never authenticate;
    their authority is the governed object plus the causal chain."""
    principal = get_principal(session, name)
    if principal:
        return principal
    return create_principal(session, name=name, display_name=display_name or name,
                            kind="DELEGATED", created_by=created_by)


def bootstrap_admin(session: Session):
    """First startup with zero HUMAN principals: create 'admin' with a
    one-time generated password (returned to the caller for one-time
    console display, never logged) and must_change_password set."""
    has_human = session.query(db.Principal).filter_by(kind="HUMAN").first()
    if has_human:
        return None, None
    admin = create_principal(session, name="admin", display_name="Administrator",
                             kind="HUMAN", role="ADMIN", created_by="system")
    admin.must_change_password = True
    one_time_password = _secrets.token_urlsafe(12)
    set_password(session, admin, one_time_password, actor="system")
    return admin, one_time_password


# ------------------------------------------------------------ credentials

def _active_credentials(session: Session, principal: db.Principal, kind: str):
    now = datetime.datetime.utcnow()
    rows = session.query(db.Credential).filter_by(principal_id=principal.id, kind=kind,
                                                  revoked_at=None).all()
    return [c for c in rows if c.expires_at is None or c.expires_at > now]


def set_password(session: Session, principal: db.Principal, password: str,
                 actor: str = None) -> db.Credential:
    """Rotation = revoke old + create new. The old row stays forever so
    facts pointing at its fingerprint remain explainable (lineage)."""
    if principal.kind != "HUMAN":
        raise ValueError("Only HUMAN principals authenticate with passwords")
    rotated_from = None
    for old in _active_credentials(session, principal, "PASSWORD"):
        old.revoked_at = datetime.datetime.utcnow()
        rotated_from = old.fingerprint
        _audit(session, actor=actor or principal.name, event_type="CREDENTIAL_REVOKED",
               target_id=old.fingerprint, details='{"reason": "rotated"}')
    cred = db.Credential(principal_id=principal.id, kind="PASSWORD",
                         secret_hash=_hash_password(password), fingerprint="pending")
    session.add(cred)
    session.flush()  # assigns id, needed by the fingerprint
    cred.fingerprint = _fingerprint(cred.id, cred.secret_hash)
    session.commit()
    session.refresh(cred)
    import json
    _audit(session, actor=actor or principal.name, event_type="CREDENTIAL_CREATED",
           target_id=cred.fingerprint,
           details=json.dumps({"kind": "PASSWORD", "principal": principal.name,
                               "rotated_from": rotated_from}))
    return cred


def issue_token(session: Session, principal: db.Principal, kind: str = "API_TOKEN",
                label: str = None, expires_at: datetime.datetime = None,
                issued_by_credential_id: int = None, actor: str = None):
    """Returns (plaintext, credential). The plaintext exists exactly once,
    here - only its sha256 is stored."""
    if kind not in ("API_TOKEN", "SESSION"):
        raise ValueError(f"issue_token issues API_TOKEN or SESSION, not {kind}")
    plaintext = TOKEN_PREFIX + _secrets.token_urlsafe(32)
    cred = db.Credential(principal_id=principal.id, kind=kind,
                         secret_hash=_hash_token(plaintext), fingerprint="pending",
                         label=label, expires_at=expires_at,
                         issued_by_credential_id=issued_by_credential_id)
    session.add(cred)
    session.flush()
    cred.fingerprint = _fingerprint(cred.id, cred.secret_hash)
    session.commit()
    session.refresh(cred)
    import json
    _audit(session, actor=actor or principal.name, event_type="CREDENTIAL_CREATED",
           target_id=cred.fingerprint,
           details=json.dumps({"kind": kind, "principal": principal.name, "label": label}))
    return plaintext, cred


def revoke_credential(session: Session, credential: db.Credential, actor: str,
                      reason: str = "revoked"):
    if credential.revoked_at is None:
        credential.revoked_at = datetime.datetime.utcnow()
        session.commit()
        import json
        _audit(session, actor=actor, event_type="CREDENTIAL_REVOKED",
               target_id=credential.fingerprint, details=json.dumps({"reason": reason}))
    return credential


# ----------------------------------------------------------- authenticate

def authenticate_password(session: Session, name: str, password: str):
    """Login: verify the proposed name+password, issue a SESSION credential
    recording WHICH password credential authenticated it (lineage).
    Returns (session_token_plaintext, principal) or (None, None).
    Failures are audited with the PROPOSAL, never treated as an actor."""
    import json
    principal = get_principal(session, name)
    if principal is None or principal.kind != "HUMAN" or not principal.active:
        _audit(session, actor="identity_boundary", event_type="LOGIN_FAILED",
               details=json.dumps({"proposed_name": name, "reason": "unknown_or_inactive_principal"}))
        return None, None
    for cred in _active_credentials(session, principal, "PASSWORD"):
        if _verify_password(password, cred.secret_hash):
            cred.last_used_at = datetime.datetime.utcnow()
            session.commit()
            token, _session_cred = issue_token(
                session, principal, kind="SESSION",
                expires_at=datetime.datetime.utcnow() + SESSION_TTL,
                issued_by_credential_id=cred.id, actor=principal.name)
            _audit(session, actor=principal.name, event_type="LOGIN_SUCCEEDED",
                   target_id=str(principal.id),
                   details=json.dumps({"credential": cred.fingerprint}))
            return token, principal
    _audit(session, actor="identity_boundary", event_type="LOGIN_FAILED",
           details=json.dumps({"proposed_name": name, "reason": "bad_credentials"}))
    return None, None


def resolve_token(session: Session, token: str):
    """Bearer resolution: SESSION or API_TOKEN -> (principal, credential),
    or (None, None). Expired, revoked, and deactivated-principal tokens
    all fail closed."""
    if not token:
        return None, None
    secret_hash = _hash_token(token)
    cred = session.query(db.Credential).filter_by(secret_hash=secret_hash).first()
    if cred is None or cred.kind == "PASSWORD" or cred.revoked_at is not None:
        return None, None
    if cred.expires_at is not None and cred.expires_at <= datetime.datetime.utcnow():
        return None, None
    principal = session.query(db.Principal).filter_by(id=cred.principal_id).first()
    if principal is None or not principal.active:
        return None, None
    cred.last_used_at = datetime.datetime.utcnow()
    session.commit()
    return principal, cred


# ------------------------------------------------------------------ facts

def mint_fact(session: Session, principal: db.Principal, method: str,
              credential: db.Credential = None,
              on_behalf_of: db.IdentityFact = None) -> db.IdentityFact:
    """The boundary's verdict: an immutable snapshot of WHO this is, right
    now. Written once, never updated (D3 applied to actors)."""
    if method not in AUTH_METHODS:
        raise ValueError(f"Unknown authentication method: {method}")
    if method in ("PASSWORD", "API_TOKEN") and credential is None:
        raise ValueError(f"{method} facts must record the credential that authenticated them")
    if method in ("DELEGATED", "INTERNAL") and credential is not None:
        raise ValueError(f"{method} actors hold no credentials - lineage would be fabricated")
    fact = db.IdentityFact(
        principal_id=principal.id,
        principal_name=principal.name,
        display_name=principal.display_name,
        principal_kind=principal.kind,
        role_snapshot=principal.role,
        authentication_method=method,
        credential_fingerprint=credential.fingerprint if credential else None,
        on_behalf_of_fact_id=on_behalf_of.id if on_behalf_of else None,
    )
    session.add(fact)
    session.commit()
    session.refresh(fact)
    return fact


def system_fact(session: Session, name: str = "system") -> db.IdentityFact:
    """The platform acting as itself (engines, ingestion internals)."""
    principal = get_principal(session, name)
    if principal is None:
        ensure_system_principals(session)
        principal = get_principal(session, name)
    if principal is None or principal.kind != "SYSTEM":
        raise ValueError(f"'{name}' is not a SYSTEM principal")
    return mint_fact(session, principal, method="INTERNAL")


def delegated_fact(session: Session, name: str, display_name: str = None,
                   on_behalf_of: db.IdentityFact = None) -> db.IdentityFact:
    """policy:X / connector:Y acting under delegated authority.
    on_behalf_of carries WHO authorized (identity chain only); the causal
    WHY stays in ActionContext - governed objects and D17 provenance."""
    principal = ensure_delegated_principal(session, name, display_name)
    return mint_fact(session, principal, method="DELEGATED", on_behalf_of=on_behalf_of)
