"""Insights routes (audit T2.4, relocated VERBATIM from app/main.py).

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


# Agent Center: gateway activity aggregated from the audit ledger.
@router.get("/api/agents/activity")
def get_agent_activity(db_session: Session = Depends(get_db),
                       actor: identity.Actor = Depends(require_perm("audit:read"))):
    events = db_session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type.in_(["MCP_TOOL_CALLED", "MCP_ACCESS_DENIED"])
    ).order_by(db.AuditEvent.timestamp.desc()).limit(2000).all()

    agents = {}
    # Audit QW-5 (docs/audit-2026-07-07.md, M-CQ-1): unparseable ledger rows
    # used to vanish from this view with no trace. They are still excluded
    # from aggregation (their content is unreadable) but are now COUNTED and
    # reported - an activity view over an audit ledger must say when it
    # could not read part of the ledger.
    unparseable_events = 0
    for e in events:
        try:
            d = json.loads(e.details)
        except Exception:
            unparseable_events += 1
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
        "total_denied": sum(a["denied"] for a in agents.values()),
        # Honest reporting (D12): rows this view could not read are declared,
        # never silently dropped.
        "unparseable_events": unparseable_events
    }

# Audit Trail routes
@router.get("/api/audit", response_model=List[schemas.AuditEventResponse])
def get_audit_trail(
    limit: int = 100,
    event_prefix: Optional[str] = None,
    actor: Optional[str] = None,
    target_id: Optional[str] = None,
    since: Optional[datetime.datetime] = None,
    until: Optional[datetime.datetime] = None,
    db_session: Session = Depends(get_db),
    auth_actor: identity.Actor = Depends(require_perm("audit:read"))
):
    return crud.get_audit_events(
        db_session, limit=limit, event_prefix=event_prefix,
        actor=actor, target_id=target_id, since=since, until=until
    )

# Dashboard summaries
@router.get("/api/dashboard/{project_id}")
def get_dashboard_summary(project_id: int, db_session: Session = Depends(get_db),
                          actor: identity.Actor = Depends(require_perm("assets:read"))):
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

# Governance Inbox & Readiness Console (MVP 0.9.1): a computed operational
# index over existing reviewable records. Read-only - all review actions
# stay on the specialized workbench endpoints above.
@router.get("/api/projects/{project_id}/governance/inbox")
def get_governance_inbox(project_id: int, db_session: Session = Depends(get_db),
                         actor: identity.Actor = Depends(require_perm("assets:read"))):
    project = db_session.query(db.Project).filter(db.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return governance_inbox.build_inbox(db_session, project_id)

# The Operations view (v1.4.1, the D8 amendment recorded in
# docs/diagnostic-workbench-v1.4.md): a computed projection of Operations
# Realm activity - agents, the proposal pipeline (verdicts recomputed at
# read time, never stored), and the PROPOSAL lanes. Read-only; the only
# write in the area is the pre-existing asset-review PATCH (the human
# gate). MCP call aggregates stay behind audit:read (/api/agents/activity).
@router.get("/api/projects/{project_id}/operations")
def get_operations_view(project_id: int, db_session: Session = Depends(get_db),
                        actor: identity.Actor = Depends(require_perm("assets:read"))):
    project = db_session.query(db.Project).filter(db.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return operations_view.build_operations(db_session, project_id)

# Computed Consumption Inbox (v1.1.x WS2, D24): the v0.9.1 inbox pattern
# applied to consumption. Read-only and the ONE endpoint this milestone
# adds. Severity comes from consumption_inbox.severity_of - the single
# shared function (D2); missing hops are declared, never dropped (D12);
# nothing is persisted and there is deliberately NO dismiss/mark-resolved:
# items disappear when the underlying governed facts change.
@router.get("/api/consumption/inbox")
def get_consumption_inbox(project_id: Optional[int] = None,
                          db_session: Session = Depends(get_db),
                          actor: identity.Actor = Depends(require_perm("assets:read"))):
    return consumption_inbox.build_inbox(db_session, project_id)
