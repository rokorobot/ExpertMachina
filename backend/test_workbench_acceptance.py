import json
import os
import subprocess
import sys
import tempfile
import zipfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_wsaccept_packages_")
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_wsaccept_renders_")
os.environ["EM_SECRET_KEY"] = "acceptance-master-key-material-1"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

# THE v1.4.0 MILESTONE GATE (D29 The One-Way Valve + D30 Derived Source
# Class, docs/diagnostic-workbench-v1.4.md).
#
# The full loop, once, end to end: corpus in through the real governed
# pipeline -> a bound agent diagnoses through the existing doors ->
# its proposal lands in /08_proposals -> the scan holds every candidate
# under a live permissive policy environment (the lane sentinel, live)
# -> a human accepts ONE finding -> a DERIVED fact with complete
# verified synthesis provenance -> the fact is retrievable, packageable,
# renderable, and MCP-queryable with its class declared -> a PRIMARY
# contradiction surfaces with declared asymmetry -> closing on the two
# constitutional assertions: THE LEDGER ALONE proves no agent principal
# wrote any canonical fact directly, and the D24 snapshot stands at the
# WS0-ratified 28 tables / 305 columns.

_tmpdir = tempfile.mkdtemp(prefix="em_wsaccept_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'accept.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_wsaccept_qdrant_")

from app import schemas  # noqa: E402
from app import crud  # noqa: E402
from app import connectors  # noqa: E402
from app import custody  # noqa: E402
from app import identity  # noqa: E402
from app import policy  # noqa: E402
from app import proposals  # noqa: E402
from app import tier2  # noqa: E402
from app import conflict_engine  # noqa: E402
from app import governance_inbox  # noqa: E402
from app import query_engine  # noqa: E402
from app import package_builder  # noqa: E402
from app import package_consumer  # noqa: E402
from app import mcp_gateway  # noqa: E402
from app.projections import engine as projection_engine  # noqa: E402
import test_support  # noqa: E402
import test_workbench_projection  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
from workbench import onboarding_diagnostic as wb  # noqa: E402

SENTINEL = "SENTINEL-ws4-acceptance-secret-9d2f41"
CORPUS = {
    "systems.txt": "The onboarding platform stores training records in a PostgreSQL database server.",
    "policy.txt": "All new hires must complete safety training before badge access is granted.",
}
PROPOSED_SENTENCE = ("All new contractors must complete mentor onboarding "
                     "before badge issuance.")
CONTRADICTING_PRIMARY = ("All new contractors must never complete mentor "
                         "onboarding before badge issuance.")


def write_file(folder, name, text):
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    return path


def run_scan(session, connector):
    job = db.IngestionJob(project_id=connector.project_id,
                          connector_id=connector.id, status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    connectors.execute_ingestion_job(session, job.id)
    tier2.drain()
    session.refresh(job)
    assert job.status == "COMPLETED", f"{job.status} / {job.error}"
    return job


class InProcessGraphClient:
    def get_domain_subgraph(self, project_id, domain_prefix):
        session = db.SessionLocal()
        try:
            return mcp_gateway.get_domain_subgraph(project_id, domain_prefix,
                                                   session=session)
        finally:
            session.close()


def deterministic_synthesizer(package_path, questions):
    package = package_consumer.load_package(package_path)
    findings = []
    for i, question in enumerate(questions):
        retrieval = package_consumer.retrieve(package, question, top_k=3)
        selected = retrieval["selected"]
        names = ", ".join(e["name"] for e in selected) or "no governed evidence"
        text = f"Evidence review for onboarding: {names}."
        if i == 0:
            text += f" Proposed knowledge: {PROPOSED_SENTENCE}"
        findings.append({"question": question, "finding": text,
                         "cited_asset_ids": [e["asset_id"] for e in selected]})
    return findings


class ApproveEverythingVerifier:
    identity = {"method": "GUARD_APPROVE_EVERYTHING",
                "note": "acceptance lane-sentinel seam"}

    def check(self, candidate, corpus):
        return {"pairs_checked": len(corpus), "pairs_dropped": 0,
                "contradictions": []}


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    custody.create_external_credential(
        session, name="ws4-sentinel", purpose="CONNECTOR",
        secret=SENTINEL, actor=officer)
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Workbench Acceptance", description="v1.4.0 milestone gate",
        customer_id=customer.id), actor=officer)
    tier2.verifier_factory = ApproveEverythingVerifier

    # --- Stage 1: the corpus enters through the REAL governed pipeline.
    print("\n--- Stage 1: corpus in ---")
    corpus_folder = tempfile.mkdtemp(prefix="em_wsaccept_corpus_")
    primary_connector = db.SourceConnector(
        project_id=project.id, name="Onboarding Docs", type="LOCAL_FOLDER",
        root_path=corpus_folder, include_extensions=".txt")
    session.add(primary_connector)
    session.commit()
    session.refresh(primary_connector)
    for name, sentence in CORPUS.items():
        write_file(corpus_folder, name, sentence)
    run_scan(session, primary_connector)
    reviewer = test_support.governed_actor(session, "GateReviewer")
    for asset in session.query(db.KnowledgeAsset).filter_by(
            project_id=project.id, status="CANDIDATE").all():
        crud.update_knowledge_asset(
            session, asset.id,
            schemas.KnowledgeAssetUpdate(status="APPROVED", domain="onboarding"),
            actor=reviewer, review_notes="corpus approval")
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    assert approved and all(a.source_class == "PRIMARY" for a in approved)
    print(f"Stage 1 passed: {len(approved)} PRIMARY facts approved by a human.")

    # --- Stage 2: the consumption chain - package, agent, binding.
    print("\n--- Stage 2: the consumption chain ---")
    model = db.ExpertModel(project_id=project.id, name="Onboarding Expert",
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    session.add(model)
    session.commit()
    session.refresh(model)
    package_row = db.AgentPackage(project_id=project.id, expert_model_id=model.id,
                                  name="Onboarding Package",
                                  clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    package_builder.build_package(session, package_row)
    agent = identity.create_principal(session, name="onboarding-diagnostic",
                                      display_name="Onboarding Diagnostic",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _cred = identity.issue_token(session, agent, kind="API_TOKEN",
                                              label="ws4", actor="test-suite")
    issuer = test_support.governed_actor(session, "BindingIssuer")
    binding = db.ExpertAgentBinding(
        agent_package_id=package_row.id, agent_principal_id=agent.id,
        package_hash=package_row.package_hash, package_version="v1",
        principal_clearance_at_issue="INTERNAL",
        selected_provider="ANTHROPIC", selected_model_name="claude-opus-4-8",
        selection_evidence_json="{}",
        identity_fact_id=issuer.fact(session).id)
    session.add(binding)
    session.commit()
    session.refresh(binding)
    print(f"Stage 2 passed: package {package_row.package_hash[:12]}... bound "
          f"to AGENT '{agent.name}'.")

    # --- Stage 3: the bound agent diagnoses through the existing doors.
    print("\n--- Stage 3: evidence-backed diagnosis out ---")
    vault_dir = tempfile.mkdtemp(prefix="em_wsaccept_vault_")
    subprocess.run([sys.executable, os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                    "--vault-dir", vault_dir], capture_output=True, check=True)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        proposal_path = wb.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="onboarding-diagnostic", binding_id=binding.id,
            domain_prefix="onboarding",
            synthesizer=deterministic_synthesizer,
            graph_client=InProcessGraphClient())
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    with open(proposal_path, encoding="utf-8") as f:
        proposal_content = f.read()
    assert PROPOSED_SENTENCE in proposal_content
    print(f"Stage 3 passed: the diagnosis landed at "
          f"{os.path.relpath(proposal_path, vault_dir)}.")

    # --- Stage 4: the return path holds under a live permissive
    # policy environment (the lane sentinel, live at the milestone gate).
    print("\n--- Stage 4: the proposal holds for the gate ---")
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add_all([
        db.ApprovalPolicy(project_id=project.id, name="everything-tier1",
                          asset_types_json=all_types, enabled=True),
        db.ApprovalPolicy(project_id=project.id, name="everything-tier2",
                          asset_types_json=all_types, enabled=True,
                          engine_conditions_json=json.dumps(
                              {"contradiction_check": "CLEAN_REQUIRED"})),
    ])
    lane_connector = db.SourceConnector(
        project_id=project.id, name="Proposal Lane", type="LOCAL_FOLDER",
        root_path=os.path.join(vault_dir, "08_proposals"),
        include_extensions=".md", lane="PROPOSAL")
    session.add(lane_connector)
    session.commit()
    session.refresh(lane_connector)
    run_scan(session, lane_connector)

    lane_doc_ids = policy.proposal_lane_document_ids(
        session, [d.id for d in session.query(db.Document).filter_by(
            project_id=project.id).all()])
    proposal_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_doc_ids)).all()
    assert proposal_assets
    assert all(a.status == "CANDIDATE" and a.source_class == "DERIVED"
               for a in proposal_assets), \
        "D29: every proposal candidate holds; D30: every one is DERIVED"
    declared = set()
    for e in session.query(db.AuditEvent).filter(db.AuditEvent.event_type.in_(
            ("POLICY_AUTOAPPROVAL_COMPLETED", "POLICY_TIER2_COMPLETED"))).all():
        declared.update(json.loads(e.details).get("proposal_lane_held_ids", []))
    assert {a.id for a in proposal_assets} <= declared, "holds must be declared"
    print(f"Stage 4 passed: {len(proposal_assets)} DERIVED candidate(s) held "
          f"under tier-1 + a live approve-everything tier-2 engine; declared.")

    # --- Stage 5: a human accepts ONE finding -> the DERIVED fact.
    print("\n--- Stage 5: one accepted finding, complete provenance ---")
    finding = next(a for a in proposal_assets
                   if "mentor onboarding" in (a.content or ""))
    crud.update_knowledge_asset(
        session, finding.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted the diagnostic finding")
    session.refresh(finding)
    assert finding.status == "APPROVED" and finding.source_class == "DERIVED"
    event = session.query(db.AuditEvent).filter_by(
        event_type="ASSET_APPROVED", target_id=str(finding.id)).order_by(
        db.AuditEvent.id.desc()).first()
    details = json.loads(event.details)
    prov = details["synthesis_provenance"]
    assert prov["provenance_verified"] is True
    assert prov["claimed"]["agent_principal"] == "onboarding-diagnostic"
    assert prov["verified"]["binding_id"] == binding.id
    assert prov["verified"]["package_hash"] == package_row.package_hash
    assert prov["cited_assets"]["missing"] == []
    fact = session.query(db.IdentityFact).filter_by(
        id=event.identity_fact_id).first()
    assert fact.principal_name == "GateReviewer" and fact.principal_kind == "HUMAN"
    print(f"Stage 5 passed: asset {finding.id} is an APPROVED DERIVED fact; "
          f"the event names agent, binding {binding.id}, package hash, "
          f"{len(prov['cited_assets']['found'])} citations, and the human.")

    # --- Stage 6: the DERIVED fact is ordinary APPROVED knowledge with
    # its class declared in every channel.
    print("\n--- Stage 6: retrievable, packageable, renderable, queryable ---")
    citation = query_engine._build_citation(session, finding)
    assert citation["source_class"] == "DERIVED"
    model.asset_ids_json = json.dumps([a.id for a in approved] + [finding.id])
    model.asset_count = len(approved) + 1
    session.commit()
    package_builder.build_package(session, package_row)
    with zipfile.ZipFile(package_row.file_path) as zf:
        knowledge = json.loads(zf.read("knowledge.json"))
    assert {e["asset_id"]: e["source_class"] for e in knowledge}[finding.id] == "DERIVED"
    projection_engine.render(session, officer, project.id, renderer="graph")
    graph_json = None
    for root, _dirs, files in os.walk(os.environ["EM_PROJECTION_DIR"]):
        if "graph.json" in files:
            with open(os.path.join(root, "graph.json"), encoding="utf-8") as f:
                graph_json = f.read()
    assert graph_json and '"DERIVED"' in graph_json
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        neighbors = mcp_gateway.get_graph_neighbors(
            project.id, f"asset:{finding.id}", session=session)
        assert neighbors["node"]["metadata"]["source_class"] == "DERIVED"
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    print("Stage 6 passed: citation, package bytes, rendered graph, and the "
          "MCP graph node all declare DERIVED.")

    # --- Stage 7: primary prevails - declared, never auto-resolved.
    print("\n--- Stage 7: the PRIMARY contradiction, asymmetry declared ---")
    contradicting = db.KnowledgeAsset(
        project_id=project.id, name=finding.name, type=finding.type,
        content=CONTRADICTING_PRIMARY, status="APPROVED",
        access_level="INTERNAL", domain="onboarding")
    session.add(contradicting)
    session.commit()
    session.refresh(contradicting)
    rel = db.AssetRelationship(
        project_id=project.id, expert_model_id=model.id,
        source_asset_id=contradicting.id, target_asset_id=finding.id,
        relationship_type="CONFLICTS_WITH",
        classification="DIRECT_CONTRADICTION", confidence=0.99,
        status="DETECTED")
    session.add(rel)
    session.commit()
    session.refresh(rel)
    note = conflict_engine.class_annotations(session, [rel])[rel.id]
    assert note["class_asymmetry"] == "PRIMARY_OVER_DERIVED"
    assert note["presumptive_review_target_asset_id"] == finding.id
    inbox_item = next(i for i in governance_inbox.build_inbox(
        session, project.id)["items"]
        if i["type"] == "CONFLICT" and i["source_id"] == rel.id)
    assert "Primary prevails" in inbox_item["reason"]
    session.refresh(rel)
    assert rel.status == "DETECTED", "nothing auto-resolves"
    assert not conflict_engine.evaluate_compile_gate(session, model.id)["allowed"], \
        "the gate blocks the unreviewed contradiction - class-blind"
    print("Stage 7 passed: asymmetry declared, the DERIVED side the "
          "presumptive target, the conflict unresolved, the gate blocking.")

    # --- Stage 8: the D25 sweep over the milestone's new surfaces.
    print("\n--- Stage 8: custody sentinel sweep ---")
    swept = 0
    for base in (vault_dir, os.environ["EM_PROJECTION_DIR"],
                 os.environ["EM_PACKAGE_DIR"]):
        for root, _dirs, files in os.walk(base):
            for name in files:
                with open(os.path.join(root, name), "rb") as f:
                    assert SENTINEL.encode() not in f.read()
                swept += 1
    for row_event in session.query(db.AuditEvent).all():
        assert SENTINEL not in f"{row_event.details} {row_event.target_id}"
    print(f"Stage 8 passed: {swept} vault/render/package files + the ledger, "
          f"sentinel-free.")

    # --- THE CLOSING LINES.
    print("\n--- The closing lines: the constitutional claims ---")
    # (a) THE LEDGER PROOF: no agent principal wrote any canonical fact.
    approval_events = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type.in_(
            ("ASSET_APPROVED", "ASSET_AUTO_APPROVED", "ASSET_REVIEWED",
             "ASSET_REVISION_APPROVED"))).all()
    assert approval_events, "the loop must have produced approval evidence"
    for e in approval_events:
        assert e.identity_fact_id is not None, \
            f"event {e.id}: a canonical write without identity evidence"
        e_fact = session.query(db.IdentityFact).filter_by(
            id=e.identity_fact_id).first()
        assert e_fact.principal_kind != "AGENT", \
            f"D29 VIOLATION: event {e.id} - an AGENT wrote canonical state"
    derived_approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED", source_class="DERIVED").all()
    for asset in derived_approved:
        human_reviews = [r for r in asset.reviews
                         if r.approver and not r.approver.startswith("policy:")]
        assert human_reviews, f"DERIVED fact {asset.id} without a human review"
    # (b) the D24 snapshot at the WS0-ratified shape.
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    assert live == test_workbench_projection.FROZEN_SCHEMA
    tables = len(live)
    columns = sum(len(cols) for cols in live.values())
    assert (tables, columns) == (28, 305)
    print(f"CLOSING LINES passed: {len(approval_events)} approval events all "
          f"carry non-AGENT identity facts; every APPROVED DERIVED fact has "
          f"a human review; the D24 snapshot stands at {tables} tables / "
          f"{columns} columns exactly as ratified at WS0.")
    print("\n=== v1.4.0 MILESTONE ACCEPTANCE passed: the full loop, once, "
          "end to end - and no agent wrote canonical facts directly. ===")
    session.close()


if __name__ == "__main__":
    main()
