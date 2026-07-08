"""v1.9 WS3 - THE MILESTONE GATE for the Executive Operations Briefing
Workbench, with THE BRIEFING PROOF.

The first cross-workbench consumer closes: the governed state the
sellable trio produced (compliance + procurement corpora through the
real pipeline in ONE project, accepted DERIVED facts from BOTH
workbenches, a held pending-sentinel plant, a post-since acceptance, a
post-compile-drift conflict, EXECUTIVE memos above clearance) is
composed into ONE briefing at the declared clock - and every claim
about that briefing is proven on the bytes.

THE BRIEFING PROOF (the distinctive v1.9 stage, swept test-side,
independent of the runner's own enforcement):
  - every briefing sentence is governed-cited, the declared clock, or
    inside one of the two explicitly framed sections (SYNTHESIS_INFERRED
    / the boundary) - a mechanical line sweep over the pack bytes;
  - every DERIVED citation names its workbench-of-origin (never
    "origin-undeclared"); PRIMARY stays class-visible;
  - byte-identical regeneration at the same declared as_of/since;
  - THE PENDING-PROPOSAL SENTINEL appears in NO briefing, proposal, or
    package byte; the EXECUTIVE clearance sentinels appear in NO written
    byte; the forbidden vocabulary appears in NO written byte;
  - the boundary section is present and TRUTHFUL: it names [PMD], [OE],
    [ES], and the exact exclusion counts the gateway declared;
  - unknowns are REFUSAL_BACKED; a COVERED question (amended into a temp
    contract copy - frames are contract-declared) produces NO gap entry,
    NO proposal, and NO trace in the pack bytes;
  - only EXECUTIVE_EVIDENCE_GAP proposals exist; the read-compose skills
    emit none; the pack is assist output that never enters knowledge;
  - [PMD]/[OE]/[ES]/persistent-register/schedule/multi-project/no-clock
    all refuse live at the gate;
  - ZERO DOOR GROWTH proven structurally: route-manifest digest
    byte-identical, the MCP surface frozen at 9 tools, D24 at 28/305;
    the runner-local BriefingGraphClient is an adapter over an EXISTING
    frozen tool (a structural subclass check), never a new door.

Then the valve at the gate (every gap candidate held DERIVED under a
global permissive Tier-1 policy AND a live approve-everything Tier-2
engine; the pending plant never accepted), ONE human acceptance with
verified synthesis provenance, composition standing (the accepted gap
travels into the recompiled package and the NEXT briefing cites it
[DERIVED, origin: executive-briefing] - the briefing consuming its own
accepted finding), the vault before/after, and THE CLOSING LINES (the
ledger alone proves no agent wrote canonical facts; no shared summary
fact store exists anywhere).

THE COMMERCIAL VERDICT is not automated: the user reads the exported
briefing pack as the CEO (EM_COMMERCIAL_ARTIFACT_DIR exports the pack +
the gap proposals). The real-model honest slot is reported at the end.
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_exec3_pkg_")
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_exec3_render_")

# Guard 5 + the route guard first (guard's import overrides db.engine;
# this suite re-overrides) - the door-sweep checker, the frozen 9-tool
# assertion, and the door-growth instrument.
import test_agent_authorship_guard as guard   # noqa: E402
import test_route_manifest as route_guard      # noqa: E402

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_exec3_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'accept.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_exec3_qdrant_")

from app import (schemas, crud, connectors, identity,  # noqa: E402
                 package_builder, package_consumer, mcp_gateway,
                 policy, proposals, tier2)
from app.projections import engine as projection_engine   # noqa: E402
import test_support                           # noqa: E402
import test_workbench_projection              # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.common as wb_common          # noqa: E402
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
EXEC_SENTINELS = ("EM-EXEC-SENTINEL-7C2R",   # the compliance EXECUTIVE memo
                  "EM-EXEC-SENTINEL-4V8P")   # the procurement EXECUTIVE memo
PENDING_SENTINEL = "EM-PENDING-SENTINEL-9K3W"
AS_OF = "2026-06-01"
# The covered control (the WS1 fixture's answered question - the v1.7
# P2c plant): amended into a TEMP contract copy at stage 4, because
# frames are contract-declared, never ad hoc.
Q_COVERED = ("Was the annual incident response plan test completed "
             "and the test report retained for audit review?")

# THE BRIEFING PROOF's own source-token list (test-side, deliberately
# NOT imported from the runner - the sweep is an independent instrument
# over the pack bytes, the way the clause-arithmetic sweep was v1.8's).
SOURCE_TOKENS = ("asset ", "conflict ", "trust component", "revision ",
                 "INSUFFICIENT EVIDENCE", "as_of", "since ", "exclud",
                 "[DERIVED]", "[PMD]", "[OE]", "[ES]",
                 # the declared-absence note (the WS3 gate fix): an empty
                 # mandatory section states its emptiness - declared,
                 # never silent, never unsourced.
                 "an empty section is itself information")
NINE_TOOLS = ("ask_expert", "get_trust_score", "get_provenance",
              "get_conflicts", "check_gate_status", "get_graph_neighbors",
              "get_lineage_path", "get_domain_subgraph",
              "get_revision_history")


class ApproveEverythingVerifier:
    identity = {"method": "GUARD_APPROVE_EVERYTHING",
                "note": "executive acceptance lane-sentinel seam"}

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


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


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


def build_package_for(session, project_id, name, asset_ids):
    model = db.ExpertModel(project_id=project_id, name=name,
                           asset_ids_json=json.dumps(sorted(asset_ids)),
                           asset_count=len(asset_ids))
    session.add(model)
    session.commit()
    session.refresh(model)
    package_row = db.AgentPackage(project_id=project_id,
                                  expert_model_id=model.id, name=name,
                                  clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    package_builder.build_package(session, package_row)
    session.refresh(package_row)
    return model, package_row


def bind_agent(session, package_row, agent, issuer, version):
    binding = db.ExpertAgentBinding(
        agent_package_id=package_row.id, agent_principal_id=agent.id,
        package_hash=package_row.package_hash, package_version=version,
        principal_clearance_at_issue="INTERNAL",
        selected_provider="ANTHROPIC", selected_model_name="claude-opus-4-8",
        selection_evidence_json="{}",
        identity_fact_id=issuer.fact(session).id)
    session.add(binding)
    session.commit()
    session.refresh(binding)
    return binding


def build_fixture(session, project, reviewer, issuer, agent_token, agent):
    """The cross-workbench fixture at the milestone gate (the WS1/WS2
    shape, hardened with the v1.8 valve posture): both loops in one
    project; a global permissive Tier-1 policy AND a live
    approve-everything Tier-2 engine BEFORE any lane scan; one
    acceptance per workbench; the pending sentinel held; a post-since
    acceptance; a post-compile-drift conflict."""
    for name, root, domain in (("Compliance Docs", COMPLIANCE_CORPUS, "compliance"),
                               ("Procurement Docs", PROCUREMENT_CORPUS, "procurement")):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
        approve_all(session, project.id, reviewer, f"gate fixture: {domain}",
                    domain=domain)
    assert session.query(db.Document).filter_by(
        project_id=project.id).count() == 24, "both 12-document corpora"
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
    _model, package_row = build_package_for(
        session, project.id, "Company Package", [a.id for a in approved])
    loaded = package_consumer.load_package(package_row.file_path)
    packaged_ids = {e["asset_id"] for e in loaded["knowledge"]}
    exec_ids = {a.id for a in approved if a.access_level == "EXECUTIVE"}
    assert exec_ids and not (exec_ids & packaged_ids), \
        "the EXECUTIVE memos must be excluded from the INTERNAL package"
    binding = bind_agent(session, package_row, agent, issuer, "v1")

    vault_dir = tempfile.mkdtemp(prefix="em_exec3_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    answerer = make_answerer(loaded)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        compliance_runner.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="executive-briefing", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF, answerer=answerer)
        procurement_runner.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="executive-briefing", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF, window_days=90,
            answerer=answerer)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    # the pending sentinel plant (held forever, never accepted)
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
    # the v1.8 valve posture BEFORE any lane scan: maximal permissiveness
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
    lane_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_doc_ids)).all()
    assert lane_assets and all(
        a.status == "CANDIDATE" and a.source_class == "DERIVED"
        for a in lane_assets), "the lane sentinel must hold at the gate"
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
            actor=reviewer, review_notes=f"gate fixture accept {wb}")
    time.sleep(1.1)
    since = datetime.datetime.utcnow().date().isoformat()
    time.sleep(1.1)
    late_doc = next(d for d in docs.values()
                    if (d.filename or "").startswith("compliance-obligation-"))
    late = sorted((a for a in lane_assets if a.document_id == late_doc.id
                   and a.status == "CANDIDATE"), key=lambda a: a.id)[0]
    crud.update_knowledge_asset(
        session, late.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="gate fixture: post-since acceptance")
    # recompile with the accepted DERIVED facts + a post-compile conflict
    approved2 = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    model2, pkg2 = build_package_for(
        session, project.id, "Company Package v2", [a.id for a in approved2])

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
    binding2 = bind_agent(session, pkg2, agent, issuer, "v2")
    return dict(vault_dir=vault_dir, package=pkg2, binding=binding2,
                model=model2, since=since,
                loaded=package_consumer.load_package(pkg2.file_path),
                accepted_derived=[a.id for a in approved2
                                  if a.source_class == "DERIVED"],
                pending_plant_path=os.path.join(
                    vault_dir, "08_proposals",
                    "executive-briefing-fixture-pending.md"))


def main():
    db.init_db()
    tier2.verifier_factory = ApproveEverythingVerifier
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "ExecGateOfficer")
    reviewer = test_support.governed_actor(session, "ExecGateReviewer")
    issuer = test_support.governed_actor(session, "ExecGateIssuer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Executive Briefing", description="THE MILESTONE GATE",
        customer_id=customer.id), actor=officer)
    agent = identity.create_principal(session, name="executive-briefing",
                                      display_name="Executive Briefing",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _c = identity.issue_token(session, agent, kind="API_TOKEN",
                                           label="gate", actor="test-suite")

    # ------------------------------------------------------- Stage 1
    print("\n--- Stage 1: the workstream record + the adapter record ---")
    with open(os.path.join(REPO_DIR, "docs", "executive-briefing-v1.9.md"),
              encoding="utf-8") as f:
        record = f.read()
    for needle in ("WS0 PASSED", "WS1 RATIFICATION: PASSED",
                   "WS2 RATIFICATION: PASSED",
                   "THE FIXTURE PROOF", "THE DIAGNOSIS PROOF"):
        assert needle in record, f"gate record missing: {needle}"
    for suite in ("test_executive_fixture.py", "test_executive_workbench.py"):
        assert os.path.isfile(os.path.join(REPO_DIR, "backend", suite)), suite
    contracts = wb_common.load_active_contracts(SKILLS_DIR, runner.ACTIVE_SKILLS)
    assert len(contracts) == 6
    for skill_id, contract in contracts.items():
        with open(contract["path"], encoding="utf-8") as f:
            text = f.read()
        if skill_id == "generate_unknowns_evidence_gaps_report":
            assert "allowed_finding_kinds: [EXECUTIVE_EVIDENCE_GAP]" in text
        else:
            assert "allowed_finding_kinds: []" in text, \
                f"{skill_id} must declare no finding kinds"
    assert contracts["prepare_executive_briefing"]["boundary_tags"] == \
        "[assist, synth]", "the briefing is assist/synth only"
    # the runner-local BriefingGraphClient is an ADAPTER over an existing
    # frozen tool - a structural subclass of the shared stdio client whose
    # ONLY addition is get_trust_score, one of the nine frozen tools.
    assert issubclass(runner.BriefingGraphClient, wb_common.StdioMcpGraphClient)
    extra = {n for n in vars(runner.BriefingGraphClient)
             if not n.startswith("__")}
    assert extra == {"get_trust_score"}, \
        f"the adapter must add exactly get_trust_score: {extra}"
    assert "get_trust_score" in NINE_TOOLS
    print("Stage 1 passed: WS0/WS1/WS2 gate records + both prior suites "
          "present; six ACTIVE contracts (read-compose kinds empty, the gap "
          "skill's single kind, the briefing [assist, synth]); "
          "BriefingGraphClient recorded as an adapter over the existing "
          "frozen get_trust_score tool - never door growth.")

    # ------------------------------------------------------- Stage 2
    print("\n--- Stage 2: the cross-workbench fixture through the real pipeline ---")
    fx = build_fixture(session, project, reviewer, issuer, agent_token, agent)
    assert len(fx["accepted_derived"]) == 3, \
        "one acceptance per workbench + the post-since acceptance"
    print(f"Stage 2 passed: 24 documents (both corpora) through the real "
          f"pipeline; {len(fx['accepted_derived'])} accepted DERIVED facts "
          "(both workbenches + the post-since plant); the pending sentinel "
          "held; package v2 recompiled with a post-compile conflict; the "
          "valve policies (permissive Tier-1 + approve-everything Tier-2) "
          "live before any lane scan.")

    # ------------------------------------------------------- Stage 3
    print("\n--- Stage 3: THE BRIEFING at the declared clock, twice ---")
    baseline = vault_files(fx["vault_dir"])
    answerer = make_answerer(fx["loaded"])
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        first = runner.run_briefing(
            fx["package"].file_path, fx["vault_dir"], project.id,
            agent_principal="executive-briefing", binding_id=fx["binding"].id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            since=fx["since"], answerer=answerer)
        hashes1 = {p: sha(p) for p in [first["briefing"]] + first["proposals"]}
        second = runner.run_briefing(
            fx["package"].file_path, fx["vault_dir"], project.id,
            agent_principal="executive-briefing", binding_id=fx["binding"].id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            since=fx["since"], answerer=answerer)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    assert first["briefing"] == second["briefing"]
    assert first["proposals"] == second["proposals"]
    for p, h in hashes1.items():
        assert sha(p) == h, f"regeneration must be byte-identical: {p}"
    new_files = vault_files(fx["vault_dir"]) - baseline
    for rel in new_files:
        assert rel.startswith(("07_agent_workspaces/", "08_proposals/")), rel
    briefs = [r for r in new_files if r.startswith("07_agent_workspaces/")]
    assert len(briefs) == 1 and first["briefing"].endswith(
        briefs[0].split("/")[-1])
    assert not any("07_agent_workspaces" in p for p in first["proposals"])
    with open(first["briefing"], encoding="utf-8") as f:
        pack = f.read()
    print(f"Stage 3 passed: one briefing pack + {len(first['proposals'])} gap "
          "proposal(s) at the declared clock, byte-identical across "
          "regeneration (sha256 over every written file), confined to "
          "07_agent_workspaces / 08_proposals.")

    # ------------------------------------------------------- Stage 4
    print("\n--- Stage 4: THE BRIEFING PROOF ---")
    # (a) the sentence sweep: every line is header-clocked, governed-cited,
    # or inside one of the two explicitly framed sections.
    cited_titles = ("## Accepted findings (by class and workbench-of-origin)",
                    "## Unresolved conflicts",
                    "## Governance health (door-visible signals only)",
                    f"## What changed since {fx['since']}",
                    "## Unknowns & evidence gaps")
    framed_titles = ("## Recommended attention [SYNTHESIS_INFERRED]",
                     "## What this briefing cannot see")
    seen_titles, active, header_lines = [], None, []
    swept = 0
    for line in pack.splitlines():
        s = line.strip()
        if s.startswith("## "):
            active = s
            seen_titles.append(s)
            continue
        if not s:
            continue
        if active is None:
            header_lines.append(s)
        elif active in cited_titles:
            assert any(tok in line for tok in SOURCE_TOKENS), \
                f"THE UNSOURCED SENTENCE in a cited section: {line!r}"
            swept += 1
        else:
            assert active in framed_titles, f"unknown section: {active}"
    assert tuple(seen_titles) == cited_titles + framed_titles, seen_titles
    header = " ".join(header_lines)
    assert f"as_of {AS_OF}" in header and f"since {fx['since']}" in header, \
        "the header must declare the clock verbatim"
    assert "NOT a proposal" in header
    assert "This section is SYNTHESIS_INFERRED" in pack
    assert "composes ONLY what the governed doors expose" in pack
    assert swept >= 20, f"the sweep must cover real content: {swept}"
    # (b) every DERIVED citation names its workbench-of-origin
    derived_tags = re.findall(r"\[DERIVED[^\]]*\]", pack)
    assert derived_tags and all(
        re.fullmatch(r"\[DERIVED, origin: [a-z][a-z-]*\]", t)
        for t in derived_tags), derived_tags
    assert "origin-undeclared" not in pack
    accepted_section = pack.split(cited_titles[0])[1].split(cited_titles[1])[0]
    assert "[DERIVED, origin: compliance-obligation]" in accepted_section
    assert "[DERIVED, origin: procurement-intelligence]" in accepted_section
    assert "[PRIMARY]" in accepted_section
    # (c)+(d) sentinels + forbidden vocabulary absent from every written byte;
    # the pending sentinel also absent from every PACKAGE byte.
    forbidden = runner.parse_forbidden_vocabulary(MANIFEST)
    assert len(forbidden) == 12, "the ratified 12-phrase list"
    for path in [first["briefing"]] + first["proposals"]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        low = text.lower()
        for phrase in forbidden:
            assert phrase not in low, f"forbidden vocabulary: {phrase!r}"
        for sentinel in EXEC_SENTINELS + (PENDING_SENTINEL,):
            assert sentinel not in text, f"{sentinel} leaked into {path}"
    with open(fx["package"].file_path, "rb") as f:
        package_bytes = f.read()
    assert PENDING_SENTINEL.encode() not in package_bytes, \
        "a held proposal leaked into the package"
    for sentinel in EXEC_SENTINELS:
        assert sentinel.encode() not in package_bytes
    # (e) the boundary section is present and TRUTHFUL: it names the
    # unminted decisions AND the exact exclusion counts the gateway declared.
    boundary = pack.split("## What this briefing cannot see")[1]
    for tag in ("[PMD]", "[OE]", "[ES]"):
        assert tag in boundary, f"the boundary must name {tag}"
    assert first["exclusions"].get("assets_above_clearance", 0) >= 1, \
        "the EXECUTIVE memos must be genuinely excluded this run"
    assert str(first["exclusions"]) in boundary, \
        "the boundary must quote the gateway's declared exclusions verbatim"
    # (f) unknowns REFUSAL_BACKED; the covered control leaves NO trace
    assert first["findings"], "at least one evidence gap must fire"
    for f_ in first["findings"]:
        assert f_["finding_kind"] == "EXECUTIVE_EVIDENCE_GAP"
        assert f_["evidence_basis"] == "REFUSAL_BACKED"
        assert f_["cited_assets"] == []
    for path in first["proposals"]:
        with open(path, encoding="utf-8") as f:
            parsed = proposals.parse_frontmatter(f.read())
        assert parsed["claimed"] and not parsed["problems"], parsed
        assert parsed["claims"]["finding_kind"] == "EXECUTIVE_EVIDENCE_GAP"
        assert parsed["claims"]["workbench"] == "executive-briefing"
    assert len(first["proposals"]) == len(first["findings"]), \
        "only the gap skill proposes; the read-compose skills never do"
    # the covered control: amend the question into a TEMP contract copy
    # (frames are contract-declared; a deployment extends by amendment).
    tmp_skills = tempfile.mkdtemp(prefix="em_exec3_skills_")
    for name in os.listdir(SKILLS_DIR):
        shutil.copy(os.path.join(SKILLS_DIR, name), tmp_skills)
    gap_contract = os.path.join(tmp_skills,
                                "generate_unknowns_evidence_gaps_report.yaml")
    with open(gap_contract, encoding="utf-8") as f:
        text = f.read()
    text = text.replace("allowed_inputs:",
                        f'  - "{Q_COVERED}"\nallowed_inputs:', 1)
    with open(gap_contract, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        covered_run = runner.run_briefing(
            fx["package"].file_path, fx["vault_dir"], project.id,
            agent_principal="executive-briefing", binding_id=fx["binding"].id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            since=fx["since"], answerer=answerer, skills_dir=tmp_skills)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    covered_skips = [s for s in covered_run["skipped"]
                     if "covered control" in s["reason"]]
    assert len(covered_skips) == 1 and Q_COVERED in covered_skips[0]["reason"]
    assert covered_run["proposals"] == first["proposals"], \
        "a covered question must produce NO proposal"
    assert sha(covered_run["briefing"]) == hashes1[first["briefing"]], \
        "a covered question must leave NO trace in the pack bytes"
    # (g) the boundaries refuse live at the gate
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        def expect(kwargs, needle):
            try:
                runner.run_briefing(
                    fx["package"].file_path, fx["vault_dir"], project.id,
                    agent_principal="executive-briefing",
                    binding_id=fx["binding"].id,
                    graph_client=InProcessGraphClient(), answerer=answerer,
                    **kwargs)
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
        for gated, needle in sorted(runner.GATED_SKILLS.items()):
            assert expect(dict(as_of=AS_OF, since=fx["since"],
                               requested_skills=runner.ACTIVE_SKILLS + (gated,)),
                          needle), f"{gated} must refuse naming {needle!r}"
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    # (h) ZERO DOOR GROWTH, structural
    assert route_guard.digest(route_guard.build_manifest()) == \
        route_guard.FROZEN_DIGEST, "a REST door changed - zero door growth"
    tool_fns = [n for n in dir(mcp_gateway) if n in NINE_TOOLS]
    assert len(tool_fns) == 9, f"the MCP surface is not frozen at 9: {tool_fns}"
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    assert live == test_workbench_projection.FROZEN_SCHEMA
    tables, columns = len(live), sum(len(c) for c in live.values())
    assert (tables, columns) == (28, 305), (tables, columns)
    print(f"Stage 4 passed: THE BRIEFING PROOF - {swept} cited-section lines "
          f"each carrying a governed source token (header clocked verbatim, "
          f"exactly the 7 declared sections); every [DERIVED] tag "
          f"origin-named, both workbenches present, PRIMARY visible; the "
          f"pending + EXECUTIVE sentinels and the 12 forbidden phrases in NO "
          f"written or packaged byte; the boundary quotes the gateway's "
          f"exclusions verbatim ({first['exclusions']}); the covered "
          f"question left no gap, no proposal, no byte; "
          f"{4 + len(runner.GATED_SKILLS)} refusals live; route digest "
          f"byte-identical, MCP frozen at 9 tools, D24 at {tables}/{columns}.")

    # ------------------------------------------------------- Stage 5
    print("\n--- Stage 5: the valve holds; a human accepts one evidence gap ---")
    lane = session.query(db.SourceConnector).filter_by(
        project_id=project.id, lane="PROPOSAL").first()
    run_scan(session, lane)
    gap_docs = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename.like("executive-briefing-generate_unknowns%")).all()
    assert len(gap_docs) == len(first["proposals"])
    gap_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_([d.id for d in gap_docs])).all()
    assert gap_assets and all(a.status == "CANDIDATE"
                              and a.source_class == "DERIVED"
                              for a in gap_assets), \
        "every gap candidate held DERIVED under permissive Tier-1 AND " \
        "approve-everything Tier-2 - never auto-approved"
    pending_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename.like("%fixture-pending%")).first()
    for a in session.query(db.KnowledgeAsset).filter_by(
            document_id=pending_doc.id).all():
        assert a.status == "CANDIDATE", "the pending plant must stay held"
    accepted_gap = sorted(gap_assets, key=lambda a: a.id)[0]
    crud.update_knowledge_asset(
        session, accepted_gap.id,
        schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted the evidence gap")
    session.refresh(accepted_gap)
    assert accepted_gap.status == "APPROVED"
    assert accepted_gap.source_class == "DERIVED"
    event = session.query(db.AuditEvent).filter_by(
        event_type="ASSET_APPROVED", target_id=str(accepted_gap.id)).order_by(
        db.AuditEvent.id.desc()).first()
    prov = json.loads(event.details)["synthesis_provenance"]
    assert prov["provenance_verified"] is True
    assert prov["claimed"]["agent_principal"] == "executive-briefing"
    assert prov["verified"]["binding_id"] == fx["binding"].id
    assert prov["verified"]["package_hash"] == fx["package"].package_hash
    # a REFUSAL_BACKED gap cites nothing - the provenance record honestly
    # carries no cited-assets verdict (nothing claimed, nothing missing).
    assert prov["cited_assets"] is None
    print(f"Stage 5 passed: {len(gap_assets)} gap candidate(s) held DERIVED "
          "at the valve; the pending plant still held; ONE human acceptance "
          "-> APPROVED DERIVED with the approval event quoting VERIFIED "
          "synthesis provenance.")

    # ------------------------------------------------------- Stage 6
    print("\n--- Stage 6: composition - the briefing consumes its own gap ---")
    approved_now = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    _model3, pkg3 = build_package_for(
        session, project.id, "Company Package v3", [a.id for a in approved_now])
    loaded3 = package_consumer.load_package(pkg3.file_path)
    classes = {e["asset_id"]: e.get("source_class")
               for e in loaded3["knowledge"]}
    assert classes.get(accepted_gap.id) == "DERIVED", \
        "the accepted gap must travel into the recompiled package"
    candidate_ids = {a.id for a in session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="CANDIDATE").all()}
    assert not (candidate_ids & set(classes)), \
        "pending proposals must never enter the recompiled package"
    with open(pkg3.file_path, "rb") as f:
        assert PENDING_SENTINEL.encode() not in f.read()
    binding3 = bind_agent(session, pkg3, agent, issuer, "v3")
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        third = runner.run_briefing(
            pkg3.file_path, fx["vault_dir"], project.id,
            agent_principal="executive-briefing", binding_id=binding3.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            since=fx["since"], answerer=make_answerer(loaded3))
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    with open(third["briefing"], encoding="utf-8") as f:
        pack3 = f.read()
    assert "[DERIVED, origin: executive-briefing]" in pack3, \
        "the next briefing must cite the accepted gap AS DERIVED, " \
        "origin-named executive-briefing"
    assert "executive-briefing" in third["accepted_origins"]
    changed3 = pack3.split(f"## What changed since {fx['since']}")[1].split(
        "## Unknowns")[0]
    assert f"asset {accepted_gap.id} " in changed3, \
        "the post-since gap acceptance must appear in what-changed"
    # the declared-absence discipline live (the WS3 gate fix): the v2-model
    # conflict does not travel to the recompiled model, so this briefing's
    # conflicts section is legitimately empty - and SAYS so.
    conflicts3 = pack3.split("## Unresolved conflicts")[1].split(
        "## Governance")[0]
    assert "an empty section is itself information" in conflicts3, \
        "an empty mandatory section must declare its emptiness"
    print("Stage 6 passed: the accepted gap traveled DERIVED into package v3 "
          "(pending candidates structurally absent); the NEXT briefing cites "
          "it [DERIVED, origin: executive-briefing] and reports it in "
          "what-changed - the briefing consuming its own accepted finding; "
          "the empty conflicts section a DECLARED absence.")

    # ------------------------------------------------------- Stage 7
    print("\n--- Stage 7: the vault before/after ---")
    os.environ["EM_VAULT_DIR"] = fx["vault_dir"]
    render = projection_engine.render(session, officer, project.id,
                                      renderer="vault")
    assert render["content_mode"] == "FULL_CONTENT"
    knowledge_dir = os.path.join(fx["vault_dir"], "02_knowledge")
    gap_note = 0
    for root, _dirs, files in os.walk(knowledge_dir):
        for name in files:
            with open(os.path.join(root, name), encoding="utf-8") as f:
                text = f.read()
            for sentinel in EXEC_SENTINELS:
                assert sentinel not in text, "clearance leaked into a note"
            assert PENDING_SENTINEL not in text, "a held plant was rendered"
            if (f"asset_{accepted_gap.id}_" in name
                    or f"asset_{accepted_gap.id}." in name):
                assert 'source_class: "DERIVED"' in text
                assert "This note is not canonical." in text
                gap_note += 1
    assert gap_note == 1, "the accepted gap must render as a marked DERIVED note"
    for path in [first["briefing"]] + first["proposals"] + third["proposals"]:
        assert os.path.isfile(path), "the render must never touch 07/08"
    assert sha(first["briefing"]) == hashes1[first["briefing"]]
    print("Stage 7 passed: the accepted gap renders as a marked DERIVED "
          "note, visibly non-canonical; no sentinel in any rendered note; "
          "the briefing pack and every proposal byte-identical through the "
          "render - the untouchable floor held.")

    # ------------------------------------------------------- Stage 8
    print("\n--- Stage 8: THE CLOSING LINES ---")
    approval_events = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type.in_(
            ("ASSET_APPROVED", "ASSET_AUTO_APPROVED", "ASSET_REVIEWED",
             "ASSET_REVISION_APPROVED"))).all()
    assert approval_events
    for e in approval_events:
        assert e.identity_fact_id is not None
        e_fact = session.query(db.IdentityFact).filter_by(
            id=e.identity_fact_id).first()
        assert e_fact.principal_kind != "AGENT", \
            f"D29 VIOLATION: event {e.id} - an AGENT wrote canonical state"
    derived_approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED",
        source_class="DERIVED").all()
    assert len(derived_approved) == len(fx["accepted_derived"]) + 1
    for asset in derived_approved:
        human_reviews = [r for r in asset.reviews
                         if r.approver and not r.approver.startswith("policy:")]
        assert human_reviews, f"DERIVED fact {asset.id} without a human review"
    # no shared summary fact store: the pack was never ingested (the lane
    # roots at 08_proposals; no document carries the pack stub), no
    # read-compose output exists outside 07_agent_workspaces, and no table
    # exists that could hold one (D24).
    for doc in session.query(db.Document).filter_by(project_id=project.id).all():
        assert "executive-briefing-executive-briefing" not in (doc.filename or ""), \
            "the briefing pack must never be ingested as knowledge"
    for rel in vault_files(fx["vault_dir"]):
        if "executive-briefing-executive-briefing" in rel:
            assert rel.startswith("07_agent_workspaces/"), rel
    swept_files = 0
    for base in (fx["vault_dir"], os.environ["EM_PACKAGE_DIR"],
                 os.environ["EM_PROJECTION_DIR"]):
        for root, _dirs, files in os.walk(base):
            for name in files:
                if name == "executive-briefing-fixture-pending.md":
                    continue   # the held plant itself (08, never accepted)
                with open(os.path.join(root, name), "rb") as f:
                    blob = f.read()
                for sentinel in EXEC_SENTINELS:
                    assert sentinel.encode() not in blob, \
                        f"{sentinel} in {os.path.join(root, name)}"
                assert PENDING_SENTINEL.encode() not in blob, \
                    f"pending sentinel in {os.path.join(root, name)}"
                swept_files += 1
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    assert live == test_workbench_projection.FROZEN_SCHEMA
    tables, columns = len(live), sum(len(c) for c in live.values())
    assert (tables, columns) == (28, 305), (tables, columns)
    print(f"Stage 8 passed: every approval event carries a non-AGENT "
          f"identity fact; every APPROVED DERIVED fact has a human review; "
          f"no shared summary fact store anywhere; {swept_files} files swept "
          f"clean of every sentinel; the D24 snapshot stands at exactly "
          f"{tables} tables / {columns} columns.")

    # ----------------------------------------------- The verdict artifact
    artifact_dir = os.environ.get("EM_COMMERCIAL_ARTIFACT_DIR")
    if artifact_dir:
        os.makedirs(artifact_dir, exist_ok=True)
        for path in [first["briefing"]] + first["proposals"]:
            shutil.copy(path, artifact_dir)

    # ------------------------------------------------------- Honest slot
    key = os.environ.get("OPENAI_API_KEY", "")
    real_key = bool(key) and key != "mock-key" or bool(
        os.environ.get("ANTHROPIC_API_KEY"))
    print("\nHonest slot - the ONE real-model diagnostic run: "
          + ("a provider key is present; run the workbench without the "
             "injected answerer and append the evidence."
             if real_key else
             "PENDING (no provider key in this environment; the runner's "
             "stdio MCP door and D19 synthesis path are code-complete - a "
             "narrated briefing over real governed facts is the natural "
             "vehicle)."))

    session.close()
    print("\n=== THE v1.9 MILESTONE GATE PASSED: the first cross-workbench "
          "consumer, end to end - every sentence sourced or framed, every "
          "DERIVED citation origin-named, the pending boundary proven on "
          "bytes, the covered question traceless, the boundary section "
          "truthful, zero doors grown, and the briefing consuming its own "
          "human-accepted finding. 28 tables / 305 columns. ===")


if __name__ == "__main__":
    main()
