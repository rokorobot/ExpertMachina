import json
import os
import sys
import tempfile
import zipfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_disc_renders_")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_disc_packages_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

# v1.4.0 WS2 gate suite - primary-over-derived conflict discipline +
# class travels (D30, docs/diagnostic-workbench-v1.4.md).
#
# The discipline proof: a DERIVED fact contradicting a PRIMARY fact
# surfaces with declared asymmetry on every surface that shows the
# conflict; the class is present in every consumer channel's output
# (package bytes, graph.json, MCP response, citation); nothing is
# auto-resolved; the compile gate verdict is identical to the same
# conflict between two PRIMARY facts.

_tmpdir = tempfile.mkdtemp(prefix="em_disc_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'disc.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_disc_qdrant_")

from app import schemas  # noqa: E402
from app import crud  # noqa: E402
from app import identity  # noqa: E402
from app import conflict_engine  # noqa: E402
from app import governance_inbox  # noqa: E402
from app import query_engine  # noqa: E402
from app import package_builder  # noqa: E402
from app import package_consumer  # noqa: E402
from app import mcp_gateway  # noqa: E402
from app.projections import engine as projection_engine  # noqa: E402
import test_support  # noqa: E402


def _approved_asset(session, project_id, name, content, source_class="PRIMARY",
                    asset_type="POLICY", domain=None):
    """Raw-row seeding (established suite practice): an APPROVED asset of
    a declared class. Production class assignment is proposals.py's job,
    proven at the WS1 gate - this suite tests what happens AFTER a
    DERIVED fact exists."""
    asset = db.KnowledgeAsset(project_id=project_id, name=name, type=asset_type,
                              content=content, status="APPROVED",
                              access_level="INTERNAL", domain=domain,
                              source_class=source_class)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _conflict(session, project_id, expert_model_id, a, b,
              classification="DIRECT_CONTRADICTION"):
    rel = db.AssetRelationship(project_id=project_id,
                               expert_model_id=expert_model_id,
                               source_asset_id=a.id, target_asset_id=b.id,
                               relationship_type="CONFLICTS_WITH",
                               classification=classification,
                               confidence=0.99, status="DETECTED")
    session.add(rel)
    session.commit()
    session.refresh(rel)
    return rel


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Discipline", description="D30 WS2 gate", customer_id=customer.id),
        actor=officer)

    primary = _approved_asset(
        session, project.id, "Retention Policy",
        "Customer records must be retained for seven years.",
        source_class="PRIMARY", domain="compliance")
    derived = _approved_asset(
        session, project.id, "Retention Finding",
        "Customer records must be deleted after one year.",
        source_class="DERIVED", domain="compliance")
    control_a = _approved_asset(
        session, project.id, "Access Policy",
        "Contractors receive badge access after security training.",
        source_class="PRIMARY")
    control_b = _approved_asset(
        session, project.id, "Access Rule",
        "Contractors never receive badge access.",
        source_class="PRIMARY")

    mixed_model = db.ExpertModel(project_id=project.id, name="Mixed",
                                 asset_ids_json=json.dumps([primary.id, derived.id]),
                                 asset_count=2)
    control_model = db.ExpertModel(project_id=project.id, name="Control",
                                   asset_ids_json=json.dumps([control_a.id, control_b.id]),
                                   asset_count=2)
    session.add_all([mixed_model, control_model])
    session.commit()
    session.refresh(mixed_model)
    session.refresh(control_model)

    mixed_rel = _conflict(session, project.id, mixed_model.id, primary, derived)
    control_rel = _conflict(session, project.id, control_model.id, control_a, control_b)

    # ------------------------------------------------------------ Part 1
    # The shared annotator: asymmetry declared, DERIVED side the
    # presumptive review target, symmetric pairs honestly None.
    print("\n--- Part 1: the shared class annotator (D30) ---")
    annotations = conflict_engine.class_annotations(session, [mixed_rel, control_rel])
    mixed_note = annotations[mixed_rel.id]
    assert mixed_note["class_asymmetry"] == "PRIMARY_OVER_DERIVED"
    assert mixed_note["presumptive_review_target_asset_id"] == derived.id, \
        "the DERIVED side is the presumptive review target"
    assert {mixed_note["source_asset_source_class"],
            mixed_note["target_asset_source_class"]} == {"PRIMARY", "DERIVED"}
    control_note = annotations[control_rel.id]
    assert control_note["class_asymmetry"] is None
    assert control_note["presumptive_review_target_asset_id"] is None
    print("Part 1 passed: PRIMARYxDERIVED declared with the derived side as "
          "presumptive target; PRIMARYxPRIMARY honestly symmetric.")

    # ------------------------------------------------------------ Part 2
    # Every surface that shows the conflict declares the same asymmetry.
    print("\n--- Part 2: asymmetry on every conflict surface ---")
    from fastapi.testclient import TestClient
    from app import main as app_main
    with TestClient(app_main.app) as client:
        with db.SessionLocal() as boot:
            reviewer = identity.create_principal(
                boot, name="disc-reviewer", display_name="Disc Reviewer",
                kind="HUMAN", role="GOVERNANCE_REVIEWER", created_by="test-suite")
            identity.set_password(boot, reviewer, "disc-reviewer-pass-1",
                                  actor="test-suite")
        r = client.post("/api/auth/login", json={"name": "disc-reviewer",
                                                 "password": "disc-reviewer-pass-1"})
        REVIEWER = {"Authorization": f"Bearer {r.json()['token']}"}

        r = client.get(f"/api/experts/{mixed_model.id}/conflicts", headers=REVIEWER)
        assert r.status_code == 200, r.text
        rest_rel = r.json()[0]
        assert rest_rel["class_asymmetry"] == "PRIMARY_OVER_DERIVED"
        assert rest_rel["presumptive_review_target_asset_id"] == derived.id
        r = client.get(f"/api/experts/{control_model.id}/conflicts", headers=REVIEWER)
        assert r.json()[0]["class_asymmetry"] is None

    inbox = governance_inbox.build_inbox(session, project.id)
    conflict_items = {i["source_id"]: i for i in inbox["items"]
                      if i["type"] == "CONFLICT"}
    mixed_item = conflict_items[mixed_rel.id]
    assert mixed_item["class_asymmetry"] == "PRIMARY_OVER_DERIVED"
    assert mixed_item["presumptive_review_target_asset_id"] == derived.id
    assert "Primary prevails" in mixed_item["reason"]
    assert "unless a human rules otherwise" in mixed_item["reason"]
    control_item = conflict_items[control_rel.id]
    assert control_item["class_asymmetry"] is None
    assert "Primary prevails" not in control_item["reason"]

    # The MCP surface (the governed agent channel): same annotator.
    agent = identity.create_principal(session, name="disc-agent",
                                      display_name="Disc Agent", kind="AGENT",
                                      clearance="INTERNAL", created_by="test-suite")
    agent_token, _cred = identity.issue_token(session, agent, kind="API_TOKEN",
                                              label="disc", actor="test-suite")
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        mcp_conflicts = mcp_gateway.get_conflicts(mixed_model.id, session=session)
        mcp_rel = mcp_conflicts["relationships"][0]
        assert mcp_rel["class_asymmetry"] == "PRIMARY_OVER_DERIVED"
        assert mcp_rel["presumptive_review_target_asset_id"] == derived.id
        assert {mcp_rel["source_asset_source_class"],
                mcp_rel["target_asset_source_class"]} == {"PRIMARY", "DERIVED"}
        # get_provenance carries the class (clearance-checked channel).
        prov = mcp_gateway.get_provenance(derived.id, session=session)
        assert prov["source_class"] == "DERIVED"
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    print("Part 2 passed: REST conflicts, inbox item, MCP get_conflicts, and "
          "MCP get_provenance all declare the same asymmetry and classes.")

    # ------------------------------------------------------------ Part 3
    # Nothing auto-resolves; the compile gate is class-blind.
    print("\n--- Part 3: nothing auto-resolves; the gate is class-blind ---")
    session.refresh(mixed_rel)
    assert mixed_rel.status == "DETECTED" and mixed_rel.reviewed_by is None, \
        "reading surfaces must never resolve a conflict"
    mixed_gate = conflict_engine.evaluate_compile_gate(session, mixed_model.id)
    control_gate = conflict_engine.evaluate_compile_gate(session, control_model.id)
    assert mixed_gate["allowed"] == control_gate["allowed"], \
        "the gate verdict must be identical for the same conflict shape"
    assert not mixed_gate["allowed"], \
        "an unreviewed DIRECT_CONTRADICTION blocks - whichever class it involves"
    assert (conflict_engine.relationship_gate_disposition(mixed_rel)
            == conflict_engine.relationship_gate_disposition(control_rel)), \
        "disposition is class-blind"
    # Humans still rule: dismissing the mixed conflict works exactly as
    # before, and the gate follows the human, not the class.
    conflict_engine.review_relationship(session, mixed_rel.id, status="DISMISSED",
                                        reviewer=officer,
                                        notes="context: finding covers a different record species")
    session.refresh(mixed_rel)
    assert mixed_rel.status == "DISMISSED"
    assert conflict_engine.evaluate_compile_gate(session, mixed_model.id)["allowed"]
    print("Part 3 passed: DETECTED until a human ruled; gate verdicts "
          "identical across classes; the human dismissal reopened the gate.")

    # ------------------------------------------------------------ Part 4
    # Class travels: package bytes, graph.json, MCP graph node, citation.
    print("\n--- Part 4: the class in every consumer channel's output ---")
    # The portable channel (.empkg): compile the mixed model (its
    # conflict is now dismissed, so the gate permits it).
    package_row = db.AgentPackage(project_id=project.id,
                                  expert_model_id=mixed_model.id,
                                  name="Mixed Package",
                                  clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    build = package_builder.build_package(session, package_row)
    with zipfile.ZipFile(package_row.file_path) as zf:
        knowledge = json.loads(zf.read("knowledge.json"))
    classes_in_package = {e["asset_id"]: e["source_class"] for e in knowledge}
    assert classes_in_package[primary.id] == "PRIMARY"
    assert classes_in_package[derived.id] == "DERIVED"

    # The consumer's own retrieval carries the class through the
    # portable channel end (no generation needed for the travel proof).
    loaded = package_consumer.load_package(package_row.file_path)
    retrieval = package_consumer.retrieve(loaded, "How long are customer records retained?")
    assert retrieval["selected"], "retrieval must select evidence"
    assert all("source_class" in entry for entry in retrieval["selected"])
    selected_classes = {e["asset_id"]: e["source_class"] for e in retrieval["selected"]}
    assert selected_classes.get(derived.id, selected_classes.get(primary.id)) in (
        "PRIMARY", "DERIVED")

    # The rendered lens (graph.json bytes) + the composed projection.
    projection = projection_engine.compose(session, project.id)
    node_classes = {n.id: n.metadata.get("source_class")
                    for n in projection.nodes if n.kind == "ASSET"}
    assert node_classes[f"asset:{primary.id}"] == "PRIMARY"
    assert node_classes[f"asset:{derived.id}"] == "DERIVED"
    conflict_edges = [e for e in projection.edges if e.relation == "CONFLICTS_WITH"]
    mixed_edges = [e for e in conflict_edges
                   if {e.source_id, e.target_id} == {f"asset:{primary.id}",
                                                     f"asset:{derived.id}"}]
    assert mixed_edges and mixed_edges[0].metadata.get("class_asymmetry") == \
        "PRIMARY_OVER_DERIVED"
    control_edges = [e for e in conflict_edges
                     if {e.source_id, e.target_id} == {f"asset:{control_a.id}",
                                                       f"asset:{control_b.id}"}]
    assert control_edges and "class_asymmetry" not in control_edges[0].metadata

    projection_engine.render(session, officer, project.id, renderer="graph")
    graph_json_path = None
    for root, _dirs, files in os.walk(os.environ["EM_PROJECTION_DIR"]):
        if "graph.json" in files:
            graph_json_path = os.path.join(root, "graph.json")
    assert graph_json_path, "the graph render must exist under EM_PROJECTION_DIR"
    with open(graph_json_path, "r", encoding="utf-8") as f:
        graph_bytes = f.read()
    assert '"source_class"' in graph_bytes and '"DERIVED"' in graph_bytes, \
        "the rendered artifact must show derivation"

    # The governed live channel: MCP graph neighbors + the LIVE citation.
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        neighbors = mcp_gateway.get_graph_neighbors(project.id,
                                                    f"asset:{derived.id}",
                                                    session=session)
        node = neighbors.get("node") or {}
        assert node.get("metadata", {}).get("source_class") == "DERIVED", neighbors
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    citation = query_engine._build_citation(session, derived)
    assert citation["source_class"] == "DERIVED"
    assert query_engine._build_citation(session, primary)["source_class"] == "PRIMARY"
    print("Part 4 passed: package bytes, consumer retrieval, composed "
          "projection, rendered graph.json, MCP graph node, and citations "
          "all carry the class.")

    session.close()
    print("\nAll v1.4.0 WS2 discipline checks passed: PRIMARYxDERIVED "
          "asymmetry declared identically on every conflict surface with the "
          "derived side as presumptive review target, nothing auto-resolved, "
          "the compile gate class-blind, and the class present in every "
          "consumer channel's output.")


if __name__ == "__main__":
    main()
