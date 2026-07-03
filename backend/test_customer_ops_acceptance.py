"""v1.6 WS3 - THE MILESTONE GATE for the Customer Operations Workbench.

The full commercial loop, once, end to end: the ratified corpus enters
through the real governed pipeline -> PRIMARY facts approved by a human
(with the revision choreography) -> an INTERNAL package is compiled and
bound to a real AGENT principal -> the workbench diagnoses through the
doors, honoring the five ratified skill contracts -> one proposal per
finding lands in /08_proposals -> the valve holds every candidate
DERIVED under a global permissive Tier-1 policy AND a live
approve-everything Tier-2 engine -> a human accepts one finding per
kind -> APPROVED DERIVED facts with verified synthesis provenance ->
the vault re-render shows each accepted finding as a marked DERIVED
note, visibly non-canonical -> closing lines: the ledger alone proves
no agent principal wrote canonical facts, every APPROVED DERIVED fact
has a human review, the clearance sweep is clean, and the D24 snapshot
stands at exactly 28 tables / 305 columns.

Conflict rows: declared fixture DETECTED pairs by default (the real-NLI
detection proof is the WS1 corpus-proof gate evidence);
EM_CORPUS_PROOF_NLI=1 runs the real scan instead.

THE COMMERCIAL VERDICT is not automated: the user reads the rendered
diagnosis as the business reader at this gate. The real-model honest
slot is reported at the end - attempted only when a real provider key
exists, pending honestly otherwise.
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
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_coacc_pkg_")
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_coacc_render_")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_coacc_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'accept.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_coacc_qdrant_")

from app import (schemas, crud, connectors, revisions, conflict_engine,  # noqa: E402
                 package_builder, package_consumer, identity, mcp_gateway,
                 policy, proposals, tier2)
from app.projections import engine as projection_engine   # noqa: E402
import test_support                           # noqa: E402
import test_workbench_projection              # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.customer_operations.runner as runner   # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "customer_operations")
CORPUS_DIR = os.path.join(WB_DIR, "corpus")
SEED_DIR = os.path.join(WB_DIR, "corpus_seed")
SENTINEL = "EM-EXEC-SENTINEL-9Q4Z"
KIND_TO_SKILL = {kind: skill for skill, (kind, _b) in runner.FINDING_KINDS.items()}


class ApproveEverythingVerifier:
    identity = {"method": "GUARD_APPROVE_EVERYTHING",
                "note": "customer-ops acceptance lane-sentinel seam"}

    def check(self, candidate, corpus):
        return {"pairs_checked": len(corpus), "pairs_dropped": 0,
                "contradictions": []}


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


def approve_all(session, project_id, reviewer, note, domain=None):
    count = 0
    for asset in session.query(db.KnowledgeAsset).filter(
            db.KnowledgeAsset.project_id == project_id,
            db.KnowledgeAsset.status == "CANDIDATE").all():
        crud.update_knowledge_asset(
            session, asset.id,
            schemas.KnowledgeAssetUpdate(status="APPROVED", domain=domain),
            actor=reviewer, review_notes=note)
        count += 1
    return count


class InProcessGraphClient:
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
        return {"answer": text, "cited_asset_ids": [],
                "evidence": sel}
    return answer


def main():
    db.init_db()
    tier2.verifier_factory = ApproveEverythingVerifier
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "AcceptanceOfficer")
    reviewer = test_support.governed_actor(session, "AcceptanceReviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Customer Operations", description="THE MILESTONE GATE",
        customer_id=customer.id), actor=officer)

    # ------------------------------------------------------- Stage 1
    print("\n--- Stage 1: the ratified corpus through the real pipeline ---")
    scan_dir = tempfile.mkdtemp(prefix="em_coacc_scan_")
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
    approve_all(session, project.id, reviewer, "acceptance: rev-1 corpus",
                domain="customer_operations")
    shutil.copy(os.path.join(CORPUS_DIR, "refund-policy.md"),
                os.path.join(scan_dir, "refund-policy.md"))
    run_scan(session, primary)
    pending = [r for r in session.query(db.AssetRevision).filter(
        db.AssetRevision.status == "CANDIDATE").all()
        if "within 14 days" in (r.content or "")]
    assert pending, "the refund-window revision must be pending"
    revisions.review_revision(session, pending[0].id, "APPROVE",
                              actor=reviewer, notes="acceptance choreography")
    approve_all(session, project.id, reviewer, "acceptance: rev-2 additions",
                domain="customer_operations")
    matrix_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename.like("%refund-authority-matrix%")).first()
    for a in session.query(db.KnowledgeAsset).filter(
            db.KnowledgeAsset.document_id == matrix_doc.id).all():
        a.access_level = "EXECUTIVE"
    session.commit()
    approved = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.status == "APPROVED").all()
    print(f"Stage 1 passed: {len(approved)} PRIMARY facts approved by a human "
          "into the customer_operations domain; the superseded chain stands.")

    # ------------------------------------------------------- Stage 2
    print("\n--- Stage 2: package compiled, agent bound, conflicts scanned ---")
    model = db.ExpertModel(project_id=project.id,
                           name="Customer Operations Expert",
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    session.add(model)
    session.commit()
    session.refresh(model)
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
    agent = identity.create_principal(session, name="customer-operations",
                                      display_name="Customer Operations",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _cred = identity.issue_token(session, agent, kind="API_TOKEN",
                                              label="acceptance",
                                              actor="test-suite")
    issuer = test_support.governed_actor(session, "AcceptanceIssuer")
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
    if REAL_NLI:
        summary = conflict_engine.scan_expert_model_conflicts(session, model.id)
        assert summary["nli_available"], "real-NLI mode requires the model"
        mode = f"REAL NLI ({summary['compared_pairs']} pairs)"
    else:
        def find(needle, extra=None):
            return next(a for a in approved if needle in (a.content or "")
                        and (extra is None or extra in (a.content or "")))
        for a_id, b_id in ((find("24 hours").id, find("48 hours").id),
                           (find("within 14 days").id,
                            find("30 days", extra="refund policy allows").id)):
            session.add(db.AssetRelationship(
                project_id=project.id, expert_model_id=model.id,
                source_asset_id=a_id, target_asset_id=b_id,
                relationship_type="CONFLICTS_WITH",
                classification="DIRECT_CONTRADICTION", confidence=0.99,
                status="DETECTED",
                verifier_json=json.dumps({"method": "TEST_FIXTURE"})))
        session.commit()
        mode = "declared fixture conflicts (real-NLI = WS1 gate evidence)"
    print(f"Stage 2 passed: INTERNAL package + real AGENT binding; {mode}.")

    # ------------------------------------------------------- Stage 3
    print("\n--- Stage 3: THE DIAGNOSIS through the doors ---")
    vault_dir = tempfile.mkdtemp(prefix="em_coacc_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        diagnosis = runner.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="customer-operations", binding_id=binding.id,
            graph_client=InProcessGraphClient(),
            answerer=make_answerer(loaded))
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    kinds = {f["finding_kind"] for f in diagnosis["findings"]}
    assert set(KIND_TO_SKILL) <= kinds, f"kinds missing: {kinds}"
    artifact_dir = os.environ.get("EM_COMMERCIAL_ARTIFACT_DIR")
    if artifact_dir:
        # THE COMMERCIAL VERDICT export: copy the rendered diagnosis for
        # the business reader. An export of proposal documents - never a
        # promotion, never knowledge.
        os.makedirs(artifact_dir, exist_ok=True)
        for path in diagnosis["proposals"] + [diagnosis["brief"]]:
            shutil.copy(path, artifact_dir)
    print(f"Stage 3 passed: {len(diagnosis['proposals'])} per-finding "
          f"proposals across all four kinds, written to /08_proposals only.")

    # ------------------------------------------------------- Stage 4
    print("\n--- Stage 4: the valve holds at the milestone gate ---")
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add(db.ApprovalPolicy(project_id=project.id, name="everything",
                                  asset_types_json=all_types, enabled=True))
    session.add(db.ApprovalPolicy(project_id=project.id, name="everything-tier2",
                                  asset_types_json=all_types, enabled=True,
                                  engine_conditions_json=json.dumps(
                                      {"contradiction_check": "CLEAN_REQUIRED"})))
    session.commit()
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
    assert len(lane_doc_ids) == len(diagnosis["proposals"])
    lane_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_doc_ids)).all()
    assert lane_assets and all(
        a.status == "CANDIDATE" and a.source_class == "DERIVED"
        for a in lane_assets), "the lane sentinel must hold at the gate"
    print(f"Stage 4 passed: {len(lane_assets)} candidates all held DERIVED "
          "under a global permissive Tier-1 policy AND a live "
          "approve-everything Tier-2 engine - never auto-approved.")

    # ------------------------------------------------------- Stage 5
    print("\n--- Stage 5: a human accepts one finding per kind ---")
    docs_by_id = {d.id: d for d in session.query(db.Document).filter(
        db.Document.id.in_(lane_doc_ids)).all()}
    accepted = {}
    for kind, skill in sorted(KIND_TO_SKILL.items()):
        doc = next(d for d in docs_by_id.values() if skill in (d.filename or ""))
        candidate = sorted((a for a in lane_assets if a.document_id == doc.id),
                           key=lambda a: a.id)[0]
        crud.update_knowledge_asset(
            session, candidate.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=reviewer,
            review_notes=f"human accepted the {kind} finding")
        session.refresh(candidate)
        assert candidate.status == "APPROVED"
        assert candidate.source_class == "DERIVED"
        event = session.query(db.AuditEvent).filter_by(
            event_type="ASSET_APPROVED", target_id=str(candidate.id)).order_by(
            db.AuditEvent.id.desc()).first()
        details = json.loads(event.details)
        prov = details["synthesis_provenance"]
        assert prov["provenance_verified"] is True
        assert prov["claimed"]["agent_principal"] == "customer-operations"
        assert prov["verified"]["binding_id"] == binding.id
        assert prov["verified"]["package_hash"] == package_row.package_hash
        assert prov["cited_assets"]["missing"] == []
        accepted[kind] = candidate
    print("Stage 5 passed: four APPROVED DERIVED facts (one per kind), each "
          "approval event quoting VERIFIED synthesis provenance - agent, "
          "binding, package hash, cited governed evidence, accepting human.")

    # ------------------------------------------------------- Stage 6
    print("\n--- Stage 6: the vault before/after ---")
    os.environ["EM_VAULT_DIR"] = vault_dir
    render = projection_engine.render(session, officer, project.id,
                                      renderer="vault")
    assert render["content_mode"] == "FULL_CONTENT"
    knowledge_dir = os.path.join(vault_dir, "02_knowledge")
    derived_notes = 0
    for root, _dirs, files in os.walk(knowledge_dir):
        for name in files:
            with open(os.path.join(root, name), encoding="utf-8") as f:
                text = f.read()
            assert SENTINEL not in text, "clearance leaked into a vault note"
            for kind, asset in accepted.items():
                if f"asset_{asset.id}_" in name or f"asset_{asset.id}." in name:
                    assert 'source_class: "DERIVED"' in text
                    assert "**DERIVED**" in text
                    assert "This note is not canonical." in text
                    derived_notes += 1
    assert derived_notes == len(accepted), \
        f"every accepted finding must render as a marked DERIVED note " \
        f"({derived_notes}/{len(accepted)})"
    # The untouchable floor survived the render: every proposal intact.
    for path in diagnosis["proposals"]:
        assert os.path.isfile(path), "regeneration must never touch 08_proposals"
    print(f"Stage 6 passed: the re-rendered vault shows all {derived_notes} "
          "accepted findings as marked DERIVED notes, visibly non-canonical; "
          "the untouchable floor held through the render.")

    # ------------------------------------------------------- Stage 7
    print("\n--- Stage 7: THE CLOSING LINES ---")
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
        project_id=project.id, status="APPROVED",
        source_class="DERIVED").all()
    assert len(derived_approved) == len(accepted)
    for asset in derived_approved:
        human_reviews = [r for r in asset.reviews
                         if r.approver and not r.approver.startswith("policy:")]
        assert human_reviews, f"DERIVED fact {asset.id} without a human review"
    swept = 0
    for base in (vault_dir, os.environ["EM_PROJECTION_DIR"],
                 os.environ["EM_PACKAGE_DIR"]):
        for root, _dirs, files in os.walk(base):
            for name in files:
                with open(os.path.join(root, name), "rb") as f:
                    assert SENTINEL.encode() not in f.read(), \
                        f"clearance sweep hit: {os.path.join(root, name)}"
                swept += 1
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    assert live == test_workbench_projection.FROZEN_SCHEMA
    tables = len(live)
    columns = sum(len(cols) for cols in live.values())
    assert (tables, columns) == (28, 305), (tables, columns)
    print(f"Stage 7 passed: every approval event carries a non-AGENT identity "
          f"fact; every APPROVED DERIVED fact has a human review; {swept} "
          f"files swept clean of the EXECUTIVE sentinel; the D24 snapshot "
          f"stands at exactly {tables} tables / {columns} columns.")

    # ------------------------------------------------------- Honest slot
    key = os.environ.get("OPENAI_API_KEY", "")
    real_key = bool(key) and key != "mock-key" or bool(
        os.environ.get("ANTHROPIC_API_KEY"))
    print("\nHonest slot - the ONE real-model diagnostic run: "
          + ("a provider key is present; run the workbench without the "
             "injected answerer/narrator and append the evidence to the "
             "gate record." if real_key else
             "PENDING (no provider key in this environment; the runner's "
             "stdio MCP door and D19 synthesis path are code-complete)."))

    session.close()
    print("\n=== THE v1.6 MILESTONE GATE PASSED: the full commercial loop, "
          "once, end to end - diagnosed through the doors, held by the "
          "valve, accepted by a human, visible in the vault as DERIVED, "
          "with the ledger proving no agent wrote canonical facts. "
          "28 tables / 305 columns. ===")


if __name__ == "__main__":
    main()
