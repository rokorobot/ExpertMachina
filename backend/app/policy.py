import json
import datetime

from sqlalchemy.orm import Session

from app import database as db
from app import crud
from app import schemas
from app import identity
from app import classification

# Policy-Based Auto Approval (MVP 0.10.2; Tier-0 source authority v1.2.1 WS2, D26).
#
# The pressure valve bulk ingestion requires: deterministic, versioned rules
# auto-approve low-risk asset classes at ingestion time, so the review queue
# holds only what genuinely needs a human. Scope rules, deliberately narrow:
#
#   - Applies to NEW CANDIDATE assets created by an ingestion event (upload,
#     connector scan, manual extract). Candidate REVISIONS of approved assets
#     always wait for a human - a revision changes already-trusted content.
#   - Matching is deterministic: asset.type against the policy's declared
#     type list, optionally scoped to one connector. Tier-0 (D26): a policy
#     may additionally require source-authority conditions - deterministic
#     equals/in matches (dotted keys) against the VERBATIM source metadata
#     persisted on the scan row. Source authority is EVIDENCE for approval,
#     not approval itself: the source is trusted only through an explicit
#     governed policy, versioned rules, audit evidence. Absent metadata
#     never satisfies a condition (D12); NULL or empty conditions preserve
#     v0.10.2 behavior exactly (the D19 empty-config invariant).
#   - Every auto-approval goes through crud.update_knowledge_asset - the
#     same transition path as a human approval (AssetReview row, baseline
#     revision, document lifecycle) - with actor "policy:<name>" and an
#     ASSET_AUTO_APPROVED event carrying machine-verifiable provenance:
#     policy id, name, version, the rule snapshot that fired, and - for a
#     Tier-0 firing - the matched authority metadata quoted verbatim.
#   - D12 honesty: assets a policy declined are counted and declared in the
#     POLICY_AUTOAPPROVAL_COMPLETED summary, never silently skipped -
#     including assets HELD because source conditions were unmet. When no
#     policy applies to a scope, nothing runs and nothing claims to have run.

ALLOWED_ASSET_TYPES = {"PROCEDURE", "POLICY", "ROLE", "SYSTEM", "WORKFLOW", "PRODUCT", "DEPARTMENT"}


def validate_source_conditions(conditions):
    """Structural validation of Tier-0 conditions - loud, never permissive.
    Returns the normalized list, or None when empty (empty conditions are
    stored as NULL: no conditions to fail, the pre-Tier-0 behavior)."""
    if conditions is None:
        return None
    if not isinstance(conditions, list):
        raise ValueError("source_conditions must be a list")
    for i, cond in enumerate(conditions):
        if not isinstance(cond, dict) or not cond.get("key"):
            raise ValueError(f"source_conditions[{i}]: needs a 'key'")
        if ("equals" in cond) == ("in" in cond):
            raise ValueError(f"source_conditions[{i}]: exactly one of 'equals'/'in'")
        if "in" in cond and not isinstance(cond["in"], list):
            raise ValueError(f"source_conditions[{i}]: 'in' must be a list")
        unknown = set(cond) - {"key", "equals", "in"}
        if unknown:
            raise ValueError(f"source_conditions[{i}]: unknown fields {sorted(unknown)}")
    return conditions or None


def validate_domains(domains):
    """Optional domain-prefix coverage narrowing (D26/D27). Empty lists
    are stored as NULL (all domains - existing behavior preserved)."""
    if domains is None:
        return None
    if not isinstance(domains, list):
        raise ValueError("domains must be a list of domain path prefixes")
    return [classification.validate_domain_path(d) for d in domains] or None


def domain_covered(policy_row, asset) -> bool:
    """Deny-by-default coverage: a policy with declared domains covers
    only assets under those prefixes; an UNCLASSIFIED asset is not under
    any prefix. NULL domains = all domains (v0.10.2 behavior)."""
    domains = policy_row.domains
    if not domains:
        return True
    if not asset.domain:
        return False
    return any(asset.domain == d or asset.domain.startswith(d + "/")
               for d in domains)


def source_conditions_met(policy_row, source_metadata):
    """(met, matched_evidence). ALL conditions must hold (AND); evidence
    quotes the values that carried the authority, for provenance. A key
    the source did not expose never satisfies - absence is not
    satisfaction (D12)."""
    conditions = policy_row.source_conditions
    if not conditions:
        return True, None  # NULL/empty = no conditions to fail (D19 invariant)
    evidence = {}
    for cond in conditions:
        found, value = classification.metadata_value(source_metadata or {}, cond["key"])
        if not found:
            return False, None
        if "equals" in cond and value != cond["equals"]:
            return False, None
        if "in" in cond and value not in cond["in"]:
            return False, None
        evidence[cond["key"]] = value
    return True, evidence


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
                        connector_id: int = None, ingestion_job_id: int = None,
                        on_behalf_of_fact=None) -> dict:
    """Evaluate enabled policies against the CANDIDATE assets created from
    the given documents (one ingestion event). Returns a declared summary;
    writes per-asset ASSET_AUTO_APPROVED events and one
    POLICY_AUTOAPPROVAL_COMPLETED summary event when policies were in scope.

    Identity Boundary v1.0: each firing policy acts as a DELEGATED actor
    `policy:<name>` whose identity fact chains to on_behalf_of_fact (the
    connector's fact for a scan, the human's fact for upload/extract) -
    the WHO chain. The causal WHY stays where D17 put it: the provenance
    JSON on the ASSET_AUTO_APPROVED event (ActionContext, independent)."""
    summary = {
        "policies_evaluated": 0,
        "assets_considered": 0,
        "auto_approved": 0,
        "skipped_type_not_covered": 0,
        "skipped_source_conditions_unmet": 0,
        "deferred_to_tier2": 0,
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

    # Tier-0 evidence: the verbatim source metadata persisted on this
    # ingestion event's scan rows. Uploads have none - source-authority
    # policies simply cannot fire for them (honest, not fabricated).
    source_context = classification._source_context(session, document_ids, ingestion_job_id)

    approved_ids = []
    held_ids = []  # declared exceptions: type covered, source conditions unmet
    policy_actors = {}  # one DELEGATED actor (one fact) per firing policy per run
    for asset in assets:
        source_uri, source_metadata = source_context.get(asset.document_id, (None, {}))
        matched, matched_evidence = None, None
        conditions_blocked, tier2_relevant = False, False
        for p in policies:
            if asset.type not in p.asset_types:
                continue
            if not domain_covered(p, asset):
                continue
            if p.engine_conditions:
                # Tier-2 policies cannot decide synchronously - the
                # engine verdict belongs to the async pass (D4). The
                # asset is DEFERRED, honestly, not skipped.
                tier2_relevant = True
                continue
            met, evidence = source_conditions_met(p, source_metadata)
            if not met:
                conditions_blocked = True
                continue
            matched, matched_evidence = p, evidence
            break
        if not matched:
            if conditions_blocked:
                # Source authority is evidence for approval, not approval
                # itself: without it the asset HOLDS for a human - a
                # declared exception, never an engine rejection.
                summary["skipped_source_conditions_unmet"] += 1
                held_ids.append(asset.id)
            elif tier2_relevant:
                summary["deferred_to_tier2"] += 1
            else:
                summary["skipped_type_not_covered"] += 1
            continue
        if matched.id not in policy_actors:
            policy_actors[matched.id] = identity.delegated_actor(
                session, f"policy:{matched.name}", on_behalf_of=on_behalf_of_fact)
        # Immutable provenance: six months later, "why was this approved
        # automatically?" must be answerable from this event alone.
        provenance = {
            "policy_id": matched.id,
            "policy_name": matched.name,
            "policy_version": matched.version,
            "policy_snapshot": {"asset_types": matched.asset_types,
                                "connector_id": matched.connector_id,
                                "source_conditions": matched.source_conditions,
                                "domains": matched.domains},
            "asset_type": asset.type,
            "document_id": asset.document_id,
            "ingestion_job_id": ingestion_job_id,
            "approved_without_human": True,
            "triggered_at": datetime.datetime.utcnow().isoformat(),
        }
        if matched.source_conditions:
            # Tier-0: the inherited authority is NAMED in the event -
            # matched metadata quoted verbatim, indefinitely answerable.
            provenance["source_authority"] = {
                "matched": matched_evidence,
                "source_uri": source_uri,
            }
        crud.update_knowledge_asset(
            session, asset.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=policy_actors[matched.id],
            audit_event_type="ASSET_AUTO_APPROVED",
            audit_details=json.dumps(provenance),
            review_notes=f"approved by policy: {matched.name} (v{matched.version})",
        )
        summary["auto_approved"] += 1
        approved_ids.append(asset.id)

    engine_actor = identity.system_actor(session, "policy_engine")
    crud.log_audit_event(
        session, actor=engine_actor.display, identity_fact_id=engine_actor.fact(session).id,
        event_type="POLICY_AUTOAPPROVAL_COMPLETED",
        target_id=str(ingestion_job_id) if ingestion_job_id else None,
        details=json.dumps({
            **summary,
            "connector_id": connector_id,
            "approved_asset_ids": approved_ids,
            "source_condition_held_ids": held_ids,
            "policies": [{"id": p.id, "name": p.name, "version": p.version} for p in policies],
        }))
    return summary
