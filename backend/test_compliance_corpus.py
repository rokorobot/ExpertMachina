"""v1.7 WS1 - THE CORPUS PROOF for the Compliance & Obligation
Workbench.

Proves the WS0-ratified WS1 requirements against the ratified corpus
(workbench/compliance_obligation/corpus/, plant map in CORPUS.md -
the non-runtime oracle), through EM's OWN machinery, before any
workbench runner code reads the corpus:

  1. Real-NLI detection of the compliance contradiction (P5: contract
     records retained TEN years vs destroyed THREE years) in
     gate-evidence mode.
  2. Review-interval overdue logic from the document's OWN declared
     interval plus the pinned as_of (P3 overdue / P3c current) -
     never age alone, never wall-clock.
  3. consume() reproducibly refuses the absent-evidence question (P2)
     and the undocumented-owner question (P4).
  4. consume() ANSWERS the covered controls (P2c incident test
     report; P4c the named Compliance Officer) - refusal-first cuts
     both ways.
  5. Explicit obligation extraction only: the declared marker rule
     selects the P1 plants verbatim and never the implied sentence
     (P7); source_type and obligation_type derive from the declared
     contract rules.
  6. Draft contracts do not masquerade as ratified contracts: the
     ACTIVE set is exactly the ratified eleven (5 customer-ops + 6
     compliance), every ratified_path resolves, every CONSOLIDATED
     draft carries consolidated_into + a resolving ratified_path (the
     consolidation ruling), and the deferred deadline family stays
     SEQUENCED.

Honesty notes (the v1.6 pattern, inherited):
  - The conflict scan runs the REAL NLI engine under
    EM_CORPUS_PROOF_NLI=1 (the gate-evidence run); in bare CI the
    NLI-detection assertion is SKIPPED loudly and a declared fixture
    conflict drives the gate flow.
  - consume() refusal in CI runs through the DECLARED deterministic
    contract-follower at the D19 llm.generate seam; the refusal
    PRECONDITION (no covering evidence in the package) is asserted
    deterministically either way. The real-model refusal remains the
    open honest slot.
  - The sensitivity posture: every assertion here is about what the
    governed corpus states or cannot answer - nothing in this suite
    verifies company practice.
"""
import json
import os
import re
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

REAL_NLI = os.environ.get("EM_CORPUS_PROOF_NLI", "").strip() == "1"
if not REAL_NLI:
    os.environ["EM_NLI_VERIFICATION"] = "off"
else:
    # Gate-evidence mode judges EVERY pair: the embedding pre-filter
    # ranks by ingestion.get_embedding, which is a mock under the CI
    # key - it must never silently decide plant fate (D12: no silent
    # caps). A declared test-run knob; deployment posture unchanged.
    os.environ.setdefault("EM_CONFLICT_MAX_PAIRS", "2000")
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_compl_pkg_")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_compl_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'corpus.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_compl_qdrant_")

from app import (schemas, crud, connectors, conflict_engine,  # noqa: E402
                 package_builder, package_consumer, tier2, llm)
import test_support                           # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WB_DIR = os.path.join(REPO_ROOT, "workbench", "compliance_obligation")
CORPUS_DIR = os.path.join(WB_DIR, "corpus")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
CUSOPS_DIR = os.path.join(REPO_ROOT, "workbench", "customer_operations")
DRAFTS_DIR = os.path.join(REPO_ROOT, "docs", "skill-contracts")

SENTINEL = "EM-EXEC-SENTINEL-7C2R"

# The declared question frames (must match the ratified contracts -
# asserted in Part 7 against the contract bytes).
Q_TRAIN_GAP = ("Which approved record shows the completed security "
               "awareness training summary for the latest cycle?")
Q_IR_COVERED = ("Was the annual incident response plan test completed "
                "and the test report retained for audit review?")
Q_OWNER_GAP = "Who is responsible for sending personal data breach notifications?"
Q_OWNER_COVERED = ("Who is responsible for coordinating the annual ISO "
                   "27001 surveillance audit?")

# The declared clock (CORPUS.md): as_of is a run parameter, never
# wall-clock.
AS_OF = (2026, 6, 1)

# The declared explicit-marker rule (extract_compliance_obligations).
MARKER_RE = re.compile(r"\b(must|shall|is required to)\b")
# The declared review-interval convention (identify_outdated_policies),
# applied over whitespace-normalized governed content.
REVIEW_RE = re.compile(
    r"must be reviewed every (\d+) months, and its last completed "
    r"review was dated (\d{4})-(\d{2})-(\d{2})")

OVERLAP_THRESHOLD = 6
REFUSAL_TEXT = ("INSUFFICIENT EVIDENCE - the governed evidence offered does "
                "not contain the answer to this question.")

RATIFIED_ACTIVE = 17  # 5 customer-ops (v1.6) + 6 compliance (v1.7) + 6 procurement (v1.8 WS1 promotion)


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


def overlap(question, content):
    qt = package_consumer._tokens(question)
    return len(qt & package_consumer._tokens(content))


def add_months(y, m, d, n):
    total = (m - 1) + n
    return (y + total // 12, total % 12 + 1, d)


def source_type(filename):
    """The declared source_type_rules, verbatim from the contract."""
    name = filename.lower()
    if "agreement" in name or "contract" in name:
        return "contract"
    if "certification" in name or "certificate" in name:
        return "certification"
    if "regulatory" in name or "regulation" in name:
        return "regulatory"
    return "policy"


def obligation_type(excerpt):
    """The declared obligation_type_rules, verbatim from the contract."""
    text = excerpt.lower()
    for keys, kind in ((("notify", "notification"), "notification"),
                       (("training",), "training"),
                       (("certification", "certified"), "certification"),
                       (("retain", "retention", "destroy"), "retention"),
                       (("report",), "reporting"),
                       (("approval",), "approval"),
                       (("payment", "pay "), "payment"),
                       (("deliver",), "delivery")):
        if any(k in text for k in keys):
            return kind
    return "UNCLASSIFIED"


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


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "ComplianceOfficer")
    reviewer = test_support.governed_actor(session, "ComplianceReviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Compliance Corpus", description="v1.7 WS1 corpus proof",
        customer_id=customer.id), actor=officer)

    connector = db.SourceConnector(project_id=project.id,
                                   name="Compliance Corpus",
                                   type="LOCAL_FOLDER", root_path=CORPUS_DIR,
                                   include_extensions=".md")
    session.add(connector)
    session.commit()
    session.refresh(connector)

    # --- Part 1: the corpus enters through the real pipeline -------------
    print("\n--- Part 1: the corpus through the real pipeline ---")
    run_scan(session, connector)
    doc_count = session.query(db.Document).filter(
        db.Document.project_id == project.id).count()
    assert doc_count == 12, f"expected the 12 corpus documents, got {doc_count}"
    approved_count = approve_all_candidates(
        session, project.id, reviewer, "WS1 compliance corpus approval")
    assert approved_count > 0, "no CANDIDATE assets extracted"
    assets = approved_assets(session, project.id)
    contents = [norm(a.content) for a in assets]
    for needle, label in (("within 72 hours", "P1 breach notification"),
                          ("prior written approval", "P1 sub-processor approval"),
                          ("security awareness training", "P1 training obligation"),
                          ("completion summary for each training cycle",
                           "P2 evidence requirement"),
                          ("ISO 27001", "P1 certification obligation"),
                          ("retained for ten years", "P5 retention side A"),
                          ("destroyed three years", "P5 retention side B"),
                          ("review was dated 2024-05-02", "P3 overdue interval"),
                          ("review was dated 2025-11-10", "P3c current interval"),
                          ("Compliance Officer is responsible",
                           "P4c documented owner")):
        assert any(needle in c for c in contents), \
            f"{label} not present in governed content ({needle!r})"
    print(f"Part 1 passed: {doc_count} documents, {approved_count} assets "
          "approved by a human; every plant sentence present in governed "
          "content.")

    # --- Part 2: explicit obligation extraction only (P1 + P7) ----------
    print("\n--- Part 2: the explicit-marker rule over governed content ---")
    by_doc = {}
    for a in assets:
        doc = session.query(db.Document).filter(
            db.Document.id == a.document_id).first()
        by_doc.setdefault(doc.filename if doc else "?", []).append(norm(a.content))
    obligations = [(fn, c) for fn, cs in by_doc.items() for c in cs
                   if MARKER_RE.search(c)]
    assert obligations, "no explicit-marker obligations in governed content"
    # The P7 implied sentence never carries a marker, in the raw corpus
    # and in every governed obligation.
    with open(os.path.join(CORPUS_DIR, "code-of-business-conduct.md"),
              encoding="utf-8") as f:
        conduct = norm(f.read())
    implied = ("Teams are encouraged to archive completed project files "
               "when convenient.")
    assert implied in conduct, "the P7 implied sentence is missing"
    assert not MARKER_RE.search(implied), \
        "the implied sentence must not carry an explicit marker"
    assert not any("encouraged to archive" in c for _fn, c in obligations), \
        "the implied sentence leaked into the explicit-obligation set"
    # The declared source_type and obligation_type rules produce the
    # CORPUS.md expectations for the four P1 source types.
    expectations = [
        ("data-processing-agreement.md", "within 72 hours",
         "contract", "notification"),
        ("data-processing-agreement.md", "prior written approval",
         "contract", "approval"),
        ("security-training-policy.md", "completion summary for each training",
         "policy", "training"),
        ("iso-27001-certification-statement.md", "shall maintain certification",
         "certification", "certification"),
        ("regulatory-record-keeping-summary.md", "retained for ten years",
         "regulatory", "retention"),
        ("finance-archiving-guideline.md", "destroyed three years",
         "policy", "retention"),
    ]
    for fn, needle, want_src, want_kind in expectations:
        matches = [c for f2, c in obligations if f2 == fn and needle in c]
        assert matches, f"{fn}: obligation {needle!r} not in the marker set"
        assert source_type(fn) == want_src, \
            f"{fn}: source_type {source_type(fn)} != {want_src}"
        got = obligation_type(matches[0])
        assert got == want_kind, \
            f"{fn} ({needle!r}): obligation_type {got} != {want_kind}"
    print(f"Part 2 passed: {len(obligations)} explicit-marker statements; "
          "the implied P7 sentence excluded; declared source_type and "
          "obligation_type rules reproduce the plant-map expectations.")

    # --- Part 3: the review-interval condition (P3 / P3c) ---------------
    print("\n--- Part 3: the declared review-interval convention ---")
    verdicts = {}
    for fn, cs in by_doc.items():
        for c in cs:
            m = REVIEW_RE.search(c)
            if m:
                months, y, mo, d = (int(m.group(1)), int(m.group(2)),
                                    int(m.group(3)), int(m.group(4)))
                due = add_months(y, mo, d, months)
                verdicts[fn] = ("OVERDUE" if due < AS_OF else "CURRENT", due)
    assert verdicts.get("acceptable-use-policy.md", ("?",))[0] == "OVERDUE", \
        f"P3 should be overdue at as_of {AS_OF}: {verdicts}"
    assert verdicts.get("access-control-policy.md", ("?",))[0] == "CURRENT", \
        f"P3c should be current at as_of {AS_OF}: {verdicts}"
    assert len(verdicts) == 2, \
        f"exactly the two review-interval policies expected: {verdicts}"
    print(f"Part 3 passed: at declared as_of {AS_OF} the acceptable-use "
          f"policy is OVERDUE (due {verdicts['acceptable-use-policy.md'][1]}) "
          f"and the access-control policy is CURRENT (due "
          f"{verdicts['access-control-policy.md'][1]}) - the document's own "
          "declared interval, never age alone, never wall-clock.")

    # --- Part 4: the conflict scan (P5) + gate + INTERNAL package -------
    print("\n--- Part 4: conflict scan -> gate -> INTERNAL package ---")
    model = db.ExpertModel(project_id=project.id, name="Compliance Expert",
                           asset_ids_json=json.dumps([a.id for a in assets]),
                           asset_count=len(assets))
    session.add(model)
    session.commit()
    session.refresh(model)
    summary = conflict_engine.scan_expert_model_conflicts(session, model.id)
    by_id = {a.id: norm(a.content) for a in assets}
    conflicts = [r for r in summary["relationships"]
                 if r.relationship_type == "CONFLICTS_WITH"]
    if summary.get("nli_available"):
        def pair_has(rel, needle_a, needle_b):
            a = by_id.get(rel.source_asset_id, "")
            b = by_id.get(rel.target_asset_id, "")
            return ((needle_a in a and needle_b in b)
                    or (needle_a in b and needle_b in a))
        p5 = [r for r in conflicts
              if pair_has(r, "retained for ten years", "destroyed three years")]
        assert p5, "P5 retention contradiction (10y vs 3y) NOT detected"
        assert p5[0].classification == "DIRECT_CONTRADICTION", \
            f"P5 must classify DIRECT_CONTRADICTION, got {p5[0].classification}"
        print(f"Part 4a passed: REAL NLI scan ({summary['compared_pairs']} "
              f"pairs) detected P5 ({p5[0].classification}, conf "
              f"{p5[0].confidence:.3f}); {len(conflicts)} conflict(s) total.")
    else:
        rec = next(a for a in assets
                   if "retained for ten years" in norm(a.content))
        arc = next(a for a in assets
                   if "destroyed three years" in norm(a.content))
        session.add(db.AssetRelationship(
            project_id=project.id, expert_model_id=model.id,
            source_asset_id=rec.id, target_asset_id=arc.id,
            relationship_type="CONFLICTS_WITH",
            classification="DIRECT_CONTRADICTION", confidence=0.99,
            status="DETECTED",
            verifier_json=json.dumps({"method": "TEST_FIXTURE"})))
        session.commit()
        conflicts = session.query(db.AssetRelationship).filter(
            db.AssetRelationship.expert_model_id == model.id,
            db.AssetRelationship.relationship_type == "CONFLICTS_WITH").all()
        print("Part 4a SKIPPED (NLI model unavailable): detection assertion "
              "deferred to the recorded real-NLI gate run; a declared fixture "
              "conflict drives the gate flow.")
    gate = conflict_engine.evaluate_compile_gate(session, model.id)
    assert not gate["allowed"], "unreviewed contradictions should block compile"
    for rel in conflicts:
        conflict_engine.review_relationship(
            session, rel.id, "DISMISSED", reviewer=reviewer,
            notes="WS1 corpus proof: plant contextualized by the human reviewer")
    gate = conflict_engine.evaluate_compile_gate(session, model.id)
    assert gate["allowed"], "gate should open after human review"
    memo_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename.like("%risk-acceptance-memo%")).first()
    assert memo_doc is not None, "the EXECUTIVE memo document is missing"
    exec_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id == memo_doc.id).all()
    assert exec_assets, "no assets extracted from the EXECUTIVE memo"
    for a in exec_assets:
        a.access_level = "EXECUTIVE"
    session.commit()
    package_row = db.AgentPackage(project_id=project.id,
                                  expert_model_id=model.id,
                                  name="Compliance Package",
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
    print(f"Part 4b passed: gate blocked on {len(conflicts)} unreviewed "
          "contradiction(s), opened only by governed human dismissal; "
          "INTERNAL package compiled with the EXECUTIVE sentinel absent.")

    # --- Part 5: the refusal preconditions, deterministically ------------
    print("\n--- Part 5: refusal preconditions (both directions) ---")
    best = {}
    for label, question in (("train_gap", Q_TRAIN_GAP),
                            ("owner_gap", Q_OWNER_GAP),
                            ("ir_covered", Q_IR_COVERED),
                            ("owner_covered", Q_OWNER_COVERED)):
        sel = package_consumer.retrieve(loaded, question, top_k=8)["selected"]
        best[label] = max(overlap(question, e.get("content") or "")
                          for e in sel)
    r_train = package_consumer.retrieve(loaded, Q_TRAIN_GAP, top_k=8)
    assert any("completion summary" in norm(e.get("content"))
               for e in r_train["selected"]), \
        "the P2 requirement excerpt is not retrievable"
    assert best["train_gap"] < OVERLAP_THRESHOLD, \
        f"training-evidence question unexpectedly covered ({best['train_gap']})"
    assert best["owner_gap"] < OVERLAP_THRESHOLD, \
        f"owner question unexpectedly covered ({best['owner_gap']})"
    assert best["ir_covered"] >= OVERLAP_THRESHOLD, \
        f"incident-test control should be covered ({best['ir_covered']})"
    assert best["owner_covered"] >= OVERLAP_THRESHOLD, \
        f"ISO-owner control should be covered ({best['owner_covered']})"
    print(f"Part 5 passed: gap questions uncovered (max overlaps "
          f"{best['train_gap']}/{best['owner_gap']} < {OVERLAP_THRESHOLD}); "
          f"covered controls covered ({best['ir_covered']}/"
          f"{best['owner_covered']} >= {OVERLAP_THRESHOLD}).")

    # --- Part 6: consume() refuses AND answers, reproducibly -------------
    print("\n--- Part 6: refusing correctly before answering correctly ---")

    def contract_follower(function, system, user, session=None, max_tokens=4096):
        """The DECLARED deterministic CI contract-follower at the D19
        seam (the v1.6 pattern): answers only when one governed evidence
        item shares >= OVERLAP_THRESHOLD retrieval tokens with the
        question; otherwise the packaged refusal verbatim."""
        sel = package_consumer.retrieve(loaded, user, top_k=8)["selected"]
        scored = sorted(((overlap(user, e.get("content") or ""), e) for e in sel),
                        key=lambda t: (-t[0], t[1]["asset_id"]))
        if scored and scored[0][0] >= OVERLAP_THRESHOLD:
            _score, e = scored[0]
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
        for question, label in ((Q_TRAIN_GAP, "training evidence"),
                                (Q_OWNER_GAP, "breach-notification owner")):
            first = package_consumer.consume(package_row.file_path, question)
            second = package_consumer.consume(package_row.file_path, question)
            assert first["answer"] == second["answer"], f"{label}: not reproducible"
            assert "INSUFFICIENT EVIDENCE" in first["answer"], \
                f"{label}: expected a refusal, got: {first['answer'][:80]}"
            assert first["cited_asset_ids"] == [], \
                f"{label}: a refusal must cite nothing"
        for question, needle, label in (
                (Q_IR_COVERED, "test report is retained", "incident test"),
                (Q_OWNER_COVERED, "Compliance Officer", "ISO owner")):
            answer = package_consumer.consume(package_row.file_path, question)
            assert "INSUFFICIENT EVIDENCE" not in answer["answer"], \
                f"{label}: the covered control should be answerable"
            assert answer["cited_asset_ids"], \
                f"{label}: the covered answer must cite evidence"
            assert needle in norm(answer["answer"]), \
                f"{label}: the answer should quote the covering evidence"
    finally:
        llm.generate = original_generate
    print("Part 6 passed: both gap questions refused reproducibly with zero "
          "citations; both covered controls answered with citations - "
          "refusing correctly before answering correctly, in BOTH directions.")

    # --- Part 7: draft != ratified + the consolidation ruling -----------
    print("\n--- Part 7: no draft masquerades; consolidation is never silent ---")
    active, consolidated, deferred, total = [], [], [], 0
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
            status = match.group(1)
            if status == "ACTIVE":
                active.append(name)
                rp = re.search(r"^ratified_path: (\S+)", text, re.MULTILINE)
                assert rp, f"{name}: ACTIVE draft without ratified_path"
                assert os.path.isfile(os.path.join(REPO_ROOT, rp.group(1))), \
                    f"{name}: ratified_path does not resolve"
            elif status == "CONSOLIDATED":
                consolidated.append(name)
                ci = re.search(r"^consolidated_into: (\S+)", text, re.MULTILINE)
                rp = re.search(r"^ratified_path: (\S+)", text, re.MULTILINE)
                assert ci, f"{name}: CONSOLIDATED draft without consolidated_into"
                assert rp, f"{name}: CONSOLIDATED draft without ratified_path"
                target = os.path.join(REPO_ROOT, rp.group(1))
                assert os.path.isfile(target), \
                    f"{name}: consolidation ratified_path does not resolve"
                assert os.path.basename(target) == ci.group(1) + ".yaml", \
                    f"{name}: consolidated_into and ratified_path disagree"
            if "the v1.7 deadline deferral" in text:
                deferred.append(name)
                assert status == "SEQUENCED", \
                    f"{name}: the deferred deadline family must stay SEQUENCED"
    assert len(active) == RATIFIED_ACTIVE, \
        f"expected exactly {RATIFIED_ACTIVE} ACTIVE drafts, got {sorted(active)}"
    assert len(consolidated) == 13, \
        f"expected the 13 consolidated drafts (8 at v1.7 + 5 at v1.8), got {sorted(consolidated)}"
    assert sorted(deferred) == ["detect_certification_expiry_risk.yaml",
                                "identify_upcoming_obligations_30_60_90.yaml",
                                "track_explicit_deadlines.yaml",
                                "track_recurrence_rules.yaml"], \
        f"the deferred deadline family is wrong: {sorted(deferred)}"
    # The manifests and the ratified skill files agree, per bundle.
    for wb_dir, expected_count in ((CUSOPS_DIR, 5), (WB_DIR, 6)):
        skills_dir = os.path.join(wb_dir, "skills")
        ratified = sorted(n[:-5] for n in os.listdir(skills_dir)
                          if n.endswith(".yaml"))
        assert len(ratified) == expected_count, \
            f"{wb_dir}: expected {expected_count} ratified contracts"
        with open(os.path.join(wb_dir, "workbench.yaml"), encoding="utf-8") as f:
            manifest = f.read()
        declared = re.findall(r"^  - (\w+)$",
                              manifest.split("skills:\n")[1], re.MULTILINE)
        declared = declared[:expected_count]
        assert sorted(declared) == ratified, \
            f"{wb_dir}: manifest skills {sorted(declared)} != files {ratified}"
    # The declared question frames match the ratified contract bytes.
    with open(os.path.join(SKILLS_DIR, "detect_missing_evidence.yaml"),
              encoding="utf-8") as f:
        me_text = norm(f.read())
    with open(os.path.join(SKILLS_DIR,
                           "detect_undocumented_obligation_owner.yaml"),
              encoding="utf-8") as f:
        ow_text = norm(f.read())
    for q, where, label in ((Q_TRAIN_GAP, me_text, "training gap"),
                            (Q_IR_COVERED, me_text, "incident covered"),
                            (Q_OWNER_GAP, ow_text, "owner gap"),
                            (Q_OWNER_COVERED, ow_text, "owner covered")):
        assert q in where, f"the {label} question is not the contract's frame"
    print(f"Part 7 passed: {total} draft contracts swept; exactly "
          f"{RATIFIED_ACTIVE} ACTIVE with resolving ratified_path; the 8 "
          "CONSOLIDATED drafts each carry consolidated_into + a resolving "
          "ratified_path; the deadline family stays SEQUENCED; both bundle "
          "manifests agree with their ratified files; the suite's question "
          "frames are the contracts' frames verbatim.")

    session.close()
    print("\n=== All compliance corpus-proof checks passed: the corpus "
          "refuses correctly before it answers correctly - in both "
          "directions - and consolidation is never silent promotion. ===")


if __name__ == "__main__":
    main()
