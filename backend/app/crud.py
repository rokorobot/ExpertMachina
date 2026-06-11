import datetime
import json
import uuid
from sqlalchemy.orm import Session
from app import database as db
from app import schemas

# Customer helpers
def get_or_create_default_customer(session: Session) -> db.Customer:
    cust = session.query(db.Customer).filter_by(name="Default Customer").first()
    if not cust:
        cust = db.Customer(name="Default Customer", api_key=str(uuid.uuid4()))
        session.add(cust)
        session.commit()
        session.refresh(cust)
        log_audit_event(session, actor="system", event_type="CUSTOMER_CREATED", target_id=str(cust.id), details="Default customer initialized automatically")
    return cust

# Audit Ledger Helper
def log_audit_event(session: Session, actor: str, event_type: str, target_id: str = None, details: str = None):
    event = db.AuditEvent(
        timestamp=datetime.datetime.utcnow(),
        actor=actor,
        event_type=event_type,
        target_id=target_id,
        details=details
    )
    session.add(event)
    session.commit()
    return event

# Project Operations
def get_projects(session: Session, customer_id: int):
    return session.query(db.Project).filter(db.Project.customer_id == customer_id).all()

def create_project(session: Session, project: schemas.ProjectCreate):
    db_project = db.Project(
        name=project.name,
        description=project.description,
        customer_id=project.customer_id,
        status="NEW"
    )
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    log_audit_event(session, actor="user", event_type="PROJECT_CREATED", target_id=str(db_project.id), details=f"Project '{db_project.name}' created.")
    return db_project

def update_project_status(session: Session, project_id: int, status: str):
    proj = session.query(db.Project).filter(db.Project.id == project_id).first()
    if proj:
        old_status = proj.status
        proj.status = status
        session.commit()
        session.refresh(proj)
        log_audit_event(session, actor="system", event_type="PROJECT_STATUS_UPDATED", target_id=str(proj.id), details=f"Status changed from {old_status} to {status}.")
    return proj

# Document Operations
def get_documents(session: Session, project_id: int):
    # Dynamically audit and sync lifecycle state for all documents in the project
    docs = session.query(db.Document).filter(db.Document.project_id == project_id).all()
    for doc in docs:
        update_document_lifecycle(session, doc.id)
        
    return session.query(db.Document).filter(
        db.Document.project_id == project_id
    ).filter(
        ~db.Document.status.in_(["ALL_ASSETS_REJECTED", "DELETED"])
    ).all()

def update_document_lifecycle(session: Session, document_id: int):
    doc = session.query(db.Document).filter(db.Document.id == document_id).first()
    if not doc:
        return
    
    # Don't overwrite DELETED status
    if doc.status == "DELETED":
        return
        
    assets = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.document_id == document_id).all()
    if not assets:
        if doc.status in ["ASSETS_EXTRACTED", "PARTIALLY_APPROVED", "APPROVED", "ALL_ASSETS_REJECTED"]:
            doc.status = "DELETED"
            log_audit_event(session, actor="system", event_type="DOCUMENT_STATUS_UPDATED", target_id=str(document_id), details=f"Document '{doc.filename}' status updated to DELETED because all its assets were deleted.")
        return
        
    total = len(assets)
    archived_count = sum(1 for a in assets if a.status in ["REJECTED", "ARCHIVED"])
    approved_count = sum(1 for a in assets if a.status == "APPROVED")
    
    if archived_count == total:
        new_status = "ALL_ASSETS_REJECTED"
    elif approved_count == total:
        new_status = "APPROVED"
    elif approved_count > 0:
        new_status = "PARTIALLY_APPROVED"
    else:
        new_status = "ASSETS_EXTRACTED"
        
    if doc.status != new_status:
        old_status = doc.status
        doc.status = new_status
        log_audit_event(session, actor="system", event_type="DOCUMENT_STATUS_UPDATED", target_id=str(document_id), details=f"Document '{doc.filename}' status updated from {old_status} to {new_status} based on assets review.")
        
    session.commit()

def create_document(session: Session, project_id: int, filename: str, file_path: str, department: str = "General", owner: str = "System"):
    db_doc = db.Document(
        project_id=project_id,
        filename=filename,
        file_path=file_path,
        file_type=filename.split(".")[-1].upper() if "." in filename else "UNKNOWN",
        department=department,
        owner=owner,
        version="1.0",
        status="INGESTED",
        created_at=datetime.datetime.utcnow(),
        modified_at=datetime.datetime.utcnow()
    )
    session.add(db_doc)
    session.commit()
    session.refresh(db_doc)
    log_audit_event(session, actor=owner, event_type="DOCUMENT_UPLOADED", target_id=str(db_doc.id), details=f"Uploaded document: {filename}")
    return db_doc

def get_document_chunks(session: Session, document_id: int):
    return session.query(db.DocumentChunk).filter(db.DocumentChunk.document_id == document_id).all()

# Knowledge Asset Operations
def get_knowledge_assets(session: Session, project_id: int):
    return session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.project_id == project_id).all()

def get_knowledge_asset_by_id(session: Session, asset_id: int):
    return session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()

def create_knowledge_asset(session: Session, asset: schemas.KnowledgeAssetCreate):
    db_asset = db.KnowledgeAsset(
        project_id=asset.project_id,
        type=asset.type,
        name=asset.name,
        owner=asset.owner,
        condition=asset.condition,
        source_citation=asset.source_citation,
        content=asset.content,
        status="CANDIDATE",
        access_level=asset.access_level,
        document_id=asset.document_id,
        chunk_id=asset.chunk_id,
        source_page=asset.source_page,
        source_section=asset.source_section,
        source_hash=asset.source_hash,
        extraction_method=asset.extraction_method,
        created_at=datetime.datetime.utcnow()
    )
    session.add(db_asset)
    session.commit()
    session.refresh(db_asset)
    log_audit_event(session, actor="system", event_type="ASSET_GENERATED", target_id=str(db_asset.id), details=f"Generated asset: [{db_asset.type}] {db_asset.name} via {db_asset.extraction_method}")
    return db_asset

def update_knowledge_asset(session: Session, asset_id: int, update: schemas.KnowledgeAssetUpdate, actor: str = "user"):
    asset = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
    if not asset:
        return None
    
    update_data = update.dict(exclude_unset=True)

    # Core revision rule: approved content is never edited in place.
    # A content edit on an APPROVED asset becomes a CANDIDATE revision;
    # the asset row keeps serving the active approved revision.
    if (asset.status == "APPROVED"
            and "content" in update_data
            and update_data["content"] != asset.content
            and update_data.get("status", "APPROVED") == "APPROVED"):
        from app import revisions
        new_content = update_data.pop("content")
        revisions.create_candidate_revision(
            session, asset.id, new_content, actor=actor,
            change_reason="Edited via asset update"
        )

    status_change = None

    for key, value in update_data.items():
        if key == "status" and value != asset.status:
            status_change = (asset.status, value)
        setattr(asset, key, value)
    
    session.commit()
    session.refresh(asset)
    
    if status_change:
        old_st, new_st = status_change
        event_t = "ASSET_REVIEWED" if new_st == "REVIEWED" else "ASSET_APPROVED" if new_st == "APPROVED" else "ASSET_UPDATED"
        log_audit_event(session, actor=actor, event_type=event_t, target_id=str(asset.id), details=f"Asset status updated from {old_st} to {new_st}")
        if new_st == "APPROVED":
            # Record the approval as a review row so citations carry real
            # approver provenance instead of fabricated defaults.
            session.add(db.AssetReview(asset_id=asset.id, approver=actor, notes=f"Approved (status changed from {old_st})"))
            session.commit()
            # Lazy revision adoption: first approval creates revision 1
            # from the asset's current state.
            from app import revisions
            revisions.ensure_baseline_revision(session, asset, actor=actor)
        if asset.document_id:
            update_document_lifecycle(session, asset.document_id)
    else:
        log_audit_event(session, actor=actor, event_type="ASSET_UPDATED", target_id=str(asset.id), details="Asset metadata updated manually")
        
    return asset

# Asset Reviews
def create_asset_review(session: Session, asset_id: int, review: schemas.AssetReviewCreate, actor: str = "user"):
    db_review = db.AssetReview(
        asset_id=asset_id,
        reviewer=review.reviewer,
        approver=review.approver,
        notes=review.notes,
        reviewed_at=datetime.datetime.utcnow()
    )
    session.add(db_review)
    session.commit()
    session.refresh(db_review)
    return db_review

# Quality Scores
def create_quality_score(session: Session, asset_id: int, score: schemas.QualityScoreBase):
    db_score = db.QualityScore(
        asset_id=asset_id,
        coverage_score=score.coverage_score,
        freshness_score=score.freshness_score,
        verification_score=score.verification_score,
        conflict_score=score.conflict_score,
        overall_score=score.overall_score,
        recorded_at=datetime.datetime.utcnow()
    )
    session.add(db_score)
    session.commit()
    session.refresh(db_score)
    return db_score

# Expert Model Builder
def get_expert_models(session: Session, project_id: int):
    return session.query(db.ExpertModel).filter(db.ExpertModel.project_id == project_id).all()

def create_expert_model(session: Session, model_in: schemas.ExpertModelCreate):
    # Retrieve all requested assets to verify status
    assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.id.in_(model_in.asset_ids)
    ).all()
    
    if len(assets) != len(model_in.asset_ids):
        raise ValueError("One or more asset IDs are invalid or do not exist in the workspace.")
        
    for asset in assets:
        if asset.status != "APPROVED":
            log_audit_event(
                session, 
                actor="system", 
                event_type="GOVERNANCE_BLOCKED_NON_APPROVED_ASSET", 
                target_id=str(asset.id), 
                details=f"Expert Model compilation blocked: asset '{asset.name}' (ID: {asset.id}) is in status '{asset.status}' (must be APPROVED)."
            )
            raise ValueError(f"Asset '{asset.name}' (ID: {asset.id}) is in status '{asset.status}'. Only APPROVED assets can be grouped.")
    
    count = len(assets)
    avg_quality = 0.0
    avg_coverage = 0.0
    
    if count > 0:
        qual_sums = 0.0
        cov_sums = 0.0
        for asset in assets:
            # Get latest quality score
            score = session.query(db.QualityScore).filter(db.QualityScore.asset_id == asset.id).order_by(db.QualityScore.recorded_at.desc()).first()
            if score:
                qual_sums += score.overall_score
                cov_sums += score.coverage_score
            else:
                qual_sums += 70.0 # fallback
                cov_sums += 75.0
        avg_quality = round(qual_sums / count, 1)
        avg_coverage = round(cov_sums / count, 1)

    db_model = db.ExpertModel(
        project_id=model_in.project_id,
        name=model_in.name,
        description=model_in.description,
        asset_count=count,
        quality_score=avg_quality,
        coverage_score=avg_coverage,
        asset_ids_json=json.dumps(model_in.asset_ids),
        created_at=datetime.datetime.utcnow()
    )
    session.add(db_model)
    session.commit()
    session.refresh(db_model)
    
    log_audit_event(session, actor="user", event_type="EXPERT_MODEL_CREATED", target_id=str(db_model.id), details=f"Expert model '{db_model.name}' constructed with {count} grouped assets.")
    return db_model

# Agent Packages
def get_agent_packages(session: Session, project_id: int):
    return session.query(db.AgentPackage).filter(db.AgentPackage.project_id == project_id).all()

def create_agent_package(session: Session, package_in: schemas.AgentPackageCreate):
    model = session.query(db.ExpertModel).filter(db.ExpertModel.id == package_in.expert_model_id).first()
    if not model:
        return None

    # Compile gate (MVP 0.8): unresolved semantic conflicts block publication.
    from app import conflict_engine
    gate = conflict_engine.evaluate_compile_gate(session, package_in.expert_model_id)
    if not gate["allowed"]:
        log_audit_event(
            session,
            actor="user",
            event_type="GOVERNANCE_BLOCKED_UNRESOLVED_CONFLICTS",
            target_id=str(package_in.expert_model_id),
            details=json.dumps({
                "attempted_package_name": package_in.name,
                "blocking_conflicts": gate["blocking_conflicts"],
                "policy": gate["policy"]
            })
        )
        reasons = sorted({b["reason"] for b in gate["blocking_conflicts"]})
        raise ValueError(
            f"Compile blocked by governance gate: {len(gate['blocking_conflicts'])} unresolved "
            f"semantic conflict(s) ({', '.join(reasons)}). Review them in the Knowledge Conflicts "
            f"workbench before publishing."
        )

    # Query assets included in the model to serialize references and source provenances
    # In a real system we associate assets to model via a join.
    # Here, for MVP, we compile the active approved assets of the project into the package.
    # We will search knowledge assets in the database.
    # To keep it simple, we serialize a list of reference details.
    assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == package_in.project_id,
        db.KnowledgeAsset.status == "APPROVED"
    ).order_by(db.KnowledgeAsset.id.asc()).all()
    
    refs = []
    for asset in assets:
        doc = session.query(db.Document).filter(db.Document.id == asset.document_id).first()
        doc_name = doc.filename if doc else "Unknown"
        refs.append({
            "asset_id": asset.id,
            "name": asset.name,
            "type": asset.type,
            "source_citation": asset.source_citation,
            "extraction_method": asset.extraction_method,
            "access_level": asset.access_level,
            "source_document": doc_name,
            "source_page": asset.source_page,
            "source_section": asset.source_section,
            "source_hash": asset.source_hash
        })

    db_package = db.AgentPackage(
        project_id=package_in.project_id,
        name=package_in.name,
        expert_model_id=package_in.expert_model_id,
        governance_version=package_in.governance_version or "0.1.0",
        quality_score=model.quality_score,
        asset_references=json.dumps(refs),
        created_at=datetime.datetime.utcnow()
    )
    session.add(db_package)
    session.commit()
    session.refresh(db_package)
    
    # Publication is a governance event: record the gate verdict that allowed it.
    log_audit_event(
        session,
        actor="user",
        event_type="AGENT_PACKAGE_CREATED",
        target_id=str(db_package.id),
        details=json.dumps({
            "package_name": db_package.name,
            "expert_model_id": db_package.expert_model_id,
            "governance_version": db_package.governance_version,
            "compile_gate": {
                "allowed": True,
                "conflict_scan_performed": gate["conflict_scan_performed"],
                "advisory_conflicts": len(gate["advisory_conflicts"]),
                "dismissed_conflicts": gate["dismissed_conflicts"],
                "policy": gate["policy"]
            }
        })
    )
    return db_package

# Audit Ledger Retrieves
def get_audit_events(session: Session, limit: int = 100, event_prefix: str = None,
                     actor: str = None, target_id: str = None,
                     since: datetime.datetime = None, until: datetime.datetime = None):
    """Audit Ledger Explorer query: every filter narrows the immutable event
    stream; no filter ever mutates it."""
    query = session.query(db.AuditEvent)
    if event_prefix:
        query = query.filter(db.AuditEvent.event_type.like(f"{event_prefix}%"))
    if actor:
        query = query.filter(db.AuditEvent.actor == actor)
    if target_id:
        query = query.filter(db.AuditEvent.target_id == str(target_id))
    if since:
        query = query.filter(db.AuditEvent.timestamp >= since)
    if until:
        query = query.filter(db.AuditEvent.timestamp <= until)
    return query.order_by(db.AuditEvent.timestamp.desc()).limit(limit).all()

# Delete Operations
def delete_knowledge_asset(session: Session, asset_id: int, actor: str = "system"):
    asset = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
    if asset:
        asset_name = asset.name
        asset_type = asset.type
        doc_id = asset.document_id
        # Log to ledger
        log_audit_event(session, actor=actor, event_type="ASSET_DELETED", target_id=str(asset_id), details=f"Permanently deleted asset: [{asset_type}] {asset_name}")
        session.delete(asset)
        session.commit()
        
        if doc_id:
            update_document_lifecycle(session, doc_id)
        return True
    return False

def delete_knowledge_assets_by_document(session: Session, document_id: int, status: str = None, actor: str = "system"):
    query = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.document_id == document_id)
    if status:
        query = query.filter(db.KnowledgeAsset.status == status)
    
    assets = query.all()
    count = len(assets)
    if count > 0:
        doc = session.query(db.Document).filter(db.Document.id == document_id).first()
        doc_name = doc.filename if doc else f"Doc #{document_id}"
        status_label = f" with status '{status}'" if status else ""
        
        # Log bulk deletion
        log_audit_event(session, actor=actor, event_type="BULK_ASSETS_DELETED", target_id=str(document_id), details=f"Bulk deleted {count} assets{status_label} from document '{doc_name}'")
        
        for asset in assets:
            session.delete(asset)
        session.commit()
        
        update_document_lifecycle(session, document_id)
        return count
    return 0

# Benchmark Questions CRUD
def create_benchmark_question(session: Session, q_in: schemas.BenchmarkQuestionCreate) -> db.BenchmarkQuestion:
    db_question = db.BenchmarkQuestion(
        project_id=q_in.project_id,
        question=q_in.question,
        expected_claims_json=json.dumps(q_in.expected_claims),
        expected_answer_type=q_in.expected_answer_type,
        required_citation_count=q_in.required_citation_count,
        tags=q_in.tags,
        severity=q_in.severity,
        min_required_coverage=q_in.min_required_coverage,
        created_at=datetime.datetime.utcnow()
    )
    session.add(db_question)
    session.commit()
    session.refresh(db_question)
    return db_question

def get_benchmark_question(session: Session, question_id: int) -> db.BenchmarkQuestion:
    return session.query(db.BenchmarkQuestion).filter(db.BenchmarkQuestion.id == question_id).first()

def get_benchmark_questions(session: Session, project_id: int, limit: int = 100) -> list:
    return session.query(db.BenchmarkQuestion).filter(db.BenchmarkQuestion.project_id == project_id).order_by(db.BenchmarkQuestion.created_at.desc()).limit(limit).all()

def update_benchmark_question(session: Session, question_id: int, update: schemas.BenchmarkQuestionUpdate) -> db.BenchmarkQuestion:
    db_question = get_benchmark_question(session, question_id)
    if not db_question:
        return None
    
    update_data = update.dict(exclude_unset=True)
    if "expected_claims" in update_data:
        db_question.expected_claims_json = json.dumps(update_data.pop("expected_claims"))
        
    for key, val in update_data.items():
        setattr(db_question, key, val)
        
    session.commit()
    session.refresh(db_question)
    return db_question

def delete_benchmark_question(session: Session, question_id: int) -> bool:
    db_question = get_benchmark_question(session, question_id)
    if db_question:
        session.delete(db_question)
        session.commit()
        return True
    return False
