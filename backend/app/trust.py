import json
import datetime

from sqlalchemy.orm import Session

from app import database as db
from app import conflict_engine

# Expert Model Trust Score (MVP 0.8 Sprint 3).
#
# A first-class, hierarchical object - never a single opaque number.
# Five components, each 0-100 with a human-readable reason:
#
#   evaluation_reliability  pass rate of the latest completed benchmark run
#   evidence_coverage       average claim coverage of the latest run
#   conflict_integrity      the semantic conflict score (conflict-score-v1)
#   governance_health       penalties for governance debt: unreviewed
#                           conflicts, pending revisions, a currently
#                           blocked compile gate, missing provenance
#   revision_freshness      days since the last governance review activity
#
# Components without underlying data are reported as NOT_MEASURED and
# excluded from the weighted aggregate - never fabricated.

TRUST_VERSION = "trust-score-v1"

WEIGHTS = {
    "evaluation_reliability": 0.25,
    "evidence_coverage": 0.20,
    "conflict_integrity": 0.25,
    "governance_health": 0.20,
    "revision_freshness": 0.10,
}

LABELS = {
    "evaluation_reliability": "Evaluation Reliability",
    "evidence_coverage": "Evidence Coverage",
    "conflict_integrity": "Conflict Integrity",
    "governance_health": "Governance Health",
    "revision_freshness": "Revision Freshness",
}

# Governance health penalties (governance signals, not knowledge signals).
PENALTY_UNREVIEWED_CONFLICT = 8.0
PENALTY_PENDING_REVISION = 5.0
PENALTY_BLOCKED_GATE = 15.0
PENALTY_MISSING_PROVENANCE = 4.0
MISSING_PROVENANCE_CAP = 20.0

# Revision freshness tiers: (max_days, score).
FRESHNESS_TIERS = [(30, 100.0), (90, 85.0), (180, 70.0), (365, 50.0)]
FRESHNESS_FLOOR = 25.0


def _component(key, score, reason, details=None, measured=True):
    return {
        "key": key,
        "label": LABELS[key],
        "score": round(score, 1) if score is not None else None,
        "weight": WEIGHTS[key],
        "measured": measured,
        "reason": reason,
        "details": details or {},
    }


def _member_assets(session: Session, expert_model):
    try:
        asset_ids = json.loads(expert_model.asset_ids_json or "[]")
    except Exception:
        asset_ids = []
    if not asset_ids:
        return []
    return session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.id.in_(asset_ids)).all()


def _evaluation_components(session: Session, expert_model_id: int):
    run = session.query(db.EvaluationRun).filter(
        db.EvaluationRun.expert_model_id == expert_model_id,
        db.EvaluationRun.status == "COMPLETED"
    ).order_by(db.EvaluationRun.id.desc()).first()

    if not run:
        reason = "No completed evaluation runs for this model - run a benchmark evaluation to measure."
        return (
            _component("evaluation_reliability", None, reason, measured=False),
            _component("evidence_coverage", None, reason, measured=False),
        )

    reliability = round(run.pass_rate * 100, 1)
    coverage = round(run.average_coverage_score * 100, 1)
    details = {"evaluation_run_id": run.id, "completed_at": run.completed_at.isoformat() if run.completed_at else None}
    return (
        _component("evaluation_reliability", reliability,
                   f"Pass rate {reliability}% on evaluation run #{run.id}.", details),
        _component("evidence_coverage", coverage,
                   f"Average claim coverage {coverage}% on evaluation run #{run.id}.", details),
    )


def _conflict_component(session: Session, expert_model_id: int):
    score = conflict_engine.compute_semantic_conflict_score(session, expert_model_id)
    return _component(
        "conflict_integrity",
        score["semantic_conflict_score"],
        score["semantic_conflict_summary"],
        {"score_version": score["score_version"], "breakdown": score["breakdown"]},
    )


def _governance_health_component(session: Session, expert_model, assets):
    penalties = []

    unreviewed = session.query(db.AssetRelationship).filter(
        db.AssetRelationship.expert_model_id == expert_model.id,
        db.AssetRelationship.relationship_type == "CONFLICTS_WITH",
        db.AssetRelationship.status == "DETECTED"
    ).count()
    if unreviewed:
        penalties.append({"signal": "unreviewed_conflicts", "count": unreviewed,
                          "penalty": round(unreviewed * PENALTY_UNREVIEWED_CONFLICT, 1)})

    asset_ids = [a.id for a in assets]
    pending = 0
    if asset_ids:
        pending = session.query(db.AssetRevision).filter(
            db.AssetRevision.asset_id.in_(asset_ids),
            db.AssetRevision.status == "CANDIDATE"
        ).count()
    if pending:
        penalties.append({"signal": "pending_revisions", "count": pending,
                          "penalty": round(pending * PENALTY_PENDING_REVISION, 1)})

    gate = conflict_engine.evaluate_compile_gate(session, expert_model.id)
    if not gate["allowed"]:
        penalties.append({"signal": "compile_gate_blocked", "count": len(gate["blocking_conflicts"]),
                          "penalty": PENALTY_BLOCKED_GATE})

    missing = sum(
        1 for a in assets
        if not a.source_hash or a.source_page is None or not a.source_section
    )
    if missing:
        penalties.append({"signal": "missing_provenance", "count": missing,
                          "penalty": round(min(missing * PENALTY_MISSING_PROVENANCE, MISSING_PROVENANCE_CAP), 1)})

    total_penalty = sum(p["penalty"] for p in penalties)
    score = max(0.0, 100.0 - total_penalty)
    if penalties:
        reason = "; ".join(f"{p['count']} {p['signal'].replace('_', ' ')} (-{p['penalty']})" for p in penalties) + "."
    else:
        reason = "No outstanding governance debt."
    return _component("governance_health", score, reason, {"penalties": penalties, "compile_gate_allowed": gate["allowed"]})


def _freshness_component(session: Session, assets):
    asset_ids = [a.id for a in assets]
    if not asset_ids:
        return _component("revision_freshness", None, "Model has no member assets.", measured=False)

    last_review = session.query(db.AssetReview).filter(
        db.AssetReview.asset_id.in_(asset_ids)
    ).order_by(db.AssetReview.reviewed_at.desc()).first()

    if not last_review or not last_review.reviewed_at:
        return _component("revision_freshness", None,
                          "No recorded governance reviews for member assets.", measured=False)

    days = max(0, (datetime.datetime.utcnow() - last_review.reviewed_at).days)
    score = FRESHNESS_FLOOR
    for max_days, tier_score in FRESHNESS_TIERS:
        if days <= max_days:
            score = tier_score
            break
    return _component("revision_freshness", score,
                      f"Last governance review {days} day{'s' if days != 1 else ''} ago.",
                      {"days_since_last_review": days, "last_reviewed_by": last_review.approver or last_review.reviewer})


def compute_trust_score(session: Session, expert_model_id: int) -> dict:
    expert_model = session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not expert_model:
        raise LookupError(f"Expert Model with ID {expert_model_id} not found")

    assets = _member_assets(session, expert_model)
    reliability, coverage = _evaluation_components(session, expert_model_id)
    components = [
        reliability,
        coverage,
        _conflict_component(session, expert_model_id),
        _governance_health_component(session, expert_model, assets),
        _freshness_component(session, assets),
    ]

    measured = [c for c in components if c["measured"]]
    total_weight = sum(c["weight"] for c in measured)
    if total_weight > 0:
        trust_score = round(sum(c["score"] * c["weight"] for c in measured) / total_weight, 1)
    else:
        trust_score = None

    measured_count = len(measured)
    summary = (
        f"Trust score {trust_score} from {measured_count} of {len(components)} components"
        f" (weights renormalized over measured components)."
        if trust_score is not None else
        "Trust score not computable: no components have underlying data yet."
    )

    return {
        "expert_model_id": expert_model_id,
        "trust_score": trust_score,
        "score_version": TRUST_VERSION,
        "summary": summary,
        "components": components,
    }
