"""Shared FastAPI dependencies (audit T2.4, the main.py router split).

Relocated VERBATIM from app/main.py so router modules and main can share one
identity for each dependency object (test suites override
`app.dependency_overrides[get_db]` and import these by name - the object
identity must not change). Behavior is unchanged: this is a pure relocation.
main.py re-exports these names for backward compatibility.
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import database as db
from app import identity


# DB dependency
def get_db():
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


# Identity Boundary v1.0 (docs/identity-boundary-v1.md, D20 candidate):
# callers propose identity (a bearer token); this dependency decides the
# actor. Every state-changing route depends on it - caller-supplied actor
# strings (?actor=, body reviewer/created_by fields) no longer exist, and
# unknown fields a stale client still sends are ignored by the schemas.
def require_actor(authorization: Optional[str] = Header(None),
                  db_session: Session = Depends(get_db)) -> identity.Actor:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    principal, credential = identity.resolve_token(db_session, token)
    if principal is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: the identity boundary decides actors; "
                   "callers cannot assert them. Log in at /api/auth/login.")
    if principal.kind == "AGENT":
        # Agents consume knowledge through the MCP gateway (D10's governed
        # channel) under clearance. What an agent may do on the REST surface
        # is an authorization question - answered by the WS3 role matrix,
        # not implicitly by possession of a token.
        raise HTTPException(
            status_code=403,
            detail="AGENT tokens are valid at the MCP gateway only; REST access for "
                   "agents awaits the authorization matrix (v1.0 WS3).")
    method = "PASSWORD" if credential.kind == "SESSION" else "API_TOKEN"
    return identity.Actor(principal, method, credential=credential)


# WS3: centralized authorization. Authentication answers WHO; this guard
# answers WHETHER. The matrix lives in identity.ROLE_PERMISSIONS (small,
# code-resident, backend-enforced); the UI only hides what the backend
# would refuse. Grants for non-read permissions and all denials are
# audited with the actor's identity fact.
def require_perm(permission: str):
    def guard(actor: identity.Actor = Depends(require_actor),
              db_session: Session = Depends(get_db)) -> identity.Actor:
        try:
            identity.authorize(db_session, actor, permission)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        return actor
    return guard


def _authorize_or_403(db_session: Session, actor: identity.Actor, permission: str):
    """In-route authorization for routes whose required permission depends
    on the payload (e.g. asset status transitions)."""
    try:
        identity.authorize(db_session, actor, permission)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
