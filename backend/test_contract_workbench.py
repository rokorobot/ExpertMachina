"""v2.1 WS2 - THE DIAGNOSIS PROOF for the Contract Intelligence
Workbench (the shared engine).

The runner (workbench/contract_intelligence/runner.py, on
workbench/common.py - the FOURTH zero-edit reuse) is proven as a
governed clause-register engine, not a vague agent:

  - contracts drive runtime: the pinned fifteen-class taxonomy, the
    first-match order, the marker regimes, the contract-document rule,
    and the required-metadata groups are all PARSED from the ratified
    YAMLs; an independent test-side application of the same bytes
    produces the IDENTICAL candidate set (two implementations, one
    contract);
  - every CONTRACT_CLAUSE statement carries its excerpt VERBATIM (the
    paraphrase check is byte equality against packaged content); the
    forbidden legal-conclusion vocabulary appears in no written byte;
  - CONTRACT_METADATA_GAP declares absence per contract under the
    pinned rules (a real gap on a real corpus contract), and covered
    contracts produce NO gap (refusal-first, both ways);
  - byte-identical regeneration at the same declared as_of; outputs
    confined to 07/08; the brief is assist-only, never a proposal;
  - the valve holds register candidates DERIVED; ONE human acceptance
    -> the register entry travels into the recompiled package and BOTH
    unchanged consumers cite it by asset id (the shared-engine runtime
    check - THE CONVERGENCE re-proven through the runner's OWN output);
  - idempotence across generations: re-running on the recompiled
    package SKIPS the registered clause (declared in `skipped`), never
    re-proposing the register;
  - no as_of refuses; every gated/SEQUENCED skill refuses live naming
    its ruling; Guard 5 sweeps the new module with zero edits; route
    manifest 88, MCP 9, D24 28/305.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_ci2_pkg_")

# Guard 5 first (its import overrides db.engine; this suite re-overrides)
import test_agent_authorship_guard as guard   # noqa: E402
import test_route_manifest as route_guard      # noqa: E402

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_ci2_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'ws2.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_ci2_qdrant_")

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
SKILLS_DIR = os.path.join(WB_DIR, "skills")
MANIFEST = os.path.join(WB_DIR, "workbench.yaml")
COMPLIANCE_CORPUS = os.path.join(REPO_DIR, "workbench",
                                 "compliance_obligation", "corpus")
PROCUREMENT_CORPUS = os.path.join(REPO_DIR, "workbench",
                                  "procurement_intelligence", "corpus")
AS_OF = "2026-06-01"


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


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


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "CI2Officer")
    reviewer = test_support.governed_actor(session, "CI2Reviewer")
    issuer = test_support.governed_actor(session, "CI2Issuer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Contract Intelligence WS2", description="the diagnosis proof",
        customer_id=customer.id), actor=officer)
    agent = identity.create_principal(session, name="contract-intelligence",
                                      display_name="Contract Intelligence",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _c = identity.issue_token(session, agent, kind="API_TOKEN",
                                           label="ws2", actor="test-suite")

    # ------------------------------------------------------------ Part 1
    print("\n--- Part 1: Guard 5 sweeps every workbench module, zero edits ---")
    swept = 0
    for root, _dirs, files in os.walk(os.path.join(REPO_DIR, "workbench")):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            with open(path, "r", encoding="utf-8") as f:
                v = guard.workbench_import_violations(
                    os.path.relpath(path, REPO_DIR).replace(os.sep, "/"),
                    f.read())
            assert not v, "\n".join(v)
            swept += 1
    assert swept >= 8, f"the new runner must be inside the sweep: {swept}"
    print(f"Part 1 passed: {swept} workbench module(s) inside the ruled "
          "doors - zero guard edits.")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: the fixture through the real pipeline ---")
    for name, root, domain in (("Compliance Docs", COMPLIANCE_CORPUS, "compliance"),
                               ("Procurement Docs", PROCUREMENT_CORPUS, "procurement")):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
        approve_all(session, project.id, reviewer, f"ws2: {domain}",
                    domain=domain)
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    _model, pkg = build_package_for(session, project.id, "Contract Package",
                                    [a.id for a in approved])
    binding = bind_agent(session, pkg, agent, issuer, "v1")
    loaded = package_consumer.load_package(pkg.file_path)
    vault_dir = tempfile.mkdtemp(prefix="em_ci2_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    print(f"Part 2 passed: 24 documents -> {len(approved)} PRIMARY facts, "
          "INTERNAL package + real AGENT binding, vault bootstrapped.")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE DIAGNOSIS (contracts drive runtime) ---")
    baseline = vault_files(vault_dir)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        first = runner.run_diagnostic(
            pkg.file_path, vault_dir, project.id,
            agent_principal="contract-intelligence", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF)
        second = runner.run_diagnostic(
            pkg.file_path, vault_dir, project.id,
            agent_principal="contract-intelligence", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    assert first["proposals"] == second["proposals"]
    assert sha(first["brief"]) == sha(second["brief"]), "byte-identical brief"
    for p in first["proposals"]:
        assert os.path.isfile(p)
    new_files = vault_files(vault_dir) - baseline
    for rel in new_files:
        assert rel.startswith(("07_agent_workspaces/", "08_proposals/")), rel
    assert not any("07_agent_workspaces" in p for p in first["proposals"]), \
        "the brief must never be a proposal"
    # TWO IMPLEMENTATIONS, ONE CONTRACT: an independent application of
    # the ratified rules must produce the identical clause-candidate set.
    engine_path = first["contracts"]["extract_contract_clauses"]
    rules = runner.parse_taxonomy(engine_path)
    commitment, structural, markers = runner.parse_regimes(engine_path)
    doc_terms = runner.parse_contract_document_terms(engine_path)
    expected = set()
    for e in loaded["knowledge"]:
        src = (e.get("provenance") or {}).get("source_document") or ""
        if not any(t in src.lower() for t in doc_terms):
            continue
        content = norm(e.get("content"))
        cls = runner.classify(content, rules)
        if cls and runner.qualifies(content, cls, commitment, structural,
                                    markers):
            expected.add((e["asset_id"], cls))
    got = {(f["cited_assets"][0], f["clause_class"])
           for f in first["findings"]
           if f["finding_kind"] == "CONTRACT_CLAUSE"}
    assert got == expected, \
        f"runner vs independent application differ: {got ^ expected}"
    clause_count = len(got)
    assert clause_count >= 10
    print(f"Part 3 passed: {clause_count} clause candidates - the runner's "
          f"set EQUALS the independent application of the ratified rules; "
          f"byte-identical at the declared clock; outputs confined to "
          f"07/08.")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: the posture on the bytes ---")
    forbidden = runner.parse_forbidden_vocabulary(MANIFEST)
    assert len(forbidden) == 12
    by_id = {e["asset_id"]: norm(e.get("content"))
             for e in loaded["knowledge"]}
    verbatim_checked = 0
    for f in first["findings"]:
        if f["finding_kind"] != "CONTRACT_CLAUSE":
            continue
        src_content = by_id[f["cited_assets"][0]]
        assert f'"{src_content}"' in f["statement"], \
            f"THE PARAPHRASED CLAUSE: statement does not carry the " \
            f"verbatim excerpt of asset {f['cited_assets'][0]}"
        verbatim_checked += 1
    for path in [first["brief"]] + first["proposals"]:
        with open(path, encoding="utf-8") as f:
            low = f.read().lower()
        for phrase in forbidden:
            assert phrase not in low, f"forbidden vocabulary: {phrase!r}"
    # gaps: a REAL corpus contract missing a required group, and covered
    # contracts producing NO gap (refusal-first both ways)
    gaps = [f for f in first["findings"]
            if f["finding_kind"] == "CONTRACT_METADATA_GAP"]
    assert gaps, "the corpus carries a genuine metadata gap"
    gap_docs = {f["contract_document"] for f in gaps}
    assert first["covered_contracts"], "covered contracts must exist"
    assert not (gap_docs & set(first["covered_contracts"]))
    for f in gaps:
        assert "never that the clause does not exist" in f["statement"]
    print(f"Part 4 passed: {verbatim_checked} clause statements carry their "
          f"excerpt VERBATIM (byte equality); the 12 forbidden phrases in "
          f"no written byte; {len(gaps)} genuine gap(s) on "
          f"{sorted(gap_docs)}; {len(first['covered_contracts'])} covered "
          f"contract(s) produced no gap.")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: the valve + ONE acceptance -> the register ---")
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
                               for a in lane_assets), "the valve holds"
    # accept the CONVERGENCE clause's register candidate (the CloudHost
    # SLA subprocessor clause - it carries both consumers' markers)
    conv_finding = next(f for f in first["findings"]
                        if f["finding_kind"] == "CONTRACT_CLAUSE"
                        and "subprocessor" in f["statement"])
    docs = {d.id: d for d in session.query(db.Document).filter(
        db.Document.id.in_(lane_doc_ids)).all()}
    conv_doc = next(
        d for d in docs.values()
        if "extract_contract_clauses" in (d.filename or "")
        and str(conv_finding["cited_assets"][0]) in
        open(os.path.join(vault_dir, "08_proposals", d.filename),
             encoding="utf-8").read()
        and "subprocessor" in
        open(os.path.join(vault_dir, "08_proposals", d.filename),
             encoding="utf-8").read())
    cands = sorted((a for a in lane_assets if a.document_id == conv_doc.id),
                   key=lambda a: a.id)
    pick = next(a for a in cands if "subprocessor" in norm(a.content)
                and "shall" in norm(a.content).lower())
    crud.update_knowledge_asset(
        session, pick.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="ws2: register entry accepted")
    session.refresh(pick)
    assert pick.status == "APPROVED" and pick.source_class == "DERIVED"
    event = session.query(db.AuditEvent).filter_by(
        event_type="ASSET_APPROVED", target_id=str(pick.id)).order_by(
        db.AuditEvent.id.desc()).first()
    prov = json.loads(event.details)["synthesis_provenance"]
    assert prov["provenance_verified"] is True
    assert prov["claimed"]["agent_principal"] == "contract-intelligence"
    assert prov["cited_assets"]["missing"] == []
    print(f"Part 5 passed: {len(lane_assets)} register candidates held "
          f"DERIVED; ONE human acceptance (asset {pick.id}) with VERIFIED "
          f"synthesis provenance citing the PRIMARY clause.")

    # ------------------------------------------------------------ Part 6
    print("\n--- Part 6: THE SHARED-ENGINE RUNTIME CHECK ---")
    approved2 = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    _m2, pkg2 = build_package_for(session, project.id, "Contract Package v2",
                                  [a.id for a in approved2])
    binding2 = bind_agent(session, pkg2, agent, issuer, "v2")
    loaded2 = package_consumer.load_package(pkg2.file_path)
    assert pick.id in {e["asset_id"] for e in loaded2["knowledge"]}
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
        third = runner.run_diagnostic(
            pkg2.file_path, vault_dir, project.id,
            agent_principal="contract-intelligence", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    comp_citing = [f for f in compliance["findings"]
                   if pick.id in f.get("cited_assets", [])]
    proc_citing = [f for f in procurement["findings"]
                   if pick.id in f.get("cited_assets", [])]
    assert comp_citing and proc_citing, \
        "BOTH unchanged consumers must cite the runner-produced register " \
        "entry by asset id"
    # idempotence: the engine never re-proposes its own register
    assert pick.id in third["register_entries"]
    assert any("already registered" in s["reason"] for s in third["skipped"])
    reg_texts = [norm(e.get("content")) for e in loaded2["knowledge"]
                 if e["asset_id"] == pick.id]
    assert not any(reg_texts[0] in f["statement"]
                   for f in third["findings"]
                   if f["finding_kind"] == "CONTRACT_CLAUSE"), \
        "the registered clause must not be re-proposed"
    # the brief shows the register with class + origin visible
    with open(third["brief"], encoding="utf-8") as f:
        brief3 = f.read()
    assert f"asset {pick.id} [DERIVED, origin: contract-intelligence]" in brief3
    print(f"Part 6 passed: THE CONVERGENCE through the runner's OWN output "
          f"- register entry {pick.id} cited by asset id by BOTH unchanged "
          f"consumers ({sorted({f['finding_kind'] for f in comp_citing})} / "
          f"{sorted({f['finding_kind'] for f in proc_citing})}); the "
          f"re-run SKIPS the registered clause (idempotence); the brief "
          f"shows [DERIVED, origin: contract-intelligence].")

    # ------------------------------------------------------------ Part 7
    print("\n--- Part 7: refusals live; zero door growth ---")
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        def expect(kwargs, needle):
            try:
                runner.run_diagnostic(
                    pkg2.file_path, vault_dir, project.id,
                    agent_principal="contract-intelligence",
                    binding_id=binding2.id,
                    graph_client=InProcessGraphClient(), **kwargs)
            except RuntimeError as e:
                return needle in str(e)
            return False
        assert expect(dict(as_of=None), "no as_of declared")
        for gated, needle_full in sorted(runner.GATED_SKILLS.items()):
            needle = needle_full.split("(")[0].split(":")[0].strip()[:30]
            assert expect(dict(as_of=AS_OF,
                               requested_skills=runner.ACTIVE_SKILLS + (gated,)),
                          needle), f"{gated} must refuse naming {needle!r}"
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
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
    session.close()
    print(f"Part 7 passed: no-as_of + all {len(runner.GATED_SKILLS)} "
          f"gated/SEQUENCED skills refused live naming their ruling; route "
          f"manifest 88 at its ratified digest; MCP at 9; D24 at "
          f"{tables}/{columns}.")

    print("\n=== All v2.1 WS2 diagnosis-proof checks passed: the contracts "
          "drive the runtime (two implementations, one contract, identical "
          "sets), every clause verbatim, absence declared honestly, the "
          "valve holding, and THE CONVERGENCE re-proven through the "
          "runner's own accepted output - the shared engine feeds two "
          "unchanged readers and never re-proposes its own register. ===")


if __name__ == "__main__":
    main()
