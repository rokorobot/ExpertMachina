"""v2.4 WS1 gate suite — THE PRECONDITION PROOF (the 87th suite).

Proves the WS0-ratified v2.4 preconditions against the ratified
contracts and the REAL corpora BEFORE any runner exists
(docs/customer-success-intelligence-v2.4.md — Customer Success
Intelligence, catalog #6, the per-customer axis; the ratified name
drops "Retention"):

  1. THE BUNDLE SHAPE — the manifest + the five ratified contracts
     agree; every binding convention is declared in the bytes; NO
     runner exists yet, NO UI, NO operational customer-data door; the
     forbidden-input classes are named; THE HEALTH-SCORE PLANT, THE
     BASELINE DOCTRINE, THE IMPUTED HEALTH, THE HEALTH-SENTENCE
     DISTINCTION, and the five named proofs are recorded (WS0 doc +
     registry #6 promotion + the user-ratified corpus stop).
  2. The corpora through the real pipeline — the 12-document
     customer-operations corpus + the 4-document
     corpus_customer_success/ extension, two connectors, one project,
     every candidate human-approved.
  3. THE DEVIATION MATERIAL REPORT — the contract's OWN declared
     baseline marker, axes, and value patterns (parsed from the
     ratified bytes) fire on approved facts: the standard-terms
     baseline exists and self-identifies; Acme Industrial DEVIATES on
     both declared axes (weekly/two business days vs monthly/five;
     sixty vs ninety days); Northwind Logistics CONFORMS on both -
     the silence half of THE CUSTOM TERMS PROOF is provable on the
     bytes.
  4. THE COVERAGE + WINDOW preconditions — the QBR promise exists
     governed (brochure + the Acme agreement) with NO covering QBR
     procedure anywhere (the qbr_procedure gap is real); the
     escalation obligation HAS covering material (the covered case
     will stay silent); the Acme renewal anchor co-locates its date
     and notice period in ONE fact, and the declared arithmetic
     (2026-09-30 - 60 days = 2026-08-01) lands inside the declared
     window while Northwind's (2027-03-31 - 90 days) lands outside.
  5. THE THIRD HARVEST precondition — the dated renewal clause is an
     approved fact citable BY governed asset id, and the v2.1
     register taxonomy carries the classes v2.4 will harvest
     (renewal / sla / notification_obligation / reporting_obligation).
  6. THE UNREAD CUSTOMER precondition + the closers — the manifest's
     IMPUTED-HEALTH vocabulary appears in the approved facts of
     EXACTLY ONE document (THE HEALTH-SCORE PLANT), so the WS2 quote-
     frame sweep will have real teeth; no operational customer-data
     door exists in any contract byte; the two cross-workbench
     consolidations resolve; the [ES] draft is SEQUENCED with the
     read-only condition on its bytes; the six Future-[OE] drafts
     stay FUTURE; global sweep at 39/73; zero stewardship; D24 at
     exactly 28 tables / 305 columns.

No [OE] operational fact, no [PMD] ingress, no route, no table, no
tool, no guard, and no law is needed anywhere in this suite - the
preconditions hold on governed document facts alone. NO runner is
built.
"""
import datetime
import os
import re
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_cs_pkg_")

from sqlalchemy import create_engine, inspect  # noqa: E402
from sqlalchemy.orm import sessionmaker        # noqa: E402
from app import database as db                 # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_cs_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'corpus.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                      # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_cs_qdrant_")

from app import schemas, crud, connectors, tier2  # noqa: E402
import test_support                            # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WB_DIR = os.path.join(REPO_ROOT, "workbench", "customer_success_intelligence")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
CS_CORPUS = os.path.join(WB_DIR, "corpus_customer_success")
CUSOPS_CORPUS = os.path.join(REPO_ROOT, "workbench",
                             "customer_operations", "corpus")
CI_SKILLS = os.path.join(REPO_ROOT, "workbench", "contract_intelligence",
                         "skills")
DRAFTS_DIR = os.path.join(REPO_ROOT, "docs", "skill-contracts")
CS_DRAFTS = os.path.join(DRAFTS_DIR, "06_customer_success_retention")
WS0_DOC = os.path.join(REPO_ROOT, "docs",
                       "customer-success-intelligence-v2.4.md")
REGISTRY_DOC = os.path.join(REPO_ROOT, "docs", "workbench-skill-registry.md")

ACTIVE_FIVE = ("detect_customer_term_deviation",
               "detect_customer_renewal_obligations",
               "detect_customer_coverage_gap",
               "detect_unbacked_customer_health_assumption",
               "prepare_customer_success_review_brief")

# The global registry sweep - moves with each promotion: 34/58 at
# v2.3, +5 ACTIVE / +15 CONSOLIDATED at the v2.4 promotion.
GLOBAL_SWEEP = (39, 73)

# The declared run parameters the proofs use (CORPUS.md seeding notes).
AS_OF = datetime.date(2026, 7, 10)
WINDOW_DAYS = 90
PLANT_DOC = "acme-account-plan.md"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def norm(t):
    return " ".join((t or "").split())


def parse_nested_marker_map(text, map_key):
    """Read `map_key:` (a nested map of `key: ["m", ...]` entries, values
    may wrap across lines) inside a convention block - returns
    {key: [markers]}. The v2.3 parser, unchanged."""
    lines = text.splitlines()
    out, in_map, cur_key, buf = {}, False, None, ""
    for line in lines:
        s = line.strip()
        if s.startswith(f"{map_key}:"):
            in_map = True
            continue
        if not in_map:
            continue
        if cur_key is not None:
            buf += " " + s
            if "]" in buf:
                out[cur_key] = re.findall(r'"([^"]+)"', buf)
                cur_key, buf = None, ""
            continue
        m = re.match(r"^([a-z_]+):\s*\[(.*)$", s)
        if m:
            cur_key, buf = m.group(1), m.group(2)
            if "]" in buf:
                out[cur_key] = re.findall(r'"([^"]+)"', buf)
                cur_key, buf = None, ""
            continue
        if s and not s.startswith("#"):
            break
    return out


def parse_flat_list(text, key):
    """Read `key: ["a", "b", ...]` (possibly wrapped across lines)."""
    seg = text.split(f"{key}:")[1]
    buf = ""
    for line in seg.splitlines():
        buf += " " + line.strip()
        if "]" in buf:
            break
    return re.findall(r'"([^"]+)"', buf)


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


def axis_values(content, patterns):
    """The declared value patterns over a fact's bytes - verbatim,
    never normalized."""
    found = set()
    low = content.lower()
    for pat in patterns:
        for m in re.finditer(pat, low):
            found.add(m.group(0))
    return found


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
    assert "canonical_number: 6" in manifest
    assert "workbench: customer_success_intelligence" in manifest
    assert "Retention" not in manifest.split("\n")[0], \
        "the ratified name drops Retention"

    # The bundle carries ONLY the runner - never an operational
    # connector, CRM/usage/ticket/NPS/telemetry/health-score reader, or
    # UI module. (At WS1 this set is empty; WS2 adds runner.py. The
    # DURABLE precondition - the one this permanent suite guards
    # forever - is that no operational-reader module ever appears.)
    py_files = set(f for f in os.listdir(WB_DIR) if f.endswith(".py"))
    assert py_files <= {"runner.py"}, \
        f"the bundle carries only the runner, never a reader: {py_files}"
    for root, _dirs, files in os.walk(WB_DIR):
        for fname in files:
            assert not fname.endswith((".tsx", ".jsx", ".html", ".css")), \
                f"no UI module may exist in the bundle: {fname}"

    # The binding conventions are declared, not implied. (Prose needles
    # checked against normalized text - YAML wraps prose across lines.)
    dev = read(os.path.join(SKILLS_DIR, "detect_customer_term_deviation.yaml"))
    for needle in ("baseline_markers", "deviation_axes",
                   "axis_value_patterns", "comparability_rule"):
        assert needle in dev, f"detect_customer_term_deviation missing {needle}"
    for needle in ("no standard baseline, no deviation diagnosis",
                   "THE IMPUTED HEALTH"):
        assert needle in norm(dev), \
            f"detect_customer_term_deviation missing {needle}"
    ren = read(os.path.join(SKILLS_DIR,
                            "detect_customer_renewal_obligations.yaml"))
    for needle in ("the_third_harvest", "window_rule", "obligation_markers"):
        assert needle in ren, \
            f"detect_customer_renewal_obligations missing {needle}"
    assert "THE INVENTED DATE" in norm(ren)
    cov = read(os.path.join(SKILLS_DIR, "detect_customer_coverage_gap.yaml"))
    for needle in ("coverage_classes", "obligation_markers",
                   "REFUSAL_BACKED", "coverage_rule"):
        assert needle in cov, f"detect_customer_coverage_gap missing {needle}"
    asm = read(os.path.join(SKILLS_DIR,
                            "detect_unbacked_customer_health_assumption.yaml"))
    for needle in ("assumption_markers", "the_quote_frame"):
        assert needle in asm, \
            f"detect_unbacked_customer_health_assumption missing {needle}"
    for needle in ("TRUE or FALSE", "THE IMPUTED HEALTH"):
        assert needle in norm(asm), \
            f"detect_unbacked_customer_health_assumption missing {needle}"
    brief = read(os.path.join(SKILLS_DIR,
                              "prepare_customer_success_review_brief.yaml"))
    assert "[assist, synth]" in brief and "brief_sections" in brief \
        and "NEVER written to /08_proposals" in norm(brief)

    # The forbidden-input classes + the doctrines + the plant declared.
    for needle in ("forbidden_inputs", "the_baseline_doctrine",
                   "the_health_sentence_distinction", "the_unread_customer",
                   "forbidden_vocabulary"):
        assert needle in manifest, f"manifest missing {needle}"
    for needle in ("usage and activity records", "THE HEALTH-SCORE PLANT",
                   "OWNER_ASSIGNED"):
        assert needle in norm(manifest), f"manifest missing {needle}"

    # The WS0 doc records the doctrine + the five named proofs; the
    # registry is promoted; the corpus stop was user-ratified.
    ws0 = norm(read(WS0_DOC))
    for needle in ("THE IMPUTED HEALTH", "THE HEALTH-SENTENCE DISTINCTION",
                   "no standard baseline, no deviation diagnosis",
                   "THE CUSTOM TERMS PROOF", "THE UNREAD CUSTOMER",
                   "THE THIRD HARVEST", "THE COMPUTED RENEWAL WINDOW",
                   "THE IMPUTED HEALTH SWEEP", "THE HEALTH-SCORE PLANT"):
        assert needle in ws0, f"WS0 doc missing {needle}"
    registry = read(REGISTRY_DOC)
    assert "## 6. Customer Success Intelligence Workbench — ACTIVE (v2.4)" \
        in registry, "registry #6 not promoted"
    assert "SEQUENCED/[ES]" in registry
    corpus_map = read(os.path.join(WB_DIR, "CORPUS.md"))
    assert "REUSE-FIRST" in corpus_map and "user-ratified" in corpus_map, \
        "the corpus stop must be recorded as reuse-first and user-ratified"
    print("Part 1 passed: manifest + 5 ratified contracts agree; every "
          "binding convention declared; NO runner, NO UI, NO operational "
          "door yet; the doctrines, the plant, the proofs, the promotion, "
          "and the ratified corpus stop are all recorded on the bytes.")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: the corpora through the real pipeline ---")
    officer = test_support.governed_actor(session, "cs_officer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Customer Success Corpus", description="v2.4 WS1 precondition proof",
        customer_id=customer.id), actor=officer)
    for name, root in (("Customer Operations Corpus", CUSOPS_CORPUS),
                       ("Customer Success Extension Corpus", CS_CORPUS)):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
    doc_count = session.query(db.Document).filter_by(
        project_id=project.id).count()
    assert doc_count == 16, \
        f"expected 12 customer-ops + 4 customer-success docs, got {doc_count}"
    reviewer = test_support.governed_actor(session, "cs_reviewer")
    approve_all(session, project.id, reviewer, "WS1 cs corpus approval")
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    assert approved and all(a.source_class == "PRIMARY" for a in approved)
    doc_by_id = {d.id: d.filename for d in session.query(db.Document)
                 .filter_by(project_id=project.id).all()}
    facts = [(a.id, norm(a.content), doc_by_id.get(a.document_id, ""))
             for a in approved]
    print(f"Part 2 passed: 16 documents -> {len(approved)} approved PRIMARY "
          f"facts through the real pipeline.")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE DEVIATION MATERIAL REPORT (declared markers "
          "over real facts) ---")
    baseline_markers = parse_nested_marker_map(dev, "baseline_markers")
    axes = parse_nested_marker_map(dev, "deviation_axes")
    value_patterns = parse_nested_marker_map(dev, "axis_value_patterns")
    assert set(axes) == {"reporting_cadence", "renewal_notice"}, axes
    std_marker = baseline_markers["standard_terms"][0]
    assert std_marker == "standard terms"

    def side(fact_filter):
        """{axis: set-of-verbatim-values} for the facts a filter selects."""
        out = {}
        for axis, markers in axes.items():
            vals = set()
            for _aid, c, fn in facts:
                low = c.lower()
                if not fact_filter(low, fn):
                    continue
                if any(mk in low for mk in markers):
                    vals |= axis_values(c, value_patterns[axis])
            out[axis] = vals
        return out

    baseline = side(lambda low, fn: std_marker in low)
    acme = side(lambda low, fn: "acme industrial" in low)
    north = side(lambda low, fn: "northwind logistics" in low)
    for axis in axes:
        assert baseline[axis], f"no baseline fact states the {axis} axis"
        assert acme[axis], f"no Acme fact states the {axis} axis"
        assert north[axis], f"no Northwind fact states the {axis} axis"
        # THE CUSTOM TERMS PROOF precondition, on the bytes: Acme's
        # verbatim values DIFFER from the baseline; Northwind's are
        # IDENTICAL (its silence will be provable, not accidental).
        assert acme[axis] != baseline[axis], \
            f"Acme must DEVIATE on {axis}: {acme[axis]} vs {baseline[axis]}"
        assert north[axis] == baseline[axis], \
            f"Northwind must CONFORM on {axis}: {north[axis]} vs {baseline[axis]}"
    assert "weekly" in {v for v in acme["reporting_cadence"]}
    assert "sixty days" in acme["renewal_notice"]
    assert "ninety days" in north["renewal_notice"]
    print(f"Part 3 passed: the baseline self-identifies ({std_marker!r}); "
          f"Acme deviates on both axes ({sorted(acme['reporting_cadence'])} vs "
          f"{sorted(baseline['reporting_cadence'])}; {sorted(acme['renewal_notice'])} "
          f"vs {sorted(baseline['renewal_notice'])}); Northwind conforms on both.")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: THE COVERAGE + WINDOW preconditions ---")
    cov_markers = parse_nested_marker_map(cov, "obligation_markers")
    qbr_marker = cov_markers["qbr_procedure"][0]
    qbr_facts = [(aid, c, fn) for aid, c, fn in facts
                 if qbr_marker in c.lower()]
    assert len(qbr_facts) >= 2, \
        "the QBR promise must exist governed (brochure + Acme agreement)"
    assert {fn for _a, _c, fn in qbr_facts} >= {
        "sales-enterprise-brochure.md", "acme-service-agreement.md"}
    # NO covering QBR procedure exists anywhere - not as a document, not
    # as a procedural fact (the promise facts themselves are promises).
    assert not any("qbr" in fn.lower() for fn in doc_by_id.values()), \
        "no QBR procedure document may exist (the gap must be real)"
    assert not any(qbr_marker in c.lower() and "procedure" in c.lower()
                   for _a, c, _f in facts), \
        "no fact may describe a QBR procedure (the gap must be real)"
    # The COVERED contrast: escalation obligations exist AND the
    # covering procedure exists (the covered case will stay silent).
    esc_marker = cov_markers["escalation"][0]
    esc_obligations = [aid for aid, c, fn in facts
                       if esc_marker in c.lower()
                       and fn != "support-escalation-procedure.md"]
    esc_coverage = [aid for aid, c, fn in facts
                    if fn == "support-escalation-procedure.md"]
    assert esc_obligations and esc_coverage, \
        "the covered side needs both the obligation and the coverage"

    # THE COMPUTED RENEWAL WINDOW precondition: date + notice period
    # co-located in ONE fact (the v2.3 co-location lesson), and the
    # declared arithmetic lands in-window for Acme, out-of-window for
    # Northwind, at the declared clock.
    acme_anchor = [(aid, c) for aid, c, fn in facts
                   if "2026-09-30" in c and "sixty days" in c.lower()]
    assert acme_anchor, \
        "the Acme anchor must co-locate its date and notice period"
    north_anchor = [(aid, c) for aid, c, fn in facts
                    if "2027-03-31" in c and "ninety days" in c.lower()]
    assert north_anchor, \
        "the Northwind anchor must co-locate its date and notice period"
    acme_due = datetime.date(2026, 9, 30) - datetime.timedelta(days=60)
    north_due = datetime.date(2027, 3, 31) - datetime.timedelta(days=90)
    in_window = lambda d: AS_OF <= d <= AS_OF + datetime.timedelta(  # noqa: E731
        days=WINDOW_DAYS)
    assert acme_due == datetime.date(2026, 8, 1) and in_window(acme_due), \
        "2026-09-30 - 60 days = 2026-08-01 must land inside the window"
    assert not in_window(north_due), \
        "Northwind's notice date must land outside the declared window"
    print(f"Part 4 passed: the QBR gap is real ({len(qbr_facts)} promise "
          f"facts, zero coverage); the escalation obligation is covered "
          f"({len(esc_obligations)} obligation(s), {len(esc_coverage)} "
          f"coverage fact(s)); the declared arithmetic lands "
          f"{acme_due} IN-window (Acme) and {north_due} OUT (Northwind).")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: THE THIRD HARVEST precondition (register anchor "
          "citable BY ID) ---")
    dated = [(aid, c) for aid, c, fn in facts
             if re.search(r"\d{4}-\d{2}-\d{2}", c)
             and ("renew" in c.lower() or "notice" in c.lower())]
    assert dated, "a dated renewal/notice clause must be approved"
    anchor_id, anchor_c = dated[0]
    assert isinstance(anchor_id, int) and anchor_id > 0
    ci_text = read(os.path.join(CI_SKILLS, "extract_contract_clauses.yaml"))
    taxonomy = ci_text.split("clause_class_taxonomy:")[1]
    for cls in ("renewal", "sla", "notification_obligation",
                "reporting_obligation"):
        assert f"- {cls}:" in taxonomy or f"{cls}," in taxonomy \
            or f"{cls}]" in taxonomy, \
            f"the v2.1 register taxonomy must carry the {cls} class"
    print(f"Part 5 passed: asset #{anchor_id} is a dated register-class "
          f"clause citable BY id; the v2.1 taxonomy classifies every class "
          f"v2.4 harvests - the anchor resolves before any runner exists.")

    # ------------------------------------------------------------ Part 6
    print("\n--- Part 6: THE UNREAD CUSTOMER precondition + the closers ---")
    # THE IMPUTED HEALTH separability: the manifest's forbidden
    # vocabulary appears in approved facts of EXACTLY ONE document -
    # THE HEALTH-SCORE PLANT - so the WS2 quote-frame sweep has real
    # teeth: anything else that writes such a phrase wrote it itself.
    vocab = re.findall(r'^  - "([^"]+)"',
                       manifest.split("forbidden_vocabulary:")[1]
                       .split("forbidden_inputs:")[0], re.MULTILINE)
    assert len(vocab) >= 12, "the manifest must declare the sweep vocabulary"
    carriers = {}
    for aid, c, fn in facts:
        low = c.lower()
        for phrase in vocab:
            if phrase.lower() in low:
                carriers.setdefault(fn, set()).add(phrase)
    assert set(carriers) == {PLANT_DOC}, \
        f"forbidden vocabulary must trace to the plant ONLY: {carriers}"
    plant_hits = carriers[PLANT_DOC]
    for phrase in ("is healthy", "churn risk", "customer is satisfied",
                   "health score", "likely to renew"):
        assert phrase in plant_hits, f"the plant must carry {phrase!r}"
    # The plant document IS ingested (WS2's runner will see it and may
    # surface it ONLY inside the quote frame).
    assert PLANT_DOC in doc_by_id.values()
    # The assumption skill's declared markers fire on the plant facts.
    asm_markers = parse_flat_list(asm, "assumption_markers")
    plant_facts = [c for _a, c, fn in facts if fn == PLANT_DOC]
    fired = [mk for mk in asm_markers
             if any(mk in c.lower() for c in plant_facts)]
    assert len(fired) >= 4, f"assumption markers must fire on the plant: {fired}"

    # No operational customer-data door exists: the manifest doors list
    # only the three governed doors, and no contract's allowed_inputs
    # names an operational record (CRM/usage/ticket/NPS/telemetry
    # appear ONLY in forbidden_inputs / forbidden_vocabulary).
    txn = ("crm", "nps", "ticket", "usage", "telemetry", "activity feed",
           "health-score", "health score")
    doors_block = manifest.split("doors:\n")[1].split("skills:")[0].lower()
    assert not any(term in doors_block for term in txn), \
        f"an operational term leaked into the doors block: {doors_block}"
    for s in ACTIVE_FIVE:
        txt = read(os.path.join(SKILLS_DIR, s + ".yaml"))
        allowed = txt.split("allowed_inputs:")[1].split(
            "forbidden_inputs:")[0].lower()
        assert not any(term in allowed for term in txn), \
            f"{s}: an operational term leaked into allowed_inputs"

    # The two cross-workbench consolidations resolve (basename
    # discipline); the [ES] draft is SEQUENCED with the read-only
    # condition on its bytes; the six Future-[OE] drafts stay FUTURE.
    for draft, target in (
            ("extract_customer_communication_obligations",
             "extract_contract_clauses"),
            ("detect_outdated_cs_documentation", "identify_outdated_policies")):
        d = read(os.path.join(CS_DRAFTS, draft + ".yaml"))
        assert "status: CONSOLIDATED" in d
        ci = re.search(r"^consolidated_into: (\S+)", d, re.MULTILINE).group(1)
        rp = re.search(r"^ratified_path: (\S+)", d, re.MULTILINE).group(1)
        assert ci == target
        assert os.path.isfile(os.path.join(REPO_ROOT, rp))
        assert os.path.basename(rp) == target + ".yaml"
    es = read(os.path.join(CS_DRAFTS,
                           "detect_customer_obligations_without_owner.yaml"))
    assert "status: SEQUENCED" in es and "read-only" in es \
        and "OWNER_ASSIGNED" in es, \
        "the [ES] draft must be SEQUENCED with the read-only condition"
    for oe in ("detect_declining_activity", "detect_low_usage",
               "detect_unresolved_customer_issues", "score_customer_risk",
               "cluster_recurring_complaints", "identify_churn_signals"):
        assert "status: FUTURE" in read(os.path.join(CS_DRAFTS, oe + ".yaml")), \
            f"{oe} must stay FUTURE ([OE] is unminted)"

    # Global sweep at the ratified totals (the promotion landed).
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
    assert (active, consolidated) == GLOBAL_SWEEP, \
        f"global sweep must be {GLOBAL_SWEEP}, got {active}/{consolidated}"

    # Zero stewardship; D24 byte-exact.
    assert session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "STEWARDSHIP_DECISION").count() == 0
    inspector = inspect(db.engine)
    tables = [t for t in inspector.get_table_names() if t != "alembic_version"]
    columns = sum(len(inspector.get_columns(t)) for t in tables)
    assert (len(tables), columns) == (28, 305), \
        f"D24 must hold at 28/305, got {len(tables)}/{columns}"
    print(f"Part 6 passed: THE HEALTH-SCORE PLANT is the ONLY document "
          f"whose facts carry the IMPUTED-HEALTH vocabulary "
          f"({sorted(plant_hits)}); {len(fired)} assumption markers fire on "
          f"it; no operational door exists; both cross-workbench "
          f"consolidations resolve; the [ES] draft holds its read-only "
          f"condition; the six [OE] drafts stay FUTURE; global sweep "
          f"{GLOBAL_SWEEP[0]}/{GLOBAL_SWEEP[1]}; zero stewardship; D24 at "
          f"exactly 28 tables / 305 columns.")

    session.close()
    print("\nAll v2.4 WS1 preconditions passed: the ratified contracts and "
          "the corpora (customer-operations + the ratified "
          "corpus_customer_success/ plants) carry every deviation, "
          "coverage, window, harvest-anchor, and unread-customer "
          "precondition - document-governed, before any runner exists. "
          "No standard baseline, no deviation diagnosis; THE IMPUTED "
          "HEALTH refused; no [OE].")


if __name__ == "__main__":
    main()
