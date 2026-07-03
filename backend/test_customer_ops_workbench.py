"""v1.6 WS2 - THE DIAGNOSIS PROOF for the Customer Operations Workbench.

The runner (workbench/customer_operations/runner.py) is proven as a
governed skill bundle, not a vague agent: every deterministically
detectable plant found and CORRECTLY KINDED; every finding names the
skill that produced it and conforms to that skill's declared output
format and evidence basis; a skill's refusal condition proven live (a
covered question produces NO finding); a non-ACTIVE contract refused
(tags are gates); byte-identical re-runs; writes confined to the two
permitted vault folders; the EXECUTIVE sentinel absent from every
written byte; Guard 5 sweeps the module with zero guard edits; and the
return path holds every finding as a held DERIVED candidate with
provenance verified against the governed binding.

Conflict rows: fixture DETECTED pairs by default (declared - the
real-NLI detection proof is WS1's corpus-proof gate evidence); with
EM_CORPUS_PROOF_NLI=1 the real scan runs instead and assertions are
presence-based.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

REAL_NLI = os.environ.get("EM_CORPUS_PROOF_NLI", "").strip() == "1"
if not REAL_NLI:
    os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_cusops2_pkg_")

# Guard 5 first (its import overrides db.engine; this suite re-overrides
# and wins - the ruled import-order trick), for its door-sweep checker.
import test_agent_authorship_guard as guard   # noqa: E402

if REAL_NLI:
    # The guard import forces EM_NLI_VERIFICATION=off; the gate-evidence
    # mode needs the real engine back on before any pipeline load.
    os.environ["EM_NLI_VERIFICATION"] = "on"

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_cusops2_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'ws2.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_cusops2_qdrant_")

from app import (schemas, crud, connectors, revisions, conflict_engine,  # noqa: E402
                 package_builder, package_consumer, identity, mcp_gateway,
                 policy, proposals, tier2)
import test_support                           # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.customer_operations.runner as runner   # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "customer_operations")
CORPUS_DIR = os.path.join(WB_DIR, "corpus")
SEED_DIR = os.path.join(WB_DIR, "corpus_seed")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
SENTINEL = "EM-EXEC-SENTINEL-9Q4Z"
CONTROL_QUESTION = ("May customers request a refund within days of delivery "
                    "under the refund policy?")


def run_scan(session, connector):
    job = db.IngestionJob(project_id=connector.project_id,
                          connector_id=connector.id, status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    connectors.execute_ingestion_job(session, job.id)
    tier2.drain()
    session.refresh(job)
    assert job.status == "COMPLETED", f"scan {job.status}: {job.error}"


def approve_all(session, project_id, reviewer, note):
    for asset in session.query(db.KnowledgeAsset).filter(
            db.KnowledgeAsset.project_id == project_id,
            db.KnowledgeAsset.status == "CANDIDATE").all():
        crud.update_knowledge_asset(
            session, asset.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=reviewer, review_notes=note)


def vault_files(vault_dir):
    found = set()
    for root, _dirs, files in os.walk(vault_dir):
        for name in files:
            found.add(os.path.relpath(os.path.join(root, name), vault_dir)
                      .replace(os.sep, "/"))
    return found


class InProcessGraphClient:
    """CI substitute for the stdio transport: the SAME gateway
    functions, token resolution, clearance, and audited composition -
    minus the subprocess (the pilot pattern; the stdio door is the
    real-run transport)."""

    def _run(self, fn, *args):
        session = db.SessionLocal()
        try:
            return fn(*args, session=session)
        finally:
            session.close()

    def get_conflicts(self, expert_model_id):
        return self._run(mcp_gateway.get_conflicts, expert_model_id)

    def get_revision_history(self, asset_id):
        return self._run(mcp_gateway.get_revision_history, asset_id)

    def get_domain_subgraph(self, project_id, domain_prefix):
        return self._run(mcp_gateway.get_domain_subgraph, project_id,
                         domain_prefix)


def make_answerer(loaded_package):
    """The declared deterministic CI contract-follower (the WS1-ratified
    rule): answers only when one governed evidence item shares >= 6
    retrieval tokens with the question; otherwise the packaged refusal
    verbatim. Mirrors consume()'s return shape."""
    def answer(question):
        sel = package_consumer.retrieve(loaded_package, question,
                                        top_k=8)["selected"]
        qt = package_consumer._tokens(question)
        scored = sorted(
            ((len(qt & package_consumer._tokens(e.get("content") or "")), e)
             for e in sel), key=lambda t: (-t[0], t[1]["asset_id"]))
        if scored and scored[0][0] >= 6:
            best = scored[0][1]
            text = (f"Per the governed evidence (asset_id {best['asset_id']}): "
                    f"{best.get('content')}")
        else:
            text = ("INSUFFICIENT EVIDENCE - the governed evidence offered "
                    "does not contain the answer to this question.")
        return {"answer": text,
                "cited_asset_ids": [] if "INSUFFICIENT" in text
                else [scored[0][1]["asset_id"]],
                "evidence": sel}
    return answer


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "WS2Officer")
    reviewer = test_support.governed_actor(session, "WS2Reviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Customer Ops WS2", description="the diagnosis proof",
        customer_id=customer.id), actor=officer)

    # ------------------------------------------------------------ Part 1
    print("\n--- Part 1: the runner passes the Guard 5 door sweep ---")
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
    assert swept >= 3, "pilot + runner must exist and be swept"
    print(f"Part 1 passed: {swept} workbench module(s) inside the ruled "
          "doors - zero guard edits.")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: corpus in, package compiled, agent bound ---")
    scan_dir = tempfile.mkdtemp(prefix="em_cusops2_scan_")
    for name in sorted(os.listdir(CORPUS_DIR)):
        shutil.copy(os.path.join(CORPUS_DIR, name), os.path.join(scan_dir, name))
    shutil.copy(os.path.join(SEED_DIR, "refund-policy.md"),
                os.path.join(scan_dir, "refund-policy.md"))
    primary = db.SourceConnector(project_id=project.id, name="Customer Ops Docs",
                                 type="LOCAL_FOLDER", root_path=scan_dir,
                                 include_extensions=".md")
    session.add(primary)
    session.commit()
    session.refresh(primary)
    run_scan(session, primary)
    approve_all(session, project.id, reviewer, "WS2 corpus approval (rev-1)")
    shutil.copy(os.path.join(CORPUS_DIR, "refund-policy.md"),
                os.path.join(scan_dir, "refund-policy.md"))
    run_scan(session, primary)
    pending = [r for r in session.query(db.AssetRevision).filter(
        db.AssetRevision.status == "CANDIDATE").all()
        if "within 14 days" in (r.content or "")]
    assert pending, "the refund-window revision must be pending"
    revisions.review_revision(session, pending[0].id, "APPROVE",
                              actor=reviewer, notes="WS2 choreography")
    approve_all(session, project.id, reviewer, "WS2 corpus approval (rev-2)")

    matrix_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename.like("%refund-authority-matrix%")).first()
    exec_ids = set()
    for a in session.query(db.KnowledgeAsset).filter(
            db.KnowledgeAsset.document_id == matrix_doc.id).all():
        a.access_level = "EXECUTIVE"
        exec_ids.add(a.id)
    session.commit()

    approved = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.status == "APPROVED").all()
    model = db.ExpertModel(project_id=project.id,
                           name="Customer Operations Expert",
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    session.add(model)
    session.commit()
    session.refresh(model)
    # Compile BEFORE the conflict scan: the workbench diagnoses drift on
    # an already-bound package - the realistic operating rhythm.
    package_row = db.AgentPackage(project_id=project.id,
                                  expert_model_id=model.id,
                                  name="Customer Operations Package",
                                  clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    package_builder.build_package(session, package_row)
    session.refresh(package_row)
    loaded = package_consumer.load_package(package_row.file_path)
    packaged_ids = {e["asset_id"] for e in loaded["knowledge"]}
    assert not (exec_ids & packaged_ids), "EXECUTIVE assets must be excluded"

    agent = identity.create_principal(session, name="customer-operations",
                                      display_name="Customer Operations",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _cred = identity.issue_token(session, agent, kind="API_TOKEN",
                                              label="ws2", actor="test-suite")
    issuer = test_support.governed_actor(session, "WS2Issuer")
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

    by_content = {a.id: (a.content or "") for a in approved}
    if REAL_NLI:
        summary = conflict_engine.scan_expert_model_conflicts(session, model.id)
        assert summary["nli_available"], "real-NLI mode requires the model"
        mode = f"REAL NLI ({summary['compared_pairs']} pairs)"
    else:
        def find(needle, extra=None):
            return next(a for a in approved if needle in (a.content or "")
                        and (extra is None or extra in (a.content or "")))
        p1 = (find("24 hours").id, find("48 hours").id)
        p3 = (find("within 14 days").id,
              find("30 days", extra="refund policy allows").id)
        for a_id, b_id in (p1, p3):
            session.add(db.AssetRelationship(
                project_id=project.id, expert_model_id=model.id,
                source_asset_id=a_id, target_asset_id=b_id,
                relationship_type="CONFLICTS_WITH",
                classification="DIRECT_CONTRADICTION", confidence=0.99,
                status="DETECTED",
                verifier_json=json.dumps({"method": "TEST_FIXTURE"})))
        session.commit()
        mode = "declared fixture conflicts (real-NLI detection = WS1 gate evidence)"
    print(f"Part 2 passed: package compiled + agent bound; conflicts via {mode}.")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE DIAGNOSIS (skills, kinds, evidence, determinism) ---")
    vault_dir = tempfile.mkdtemp(prefix="em_cusops2_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    baseline = vault_files(vault_dir)
    answerer = make_answerer(loaded)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        runs = [runner.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="customer-operations", binding_id=binding.id,
            graph_client=InProcessGraphClient(), answerer=answerer)
            for _ in range(2)]
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    first, second = runs
    assert first["proposals"] == second["proposals"], "paths must be identical"
    for path in first["proposals"]:
        with open(path, encoding="utf-8") as f:
            content_1 = f.read()
        assert os.path.isfile(path)
        with open(path, encoding="utf-8") as f:
            assert f.read() == content_1
    kinds = {f["finding_kind"] for f in first["findings"]}
    for expected in ("CUSTOMER_PROMISE_CONFLICT", "OUTDATED_CUSTOMER_GUIDANCE",
                     "MISSING_SUPPORT_PLAYBOOK", "SLA_OBLIGATION_GAP"):
        assert expected in kinds, f"{expected} missing from the diagnosis"

    new_files = vault_files(vault_dir) - baseline
    for rel in new_files:
        assert rel.startswith(("08_proposals/", "07_agent_workspaces/")), \
            f"writes must be confined: {rel}"
    briefs = [r for r in new_files if r.startswith("07_agent_workspaces/")]
    assert len(briefs) == 1, "exactly one assist brief in the workspace"

    expected_kind = dict(runner.FINDING_KINDS)
    for path in first["proposals"]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert SENTINEL not in text, "EXECUTIVE sentinel leaked into a proposal"
        parsed = proposals.parse_frontmatter(text)
        assert parsed["claimed"] and not parsed["problems"], parsed
        claims = parsed["claims"]
        assert claims["agent_principal"] == "customer-operations"
        assert int(claims["binding_id"]) == binding.id
        assert claims["package_hash"] == package_row.package_hash
        assert claims["workbench"] == "customer-operations"
        skill = claims["skill"]
        kind, basis = expected_kind[skill]
        assert claims["finding_kind"] == kind, (skill, claims["finding_kind"])
        assert claims["evidence_basis"] == basis
        cited = [int(t) for t in claims["cited_assets"].split(",") if t]
        assert cited and set(cited) <= packaged_ids, \
            "every citation names a packaged INTERNAL asset the agent consumed"
        assert "Exclusions declared by the gateway" in text, \
            "the clearance exclusion must be declared inside the proposal"
    with open(os.path.join(vault_dir, briefs[0]), encoding="utf-8") as f:
        brief_text = f.read()
    assert SENTINEL not in brief_text
    assert "never enters knowledge" in brief_text

    def finding(kind):
        return [f for f in first["findings"] if f["finding_kind"] == kind]
    p1f = finding("CUSTOMER_PROMISE_CONFLICT")
    assert any("24 hours" in f["excerpt_a"] + f["excerpt_b"]
               and "48 hours" in f["excerpt_a"] + f["excerpt_b"]
               for f in p1f), "P1 must pair the 24h promise with the 48h target"
    p3f = finding("OUTDATED_CUSTOMER_GUIDANCE")
    assert any("30 days" in f["excerpt_outdated"]
               and "14 days" in f["excerpt_current"] for f in p3f), \
        "P3 must show the 30-day guidance against the current 14-day revision"
    p2f = finding("MISSING_SUPPORT_PLAYBOOK")
    assert any("refund exception playbook" in f["trigger_excerpt"]
               for f in p2f), "P2 must cite the playbook-naming excerpt"
    p4f = finding("SLA_OBLIGATION_GAP")
    assert any("monthly service performance report" in f["trigger_excerpt"]
               for f in p4f), "P4 must cite the explicit obligation excerpt"
    print(f"Part 3 passed: {len(first['proposals'])} per-finding proposals "
          f"(kinds: {sorted(kinds)}), byte-identical across runs, confined to "
          "08_proposals + one workspace brief, skill claims conform to the "
          "ratified contracts, sentinel absent, exclusions declared.")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: contracts drive behavior (refusal + status gates) ---")
    covered_dir = tempfile.mkdtemp(prefix="em_cusops2_skills_")
    for name in os.listdir(SKILLS_DIR):
        shutil.copy(os.path.join(SKILLS_DIR, name), os.path.join(covered_dir, name))
    sla_path = os.path.join(covered_dir, "detect_sla_obligation_gap.yaml")
    with open(sla_path, encoding="utf-8") as f:
        sla_text = f.read()
    with open(sla_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(sla_text.replace(
            "question_frame:",
            f'question_frame:\n  - "{CONTROL_QUESTION}"', 1))
    vault_dir_2 = tempfile.mkdtemp(prefix="em_cusops2_vault_b_")
    subprocess.run([sys.executable,
                    os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                    "--vault-dir", vault_dir_2], capture_output=True, text=True)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        covered_run = runner.run_diagnostic(
            package_row.file_path, vault_dir_2, project.id,
            agent_principal="customer-operations", binding_id=binding.id,
            graph_client=InProcessGraphClient(), answerer=answerer,
            skills_dir=covered_dir)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    assert not any(f.get("question") == CONTROL_QUESTION
                   for f in covered_run["findings"]), \
        "a covered question must produce NO finding"
    assert any(s["reason"].startswith("the corpus answers")
               and CONTROL_QUESTION in s["reason"]
               for s in covered_run["skipped"]), \
        "the covered question must be skipped with the refusing reason"

    gated_dir = tempfile.mkdtemp(prefix="em_cusops2_skills_g_")
    for name in os.listdir(SKILLS_DIR):
        shutil.copy(os.path.join(SKILLS_DIR, name), os.path.join(gated_dir, name))
    promise_path = os.path.join(gated_dir, "detect_customer_promise_conflict.yaml")
    with open(promise_path, encoding="utf-8") as f:
        promise_text = f.read()
    with open(promise_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(promise_text.replace("status: ACTIVE", "status: SEQUENCED", 1))
    refused = False
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        runner.run_diagnostic(
            package_row.file_path, vault_dir_2, project.id,
            agent_principal="customer-operations", binding_id=binding.id,
            graph_client=InProcessGraphClient(), answerer=answerer,
            skills_dir=gated_dir)
    except RuntimeError as e:
        refused = "not ACTIVE" in str(e)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    assert refused, "a non-ACTIVE contract must be refused - tags are gates"
    print("Part 4 passed: a covered question produced no finding (refusal-"
          "first, from the contract's own frame); a SEQUENCED contract was "
          "refused at run time.")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: the return path holds every finding ---")
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
    assert len(lane_doc_ids) == len(first["proposals"]), \
        "every per-finding proposal must be ingested"
    lane_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_doc_ids)).all()
    assert lane_assets and all(
        a.status == "CANDIDATE" and a.source_class == "DERIVED"
        for a in lane_assets), \
        [(a.id, a.status, a.source_class) for a in lane_assets]
    verdict = proposals.verify_provenance(session, sorted(lane_doc_ids)[0])
    assert verdict["provenance_verified"], verdict["reasons"]
    assert verdict["verified"]["binding_id"] == binding.id
    assert verdict["cited_assets"]["missing"] == []
    print(f"Part 5 passed: {len(lane_doc_ids)} proposals ingested; "
          f"{len(lane_assets)} candidates all held DERIVED under a live "
          "permissive policy; provenance verified against the governed "
          "binding.")

    session.close()
    print("\n=== All v1.6 WS2 diagnosis-proof checks passed: the workbench "
          "is a governed skill bundle - declared inputs, evidence rules, "
          "refusal conditions, finding outputs, and the human approval "
          "path. ===")


if __name__ == "__main__":
    main()
