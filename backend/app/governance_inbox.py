import json
import datetime

from sqlalchemy.orm import Session

from app import database as db
from app import conflict_engine
from app import trust

# Governance Inbox & Readiness Console (MVP 0.9.1).
#
# A computed operational index over existing reviewable records - NOT a new
# governance state machine. No new tables, no new statuses, no writes: every
# item is derived live from AssetRelationship, AssetRevision, and the trust
# components, and deep-links into the specialized workbench where the actual
# review decision happens.
#
# Severity is derived through conflict_engine.relationship_gate_disposition,
# the same rule evaluate_compile_gate uses, so the inbox and the compile gate
# can never disagree about what blocks deployment.
#
#   HIGH    blocks the compile gate
#   MEDIUM  requires a human verdict but does not block compile
#   LOW     live-computed governance fact (freshness, provenance, coverage)
#
# Buckets answer "what do I do with this":
#   NEEDS_REVIEW  actionable now (blocking conflicts, advisory detections,
#                 pending candidate revisions)
#   CAN_WAIT      informational warnings and policy-allowed confirmed conflicts
#   RESOLVED      reviewed within the last RESOLVED_WINDOW_DAYS days

INBOX_VERSION = "governance-inbox-v1"
RESOLVED_WINDOW_DAYS = 7

_SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
_CLASS_LABELS = {
    "DIRECT_CONTRADICTION": "direct contradiction",
    "ACCESS_CONFLICT": "access conflict",
    "SCOPE_CONFLICT": "scope conflict",
    "TEMPORAL_SUPERSESSION": "temporal supersession",
}


def _iso(dt):
    return dt.isoformat() if dt else None


def _conflict_items(session: Session, project_id: int, model_names: dict,
                    asset_names: dict, policy: dict, resolved_cutoff) -> list:
    rels = session.query(db.AssetRelationship).filter(
        db.AssetRelationship.project_id == project_id,
        db.AssetRelationship.relationship_type == "CONFLICTS_WITH"
    ).all()

    items = []
    for rel in rels:
        disposition = conflict_engine.relationship_gate_disposition(rel, policy)
        label = _CLASS_LABELS.get(rel.classification, "conflict")
        name_a = asset_names.get(rel.source_asset_id, f"Asset {rel.source_asset_id}")
        name_b = asset_names.get(rel.target_asset_id, f"Asset {rel.target_asset_id}")
        title = f"{label.capitalize()}: '{name_a}' vs '{name_b}'"

        if disposition == "DISMISSED":
            if not rel.reviewed_at or rel.reviewed_at < resolved_cutoff:
                continue  # old dismissals are contextualized noise, not inbox items
            severity, bucket = "LOW", "RESOLVED"
            reason = f"Dismissed by {rel.reviewed_by or 'operator'}."
        elif disposition == "BLOCKING":
            severity, bucket = "HIGH", "NEEDS_REVIEW"
            if rel.status == "CONFIRMED":
                reason = "Blocks compile gate: confirmed conflict requires asset remediation."
            else:
                reason = "Blocks compile gate: unreviewed conflict requires a review verdict."
        else:  # ADVISORY
            if rel.status == "CONFIRMED":
                severity, bucket = "MEDIUM", "CAN_WAIT"
                reason = "Confirmed conflict; compile policy allows deployment."
            else:
                severity, bucket = "MEDIUM", "NEEDS_REVIEW"
                reason = "Advisory conflict awaiting review (does not block compile)."

        items.append({
            "id": f"CONFLICT-{rel.id}",
            "type": "CONFLICT",
            "source_id": rel.id,
            "expert_model_id": rel.expert_model_id,
            "expert_model_name": model_names.get(rel.expert_model_id),
            "source_asset_id": rel.source_asset_id,
            "target_asset_id": rel.target_asset_id,
            "status": rel.status,
            "classification": rel.classification,
            "confidence": rel.confidence,
            "severity": severity,
            "bucket": bucket,
            "title": title,
            "reason": reason,
            "deep_link": f"/?tab=conflicts&expert={rel.expert_model_id}&relationship={rel.id}",
            "created_at": _iso(rel.detected_at),
            "resolved_at": _iso(rel.reviewed_at) if bucket == "RESOLVED" else None,
        })
    return items


def _revision_items(session: Session, project_id: int, resolved_cutoff,
                    model_assets: dict) -> list:
    rows = session.query(db.AssetRevision).join(
        db.KnowledgeAsset, db.AssetRevision.asset_id == db.KnowledgeAsset.id
    ).filter(db.KnowledgeAsset.project_id == project_id).all()

    items = []
    for rev in rows:
        if rev.status == "ARCHIVED":
            continue  # supersession bookkeeping, never a work item
        if rev.status == "CANDIDATE":
            severity, bucket = "MEDIUM", "NEEDS_REVIEW"
            reason = "Pending candidate revision on an approved asset awaits an approve/reject verdict."
            resolved_at = None
        else:  # APPROVED | REJECTED
            # Lazily-created baseline revisions are auto-approved bookkeeping,
            # not review outcomes; real candidates always supersede something.
            if rev.supersedes_revision_id is None:
                continue
            # REJECTED rows carry no review timestamp; created_at is the best
            # available recency signal for the resolved window.
            resolved_at = rev.approved_at or rev.created_at
            if not resolved_at or resolved_at < resolved_cutoff:
                continue
            severity, bucket = "LOW", "RESOLVED"
            actor = rev.approved_by or rev.created_by or "operator"
            reason = (f"Approved by {actor}." if rev.status == "APPROVED"
                      else "Rejected; active revision unchanged.")

        asset = rev.asset
        items.append({
            "id": f"REVISION-{rev.id}",
            "type": "REVISION",
            "source_id": rev.id,
            # Revisions are asset-scoped, not model-scoped; the related ids
            # exist only so the readiness panel's model filter can include them.
            "expert_model_id": None,
            "expert_model_name": None,
            "related_expert_model_ids": [
                mid for mid, ids in model_assets.items() if rev.asset_id in ids
            ],
            "asset_id": rev.asset_id,
            "status": rev.status,
            "classification": None,
            "confidence": None,
            "severity": severity,
            "bucket": bucket,
            "title": f"Revision {rev.revision_number} of '{asset.name}'",
            "reason": reason,
            "deep_link": f"/?tab=revisions&revision={rev.id}",
            "created_at": _iso(rev.created_at),
            "resolved_at": _iso(resolved_at) if bucket == "RESOLVED" else None,
        })
    return items


def _evidence_gap_items(session: Session, model_id: int, model_name: str) -> list:
    """Evidence gaps from the LATEST completed evaluation run for the model -
    the same latest-run rule trust.py uses, so superseded gaps disappear on
    the next run exactly like recomputed conflicts do. No cross-run state.

    Severity preserves the v0.9.1 invariant that HIGH means blocks-the-
    compile-gate (evidence gaps do not): CONTRADICTED claims are MEDIUM and
    need review now (they hard-fail answers); UNSUPPORTED claims are LOW
    coverage risks that can wait."""
    run = session.query(db.EvaluationRun).filter(
        db.EvaluationRun.expert_model_id == model_id,
        db.EvaluationRun.status == "COMPLETED"
    ).order_by(db.EvaluationRun.id.desc()).first()
    if not run:
        return []

    verdicts = session.query(db.ClaimVerdict).filter(
        db.ClaimVerdict.evaluation_run_id == run.id,
        db.ClaimVerdict.verdict.in_(["UNSUPPORTED", "CONTRADICTED"])
    ).all()

    items = []
    for v in verdicts:
        if v.verdict == "CONTRADICTED":
            severity, bucket = "MEDIUM", "NEEDS_REVIEW"
            reason = ("Answer claim contradicts approved evidence - hard-fails queries. "
                      "Review the evidence or revise the conflicting asset.")
        else:
            severity, bucket = "LOW", "CAN_WAIT"
            reason = "Claim lacks supporting evidence - coverage risk. Attach a source document or revise the asset."
        claim_preview = v.claim if len(v.claim) <= 90 else v.claim[:87] + "..."
        items.append({
            "id": f"EVIDENCE_GAP-{v.id}",
            "type": "EVIDENCE_GAP",
            "source_id": v.id,
            "expert_model_id": model_id,
            "expert_model_name": model_name,
            "status": v.verdict,
            "classification": None,
            "confidence": v.confidence,
            "severity": severity,
            "bucket": bucket,
            "title": f"{'Contradicted' if v.verdict == 'CONTRADICTED' else 'Unsupported'} claim: \"{claim_preview}\"",
            "reason": reason,
            "deep_link": f"/?tab=evaluations&run={run.id}&result={v.question_result_id}",
            "created_at": _iso(v.created_at),
            "resolved_at": None,
        })
    return items


def _warning_items(trust_score: dict, model_id: int, model_name: str) -> list:
    """LOW-severity live facts derived from the trust components. Unreviewed
    conflicts and pending revisions are NOT duplicated here - they already
    appear as first-class inbox items."""
    items = []
    components = {c["key"]: c for c in trust_score["components"]}

    freshness = components.get("revision_freshness")
    if freshness and freshness["measured"] and freshness["score"] is not None and freshness["score"] < 100:
        days = freshness["details"].get("days_since_last_review")
        items.append(("stale_review",
                      f"Governance review stale: {days} days since last review",
                      freshness["reason"]))

    health = components.get("governance_health")
    if health:
        for penalty in health["details"].get("penalties", []):
            if penalty["signal"] == "missing_provenance":
                items.append(("missing_provenance",
                              f"{penalty['count']} asset{'s' if penalty['count'] != 1 else ''} missing provenance",
                              f"Provenance fields incomplete; trust penalty -{penalty['penalty']}."))

    reliability = components.get("evaluation_reliability")
    if reliability and not reliability["measured"]:
        items.append(("no_evaluation",
                      "No completed evaluation run",
                      "Evaluation reliability and evidence coverage are unmeasured."))

    return [{
        "id": f"WARNING-{model_id}-{signal}",
        "type": "GOVERNANCE_WARNING",
        "source_id": model_id,
        "expert_model_id": model_id,
        "expert_model_name": model_name,
        "status": "ACTIVE",
        "classification": None,
        "confidence": None,
        "severity": "LOW",
        "bucket": "CAN_WAIT",
        "title": title,
        "reason": reason,
        "deep_link": f"/?tab=experts&expert={model_id}",
        "created_at": None,
        "resolved_at": None,
    } for signal, title, reason in items]


def build_inbox(session: Session, project_id: int) -> dict:
    models = session.query(db.ExpertModel).filter(
        db.ExpertModel.project_id == project_id
    ).all()
    model_names = {m.id: m.name for m in models}
    assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id
    ).all()
    asset_names = {a.id: a.name for a in assets}

    policy = conflict_engine._gate_policy()
    now = datetime.datetime.utcnow()
    resolved_cutoff = now - datetime.timedelta(days=RESOLVED_WINDOW_DAYS)

    model_assets = {}
    for m in models:
        try:
            model_assets[m.id] = set(json.loads(m.asset_ids_json or "[]"))
        except Exception:
            model_assets[m.id] = set()

    items = _conflict_items(session, project_id, model_names, asset_names, policy, resolved_cutoff)
    items += _revision_items(session, project_id, resolved_cutoff, model_assets)

    # Per-model readiness: the existing compile gate response plus trust facts.
    # compute_trust_score is all cheap queries (no NLI), same as the existing
    # /api/projects/{id}/trust-scores endpoint.
    readiness = []
    for model in models:
        trust_score = trust.compute_trust_score(session, model.id)
        gate = conflict_engine.evaluate_compile_gate(session, model.id)
        items += _warning_items(trust_score, model.id, model.name)
        items += _evidence_gap_items(session, model.id, model.name)

        health = next((c for c in trust_score["components"] if c["key"] == "governance_health"), None)
        governance_facts = []
        if health:
            for p in health["details"].get("penalties", []):
                governance_facts.append(
                    f"{p['count']} {p['signal'].replace('_', ' ')} (-{p['penalty']})"
                )
        readiness.append({
            "expert_model_id": model.id,
            "expert_model_name": model.name,
            "trust_score": trust_score["trust_score"],
            "trust_summary": trust_score["summary"],
            "compile_allowed": gate["allowed"],
            "blocking_conflicts": gate["blocking_conflicts"],
            "advisory_conflicts": gate["advisory_conflicts"],
            "dismissed_conflicts": gate["dismissed_conflicts"],
            "conflict_scan_performed": gate["conflict_scan_performed"],
            "governance_facts": governance_facts,
        })

    # Severity first; within a tier the newest item matters most.
    items.sort(key=lambda i: i["created_at"] or "", reverse=True)
    items.sort(key=lambda i: _SEVERITY_RANK.get(i["severity"], 3))

    summary = {
        "needs_review": sum(1 for i in items if i["bucket"] == "NEEDS_REVIEW"),
        "can_wait": sum(1 for i in items if i["bucket"] == "CAN_WAIT"),
        "recently_resolved": sum(1 for i in items if i["bucket"] == "RESOLVED"),
        "high_severity": sum(1 for i in items if i["severity"] == "HIGH"),
        "blocked_expert_models": sum(1 for r in readiness if not r["compile_allowed"]),
        "total_expert_models": len(models),
    }

    return {
        "project_id": project_id,
        "inbox_version": INBOX_VERSION,
        "generated_at": now.isoformat(),
        "resolved_window_days": RESOLVED_WINDOW_DAYS,
        "gate_policy": policy,
        "summary": summary,
        "items": items,
        "readiness": readiness,
    }
