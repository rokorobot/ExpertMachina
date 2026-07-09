"""v2.4 WS3 gate suite — THE MILESTONE GATE (the 89th suite).

The full commercial loop for Customer Success Intelligence
(docs/customer-success-intelligence-v2.4.md), end to end, plus the six
named proofs:

  Stage 1  corpora (12 customer-operations + 4 corpus_customer_success)
           approved PRIMARY.
  Stage 2  INTERNAL package + a real AGENT binding.
  Stage 3  THE REAL REGISTER CHAIN — the v2.1 Contract Intelligence
           engine extracts clause candidates; the valve holds them
           DERIVED despite an approve-everything policy (D29); a human
           accepts a dated customer renewal/notice clause -> the
           accepted DERIVED register fact.
  Stage 4  the recompiled package; the customer-success runner ENGAGED
           at the declared clock + declared customers; all four finding
           kinds fire; the diagnosis writes nothing governed
           (fingerprint bracketed tightly around the run).
  Stage 5  THE THIRD HARVEST PROOF — a renewal-obligation finding cites
           the DERIVED register fact BY id; the cross-workbench
           consolidations are intact (extract_customer_communication_
           obligations CONSOLIDATED into the v2.1 register;
           detect_outdated_cs_documentation into the shipped v1.7
           skill); v2.4 has NO extraction path of its own.
  Stage 6  THE CUSTOM TERMS PROOF + THE COMPUTED RENEWAL WINDOW — Acme
           deviates on both declared axes; Northwind produces ZERO
           deviation findings (conformance recorded as skips, proven on
           the proposal bytes too); every window is declared date
           arithmetic over verbatim dates, the formula on the bytes.
  Stage 7  THE IMPUTED HEALTH SWEEP + THE UNREAD CUSTOMER — the
           relationship-state vocabulary appears on NO written byte
           outside a "> " quoted-claim blockquote and DOES surface
           there (the plant, quote-framed); no plant fact yields any
           finding kind but UNBACKED_HEALTH_ASSUMPTION; the dictionary
           catches a synthetic violation and spares legitimate prose;
           no operational customer-data door exists.
  Stage 8  the valve + the human gate — customer-success proposals held
           DERIVED; provenance verified; one accepted; still DERIVED.
  Stage 9  the bundle / registry / sweep proof — five ratified
           contracts + manifest agree; registry #6 is Customer Success
           Intelligence — ACTIVE (v2.4); global sweep 39/73; the [ES]
           draft SEQUENCED with its read-only condition; the six [OE]
           drafts FUTURE; no accidental promotion.
  Stage 10 the catalog / presentation proof — EXACTLY ONE
           WORKBENCH_CATALOG_INFO row (customer-success-intelligence,
           #6, v2.4), presentation only; its wording claims no CRM /
           churn / telemetry / ranking / NPS / outreach capability.
  Stage 11 the closers — route manifest 88 (digest frozen, no new
           route), the nine MCP tools, D24 byte-identical 28/305.
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
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_cs3_pkg_")

import test_agent_authorship_guard as guard   # noqa: E402,F401 - engine override order
import test_route_manifest as route_guard      # noqa: E402

from sqlalchemy import create_engine, text     # noqa: E402
from sqlalchemy.orm import sessionmaker        # noqa: E402
from app import database as db                 # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_cs3_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'gate.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                      # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_cs3_qdrant_")

from app import (schemas, crud, connectors, identity, mcp_gateway,  # noqa: E402
                 package_builder, package_consumer, policy, proposals, tier2)
import test_support                            # noqa: E402
import test_workbench_projection               # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.customer_success_intelligence.runner as cs_runner   # noqa: E402
import workbench.contract_intelligence.runner as engine_runner       # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "customer_success_intelligence")
CS_CORPUS = os.path.join(WB_DIR, "corpus_customer_success")
CUSOPS_CORPUS = os.path.join(REPO_DIR, "workbench",
                             "customer_operations", "corpus")
DRAFTS_DIR = os.path.join(REPO_DIR, "docs", "skill-contracts")
CS_DRAFTS = os.path.join(DRAFTS_DIR, "06_customer_success_retention")
PAGE_TSX = os.path.join(REPO_DIR, "frontend", "src", "app", "page.tsx")

AS_OF = "2026-07-10"
WINDOW = 90
CUSTOMERS = ("Acme Industrial", "Northwind Logistics")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

ACTIVE_FIVE = ("detect_customer_term_deviation",
               "detect_customer_renewal_obligations",
               "detect_customer_coverage_gap",
               "detect_unbacked_customer_health_assumption",
               "prepare_customer_success_review_brief")
GLOBAL_SWEEP = (39, 73)


class ApproveEverythingVerifier:
    identity = {"method": "GATE_APPROVE_EVERYTHING",
                "note": "customer-success acceptance lane-sentinel seam"}

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


def bootstrap_vault():
    vault_dir = tempfile.mkdtemp(prefix="em_cs3_vault_")
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
    officer = test_support.governed_actor(session, "CSGateOfficer")
    reviewer = test_support.governed_actor(session, "CSGateReviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Customer Success Gate", description="v2.4 THE MILESTONE GATE",
        customer_id=customer.id), actor=officer)

    # ------------------------------------------------------- Stage 1
    print("\n--- Stage 1: the corpora through the real pipeline ---")
    for name, root in (("Customer Operations Docs", CUSOPS_CORPUS),
                       ("Customer Success Docs", CS_CORPUS)):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
    assert session.query(db.Document).filter_by(
        project_id=project.id).count() == 16
    approve_all(session, project.id, reviewer, "gate: corpus approval")
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    assert all(a.source_class == "PRIMARY" for a in approved)
    print(f"Stage 1 passed: 16 documents -> {len(approved)} human-approved "
          f"PRIMARY facts.")

    # ------------------------------------------------------- Stage 2
    print("\n--- Stage 2: INTERNAL package + real AGENT binding ---")
    agent = identity.create_principal(session, name="workbench-agent",
                                      display_name="Workbench Agent",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _c = identity.issue_token(session, agent, kind="API_TOKEN",
                                           label="gate", actor="test-suite")
    issuer = test_support.governed_actor(session, "CSGateIssuer")
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
                        and a.source_class == "DERIVED" for a in held), \
        "register candidates held DERIVED despite the approve-everything policy"
    # accept a real dated renewal/notice register CLAUSE the customer-
    # success runner will harvest: a YYYY-MM-DD date + a renewal/notice
    # marker + a term-end marker (so the declared window arithmetic runs).
    def is_harvest_anchor(content):
        low = norm(content).lower()
        return (DATE_RE.search(content)
                and ("renew" in low or "notice" in low)
                and ("ends on" in low or "before that date" in low)
                and "2026-09-30" in content
                and "no clause of required group" not in low)
    cand = sorted((a for a in held if is_harvest_anchor(a.content)),
                  key=lambda a: a.id)
    assert cand, "the engine must produce the dated customer renewal clause"
    reg = cand[0]
    crud.update_knowledge_asset(
        session, reg.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted the register clause")
    session.refresh(reg)
    assert reg.status == "APPROVED" and reg.source_class == "DERIVED"
    print(f"Stage 3 passed: {len(held)} register candidates held DERIVED; "
          f"human accepted register clause #{reg.id} "
          f"(\"{norm(reg.content)[:60]}...\").")

    # ------------------------------------------------------- Stage 4
    print("\n--- Stage 4: recompiled package; THE CUSTOMER-SUCCESS "
          "DIAGNOSIS ---")
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
        diag = cs_runner.run_diagnostic(
            pkg2.file_path, vault_b, project.id,
            agent_principal="workbench-agent", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW, customers=CUSTOMERS, answerer=answerer2)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    kinds = {f["finding_kind"] for f in diag["findings"]}
    for expected in ("CUSTOMER_TERM_DEVIATION", "CUSTOMER_RENEWAL_OBLIGATION",
                     "CUSTOMER_COVERAGE_GAP", "UNBACKED_HEALTH_ASSUMPTION"):
        assert expected in kinds, f"{expected} missing from the diagnosis"
    # the diagnosis is a computed projection: it writes nothing governed
    # (bracketed tightly around the run, before any valve ingestion).
    assert db_fingerprint() == fp_before, \
        "the diagnosis must write nothing governed"
    print(f"Stage 4 passed: {len(diag['findings'])} findings, all four kinds, "
          f"at the declared clock ({AS_OF} + {WINDOW}d) for the declared "
          f"customers; the run wrote nothing governed.")

    def findings(kind):
        return [f for f in diag["findings"] if f["finding_kind"] == kind]

    # ------------------------------------------------------- Stage 5
    print("\n--- Stage 5: THE THIRD HARVEST PROOF (register cited BY id; "
          "consolidations intact) ---")
    harvest = [f for f in findings("CUSTOMER_RENEWAL_OBLIGATION")
               if f["asset_id"] == reg.id]
    assert harvest, "a renewal finding must cite the DERIVED register fact"
    assert "DERIVED" in harvest[0]["cite"] and harvest[0]["harvested"]
    assert harvest[0]["cited_assets"] == [reg.id]
    # the chain resolves: the register clause names its PRIMARY source.
    m = re.search(r"governed asset (\d+)", norm(reg.content))
    if m:
        primary = session.get(db.KnowledgeAsset, int(m.group(1)))
        assert primary is not None and primary.source_class == "PRIMARY"
    # the cross-workbench consolidations are intact; v2.4 has NO
    # extraction path of its own.
    assert "extract_customer_communication_obligations" \
        not in cs_runner.ACTIVE_SKILLS
    for draft, target in (
            ("extract_customer_communication_obligations",
             "extract_contract_clauses"),
            ("detect_outdated_cs_documentation", "identify_outdated_policies")):
        d = open(os.path.join(CS_DRAFTS, draft + ".yaml"),
                 encoding="utf-8").read()
        assert "status: CONSOLIDATED" in d and target in d
    for s in os.listdir(os.path.join(WB_DIR, "skills")):
        assert not s.startswith("extract_"), \
            "v2.4 must have no extraction skill of its own"
    print(f"Stage 5 passed: renewal finding cites register #{reg.id} "
          f"[DERIVED] BY id (action {harvest[0]['action_date']}); both "
          f"cross-workbench consolidations intact; no re-extraction path.")

    # ------------------------------------------------------- Stage 6
    print("\n--- Stage 6: THE CUSTOM TERMS PROOF + THE COMPUTED RENEWAL "
          "WINDOW ---")
    acme_axes = {f["axis"] for f in findings("CUSTOMER_TERM_DEVIATION")
                 if f["customer"] == "Acme Industrial"}
    assert acme_axes == {"reporting_cadence", "renewal_notice"}, acme_axes
    nw_dev = [f for f in findings("CUSTOMER_TERM_DEVIATION")
              if f["customer"] == "Northwind Logistics"]
    assert not nw_dev, "the conforming customer must be SILENT"
    for p in diag["proposals"]:
        body = open(p, encoding="utf-8").read()
        if "finding_kind: CUSTOMER_TERM_DEVIATION" in body:
            assert "Northwind" not in body, \
                "no deviation proposal may name the conforming customer"
    nw_conform = [s for s in diag["skipped"]
                  if "Northwind Logistics conforms" in s["reason"]]
    assert len(nw_conform) == 2, "conformance recorded on BOTH axes"
    # every windowed obligation is declared date arithmetic over verbatim
    # dates - recomputed here from the cited fact's own bytes.
    import datetime as _dt
    id_to_content = {a.id: norm(a.content) for a in
                     session.query(db.KnowledgeAsset).filter_by(
                         project_id=project.id).all()}
    windowed = findings("CUSTOMER_RENEWAL_OBLIGATION")
    assert windowed
    for f in windowed:
        src = id_to_content[f["asset_id"]]
        stated = DATE_RE.search(src).group(0)
        d = _dt.date(*(int(p) for p in stated.split("-")))
        if f.get("arithmetic"):
            assert stated in f["arithmetic"], "the verbatim date in the formula"
            notice = int(re.search(r"- (\d+) days", f["arithmetic"]).group(1))
            assert (d - _dt.timedelta(days=notice)).isoformat() \
                == f["action_date"], "the window arithmetic must reproduce"
        else:
            assert f["action_date"] == stated
    on_bytes = any("date arithmetic over the verbatim term-end date"
                   in open(p, encoding="utf-8").read()
                   for p in diag["proposals"])
    assert on_bytes, "the declared formula must appear on the proposal bytes"
    print(f"Stage 6 passed: Acme deviates on both axes; Northwind silent "
          f"(2 conformance skips, zero deviation proposals); "
          f"{len(windowed)} windowed obligation(s), every action date "
          f"reproduced by declared arithmetic over the verbatim bytes.")

    # ------------------------------------------------------- Stage 7
    print("\n--- Stage 7: THE IMPUTED HEALTH SWEEP + THE UNREAD CUSTOMER ---")
    forbidden = cs_runner.parse_forbidden_vocabulary(
        os.path.join(WB_DIR, "workbench.yaml"))
    quoted_hits = 0
    for path in diag["proposals"] + [diag["brief"]]:
        for raw in open(path, encoding="utf-8").read().splitlines():
            low = raw.lower()
            for phrase in forbidden:
                if phrase in low:
                    assert raw.startswith(cs_runner.QUOTE_PREFIX), (
                        f"IMPUTED-HEALTH vocab {phrase!r} outside the quote "
                        f"frame in {os.path.basename(path)}: {raw!r}")
                    quoted_hits += 1
    assert quoted_hits > 0, "the plant must surface - quote-framed"
    # the plant yields ONLY assumption findings, never a relationship-
    # state or any other finding kind.
    plant_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename == "acme-account-plan.md").first()
    assert plant_doc is not None
    plant_ids = {a.id for a in session.query(db.KnowledgeAsset).filter_by(
        document_id=plant_doc.id).all()}
    for f in diag["findings"]:
        if f["asset_id"] in plant_ids:
            assert f["finding_kind"] == "UNBACKED_HEALTH_ASSUMPTION", \
                "a plant fact may surface ONLY as an unbacked assumption"
    # the dictionary catches a synthetic violation and spares legit prose.
    violation = "Analysis: the customer is satisfied and churn risk is low."
    assert any(p in violation.lower() for p in forbidden)
    legit = ("A complaint is registered when a customer expresses "
             "dissatisfaction with the service.")
    assert not any(p in legit.lower() for p in forbidden), \
        "the dictionary must spare 'expresses dissatisfaction'"
    # structural: no operational customer-data door.
    assert set(f for f in os.listdir(WB_DIR)
               if f.endswith(".py")) == {"runner.py"}
    print(f"Stage 7 passed: {quoted_hits} vocabulary byte(s), every one "
          f"quote-framed; plant facts yield ONLY assumption findings; the "
          f"dictionary catches the violation and spares 'expresses "
          f"dissatisfaction'; only runner.py in the bundle.")

    # ------------------------------------------------------- Stage 8
    print("\n--- Stage 8: the valve + the human gate ---")
    lane_b = db.SourceConnector(project_id=project.id, name="CS Lane",
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
        for a in lane_b_assets), "cs proposals held DERIVED at the gate"
    candidate = sorted(lane_b_assets, key=lambda a: a.id)[0]
    verdict = proposals.verify_provenance(session, candidate.document_id)
    assert verdict["provenance_verified"] is True, verdict["reasons"]
    crud.update_knowledge_asset(
        session, candidate.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted the cs finding")
    session.refresh(candidate)
    assert candidate.status == "APPROVED" and candidate.source_class == "DERIVED"
    print(f"Stage 8 passed: {len(lane_b_assets)} cs candidates held DERIVED; "
          f"provenance verified; one accepted -> APPROVED, still DERIVED.")

    # ------------------------------------------------------- Stage 9
    print("\n--- Stage 9: the bundle / registry / sweep proof ---")
    ratified = sorted(n[:-5] for n in os.listdir(os.path.join(WB_DIR, "skills"))
                      if n.endswith(".yaml"))
    assert ratified == sorted(ACTIVE_FIVE)
    manifest = open(os.path.join(WB_DIR, "workbench.yaml"),
                    encoding="utf-8").read()
    declared = re.findall(r"^  - (\w+)$", manifest.split("skills:\n")[1],
                          re.MULTILINE)[:5]
    assert sorted(declared) == sorted(ACTIVE_FIVE)
    assert "canonical_number: 6" in manifest
    registry = open(os.path.join(REPO_DIR, "docs",
                                 "workbench-skill-registry.md"),
                    encoding="utf-8").read()
    assert "## 6. Customer Success Intelligence Workbench — ACTIVE (v2.4)" \
        in registry
    es_draft = open(os.path.join(
        CS_DRAFTS, "detect_customer_obligations_without_owner.yaml"),
        encoding="utf-8").read()
    assert "status: SEQUENCED" in es_draft and "read-only" in es_draft \
        and "OWNER_ASSIGNED" in es_draft
    for oe in ("detect_declining_activity", "detect_low_usage",
               "detect_unresolved_customer_issues", "score_customer_risk",
               "cluster_recurring_complaints", "identify_churn_signals"):
        oe_text = open(os.path.join(CS_DRAFTS, oe + ".yaml"),
                       encoding="utf-8").read()
        assert "status: FUTURE" in oe_text, f"{oe} must stay FUTURE"
    active = consolidated = 0
    for folder, _dirs, files in os.walk(DRAFTS_DIR):
        for name in files:
            if not name.endswith(".yaml"):
                continue
            st = re.search(r"^status: (\S+)",
                           open(os.path.join(folder, name),
                                encoding="utf-8").read(), re.MULTILINE)
            if st and st.group(1) == "ACTIVE":
                active += 1
            elif st and st.group(1) == "CONSOLIDATED":
                consolidated += 1
    assert (active, consolidated) == GLOBAL_SWEEP, \
        f"global sweep must be {GLOBAL_SWEEP}, got {active}/{consolidated}"
    print(f"Stage 9 passed: 5 contracts + manifest agree; registry #6 "
          f"ACTIVE (v2.4); [ES] SEQUENCED read-only; six [OE] FUTURE; "
          f"global sweep {GLOBAL_SWEEP[0]}/{GLOBAL_SWEEP[1]} - no accidental "
          f"promotion.")

    # ------------------------------------------------------- Stage 10
    print("\n--- Stage 10: the catalog / presentation proof ---")
    page = open(PAGE_TSX, encoding="utf-8").read()
    rows = re.findall(r"'customer-success-intelligence':\s*\{[^}]*\}", page)
    assert len(rows) == 1, \
        f"EXACTLY ONE catalog row, got {len(rows)}"
    row = rows[0]
    assert "canonical: 6" in row and "'v2.4'" in row \
        and "Customer Success Intelligence" in row
    # presentation only: the row's wording claims no operational capability.
    for banned in ("crm", "churn", "telemetry", "ranking", "nps",
                   "outreach", "health score", "scoring", "prediction"):
        assert banned not in row.lower(), \
            f"the catalog row must not imply {banned!r}"
    # the row lives inside the WORKBENCH_CATALOG_INFO presentation map.
    info_block = page.split("WORKBENCH_CATALOG_INFO", 1)[1]
    assert "'customer-success-intelligence'" in info_block.split("};")[0]
    print("Stage 10 passed: EXACTLY ONE WORKBENCH_CATALOG_INFO row "
          "(customer-success-intelligence, #6, v2.4); wording claims no "
          "CRM/churn/telemetry/ranking/NPS/outreach/scoring capability.")

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
    print("Stage 11 passed: route manifest 88 (digest frozen - no new "
          "route); the nine MCP tools; D24 byte-identical at 28/305.")

    session.close()
    print("\n=== THE v2.4 MILESTONE GATE PASSED: per-customer term "
          "deviation, obligation windows, coverage gaps, and quoted "
          "unsupported assumptions from approved documents, register facts, "
          "and a declared clock - the register harvested BY id through the "
          "REAL chain, the conforming customer silent, the plant surfacing "
          "only through THE QUOTE FRAME, the human gate deciding "
          "everything, and the customer relationship's state never "
          "asserted anywhere. 28/305. ===")


if __name__ == "__main__":
    main()
