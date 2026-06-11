import os
import shutil
import hashlib
import json
import datetime
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from app import database as db
from app import schemas
from app import crud
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

@app.on_event("startup")
def startup_event():
    db.init_db()
    with db.SessionLocal() as session:
        # Create default customer
        crud.get_or_create_default_customer(session)

# Status Check
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "ExpertMachina Backend"}

# Customer / Workspace Project routes
@app.get("/api/projects", response_model=List[schemas.ProjectResponse])
def get_projects(db_session: Session = Depends(get_db)):
    cust = crud.get_or_create_default_customer(db_session)
    return crud.get_projects(db_session, customer_id=cust.id)

@app.post("/api/projects", response_model=schemas.ProjectResponse)
def create_project(project: schemas.ProjectCreate, db_session: Session = Depends(get_db)):
    return crud.create_project(db_session, project)

# Documents routes
@app.get("/api/projects/{project_id}/documents", response_model=List[schemas.DocumentResponse])
def get_documents(project_id: int, db_session: Session = Depends(get_db)):
    return crud.get_documents(db_session, project_id)

@app.post("/api/projects/{project_id}/documents", response_model=schemas.DocumentResponse)
def upload_document(
    project_id: int, 
    file: UploadFile = File(...), 
    department: str = Form("General"), 
    owner: str = Form("User"),
    db_session: Session = Depends(get_db)
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
        owner=owner
    )
    
    # Process asynchronously (for MVP sync parsing is fast enough, we execute inline)
    ingestion.parse_and_index_document(db_session, doc.id)
    db_session.refresh(doc)
    
    if doc.status == "PARSED":
        extraction.extract_knowledge_assets_from_project(db_session, project_id)
        # Policy-Based Auto Approval (MVP 0.10.2): unscoped policies apply to
        # uploads too - the same rules regardless of how a document arrived.
        policy.apply_auto_approval(db_session, project_id, [doc.id])
        db_session.refresh(doc)

    return doc

@app.post("/api/projects/{project_id}/documents/batch-demo")
def upload_batch_demo(project_id: int, db_session: Session = Depends(get_db)):
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
            owner=d["owner"]
        )
        ingestion.parse_and_index_document(db_session, doc.id)
        docs_created.append(doc.filename)
        
    return {"message": "Batch demo SOP documents uploaded and parsed successfully", "documents": docs_created}

# Enterprise Source Connector routes (MVP 0.10.0): LOCAL_FOLDER, scan-now
# only. Connector output becomes ordinary documents and CANDIDATE assets in
# the existing governance pipeline - no connector-specific review flow.
@app.post("/api/projects/{project_id}/connectors", response_model=schemas.SourceConnectorResponse)
def create_source_connector(project_id: int, connector_in: schemas.SourceConnectorCreate, db_session: Session = Depends(get_db)):
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
    crud.log_audit_event(db_session, actor="operator", event_type="SOURCE_CONNECTOR_CREATED",
                         target_id=str(connector.id),
                         details=json.dumps({"name": connector.name, "type": connector.type,
                                             "root_path": connector.root_path}))
    return connector

@app.get("/api/projects/{project_id}/connectors", response_model=List[schemas.SourceConnectorResponse])
def list_source_connectors(project_id: int, db_session: Session = Depends(get_db)):
    return db_session.query(db.SourceConnector).filter(
        db.SourceConnector.project_id == project_id).order_by(db.SourceConnector.id).all()

@app.post("/api/connectors/{connector_id}/scan", response_model=schemas.IngestionJobResponse)
def scan_source_connector(connector_id: int, background_tasks: BackgroundTasks, db_session: Session = Depends(get_db)):
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
    background_tasks.add_task(connectors.run_ingestion_job, job.id)
    return job

@app.get("/api/projects/{project_id}/ingestion-jobs", response_model=List[schemas.IngestionJobResponse])
def list_ingestion_jobs(project_id: int, db_session: Session = Depends(get_db)):
    return db_session.query(db.IngestionJob).filter(
        db.IngestionJob.project_id == project_id).order_by(db.IngestionJob.id.desc()).all()

@app.get("/api/ingestion-jobs/{job_id}", response_model=schemas.IngestionJobResponse)
def get_ingestion_job(job_id: int, db_session: Session = Depends(get_db)):
    job = db_session.query(db.IngestionJob).filter(db.IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Ingestion job {job_id} not found")
    return job

@app.get("/api/ingestion-jobs/{job_id}/files", response_model=List[schemas.SourceDocumentResponse])
def list_ingestion_job_files(job_id: int, status: Optional[str] = None, db_session: Session = Depends(get_db)):
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
def create_approval_policy(project_id: int, policy_in: schemas.ApprovalPolicyCreate, db_session: Session = Depends(get_db)):
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
        created_by=policy_in.created_by or "operator",
    )
    db_session.add(pol)
    db_session.commit()
    db_session.refresh(pol)
    crud.log_audit_event(db_session, actor=pol.created_by, event_type="POLICY_CREATED",
                         target_id=str(pol.id),
                         details=json.dumps({"name": pol.name, "version": pol.version,
                                             "asset_types": types, "connector_id": pol.connector_id}))
    return pol

@app.get("/api/projects/{project_id}/approval-policies", response_model=List[schemas.ApprovalPolicyResponse])
def list_approval_policies(project_id: int, db_session: Session = Depends(get_db)):
    return db_session.query(db.ApprovalPolicy).filter(
        db.ApprovalPolicy.project_id == project_id).order_by(db.ApprovalPolicy.id).all()

@app.patch("/api/approval-policies/{policy_id}", response_model=schemas.ApprovalPolicyResponse)
def update_approval_policy(policy_id: int, update: schemas.ApprovalPolicyUpdate, actor: str = "operator",
                           db_session: Session = Depends(get_db)):
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
        crud.log_audit_event(db_session, actor=actor, event_type="POLICY_UPDATED",
                             target_id=str(pol.id),
                             details=json.dumps({"old": old_snapshot,
                                                 "new": {"name": pol.name, "asset_types": pol.asset_types,
                                                         "connector_id": pol.connector_id, "version": pol.version}}))
    if toggled is not None:
        crud.log_audit_event(db_session, actor=actor,
                             event_type="POLICY_ENABLED" if toggled else "POLICY_DISABLED",
                             target_id=str(pol.id),
                             details=json.dumps({"name": pol.name, "version": pol.version}))
    return pol

# Knowledge Assets routes
@app.get("/api/projects/{project_id}/assets", response_model=List[schemas.KnowledgeAssetResponse])
def get_assets(project_id: int, db_session: Session = Depends(get_db)):
    return crud.get_knowledge_assets(db_session, project_id)

@app.post("/api/projects/{project_id}/extract")
def extract_assets(project_id: int, db_session: Session = Depends(get_db)):
    # Documents without assets BEFORE extraction are the ones this call will
    # extract for - the auto-approval scope for this ingestion event.
    fresh_doc_ids = [d.id for d in db_session.query(db.Document).filter(
        db.Document.project_id == project_id, db.Document.status == "PARSED").all()
        if not db_session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.document_id == d.id).first()]
    success = extraction.extract_knowledge_assets_from_project(db_session, project_id)
    if not success:
        raise HTTPException(status_code=400, detail="No parsed documents found to extract assets from. Please upload documents first.")
    auto_approval = policy.apply_auto_approval(db_session, project_id, fresh_doc_ids)
    return {"message": "Knowledge assets extracted successfully.", "auto_approval": auto_approval}

# NOTE: /api/assets/bulk MUST be registered BEFORE /api/assets/{asset_id} -
# FastAPI matches routes in registration order, and the dynamic route would
# otherwise swallow "bulk" and 422 on int parsing (audit finding C1: the
# bulk endpoint was unreachable from v0.2 until this fix).
@app.patch("/api/assets/bulk", response_model=List[schemas.KnowledgeAssetResponse])
def bulk_update_assets(bulk_in: schemas.AssetBulkUpdate, actor: str = "User", db_session: Session = Depends(get_db)):
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
def update_asset(asset_id: int, update: schemas.KnowledgeAssetUpdate, actor: str = "User", db_session: Session = Depends(get_db)):
    asset = crud.update_knowledge_asset(db_session, asset_id, update, actor=actor)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# Expert Models routes
@app.get("/api/projects/{project_id}/experts", response_model=List[schemas.ExpertModelResponse])
def get_experts(project_id: int, db_session: Session = Depends(get_db)):
    return crud.get_expert_models(db_session, project_id)

@app.post("/api/projects/{project_id}/experts", response_model=schemas.ExpertModelResponse)
def create_expert(project_id: int, expert_in: schemas.ExpertModelCreate, db_session: Session = Depends(get_db)):
    # Validate project_id matches
    if expert_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    try:
        return crud.create_expert_model(db_session, expert_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/api/projects/{project_id}/query", response_model=schemas.QueryResponse)
def execute_query(project_id: int, query_in: schemas.QueryInput, db_session: Session = Depends(get_db)):
    if not query_in.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Single shared pipeline (Verified Answer v1) - also used by the MCP gateway.
    result = query_engine.execute_expert_query(
        db_session,
        expert_model_id=query_in.expert_model_id,
        question=query_in.question,
        caller_access_level=query_in.access_level,
        actor="operator_admin_02"
    )
    return schemas.QueryResponse(**result)

# Agent Packages routes
@app.get("/api/projects/{project_id}/packages", response_model=List[schemas.AgentPackageResponse])
def get_packages(project_id: int, db_session: Session = Depends(get_db)):
    return crud.get_agent_packages(db_session, project_id)

@app.post("/api/projects/{project_id}/packages", response_model=schemas.AgentPackageResponse)
def create_package(project_id: int, pkg_in: schemas.AgentPackageCreate, db_session: Session = Depends(get_db)):
    if pkg_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    try:
        pkg = crud.create_agent_package(db_session, pkg_in)
    except ValueError as e:
        # Governance gate block: 409 Conflict, with the reason for the operator.
        raise HTTPException(status_code=409, detail=str(e))
    if not pkg:
        raise HTTPException(status_code=404, detail="Expert model not found")
    return pkg

# Agent Package Builder (MVP 0.9.4): download the compiled .empkg artifact.
@app.get("/api/packages/{package_id}/download")
def download_agent_package(package_id: int, db_session: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    pkg = db_session.query(db.AgentPackage).filter(db.AgentPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    if not pkg.file_path or not os.path.exists(pkg.file_path):
        raise HTTPException(status_code=404, detail="Package artifact not found on disk (compiled before MVP 0.9.4 or file removed)")
    return FileResponse(pkg.file_path, media_type="application/zip",
                        filename=os.path.basename(pkg.file_path))

@app.get("/api/experts/{expert_model_id}/compile-gate")
def get_compile_gate(expert_model_id: int, db_session: Session = Depends(get_db)):
    expert_model = db_session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not expert_model:
        raise HTTPException(status_code=404, detail=f"Expert Model with ID {expert_model_id} not found")
    return conflict_engine.evaluate_compile_gate(db_session, expert_model_id)

# Agent Center: gateway activity aggregated from the audit ledger.
@app.get("/api/agents/activity")
def get_agent_activity(db_session: Session = Depends(get_db)):
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
    db_session: Session = Depends(get_db)
):
    return crud.get_audit_events(
        db_session, limit=limit, event_prefix=event_prefix,
        actor=actor, target_id=target_id, since=since, until=until
    )

# Dashboard summaries
@app.get("/api/dashboard/{project_id}")
def get_dashboard_summary(project_id: int, db_session: Session = Depends(get_db)):
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
def get_benchmarks(project_id: int, limit: int = 100, db_session: Session = Depends(get_db)):
    return crud.get_benchmark_questions(db_session, project_id, limit=limit)

@app.post("/api/projects/{project_id}/benchmarks", response_model=schemas.BenchmarkQuestionResponse)
def create_benchmark(project_id: int, q_in: schemas.BenchmarkQuestionCreate, db_session: Session = Depends(get_db)):
    if q_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    return crud.create_benchmark_question(db_session, q_in)

@app.put("/api/projects/{project_id}/benchmarks/{benchmark_id}", response_model=schemas.BenchmarkQuestionResponse)
def update_benchmark(project_id: int, benchmark_id: int, q_update: schemas.BenchmarkQuestionUpdate, db_session: Session = Depends(get_db)):
    q = crud.get_benchmark_question(db_session, benchmark_id)
    if not q or q.project_id != project_id:
        raise HTTPException(status_code=404, detail="Benchmark question not found")
    updated = crud.update_benchmark_question(db_session, benchmark_id, q_update)
    return updated

@app.delete("/api/projects/{project_id}/benchmarks/{benchmark_id}")
def delete_benchmark(project_id: int, benchmark_id: int, db_session: Session = Depends(get_db)):
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
    db_session: Session = Depends(get_db)
):
    if run_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    
    try:
        db_run = evaluation.create_evaluation_run(db_session, run_in)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    # Trigger execution in the background
    background_tasks.add_task(evaluation.run_evaluation_batch, db_session, db_run.id)
    return db_run

@app.get("/api/projects/{project_id}/evaluations", response_model=List[schemas.EvaluationRunResponse])
def list_evaluations(project_id: int, db_session: Session = Depends(get_db)):
    return db_session.query(db.EvaluationRun).filter(db.EvaluationRun.project_id == project_id).order_by(db.EvaluationRun.started_at.desc()).all()

@app.get("/api/projects/{project_id}/evaluations/{run_id}", response_model=schemas.EvaluationRunResponse)
def get_evaluation(project_id: int, run_id: int, db_session: Session = Depends(get_db)):
    run = db_session.query(db.EvaluationRun).filter(db.EvaluationRun.id == run_id, db.EvaluationRun.project_id == project_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return run

# Deletion routes
@app.delete("/api/knowledge-assets/{asset_id}")
def delete_asset(asset_id: int, actor: str = "GovernanceOfficer", db_session: Session = Depends(get_db)):
    deleted = crud.delete_knowledge_asset(db_session, asset_id, actor=actor)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": f"Asset {asset_id} deleted successfully"}

@app.delete("/api/documents/{document_id}/knowledge-assets")
def delete_document_assets(document_id: int, status: Optional[str] = None, actor: str = "GovernanceOfficer", db_session: Session = Depends(get_db)):
    count = crud.delete_knowledge_assets_by_document(db_session, document_id, status=status, actor=actor)
    return {"message": f"Deleted {count} assets from document {document_id}"}

# Asset Revision Workflow routes (MVP 0.7 Sprint 4)
@app.get("/api/projects/{project_id}/revisions", response_model=List[schemas.RevisionQueueItem])
def get_project_revision_queue(project_id: int, status: Optional[str] = None, db_session: Session = Depends(get_db)):
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
def get_asset_revisions(asset_id: int, db_session: Session = Depends(get_db)):
    asset = db_session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    return revisions.get_revisions(db_session, asset_id)

@app.post("/api/assets/{asset_id}/revisions", response_model=schemas.AssetRevisionResponse)
def create_asset_revision(asset_id: int, revision_in: schemas.AssetRevisionCreate, db_session: Session = Depends(get_db)):
    try:
        return revisions.create_candidate_revision(
            db_session, asset_id, revision_in.content,
            actor=revision_in.actor, change_reason=revision_in.change_reason
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/revisions/{revision_id}/review", response_model=schemas.AssetRevisionResponse)
def review_asset_revision(revision_id: int, review: schemas.RevisionReviewUpdate, background_tasks: BackgroundTasks, db_session: Session = Depends(get_db)):
    try:
        revision = revisions.review_revision(
            db_session, revision_id, action=review.action,
            actor=review.reviewer, notes=review.notes
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
def run_conflict_scan(expert_model_id: int, db_session: Session = Depends(get_db)):
    try:
        return conflict_engine.scan_expert_model_conflicts(db_session, expert_model_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/experts/{expert_model_id}/trust-score", response_model=schemas.TrustScoreResponse)
def get_expert_model_trust_score(expert_model_id: int, db_session: Session = Depends(get_db)):
    try:
        return trust.compute_trust_score(db_session, expert_model_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/projects/{project_id}/trust-scores", response_model=List[schemas.TrustScoreResponse])
def get_project_trust_scores(project_id: int, db_session: Session = Depends(get_db)):
    models = db_session.query(db.ExpertModel).filter(db.ExpertModel.project_id == project_id).all()
    return [trust.compute_trust_score(db_session, m.id) for m in models]

@app.get("/api/experts/{expert_model_id}/conflict-score", response_model=schemas.ConflictScoreResponse)
def get_expert_model_conflict_score(expert_model_id: int, db_session: Session = Depends(get_db)):
    expert_model = db_session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not expert_model:
        raise HTTPException(status_code=404, detail=f"Expert Model with ID {expert_model_id} not found")
    return conflict_engine.compute_semantic_conflict_score(db_session, expert_model_id)

@app.get("/api/experts/{expert_model_id}/conflicts", response_model=List[schemas.AssetRelationshipResponse])
def get_expert_model_conflicts(expert_model_id: int, relationship_type: Optional[str] = None, db_session: Session = Depends(get_db)):
    query = db_session.query(db.AssetRelationship).filter(db.AssetRelationship.expert_model_id == expert_model_id)
    if relationship_type:
        query = query.filter(db.AssetRelationship.relationship_type == relationship_type)
    return query.order_by(db.AssetRelationship.confidence.desc()).all()

@app.patch("/api/conflicts/{relationship_id}", response_model=schemas.AssetRelationshipResponse)
def review_conflict(relationship_id: int, review: schemas.ConflictReviewUpdate, db_session: Session = Depends(get_db)):
    try:
        return conflict_engine.review_relationship(
            db_session, relationship_id, status=review.status, reviewer=review.reviewer, notes=review.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Governance Inbox & Readiness Console (MVP 0.9.1): a computed operational
# index over existing reviewable records. Read-only - all review actions
# stay on the specialized workbench endpoints above.
@app.get("/api/projects/{project_id}/governance/inbox")
def get_governance_inbox(project_id: int, db_session: Session = Depends(get_db)):
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
def get_expert_coverage_trend(expert_model_id: int, db_session: Session = Depends(get_db)):
    model = db_session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Expert Model {expert_model_id} not found")
    return evaluation.coverage_trend(db_session, expert_model_id)

@app.get("/api/evaluations/{run_id}/verdicts", response_model=List[schemas.ClaimVerdictResponse])
def get_run_claim_verdicts(run_id: int, verdict: Optional[str] = None, db_session: Session = Depends(get_db)):
    query = db_session.query(db.ClaimVerdict).filter(db.ClaimVerdict.evaluation_run_id == run_id)
    if verdict:
        query = query.filter(db.ClaimVerdict.verdict == verdict)
    return query.order_by(db.ClaimVerdict.id).all()

@app.post("/api/claim-verdicts/{verdict_id}/review")
def review_claim_verdict(verdict_id: int, review: schemas.VerificationReviewCreate, db_session: Session = Depends(get_db)):
    v = db_session.query(db.ClaimVerdict).filter(db.ClaimVerdict.id == verdict_id).first()
    if not v:
        raise HTTPException(status_code=404, detail=f"Claim verdict {verdict_id} not found")
    crud.log_audit_event(
        db_session,
        actor=review.reviewer or "operator",
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
    return {"claim_verdict_id": v.id, "reviewed_by": review.reviewer, "event_type": "VERIFICATION_REVIEWED"}

