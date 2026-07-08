"""v2.1 WS3 - THE MILESTONE GATE for the Contract Intelligence
Workbench, with THE SHARED ENGINE PROOF.

The full commercial loop, once, end to end: both governed corpora enter
through the real pipeline -> PRIMARY facts human-approved into two
domains (the EXECUTIVE memos seeded above package clearance) -> an
INTERNAL package bound to a real AGENT principal -> THE ENGINE
diagnoses at the declared as_of, honoring the three ratified contracts
-> register candidates land in /08_proposals -> the valve holds every
candidate DERIVED under a global permissive Tier-1 policy AND a live
approve-everything Tier-2 engine -> a human accepts register entries
across MULTIPLE clause classes plus one metadata gap -> APPROVED
DERIVED facts with verified synthesis provenance.

THEN THE SHARED ENGINE PROOF (the distinctive v2.1 stage):
  - ONE extraction contract: every accepted register entry claims skill
    extract_contract_clauses, and the accepted set spans >= 3 pinned
    clause classes;
  - TWO consumers, UNCHANGED: the v1.7 compliance and v1.8 procurement
    runners - whose sources never name the engine - each cite an
    accepted register entry BY ASSET ID;
  - ZERO DRIFT BY ID: the convergence entry's id appears in BOTH
    consumers' citation sets, and the provenance chain resolves
    consumer finding -> register entry (origin contract-intelligence)
    -> the PRIMARY contract clause whose content carries the verbatim
    text;
  - NO SHARED FACT STORE, proven three ways: (a) D24 byte-identical at
    28/305 - no table exists to hold one; (b) THE EXACTLY-TWO-COPIES
    CHECK - the convergence clause exists in APPROVED knowledge exactly
    twice by design (the PRIMARY source + the accepted register entry)
    and consumer runs add ZERO approved copies; (c) THE WORKSPACE
    DELETION TEST - deleting the engine's ENTIRE output surface (the
    brief and every register proposal file) changes NEITHER consumer's
    findings by one byte of citation: the feed lives in governed facts
    alone;
  - THE REGISTER DISTINCTION on the bytes: the brief (synthesis) never
    enters knowledge (no document, no asset carries it); the
    legal-conclusion vocabulary appears in NO written byte anywhere;
  - the held register plant (never accepted) reaches no package byte,
    no consumer finding, no brief;
  - THE CLOSING LINES: every approval event non-AGENT; every APPROVED
    DERIVED fact human-reviewed; the EXECUTIVE sentinels absent from
    every written byte; route manifest 88 at its ratified digest; MCP
    9; D24 at 28 tables / 305 columns.

THE COMMERCIAL VERDICT is not automated: the user reads the exported
register + brief as GENERAL COUNSEL / the procurement owner
(EM_COMMERCIAL_ARTIFACT_DIR exports them). The real-model honest slot
is reported at the end.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_ci3_pkg_")
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_ci3_render_")

import test_route_manifest as route_guard      # noqa: E402

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_ci3_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'accept.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_ci3_qdrant_")

from app import (schemas, crud, connectors, identity,  # noqa: E402
                 package_builder, package_consumer, mcp_gateway,
                 policy, proposals, tier2)
import test_support                           # noqa: E402
import test_workbench_projection              # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.contract_intelligence.runner as runner   # noqa: E402
import workbench.compliance_obligation.runner as compliance_runner   # noqa: E402
import workbench.procurement_intelligence.runner as procurement_runner  # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "contract_intelligence")
COMPLIANCE_CORPUS = os.path.join(REPO_DIR, "workbench",
                                 "compliance_obligation", "corpus")
PROCUREMENT_CORPUS = os.path.join(REPO_DIR, "workbench",
                                  "procurement_intelligence", "corpus")
EXEC_SENTINELS = ("EM-EXEC-SENTINEL-7C2R", "EM-EXEC-SENTINEL-4V8P")
HELD_SENTINEL = "EM-REGISTER-HELD-8W2K"
AS_OF = "2026-06-01"
CONVERGENCE_FRag = "subprocessor"


class ApproveEverythingVerifier:
    identity = {"method": "GUARD_APPROVE_EVERYTHING",
                "note": "contract acceptance lane-sentinel seam"}

    def check(self, candidate, corpus):
        return {"pairs_checked": len(corpus), "pairs_dropped": 0,
                "contradictions": []}


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
            return {"answer": f"Per the governed evidence (asset_id "
                              f"{best[1]['asset_id']}): {best[1].get('content')}",
                    "cited_asset_ids": [best[1]["asset_id"]], "evidence": sel}
        return {"answer": "INSUFFICIENT EVIDENCE - the governed evidence "
                          "offered does not contain the answer to this "
                          "question.", "cited_asset_ids": [], "evidence": sel}
    return answer


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


def consumer_citation_fingerprint(result):
    """The consumer's citation surface, as a deterministic fingerprint:
    sorted (finding_kind, tuple(cited_assets)) pairs - what the consumer
    CITES, independent of file paths."""
    pairs = sorted((f["finding_kind"], tuple(sorted(f.get("cited_assets", ()))))
                   for f in result["findings"])
    return hashlib.sha256(repr(pairs).encode()).hexdigest(), pairs


def main_test():
    db.init_db()
    tier2.verifier_factory = ApproveEverythingVerifier
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "CI3Officer")
    reviewer = test_support.governed_actor(session, "CI3Reviewer")
    issuer = test_support.governed_actor(session, "CI3Issuer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Contract Intelligence", description="THE MILESTONE GATE",
        customer_id=customer.id), actor=officer)
    agent = identity.create_principal(session, name="contract-intelligence",
                                      display_name="Contract Intelligence",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _c = identity.issue_token(session, agent, kind="API_TOKEN",
                                           label="gate", actor="test-suite")

    # ------------------------------------------------------- Stage 1
    print("\n--- Stage 1: the workstream record + the engine's isolation ---")
    with open(os.path.join(REPO_DIR, "docs", "contract-intelligence-v2.1.md"),
              encoding="utf-8") as f:
        record = f.read()
    for needle in ("WS0 PASSED", "WS1 RATIFICATION: PASSED",
                   "WS2 RATIFICATION: PASSED",
                   "THE EXTRACTION PRECONDITION PROOF", "THE DIAGNOSIS PROOF"):
        assert needle in record, f"gate record missing: {needle}"
    for suite in ("test_contract_corpus.py", "test_contract_workbench.py"):
        assert os.path.isfile(os.path.join(REPO_DIR, "backend", suite))
    for consumer in ("compliance_obligation/runner.py",
                     "procurement_intelligence/runner.py"):
        with open(os.path.join(REPO_DIR, "workbench", consumer),
                  encoding="utf-8") as f:
            assert "contract_intelligence" not in f.read(), \
                f"{consumer} must never name the engine"
    print("Stage 1 passed: WS0/WS1/WS2 records + both prior suites present; "
          "neither consumer's source names the engine.")

    # ------------------------------------------------------- Stage 2
    print("\n--- Stage 2: the corpora through the real pipeline ---")
    for name, root, domain in (("Compliance Docs", COMPLIANCE_CORPUS, "compliance"),
                               ("Procurement Docs", PROCUREMENT_CORPUS, "procurement")):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
        approve_all(session, project.id, reviewer, f"gate: {domain}",
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
    _m, pkg = build_package_for(session, project.id, "Contract Package",
                                [a.id for a in approved])
    loaded = package_consumer.load_package(pkg.file_path)
    exec_ids = {a.id for a in approved if a.access_level == "EXECUTIVE"}
    assert exec_ids and not (exec_ids & {e["asset_id"]
                                         for e in loaded["knowledge"]})
    binding = bind_agent(session, pkg, agent, issuer, "v1")
    vault_dir = tempfile.mkdtemp(prefix="em_ci3_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    print(f"Stage 2 passed: {len(approved)} PRIMARY facts into two domains; "
          "the EXECUTIVE memos above package clearance; INTERNAL package + "
          "real AGENT binding.")

    # ------------------------------------------------------- Stage 3
    print("\n--- Stage 3: THE ENGINE diagnoses at the declared clock ---")
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        diagnosis = runner.run_diagnostic(
            pkg.file_path, vault_dir, project.id,
            agent_principal="contract-intelligence", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    clause_findings = [f for f in diagnosis["findings"]
                       if f["finding_kind"] == "CONTRACT_CLAUSE"]
    gap_findings = [f for f in diagnosis["findings"]
                    if f["finding_kind"] == "CONTRACT_METADATA_GAP"]
    assert len(clause_findings) >= 10 and gap_findings
    classes_proposed = {f["clause_class"] for f in clause_findings}
    assert len(classes_proposed) >= 4
    # the held register plant (never accepted)
    with open(os.path.join(vault_dir, "08_proposals",
                           "contract-intelligence-extract_contract_clauses-"
                           "0f0f0f0f0f0f.md"),
              "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join([
            "---", "em_proposal: 1",
            "agent_principal: contract-intelligence",
            f"binding_id: {binding.id}",
            f"package_hash: {pkg.package_hash}",
            "workbench: contract-intelligence",
            "skill: extract_contract_clauses", "skill_version: 1",
            "finding_kind: CONTRACT_CLAUSE",
            "evidence_basis: EXCERPT_BACKED", "cited_assets: ", "---", "",
            "# Held register plant", "",
            f"This held candidate carries the sentinel {HELD_SENTINEL} and",
            "must never be accepted as knowledge.", ""]))
    print(f"Stage 3 passed: {len(clause_findings)} clause candidates across "
          f"{len(classes_proposed)} classes + {len(gap_findings)} metadata "
          f"gaps at as_of {AS_OF}; the held plant seeded.")

    # ------------------------------------------------------- Stage 4
    print("\n--- Stage 4: the valve holds under maximal permissiveness ---")
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add(db.ApprovalPolicy(project_id=project.id, name="everything",
                                  asset_types_json=all_types, enabled=True))
    session.add(db.ApprovalPolicy(project_id=project.id, name="everything-t2",
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
    print(f"Stage 4 passed: {len(lane_assets)} candidates all held DERIVED "
          "under a global permissive Tier-1 policy AND a live "
          "approve-everything Tier-2 engine - never auto-approved.")

    # ------------------------------------------------------- Stage 5
    print("\n--- Stage 5: a human builds the register (multi-class) ---")
    docs = {d.id: d for d in session.query(db.Document).filter(
        db.Document.id.in_(lane_doc_ids)).all()}
    by_id = {a.id: norm(a.content) for a in approved}

    def doc_text(d):
        with open(os.path.join(vault_dir, "08_proposals", d.filename),
                  encoding="utf-8") as f:
            return f.read()

    accepted = {}
    # the convergence clause is fragment-pinned (it carries both
    # consumers' markers); the other classes take ANY real candidate of
    # that class - the register's breadth is the claim, not a specific
    # sentence (packaged chunking may prefix headings).
    want = [("data_access", CONVERGENCE_FRag),
            ("renewal", None),
            ("payment", None),
            ("certification_obligation", None)]
    for cls, frag in want:
        matches = sorted(
            (d for d in docs.values()
             if "extract_contract_clauses" in (d.filename or "")
             and f"Clause class {cls}" in doc_text(d)
             and (frag is None or frag.lower() in doc_text(d).lower())),
            key=lambda d: d.filename or "")
        assert matches, f"no register proposal for class={cls!r} frag={frag!r}"
        doc = matches[0]
        cands = sorted((a for a in lane_assets if a.document_id == doc.id),
                       key=lambda a: a.id)
        pick = next((a for a in cands
                     if frag and frag.lower() in norm(a.content).lower()),
                    next((a for a in cands
                          if re.search(r"(must|shall|holds a current|"
                                       r"agreement)",
                                       norm(a.content), re.IGNORECASE)),
                         cands[0]))
        crud.update_knowledge_asset(
            session, pick.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=reviewer, review_notes=f"gate: register {cls}")
        session.refresh(pick)
        assert pick.status == "APPROVED" and pick.source_class == "DERIVED"
        event = session.query(db.AuditEvent).filter_by(
            event_type="ASSET_APPROVED", target_id=str(pick.id)).order_by(
            db.AuditEvent.id.desc()).first()
        prov = json.loads(event.details)["synthesis_provenance"]
        assert prov["provenance_verified"] is True
        assert prov["claimed"]["agent_principal"] == "contract-intelligence"
        assert prov["verified"]["binding_id"] == binding.id
        assert prov["cited_assets"]["missing"] == []
        accepted[cls] = pick
    # plus one metadata gap accepted as a DERIVED fact
    gap_doc = next(d for d in docs.values()
                   if "detect_missing_contract_metadata" in (d.filename or ""))
    gap_cands = sorted((a for a in lane_assets
                        if a.document_id == gap_doc.id), key=lambda a: a.id)
    gap_pick = next((a for a in gap_cands
                     if "never that the clause does not exist"
                     in norm(a.content)), gap_cands[0])
    crud.update_knowledge_asset(
        session, gap_pick.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="gate: metadata gap accepted")
    print(f"Stage 5 passed: {len(accepted)} register entries accepted across "
          f"classes {sorted(accepted)} + one metadata gap - every approval "
          "event quoting VERIFIED synthesis provenance.")

    # ------------------------------------------------------- Stage 6
    print("\n--- Stage 6: THE SHARED ENGINE PROOF ---")
    approved2 = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    _m2, pkg2 = build_package_for(session, project.id, "Contract Package v2",
                                  [a.id for a in approved2])
    binding2 = bind_agent(session, pkg2, agent, issuer, "v2")
    loaded2 = package_consumer.load_package(pkg2.file_path)
    packaged2 = {e["asset_id"] for e in loaded2["knowledge"]}
    assert all(a.id in packaged2 for a in accepted.values())
    with open(pkg2.file_path, "rb") as f:
        pkg2_bytes = f.read()
    assert HELD_SENTINEL.encode() not in pkg2_bytes, \
        "the held register plant leaked into the package"
    conv = accepted["data_access"]
    answerer = make_answerer(loaded2)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        compliance = compliance_runner.run_diagnostic(
            pkg2.file_path, vault_dir, project.id,
            agent_principal="contract-intelligence", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            answerer=answerer)
        procurement = procurement_runner.run_diagnostic(
            pkg2.file_path, vault_dir, project.id,
            agent_principal="contract-intelligence", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF, window_days=90,
            answerer=answerer)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    comp_fp, comp_pairs = consumer_citation_fingerprint(compliance)
    proc_fp, proc_pairs = consumer_citation_fingerprint(procurement)
    comp_cited = {i for _k, ids in comp_pairs for i in ids}
    proc_cited = {i for _k, ids in proc_pairs for i in ids}
    # (a) one extraction contract, >= 3 classes accepted
    assert len(accepted) >= 3
    # (b)+(c) two unchanged consumers, ZERO DRIFT BY ID
    assert conv.id in comp_cited and conv.id in proc_cited, \
        "THE CONVERGENCE: both consumers must cite the register entry by id"
    held_ids = {a.id for a in lane_assets
                if HELD_SENTINEL in norm(a.content)}
    assert held_ids and not (held_ids & (comp_cited | proc_cited)), \
        "no consumer may cite the held plant"
    # the provenance chain: register -> PRIMARY
    conv_entry = next(e for e in loaded2["knowledge"]
                      if e["asset_id"] == conv.id)
    src = (conv_entry.get("provenance") or {}).get("source_document") or ""
    assert re.match(r"^contract-intelligence-extract_contract_clauses-"
                    r"[0-9a-f]{12}\.md$", src), src
    reg_doc = next(d for d in docs.values() if d.filename == src)
    frontmatter = proposals.parse_frontmatter(doc_text(reg_doc))
    primary_ids = [int(t) for t in
                   frontmatter["claims"]["cited_assets"].split(",") if t]
    assert primary_ids and all(i in by_id for i in primary_ids)
    assert CONVERGENCE_FRag in by_id[primary_ids[0]].lower(), \
        "the PRIMARY source must carry the verbatim clause"
    # (d) NO SHARED FACT STORE - the exactly-two-copies check
    clause_norm = norm(conv_entry.get("content")).lower()
    copies = [a.id for a in approved2
              if clause_norm in norm(a.content).lower()
              or norm(a.content).lower() in clause_norm]
    assert len(copies) == 2 and set(copies) == {primary_ids[0], conv.id}, \
        f"the clause must exist in APPROVED knowledge exactly twice " \
        f"(PRIMARY + register): {copies}"
    approved_count_before = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").count()
    # (d) THE WORKSPACE DELETION TEST: erase the engine's ENTIRE output
    # surface, then re-run both consumers - citation-identical.
    deleted = 0
    for p in diagnosis["proposals"] + [diagnosis["brief"]]:
        if os.path.isfile(p):
            os.remove(p)
            deleted += 1
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        compliance_after = compliance_runner.run_diagnostic(
            pkg2.file_path, vault_dir, project.id,
            agent_principal="contract-intelligence", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            answerer=make_answerer(loaded2))
        procurement_after = procurement_runner.run_diagnostic(
            pkg2.file_path, vault_dir, project.id,
            agent_principal="contract-intelligence", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF, window_days=90,
            answerer=make_answerer(loaded2))
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    assert consumer_citation_fingerprint(compliance_after)[0] == comp_fp
    assert consumer_citation_fingerprint(procurement_after)[0] == proc_fp
    approved_count_after = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").count()
    assert approved_count_after == approved_count_before, \
        "consumer runs must create ZERO approved facts"
    print(f"Stage 6 passed: THE SHARED ENGINE PROOF - register entry "
          f"{conv.id} cited by id by BOTH unchanged consumers; provenance "
          f"chain register->PRIMARY({primary_ids[0]}) resolves; the clause "
          f"exists in APPROVED knowledge exactly TWICE by design; deleting "
          f"{deleted} engine output files changed neither consumer's "
          f"citations by one byte; zero approved facts created by consumer "
          f"runs; the held plant cited by no one.")

    # ------------------------------------------------------- Stage 7
    print("\n--- Stage 7: THE REGISTER DISTINCTION on the bytes ---")
    # the brief never entered knowledge (it was deleted above and was
    # never in a lane - assert no document ever carried its stub)
    for d in session.query(db.Document).filter_by(project_id=project.id).all():
        assert "review-brief" not in (d.filename or ""), \
            "the brief (synthesis) must never be ingested"
    forbidden = runner.parse_forbidden_vocabulary(
        os.path.join(WB_DIR, "workbench.yaml"))
    swept = 0
    for base in (vault_dir, os.environ["EM_PACKAGE_DIR"]):
        for root, _dirs, files in os.walk(base):
            for name in files:
                with open(os.path.join(root, name), "rb") as f:
                    blob = f.read()
                low = blob.decode("utf-8", errors="ignore").lower()
                for phrase in forbidden:
                    assert phrase not in low, \
                        f"legal-conclusion vocabulary in {name}: {phrase!r}"
                for sentinel in EXEC_SENTINELS:
                    assert sentinel.encode() not in blob, \
                        f"clearance sentinel in {name}"
                swept += 1
    print(f"Stage 7 passed: the brief never entered knowledge; {swept} "
          f"files swept - no legal-conclusion phrase, no EXECUTIVE "
          f"sentinel in any written byte.")

    # ------------------------------------------------------- Stage 8
    print("\n--- Stage 8: THE CLOSING LINES ---")
    approval_events = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type.in_(
            ("ASSET_APPROVED", "ASSET_AUTO_APPROVED", "ASSET_REVIEWED",
             "ASSET_REVISION_APPROVED"))).all()
    assert approval_events
    for e in approval_events:
        assert e.identity_fact_id is not None
        fact = session.query(db.IdentityFact).filter_by(
            id=e.identity_fact_id).first()
        assert fact.principal_kind != "AGENT", \
            f"D29 VIOLATION: event {e.id} - an AGENT wrote canonical state"
    derived_approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED",
        source_class="DERIVED").all()
    assert len(derived_approved) == len(accepted) + 1   # + the gap
    for asset in derived_approved:
        human_reviews = [r for r in asset.reviews
                         if r.approver and not r.approver.startswith("policy:")]
        assert human_reviews, f"DERIVED fact {asset.id} without a human review"
    assert route_guard.digest(route_guard.build_manifest()) == \
        route_guard.FROZEN_DIGEST
    assert len(route_guard.build_manifest()) == 88
    nine = ("ask_expert", "get_trust_score", "get_provenance",
            "get_conflicts", "check_gate_status", "get_graph_neighbors",
            "get_lineage_path", "get_domain_subgraph", "get_revision_history")
    assert len([n for n in dir(mcp_gateway) if n in nine]) == 9
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    assert live == test_workbench_projection.FROZEN_SCHEMA
    tables, columns = len(live), sum(len(c) for c in live.values())
    assert (tables, columns) == (28, 305), (tables, columns)
    print(f"Stage 8 passed: every approval event non-AGENT; every APPROVED "
          f"DERIVED fact human-reviewed; route manifest 88 at its ratified "
          f"digest; MCP at 9; D24 at exactly {tables}/{columns}.")

    # ----------------------------------------------- The verdict artifact
    artifact_dir = os.environ.get("EM_COMMERCIAL_ARTIFACT_DIR")
    if artifact_dir:
        os.makedirs(artifact_dir, exist_ok=True)
        # regenerate the brief for the reader (deleted by the proof above)
        os.environ["EM_AGENT_TOKEN"] = agent_token
        try:
            fresh = runner.run_diagnostic(
                pkg2.file_path, vault_dir, project.id,
                agent_principal="contract-intelligence",
                binding_id=binding2.id,
                graph_client=InProcessGraphClient(), as_of=AS_OF)
        finally:
            os.environ.pop("EM_AGENT_TOKEN", None)
        for path in [fresh["brief"]] + fresh["proposals"][:6]:
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
             "stdio MCP door and D19 synthesis path are code-complete)."))

    session.close()
    print("\n=== THE v2.1 MILESTONE GATE PASSED: one extraction contract "
          "built the register, a human accepted it across classes, two "
          "UNCHANGED consumers cite the same governed asset id, the clause "
          "exists exactly twice by design, and deleting the engine's whole "
          "workspace changed nothing - the shared engine is governed facts, "
          "not a store. 88 routes, 9 tools, 28 tables / 305 columns. ===")


if __name__ == "__main__":
    main_test()
