"""v1.6 WS1 (part 2) - THE CORPUS PROOF for the Customer Operations
Workbench.

Proves the WS1-required six, against the ratified corpus
(workbench/customer_operations/corpus/, plant map in CORPUS.md - the
non-runtime oracle), through EM's OWN machinery, before any workbench
runner code reads the corpus:

  1. The conflict scan detects the promise conflict (P1: 24h vs 48h).
  2. The scan detects the outdated FAQ condition (P3: 30 vs 14 days).
  3. The revision choreography produces the superseded chain
     (refund policy rev1 -> ARCHIVED, superseded by APPROVED rev2).
  4. consume() reproducibly refuses the playbook question (P2).
  5. consume() reproducibly refuses the reporting question (P4).
  6. No generated draft contract is treated as ratified without an
     explicit ratified_path (the draft != executable boundary).

Honesty notes:
  - The conflict scan runs the REAL NLI engine when available
    (nli_available); when the model is not loadable (bare CI), the
    NLI-detection assertion is SKIPPED loudly and declared fixture
    conflicts drive the gate flow - the real-NLI run is gate evidence,
    recorded in the build contract.
  - consume() refusal in CI runs through a DECLARED deterministic
    contract-follower injected at the D19 llm.generate seam: it
    answers only when a single governed evidence item shares >= 6
    retrieval tokens with the question, otherwise it returns the
    packaged refusal verbatim. The real-model refusal belongs to the
    open honest slot. The refusal PRECONDITION (no covering evidence
    exists in the package) is asserted deterministically either way.
"""
import json
import os
import re
import shutil
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Real-NLI mode (EM_CORPUS_PROOF_NLI=1) is the gate-evidence run: the
# conflict scan loads the real mDeBERTa pipeline and MUST detect the
# plants. Without the knob (bare CI), NLI is off and Part 3 skips
# honestly with declared fixture conflicts driving the gate flow.
REAL_NLI = os.environ.get("EM_CORPUS_PROOF_NLI", "").strip() == "1"
if not REAL_NLI:
    os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_cusops_pkg_")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_cusops_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'corpus.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_cusops_qdrant_")

from app import (schemas, crud, connectors, revisions, conflict_engine,  # noqa: E402
                 package_builder, package_consumer, tier2, llm)
import test_support                           # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WB_DIR = os.path.join(REPO_ROOT, "workbench", "customer_operations")
CORPUS_DIR = os.path.join(WB_DIR, "corpus")
SEED_DIR = os.path.join(WB_DIR, "corpus_seed")
DRAFTS_DIR = os.path.join(REPO_ROOT, "docs", "skill-contracts")

SENTINEL = "EM-EXEC-SENTINEL-9Q4Z"
PLAYBOOK_QUESTION = ("What is the approved escalation playbook for "
                     "enterprise refund exceptions?")
REPORTING_QUESTION = ("What is the approved procedure for producing the "
                      "monthly service performance report?")
CONTROL_QUESTION = ("May customers request a refund within days of delivery "
                    "under the refund policy?")
OVERLAP_THRESHOLD = 6
REFUSAL_TEXT = ("INSUFFICIENT EVIDENCE - the governed evidence offered does "
                "not contain the answer to this question.")


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
    return job


def approve_all_candidates(session, project_id, reviewer, note):
    candidates = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id,
        db.KnowledgeAsset.status == "CANDIDATE").all()
    for asset in candidates:
        crud.update_knowledge_asset(
            session, asset.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=reviewer, review_notes=note)
    return len(candidates)


def approved_assets(session, project_id):
    return session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id,
        db.KnowledgeAsset.status == "APPROVED").all()


def overlap(question, content):
    qt = package_consumer._tokens(question)
    return len(qt & package_consumer._tokens(content))


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "CorpusOfficer")
    reviewer = test_support.governed_actor(session, "CorpusReviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Customer Operations Corpus", description="v1.6 WS1 corpus proof",
        customer_id=customer.id), actor=officer)

    # The scan folder starts from the ratified corpus, with the refund
    # policy at its revision-1 content (the CORPUS.md choreography).
    scan_dir = tempfile.mkdtemp(prefix="em_cusops_scan_")
    for name in sorted(os.listdir(CORPUS_DIR)):
        shutil.copy(os.path.join(CORPUS_DIR, name), os.path.join(scan_dir, name))
    shutil.copy(os.path.join(SEED_DIR, "refund-policy.md"),
                os.path.join(scan_dir, "refund-policy.md"))

    connector = db.SourceConnector(project_id=project.id,
                                   name="Customer Ops Corpus",
                                   type="LOCAL_FOLDER", root_path=scan_dir,
                                   include_extensions=".md")
    session.add(connector)
    session.commit()
    session.refresh(connector)

    # --- Part 1: the corpus enters through the real pipeline -------------
    print("\n--- Part 1: the corpus through the real pipeline ---")
    run_scan(session, connector)
    doc_count = session.query(db.Document).filter(
        db.Document.project_id == project.id).count()
    assert doc_count >= 12, f"expected the 12 corpus documents, got {doc_count}"
    approved_count = approve_all_candidates(
        session, project.id, reviewer, "WS1 corpus approval (revision-1 state)")
    assert approved_count > 0, "no CANDIDATE assets extracted"
    contents = [a.content or "" for a in approved_assets(session, project.id)]
    assert any("24 hours" in c for c in contents), "P1 promise sentence not extracted"
    assert any("48 hours" in c for c in contents), "P1 SOP sentence not extracted"
    assert any("30 days" in c for c in contents), "30-day sentences not extracted"
    print(f"Part 1 passed: {doc_count} documents, {approved_count} assets "
          "approved by a human; plant sentences present in governed content.")

    # --- Part 2: the revision choreography (proof 3) ----------------------
    print("\n--- Part 2: the revision choreography -> the superseded chain ---")
    shutil.copy(os.path.join(CORPUS_DIR, "refund-policy.md"),
                os.path.join(scan_dir, "refund-policy.md"))
    run_scan(session, connector)
    pending = session.query(db.AssetRevision).filter(
        db.AssetRevision.status == "CANDIDATE").all()
    target = [r for r in pending if "within 14 days" in (r.content or "")]
    assert target, "the changed refund window produced no candidate revision"
    rev2 = target[0]
    revisions.review_revision(session, rev2.id, "APPROVE", actor=reviewer,
                              notes="WS1 choreography: 30 -> 14 days ratified")
    asset = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.id == rev2.asset_id).first()
    chain = sorted(asset.revisions, key=lambda r: r.revision_number)
    rev1 = chain[0]
    session.refresh(rev1)
    session.refresh(rev2)
    assert rev1.status == "ARCHIVED", f"rev1 is {rev1.status}, not ARCHIVED"
    assert rev1.superseded_by_revision_id == rev2.id, "superseded chain broken"
    assert rev2.status == "APPROVED"
    assert "within 14 days" in asset.content, "asset not serving revision 2"
    assert "30 days" in (rev1.content or ""), "rev1 lost its 30-day content"
    # v2's new sentences (the playbook reference) arrive as NEW candidates.
    new_approved = approve_all_candidates(
        session, project.id, reviewer, "WS1 corpus approval (revision-2 additions)")
    contents = [a.content or "" for a in approved_assets(session, project.id)]
    assert any("refund exception playbook" in c for c in contents), \
        "the P2 playbook reference did not become governed content"
    print(f"Part 2 passed: rev1 ARCHIVED -> superseded_by rev2 APPROVED; the "
          f"asset serves 14 days; {new_approved} revision-2 additions approved.")

    # --- Part 3: the conflict scan (proofs 1 + 2) -------------------------
    print("\n--- Part 3: the conflict scan on the governed corpus ---")
    assets = approved_assets(session, project.id)
    model = db.ExpertModel(project_id=project.id, name="Customer Operations Expert",
                           asset_ids_json=json.dumps([a.id for a in assets]),
                           asset_count=len(assets))
    session.add(model)
    session.commit()
    session.refresh(model)
    summary = conflict_engine.scan_expert_model_conflicts(session, model.id)
    by_id = {a.id: (a.content or "") for a in assets}
    conflicts = [r for r in summary["relationships"]
                 if r.relationship_type == "CONFLICTS_WITH"]
    nli_ran = bool(summary.get("nli_available"))
    if nli_ran:
        def pair_has(rel, needle_a, needle_b):
            a = by_id.get(rel.source_asset_id, "")
            b = by_id.get(rel.target_asset_id, "")
            return ((needle_a in a and needle_b in b)
                    or (needle_a in b and needle_b in a))
        p1 = [r for r in conflicts if pair_has(r, "24 hours", "48 hours")]
        p3 = [r for r in conflicts if pair_has(r, "14 days", "30 days")]
        assert p1, "P1 promise conflict (24h vs 48h) NOT detected by the scan"
        assert p3, "P3 outdated-FAQ conflict (30 vs 14 days) NOT detected"
        print(f"Part 3 passed: REAL NLI scan ({summary['compared_pairs']} pairs) "
              f"detected P1 ({p1[0].classification}, conf {p1[0].confidence:.3f}) "
              f"and P3 ({p3[0].classification}, conf {p3[0].confidence:.3f}); "
              f"{len(conflicts)} conflict(s) total.")
    else:
        # Honest skip: the detection proof requires the NLI model; the
        # gate flow below still runs on declared fixture conflicts.
        faq = next(a for a in assets if "30 days" in (a.content or "")
                   and "refund policy allows" in (a.content or ""))
        pol = next(a for a in assets if "within 14 days" in (a.content or ""))
        bro = next(a for a in assets if "24 hours" in (a.content or ""))
        sop = next(a for a in assets if "48 hours" in (a.content or ""))
        for a_id, b_id in ((bro.id, sop.id), (pol.id, faq.id)):
            session.add(db.AssetRelationship(
                project_id=project.id, expert_model_id=model.id,
                source_asset_id=a_id, target_asset_id=b_id,
                relationship_type="CONFLICTS_WITH",
                classification="DIRECT_CONTRADICTION", confidence=0.99,
                status="DETECTED",
                verifier_json=json.dumps({"method": "TEST_FIXTURE"})))
        session.commit()
        conflicts = session.query(db.AssetRelationship).filter(
            db.AssetRelationship.expert_model_id == model.id,
            db.AssetRelationship.relationship_type == "CONFLICTS_WITH").all()
        print("Part 3 SKIPPED (NLI model unavailable): detection assertion "
              "deferred to the recorded real-NLI gate run; declared fixture "
              "conflicts drive the gate flow.")

    # --- Part 4: the compile gate blocks, a human rules, the package ----
    print("\n--- Part 4: gate blocked -> human dismissal -> INTERNAL package ---")
    gate = conflict_engine.evaluate_compile_gate(session, model.id)
    assert not gate["allowed"], "unreviewed contradictions should block compile"
    for rel in conflicts:
        conflict_engine.review_relationship(
            session, rel.id, "DISMISSED", reviewer=reviewer,
            notes="WS1 corpus proof: plant contextualized by the human reviewer")
    gate = conflict_engine.evaluate_compile_gate(session, model.id)
    assert gate["allowed"], "gate should open after human review"
    matrix_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename.like("%refund-authority-matrix%")).first()
    assert matrix_doc is not None, "the EXECUTIVE matrix document is missing"
    exec_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id == matrix_doc.id).all()
    assert exec_assets, "no assets extracted from the EXECUTIVE matrix"
    for a in exec_assets:
        a.access_level = "EXECUTIVE"
    session.commit()
    package_row = db.AgentPackage(project_id=project.id,
                                  expert_model_id=model.id,
                                  name="Customer Operations Package",
                                  clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    package_builder.build_package(session, package_row)
    session.refresh(package_row)
    with open(package_row.file_path, "rb") as f:
        raw = f.read()
    assert SENTINEL.encode() not in raw, \
        "the EXECUTIVE sentinel leaked into the INTERNAL package bytes"
    loaded = package_consumer.load_package(package_row.file_path)
    print(f"Part 4 passed: gate blocked on {len(conflicts)} unreviewed "
          "contradiction(s), opened only by governed human dismissal; INTERNAL "
          "package compiled with the EXECUTIVE sentinel absent from every byte.")

    # --- Part 5: the refusal preconditions, deterministically ------------
    print("\n--- Part 5: refusal preconditions (no covering evidence exists) ---")
    r_play = package_consumer.retrieve(loaded, PLAYBOOK_QUESTION, top_k=8)
    assert any("refund exception playbook" in (e.get("content") or "")
               for e in r_play["selected"]), \
        "the P2 trigger (the playbook reference) is not retrievable"
    best_play = max(overlap(PLAYBOOK_QUESTION, e.get("content") or "")
                    for e in r_play["selected"])
    assert best_play < OVERLAP_THRESHOLD, \
        f"playbook question unexpectedly covered (overlap {best_play})"
    r_rep = package_consumer.retrieve(loaded, REPORTING_QUESTION, top_k=8)
    assert any("monthly service performance report" in (e.get("content") or "")
               for e in r_rep["selected"]), \
        "the P4 obligation excerpt is not retrievable"
    best_rep = max(overlap(REPORTING_QUESTION, e.get("content") or "")
                   for e in r_rep["selected"])
    assert best_rep < OVERLAP_THRESHOLD, \
        f"reporting question unexpectedly covered (overlap {best_rep})"
    r_ctl = package_consumer.retrieve(loaded, CONTROL_QUESTION, top_k=8)
    best_ctl = max(overlap(CONTROL_QUESTION, e.get("content") or "")
                   for e in r_ctl["selected"])
    assert best_ctl >= OVERLAP_THRESHOLD, \
        f"control question should be covered (overlap {best_ctl})"
    print(f"Part 5 passed: obligations retrievable (the gap is real), no "
          f"covering evidence for either gap question (max overlaps "
          f"{best_play}/{best_rep} < {OVERLAP_THRESHOLD}); the control "
          f"question is covered ({best_ctl}).")

    # --- Part 6: consume() refuses, reproducibly (proofs 4 + 5) ----------
    print("\n--- Part 6: consume() refuses correctly before answering correctly ---")

    def contract_follower(function, system, user, session=None, max_tokens=4096):
        """The DECLARED deterministic CI contract-follower at the D19 seam:
        answers only when one governed evidence item shares >=
        OVERLAP_THRESHOLD retrieval tokens with the question; otherwise
        returns the packaged refusal verbatim. The real-model refusal is
        the open honest slot."""
        sel = package_consumer.retrieve(loaded, user, top_k=8)["selected"]
        scored = sorted(((overlap(user, e.get("content") or ""), e) for e in sel),
                        key=lambda t: (-t[0], t[1]["asset_id"]))
        if scored and scored[0][0] >= OVERLAP_THRESHOLD:
            score, e = scored[0]
            text = (f"Per the governed evidence (asset_id {e['asset_id']}): "
                    f"{e.get('content')}")
        else:
            text = REFUSAL_TEXT
        return {"function": function, "provider": "TEST",
                "model": "contract-follower-v1", "source": "deterministic-ci",
                "text": text}

    original_generate = llm.generate
    llm.generate = contract_follower
    try:
        for question, label in ((PLAYBOOK_QUESTION, "playbook"),
                                (REPORTING_QUESTION, "reporting")):
            first = package_consumer.consume(package_row.file_path, question)
            second = package_consumer.consume(package_row.file_path, question)
            assert first["answer"] == second["answer"], f"{label}: not reproducible"
            assert "INSUFFICIENT EVIDENCE" in first["answer"], \
                f"{label}: expected a refusal, got: {first['answer'][:80]}"
            assert first["cited_asset_ids"] == [], \
                f"{label}: a refusal must cite nothing"
        control = package_consumer.consume(package_row.file_path, CONTROL_QUESTION)
        assert "INSUFFICIENT EVIDENCE" not in control["answer"], \
            "the control question should be answerable"
        assert control["cited_asset_ids"], "the control answer must cite evidence"
    finally:
        llm.generate = original_generate
    print("Part 6 passed: both gap questions refused reproducibly with zero "
          "citations; the covered control question answered with citations - "
          "refusing correctly before answering correctly.")

    # --- Part 7: draft != ratified (proof 6) ------------------------------
    print("\n--- Part 7: no draft contract passes as ratified ---")
    active, total = [], 0
    for folder, _dirs, files in os.walk(DRAFTS_DIR):
        for name in files:
            if not name.endswith(".yaml"):
                continue
            total += 1
            path = os.path.join(folder, name)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            match = re.search(r"^status: (\S+)", text, re.MULTILINE)
            assert match, f"{name}: draft contract missing a status field"
            assert "boundary_tags:" in text, f"{name}: missing boundary_tags"
            if match.group(1) == "ACTIVE":
                active.append(name)
                rp = re.search(r"^ratified_path: (\S+)", text, re.MULTILINE)
                assert rp, f"{name}: ACTIVE draft without ratified_path"
                assert os.path.isfile(os.path.join(REPO_ROOT, rp.group(1))), \
                    f"{name}: ratified_path does not resolve"
    # v1.7 WS1 (recorded edit, ratified consolidation ruling): later
    # workbench promotions add their own ACTIVE drafts; THIS suite
    # asserts the customer-ops set stays exactly five.
    cusops_active = [n for n in active if os.path.isfile(
        os.path.join(DRAFTS_DIR, "05_customer_operations", n))]
    assert len(cusops_active) == 5, \
        f"expected exactly 5 customer-ops ACTIVE drafts, got {cusops_active}"
    skills_dir = os.path.join(WB_DIR, "skills")
    ratified = sorted(n[:-5] for n in os.listdir(skills_dir) if n.endswith(".yaml"))
    with open(os.path.join(WB_DIR, "workbench.yaml"), "r", encoding="utf-8") as f:
        manifest = f.read()
    declared = re.findall(r"^  - (\w+)$", manifest.split("skills:")[1]
                          .split("refused_until_minted:")[0], re.MULTILINE)
    assert sorted(declared) == ratified, \
        f"manifest skills {sorted(declared)} != ratified files {ratified}"
    print(f"Part 7 passed: {total} draft contracts swept; exactly 5 "
          "customer-ops ACTIVE (later promotions carry their own suites), "
          "each with a resolving ratified_path; the manifest and the "
          "ratified skill files agree.")

    session.close()
    print("\n=== All customer-ops corpus-proof checks passed: the corpus "
          "refuses correctly before it answers correctly. ===")


if __name__ == "__main__":
    main()
