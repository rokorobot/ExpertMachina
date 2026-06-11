import json
import hashlib
import datetime

from sqlalchemy.orm import Session

from app import database as db
from app import crud

# Asset Revision Workflow (MVP 0.7 Sprint 4).
#
# Core rule: approved assets are never edited in place. Editing creates a
# new CANDIDATE revision; the old approved revision stays active until the
# candidate passes review. Strictly linear - one pending candidate at a
# time, no branching.
#
# Lazy adoption: existing assets get revision 1 created from their current
# state on first approval or first edit; nothing is migrated aggressively.


def _content_hash(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()


def _active_revision(asset: db.KnowledgeAsset):
    approved = [r for r in asset.revisions if r.status == "APPROVED"]
    return max(approved, key=lambda r: r.revision_number) if approved else None


def ensure_baseline_revision(session: Session, asset: db.KnowledgeAsset, actor: str = "system"):
    """Revision 1, created lazily from the asset's current state."""
    if asset.revisions:
        return None
    baseline = db.AssetRevision(
        asset_id=asset.id,
        revision_number=1,
        status="APPROVED" if asset.status == "APPROVED" else "CANDIDATE",
        content=asset.content,
        source_hash=asset.source_hash,
        content_hash=_content_hash(asset.content),
        created_by=actor,
        approved_by=actor if asset.status == "APPROVED" else None,
        approved_at=datetime.datetime.utcnow() if asset.status == "APPROVED" else None,
        change_reason="Baseline revision created from existing asset state"
    )
    session.add(baseline)
    session.commit()
    session.refresh(baseline)
    return baseline


def create_candidate_revision(session: Session, asset_id: int, content: str,
                              actor: str = "user", change_reason: str = None) -> db.AssetRevision:
    asset = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
    if not asset:
        raise LookupError(f"Asset {asset_id} not found")
    if asset.status != "APPROVED":
        raise ValueError("Revisions apply to APPROVED assets; non-approved assets are edited in place")
    if any(r.status == "CANDIDATE" for r in asset.revisions):
        raise ValueError("A candidate revision is already pending review for this asset")

    ensure_baseline_revision(session, asset, actor=actor)
    session.refresh(asset)
    active = _active_revision(asset)
    next_number = max(r.revision_number for r in asset.revisions) + 1

    revision = db.AssetRevision(
        asset_id=asset.id,
        revision_number=next_number,
        status="CANDIDATE",
        content=content,
        source_hash=asset.source_hash,
        content_hash=_content_hash(content),
        created_by=actor,
        supersedes_revision_id=active.id if active else None,
        change_reason=change_reason
    )
    session.add(revision)
    session.commit()
    session.refresh(revision)

    crud.log_audit_event(
        session,
        actor=actor,
        event_type="ASSET_REVISION_CREATED",
        target_id=str(asset.id),
        details=json.dumps({
            "asset_id": asset.id,
            "revision_id": revision.id,
            "revision_number": revision.revision_number,
            "supersedes_revision_id": revision.supersedes_revision_id,
            "content_hash": revision.content_hash,
            "change_reason": change_reason
        })
    )
    return revision


def review_revision(session: Session, revision_id: int, action: str,
                    actor: str = "user", notes: str = None) -> db.AssetRevision:
    if action not in ("APPROVE", "REJECT"):
        raise ValueError("Review action must be APPROVE or REJECT")
    revision = session.query(db.AssetRevision).filter(db.AssetRevision.id == revision_id).first()
    if not revision:
        raise LookupError(f"Revision {revision_id} not found")
    if revision.status != "CANDIDATE":
        raise ValueError(f"Only CANDIDATE revisions can be reviewed (revision is {revision.status})")

    asset = revision.asset

    if action == "REJECT":
        revision.status = "REJECTED"
        revision.change_reason = revision.change_reason or notes
        session.commit()
        session.refresh(revision)
        crud.log_audit_event(
            session,
            actor=actor,
            event_type="ASSET_REVISION_REJECTED",
            target_id=str(asset.id),
            details=json.dumps({
                "asset_id": asset.id,
                "revision_id": revision.id,
                "revision_number": revision.revision_number,
                "notes": notes
            })
        )
        return revision

    # APPROVE: supersede the old active revision, promote the candidate,
    # and update the asset row projection to the new content.
    old_active = _active_revision(asset)
    if old_active:
        old_active.status = "ARCHIVED"
        old_active.superseded_by_revision_id = revision.id

    revision.status = "APPROVED"
    revision.approved_by = actor
    revision.approved_at = datetime.datetime.utcnow()
    asset.content = revision.content

    session.add(db.AssetReview(
        asset_id=asset.id,
        approver=actor,
        notes=f"Revision {revision.revision_number} approved" + (f": {notes}" if notes else "")
    ))
    session.commit()
    session.refresh(revision)

    # Self-healing governance: an approved revision changes semantic meaning,
    # so the conflict graph of every Expert Model containing this asset is
    # stale. The rescan is heavy (NLI) and runs as a background task
    # (v0.9.2a) - the approval event records that it was scheduled, and each
    # background scan writes its own CONFLICT_SCAN_COMPLETED event. State
    # transition and recomputation are deliberately separate.
    affected_ids = affected_expert_model_ids(session, asset)

    crud.log_audit_event(
        session,
        actor=actor,
        event_type="ASSET_REVISION_APPROVED",
        target_id=str(asset.id),
        details=json.dumps({
            "asset_id": asset.id,
            "revision_id": revision.id,
            "revision_number": revision.revision_number,
            "superseded_revision_id": old_active.id if old_active else None,
            "content_hash": revision.content_hash,
            "notes": notes,
            "rescan_scheduled": bool(affected_ids),
            "affected_model_ids": affected_ids
        })
    )
    return revision


def affected_expert_model_ids(session: Session, asset: db.KnowledgeAsset) -> list:
    """Expert Models whose conflict graph is staled by a change to this asset."""
    ids = []
    models = session.query(db.ExpertModel).filter(
        db.ExpertModel.project_id == asset.project_id
    ).all()
    for model in models:
        try:
            asset_ids = json.loads(model.asset_ids_json or "[]")
        except Exception:
            asset_ids = []
        if asset.id in asset_ids:
            ids.append(model.id)
    return ids


def run_post_approval_rescan(asset_id: int):
    """Background-task entry point (v0.9.2a): owns its session so it can run
    after the approval response has been sent. Invalidates content-bound
    verdicts and rescans every affected Expert Model; each scan writes its
    own CONFLICT_SCAN_COMPLETED audit event."""
    session = db.SessionLocal()
    try:
        asset = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
        if not asset:
            print(f"Post-approval rescan skipped: asset {asset_id} no longer exists")
            return
        _rescan_affected_models(session, asset)
    finally:
        session.close()


def _rescan_affected_models(session: Session, asset: db.KnowledgeAsset) -> list:
    from app import conflict_engine
    results = []
    for model_id in affected_expert_model_ids(session, asset):
        model = session.query(db.ExpertModel).filter(db.ExpertModel.id == model_id).first()
        try:
            # Operator conflict verdicts are content-bound: a CONFIRMED or
            # DISMISSED verdict involving this asset judged content that no
            # longer exists. Invalidate those pairs so the rescan re-judges
            # them fresh; verdicts on unrelated pairs survive untouched.
            stale = session.query(db.AssetRelationship).filter(
                db.AssetRelationship.expert_model_id == model.id,
                (db.AssetRelationship.source_asset_id == asset.id) |
                (db.AssetRelationship.target_asset_id == asset.id)
            ).all()
            invalidated_reviews = sum(1 for r in stale if r.status in ("CONFIRMED", "DISMISSED"))
            for r in stale:
                session.delete(r)
            session.commit()

            scan = conflict_engine.scan_expert_model_conflicts(session, model.id)
            results.append({
                "expert_model_id": model.id,
                "nli_available": scan["nli_available"],
                "conflicts_found": scan["conflicts_found"],
                "invalidated_reviews": invalidated_reviews,
                "semantic_conflict_score": scan["semantic_conflict_score"]
            })
        except Exception as e:
            print(f"Post-approval conflict rescan failed for model {model.id}: {e}")
            results.append({"expert_model_id": model.id, "error": str(e)})
    return results


def get_revisions(session: Session, asset_id: int):
    return session.query(db.AssetRevision).filter(
        db.AssetRevision.asset_id == asset_id
    ).order_by(db.AssetRevision.revision_number.desc()).all()
