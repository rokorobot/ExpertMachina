"""v2.6.0 WS1 - Operations / Process Improvement: THE PIPELINE CORPUS PROOF.

The catalog #8 corpus proof the template requires and the bundle lacked:
`corpus_operations/` through the REAL governed pipeline (LOCAL_FOLDER scan
-> extraction -> human approval into the workbench domain -> an INTERNAL
empkg-v1.1 package), then every CORPUS.md plant asserted on the PACKAGED
FACTS - the only thing the runner ever reads - using the contracts' own
declared markers. No runner is involved (v2.6 WS1, user-ratified).

The CI pipeline extracts with the rule-based extractor (mock key): a
sentence becomes a fact only if it carries an extraction keyword. The
v2.6 verdict run found four plants lost at extraction; the corpus text
was amended (meaning preserved) so each plant survives as a fact.

Plants (CORPUS.md):
  P1 access-timing contradiction (2 vs 5 business days), cross-document;
  P2 approval-authority SOP-vs-policy pair (CAB + single approver vs team
     lead alone), cross-document;
  P3 two terminal steps with a completion marker and no handoff marker;
  P4 supersession notice naming OPS-RA-04 + the superseded document's own
     identity (its code) and rule as facts;
  P5 three declared review cadences, each with interval + last-review
     date in the SAME document (separate facts - the runner must join by
     document, pinned here for WS2);
  P6 ordered, citable steps in the onboarding SOP and access procedure.
"""
import json
import os
import re
import shutil
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_opspipe_pkg_")
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_opspipe_render_")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmp = tempfile.mkdtemp(prefix="em_opspipe_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmp, 'p.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_opspipe_qdrant_")
from app import schemas, crud, package_builder, package_consumer, tier2   # noqa: E402
import test_support                           # noqa: E402
import test_customer_ops_acceptance as co     # noqa: E402  (pipeline helpers)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO)
import workbench.operations_process_improvement.runner as runner   # noqa: E402

WB = os.path.join(REPO, "workbench", "operations_process_improvement")
SKILLS = os.path.join(WB, "skills")
CORPUS = os.path.join(WB, "corpus_operations")
DOMAIN = "operations_process_improvement"


def markers(skill, block, key):
    return runner.parse_marker_list(os.path.join(SKILLS, f"{skill}.yaml"), block, key)


def packaged_facts():
    db.init_db()
    tier2.verifier_factory = co.ApproveEverythingVerifier
    s = db.SessionLocal()
    officer = test_support.governed_actor(s, "OpsPipeOfficer")
    reviewer = test_support.governed_actor(s, "OpsPipeReviewer")
    customer = crud.get_or_create_default_customer(s)
    project = crud.create_project(s, schemas.ProjectCreate(
        name="Meridian Operations", description="v2.6 WS1", customer_id=customer.id),
        actor=officer)
    scan = tempfile.mkdtemp(prefix="em_opspipe_scan_")
    for n in sorted(os.listdir(CORPUS)):
        shutil.copy(os.path.join(CORPUS, n), os.path.join(scan, n))
    conn = db.SourceConnector(project_id=project.id, name="Ops Docs", type="LOCAL_FOLDER",
                              root_path=scan, include_extensions=".md")
    s.add(conn); s.commit(); s.refresh(conn)
    co.run_scan(s, conn)
    co.approve_all(s, project.id, reviewer, "v2.6 WS1: ops corpus", domain=DOMAIN)
    approved = s.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.status == "APPROVED").all()
    model = db.ExpertModel(project_id=project.id, name="Operations Expert",
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    s.add(model); s.commit(); s.refresh(model)
    pkg = db.AgentPackage(project_id=project.id, expert_model_id=model.id,
                          name="Operations Package", clearance_level="INTERNAL")
    s.add(pkg); s.commit(); s.refresh(pkg)
    package_builder.build_package(s, pkg); s.refresh(pkg)
    loaded = package_consumer.load_package(pkg.file_path)
    s.close()
    return loaded


def by_doc(knowledge):
    docs = {}
    for e in knowledge:
        doc = (e.get("provenance") or {}).get("source_document")
        docs.setdefault(doc, []).append(" ".join((e.get("content") or "").split()))
    return docs


def has(docs, doc, needle):
    return [c for c in docs.get(doc, []) if needle.lower() in c.lower()]


def main():
    print("\n--- Part 1: the corpus through the real pipeline into an empkg-v1.1 package ---")
    loaded = packaged_facts()
    docs = by_doc(loaded["knowledge"])
    assert loaded["manifest"]["package_format"] == "empkg-v1.1"
    assert len(docs) == 6, sorted(docs)
    print(f"Part 1 passed: {len(loaded['knowledge'])} human-approved facts from "
          f"{len(docs)} documents in the {DOMAIN} domain.")

    print("\n--- Part 2: every CORPUS.md plant survives extraction as a packaged fact ---")
    ON, AR, CP, CS, RA, AG = ("employee-onboarding-sop.md", "access-request-procedure.md",
                              "change-management-policy.md", "change-management-sop.md",
                              "remote-access-sop.md", "access-governance-policy.md")
    # P1
    assert has(docs, ON, "within 2 business days") and has(docs, AR, "within 5 business days"), \
        "P1: both sides of the access-timing contradiction must be facts"
    # P2
    assert has(docs, CP, "must be approved by the change advisory board"), "P2 policy side"
    assert has(docs, CP, "single approver"), "P2 single-approver prohibition"
    assert has(docs, CS, "approved by the team lead alone"), "P2 SOP side"
    # P3 - completion marker present, no handoff marker (the contract's own lists)
    completion = markers("detect_missing_handoffs", "handoff_convention", "completion_markers")
    handoff = markers("detect_missing_handoffs", "handoff_convention", "handoff_markers")
    for doc, needle in ((AR, "is then closed out"), (ON, "is complete after the two-week period")):
        facts = has(docs, doc, needle)
        assert facts, f"P3: terminal step {needle!r} must be a fact"
        f = facts[0].lower()
        assert any(m in f for m in completion) and not any(m in f for m in handoff), (needle, f)
    # P4
    sup = markers("detect_outdated_process_documents", "staleness_convention",
                  "supersession_markers")
    assert [c for c in docs[AG] if "OPS-RA-04" in c and any(m in c.lower() for m in sup)], \
        "P4: the supersession notice naming OPS-RA-04 must be a fact"
    assert has(docs, RA, "OPS-RA-04"), \
        "P4: the superseded document's own identity (its code) must be a fact"
    assert has(docs, RA, "shared team VPN credential"), "P4: the superseded rule"
    # P5 - interval and last-review date in the SAME document
    for doc, months, date in ((CP, 12, "2024-01-15"), (CS, 6, "2024-02-01"),
                              (AG, 12, "2026-05-01")):
        assert has(docs, doc, f"reviewed at least once every {months} months"), (doc, months)
        assert has(docs, doc, f"last review was recorded on {date}"), (doc, date)
    # P6 - ordered, citable steps
    for doc, n in ((ON, 4), (AR, 3)):
        steps = sorted({int(m) for c in docs[doc] for m in re.findall(r"\bStep (\d)\b", c)})
        assert steps == list(range(1, n + 1)), (doc, steps)
    print("Part 2 passed: P1-P6 all present as packaged facts, judged with the "
          "contracts' own completion / handoff / supersession markers.")

    print("\n=== v2.6.0 WS1 passed: the catalog #8 corpus survives the real "
          "governed pipeline - every plant is a fact the runner can read. ===")


if __name__ == "__main__":
    main()
