import os
import datetime
import json
import uuid
from sqlalchemy.orm import Session
from app import database as db
from app import schemas
from app import identity

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
def log_audit_event(session: Session, actor: str, event_type: str, target_id: str = None, details: str = None,
                    identity_fact_id: int = None):
    # identity_fact_id (Identity Boundary v1.0): the immutable evidence of
    # WHO acted. NULL = pre-boundary legacy; actor remains the readable
    # display string either way.
    event = db.AuditEvent(
        timestamp=datetime.datetime.utcnow(),
        actor=actor,
        event_type=event_type,
        target_id=target_id,
        details=details,
        identity_fact_id=identity_fact_id
    )
    session.add(event)
    session.commit()
    return event

# Project Operations
def get_projects(session: Session, customer_id: int):
    return session.query(db.Project).filter(db.Project.customer_id == customer_id).all()

def create_project(session: Session, project: schemas.ProjectCreate, actor: identity.Actor = None):
    actor = identity.require_actor_object(actor)
    db_project = db.Project(
        name=project.name,
        description=project.description,
        customer_id=project.customer_id,
        status="NEW"
    )
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    log_audit_event(session, actor=actor.display, event_type="PROJECT_CREATED", target_id=str(db_project.id),
                    details=f"Project '{db_project.name}' created.", identity_fact_id=actor.fact(session).id)
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

def create_document(session: Session, project_id: int, filename: str, file_path: str, department: str = "General", owner: str = "System",
                    actor: identity.Actor = None):
    # owner/department are DOCUMENT METADATA (who owns the content); actor is
    # WHO PERFORMED the upload - boundary-decided, never caller-asserted.
    actor = identity.require_actor_object(actor)
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
    log_audit_event(session, actor=actor.display, event_type="DOCUMENT_UPLOADED", target_id=str(db_doc.id),
                    details=f"Uploaded document: {filename}", identity_fact_id=actor.fact(session).id)
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

def update_knowledge_asset(session: Session, asset_id: int, update: schemas.KnowledgeAssetUpdate, actor: identity.Actor = None,
                           audit_event_type: str = None, audit_details: str = None, review_notes: str = None):
    # audit_event_type/audit_details/review_notes let a policy approval carry
    # its own audit fingerprint (ASSET_AUTO_APPROVED + provenance JSON) while
    # going through this single approval transition path - same AssetReview,
    # same baseline revision, same document lifecycle as a human approval.
    actor = identity.require_actor_object(actor)
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

    # v1.2.1 WS1 (D27): a domain change through this surface is a human
    # correction - a governed act with its own audit vocabulary, never a
    # silent metadata edit. Domain is taxonomy, not content: it never
    # creates a revision and never touches provenance or history.
    # Correcting to None (unclassify) is legitimate and honest (D12).
    domain_change = None
    if "domain" in update_data:
        new_domain = update_data["domain"]
        if new_domain is not None:
            from app import classification
            new_domain = classification.validate_domain_path(new_domain)
            update_data["domain"] = new_domain
        if new_domain != asset.domain:
            domain_change = (asset.domain, new_domain)
        else:
            update_data.pop("domain")

    status_change = None

    for key, value in update_data.items():
        if key == "status" and value != asset.status:
            status_change = (asset.status, value)
        setattr(asset, key, value)
    
    session.commit()
    session.refresh(asset)

    if domain_change:
        old_domain, new_domain = domain_change
        log_audit_event(session, actor=actor.display, event_type="ASSET_DOMAIN_CORRECTED",
                        target_id=str(asset.id),
                        details=json.dumps({"old_domain": old_domain, "new_domain": new_domain}),
                        identity_fact_id=actor.fact(session).id)

    if status_change:
        old_st, new_st = status_change
        event_t = audit_event_type or ("ASSET_REVIEWED" if new_st == "REVIEWED" else "ASSET_APPROVED" if new_st == "APPROVED" else "ASSET_UPDATED")
        event_details = audit_details or f"Asset status updated from {old_st} to {new_st}"
        # v1.4.0 WS1 (D30): accepting a DERIVED fact quotes its synthesis
        # provenance - the verification verdict recomputed against
        # governed records AT approval time, verbatim claims included.
        # Only humans reach this branch (proposal-lane candidates are
        # outside every policy tier per D29), so event_details here is
        # the plain human-approval string - wrapped, never overwritten.
        if new_st == "APPROVED" and asset.source_class == "DERIVED":
            from app import proposals
            event_details = json.dumps({
                "note": event_details,
                "source_class": "DERIVED",
                "synthesis_provenance": proposals.approval_provenance(session, asset),
            })
        log_audit_event(session, actor=actor.display, event_type=event_t, target_id=str(asset.id),
                        details=event_details,
                        identity_fact_id=actor.fact(session).id)
        if new_st == "APPROVED":
            # Record the approval as a review row so citations carry real
            # approver provenance instead of fabricated defaults.
            session.add(db.AssetReview(asset_id=asset.id, approver=actor.display,
                                       notes=review_notes or f"Approved (status changed from {old_st})",
                                       identity_fact_id=actor.fact(session).id))
            session.commit()
            # Lazy revision adoption: first approval creates revision 1
            # from the asset's current state.
            from app import revisions
            revisions.ensure_baseline_revision(session, asset, actor=actor)
        if asset.document_id:
            update_document_lifecycle(session, asset.document_id)
    elif not (domain_change and len(update_data) == 1):
        # Unchanged behavior for every non-domain update; a domain-only
        # correction already carries its own event above.
        log_audit_event(session, actor=actor.display, event_type="ASSET_UPDATED", target_id=str(asset.id),
                        details="Asset metadata updated manually", identity_fact_id=actor.fact(session).id)

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

def create_expert_model(session: Session, model_in: schemas.ExpertModelCreate, actor: identity.Actor = None):
    actor = identity.require_actor_object(actor)
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
                actor=actor.display,
                event_type="GOVERNANCE_BLOCKED_NON_APPROVED_ASSET",
                target_id=str(asset.id),
                details=f"Expert Model compilation blocked: asset '{asset.name}' (ID: {asset.id}) is in status '{asset.status}' (must be APPROVED).",
                identity_fact_id=actor.fact(session).id
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
    
    log_audit_event(session, actor=actor.display, event_type="EXPERT_MODEL_CREATED", target_id=str(db_model.id),
                    details=f"Expert model '{db_model.name}' constructed with {count} grouped assets.",
                    identity_fact_id=actor.fact(session).id)
    return db_model

# Agent Packages
def get_agent_packages(session: Session, project_id: int):
    return session.query(db.AgentPackage).filter(db.AgentPackage.project_id == project_id).all()

def create_agent_package(session: Session, package_in: schemas.AgentPackageCreate, actor: identity.Actor = None):
    actor = identity.require_actor_object(actor)
    model = session.query(db.ExpertModel).filter(db.ExpertModel.id == package_in.expert_model_id).first()
    if not model:
        return None

    # Compile gate (MVP 0.8): unresolved semantic conflicts block publication.
    from app import conflict_engine
    gate = conflict_engine.evaluate_compile_gate(session, package_in.expert_model_id)
    if not gate["allowed"]:
        log_audit_event(
            session,
            actor=actor.display,
            event_type="GOVERNANCE_BLOCKED_UNRESOLVED_CONFLICTS",
            target_id=str(package_in.expert_model_id),
            details=json.dumps({
                "attempted_package_name": package_in.name,
                "blocking_conflicts": gate["blocking_conflicts"],
                "policy": gate["policy"]
            }),
            identity_fact_id=actor.fact(session).id
        )
        reasons = sorted({b["reason"] for b in gate["blocking_conflicts"]})
        raise ValueError(
            f"Compile blocked by governance gate: {len(gate['blocking_conflicts'])} unresolved "
            f"semantic conflict(s) ({', '.join(reasons)}). Review them in the Knowledge Conflicts "
            f"workbench before publishing."
        )

    # The package contains the MODEL's member assets at or below the declared
    # clearance (MVP 0.9.4 - previously this compiled every approved asset in
    # the project, which leaked non-member knowledge into packages).
    from app import package_builder
    clearance = (package_in.clearance_level or "INTERNAL").upper()
    assets, excluded_count = package_builder.member_assets(session, model, clearance)

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
        clearance_level=clearance,
        created_at=datetime.datetime.utcnow()
    )
    session.add(db_package)
    session.commit()
    session.refresh(db_package)

    # Emit the portable .empkg artifact (MVP 0.9.4) - the thing the compile
    # gate has been guarding. Hashed, clearance-filtered, snapshot-stamped.
    manifest = package_builder.build_package(session, db_package)

    # Publication is a governance event: record the gate verdict that allowed
    # it and the tamper-evident package hash.
    log_audit_event(
        session,
        actor=actor.display,
        event_type="AGENT_PACKAGE_CREATED",
        identity_fact_id=actor.fact(session).id,
        target_id=str(db_package.id),
        details=json.dumps({
            "package_name": db_package.name,
            "expert_model_id": db_package.expert_model_id,
            "governance_version": db_package.governance_version,
            "clearance_level": clearance,
            "package_hash": db_package.package_hash,
            "asset_count": manifest["asset_count"],
            "excluded_assets_above_clearance": excluded_count,
            "trust_score": manifest["trust_score"],
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
def delete_knowledge_asset(session: Session, asset_id: int, actor: identity.Actor = None):
    actor = identity.require_actor_object(actor)
    asset = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
    if asset:
        asset_name = asset.name
        asset_type = asset.type
        doc_id = asset.document_id
        # Log to ledger
        log_audit_event(session, actor=actor.display, event_type="ASSET_DELETED", target_id=str(asset_id),
                        details=f"Permanently deleted asset: [{asset_type}] {asset_name}",
                        identity_fact_id=actor.fact(session).id)
        session.delete(asset)
        session.commit()
        
        if doc_id:
            update_document_lifecycle(session, doc_id)
        return True
    return False

def delete_knowledge_assets_by_document(session: Session, document_id: int, status: str = None, actor: identity.Actor = None):
    actor = identity.require_actor_object(actor)
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
        log_audit_event(session, actor=actor.display, event_type="BULK_ASSETS_DELETED", target_id=str(document_id),
                        details=f"Bulk deleted {count} assets{status_label} from document '{doc_name}'",
                        identity_fact_id=actor.fact(session).id)
        
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

# Package Model Selection (v1.1 WS3): a governed decision at the package
# layer - which consumer model is selected for this frozen artifact, based
# on which PACKAGE evaluation runs. The boundary validates the proposed
# evidence; one current selection per package; history lives in
# PACKAGE_MODEL_SELECTED audit events, never in row lifecycle.

def get_package_model_selection(session: Session, agent_package_id: int):
    return session.query(db.PackageModelSelection).filter(
        db.PackageModelSelection.agent_package_id == agent_package_id).first()


def set_package_model_selection(session: Session, agent_package_id: int,
                                update: schemas.PackageModelSelectionUpdate,
                                actor: identity.Actor = None) -> db.PackageModelSelection:
    """Select (or re-select) the consumer model for a package. Rules:
    - the rationale is mandatory: "why this model?" must be answerable
      from the decision itself, indefinitely (the D17 provenance pattern);
    - every supporting run must be a COMPLETED PACKAGE run for this exact
      package_hash - evidence about another artifact is not evidence;
    - the selected coordinates must appear among the supporting runs: a
      model without a successful run for this package cannot be selected.
    Changing the selection updates the single current row and writes a new
    audit event; prior events remain untouched."""
    actor = identity.require_actor_object(actor)
    pkg = session.query(db.AgentPackage).filter(db.AgentPackage.id == agent_package_id).first()
    if not pkg:
        raise LookupError(f"Agent Package with ID {agent_package_id} not found")
    if not pkg.package_hash:
        raise ValueError(f"Agent Package {agent_package_id} has no package hash - nothing to select for")

    provider = (update.provider or "").strip().upper()
    model_name = (update.model or "").strip()
    rationale = (update.rationale or "").strip()
    run_ids = list(dict.fromkeys(update.supporting_evaluation_run_ids or []))
    if not provider or not model_name:
        raise ValueError("A selection names a provider and a model")
    if not rationale:
        raise ValueError("A selection requires a rationale - 'why this model?' must be answerable from the decision")
    if not run_ids:
        raise ValueError("A selection requires supporting evaluation run ids - selection without evidence is preference")

    runs = session.query(db.EvaluationRun).filter(db.EvaluationRun.id.in_(run_ids)).all()
    runs_by_id = {r.id: r for r in runs}
    for run_id in run_ids:
        run = runs_by_id.get(run_id)
        if not run:
            raise ValueError(f"Supporting evaluation run {run_id} does not exist")
        if run.run_type != "PACKAGE":
            raise ValueError(f"Supporting run {run_id} is a {run.run_type} run - selection evidence is PACKAGE-channel only (D10)")
        if run.status != "COMPLETED":
            raise ValueError(f"Supporting run {run_id} is {run.status}, not COMPLETED - it measured nothing (D12)")
        if run.package_hash != pkg.package_hash:
            raise ValueError(f"Supporting run {run_id} evaluated a different package artifact "
                             f"({(run.package_hash or '')[:16]}... vs {pkg.package_hash[:16]}...)")
    if not any((r.consumer_model_provider, r.consumer_model_name) == (provider, model_name)
               for r in runs_by_id.values()):
        raise ValueError(f"{provider}/{model_name} has no successful PACKAGE run among the supporting "
                         f"evidence for this package - a model without a run cannot be selected")

    selection = get_package_model_selection(session, agent_package_id)
    old = None
    if selection:
        old = {"provider": selection.selected_provider, "model": selection.selected_model_name,
               "supporting_evaluation_run_ids": selection.supporting_evaluation_run_ids,
               "rationale": selection.rationale}
    else:
        selection = db.PackageModelSelection(agent_package_id=agent_package_id)
        session.add(selection)

    selection.package_version = pkg.governance_version
    selection.package_hash = pkg.package_hash
    selection.selected_provider = provider
    selection.selected_model_name = model_name
    selection.supporting_evaluation_run_ids_json = json.dumps(run_ids)
    selection.rationale = rationale
    selection.selected_by_principal_id = actor.principal.id
    selection.selected_at = datetime.datetime.utcnow()
    session.commit()
    session.refresh(selection)

    log_audit_event(
        session, actor=actor.display, event_type="PACKAGE_MODEL_SELECTED",
        target_id=str(agent_package_id),
        details=json.dumps({
            "package_name": pkg.name,
            "package_version": pkg.governance_version,
            "package_hash": pkg.package_hash,
            "old_selection": old,
            "new_selection": {"provider": provider, "model": model_name,
                              "supporting_evaluation_run_ids": run_ids,
                              "rationale": rationale},
            "note": "selection is a governed decision over PACKAGE evaluation evidence; "
                    "comparison stays computed (D1), binding is a later workstream (D22)"}),
        identity_fact_id=actor.fact(session).id)
    return selection

# Expert Agent Binding (v1.1 WS4, D22): a governed binding of the current
# selected package model to an existing active AGENT principal. The binding
# executes nothing, mints no tokens (token issuance stays a governed
# identity operation - never hidden inside package binding), and
# orchestrates nothing. Bindings are append-only snapshots: later selection
# changes never rewrite them.

def list_expert_agent_bindings(session: Session, agent_package_id: int):
    return session.query(db.ExpertAgentBinding).filter(
        db.ExpertAgentBinding.agent_package_id == agent_package_id
    ).order_by(db.ExpertAgentBinding.id.asc()).all()


def create_expert_agent_binding(session: Session, agent_package_id: int,
                                create: schemas.ExpertAgentBindingCreate,
                                actor: identity.Actor = None) -> db.ExpertAgentBinding:
    """Issue a binding. Refusals, in order: missing/artifact-less package,
    package hash drift, no current model selection, stale selection,
    selected-model mismatch against the caller's confirmation proposal,
    missing/non-AGENT/inactive principal, principal clearance below the
    package's compiled clearance. The binding model ALWAYS equals the
    package's current PackageModelSelection at issue time - otherwise
    selection is not load-bearing."""
    from app import package_consumer
    from app.query_engine import ACCESS_RANK

    actor = identity.require_actor_object(actor)
    pkg = session.query(db.AgentPackage).filter(db.AgentPackage.id == agent_package_id).first()
    if not pkg:
        raise LookupError(f"Agent Package with ID {agent_package_id} not found")
    if not pkg.package_hash or not pkg.file_path or not os.path.exists(pkg.file_path):
        raise ValueError(f"Agent Package {agent_package_id} has no .empkg artifact - nothing to bind")
    try:
        loaded = package_consumer.load_package(pkg.file_path)
    except package_consumer.PackageVerificationError as e:
        raise ValueError(f"Package artifact fails verification: {e}")
    if loaded["package_hash"] != pkg.package_hash:
        raise ValueError(
            f"Package artifact hash {loaded['package_hash'][:16]}... does not match the recorded "
            f"hash {pkg.package_hash[:16]}... - refusing to bind a drifted artifact")

    selection = get_package_model_selection(session, agent_package_id)
    if not selection:
        raise ValueError(f"Agent Package {agent_package_id} has no current model selection - "
                         f"a binding deploys a SELECTED model (WS3), never an implicit one")
    if selection.package_hash != pkg.package_hash:
        raise ValueError("The current selection was made for a different package artifact - re-select first")
    if create.expected_provider or create.expected_model:
        expected = ((create.expected_provider or "").strip().upper(),
                    (create.expected_model or "").strip())
        current = (selection.selected_provider, selection.selected_model_name)
        if expected != current:
            raise ValueError(
                f"Selected model mismatch: caller expected {expected[0]}/{expected[1]} but the "
                f"current selection is {current[0]}/{current[1]} - re-read the selection and retry")

    principal = session.query(db.Principal).filter(
        db.Principal.id == create.agent_principal_id).first()
    if not principal:
        raise LookupError(f"Principal with ID {create.agent_principal_id} not found")
    if principal.kind != "AGENT":
        raise ValueError(f"Principal '{principal.name}' is {principal.kind}, not AGENT - "
                         f"bindings deploy to agent principals only")
    if not principal.active:
        raise ValueError(f"Principal '{principal.name}' is deactivated - bindings require an active principal")
    principal_clearance = (principal.clearance or "PUBLIC").upper()
    package_clearance = (pkg.clearance_level or "INTERNAL").upper()
    if ACCESS_RANK.get(principal_clearance, 0) < ACCESS_RANK.get(package_clearance, 0):
        raise ValueError(
            f"Principal clearance {principal_clearance} is below the package's compiled clearance "
            f"{package_clearance} - a binding must not hand an agent knowledge above its tier")

    selection_evidence = {
        "selection_id": selection.id,
        "provider": selection.selected_provider,
        "model": selection.selected_model_name,
        "supporting_evaluation_run_ids": selection.supporting_evaluation_run_ids,
        "rationale": selection.rationale,
        "selected_by_principal_id": selection.selected_by_principal_id,
        "selected_at": selection.selected_at.isoformat() if selection.selected_at else None,
    }
    fact_id = actor.fact(session).id
    binding = db.ExpertAgentBinding(
        agent_package_id=agent_package_id,
        package_version=pkg.governance_version,
        package_hash=pkg.package_hash,
        selected_provider=selection.selected_provider,
        selected_model_name=selection.selected_model_name,
        agent_principal_id=principal.id,
        principal_clearance_at_issue=principal_clearance,
        selection_evidence_json=json.dumps(selection_evidence),
        identity_fact_id=fact_id,
    )
    session.add(binding)
    session.commit()
    session.refresh(binding)

    log_audit_event(
        session, actor=actor.display, event_type="EXPERT_AGENT_BINDING_CREATED",
        target_id=str(binding.id),
        details=json.dumps({
            "agent_package_id": agent_package_id,
            "package_name": pkg.name,
            "package_version": pkg.governance_version,
            "package_hash": pkg.package_hash,
            "selected_provider": selection.selected_provider,
            "selected_model_name": selection.selected_model_name,
            "agent_principal_id": principal.id,
            "agent_principal_name": principal.name,
            "principal_clearance_at_issue": principal_clearance,
            "package_clearance": package_clearance,
            "selection_evidence": selection_evidence,
            "note": "a binding, never a runtime (D22): executes nothing, mints no tokens, "
                    "orchestrates nothing; later selection changes do not rewrite it"}),
        identity_fact_id=fact_id)
    return binding
