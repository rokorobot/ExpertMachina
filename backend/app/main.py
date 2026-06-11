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

# Initialize FastAPI app
app = FastAPI(title="ExpertMachina MVP Backend", version="0.1.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow all
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
    file_path = os.path.join(UPLOAD_DIR, f"{project_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    doc = crud.create_document(
        db_session, 
        project_id=project_id, 
        filename=file.filename, 
        file_path=file_path,
        department=department,
        owner=owner
    )
    
    # Process asynchronously (for MVP sync parsing is fast enough, we execute inline)
    ingestion.parse_and_index_document(db_session, doc.id)
    db_session.refresh(doc)
    
    if doc.status == "PARSED":
        extraction.extract_knowledge_assets_from_project(db_session, project_id)
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

# Knowledge Assets routes
@app.get("/api/projects/{project_id}/assets", response_model=List[schemas.KnowledgeAssetResponse])
def get_assets(project_id: int, db_session: Session = Depends(get_db)):
    return crud.get_knowledge_assets(db_session, project_id)

@app.post("/api/projects/{project_id}/extract")
def extract_assets(project_id: int, db_session: Session = Depends(get_db)):
    success = extraction.extract_knowledge_assets_from_project(db_session, project_id)
    if not success:
        raise HTTPException(status_code=400, detail="No parsed documents found to extract assets from. Please upload documents first.")
    return {"message": "Knowledge assets extracted successfully."}

@app.patch("/api/assets/{asset_id}", response_model=schemas.KnowledgeAssetResponse)
def update_asset(asset_id: int, update: schemas.KnowledgeAssetUpdate, actor: str = "User", db_session: Session = Depends(get_db)):
    asset = crud.update_knowledge_asset(db_session, asset_id, update, actor=actor)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@app.patch("/api/assets/bulk", response_model=List[schemas.KnowledgeAssetResponse])
def bulk_update_assets(bulk_in: schemas.AssetBulkUpdate, actor: str = "User", db_session: Session = Depends(get_db)):
    updated_assets = []
    affected_doc_ids = set()
    for asset_id in bulk_in.asset_ids:
        asset = db_session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
        if asset:
            old_st = asset.status
            asset.status = bulk_in.status
            db_session.commit()
            db_session.refresh(asset)
            
            event_t = "ASSET_REVIEWED" if bulk_in.status == "REVIEWED" else "ASSET_APPROVED" if bulk_in.status == "APPROVED" else "ASSET_UPDATED"
            crud.log_audit_event(db_session, actor=actor, event_type=event_t, target_id=str(asset.id), details=f"Asset status updated from {old_st} to {bulk_in.status} via bulk update")
            if bulk_in.status == "APPROVED" and old_st != "APPROVED":
                db_session.add(db.AssetReview(asset_id=asset.id, approver=actor, notes=f"Approved via bulk update (from {old_st})"))
                db_session.commit()
            
            if asset.document_id:
                affected_doc_ids.add(asset.document_id)
            updated_assets.append(asset)
            
    for doc_id in affected_doc_ids:
        crud.update_document_lifecycle(db_session, doc_id)
        
    return updated_assets


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
def review_asset_revision(revision_id: int, review: schemas.RevisionReviewUpdate, db_session: Session = Depends(get_db)):
    try:
        return revisions.review_revision(
            db_session, revision_id, action=review.action,
            actor=review.reviewer, notes=review.notes
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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

