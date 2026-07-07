"""Experts routes (audit T2.4, relocated VERBATIM from app/main.py).

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



# Expert Models routes
@router.get("/api/projects/{project_id}/experts", response_model=List[schemas.ExpertModelResponse])
def get_experts(project_id: int, db_session: Session = Depends(get_db),
                actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.get_expert_models(db_session, project_id)

@router.post("/api/projects/{project_id}/experts", response_model=schemas.ExpertModelResponse)
def create_expert(project_id: int, expert_in: schemas.ExpertModelCreate, db_session: Session = Depends(get_db),
                  actor: identity.Actor = Depends(require_perm("assets:approve"))):
    # Validate project_id matches
    if expert_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    try:
        return crud.create_expert_model(db_session, expert_in, actor=actor)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/api/projects/{project_id}/query", response_model=schemas.QueryResponse)
def execute_query(project_id: int, query_in: schemas.QueryInput, db_session: Session = Depends(get_db),
                  actor: identity.Actor = Depends(require_perm("assets:read"))):
    if not query_in.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Single shared pipeline (Verified Answer v1) - also used by the MCP gateway.
    # The boundary-decided display replaces the old hardcoded operator string;
    # query_engine's internal audit trail keeps its own event shapes.
    #
    # Clearance is decided by the boundary from the authenticated principal
    # (audit fix H-SEC-1, 2026-07-07) - the same law the MCP gateway enforces.
    # The request-body access_level may only NARROW the tier, never widen it:
    # a READ_ONLY caller can no longer read EXECUTIVE assets by asking for them.
    effective_clearance = identity.effective_query_clearance(
        actor.principal, query_in.access_level)
    result = query_engine.execute_expert_query(
        db_session,
        expert_model_id=query_in.expert_model_id,
        question=query_in.question,
        caller_access_level=effective_clearance,
        actor=actor.display
    )
    return schemas.QueryResponse(**result)

@router.get("/api/experts/{expert_model_id}/compile-gate")
def get_compile_gate(expert_model_id: int, db_session: Session = Depends(get_db),
                     actor: identity.Actor = Depends(require_perm("assets:read"))):
    expert_model = db_session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not expert_model:
        raise HTTPException(status_code=404, detail=f"Expert Model with ID {expert_model_id} not found")
    return conflict_engine.evaluate_compile_gate(db_session, expert_model_id)

# Knowledge Integrity Engine routes (MVP 0.7: Semantic Conflict Engine)
@router.post("/api/experts/{expert_model_id}/conflict-scan", response_model=schemas.ConflictScanResponse)
def run_conflict_scan(expert_model_id: int, db_session: Session = Depends(get_db),
                      actor: identity.Actor = Depends(require_perm("assets:review"))):
    try:
        return conflict_engine.scan_expert_model_conflicts(db_session, expert_model_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/experts/{expert_model_id}/trust-score", response_model=schemas.TrustScoreResponse)
def get_expert_model_trust_score(expert_model_id: int, db_session: Session = Depends(get_db),
                                 actor: identity.Actor = Depends(require_perm("assets:read"))):
    try:
        return trust.compute_trust_score(db_session, expert_model_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/projects/{project_id}/trust-scores", response_model=List[schemas.TrustScoreResponse])
def get_project_trust_scores(project_id: int, db_session: Session = Depends(get_db),
                             actor: identity.Actor = Depends(require_perm("assets:read"))):
    models = db_session.query(db.ExpertModel).filter(db.ExpertModel.project_id == project_id).all()
    return [trust.compute_trust_score(db_session, m.id) for m in models]

@router.get("/api/experts/{expert_model_id}/conflict-score", response_model=schemas.ConflictScoreResponse)
def get_expert_model_conflict_score(expert_model_id: int, db_session: Session = Depends(get_db),
                                    actor: identity.Actor = Depends(require_perm("assets:read"))):
    expert_model = db_session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not expert_model:
        raise HTTPException(status_code=404, detail=f"Expert Model with ID {expert_model_id} not found")
    return conflict_engine.compute_semantic_conflict_score(db_session, expert_model_id)

def _annotated_relationship(db_session, rel, annotations=None):
    """v1.4.0 WS2 (D30): serialize a relationship with its computed
    source-class context - the shared annotator, so every conflict
    surface declares the same asymmetry."""
    annotations = annotations or conflict_engine.class_annotations(db_session, [rel])
    data = schemas.AssetRelationshipResponse.model_validate(rel).model_dump()
    data.update(annotations[rel.id])
    return data

@router.get("/api/experts/{expert_model_id}/conflicts", response_model=List[schemas.AssetRelationshipResponse])
def get_expert_model_conflicts(expert_model_id: int, relationship_type: Optional[str] = None, db_session: Session = Depends(get_db),
                               actor: identity.Actor = Depends(require_perm("assets:read"))):
    query = db_session.query(db.AssetRelationship).filter(db.AssetRelationship.expert_model_id == expert_model_id)
    if relationship_type:
        query = query.filter(db.AssetRelationship.relationship_type == relationship_type)
    rels = query.order_by(db.AssetRelationship.confidence.desc()).all()
    annotations = conflict_engine.class_annotations(db_session, rels)
    return [_annotated_relationship(db_session, r, annotations) for r in rels]

@router.patch("/api/conflicts/{relationship_id}", response_model=schemas.AssetRelationshipResponse)
def review_conflict(relationship_id: int, review: schemas.ConflictReviewUpdate, db_session: Session = Depends(get_db),
                    actor: identity.Actor = Depends(require_perm("assets:approve"))):
    try:
        rel = conflict_engine.review_relationship(
            db_session, relationship_id, status=review.status, reviewer=actor, notes=review.notes
        )
        return _annotated_relationship(db_session, rel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
