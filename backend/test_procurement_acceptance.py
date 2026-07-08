"""v1.8 WS3 - THE MILESTONE GATE for the Procurement Document
Intelligence Workbench, with THE CLAUSE ARITHMETIC PROOF.

The full commercial loop, once, end to end: the ratified corpus enters
through the real governed pipeline -> PRIMARY facts approved by a human
into the `procurement` domain -> an INTERNAL package is compiled and
bound to a real AGENT principal -> the workbench diagnoses through the
doors at the declared as_of + window_days, honoring the six ratified
contracts -> one proposal per finding lands in /08_proposals -> the
valve holds every candidate DERIVED under a global permissive Tier-1
policy AND a live approve-everything Tier-2 engine -> a human accepts
one finding per kind -> APPROVED DERIVED facts with verified synthesis
provenance.

THEN THE CLAUSE ARITHMETIC PROOF (the distinctive v1.8 stage): every
number in every Finding statement is traceable - it appears verbatim in
a cited governed asset's content, or it is the declared clock (as_of /
window_days) or the deterministic days-until arithmetic over a verbatim
date. "one fifth" stays text and "20%" appears in no written byte; the
unparseable date is refused, declared; the noisy irrelevant numbers
appear in no proposal; the explicit 7% is quoted verbatim; window
positive/negative, the auto-renewal facet, supplier-named certification
coverage, and the vendor-policy conflict positive/negative all hold; no
persistent calendar exists ANYWHERE (no new file, no schema, refusal
proven); [OE]/[ES]/SEQUENCED refuse live.

Then the standing composition machinery re-proven (an accepted DERIVED
vendor fact travels into the recompiled package and is cited AS DERIVED
by a second-generation finding), the vault before/after (accepted
findings as marked DERIVED notes; the untouchable floor intact), and
THE CLOSING LINES: the ledger alone proves no agent principal wrote
canonical facts; every APPROVED DERIVED fact has a human review; the
EXECUTIVE sentinel absent from every written byte; the D24 snapshot at
exactly 28 tables / 305 columns.

THE COMMERCIAL VERDICT is not automated: the user reads the exported
diagnosis as the PROCUREMENT/FINANCE reader (EM_COMMERCIAL_ARTIFACT_DIR
exports the proposals + the renegotiation brief). The real-model honest
slot is reported at the end.
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
else:
    os.environ.setdefault("EM_CONFLICT_MAX_PAIRS", "2000")
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_procacc_pkg_")
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_procacc_render_")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_procacc_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'accept.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_procacc_qdrant_")

from app import (schemas, crud, connectors, conflict_engine,  # noqa: E402
                 package_builder, package_consumer, identity, mcp_gateway,
                 policy, proposals, tier2)
from app.projections import engine as projection_engine   # noqa: E402
import test_support                           # noqa: E402
import test_workbench_projection              # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.procurement_intelligence.runner as runner   # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "procurement_intelligence")
CORPUS_DIR = os.path.join(WB_DIR, "corpus")
SENTINEL = "EM-EXEC-SENTINEL-4V8P"
AS_OF = "2026-06-01"
WINDOW_DAYS = 90
KIND_TO_SKILL = {kind: skill for skill, (kind, _b) in runner.FINDING_KINDS.items()}


class ApproveEverythingVerifier:
    identity = {"method": "GUARD_APPROVE_EVERYTHING",
                "note": "procurement acceptance lane-sentinel seam"}

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
    """The declared deterministic CI contract-follower with SUPPLIER-NAMED
    COVERAGE (the ratified evidence rule)."""
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


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


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


def bind_agent(session, package_row, agent, issuer):
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
    return binding


def main():
    db.init_db()
    tier2.verifier_factory = ApproveEverythingVerifier
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "ProcAcceptOfficer")
    reviewer = test_support.governed_actor(session, "ProcAcceptReviewer")
    issuer = test_support.governed_actor(session, "ProcAcceptIssuer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Procurement Intelligence", description="THE MILESTONE GATE",
        customer_id=customer.id), actor=officer)

    # ------------------------------------------------------- Stage 1
    print("\n--- Stage 1: the ratified corpus through the real pipeline ---")
    primary = db.SourceConnector(project_id=project.id, name="Procurement Docs",
                                 type="LOCAL_FOLDER", root_path=CORPUS_DIR,
                                 include_extensions=".md")
    session.add(primary)
    session.commit()
    session.refresh(primary)
    run_scan(session, primary)
    assert session.query(db.Document).filter_by(
        project_id=project.id).count() == 12
    approve_all(session, project.id, reviewer, "acceptance: procurement corpus",
                domain="procurement")
    memo_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename.like("%executive-vendor-strategy%")).first()
    for a in session.query(db.KnowledgeAsset).filter_by(
            document_id=memo_doc.id).all():
        a.access_level = "EXECUTIVE"
    session.commit()
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    assert all(a.domain == "procurement" for a in approved)
    print(f"Stage 1 passed: {len(approved)} PRIMARY facts approved by a human "
          "into the `procurement` domain; the EXECUTIVE memo seeded above the "
          "package clearance.")

    # ------------------------------------------------------- Stage 2
    print("\n--- Stage 2: INTERNAL package, real AGENT binding, conflicts ---")
    model, package_row = build_package_for(
        session, project.id, "Procurement Expert", [a.id for a in approved])
    loaded = package_consumer.load_package(package_row.file_path)
    packaged_ids = {e["asset_id"] for e in loaded["knowledge"]}
    exec_ids = {a.id for a in approved if a.access_level == "EXECUTIVE"}
    assert not (exec_ids & packaged_ids), "EXECUTIVE assets must be excluded"
    agent = identity.create_principal(session, name="procurement-intelligence",
                                      display_name="Procurement Intelligence",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _cred = identity.issue_token(session, agent, kind="API_TOKEN",
                                              label="acceptance",
                                              actor="test-suite")
    binding = bind_agent(session, package_row, agent, issuer)

    def find(needle):
        return next(a for a in approved if needle in norm(a.content))
    if REAL_NLI:
        summary = conflict_engine.scan_expert_model_conflicts(session, model.id)
        assert summary["nli_available"]
        mode = f"REAL NLI ({summary['compared_pairs']} pairs)"
    else:
        session.add(db.AssetRelationship(
            project_id=project.id, expert_model_id=model.id,
            source_asset_id=find("payable within 21 days").id,
            target_asset_id=find("at least 45 days").id,
            relationship_type="CONFLICTS_WITH",
            classification="DIRECT_CONTRADICTION", confidence=0.99,
            status="DETECTED",
            verifier_json=json.dumps({"method": "TEST_FIXTURE"})))
        session.commit()
        mode = "declared fixture conflicts (real-NLI = WS1 gate evidence)"
    print(f"Stage 2 passed: INTERNAL package + real AGENT binding; {mode}.")

    # ------------------------------------------------------- Stage 3
    print("\n--- Stage 3: THE DIAGNOSIS through the doors (declared clock) ---")
    vault_dir = tempfile.mkdtemp(prefix="em_procacc_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    answerer = make_answerer(loaded)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        diagnosis = runner.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="procurement-intelligence", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW_DAYS, answerer=answerer)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    kinds = {f["finding_kind"] for f in diagnosis["findings"]}
    assert set(KIND_TO_SKILL) <= kinds, f"kinds missing: {kinds}"
    artifact_dir = os.environ.get("EM_COMMERCIAL_ARTIFACT_DIR")
    if artifact_dir:
        os.makedirs(artifact_dir, exist_ok=True)
        for path in diagnosis["proposals"] + [diagnosis["brief"]]:
            shutil.copy(path, artifact_dir)
    print(f"Stage 3 passed: {len(diagnosis['proposals'])} per-finding "
          f"proposals across all five kinds at as_of {AS_OF}/+{WINDOW_DAYS}d.")

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
        candidates = sorted((a for a in lane_assets if a.document_id == doc.id),
                            key=lambda a: a.id)
        # prefer a marker-carrying candidate: the accepted DERIVED fact must
        # be re-extractable in the recompiled package (the composition
        # standing check in Stage 7 - the v1.7 selection pattern).
        with_marker = [a for a in candidates
                       if re.search(r"(must|shall)", norm(a.content))]
        candidate = (with_marker or candidates)[0]
        crud.update_knowledge_asset(
            session, candidate.id,
            schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=reviewer, review_notes=f"human accepted the {kind} finding")
        session.refresh(candidate)
        assert candidate.status == "APPROVED"
        assert candidate.source_class == "DERIVED"
        event = session.query(db.AuditEvent).filter_by(
            event_type="ASSET_APPROVED", target_id=str(candidate.id)).order_by(
            db.AuditEvent.id.desc()).first()
        prov = json.loads(event.details)["synthesis_provenance"]
        assert prov["provenance_verified"] is True
        assert prov["claimed"]["agent_principal"] == "procurement-intelligence"
        assert prov["verified"]["binding_id"] == binding.id
        assert prov["verified"]["package_hash"] == package_row.package_hash
        assert prov["cited_assets"]["missing"] == []
        accepted[kind] = candidate
    print(f"Stage 5 passed: {len(accepted)} APPROVED DERIVED facts (one per "
          "kind), each approval event quoting VERIFIED synthesis provenance.")

    # ------------------------------------------------------- Stage 6
    print("\n--- Stage 6: THE CLAUSE ARITHMETIC PROOF ---")
    by_id = {a.id: norm(a.content) for a in approved}
    import datetime
    as_of_date = datetime.date(*(int(p) for p in AS_OF.split("-")))
    declared_numbers = {str(WINDOW_DAYS)} | set(AS_OF.split("-")) | {AS_OF}

    checked_numbers = 0
    for path in diagnosis["proposals"]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        # the noisy irrelevant numbers appear in NO proposal
        for noisy in ("4501 Commerce Park", "555 0142", "clause 12.3", "700000"):
            assert noisy not in text, f"noisy number promoted: {noisy}"
        assert "20%" not in text, "the converted paraphrase must never appear"
        assert SENTINEL not in text
        # every number in the Finding statement is traceable: verbatim in a
        # cited asset's governed content, or the declared clock / the
        # days-until arithmetic over a verbatim date.
        parsed = proposals.parse_frontmatter(text)
        cited = [int(t) for t in parsed["claims"]["cited_assets"].split(",") if t]
        cited_content = " ".join(by_id.get(i, "") for i in cited)
        statement = text.split("## Finding", 1)[1].split("## Evidence", 1)[0]
        # citation ids ("asset 21") are governed identifiers, not clause
        # numbers - the frontmatter already verifies them against the
        # packaged ids; exclude them from the arithmetic sweep.
        statement = re.sub(r"asset \d+", "asset", statement)
        allowed_computed = set(declared_numbers)
        for date_m in re.finditer(r"\d{4}-\d{2}-\d{2}", cited_content):
            d = datetime.date(*(int(p) for p in date_m.group(0).split("-")))
            allowed_computed.add(str((d - as_of_date).days))
        for num in re.findall(r"\d[\d,.\-]*%?", statement):
            token = num.rstrip(".,")
            ok = (token in cited_content or token in allowed_computed
                  or token in AS_OF)
            assert ok, (f"{os.path.basename(path)}: number {token!r} in the "
                        f"Finding statement is neither verbatim-cited nor the "
                        f"declared clock arithmetic - THE INVENTED NUMBER")
            checked_numbers += 1
    # the specific plants, re-asserted at the gate:
    def finding(kind):
        return [f for f in diagnosis["findings"] if f["finding_kind"] == kind]
    p1 = [f for f in finding("RENEWAL_WINDOW")
          if "2026-08-15" in f["excerpt"]]
    assert p1 and p1[0]["days_until"] == 75 and p1[0]["auto_renewal_excerpt"]
    assert not any("2027-09-30" in f["excerpt"]
                   for f in finding("RENEWAL_WINDOW")), "window negative silent"
    assert any("no parseable date" in s["reason"] for s in diagnosis["skipped"])
    prices = finding("PRICE_INCREASE_CLAUSE")
    assert any("7%" in f["excerpt"] and not f["non_numeric"] for f in prices)
    trap = [f for f in prices if "one fifth" in f["excerpt"]]
    assert trap and trap[0]["non_numeric"] and not re.search(r"\d", trap[0]["excerpt"])
    missing = finding("MISSING_SUPPLIER_CERTIFICATION")
    assert any(f["supplier"] == "DataFlow" for f in missing)
    assert not any(f["supplier"] == "SecureStore" for f in missing)
    conflicts = finding("VENDOR_POLICY_CONFLICT")
    assert any("21 days" in f["excerpt_contract"] + f["excerpt_policy"]
               for f in conflicts)
    # no persistent calendar exists anywhere: the refusal is live and no
    # calendar-shaped artifact was written.
    refused_calendar = False
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        runner.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="procurement-intelligence", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW_DAYS, answerer=answerer,
            persistent_calendar=True)
    except RuntimeError as e:
        refused_calendar = "persistent renewal calendar" in str(e)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    assert refused_calendar, "the persistent-calendar request must refuse"
    for root, _dirs, files in os.walk(vault_dir):
        for name in files:
            assert "calendar" not in name.lower(), \
                "no calendar-shaped artifact may exist"
    # [OE]/[ES]/SEQUENCED refuse live (re-asserted at the gate):
    for extra, needle in (("compare_contract_pricing_vs_invoices",
                           "Operational Evidence Realm"),
                          ("identify_owner_gaps", "Exception Stewardship"),
                          ("propose_vendor_consolidation", "SEQUENCED")):
        refused = False
        os.environ["EM_AGENT_TOKEN"] = agent_token
        try:
            runner.run_diagnostic(
                package_row.file_path, vault_dir, project.id,
                agent_principal="procurement-intelligence",
                binding_id=binding.id, graph_client=InProcessGraphClient(),
                as_of=AS_OF, window_days=WINDOW_DAYS, answerer=answerer,
                requested_skills=runner.ACTIVE_SKILLS + (extra,))
        except RuntimeError as e:
            refused = needle in str(e)
        finally:
            os.environ.pop("EM_AGENT_TOKEN", None)
        assert refused, f"{extra} must refuse naming {needle}"
    print(f"Stage 6 passed: THE CLAUSE ARITHMETIC PROOF - {checked_numbers} "
          "numbers across every Finding statement each traceable to a "
          "verbatim-cited clause or the declared clock arithmetic; the trap "
          "stayed text; the unparseable date refused; window both directions; "
          "supplier-named coverage; conflict both directions; no calendar "
          "anywhere; [OE]/[ES]/SEQUENCED refused live.")

    # ------------------------------------------------------- Stage 7
    print("\n--- Stage 7: composition standing - DERIVED travels and is cited ---")
    approved_now = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    derived_ids = {a.id for a in approved_now if a.source_class == "DERIVED"}
    assert derived_ids == {a.id for a in accepted.values()}
    model2, package_row2 = build_package_for(
        session, project.id, "Procurement Expert v2",
        [a.id for a in approved_now])
    loaded2 = package_consumer.load_package(package_row2.file_path)
    classes = {e["asset_id"]: e.get("source_class")
               for e in loaded2["knowledge"]}
    assert {i for i, c in classes.items() if c == "DERIVED"} == derived_ids, \
        "accepted DERIVED facts must travel into the recompiled package"
    candidate_ids = {a.id for a in session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="CANDIDATE").all()}
    assert not (candidate_ids & set(classes)), \
        "pending proposals must never enter the recompiled package"
    binding2 = bind_agent(session, package_row2, agent, issuer)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        second = runner.run_diagnostic(
            package_row2.file_path, vault_dir, project.id,
            agent_principal="procurement-intelligence", binding_id=binding2.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW_DAYS, answerer=make_answerer(loaded2))
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    gen2 = [f for f in second["findings"]
            if set(f["cited_assets"]) & derived_ids]
    assert gen2, "a second-generation finding must cite a DERIVED asset"
    g2_path = next(p for p in second["proposals"] if p not in diagnosis["proposals"])
    sample = [p for p in second["proposals"]
              if p not in diagnosis["proposals"]]
    derived_flagged = False
    for p in sample:
        with open(p, encoding="utf-8") as f:
            if "[DERIVED]" in f.read():
                derived_flagged = True
                break
    assert derived_flagged, "DERIVED citations must be flagged in proposal bytes"
    print(f"Stage 7 passed: {len(derived_ids)} accepted DERIVED facts traveled "
          f"into the recompiled package (pending proposals structurally "
          f"absent); {len(gen2)} second-generation finding(s) cite DERIVED "
          "evidence, flagged [DERIVED] in the proposal bytes - the v1.7 "
          "composition machinery standing.")

    # ------------------------------------------------------- Stage 8
    print("\n--- Stage 8: the vault before/after ---")
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
                    assert "This note is not canonical." in text
                    derived_notes += 1
    assert derived_notes == len(accepted)
    for path in diagnosis["proposals"] + second["proposals"]:
        assert os.path.isfile(path), "regeneration must never touch 08_proposals"
    print(f"Stage 8 passed: all {derived_notes} accepted findings render as "
          "marked DERIVED notes, visibly non-canonical; the untouchable floor "
          "held through the render.")

    # ------------------------------------------------------- Stage 9
    print("\n--- Stage 9: THE CLOSING LINES ---")
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
                    assert SENTINEL.encode() not in f.read()
                swept += 1
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    assert live == test_workbench_projection.FROZEN_SCHEMA
    tables, columns = len(live), sum(len(c) for c in live.values())
    assert (tables, columns) == (28, 305), (tables, columns)
    print(f"Stage 9 passed: every approval event carries a non-AGENT identity "
          f"fact; every APPROVED DERIVED fact has a human review; {swept} "
          f"files swept clean of the EXECUTIVE sentinel; the D24 snapshot "
          f"stands at exactly {tables} tables / {columns} columns.")

    # ------------------------------------------------------- Honest slot
    key = os.environ.get("OPENAI_API_KEY", "")
    real_key = bool(key) and key != "mock-key" or bool(
        os.environ.get("ANTHROPIC_API_KEY"))
    print("\nHonest slot - the ONE real-model diagnostic run: "
          + ("a provider key is present; run the workbench without the "
             "injected answerer/narrator and append the evidence."
             if real_key else
             "PENDING (no provider key in this environment; the runner's "
             "stdio MCP door and D19 synthesis path are code-complete)."))

    session.close()
    print("\n=== THE v1.8 MILESTONE GATE PASSED: the full commercial loop, "
          "once, end to end - every number verbatim, every window computed "
          "on the declared clock, held by the valve, accepted by a human, "
          "DERIVED visible everywhere it travels, with the ledger proving "
          "no agent wrote canonical facts. 28 tables / 305 columns. ===")


if __name__ == "__main__":
    main()
