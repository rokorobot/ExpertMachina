import os
import shutil
import hashlib
import json
import datetime
from fastapi import FastAPI, Depends, Header, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

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
from app import connectors
from app import policy
from app import llm

# Initialize FastAPI app
app = FastAPI(title="ExpertMachina MVP Backend", version="0.1.0")

# CORS: explicit local frontend origins only (audit hardening). The API has
# no identity layer until v1.x (D14) - a wildcard here let any webpage the
# operator visits call state-mutating endpoints from their browser. Override
# for other deployments via EM_CORS_ORIGINS (comma-separated).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get(
        "EM_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload directory
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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


@app.on_event("startup")
def startup_event():
    db.init_db()
    with db.SessionLocal() as session:
        # Create default customer
        crud.get_or_create_default_customer(session)
        # Identity Boundary bootstrap: platform principals, the one-time
        # admin, and DELEGATED registrations for pre-boundary governed
        # objects (their historical audit rows stay legacy - D12).
        identity.ensure_system_principals(session)
        admin, one_time_password = identity.bootstrap_admin(session)
        if one_time_password:
            # flush=True: under uvicorn, stdout is block-buffered - without
            # an explicit flush the one-time credential can sit invisible in
            # the buffer, which operationally means a locked-out admin.
            print("=" * 64, flush=True)
            print("IDENTITY BOUNDARY BOOTSTRAP - one-time admin credential", flush=True)
            print("  username: admin", flush=True)
            print(f"  password: {one_time_password}", flush=True)
            print("  Shown once, never stored in plaintext. Change it after login.", flush=True)
            print("=" * 64, flush=True)
        for pol in session.query(db.ApprovalPolicy).all():
            identity.ensure_delegated_principal(session, f"policy:{pol.name}")
        for conn in session.query(db.SourceConnector).all():
            identity.ensure_delegated_principal(session, f"connector:{conn.name}")
        # WS3: pre-matrix role names migrate in the mutable registry only;
        # historical role_snapshots keep what was true at action time.
        identity.migrate_legacy_roles(session)
        # WS4 hardening: the boundary validates its own data at startup.
        # Report-only (authorization fails closed regardless), but LOUD.
        findings = identity.validate_boundary(session)
        for finding in findings:
            print(f"BOUNDARY VALIDATION: {finding}", flush=True)

# Status Check
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "ExpertMachina Backend"}

# Identity Boundary v1.0: authentication endpoints. Login verifies the
# proposed name+password and issues a SESSION credential that records
# which password generation authenticated it (lineage); everything else
# resolves bearer tokens through require_actor.
@app.post("/api/auth/login", response_model=schemas.LoginResponse)
def auth_login(body: schemas.LoginRequest, db_session: Session = Depends(get_db)):
    token, principal = identity.authenticate_password(db_session, body.name.strip(), body.password)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return schemas.LoginResponse(
        token=token, name=principal.name, display_name=principal.display_name,
        role=principal.role, kind=principal.kind,
        must_change_password=bool(principal.must_change_password))

@app.get("/api/auth/me", response_model=schemas.AuthIdentityResponse)
def auth_me(actor: identity.Actor = Depends(require_actor)):
    p = actor.principal
    return schemas.AuthIdentityResponse(
        name=p.name, display_name=p.display_name, role=p.role, kind=p.kind,
        must_change_password=bool(p.must_change_password))

@app.post("/api/auth/logout")
def auth_logout(actor: identity.Actor = Depends(require_actor),
                db_session: Session = Depends(get_db)):
    if actor.credential is not None and actor.credential.kind == "SESSION":
        identity.revoke_credential(db_session, actor.credential, actor=actor.name, reason="logout")
    return {"ok": True}

@app.post("/api/auth/change-password", response_model=schemas.AuthIdentityResponse)
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

# Identity administration (v1.0 WS2b): AGENT/SERVICE principals and API
# tokens, ADMIN only. Tokens govern agents and services the way sessions
# govern humans: issued against the registry, hashed at rest, plaintext
# shown exactly once, revoked never deleted (lineage). The MCP gateway
# resolves EM_AGENT_TOKEN against these per call.
@app.get("/api/identity/principals", response_model=List[schemas.PrincipalResponse])
def list_principals(db_session: Session = Depends(get_db),
                    actor: identity.Actor = Depends(require_perm("identity:manage"))):
    return db_session.query(db.Principal).order_by(db.Principal.id).all()

@app.post("/api/identity/principals", response_model=schemas.PrincipalCreatedResponse)
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


@app.patch("/api/identity/principals/{name}", response_model=schemas.PrincipalResponse)
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


@app.post("/api/identity/principals/{name}/reset-password", response_model=schemas.PrincipalCreatedResponse)
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

@app.post("/api/identity/tokens", response_model=schemas.TokenIssuedResponse)
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

@app.get("/api/identity/tokens", response_model=List[schemas.TokenResponse])
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

@app.post("/api/identity/tokens/{fingerprint}/revoke", response_model=schemas.TokenResponse)
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

# Customer / Workspace Project routes
@app.get("/api/projects", response_model=List[schemas.ProjectResponse])
def get_projects(db_session: Session = Depends(get_db),
                 actor: identity.Actor = Depends(require_perm("assets:read"))):
    cust = crud.get_or_create_default_customer(db_session)
    return crud.get_projects(db_session, customer_id=cust.id)

@app.post("/api/projects", response_model=schemas.ProjectResponse)
def create_project(project: schemas.ProjectCreate, db_session: Session = Depends(get_db),
                   actor: identity.Actor = Depends(require_perm("documents:ingest"))):
    return crud.create_project(db_session, project, actor=actor)

# Documents routes
@app.get("/api/projects/{project_id}/documents", response_model=List[schemas.DocumentResponse])
def get_documents(project_id: int, db_session: Session = Depends(get_db),
                  actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.get_documents(db_session, project_id)

@app.post("/api/projects/{project_id}/documents", response_model=schemas.DocumentResponse)
def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    department: str = Form("General"),
    owner: str = Form("User"),  # document METADATA (content owner) - the acting identity is boundary-decided
    db_session: Session = Depends(get_db),
    actor: identity.Actor = Depends(require_perm("documents:ingest"))
):
    # Sanitize the client-supplied filename: strip any path components so a
    # crafted name can never escape UPLOAD_DIR (defense in depth - the
    # project-id prefix already breaks clean traversal, but multipart
    # filenames are attacker-controlled input and treated as such).
    filename = os.path.basename((file.filename or "").replace("\\", "/")).strip()
    if not filename or filename in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = os.path.join(UPLOAD_DIR, f"{project_id}_{filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = crud.create_document(
        db_session,
        project_id=project_id,
        filename=filename,
        file_path=file_path,
        department=department,
        owner=owner,
        actor=actor
    )

    # Process asynchronously (for MVP sync parsing is fast enough, we execute inline)
    ingestion.parse_and_index_document(db_session, doc.id)
    db_session.refresh(doc)

    if doc.status == "PARSED":
        extraction.extract_knowledge_assets_from_project(db_session, project_id)
        # Policy-Based Auto Approval (MVP 0.10.2): unscoped policies apply to
        # uploads too - the same rules regardless of how a document arrived.
        # The firing policy's identity chains to the uploader's fact.
        policy.apply_auto_approval(db_session, project_id, [doc.id],
                                   on_behalf_of_fact=actor.fact(db_session))
        db_session.refresh(doc)

    return doc

@app.post("/api/projects/{project_id}/documents/batch-demo")
def upload_batch_demo(project_id: int, db_session: Session = Depends(get_db),
                      actor: identity.Actor = Depends(require_perm("documents:ingest"))):
    # Pre-built standard mock SOPs to test ingestion of 100+ simulated nodes/documents quickly
    sample_docs = [
        {
            "filename": "SOP-001_Deviation_Management.txt",
            "content": (
                "SOP-001: Standard Operating Procedure for Deviation Management.\n"
                "Purpose: Provide standardized guidelines to log, assess, and resolve deviations.\n"
                "Policy: All deviations must be reviewed by QA before closure. Unresolved deviations will escalate to the VP of Quality after 30 days.\n"
                "Procedure:\n"
                "1. Identify the deviation and isolate affected products immediately.\n"
                "2. Log deviation ticket in QMS within 24 hours.\n"
                "3. Perform Root Cause Analysis (RCA) using 5-Whys methodology.\n"
                "4. QA reviewer must verify containment actions before approving resolution plans."
            ),
            "department": "Quality Assurance",
            "owner": "QA Director"
        },
        {
            "filename": "SOP-002_SLA_Refund_Policy.txt",
            "content": (
                "SOP-002: SLA Refund and Cancellation Guidelines.\n"
                "Purpose: Detail standard refund frameworks for Enterprise SLAs.\n"
                "Policy: Under standard contracts, clients can request a pro-rated refund within the first 30 days of contract execution if service uptime falls below 99.9% for two consecutive weeks. Any exceptions require written sign-off from the Finance Director.\n"
                "Procedure:\n"
                "1. Finance team verifies uptime reports via system dashboard.\n"
                "2. System operations log incident tickets and identify affected servers.\n"
                "3. Finance Director reviews refund ticket and signs approval."
            ),
            "department": "Finance",
            "owner": "Finance Director"
        },
        {
            "filename": "SOP-003_Clinical_Monitoring_Plan.txt",
            "content": (
                "SOP-003: Clinical Trial Monitoring Protocols.\n"
                "Purpose: Outline processes for monitoring clinical trial ABC-201.\n"
                "Policy: Study ABC-201 utilizes Monitoring Plan v2.1. It includes remote source data verification (rSDV) protocols in response to updated FDA guidance on decentralized trials.\n"
                "Procedure:\n"
                "1. Remote monitors must establish secure VPN access before logging into clinical data archives.\n"
                "2. Check 100% of consent signatures and 20% of critical data endpoints.\n"
                "3. Report audit exceptions directly to the Lead Investigator."
            ),
            "department": "Clinical Operations",
            "owner": "Clinical Operations Lead"
        }
    ]
    
    docs_created = []
    for d in sample_docs:
        file_path = os.path.join(UPLOAD_DIR, f"{project_id}_{d['filename']}")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(d["content"])
            
        doc = crud.create_document(
            db_session,
            project_id=project_id,
            filename=d["filename"],
            file_path=file_path,
            department=d["department"],
            owner=d["owner"],
            actor=actor
        )
        ingestion.parse_and_index_document(db_session, doc.id)
        docs_created.append(doc.filename)
        
    return {"message": "Batch demo SOP documents uploaded and parsed successfully", "documents": docs_created}

# Enterprise Source Connector routes (MVP 0.10.0): LOCAL_FOLDER, scan-now
# only. Connector output becomes ordinary documents and CANDIDATE assets in
# the existing governance pipeline - no connector-specific review flow.
@app.post("/api/projects/{project_id}/connectors", response_model=schemas.SourceConnectorResponse)
def create_source_connector(project_id: int, connector_in: schemas.SourceConnectorCreate, db_session: Session = Depends(get_db),
                            actor: identity.Actor = Depends(require_perm("connectors:manage"))):
    if (connector_in.type or "LOCAL_FOLDER").upper() != "LOCAL_FOLDER":
        raise HTTPException(status_code=400, detail="Only LOCAL_FOLDER connectors are supported in this release")
    if not connector_in.root_path.strip():
        raise HTTPException(status_code=400, detail="root_path is required")
    connector = db.SourceConnector(
        project_id=project_id,
        name=connector_in.name,
        type="LOCAL_FOLDER",
        root_path=connector_in.root_path.strip(),
        include_extensions=connector_in.include_extensions or ".txt,.md,.pdf,.docx",
    )
    db_session.add(connector)
    db_session.commit()
    db_session.refresh(connector)
    identity.ensure_delegated_principal(db_session, f"connector:{connector.name}",
                                        created_by=actor.name)
    crud.log_audit_event(db_session, actor=actor.display, event_type="SOURCE_CONNECTOR_CREATED",
                         target_id=str(connector.id),
                         details=json.dumps({"name": connector.name, "type": connector.type,
                                             "root_path": connector.root_path}),
                         identity_fact_id=actor.fact(db_session).id)
    return connector

@app.get("/api/projects/{project_id}/connectors", response_model=List[schemas.SourceConnectorResponse])
def list_source_connectors(project_id: int, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:read"))):
    return db_session.query(db.SourceConnector).filter(
        db.SourceConnector.project_id == project_id).order_by(db.SourceConnector.id).all()

@app.post("/api/connectors/{connector_id}/scan", response_model=schemas.IngestionJobResponse)
def scan_source_connector(connector_id: int, background_tasks: BackgroundTasks, db_session: Session = Depends(get_db),
                          actor: identity.Actor = Depends(require_perm("connectors:manage"))):
    connector = db_session.query(db.SourceConnector).filter(db.SourceConnector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")
    running = db_session.query(db.IngestionJob).filter(
        db.IngestionJob.connector_id == connector_id,
        db.IngestionJob.status.in_(["PENDING", "RUNNING"])
    ).first()
    if running:
        raise HTTPException(status_code=409, detail=f"Ingestion job {running.id} is already in progress for this connector")
    job = db.IngestionJob(project_id=connector.project_id, connector_id=connector.id, status="PENDING")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    # v0.9.2a discipline: return immediately; the scan owns its own session.
    # The scheduling actor's fact is minted NOW (request session) and handed
    # to the job by ID - the connector's DELEGATED fact will chain to it.
    background_tasks.add_task(connectors.run_ingestion_job, job.id,
                              on_behalf_of_fact_id=actor.fact(db_session).id)
    return job

@app.get("/api/projects/{project_id}/ingestion-jobs", response_model=List[schemas.IngestionJobResponse])
def list_ingestion_jobs(project_id: int, db_session: Session = Depends(get_db),
                        actor: identity.Actor = Depends(require_perm("assets:read"))):
    return db_session.query(db.IngestionJob).filter(
        db.IngestionJob.project_id == project_id).order_by(db.IngestionJob.id.desc()).all()

@app.get("/api/ingestion-jobs/{job_id}", response_model=schemas.IngestionJobResponse)
def get_ingestion_job(job_id: int, db_session: Session = Depends(get_db),
                      actor: identity.Actor = Depends(require_perm("assets:read"))):
    job = db_session.query(db.IngestionJob).filter(db.IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Ingestion job {job_id} not found")
    return job

@app.get("/api/ingestion-jobs/{job_id}/files", response_model=List[schemas.SourceDocumentResponse])
def list_ingestion_job_files(job_id: int, status: Optional[str] = None, db_session: Session = Depends(get_db),
                             actor: identity.Actor = Depends(require_perm("assets:read"))):
    query = db_session.query(db.SourceDocument).filter(db.SourceDocument.ingestion_job_id == job_id)
    if status:
        query = query.filter(db.SourceDocument.status == status.upper())
    return query.order_by(db.SourceDocument.id).all()

# Approval Policy routes (MVP 0.10.2): deterministic, versioned auto-approval
# rules. Policies are governed facts - create/update/toggle are audit events,
# and definition changes bump the version that ASSET_AUTO_APPROVED events
# reference. No delete: disable instead; audit history references the rule.
def _validated_policy_fields(db_session: Session, project_id: int, asset_types: List[str], connector_id: Optional[int]):
    types = [t.strip().upper() for t in (asset_types or []) if t.strip()]
    invalid = [t for t in types if t not in policy.ALLOWED_ASSET_TYPES]
    if not types or invalid:
        raise HTTPException(status_code=400,
                            detail=f"asset_types must be a non-empty subset of {sorted(policy.ALLOWED_ASSET_TYPES)}"
                                   + (f"; invalid: {invalid}" if invalid else ""))
    if connector_id is not None:
        connector = db_session.query(db.SourceConnector).filter(
            db.SourceConnector.id == connector_id, db.SourceConnector.project_id == project_id).first()
        if not connector:
            raise HTTPException(status_code=400, detail=f"Connector {connector_id} not found in project {project_id}")
    return types

@app.post("/api/projects/{project_id}/approval-policies", response_model=schemas.ApprovalPolicyResponse)
def create_approval_policy(project_id: int, policy_in: schemas.ApprovalPolicyCreate, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:approve"))):
    if not policy_in.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    types = _validated_policy_fields(db_session, project_id, policy_in.asset_types, policy_in.connector_id)
    pol = db.ApprovalPolicy(
        project_id=project_id,
        name=policy_in.name.strip(),
        asset_types_json=json.dumps(types),
        connector_id=policy_in.connector_id,
        enabled=True,
        version=1,
        created_by=actor.display,
    )
    db_session.add(pol)
    db_session.commit()
    db_session.refresh(pol)
    identity.ensure_delegated_principal(db_session, f"policy:{pol.name}", created_by=actor.name)
    crud.log_audit_event(db_session, actor=actor.display, event_type="POLICY_CREATED",
                         target_id=str(pol.id),
                         details=json.dumps({"name": pol.name, "version": pol.version,
                                             "asset_types": types, "connector_id": pol.connector_id}),
                         identity_fact_id=actor.fact(db_session).id)
    return pol

@app.get("/api/projects/{project_id}/approval-policies", response_model=List[schemas.ApprovalPolicyResponse])
def list_approval_policies(project_id: int, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:read"))):
    return db_session.query(db.ApprovalPolicy).filter(
        db.ApprovalPolicy.project_id == project_id).order_by(db.ApprovalPolicy.id).all()

@app.patch("/api/approval-policies/{policy_id}", response_model=schemas.ApprovalPolicyResponse)
def update_approval_policy(policy_id: int, update: schemas.ApprovalPolicyUpdate,
                           db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:approve"))):
    pol = db_session.query(db.ApprovalPolicy).filter(db.ApprovalPolicy.id == policy_id).first()
    if not pol:
        raise HTTPException(status_code=404, detail=f"Approval policy {policy_id} not found")
    data = update.dict(exclude_unset=True)

    # Definition changes (what the rule approves) bump the version so past
    # ASSET_AUTO_APPROVED events keep pointing at the rule text that fired.
    # The enabled flag is operational, not definitional - audited, no bump.
    definition_changed = False
    if "asset_types" in data or "connector_id" in data or "name" in data:
        new_types = _validated_policy_fields(
            db_session, pol.project_id,
            data.get("asset_types", pol.asset_types),
            data.get("connector_id", pol.connector_id))
        old_snapshot = {"name": pol.name, "asset_types": pol.asset_types,
                        "connector_id": pol.connector_id, "version": pol.version}
        if "name" in data and data["name"].strip():
            pol.name = data["name"].strip()
        pol.asset_types_json = json.dumps(new_types)
        if "connector_id" in data:
            pol.connector_id = data["connector_id"]
        pol.version += 1
        definition_changed = True

    toggled = None
    if "enabled" in data and bool(data["enabled"]) != bool(pol.enabled):
        pol.enabled = bool(data["enabled"])
        toggled = pol.enabled

    pol.updated_at = datetime.datetime.utcnow()
    db_session.commit()
    db_session.refresh(pol)

    if definition_changed:
        identity.ensure_delegated_principal(db_session, f"policy:{pol.name}", created_by=actor.name)
        crud.log_audit_event(db_session, actor=actor.display, event_type="POLICY_UPDATED",
                             target_id=str(pol.id),
                             details=json.dumps({"old": old_snapshot,
                                                 "new": {"name": pol.name, "asset_types": pol.asset_types,
                                                         "connector_id": pol.connector_id, "version": pol.version}}),
                             identity_fact_id=actor.fact(db_session).id)
    if toggled is not None:
        crud.log_audit_event(db_session, actor=actor.display,
                             event_type="POLICY_ENABLED" if toggled else "POLICY_DISABLED",
                             target_id=str(pol.id),
                             details=json.dumps({"name": pol.name, "version": pol.version}),
                             identity_fact_id=actor.fact(db_session).id)
    return pol

# LLM Provider Settings routes (MVP 0.12): governed model-per-function
# configuration. Stores model selection, never credentials (D14/D19
# candidate). Empty config preserves prior behavior:
# DB config missing -> OPENAI_MODEL env -> gpt-4o-mini default.
@app.get("/api/settings/llm", response_model=List[schemas.LLMFunctionSettingResponse])
def list_llm_settings(db_session: Session = Depends(get_db),
                      actor: identity.Actor = Depends(require_perm("settings:manage"))):
    out = []
    for function, description in llm.FUNCTIONS.items():
        row = db_session.query(db.LLMFunctionConfig).filter(
            db.LLMFunctionConfig.function == function).first()
        resolved = llm.resolve(function, db_session)
        out.append(schemas.LLMFunctionSettingResponse(
            function=function, description=description,
            provider=resolved["provider"],
            configured_model=row.model if row else None,
            effective_model=resolved["model"], source=resolved["source"]))
    return out

@app.put("/api/settings/llm/{function}", response_model=schemas.LLMFunctionSettingResponse)
def update_llm_setting(function: str, update: schemas.LLMFunctionSettingUpdate,
                       db_session: Session = Depends(get_db),
                       actor: identity.Actor = Depends(require_perm("settings:manage"))):
    function = function.upper()
    if function not in llm.FUNCTIONS:
        raise HTTPException(status_code=400,
                            detail=f"Unknown LLM function '{function}'. Known: {sorted(llm.FUNCTIONS)}")
    new_model = (update.model or "").strip() or None
    new_provider = (update.provider or "").strip().upper() or None
    if new_provider and new_provider not in llm.ADAPTERS:
        raise HTTPException(status_code=400,
                            detail=f"Unknown provider '{new_provider}'. Known: {sorted(llm.ADAPTERS)}")
    row = db_session.query(db.LLMFunctionConfig).filter(
        db.LLMFunctionConfig.function == function).first()
    old_model = row.model if row else None
    old_provider = (row.provider if row else None) or "OPENAI"
    if not row:
        row = db.LLMFunctionConfig(function=function, provider="OPENAI")
        db_session.add(row)
    row.model = new_model
    if new_provider:
        row.provider = new_provider
    row.updated_by = actor.display
    row.updated_at = datetime.datetime.utcnow()
    db_session.commit()
    crud.log_audit_event(
        db_session, actor=actor.display, event_type="LLM_CONFIG_UPDATED",
        target_id=function,
        details=json.dumps({"function": function, "old_model": old_model,
                            "new_model": new_model,
                            "old_provider": old_provider, "new_provider": row.provider,
                            "note": "model selection only - credentials never stored (env-based until v1.x)"}),
        identity_fact_id=actor.fact(db_session).id)
    resolved = llm.resolve(function, db_session)
    return schemas.LLMFunctionSettingResponse(
        function=function, description=llm.FUNCTIONS[function],
        provider=resolved["provider"], configured_model=new_model,
        effective_model=resolved["model"], source=resolved["source"])

# Knowledge Assets routes
@app.get("/api/projects/{project_id}/assets", response_model=List[schemas.KnowledgeAssetResponse])
def get_assets(project_id: int, db_session: Session = Depends(get_db),
               actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.get_knowledge_assets(db_session, project_id)

@app.post("/api/projects/{project_id}/extract")
def extract_assets(project_id: int, db_session: Session = Depends(get_db),
                   actor: identity.Actor = Depends(require_perm("documents:ingest"))):
    # Documents without assets BEFORE extraction are the ones this call will
    # extract for - the auto-approval scope for this ingestion event.
    fresh_doc_ids = [d.id for d in db_session.query(db.Document).filter(
        db.Document.project_id == project_id, db.Document.status == "PARSED").all()
        if not db_session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.document_id == d.id).first()]
    success = extraction.extract_knowledge_assets_from_project(db_session, project_id)
    if not success:
        raise HTTPException(status_code=400, detail="No parsed documents found to extract assets from. Please upload documents first.")
    auto_approval = policy.apply_auto_approval(db_session, project_id, fresh_doc_ids,
                                               on_behalf_of_fact=actor.fact(db_session))
    return {"message": "Knowledge assets extracted successfully.", "auto_approval": auto_approval}

def _asset_transition_permission(new_status: Optional[str]) -> str:
    """WS3: the permission an asset update needs depends on the transition -
    APPROVED/ARCHIVED are approval power; everything else is review work."""
    if new_status and new_status.upper() in ("APPROVED", "ARCHIVED"):
        return "assets:approve"
    return "assets:review"


# NOTE: /api/assets/bulk MUST be registered BEFORE /api/assets/{asset_id} -
# FastAPI matches routes in registration order, and the dynamic route would
# otherwise swallow "bulk" and 422 on int parsing (audit finding C1: the
# bulk endpoint was unreachable from v0.2 until this fix).
@app.patch("/api/assets/bulk", response_model=List[schemas.KnowledgeAssetResponse])
def bulk_update_assets(bulk_in: schemas.AssetBulkUpdate, db_session: Session = Depends(get_db),
                       actor: identity.Actor = Depends(require_actor)):
    _authorize_or_403(db_session, actor, _asset_transition_permission(bulk_in.status))
    # One approval path for every species of approval (the D17/D18 lesson):
    # delegate to crud.update_knowledge_asset so bulk approvals get the same
    # AssetReview, baseline revision, and lifecycle side effects as single
    # and policy approvals - the old inline copy here skipped the baseline
    # revision entirely.
    updated_assets = []
    for asset_id in bulk_in.asset_ids:
        asset = db_session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
        if not asset:
            continue
        old_st = asset.status
        updated = crud.update_knowledge_asset(
            db_session, asset_id, schemas.KnowledgeAssetUpdate(status=bulk_in.status), actor=actor,
            audit_details=f"Asset status updated from {old_st} to {bulk_in.status} via bulk update",
            review_notes=f"Approved via bulk update (from {old_st})")
        if updated:
            updated_assets.append(updated)
    return updated_assets

@app.patch("/api/assets/{asset_id}", response_model=schemas.KnowledgeAssetResponse)
def update_asset(asset_id: int, update: schemas.KnowledgeAssetUpdate, db_session: Session = Depends(get_db),
                 actor: identity.Actor = Depends(require_actor)):
    _authorize_or_403(db_session, actor, _asset_transition_permission(update.status))
    asset = crud.update_knowledge_asset(db_session, asset_id, update, actor=actor)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# Expert Models routes
@app.get("/api/projects/{project_id}/experts", response_model=List[schemas.ExpertModelResponse])
def get_experts(project_id: int, db_session: Session = Depends(get_db),
                actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.get_expert_models(db_session, project_id)

@app.post("/api/projects/{project_id}/experts", response_model=schemas.ExpertModelResponse)
def create_expert(project_id: int, expert_in: schemas.ExpertModelCreate, db_session: Session = Depends(get_db),
                  actor: identity.Actor = Depends(require_perm("assets:approve"))):
    # Validate project_id matches
    if expert_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    try:
        return crud.create_expert_model(db_session, expert_in, actor=actor)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/api/projects/{project_id}/query", response_model=schemas.QueryResponse)
def execute_query(project_id: int, query_in: schemas.QueryInput, db_session: Session = Depends(get_db),
                  actor: identity.Actor = Depends(require_perm("assets:read"))):
    if not query_in.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Single shared pipeline (Verified Answer v1) - also used by the MCP gateway.
    # The boundary-decided display replaces the old hardcoded operator string;
    # query_engine's internal audit trail keeps its own event shapes.
    result = query_engine.execute_expert_query(
        db_session,
        expert_model_id=query_in.expert_model_id,
        question=query_in.question,
        caller_access_level=query_in.access_level,
        actor=actor.display
    )
    return schemas.QueryResponse(**result)

# Agent Packages routes
@app.get("/api/projects/{project_id}/packages", response_model=List[schemas.AgentPackageResponse])
def get_packages(project_id: int, db_session: Session = Depends(get_db),
                 actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.get_agent_packages(db_session, project_id)

@app.post("/api/projects/{project_id}/packages", response_model=schemas.AgentPackageResponse)
def create_package(project_id: int, pkg_in: schemas.AgentPackageCreate, db_session: Session = Depends(get_db),
                   actor: identity.Actor = Depends(require_perm("assets:approve"))):
    if pkg_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    try:
        pkg = crud.create_agent_package(db_session, pkg_in, actor=actor)
    except ValueError as e:
        # Governance gate block: 409 Conflict, with the reason for the operator.
        raise HTTPException(status_code=409, detail=str(e))
    if not pkg:
        raise HTTPException(status_code=404, detail="Expert model not found")
    return pkg

# Agent Package Builder (MVP 0.9.4): download the compiled .empkg artifact.
@app.get("/api/packages/{package_id}/download")
def download_agent_package(package_id: int, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:read"))):
    from fastapi.responses import FileResponse
    pkg = db_session.query(db.AgentPackage).filter(db.AgentPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    if not pkg.file_path or not os.path.exists(pkg.file_path):
        raise HTTPException(status_code=404, detail="Package artifact not found on disk (compiled before MVP 0.9.4 or file removed)")
    return FileResponse(pkg.file_path, media_type="application/zip",
                        filename=os.path.basename(pkg.file_path))

@app.get("/api/experts/{expert_model_id}/compile-gate")
def get_compile_gate(expert_model_id: int, db_session: Session = Depends(get_db),
                     actor: identity.Actor = Depends(require_perm("assets:read"))):
    expert_model = db_session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not expert_model:
        raise HTTPException(status_code=404, detail=f"Expert Model with ID {expert_model_id} not found")
    return conflict_engine.evaluate_compile_gate(db_session, expert_model_id)

# Agent Center: gateway activity aggregated from the audit ledger.
@app.get("/api/agents/activity")
def get_agent_activity(db_session: Session = Depends(get_db),
                       actor: identity.Actor = Depends(require_perm("audit:read"))):
    events = db_session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type.in_(["MCP_TOOL_CALLED", "MCP_ACCESS_DENIED"])
    ).order_by(db.AuditEvent.timestamp.desc()).limit(2000).all()

    agents = {}
    for e in events:
        try:
            d = json.loads(e.details)
        except Exception:
            continue
        agent_id = d.get("agent_id", e.actor)
        a = agents.setdefault(agent_id, {
            "agent_id": agent_id,
            "clearance": d.get("clearance"),  # newest event first = current clearance
            "calls": 0,
            "denied": 0,
            "blocked_answers": 0,
            "tools": {},
            "expert_models": set(),
            "last_seen": e.timestamp.isoformat(),
            "gateway_version": d.get("gateway_version")
        })
        if e.event_type == "MCP_ACCESS_DENIED":
            a["denied"] += 1
        else:
            a["calls"] += 1
            tool = d.get("tool_name", "unknown")
            a["tools"][tool] = a["tools"].get(tool, 0) + 1
            if d.get("expert_model_id") is not None:
                a["expert_models"].add(d["expert_model_id"])

    # Verification-blocked answers per agent (the agent asked; the system refused).
    for agent_id, a in agents.items():
        a["blocked_answers"] = db_session.query(db.AuditEvent).filter(
            db.AuditEvent.actor == agent_id,
            db.AuditEvent.event_type.like("ASK_EXPERT_BLOCKED%")
        ).count()
        a["expert_models"] = sorted(a["expert_models"])

    return {
        "agents": sorted(agents.values(), key=lambda x: x["last_seen"], reverse=True),
        "total_calls": sum(a["calls"] for a in agents.values()),
        "total_denied": sum(a["denied"] for a in agents.values())
    }

# Audit Trail routes
@app.get("/api/audit", response_model=List[schemas.AuditEventResponse])
def get_audit_trail(
    limit: int = 100,
    event_prefix: Optional[str] = None,
    actor: Optional[str] = None,
    target_id: Optional[str] = None,
    since: Optional[datetime.datetime] = None,
    until: Optional[datetime.datetime] = None,
    db_session: Session = Depends(get_db),
    auth_actor: identity.Actor = Depends(require_perm("audit:read"))
):
    return crud.get_audit_events(
        db_session, limit=limit, event_prefix=event_prefix,
        actor=actor, target_id=target_id, since=since, until=until
    )

# Dashboard summaries
@app.get("/api/dashboard/{project_id}")
def get_dashboard_summary(project_id: int, db_session: Session = Depends(get_db),
                          actor: identity.Actor = Depends(require_perm("assets:read"))):
    # Count totals
    docs = crud.get_documents(db_session, project_id)
    assets = crud.get_knowledge_assets(db_session, project_id)
    experts = crud.get_expert_models(db_session, project_id)
    packages = crud.get_agent_packages(db_session, project_id)
    
    parsed_count = sum(1 for d in docs if d.status == "PARSED")
    failed_count = sum(1 for d in docs if d.status == "FAILED")
    
    # Calculate readiness score (average quality score of all documents/assets)
    # Sum scores
    total_score = 0
    score_count = 0
    for asset in assets:
        for score in asset.quality_scores:
            total_score += score.overall_score
            score_count += 1
            
    readiness_score = int(total_score / score_count) if score_count > 0 else 0
    
    return {
        "documents_uploaded": len(docs),
        "documents_parsed": parsed_count,
        "documents_failed": failed_count,
        "readiness_score": readiness_score,
        "assets_extracted": len(assets),
        "expert_models": len(experts),
        "agent_packages": len(packages),
        "assets_status_counts": {
            "CANDIDATE": sum(1 for a in assets if a.status == "CANDIDATE"),
            "REVIEWED": sum(1 for a in assets if a.status == "REVIEWED"),
            "APPROVED": sum(1 for a in assets if a.status == "APPROVED"),
            "ARCHIVED": sum(1 for a in assets if a.status == "ARCHIVED")
        }
    }

# Benchmark routes
@app.get("/api/projects/{project_id}/benchmarks", response_model=List[schemas.BenchmarkQuestionResponse])
def get_benchmarks(project_id: int, limit: int = 100, db_session: Session = Depends(get_db),
                   actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.get_benchmark_questions(db_session, project_id, limit=limit)

@app.post("/api/projects/{project_id}/benchmarks", response_model=schemas.BenchmarkQuestionResponse)
def create_benchmark(project_id: int, q_in: schemas.BenchmarkQuestionCreate, db_session: Session = Depends(get_db),
                     actor: identity.Actor = Depends(require_perm("assets:review"))):
    if q_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    return crud.create_benchmark_question(db_session, q_in)

@app.put("/api/projects/{project_id}/benchmarks/{benchmark_id}", response_model=schemas.BenchmarkQuestionResponse)
def update_benchmark(project_id: int, benchmark_id: int, q_update: schemas.BenchmarkQuestionUpdate, db_session: Session = Depends(get_db),
                     actor: identity.Actor = Depends(require_perm("assets:review"))):
    q = crud.get_benchmark_question(db_session, benchmark_id)
    if not q or q.project_id != project_id:
        raise HTTPException(status_code=404, detail="Benchmark question not found")
    updated = crud.update_benchmark_question(db_session, benchmark_id, q_update)
    return updated

@app.delete("/api/projects/{project_id}/benchmarks/{benchmark_id}")
def delete_benchmark(project_id: int, benchmark_id: int, db_session: Session = Depends(get_db),
                     actor: identity.Actor = Depends(require_perm("assets:review"))):
    q = crud.get_benchmark_question(db_session, benchmark_id)
    if not q or q.project_id != project_id:
        raise HTTPException(status_code=404, detail="Benchmark question not found")
    deleted = crud.delete_benchmark_question(db_session, benchmark_id)
    return {"message": "Benchmark question deleted successfully"}

# Evaluation runs routes
@app.post("/api/projects/{project_id}/evaluations", response_model=schemas.EvaluationRunResponse)
def trigger_evaluation(
    project_id: int,
    run_in: schemas.EvaluationRunCreate,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db),
    actor: identity.Actor = Depends(require_perm("assets:review"))
):
    if run_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    
    try:
        db_run = evaluation.create_evaluation_run(db_session, run_in)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # v1.1 WS2 channel rules: LIVE refuses package coordinates,
        # PACKAGE requires them - violations are bad requests, not 404s.
        raise HTTPException(status_code=400, detail=str(e))

    # Trigger execution in the background
    background_tasks.add_task(evaluation.run_evaluation_batch, db_session, db_run.id)
    return db_run

@app.get("/api/projects/{project_id}/evaluations", response_model=List[schemas.EvaluationRunResponse])
def list_evaluations(project_id: int, db_session: Session = Depends(get_db),
                     actor: identity.Actor = Depends(require_perm("assets:read"))):
    return db_session.query(db.EvaluationRun).filter(db.EvaluationRun.project_id == project_id).order_by(db.EvaluationRun.started_at.desc()).all()

@app.get("/api/projects/{project_id}/evaluations/{run_id}", response_model=schemas.EvaluationRunResponse)
def get_evaluation(project_id: int, run_id: int, db_session: Session = Depends(get_db),
                   actor: identity.Actor = Depends(require_perm("assets:read"))):
    run = db_session.query(db.EvaluationRun).filter(db.EvaluationRun.id == run_id, db.EvaluationRun.project_id == project_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return run

@app.get("/api/packages/{package_id}/model-comparison")
def get_package_model_comparison(package_id: int, db_session: Session = Depends(get_db),
                                 actor: identity.Actor = Depends(require_perm("assets:read"))):
    # v1.1 WS2: computed comparison over COMPLETED PACKAGE runs (D1 - no
    # leaderboard table). Unrun models are absent, not zero (D12). This
    # endpoint compares; selection is WS3, a governed decision.
    try:
        return evaluation.package_model_comparison(db_session, package_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/packages/{package_id}/model-selection", response_model=schemas.PackageModelSelectionResponse)
def get_package_model_selection(package_id: int, db_session: Session = Depends(get_db),
                                actor: identity.Actor = Depends(require_perm("assets:read"))):
    selection = crud.get_package_model_selection(db_session, package_id)
    if not selection:
        raise HTTPException(status_code=404, detail="No model selected for this package yet")
    return selection

@app.put("/api/packages/{package_id}/model-selection", response_model=schemas.PackageModelSelectionResponse)
def put_package_model_selection(package_id: int, update: schemas.PackageModelSelectionUpdate,
                                db_session: Session = Depends(get_db),
                                actor: identity.Actor = Depends(require_perm("assets:approve"))):
    # v1.1 WS3: selecting a model for a package is a governed decision at
    # the approval tier (the tier that compiled the package). The boundary
    # validates the supporting PACKAGE-run evidence; every change is a
    # PACKAGE_MODEL_SELECTED audit event carrying the actor's identity fact.
    try:
        return crud.set_package_model_selection(db_session, package_id, update, actor=actor)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/packages/{package_id}/bindings", response_model=List[schemas.ExpertAgentBindingResponse])
def list_expert_agent_bindings(package_id: int, db_session: Session = Depends(get_db),
                               actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.list_expert_agent_bindings(db_session, package_id)

@app.post("/api/packages/{package_id}/bindings", response_model=schemas.ExpertAgentBindingResponse)
def create_expert_agent_binding(package_id: int, create: schemas.ExpertAgentBindingCreate,
                                db_session: Session = Depends(get_db),
                                actor: identity.Actor = Depends(require_perm("assets:approve"))):
    # v1.1 WS4 (D22): issue a governed binding of the package's CURRENT
    # selected model to an existing active AGENT principal. The binding is
    # an append-only snapshot - it executes nothing, mints no tokens
    # (token issuance stays in Users & Tokens, a governed identity
    # operation), and orchestrates nothing.
    try:
        return crud.create_expert_agent_binding(db_session, package_id, create, actor=actor)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Deletion routes
@app.delete("/api/knowledge-assets/{asset_id}")
def delete_asset(asset_id: int, db_session: Session = Depends(get_db),
                 actor: identity.Actor = Depends(require_perm("assets:delete"))):
    deleted = crud.delete_knowledge_asset(db_session, asset_id, actor=actor)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": f"Asset {asset_id} deleted successfully"}

@app.delete("/api/documents/{document_id}/knowledge-assets")
def delete_document_assets(document_id: int, status: Optional[str] = None, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:delete"))):
    count = crud.delete_knowledge_assets_by_document(db_session, document_id, status=status, actor=actor)
    return {"message": f"Deleted {count} assets from document {document_id}"}

# Asset Revision Workflow routes (MVP 0.7 Sprint 4)
@app.get("/api/projects/{project_id}/revisions", response_model=List[schemas.RevisionQueueItem])
def get_project_revision_queue(project_id: int, status: Optional[str] = None, db_session: Session = Depends(get_db),
                               actor: identity.Actor = Depends(require_perm("assets:read"))):
    """Revision review queue: all revisions for the project's assets, each
    paired with its comparison baseline (the revision it supersedes)."""
    query = db_session.query(db.AssetRevision).join(
        db.KnowledgeAsset, db.AssetRevision.asset_id == db.KnowledgeAsset.id
    ).filter(db.KnowledgeAsset.project_id == project_id)
    if status:
        query = query.filter(db.AssetRevision.status == status)
    rows = query.order_by(db.AssetRevision.created_at.desc(), db.AssetRevision.id.desc()).all()

    items = []
    for rev in rows:
        asset = rev.asset
        baseline = None
        if rev.supersedes_revision_id:
            baseline = db_session.query(db.AssetRevision).filter(db.AssetRevision.id == rev.supersedes_revision_id).first()
        items.append(schemas.RevisionQueueItem(
            revision=schemas.AssetRevisionResponse.model_validate(rev),
            asset_id=asset.id,
            asset_name=asset.name,
            asset_type=asset.type,
            asset_access_level=asset.access_level,
            baseline_revision_number=baseline.revision_number if baseline else None,
            baseline_content=baseline.content if baseline else None,
            baseline_content_hash=baseline.content_hash if baseline else None,
            baseline_source_hash=baseline.source_hash if baseline else None
        ))
    return items

@app.get("/api/assets/{asset_id}/revisions", response_model=List[schemas.AssetRevisionResponse])
def get_asset_revisions(asset_id: int, db_session: Session = Depends(get_db),
                        actor: identity.Actor = Depends(require_perm("assets:read"))):
    asset = db_session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    return revisions.get_revisions(db_session, asset_id)

@app.post("/api/assets/{asset_id}/revisions", response_model=schemas.AssetRevisionResponse)
def create_asset_revision(asset_id: int, revision_in: schemas.AssetRevisionCreate, db_session: Session = Depends(get_db),
                          actor: identity.Actor = Depends(require_perm("assets:review"))):
    try:
        return revisions.create_candidate_revision(
            db_session, asset_id, revision_in.content,
            actor=actor, change_reason=revision_in.change_reason
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/revisions/{revision_id}/review", response_model=schemas.AssetRevisionResponse)
def review_asset_revision(revision_id: int, review: schemas.RevisionReviewUpdate, background_tasks: BackgroundTasks,
                          db_session: Session = Depends(get_db),
                          actor: identity.Actor = Depends(require_perm("assets:approve"))):
    try:
        revision = revisions.review_revision(
            db_session, revision_id, action=review.action,
            actor=actor, notes=review.notes
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # v0.9.2a: the approval returns immediately; the heavy NLI conflict
    # rescan of affected Expert Models runs as a background task with its
    # own session. State transition and recomputation are separate.
    if review.action == "APPROVE":
        background_tasks.add_task(revisions.run_post_approval_rescan, revision.asset_id)
    return revision

# Knowledge Integrity Engine routes (MVP 0.7: Semantic Conflict Engine)
@app.post("/api/experts/{expert_model_id}/conflict-scan", response_model=schemas.ConflictScanResponse)
def run_conflict_scan(expert_model_id: int, db_session: Session = Depends(get_db),
                      actor: identity.Actor = Depends(require_perm("assets:review"))):
    try:
        return conflict_engine.scan_expert_model_conflicts(db_session, expert_model_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/experts/{expert_model_id}/trust-score", response_model=schemas.TrustScoreResponse)
def get_expert_model_trust_score(expert_model_id: int, db_session: Session = Depends(get_db),
                                 actor: identity.Actor = Depends(require_perm("assets:read"))):
    try:
        return trust.compute_trust_score(db_session, expert_model_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/projects/{project_id}/trust-scores", response_model=List[schemas.TrustScoreResponse])
def get_project_trust_scores(project_id: int, db_session: Session = Depends(get_db),
                             actor: identity.Actor = Depends(require_perm("assets:read"))):
    models = db_session.query(db.ExpertModel).filter(db.ExpertModel.project_id == project_id).all()
    return [trust.compute_trust_score(db_session, m.id) for m in models]

@app.get("/api/experts/{expert_model_id}/conflict-score", response_model=schemas.ConflictScoreResponse)
def get_expert_model_conflict_score(expert_model_id: int, db_session: Session = Depends(get_db),
                                    actor: identity.Actor = Depends(require_perm("assets:read"))):
    expert_model = db_session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not expert_model:
        raise HTTPException(status_code=404, detail=f"Expert Model with ID {expert_model_id} not found")
    return conflict_engine.compute_semantic_conflict_score(db_session, expert_model_id)

@app.get("/api/experts/{expert_model_id}/conflicts", response_model=List[schemas.AssetRelationshipResponse])
def get_expert_model_conflicts(expert_model_id: int, relationship_type: Optional[str] = None, db_session: Session = Depends(get_db),
                               actor: identity.Actor = Depends(require_perm("assets:read"))):
    query = db_session.query(db.AssetRelationship).filter(db.AssetRelationship.expert_model_id == expert_model_id)
    if relationship_type:
        query = query.filter(db.AssetRelationship.relationship_type == relationship_type)
    return query.order_by(db.AssetRelationship.confidence.desc()).all()

@app.patch("/api/conflicts/{relationship_id}", response_model=schemas.AssetRelationshipResponse)
def review_conflict(relationship_id: int, review: schemas.ConflictReviewUpdate, db_session: Session = Depends(get_db),
                    actor: identity.Actor = Depends(require_perm("assets:approve"))):
    try:
        return conflict_engine.review_relationship(
            db_session, relationship_id, status=review.status, reviewer=actor, notes=review.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Governance Inbox & Readiness Console (MVP 0.9.1): a computed operational
# index over existing reviewable records. Read-only - all review actions
# stay on the specialized workbench endpoints above.
@app.get("/api/projects/{project_id}/governance/inbox")
def get_governance_inbox(project_id: int, db_session: Session = Depends(get_db),
                         actor: identity.Actor = Depends(require_perm("assets:read"))):
    project = db_session.query(db.Project).filter(db.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return governance_inbox.build_inbox(db_session, project_id)

# Persisted Verification Verdicts (MVP 0.9.2). A verdict is an immutable
# measurement: reviewing one records a VERIFICATION_REVIEWED audit event and
# never mutates the ClaimVerdict row. Remediation happens on the asset or
# revision; the next evaluation run produces fresh verdicts.
# Answer Coverage Governance (MVP 0.9.3): trend over persisted run facts.
@app.get("/api/experts/{expert_model_id}/coverage-trend")
def get_expert_coverage_trend(expert_model_id: int, db_session: Session = Depends(get_db),
                              actor: identity.Actor = Depends(require_perm("assets:read"))):
    model = db_session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Expert Model {expert_model_id} not found")
    return evaluation.coverage_trend(db_session, expert_model_id)

@app.get("/api/evaluations/{run_id}/verdicts", response_model=List[schemas.ClaimVerdictResponse])
def get_run_claim_verdicts(run_id: int, verdict: Optional[str] = None, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:read"))):
    query = db_session.query(db.ClaimVerdict).filter(db.ClaimVerdict.evaluation_run_id == run_id)
    if verdict:
        query = query.filter(db.ClaimVerdict.verdict == verdict)
    return query.order_by(db.ClaimVerdict.id).all()

@app.post("/api/claim-verdicts/{verdict_id}/review")
def review_claim_verdict(verdict_id: int, review: schemas.VerificationReviewCreate, db_session: Session = Depends(get_db),
                         actor: identity.Actor = Depends(require_perm("assets:review"))):
    v = db_session.query(db.ClaimVerdict).filter(db.ClaimVerdict.id == verdict_id).first()
    if not v:
        raise HTTPException(status_code=404, detail=f"Claim verdict {verdict_id} not found")
    crud.log_audit_event(
        db_session,
        actor=actor.display,
        identity_fact_id=actor.fact(db_session).id,
        event_type="VERIFICATION_REVIEWED",
        target_id=str(v.id),
        details=json.dumps({
            "claim_verdict_id": v.id,
            "claim": v.claim,
            "verdict_seen": v.verdict,
            "confidence_seen": v.confidence,
            "expert_model_id": v.expert_model_id,
            "evaluation_run_id": v.evaluation_run_id,
            "question_result_id": v.question_result_id,
            "comment": review.comment
        })
    )
    return {"claim_verdict_id": v.id, "reviewed_by": actor.display, "event_type": "VERIFICATION_REVIEWED"}

