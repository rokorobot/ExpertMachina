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

# v1.4.0 WS1 gate suite - the proposal lane (D29/D30,
# docs/diagnostic-workbench-v1.4.md).
#
# The lane proof: a seeded proposal with valid provenance flows
# scan -> CANDIDATE (held: the sentinel live) -> human accept -> DERIVED
# fact whose provenance chain answers the opening question from governed
# records alone; a forged binding claim is a declared exception, held
# for review, never rejected by the engine; a proposal claiming PRIMARY
# is still DERIVED.

_tmpdir = tempfile.mkdtemp(prefix="em_lane_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'lane.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_lane_qdrant_")

from app import schemas  # noqa: E402
from app import crud  # noqa: E402
from app import connectors  # noqa: E402
from app import identity  # noqa: E402
from app import policy  # noqa: E402
from app import proposals  # noqa: E402
from app import tier2  # noqa: E402
from app import governance_inbox  # noqa: E402
import test_support  # noqa: E402

FINDING_SENTENCE = "The onboarding workflow stores mentor checklists in a Postgres database server."
FINDING_POLICY = "All new hires must sign the equipment liability waiver before badge issuance."
PRIMARY_SENTENCE = "The rostering platform stores shift plans in a MySQL database server."


def write_file(folder, name, text):
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
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


def frontmatter(**claims):
    lines = ["---"] + [f"{k}: {v}" for k, v in claims.items()] + ["---", ""]
    return "\n".join(lines)


def assets_of_doc(session, source_uri_fragment, connector_id):
    sd = session.query(db.SourceDocument).filter(
        db.SourceDocument.connector_id == connector_id,
        db.SourceDocument.source_uri.like(f"%{source_uri_fragment}%"),
    ).order_by(db.SourceDocument.id.desc()).first()
    assert sd is not None and sd.document_id is not None, \
        f"no ingested source row for {source_uri_fragment}"
    return sd.document_id, session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id == sd.document_id).all()


def exception_items(session, project_id):
    inbox = governance_inbox.build_inbox(session, project_id)
    return [i for i in inbox["items"] if i["type"] == "INGESTION_EXCEPTION"]


def main():
    db.init_db()

    # ------------------------------------------------------------ Part 1
    # The lane is a governed declaration on the existing connector route.
    print("\n--- Part 1: connector lane declaration (governed route) ---")
    from fastapi.testclient import TestClient
    from app import main as app_main
    proposal_folder = tempfile.mkdtemp(prefix="em_lane_proposals_")
    primary_folder = tempfile.mkdtemp(prefix="em_lane_primary_")
    with TestClient(app_main.app) as client:
        with db.SessionLocal() as boot:
            operator = identity.create_principal(
                boot, name="lane-operator", display_name="Lane Operator",
                kind="HUMAN", role="KNOWLEDGE_OPERATOR", created_by="test-suite")
            identity.set_password(boot, operator, "lane-operator-pass-1", actor="test-suite")
            admin = identity.create_principal(
                boot, name="lane-admin", display_name="Lane Admin",
                kind="HUMAN", role="ADMIN", created_by="test-suite")
            identity.set_password(boot, admin, "lane-admin-pass-1", actor="test-suite")
        r = client.post("/api/auth/login",
                        json={"name": "lane-admin", "password": "lane-admin-pass-1"})
        ADMIN = {"Authorization": f"Bearer {r.json()['token']}"}
        r = client.post("/api/auth/login",
                        json={"name": "lane-operator", "password": "lane-operator-pass-1"})
        OPERATOR = {"Authorization": f"Bearer {r.json()['token']}"}

        r = client.post("/api/projects",
                        json={"name": "Lane", "description": "", "customer_id": 1},
                        headers=ADMIN)
        assert r.status_code == 200, r.text
        project_id = r.json()["id"]

        r = client.post(f"/api/projects/{project_id}/connectors",
                        json={"name": "Proposal Lane", "root_path": proposal_folder,
                              "include_extensions": ".txt", "lane": "PROPOSAL"},
                        headers=OPERATOR)
        assert r.status_code == 200, r.text
        assert r.json()["lane"] == "PROPOSAL"
        proposal_connector_id = r.json()["id"]

        r = client.post(f"/api/projects/{project_id}/connectors",
                        json={"name": "Primary Share", "root_path": primary_folder,
                              "include_extensions": ".txt"},
                        headers=OPERATOR)
        assert r.status_code == 200, r.text
        assert r.json()["lane"] == "PRIMARY", "omitted lane must default PRIMARY"
        primary_connector_id = r.json()["id"]

        r = client.post(f"/api/projects/{project_id}/connectors",
                        json={"name": "Bad Lane", "root_path": proposal_folder,
                              "lane": "AGENT_EXPRESS"},
                        headers=OPERATOR)
        assert r.status_code == 400, "an unruled lane value must be refused"

    with db.SessionLocal() as check:
        created = [json.loads(e.details) for e in check.query(db.AuditEvent)
                   .filter_by(event_type="SOURCE_CONNECTOR_CREATED").all()]
        lanes = {d["name"]: d.get("lane") for d in created}
        assert lanes["Proposal Lane"] == "PROPOSAL" and lanes["Primary Share"] == "PRIMARY", \
            f"lane must be declared in the creation event: {lanes}"
    print("Part 1 passed: lane declared on the governed route, recorded in "
          "the ledger, unruled values refused, default PRIMARY.")

    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    proposal_connector = session.query(db.SourceConnector).get(proposal_connector_id)
    primary_connector = session.query(db.SourceConnector).get(primary_connector_id)

    # ------------------------------------------------------------ Part 2
    # Channel decides class - a claim of PRIMARY is still DERIVED.
    print("\n--- Part 2: channel decides class (D30) ---")
    write_file(primary_folder, "handbook.txt", PRIMARY_SENTENCE + "\n")
    write_file(proposal_folder, "finding-0001.txt",
               frontmatter(em_proposal=1, source_class="PRIMARY")
               + FINDING_SENTENCE + "\n")
    run_scan(session, primary_connector)
    run_scan(session, proposal_connector)

    _, primary_assets = assets_of_doc(session, "handbook.txt", primary_connector.id)
    assert primary_assets and all(a.source_class == "PRIMARY" for a in primary_assets)
    doc1_id, proposal_assets = assets_of_doc(session, "finding-0001.txt",
                                             proposal_connector.id)
    assert proposal_assets and all(a.source_class == "DERIVED" for a in proposal_assets), \
        [f"{a.id}:{a.source_class}" for a in proposal_assets]

    verdict = proposals.verify_provenance(session, doc1_id)
    assert verdict["provenance_claimed"] and not verdict["provenance_verified"]
    assert "source_class" in verdict["unrecognized_keys"], \
        "the class claim must be recorded as an unrecognized claim, never obeyed"
    assert verdict["claimed"].get("source_class") == "PRIMARY", \
        "claims are recorded verbatim (D12)"

    # Idempotent: a rescan converges on the same class.
    run_scan(session, proposal_connector)
    session.expire_all()
    _, proposal_assets = assets_of_doc(session, "finding-0001.txt", proposal_connector.id)
    assert all(a.source_class == "DERIVED" for a in proposal_assets)
    print(f"Part 2 passed: {len(proposal_assets)} proposal asset(s) DERIVED "
          f"despite the PRIMARY claim (claim recorded verbatim, never obeyed); "
          f"primary lane stays PRIMARY; rescans idempotent.")

    # ------------------------------------------------------------ Part 3
    # The verified chain: proposal -> human gate -> DERIVED fact whose
    # provenance answers the opening question from governed records.
    print("\n--- Part 3: verified synthesis provenance, end to end ---")
    agent = identity.create_principal(session, name="onboarding-diagnostic",
                                      display_name="Onboarding Diagnostic",
                                      kind="AGENT", created_by="test-suite")
    issuer = test_support.governed_actor(session, "BindingIssuer")
    package = db.AgentPackage(project_id=project_id, name="Onboarding Expert",
                              package_hash="ph_" + "a1" * 30,
                              clearance_level="INTERNAL")
    session.add(package)
    session.commit()
    session.refresh(package)
    binding = db.ExpertAgentBinding(
        agent_package_id=package.id, agent_principal_id=agent.id,
        package_hash=package.package_hash, package_version="v7",
        principal_clearance_at_issue="INTERNAL",
        selected_provider="ANTHROPIC", selected_model_name="claude-opus-4-8",
        selection_evidence_json="{}",
        identity_fact_id=issuer.fact(session).id)
    session.add(binding)
    session.commit()
    session.refresh(binding)

    cited = ",".join(str(a.id) for a in primary_assets)
    write_file(proposal_folder, "finding-0002.txt",
               frontmatter(em_proposal=1,
                           agent_principal="onboarding-diagnostic",
                           binding_id=binding.id,
                           package_hash=package.package_hash,
                           workbench="onboarding-diagnostic",
                           cited_assets=cited)
               + FINDING_POLICY + "\n")
    run_scan(session, proposal_connector)
    doc2_id, finding_assets = assets_of_doc(session, "finding-0002.txt",
                                            proposal_connector.id)
    assert finding_assets and all(a.source_class == "DERIVED" for a in finding_assets)
    assert all(a.status == "CANDIDATE" for a in finding_assets), \
        "proposal candidates hold for the human gate"

    verdict = proposals.verify_provenance(session, doc2_id)
    assert verdict["provenance_verified"], verdict["reasons"]
    assert verdict["verified"]["binding_id"] == binding.id
    assert verdict["verified"]["agent_principal"] == "onboarding-diagnostic"
    assert verdict["cited_assets"]["missing"] == []

    items = exception_items(session, project_id)
    awaiting = [i for i in items if i["classification"] == "PROPOSAL_AWAITING_GATE"
                and i["asset_id"] in {a.id for a in finding_assets}]
    assert awaiting, "verified proposals must surface as awaiting the gate"
    assert all(i["severity"] == "LOW" and i["provenance_verified"] for i in awaiting)
    assert "never auto-approved" in awaiting[0]["reason"], \
        "the reason must state the constitutional hold, not a coverage gap"

    # The human gate: acceptance quotes the recomputed verified provenance.
    target = finding_assets[0]
    reviewer = test_support.governed_actor(session, "GateReviewer")
    crud.update_knowledge_asset(
        session, target.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted the finding at the gate")
    session.refresh(target)
    assert target.status == "APPROVED" and target.source_class == "DERIVED"

    event = session.query(db.AuditEvent).filter_by(
        event_type="ASSET_APPROVED", target_id=str(target.id)).order_by(
        db.AuditEvent.id.desc()).first()
    details = json.loads(event.details)
    prov = details["synthesis_provenance"]
    # THE OPENING QUESTION, answered from the approval event + governed
    # records alone: which agent, which binding, which package hash,
    # citing what - and which human accepted.
    assert details["source_class"] == "DERIVED"
    assert prov["provenance_verified"] is True
    assert prov["claimed"]["agent_principal"] == "onboarding-diagnostic", \
        "claims quoted verbatim"
    assert prov["verified"]["binding_id"] == binding.id
    assert prov["verified"]["package_hash"] == package.package_hash
    assert prov["cited_assets"]["found"] == sorted(a.id for a in primary_assets)
    accepting_fact = session.query(db.IdentityFact).filter_by(
        id=event.identity_fact_id).first()
    assert accepting_fact is not None and accepting_fact.principal_name == "GateReviewer"
    review_rows = [r for r in target.reviews if not (r.approver or "").startswith("policy:")]
    assert review_rows, "the accepting human leaves a review row"
    # The accepted item leaves the inbox (no dismiss - facts changed).
    remaining = {i["asset_id"] for i in exception_items(session, project_id)}
    assert target.id not in remaining
    print(f"Part 3 passed: asset {target.id} is an APPROVED DERIVED fact; the "
          f"approval event alone names agent, binding {binding.id}, package "
          f"hash, {len(prov['cited_assets']['found'])} cited assets, and the "
          f"accepting human's identity fact.")

    # ------------------------------------------------------------ Part 4
    # Forged provenance: four postures, each a declared MEDIUM exception.
    print("\n--- Part 4: forged provenance is held and declared ---")
    other_agent = identity.create_principal(session, name="other-agent",
                                            display_name="Other Agent",
                                            kind="AGENT", created_by="test-suite")
    postures = {
        "finding-forged-binding.txt": frontmatter(
            em_proposal=1, agent_principal="onboarding-diagnostic",
            binding_id=999999, package_hash=package.package_hash),
        "finding-wrong-principal.txt": frontmatter(
            em_proposal=1, agent_principal="other-agent",
            binding_id=binding.id, package_hash=package.package_hash),
        "finding-wrong-hash.txt": frontmatter(
            em_proposal=1, agent_principal="onboarding-diagnostic",
            binding_id=binding.id, package_hash="ph_" + "ff" * 30),
        "finding-bare.txt": "",  # no frontmatter: nothing claimed
    }
    for i, (name, fm) in enumerate(postures.items()):
        write_file(proposal_folder, name,
                   fm + f"The audit archive {i} stores retention logs in a "
                        f"SQLite database server.\n")
    run_scan(session, proposal_connector)

    expected_reason_fragment = {
        "finding-forged-binding.txt": "does not exist in governed records",
        "finding-wrong-principal.txt": "belongs to principal",
        "finding-wrong-hash.txt": "does not match binding",
        "finding-bare.txt": "no provenance claimed",
    }
    items = exception_items(session, project_id)
    held_asset_ids = []
    for name, fragment in expected_reason_fragment.items():
        doc_id, doc_assets = assets_of_doc(session, name, proposal_connector.id)
        assert doc_assets and all(a.source_class == "DERIVED" for a in doc_assets)
        verdict = proposals.verify_provenance(session, doc_id)
        assert not verdict["provenance_verified"]
        assert any(fragment in r for r in verdict["reasons"]), \
            f"{name}: {fragment!r} not among {verdict['reasons']}"
        doc_items = [x for x in items if x["asset_id"] in {a.id for a in doc_assets}]
        assert doc_items and all(
            x["classification"] == "PROPOSAL_PROVENANCE_UNVERIFIED"
            and x["severity"] == "MEDIUM" for x in doc_items), \
            f"{name}: {[x['classification'] for x in doc_items]}"
        assert all("held for review" in x["reason"].lower()
                   and "the human gate decides" in x["reason"].lower()
                   for x in doc_items), \
            "the language ruling: held for review, the human gate decides"
        held_asset_ids.extend(a.id for a in doc_assets)

    # The human gate stays open even for unverified provenance - humans
    # refuse content, engines only refuse to approve. The acceptance
    # records the failed verification honestly.
    unverified_target = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.id.in_(held_asset_ids)).first()
    crud.update_knowledge_asset(
        session, unverified_target.id,
        schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="accepted despite unverified provenance")
    event = session.query(db.AuditEvent).filter_by(
        event_type="ASSET_APPROVED", target_id=str(unverified_target.id)).order_by(
        db.AuditEvent.id.desc()).first()
    prov = json.loads(event.details)["synthesis_provenance"]
    assert prov["provenance_verified"] is False, \
        "an acceptance of unverified provenance must say so, indefinitely"
    print(f"Part 4 passed: 4 forged/bare postures held as MEDIUM declared "
          f"exceptions with named reasons; the human gate stays open and "
          f"records the failed verification honestly.")

    # ------------------------------------------------------------ Part 5
    # The valve on this corpus: a global permissive policy approves the
    # primary lane and cannot touch the proposal lane (the guard owns
    # the full sentinel; this proves it live on WS1's machinery).
    print("\n--- Part 5: the valve holds on the lane's own corpus ---")
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add(db.ApprovalPolicy(project_id=project_id, name="everything",
                                  asset_types_json=all_types, enabled=True))
    session.commit()
    write_file(primary_folder, "handbook-2.txt",
               "The badge printer stores access codes in a Redis database server.\n")
    write_file(proposal_folder, "finding-0003.txt",
               frontmatter(em_proposal=1, agent_principal="onboarding-diagnostic",
                           binding_id=binding.id, package_hash=package.package_hash)
               + "The exit process stores clearance receipts in an Oracle database server.\n")
    run_scan(session, primary_connector)
    run_scan(session, proposal_connector)

    _, new_primary = assets_of_doc(session, "handbook-2.txt", primary_connector.id)
    assert any(a.status == "APPROVED" for a in new_primary), \
        "the permissive policy must auto-approve the PRIMARY lane"
    _, new_proposal = assets_of_doc(session, "finding-0003.txt", proposal_connector.id)
    assert all(a.status == "CANDIDATE" for a in new_proposal), \
        "D29 violation: a policy touched the proposal lane"
    declared = set()
    for e in session.query(db.AuditEvent).filter_by(
            event_type="POLICY_AUTOAPPROVAL_COMPLETED").all():
        declared.update(json.loads(e.details).get("proposal_lane_held_ids", []))
    assert {a.id for a in new_proposal} <= declared, "the hold must be declared"
    print(f"Part 5 passed: primary auto-approved, {len(new_proposal)} proposal "
          f"candidate(s) held and declared under the same global policy.")

    session.close()
    print("\nAll v1.4.0 WS1 proposal-lane checks passed: lane declared on the "
          "governed route, class channel-decided (claims recorded, never "
          "obeyed), synthesis provenance verified against governed records "
          "and quoted verbatim at the human gate, forged claims held as "
          "declared exceptions, the valve live on the lane's own corpus.")


if __name__ == "__main__":
    main()
