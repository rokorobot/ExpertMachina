import json
import datetime

from sqlalchemy.orm import Session

from app import database as db
from app import conflict_engine
from app import trust
from app import policy as policy_module
from app import tier2 as tier2_module
from app import proposals as proposals_module
from app.projections import engine as projection_engine

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
    # v1.4.0 WS2 (D30): the shared class annotator - the inbox and the
    # conflicts workbench cannot disagree about asymmetry.
    annotations = conflict_engine.class_annotations(session, rels)

    items = []
    for rel in rels:
        disposition = conflict_engine.relationship_gate_disposition(rel, policy)
        annotation = annotations[rel.id]
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

        # D30: the asymmetry is declared wherever the conflict is
        # surfaced - a presentation ruling; severity and disposition
        # above are class-blind.
        if annotation["class_asymmetry"] == "PRIMARY_OVER_DERIVED" and bucket != "RESOLVED":
            reason += (" Primary prevails: the derived side is the presumptive "
                       "review target unless a human rules otherwise.")

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
            **annotation,
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


# v1.2.1 WS4 (D26): ingestion exceptions - the automation ladder's held
# and uncovered candidates, projected from ledger facts and current
# governed objects. NO new state, NO dismiss: an item exists while the
# asset is CANDIDATE and leaves the moment a human reviews it or the
# governing facts change (D1/D24). Per D2, ingestion exceptions never
# block the compile gate, so they are never HIGH - ranked visibility,
# not false emergency.
#
# ONE severity function; an unknown kind fails loudly (the consumption-
# inbox discipline).
_EXCEPTION_SEVERITY = {
    # v1.4.0 WS1 (D29/D30): agent proposals. Unverifiable synthesis
    # provenance is the loud case; a verified proposal awaiting the
    # human gate is the proposal lane working exactly as ruled.
    "PROPOSAL_PROVENANCE_UNVERIFIED": "MEDIUM",
    "PROPOSAL_AWAITING_GATE": "LOW",
    "TIER2_CONTRADICTION_HELD": "MEDIUM",  # the engine refused; a human must judge the content
    "TIER2_UNVERIFIED": "MEDIUM",          # automation was configured but could not complete
    "SOURCE_AUTHORITY_HELD": "MEDIUM",     # covered by Tier-0, but the source did not vouch
    "NOT_COVERED": "LOW",                  # no automation covers it - the ordinary human queue
    "UNCLASSIFIED": "LOW",                 # classification exists but assigned nothing
}


def ingestion_exception_severity(kind: str) -> str:
    if kind not in _EXCEPTION_SEVERITY:
        raise ValueError(f"Unknown ingestion exception kind: {kind}")
    return _EXCEPTION_SEVERITY[kind]


def _latest_automation_evidence(session: Session, candidate_ids: set) -> tuple:
    """(tier2_holds, source_holds): per-asset evidence from the newest
    ledger event naming each asset. Read-only ledger projection."""
    tier2_holds, source_holds = {}, {}
    for event in session.query(db.AuditEvent).filter(
            db.AuditEvent.event_type == "POLICY_TIER2_COMPLETED"
    ).order_by(db.AuditEvent.id).all():
        try:
            details = json.loads(event.details or "{}")
        except ValueError:
            continue
        for hold in details.get("held") or []:
            if hold.get("asset_id") in candidate_ids:
                tier2_holds[hold["asset_id"]] = {**hold, "event_id": event.id,
                                                 "created_at": event.timestamp}
    for event in session.query(db.AuditEvent).filter(
            db.AuditEvent.event_type == "POLICY_AUTOAPPROVAL_COMPLETED"
    ).order_by(db.AuditEvent.id).all():
        try:
            details = json.loads(event.details or "{}")
        except ValueError:
            continue
        for asset_id in details.get("source_condition_held_ids") or []:
            if asset_id in candidate_ids:
                source_holds[asset_id] = {
                    "event_id": event.id, "created_at": event.timestamp,
                    "policies": details.get("policies") or []}
    return tier2_holds, source_holds


def _projection_staleness_items(session: Session, project_id: int) -> list:
    """v1.3 WS1 (D28): staleness is computed, detectable, never silent.
    The latest render per renderer (projected from PROJECTION_RENDERED
    ledger events alone) is recomposed and compared by content hash; a
    drifted render surfaces as a LOW hygiene item. LOW by ruling: a
    stale render never blocks the compile gate (D2), and it is repaired
    by regenerating, never by editing. No dismiss - the item leaves when
    the render is regenerated."""
    items = []
    for entry in projection_engine.render_history(session, project_id):
        if entry.get("current") and entry.get("stale"):
            items.append({
                "id": f"PROJECTION-{entry['event_id']}",
                "type": "PROJECTION_STALE",
                "source_id": entry["event_id"],
                "renderer": entry.get("renderer"),
                "clearance": entry.get("clearance"),
                "rendered_at": entry.get("rendered_at"),
                "audit_cursor": entry.get("audit_cursor"),
                "severity": "LOW",
                "bucket": "CAN_WAIT",
                "reason": (f"The latest '{entry.get('renderer')}' render no "
                           f"longer reflects governed facts - regenerate it."),
                "created_at": entry.get("timestamp"),
                "resolved_at": None,
            })
    return items


def _ingestion_exception_items(session: Session, project_id: int,
                               asset_names: dict) -> list:
    candidates = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id,
        db.KnowledgeAsset.status == "CANDIDATE",
    ).order_by(db.KnowledgeAsset.id).all()
    if not candidates:
        return []

    tier2_holds, source_holds = _latest_automation_evidence(
        session, {a.id for a in candidates})
    approval_policies = session.query(db.ApprovalPolicy).filter(
        db.ApprovalPolicy.project_id == project_id,
        db.ApprovalPolicy.enabled == True,  # noqa: E712 - SQLAlchemy expression
    ).order_by(db.ApprovalPolicy.id).all()
    classification_in_scope = session.query(db.ClassificationPolicy).filter(
        db.ClassificationPolicy.project_id == project_id,
        db.ClassificationPolicy.enabled == True,  # noqa: E712
    ).count() > 0

    # A candidate's connector context, for honest connector-scope coverage.
    doc_connector = {}
    doc_ids = {a.document_id for a in candidates if a.document_id}
    if doc_ids:
        for sd in session.query(db.SourceDocument).filter(
                db.SourceDocument.document_id.in_(doc_ids)
        ).order_by(db.SourceDocument.id).all():
            doc_connector[sd.document_id] = sd.connector_id

    # v1.4.0 WS1 (D29/D30): proposal-lane candidates are the most
    # specific state a candidate can be in - constitutionally held for
    # the human gate, with synthesis provenance verified live against
    # governed records (computed here, never stored).
    proposal_verdicts = proposals_module.proposal_verdicts(
        session, sorted(doc_ids)) if doc_ids else {}

    items = []
    for asset in candidates:
        connector_id = doc_connector.get(asset.document_id)
        covering = [p for p in approval_policies
                    if (p.connector_id is None or p.connector_id == connector_id)
                    and asset.type in p.asset_types
                    and policy_module.domain_covered(p, asset)]
        tier2_covering = [p for p in covering if tier2_module.is_tier2(p)]

        # Most specific explanation wins; exactly one item per candidate.
        if asset.document_id in proposal_verdicts:
            verdict = proposal_verdicts[asset.document_id]
            if not verdict["provenance_verified"]:
                kind = "PROPOSAL_PROVENANCE_UNVERIFIED"
                title = (f"Proposal held: '{asset.name}' has unverified "
                         f"synthesis provenance")
                reason = ("An agent proposal claims provenance that could not "
                          "be verified against governed records ("
                          + "; ".join(verdict["reasons"])
                          + "). Held for review - the human gate decides; "
                          "nothing is rejected by the engine.")
            else:
                kind = "PROPOSAL_AWAITING_GATE"
                verified = verdict["verified"]
                title = f"Proposal: '{asset.name}' awaits the human gate"
                reason = (f"Agent-synthesized proposal from "
                          f"'{verified['agent_principal']}' under binding "
                          f"{verified['binding_id']} (package "
                          f"{verified['package_hash'][:12]}…) - provenance "
                          f"verified. Proposal-lane candidates are never "
                          f"auto-approved (D29); accepting it creates a "
                          f"DERIVED fact.")
            extra = {"provenance_claimed": verdict["provenance_claimed"],
                     "provenance_verified": verdict["provenance_verified"],
                     "provenance_reasons": verdict["reasons"],
                     "binding_id": (verdict["verified"] or {}).get("binding_id"),
                     "cited_assets": verdict["cited_assets"]}
            created_at = asset.created_at
        elif asset.id in tier2_holds:
            hold = tier2_holds[asset.id]
            top = (hold.get("contradictions") or [{}])[0]
            contra_name = asset_names.get(top.get("asset_id"),
                                          f"Asset {top.get('asset_id')}")
            kind = "TIER2_CONTRADICTION_HELD"
            title = f"Held: '{asset.name}' contradicts approved '{contra_name}'"
            reason = (f"The engine refused to auto-approve: contradiction with "
                      f"approved asset {top.get('asset_id')} "
                      f"(score {top.get('score')}). Engines refuse to approve; "
                      f"only humans refuse content - review the candidate.")
            extra = {"contradicting_asset_id": top.get("asset_id"),
                     "contradiction_score": top.get("score"),
                     "audit_event_id": hold["event_id"]}
            created_at = hold.get("created_at")
        elif asset.id in source_holds:
            hold = source_holds[asset.id]
            kind = "SOURCE_AUTHORITY_HELD"
            title = f"Held: '{asset.name}' lacks source authority"
            reason = ("Covered by a source-authority policy, but the source "
                      "metadata did not satisfy its conditions - the source "
                      "did not vouch for this document. Review manually.")
            extra = {"audit_event_id": hold["event_id"],
                     "policies": hold["policies"]}
            created_at = hold.get("created_at")
        elif tier2_covering:
            kind = "TIER2_UNVERIFIED"
            title = f"Unverified: '{asset.name}' awaits engine verification"
            reason = (f"Covered by Tier-2 policy "
                      f"'{tier2_covering[0].name}' (v{tier2_covering[0].version}) "
                      f"but no engine verdict approved or held it - the pass "
                      f"may be pending, unavailable, or failed. Review manually "
                      f"or re-scan.")
            extra = {"policy_id": tier2_covering[0].id}
            created_at = asset.created_at
        elif classification_in_scope and not asset.domain:
            kind = "UNCLASSIFIED"
            title = f"Unclassified: '{asset.name}' has no domain"
            reason = ("Classification policies are active but none assigned a "
                      "domain. Correct the domain on the asset or extend a "
                      "classification policy.")
            extra = {}
            created_at = asset.created_at
        else:
            kind = "NOT_COVERED"
            title = f"Awaiting review: '{asset.name}'"
            reason = ("No enabled approval policy covers this candidate - it "
                      "is in the ordinary human review queue by design "
                      "(deny-by-default coverage).")
            extra = {}
            created_at = asset.created_at

        items.append({
            "id": f"INGESTION_EXCEPTION-{asset.id}",
            "type": "INGESTION_EXCEPTION",
            "source_id": asset.id,
            "expert_model_id": None,
            "expert_model_name": None,
            "asset_id": asset.id,
            "document_id": asset.document_id,
            "domain": asset.domain,
            "status": "CANDIDATE",
            "classification": kind,
            "confidence": None,
            "severity": ingestion_exception_severity(kind),
            "bucket": "NEEDS_REVIEW" if ingestion_exception_severity(kind) == "MEDIUM"
                      else ("CAN_WAIT" if kind == "UNCLASSIFIED" else "NEEDS_REVIEW"),
            "title": title,
            "reason": reason,
            "deep_link": f"/?tab=assets&asset={asset.id}",
            "created_at": _iso(created_at),
            "resolved_at": None,
            **extra,
        })
    return items


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
    items += _ingestion_exception_items(session, project_id, asset_names)
    items += _projection_staleness_items(session, project_id)

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
        "ingestion_exceptions": sum(1 for i in items if i["type"] == "INGESTION_EXCEPTION"),
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
