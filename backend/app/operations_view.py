from sqlalchemy.orm import Session

from app import database as db
from app import proposals

# The Operations view (v1.4.1 - the D8 amendment recorded in
# docs/diagnostic-workbench-v1.4.md).
#
# A pure projection (D1/D24) of Operations Realm activity: which bound
# agents exist and what they have proposed, which proposals are in
# flight at the human gate, and the lanes they arrive through. NO new
# state, no dismiss, no workflow rows - current governed facts and the
# proposal documents themselves are the only sources, and every
# provenance verdict is recomputed at read time (never stored).
#
# "Operate" here means the HUMAN side of the loop only (D22 held):
# reviewing held proposals through the one existing review write,
# administering PROPOSAL-lane connectors, scan-now. ExpertMachina never
# launches agents - workbench execution stays outside the boundary.
#
# Read grants: everything here derives from assets-scoped governed
# facts (documents, assets, connectors, principals, bindings), so the
# endpoint rides assets:read. MCP call aggregates are ledger-derived
# and stay behind the existing audit:read surface (/api/agents/activity)
# - the UI merges them only for viewers who hold that grant.


def _iso(dt):
    return dt.isoformat() if dt else None


def build_operations(session: Session, project_id: int) -> dict:
    # ---- Lanes: the PROPOSAL-lane connectors and their scan history.
    lane_connectors = session.query(db.SourceConnector).filter(
        db.SourceConnector.project_id == project_id,
        db.SourceConnector.lane == "PROPOSAL",
    ).order_by(db.SourceConnector.id).all()
    lanes = []
    for connector in lane_connectors:
        last_job = session.query(db.IngestionJob).filter(
            db.IngestionJob.connector_id == connector.id,
        ).order_by(db.IngestionJob.id.desc()).first()
        lanes.append({
            "connector_id": connector.id,
            "name": connector.name,
            "root_path": connector.root_path,
            "include_extensions": connector.include_extensions,
            "created_at": _iso(connector.created_at),
            "last_scan": None if last_job is None else {
                "job_id": last_job.id,
                "status": last_job.status,
                "started_at": _iso(last_job.started_at),
                "completed_at": _iso(last_job.completed_at),
                "files_discovered": last_job.files_discovered,
                "files_ingested": last_job.files_ingested,
                "files_changed": last_job.files_changed,
            },
        })

    # ---- The pipeline: every proposal document, its recomputed
    # provenance verdict, and its candidates at the gate.
    lane_ids = [c.id for c in lane_connectors]
    doc_connector = {}
    if lane_ids:
        for sd in session.query(db.SourceDocument).filter(
                db.SourceDocument.connector_id.in_(lane_ids),
                db.SourceDocument.document_id.isnot(None),
        ).order_by(db.SourceDocument.id).all():
            doc_connector[sd.document_id] = sd.connector_id

    pipeline = []
    proposal_stats = {}  # agent principal name -> counters
    for doc_id in sorted(doc_connector):
        document = session.query(db.Document).filter(
            db.Document.id == doc_id).first()
        if document is None:
            continue
        verdict = proposals.verify_provenance(session, doc_id)
        assets = session.query(db.KnowledgeAsset).filter(
            db.KnowledgeAsset.document_id == doc_id,
        ).order_by(db.KnowledgeAsset.id).all()
        held = [a for a in assets if a.status == "CANDIDATE"]
        accepted = [a for a in assets if a.status == "APPROVED"]
        agent_name = ((verdict.get("verified") or {}).get("agent_principal")
                      or verdict["claimed"].get("agent_principal"))
        pipeline.append({
            "document_id": doc_id,
            "filename": document.filename,
            "connector_id": doc_connector[doc_id],
            "ingested_at": _iso(document.created_at),
            "agent_principal": agent_name,
            "provenance": verdict,  # recomputed, verbatim claims included
            "candidates": [{
                "asset_id": a.id,
                "name": a.name,
                "type": a.type,
                "status": a.status,
                "source_class": a.source_class,
            } for a in assets],
            "held_count": len(held),
            "accepted_count": len(accepted),
        })
        stats = proposal_stats.setdefault(agent_name or "(unattributed)", {
            "proposal_documents": 0, "held_candidates": 0,
            "accepted_derived": 0, "unverified_documents": 0,
        })
        stats["proposal_documents"] += 1
        stats["held_candidates"] += len(held)
        stats["accepted_derived"] += sum(
            1 for a in accepted if a.source_class == "DERIVED")
        if not verdict["provenance_verified"]:
            stats["unverified_documents"] += 1

    # ---- The agents: every AGENT principal, its bindings, and what it
    # has proposed. Registry + governed facts only.
    agents = []
    for principal in session.query(db.Principal).filter(
            db.Principal.kind == "AGENT").order_by(db.Principal.id).all():
        bindings = session.query(db.ExpertAgentBinding).filter(
            db.ExpertAgentBinding.agent_principal_id == principal.id,
        ).order_by(db.ExpertAgentBinding.id).all()
        latest = bindings[-1] if bindings else None
        agents.append({
            "principal_id": principal.id,
            "name": principal.name,
            "display_name": principal.display_name,
            "active": bool(principal.active),
            "clearance": principal.clearance,
            "bindings": len(bindings),
            "latest_binding": None if latest is None else {
                "binding_id": latest.id,
                "package_version": latest.package_version,
                "package_hash": latest.package_hash,
                "selected_provider": latest.selected_provider,
                "selected_model_name": latest.selected_model_name,
                "created_at": _iso(latest.created_at),
            },
            "proposals": proposal_stats.get(principal.name, {
                "proposal_documents": 0, "held_candidates": 0,
                "accepted_derived": 0, "unverified_documents": 0,
            }),
        })

    unattributed = proposal_stats.get("(unattributed)")
    return {
        "project_id": project_id,
        "agents": agents,
        "pipeline": pipeline,
        "lanes": lanes,
        # Declared, never silent (D12): proposals whose provenance names
        # no resolvable agent still count somewhere visible.
        "unattributed_proposals": unattributed,
        "summary": {
            "agents": len(agents),
            "active_agents": sum(1 for a in agents if a["active"]),
            "lanes": len(lanes),
            "proposal_documents": len(pipeline),
            "held_candidates": sum(p["held_count"] for p in pipeline),
            "accepted_derived": sum(
                1 for p in pipeline for c in p["candidates"]
                if c["status"] == "APPROVED" and c["source_class"] == "DERIVED"),
            "unverified_documents": sum(
                1 for p in pipeline
                if not p["provenance"]["provenance_verified"]),
        },
    }
