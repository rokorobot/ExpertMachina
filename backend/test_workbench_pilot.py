import json
import os
import subprocess
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_pilot_packages_")

# The guard is imported FIRST (its import overrides db.engine to its own
# temp store; this suite overrides again below and wins) so its
# workbench door-sweep checker can run here against the real modules -
# the WS3 gate proof rides the same checker CI enforces permanently.
import test_agent_authorship_guard as guard  # noqa: E402

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

# v1.4.0 WS3 gate suite - the workbench pilot + vault skeleton
# (D29/D30/D22, docs/diagnostic-workbench-v1.4.md).
#
# The diagnosis proof: the reference consumer produces an evidence-backed
# diagnosis from a seeded corpus deterministically in CI - every finding
# cites governed asset ids it consumed - and writes it to /08_proposals
# with valid frontmatter; the runner's imports pass the Guard 5 door
# sweep; the runner at AGENT clearance cannot read above its tier; the
# proposal is ingestible through the return path and holds for the gate.

_tmpdir = tempfile.mkdtemp(prefix="em_pilot_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'pilot.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_pilot_qdrant_")

from app import schemas  # noqa: E402
from app import crud  # noqa: E402
from app import connectors  # noqa: E402
from app import identity  # noqa: E402
from app import policy  # noqa: E402
from app import proposals  # noqa: E402
from app import tier2  # noqa: E402
from app import package_builder  # noqa: E402
from app import package_consumer  # noqa: E402
from app import mcp_gateway  # noqa: E402
import test_support  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
from workbench import onboarding_diagnostic as wb  # noqa: E402

CORPUS = {
    "systems.txt": "The onboarding platform stores training records in a PostgreSQL database server.",
    "policy.txt": "All new hires must complete safety training before badge access is granted.",
    "restricted.txt": "The compensation platform stores TOPSECRET-MARKER salary bands in an Oracle database server.",
}
PROPOSED_SENTENCE = ("All new contractors must complete mentor onboarding "
                     "before badge issuance.")


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


def vault_files(vault_dir):
    found = set()
    for root, _dirs, files in os.walk(vault_dir):
        for name in files:
            found.add(os.path.relpath(os.path.join(root, name), vault_dir)
                      .replace(os.sep, "/"))
    return found


class InProcessGraphClient:
    """The CI substitute for the stdio transport: the SAME gateway
    functions, the SAME EM_AGENT_TOKEN resolution, the SAME registry
    clearance and audited composition - minus the subprocess. The stdio
    transport itself (wb.StdioMcpGraphClient) is the real-run door,
    exercised at the WS4 honest slot."""

    def get_domain_subgraph(self, project_id, domain_prefix):
        session = db.SessionLocal()
        try:
            return mcp_gateway.get_domain_subgraph(project_id, domain_prefix,
                                                   session=session)
        finally:
            session.close()


def deterministic_synthesizer(package_path, questions):
    """The injectable seam's CI side: findings composed from the
    consumer's own package-local retrieval - deterministic, no LLM,
    every finding citing exactly the evidence retrieval offered."""
    package = package_consumer.load_package(package_path)
    findings = []
    for i, question in enumerate(questions):
        retrieval = package_consumer.retrieve(package, question, top_k=3)
        selected = retrieval["selected"]
        names = ", ".join(e["name"] for e in selected) or "no governed evidence"
        text = f"Evidence review for onboarding: {names}."
        if i == 0:
            text += f" Proposed knowledge: {PROPOSED_SENTENCE}"
        findings.append({
            "question": question,
            "finding": text,
            "cited_asset_ids": [e["asset_id"] for e in selected],
        })
    return findings


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Pilot", description="WS3 gate", customer_id=customer.id),
        actor=officer)

    # ------------------------------------------------------------ Part 1
    # The vault skeleton, bootstrapped by the shipped script - idempotent,
    # 01-06 deliberately absent.
    print("\n--- Part 1: vault skeleton (bootstrap script) ---")
    vault_dir = tempfile.mkdtemp(prefix="em_pilot_vault_")
    bootstrap = os.path.join(REPO_DIR, "vault", "bootstrap.py")
    for _ in range(2):  # idempotent
        result = subprocess.run([sys.executable, bootstrap,
                                 "--vault-dir", vault_dir],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    entries = sorted(os.listdir(vault_dir))
    assert entries == ["00_system", "07_agent_workspaces", "08_proposals"], entries
    contract_path = os.path.join(vault_dir, "00_system", "agent-contract.md")
    assert os.path.isfile(contract_path)
    with open(contract_path, encoding="utf-8") as f:
        contract = f.read()
    assert "One-Way Valve" in contract and "08_proposals" in contract
    assert not any(e.startswith(("01", "02", "03", "04", "05", "06"))
                   for e in entries), "folders 01-06 are reserved for v1.5"
    print("Part 1 passed: skeleton created idempotently; the contract "
          "deployed; 01-06 honestly absent.")

    # ------------------------------------------------------------ Part 2
    # The Guard 5 door sweep, run here against the real workbench modules.
    print("\n--- Part 2: the workbench passes the door sweep ---")
    swept = 0
    for root, _dirs, files in os.walk(os.path.join(REPO_DIR, "workbench")):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            with open(path, "r", encoding="utf-8") as f:
                violations = guard.workbench_import_violations(
                    os.path.relpath(path, REPO_DIR).replace(os.sep, "/"),
                    f.read())
            assert not violations, "\n".join(violations)
            swept += 1
    assert swept >= 2, "the workbench package must exist and be swept"
    print(f"Part 2 passed: {swept} workbench module(s) inside the ruled "
          f"doors (stdlib + app.package_consumer + app.llm + mcp).")

    # ------------------------------------------------------------ Part 3
    # Seed the corpus through the real pipeline; compile the package.
    print("\n--- Part 3: corpus in, package compiled ---")
    corpus_folder = tempfile.mkdtemp(prefix="em_pilot_corpus_")
    primary = db.SourceConnector(project_id=project.id, name="Onboarding Docs",
                                 type="LOCAL_FOLDER", root_path=corpus_folder,
                                 include_extensions=".txt")
    session.add(primary)
    session.commit()
    session.refresh(primary)
    for name, sentence in CORPUS.items():
        write_file(corpus_folder, name, sentence)
    run_scan(session, primary)

    reviewer = test_support.governed_actor(session, "PilotReviewer")
    candidates = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.status == "CANDIDATE").order_by(db.KnowledgeAsset.id).all()
    assert candidates, "the corpus must extract candidates"
    for asset in candidates:
        crud.update_knowledge_asset(
            session, asset.id, schemas.KnowledgeAssetUpdate(
                status="APPROVED", domain="onboarding"),
            actor=reviewer, review_notes="pilot corpus approval")
    approved = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.status == "APPROVED").order_by(db.KnowledgeAsset.id).all()
    restricted = next(a for a in approved if "TOPSECRET-MARKER" in a.content)
    restricted.access_level = "EXECUTIVE"
    session.commit()
    internal_ids = sorted(a.id for a in approved if a.id != restricted.id)

    model = db.ExpertModel(project_id=project.id, name="Onboarding Expert",
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    session.add(model)
    session.commit()
    session.refresh(model)
    package_row = db.AgentPackage(project_id=project.id,
                                  expert_model_id=model.id,
                                  name="Onboarding Package",
                                  clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    package_builder.build_package(session, package_row)
    loaded = package_consumer.load_package(package_row.file_path)
    packaged_ids = {e["asset_id"] for e in loaded["knowledge"]}
    assert restricted.id not in packaged_ids, \
        "the INTERNAL package must exclude the EXECUTIVE asset"

    agent = identity.create_principal(session, name="onboarding-diagnostic",
                                      display_name="Onboarding Diagnostic",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _cred = identity.issue_token(session, agent, kind="API_TOKEN",
                                              label="pilot", actor="test-suite")
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
    print(f"Part 3 passed: {len(approved)} approved assets "
          f"({len(internal_ids)} INTERNAL + 1 EXECUTIVE), package compiled "
          f"with the exclusion, agent bound.")

    # ------------------------------------------------------------ Part 4
    # THE DIAGNOSIS: deterministic, evidence-backed, vault-confined.
    print("\n--- Part 4: the diagnosis (deterministic, evidence-backed) ---")
    baseline = vault_files(vault_dir)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        first_path = wb.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="onboarding-diagnostic", binding_id=binding.id,
            domain_prefix="onboarding",
            synthesizer=deterministic_synthesizer,
            graph_client=InProcessGraphClient())
        with open(first_path, encoding="utf-8") as f:
            first_content = f.read()
        second_path = wb.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="onboarding-diagnostic", binding_id=binding.id,
            domain_prefix="onboarding",
            synthesizer=deterministic_synthesizer,
            graph_client=InProcessGraphClient())
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    assert second_path == first_path, "same corpus -> same proposal file"
    with open(second_path, encoding="utf-8") as f:
        assert f.read() == first_content, "same corpus -> byte-identical proposal"

    rel = os.path.relpath(first_path, vault_dir).replace(os.sep, "/")
    assert rel.startswith("08_proposals/"), rel
    new_files = vault_files(vault_dir) - baseline
    assert new_files == {rel}, \
        f"the workbench must write ONLY its proposal: {new_files}"

    parsed = proposals.parse_frontmatter(first_content)
    assert parsed["claimed"] and not parsed["problems"]
    assert parsed["claims"]["agent_principal"] == "onboarding-diagnostic"
    assert int(parsed["claims"]["binding_id"]) == binding.id
    assert parsed["claims"]["package_hash"] == package_row.package_hash
    cited = [int(t) for t in parsed["claims"]["cited_assets"].split(",") if t]
    assert cited and set(cited) <= set(internal_ids), \
        "every citation names a governed INTERNAL asset the agent consumed"
    assert PROPOSED_SENTENCE in first_content, \
        "the synthesized finding is in the proposal body"
    print(f"Part 4 passed: byte-identical across runs, confined to "
          f"08_proposals, frontmatter valid, {len(cited)} governed citations.")

    # ------------------------------------------------------------ Part 5
    # Clearance at the door: nothing above the agent's tier reaches the
    # diagnosis - and the gateway's exclusions are declared IN it.
    print("\n--- Part 5: the agent's tier holds at both doors ---")
    assert "TOPSECRET-MARKER" not in first_content
    assert restricted.id not in cited
    assert "assets_above_clearance" in first_content, \
        "the declared exclusion travels into the proposal (D12 visible)"
    print("Part 5 passed: the EXECUTIVE asset is absent from citations and "
          "bytes; the exclusion is declared, not silent.")

    # ------------------------------------------------------------ Part 6
    # The return path: the proposal is ingestible, DERIVED, and held
    # under a live permissive policy.
    print("\n--- Part 6: the return path holds the proposal ---")
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add(db.ApprovalPolicy(project_id=project.id, name="everything",
                                  asset_types_json=all_types, enabled=True))
    lane = db.SourceConnector(project_id=project.id, name="Proposal Lane",
                              type="LOCAL_FOLDER",
                              root_path=os.path.join(vault_dir, "08_proposals"),
                              include_extensions=".md", lane="PROPOSAL")
    session.add(lane)
    session.commit()
    session.refresh(lane)
    run_scan(session, lane)

    lane_doc_ids = policy.proposal_lane_document_ids(
        session, [d.id for d in session.query(db.Document).filter_by(
            project_id=project.id).all()])
    assert lane_doc_ids, "the proposal must have been ingested"
    proposal_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_doc_ids)).all()
    assert proposal_assets, "the proposal must extract candidates"
    assert all(a.status == "CANDIDATE" and a.source_class == "DERIVED"
               for a in proposal_assets), \
        [(a.id, a.status, a.source_class) for a in proposal_assets]
    verdict = proposals.verify_provenance(session, sorted(lane_doc_ids)[0])
    assert verdict["provenance_verified"], verdict["reasons"]
    assert verdict["verified"]["binding_id"] == binding.id
    assert verdict["cited_assets"]["missing"] == []
    print(f"Part 6 passed: {len(proposal_assets)} DERIVED candidate(s) held "
          f"under a live permissive policy; provenance verified against the "
          f"governed binding.")

    session.close()
    print("\nAll v1.4.0 WS3 workbench-pilot checks passed: the vault skeleton "
          "shipped, the reference consumer stays inside its doors, the "
          "diagnosis is deterministic and evidence-backed at the agent's "
          "clearance, and its proposal re-enters only through the lane, "
          "held for the human gate.")


if __name__ == "__main__":
    main()
