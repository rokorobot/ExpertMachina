"""The projection engine (v1.3.0 WS1, D28) - THE DECIDER.

Composes clearance-filtered, cursor-stamped projections of governed
facts and hands them to renderers, which choose only their shape on
disk. This module is the ONLY emitter of PROJECTION_* ledger events and
the only code allowed to name EM_PROJECTION_DIR - both enforced
structurally by test_projection_guard.py, as is everything else this
module must never do: no governed writes, no schema, no reading a
rendered artifact back. Renders regenerate wholesale; a render is
verifiable evidence of what was projected, never a source of what is
true.

Determinism ruling (contract ruling 9): same facts + same scope + same
clearance = byte-identical projection.json. rendered_at lives in the
manifest only, so the projection content hash detects real drift -
staleness is judged by recomposing and comparing hashes, never by
guessing from timestamps.
"""
import dataclasses
import datetime
import hashlib
import json
import os
import shutil

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import database as db
from app import crud
from app.projections import contract
from app.projections.renderers import graph as graph_renderer

ENGINE_VERSION = "projection-engine-v1"
EXCERPT_LIMIT = 240  # bounded excerpt, never full content (scoping ruling 3)
ALLOWED_STATUSES = ("CANDIDATE", "REVIEWED", "APPROVED", "ARCHIVED")
DEFAULT_STATUS_INCLUSION = ("APPROVED",)  # scoping ruling 4
ACCESS_RANK = {"PUBLIC": 0, "INTERNAL": 1, "RESTRICTED": 2, "EXECUTIVE": 3}

# Renderer registry: name -> callable(Projection) -> {filename: bytes}.
# The canonical projection.json + manifest.json are always written by
# the engine itself; a renderer only ADDS presentation files. Renderers
# receive a completed projection - they never see the session.
RENDERERS = {"projection": None,
             "graph": graph_renderer.render_files}


def _rank(level):
    return ACCESS_RANK.get((level or "INTERNAL").upper(), ACCESS_RANK["INTERNAL"])


def _in_domain(domain, prefix):
    if prefix is None:
        return True
    if domain is None:
        return False  # deny-by-default: unclassified is never in a scoped render (D27 posture)
    return domain == prefix or domain.startswith(prefix + "/")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _node_sort_key(node):
    kind, _sep, raw_id = node.id.partition(":")
    return (kind, int(raw_id))


def compose(session: Session, project_id: int, clearance: str = "INTERNAL",
            status_inclusion=DEFAULT_STATUS_INCLUSION,
            domain_prefix: str = None) -> contract.Projection:
    """Compose the projection: exactly the governed facts in scope, with
    every exclusion counted and declared (D12). Deterministic by
    construction - stable queries, stable ordering, no timestamps."""
    statuses = tuple(sorted({s.upper() for s in status_inclusion}))
    for status in statuses:
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"Unknown asset status '{status}'. "
                             f"Known: {sorted(ALLOWED_STATUSES)}")
    clearance = (clearance or "INTERNAL").upper()
    if clearance not in ACCESS_RANK:
        raise ValueError(f"Unknown clearance '{clearance}'. "
                         f"Known: {sorted(ACCESS_RANK)}")

    cursor = session.query(func.max(db.AuditEvent.id)).scalar() or 0

    all_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id).order_by(
        db.KnowledgeAsset.id).all()

    excluded = {"assets_status_out_of_scope": 0,
                "assets_above_clearance": 0,
                "assets_outside_domain_scope": 0,
                "relationship_edges_out_of_scope": 0}
    assets = []
    for asset in all_assets:
        if asset.status not in statuses:
            excluded["assets_status_out_of_scope"] += 1
        elif _rank(asset.access_level) > _rank(clearance):
            excluded["assets_above_clearance"] += 1
        elif not _in_domain(asset.domain, domain_prefix):
            excluded["assets_outside_domain_scope"] += 1
        else:
            assets.append(asset)
    asset_ids = {a.id for a in assets}

    nodes = []
    edges = []
    groups = {}

    for asset in assets:
        node_id = f"asset:{asset.id}"
        nodes.append(contract.ProjectionNode(
            id=node_id, kind="ASSET", label=asset.name, status=asset.status,
            domain=asset.domain,
            excerpt=(asset.content or "")[:EXCERPT_LIMIT],
            metadata={"type": asset.type, "access_level": asset.access_level}))
        if asset.domain:
            groups[asset.domain] = groups.get(asset.domain, []) + [node_id]

    # Documents: provenance anchors of the included assets.
    document_ids = sorted({a.document_id for a in assets if a.document_id})
    if document_ids:
        for document in session.query(db.Document).filter(
                db.Document.id.in_(document_ids)).order_by(db.Document.id):
            nodes.append(contract.ProjectionNode(
                id=f"document:{document.id}", kind="DOCUMENT",
                label=document.filename, status=document.status,
                metadata={"file_type": document.file_type}))
        for asset in assets:
            if asset.document_id:
                edges.append(contract.ProjectionEdge(
                    source_id=f"asset:{asset.id}",
                    target_id=f"document:{asset.document_id}",
                    relation="PROVENANCE"))

    # Expert models: membership over the included assets. Under a domain
    # scope, a model with no included member is out of scope.
    expert_ids = []
    for expert in session.query(db.ExpertModel).filter(
            db.ExpertModel.project_id == project_id).order_by(db.ExpertModel.id):
        try:
            member_ids = sorted(set(json.loads(expert.asset_ids_json or "[]")) & asset_ids)
        except (TypeError, ValueError):
            member_ids = []
        if domain_prefix is not None and not member_ids:
            continue
        expert_ids.append(expert.id)
        nodes.append(contract.ProjectionNode(
            id=f"expert:{expert.id}", kind="EXPERT_MODEL", label=expert.name,
            metadata={"asset_count": expert.asset_count}))
        for member_id in member_ids:
            edges.append(contract.ProjectionEdge(
                source_id=f"asset:{member_id}",
                target_id=f"expert:{expert.id}", relation="MEMBER_OF"))

    # The consumption chain: package -> selection -> binding -> principal.
    package_ids = []
    if expert_ids:
        for package in session.query(db.AgentPackage).filter(
                db.AgentPackage.expert_model_id.in_(expert_ids)).order_by(
                db.AgentPackage.id):
            package_ids.append(package.id)
            nodes.append(contract.ProjectionNode(
                id=f"package:{package.id}", kind="PACKAGE", label=package.name,
                metadata={"clearance_level": package.clearance_level,
                          "package_hash": package.package_hash,
                          "governance_version": package.governance_version}))
            edges.append(contract.ProjectionEdge(
                source_id=f"package:{package.id}",
                target_id=f"expert:{package.expert_model_id}",
                relation="COMPILED_FROM"))
    principal_ids = []
    if package_ids:
        for selection in session.query(db.PackageModelSelection).filter(
                db.PackageModelSelection.agent_package_id.in_(package_ids)
                ).order_by(db.PackageModelSelection.id):
            nodes.append(contract.ProjectionNode(
                id=f"selection:{selection.id}", kind="SELECTION",
                label=f"{selection.selected_provider}/{selection.selected_model_name}",
                metadata={"provider": selection.selected_provider,
                          "model": selection.selected_model_name,
                          "package_hash": selection.package_hash}))
            edges.append(contract.ProjectionEdge(
                source_id=f"selection:{selection.id}",
                target_id=f"package:{selection.agent_package_id}",
                relation="SELECTED"))
        for binding in session.query(db.ExpertAgentBinding).filter(
                db.ExpertAgentBinding.agent_package_id.in_(package_ids)
                ).order_by(db.ExpertAgentBinding.id):
            nodes.append(contract.ProjectionNode(
                id=f"binding:{binding.id}", kind="BINDING",
                label=f"binding #{binding.id}",
                metadata={"provider": binding.selected_provider,
                          "model": binding.selected_model_name,
                          "package_hash": binding.package_hash,
                          "clearance_at_issue": binding.principal_clearance_at_issue}))
            edges.append(contract.ProjectionEdge(
                source_id=f"binding:{binding.id}",
                target_id=f"package:{binding.agent_package_id}",
                relation="BOUND_TO"))
            edges.append(contract.ProjectionEdge(
                source_id=f"binding:{binding.id}",
                target_id=f"principal:{binding.agent_principal_id}",
                relation="BOUND_TO"))
            principal_ids.append(binding.agent_principal_id)
    if principal_ids:
        for principal in session.query(db.Principal).filter(
                db.Principal.id.in_(sorted(set(principal_ids)))).order_by(
                db.Principal.id):
            nodes.append(contract.ProjectionNode(
                id=f"principal:{principal.id}", kind="PRINCIPAL",
                label=principal.display_name,
                metadata={"kind": principal.kind,
                          "clearance": principal.clearance,
                          "active": bool(principal.active)}))

    # Governed relationships between INCLUDED assets; edges with an
    # excluded endpoint are dropped and the drop is declared (D12).
    for rel in session.query(db.AssetRelationship).filter(
            db.AssetRelationship.project_id == project_id).order_by(
            db.AssetRelationship.id):
        if rel.source_asset_id in asset_ids and rel.target_asset_id in asset_ids:
            edges.append(contract.ProjectionEdge(
                source_id=f"asset:{rel.source_asset_id}",
                target_id=f"asset:{rel.target_asset_id}",
                relation=rel.relationship_type,
                metadata={"classification": rel.classification,
                          "confidence": rel.confidence,
                          "review_status": rel.status,
                          "expert_model_id": rel.expert_model_id}))
        else:
            excluded["relationship_edges_out_of_scope"] += 1

    scope = {"domain_prefix": domain_prefix}
    return contract.Projection(
        project_id=project_id, clearance=clearance, status_inclusion=statuses,
        audit_cursor=cursor, engine_version=ENGINE_VERSION,
        nodes=tuple(sorted(nodes, key=_node_sort_key)),
        edges=tuple(sorted(edges, key=lambda e: (e.relation, e.source_id, e.target_id))),
        groups={k: sorted(v) for k, v in sorted(groups.items())},
        excluded=excluded, scope=scope)


def canonical_json(projection: contract.Projection) -> str:
    """The deterministic serialization whose sha256 is the projection's
    content identity: the FACTS projected, never the moment of
    projection. The audit cursor is a stamp - it lives in the manifest
    and the ledger event, not in the content; otherwise a render's own
    PROJECTION_RENDERED event would move the cursor and make every
    subsequent identical render look like drift."""
    payload = dataclasses.asdict(projection)
    payload.pop("audit_cursor")
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def projection_hash(projection: contract.Projection) -> str:
    return _sha256(canonical_json(projection).encode("utf-8"))


def _output_base() -> str:
    return os.environ.get("EM_PROJECTION_DIR") or os.path.join(
        os.getcwd(), "projections")


def render(session: Session, actor, project_id: int,
           renderer: str = "projection", clearance: str = "INTERNAL",
           status_inclusion=DEFAULT_STATUS_INCLUSION,
           domain_prefix: str = None) -> dict:
    """Compose, write, stamp, record. Returns a metadata-only summary -
    never file contents. The PROJECTION_RENDERED event alone answers
    'what was projected, for whom, at which ledger moment' indefinitely."""
    if renderer not in RENDERERS:
        raise ValueError(f"Unknown renderer '{renderer}'. "
                         f"Known: {sorted(RENDERERS)}")
    projection = compose(session, project_id, clearance=clearance,
                         status_inclusion=status_inclusion,
                         domain_prefix=domain_prefix)
    canonical = canonical_json(projection).encode("utf-8")

    relative_dir = os.path.join(f"project_{project_id}", renderer)
    out_dir = os.path.join(_output_base(), relative_dir)
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)  # renders regenerate wholesale (D28)
    os.makedirs(out_dir)

    outputs = {"projection.json": canonical}
    renderer_fn = RENDERERS[renderer]
    if renderer_fn is not None:
        for name, content in renderer_fn(projection).items():
            outputs[name] = content if isinstance(content, bytes) \
                else content.encode("utf-8")
    file_hashes = {}
    for name in sorted(outputs):
        with open(os.path.join(out_dir, name), "wb") as f:
            f.write(outputs[name])
        file_hashes[name] = _sha256(outputs[name])

    rendered_at = datetime.datetime.utcnow().isoformat()
    counts = {"nodes": len(projection.nodes), "edges": len(projection.edges),
              "groups": len(projection.groups)}
    manifest = contract.RenderManifest(
        renderer=renderer, engine_version=ENGINE_VERSION,
        rendered_at=rendered_at, audit_cursor=projection.audit_cursor,
        clearance=projection.clearance,
        status_inclusion=projection.status_inclusion,
        files=file_hashes, counts=counts)
    manifest_bytes = json.dumps(dataclasses.asdict(manifest), sort_keys=True,
                                separators=(",", ":")).encode("utf-8")
    with open(os.path.join(out_dir, "manifest.json"), "wb") as f:
        f.write(manifest_bytes)
    manifest_hash = _sha256(manifest_bytes)

    details = {
        "renderer": renderer,
        "engine_version": ENGINE_VERSION,
        "clearance": projection.clearance,
        "status_inclusion": list(projection.status_inclusion),
        "domain_prefix": domain_prefix,
        "audit_cursor": projection.audit_cursor,
        "rendered_at": rendered_at,
        "counts": counts,
        "excluded": projection.excluded,
        "projection_hash": _sha256(canonical),
        "manifest_hash": manifest_hash,
        "files": file_hashes,
        "output": relative_dir.replace(os.sep, "/"),
    }
    crud.log_audit_event(
        session, actor=actor.display,
        identity_fact_id=actor.fact(session).id,
        event_type="PROJECTION_RENDERED", target_id=str(project_id),
        details=json.dumps(details))
    return {"status": "RENDERED", **details}


def is_stale(session: Session, project_id: int, recorded: dict) -> bool:
    """Staleness is computed, detectable, never silent (D28): recompose
    with the recorded parameters and compare content hashes. Deterministic
    composition makes this exact - no cursor heuristics, no timestamp
    guessing."""
    current = compose(session, project_id,
                      clearance=recorded.get("clearance", "INTERNAL"),
                      status_inclusion=tuple(
                          recorded.get("status_inclusion")
                          or DEFAULT_STATUS_INCLUSION),
                      domain_prefix=recorded.get("domain_prefix"))
    return projection_hash(current) != recorded.get("projection_hash")


def render_history(session: Session, project_id: int) -> list:
    """The render history, projected from the ledger alone (D24: computed,
    never stored). The latest render per renderer carries a computed
    staleness verdict."""
    events = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "PROJECTION_RENDERED",
        db.AuditEvent.target_id == str(project_id)).order_by(
        db.AuditEvent.id.desc()).all()
    history = []
    seen_renderers = {}
    for event in events:
        try:
            recorded = json.loads(event.details or "{}")
        except ValueError:
            recorded = {}
        current = recorded.get("renderer") not in seen_renderers
        item = {"event_id": event.id,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "actor": event.actor,
                "current": current,
                "stale": is_stale(session, project_id, recorded) if current else None,
                **recorded}
        if current:
            seen_renderers[recorded.get("renderer")] = event.id
        history.append(item)
    return history
