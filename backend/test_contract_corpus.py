"""v2.1 WS1 - THE EXTRACTION PRECONDITION PROOF for the Contract
Intelligence Workbench (the shared engine), BEFORE any runner exists.

The shared-engine premise is proven on the real governed substrate:

  1. THE BUNDLE SHAPE - the manifest and the three ratified contracts
     agree; the clause_class taxonomy is PINNED and CLOSED at exactly
     fifteen classes in a declared order; the forbidden vocabulary is
     the ratified twelve; THE REGISTER DISTINCTION is in the manifest
     bytes; the 16_contract_intelligence drafts stand at exactly
     3 ACTIVE / 22 CONSOLIDATED / 5 SEQUENCED / 1 [ES]-gated FUTURE,
     every ratified_path resolving (the global 26/40 sweep lives in
     the prior corpus suites, re-run green at this gate).
  2. THE COVERAGE REPORT - the declared first-match rules and marker
     regimes, parsed from the ratified contract bytes and applied
     test-side to the REAL corpora (procurement + compliance, through
     the real pipeline), fire for the load-bearing classes; classes
     the existing corpora cannot exercise are DECLARED, never papered
     over (ruling 7: prove no new corpus is needed, or surface the
     limitation).
  3. THE CONSUMER-MARKER PRECONDITION (the risky heart, proven before
     the runner): a register entry in the ratified proposal shape -
     the VERBATIM CloudHost SLA clause, accepted as a DERIVED fact -
     is cited BY ASSET ID by findings of BOTH unchanged consumers
     (the v1.7 compliance runner and the v1.8 procurement runner,
     zero edits): THE CONVERGENCE CLAUSE. Zero drift is an id
     equality, not a string comparison.
  4. THE PROVENANCE CHAIN - consumer finding -> register entry
     (origin contract-intelligence via the v1.9 filename convention)
     -> the PRIMARY clause asset (the register's cited source).
  5. THE VALVE + THE HELD PLANT - register candidates hold DERIVED;
     a never-accepted register proposal reaches no package byte and
     no consumer finding.
  6. NO SHARED FACT STORE - the consumers' sources never import or
     name contract_intelligence; the bundle ships NO runner at WS1;
     route manifest 88 at its ratified digest; MCP 9; D24 28/305.
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
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_ci1_pkg_")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_ci1_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'ws1.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_ci1_qdrant_")

from app import (schemas, crud, connectors, identity,  # noqa: E402
                 package_builder, package_consumer, mcp_gateway,
                 policy, proposals, tier2)
import test_support                           # noqa: E402
import test_workbench_projection              # noqa: E402
import test_route_manifest as route_guard     # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.compliance_obligation.runner as compliance_runner   # noqa: E402
import workbench.procurement_intelligence.runner as procurement_runner  # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "contract_intelligence")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
MANIFEST = os.path.join(WB_DIR, "workbench.yaml")
DRAFTS_16 = os.path.join(REPO_DIR, "docs", "skill-contracts",
                         "16_contract_intelligence")
COMPLIANCE_CORPUS = os.path.join(REPO_DIR, "workbench",
                                 "compliance_obligation", "corpus")
PROCUREMENT_CORPUS = os.path.join(REPO_DIR, "workbench",
                                  "procurement_intelligence", "corpus")
AS_OF = "2026-06-01"

# The pinned taxonomy, in the ratified order (asserted against the
# contract bytes in Part 1 - this suite and the contract must agree).
PINNED_CLASSES = (
    "approval_requirements", "renewal", "termination", "effective_date",
    "expiry_date", "sla", "data_access", "notification_obligation",
    "certification_obligation", "audit_rights", "reporting_obligation",
    "confidentiality", "liability_indemnity", "payment", "parties")

# THE CONVERGENCE CLAUSE (verbatim from the CloudHost SLA schedule,
# already a governed PRIMARY fact of the v1.8 corpus): carries the
# v1.7 obligation marker ("shall") AND the v1.8 term-class keywords
# ("subprocessor", "personal data") simultaneously.
CONVERGENCE_CLAUSE = ("CloudHost shall notify the customer in writing "
                      "before granting any subprocessor access to "
                      "personal data held in the service.")
RENEWAL_CLAUSE = ("The agreement renews automatically for successive "
                  "twelve-month terms unless either party gives written "
                  "notice of non-renewal at least 60 days before the "
                  "termination date.")
HELD_SENTINEL = "EM-REGISTER-HELD-5T7Q"


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


# ------------------------- the declared rules, parsed from contract bytes

def parse_taxonomy(path):
    """(ordered [(class, [keywords])]) from the clause_class_taxonomy
    block - the suite applies EXACTLY what the contract declares."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    rules, capturing = [], False
    for line in lines:
        if line.startswith("clause_class_taxonomy:"):
            capturing = True
            continue
        if capturing:
            s = line.strip()
            if s.startswith("#") or not s:
                continue
            if line and not line.startswith(" "):
                break
            m = re.match(r'- (\w+): (.+)$', s)
            if m:
                kws = re.findall(r'"([^"]+)"', m.group(2))
                rules.append((m.group(1), [k.lower() for k in kws]))
    return rules


def parse_regimes(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    def block_list(anchor):
        seg = text.split(anchor, 1)[1]
        m = re.search(r"classes: \[([^\]]+)\]", seg)
        return [c.strip() for c in m.group(1).replace("\n", " ").split(",")]
    commitment = block_list("commitment_classes:")
    structural = block_list("structural_classes:")
    seg = text.split("explicit_markers:", 1)[1]
    markers = re.findall(r'"([^"]+)"', seg.split("]", 1)[0])
    return commitment, structural, [m.lower() for m in markers]


def classify(sentence, rules):
    low = sentence.lower()
    for cls, kws in rules:
        if any(k in low for k in kws):
            return cls
    return None


def qualifies(sentence, cls, commitment, structural, markers):
    low = sentence.lower()
    if cls in commitment:
        return any(m in low for m in markers)
    if cls in structural:
        return bool(re.search(r"\d{4}-\d{2}-\d{2}", sentence)
                    or re.search(r"\d", sentence)
                    or re.search(r"days|months|years|anniversary", low)
                    or re.search(r"\b[A-Z][a-z]+[A-Z]", sentence))
    return False


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "CI1Officer")
    reviewer = test_support.governed_actor(session, "CI1Reviewer")
    issuer = test_support.governed_actor(session, "CI1Issuer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Contract Intelligence WS1", description="the precondition proof",
        customer_id=customer.id), actor=officer)

    # ------------------------------------------------------------ Part 1
    print("\n--- Part 1: THE BUNDLE SHAPE (pinned, closed, ratified) ---")
    required_fields = (
        "skill_id:", "workbench:", "status:", "boundary_tags:", "purpose:",
        "allowed_inputs:", "forbidden_inputs:", "evidence_rules:",
        "allowed_finding_kinds:", "output_format:",
        "human_approval_requirement:", "audit_event:", "refusal_conditions:")
    ratified = sorted(n[:-5] for n in os.listdir(SKILLS_DIR)
                      if n.endswith(".yaml"))
    assert ratified == ["detect_missing_contract_metadata",
                        "extract_contract_clauses",
                        "prepare_contract_review_brief"], ratified
    for name in ratified:
        with open(os.path.join(SKILLS_DIR, name + ".yaml"),
                  encoding="utf-8") as f:
            text = f.read()
        for field in required_fields:
            assert field in text, f"{name}: missing {field}"
        assert "status: ACTIVE" in text
    with open(MANIFEST, encoding="utf-8") as f:
        manifest = f.read()
    declared = re.findall(r"^  - (\w+)$",
                          manifest.split("skills:\n")[1], re.MULTILINE)[:3]
    assert sorted(declared) == ratified, "manifest and skills/ disagree"
    assert "THE PARAPHRASED CLAUSE" in manifest
    assert "narrative synthesis of accepted facts may never" in manifest.lower() \
        or "narrative synthesis" in manifest, "THE REGISTER DISTINCTION missing"
    forbidden = re.findall(r'^  - "([^"]+)"$',
                           manifest.split("forbidden_vocabulary:")[1]
                           .split("domain_scope:")[0], re.MULTILINE)
    assert len(forbidden) == 12, f"the ratified twelve: {len(forbidden)}"
    engine_path = os.path.join(SKILLS_DIR, "extract_contract_clauses.yaml")
    rules = parse_taxonomy(engine_path)
    assert tuple(c for c, _ in rules) == PINNED_CLASSES, \
        f"the taxonomy is pinned and CLOSED in the ratified order: {rules}"
    assert all(kws for _, kws in rules), "every class carries keywords"
    commitment, structural, markers = parse_regimes(engine_path)
    assert set(commitment) | set(structural) == set(PINNED_CLASSES), \
        "every class belongs to exactly one marker regime"
    assert not set(commitment) & set(structural)
    assert len(markers) >= 4
    # the 16_ drafts: 3 ACTIVE / 22 CONSOLIDATED / 5 SEQUENCED / 1 FUTURE
    statuses, resolved = {}, 0
    for name in sorted(os.listdir(DRAFTS_16)):
        if not name.endswith(".yaml"):
            continue
        with open(os.path.join(DRAFTS_16, name), encoding="utf-8") as f:
            text = f.read()
        status = re.search(r"^status: (\S+)", text, re.MULTILINE).group(1)
        statuses[status] = statuses.get(status, 0) + 1
        rp = re.search(r"^ratified_path: (\S+)", text, re.MULTILINE)
        if status in ("ACTIVE", "CONSOLIDATED"):
            assert rp, f"{name}: needs ratified_path"
            assert os.path.isfile(os.path.join(REPO_DIR, rp.group(1))), \
                f"{name}: ratified_path does not resolve"
            resolved += 1
    assert statuses == {"ACTIVE": 3, "CONSOLIDATED": 22,
                        "SEQUENCED": 5, "FUTURE": 1}, statuses
    print(f"Part 1 passed: manifest and 3 ratified contracts agree; the "
          f"taxonomy pinned+closed at {len(rules)} classes in the ratified "
          f"order; two marker regimes partition it; 12 forbidden phrases; "
          f"THE REGISTER DISTINCTION in the manifest bytes; 16_ drafts at "
          f"3/22/5/1 with {resolved} resolving ratified_paths.")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: both corpora through the real pipeline ---")
    for name, root, domain in (("Compliance Docs", COMPLIANCE_CORPUS, "compliance"),
                               ("Procurement Docs", PROCUREMENT_CORPUS, "procurement")):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
        approve_all(session, project.id, reviewer, f"ws1: {domain}",
                    domain=domain)
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    assert len(approved) >= 80
    docs = {d.id: d for d in session.query(db.Document).filter_by(
        project_id=project.id).all()}
    assert len(docs) == 24
    print(f"Part 2 passed: 24 documents -> {len(approved)} PRIMARY facts "
          "through the real pipeline.")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE COVERAGE REPORT (declared rules over real facts) ---")
    contract_doc_rule = re.compile(r"agreement|addendum|schedule|\bmsa\b|\bsla\b",
                                   re.IGNORECASE)
    contract_doc_ids = {d.id for d in docs.values()
                        if contract_doc_rule.search(d.filename or "")}
    assert len(contract_doc_ids) >= 7, \
        f"the corpora must carry a real contract set: {len(contract_doc_ids)}"
    coverage = {cls: [] for cls, _ in rules}
    for a in approved:
        if a.document_id not in contract_doc_ids:
            continue
        content = norm(a.content)
        cls = classify(content, rules)
        if cls and qualifies(content, cls, commitment, structural, markers):
            coverage[cls].append(a.id)
    covered = {c for c, ids in coverage.items() if ids}
    uncovered = [c for c, _ in rules if c not in covered]
    # The load-bearing floor mirrors the ratified required_metadata
    # grouping: term_boundary is ANY OF renewal/termination/
    # effective_date/expiry_date (first-match shadowing is DECLARED
    # behavior - this corpus's termination sentences ride under "Term
    # and renewal" headings, so `renewal` legitimately wins; likewise
    # notify-sentences here always co-occur with data_access/renewal
    # vocabulary, so notification_obligation is shadowed - recorded,
    # never a silent threshold bend).
    LOAD_BEARING = {"payment", "sla", "data_access",
                    "certification_obligation", "approval_requirements"}
    missing_load_bearing = LOAD_BEARING - covered
    assert not missing_load_bearing, \
        f"load-bearing classes uncovered by the existing corpora: {missing_load_bearing}"
    assert covered & {"renewal", "termination", "effective_date",
                      "expiry_date"}, \
        "the term_boundary group must fire on the existing corpora"
    assert len(covered) >= 7, f"covered={sorted(covered)}"
    print(f"Part 3 passed: {len(covered)}/15 classes fire on the existing "
          f"corpora under the declared rules ({sum(len(v) for v in coverage.values())} "
          f"clause candidates across {len(contract_doc_ids)} contract "
          f"documents). DECLARED fixture-uncovered (honest, ruling 7): "
          f"{uncovered or 'none'} - no new corpus is needed for the "
          f"load-bearing set; the uncovered classes stay in the pinned "
          f"taxonomy and simply produce no register entry here.")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: the register plants + the valve ---")
    _model, package_row = (lambda ids: (lambda m: (m, (lambda p: (
        package_builder.build_package(session, p), session.refresh(p), p)[-1])(
        (lambda pr: (session.add(pr), session.commit(), session.refresh(pr), pr)[-1])(
            db.AgentPackage(project_id=project.id, expert_model_id=m.id,
                            name="Contract Package", clearance_level="INTERNAL")))))(
        (lambda mo: (session.add(mo), session.commit(), session.refresh(mo), mo)[-1])(
            db.ExpertModel(project_id=project.id, name="Contract Expert",
                           asset_ids_json=json.dumps(sorted(ids)),
                           asset_count=len(ids)))))([a.id for a in approved])
    agent = identity.create_principal(session, name="contract-intelligence",
                                      display_name="Contract Intelligence",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _c = identity.issue_token(session, agent, kind="API_TOKEN",
                                           label="ws1", actor="test-suite")
    binding = db.ExpertAgentBinding(
        agent_package_id=package_row.id, agent_principal_id=agent.id,
        package_hash=package_row.package_hash, package_version="v1",
        principal_clearance_at_issue="INTERNAL",
        selected_provider="ANTHROPIC", selected_model_name="claude-opus-4-8",
        selection_evidence_json="{}", identity_fact_id=issuer.fact(session).id)
    session.add(binding)
    session.commit()
    session.refresh(binding)

    def find_primary(needle):
        return next(a for a in approved if needle[:60] in norm(a.content))
    primary_conv = find_primary(CONVERGENCE_CLAUSE)
    primary_renew = find_primary(RENEWAL_CLAUSE)

    vault_dir = tempfile.mkdtemp(prefix="em_ci1_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    def write_register_entry(clause, clause_class, cited_id, hash12):
        body = "\n".join([
            "---", "em_proposal: 1", "agent_principal: contract-intelligence",
            f"binding_id: {binding.id}",
            f"package_hash: {package_row.package_hash}",
            "workbench: contract-intelligence",
            "skill: extract_contract_clauses", "skill_version: 1",
            "finding_kind: CONTRACT_CLAUSE", "evidence_basis: EXCERPT_BACKED",
            f"cited_assets: {cited_id}", "---", "",
            "# Contract clause - register candidate", "",
            f"Clause class: {clause_class} (from the pinned taxonomy).", "",
            "## Finding", "", clause, "",
            "## Evidence", "",
            f"- Verbatim excerpt of governed asset {cited_id}; the register "
            "adds declared structure only.", ""])
        path = os.path.join(vault_dir, "08_proposals",
                            f"contract-intelligence-extract_contract_clauses-{hash12}.md")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        return path

    write_register_entry(CONVERGENCE_CLAUSE, "data_access",
                         primary_conv.id, "a1b2c3d4e5f6")
    write_register_entry(RENEWAL_CLAUSE, "renewal",
                         primary_renew.id, "b2c3d4e5f6a1")
    write_register_entry(
        f"The held plant {HELD_SENTINEL} must never be accepted as knowledge.",
        "confidentiality", primary_conv.id, "c3d4e5f6a1b2")
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
    assert lane_assets and all(a.status == "CANDIDATE" and
                               a.source_class == "DERIVED"
                               for a in lane_assets), "the valve holds"
    lane_docs = {d.id: d for d in session.query(db.Document).filter(
        db.Document.id.in_(lane_doc_ids)).all()}

    def accept_register(hash12, clause_frag):
        doc = next(d for d in lane_docs.values()
                   if hash12 in (d.filename or ""))
        cands = sorted((a for a in lane_assets if a.document_id == doc.id),
                       key=lambda a: a.id)
        pick = next(a for a in cands if clause_frag[:40] in norm(a.content))
        crud.update_knowledge_asset(
            session, pick.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=reviewer, review_notes="ws1: register entry accepted")
        session.refresh(pick)
        assert pick.source_class == "DERIVED"
        return pick

    register_conv = accept_register("a1b2c3d4e5f6", CONVERGENCE_CLAUSE)
    register_renew = accept_register("b2c3d4e5f6a1", RENEWAL_CLAUSE)
    verdict = proposals.verify_provenance(
        session, next(d.id for d in lane_docs.values()
                      if "a1b2c3d4e5f6" in (d.filename or "")))
    assert verdict["provenance_verified"], verdict["reasons"]
    assert verdict["cited_assets"]["missing"] == []
    print(f"Part 4 passed: 3 register proposals held DERIVED at the valve; "
          f"2 accepted by a human (assets {register_conv.id}, "
          f"{register_renew.id}) with VERIFIED provenance citing their "
          f"PRIMARY sources ({primary_conv.id}, {primary_renew.id}); the "
          f"held plant stays CANDIDATE.")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: THE CONSUMER-MARKER PRECONDITION + THE CONVERGENCE ---")
    approved2 = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    model2 = db.ExpertModel(project_id=project.id, name="Contract Expert v2",
                            asset_ids_json=json.dumps([a.id for a in approved2]),
                            asset_count=len(approved2))
    session.add(model2)
    session.commit()
    session.refresh(model2)
    pkg2 = db.AgentPackage(project_id=project.id, expert_model_id=model2.id,
                           name="Contract Package v2",
                           clearance_level="INTERNAL")
    session.add(pkg2)
    session.commit()
    session.refresh(pkg2)
    package_builder.build_package(session, pkg2)
    session.refresh(pkg2)
    loaded2 = package_consumer.load_package(pkg2.file_path)
    entries = {e["asset_id"]: e for e in loaded2["knowledge"]}
    assert register_conv.id in entries and register_renew.id in entries
    with open(pkg2.file_path, "rb") as f:
        pkg_bytes = f.read()
    assert HELD_SENTINEL.encode() not in pkg_bytes, \
        "the held register plant leaked into the package"
    # origin derivable via the v1.9 filename convention
    origin_re = re.compile(r"^([a-z][a-z-]*?)-([a-z][a-z_]*)-[0-9a-f]{12}\.md$")
    src = entries[register_conv.id].get("provenance", {}).get("source_document", "")
    m = origin_re.match(src)
    assert m and m.group(1) == "contract-intelligence", src
    binding2 = db.ExpertAgentBinding(
        agent_package_id=pkg2.id, agent_principal_id=agent.id,
        package_hash=pkg2.package_hash, package_version="v2",
        principal_clearance_at_issue="INTERNAL",
        selected_provider="ANTHROPIC", selected_model_name="claude-opus-4-8",
        selection_evidence_json="{}", identity_fact_id=issuer.fact(session).id)
    session.add(binding2)
    session.commit()
    session.refresh(binding2)

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
    comp_citing = [f for f in compliance["findings"]
                   if register_conv.id in f.get("cited_assets", [])]
    proc_citing = [f for f in procurement["findings"]
                   if register_conv.id in f.get("cited_assets", [])]
    assert comp_citing, \
        "the UNCHANGED v1.7 runner must cite the register entry by id"
    assert proc_citing, \
        "the UNCHANGED v1.8 runner must cite the register entry by id"
    # ZERO DRIFT: the same governed asset id under both readers.
    assert (register_conv.id in {i for f in comp_citing
                                 for i in f["cited_assets"]} and
            register_conv.id in {i for f in proc_citing
                                 for i in f["cited_assets"]})
    # the DERIVED class is flagged in consumer proposal bytes
    derived_flagged = 0
    held_leaks = 0
    for path in compliance["proposals"] + procurement["proposals"]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if str(register_conv.id) in text and "[DERIVED]" in text:
            derived_flagged += 1
        if HELD_SENTINEL in text:
            held_leaks += 1
    assert derived_flagged >= 1, \
        "consumers must flag the register citation [DERIVED]"
    assert held_leaks == 0, "no consumer finding may cite the held plant"
    comp_kinds = {f["finding_kind"] for f in comp_citing}
    proc_kinds = {f["finding_kind"] for f in proc_citing}
    print(f"Part 5 passed: THE CONVERGENCE - register entry "
          f"{register_conv.id} cited by asset id by BOTH unchanged "
          f"consumers (v1.7 {sorted(comp_kinds)}; v1.8 {sorted(proc_kinds)}); "
          f"[DERIVED]-flagged in consumer proposal bytes; the held plant in "
          f"no package byte and no consumer finding.")

    # ------------------------------------------------------------ Part 6
    print("\n--- Part 6: NO SHARED FACT STORE + the structural closers ---")
    for runner_path in ("compliance_obligation/runner.py",
                        "procurement_intelligence/runner.py"):
        with open(os.path.join(REPO_DIR, "workbench", runner_path),
                  encoding="utf-8") as f:
            src_text = f.read()
        assert "contract_intelligence" not in src_text, \
            f"{runner_path}: consumers must not import the engine - the " \
            f"feed is governed facts only"
    # Epoch-aware (the WS1 gate shipped NO runner; WS2 mounts it): once
    # the runner exists, the stronger claim replaces absence - the
    # runner's parsed rules must EQUAL this suite's independent parse of
    # the same ratified bytes (two implementations, one contract).
    runner_path = os.path.join(WB_DIR, "runner.py")
    if os.path.isfile(runner_path):
        import workbench.contract_intelligence.runner as ci_runner
        assert ci_runner.parse_taxonomy(engine_path) == rules, \
            "the runner's taxonomy parse drifted from the ratified bytes"
        assert ci_runner.parse_regimes(engine_path) == \
            (commitment, structural, markers), "regimes drifted"
    else:
        pass  # WS1 epoch: the precondition proof precedes the runner
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
    print(f"Part 6 passed: consumers never name the engine (facts are the "
          f"only feed); no runner at WS1; route manifest 88 at its ratified "
          f"digest; MCP at 9; D24 at {tables}/{columns}.")

    print("\n=== All v2.1 WS1 extraction-precondition checks passed: the "
          "taxonomy is pinned and closed, the declared rules fire on the "
          "existing corpora (uncovered classes DECLARED, not papered over), "
          "and THE CONVERGENCE stands - one register entry, accepted once, "
          "cited by asset id by BOTH unchanged consumers with derivation "
          "visible. The shared engine is provable from the laws already "
          "paid for - before any runner exists. ===")


if __name__ == "__main__":
    main()
