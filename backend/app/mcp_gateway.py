import os
import json
import datetime

from app import database as db
from app import crud
from app import query_engine
from app import conflict_engine
from app import trust
from app import revisions as revisions_module

# MCP Agent Gateway (MVP 0.9 Sprint 1) - READ-ONLY.
#
# The gateway exposes Governance Contract v1; it adds no semantics of its
# own. Every tool delegates to the exact functions the REST console uses,
# and every call emits an MCP_TOOL_CALLED audit event - the gateway itself
# is part of the governance boundary.
#
# Agent identity and clearance come from the MCP server configuration
# (per-agent connection): EM_AGENT_ID and EM_AGENT_CLEARANCE. Clearance
# follows Access Model v1 (PUBLIC < INTERNAL < RESTRICTED < EXECUTIVE)
# and defaults to the most restrictive tier when unset.

GATEWAY_VERSION = "mcp-gateway-v1"
VALID_CLEARANCES = ("PUBLIC", "INTERNAL", "RESTRICTED", "EXECUTIVE")


def agent_identity() -> dict:
    clearance = os.environ.get("EM_AGENT_CLEARANCE", "PUBLIC").upper()
    if clearance not in VALID_CLEARANCES:
        clearance = "PUBLIC"
    return {
        "agent_id": os.environ.get("EM_AGENT_ID", "unidentified-agent"),
        "clearance": clearance,
    }


def _audit_tool_call(session, tool_name: str, expert_model_id, extra: dict = None):
    identity = agent_identity()
    crud.log_audit_event(
        session,
        actor=identity["agent_id"],
        event_type="MCP_TOOL_CALLED",
        target_id=str(expert_model_id) if expert_model_id is not None else None,
        details=json.dumps({
            "tool_name": tool_name,
            "agent_id": identity["agent_id"],
            "clearance": identity["clearance"],
            "expert_model_id": expert_model_id,
            "gateway_version": GATEWAY_VERSION,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            **(extra or {})
        })
    )


def _check_asset_clearance(session, asset: db.KnowledgeAsset, tool_name: str):
    """Access Model v1: deny when the asset's tier exceeds the agent's
    clearance. Denials are themselves audit events."""
    identity = agent_identity()
    asset_rank = query_engine._access_rank(asset.access_level)
    agent_rank = query_engine._access_rank(identity["clearance"])
    if asset_rank > agent_rank:
        crud.log_audit_event(
            session,
            actor=identity["agent_id"],
            event_type="MCP_ACCESS_DENIED",
            target_id=str(asset.id),
            details=json.dumps({
                "tool_name": tool_name,
                "agent_id": identity["agent_id"],
                "clearance": identity["clearance"],
                "required_access_level": asset.access_level,
                "asset_id": asset.id,
                "gateway_version": GATEWAY_VERSION,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            })
        )
        raise ValueError(
            f"Access denied: asset {asset.id} requires {asset.access_level} clearance; "
            f"this agent has {identity['clearance']}."
        )


def ask_expert(expert_model_id: int, question: str, session=None) -> dict:
    """Verified Answer v1 (Governance Contract section 8), under the
    calling agent's clearance."""
    own_session = session is None
    session = session or db.SessionLocal()
    try:
        identity = agent_identity()
        _audit_tool_call(session, "ask_expert", expert_model_id, {"question": question})
        result = query_engine.execute_expert_query(
            session,
            expert_model_id=expert_model_id,
            question=question,
            caller_access_level=identity["clearance"],
            actor=identity["agent_id"]
        )
        return result
    finally:
        if own_session:
            session.close()


def get_trust_score(expert_model_id: int, session=None) -> dict:
    """Trust Score v1 (Governance Contract section 7)."""
    own_session = session is None
    session = session or db.SessionLocal()
    try:
        _audit_tool_call(session, "get_trust_score", expert_model_id)
        return trust.compute_trust_score(session, expert_model_id)
    finally:
        if own_session:
            session.close()


def check_gate_status(expert_model_id: int, session=None) -> dict:
    """Compile Gate v1 verdict (Governance Contract section 6),
    previewed without side effects."""
    own_session = session is None
    session = session or db.SessionLocal()
    try:
        _audit_tool_call(session, "check_gate_status", expert_model_id)
        gate = conflict_engine.evaluate_compile_gate(session, expert_model_id)
        return {
            "expert_model_id": expert_model_id,
            "status": "ALLOWED" if gate["allowed"] else "BLOCKED",
            "reasons": gate["blocking_conflicts"],
            "advisory_conflicts": gate["advisory_conflicts"],
            "dismissed_conflicts": gate["dismissed_conflicts"],
            "conflict_scan_performed": gate["conflict_scan_performed"],
            "policy": gate["policy"]
        }
    finally:
        if own_session:
            session.close()


def get_provenance(asset_id: int, session=None) -> dict:
    """Chain of custody for one asset (Governance Contract sections 3-4):
    document, page, section, hashes, approver identity, active revision."""
    own_session = session is None
    session = session or db.SessionLocal()
    try:
        _audit_tool_call(session, "get_provenance", None, {"asset_id": asset_id})
        asset = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
        if not asset:
            raise LookupError(f"Asset {asset_id} not found")
        _check_asset_clearance(session, asset, "get_provenance")
        citation = query_engine._build_citation(session, asset)
        return {
            **citation,
            "type": asset.type,
            "access_level": asset.access_level,
            "extraction_method": asset.extraction_method,
            "document_id": asset.document_id,
            "chunk_id": asset.chunk_id,
            "revision_count": asset.revision_count,
            "has_pending_revision": asset.has_pending_revision
        }
    finally:
        if own_session:
            session.close()


def get_conflicts(expert_model_id: int, session=None) -> dict:
    """Semantic conflict relationships for an Expert Model (Governance
    Contract section 5). Returns relationship metadata only - asset content
    stays behind the clearance-checked tools."""
    own_session = session is None
    session = session or db.SessionLocal()
    try:
        _audit_tool_call(session, "get_conflicts", expert_model_id)
        rels = session.query(db.AssetRelationship).filter(
            db.AssetRelationship.expert_model_id == expert_model_id
        ).order_by(db.AssetRelationship.confidence.desc()).all()
        score = conflict_engine.compute_semantic_conflict_score(session, expert_model_id)
        return {
            "expert_model_id": expert_model_id,
            "semantic_conflict_score": score["semantic_conflict_score"],
            "semantic_conflict_summary": score["semantic_conflict_summary"],
            "relationships": [{
                "id": r.id,
                "source_asset_id": r.source_asset_id,
                "target_asset_id": r.target_asset_id,
                "relationship_type": r.relationship_type,
                "classification": r.classification,
                "confidence": r.confidence,
                "status": r.status,
                "detected_at": r.detected_at.isoformat() if r.detected_at else None,
                "reviewed_by": r.reviewed_by,
                "review_notes": r.notes,
                "verifier": r.verifier
            } for r in rels]
        }
    finally:
        if own_session:
            session.close()


def get_revision_history(asset_id: int, session=None) -> dict:
    """Immutable revision chain for one asset (Governance Contract
    section 4), under the calling agent's clearance."""
    own_session = session is None
    session = session or db.SessionLocal()
    try:
        _audit_tool_call(session, "get_revision_history", None, {"asset_id": asset_id})
        asset = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id == asset_id).first()
        if not asset:
            raise LookupError(f"Asset {asset_id} not found")
        _check_asset_clearance(session, asset, "get_revision_history")
        revs = revisions_module.get_revisions(session, asset_id)
        return {
            "asset_id": asset_id,
            "asset_name": asset.name,
            "active_revision_number": asset.active_revision_number,
            "revisions": [{
                "revision_number": r.revision_number,
                "status": r.status,
                "content": r.content,
                "content_hash": r.content_hash,
                "source_hash": r.source_hash,
                "created_by": r.created_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "approved_by": r.approved_by,
                "approved_at": r.approved_at.isoformat() if r.approved_at else None,
                "supersedes_revision_id": r.supersedes_revision_id,
                "superseded_by_revision_id": r.superseded_by_revision_id,
                "change_reason": r.change_reason
            } for r in revs]
        }
    finally:
        if own_session:
            session.close()
