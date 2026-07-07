"""Identity Admin routes (audit T2.4, relocated VERBATIM from app/main.py).

Pure relocation: no endpoint semantics, paths, status codes, response
models, dependency behavior, or audit events changed. Proven by
test_route_manifest.py (byte-identical route contract).
"""
import os
import shutil
import hashlib
import json
import uuid
import datetime
from fastapi import APIRouter, Depends, Header, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app import logging_config
from app import database as db
from app import schemas
from app import crud
from app import identity
from app import ingestion
from app import extraction
from app import query_engine
from app import evaluation
from app import conflict_engine
from app import revisions
from app import trust
from app import governance_inbox
from app import consumption_inbox
from app import operations_view
from app import binding_lineage
from app import connectors
from app import policy
from app import classification
from app import tier2
from app import llm
from app import custody
from app.projections import engine as projection_engine
from app.deps import get_db, require_actor, require_perm, _authorize_or_403

logger = logging_config.get_logger(__name__)
UPLOAD_DIR = "./uploads"

router = APIRouter()


# Identity administration (v1.0 WS2b): AGENT/SERVICE principals and API
# tokens, ADMIN only. Tokens govern agents and services the way sessions
# govern humans: issued against the registry, hashed at rest, plaintext
# shown exactly once, revoked never deleted (lineage). The MCP gateway
# resolves EM_AGENT_TOKEN against these per call.
@router.get("/api/identity/principals", response_model=List[schemas.PrincipalResponse])
def list_principals(db_session: Session = Depends(get_db),
                    actor: identity.Actor = Depends(require_perm("identity:manage"))):
    return db_session.query(db.Principal).order_by(db.Principal.id).all()

@router.post("/api/identity/principals", response_model=schemas.PrincipalCreatedResponse)
def create_identity_principal(body: schemas.PrincipalCreate,
                              db_session: Session = Depends(get_db),
                              actor: identity.Actor = Depends(require_perm("identity:manage"))):
    kind = (body.kind or "").strip().upper()
    if kind not in ("HUMAN", "AGENT", "SERVICE"):
        raise HTTPException(status_code=400,
                            detail="Only HUMAN, AGENT, and SERVICE principals are created here; "
                                   "SYSTEM and DELEGATED principals are platform-managed.")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    clearance = (body.clearance or "").strip().upper() or None
    role = (body.role or "").strip().upper() or None
    if kind == "AGENT":
        clearance = clearance or "PUBLIC"
        if clearance not in ("PUBLIC", "INTERNAL", "RESTRICTED", "EXECUTIVE"):
            raise HTTPException(status_code=400, detail=f"Invalid clearance '{clearance}'")
    elif clearance is not None:
        raise HTTPException(status_code=400, detail="clearance applies to AGENT principals only")
    if kind == "HUMAN" and role is None:
        role = "READ_ONLY"  # least privilege until explicitly granted
    if kind == "SERVICE" and role is None:
        role = "READ_ONLY"
    try:
        principal = identity.create_principal(
            db_session, name=name, display_name=(body.display_name or name).strip(),
            kind=kind, role=role, clearance=clearance, created_by=actor.display,
            identity_fact_id=actor.fact(db_session).id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    one_time_password = None
    if kind == "HUMAN":
        # the bootstrap pattern: generated, shown once, rotation forced
        import secrets as _secrets
        one_time_password = _secrets.token_urlsafe(12)
        principal.must_change_password = True
        identity.set_password(db_session, principal, one_time_password, actor=actor.display)
    return schemas.PrincipalCreatedResponse(
        id=principal.id, name=principal.name, display_name=principal.display_name,
        kind=principal.kind, role=principal.role, clearance=principal.clearance,
        active=principal.active, created_by=principal.created_by,
        created_at=principal.created_at, one_time_password=one_time_password)


@router.patch("/api/identity/principals/{name}", response_model=schemas.PrincipalResponse)
def update_identity_principal(name: str, body: schemas.PrincipalUpdate,
                              db_session: Session = Depends(get_db),
                              actor: identity.Actor = Depends(require_perm("identity:manage"))):
    principal = identity.get_principal(db_session, name)
    if principal is None:
        raise HTTPException(status_code=404, detail=f"Principal '{name}' not found")
    if principal.kind in ("SYSTEM", "DELEGATED"):
        raise HTTPException(status_code=400, detail=f"{principal.kind} principals are platform-managed")
    if principal.id == actor.principal.id and (body.role is not None or body.active is not None):
        raise HTTPException(status_code=400,
                            detail="Administrators cannot change their own role or deactivate "
                                   "themselves (lockout/escalation guard)")
    changes = {}
    if body.display_name is not None and body.display_name.strip():
        changes["display_name"] = (principal.display_name, body.display_name.strip())
        principal.display_name = body.display_name.strip()
    if body.role is not None:
        new_role = body.role.strip().upper()
        if new_role not in identity.ROLES:
            raise HTTPException(status_code=400, detail=f"Unknown role: {new_role}")
        if new_role not in identity.ALLOWED_ROLES_BY_KIND.get(principal.kind, set()):
            raise HTTPException(status_code=400,
                                detail=f"{principal.kind} principals may not hold role {new_role}")
        changes["role"] = (principal.role, new_role)
        principal.role = new_role
    if body.clearance is not None:
        if principal.kind != "AGENT":
            raise HTTPException(status_code=400, detail="clearance applies to AGENT principals only")
        new_clearance = body.clearance.strip().upper()
        if new_clearance not in ("PUBLIC", "INTERNAL", "RESTRICTED", "EXECUTIVE"):
            raise HTTPException(status_code=400, detail=f"Invalid clearance '{new_clearance}'")
        changes["clearance"] = (principal.clearance, new_clearance)
        principal.clearance = new_clearance
    if body.active is not None and bool(body.active) != bool(principal.active):
        changes["active"] = (bool(principal.active), bool(body.active))
        principal.active = bool(body.active)
        if not principal.active:
            # deactivation kills live sessions and tokens fail closed at resolve time
            for cred in db_session.query(db.Credential).filter(
                    db.Credential.principal_id == principal.id,
                    db.Credential.kind == "SESSION",
                    db.Credential.revoked_at.is_(None)).all():
                identity.revoke_credential(db_session, cred, actor=actor.display,
                                           reason="principal deactivated",
                                           identity_fact_id=actor.fact(db_session).id)
    if changes:
        db_session.commit()
        crud.log_audit_event(db_session, actor=actor.display, event_type="PRINCIPAL_UPDATED",
                             target_id=str(principal.id),
                             details=json.dumps({"principal": principal.name,
                                                 "changes": {k: {"old": v[0], "new": v[1]}
                                                             for k, v in changes.items()}}),
                             identity_fact_id=actor.fact(db_session).id)
    return principal


@router.post("/api/identity/principals/{name}/reset-password", response_model=schemas.PrincipalCreatedResponse)
def reset_principal_password(name: str,
                             db_session: Session = Depends(get_db),
                             actor: identity.Actor = Depends(require_perm("identity:manage"))):
    """Admin recovery for HUMAN principals: a new generated one-time
    password (shown once), forced rotation, live sessions revoked."""
    principal = identity.get_principal(db_session, name)
    if principal is None:
        raise HTTPException(status_code=404, detail=f"Principal '{name}' not found")
    if principal.kind != "HUMAN":
        raise HTTPException(status_code=400, detail="Password resets apply to HUMAN principals")
    import secrets as _secrets
    one_time_password = _secrets.token_urlsafe(12)
    identity.set_password(db_session, principal, one_time_password, actor=actor.display)
    principal.must_change_password = True
    for cred in db_session.query(db.Credential).filter(
            db.Credential.principal_id == principal.id,
            db.Credential.kind == "SESSION",
            db.Credential.revoked_at.is_(None)).all():
        identity.revoke_credential(db_session, cred, actor=actor.display,
                                   reason="password reset",
                                   identity_fact_id=actor.fact(db_session).id)
    db_session.commit()
    return schemas.PrincipalCreatedResponse(
        id=principal.id, name=principal.name, display_name=principal.display_name,
        kind=principal.kind, role=principal.role, clearance=principal.clearance,
        active=principal.active, created_by=principal.created_by,
        created_at=principal.created_at, one_time_password=one_time_password)

@router.post("/api/identity/tokens", response_model=schemas.TokenIssuedResponse)
def issue_identity_token(body: schemas.TokenIssueRequest,
                         db_session: Session = Depends(get_db),
                         actor: identity.Actor = Depends(require_perm("tokens:manage"))):
    principal = identity.get_principal(db_session, (body.principal_name or "").strip())
    if principal is None:
        raise HTTPException(status_code=404, detail=f"Principal '{body.principal_name}' not found")
    if principal.kind not in ("AGENT", "SERVICE"):
        raise HTTPException(status_code=400,
                            detail=f"API tokens are for AGENT/SERVICE principals; "
                                   f"{principal.kind} principals authenticate with passwords/sessions.")
    if not principal.active:
        raise HTTPException(status_code=400, detail=f"Principal '{principal.name}' is deactivated")
    expires_at = None
    if body.expires_days is not None:
        if body.expires_days <= 0:
            raise HTTPException(status_code=400, detail="expires_days must be positive")
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=body.expires_days)
    plaintext, cred = identity.issue_token(
        db_session, principal, kind="API_TOKEN", label=body.label, expires_at=expires_at,
        actor=actor.display, identity_fact_id=actor.fact(db_session).id)
    return schemas.TokenIssuedResponse(
        token=plaintext, fingerprint=cred.fingerprint, principal_name=principal.name,
        label=cred.label, expires_at=cred.expires_at)

@router.get("/api/identity/tokens", response_model=List[schemas.TokenResponse])
def list_identity_tokens(db_session: Session = Depends(get_db),
                         actor: identity.Actor = Depends(require_perm("tokens:manage"))):
    rows = db_session.query(db.Credential, db.Principal).join(
        db.Principal, db.Credential.principal_id == db.Principal.id).filter(
        db.Credential.kind == "API_TOKEN").order_by(db.Credential.id).all()
    # fingerprints only - hashes never leave the store, plaintext never returns
    return [schemas.TokenResponse(
        fingerprint=c.fingerprint, principal_name=p.name, principal_kind=p.kind,
        label=c.label, created_at=c.created_at, expires_at=c.expires_at,
        revoked_at=c.revoked_at, last_used_at=c.last_used_at) for c, p in rows]

@router.post("/api/identity/tokens/{fingerprint}/revoke", response_model=schemas.TokenResponse)
def revoke_identity_token(fingerprint: str,
                          db_session: Session = Depends(get_db),
                          actor: identity.Actor = Depends(require_perm("tokens:manage"))):
    cred = db_session.query(db.Credential).filter(
        db.Credential.fingerprint == fingerprint, db.Credential.kind == "API_TOKEN").first()
    if cred is None:
        raise HTTPException(status_code=404, detail=f"Token '{fingerprint}' not found")
    identity.revoke_credential(db_session, cred, actor=actor.display,
                               reason="revoked by administrator",
                               identity_fact_id=actor.fact(db_session).id)
    principal = db_session.query(db.Principal).filter(db.Principal.id == cred.principal_id).first()
    return schemas.TokenResponse(
        fingerprint=cred.fingerprint, principal_name=principal.name, principal_kind=principal.kind,
        label=cred.label, created_at=cred.created_at, expires_at=cred.expires_at,
        revoked_at=cred.revoked_at, last_used_at=cred.last_used_at)
