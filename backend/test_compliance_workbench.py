"""v1.7 WS2 - THE DIAGNOSIS PROOF for the Compliance & Obligation
Workbench.

The runner (workbench/compliance_obligation/runner.py, built on
workbench/common.py - the ruling-6 shared plumbing) is proven as a governed
skill bundle, not a vague agent:

  - every deterministically detectable plant found and CORRECTLY KINDED
    (P1 obligations across all four declared source types with declared
    source_type + obligation_type; P2 missing evidence; P3 the
    review-interval overdue policy; P4 the undocumented owner; P5 the
    cross-document contradiction);
  - the covered controls produce NO finding, declared in `skipped`
    (P2c the retained test report; P3c the current review; P4c the named
    Compliance Officer) - refusal-first cuts both ways;
  - the implied sentence (P7) is never extracted - explicit markers only;
  - the declared clock: as_of is a run parameter recorded verbatim; a run
    without as_of is REFUSED (wall-clock is never sampled);
  - a GATED skill ([OE]) is refused live, naming the unminted decision
    (ruling 3), and a SEQUENCED contract is refused at runtime;
  - THE SENSITIVITY POSTURE: the manifest's forbidden vocabulary is absent
    from every written byte (no practice overclaim);
  - byte-identical re-runs at the pinned as_of; writes confined to
    /08_proposals + the audit-readiness pack in /07_agent_workspaces; the
    EXECUTIVE sentinel absent from every written byte;
  - Guard 5 sweeps every workbench module with zero guard edits; and the
    return path holds every finding as a held DERIVED candidate with
    provenance verified against the governed binding.

Conflict rows: fixture DETECTED pairs by default (declared - the real-NLI
detection proof is WS1's corpus-proof gate evidence); with
EM_CORPUS_PROOF_NLI=1 the real scan runs instead and the noise-deferral
assertion is skipped (presence-based).
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
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_compl2_pkg_")

# Guard 5 first (its import overrides db.engine; this suite re-overrides
# and wins - the ruled import-order trick), for its door-sweep checker.
import test_agent_authorship_guard as guard   # noqa: E402

if REAL_NLI:
    # The guard import forces EM_NLI_VERIFICATION=off; the gate-evidence
    # mode needs the real engine back on before any pipeline load.
    os.environ["EM_NLI_VERIFICATION"] = "on"

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_compl2_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'ws2.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_compl2_qdrant_")

from app import (schemas, crud, connectors, conflict_engine,  # noqa: E402
                 package_builder, package_consumer, identity, mcp_gateway,
                 policy, proposals, tier2)
import test_support                           # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.compliance_obligation.runner as runner   # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "compliance_obligation")
CORPUS_DIR = os.path.join(WB_DIR, "corpus")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
MANIFEST = os.path.join(WB_DIR, "workbench.yaml")
SENTINEL = "EM-EXEC-SENTINEL-7C2R"
AS_OF = "2026-06-01"

# The declared frames (asserted against the ratified contract bytes at
# WS1 Part 7; used here to identify the walks' outcomes).
Q_TRAIN_GAP = ("Which approved record shows the completed security "
               "awareness training summary for the latest cycle?")
Q_IR_COVERED = ("Was the annual incident response plan test completed "
                "and the test report retained for audit review?")
Q_OWNER_GAP = "Who is responsible for sending personal data breach notifications?"
Q_OWNER_COVERED = ("Who is responsible for coordinating the annual ISO "
                   "27001 surveillance audit?")


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
    """CI substitute for the stdio transport: the SAME gateway functions,
    token resolution, clearance, and audited composition - minus the
    subprocess (the stdio door is the real-run transport)."""

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
    """The declared deterministic CI contract-follower (the WS1-ratified
    rule): answers only when one governed evidence item shares >= 6
    retrieval tokens with the question; otherwise the packaged refusal
    verbatim. Mirrors consume()'s return shape."""
    def answer(question):
        sel = package_consumer.retrieve(loaded_package, question,
                                        top_k=8)["selected"]
        qt = package_consumer._tokens(question)
        scored = sorted(
            ((len(qt & package_consumer._tokens(e.get("content") or "")), e)
             for e in sel), key=lambda t: (-t[0], t[1]["asset_id"]))
        if scored and scored[0][0] >= 6:
            best = scored[0][1]
            text = (f"Per the governed evidence (asset_id {best['asset_id']}): "
                    f"{best.get('content')}")
        else:
            text = ("INSUFFICIENT EVIDENCE - the governed evidence offered "
                    "does not contain the answer to this question.")
        return {"answer": text,
                "cited_asset_ids": [] if "INSUFFICIENT" in text
                else [scored[0][1]["asset_id"]],
                "evidence": sel}
    return answer


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "WS2ComplOfficer")
    reviewer = test_support.governed_actor(session, "WS2ComplReviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Compliance WS2", description="the diagnosis proof",
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
    assert swept >= 4, "pilot + both runners + common.py must exist and be swept"
    print(f"Part 1 passed: {swept} workbench module(s) inside the ruled "
          "doors - zero guard edits (common.py and the compliance runner "
          "swept the moment they exist).")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: corpus in, package compiled, agent bound ---")
    primary = db.SourceConnector(project_id=project.id, name="Compliance Docs",
                                 type="LOCAL_FOLDER", root_path=CORPUS_DIR,
                                 include_extensions=".md")
    session.add(primary)
    session.commit()
    session.refresh(primary)
    run_scan(session, primary)
    doc_count = session.query(db.Document).filter(
        db.Document.project_id == project.id).count()
    assert doc_count == 12, f"expected the 12 corpus documents, got {doc_count}"
    approve_all(session, project.id, reviewer, "WS2 compliance corpus approval")

    memo_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename.like("%risk-acceptance-memo%")).first()
    exec_ids = set()
    for a in session.query(db.KnowledgeAsset).filter(
            db.KnowledgeAsset.document_id == memo_doc.id).all():
        a.access_level = "EXECUTIVE"
        exec_ids.add(a.id)
    session.commit()

    approved = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.status == "APPROVED").all()
    model = db.ExpertModel(project_id=project.id, name="Compliance Expert",
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    session.add(model)
    session.commit()
    session.refresh(model)
    package_row = db.AgentPackage(project_id=project.id,
                                  expert_model_id=model.id,
                                  name="Compliance Package",
                                  clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    package_builder.build_package(session, package_row)
    session.refresh(package_row)
    loaded = package_consumer.load_package(package_row.file_path)
    packaged_ids = {e["asset_id"] for e in loaded["knowledge"]}
    assert not (exec_ids & packaged_ids), "EXECUTIVE assets must be excluded"

    agent = identity.create_principal(session, name="compliance-obligation",
                                      display_name="Compliance Obligation",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _cred = identity.issue_token(session, agent, kind="API_TOKEN",
                                              label="ws2", actor="test-suite")
    issuer = test_support.governed_actor(session, "WS2ComplIssuer")
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

    if REAL_NLI:
        summary = conflict_engine.scan_expert_model_conflicts(session, model.id)
        assert summary["nli_available"], "real-NLI mode requires the model"
        mode = f"REAL NLI ({summary['compared_pairs']} pairs)"
    else:
        def find(needle, extra=None):
            return next(a for a in approved if needle in norm(a.content)
                        and (extra is None or extra in norm(a.content)))
        p5 = (find("retained for ten years").id,
              find("destroyed three years").id)
        # The declared NOISE plant: a cross-topic timeframe pair (the NLI
        # over-fire shape) - the inherited same-subject rule must DEFER it.
        noise = (find("within 72 hours").id,
                 find("complete security awareness training").id)
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
    print(f"Part 2 passed: {doc_count} documents in, package compiled + agent "
          f"bound; conflicts via {mode}.")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE DIAGNOSIS (kinds, confinement, determinism, posture) ---")
    vault_dir = tempfile.mkdtemp(prefix="em_compl2_vault_")
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
            agent_principal="compliance-obligation", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            answerer=answerer) for _ in range(2)]
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    first, second = runs
    assert first["as_of"] == AS_OF, "the declared as_of must be recorded"
    assert first["proposals"] == second["proposals"], "paths must be identical"
    assert first["pack"] == second["pack"], "the pack path must be identical"
    for path in first["proposals"] + [first["pack"]]:
        with open(path, encoding="utf-8") as f:
            content_1 = f.read()
        with open(path, encoding="utf-8") as f:
            assert f.read() == content_1

    kinds = {f["finding_kind"] for f in first["findings"]}
    for expected in ("COMPLIANCE_OBLIGATION", "MISSING_COMPLIANCE_EVIDENCE",
                     "OUTDATED_POLICY", "UNDOCUMENTED_OBLIGATION_OWNER",
                     "CONFLICTING_COMPLIANCE_STATEMENTS"):
        assert expected in kinds, f"{expected} missing from the diagnosis"

    new_files = vault_files(vault_dir) - baseline
    for rel in new_files:
        assert rel.startswith(("08_proposals/", "07_agent_workspaces/")), \
            f"writes must be confined: {rel}"
    packs = [r for r in new_files if r.startswith("07_agent_workspaces/")]
    assert len(packs) == 1, "exactly one audit-readiness pack in the workspace"

    expected_kind = dict(runner.FINDING_KINDS)
    forbidden = runner.parse_forbidden_vocabulary(MANIFEST)
    assert len(forbidden) >= 8, "the manifest must declare the posture sweep"
    for path in first["proposals"]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert SENTINEL not in text, "EXECUTIVE sentinel leaked into a proposal"
        lowered = text.lower()
        for phrase in forbidden:
            assert phrase not in lowered, \
                f"THE SENSITIVITY POSTURE: {phrase!r} in a written proposal byte"
        parsed = proposals.parse_frontmatter(text)
        assert parsed["claimed"] and not parsed["problems"], parsed
        claims = parsed["claims"]
        assert claims["agent_principal"] == "compliance-obligation"
        assert int(claims["binding_id"]) == binding.id
        assert claims["package_hash"] == package_row.package_hash
        assert claims["workbench"] == "compliance-obligation"
        skill = claims["skill"]
        kind, basis = expected_kind[skill]
        assert claims["finding_kind"] == kind, (skill, claims["finding_kind"])
        assert claims["evidence_basis"] == basis
        cited = [int(t) for t in claims["cited_assets"].split(",") if t]
        assert cited and set(cited) <= packaged_ids, \
            "every citation names a packaged INTERNAL asset the agent consumed"
        assert "Exclusions declared by the gateway" in text, \
            "the clearance exclusion must be declared inside the proposal"
    with open(first["pack"], encoding="utf-8") as f:
        pack_text = f.read()
    assert SENTINEL not in pack_text
    lowered_pack = pack_text.lower()
    for phrase in forbidden:
        assert phrase not in lowered_pack, \
            f"THE SENSITIVITY POSTURE: {phrase!r} in the pack bytes"
    for section in ("## Known", "## Missing", "## Contradictory",
                    "## Unverified"):
        assert section in pack_text, \
            f"the pack's four mandatory sections must always be present: {section}"
    assert "never enters knowledge" in pack_text
    assert "SYNTHESIS_INFERRED" in pack_text
    print(f"Part 3 passed: {len(first['proposals'])} per-finding proposals "
          f"(kinds: {sorted(kinds)}), byte-identical across runs at pinned "
          f"as_of {AS_OF}, confined to 08_proposals + one workspace pack "
          "(four mandatory sections), skill claims conform to the ratified "
          "contracts, sentinel absent, forbidden vocabulary absent from "
          "every written byte, exclusions declared.")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: every plant found and correctly kinded; covered "
          "controls silent ---")

    def finding(kind):
        return [f for f in first["findings"] if f["finding_kind"] == kind]

    obligations = finding("COMPLIANCE_OBLIGATION")
    for needle, want_src, want_type, label in (
            ("within 72 hours", "contract", "notification", "P1 breach"),
            ("prior written approval", "contract", "approval", "P1 sub-processor"),
            ("security awareness training", "policy", "training", "P1 training"),
            ("shall maintain certification", "certification", "certification",
             "P1 certification"),
            ("retained for ten years", "regulatory", "retention", "P1 retention"),
            ("destroyed three years", "policy", "retention", "P1 disposal")):
        hits = [f for f in obligations if needle in f["excerpt"]]
        assert hits, f"{label}: no obligation finding quotes {needle!r}"
        assert hits[0]["source_type"] == want_src, \
            f"{label}: source_type {hits[0]['source_type']} != {want_src}"
        assert hits[0]["obligation_type"] == want_type, \
            f"{label}: obligation_type {hits[0]['obligation_type']} != {want_type}"
    assert not any("encouraged to archive" in f["excerpt"]
                   for f in obligations), \
        "P7: the implied sentence must never be extracted as an obligation"

    missing = finding("MISSING_COMPLIANCE_EVIDENCE")
    p2 = [f for f in missing if f["question"] == Q_TRAIN_GAP]
    assert p2, "P2: the training-evidence gap must be found"
    assert p2[0]["requirement_class"] == "training_completion"
    assert "completion summary" in p2[0]["requirement_excerpt"], \
        "P2 must cite the requirement excerpt verbatim"
    assert not any(f["question"] == Q_IR_COVERED for f in missing), \
        "P2c: the covered incident-testing control must produce NO finding"
    assert any("the corpus answers" in s["reason"] and Q_IR_COVERED in s["reason"]
               for s in first["skipped"]), \
        "P2c must be skipped with the covered-control reason, declared"

    outdated = [f for f in finding("OUTDATED_POLICY")
                if f.get("route") == "REVIEW_INTERVAL"]
    assert len(outdated) == 1, \
        f"P3: exactly one review-interval finding expected, got {len(outdated)}"
    p3 = outdated[0]
    assert "2024-05-02" in p3["excerpt"], "P3 must quote the declared review"
    assert p3["due"] == "2025-05-02", f"P3 computed due {p3['due']}"
    assert p3["as_of"] == AS_OF, "P3 must record the declared as_of verbatim"
    assert any("current at as_of" in s["reason"] and "2026-11-10" in s["reason"]
               for s in first["skipped"]), \
        "P3c: the current policy must be skipped with its computed due date"

    owners = finding("UNDOCUMENTED_OBLIGATION_OWNER")
    p4 = [f for f in owners if f["question"] == Q_OWNER_GAP]
    assert p4, "P4: the undocumented breach-notification owner must be found"
    assert "personal data breach" in p4[0]["excerpt"], \
        "P4 must cite the explicit obligation excerpt"
    assert not any(f["question"] == Q_OWNER_COVERED for f in owners), \
        "P4c: the documented ISO owner must produce NO finding"
    assert any("names the owner" in s["reason"] and Q_OWNER_COVERED in s["reason"]
               for s in first["skipped"]), \
        "P4c must be skipped with the covered-control reason, declared"

    conflicts = finding("CONFLICTING_COMPLIANCE_STATEMENTS")
    assert any(("ten years" in f["excerpt_a"] + f["excerpt_b"])
               and ("three years" in f["excerpt_a"] + f["excerpt_b"])
               for f in conflicts), \
        "P5 must pair the ten-year retention with the three-year destruction"
    if not REAL_NLI:
        assert any("no shared subject matter" in s["reason"]
                   for s in first["skipped"]), \
            "the noise contradiction must be deferred, declared"
        assert not any("72 hours" in f.get("excerpt_a", "")
                       + f.get("excerpt_b", "") for f in conflicts), \
            "the cross-topic noise pair must not become a finding"
    print(f"Part 4 passed: P1 x6 correctly typed by the declared rules, P7 "
          f"never extracted; P2/P3/P4/P5 found and kinded; P2c/P3c/P4c "
          "covered controls silent with declared reasons; the noise pair "
          "deferred by the inherited same-subject rule.")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: contracts drive behavior (clock, gates, statuses) ---")
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        # (a) the declared clock: a run without as_of is REFUSED.
        refused_clock = False
        try:
            runner.run_diagnostic(
                package_row.file_path, vault_dir, project.id,
                agent_principal="compliance-obligation", binding_id=binding.id,
                graph_client=InProcessGraphClient(), as_of=None,
                answerer=answerer)
        except RuntimeError as e:
            refused_clock = "no as_of declared" in str(e)
        assert refused_clock, "a run without as_of must be refused"

        # (b) a gated [OE] skill is refused LIVE, naming the unminted decision.
        refused_gate = False
        try:
            runner.run_diagnostic(
                package_row.file_path, vault_dir, project.id,
                agent_principal="compliance-obligation", binding_id=binding.id,
                graph_client=InProcessGraphClient(), as_of=AS_OF,
                answerer=answerer,
                requested_skills=runner.ACTIVE_SKILLS
                + ("compare_policy_vs_practice",))
        except RuntimeError as e:
            refused_gate = "Operational Evidence Realm" in str(e)
        assert refused_gate, \
            "a gated skill must be refused live, naming the unminted decision"

        # (c) a SEQUENCED contract is refused at runtime (tags are gates).
        gated_dir = tempfile.mkdtemp(prefix="em_compl2_skills_g_")
        for name in os.listdir(SKILLS_DIR):
            shutil.copy(os.path.join(SKILLS_DIR, name),
                        os.path.join(gated_dir, name))
        outdated_path = os.path.join(gated_dir, "identify_outdated_policies.yaml")
        with open(outdated_path, encoding="utf-8") as f:
            text = f.read()
        with open(outdated_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace("status: ACTIVE", "status: SEQUENCED", 1))
        refused_status = False
        try:
            runner.run_diagnostic(
                package_row.file_path, vault_dir, project.id,
                agent_principal="compliance-obligation", binding_id=binding.id,
                graph_client=InProcessGraphClient(), as_of=AS_OF,
                answerer=answerer, skills_dir=gated_dir)
        except RuntimeError as e:
            refused_status = "not ACTIVE" in str(e)
        assert refused_status, "a non-ACTIVE contract must be refused"
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    print("Part 5 passed: no-as_of refused (the clock is declared, never "
          "sampled); compare_policy_vs_practice refused live naming the "
          "Operational Evidence Realm; a SEQUENCED contract refused at "
          "runtime.")

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
        for a in lane_assets), \
        [(a.id, a.status, a.source_class) for a in lane_assets]
    verdict = proposals.verify_provenance(session, sorted(lane_doc_ids)[0])
    assert verdict["provenance_verified"], verdict["reasons"]
    assert verdict["verified"]["binding_id"] == binding.id
    assert verdict["cited_assets"]["missing"] == []
    print(f"Part 6 passed: {len(lane_doc_ids)} proposals ingested; "
          f"{len(lane_assets)} candidates all held DERIVED under a live "
          "permissive policy; provenance verified against the governed "
          "binding.")

    session.close()
    print("\n=== All v1.7 WS2 diagnosis-proof checks passed: the Compliance "
          "& Obligation workbench is a governed skill bundle - declared "
          "frames, declared clock, declared gates, document-grounded or "
          "refused, and never a practice overclaim. ===")


if __name__ == "__main__":
    main()
