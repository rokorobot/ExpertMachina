"""Assets routes (audit T2.4, relocated VERBATIM from app/main.py).

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


# Knowledge Assets routes
@router.get("/api/projects/{project_id}/assets", response_model=List[schemas.KnowledgeAssetResponse])
def get_assets(project_id: int, db_session: Session = Depends(get_db),
               actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.get_knowledge_assets(db_session, project_id)

@router.post("/api/projects/{project_id}/extract")
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
    classification.classify_assets(db_session, project_id, fresh_doc_ids,
                                   on_behalf_of_fact=actor.fact(db_session))
    auto_approval = policy.apply_auto_approval(db_session, project_id, fresh_doc_ids,
                                               on_behalf_of_fact=actor.fact(db_session))
    # Tier-2 async (D4): the response records scheduling only; the pass
    # owns its session and writes POLICY_TIER2_COMPLETED itself.
    tier2_scheduled = False
    if fresh_doc_ids and tier2.tier2_policies_in_scope(db_session, project_id):
        tier2.schedule_pass(project_id, fresh_doc_ids,
                            on_behalf_of_fact_id=actor.fact(db_session).id)
        tier2_scheduled = True
    return {"message": "Knowledge assets extracted successfully.",
            "auto_approval": auto_approval, "tier2_scheduled": tier2_scheduled}

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
@router.patch("/api/assets/bulk", response_model=List[schemas.KnowledgeAssetResponse])
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

@router.patch("/api/assets/{asset_id}", response_model=schemas.KnowledgeAssetResponse)
def update_asset(asset_id: int, update: schemas.KnowledgeAssetUpdate, db_session: Session = Depends(get_db),
                 actor: identity.Actor = Depends(require_actor)):
    _authorize_or_403(db_session, actor, _asset_transition_permission(update.status))
    asset = crud.update_knowledge_asset(db_session, asset_id, update, actor=actor)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

# Deletion routes
@router.delete("/api/knowledge-assets/{asset_id}")
def delete_asset(asset_id: int, db_session: Session = Depends(get_db),
                 actor: identity.Actor = Depends(require_perm("assets:delete"))):
    deleted = crud.delete_knowledge_asset(db_session, asset_id, actor=actor)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": f"Asset {asset_id} deleted successfully"}

@router.delete("/api/documents/{document_id}/knowledge-assets")
def delete_document_assets(document_id: int, status: Optional[str] = None, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:delete"))):
    count = crud.delete_knowledge_assets_by_document(db_session, document_id, status=status, actor=actor)
    return {"message": f"Deleted {count} assets from document {document_id}"}

# Asset Revision Workflow routes (MVP 0.7 Sprint 4)
@router.get("/api/projects/{project_id}/revisions", response_model=List[schemas.RevisionQueueItem])
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

@router.get("/api/assets/{asset_id}/revisions", response_model=List[schemas.AssetRevisionResponse])
def get_asset_revisions(asset_id: int, db_session: Session = Depends(get_db),
                        actor: identity.Actor = Depends(require_perm("assets:read"))):
    asset = db_session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    return revisions.get_revisions(db_session, asset_id)

@router.post("/api/assets/{asset_id}/revisions", response_model=schemas.AssetRevisionResponse)
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

@router.post("/api/revisions/{revision_id}/review", response_model=schemas.AssetRevisionResponse)
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
