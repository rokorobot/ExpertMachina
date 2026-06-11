import json
import datetime

from sqlalchemy.orm import Session

from app import database as db
from app import crud
from app import schemas

# Policy-Based Auto Approval (MVP 0.10.2).
#
# The pressure valve bulk ingestion requires: deterministic, versioned rules
# auto-approve low-risk asset classes at ingestion time, so the review queue
# holds only what genuinely needs a human. Scope rules, deliberately narrow:
#
#   - Applies to NEW CANDIDATE assets created by an ingestion event (upload,
#     connector scan, manual extract). Candidate REVISIONS of approved assets
#     always wait for a human - a revision changes already-trusted content.
#   - Matching is deterministic: asset.type against the policy's declared
#     type list, optionally scoped to one connector. Semantic conditions
#     (formatting-only diffs, NLI contradiction checks) are a later phase.
#   - Every auto-approval goes through crud.update_knowledge_asset - the
#     same transition path as a human approval (AssetReview row, baseline
#     revision, document lifecycle) - with actor "policy:<name>" and an
#     ASSET_AUTO_APPROVED event carrying machine-verifiable provenance:
#     policy id, name, version, and the rule snapshot that fired.
#   - D12 honesty: assets a policy declined are counted and declared in the
#     POLICY_AUTOAPPROVAL_COMPLETED summary, never silently skipped. When no
#     policy applies to a scope, nothing runs and nothing claims to have run.

ALLOWED_ASSET_TYPES = {"PROCEDURE", "POLICY", "ROLE", "SYSTEM", "WORKFLOW", "PRODUCT", "DEPARTMENT"}


def policies_for_scope(session: Session, project_id: int, connector_id: int = None) -> list:
    """Enabled policies applicable to an ingestion event. A connector-scoped
    policy fires only for that connector; an unscoped policy fires for any
    source, including manual upload."""
    policies = session.query(db.ApprovalPolicy).filter(
        db.ApprovalPolicy.project_id == project_id,
        db.ApprovalPolicy.enabled == True,  # noqa: E712 - SQLAlchemy expression
    ).order_by(db.ApprovalPolicy.id).all()
    return [p for p in policies if p.connector_id is None or p.connector_id == connector_id]


def apply_auto_approval(session: Session, project_id: int, document_ids: list,
                        connector_id: int = None, ingestion_job_id: int = None) -> dict:
    """Evaluate enabled policies against the CANDIDATE assets created from
    the given documents (one ingestion event). Returns a declared summary;
    writes per-asset ASSET_AUTO_APPROVED events and one
    POLICY_AUTOAPPROVAL_COMPLETED summary event when policies were in scope."""
    summary = {
        "policies_evaluated": 0,
        "assets_considered": 0,
        "auto_approved": 0,
        "skipped_type_not_covered": 0,
    }
    if not document_ids:
        return summary

    policies = policies_for_scope(session, project_id, connector_id)
    summary["policies_evaluated"] = len(policies)
    if not policies:
        return summary

    assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id,
        db.KnowledgeAsset.document_id.in_(document_ids),
        db.KnowledgeAsset.status == "CANDIDATE",
    ).order_by(db.KnowledgeAsset.id).all()
    summary["assets_considered"] = len(assets)

    approved_ids = []
    for asset in assets:
        matched = next((p for p in policies if asset.type in p.asset_types), None)
        if not matched:
            summary["skipped_type_not_covered"] += 1
            continue
        # Immutable provenance: six months later, "why was this approved
        # automatically?" must be answerable from this event alone.
        provenance = {
            "policy_id": matched.id,
            "policy_name": matched.name,
            "policy_version": matched.version,
            "policy_snapshot": {"asset_types": matched.asset_types, "connector_id": matched.connector_id},
            "asset_type": asset.type,
            "document_id": asset.document_id,
            "ingestion_job_id": ingestion_job_id,
            "approved_without_human": True,
            "triggered_at": datetime.datetime.utcnow().isoformat(),
        }
        crud.update_knowledge_asset(
            session, asset.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=f"policy:{matched.name}",
            audit_event_type="ASSET_AUTO_APPROVED",
            audit_details=json.dumps(provenance),
            review_notes=f"approved by policy: {matched.name} (v{matched.version})",
        )
        summary["auto_approved"] += 1
        approved_ids.append(asset.id)

    crud.log_audit_event(
        session, actor="policy_engine", event_type="POLICY_AUTOAPPROVAL_COMPLETED",
        target_id=str(ingestion_job_id) if ingestion_job_id else None,
        details=json.dumps({
            **summary,
            "connector_id": connector_id,
            "approved_asset_ids": approved_ids,
            "policies": [{"id": p.id, "name": p.name, "version": p.version} for p in policies],
        }))
    return summary
