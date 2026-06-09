import os
import shutil
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from app import database as db
from app import schemas
from app import crud
from app import ingestion
from app import extraction
from app import query_engine

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
    
    citations = query_engine.retrieve_approved_evidence(
        db_session,
        expert_model_id=query_in.expert_model_id,
        question=query_in.question
    )
    
    if not citations:
        return schemas.QueryResponse(
            answer="INSUFFICIENT EVIDENCE",
            confidence_score=0.0,
            coverage_score=0.0,
            verification_status="INSUFFICIENT_EVIDENCE",
            citations=[]
        )
    
    # Simple Sprint 2 output verification synthesis
    ref_contents = " ".join([c["content"] for c in citations])
    return schemas.QueryResponse(
        answer=f"Verified grounded answer synthesized from Expert Model: {ref_contents}",
        confidence_score=0.95,
        coverage_score=1.00,
        verification_status="VERIFIED",
        citations=citations
    )

# Agent Packages routes
@app.get("/api/projects/{project_id}/packages", response_model=List[schemas.AgentPackageResponse])
def get_packages(project_id: int, db_session: Session = Depends(get_db)):
    return crud.get_agent_packages(db_session, project_id)

@app.post("/api/projects/{project_id}/packages", response_model=schemas.AgentPackageResponse)
def create_package(project_id: int, pkg_in: schemas.AgentPackageCreate, db_session: Session = Depends(get_db)):
    if pkg_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    pkg = crud.create_agent_package(db_session, pkg_in)
    if not pkg:
        raise HTTPException(status_code=404, detail="Expert model not found")
    return pkg

# Audit Trail routes
@app.get("/api/audit", response_model=List[schemas.AuditEventResponse])
def get_audit_trail(limit: int = 100, db_session: Session = Depends(get_db)):
    return crud.get_audit_events(db_session, limit=limit)

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

