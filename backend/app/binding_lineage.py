import json
import datetime

from sqlalchemy.orm import Session

from app import database as db
from app import consumption_inbox

# Binding Lineage Projection (v1.1.x WS3, docs/workbench-v1.1x.md).
#
# The differentiation sentence made computable: starting from one
# ExpertAgentBinding, walk BACKWARDS through the governed chain
#
#   binding -> package snapshot -> current package-family status
#           -> selected model snapshot -> selection evidence
#           -> supporting evaluation runs -> package assets
#           -> source documents
#
# and SIDEWAYS into identity
#
#   binding -> AGENT principal -> active credentials summary
#           -> relevant audit events
#
# composed SERVER-SIDE because the chain is a product claim, not a UI
# convenience (ruled at scoping). The rule, D12 applied to traversal:
# every expected hop either resolves or is explicitly declared missing -
# no silent gaps. Each section carries its own `missing` list; the
# response aggregates the count so "is anything unverifiable?" is one
# field.
#
# Warnings are NOT recomputed here with private logic: they are the
# consumption-inbox items affecting this binding and its package, so the
# explorer and the inbox can never disagree (the D2 discipline, reused).
#
# Pure projection (D24): no actor parameter, no writes, nothing cached.

LINEAGE_VERSION = "binding-lineage-v1"


def _iso(dt):
    return dt.isoformat() if dt else None


def build_lineage(session: Session, binding_id: int) -> dict:
    binding = session.query(db.ExpertAgentBinding).filter(
        db.ExpertAgentBinding.id == binding_id).first()
    if binding is None:
        raise LookupError(f"Binding {binding_id} not found")

    missing_total = []

    def declare(section_missing, text):
        section_missing.append(text)
        missing_total.append(text)

    # ---- the binding itself: an append-only snapshot, reported verbatim
    binding_view = {
        "id": binding.id,
        "agent_package_id": binding.agent_package_id,
        "package_version": binding.package_version,
        "package_hash": binding.package_hash,
        "selected_provider": binding.selected_provider,
        "selected_model_name": binding.selected_model_name,
        "agent_principal_id": binding.agent_principal_id,
        "principal_clearance_at_issue": binding.principal_clearance_at_issue,
        "created_at": _iso(binding.created_at),
    }

    # ---- issued-by-whom: the immutable identity fact (D20 - rename,
    # demotion, and deactivation of the issuer never change this answer)
    issued_by = {"missing": []}
    fact = session.query(db.IdentityFact).filter(
        db.IdentityFact.id == binding.identity_fact_id).first()
    if fact is None:
        declare(issued_by["missing"],
                f"identity fact {binding.identity_fact_id} not found - the issuance "
                f"evidence cannot be resolved")
    else:
        issued_by.update({
            "identity_fact_id": fact.id,
            "principal_name": fact.principal_name,
            "display_name": fact.display_name,
            "principal_kind": fact.principal_kind,
            "role_at_issue": fact.role_snapshot,
            "authentication_method": fact.authentication_method,
            "issued_at": _iso(fact.created_at),
        })

    # ---- backwards hop 1: the bound package artifact (snapshot row)
    package = {"missing": []}
    pkg = session.query(db.AgentPackage).filter(
        db.AgentPackage.id == binding.agent_package_id).first()
    if pkg is None:
        declare(package["missing"],
                f"Agent Package {binding.agent_package_id} not found - the bound "
                f"artifact row cannot be resolved")
    else:
        manifest = pkg.manifest or {}
        package.update({
            "package_id": pkg.id,
            "project_id": pkg.project_id,
            "name": pkg.name,
            "version": pkg.governance_version,
            "hash": pkg.package_hash,
            "clearance_level": pkg.clearance_level,
            "compiled_at": manifest.get("compiled_at"),
            "trust_score_at_compile": manifest.get("trust_score"),
            "asset_count_at_compile": manifest.get("asset_count"),
            "expert_model": manifest.get("expert_model"),
        })
        if binding.package_hash != pkg.package_hash:
            declare(package["missing"],
                    "binding's package hash does not match the bound artifact row - "
                    "the snapshot chain is unverifiable")

    # ---- backwards hop 2: current package-family status (drift anchor)
    family_status = {"missing": []}
    if pkg is not None:
        family_rows = session.query(db.AgentPackage).filter(
            db.AgentPackage.project_id == pkg.project_id,
            db.AgentPackage.expert_model_id == pkg.expert_model_id,
            db.AgentPackage.name == pkg.name).all()
        current = max(family_rows, key=lambda p: p.id)
        family_status.update({
            "current_package_id": current.id,
            "current_version": current.governance_version,
            "current_hash": current.package_hash,
            "artifact_count": len(family_rows),
            "superseded": bool(current.id != pkg.id
                               and current.package_hash != pkg.package_hash),
        })
    else:
        declare(family_status["missing"],
                "package family cannot be determined without the bound artifact row")

    # ---- backwards hop 3: selected model snapshot vs the current selection
    model = {
        "provider": binding.selected_provider,
        "model": binding.selected_model_name,
        "current_selection": None,
        "matches_current_selection": None,
        "missing": [],
    }
    selection_now = session.query(db.PackageModelSelection).filter(
        db.PackageModelSelection.agent_package_id == binding.agent_package_id).first()
    if selection_now is None:
        declare(model["missing"],
                "the package has no current model selection - the binding's model "
                "snapshot has nothing current to compare against")
    else:
        model["current_selection"] = {
            "provider": selection_now.selected_provider,
            "model": selection_now.selected_model_name,
            "selected_at": _iso(selection_now.selected_at),
            "rationale": selection_now.rationale,
        }
        model["matches_current_selection"] = bool(
            (selection_now.selected_provider, selection_now.selected_model_name)
            == (binding.selected_provider, binding.selected_model_name))

    # ---- backwards hop 4: the selection evidence FROZEN AT ISSUE
    evidence = {"missing": []}
    frozen = binding.selection_evidence or {}
    if not frozen:
        declare(evidence["missing"], "the binding carries no frozen selection evidence")
    else:
        evidence.update({
            "selection_id": frozen.get("selection_id"),
            "rationale": frozen.get("rationale"),
            "selected_at": frozen.get("selected_at"),
            "supporting_evaluation_run_ids": frozen.get("supporting_evaluation_run_ids", []),
        })
        selector = session.query(db.Principal).filter(
            db.Principal.id == frozen.get("selected_by_principal_id")).first()
        if selector is None:
            declare(evidence["missing"],
                    f"selecting principal {frozen.get('selected_by_principal_id')} "
                    f"not found in the registry")
        else:
            evidence["selected_by"] = selector.name

    # ---- backwards hop 5: the supporting evaluation runs, one by one
    runs = []
    runs_missing = []
    for run_id in (frozen.get("supporting_evaluation_run_ids") or []):
        run = session.query(db.EvaluationRun).filter(
            db.EvaluationRun.id == run_id).first()
        if run is None:
            declare(runs_missing, f"supporting evaluation run {run_id} not found")
            continue
        runs.append({
            "run_id": run.id,
            "run_type": run.run_type,
            "status": run.status,
            "consumer_model_provider": run.consumer_model_provider,
            "consumer_model_name": run.consumer_model_name,
            "package_hash": run.package_hash,
            "pass_rate": run.pass_rate,
            "average_coverage_score": run.average_coverage_score,
            "completed_at": _iso(run.completed_at),
            "evaluates_bound_artifact": bool(run.package_hash == binding.package_hash),
        })

    # ---- backwards hops 6-7: package assets -> source documents. The
    # compile-time references are the snapshot; live rows may have moved on,
    # and each unresolvable reference is declared.
    assets = []
    assets_missing = []
    documents = {}
    documents_missing = []
    refs = []
    if pkg is not None:
        try:
            refs = json.loads(pkg.asset_references or "[]")
        except Exception:
            declare(assets_missing, "package asset references are unreadable")
    for ref in refs:
        asset_id = ref.get("asset_id")
        live = session.query(db.KnowledgeAsset).filter(
            db.KnowledgeAsset.id == asset_id).first()
        entry = {
            "asset_id": asset_id,
            "name": ref.get("name"),
            "type": ref.get("type"),
            "source_document": ref.get("source_document"),
            "source_page": ref.get("source_page"),
            "source_hash": ref.get("source_hash"),
            "live_status": live.status if live else None,
        }
        if live is None:
            declare(assets_missing,
                    f"packaged asset {asset_id} ('{ref.get('name')}') no longer exists "
                    f"in the knowledge base - the package snapshot remains the evidence")
        else:
            doc = session.query(db.Document).filter(
                db.Document.id == live.document_id).first()
            if doc is None:
                declare(documents_missing,
                        f"source document for asset {asset_id} ('{ref.get('name')}') "
                        f"not found")
            else:
                documents[doc.id] = {
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "status": doc.status,
                    "content_hash": doc.content_hash,
                    "created_at": _iso(doc.created_at),
                }
        assets.append(entry)

    # ---- sideways hop 1: the AGENT principal as it stands NOW (the
    # binding's clearance snapshot above is how it stood at issue)
    principal_view = {"missing": []}
    principal = session.query(db.Principal).filter(
        db.Principal.id == binding.agent_principal_id).first()
    if principal is None:
        declare(principal_view["missing"],
                f"AGENT principal {binding.agent_principal_id} not found in the "
                f"registry - the binding is unverifiable sideways")
    else:
        principal_view.update({
            "principal_id": principal.id,
            "name": principal.name,
            "display_name": principal.display_name,
            "kind": principal.kind,
            "role": principal.role,
            "clearance_now": principal.clearance,
            "active": principal.active,
            "created_at": _iso(principal.created_at),
        })

    # ---- sideways hop 2: credentials SUMMARY (counts and kind facts only -
    # never fingerprints, never secrets)
    now = datetime.datetime.utcnow()
    creds = session.query(db.Credential).filter(
        db.Credential.principal_id == binding.agent_principal_id).all()
    active = [c for c in creds if c.revoked_at is None
              and (c.expires_at is None or c.expires_at > now)]
    credentials = {
        "active_count": len(active),
        "revoked_count": sum(1 for c in creds if c.revoked_at is not None),
        "kinds": sorted({c.kind for c in active}),
        "last_used_at": _iso(max((c.last_used_at for c in active if c.last_used_at),
                                 default=None)),
        "missing": [],
    }
    if principal is not None and principal.active and not active:
        declare(credentials["missing"],
                "the bound principal holds no active credential - the serving agent "
                "currently cannot authenticate")

    # ---- sideways hop 3: the relevant audit events (issuance, the
    # selection decisions on this package, the package compile)
    audit_events = []
    if pkg is not None:
        wanted = [("EXPERT_AGENT_BINDING_CREATED", str(binding.id)),
                  ("PACKAGE_MODEL_SELECTED", str(pkg.id)),
                  ("AGENT_PACKAGE_CREATED", str(pkg.id))]
    else:
        wanted = [("EXPERT_AGENT_BINDING_CREATED", str(binding.id))]
    for event_type, target in wanted:
        rows = session.query(db.AuditEvent).filter(
            db.AuditEvent.event_type == event_type,
            db.AuditEvent.target_id == target,
        ).order_by(db.AuditEvent.timestamp.desc()).all()
        for ev in rows:
            audit_events.append({
                "id": ev.id,
                "timestamp": _iso(ev.timestamp),
                "actor": ev.actor,
                "event_type": ev.event_type,
                "identity_fact_id": ev.identity_fact_id,
            })
    audit = {"events": audit_events, "missing": []}
    if not any(e["event_type"] == "EXPERT_AGENT_BINDING_CREATED" for e in audit_events):
        declare(audit["missing"],
                "no EXPERT_AGENT_BINDING_CREATED audit event found for this binding")

    # ---- warnings: the consumption-inbox items affecting this binding and
    # its package - THE shared severity function, reused, never duplicated.
    warnings = []
    if pkg is not None:
        inbox = consumption_inbox.build_inbox(session, pkg.project_id)
        warnings = [i for i in inbox["items"]
                    if i["binding_id"] == binding.id
                    or (i["package_id"] == pkg.id and i["binding_id"] is None)]

    return {
        "lineage_version": LINEAGE_VERSION,
        "generated_at": now.isoformat(),
        "binding": binding_view,
        "issued_by": issued_by,
        "package": package,
        "family_status": family_status,
        "model": model,
        "selection_evidence": evidence,
        "evaluation_runs": {"runs": runs, "missing": runs_missing},
        "assets": {"assets": assets, "missing": assets_missing},
        "source_documents": {"documents": sorted(documents.values(),
                                                 key=lambda d: d["document_id"]),
                             "missing": documents_missing},
        "principal": principal_view,
        "credentials": credentials,
        "audit": audit,
        "warnings": warnings,
        "declared_missing_total": len(missing_total),
    }
