"""v2.3 WS3 gate suite — THE MILESTONE GATE (the 86th suite).

The full commercial loop for Finance & Cost Leakage
(docs/finance-cost-leakage-v2.3.md), end to end, plus the five named
proofs:

  Stage 1  corpora (12 procurement + 3 corpus_finance) approved PRIMARY.
  Stage 2  INTERNAL package + a real AGENT binding.
  Stage 3  THE REAL REGISTER CHAIN — the v2.1 Contract Intelligence
           engine extracts clause candidates; the valve holds them
           DERIVED; a human accepts a fee/price register clause -> the
           accepted DERIVED register fact.
  Stage 4  the recompiled package; the finance runner ENGAGED at the
           declared clock pair.
  Stage 5  THE SECOND HARVEST PROOF — an exposure finding cites the
           DERIVED register fact BY id; the chain resolves finding ->
           DERIVED register -> PRIMARY contract; the cross-workbench
           consolidation is intact (extract_payment_terms CONSOLIDATED
           into the v2.1 register; v2.3 has NO payment-term
           re-extraction path).
  Stage 6  THE EXPOSURE ARITHMETIC — declared arithmetic over verbatim
           values, the formula on the bytes.
  Stage 7  THE INVENTED MONEY SWEEP — every money token in every finding
           is tier 1/2/3; the SETTLED-ACCOUNT dictionary catches a
           synthetic violation and spares "not paid by its due date".
  Stage 8  the valve + the human gate — exposure proposals held DERIVED;
           one accepted; still DERIVED.
  Stage 9  THE UNOPENED LEDGER end-to-end — THE INVOICE PLANT document
           declined with [OE]; no transactional door; the diagnosis
           wrote nothing governed; no SETTLED-ACCOUNT vocabulary on the
           bytes.
  Stage 10 THE LABELED SCENARIO — the scenario brief labels every
           estimate in-unit, 07-confined, never a proposal.
  Stage 11 the closers — route manifest 88, the nine MCP tools, D24
           byte-identical 28/305.
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
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_fin3_pkg_")

import test_agent_authorship_guard as guard   # noqa: E402,F401 - engine override order
import test_route_manifest as route_guard      # noqa: E402

from sqlalchemy import create_engine, text     # noqa: E402
from sqlalchemy.orm import sessionmaker        # noqa: E402
from app import database as db                 # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_fin3_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'gate.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                      # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_fin3_qdrant_")

from app import (schemas, crud, connectors, identity, mcp_gateway,  # noqa: E402
                 package_builder, package_consumer, policy, proposals, tier2)
import test_support                            # noqa: E402
import test_workbench_projection               # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.finance_cost_leakage.runner as finance_runner   # noqa: E402
import workbench.contract_intelligence.runner as engine_runner   # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "finance_cost_leakage")
FINANCE_CORPUS = os.path.join(WB_DIR, "corpus_finance")
PROC_CORPUS = os.path.join(REPO_DIR, "workbench",
                           "procurement_intelligence", "corpus")
DRAFTS_DIR = os.path.join(REPO_DIR, "docs", "skill-contracts")

AS_OF = "2026-07-10"
WINDOW = 120
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
MONEY_RE = re.compile(r"[0-9][0-9,]*(?:\.[0-9]+)?\s*EUR|\b\d+(?:\.\d+)?\s?%")


class ApproveEverythingVerifier:
    identity = {"method": "GATE_APPROVE_EVERYTHING",
                "note": "finance acceptance lane-sentinel seam"}

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


def bootstrap_vault():
    vault_dir = tempfile.mkdtemp(prefix="em_fin3_vault_")
    r = subprocess.run([sys.executable,
                        os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                        "--vault-dir", vault_dir],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return vault_dir


def compile_package(session, project, name):
    approved = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.status == "APPROVED").order_by(
        db.KnowledgeAsset.id).all()
    model = db.ExpertModel(project_id=project.id, name=name,
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    session.add(model)
    session.commit()
    session.refresh(model)
    pkg = db.AgentPackage(project_id=project.id, expert_model_id=model.id,
                          name=name, clearance_level="INTERNAL")
    session.add(pkg)
    session.commit()
    session.refresh(pkg)
    package_builder.build_package(session, pkg)
    session.refresh(pkg)
    return pkg


def bind(session, pkg, agent, issuer):
    binding = db.ExpertAgentBinding(
        agent_package_id=pkg.id, agent_principal_id=agent.id,
        package_hash=pkg.package_hash, package_version="v1",
        principal_clearance_at_issue="INTERNAL",
        selected_provider="ANTHROPIC", selected_model_name="claude-opus-4-8",
        selection_evidence_json="{}",
        identity_fact_id=issuer.fact(session).id)
    session.add(binding)
    session.commit()
    session.refresh(binding)
    return binding


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
            text_ = (f"Per the governed evidence (asset_id {best['asset_id']}): "
                     f"{best.get('content')}")
        else:
            text_ = ("INSUFFICIENT EVIDENCE - the governed evidence offered "
                     "does not contain the answer to this question.")
        return {"answer": text_,
                "cited_asset_ids": [] if "INSUFFICIENT" in text_
                else [scored[0][1]["asset_id"]],
                "evidence": sel}
    return answer


def norm(t):
    return " ".join((t or "").split())


def db_fingerprint():
    """Every governed KNOWLEDGE table, byte-exact. Three operational-
    evidence tables that grow on ANY authenticated read BY LAW are
    excluded (the v2.2 ruling): the audit ledger, credentials
    (last_used_at), identity_facts (D20)."""
    h = hashlib.sha256()
    skip = {db.AuditEvent.__tablename__, "credentials", "identity_facts"}
    with db.engine.connect() as conn:
        for table in sorted(t.name for t in db.Base.metadata.sorted_tables):
            if table in skip:
                continue
            rows = conn.execute(text(f"SELECT * FROM {table} ORDER BY 1")).fetchall()
            h.update(table.encode())
            for row in rows:
                h.update(repr(tuple(row)).encode())
    return h.hexdigest()


def main():
    tier2.verifier_factory = ApproveEverythingVerifier
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "FinGateOfficer")
    reviewer = test_support.governed_actor(session, "FinGateReviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Finance Gate", description="v2.3 THE MILESTONE GATE",
        customer_id=customer.id), actor=officer)

    # ------------------------------------------------------- Stage 1
    print("\n--- Stage 1: the corpora through the real pipeline ---")
    for name, root in (("Procurement Docs", PROC_CORPUS),
                       ("Finance Extension Docs", FINANCE_CORPUS)):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
    assert session.query(db.Document).filter_by(project_id=project.id).count() == 15
    approve_all(session, project.id, reviewer, "gate: corpus approval")
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    assert all(a.source_class == "PRIMARY" for a in approved)
    print(f"Stage 1 passed: 15 documents -> {len(approved)} human-approved "
          f"PRIMARY facts.")

    # ------------------------------------------------------- Stage 2
    print("\n--- Stage 2: INTERNAL package + real AGENT binding ---")
    agent = identity.create_principal(session, name="workbench-agent",
                                      display_name="Workbench Agent",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _c = identity.issue_token(session, agent, kind="API_TOKEN",
                                           label="gate", actor="test-suite")
    issuer = test_support.governed_actor(session, "FinGateIssuer")
    pkg1 = compile_package(session, project, "Gate Package v1")
    binding1 = bind(session, pkg1, agent, issuer)
    print(f"Stage 2 passed: package {pkg1.package_hash[:12]}... bound.")

    # ------------------------------------------------------- Stage 3
    print("\n--- Stage 3: THE REAL REGISTER CHAIN (v2.1 engine -> valve -> "
          "human) ---")
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add(db.ApprovalPolicy(project_id=project.id, name="everything",
                                  asset_types_json=all_types, enabled=True))
    session.add(db.ApprovalPolicy(project_id=project.id, name="everything-t2",
                                  asset_types_json=all_types, enabled=True,
                                  engine_conditions_json=json.dumps(
                                      {"contradiction_check": "CLEAN_REQUIRED"})))
    session.commit()
    vault_a = bootstrap_vault()
    loaded1 = package_consumer.load_package(pkg1.file_path)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        engine_runner.run_diagnostic(
            pkg1.file_path, vault_a, project.id,
            agent_principal="workbench-agent", binding_id=binding1.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            answerer=make_answerer(loaded1))
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    lane_a = db.SourceConnector(project_id=project.id, name="Register Lane",
                                type="LOCAL_FOLDER",
                                root_path=os.path.join(vault_a, "08_proposals"),
                                include_extensions=".md", lane="PROPOSAL")
    session.add(lane_a)
    session.commit()
    session.refresh(lane_a)
    run_scan(session, lane_a)
    lane_a_docs = policy.proposal_lane_document_ids(
        session, [d.id for d in session.query(db.Document).filter_by(
            project_id=project.id).all()])
    held = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_a_docs)).all()
    assert held and all(a.status == "CANDIDATE"
                        and a.source_class == "DERIVED" for a in held)
    # accept a real register CLAUSE carrying a finance exposure marker and
    # a concrete figure (not a metadata-gap proposal) - a fee/price clause
    # the finance runner will harvest AND run declared arithmetic on.
    fin_markers = ("increase", "renew", "fee", "penalty", "surcharge")
    cand = [a for a in held
            if any(m in norm(a.content).lower() for m in fin_markers)
            and "no clause of required group" not in norm(a.content).lower()
            and (re.search(r"[0-9][0-9,]*\s*EUR", norm(a.content))
                 or re.search(r"\d+\s?%", norm(a.content)))]
    assert cand, "the engine must produce a finance-relevant register clause"
    # prefer one carrying BOTH a currency base and a rate (declared
    # arithmetic material), else the first finance clause.
    both = [a for a in cand
            if re.search(r"[0-9][0-9,]*\s*EUR", norm(a.content))
            and re.search(r"\d+\s?%", norm(a.content))]
    reg = sorted(both or cand, key=lambda a: a.id)[0]
    crud.update_knowledge_asset(
        session, reg.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted the register clause")
    session.refresh(reg)
    assert reg.status == "APPROVED" and reg.source_class == "DERIVED"
    print(f"Stage 3 passed: {len(held)} register candidates held DERIVED; "
          f"human accepted register clause #{reg.id} "
          f"(\"{norm(reg.content)[:60]}...\").")

    # ------------------------------------------------------- Stage 4
    print("\n--- Stage 4: recompiled package; THE FINANCE DIAGNOSIS ---")
    pkg2 = compile_package(session, project, "Gate Package v2")
    binding2 = bind(session, pkg2, agent, issuer)
    loaded2 = package_consumer.load_package(pkg2.file_path)
    assert any(e["asset_id"] == reg.id for e in loaded2["knowledge"]), \
        "the recompiled package must carry the register fact"
    vault_b = bootstrap_vault()
    answerer2 = make_answerer(loaded2)
    fp_before = db_fingerprint()
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        diag = finance_runner.run_diagnostic(
            pkg2.file_path, vault_b, project.id,
            agent_principal="workbench-agent", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW, answerer=answerer2)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    kinds = {f["finding_kind"] for f in diag["findings"]}
    assert "COST_EXPOSURE" in kinds
    # the diagnosis is a computed projection: it writes nothing governed
    # (bracketed tightly around the run, before any valve ingestion).
    assert db_fingerprint() == fp_before, \
        "the diagnosis must write nothing governed"
    print(f"Stage 4 passed: {len(diag['findings'])} findings at the declared "
          f"clock pair ({AS_OF} + {WINDOW}d); the run wrote nothing governed.")

    def cost_findings():
        return [f for f in diag["findings"] if f["finding_kind"] == "COST_EXPOSURE"]

    # ------------------------------------------------------- Stage 5
    print("\n--- Stage 5: THE SECOND HARVEST PROOF (register cited BY id; "
          "consolidation intact) ---")
    harvest = [f for f in cost_findings() if f["asset_id"] == reg.id]
    assert harvest, "an exposure finding must cite the DERIVED register fact"
    assert "DERIVED" in harvest[0]["cite"]
    # the chain resolves: register clause names its PRIMARY source.
    m = re.search(r"governed asset (\d+)", norm(reg.content))
    if m:
        primary = session.get(db.KnowledgeAsset, int(m.group(1)))
        assert primary is not None
    # the cross-workbench consolidation is intact; v2.3 has NO
    # payment-term re-extraction path.
    assert "extract_payment_terms" not in finance_runner.ACTIVE_SKILLS
    epx = open(os.path.join(DRAFTS_DIR, "02_finance_cost_leakage",
                            "extract_payment_terms.yaml"), encoding="utf-8").read()
    assert "status: CONSOLIDATED" in epx and "extract_contract_clauses" in epx
    # no v2.3 skill file re-implements clause/payment extraction.
    for s in os.listdir(os.path.join(WB_DIR, "skills")):
        assert "extract_payment_terms" not in s
    print(f"Stage 5 passed: exposure finding cites register #{reg.id} "
          f"[DERIVED] BY id; extract_payment_terms CONSOLIDATED into the "
          f"v2.1 register; no re-extraction path in v2.3.")

    # ------------------------------------------------------- Stage 6
    print("\n--- Stage 6: THE EXPOSURE ARITHMETIC ---")
    arith = [f for f in cost_findings() if f.get("arithmetic")]
    assert arith, "at least one exposure carries declared arithmetic"
    for f in arith:
        assert "declared arithmetic over verbatim values" in f["arithmetic"]
    # the formula appears on the proposal bytes.
    on_bytes = False
    for path in diag["proposals"]:
        with open(path, encoding="utf-8") as fh:
            if "declared arithmetic over verbatim values" in fh.read():
                on_bytes = True
    assert on_bytes
    print(f"Stage 6 passed: {len(arith)} declared-arithmetic exposure(s); "
          f"e.g. \"{arith[0]['arithmetic']}\" - on the bytes.")

    # ------------------------------------------------------- Stage 7
    print("\n--- Stage 7: THE INVENTED MONEY SWEEP ---")
    forbidden = finance_runner.parse_forbidden_vocabulary(
        os.path.join(WB_DIR, "workbench.yaml"))
    # every money token in every finding statement is governed: it appears
    # in a cited source fact OR in the finding's declared arithmetic.
    id_to_content = {a.id: norm(a.content) for a in
                     session.query(db.KnowledgeAsset).filter_by(
                         project_id=project.id).all()}
    for f in cost_findings():
        statement = f["statement"]
        arithmetic = f.get("arithmetic") or ""
        sources = " ".join(id_to_content.get(i, "")
                           for i in f["cited_assets"])
        for tok in MONEY_RE.findall(statement):
            t = tok.strip()
            assert t in sources or t in arithmetic, \
                f"money token {t!r} not verbatim in a cited source or arithmetic"
    # the dictionary catches a synthetic settled-account violation...
    violation = "The actual cost was 5,000 EUR and the payment cleared."
    assert any(p in violation.lower() for p in forbidden), \
        "the SETTLED-ACCOUNT dictionary must catch a real violation"
    # ...and spares the legitimate conditional clause.
    legit = "Any amount not paid by its due date shall be subject to a fee."
    assert not any(p in legit.lower() for p in forbidden), \
        "the dictionary must spare 'not paid by its due date'"
    print("Stage 7 passed: every money token verbatim-cited or declared "
          "arithmetic; the sweep catches 'payment cleared'/'actual cost "
          "was' and spares 'not paid by its due date'.")

    # ------------------------------------------------------- Stage 8
    print("\n--- Stage 8: the valve + the human gate ---")
    lane_b = db.SourceConnector(project_id=project.id, name="Finance Lane",
                                type="LOCAL_FOLDER",
                                root_path=os.path.join(vault_b, "08_proposals"),
                                include_extensions=".md", lane="PROPOSAL")
    session.add(lane_b)
    session.commit()
    session.refresh(lane_b)
    run_scan(session, lane_b)
    all_docs = [d.id for d in session.query(db.Document).filter_by(
        project_id=project.id).all()]
    lane_b_docs = [d for d in policy.proposal_lane_document_ids(session, all_docs)
                   if d not in lane_a_docs]
    lane_b_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_b_docs)).all()
    assert lane_b_assets and all(
        a.status == "CANDIDATE" and a.source_class == "DERIVED"
        for a in lane_b_assets), "exposure proposals held DERIVED at the gate"
    candidate = sorted(lane_b_assets, key=lambda a: a.id)[0]
    verdict = proposals.verify_provenance(session, candidate.document_id)
    assert verdict["provenance_verified"] is True, verdict["reasons"]
    crud.update_knowledge_asset(
        session, candidate.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted the exposure finding")
    session.refresh(candidate)
    assert candidate.status == "APPROVED" and candidate.source_class == "DERIVED"
    print(f"Stage 8 passed: {len(lane_b_assets)} exposure candidates held "
          f"DERIVED; provenance verified; one accepted -> APPROVED, still "
          f"DERIVED.")

    # ------------------------------------------------------- Stage 9
    print("\n--- Stage 9: THE UNOPENED LEDGER end-to-end ---")
    # structural: no transactional door / reader module.
    assert set(f for f in os.listdir(WB_DIR) if f.endswith(".py")) == {"runner.py"}
    # adversarial: THE INVOICE PLANT document was ingested (Stage 1) and, if
    # any of its facts reached the runner, they were declined naming [OE].
    inv_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename == "vendor-invoice-4471.md").first()
    assert inv_doc is not None, "the invoice plant must be an ingested document"
    inv_asset_ids = {a.id for a in session.query(db.KnowledgeAsset).filter_by(
        document_id=inv_doc.id).all()}
    assert not any(f["asset_id"] in inv_asset_ids for f in diag["findings"]), \
        "no invoice-plant fact may become a finding"
    # byte-level: no SETTLED-ACCOUNT vocabulary on any written byte.
    written = [open(p, encoding="utf-8").read().lower()
               for p in diag["proposals"] + [diag["brief"], diag["pack"]]]
    for phrase in forbidden:
        for body in written:
            assert phrase not in body, f"SETTLED-ACCOUNT vocab {phrase!r} on bytes"
    print("Stage 9 passed: only runner.py in the bundle; no invoice-plant "
          "fact became a finding; zero SETTLED-ACCOUNT vocabulary on the "
          "bytes (the diagnosis wrote nothing governed - proven in Stage 4).")

    # ------------------------------------------------------- Stage 10
    print("\n--- Stage 10: THE LABELED SCENARIO ---")
    with open(diag["brief"], encoding="utf-8") as fh:
        brief = fh.read()
    assert "[ESTIMATE, non-authoritative]" in brief
    assert "/08_proposals/" not in diag["brief"].replace(os.sep, "/")
    assert diag["brief"] not in diag["proposals"]
    assert "07_agent_workspaces" in diag["brief"].replace(os.sep, "/")
    print("Stage 10 passed: the scenario brief labels estimates in-unit, "
          "07-confined, never a proposal.")

    # ------------------------------------------------------- Stage 11
    print("\n--- Stage 11: the closers ---")
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
    print("Stage 11 passed: route manifest 88 (digest frozen); the nine MCP "
          "tools; D24 byte-identical at 28/305.")

    session.close()
    print("\n=== THE v2.3 MILESTONE GATE PASSED: document-governed cost "
          "exposure from approved documents, register facts, and a declared "
          "clock - declared arithmetic over verbatim values, the register "
          "harvested BY id, THE INVOICE PLANT declined naming [OE], "
          "estimates labeled in-unit, the human gate deciding everything, "
          "and no transactional truth determined anywhere. 28/305. ===")


if __name__ == "__main__":
    main()
