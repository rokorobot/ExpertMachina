"""Projects routes (audit T2.4, relocated VERBATIM from app/main.py).

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


# Customer / Workspace Project routes
@router.get("/api/projects", response_model=List[schemas.ProjectResponse])
def get_projects(db_session: Session = Depends(get_db),
                 actor: identity.Actor = Depends(require_perm("assets:read"))):
    cust = crud.get_or_create_default_customer(db_session)
    return crud.get_projects(db_session, customer_id=cust.id)

@router.post("/api/projects", response_model=schemas.ProjectResponse)
def create_project(project: schemas.ProjectCreate, db_session: Session = Depends(get_db),
                   actor: identity.Actor = Depends(require_perm("documents:ingest"))):
    return crud.create_project(db_session, project, actor=actor)

# Documents routes
@router.get("/api/projects/{project_id}/documents", response_model=List[schemas.DocumentResponse])
def get_documents(project_id: int, db_session: Session = Depends(get_db),
                  actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.get_documents(db_session, project_id)

@router.post("/api/projects/{project_id}/documents", response_model=schemas.DocumentResponse)
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
        # Domain classification before approval (v1.2.1 WS1, D27): the
        # same order everywhere, so approval policies can consume domains.
        classification.classify_assets(db_session, project_id, [doc.id],
                                       on_behalf_of_fact=actor.fact(db_session))
        # Policy-Based Auto Approval (MVP 0.10.2): unscoped policies apply to
        # uploads too - the same rules regardless of how a document arrived.
        # The firing policy's identity chains to the uploader's fact.
        policy.apply_auto_approval(db_session, project_id, [doc.id],
                                   on_behalf_of_fact=actor.fact(db_session))
        # Tier-2 async (D4): scheduled only; the pass reports itself.
        if tier2.tier2_policies_in_scope(db_session, project_id):
            tier2.schedule_pass(project_id, [doc.id],
                                on_behalf_of_fact_id=actor.fact(db_session).id)
        db_session.refresh(doc)

    return doc

@router.post("/api/projects/{project_id}/documents/batch-demo")
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
