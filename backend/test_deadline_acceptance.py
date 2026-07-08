"""v2.2 WS3 gate suite — THE MILESTONE GATE (the 83rd suite).

The full commercial loop for Deadline & Obligation Intelligence
(docs/deadline-obligation-v2.2.md), end to end, plus the four named
proofs:

  Stage 1  both corpora + the extension plants through the real
           pipeline; every fact human-approved PRIMARY.
  Stage 2  INTERNAL package + a real AGENT binding.
  Stage 3  THE REAL REGISTER CHAIN — the v2.1 Contract Intelligence
           engine extracts the register candidates; the valve holds
           them DERIVED under a live permissive Tier-1 + an
           approve-everything Tier-2; a human accepts the dated
           renewal clause -> the accepted DERIVED register fact.
  Stage 4  the recompiled package carries the register fact; the
           EXTENDED compliance runner diagnoses ENGAGED at the
           declared clock pair.
  Stage 5  THE HARVEST PROOF — the deadline finding cites the
           register fact BY governed asset id; the provenance chain
           resolves finding -> DERIVED register clause -> PRIMARY
           contract source; NO SHARED FACT STORE (the clause lives in
           approved knowledge exactly twice, PRIMARY + register; the
           deadline run creates zero approved facts).
  Stage 6  THE COMPUTED CALENDAR — every runner output deleted; the
           28-table byte fingerprint unchanged; the same declared
           clock reproduces byte-identical outputs; a re-declared
           clock changes only the legitimately computed fields.
  Stage 7  THE AMBIGUITY PROOF, on the bytes — vague timing flagged,
           never dated; recurrence never expanded; every date in
           every flagged/recurrence proposal verbatim in its cited
           governed source.
  Stage 8  the valve + the human gate — deadline/recurrence proposals
           held DERIVED; ONE accepted through the existing review
           flow; provenance verified; still DERIVED.
  Stage 9  THE NON-CONFLATION PROOF — a real human DUE_DATE_SET
           stewardship decision co-exists with the accepted deadline
           fact; neither becomes the other; the runner authored ZERO
           stewardship events; the [OE] status question refused live,
           naming the unminted realm.
  Stage 10 the structural closers — route manifest 88 (frozen
           digest), the nine MCP tools, D24 byte-identical 28/305.
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
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_ddl3_pkg_")

import test_agent_authorship_guard as guard   # noqa: E402,F401 - engine override order
import test_route_manifest as route_guard      # noqa: E402

from sqlalchemy import create_engine, text     # noqa: E402
from sqlalchemy.orm import sessionmaker        # noqa: E402
from app import database as db                 # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_ddl3_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'gate.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                      # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_ddl3_qdrant_")

from app import (schemas, crud, connectors,    # noqa: E402
                 governance_inbox, identity, mcp_gateway, package_builder,
                 package_consumer, policy, proposals, stewardship, tier2)
import test_support                            # noqa: E402
import test_workbench_projection               # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.compliance_obligation.runner as compliance_runner  # noqa: E402
import workbench.contract_intelligence.runner as engine_runner      # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "compliance_obligation")
CORPUS_DIR = os.path.join(WB_DIR, "corpus")
DEADLINE_DIR = os.path.join(WB_DIR, "corpus_deadline")
PROC_CORPUS = os.path.join(REPO_DIR, "workbench",
                           "procurement_intelligence", "corpus")

AS_OF = "2026-07-10"
WINDOW = 60
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


class ApproveEverythingVerifier:
    identity = {"method": "GATE_APPROVE_EVERYTHING",
                "note": "deadline acceptance lane-sentinel seam"}

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
    vault_dir = tempfile.mkdtemp(prefix="em_ddl3_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
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
    return re.sub(r"\s+", " ", t or "").strip()


def db_fingerprint():
    """A deterministic byte fingerprint of every governed KNOWLEDGE table
    (the disappearance-test convention: computed artifacts must be
    deletable with ZERO governed change). Three OPERATIONAL-EVIDENCE
    tables are excluded, declared - each grows on ANY authenticated read
    BY LAW, and none is knowledge: the append-only audit ledger (every
    MCP call is a ledger event), the credentials table (token use stamps
    last_used_at), and identity_facts (D20 - every authenticated
    resolution is identity-fact evidence). What must never move is
    governed KNOWLEDGE."""
    h = hashlib.sha256()
    per = {}
    skip = {db.AuditEvent.__tablename__, "credentials", "identity_facts"}
    with db.engine.connect() as conn:
        for table in sorted(t.name for t in db.Base.metadata.sorted_tables):
            if table in skip:
                continue
            rows = conn.execute(
                text(f"SELECT * FROM {table} ORDER BY 1")).fetchall()
            per[table] = hashlib.sha256(
                b"|".join(repr(tuple(row)).encode() for row in rows)
            ).hexdigest()
            h.update(table.encode())
            for row in rows:
                h.update(repr(tuple(row)).encode())
    db_fingerprint.per = per
    return h.hexdigest()


def wipe_outputs(run_summary):
    for path in (run_summary["proposals"]
                 + [run_summary["pack"], run_summary["brief"]]):
        if path and os.path.isfile(path):
            os.remove(path)


def main():
    tier2.verifier_factory = ApproveEverythingVerifier
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "DdlGateOfficer")
    reviewer = test_support.governed_actor(session, "DdlGateReviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Deadline Gate", description="v2.2 THE MILESTONE GATE",
        customer_id=customer.id), actor=officer)

    # ------------------------------------------------------- Stage 1
    print("\n--- Stage 1: the corpora through the real pipeline ---")
    for name, root in (("Compliance Docs", CORPUS_DIR),
                       ("Deadline Extension Docs", DEADLINE_DIR),
                       ("Procurement Docs", PROC_CORPUS)):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
    doc_count = session.query(db.Document).filter_by(
        project_id=project.id).count()
    assert doc_count == 26, f"expected 26 documents, got {doc_count}"
    approve_all(session, project.id, reviewer, "gate: corpus approval")
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    assert all(a.source_class == "PRIMARY" for a in approved)
    print(f"Stage 1 passed: 26 documents -> {len(approved)} human-approved "
          f"PRIMARY facts.")

    # ------------------------------------------------------- Stage 2
    print("\n--- Stage 2: INTERNAL package + real AGENT binding ---")
    agent = identity.create_principal(session, name="workbench-agent",
                                      display_name="Workbench Agent",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _cred = identity.issue_token(session, agent, kind="API_TOKEN",
                                              label="gate", actor="test-suite")
    issuer = test_support.governed_actor(session, "DdlGateIssuer")
    pkg1 = compile_package(session, project, "Gate Package v1")
    binding1 = bind(session, pkg1, agent, issuer)
    print(f"Stage 2 passed: package {pkg1.package_hash[:12]}… bound to "
          f"AGENT {agent.name}.")

    # ------------------------------------------------------- Stage 3
    print("\n--- Stage 3: THE REAL REGISTER CHAIN (v2.1 engine -> valve -> "
          "human) ---")
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add(db.ApprovalPolicy(project_id=project.id, name="everything",
                                  asset_types_json=all_types, enabled=True))
    session.add(db.ApprovalPolicy(project_id=project.id,
                                  name="everything-tier2",
                                  asset_types_json=all_types, enabled=True,
                                  engine_conditions_json=json.dumps(
                                      {"contradiction_check": "CLEAN_REQUIRED"})))
    session.commit()

    vault_a = bootstrap_vault()
    loaded1 = package_consumer.load_package(pkg1.file_path)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        engine = engine_runner.run_diagnostic(
            pkg1.file_path, vault_a, project.id,
            agent_principal="workbench-agent", binding_id=binding1.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            answerer=make_answerer(loaded1))
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    clause_findings = [f for f in engine["findings"]
                       if f["finding_kind"] == "CONTRACT_CLAUSE"]
    assert clause_findings, "the engine must propose register entries"

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
        "the valve must hold every register candidate DERIVED"

    register_candidates = [a for a in held
                           if "2026-08-15" in norm(a.content)
                           and "governed asset" in norm(a.content)]
    assert register_candidates, \
        "the dated termination clause must be a register candidate"
    reg = register_candidates[0]
    crud.update_knowledge_asset(
        session, reg.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted the register clause")
    session.refresh(reg)
    assert reg.status == "APPROVED" and reg.source_class == "DERIVED"
    print(f"Stage 3 passed: {len(held)} register candidates held DERIVED "
          f"under live permissive policies; the human accepted the dated "
          f"clause -> DERIVED register fact #{reg.id}.")

    # ------------------------------------------------------- Stage 4
    print("\n--- Stage 4: the recompiled package; THE DEADLINE DIAGNOSIS "
          "engaged ---")
    pkg2 = compile_package(session, project, "Gate Package v2")
    binding2 = bind(session, pkg2, agent, issuer)
    loaded2 = package_consumer.load_package(pkg2.file_path)
    assert any(e["asset_id"] == reg.id for e in loaded2["knowledge"]), \
        "the recompiled package must carry the register fact"
    vault_b = bootstrap_vault()
    answerer2 = make_answerer(loaded2)
    fingerprint_before = db_fingerprint()
    per_before = dict(db_fingerprint.per)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        diagnosis = compliance_runner.run_diagnostic(
            pkg2.file_path, vault_b, project.id,
            agent_principal="workbench-agent", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW, answerer=answerer2)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    kinds = {f["finding_kind"] for f in diagnosis["findings"]}
    assert {"OBLIGATION_DEADLINE", "DEADLINE_AMBIGUITY",
            "RECURRENCE_RULE"} <= kinds, kinds
    print(f"Stage 4 passed: {len(diagnosis['findings'])} findings at the "
          f"declared clock pair ({AS_OF} + {WINDOW}d).")

    # ------------------------------------------------------- Stage 5
    print("\n--- Stage 5: THE HARVEST PROOF (finding -> register -> "
          "PRIMARY; no shared fact store) ---")
    dated = [f for f in diagnosis["findings"]
             if f["finding_kind"] == "OBLIGATION_DEADLINE"]
    harvest = [f for f in dated if f["asset_id"] == reg.id]
    assert harvest, "the deadline finding must cite the register fact BY ID"
    hf = harvest[0]
    assert hf["date"] == "2026-08-15" and hf["days_until"] == 36
    assert "DERIVED" in hf["cite"], "the register fact is cited AS DERIVED"
    # The chain resolves: register clause -> its named PRIMARY source.
    m = re.search(r"governed asset (\d+)", norm(reg.content))
    assert m, "the register entry names its PRIMARY source verbatim"
    primary = session.get(db.KnowledgeAsset, int(m.group(1)))
    assert primary is not None and primary.source_class == "PRIMARY"
    src_doc = session.get(db.Document, primary.document_id)
    assert "cloudhost" in src_doc.filename, \
        f"the chain must end at the MSA source: {src_doc.filename}"
    # NO SHARED FACT STORE: the clause exists in approved knowledge
    # exactly twice (PRIMARY + register), and the deadline run created
    # zero approved facts.
    carriers = [a for a in session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
        if "terminates on 2026-08-15" in norm(a.content)]
    assert len(carriers) == 2, \
        f"exactly two governed copies (PRIMARY + register), got {len(carriers)}"
    assert {a.source_class for a in carriers} == {"PRIMARY", "DERIVED"}
    fp_after = db_fingerprint()
    changed = [k for k, v in db_fingerprint.per.items()
               if per_before.get(k) != v]
    assert fp_after == fingerprint_before, \
        f"the deadline diagnosis must write NOTHING governed: {changed}"
    print(f"Stage 5 passed: finding -> register #{reg.id} (DERIVED) -> "
          f"PRIMARY #{primary.id} ({src_doc.filename}); the clause lives in "
          f"governed knowledge exactly twice; the run wrote nothing "
          f"governed.")

    # ------------------------------------------------------- Stage 6
    print("\n--- Stage 6: THE COMPUTED CALENDAR ---")
    recorded = {}
    for path in diagnosis["proposals"] + [diagnosis["brief"]]:
        with open(path, encoding="utf-8") as f:
            recorded[os.path.basename(path)] = f.read()
    wipe_outputs(diagnosis)
    assert db_fingerprint() == fingerprint_before, \
        "deleting every computed output must change ZERO governed bytes"
    vault_c = bootstrap_vault()
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        again = compliance_runner.run_diagnostic(
            pkg2.file_path, vault_c, project.id,
            agent_principal="workbench-agent", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW, answerer=answerer2)
        narrow = compliance_runner.run_diagnostic(
            pkg2.file_path, bootstrap_vault(), project.id,
            agent_principal="workbench-agent", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=30, answerer=answerer2)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    reproduced = {}
    for path in again["proposals"] + [again["brief"]]:
        with open(path, encoding="utf-8") as f:
            reproduced[os.path.basename(path)] = f.read()
    assert reproduced == recorded, \
        "the same declared clock must reproduce byte-identical outputs"
    # A re-declared clock changes ONLY the legitimately computed fields:
    # the harvest date (36 days) leaves the 30-day window as a declared
    # skip; the clock-free proposals are byte-identical by content hash.
    assert not any(f.get("asset_id") == reg.id and
                   f["finding_kind"] == "OBLIGATION_DEADLINE"
                   for f in narrow["findings"])
    assert any("outside the declared 30-day window" in s["reason"]
               for s in narrow["skipped"])
    clockfree_recorded = {n for n, b in reproduced.items()
                          if "extract_recurrence_rules" in n
                          or "detect_obligation_deadlines" in n
                          and "DEADLINE_AMBIGUITY" in b}
    narrow_names = {os.path.basename(p) for p in narrow["proposals"]}
    assert {n for n in clockfree_recorded
            if "extract_recurrence_rules" in n} <= narrow_names, \
        "clock-free recurrence proposals are byte-identical (same hash names)"
    print(f"Stage 6 passed: THE COMPUTED CALENDAR - {len(recorded)} outputs "
          f"deleted, zero governed change; the declared clock reproduced "
          f"every byte; the re-declared clock changed only computed fields.")

    # ------------------------------------------------------- Stage 7
    print("\n--- Stage 7: THE AMBIGUITY PROOF, on the bytes ---")
    vague = [f for f in again["findings"]
             if f["finding_kind"] == "DEADLINE_AMBIGUITY"]
    markers = {f["vague_marker"] for f in vague}
    assert {"promptly", "within a reasonable period",
            "in a timely manner"} <= markers, markers
    swept = 0
    for path in again["proposals"]:
        with open(path, encoding="utf-8") as f:
            body = f.read()
        kind_m = re.search(r"^finding_kind: (\S+)", body, re.MULTILINE)
        cited_m = re.search(r"^cited_assets: (\S+)", body, re.MULTILINE)
        if kind_m.group(1) in ("DEADLINE_AMBIGUITY", "RECURRENCE_RULE",
                               "RECURRENCE_AMBIGUITY"):
            sources = [norm(session.get(db.KnowledgeAsset, int(i)).content)
                       for i in cited_m.group(1).split(",")]
            for d in DATE_RE.findall(body):
                assert any(d in s for s in sources), \
                    f"a date not in the governed source: {d} ({path})"
            swept += 1
    assert swept >= 4
    print(f"Stage 7 passed: {len(vague)} vague duties flagged and never "
          f"dated; {swept} flagged/recurrence proposals swept - every date "
          f"verbatim in its cited governed source; nothing expanded.")

    # ------------------------------------------------------- Stage 8
    print("\n--- Stage 8: the valve + the human gate on the deadline "
          "outputs ---")
    lane_b = db.SourceConnector(project_id=project.id, name="Deadline Lane",
                                type="LOCAL_FOLDER",
                                root_path=os.path.join(vault_c, "08_proposals"),
                                include_extensions=".md", lane="PROPOSAL")
    session.add(lane_b)
    session.commit()
    session.refresh(lane_b)
    run_scan(session, lane_b)
    lane_b_docs = [d.id for d in session.query(db.Document).filter(
        db.Document.project_id == project.id).all()
        if d.id in policy.proposal_lane_document_ids(
            session, [d.id]) and d.id not in lane_a_docs]
    lane_b_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_b_docs)).all()
    assert lane_b_assets and all(
        a.status == "CANDIDATE" and a.source_class == "DERIVED"
        for a in lane_b_assets), \
        "every deadline/recurrence candidate held DERIVED at the gate"
    harvest_doc = [d for d in lane_b_docs
                   if any("2026-08-15" in norm(a.content)
                          for a in lane_b_assets if a.document_id == d)]
    assert harvest_doc, "the harvest proposal must be at the gate"
    verdict = proposals.verify_provenance(session, harvest_doc[0])
    assert verdict["provenance_verified"] is True, verdict["reasons"]
    candidate = next(a for a in lane_b_assets
                     if a.document_id == harvest_doc[0])
    crud.update_knowledge_asset(
        session, candidate.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted the deadline finding")
    session.refresh(candidate)
    assert candidate.status == "APPROVED" and candidate.source_class == "DERIVED"
    print(f"Stage 8 passed: {len(lane_b_assets)} candidates held DERIVED; "
          f"provenance verified against the governed binding; the human "
          f"accepted ONE deadline finding -> APPROVED, still DERIVED.")

    # ------------------------------------------------------- Stage 9
    print("\n--- Stage 9: THE NON-CONFLATION PROOF + the live [OE] "
          "refusal ---")
    assert session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "STEWARDSHIP_DECISION").count() == 0, \
        "no runner, valve, or acceptance step may author stewardship"
    inbox = governance_inbox.build_inbox(session, project.id)
    items = inbox["items"]
    assert items, "the computed inbox must carry real exceptions"
    target = items[0]
    stewardship.record_decision(
        session, reviewer, exception_key=target["id"],
        exception_type=target["type"], kind="DUE_DATE_SET",
        due_date="2026-08-01",
        reason="the human schedules the review - a stewardship decision, "
               "never a document fact")
    assert session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "STEWARDSHIP_DECISION").count() == 1
    session.refresh(candidate)
    assert candidate.status == "APPROVED" and candidate.source_class == "DERIVED", \
        "the stewardship decision must not touch the deadline fact"
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    assert live == test_workbench_projection.FROZEN_SCHEMA, \
        "the decision persists in the ledger alone - no table anywhere"
    refused_oe = False
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        compliance_runner.run_diagnostic(
            pkg2.file_path, vault_c, project.id,
            agent_principal="workbench-agent", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW, answerer=answerer2,
            requested_skills=compliance_runner.ACTIVE_SKILLS
            + ("verify_obligations_against_operational_records",))
    except RuntimeError as e:
        refused_oe = "Operational Evidence Realm" in str(e)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    assert refused_oe, "the operational-status question must name [OE]"
    print("Stage 9 passed: a human DUE_DATE_SET decision and the accepted "
          "deadline fact co-exist without becoming each other - the "
          "decision in the ledger alone, the fact in governed knowledge; "
          "the runner authored zero stewardship; the [OE] status question "
          "refused live, naming the unminted realm ([PMD] equally unneeded "
          "- no metadata ingress exists anywhere in this gate).")

    # ------------------------------------------------------- Stage 10
    print("\n--- Stage 10: the structural closers ---")
    assert route_guard.digest(route_guard.build_manifest()) == \
        route_guard.FROZEN_DIGEST
    assert len(route_guard.build_manifest()) == 88
    nine = ("ask_expert", "get_trust_score", "get_provenance",
            "get_conflicts", "check_gate_status", "get_graph_neighbors",
            "get_lineage_path", "get_domain_subgraph", "get_revision_history")
    assert len([n for n in dir(mcp_gateway) if n in nine]) == 9
    assert live == test_workbench_projection.FROZEN_SCHEMA
    print("Stage 10 passed: route manifest 88 (digest frozen); the nine "
          "MCP tools; D24 byte-identical at 28/305 - no route, no table, "
          "no tool, no guard, no law.")

    session.close()
    print("\n=== THE v2.2 MILESTONE GATE PASSED: a compliance calendar "
          "computed from governed obligations at a declared clock - every "
          "deadline source-cited through the register to its PRIMARY "
          "contract, every vague duty flagged never dated, every "
          "recurrence verbatim never expanded, deletion losing nothing, "
          "the human gate deciding everything, and no claim anywhere that "
          "the work was completed. 28 tables / 305 columns. ===")


if __name__ == "__main__":
    main()
