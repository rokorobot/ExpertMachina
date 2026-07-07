"""v1.8 WS1 - THE CORPUS PROOF for the Procurement Document
Intelligence Workbench.

Proves the WS0-ratified WS1 requirements against the ratified corpus
(workbench/procurement_intelligence/corpus/, plant map in CORPUS.md -
the non-runtime oracle), through EM's OWN machinery, BEFORE any runner
code reads the corpus:

  1. The 12 documents enter through the real pipeline; every plant
     sentence present in governed content.
  2. THE CLAUSE ARITHMETIC preconditions: the declared date marker
     extracts verbatim dates; window arithmetic at the pinned as_of
     verdicts P1 IN and P1c OUT; the P6 renewal-context sentence has NO
     parseable date (the refusal precondition - never guessed); the
     paraphrase trap (P3t) carries NO digit and no percent token, and
     "20%" appears NOWHERE in governed content; the P8 noisy numbers
     match no extraction marker (never promoted).
  3. The declared extraction rules reproduce the T1 term classes (sla /
     data_access) and the P3 explicit percentage verbatim.
  4. The P5 payment-terms contradiction is detectable (real NLI under
     EM_CORPUS_PROOF_NLI=1; declared fixture otherwise), passes the
     inherited same-subject + cross-document rules, and the compile
     gate -> INTERNAL package excludes the EXECUTIVE sentinel.
  5. consume() reproducibly REFUSES the DataFlow certificate question
     and ANSWERS the SecureStore one with supplier-named evidence
     (refusal-first cuts both ways; SUPPLIER-NAMED COVERAGE per the
     ratified contract - another supplier's certificate is never
     evidence).
  6. The six ratified contracts exist with the required 13-field shape;
     the manifest agrees; the draft != ratified sweep stays honest
     (17 ACTIVE / 13 CONSOLIDATED globally; consolidation never silent).
  7. Zero schema: the D24 metadata count stands at 28 tables / 305
     columns; no backend module changed.

The sensitivity posture holds in the proof itself: every assertion is
about what governed documents state or cannot answer - nothing here
estimates, converts, or invents a number (THE INVENTED NUMBER is the
cardinal sin).
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
    os.environ.setdefault("EM_CONFLICT_MAX_PAIRS", "2000")
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_proc_pkg_")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_proc_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'corpus.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_proc_qdrant_")

from app import (schemas, crud, connectors, conflict_engine,  # noqa: E402
                 package_builder, package_consumer, tier2, llm)
import test_support                           # noqa: E402

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from workbench import common                  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WB_DIR = os.path.join(REPO_ROOT, "workbench", "procurement_intelligence")
CORPUS_DIR = os.path.join(WB_DIR, "corpus")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
DRAFTS_DIR = os.path.join(REPO_ROOT, "docs", "skill-contracts")

SENTINEL = "EM-EXEC-SENTINEL-4V8P"

# The declared clock (CORPUS.md): run parameters, never wall-clock.
AS_OF = (2026, 6, 1)
WINDOW_DAYS = 90

# The declared conventions, verbatim from the ratified contracts
# (asserted against the contract bytes in Part 6).
DATE_MARKER_RE = re.compile(
    r"(terminates on|expires on|renews on|termination date of) "
    r"(\d{4}-\d{2}-\d{2})")
RENEWAL_CONTEXT = ("renews", "renewal", "expires", "terminates")
TERM_MARKER_RE = re.compile(r"\b(must|shall|is required to|will provide)\b")
INCREASE_MARKERS = ("increases by", "increase of", "price adjustment",
                    "uplift", "adjusted upward")
PCT_RE = re.compile(r"\d+(\.\d+)?\s?%")

Q_CERT_MISSING = ("Which approved document holds the current ISO 27001 "
                  "certificate for DataFlow?")
Q_CERT_COVERED = ("Which approved document holds the current ISO 27001 "
                  "certificate for SecureStore?")

OVERLAP_THRESHOLD = 6
REFUSAL_TEXT = ("INSUFFICIENT EVIDENCE - the governed evidence offered does "
                "not contain the answer to this question.")

RATIFIED_ACTIVE = 17   # 5 (v1.6) + 6 (v1.7) + 6 (v1.8)
RATIFIED_CONSOLIDATED = 13   # 8 (v1.7) + 5 (v1.8)
REQUIRED_FIELDS = (
    "skill_id:", "workbench:", "status:", "boundary_tags:", "purpose:",
    "allowed_inputs:", "forbidden_inputs:", "evidence_rules:",
    "allowed_finding_kinds:", "output_format:",
    "human_approval_requirement:", "audit_event:", "refusal_conditions:")

ACTIVE_SIX = ("extract_vendor_terms", "detect_renewal_window",
              "detect_price_increase_clauses",
              "identify_missing_supplier_certifications",
              "detect_vendor_policy_conflict", "prepare_renegotiation_brief")


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


def add_days(y, m, d, n):
    import datetime
    end = datetime.date(y, m, d) + datetime.timedelta(days=n)
    return (end.year, end.month, end.day)


def overlap(question, content):
    qt = package_consumer._tokens(question)
    return len(qt & package_consumer._tokens(content))


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


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "ProcOfficer")
    reviewer = test_support.governed_actor(session, "ProcReviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Procurement Corpus", description="v1.8 WS1 corpus proof",
        customer_id=customer.id), actor=officer)
    connector = db.SourceConnector(project_id=project.id,
                                   name="Procurement Corpus",
                                   type="LOCAL_FOLDER", root_path=CORPUS_DIR,
                                   include_extensions=".md")
    session.add(connector)
    session.commit()
    session.refresh(connector)

    # --- Part 1: the corpus through the real pipeline --------------------
    print("\n--- Part 1: the corpus through the real pipeline ---")
    run_scan(session, connector)
    doc_count = session.query(db.Document).filter(
        db.Document.project_id == project.id).count()
    assert doc_count == 12, f"expected the 12 corpus documents, got {doc_count}"
    for asset in session.query(db.KnowledgeAsset).filter_by(
            project_id=project.id, status="CANDIDATE").all():
        crud.update_knowledge_asset(
            session, asset.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=reviewer, review_notes="WS1 procurement corpus approval")
    assets = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    contents = [norm(a.content) for a in assets]
    for needle, label in (("terminates on 2026-08-15", "P1 window positive"),
                          ("terminates on 2027-09-30", "P1c window negative"),
                          ("renews automatically", "P2 auto-renewal"),
                          ("increases by 7%", "P3 explicit percentage"),
                          ("increases by one fifth", "P3t paraphrase trap"),
                          ("must hold a current ISO 27001 certificate",
                           "P4 requirement"),
                          ("DataFlow processes customer data", "P4 scope"),
                          ("SecureStore holds a current ISO 27001 certificate",
                           "P4c covered certificate"),
                          ("payable within 21 days", "P5 conflict side A"),
                          ("must be at least 45 days", "P5 conflict side B"),
                          ("payable within 60 days", "P5c conforming"),
                          ("renews at the start of the fiscal year",
                           "P6 unparseable date"),
                          ("99.9% monthly service availability", "T1 sla term")):
        assert any(needle in c for c in contents), \
            f"{label} not present in governed content ({needle!r})"
    print(f"Part 1 passed: 12 documents, {len(assets)} assets approved by a "
          "human; every plant sentence present in governed content.")

    # --- Part 2: THE CLAUSE ARITHMETIC preconditions ----------------------
    print("\n--- Part 2: clause arithmetic - verbatim dates, declared clock ---")
    window_end = add_days(*AS_OF, WINDOW_DAYS)
    verdicts = {}
    for c in contents:
        for m in DATE_MARKER_RE.finditer(c):
            y, mo, d = (int(p) for p in m.group(2).split("-"))
            in_window = AS_OF <= (y, mo, d) <= window_end
            verdicts[m.group(2)] = in_window
    assert verdicts.get("2026-08-15") is True, \
        f"P1 must verdict IN-window at as_of {AS_OF}: {verdicts}"
    assert verdicts.get("2027-09-30") is False, \
        f"P1c must verdict OUT-of-window: {verdicts}"
    assert len(verdicts) == 2, \
        f"exactly the two dated termination clauses expected: {verdicts}"
    # P6: renewal context with NO parseable date -> the refusal precondition.
    legacy = [c for c in contents if "start of the fiscal year" in c]
    assert legacy and all(
        any(k in c.lower() for k in RENEWAL_CONTEXT)
        and not DATE_MARKER_RE.search(c) and not re.search(r"\d{4}-\d{2}-\d{2}", c)
        for c in legacy), "P6 must be renewal-context with no parseable date"
    # P3t: the paraphrase trap carries NO digits and no percent token; the
    # converted value appears NOWHERE in governed content.
    trap = [c for c in contents if "one fifth" in c]
    assert trap, "the paraphrase trap is missing"
    for c in trap:
        sent = next(t for t in re.split(r"(?<=[.;])\s+", c) if "one fifth" in t)
        assert not re.search(r"\d", sent), f"trap sentence carries a digit: {sent!r}"
        assert not PCT_RE.search(c), "the trap must carry no percent token"
    assert not any("20%" in c for c in contents), \
        "the converted paraphrase value must appear NOWHERE (THE INVENTED NUMBER)"
    # P8: noisy numbers match no extraction marker - never promoted.
    noisy = [c for c in contents
             if any(n in c for n in ("4501 Commerce Park", "555 0142",
                                     "clause 12.3", "700000"))]
    assert noisy, "the noisy sentences must exist in governed content"
    for c in noisy:
        assert not any(mk in c.lower() for mk in INCREASE_MARKERS), c
        assert not DATE_MARKER_RE.search(c), c
        assert not TERM_MARKER_RE.search(c), \
            f"noisy sentence must carry no extraction marker: {c!r}"
    print(f"Part 2 passed: window arithmetic from verbatim dates at declared "
          f"as_of {AS_OF}/+{WINDOW_DAYS}d (P1 IN, P1c OUT); P6 refusal "
          "precondition holds; the paraphrase trap is non-numeric and its "
          "conversion absent corpus-wide; noisy numbers match no marker.")

    # --- Part 3: the declared extraction rules ----------------------------
    print("\n--- Part 3: declared term classes + explicit percentage ---")
    sla = [c for c in contents if "99.9% monthly service availability" in c]
    assert sla and all(TERM_MARKER_RE.search(c) for c in sla)
    assert any(k in sla[0].lower() for k in ("availability",)), "sla class"
    da = [c for c in contents if "subprocessor" in c.lower()]
    assert da and any(TERM_MARKER_RE.search(c) for c in da), "data_access term"
    p3 = [c for c in contents if "increases by 7%" in c]
    assert p3 and PCT_RE.search(p3[0]), "P3 percentage must be verbatim"
    print("Part 3 passed: T1 terms carry explicit markers with their declared "
          "classes; the P3 percentage is verbatim-citable.")

    # --- Part 4: the P5 conflict + gate + INTERNAL package ---------------
    print("\n--- Part 4: conflict scan -> gate -> INTERNAL package ---")
    a_side = next(a for a in assets if "payable within 21 days" in norm(a.content))
    b_side = next(a for a in assets if "must be at least 45 days" in norm(a.content))
    assert common.shared_subject(norm(a_side.content), norm(b_side.content)) \
        >= common.SAME_SUBJECT_MINIMUM, "P5 must pass the same-subject rule"
    assert a_side.document_id != b_side.document_id, "P5 must be cross-document"
    model = db.ExpertModel(project_id=project.id, name="Procurement Expert",
                           asset_ids_json=json.dumps([a.id for a in assets]),
                           asset_count=len(assets))
    session.add(model)
    session.commit()
    session.refresh(model)
    summary = conflict_engine.scan_expert_model_conflicts(session, model.id)
    conflicts = [r for r in summary["relationships"]
                 if r.relationship_type == "CONFLICTS_WITH"]
    if summary.get("nli_available"):
        p5 = [r for r in conflicts
              if {r.source_asset_id, r.target_asset_id} == {a_side.id, b_side.id}]
        assert p5, "P5 payment-terms contradiction NOT detected by real NLI"
        print(f"Part 4a passed: REAL NLI ({summary['compared_pairs']} pairs) "
              f"detected P5 ({p5[0].classification}, conf {p5[0].confidence:.3f}).")
    else:
        session.add(db.AssetRelationship(
            project_id=project.id, expert_model_id=model.id,
            source_asset_id=a_side.id, target_asset_id=b_side.id,
            relationship_type="CONFLICTS_WITH",
            classification="DIRECT_CONTRADICTION", confidence=0.99,
            status="DETECTED",
            verifier_json=json.dumps({"method": "TEST_FIXTURE"})))
        session.commit()
        conflicts = session.query(db.AssetRelationship).filter_by(
            expert_model_id=model.id,
            relationship_type="CONFLICTS_WITH").all()
        print("Part 4a SKIPPED (NLI model unavailable): detection deferred to "
              "the recorded real-NLI gate run; a declared fixture drives the flow.")
    gate = conflict_engine.evaluate_compile_gate(session, model.id)
    assert not gate["allowed"], "unreviewed contradictions should block compile"
    for rel in conflicts:
        conflict_engine.review_relationship(
            session, rel.id, "DISMISSED", reviewer=reviewer,
            notes="WS1 corpus proof: plant contextualized by the human reviewer")
    assert conflict_engine.evaluate_compile_gate(session, model.id)["allowed"]
    memo_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename.like("%executive-vendor-strategy%")).first()
    for a in session.query(db.KnowledgeAsset).filter_by(
            document_id=memo_doc.id).all():
        a.access_level = "EXECUTIVE"
    session.commit()
    package_row = db.AgentPackage(project_id=project.id,
                                  expert_model_id=model.id,
                                  name="Procurement Package",
                                  clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    package_builder.build_package(session, package_row)
    session.refresh(package_row)
    with open(package_row.file_path, "rb") as f:
        assert SENTINEL.encode() not in f.read(), \
            "the EXECUTIVE sentinel leaked into the INTERNAL package bytes"
    loaded = package_consumer.load_package(package_row.file_path)
    print("Part 4b passed: gate blocked then opened by governed human review; "
          "INTERNAL package compiled with the EXECUTIVE sentinel absent.")

    # --- Part 5: consume() refuses AND answers, supplier-named -----------
    print("\n--- Part 5: refusing correctly before answering correctly ---")

    def contract_follower(function, system, user, session=None, max_tokens=4096):
        """The DECLARED deterministic CI contract-follower at the D19
        seam: answers only when one governed evidence item shares >=
        OVERLAP_THRESHOLD retrieval tokens with the question AND names
        the supplier the question names (SUPPLIER-NAMED COVERAGE, the
        ratified evidence rule); otherwise the packaged refusal."""
        sel = package_consumer.retrieve(loaded, user, top_k=8)["selected"]
        supplier = None
        for name in ("DataFlow", "SecureStore", "CloudHost", "Translient",
                     "PrintWorks", "OfficeSupply"):
            if name.lower() in user.lower():
                supplier = name
        scored = sorted(((overlap(user, e.get("content") or ""), e)
                         for e in sel),
                        key=lambda t: (-t[0], t[1]["asset_id"]))
        best = next(((s, e) for s, e in scored
                     if s >= OVERLAP_THRESHOLD
                     and (supplier is None
                          or supplier.lower() in (e.get("content") or "").lower())),
                    None)
        if best:
            text = (f"Per the governed evidence (asset_id "
                    f"{best[1]['asset_id']}): {best[1].get('content')}")
        else:
            text = REFUSAL_TEXT
        return {"function": function, "provider": "TEST",
                "model": "contract-follower-v1", "source": "deterministic-ci",
                "text": text}

    original_generate = llm.generate
    llm.generate = contract_follower
    try:
        first = package_consumer.consume(package_row.file_path, Q_CERT_MISSING)
        second = package_consumer.consume(package_row.file_path, Q_CERT_MISSING)
        assert first["answer"] == second["answer"], "refusal not reproducible"
        assert "INSUFFICIENT EVIDENCE" in first["answer"], \
            f"DataFlow question must refuse: {first['answer'][:90]}"
        assert first["cited_asset_ids"] == [], "a refusal must cite nothing"
        covered = package_consumer.consume(package_row.file_path, Q_CERT_COVERED)
        assert "INSUFFICIENT EVIDENCE" not in covered["answer"], \
            "the SecureStore covered control should be answerable"
        assert "SecureStore" in covered["answer"], \
            "the covering answer must NAME the supplier (the ratified rule)"
        assert covered["cited_asset_ids"], "the covered answer must cite evidence"
    finally:
        llm.generate = original_generate
    print("Part 5 passed: the DataFlow certificate question refused "
          "reproducibly with zero citations; the SecureStore question "
          "answered with supplier-named cited evidence.")

    # --- Part 6: contracts + the draft != ratified sweep ------------------
    print("\n--- Part 6: contract shape + no silent promotion ---")
    with open(os.path.join(WB_DIR, "workbench.yaml"), encoding="utf-8") as f:
        manifest = f.read()
    declared = re.findall(r"^  - (\w+)$", manifest.split("skills:\n")[1],
                          re.MULTILINE)[:6]
    ratified = sorted(n[:-5] for n in os.listdir(SKILLS_DIR)
                      if n.endswith(".yaml"))
    assert sorted(declared) == ratified == sorted(ACTIVE_SIX), \
        f"manifest {sorted(declared)} != files {ratified}"
    for skill in ACTIVE_SIX:
        with open(os.path.join(SKILLS_DIR, f"{skill}.yaml"),
                  encoding="utf-8") as f:
            text = f.read()
        for field in REQUIRED_FIELDS:
            assert re.search(rf"^{field}", text, re.MULTILINE), \
                f"{skill}: missing contract field {field}"
    # The suite's declared conventions are the contracts' conventions.
    with open(os.path.join(SKILLS_DIR, "detect_renewal_window.yaml"),
              encoding="utf-8") as f:
        rw = norm(f.read())
    for marker in ("terminates on", "expires on", "renews on"):
        assert marker in rw, f"date marker {marker!r} not declared"
    with open(os.path.join(SKILLS_DIR,
                           "identify_missing_supplier_certifications.yaml"),
              encoding="utf-8") as f:
        mc = norm(f.read())
    assert "must hold a current ISO 27001 certificate" in mc
    assert "SUPPLIER-NAMED COVERAGE" in mc
    active, consolidated = [], []
    for folder, _dirs, files in os.walk(DRAFTS_DIR):
        for name in files:
            if not name.endswith(".yaml"):
                continue
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                text = f.read()
            status = re.search(r"^status: (\S+)", text, re.MULTILINE).group(1)
            if status == "ACTIVE":
                active.append(name)
                rp = re.search(r"^ratified_path: (\S+)", text, re.MULTILINE)
                assert rp and os.path.isfile(os.path.join(REPO_ROOT, rp.group(1))), \
                    f"{name}: ACTIVE draft without a resolving ratified_path"
            elif status == "CONSOLIDATED":
                consolidated.append(name)
                ci = re.search(r"^consolidated_into: (\S+)", text, re.MULTILINE)
                rp = re.search(r"^ratified_path: (\S+)", text, re.MULTILINE)
                assert ci and rp, f"{name}: consolidation must never be silent"
                target = os.path.join(REPO_ROOT, rp.group(1))
                assert os.path.isfile(target), f"{name}: ratified_path broken"
                assert os.path.basename(target) == ci.group(1) + ".yaml", \
                    f"{name}: consolidated_into and ratified_path disagree"
    assert len(active) == RATIFIED_ACTIVE, \
        f"expected {RATIFIED_ACTIVE} ACTIVE drafts, got {len(active)}"
    assert len(consolidated) == RATIFIED_CONSOLIDATED, \
        f"expected {RATIFIED_CONSOLIDATED} CONSOLIDATED, got {len(consolidated)}"
    print(f"Part 6 passed: six 13-field contracts match the manifest; the "
          f"declared conventions live in the contract bytes; the global sweep "
          f"holds at {RATIFIED_ACTIVE} ACTIVE / {RATIFIED_CONSOLIDATED} "
          "CONSOLIDATED with every path resolving.")

    # --- Part 7: zero schema ----------------------------------------------
    print("\n--- Part 7: zero schema ---")
    tables = len(db.Base.metadata.tables)
    columns = sum(len(t.columns) for t in db.Base.metadata.tables.values())
    assert (tables, columns) == (28, 305), (tables, columns)
    print(f"Part 7 passed: the D24 snapshot stands at exactly {tables} tables "
          f"/ {columns} columns - v1.8 changes behavior and fixtures only.")

    session.close()
    print("\n=== All procurement corpus-proof checks passed: every number "
          "verbatim, every window computed on the declared clock, refusing "
          "correctly before answering correctly - THE INVENTED NUMBER has "
          "no path into a finding. ===")


if __name__ == "__main__":
    main()
