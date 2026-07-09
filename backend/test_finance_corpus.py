"""v2.3 WS1 gate suite — THE PRECONDITION PROOF (the 84th suite).

Proves the WS0-ratified v2.3 preconditions against the ratified
contracts and the REAL corpora BEFORE any runner exists
(docs/finance-cost-leakage-v2.3.md — Finance & Cost Leakage, catalog
#2, document-governed cost exposure intelligence):

  1. THE BUNDLE SHAPE — the manifest + the five ratified contracts
     agree; the binding conventions are declared in the bytes; NO
     runner exists yet, NO UI, NO transactional input door; the
     forbidden-input classes are named; THE INVOICE PLANT is declared.
  2. The corpora through the real pipeline — the 12-document
     procurement corpus + the 3-document corpus_finance/ extension,
     two connectors, one project, every candidate human-approved.
  3. THE EXPOSURE MATERIAL REPORT — the contract's OWN declared class
     markers (parsed from the ratified bytes) fire on approved facts:
     price_increase (8%), penalty_fee (1.5% surcharge), leakage
     (minimum commitment), renewal_cost; verbatim currency amounts
     (12,000 EUR) exist for declared arithmetic.
  4. THE POLICY-COMPARISON precondition — the finance policy's
     spend-approval thresholds and payment-terms floor are approved
     facts to compare contract terms against (the declared axes).
  5. THE SECOND HARVEST precondition — a dated register-class clause
     is an approved fact citable BY governed asset id (the v2.1
     register WILL carry the anchor detect_cost_exposure reads).
  6. THE UNOPENED LEDGER precondition — THE INVOICE PLANT, though an
     approved document, is DISTINGUISHABLE: it carries SETTLED-ACCOUNT
     transactional-truth markers no contract clause carries, so the
     runner can decline it naming [OE]; no transactional door exists;
     the two cross-workbench consolidations resolve; global sweep at
     34/58; zero stewardship; D24 at exactly 28 tables / 305 columns.

No [OE] operational fact, no [PMD] ingress, no route, no table, no
tool, no guard, and no law is needed anywhere in this suite - the
preconditions hold on governed document facts alone. NO runner is
built.
"""
import os
import re
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_fin_pkg_")

from sqlalchemy import create_engine, inspect  # noqa: E402
from sqlalchemy.orm import sessionmaker        # noqa: E402
from app import database as db                 # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_fin_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'corpus.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                      # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_fin_qdrant_")

from app import schemas, crud, connectors, tier2  # noqa: E402
import test_support                            # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WB_DIR = os.path.join(REPO_ROOT, "workbench", "finance_cost_leakage")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
FINANCE_CORPUS = os.path.join(WB_DIR, "corpus_finance")
PROC_CORPUS = os.path.join(REPO_ROOT, "workbench",
                           "procurement_intelligence", "corpus")
CI_SKILLS = os.path.join(REPO_ROOT, "workbench", "contract_intelligence",
                         "skills")
DRAFTS_DIR = os.path.join(REPO_ROOT, "docs", "skill-contracts")

ACTIVE_FIVE = ("detect_cost_exposure", "compare_terms_vs_finance_policy",
               "detect_missing_finance_evidence",
               "prepare_cost_exposure_scenario",
               "prepare_finance_evidence_pack")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def norm(t):
    return " ".join((t or "").split())


def parse_nested_marker_map(text, block_key, map_key):
    """v2.3: read `map_key:` (a nested map of `class: ["m", ...]` entries,
    values may wrap across lines) inside a convention block - returns
    {class: [markers]}. Accumulates each entry until its list closes."""
    lines = text.splitlines()
    out, in_map, cur_key, buf = {}, False, None, ""
    for line in lines:
        s = line.strip()
        if s.startswith(f"{map_key}:"):
            in_map = True
            continue
        if not in_map:
            continue
        if cur_key is not None:                     # accumulating a wrapped list
            buf += " " + s
            if "]" in buf:
                out[cur_key] = re.findall(r'"([^"]+)"', buf)
                cur_key, buf = None, ""
            continue
        m = re.match(r"^([a-z_]+):\s*\[(.*)$", s)   # a new `class: [...` entry
        if m:
            cur_key, buf = m.group(1), m.group(2)
            if "]" in buf:
                out[cur_key] = re.findall(r'"([^"]+)"', buf)
                cur_key, buf = None, ""
            continue
        if s and not s.startswith("#"):             # dedent out of the map
            break
    return out


def run_scan(session, connector):
    job = db.IngestionJob(project_id=connector.project_id,
                          connector_id=connector.id, status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    connectors.execute_ingestion_job(session, job.id)
    tier2.drain()
    session.refresh(job)
    assert job.status == "COMPLETED", f"{job.status} / {job.error}"
    return job


def approve_all(session, project_id, reviewer, note):
    for asset in session.query(db.KnowledgeAsset).filter(
            db.KnowledgeAsset.project_id == project_id,
            db.KnowledgeAsset.status == "CANDIDATE").all():
        crud.update_knowledge_asset(
            session, asset.id,
            schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=reviewer, review_notes=note)


def main():
    db.init_db()
    session = db.SessionLocal()

    # ------------------------------------------------------------ Part 1
    print("\n--- Part 1: THE BUNDLE SHAPE (document-bound, pinned) ---")
    ratified = sorted(n[:-5] for n in os.listdir(SKILLS_DIR)
                      if n.endswith(".yaml"))
    assert ratified == sorted(ACTIVE_FIVE), f"skills/ mismatch: {ratified}"
    manifest = read(os.path.join(WB_DIR, "workbench.yaml"))
    declared = re.findall(r"^  - (\w+)$", manifest.split("skills:\n")[1],
                          re.MULTILINE)[:5]
    assert sorted(declared) == sorted(ACTIVE_FIVE), "manifest disagrees"
    assert "canonical_number: 2" in manifest

    # The bundle carries ONLY the runner - never an operational connector,
    # invoice/PO/ERP/ledger/bank reader, or UI module. (At WS1 this set was
    # empty; WS2 adds runner.py. The DURABLE precondition - the one this
    # permanent suite guards forever - is that no transactional-reader
    # module ever appears in the bundle.)
    py_files = set(f for f in os.listdir(WB_DIR) if f.endswith(".py"))
    assert py_files <= {"runner.py"}, \
        f"the bundle carries only the runner, never a reader: {py_files}"

    # The binding conventions are declared, not implied.
    ddl = read(os.path.join(SKILLS_DIR, "detect_cost_exposure.yaml"))
    for needle in ("exposure_classes", "class_markers", "money_value_rule",
                   "the_second_harvest", "THE INVENTED MONEY",
                   "THE SETTLED ACCOUNT", "forbidden_vocabulary"):
        assert needle in ddl, f"detect_cost_exposure missing {needle}"
    cmp_c = read(os.path.join(SKILLS_DIR,
                              "compare_terms_vs_finance_policy.yaml"))
    assert "comparison_axes" in cmp_c and "payment_terms" in cmp_c
    scen = read(os.path.join(SKILLS_DIR, "prepare_cost_exposure_scenario.yaml"))
    assert "[assist, synth]" in scen and "estimate_label" in scen \
        and "never written to /08_proposals" in norm(scen)

    # The forbidden-input classes + THE INVOICE PLANT declared.
    for needle in ("forbidden_inputs", "invoices as transactional records",
                   "THE INVOICE PLANT", "the_unopened_ledger",
                   "the_invoice_sentence_distinction"):
        assert needle in manifest, f"manifest missing {needle}"
    print("Part 1 passed: manifest + 5 ratified contracts agree; every "
          "binding convention declared; NO runner, NO UI, NO transactional "
          "door yet; forbidden inputs + THE INVOICE PLANT declared.")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: the corpora through the real pipeline ---")
    officer = test_support.governed_actor(session, "fin_officer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Finance Corpus", description="v2.3 WS1 precondition proof",
        customer_id=customer.id), actor=officer)
    for name, root in (("Procurement Corpus", PROC_CORPUS),
                       ("Finance Extension Corpus", FINANCE_CORPUS)):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
    doc_count = session.query(db.Document).filter_by(
        project_id=project.id).count()
    assert doc_count == 15, f"expected 12 procurement + 3 finance, got {doc_count}"
    reviewer = test_support.governed_actor(session, "fin_reviewer")
    approve_all(session, project.id, reviewer, "WS1 finance corpus approval")
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    assert approved and all(a.source_class == "PRIMARY" for a in approved)
    facts = [(a.id, norm(a.content)) for a in approved]
    print(f"Part 2 passed: 15 documents -> {len(approved)} approved PRIMARY "
          f"facts through the real pipeline.")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE EXPOSURE MATERIAL REPORT (declared markers "
          "over real facts) ---")
    markers = parse_nested_marker_map(ddl, "exposure_convention",
                                      "class_markers")
    assert set(markers) >= {"price_increase", "renewal_cost", "penalty_fee",
                            "leakage", "pricing_review"}, markers
    fired = {}
    for cls, mks in markers.items():
        hits = [aid for aid, c in facts
                if any(mk in c.lower() for mk in mks)]
        fired[cls] = hits
    for cls in ("price_increase", "renewal_cost", "penalty_fee", "leakage"):
        assert fired[cls], f"no approved fact carries a {cls} marker"
    # Verbatim currency + percentage material for the money doctrine.
    currency = [aid for aid, c in facts
                if re.search(r"\b[0-9][0-9,]* EUR\b", c)]
    assert currency, "a verbatim currency amount must exist (declared arithmetic)"
    pct = [aid for aid, c in facts if re.search(r"\b\d+%", c)]
    assert pct, "a verbatim percentage escalator/surcharge must exist"
    assert any("12,000 EUR" in c for _a, c in facts), \
        "the colocation fee anchor must be an approved fact"
    print(f"Part 3 passed: exposure markers fire - price_increase "
          f"{len(fired['price_increase'])}, renewal_cost "
          f"{len(fired['renewal_cost'])}, penalty_fee "
          f"{len(fired['penalty_fee'])}, leakage {len(fired['leakage'])}; "
          f"{len(currency)} currency fact(s), {len(pct)} percentage fact(s).")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: THE POLICY-COMPARISON precondition ---")
    policy_facts = [(aid, c) for aid, c in facts
                    if "approved by the finance director" in c.lower()
                    or "must be approved" in c.lower()
                    or "at least 30 days" in c.lower()
                    or "at least 45 days" in c.lower()]
    assert policy_facts, "finance-policy comparison material must be approved"
    thresholds = [c for _a, c in facts if "50,000 EUR" in c or "5,000 EUR" in c]
    assert thresholds, "spend-approval thresholds must be approved facts"
    floor = [c for _a, c in facts
             if "at least 30 days" in c.lower() or "at least 45 days" in c.lower()]
    assert floor, "a payment-terms floor must be an approved fact"
    payable = [c for _a, c in facts
               if re.search(r"payable within \d+ days", c.lower())]
    assert payable, "a contract payment term must exist to compare vs the floor"
    print(f"Part 4 passed: {len(thresholds)} spend-threshold fact(s), a "
          f"payment-terms floor, and {len(payable)} contract payment-term "
          f"fact(s) - the declared comparison axes have both sides.")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: THE SECOND HARVEST precondition (register anchor "
          "citable BY ID) ---")
    dated = [(aid, c) for aid, c in facts
             if re.search(r"\d{4}-\d{2}-\d{2}", c)
             and ("terminates" in c.lower() or "renews" in c.lower()
                  or "anniversary" in c.lower())]
    assert dated, "a dated renewal/termination clause must be approved"
    anchor_id, anchor_c = dated[0]
    assert isinstance(anchor_id, int) and anchor_id > 0
    ci_text = read(os.path.join(CI_SKILLS, "extract_contract_clauses.yaml"))
    structural = ci_text.split("structural_classes:")[1]
    assert "renewal" in structural and "payment" in structural, \
        "the v2.1 register taxonomy carries the classes v2.3 will harvest"
    print(f"Part 5 passed: asset #{anchor_id} is a dated register-class "
          f"clause citable BY id; the v2.1 taxonomy classifies it - the "
          f"harvest anchor resolves before any runner exists.")

    # ------------------------------------------------------------ Part 6
    print("\n--- Part 6: THE UNOPENED LEDGER precondition + the closers ---")
    # THE INVOICE PLANT is declined at the DOCUMENT level: an
    # invoice-shaped transactional record ingested and human-approved
    # AS A DOCUMENT must still never become an exposure INPUT (WS2's
    # runner declines it, naming [OE]). The precondition here is
    # separability - the plant carries transactional-truth markers, and
    # the manifest's SETTLED-ACCOUNT vocabulary appears in ZERO approved
    # exposure facts, so the WS2 sweep will have real teeth.
    settled = re.findall(r'^  - "([^"]+)"',
                         manifest.split("forbidden_vocabulary:")[1]
                         .split("forbidden_inputs:")[0], re.MULTILINE)
    assert settled, "the manifest must declare THE SETTLED ACCOUNT vocabulary"
    plant_raw = norm(read(os.path.join(FINANCE_CORPUS,
                                       "vendor-invoice-4471.md"))).lower()
    assert "invoice number: inv-4471" in plant_raw
    assert any(p in plant_raw for p in
               ("was paid", "payment cleared", "invoice was issued")), \
        "THE INVOICE PLANT must carry transactional-truth markers"
    # The plant document IS ingested (the runner will see it and decline).
    plant_doc = session.query(db.Document).filter(
        db.Document.project_id == project.id,
        db.Document.filename == "vendor-invoice-4471.md").first()
    assert plant_doc is not None, "the plant must be an ingested document"
    # BYTE-LEVEL SEPARABILITY: no approved exposure fact asserts
    # transactional truth (the SETTLED-ACCOUNT vocabulary is absent from
    # every governed fact - the legitimate penalty clause says "not paid
    # by its due date", a conditional term, never "was paid").
    for aid, c in facts:
        low = c.lower()
        for phrase in settled:
            assert phrase.lower() not in low, \
                f"asset {aid} carries SETTLED-ACCOUNT vocabulary {phrase!r}"

    # No transactional door exists: the manifest doors block lists only
    # the three governed doors, and no skill's allowed_inputs names a
    # transactional/operational record (ERP/invoice/PO/payment/ledger
    # appear ONLY in forbidden_inputs / forbidden_vocabulary).
    txn = ("erp", "invoice", "payment", "ledger", "purchase order",
           " po ", "bank")
    doors_block = manifest.split("doors:\n")[1].split("skills:")[0].lower()
    assert not any(term in doors_block for term in txn), \
        f"a transactional term leaked into the doors block: {doors_block}"
    for s in ACTIVE_FIVE:
        txt = read(os.path.join(SKILLS_DIR, s + ".yaml"))
        allowed = txt.split("allowed_inputs:")[1].split(
            "forbidden_inputs:")[0].lower()
        assert not any(term in allowed for term in txn), \
            f"{s}: a transactional term leaked into allowed_inputs"

    # The two cross-workbench consolidations resolve (basename discipline).
    for draft, target in (("extract_payment_terms", "extract_contract_clauses"),
                          ("detect_outdated_finance_policies",
                           "identify_outdated_policies")):
        d = read(os.path.join(DRAFTS_DIR, "02_finance_cost_leakage",
                              draft + ".yaml"))
        assert "status: CONSOLIDATED" in d
        ci = re.search(r"^consolidated_into: (\S+)", d, re.MULTILINE).group(1)
        rp = re.search(r"^ratified_path: (\S+)", d, re.MULTILINE).group(1)
        assert ci == target
        assert os.path.isfile(os.path.join(REPO_ROOT, rp))
        assert os.path.basename(rp) == target + ".yaml"

    # Global sweep at 34/58 (the promotion landed).
    active = consolidated = 0
    for folder, _dirs, files in os.walk(DRAFTS_DIR):
        for name in files:
            if not name.endswith(".yaml"):
                continue
            st = re.search(r"^status: (\S+)",
                           read(os.path.join(folder, name)), re.MULTILINE)
            if st and st.group(1) == "ACTIVE":
                active += 1
            elif st and st.group(1) == "CONSOLIDATED":
                consolidated += 1
    assert (active, consolidated) == (34, 58), \
        f"global sweep must be 34/58, got {active}/{consolidated}"

    # Zero stewardship; D24 byte-exact.
    assert session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "STEWARDSHIP_DECISION").count() == 0
    inspector = inspect(db.engine)
    tables = [t for t in inspector.get_table_names() if t != "alembic_version"]
    columns = sum(len(inspector.get_columns(t)) for t in tables)
    assert (len(tables), columns) == (28, 305), \
        f"D24 must hold at 28/305, got {len(tables)}/{columns}"
    print("Part 6 passed: THE INVOICE PLANT is an approved document but "
          "distinguishable by its SETTLED-ACCOUNT markers (no contract "
          "clause carries them); no transactional door exists; both "
          "cross-workbench consolidations resolve; global sweep 34/58; "
          "zero stewardship; D24 at exactly 28 tables / 305 columns.")

    session.close()
    print("\nAll v2.3 WS1 preconditions passed: the ratified contracts and "
          "the corpora (procurement + the ratified corpus_finance/ plants) "
          "carry every cost-exposure, policy-comparison, harvest-anchor, "
          "and unopened-ledger precondition - document-governed, before any "
          "runner exists. NO INVENTED MONEY, NO SETTLED ACCOUNT, no [OE].")


if __name__ == "__main__":
    main()
