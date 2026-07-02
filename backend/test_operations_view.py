import json
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

# v1.4.1 gate suite - the Operations view (the D8 amendment recorded in
# docs/diagnostic-workbench-v1.4.md).
#
# The Operations area is a pure projection (D1/D24) of Operations Realm
# activity: agents + bindings, the proposal pipeline with provenance
# verdicts recomputed at read time, and the PROPOSAL lanes. Reading it
# changes nothing; deleting nothing loses nothing; the only write in
# the area is the pre-existing asset-review PATCH (D22: "operate" means
# the human side of the loop only - EM never launches agents).

_tmpdir = tempfile.mkdtemp(prefix="em_opsview_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'ops.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_opsview_qdrant_")

from app import schemas  # noqa: E402
from app import crud  # noqa: E402
from app import connectors  # noqa: E402
from app import identity  # noqa: E402
from app import operations_view  # noqa: E402
from app import tier2  # noqa: E402
import test_support  # noqa: E402


def write_file(folder, name, text):
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def frontmatter(**claims):
    return "\n".join(["---"] + [f"{k}: {v}" for k, v in claims.items()]
                     + ["---", ""])


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


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Ops View", description="v1.4.1 gate", customer_id=customer.id),
        actor=officer)

    # Seed: one agent + binding; one PROPOSAL lane; a verified and a
    # forged proposal; one accepted DERIVED finding.
    agent = identity.create_principal(session, name="onboarding-diagnostic",
                                      display_name="Onboarding Diagnostic",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    package = db.AgentPackage(project_id=project.id, name="Ops Package",
                              package_hash="ph_" + "cd" * 30,
                              clearance_level="INTERNAL")
    session.add(package)
    session.commit()
    session.refresh(package)
    binding = db.ExpertAgentBinding(
        agent_package_id=package.id, agent_principal_id=agent.id,
        package_hash=package.package_hash, package_version="v3",
        principal_clearance_at_issue="INTERNAL",
        selected_provider="ANTHROPIC", selected_model_name="claude-opus-4-8",
        selection_evidence_json="{}",
        identity_fact_id=officer.fact(session).id)
    session.add(binding)
    session.commit()
    session.refresh(binding)

    lane_folder = tempfile.mkdtemp(prefix="em_opsview_lane_")
    lane = db.SourceConnector(project_id=project.id, name="Proposal Lane",
                              type="LOCAL_FOLDER", root_path=lane_folder,
                              include_extensions=".md", lane="PROPOSAL")
    session.add(lane)
    session.commit()
    session.refresh(lane)

    write_file(lane_folder, "finding-good.md",
               frontmatter(em_proposal=1,
                           agent_principal="onboarding-diagnostic",
                           binding_id=binding.id,
                           package_hash=package.package_hash)
               + "All mentors must sign the onboarding checklist before the first shift.\n")
    write_file(lane_folder, "finding-forged.md",
               frontmatter(em_proposal=1,
                           agent_principal="onboarding-diagnostic",
                           binding_id=999999,
                           package_hash=package.package_hash)
               + "All exit interviews must be archived in a Postgres database server.\n")
    run_scan(session, lane)

    reviewer = test_support.governed_actor(session, "GateReviewer")
    good_doc_assets = [a for a in session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="CANDIDATE").all()
        if "mentors" in (a.content or "").lower()]
    assert good_doc_assets, "the verified proposal must extract a candidate"
    accepted_asset = good_doc_assets[0]
    crud.update_knowledge_asset(
        session, accepted_asset.id,
        schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted at the gate")

    # ------------------------------------------------------------ Part 1
    # The projection: agents, pipeline, lanes - correct and complete.
    print("\n--- Part 1: the Operations projection ---")
    view = operations_view.build_operations(session, project.id)

    assert len(view["lanes"]) == 1
    lane_entry = view["lanes"][0]
    assert lane_entry["connector_id"] == lane.id
    assert lane_entry["last_scan"] is not None
    assert lane_entry["last_scan"]["status"] == "COMPLETED"

    assert len(view["pipeline"]) == 2
    by_file = {p["filename"]: p for p in view["pipeline"]}
    good = by_file["finding-good.md"]
    forged = by_file["finding-forged.md"]
    assert good["provenance"]["provenance_verified"] is True
    assert good["agent_principal"] == "onboarding-diagnostic"
    assert good["accepted_count"] == 1
    assert any(c["asset_id"] == accepted_asset.id
               and c["status"] == "APPROVED"
               and c["source_class"] == "DERIVED" for c in good["candidates"])
    assert forged["provenance"]["provenance_verified"] is False
    assert any("does not exist in governed records" in r
               for r in forged["provenance"]["reasons"])
    assert forged["held_count"] >= 1
    assert all(c["source_class"] == "DERIVED"
               for p in view["pipeline"] for c in p["candidates"])

    agent_entry = next(a for a in view["agents"]
                       if a["name"] == "onboarding-diagnostic")
    assert agent_entry["bindings"] == 1
    assert agent_entry["latest_binding"]["binding_id"] == binding.id
    assert agent_entry["latest_binding"]["package_hash"] == package.package_hash
    stats = agent_entry["proposals"]
    assert stats["proposal_documents"] == 2
    assert stats["accepted_derived"] == 1
    assert stats["unverified_documents"] == 1
    assert stats["held_candidates"] == view["summary"]["held_candidates"]

    summary = view["summary"]
    assert summary["proposal_documents"] == 2
    assert summary["accepted_derived"] == 1
    assert summary["unverified_documents"] == 1
    assert summary["lanes"] == 1 and summary["agents"] == 1
    print(f"Part 1 passed: 1 lane, 2 pipeline documents (1 verified w/ "
          f"accepted DERIVED, 1 forged held), agent attributed with "
          f"binding {binding.id}.")

    # ------------------------------------------------------------ Part 2
    # Purity: reading the view is a pure projection - no writes, no
    # events, deterministic (D24).
    print("\n--- Part 2: the view is a pure projection (D24) ---")
    events_before = session.query(db.AuditEvent).count()
    again = operations_view.build_operations(session, project.id)
    assert again == view, "same facts -> identical projection"
    assert session.query(db.AuditEvent).count() == events_before, \
        "reading the Operations view must write nothing"
    print("Part 2 passed: deterministic, event-free reads.")

    # ------------------------------------------------------------ Part 3
    # The route: assets:read reads it; no write route exists in the area.
    print("\n--- Part 3: the governed route ---")
    from fastapi.testclient import TestClient
    from app import main as app_main
    with TestClient(app_main.app) as client:
        with db.SessionLocal() as boot:
            reader = identity.create_principal(
                boot, name="ops-reader", display_name="Ops Reader",
                kind="HUMAN", role="READ_ONLY", created_by="test-suite")
            identity.set_password(boot, reader, "ops-reader-pass-1",
                                  actor="test-suite")
        r = client.post("/api/auth/login", json={"name": "ops-reader",
                                                 "password": "ops-reader-pass-1"})
        READER = {"Authorization": f"Bearer {r.json()['token']}"}
        r = client.get(f"/api/projects/{project.id}/operations", headers=READER)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["summary"]["proposal_documents"] == 2
        assert body["pipeline"][0]["provenance"]["claimed"] is not None
        r = client.get("/api/projects/999999/operations", headers=READER)
        assert r.status_code == 404
        # No mutation surface: the area's only write is the pre-existing
        # asset-review PATCH, which is not under /operations.
        r = client.post(f"/api/projects/{project.id}/operations",
                        json={}, headers=READER)
        assert r.status_code == 405, \
            "the Operations view must have no write method"
    print("Part 3 passed: assets:read reads it; unknown project 404; "
          "no write method exists.")

    session.close()
    print("\nAll v1.4.1 Operations-view checks passed: a pure computed "
          "projection of agents, pipeline, and lanes - provenance verdicts "
          "recomputed at read time, nothing written, nothing stored.")


if __name__ == "__main__":
    main()
