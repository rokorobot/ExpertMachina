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
import os
import secrets as _secrets

from sqlalchemy.orm import Session

from app import database as db

PRINCIPAL_KINDS = {"HUMAN", "DELEGATED", "SYSTEM", "SERVICE", "AGENT"}
CREDENTIAL_KINDS = {"PASSWORD", "API_TOKEN", "SESSION"}
AUTH_METHODS = {"PASSWORD", "API_TOKEN", "DELEGATED", "INTERNAL"}

# ----------------------------------------------------------- authorization
# WS3 (v1.0): identity is trusted but POWERLESS until authorized. The
# matrix is deliberately small, code-resident (governed in code, versioned
# with it), and enforced at the route boundary - the backend is the source
# of truth; the UI merely hides what it knows will be refused.

PERMISSIONS = {
    "identity:manage",   # principals: create, role changes, activate/deactivate, password resets
    "tokens:manage",     # API tokens: issue, list, revoke
    "assets:read",       # governed knowledge, projects, experts, dashboards, inbox
    "assets:review",     # asset review, candidate revisions, claim-verdict review, benchmarks/evaluations
    "assets:approve",    # approvals, revision/conflict decisions, approval policies, expert models, package compile
    "assets:delete",     # destructive asset operations
    "documents:ingest",  # uploads, extraction
    "connectors:manage", # source connectors: create, scan
    "audit:read",        # the audit ledger and agent activity
    "settings:manage",   # platform configuration (LLM provider settings)
    "mcp:consume",       # the MCP gateway (read channel under clearance)
    # v1.2.0 WS1 (D25): outbound credential CUSTODY - create, rotate,
    # revoke, bind, read metadata. Deliberately NOT under
    # connectors:manage: KNOWLEDGE_OPERATOR holds that, SERVICE
    # principals may hold KNOWLEDGE_OPERATOR, and credentialed automation
    # must never mint or rotate outbound secrets. ADMIN-only via the
    # matrix. USING a bound credential (a scan) stays a connectors:manage
    # action - the custody layer decides release (custody.release).
    "credentials:manage",
}

ROLE_PERMISSIONS = {
    "ADMIN": frozenset(PERMISSIONS),
    "GOVERNANCE_REVIEWER": frozenset({
        "assets:read", "assets:review", "assets:approve", "audit:read"}),
    "KNOWLEDGE_OPERATOR": frozenset({
        "assets:read", "documents:ingest", "connectors:manage"}),
    "AGENT_CONSUMER": frozenset({"mcp:consume"}),
    "READ_ONLY": frozenset({"assets:read"}),
}
ROLES = set(ROLE_PERMISSIONS)

# Access-tier clearance for HUMAN/SERVICE principals (audit fix 2026-07-07,
# H-SEC-1). The clearance BOUNDARY must be decided by the server from the
# principal, never asserted by the caller - the same law the MCP gateway
# already enforces for agents (mcp_gateway.agent_clearance derives clearance
# from the Principal registry, never from the env or the request). The REST
# query path previously trusted a request-body access_level, letting a
# READ_ONLY caller read EXECUTIVE-tier assets by asking for them.
#
# Precedence: an explicit Principal.clearance (already used for AGENT kind)
# wins; otherwise this code-resident role map decides. A caller-supplied
# access_level may only NARROW the effective tier (min), never widen it.
#
# Mapping rationale (RATIFIED 2026-07-07, docs/audit-2026-07-07.md open
# question 2): governance needs to see every tier it governs; ingest and
# read-only roles default to INTERNAL. Fail-closed on unknown roles.
ACCESS_TIERS = ("PUBLIC", "INTERNAL", "RESTRICTED", "EXECUTIVE")
_ACCESS_TIER_RANK = {tier: rank for rank, tier in enumerate(ACCESS_TIERS)}
ROLE_CLEARANCE = {
    "ADMIN": "EXECUTIVE",
    "GOVERNANCE_REVIEWER": "EXECUTIVE",
    "KNOWLEDGE_OPERATOR": "INTERNAL",
    "READ_ONLY": "INTERNAL",
    "AGENT_CONSUMER": "PUBLIC",  # agents route through the gateway, not here
}
DEFAULT_CLEARANCE = "PUBLIC"


def principal_clearance(principal: "db.Principal") -> str:
    """The server-decided access tier for a principal. Explicit
    Principal.clearance (set for AGENT kind) wins; otherwise the tier
    follows the principal's role. Unknown roles fail closed to PUBLIC."""
    explicit = (principal.clearance or "").upper()
    if explicit in _ACCESS_TIER_RANK:
        return explicit
    return ROLE_CLEARANCE.get(principal.role or "", DEFAULT_CLEARANCE)


def effective_query_clearance(principal: "db.Principal", requested: str = None) -> str:
    """Clearance for an evidence query: the principal's server-decided tier,
    optionally NARROWED (never widened) by a caller-supplied access_level.
    A request can voluntarily scope itself down; it can never claim up."""
    ceiling = principal_clearance(principal)
    req = (requested or "").upper()
    if req not in _ACCESS_TIER_RANK:
        return ceiling
    return req if _ACCESS_TIER_RANK[req] < _ACCESS_TIER_RANK[ceiling] else ceiling

# Kind-role discipline: a service must never become a quiet super-user,
# and an agent's REST powerlessness is structural, not configured.
ALLOWED_ROLES_BY_KIND = {
    "HUMAN": {"ADMIN", "GOVERNANCE_REVIEWER", "KNOWLEDGE_OPERATOR", "READ_ONLY"},
    "SERVICE": {"GOVERNANCE_REVIEWER", "KNOWLEDGE_OPERATOR", "READ_ONLY"},  # never ADMIN
    "AGENT": {"AGENT_CONSUMER"},
}

# Pre-WS3 role names, migrated on startup (mutable registry ONLY -
# IdentityFact.role_snapshot is historical evidence and is never rewritten).
LEGACY_ROLE_MIGRATION = {
    "GOVERNANCE_OFFICER": "GOVERNANCE_REVIEWER",
    "REVIEWER": "GOVERNANCE_REVIEWER",
    "VIEWER": "READ_ONLY",
}

# Read-bucket grant auditing (WS4 architecture hook, ruled at WS3 review):
# write grants and ALL denials are always audited; read grants follow
# EM_READ_AUDIT_MODE because enterprise customers eventually ask "who
# VIEWED this?", not only "who edited this?".
#   OFF     (default) - read grants unaudited; preserves pre-WS4 behavior
#                       (the D19 invariant: empty config changes nothing)
#   SAMPLED           - one in READ_AUDIT_SAMPLE_RATE read grants audited,
#                       the sampling declared in the event (D12)
#   FULL              - every read grant audited
READ_PERMISSIONS = {"assets:read", "audit:read"}
READ_AUDIT_MODES = ("OFF", "SAMPLED", "FULL")
READ_AUDIT_SAMPLE_RATE = 20
_read_grant_counter = 0


def read_audit_mode() -> str:
    mode = os.environ.get("EM_READ_AUDIT_MODE", "OFF").upper()
    return mode if mode in READ_AUDIT_MODES else "OFF"


def permissions_for(role: str) -> frozenset:
    return ROLE_PERMISSIONS.get(role or "", frozenset())


def is_authorized(principal: "db.Principal", permission: str) -> bool:
    return permission in permissions_for(principal.role)


def authorize(session: Session, actor: "Actor", permission: str):
    """The central authorization decision. Grants for non-read permissions
    and ALL denials are audit events carrying the actor's identity fact -
    'who tried, holding what role, asking for what' is answerable forever."""
    import json
    global _read_grant_counter
    if permission not in PERMISSIONS:
        raise ValueError(f"Unknown permission: {permission}")
    granted = is_authorized(actor.principal, permission)
    details = {"permission": permission,
               "role": actor.principal.role,
               "principal": actor.principal.name,
               "kind": actor.principal.kind}
    if granted and permission in READ_PERMISSIONS:
        mode = read_audit_mode()
        if mode == "OFF":
            return actor
        if mode == "SAMPLED":
            _read_grant_counter += 1
            if _read_grant_counter % READ_AUDIT_SAMPLE_RATE != 1:
                return actor
            details["read_audit"] = {"mode": "SAMPLED", "sample_rate": READ_AUDIT_SAMPLE_RATE}
        else:
            details["read_audit"] = {"mode": "FULL"}
    _audit(session, actor=actor.display,
           event_type="AUTHZ_GRANTED" if granted else "AUTHZ_DENIED",
           details=json.dumps(details),
           identity_fact_id=actor.fact(session).id)
    if not granted:
        raise PermissionError(
            f"Not authorized: '{permission}' requires a role granting it; "
            f"'{actor.principal.name}' holds {actor.principal.role or 'no role'}.")
    return actor


def validate_boundary(session: Session) -> list:
    """Startup hardening (WS4): structural self-checks over the boundary's
    own data - matrix sanity, kind-role discipline, credential integrity,
    recoverability. Findings are reported and audited, never silently
    absorbed; they are report-only because authorization already fails
    closed (an unknown role grants nothing), so a finding means
    'investigate', not 'the boundary is open'."""
    import json
    findings = []
    for role, perms in ROLE_PERMISSIONS.items():
        unknown = set(perms) - PERMISSIONS
        if unknown:
            findings.append(f"matrix: role {role} grants unknown permissions {sorted(unknown)}")
    principals = session.query(db.Principal).all()
    principal_ids = {p.id for p in principals}
    for p in principals:
        if p.kind not in PRINCIPAL_KINDS:
            findings.append(f"principal '{p.name}': unknown kind {p.kind!r}")
            continue
        if p.kind in ("SYSTEM", "DELEGATED"):
            if p.role is not None:
                findings.append(f"principal '{p.name}' ({p.kind}): must not hold a role, has {p.role!r}")
        else:
            if p.role not in ROLES:
                findings.append(f"principal '{p.name}' ({p.kind}): unknown role {p.role!r} (authorizes nothing - fails closed)")
            elif p.role not in ALLOWED_ROLES_BY_KIND[p.kind]:
                findings.append(f"principal '{p.name}' ({p.kind}): role {p.role} violates kind-role discipline")
    by_id = {p.id: p for p in principals}
    for c in session.query(db.Credential).all():
        if c.principal_id not in principal_ids:
            findings.append(f"credential {c.fingerprint}: orphaned (principal {c.principal_id} missing)")
        elif c.kind == "PASSWORD" and by_id[c.principal_id].kind != "HUMAN":
            findings.append(f"credential {c.fingerprint}: PASSWORD on non-HUMAN principal '{by_id[c.principal_id].name}'")
        elif c.kind not in CREDENTIAL_KINDS:
            findings.append(f"credential {c.fingerprint}: unknown kind {c.kind!r}")
    admins = [p for p in principals if p.kind == "HUMAN" and p.role == "ADMIN" and p.active]
    if not admins:
        findings.append("recovery: no active HUMAN ADMIN exists - see the documented "
                        "manual recovery procedure (docs/identity-boundary-v1.md)")
    _audit(session, actor="system", event_type="BOUNDARY_VALIDATION",
           details=json.dumps({"ok": not findings, "findings": findings,
                               "principals": len(principals)}))
    return findings


def migrate_legacy_roles(session: Session):
    """Startup data migration (WS3): rename pre-matrix roles in the MUTABLE
    registry. Historical role_snapshots keep the names that were true at
    action time (D12 - evidence is never rewritten). Idempotent; audited
    once per actually-changed principal."""
    import json
    changed = []
    for principal in session.query(db.Principal).all():
        new_role = None
        if principal.role in LEGACY_ROLE_MIGRATION:
            new_role = LEGACY_ROLE_MIGRATION[principal.role]
        elif principal.kind == "AGENT" and principal.role is None:
            new_role = "AGENT_CONSUMER"
        elif principal.kind == "SERVICE" and principal.role is None:
            new_role = "READ_ONLY"  # least privilege until explicitly granted
        if new_role and new_role != principal.role:
            changed.append({"principal": principal.name, "old": principal.role, "new": new_role})
            principal.role = new_role
    if changed:
        session.commit()
        _audit(session, actor="system", event_type="ROLE_VOCABULARY_MIGRATED",
               details=json.dumps({"changes": changed,
                                   "note": "mutable registry only; historical "
                                           "role_snapshots intentionally untouched"}))

# The platform acting as itself (observed vocabulary, v0.12.0 audit;
# classification_engine added v1.2.1 WS1, D27).
SYSTEM_PRINCIPAL_NAMES = ["system", "conflict_engine", "verification_engine",
                          "policy_engine", "classification_engine"]

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
                     created_by: str = "system",
                     identity_fact_id: int = None) -> db.Principal:
    if kind not in PRINCIPAL_KINDS:
        raise ValueError(f"Unknown principal kind: {kind}")
    if kind in ("SYSTEM", "DELEGATED"):
        if role is not None:
            raise ValueError(f"{kind} principals carry no role; authority is structural")
    else:
        if kind == "AGENT" and role is None:
            role = "AGENT_CONSUMER"
        if kind == "SERVICE" and role is None:
            role = "READ_ONLY"  # least privilege until explicitly granted
        if role not in ROLES:
            raise ValueError(f"Unknown role: {role}")
        if role not in ALLOWED_ROLES_BY_KIND[kind]:
            raise ValueError(f"{kind} principals may not hold role {role} "
                             f"(allowed: {sorted(ALLOWED_ROLES_BY_KIND[kind])})")
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
           details=json.dumps({"name": name, "kind": kind, "role": role, "clearance": clearance}),
           identity_fact_id=identity_fact_id)
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
                issued_by_credential_id: int = None, actor: str = None,
                identity_fact_id: int = None):
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
           details=json.dumps({"kind": kind, "principal": principal.name, "label": label}),
           identity_fact_id=identity_fact_id)
    return plaintext, cred


def revoke_credential(session: Session, credential: db.Credential, actor: str,
                      reason: str = "revoked", identity_fact_id: int = None):
    if credential.revoked_at is None:
        credential.revoked_at = datetime.datetime.utcnow()
        session.commit()
        import json
        _audit(session, actor=actor, event_type="CREDENTIAL_REVOKED",
               target_id=credential.fingerprint, details=json.dumps({"reason": reason}),
               identity_fact_id=identity_fact_id)
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


# ------------------------------------------------------------------ actor

class Actor:
    """Boundary-decided identity, handed to routes and the service layer.
    This object is the ONLY way a write path learns who acts - crud and
    the governance modules refuse plain strings (the structural seam:
    `?actor=GovernanceOfficer` cannot influence what gets recorded).
    fact() mints the IdentityFact lazily, once per Actor - one fact per
    authenticated request performing a governed write."""

    def __init__(self, principal: db.Principal, method: str,
                 credential: db.Credential = None,
                 on_behalf_of: db.IdentityFact = None):
        if method not in AUTH_METHODS:
            raise ValueError(f"Unknown authentication method: {method}")
        self.principal = principal
        self.method = method
        self.credential = credential
        self.on_behalf_of = on_behalf_of
        self._fact = None

    @property
    def name(self) -> str:
        return self.principal.name

    @property
    def display(self) -> str:
        return self.principal.display_name

    def fact(self, session: Session) -> db.IdentityFact:
        if self._fact is None:
            self._fact = mint_fact(session, self.principal, self.method,
                                   credential=self.credential,
                                   on_behalf_of=self.on_behalf_of)
        return self._fact


def require_actor_object(actor) -> "Actor":
    """The seam guarantee, callable from any governed write path: a string
    actor is a caller proposing identity past the boundary - refused."""
    if not isinstance(actor, Actor):
        raise TypeError(
            "String actors no longer cross the boundary (D20): governed writes "
            "take an identity.Actor decided by the boundary, not a caller-"
            f"supplied value (got {type(actor).__name__!r})")
    return actor


def system_actor(session: Session, name: str = "system") -> Actor:
    """The platform acting as itself."""
    principal = get_principal(session, name)
    if principal is None:
        ensure_system_principals(session)
        principal = get_principal(session, name)
    if principal is None or principal.kind != "SYSTEM":
        raise ValueError(f"'{name}' is not a SYSTEM principal")
    return Actor(principal, method="INTERNAL")


def delegated_actor(session: Session, name: str, display_name: str = None,
                    on_behalf_of: db.IdentityFact = None) -> Actor:
    """policy:X / connector:Y acting under delegated authority.
    on_behalf_of carries WHO authorized (identity chain only); the causal
    WHY stays in ActionContext - governed objects and D17 provenance."""
    principal = ensure_delegated_principal(session, name, display_name)
    return Actor(principal, method="DELEGATED", on_behalf_of=on_behalf_of)


def get_fact(session: Session, fact_id: int) -> db.IdentityFact:
    """Re-fetch a fact in a different session (background tasks receive
    fact IDs, never live ORM objects)."""
    return session.query(db.IdentityFact).filter_by(id=fact_id).first() if fact_id else None


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
