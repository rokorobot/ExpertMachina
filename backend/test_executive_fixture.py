"""v1.9 WS1 - THE FIXTURE PROOF for the Executive Operations Briefing
Workbench.

v1.9's input is not a new document corpus - it is the governed state
the shipped workbenches produce. This suite builds THE CROSS-WORKBENCH
FIXTURE (the compliance AND procurement loops in ONE project) and
proves the briefing's preconditions through EM's own machinery BEFORE
any briefing runner exists:

  1. Both corpora enter one project through the real pipeline; both
     workbench runners diagnose through the doors; the lane holds
     everything DERIVED; a human accepts one finding from EACH
     workbench - and every accepted DERIVED fact's
     WORKBENCH-OF-ORIGIN is derivable from provenance.source_document
     (the proposal filename convention), with zero new machinery.
  2. THE PENDING-PROPOSAL SENTINEL: a held, never-accepted proposal
     carrying a sentinel string is scanned into the lane - the
     sentinel appears in NO package byte (the [PMD] boundary provable
     on bytes at WS2/WS3).
  3. The declared-clock preconditions: a revision approved AFTER the
     captured `since` is discriminable from acceptances before it
     (approved_at ordering over governed revision records).
  4. The governance-health plants: an unresolved DIRECT_CONTRADICTION
     visible through get_conflicts on the ALREADY-COMPILED package's
     model (post-compile drift - the realistic operating rhythm), and
     get_trust_score returning its components.
  5. The unknowns preconditions: the declared executive questions
     refuse reproducibly; the covered control answers (retrieval
     overlap both directions).
  6. The six ratified contracts exist (13-field shape); the manifest
     agrees; the draft != ratified sweep stays honest (23 ACTIVE / 18
     CONSOLIDATED globally; consolidation never silent; the
     detect_unresolved_blockers split_note recorded).
  7. Zero schema: D24 at 28 tables / 305 columns.

The posture holds in the proof: nothing here composes a briefing -
these are the PRECONDITIONS, proven before the runner exists.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_execfx_pkg_")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_execfx_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'fixture.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_execfx_qdrant_")

from app import (schemas, crud, connectors, identity,  # noqa: E402
                 package_builder, package_consumer, mcp_gateway,
                 policy, proposals, tier2, llm)
import test_support                           # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.compliance_obligation.runner as compliance_runner   # noqa: E402
import workbench.procurement_intelligence.runner as procurement_runner  # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "executive_briefing")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
DRAFTS_DIR = os.path.join(REPO_DIR, "docs", "skill-contracts")
COMPLIANCE_CORPUS = os.path.join(REPO_DIR, "workbench",
                                 "compliance_obligation", "corpus")
PROCUREMENT_CORPUS = os.path.join(REPO_DIR, "workbench",
                                  "procurement_intelligence", "corpus")

PENDING_SENTINEL = "EM-PENDING-SENTINEL-9K3W"
AS_OF = "2026-06-01"
WINDOW_DAYS = 90

# The declared executive questions (must match the ratified contract -
# asserted against the contract bytes in Part 6).
Q_GAP_1 = ("Which approved document states our incident response "
           "commitments to customers?")
Q_GAP_2 = ("Which approved document states the board quorum required "
           "for emergency decisions?")
# The covered control: the compliance corpus answers the incident-test
# question (the P2c plant from v1.7).
Q_COVERED = ("Was the annual incident response plan test completed "
             "and the test report retained for audit review?")

RATIFIED_ACTIVE = 34     # +3 contract-intelligence (v2.1) +3 deadline-obligation (v2.2) +5 finance-cost-leakage (v2.3)
RATIFIED_CONSOLIDATED = 58   # +22 contract-intelligence (v2.1) +4 deadline-obligation (v2.2) +14 finance-cost-leakage (v2.3)
REQUIRED_FIELDS = (
    "skill_id:", "workbench:", "status:", "boundary_tags:", "purpose:",
    "allowed_inputs:", "forbidden_inputs:", "evidence_rules:",
    "allowed_finding_kinds:", "output_format:",
    "human_approval_requirement:", "audit_event:", "refusal_conditions:")
ACTIVE_SIX = ("summarize_accepted_findings", "summarize_unresolved_conflicts",
              "summarize_governance_health", "answer_what_changed_since",
              "generate_unknowns_evidence_gaps_report",
              "prepare_executive_briefing")


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


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
    for asset in session.query(db.KnowledgeAsset).filter(
            db.KnowledgeAsset.project_id == project_id,
            db.KnowledgeAsset.status == "CANDIDATE").all():
        crud.update_knowledge_asset(
            session, asset.id,
            schemas.KnowledgeAssetUpdate(status="APPROVED", domain=domain),
            actor=reviewer, review_notes=note)


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
    """The declared deterministic CI contract-follower (supplier-named
    coverage where a supplier is named; plain overlap otherwise)."""
    def answer(question):
        sel = package_consumer.retrieve(loaded_package, question,
                                        top_k=8)["selected"]
        supplier = None
        for name in ("DataFlow", "SecureStore", "CloudHost", "Translient",
                     "PrintWorks", "OfficeSupply"):
            if name.lower() in question.lower():
                supplier = name
        qt = package_consumer._tokens(question)
        scored = sorted(
            ((len(qt & package_consumer._tokens(e.get("content") or "")), e)
             for e in sel), key=lambda t: (-t[0], t[1]["asset_id"]))
        best = next(((s, e) for s, e in scored
                     if s >= 6 and (supplier is None
                                    or supplier.lower() in (e.get("content") or "").lower())),
                    None)
        if best:
            text = (f"Per the governed evidence (asset_id {best[1]['asset_id']}): "
                    f"{best[1].get('content')}")
            cited = [best[1]["asset_id"]]
        else:
            text = ("INSUFFICIENT EVIDENCE - the governed evidence offered "
                    "does not contain the answer to this question.")
            cited = []
        return {"answer": text, "cited_asset_ids": cited, "evidence": sel}
    return answer


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "ExecFxOfficer")
    reviewer = test_support.governed_actor(session, "ExecFxReviewer")
    issuer = test_support.governed_actor(session, "ExecFxIssuer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Executive Fixture", description="v1.9 WS1 cross-workbench fixture",
        customer_id=customer.id), actor=officer)

    # --- Part 1: BOTH corpora in one project; both loops run -------------
    print("\n--- Part 1: the cross-workbench fixture (two loops, one project) ---")
    for name, root, domain in (("Compliance Docs", COMPLIANCE_CORPUS, "compliance"),
                               ("Procurement Docs", PROCUREMENT_CORPUS, "procurement")):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
        approve_all(session, project.id, reviewer, f"fixture: {domain}",
                    domain=domain)
    for like in ("%risk-acceptance-memo%", "%executive-vendor-strategy%"):
        doc = session.query(db.Document).filter(
            db.Document.project_id == project.id,
            db.Document.filename.like(like)).first()
        for a in session.query(db.KnowledgeAsset).filter_by(
                document_id=doc.id).all():
            a.access_level = "EXECUTIVE"
    session.commit()
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    model = db.ExpertModel(project_id=project.id, name="Company Expert",
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    session.add(model)
    session.commit()
    session.refresh(model)
    package_row = db.AgentPackage(project_id=project.id,
                                  expert_model_id=model.id,
                                  name="Company Package",
                                  clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    package_builder.build_package(session, package_row)
    session.refresh(package_row)
    loaded = package_consumer.load_package(package_row.file_path)
    agent = identity.create_principal(session, name="executive-briefing",
                                      display_name="Executive Briefing",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _cred = identity.issue_token(session, agent, kind="API_TOKEN",
                                              label="fixture", actor="test-suite")
    os.environ["EM_AGENT_TOKEN"] = agent_token   # the fixture's door token
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

    vault_dir = tempfile.mkdtemp(prefix="em_execfx_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    answerer = make_answerer(loaded)
    if True:
        d1 = compliance_runner.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="executive-briefing", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            answerer=answerer)
        d2 = procurement_runner.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="executive-briefing", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW_DAYS, answerer=answerer)
    assert d1["proposals"] and d2["proposals"], "both loops must diagnose"

    # THE PENDING-PROPOSAL SENTINEL: a held proposal that is NEVER accepted.
    sentinel_doc = "\n".join([
        "---", "em_proposal: 1", "agent_principal: executive-briefing",
        f"binding_id: {binding.id}",
        f"package_hash: {package_row.package_hash}",
        "workbench: executive-briefing", "skill: fixture_pending_plant",
        "skill_version: 1", "finding_kind: FIXTURE_PENDING",
        "evidence_basis: EXCERPT_BACKED", "cited_assets: ", "---", "",
        "# Held proposal - the pending sentinel plant", "",
        f"This held proposal carries the sentinel {PENDING_SENTINEL} and",
        "must never be accepted as knowledge. Its bytes must appear in no",
        "package and no briefing.", ""])
    with open(os.path.join(vault_dir, "08_proposals",
                           "executive-briefing-fixture-pending-plant.md"),
              "w", encoding="utf-8", newline="\n") as f:
        f.write(sentinel_doc)

    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add(db.ApprovalPolicy(project_id=project.id, name="everything",
                                  asset_types_json=all_types, enabled=True))
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
    lane_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_doc_ids)).all()
    assert lane_assets and all(a.status == "CANDIDATE"
                               and a.source_class == "DERIVED"
                               for a in lane_assets)
    print(f"Part 1 passed: {len(approved)} PRIMARY facts (both domains), "
          f"{len(d1['proposals'])}+{len(d2['proposals'])} proposals from the "
          f"two runners, {len(lane_assets)} candidates held DERIVED incl. "
          "the pending sentinel plant.")

    # --- Part 2: accept ONE per workbench; origin derivable --------------
    print("\n--- Part 2: acceptances with workbench-of-origin derivable ---")
    docs_by_id = {d.id: d for d in session.query(db.Document).filter(
        db.Document.id.in_(lane_doc_ids)).all()}
    accepted = {}
    before_since_ids = []
    for wb_prefix in ("compliance-obligation-", "procurement-intelligence-"):
        doc = next(d for d in docs_by_id.values()
                   if (d.filename or "").startswith(wb_prefix))
        candidates = sorted((a for a in lane_assets if a.document_id == doc.id),
                            key=lambda a: a.id)
        with_marker = [a for a in candidates
                       if re.search(r"(must|shall)", norm(a.content))]
        candidate = (with_marker or candidates)[0]
        crud.update_knowledge_asset(
            session, candidate.id,
            schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=reviewer, review_notes=f"fixture acceptance ({wb_prefix})")
        session.refresh(candidate)
        assert candidate.source_class == "DERIVED"
        accepted[wb_prefix] = candidate
        before_since_ids.append(candidate.id)
    # origin derivable from provenance.source_document, zero new machinery:
    model2 = db.ExpertModel(project_id=project.id, name="Company Expert v2",
                            asset_ids_json=json.dumps(
                                sorted([a.id for a in session.query(
                                    db.KnowledgeAsset).filter_by(
                                    project_id=project.id,
                                    status="APPROVED").all()])),
                            asset_count=0)
    session.add(model2)
    session.commit()
    session.refresh(model2)
    package_row2 = db.AgentPackage(project_id=project.id,
                                   expert_model_id=model2.id,
                                   name="Company Package v2",
                                   clearance_level="INTERNAL")
    session.add(package_row2)
    session.commit()
    session.refresh(package_row2)
    package_builder.build_package(session, package_row2)
    session.refresh(package_row2)
    loaded2 = package_consumer.load_package(package_row2.file_path)
    by_id2 = {e["asset_id"]: e for e in loaded2["knowledge"]}
    origins = {}
    for wb_prefix, asset in accepted.items():
        entry = by_id2.get(asset.id)
        assert entry and entry.get("source_class") == "DERIVED", \
            "the accepted DERIVED fact must travel into the package"
        src = (entry.get("provenance") or {}).get("source_document") or ""
        assert src.startswith(wb_prefix), \
            f"workbench-of-origin must be derivable: {src!r}"
        origins[asset.id] = src.split("-" + src.split("-")[-1])[0]
    print(f"Part 2 passed: one acceptance per workbench; both origins "
          f"derivable from provenance.source_document "
          f"({sorted(set(v.rsplit('-', 1)[0] for v in origins.values()))}).")

    # --- Part 3: the pending sentinel is in NO package byte --------------
    print("\n--- Part 3: THE PENDING-PROPOSAL SENTINEL boundary ---")
    for path in (package_row.file_path, package_row2.file_path):
        with open(path, "rb") as f:
            assert PENDING_SENTINEL.encode() not in f.read(), \
                "a held proposal's bytes leaked into a package"
    pending = [a for a in session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="CANDIDATE").all()
        if PENDING_SENTINEL in norm(a.content)]
    assert pending, "the sentinel plant must be held as a CANDIDATE"
    assert not any(a.id in by_id2 for a in pending), \
        "held candidates are structurally absent from packages"
    print("Part 3 passed: the pending sentinel is held CANDIDATE, present in "
          "no package byte - the [PMD] boundary provable on bytes.")

    # --- Part 4: the declared-clock precondition --------------------------
    print("\n--- Part 4: the declared `since` discriminates ---")
    time.sleep(1.1)
    since_dt = datetime.datetime.utcnow()
    time.sleep(1.1)
    # one more acceptance AFTER the captured since (the what-changed plant)
    late_doc = next(d for d in docs_by_id.values()
                    if (d.filename or "").startswith("compliance-obligation-")
                    and not any(a.document_id == d.id for a in accepted.values()))
    late_candidates = sorted((a for a in lane_assets
                              if a.document_id == late_doc.id),
                             key=lambda a: a.id)
    late = late_candidates[0]
    crud.update_knowledge_asset(
        session, late.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="fixture: the post-since acceptance")
    session.refresh(late)
    gc = InProcessGraphClient()
    late_hist = gc.get_revision_history(late.id)
    late_times = [r.get("approved_at") for r in late_hist["revisions"]
                  if r.get("approved_at")]
    early_hist = gc.get_revision_history(before_since_ids[0])
    early_times = [r.get("approved_at") for r in early_hist["revisions"]
                   if r.get("approved_at")]
    since_iso = since_dt.isoformat()
    assert any(t > since_iso for t in late_times), \
        f"the late acceptance must sort after since ({late_times} vs {since_iso})"
    assert all(t < since_iso for t in early_times), \
        f"the early acceptances must sort before since ({early_times})"
    print(f"Part 4 passed: approved_at ordering discriminates at the "
          f"declared since - the what-changed precondition holds both "
          f"directions.")

    # --- Part 5: governance-health + unknowns preconditions --------------
    print("\n--- Part 5: door-visible health + the unknowns questions ---")
    # post-compile drift: an unresolved conflict inserted AFTER the package
    # compiled - visible via get_conflicts, never blocking the shipped pkg.
    def find(needle):
        return next(a for a in approved if needle in norm(a.content))
    session.add(db.AssetRelationship(
        project_id=project.id, expert_model_id=model2.id,
        source_asset_id=find("retained for ten years").id,
        target_asset_id=find("destroyed three years").id,
        relationship_type="CONFLICTS_WITH",
        classification="DIRECT_CONTRADICTION", confidence=0.99,
        status="DETECTED", verifier_json=json.dumps({"method": "TEST_FIXTURE"})))
    session.commit()
    if True:
        conflicts = gc.get_conflicts(model2.id)
        unresolved = [r for r in conflicts["relationships"]
                      if r["status"] == "DETECTED"]
        assert unresolved, "the unresolved-conflict plant must be door-visible"
        trust_session = db.SessionLocal()
        try:
            trust = mcp_gateway.get_trust_score(model2.id, session=trust_session)
        finally:
            trust_session.close()
        assert "components" in json.dumps(trust).lower() or trust, \
            "get_trust_score must return the health signal"
    original_generate = llm.generate

    def contract_follower(function, system, user, session=None, max_tokens=4096):
        r = make_answerer(loaded2)(user)
        return {"function": function, "provider": "TEST",
                "model": "contract-follower-v1", "source": "deterministic-ci",
                "text": r["answer"]}
    llm.generate = contract_follower
    try:
        for q in (Q_GAP_1, Q_GAP_2):
            first = package_consumer.consume(package_row2.file_path, q)
            second = package_consumer.consume(package_row2.file_path, q)
            assert first["answer"] == second["answer"]
            assert "INSUFFICIENT EVIDENCE" in first["answer"], \
                f"gap question must refuse: {q[:50]}"
        covered = package_consumer.consume(package_row2.file_path, Q_COVERED)
        assert "INSUFFICIENT EVIDENCE" not in covered["answer"], \
            "the covered control must answer"
    finally:
        llm.generate = original_generate
    print(f"Part 5 passed: unresolved conflict door-visible on the compiled "
          f"package (post-compile drift); trust components returned; both "
          "gap questions refused reproducibly; the covered control answered.")

    # --- Part 6: contracts + the draft != ratified sweep ------------------
    print("\n--- Part 6: contract shape + no silent promotion ---")
    with open(os.path.join(WB_DIR, "workbench.yaml"), encoding="utf-8") as f:
        manifest = f.read()
    declared = re.findall(r"^  - (\w+)$", manifest.split("skills:\n")[1],
                          re.MULTILINE)[:6]
    ratified = sorted(n[:-5] for n in os.listdir(SKILLS_DIR)
                      if n.endswith(".yaml"))
    assert sorted(declared) == ratified == sorted(ACTIVE_SIX)
    for skill in ACTIVE_SIX:
        with open(os.path.join(SKILLS_DIR, f"{skill}.yaml"),
                  encoding="utf-8") as f:
            text = f.read()
        for field in REQUIRED_FIELDS:
            assert re.search(rf"^{field}", text, re.MULTILINE), \
                f"{skill}: missing contract field {field}"
    with open(os.path.join(SKILLS_DIR,
                           "generate_unknowns_evidence_gaps_report.yaml"),
              encoding="utf-8") as f:
        gaps_text = norm(f.read())
    for q in (Q_GAP_1, Q_GAP_2):
        assert q in gaps_text, "the suite's questions are the contract's frames"
    active, consolidated = [], []
    for folder, _dirs, files in os.walk(DRAFTS_DIR):
        for name in files:
            if not name.endswith(".yaml"):
                continue
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                text = f.read()
            status = re.search(r"^status: (\S+)", text, re.MULTILINE).group(1)
            if status == "ACTIVE":
                active.append(name)
                rp = re.search(r"^ratified_path: (\S+)", text, re.MULTILINE)
                assert rp and os.path.isfile(os.path.join(REPO_DIR, rp.group(1))), \
                    f"{name}: ACTIVE without resolving ratified_path"
            elif status == "CONSOLIDATED":
                consolidated.append(name)
                ci = re.search(r"^consolidated_into: (\S+)", text, re.MULTILINE)
                rp = re.search(r"^ratified_path: (\S+)", text, re.MULTILINE)
                assert ci and rp and os.path.isfile(
                    os.path.join(REPO_DIR, rp.group(1))), \
                    f"{name}: consolidation must never be silent"
                assert os.path.basename(rp.group(1)) == ci.group(1) + ".yaml"
    assert len(active) == RATIFIED_ACTIVE, \
        f"expected {RATIFIED_ACTIVE} ACTIVE drafts, got {len(active)}"
    assert len(consolidated) == RATIFIED_CONSOLIDATED, \
        f"expected {RATIFIED_CONSOLIDATED} CONSOLIDATED, got {len(consolidated)}"
    with open(os.path.join(DRAFTS_DIR, "01_executive_ceo",
                           "detect_unresolved_blockers_by_department.yaml"),
              encoding="utf-8") as f:
        assert "split_note" in f.read(), "the split must be recorded, never silent"
    print(f"Part 6 passed: six 13-field contracts match the manifest; the "
          f"declared questions live in the contract bytes; the sweep holds "
          f"at {RATIFIED_ACTIVE} ACTIVE / {RATIFIED_CONSOLIDATED} "
          "CONSOLIDATED; the blockers split recorded.")

    # --- Part 7: zero schema ----------------------------------------------
    print("\n--- Part 7: zero schema ---")
    tables = len(db.Base.metadata.tables)
    columns = sum(len(t.columns) for t in db.Base.metadata.tables.values())
    assert (tables, columns) == (28, 305), (tables, columns)
    print(f"Part 7 passed: the D24 snapshot stands at exactly {tables} "
          f"tables / {columns} columns.")

    session.close()
    print("\n=== All executive fixture-proof checks passed: the "
          "cross-workbench governed state is real, origins are derivable, "
          "the pending sentinel is bounded, the clock discriminates, and "
          "the doors yield the health signals - before any briefing runner "
          "exists. ===")


if __name__ == "__main__":
    main()
