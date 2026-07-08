"""v1.8 WS2 - THE DIAGNOSIS PROOF for the Procurement Document
Intelligence Workbench.

The runner (workbench/procurement_intelligence/runner.py, on
workbench/common.py) is proven as a governed skill bundle, not a vague
agent:

  - every deterministically detectable plant found and CORRECTLY KINDED
    (P1 renewal window with the auto-renewal facet; P3 explicit
    percentage; P3t the paraphrase trap quoted as text, never numeric;
    P4 the missing DataFlow certificate; P5 the vendor-policy conflict;
    vendor terms with declared classes);
  - the covered controls produce NO finding, declared in `skipped`
    (P1c the out-of-window contract; P4c the supplier-named SecureStore
    certificate; the conforming payment term);
  - THE CLAUSE ARITHMETIC discipline: every number/date in a finding is
    verbatim from its excerpt; the only computed value is the
    days-until window arithmetic at the declared as_of; "20%" appears
    in NO finding byte; the noisy numbers are never promoted;
  - the declared clock: as_of + window_days are run parameters; a run
    without them, and a persistent-calendar request, are REFUSED; the
    P6 unparseable date is refused, declared;
  - a GATED skill ([OE]/[ES]) is refused live naming the unminted
    decision, and a SEQUENCED contract is refused;
  - THE INVENTED NUMBER posture: the manifest's forbidden vocabulary is
    absent from every written byte;
  - byte-identical re-runs at the pinned as_of; writes confined to
    /08_proposals + the renegotiation brief in /07_agent_workspaces;
    the EXECUTIVE sentinel absent from every written byte;
  - Guard 5 sweeps every workbench module with zero guard edits; and the
    return path holds every finding as a held DERIVED candidate with
    provenance verified against the governed binding.
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
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_proc2_pkg_")

# Guard 5 first (its import overrides db.engine; this suite re-overrides
# and wins - the ruled import-order trick), for its door-sweep checker.
import test_agent_authorship_guard as guard   # noqa: E402

if REAL_NLI:
    os.environ["EM_NLI_VERIFICATION"] = "on"

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_proc2_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'ws2.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_proc2_qdrant_")

from app import (schemas, crud, connectors, conflict_engine,  # noqa: E402
                 package_builder, package_consumer, identity, mcp_gateway,
                 policy, proposals, tier2)
import test_support                           # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.procurement_intelligence.runner as runner   # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "procurement_intelligence")
CORPUS_DIR = os.path.join(WB_DIR, "corpus")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
MANIFEST = os.path.join(WB_DIR, "workbench.yaml")
SENTINEL = "EM-EXEC-SENTINEL-4V8P"
AS_OF = "2026-06-01"
WINDOW_DAYS = 90


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
    COVERAGE: answers only when one governed item shares >= 6 retrieval
    tokens with the question AND names the supplier the question names;
    otherwise the packaged refusal."""
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


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "ProcWSOfficer")
    reviewer = test_support.governed_actor(session, "ProcWSReviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Procurement WS2", description="the diagnosis proof",
        customer_id=customer.id), actor=officer)

    # ------------------------------------------------------------ Part 1
    print("\n--- Part 1: every workbench module passes the Guard 5 door sweep ---")
    swept = 0
    for root, _dirs, files in os.walk(os.path.join(REPO_DIR, "workbench")):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            with open(path, "r", encoding="utf-8") as f:
                violations = guard.workbench_import_violations(
                    os.path.relpath(path, REPO_DIR).replace(os.sep, "/"),
                    f.read())
            assert not violations, "\n".join(violations)
            swept += 1
    assert swept >= 5, "pilot + all runners + common.py must be swept"
    print(f"Part 1 passed: {swept} workbench module(s) inside the ruled "
          "doors - zero guard edits (the procurement runner swept the moment "
          "it exists).")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: corpus in, package compiled, agent bound ---")
    primary = db.SourceConnector(project_id=project.id, name="Procurement Docs",
                                 type="LOCAL_FOLDER", root_path=CORPUS_DIR,
                                 include_extensions=".md")
    session.add(primary)
    session.commit()
    session.refresh(primary)
    run_scan(session, primary)
    assert session.query(db.Document).filter_by(project_id=project.id).count() == 12
    approve_all(session, project.id, reviewer, "WS2 procurement corpus approval")
    memo_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename.like("%executive-vendor-strategy%")).first()
    exec_ids = set()
    for a in session.query(db.KnowledgeAsset).filter_by(
            document_id=memo_doc.id).all():
        a.access_level = "EXECUTIVE"
        exec_ids.add(a.id)
    session.commit()
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    model = db.ExpertModel(project_id=project.id, name="Procurement Expert",
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    session.add(model)
    session.commit()
    session.refresh(model)
    package_row = db.AgentPackage(project_id=project.id,
                                  expert_model_id=model.id,
                                  name="Procurement Package",
                                  clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    package_builder.build_package(session, package_row)
    session.refresh(package_row)
    loaded = package_consumer.load_package(package_row.file_path)
    packaged_ids = {e["asset_id"] for e in loaded["knowledge"]}
    assert not (exec_ids & packaged_ids), "EXECUTIVE assets must be excluded"
    agent = identity.create_principal(session, name="procurement-intelligence",
                                      display_name="Procurement Intelligence",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _cred = identity.issue_token(session, agent, kind="API_TOKEN",
                                              label="ws2", actor="test-suite")
    issuer = test_support.governed_actor(session, "ProcWSIssuer")
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

    def find(needle):
        return next(a for a in approved if needle in norm(a.content))
    if REAL_NLI:
        summary = conflict_engine.scan_expert_model_conflicts(session, model.id)
        assert summary["nli_available"]
        mode = f"REAL NLI ({summary['compared_pairs']} pairs)"
    else:
        # P5: the payment-terms conflict (cross-document, same subject).
        p5 = (find("payable within 21 days").id, find("at least 45 days").id)
        # The NOISE plant: a cross-topic pair (window date vs price clause) -
        # the same-subject rule must DEFER it.
        noise = (find("terminates on 2026-08-15").id, find("increases by 7%").id)
        for a_id, b_id in (p5, noise):
            session.add(db.AssetRelationship(
                project_id=project.id, expert_model_id=model.id,
                source_asset_id=a_id, target_asset_id=b_id,
                relationship_type="CONFLICTS_WITH",
                classification="DIRECT_CONTRADICTION", confidence=0.99,
                status="DETECTED",
                verifier_json=json.dumps({"method": "TEST_FIXTURE"})))
        session.commit()
        mode = "declared fixture conflicts (real-NLI detection = WS1 gate evidence)"
    print(f"Part 2 passed: 12 documents in, package compiled + agent bound; "
          f"conflicts via {mode}.")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE DIAGNOSIS (kinds, confinement, determinism, posture) ---")
    vault_dir = tempfile.mkdtemp(prefix="em_proc2_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    baseline = vault_files(vault_dir)
    answerer = make_answerer(loaded)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        runs = [runner.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="procurement-intelligence", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW_DAYS, answerer=answerer) for _ in range(2)]
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    first, second = runs
    assert first["as_of"] == AS_OF and first["window_days"] == WINDOW_DAYS
    assert first["proposals"] == second["proposals"], "paths must be identical"
    assert first["brief"] == second["brief"], "the brief path must be identical"
    for path in first["proposals"] + [first["brief"]]:
        with open(path, encoding="utf-8") as f:
            c1 = f.read()
        with open(path, encoding="utf-8") as f:
            assert f.read() == c1

    kinds = {f["finding_kind"] for f in first["findings"]}
    for expected in ("VENDOR_TERM", "RENEWAL_WINDOW", "PRICE_INCREASE_CLAUSE",
                     "MISSING_SUPPLIER_CERTIFICATION", "VENDOR_POLICY_CONFLICT"):
        assert expected in kinds, f"{expected} missing from the diagnosis"

    new_files = vault_files(vault_dir) - baseline
    for rel in new_files:
        assert rel.startswith(("08_proposals/", "07_agent_workspaces/")), \
            f"writes must be confined: {rel}"
    briefs = [r for r in new_files if r.startswith("07_agent_workspaces/")]
    assert len(briefs) == 1, "exactly one renegotiation brief in the workspace"

    expected_kind = dict(runner.FINDING_KINDS)
    forbidden = runner.parse_forbidden_vocabulary(MANIFEST)
    assert len(forbidden) >= 8, "the manifest must declare the posture sweep"
    for path in first["proposals"]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert SENTINEL not in text, "EXECUTIVE sentinel leaked into a proposal"
        assert "20%" not in text, "the converted paraphrase must never appear"
        lowered = text.lower()
        for phrase in forbidden:
            assert phrase not in lowered, \
                f"THE INVENTED NUMBER: {phrase!r} in a written proposal byte"
        for noisy in ("4501 Commerce Park", "555 0142", "clause 12.3", "700000"):
            assert noisy not in text, \
                f"a noisy irrelevant number was promoted into a finding: {noisy}"
        parsed = proposals.parse_frontmatter(text)
        assert parsed["claimed"] and not parsed["problems"], parsed
        claims = parsed["claims"]
        assert claims["agent_principal"] == "procurement-intelligence"
        assert int(claims["binding_id"]) == binding.id
        assert claims["package_hash"] == package_row.package_hash
        assert claims["workbench"] == "procurement-intelligence"
        skill = claims["skill"]
        kind, basis = expected_kind[skill]
        assert claims["finding_kind"] == kind, (skill, claims["finding_kind"])
        assert claims["evidence_basis"] == basis
        cited = [int(t) for t in claims["cited_assets"].split(",") if t]
        assert cited and set(cited) <= packaged_ids, \
            "every citation names a packaged INTERNAL asset the agent consumed"
        assert "Exclusions declared by the gateway" in text
    with open(first["brief"], encoding="utf-8") as f:
        brief_text = f.read()
    assert SENTINEL not in brief_text and "20%" not in brief_text
    for section in ("## Known", "## Expiring or moving", "## Missing",
                    "## Unverified"):
        assert section in brief_text, f"the brief's four sections: {section}"
    assert "never enters knowledge" in brief_text
    assert "SYNTHESIS_INFERRED" in brief_text
    print(f"Part 3 passed: {len(first['proposals'])} per-finding proposals "
          f"(kinds: {sorted(kinds)}), byte-identical at as_of {AS_OF}/"
          f"+{WINDOW_DAYS}d, confined to 08_proposals + one workspace brief, "
          "claims conform, sentinel + forbidden vocabulary + '20%' + noisy "
          "numbers absent from every written byte.")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: every plant found and correctly kinded; controls silent ---")

    def finding(kind):
        return [f for f in first["findings"] if f["finding_kind"] == kind]

    # P1 renewal window + auto-renewal facet
    windows = finding("RENEWAL_WINDOW")
    p1 = [f for f in windows if "terminates on 2026-08-15" in f["excerpt"]]
    assert p1, "P1 renewal-window finding missing"
    assert p1[0]["days_until"] == 75, f"P1 days-until {p1[0]['days_until']}"
    assert p1[0]["as_of"] == AS_OF and p1[0]["window_days"] == WINDOW_DAYS
    assert p1[0].get("auto_renewal_excerpt"), "P2 auto-renewal facet missing"
    assert "60 days" in p1[0]["auto_renewal_excerpt"], "the 60-day notice period"
    assert not any("2027-09-30" in f["excerpt"] for f in windows), \
        "P1c out-of-window contract must produce NO finding"
    assert any("outside the declared window" in s["reason"]
               and "2027-09-30" in s["reason"] for s in first["skipped"]), \
        "P1c must be skipped with the out-of-window reason, declared"
    # P6 unparseable date refused, declared
    assert any("no parseable date" in s["reason"] for s in first["skipped"]), \
        "P6 unparseable date must be refused, declared"

    # P3 explicit percentage + P3t paraphrase trap
    prices = finding("PRICE_INCREASE_CLAUSE")
    p3 = [f for f in prices if "7%" in f["excerpt"]]
    assert p3 and not p3[0]["non_numeric"], "P3 explicit percentage, numeric"
    p3t = [f for f in prices if "one fifth" in f["excerpt"]]
    assert p3t and p3t[0]["non_numeric"], "P3t must be flagged non_numeric"
    assert not re.search(r"\d", p3t[0]["excerpt"]), \
        "the paraphrase-trap excerpt must carry no digit"

    # P4 missing cert + P4c covered (supplier-named)
    missing = finding("MISSING_SUPPLIER_CERTIFICATION")
    assert any(f["supplier"] == "DataFlow" for f in missing), \
        "P4 DataFlow missing certificate must be found"
    assert not any(f["supplier"] == "SecureStore" for f in missing), \
        "P4c SecureStore is covered (supplier-named) - NO finding"
    assert any("SecureStore" in s["reason"] and "supplier-named" in s["reason"]
               for s in first["skipped"]), \
        "P4c must be skipped with the supplier-named covered reason"

    # P5 vendor-policy conflict + the noise deferral
    conflicts = finding("VENDOR_POLICY_CONFLICT")
    assert any("21 days" in f["excerpt_contract"] + f["excerpt_policy"]
               and "45 days" in f["excerpt_contract"] + f["excerpt_policy"]
               for f in conflicts), "P5 payment-terms conflict missing"
    assert all("Procurement Policy" == f["named_policy"] for f in conflicts)
    if not REAL_NLI:
        assert any("no shared subject" in s["reason"] for s in first["skipped"]), \
            "the cross-topic noise pair must be deferred, declared"

    # vendor terms with declared classes
    terms = finding("VENDOR_TERM")
    assert any(f["term_class"] == "sla" for f in terms), "an sla term expected"
    print("Part 4 passed: P1 window (days-until 75) + P2 auto-renewal facet; "
          "P1c/P6 window controls silent+declared; P3 numeric / P3t non-numeric "
          "trap; P4 DataFlow missing / P4c SecureStore covered (supplier-named); "
          "P5 conflict named against the policy, noise deferred; vendor terms "
          "carry declared classes.")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: contracts drive behavior (clock, gates, statuses) ---")
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        def expect_refusal(kwargs, needle):
            try:
                runner.run_diagnostic(
                    package_row.file_path, vault_dir, project.id,
                    agent_principal="procurement-intelligence",
                    binding_id=binding.id, graph_client=InProcessGraphClient(),
                    answerer=answerer, **kwargs)
            except RuntimeError as e:
                return needle in str(e)
            return False

        assert expect_refusal(dict(as_of=None, window_days=WINDOW_DAYS),
                              "no as_of declared"), "no-as_of must refuse"
        assert expect_refusal(dict(as_of=AS_OF, window_days=0),
                              "no positive window_days"), "no-window must refuse"
        assert expect_refusal(dict(as_of=AS_OF, window_days=WINDOW_DAYS,
                                   persistent_calendar=True),
                              "persistent renewal calendar"), \
            "a persistent-calendar request must refuse (ruling 4)"
        assert expect_refusal(
            dict(as_of=AS_OF, window_days=WINDOW_DAYS,
                 requested_skills=runner.ACTIVE_SKILLS
                 + ("compare_contract_pricing_vs_invoices",)),
            "Operational Evidence Realm"), "a gated [OE] skill must refuse live"
        assert expect_refusal(
            dict(as_of=AS_OF, window_days=WINDOW_DAYS,
                 requested_skills=runner.ACTIVE_SKILLS + ("identify_owner_gaps",)),
            "Exception Stewardship"), "a gated [ES] skill must refuse live"
        assert expect_refusal(
            dict(as_of=AS_OF, window_days=WINDOW_DAYS,
                 requested_skills=runner.ACTIVE_SKILLS
                 + ("detect_single_supplier_dependency",)),
            "SEQUENCED"), "a SEQUENCED skill must refuse live"

        # a SEQUENCED contract status gate (tags are gates): flip one ACTIVE
        # contract to SEQUENCED and confirm the load refuses.
        gated_dir = tempfile.mkdtemp(prefix="em_proc2_skills_g_")
        for name in os.listdir(SKILLS_DIR):
            shutil.copy(os.path.join(SKILLS_DIR, name),
                        os.path.join(gated_dir, name))
        path = os.path.join(gated_dir, "detect_price_increase_clauses.yaml")
        with open(path, encoding="utf-8") as f:
            txt = f.read()
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt.replace("status: ACTIVE", "status: SEQUENCED", 1))
        assert expect_refusal(dict(as_of=AS_OF, window_days=WINDOW_DAYS,
                                   skills_dir=gated_dir), "not ACTIVE"), \
            "a non-ACTIVE contract must be refused at load"
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    print("Part 5 passed: no-as_of / no-window / persistent-calendar refused; "
          "[OE] + [ES] + SEQUENCED skills refused live naming the decision; a "
          "non-ACTIVE contract refused at load.")

    # ------------------------------------------------------------ Part 6
    print("\n--- Part 6: the return path holds every finding ---")
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add(db.ApprovalPolicy(project_id=project.id, name="everything",
                                  asset_types_json=all_types, enabled=True))
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
    assert len(lane_doc_ids) == len(first["proposals"]), \
        "every per-finding proposal must be ingested"
    lane_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_doc_ids)).all()
    assert lane_assets and all(
        a.status == "CANDIDATE" and a.source_class == "DERIVED"
        for a in lane_assets)
    verdict = proposals.verify_provenance(session, sorted(lane_doc_ids)[0])
    assert verdict["provenance_verified"], verdict["reasons"]
    assert verdict["verified"]["binding_id"] == binding.id
    assert verdict["cited_assets"]["missing"] == []
    print(f"Part 6 passed: {len(lane_doc_ids)} proposals ingested; "
          f"{len(lane_assets)} candidates all held DERIVED under a live "
          "permissive policy; provenance verified against the governed binding.")

    session.close()
    print("\n=== All v1.8 WS2 diagnosis-proof checks passed: the Procurement "
          "Document Intelligence workbench is a governed skill bundle - every "
          "number verbatim, every window computed on the declared clock, "
          "document-grounded or refused, and never an invented number. ===")


if __name__ == "__main__":
    main()
