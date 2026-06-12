import json
import datetime

from sqlalchemy.orm import Session

from app import database as db
from app.query_engine import ACCESS_RANK

# Computed Consumption Inbox (v1.1.x WS2, docs/workbench-v1.1x.md).
#
# The v0.9.1 Governance Inbox pattern applied to consumption: a computed
# operational index over existing governed facts - NOT a new state machine.
# No new tables, no is_stale column, no writes, no dismiss/mark-resolved:
# every item is derived live from AgentPackage, PackageModelSelection,
# EvaluationRun, ExpertAgentBinding, Principal, and Credential, and
# deep-links into the workbench where the actual governed decision happens.
# An item disappears the way it appeared: the underlying facts change.
#
# D2 discipline: ONE shared severity function (severity_of) assigns
# severity from the condition code, so no two surfaces can ever disagree
# about what HIGH means here:
#
#   HIGH    a binding is currently unsafe or unverifiable
#   MEDIUM  a selection may need review
#   LOW     informational consumption hygiene
#
# D12 discipline: every expected hop either resolves or is explicitly
# declared missing (the item's `missing` list) - never silently dropped.
#
# "Current artifact" semantics: AgentPackage rows are append-only (every
# compile creates a new row - D9's tamper-evidence depends on that), so a
# row's own hash can never change. Drift is therefore a FAMILY fact: the
# packages sharing (project, expert model, name) are versions of one
# package, the newest row is the family's current artifact, and bindings
# or selections attached to an older artifact have drifted when the
# current artifact's hash differs.

INBOX_VERSION = "consumption-inbox-v1"

_SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

# The ratified taxonomy (gate text, WS1 acceptance). The condition code is
# the ONLY input to severity - items never carry hand-assigned severities.
SEVERITY_BY_CONDITION = {
    "BINDING_PACKAGE_HASH_DRIFT": "HIGH",
    "BINDING_PRINCIPAL_INACTIVE": "HIGH",
    "BINDING_CLEARANCE_BELOW_PACKAGE": "HIGH",
    "SELECTION_PACKAGE_HASH_DRIFT": "MEDIUM",
    "SELECTION_PREDATES_NEWER_RUNS": "MEDIUM",
    "SELECTED_MODEL_ABSENT_FROM_LATEST_RUNS": "MEDIUM",
    "EVALUATED_BUT_NO_SELECTION": "LOW",
    "SELECTED_BUT_NO_BINDING": "LOW",
    "BOUND_PRINCIPAL_NO_ACTIVE_CREDENTIAL": "LOW",
}


def severity_of(condition: str) -> str:
    """THE severity function (D2): condition code in, severity out.
    Unknown conditions are a programming error, not a quiet LOW."""
    return SEVERITY_BY_CONDITION[condition]


def _iso(dt):
    return dt.isoformat() if dt else None


def _rank(level: str) -> int:
    return ACCESS_RANK.get((level or "INTERNAL").upper(), ACCESS_RANK["INTERNAL"])


def _item(condition, title, reason, pkg, deep_link, *, binding_id=None,
          selection_id=None, principal_id=None, principal_name=None,
          missing=None, source_id=None):
    return {
        "id": f"{condition}-{source_id if source_id is not None else pkg.id}",
        "condition": condition,
        "severity": severity_of(condition),
        "title": title,
        "reason": reason,
        "project_id": pkg.project_id,
        "package_id": pkg.id,
        "package_name": pkg.name,
        "package_version": pkg.governance_version,
        "binding_id": binding_id,
        "selection_id": selection_id,
        "principal_id": principal_id,
        "principal_name": principal_name,
        # Declared gaps (D12): hops that could not be resolved, named.
        "missing": missing or [],
        "deep_link": deep_link,
    }


def _short(h):
    return f"{h[:12]}…" if h else "(none)"


def _binding_items(session, pkg, current_pkg, principals_by_id,
                   active_cred_principal_ids, now):
    """HIGH conditions are per binding: bindings are append-only snapshots
    (D22/D23 - no lifecycle), so every binding for a package is potentially
    serving and every one is checked. LOW credential hygiene rides here too."""
    items = []
    bindings = session.query(db.ExpertAgentBinding).filter(
        db.ExpertAgentBinding.agent_package_id == pkg.id).all()

    for b in bindings:
        # The Binding Explorer is WS3; until it exists the deep link lands on
        # the package's workbench carrying the binding id for WS3 to claim.
        link = f"/?tab=consumption&package={pkg.id}&binding={b.id}"
        principal = principals_by_id.get(b.agent_principal_id)
        missing = []
        if principal is None:
            # A binding whose principal row cannot be resolved is not
            # skippable noise - it is an unverifiable binding, declared.
            missing.append(f"AGENT principal {b.agent_principal_id} not found in the registry")

        if current_pkg.package_hash and b.package_hash != current_pkg.package_hash:
            items.append(_item(
                "BINDING_PACKAGE_HASH_DRIFT",
                f"Binding {b.id}: package artifact changed under it",
                (f"Bound to artifact {_short(b.package_hash)} but the family's current "
                 f"artifact is {_short(current_pkg.package_hash)} "
                 f"(v{current_pkg.governance_version}). The agent is serving from premises "
                 f"that no longer match the package. Re-evaluate, re-select, and re-bind."),
                pkg, link, binding_id=b.id, principal_id=b.agent_principal_id,
                principal_name=principal.name if principal else None,
                missing=missing, source_id=b.id))

        if principal is None or not principal.active:
            items.append(_item(
                "BINDING_PRINCIPAL_INACTIVE",
                f"Binding {b.id}: AGENT principal "
                f"{'missing' if principal is None else 'deactivated'}",
                ("The bound AGENT principal "
                 + (f"({principal.name}) has been deactivated"
                    if principal is not None else "cannot be resolved")
                 + ". The binding remains historical evidence; access is withdrawn where "
                   "access lives - identity governance (D23 posture)."),
                pkg, link, binding_id=b.id, principal_id=b.agent_principal_id,
                principal_name=principal.name if principal else None,
                missing=missing, source_id=b.id))
        else:
            # Clearance and credential checks only mean something against a
            # resolvable, active principal.
            if _rank(principal.clearance) < _rank(pkg.clearance_level):
                items.append(_item(
                    "BINDING_CLEARANCE_BELOW_PACKAGE",
                    f"Binding {b.id}: clearance now below package clearance",
                    (f"'{principal.name}' now holds {principal.clearance or 'INTERNAL'} but the "
                     f"package is compiled for {pkg.clearance_level or 'INTERNAL'} (was "
                     f"{b.principal_clearance_at_issue} at issue). The principal could no "
                     f"longer receive this binding today."),
                    pkg, link, binding_id=b.id, principal_id=principal.id,
                    principal_name=principal.name, source_id=b.id))
            if principal.id not in active_cred_principal_ids:
                items.append(_item(
                    "BOUND_PRINCIPAL_NO_ACTIVE_CREDENTIAL",
                    f"Binding {b.id}: bound agent has no active credential",
                    (f"'{principal.name}' is active but holds no unrevoked, unexpired "
                     f"credential - the binding is issued to an agent that currently "
                     f"cannot authenticate. Issue a token in Users & Tokens."),
                    pkg, link, binding_id=b.id, principal_id=principal.id,
                    principal_name=principal.name, source_id=b.id))
    return items, len(bindings)


def _completed_runs_for_hash(session, package_hash):
    if not package_hash:
        return []
    return session.query(db.EvaluationRun).filter(
        db.EvaluationRun.run_type == "PACKAGE",
        db.EvaluationRun.package_hash == package_hash,
        db.EvaluationRun.status == "COMPLETED",
    ).all()


def _selection_items(session, pkg, current_pkg, now):
    """MEDIUM conditions are per selection; the LOW hygiene pair covers the
    packages around it (evaluated-but-unselected, selected-but-unbound)."""
    items = []
    selection = session.query(db.PackageModelSelection).filter(
        db.PackageModelSelection.agent_package_id == pkg.id).first()

    own_runs = _completed_runs_for_hash(session, pkg.package_hash)
    link = f"/?tab=consumption&package={pkg.id}"

    if selection is None:
        if own_runs:
            items.append(_item(
                "EVALUATED_BUT_NO_SELECTION",
                "Evaluated but no model selected",
                (f"{len(own_runs)} completed PACKAGE run"
                 f"{'s exist' if len(own_runs) != 1 else ' exists'} for this artifact "
                 f"but no governed selection has been recorded. The evidence is waiting "
                 f"for a decision."),
                pkg, link))
        return items, selection

    drifted = bool(current_pkg.package_hash
                   and selection.package_hash != current_pkg.package_hash)
    if drifted:
        items.append(_item(
            "SELECTION_PACKAGE_HASH_DRIFT",
            "Selection was made for a previous artifact",
            (f"The selection ({selection.selected_provider}/"
             f"{selection.selected_model_name}) was recorded for artifact "
             f"{_short(selection.package_hash)}; the family's current artifact is "
             f"{_short(current_pkg.package_hash)} (v{current_pkg.governance_version}). "
             f"Re-evaluate on the current artifact and record a new selection."),
            pkg, link, selection_id=selection.id))

    # New evidence on the SELECTION'S OWN artifact after the decision: the
    # decision may still stand, but it has not seen these runs.
    newer = [r for r in own_runs
             if r.completed_at and selection.selected_at and r.completed_at > selection.selected_at]
    if newer:
        items.append(_item(
            "SELECTION_PREDATES_NEWER_RUNS",
            "Newer evaluation evidence exists after the selection",
            (f"{len(newer)} successful PACKAGE run{'s' if len(newer) != 1 else ''} completed "
             f"after the selection was recorded. The decision may still stand - but it has "
             f"not seen this evidence."),
            pkg, link, selection_id=selection.id))

    # The latest successful evaluations are the current artifact's COMPLETED
    # runs. The condition fires only when that set EXISTS and the selected
    # model is not in it - an empty set is absence of evidence, not a
    # fabricated mismatch (D12); pure drift is already its own item above.
    current_runs = (own_runs if not drifted
                    else _completed_runs_for_hash(session, current_pkg.package_hash))
    if current_runs and not any(
            (r.consumer_model_provider, r.consumer_model_name)
            == (selection.selected_provider, selection.selected_model_name)
            for r in current_runs):
        items.append(_item(
            "SELECTED_MODEL_ABSENT_FROM_LATEST_RUNS",
            "Selected model absent from the latest successful evaluations",
            (f"{selection.selected_provider}/{selection.selected_model_name} is selected, "
             f"but the latest successful PACKAGE evaluations "
             f"({len(current_runs)} run{'s' if len(current_runs) != 1 else ''} on the "
             f"current artifact) do not evaluate it. The selection rests on evidence the "
             f"current artifact does not have."),
            pkg, link, selection_id=selection.id))

    return items, selection


def build_inbox(session: Session, project_id: int = None) -> dict:
    """Compute the consumption inbox across packages (optionally scoped to a
    project). Pure read: this function takes no actor and writes nothing."""
    now = datetime.datetime.utcnow()

    pkg_query = session.query(db.AgentPackage)
    if project_id is not None:
        pkg_query = pkg_query.filter(db.AgentPackage.project_id == project_id)
    packages = pkg_query.all()

    principals_by_id = {p.id: p for p in session.query(db.Principal).all()}
    active_cred_principal_ids = {
        c.principal_id for c in session.query(db.Credential).filter(
            db.Credential.revoked_at.is_(None)).all()
        if c.expires_at is None or c.expires_at > now
    }

    # Family grouping: append-only artifact rows sharing (project, expert
    # model, name) are versions of one package; the newest row is the
    # family's current artifact - the anchor every drift check compares to.
    current_by_family = {}
    for pkg in packages:
        family = (pkg.project_id, pkg.expert_model_id, pkg.name)
        cur = current_by_family.get(family)
        if cur is None or pkg.id > cur.id:
            current_by_family[family] = pkg

    items = []
    for pkg in packages:
        current_pkg = current_by_family[(pkg.project_id, pkg.expert_model_id, pkg.name)]
        binding_items, binding_count = _binding_items(
            session, pkg, current_pkg, principals_by_id, active_cred_principal_ids, now)
        selection_items, selection = _selection_items(session, pkg, current_pkg, now)
        items += binding_items + selection_items

        if selection is not None and binding_count == 0:
            items.append(_item(
                "SELECTED_BUT_NO_BINDING",
                "Selected but never bound to an agent",
                (f"{selection.selected_provider}/{selection.selected_model_name} is selected "
                 f"for this package but no agent binding has been issued - the governed "
                 f"decision is not serving anyone yet."),
                pkg, f"/?tab=consumption&package={pkg.id}", selection_id=selection.id))

    # Severity first (the shared rank), stable within a tier by package then
    # condition so recomputation from the same facts yields the same order.
    items.sort(key=lambda i: (_SEVERITY_RANK[i["severity"]], i["package_id"], i["condition"]))

    summary = {
        "high": sum(1 for i in items if i["severity"] == "HIGH"),
        "medium": sum(1 for i in items if i["severity"] == "MEDIUM"),
        "low": sum(1 for i in items if i["severity"] == "LOW"),
        "total_packages": len(packages),
        "items_with_declared_missing_hops": sum(1 for i in items if i["missing"]),
    }

    return {
        "inbox_version": INBOX_VERSION,
        "project_id": project_id,
        "generated_at": now.isoformat(),
        "summary": summary,
        "items": items,
    }
