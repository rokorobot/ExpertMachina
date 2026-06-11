import os
import json
import datetime
import itertools

from sqlalchemy.orm import Session

from app import database as db
from app import crud
from app import ingestion
from app import verification_engine

# Semantic Conflict Engine (MVP 0.7 Sprint 1).
# Runs pairwise NLI across the approved assets of an Expert Model and stores
# explicit relationships: CONFLICTS_WITH (with a conflict classification) and
# SUPPORTS. Neutral pairs are not stored. The RELATED relationship type is
# reserved in the schema for embedding-based association once real (non-mock)
# embeddings are guaranteed.
#
# NLI is asymmetric, so every pair is judged in both directions and the
# stronger signal wins. Operator review verdicts (CONFIRMED / DISMISSED)
# survive rescans; only unreviewed DETECTED rows are recomputed.

CLASSIFIER_VERSION = "RULE_METADATA_V1"
# Pairwise scans grow O(n^2); above this many pairs the embedding pre-filter
# keeps the most similar pairs and the scan reports how many were dropped.
MAX_NLI_PAIRS = int(os.environ.get("EM_CONFLICT_MAX_PAIRS", "400"))
# Knowledge-base scanning operates at a stricter threshold than answer
# verification: most asset pairs are unrelated, so the prior of a true
# conflict is low, while empirically true conflicts score 0.99+. A looser
# threshold lets cross-domain NLI noise (~0.82) surface as false alarms.
CONFLICT_CONTRADICTION_THRESHOLD = float(os.environ.get("EM_CONFLICT_CONTRADICTION_THRESHOLD", "0.90"))
CONFLICT_ENTAILMENT_THRESHOLD = float(os.environ.get("EM_CONFLICT_ENTAILMENT_THRESHOLD", "0.90"))

# Semantic conflict score (MVP 0.7 Sprint 3): 100 - weighted penalty.
# Penalties are per detected conflict pair, weighted by how severe the
# classification is and how the operator has reviewed it. A dismissed
# conflict is nearly free - the operator has already contextualized it.
# This score is standalone: it is NEVER averaged into quality_score.
SCORE_VERSION = "conflict-score-v1"
CLASSIFICATION_PENALTIES = {
    "DIRECT_CONTRADICTION": 10.0,
    "ACCESS_CONFLICT": 8.0,
    "SCOPE_CONFLICT": 5.0,
    "TEMPORAL_SUPERSESSION": 3.0,
}
STATUS_MULTIPLIERS = {
    "CONFIRMED": 1.2,
    "DETECTED": 1.0,
    "DISMISSED": 0.1,
}
_CLASS_LABELS = {
    "DIRECT_CONTRADICTION": "direct contradiction",
    "ACCESS_CONFLICT": "access conflict",
    "SCOPE_CONFLICT": "scope conflict",
    "TEMPORAL_SUPERSESSION": "temporal supersession",
}


def compute_semantic_conflict_score(session: Session, expert_model_id: int) -> dict:
    """Explainable contradiction-density score for an Expert Model.
    Returns the score, a human-readable reason, and the full penalty
    breakdown so the number is never magic."""
    conflicts = session.query(db.AssetRelationship).filter(
        db.AssetRelationship.expert_model_id == expert_model_id,
        db.AssetRelationship.relationship_type == "CONFLICTS_WITH"
    ).all()

    if not conflicts:
        return {
            "expert_model_id": expert_model_id,
            "semantic_conflict_score": 100.0,
            "semantic_conflict_summary": "No semantic conflicts detected across approved assets.",
            "breakdown": [],
            "score_version": SCORE_VERSION
        }

    counts = {}
    for rel in conflicts:
        key = (rel.status, rel.classification or "DIRECT_CONTRADICTION")
        counts[key] = counts.get(key, 0) + 1

    status_order = ["CONFIRMED", "DETECTED", "DISMISSED"]
    class_order = list(CLASSIFICATION_PENALTIES)
    breakdown = []
    parts = []
    total_penalty = 0.0
    for status in status_order:
        for classification in class_order:
            count = counts.get((status, classification), 0)
            if not count:
                continue
            penalty = round(count * CLASSIFICATION_PENALTIES[classification] * STATUS_MULTIPLIERS[status], 2)
            total_penalty += penalty
            breakdown.append({
                "status": status,
                "classification": classification,
                "count": count,
                "penalty": penalty
            })
            label = _CLASS_LABELS[classification]
            parts.append(f"{count} {status.lower()} {label}{'s' if count > 1 else ''}")

    score = max(0.0, round(100.0 - total_penalty, 1))
    return {
        "expert_model_id": expert_model_id,
        "semantic_conflict_score": score,
        "semantic_conflict_summary": ", ".join(parts) + ".",
        "breakdown": breakdown,
        "score_version": SCORE_VERSION
    }


def classify_conflict(session: Session, asset_a, asset_b) -> str:
    """Metadata-based conflict classification. Not every contradiction is a
    policy error: supersession, scope, and access tiers explain many of them.
    Order matters - the most specific structural explanation wins."""
    if (asset_a.name == asset_b.name and asset_a.type == asset_b.type
            and asset_a.document_id != asset_b.document_id):
        return "TEMPORAL_SUPERSESSION"

    doc_a = session.query(db.Document).filter(db.Document.id == asset_a.document_id).first()
    doc_b = session.query(db.Document).filter(db.Document.id == asset_b.document_id).first()
    if (doc_a and doc_b and doc_a.department and doc_b.department
            and doc_a.department != doc_b.department):
        return "SCOPE_CONFLICT"

    if (asset_a.access_level or "INTERNAL") != (asset_b.access_level or "INTERNAL"):
        return "ACCESS_CONFLICT"

    return "DIRECT_CONTRADICTION"


def _prefilter_pairs(pairs: list) -> tuple:
    """Embedding pre-filter for large models: keep the most similar pairs,
    report how many were dropped (no silent caps)."""
    if len(pairs) <= MAX_NLI_PAIRS:
        return pairs, 0
    embeddings = {}

    def emb(asset):
        if asset.id not in embeddings:
            embeddings[asset.id] = ingestion.get_embedding(asset.content)
        return embeddings[asset.id]

    scored = sorted(
        ((verification_engine._cosine(emb(a), emb(b)), a, b) for a, b in pairs),
        key=lambda item: item[0],
        reverse=True,
    )
    kept = [(a, b) for _, a, b in scored[:MAX_NLI_PAIRS]]
    return kept, len(pairs) - len(kept)


def scan_expert_model_conflicts(session: Session, expert_model_id: int) -> dict:
    expert_model = session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not expert_model:
        raise ValueError(f"Expert Model with ID {expert_model_id} not found")

    asset_ids = []
    if expert_model.asset_ids_json:
        try:
            asset_ids = json.loads(expert_model.asset_ids_json)
        except Exception:
            asset_ids = []
    assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.id.in_(asset_ids),
        db.KnowledgeAsset.status == "APPROVED"
    ).all()

    summary = {
        "expert_model_id": expert_model_id,
        "scanned_assets": len(assets),
        "compared_pairs": 0,
        "dropped_pairs": 0,
        "nli_available": False,
        "conflicts_found": 0,
        "supports_found": 0,
        "relationships": [],
        "semantic_conflict_score": 100.0,
        "semantic_conflict_summary": "No semantic conflicts detected across approved assets."
    }

    pipe = verification_engine.get_nli_pipeline()
    if pipe is None or len(assets) < 2:
        score = compute_semantic_conflict_score(session, expert_model_id)
        summary["semantic_conflict_score"] = score["semantic_conflict_score"]
        summary["semantic_conflict_summary"] = score["semantic_conflict_summary"]
        return summary
    summary["nli_available"] = True

    # Operator verdicts survive rescans: skip pairs already reviewed.
    reviewed_pairs = set()
    for rel in session.query(db.AssetRelationship).filter(
        db.AssetRelationship.expert_model_id == expert_model_id,
        db.AssetRelationship.status.in_(["CONFIRMED", "DISMISSED"])
    ).all():
        reviewed_pairs.add(frozenset((rel.source_asset_id, rel.target_asset_id)))

    # Unreviewed detections are recomputed from scratch.
    session.query(db.AssetRelationship).filter(
        db.AssetRelationship.expert_model_id == expert_model_id,
        db.AssetRelationship.status == "DETECTED"
    ).delete(synchronize_session=False)
    session.commit()

    pairs = [
        (a, b) for a, b in itertools.combinations(assets, 2)
        if frozenset((a.id, b.id)) not in reviewed_pairs
    ]
    pairs, dropped = _prefilter_pairs(pairs)
    summary["compared_pairs"] = len(pairs)
    summary["dropped_pairs"] = dropped
    if dropped:
        print(f"CONFLICT_SCAN: embedding pre-filter dropped {dropped} low-similarity pairs (cap {MAX_NLI_PAIRS}).")

    inputs = []
    for a, b in pairs:
        inputs.append({"text": a.content, "text_pair": b.content})
        inputs.append({"text": b.content, "text_pair": a.content})
    if not inputs:
        score = compute_semantic_conflict_score(session, expert_model_id)
        summary["semantic_conflict_score"] = score["semantic_conflict_score"]
        summary["semantic_conflict_summary"] = score["semantic_conflict_summary"]
        return summary

    results = pipe(inputs, top_k=None, truncation=True)
    # Record the scan's actual operating thresholds, not the answer-verifier's.
    verifier = {
        **verification_engine.verifier_identity(),
        "classifier": CLASSIFIER_VERSION,
        "entailment_threshold": CONFLICT_ENTAILMENT_THRESHOLD,
        "contradiction_threshold": CONFLICT_CONTRADICTION_THRESHOLD
    }

    new_rows = []
    for pair_idx, (a, b) in enumerate(pairs):
        score_ab = {s["label"].lower(): s["score"] for s in results[pair_idx * 2]}
        score_ba = {s["label"].lower(): s["score"] for s in results[pair_idx * 2 + 1]}
        contradiction = max(score_ab.get("contradiction", 0.0), score_ba.get("contradiction", 0.0))
        ent_ab = score_ab.get("entailment", 0.0)
        ent_ba = score_ba.get("entailment", 0.0)
        entailment = max(ent_ab, ent_ba)

        if contradiction >= CONFLICT_CONTRADICTION_THRESHOLD and contradiction > entailment:
            source, target = (a, b) if a.id < b.id else (b, a)
            new_rows.append(db.AssetRelationship(
                project_id=expert_model.project_id,
                expert_model_id=expert_model_id,
                source_asset_id=source.id,
                target_asset_id=target.id,
                relationship_type="CONFLICTS_WITH",
                classification=classify_conflict(session, a, b),
                confidence=round(contradiction, 3),
                verifier_json=json.dumps(verifier),
                status="DETECTED"
            ))
        elif entailment >= CONFLICT_ENTAILMENT_THRESHOLD:
            # Direction matters for support: the premise supports the claim.
            source, target = (a, b) if ent_ab >= ent_ba else (b, a)
            new_rows.append(db.AssetRelationship(
                project_id=expert_model.project_id,
                expert_model_id=expert_model_id,
                source_asset_id=source.id,
                target_asset_id=target.id,
                relationship_type="SUPPORTS",
                classification=None,
                confidence=round(entailment, 3),
                verifier_json=json.dumps(verifier),
                status="DETECTED"
            ))

    session.add_all(new_rows)
    session.commit()

    conflicts = [r for r in new_rows if r.relationship_type == "CONFLICTS_WITH"]
    supports = [r for r in new_rows if r.relationship_type == "SUPPORTS"]
    summary["conflicts_found"] = len(conflicts)
    summary["supports_found"] = len(supports)
    summary["relationships"] = new_rows

    score = compute_semantic_conflict_score(session, expert_model_id)
    summary["semantic_conflict_score"] = score["semantic_conflict_score"]
    summary["semantic_conflict_summary"] = score["semantic_conflict_summary"]

    for rel in conflicts:
        crud.log_audit_event(
            session,
            actor="conflict_engine",
            event_type="KNOWLEDGE_CONFLICT_DETECTED",
            target_id=str(expert_model_id),
            details=json.dumps({
                "source_asset_id": rel.source_asset_id,
                "target_asset_id": rel.target_asset_id,
                "classification": rel.classification,
                "confidence": rel.confidence,
                "verifier": verifier
            })
        )
    crud.log_audit_event(
        session,
        actor="conflict_engine",
        event_type="CONFLICT_SCAN_COMPLETED",
        target_id=str(expert_model_id),
        details=json.dumps({
            "scanned_assets": summary["scanned_assets"],
            "compared_pairs": summary["compared_pairs"],
            "dropped_pairs": summary["dropped_pairs"],
            "conflicts_found": summary["conflicts_found"],
            "supports_found": summary["supports_found"],
            "semantic_conflict_score": summary["semantic_conflict_score"],
            "semantic_conflict_summary": summary["semantic_conflict_summary"]
        })
    )
    return summary


# ---------------------------------------------------------------------------
# Package Compile Gates (MVP 0.8 Sprint 1)
# Package publication is a governance event: a model with unresolved
# semantic conflicts cannot cross the compile boundary.
#
# Policy (env-configurable, read at evaluation time):
#   EM_GATE_BLOCKING_CLASSIFICATIONS  unreviewed (DETECTED) conflicts of
#       these classes block compile. Default: DIRECT_CONTRADICTION,ACCESS_CONFLICT.
#       Other unreviewed classes are advisory.
#   EM_GATE_CONFIRMED_POLICY          'block' (default) or 'allow' for
#       operator-CONFIRMED conflicts of any class.
#   EM_GATE_REQUIRE_SCAN              '1' blocks compile when the model has
#       never had a conflict scan. Default '0'.
# Dismissed conflicts never block - the operator has contextualized them.


def _gate_policy() -> dict:
    return {
        "blocking_classifications": [
            c.strip() for c in os.environ.get(
                "EM_GATE_BLOCKING_CLASSIFICATIONS",
                "DIRECT_CONTRADICTION,ACCESS_CONFLICT"
            ).split(",") if c.strip()
        ],
        "confirmed_policy": os.environ.get("EM_GATE_CONFIRMED_POLICY", "block").lower(),
        "require_scan": os.environ.get("EM_GATE_REQUIRE_SCAN", "0") == "1",
    }


def relationship_gate_disposition(rel, policy: dict = None) -> str:
    """How a single conflict relationship affects the compile gate under the
    given policy: BLOCKING, ADVISORY, or DISMISSED. Single source of truth
    shared by evaluate_compile_gate and the governance inbox, so the two
    surfaces can never disagree about severity."""
    policy = policy or _gate_policy()
    if rel.status == "DISMISSED":
        return "DISMISSED"
    if rel.status == "CONFIRMED":
        return "BLOCKING" if policy["confirmed_policy"] == "block" else "ADVISORY"
    # DETECTED (and any unknown status, conservatively)
    return "BLOCKING" if rel.classification in policy["blocking_classifications"] else "ADVISORY"


def evaluate_compile_gate(session: Session, expert_model_id: int) -> dict:
    policy = _gate_policy()
    conflicts = session.query(db.AssetRelationship).filter(
        db.AssetRelationship.expert_model_id == expert_model_id,
        db.AssetRelationship.relationship_type == "CONFLICTS_WITH"
    ).all()

    scan_performed = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "CONFLICT_SCAN_COMPLETED",
        db.AuditEvent.target_id == str(expert_model_id)
    ).count() > 0

    def _ref(rel):
        return {
            "relationship_id": rel.id,
            "source_asset_id": rel.source_asset_id,
            "target_asset_id": rel.target_asset_id,
            "classification": rel.classification,
            "status": rel.status,
            "confidence": rel.confidence
        }

    blocking = []
    advisory = []
    dismissed_count = 0
    for rel in conflicts:
        disposition = relationship_gate_disposition(rel, policy)
        if disposition == "DISMISSED":
            dismissed_count += 1
        elif disposition == "BLOCKING":
            reason = "CONFIRMED_CONFLICT" if rel.status == "CONFIRMED" else "UNREVIEWED_CONFLICT"
            blocking.append({**_ref(rel), "reason": reason})
        else:
            advisory.append(_ref(rel))

    if policy["require_scan"] and not scan_performed:
        blocking.append({
            "relationship_id": None,
            "reason": "NO_CONFLICT_SCAN",
            "classification": None,
            "status": None,
            "confidence": None,
            "source_asset_id": None,
            "target_asset_id": None
        })

    return {
        "expert_model_id": expert_model_id,
        "allowed": not blocking,
        "blocking_conflicts": blocking,
        "advisory_conflicts": advisory,
        "dismissed_conflicts": dismissed_count,
        "conflict_scan_performed": scan_performed,
        "policy": policy
    }


def review_relationship(session: Session, relationship_id: int, status: str,
                        reviewer=None, notes: str = None):
    from app import identity
    reviewer = identity.require_actor_object(reviewer)
    if status not in ("CONFIRMED", "DISMISSED"):
        raise ValueError("Review status must be CONFIRMED or DISMISSED")
    rel = session.query(db.AssetRelationship).filter(db.AssetRelationship.id == relationship_id).first()
    if not rel:
        raise LookupError(f"Relationship {relationship_id} not found")
    rel.status = status
    rel.reviewed_by = reviewer.display
    rel.reviewed_at = datetime.datetime.utcnow()
    rel.notes = notes
    session.commit()
    session.refresh(rel)
    crud.log_audit_event(
        session,
        actor=reviewer.display,
        identity_fact_id=reviewer.fact(session).id,
        event_type=f"KNOWLEDGE_CONFLICT_{status}",
        target_id=str(rel.id),
        details=json.dumps({
            "source_asset_id": rel.source_asset_id,
            "target_asset_id": rel.target_asset_id,
            "classification": rel.classification,
            "notes": notes
        })
    )
    return rel
