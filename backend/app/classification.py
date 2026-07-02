import json
import datetime

from sqlalchemy.orm import Session

from app import database as db
from app import crud
from app import identity

# Domain Classification (v1.2.1 WS1, D27).
#
# Assets carry a governed hierarchical domain path (finances/accounting),
# assigned at ingestion by versioned classification policies and
# correctable by humans through the normal review surface. The rules:
#
#   - Domains are business dimensions, orthogonal to asset types - never
#     siblings in any hierarchy. This module writes ONLY the domain
#     column: never content, never status, never provenance, never
#     history. Classification is taxonomy governance, not asset editing.
#   - Deterministic assignment: enabled policies in id order, each
#     policy's rules in order, first match assigns. Applies to NEW
#     CANDIDATE assets of the triggering ingestion event whose domain is
#     NULL - assignment fills the unclassified, it never overwrites a
#     human correction or an earlier assignment.
#   - Every assignment writes ASSET_CLASSIFIED with the policy snapshot
#     that fired (D17 provenance discipline); unmatched assets are
#     counted and declared, never silent (D12). When no policy is in
#     scope, nothing runs and nothing claims to have run.
#   - Metadata conditions evaluate against the verbatim source metadata
#     persisted on the scan row (source_documents.source_metadata_json,
#     D26); a condition referencing absent metadata never matches -
#     absence is not satisfaction (D12).
#   - Reorganizations nest by default (prefix rewrite); replacement and
#     policy-driven splits are explicit audited taxonomy operations
#     recording the old->new mapping per asset (TAXONOMY_REORGANIZED).
#
# Rule shape (rules_json on ClassificationPolicy):
#   [{"domain": "finances/accounting",
#     "match": {"uri_prefix": "sharepoint://site/drive/Finance/",
#               "metadata": [{"key": "list_item_fields.Department",
#                             "equals": "Accounting"},
#                            {"key": "mime_type", "in": ["application/pdf"]}]}}]
# All criteria within a rule must hold (AND). A rule with an empty match
# matches everything in the policy's scope - a deliberate catch-all, not
# an absence loophole.


def validate_domain_path(path: str) -> str:
    """Hierarchical path grammar: non-empty /-separated segments, no
    leading/trailing slash. Returns the normalized path or raises."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("domain path must be a non-empty string")
    normalized = path.strip()
    segments = normalized.split("/")
    if any(not s.strip() for s in segments):
        raise ValueError(
            f"domain path {path!r} has empty segments - use "
            f"'finances/accounting' form, no leading/trailing slashes")
    return "/".join(s.strip() for s in segments)


def validate_rules(rules) -> list:
    """Structural validation of a policy's rule list - loud, never
    permissive: a malformed rule is a rejected definition, not a rule
    that silently never fires."""
    if not isinstance(rules, list) or not rules:
        raise ValueError("rules must be a non-empty list")
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict) or "domain" not in rule:
            raise ValueError(f"rule {i}: each rule needs a 'domain'")
        validate_domain_path(rule["domain"])
        match = rule.get("match", {})
        if not isinstance(match, dict):
            raise ValueError(f"rule {i}: 'match' must be an object")
        unknown = set(match) - {"uri_prefix", "metadata"}
        if unknown:
            raise ValueError(f"rule {i}: unknown match criteria {sorted(unknown)}")
        if "uri_prefix" in match and not (
                isinstance(match["uri_prefix"], str) and match["uri_prefix"]):
            raise ValueError(f"rule {i}: uri_prefix must be a non-empty string")
        for j, cond in enumerate(match.get("metadata") or []):
            if not isinstance(cond, dict) or "key" not in cond:
                raise ValueError(f"rule {i} metadata[{j}]: needs a 'key'")
            if ("equals" in cond) == ("in" in cond):
                raise ValueError(
                    f"rule {i} metadata[{j}]: exactly one of 'equals'/'in'")
            if "in" in cond and not isinstance(cond["in"], list):
                raise ValueError(f"rule {i} metadata[{j}]: 'in' must be a list")
    return rules


def metadata_value(metadata: dict, dotted_key: str):
    """Traverse nested metadata by dotted key. Returns (found, value) -
    found=False when any segment is absent, so callers can keep absence
    and null distinct from a matching value (D12)."""
    current = metadata
    for segment in dotted_key.split("."):
        if not isinstance(current, dict) or segment not in current:
            return False, None
        current = current[segment]
    return True, current


def rule_matches(rule: dict, source_uri: str, source_metadata: dict):
    """(matched, evidence) - evidence quotes the values that carried the
    match, for ASSET_CLASSIFIED provenance."""
    match = rule.get("match", {})
    evidence = {}
    prefix = match.get("uri_prefix")
    if prefix is not None:
        if not (source_uri or "").startswith(prefix):
            return False, None
        evidence["uri_prefix"] = prefix
    for cond in match.get("metadata") or []:
        found, value = metadata_value(source_metadata or {}, cond["key"])
        if not found:
            return False, None  # absence is never satisfaction (D12)
        if "equals" in cond and value != cond["equals"]:
            return False, None
        if "in" in cond and value not in cond["in"]:
            return False, None
        evidence.setdefault("metadata", {})[cond["key"]] = value
    return True, evidence


def policies_for_scope(session: Session, project_id: int, connector_id: int = None) -> list:
    """Enabled classification policies applicable to an ingestion event,
    in stable id order - the deterministic evaluation order."""
    policies = session.query(db.ClassificationPolicy).filter(
        db.ClassificationPolicy.project_id == project_id,
        db.ClassificationPolicy.enabled == True,  # noqa: E712 - SQLAlchemy expression
    ).order_by(db.ClassificationPolicy.id).all()
    return [p for p in policies if p.connector_id is None or p.connector_id == connector_id]


def _source_context(session: Session, document_ids: list, ingestion_job_id: int = None) -> dict:
    """document_id -> (source_uri, source_metadata) from the scan rows of
    this ingestion event; manual uploads have neither (rules that need
    them simply cannot match - honest, not fabricated)."""
    query = session.query(db.SourceDocument).filter(
        db.SourceDocument.document_id.in_(document_ids))
    if ingestion_job_id:
        query = query.filter(db.SourceDocument.ingestion_job_id == ingestion_job_id)
    # id order so the newest scan row wins deterministically when a
    # document has rows from multiple scans (per-scan rows are history, D7).
    return {sd.document_id: (sd.source_uri, sd.source_metadata or {})
            for sd in query.order_by(db.SourceDocument.id).all()}


def first_match(policies: list, source_uri: str, source_metadata: dict):
    """The deterministic decision: first matching rule of the first
    matching policy (policies in id order, rules in list order)."""
    for pol in policies:
        for index, rule in enumerate(pol.rules):
            matched, evidence = rule_matches(rule, source_uri, source_metadata)
            if matched:
                return pol, index, rule, evidence
    return None, None, None, None


def classify_assets(session: Session, project_id: int, document_ids: list,
                    connector_id: int = None, ingestion_job_id: int = None,
                    on_behalf_of_fact=None) -> dict:
    """Assign governed domains to the unclassified CANDIDATE assets of one
    ingestion event. Writes per-asset ASSET_CLASSIFIED events and one
    DOMAIN_CLASSIFICATION_COMPLETED summary when policies were in scope.
    Mirrors policy.apply_auto_approval's identity discipline: each firing
    policy acts as a DELEGATED actor `classification:<name>` chaining to
    on_behalf_of_fact."""
    summary = {
        "policies_evaluated": 0,
        "assets_considered": 0,
        "classified": 0,
        "unmatched": 0,
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
        db.KnowledgeAsset.domain.is_(None),
    ).order_by(db.KnowledgeAsset.id).all()
    summary["assets_considered"] = len(assets)

    context = _source_context(session, document_ids, ingestion_job_id)
    classified_ids = []
    policy_actors = {}  # one DELEGATED actor (one fact) per firing policy per run
    for asset in assets:
        source_uri, source_metadata = context.get(asset.document_id, (None, {}))
        pol, rule_index, rule, evidence = first_match(policies, source_uri, source_metadata)
        if not pol:
            summary["unmatched"] += 1
            continue
        if pol.id not in policy_actors:
            policy_actors[pol.id] = identity.delegated_actor(
                session, f"classification:{pol.name}", on_behalf_of=on_behalf_of_fact)
        actor = policy_actors[pol.id]
        asset.domain = rule["domain"]
        session.commit()
        # Immutable provenance: "why is this asset in this domain?" must
        # be answerable from this event alone, indefinitely.
        crud.log_audit_event(
            session, actor=actor.display, identity_fact_id=actor.fact(session).id,
            event_type="ASSET_CLASSIFIED", target_id=str(asset.id),
            details=json.dumps({
                "domain": rule["domain"],
                "policy_id": pol.id,
                "policy_name": pol.name,
                "policy_version": pol.version,
                "rule_index": rule_index,
                "rule_snapshot": rule,
                "matched": evidence,
                "document_id": asset.document_id,
                "ingestion_job_id": ingestion_job_id,
                "classified_at": datetime.datetime.utcnow().isoformat(),
            }))
        summary["classified"] += 1
        classified_ids.append(asset.id)

    engine_actor = identity.system_actor(session, "classification_engine")
    crud.log_audit_event(
        session, actor=engine_actor.display, identity_fact_id=engine_actor.fact(session).id,
        event_type="DOMAIN_CLASSIFICATION_COMPLETED",
        target_id=str(ingestion_job_id) if ingestion_job_id else None,
        details=json.dumps({
            **summary,
            "connector_id": connector_id,
            "classified_asset_ids": classified_ids,
            "policies": [{"id": p.id, "name": p.name, "version": p.version} for p in policies],
        }))
    return summary


# ------------------------------------------------------------- taxonomy ops

def _subtree_assets(session: Session, project_id: int, domain: str) -> list:
    """Assets in a domain and its subdomains (prefix semantics - the D27
    reason reorganizations nest by default)."""
    return session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id,
        (db.KnowledgeAsset.domain == domain)
        | db.KnowledgeAsset.domain.like(domain + "/%"),
    ).order_by(db.KnowledgeAsset.id).all()


def reorganize_taxonomy(session: Session, project_id: int, operations: list,
                        reason: str, actor) -> dict:
    """The explicit audited taxonomy operation (D27). Two kinds:

      {"kind": "rename", "from_domain": X, "to_domain": Y}
        - prefix rewrite over X's subtree (nesting/renaming; prefix
          scopes survive by construction).
      {"kind": "reclassify", "domain": X}
        - re-evaluate X's subtree against the CURRENT enabled policies;
          matched assets move to the policy's domain (this is how a
          split is done by policy change alone); unmatched assets keep
          their domain and are declared (D12).

    Writes ONLY the domain column - content, revisions, provenance, and
    history are untouched; this is taxonomy governance, never asset
    editing. ONE TAXONOMY_REORGANIZED event carries the reason, the
    operations, and the complete per-asset old->new mapping."""
    if not reason or not str(reason).strip():
        raise ValueError("a taxonomy reorganization requires a reason")
    if not isinstance(operations, list) or not operations:
        raise ValueError("operations must be a non-empty list")

    moves = []      # {"asset_id", "old", "new", "operation"}
    unmatched = []  # declared, never silent (D12)
    for i, op in enumerate(operations):
        kind = (op or {}).get("kind")
        if kind == "rename":
            from_domain = validate_domain_path(op.get("from_domain", ""))
            to_domain = validate_domain_path(op.get("to_domain", ""))
            for asset in _subtree_assets(session, project_id, from_domain):
                new_domain = to_domain + asset.domain[len(from_domain):]
                if new_domain != asset.domain:
                    moves.append({"asset_id": asset.id, "old": asset.domain,
                                  "new": new_domain, "operation": i})
                    asset.domain = new_domain
        elif kind == "reclassify":
            domain = validate_domain_path(op.get("domain", ""))
            policies = policies_for_scope(session, project_id)
            if not policies:
                raise ValueError(
                    "reclassify requires enabled classification policies - "
                    "the policies ARE the split decision")
            for asset in _subtree_assets(session, project_id, domain):
                context = _source_context(session, [asset.document_id]) \
                    if asset.document_id else {}
                source_uri, source_metadata = context.get(asset.document_id, (None, {}))
                pol, rule_index, rule, evidence = first_match(
                    policies, source_uri, source_metadata)
                if pol and rule["domain"] != asset.domain:
                    moves.append({"asset_id": asset.id, "old": asset.domain,
                                  "new": rule["domain"], "operation": i,
                                  "policy_id": pol.id, "policy_name": pol.name,
                                  "policy_version": pol.version,
                                  "rule_index": rule_index, "matched": evidence})
                    asset.domain = rule["domain"]
                elif not pol:
                    unmatched.append({"asset_id": asset.id, "domain": asset.domain,
                                      "operation": i})
        else:
            raise ValueError(f"operation {i}: kind must be 'rename' or 'reclassify'")

    session.commit()
    crud.log_audit_event(
        session, actor=actor.display, identity_fact_id=actor.fact(session).id,
        event_type="TAXONOMY_REORGANIZED", target_id=str(project_id),
        details=json.dumps({
            "reason": str(reason).strip(),
            "operations": operations,
            "moves": moves,
            "unmatched_declared": unmatched,
            "reorganized_at": datetime.datetime.utcnow().isoformat(),
        }))
    return {"moved": len(moves), "unmatched_declared": len(unmatched), "moves": moves}
