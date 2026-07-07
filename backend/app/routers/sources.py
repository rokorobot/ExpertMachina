"""Sources routes (audit T2.4, relocated VERBATIM from app/main.py).

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


# Enterprise Source Connector routes (MVP 0.10.0): LOCAL_FOLDER, scan-now
# only. Connector output becomes ordinary documents and CANDIDATE assets in
# the existing governance pipeline - no connector-specific review flow.
@router.post("/api/projects/{project_id}/connectors", response_model=schemas.SourceConnectorResponse)
def create_source_connector(project_id: int, connector_in: schemas.SourceConnectorCreate, db_session: Session = Depends(get_db),
                            actor: identity.Actor = Depends(require_perm("connectors:manage"))):
    ctype = (connector_in.type or "LOCAL_FOLDER").upper()
    if ctype not in ("LOCAL_FOLDER", "SHAREPOINT"):
        raise HTTPException(status_code=400, detail="Supported connector types: LOCAL_FOLDER, SHAREPOINT")
    if not connector_in.root_path.strip():
        raise HTTPException(status_code=400, detail="root_path is required")
    # v1.4.0 WS1 (D29/D30): the lane is a governed channel declaration.
    # PROPOSAL marks the agent-finding return path - its candidates are
    # constitutionally outside every policy tier (held for the human
    # gate) and become DERIVED facts on acceptance.
    lane = (connector_in.lane or "PRIMARY").upper()
    if lane not in ("PRIMARY", "PROPOSAL"):
        raise HTTPException(status_code=400, detail="lane must be PRIMARY or PROPOSAL")
    # v1.2.0 WS2: a SHAREPOINT connector authenticates outward, so it MUST
    # reference a stored credential (D25: by id, never by value). root_path
    # is the site URL, optionally '::LibraryName'.
    if ctype == "SHAREPOINT" and connector_in.external_credential_id is None:
        raise HTTPException(status_code=400,
                            detail="SHAREPOINT connectors require external_credential_id - "
                                   "bind an ACTIVE CONNECTOR credential (Settings requires "
                                   "credentials:manage to create one)")
    # v1.2.0 (D25): BINDING a credential to a connector is a custody act -
    # payload-dependent authorization, the transition-permission pattern.
    # connectors:manage creates connectors; directing EM to authenticate
    # outward with a specific stored secret needs credentials:manage.
    if connector_in.external_credential_id is not None:
        _authorize_or_403(db_session, actor, "credentials:manage")
        bound = custody.get_external_credential(db_session, connector_in.external_credential_id)
        if bound is None:
            raise HTTPException(status_code=404, detail=f"Credential {connector_in.external_credential_id} not found")
        if bound.status != "ACTIVE":
            raise HTTPException(status_code=409, detail=f"Credential {bound.fingerprint} is {bound.status}; bind an ACTIVE credential")
        if bound.purpose != "CONNECTOR":
            raise HTTPException(status_code=409, detail=f"Credential {bound.fingerprint} has purpose {bound.purpose}, not CONNECTOR")
    connector = db.SourceConnector(
        project_id=project_id,
        name=connector_in.name,
        type=ctype,
        root_path=connector_in.root_path.strip(),
        include_extensions=connector_in.include_extensions or ".txt,.md,.pdf,.docx",
        external_credential_id=connector_in.external_credential_id,
        lane=lane,
    )
    db_session.add(connector)
    db_session.commit()
    db_session.refresh(connector)
    identity.ensure_delegated_principal(db_session, f"connector:{connector.name}",
                                        created_by=actor.name)
    bound_fingerprint = None
    if connector.external_credential_id is not None:
        bound_fingerprint = custody.get_external_credential(
            db_session, connector.external_credential_id).fingerprint
    crud.log_audit_event(db_session, actor=actor.display, event_type="SOURCE_CONNECTOR_CREATED",
                         target_id=str(connector.id),
                         details=json.dumps({"name": connector.name, "type": connector.type,
                                             "root_path": connector.root_path,
                                             "external_credential_id": connector.external_credential_id,
                                             "external_credential_fingerprint": bound_fingerprint,
                                             "lane": connector.lane}),
                         identity_fact_id=actor.fact(db_session).id)
    return connector

@router.get("/api/projects/{project_id}/connectors", response_model=List[schemas.SourceConnectorResponse])
def list_source_connectors(project_id: int, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:read"))):
    return db_session.query(db.SourceConnector).filter(
        db.SourceConnector.project_id == project_id).order_by(db.SourceConnector.id).all()

@router.post("/api/connectors/{connector_id}/scan", response_model=schemas.IngestionJobResponse)
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

@router.get("/api/projects/{project_id}/ingestion-jobs", response_model=List[schemas.IngestionJobResponse])
def list_ingestion_jobs(project_id: int, db_session: Session = Depends(get_db),
                        actor: identity.Actor = Depends(require_perm("assets:read"))):
    return db_session.query(db.IngestionJob).filter(
        db.IngestionJob.project_id == project_id).order_by(db.IngestionJob.id.desc()).all()

@router.get("/api/ingestion-jobs/{job_id}", response_model=schemas.IngestionJobResponse)
def get_ingestion_job(job_id: int, db_session: Session = Depends(get_db),
                      actor: identity.Actor = Depends(require_perm("assets:read"))):
    job = db_session.query(db.IngestionJob).filter(db.IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Ingestion job {job_id} not found")
    return job

@router.get("/api/ingestion-jobs/{job_id}/files", response_model=List[schemas.SourceDocumentResponse])
def list_ingestion_job_files(job_id: int, status: Optional[str] = None, db_session: Session = Depends(get_db),
                             actor: identity.Actor = Depends(require_perm("assets:read"))):
    query = db_session.query(db.SourceDocument).filter(db.SourceDocument.ingestion_job_id == job_id)
    if status:
        query = query.filter(db.SourceDocument.status == status.upper())
    return query.order_by(db.SourceDocument.id).all()

# Outbound credential custody routes (v1.2.0 WS1, D25). ALL custody
# administration - create, rotate, revoke, metadata reads - sits behind
# credentials:manage (ADMIN-only via the matrix). There is NO reveal
# endpoint and never will be one: the operator supplied the secret;
# responses carry metadata only (the response schema has no field secret
# material could serialize through). USING a bound credential is a scan
# under connectors:manage - custody.release decides, per scan, audited.
@router.post("/api/credentials", response_model=schemas.ExternalCredentialResponse)
def create_external_credential(body: schemas.ExternalCredentialCreate,
                               db_session: Session = Depends(get_db),
                               actor: identity.Actor = Depends(require_perm("credentials:manage"))):
    try:
        return custody.create_external_credential(
            db_session, name=body.name, purpose=body.purpose.upper().strip(),
            secret=body.secret, actor=actor,
            granted_scopes=body.granted_scopes, coordinates=body.coordinates)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/credentials", response_model=List[schemas.ExternalCredentialResponse])
def list_external_credentials(db_session: Session = Depends(get_db),
                              actor: identity.Actor = Depends(require_perm("credentials:manage"))):
    return db_session.query(db.ExternalCredential).order_by(db.ExternalCredential.id).all()

@router.get("/api/credentials/{credential_id}", response_model=schemas.ExternalCredentialDetailResponse)
def get_external_credential_detail(credential_id: int, db_session: Session = Depends(get_db),
                                   actor: identity.Actor = Depends(require_perm("credentials:manage"))):
    cred = custody.get_external_credential(db_session, credential_id)
    if not cred:
        raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
    # Custody history: computed projection of the ledger (D24 posture) -
    # every custody event carries the fingerprint, so the join is exact.
    events = db_session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type.in_([
            "EXTERNAL_CREDENTIAL_CREATED", "EXTERNAL_CREDENTIAL_ROTATED",
            "EXTERNAL_CREDENTIAL_REVOKED", "EXTERNAL_CREDENTIAL_USED",
            "EXTERNAL_CREDENTIAL_RELEASE_REFUSED"]),
        db.AuditEvent.target_id == str(cred.id)).order_by(db.AuditEvent.id).all()
    detail = schemas.ExternalCredentialDetailResponse.model_validate(cred)
    detail.custody_events = [{
        "event_type": e.event_type, "timestamp": e.timestamp.isoformat(),
        "actor": e.actor, "identity_fact_id": e.identity_fact_id,
        "details": json.loads(e.details) if e.details else None,
    } for e in events]
    return detail

@router.post("/api/credentials/{credential_id}/rotate", response_model=schemas.ExternalCredentialResponse)
def rotate_external_credential(credential_id: int, body: schemas.ExternalCredentialRotate,
                               db_session: Session = Depends(get_db),
                               actor: identity.Actor = Depends(require_perm("credentials:manage"))):
    cred = custody.get_external_credential(db_session, credential_id)
    if not cred:
        raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
    try:
        return custody.rotate_external_credential(
            db_session, cred, new_secret=body.secret, actor=actor,
            granted_scopes=body.granted_scopes, coordinates=body.coordinates)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/api/credentials/{credential_id}/revoke", response_model=schemas.ExternalCredentialResponse)
def revoke_external_credential(credential_id: int, body: schemas.ExternalCredentialRevoke,
                               db_session: Session = Depends(get_db),
                               actor: identity.Actor = Depends(require_perm("credentials:manage"))):
    cred = custody.get_external_credential(db_session, credential_id)
    if not cred:
        raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
    try:
        return custody.revoke_external_credential(db_session, cred, actor=actor, reason=body.reason)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/api/credentials/rotate-master-key", response_model=schemas.MasterKeyRotationResponse)
def rotate_master_key(db_session: Session = Depends(get_db),
                      actor: identity.Actor = Depends(require_perm("credentials:manage"))):
    # Key material arrives via the ENVIRONMENT only (EM_SECRET_KEY = new,
    # EM_SECRET_KEY_PREVIOUS = old) - master keys never transit request
    # bodies, responses, or logs. Re-wraps data keys; secrets untouched.
    try:
        return custody.rewrap_master_key(
            db_session,
            old_master=os.environ.get("EM_SECRET_KEY_PREVIOUS"),
            new_master=os.environ.get("EM_SECRET_KEY"),
            actor=actor)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=409, detail=str(e))
