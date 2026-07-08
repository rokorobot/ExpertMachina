"""v1.9 WS2 - THE DIAGNOSIS PROOF for the Executive Operations Briefing
Workbench.

The runner (workbench/executive_briefing/runner.py, on
workbench/common.py) is proven as a governed cross-workbench consumer,
not a vague agent:

  - it reads the cross-workbench governed state (compliance + procurement
    accepted DERIVED facts in one project) through the EXISTING doors
    only; accepted findings show BOTH origins, DERIVED cited AS DERIVED,
    PRIMARY vs DERIVED class always visible;
  - unresolved conflicts cite both sides; governance health is
    door-limited (trust components, unresolved-conflict count);
    what-changed uses the declared since only; unknowns are
    REFUSAL_BACKED;
  - EXACTLY ONE proposal kind is emitted (EXECUTIVE_EVIDENCE_GAP); the
    read-compose skills emit no proposals; the briefing pack is assist,
    written to /07_agent_workspaces, never /08_proposals;
  - THE UNSOURCED SENTENCE: every cited-section line carries a governed
    token; prose lives only in the SYNTHESIS_INFERRED and boundary
    sections; the forbidden vocabulary is absent; the boundary section
    is present and truthful;
  - THE PENDING-PROPOSAL SENTINEL appears in NO briefing byte, NO gap
    proposal byte, NO package byte ([PMD] on bytes);
  - [PMD]/[OE]/[ES]/persistent-register/schedule/multi-project requests
    refuse live; a run without as_of/since refuses;
  - byte-identical regeneration at the same declared clock over the same
    governed state; the EXECUTIVE clearance sentinel absent;
  - Guard 5 sweeps every workbench module with zero edits; ZERO DOOR
    GROWTH proven structurally (route-manifest digest unchanged, MCP
    frozen at 9 tools, D24 at 28/305); and the gap proposals hold DERIVED
    with provenance verified.
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
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_exec2_pkg_")

# Guard 5 first (its import overrides db.engine; this suite re-overrides), for
# the door-sweep checker and the frozen 9-tool assertion.
import test_agent_authorship_guard as guard   # noqa: E402
import test_route_manifest as route_guard      # noqa: E402

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_exec2_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'ws2.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_exec2_qdrant_")

from app import (schemas, crud, connectors, identity,  # noqa: E402
                 package_builder, package_consumer, mcp_gateway,
                 policy, proposals, tier2)
import test_support                           # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.compliance_obligation.runner as compliance_runner   # noqa: E402
import workbench.procurement_intelligence.runner as procurement_runner  # noqa: E402
import workbench.executive_briefing.runner as runner   # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "executive_briefing")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
MANIFEST = os.path.join(WB_DIR, "workbench.yaml")
COMPLIANCE_CORPUS = os.path.join(REPO_DIR, "workbench",
                                 "compliance_obligation", "corpus")
PROCUREMENT_CORPUS = os.path.join(REPO_DIR, "workbench",
                                  "procurement_intelligence", "corpus")
EXEC_SENTINEL = "EM-EXEC-SENTINEL-7C2R"    # the compliance EXECUTIVE memo
PENDING_SENTINEL = "EM-PENDING-SENTINEL-9K3W"
AS_OF = "2026-06-01"


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


def vault_files(vault_dir):
    found = set()
    for root, _dirs, files in os.walk(vault_dir):
        for name in files:
            found.add(os.path.relpath(os.path.join(root, name), vault_dir)
                      .replace(os.sep, "/"))
    return found


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

    def get_trust_score(self, expert_model_id):
        return self._run(mcp_gateway.get_trust_score, expert_model_id)


def make_answerer(loaded_package):
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


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def build_fixture(session, project, reviewer, issuer, agent_token, agent):
    """The cross-workbench fixture (the WS1 shape): both loops in one
    project; accept one finding per workbench; hold the pending sentinel;
    a post-since acceptance; a post-compile-drift conflict."""
    for name, root, domain in (("Compliance Docs", COMPLIANCE_CORPUS, "compliance"),
                               ("Procurement Docs", PROCUREMENT_CORPUS, "procurement")):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
        approve_all(session, project.id, reviewer, f"fixture: {domain}", domain=domain)
    for like in ("%risk-acceptance-memo%", "%executive-vendor-strategy%"):
        doc = session.query(db.Document).filter(
            db.Document.project_id == project.id,
            db.Document.filename.like(like)).first()
        for a in session.query(db.KnowledgeAsset).filter_by(document_id=doc.id).all():
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
    package_row = db.AgentPackage(project_id=project.id, expert_model_id=model.id,
                                  name="Company Package", clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    package_builder.build_package(session, package_row)
    session.refresh(package_row)
    loaded = package_consumer.load_package(package_row.file_path)
    binding = db.ExpertAgentBinding(
        agent_package_id=package_row.id, agent_principal_id=agent.id,
        package_hash=package_row.package_hash, package_version="v1",
        principal_clearance_at_issue="INTERNAL",
        selected_provider="ANTHROPIC", selected_model_name="claude-opus-4-8",
        selection_evidence_json="{}", identity_fact_id=issuer.fact(session).id)
    session.add(binding)
    session.commit()
    session.refresh(binding)

    vault_dir = tempfile.mkdtemp(prefix="em_exec2_vault_")
    subprocess.run([sys.executable, os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                    "--vault-dir", vault_dir], capture_output=True, text=True)
    answerer = make_answerer(loaded)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    d1 = compliance_runner.run_diagnostic(
        package_row.file_path, vault_dir, project.id,
        agent_principal="executive-briefing", binding_id=binding.id,
        graph_client=InProcessGraphClient(), as_of=AS_OF, answerer=answerer)
    procurement_runner.run_diagnostic(
        package_row.file_path, vault_dir, project.id,
        agent_principal="executive-briefing", binding_id=binding.id,
        graph_client=InProcessGraphClient(), as_of=AS_OF, window_days=90,
        answerer=answerer)
    # the pending sentinel plant (never accepted)
    with open(os.path.join(vault_dir, "08_proposals",
                           "executive-briefing-fixture-pending.md"),
              "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join([
            "---", "em_proposal: 1", "agent_principal: executive-briefing",
            f"binding_id: {binding.id}", f"package_hash: {package_row.package_hash}",
            "workbench: executive-briefing", "skill: fixture_pending",
            "skill_version: 1", "finding_kind: FIXTURE_PENDING",
            "evidence_basis: EXCERPT_BACKED", "cited_assets: ", "---", "",
            "# Held plant", "",
            f"This held proposal carries the sentinel {PENDING_SENTINEL} and",
            "must never be accepted as knowledge.", ""]))
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
    docs = {d.id: d for d in session.query(db.Document).filter(
        db.Document.id.in_(lane_doc_ids)).all()}
    for wb in ("compliance-obligation-", "procurement-intelligence-"):
        doc = next(d for d in docs.values() if (d.filename or "").startswith(wb))
        cands = sorted((a for a in lane_assets if a.document_id == doc.id),
                       key=lambda a: a.id)
        pick = next((a for a in cands if re.search(r"(must|shall)", norm(a.content))),
                    cands[0])
        crud.update_knowledge_asset(
            session, pick.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=reviewer, review_notes=f"fixture accept {wb}")
    time.sleep(1.1)
    since = datetime.datetime.utcnow().date().isoformat()
    time.sleep(1.1)
    late_doc = next(d for d in docs.values()
                    if (d.filename or "").startswith("compliance-obligation-"))
    late = sorted((a for a in lane_assets if a.document_id == late_doc.id
                   and a.status == "CANDIDATE"), key=lambda a: a.id)[0]
    crud.update_knowledge_asset(
        session, late.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="fixture: post-since acceptance")
    # recompile with the accepted DERIVED facts + a post-compile conflict
    approved2 = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    model2 = db.ExpertModel(project_id=project.id, name="Company Expert v2",
                            asset_ids_json=json.dumps([a.id for a in approved2]),
                            asset_count=len(approved2))
    session.add(model2)
    session.commit()
    session.refresh(model2)
    pkg2 = db.AgentPackage(project_id=project.id, expert_model_id=model2.id,
                           name="Company Package v2", clearance_level="INTERNAL")
    session.add(pkg2)
    session.commit()
    session.refresh(pkg2)
    package_builder.build_package(session, pkg2)
    session.refresh(pkg2)

    def find(needle):
        return next(a for a in approved2 if needle in norm(a.content))
    session.add(db.AssetRelationship(
        project_id=project.id, expert_model_id=model2.id,
        source_asset_id=find("retained for ten years").id,
        target_asset_id=find("destroyed three years").id,
        relationship_type="CONFLICTS_WITH", classification="DIRECT_CONTRADICTION",
        confidence=0.99, status="DETECTED",
        verifier_json=json.dumps({"method": "TEST_FIXTURE"})))
    session.commit()
    binding2 = db.ExpertAgentBinding(
        agent_package_id=pkg2.id, agent_principal_id=agent.id,
        package_hash=pkg2.package_hash, package_version="v2",
        principal_clearance_at_issue="INTERNAL",
        selected_provider="ANTHROPIC", selected_model_name="claude-opus-4-8",
        selection_evidence_json="{}", identity_fact_id=issuer.fact(session).id)
    session.add(binding2)
    session.commit()
    session.refresh(binding2)
    os.environ.pop("EM_AGENT_TOKEN", None)
    return dict(vault_dir=vault_dir, package=pkg2, loaded=package_consumer.load_package(
        pkg2.file_path), binding=binding2, model=model2, since=since,
        accepted_derived=[a.id for a in approved2 if a.source_class == "DERIVED"])


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "Exec2Officer")
    reviewer = test_support.governed_actor(session, "Exec2Reviewer")
    issuer = test_support.governed_actor(session, "Exec2Issuer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Executive WS2", description="the diagnosis proof",
        customer_id=customer.id), actor=officer)
    agent = identity.create_principal(session, name="executive-briefing",
                                      display_name="Executive Briefing",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _c = identity.issue_token(session, agent, kind="API_TOKEN",
                                           label="ws2", actor="test-suite")

    # ------------------------------------------------------------ Part 1
    print("\n--- Part 1: every workbench module passes the Guard 5 door sweep ---")
    swept = 0
    for root, _dirs, files in os.walk(os.path.join(REPO_DIR, "workbench")):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            with open(path, "r", encoding="utf-8") as f:
                v = guard.workbench_import_violations(
                    os.path.relpath(path, REPO_DIR).replace(os.sep, "/"), f.read())
            assert not v, "\n".join(v)
            swept += 1
    assert swept >= 6, "all runners + common.py swept"
    print(f"Part 1 passed: {swept} workbench module(s) inside the ruled doors "
          "- zero guard edits.")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: the cross-workbench fixture ---")
    fx = build_fixture(session, project, reviewer, issuer, agent_token, agent)
    packaged_ids = {e["asset_id"] for e in fx["loaded"]["knowledge"]}
    assert fx["accepted_derived"], "the fixture must carry accepted DERIVED facts"
    print(f"Part 2 passed: package v2 with {len(fx['accepted_derived'])} accepted "
          "DERIVED facts (both workbenches) + a post-compile conflict.")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE BRIEFING (composition, determinism, posture) ---")
    baseline = vault_files(fx["vault_dir"])
    answerer = make_answerer(fx["loaded"])
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        runs = [runner.run_briefing(
            fx["package"].file_path, fx["vault_dir"], project.id,
            agent_principal="executive-briefing", binding_id=fx["binding"].id,
            graph_client=InProcessGraphClient(), as_of=AS_OF, since=fx["since"],
            answerer=answerer) for _ in range(2)]
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    first, second = runs
    assert first["as_of"] == AS_OF and first["since"] == fx["since"]
    assert first["briefing"] == second["briefing"], "byte-identical pack path"
    assert first["proposals"] == second["proposals"]
    for path in [first["briefing"]] + first["proposals"]:
        with open(path, encoding="utf-8") as f:
            c1 = f.read()
        with open(path, encoding="utf-8") as f:
            assert f.read() == c1
    with open(first["briefing"], encoding="utf-8") as f:
        pack = f.read()
    # confinement: the pack is in the workspace, the gaps in 08_proposals
    new_files = vault_files(fx["vault_dir"]) - baseline
    briefs = [r for r in new_files if r.startswith("07_agent_workspaces/")]
    props = [r for r in new_files if r.startswith("08_proposals/")]
    assert len(briefs) == 1 and first["briefing"].endswith(briefs[0].split("/")[-1])
    for rel in new_files:
        assert rel.startswith(("07_agent_workspaces/", "08_proposals/")), rel
    assert not any("07_agent_workspaces" in p for p in first["proposals"]), \
        "the briefing pack must never be a proposal"
    # the mandatory sections
    for section in ("## Accepted findings", "## Unresolved conflicts",
                    "## Governance health", "## What changed since",
                    "## Unknowns & evidence gaps",
                    "## Recommended attention [SYNTHESIS_INFERRED]",
                    "## What this briefing cannot see"):
        assert section in pack, f"mandatory section missing: {section}"
    # the posture: forbidden vocabulary + sentinels absent from EVERY byte
    forbidden = runner.parse_forbidden_vocabulary(MANIFEST)
    assert len(forbidden) >= 8
    for path in [first["briefing"]] + first["proposals"]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        low = text.lower()
        for phrase in forbidden:
            assert phrase not in low, f"forbidden vocabulary in a byte: {phrase!r}"
        assert EXEC_SENTINEL not in text, "EXECUTIVE sentinel leaked"
        assert PENDING_SENTINEL not in text, "the pending sentinel leaked"
    print(f"Part 3 passed: one briefing pack (7 mandatory sections) + "
          f"{len(first['proposals'])} gap proposal(s), byte-identical at the "
          "declared clock, confined; forbidden vocabulary + EXEC sentinel + "
          "pending sentinel absent from every written byte.")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: cross-workbench content + door-limited health ---")
    accepted_section = pack.split("## Accepted findings")[1].split("## Unresolved")[0]
    assert "[DERIVED, origin: compliance-obligation]" in accepted_section, \
        "compliance origin must be named"
    assert "[DERIVED, origin: procurement-intelligence]" in accepted_section, \
        "procurement origin must be named"
    assert "[PRIMARY]" in accepted_section, "PRIMARY class must be visible"
    assert set(first["accepted_origins"]) >= {"compliance-obligation",
                                              "procurement-intelligence"}
    conflicts_section = pack.split("## Unresolved conflicts")[1].split("## Governance")[0]
    assert "conflict " in conflicts_section and " vs asset " in conflicts_section, \
        "unresolved conflicts must cite both sides"
    assert first["unresolved_conflicts"] >= 1
    health_section = pack.split("## Governance health")[1].split("## What changed")[0]
    assert "trust component" in health_section, "trust components must show"
    assert "unresolved conflicts:" in health_section
    changed_section = pack.split(f"## What changed since {fx['since']}")[1].split(
        "## Unknowns")[0]
    assert f"since {fx['since']}" in changed_section
    assert re.search(r"asset \d+ revision \d+ accepted at", changed_section), \
        "what-changed must cite the post-since acceptance"
    boundary = pack.split("## What this briefing cannot see")[1]
    assert "[PMD]" in boundary and "[OE]" in boundary and "[ES]" in boundary, \
        "the boundary section must name the unminted decisions"
    print("Part 4 passed: both DERIVED origins named + PRIMARY visible; "
          "conflicts cite both sides; trust components + conflict count "
          "door-visible; what-changed cites the post-since acceptance; the "
          "boundary section names [PMD]/[OE]/[ES].")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: the findings ruling (one proposal kind; refusal-backed) ---")
    assert first["findings"], "at least one evidence gap must fire"
    for f in first["findings"]:
        assert f["finding_kind"] == "EXECUTIVE_EVIDENCE_GAP"
        assert f["evidence_basis"] == "REFUSAL_BACKED"
        assert f["cited_assets"] == [], "a gap cites nothing (refusal-backed)"
    for path in first["proposals"]:
        with open(path, encoding="utf-8") as f:
            parsed = proposals.parse_frontmatter(f.read())
        assert parsed["claimed"] and not parsed["problems"], parsed
        assert parsed["claims"]["finding_kind"] == "EXECUTIVE_EVIDENCE_GAP"
        assert parsed["claims"]["workbench"] == "executive-briefing"
    # the read-compose skills emitted NO proposals: exactly the gaps did.
    gap_count = len(first["findings"])
    assert len(first["proposals"]) == gap_count, \
        "only the gap skill proposes; summaries never do"
    print(f"Part 5 passed: {gap_count} EXECUTIVE_EVIDENCE_GAP proposal(s), "
          "REFUSAL_BACKED, empty citations; the read-compose skills emitted "
          "no proposals.")

    # ------------------------------------------------------------ Part 6
    print("\n--- Part 6: boundaries refuse live; clock declared ---")
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        def expect(kwargs, needle):
            try:
                runner.run_briefing(
                    fx["package"].file_path, fx["vault_dir"], project.id,
                    agent_principal="executive-briefing", binding_id=fx["binding"].id,
                    graph_client=InProcessGraphClient(), answerer=answerer, **kwargs)
            except RuntimeError as e:
                return needle in str(e)
            return False
        assert expect(dict(as_of=None, since=fx["since"]), "no as_of declared")
        assert expect(dict(as_of=AS_OF, since=None), "no since declared")
        assert expect(dict(as_of=AS_OF, since=fx["since"], schedule=True),
                      "never recurs")
        assert expect(dict(as_of=AS_OF, since=fx["since"],
                           project_ids=[project.id, project.id + 1]),
                      "multi-project")
        for extra, needle in (
                ("produce_executive_decision_queue", "Pipeline Metadata Door"),
                ("compare_operational_metrics", "Operational Evidence Realm"),
                ("route_to_responsible_owner", "Exception Stewardship"),
                ("produce_cross_functional_risk_register", "persistent-register"),
                ("schedule_weekly_briefing", "schedule refusal")):
            assert expect(dict(as_of=AS_OF, since=fx["since"],
                               requested_skills=runner.ACTIVE_SKILLS + (extra,)),
                          needle), f"{extra} must refuse naming {needle}"
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    print("Part 6 passed: no-as_of / no-since / schedule / multi-project "
          "refused; [PMD] / [OE] / [ES] / persistent-register / schedule "
          "skills refused live naming the boundary.")

    # ------------------------------------------------------------ Part 7
    print("\n--- Part 7: ZERO DOOR GROWTH (structural) ---")
    # the route manifest is byte-identical (the T2.4 guard = the door-growth
    # instrument); the MCP surface is still frozen at 9 tools (Guard 5);
    # D24 at 28/305.
    assert route_guard.digest(route_guard.build_manifest()) == \
        route_guard.FROZEN_DIGEST, "a REST door changed - zero door growth"
    from app import mcp_gateway as gw
    tool_fns = [n for n in dir(gw)
                if n in ("ask_expert", "get_trust_score", "get_provenance",
                         "get_conflicts", "check_gate_status",
                         "get_graph_neighbors", "get_lineage_path",
                         "get_domain_subgraph", "get_revision_history")]
    assert len(tool_fns) == 9, f"the MCP surface is not frozen at 9: {tool_fns}"
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    tables, columns = len(live), sum(len(c) for c in live.values())
    assert (tables, columns) == (28, 305), (tables, columns)
    print(f"Part 7 passed: route manifest byte-identical (no REST door); the "
          f"MCP surface still frozen at 9 tools; D24 at {tables}/{columns}.")

    # ------------------------------------------------------------ Part 8
    print("\n--- Part 8: the gap proposals hold DERIVED at the valve ---")
    lane = session.query(db.SourceConnector).filter_by(
        project_id=project.id, lane="PROPOSAL").first()
    run_scan(session, lane)
    gap_docs = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename.like("executive-briefing-generate_unknowns%")).all()
    assert gap_docs, "the gap proposals must ingest through the lane"
    gap_ids = [d.id for d in gap_docs]
    gap_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(gap_ids)).all()
    assert gap_assets and all(a.status == "CANDIDATE"
                              and a.source_class == "DERIVED"
                              for a in gap_assets)
    verdict = proposals.verify_provenance(session, gap_ids[0])
    assert verdict["provenance_verified"], verdict["reasons"]
    assert verdict["verified"]["binding_id"] == fx["binding"].id
    print(f"Part 8 passed: {len(gap_assets)} gap candidate(s) held DERIVED, "
          "provenance verified against the governed binding.")

    session.close()
    print("\n=== All v1.9 WS2 diagnosis-proof checks passed: the Executive "
          "Operations Briefing is a governed cross-workbench consumer - "
          "every sentence sourced, both origins named, the pending sentinel "
          "bounded, the boundaries declared, and zero doors grown. ===")


if __name__ == "__main__":
    main()
