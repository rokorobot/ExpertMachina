"""System routes (audit T2.4, relocated VERBATIM from app/main.py).

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


# Status Check
@router.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "ExpertMachina Backend"}

# Identity Boundary v1.0: authentication endpoints. Login verifies the
# proposed name+password and issues a SESSION credential that records
# which password generation authenticated it (lineage); everything else
# resolves bearer tokens through require_actor.
@router.post("/api/auth/login", response_model=schemas.LoginResponse)
def auth_login(body: schemas.LoginRequest, db_session: Session = Depends(get_db)):
    token, principal = identity.authenticate_password(db_session, body.name.strip(), body.password)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return schemas.LoginResponse(
        token=token, name=principal.name, display_name=principal.display_name,
        role=principal.role, kind=principal.kind,
        must_change_password=bool(principal.must_change_password))

@router.get("/api/auth/me", response_model=schemas.AuthIdentityResponse)
def auth_me(actor: identity.Actor = Depends(require_actor)):
    p = actor.principal
    return schemas.AuthIdentityResponse(
        name=p.name, display_name=p.display_name, role=p.role, kind=p.kind,
        must_change_password=bool(p.must_change_password))

@router.post("/api/auth/logout")
def auth_logout(actor: identity.Actor = Depends(require_actor),
                db_session: Session = Depends(get_db)):
    if actor.credential is not None and actor.credential.kind == "SESSION":
        identity.revoke_credential(db_session, actor.credential, actor=actor.name, reason="logout")
    return {"ok": True}

@router.post("/api/auth/change-password", response_model=schemas.AuthIdentityResponse)
def auth_change_password(body: schemas.ChangePasswordRequest,
                         actor: identity.Actor = Depends(require_actor),
                         db_session: Session = Depends(get_db)):
    p = actor.principal
    if p.kind != "HUMAN":
        raise HTTPException(status_code=400, detail="Only HUMAN principals hold passwords")
    if len(body.new_password or "") < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    verify_token, verified = identity.authenticate_password(db_session, p.name, body.current_password)
    if verify_token is None:
        # 400, deliberately NOT 401: the caller's SESSION is valid - what
        # failed is a field in the request body. A 401 here would make the
        # frontend's global session-expiry handler log the user out for a
        # typo (live bug, June 2026).
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    # the verification login minted a session we don't need - revoke it
    vp, vc = identity.resolve_token(db_session, verify_token)
    if vc is not None:
        identity.revoke_credential(db_session, vc, actor=p.name, reason="password-change verification")
    identity.set_password(db_session, p, body.new_password, actor=p.name)
    p.must_change_password = False
    db_session.commit()
    return schemas.AuthIdentityResponse(
        name=p.name, display_name=p.display_name, role=p.role, kind=p.kind,
        must_change_password=False)
