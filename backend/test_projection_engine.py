import hashlib
import json
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ["EM_SECRET_KEY"] = "projection-engine-suite-master-key"
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_projeng_out_")

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import custody
from app import governance_inbox
from app.projections import contract
from app.projections import engine as projection_engine
from app.main import render_projection, list_projections
import test_support

# Projection Engine suite (v1.3.0 WS1, D28,
# docs/projection-engine-v1.3.md).
#
# The engine proof: a projection contains exactly the governed facts in
# scope; every exclusion is counted and declared (D12); clearance
# filtering happens before rendering (D9); the same inputs produce
# byte-identical projection.json (rendered_at lives in the manifest
# only); staleness is computed by recompose-and-compare, surfaces as a
# LOW inbox item, and leaves when the render is regenerated; and the
# PROJECTION_RENDERED event alone answers "what was projected, for
# whom, at which ledger moment" - indefinitely.
#
# The D25 custody discipline carries over: render files are a new
# export surface, so the sentinel sweep covers every written byte.

SENTINEL = "SENTINEL-projection-secret-7f3a9c"
TREASURY_MARKER = "TREASURY-SECRET-MARKER-2f8e"
LONG_TAIL = (" padding sentence far beyond the excerpt limit." * 20
             + " UNIQUE-TAIL-MARKER-93c1")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def out_path(project_id, renderer, name):
    return os.path.join(os.environ["EM_PROJECTION_DIR"],
                        f"project_{project_id}", renderer, name)


def read_output(project_id, renderer, name) -> bytes:
    with open(out_path(project_id, renderer, name), "rb") as f:
        return f.read()


def node_ids(projection):
    return {n.id for n in projection.nodes}


def edge_set(projection):
    return {(e.relation, e.source_id, e.target_id) for e in projection.edges}


def seed(session, officer):
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Projection Proof", description="D28 WS1 gate",
        customer_id=customer.id), actor=officer)

    doc1 = db.Document(project_id=project.id, filename="finance.txt",
                       file_type="txt", status="PARSED")
    doc2 = db.Document(project_id=project.id, filename="general.txt",
                       file_type="txt", status="PARSED")
    session.add_all([doc1, doc2])
    session.commit()

    a1 = db.KnowledgeAsset(
        project_id=project.id, type="SYSTEM", name="Ledger Reconciliation",
        content="The accounting platform reconciles ledgers nightly."
                + LONG_TAIL,
        status="APPROVED", access_level="INTERNAL",
        domain="finances/accounting", document_id=doc1.id)
    a2 = db.KnowledgeAsset(
        project_id=project.id, type="POLICY", name="Treasury Strategy",
        content=f"Executive treasury strategy {TREASURY_MARKER} details.",
        status="APPROVED", access_level="EXECUTIVE",
        domain="finances/treasury", document_id=doc1.id)
    a3 = db.KnowledgeAsset(
        project_id=project.id, type="PROCEDURE", name="Draft Intranet Note",
        content="A draft procedure awaiting review.",
        status="CANDIDATE", access_level="INTERNAL", document_id=doc2.id)
    a4 = db.KnowledgeAsset(
        project_id=project.id, type="WORKFLOW", name="HR Onboarding",
        content="New joiners complete onboarding within two weeks.",
        status="APPROVED", access_level="PUBLIC", domain="hr",
        document_id=doc2.id)
    session.add_all([a1, a2, a3, a4])
    session.commit()

    session.add_all([
        db.AssetRelationship(project_id=project.id, expert_model_id=None,
                             source_asset_id=a1.id, target_asset_id=a2.id,
                             relationship_type="CONFLICTS_WITH",
                             classification="SCOPE_CONFLICT",
                             confidence=0.97, status="DETECTED"),
        db.AssetRelationship(project_id=project.id, expert_model_id=None,
                             source_asset_id=a1.id, target_asset_id=a4.id,
                             relationship_type="SUPPORTS",
                             confidence=0.91, status="DETECTED"),
    ])
    expert = db.ExpertModel(project_id=project.id, name="Finance Expert",
                            asset_count=2,
                            asset_ids_json=json.dumps([a1.id, a4.id]))
    session.add(expert)
    session.commit()

    package = db.AgentPackage(project_id=project.id, name="finance-pack",
                              expert_model_id=expert.id,
                              clearance_level="INTERNAL",
                              package_hash="hash-p1")
    session.add(package)
    session.commit()
    agent = db.Principal(name="graph-agent", display_name="Graph Agent",
                         kind="AGENT", role="AGENT_CONSUMER",
                         clearance="INTERNAL", active=True)
    session.add(agent)
    session.commit()
    session.add_all([
        db.PackageModelSelection(
            agent_package_id=package.id, package_version="1",
            package_hash="hash-p1", selected_provider="OPENAI",
            selected_model_name="gpt-4o-mini",
            supporting_evaluation_run_ids_json="[]",
            rationale="gate seed",
            selected_by_principal_id=officer.principal.id),
        db.ExpertAgentBinding(
            agent_package_id=package.id, package_version="1",
            package_hash="hash-p1", selected_provider="OPENAI",
            selected_model_name="gpt-4o-mini", agent_principal_id=agent.id,
            principal_clearance_at_issue="INTERNAL",
            selection_evidence_json="{}",
            identity_fact_id=officer.fact(session).id),
    ])
    session.commit()
    return project, {"doc1": doc1, "doc2": doc2, "a1": a1, "a2": a2,
                     "a3": a3, "a4": a4, "expert": expert,
                     "package": package, "agent": agent}


def part_1_engine_proof(session, project, rows):
    print("\n--- Part 1: exactly the governed facts in scope ---")
    projection = projection_engine.compose(
        session, project.id, clearance="EXECUTIVE")
    expected_nodes = {
        f"asset:{rows['a1'].id}", f"asset:{rows['a2'].id}",
        f"asset:{rows['a4'].id}",
        f"document:{rows['doc1'].id}", f"document:{rows['doc2'].id}",
        f"expert:{rows['expert'].id}", f"package:{rows['package'].id}",
        "selection:1", "binding:1", f"principal:{rows['agent'].id}",
    }
    assert node_ids(projection) == expected_nodes, node_ids(projection)
    edges = edge_set(projection)
    assert (f"asset:{rows['a1'].id}", f"document:{rows['doc1'].id}") in {
        (s, t) for r, s, t in edges if r == "PROVENANCE"}
    for relation, count in (("PROVENANCE", 3), ("MEMBER_OF", 2),
                            ("COMPILED_FROM", 1), ("SELECTED", 1),
                            ("BOUND_TO", 2), ("CONFLICTS_WITH", 1),
                            ("SUPPORTS", 1)):
        actual = len([e for e in edges if e[0] == relation])
        assert actual == count, f"{relation}: {actual} != {count}"
    assert set(projection.groups) == {"finances/accounting",
                                      "finances/treasury", "hr"}
    # The candidate is out of scope BY DECLARED PARAMETER, and declared.
    assert projection.excluded["assets_status_out_of_scope"] == 1
    assert projection.status_inclusion == ("APPROVED",)
    # Bounded excerpt, never full content (scoping ruling 3).
    a1_node = [n for n in projection.nodes
               if n.id == f"asset:{rows['a1'].id}"][0]
    assert len(a1_node.excerpt) == projection_engine.EXCERPT_LIMIT
    assert "UNIQUE-TAIL-MARKER-93c1" not in \
        projection_engine.canonical_json(projection)
    # The conflict edge carries its governed evidence.
    conflict = [e for e in projection.edges
                if e.relation == "CONFLICTS_WITH"][0]
    assert conflict.metadata["classification"] == "SCOPE_CONFLICT"
    assert conflict.metadata["confidence"] == 0.97
    print(f"Part 1 passed: {len(projection.nodes)} nodes / "
          f"{len(projection.edges)} edges / {len(projection.groups)} domain "
          f"groups - the exact inventory, bounded excerpts, evidence on edges.")


def part_2_clearance(session, project, rows, officer):
    print("\n--- Part 2: clearance-filtered before rendering (D9) ---")
    projection = projection_engine.compose(
        session, project.id, clearance="INTERNAL")
    assert f"asset:{rows['a2'].id}" not in node_ids(projection)
    assert projection.excluded["assets_above_clearance"] == 1
    # The conflict edge lost an endpoint - dropped AND declared (D12).
    assert not [e for e in projection.edges if e.relation == "CONFLICTS_WITH"]
    assert projection.excluded["relationship_edges_out_of_scope"] == 1
    # And on the rendered FILES: the excluded content appears nowhere.
    projection_engine.render(session, officer, project.id,
                             renderer="projection", clearance="INTERNAL")
    for name in ("projection.json", "manifest.json"):
        data = read_output(project.id, "projection", name)
        assert TREASURY_MARKER.encode() not in data, \
            f"EXECUTIVE content leaked into {name} of an INTERNAL render"
    print("Part 2 passed: EXECUTIVE asset absent from the INTERNAL "
          "projection and its files; both exclusions declared.")


def part_3_domain_scope(session, project, rows):
    print("\n--- Part 3: domain-prefix scope (D27 prefixes consumed) ---")
    projection = projection_engine.compose(
        session, project.id, clearance="EXECUTIVE",
        domain_prefix="finances")
    included = node_ids(projection)
    assert f"asset:{rows['a1'].id}" in included
    assert f"asset:{rows['a2'].id}" in included  # prefix resolves children
    assert f"asset:{rows['a4'].id}" not in included
    assert projection.excluded["assets_outside_domain_scope"] == 1
    assert not [e for e in projection.edges if e.relation == "SUPPORTS"]
    assert projection.excluded["relationship_edges_out_of_scope"] == 1
    assert projection.scope == {"domain_prefix": "finances"}
    print("Part 3 passed: prefix query resolves both finance children, "
          "out-of-domain asset excluded and declared.")


def part_4_determinism(session, project, officer):
    print("\n--- Part 4: determinism (contract ruling 9) ---")
    first = projection_engine.render(session, officer, project.id,
                                     renderer="projection")
    first_bytes = read_output(project.id, "projection", "projection.json")
    first_manifest = json.loads(
        read_output(project.id, "projection", "manifest.json"))
    second = projection_engine.render(session, officer, project.id,
                                      renderer="projection")
    second_bytes = read_output(project.id, "projection", "projection.json")
    second_manifest = json.loads(
        read_output(project.id, "projection", "manifest.json"))
    # Byte-identical content: the first render's own ledger event moved
    # the cursor, yet the projected CONTENT is unchanged - stamps live in
    # the manifest and the event, never in the content.
    assert first_bytes == second_bytes, \
        "Same facts must project to byte-identical content"
    assert first["projection_hash"] == second["projection_hash"]
    assert b"rendered_at" not in first_bytes
    assert b"audit_cursor" not in first_bytes
    changed = {k for k in first_manifest
               if first_manifest[k] != second_manifest[k]}
    assert changed <= {"rendered_at", "audit_cursor"}, changed
    assert second_manifest["audit_cursor"] > first_manifest["audit_cursor"], \
        "The manifest cursor must track the ledger moment"
    print("Part 4 passed: projected content byte-identical across renders "
          "(cursor moved in the manifest only); rendered_at confined to "
          "the manifest.")


def part_5_staleness(session, project, officer):
    print("\n--- Part 5: staleness computed, surfaced, and cleared ---")
    projection_engine.render(session, officer, project.id,
                             renderer="projection")
    history = projection_engine.render_history(session, project.id)
    latest = history[0]
    assert latest["current"] and latest["stale"] is False, latest
    stale_items = [i for i in governance_inbox.build_inbox(
        session, project.id)["items"] if i["type"] == "PROJECTION_STALE"]
    assert not stale_items, "A fresh render must not surface as stale"

    # Governed facts move: a new approved asset enters the corpus.
    session.add(db.KnowledgeAsset(
        project_id=project.id, type="SYSTEM", name="New Fact",
        content="The archive platform rotates backups weekly.",
        status="APPROVED", access_level="INTERNAL", domain="hr"))
    session.commit()

    history = projection_engine.render_history(session, project.id)
    assert history[0]["stale"] is True, \
        "A render behind governed facts must be detectably stale"
    inbox = governance_inbox.build_inbox(session, project.id)
    stale_items = [i for i in inbox["items"]
                   if i["type"] == "PROJECTION_STALE"]
    assert len(stale_items) == 1
    assert stale_items[0]["severity"] == "LOW", \
        "Staleness never blocks the compile gate (D2) - LOW, never HIGH"
    assert stale_items[0]["bucket"] == "CAN_WAIT"

    # Regenerating IS the repair: the item leaves when facts are re-projected.
    projection_engine.render(session, officer, project.id,
                             renderer="projection")
    assert projection_engine.render_history(session, project.id)[0]["stale"] is False
    stale_items = [i for i in governance_inbox.build_inbox(
        session, project.id)["items"] if i["type"] == "PROJECTION_STALE"]
    assert not stale_items
    print("Part 5 passed: drift detected by recompose-and-compare, "
          "surfaced LOW with no dismiss, cleared by regeneration alone.")


def part_6_event_quality(session, project, officer):
    print("\n--- Part 6: the ledger event answers everything (D28) ---")
    summary = projection_engine.render(
        session, officer, project.id, renderer="projection",
        clearance="INTERNAL", status_inclusion=("APPROVED",),
        domain_prefix="finances")
    event = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "PROJECTION_RENDERED").order_by(
        db.AuditEvent.id.desc()).first()
    details = json.loads(event.details)
    # What was projected, for whom, at which ledger moment - from the
    # event alone.
    assert details["renderer"] == "projection"
    assert details["clearance"] == "INTERNAL"
    assert details["status_inclusion"] == ["APPROVED"]
    assert details["domain_prefix"] == "finances"
    assert details["audit_cursor"] > 0
    assert details["counts"]["nodes"] > 0
    assert "assets_above_clearance" in details["excluded"]
    assert event.target_id == str(project.id)
    assert event.identity_fact_id is not None, \
        "A render is a governed act - it carries the actor's fact"
    # Tamper evidence: ledger hash == disk bytes, for every file.
    manifest_bytes = read_output(project.id, "projection", "manifest.json")
    assert details["manifest_hash"] == sha256(manifest_bytes)
    manifest = json.loads(manifest_bytes)
    for name, digest in manifest["files"].items():
        assert digest == sha256(read_output(project.id, "projection", name))
    assert details["projection_hash"] == manifest["files"]["projection.json"]
    assert summary["manifest_hash"] == details["manifest_hash"]
    print("Part 6 passed: renderer/clearance/statuses/scope/cursor/"
          "exclusions/hashes all answerable from the event; every disk "
          "byte accounted for in the ledger.")


def part_7_routes(session, project, officer):
    print("\n--- Part 7: routes propose; the engine decides ---")
    result = render_projection(
        project.id, schemas.ProjectionRenderRequest(renderer="projection"),
        db_session=session, actor=officer)
    assert result["status"] == "RENDERED"
    assert "content" not in result, "Route responses are metadata-only"
    history = list_projections(project.id, db_session=session, actor=officer)
    assert history and history[0]["renderer"] == "projection"
    assert history[0]["stale"] is False
    for bad_request, fragment in (
            (schemas.ProjectionRenderRequest(renderer="neo4j"), "renderer"),
            (schemas.ProjectionRenderRequest(status_inclusion=["SHINY"]), "status"),
            (schemas.ProjectionRenderRequest(clearance="ULTRA"), "clearance")):
        try:
            render_projection(project.id, bad_request,
                              db_session=session, actor=officer)
            raise AssertionError(f"bad {fragment} accepted")
        except HTTPException as e:
            assert e.status_code == 400 and fragment in str(e.detail).lower()
    try:
        render_projection(999999, schemas.ProjectionRenderRequest(),
                          db_session=session, actor=officer)
        raise AssertionError("missing project accepted")
    except HTTPException as e:
        assert e.status_code == 404
    print("Part 7 passed: render at assets:approve validates and "
          "delegates; history at assets:read; refusals refuse.")


def part_8_custody_sweep(session, project, officer):
    print("\n--- Part 8: the D25 sweep covers the new export surface ---")
    custody.create_external_credential(
        session, name="sweep-sentinel", purpose="CONNECTOR",
        secret=SENTINEL, actor=officer)
    projection_engine.render(session, officer, project.id,
                             renderer="projection", clearance="EXECUTIVE")
    render_root = os.path.join(os.environ["EM_PROJECTION_DIR"],
                               f"project_{project.id}")
    swept = 0
    for root, _dirs, files in os.walk(render_root):
        for name in files:
            with open(os.path.join(root, name), "rb") as f:
                assert SENTINEL.encode() not in f.read(), \
                    f"D25 violation: sentinel readable in render file {name}"
            swept += 1
    assert swept >= 2
    for event in session.query(db.AuditEvent).all():
        blob = f"{event.event_type} {event.details} {event.target_id}"
        assert SENTINEL not in blob, \
            f"D25 violation: sentinel in audit event {event.id}"
    print(f"Part 8 passed: {swept} render file(s) + the full ledger swept "
          f"clean - renders join the custody-swept surfaces.")


def main():
    tmp = tempfile.mkdtemp(prefix="em_projeng_db_")
    engine = create_engine(f"sqlite:///{os.path.join(tmp, 'suite.db')}",
                           connect_args={"check_same_thread": False})
    db.engine = engine
    db.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = Session
    session = Session()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    project, rows = seed(session, officer)

    part_1_engine_proof(session, project, rows)
    part_2_clearance(session, project, rows, officer)
    part_3_domain_scope(session, project, rows)
    part_4_determinism(session, project, officer)
    part_5_staleness(session, project, officer)
    part_6_event_quality(session, project, officer)
    part_7_routes(session, project, officer)
    part_8_custody_sweep(session, project, officer)
    print("\n=== All Projection Engine (WS1) tests passed successfully! ===")


if __name__ == "__main__":
    main()
