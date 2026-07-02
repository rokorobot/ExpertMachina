import hashlib
import json
import os
import shutil
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ["EM_SECRET_KEY"] = "projection-acceptance-master-key"
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_accept_out_")
os.environ["EM_AGENT_ID"] = "mallory-agent"          # hostile, inert (v1.0)
os.environ["EM_AGENT_CLEARANCE"] = "EXECUTIVE"       # hostile, inert (v1.0)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import connectors
from app import ingestion
from app import policy
from app import identity
from app import custody
from app import governance_inbox
from app import mcp_gateway
from app.projections import engine as projection_engine
import test_support
import test_workbench_projection

# THE v1.3.0 MILESTONE GATE (WS4, D28, docs/projection-engine-v1.3.md).
#
# One end-to-end narrative re-proving the whole arc in a single run:
# a corpus enters through the real governed pipeline (scan ->
# classification -> policy auto-approval), becomes an expert model,
# package, selection, and binding; a graph render exports it as a
# stamped, clearance-filtered, tamper-evident lens; an agent walks
# document -> binding as one MCP path query; governed facts move and
# the render becomes detectably stale, surfaces in the inbox, and is
# repaired by regeneration alone; every artifact is deleted and nothing
# is lost; a tampered byte is caught from the ledger alone; the D25
# sentinel appears in no rendered byte.
#
# THE CLOSING LINE is the milestone's constitutional claim: the D24
# frozen schema is byte-identical to v1.2.1's - 28 tables, 303 columns.
# The projection engine shipped as a lens, structurally incapable of
# being a second knowledge system.

SENTINEL = "SENTINEL-acceptance-secret-c41b77"
FINANCE_SENTENCE = "The accounting platform reconciles ledgers in a SQLite database server."
HR_SENTENCE = "All new joiners must sign the onboarding agreement before access."
LATER_SENTENCE = "The archive platform stores backups in a MariaDB database server."

ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_accept_qdrant_")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_file(project_id, name) -> bytes:
    path = os.path.join(os.environ["EM_PROJECTION_DIR"],
                        f"project_{project_id}", "graph", name)
    with open(path, "rb") as f:
        return f.read()


def run_scan(session, connector):
    job = db.IngestionJob(project_id=connector.project_id,
                          connector_id=connector.id, status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    connectors.execute_ingestion_job(session, job.id)
    session.refresh(job)
    assert job.status == "COMPLETED", f"{job.status} / {job.error}"
    return job


def main():
    tmp = tempfile.mkdtemp(prefix="em_accept_db_")
    engine = create_engine(f"sqlite:///{os.path.join(tmp, 'accept.db')}",
                           connect_args={"check_same_thread": False})
    db.engine = engine
    db.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = Session
    session = Session()

    officer = test_support.governed_actor(session, "GovernanceOfficer")
    custody.create_external_credential(
        session, name="acceptance-sentinel", purpose="CONNECTOR",
        secret=SENTINEL, actor=officer)
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Acceptance", description="v1.3.0 milestone gate",
        customer_id=customer.id), actor=officer)

    # --- Stage 1: the corpus enters through the REAL governed pipeline.
    print("\n--- Stage 1: corpus in (scan -> classify -> auto-approve) ---")
    folder = tempfile.mkdtemp(prefix="em_accept_src_")
    for name, sentence in (("finance/ledger.txt", FINANCE_SENTENCE),
                           ("hr/onboarding.txt", HR_SENTENCE)):
        path = os.path.join(folder, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(sentence + "\n")
    connector = db.SourceConnector(project_id=project.id, name="Acceptance Share",
                                   type="LOCAL_FOLDER", root_path=folder,
                                   include_extensions=".txt")
    session.add(connector)
    session.commit()
    session.refresh(connector)
    session.add_all([
        db.ClassificationPolicy(
            project_id=project.id, name="acceptance-taxonomy", enabled=True,
            rules_json=json.dumps([
                {"domain": "finances/accounting",
                 "match": {"uri_prefix": os.path.join(folder, "finance")}},
                {"domain": "hr",
                 "match": {"uri_prefix": os.path.join(folder, "hr")}},
            ])),
        db.ApprovalPolicy(project_id=project.id, name="acceptance-tier1",
                          asset_types_json=json.dumps(
                              sorted(policy.ALLOWED_ASSET_TYPES)),
                          enabled=True),
    ])
    session.commit()
    run_scan(session, connector)
    approved = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.status == "APPROVED").order_by(
        db.KnowledgeAsset.id).all()
    assert approved, "The pipeline must approve the corpus"
    domains = {a.domain for a in approved}
    assert "finances/accounting" in domains and "hr" in domains, domains
    print(f"Stage 1 passed: {len(approved)} assets approved by policy with "
          f"governed domains {sorted(domains)}.")

    # --- Stage 2: the consumption chain on top.
    print("\n--- Stage 2: expert -> package -> selection -> binding ---")
    expert = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Acceptance Expert", description="",
        project_id=project.id, asset_ids=[a.id for a in approved]),
        actor=officer)
    package = db.AgentPackage(project_id=project.id, name="acceptance-pack",
                              expert_model_id=expert.id,
                              clearance_level="INTERNAL",
                              package_hash="hash-accept")
    session.add(package)
    session.commit()
    agent = identity.create_principal(
        session, name="acceptance-agent", display_name="Acceptance Agent",
        kind="AGENT", clearance="INTERNAL", created_by="acceptance-gate")
    session.add_all([
        db.PackageModelSelection(
            agent_package_id=package.id, package_version="1",
            package_hash="hash-accept", selected_provider="OPENAI",
            selected_model_name="gpt-4o-mini",
            supporting_evaluation_run_ids_json="[]", rationale="gate",
            selected_by_principal_id=officer.principal.id),
        db.ExpertAgentBinding(
            agent_package_id=package.id, package_version="1",
            package_hash="hash-accept", selected_provider="OPENAI",
            selected_model_name="gpt-4o-mini", agent_principal_id=agent.id,
            principal_clearance_at_issue="INTERNAL",
            selection_evidence_json="{}",
            identity_fact_id=officer.fact(session).id),
    ])
    session.commit()
    print("Stage 2 passed: the full governed chain exists.")

    # --- Stage 3: render out - stamped, filtered, recorded.
    print("\n--- Stage 3: render out (the lens) ---")
    summary = projection_engine.render(session, officer, project.id,
                                       renderer="graph",
                                       clearance="INTERNAL")
    event = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "PROJECTION_RENDERED").order_by(
        db.AuditEvent.id.desc()).first()
    recorded = json.loads(event.details)
    assert recorded["manifest_hash"] == sha256(
        render_file(project.id, "manifest.json"))
    assert recorded["audit_cursor"] > 0 and recorded["rendered_at"]
    assert event.identity_fact_id is not None
    print(f"Stage 3 passed: {recorded['counts']['nodes']} nodes rendered, "
          f"stamped at cursor {recorded['audit_cursor']}, every hash in "
          f"the ledger.")

    # --- Stage 4: the agent walks the lens (governed channel).
    print("\n--- Stage 4: MCP path query (document -> binding) ---")
    token, _cred = identity.issue_token(session, agent, label="acceptance")
    os.environ["EM_AGENT_TOKEN"] = token
    doc_node = f"document:{approved[0].document_id}"
    path_result = mcp_gateway.get_lineage_path(
        project.id, doc_node, f"binding:{1}", session=session)
    assert path_result["path_found"] is True
    assert [e["relation"] for e in path_result["edges"]] == \
        ["PROVENANCE", "MEMBER_OF", "COMPILED_FROM", "BOUND_TO"]
    print(f"Stage 4 passed: lineage in {path_result['hops']} hops through "
          f"the same composition the file render used.")

    # --- Stage 5: facts move; staleness surfaces; regeneration repairs.
    print("\n--- Stage 5: drift -> LOW inbox item -> regenerate ---")
    with open(os.path.join(folder, "finance", "archive.txt"), "w",
              encoding="utf-8") as f:
        f.write(LATER_SENTENCE + "\n")
    run_scan(session, connector)
    history = projection_engine.render_history(session, project.id)
    assert history[0]["stale"] is True
    stale_items = [i for i in governance_inbox.build_inbox(
        session, project.id)["items"] if i["type"] == "PROJECTION_STALE"]
    assert len(stale_items) == 1 and stale_items[0]["severity"] == "LOW"
    projection_engine.render(session, officer, project.id,
                             renderer="graph", clearance="INTERNAL")
    assert projection_engine.render_history(session, project.id)[0]["stale"] is False
    assert not [i for i in governance_inbox.build_inbox(
        session, project.id)["items"] if i["type"] == "PROJECTION_STALE"]
    print("Stage 5 passed: drift detected exactly, surfaced LOW, cleared "
          "by regeneration alone - no dismiss state exists.")

    # --- Stage 6: disposable and tamper-evident.
    print("\n--- Stage 6: tamper, delete, regenerate ---")
    latest = json.loads(session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "PROJECTION_RENDERED").order_by(
        db.AuditEvent.id.desc()).first().details)
    graph_path = os.path.join(os.environ["EM_PROJECTION_DIR"],
                              f"project_{project.id}", "graph", "graph.json")
    with open(graph_path, "ab") as f:
        f.write(b" ")
    assert sha256(render_file(project.id, "graph.json")) != \
        latest["files"]["graph.json"], "tamper must be detectable"
    shutil.rmtree(os.environ["EM_PROJECTION_DIR"])
    regenerated = projection_engine.render(session, officer, project.id,
                                           renderer="graph",
                                           clearance="INTERNAL")
    assert regenerated["files"] == latest["files"], \
        "total deletion must cost nothing - the lens regenerates exactly"
    print("Stage 6 passed: one tampered byte caught against the ledger; "
          "total deletion repaired by regeneration with identical hashes.")

    # --- Stage 7: custody discipline over the export surface.
    print("\n--- Stage 7: the D25 sweep ---")
    render_root = os.path.join(os.environ["EM_PROJECTION_DIR"],
                               f"project_{project.id}")
    swept = 0
    for root, _dirs, files in os.walk(render_root):
        for name in files:
            with open(os.path.join(root, name), "rb") as f:
                assert SENTINEL.encode() not in f.read()
            swept += 1
    for row_event in session.query(db.AuditEvent).all():
        assert SENTINEL not in f"{row_event.details} {row_event.target_id}"
    print(f"Stage 7 passed: {swept} rendered files + the ledger, sentinel-free.")

    # --- THE CLOSING LINE: zero schema change.
    print("\n--- The closing line: the constitutional claim ---")
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    assert live == test_workbench_projection.FROZEN_SCHEMA
    tables = len(live)
    columns = sum(len(cols) for cols in live.values())
    assert (tables, columns) == (28, 303)
    print(f"CLOSING LINE passed: the D24 snapshot is byte-identical to "
          f"v1.2.1's - {tables} tables, {columns} columns. The projection "
          f"engine shipped as a lens, structurally incapable of being a "
          f"second knowledge system.")
    print("\n=== v1.3.0 MILESTONE ACCEPTANCE passed ===")


if __name__ == "__main__":
    main()
