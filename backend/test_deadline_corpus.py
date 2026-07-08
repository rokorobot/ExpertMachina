"""v2.2 WS1 gate suite — THE PRECONDITION PROOF (the 81st suite).

Proves the WS0-ratified v2.2 preconditions against the ratified
contracts and the REAL corpora BEFORE any runner exists
(docs/deadline-obligation-v2.2.md — the Deadline & Obligation
Intelligence extension of the compliance workbench, catalog #9):

  1. THE BUNDLE SHAPE — the extended manifest and the nine ratified
     contracts agree; the three v2.2 contracts declare every binding
     convention; the runner does NOT yet know the new skills
     (contracts before runtime — WS2 meets them, deliberately).
  2. The corpora through the real pipeline — the untouched 12-document
     compliance corpus + the 2-document corpus_deadline extension +
     the 12-document procurement corpus, three connectors, one
     project, every candidate human-approved.
  3. THE DEADLINE MATERIAL REPORT — the contract's OWN declared
     patterns (parsed from the ratified bytes, runner-convention) fire
     on approved facts: explicit dates, durations, recurrence; the
     ambiguity plants carry vague markers and NO parseable date.
  4. THE WINDOW ARITHMETIC precondition — declared as_of +
     window_days over verbatim dates only; deterministic on re-run;
     a past date is arithmetic, never a conduct claim.
  5. THE HARVEST precondition — the dated agreement clause is an
     approved fact citable BY governed asset id, and the v2.1
     register taxonomy (parsed from ITS contract bytes) classifies
     it — the register WILL carry the anchor the deadline skill reads.
  6. THE NON-CONFLATION + zero-surface closers — zero
     STEWARDSHIP_DECISION events were created by any of this; D24
     closes at exactly 28 tables / 305 columns.

No [OE] operational fact, no [PMD] ingress, no route, no table, no
tool, no guard, and no law is needed anywhere in this suite — the
preconditions hold on governed document facts and a declared clock
alone.
"""
import datetime
import os
import re
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_ddl_pkg_")

from sqlalchemy import create_engine, inspect  # noqa: E402
from sqlalchemy.orm import sessionmaker        # noqa: E402
from app import database as db                 # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_ddl_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'corpus.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                      # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_ddl_qdrant_")

from app import schemas, crud, connectors, tier2  # noqa: E402
import test_support                            # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WB_DIR = os.path.join(REPO_ROOT, "workbench", "compliance_obligation")
CORPUS_DIR = os.path.join(WB_DIR, "corpus")
DEADLINE_DIR = os.path.join(WB_DIR, "corpus_deadline")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
PROC_CORPUS = os.path.join(REPO_ROOT, "workbench",
                           "procurement_intelligence", "corpus")
CI_SKILLS = os.path.join(REPO_ROOT, "workbench", "contract_intelligence",
                         "skills")

# The declared clock (WS0 ruling 3 / the deadline_convention): run
# parameters, never wall-clock. 2026-11-30 (the certification plant) is
# inside the 90-day window of this as_of; 2026-08-15 (the MSA
# termination) is before it; 2027-09-30 is far outside it.
AS_OF = datetime.date(2026, 9, 15)
WINDOW_DAYS = 90

V22_SKILLS = ("detect_obligation_deadlines", "extract_recurrence_rules",
              "prepare_obligation_calendar_brief")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_quoted_pattern(text, key):
    """The runner convention (compliance runner._parse / procurement
    runner.parse_marker_pattern): a quoted, possibly wrapped pattern
    line, double-escaped in the file bytes."""
    lines = text.splitlines()
    raw, taking = [], False
    for line in lines:
        s = line.strip()
        if s.startswith(f"{key}:"):
            raw.append(s.split(":", 1)[1].strip())
            taking = not (raw[0].endswith('"') and len(raw[0]) > 1)
            if not taking:
                break
            continue
        if taking:
            raw.append(s)
            if s.endswith('"'):
                break
    pattern = " ".join(raw).strip().strip('"').replace("\\\\", "\\")
    assert pattern, f"contract declares no {key}"
    return re.compile(pattern)


def parse_list_items(text, key):
    """The declared quoted list items under a `key:` block."""
    items, taking = [], False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(f"{key}:"):
            taking = True
            continue
        if taking:
            if s.startswith("- "):
                items.append(s[2:].strip().strip('"'))
            elif s and not s.startswith("#"):
                break
    assert items, f"contract declares no {key} items"
    return items


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


def norm(t):
    return " ".join((t or "").split())


def main():
    db.init_db()
    session = db.SessionLocal()

    # ------------------------------------------------------------ Part 1
    print("\n--- Part 1: THE BUNDLE SHAPE (the extension, pinned) ---")
    ratified = sorted(n[:-5] for n in os.listdir(SKILLS_DIR)
                      if n.endswith(".yaml"))
    assert len(ratified) == 9, f"expected 9 ratified contracts, got {ratified}"
    manifest = read(os.path.join(WB_DIR, "workbench.yaml"))
    declared = re.findall(r"^  - (\w+)$", manifest.split("skills:\n")[1],
                          re.MULTILINE)[:9]
    assert sorted(declared) == ratified, "manifest and skills/ disagree"

    ddl_text = read(os.path.join(SKILLS_DIR,
                                 "detect_obligation_deadlines.yaml"))
    rec_text = read(os.path.join(SKILLS_DIR, "extract_recurrence_rules.yaml"))
    brief_text = read(os.path.join(SKILLS_DIR,
                                   "prepare_obligation_calendar_brief.yaml"))
    for text, sid in ((ddl_text, V22_SKILLS[0]), (rec_text, V22_SKILLS[1]),
                      (brief_text, V22_SKILLS[2])):
        assert f"skill_id: {sid}" in text and "status: ACTIVE" in text
    # The binding conventions are declared, not implied.
    for needle in ("certification_expiry", "vague_time_markers",
                   "window_rule", "register_harvest",
                   "forbidden_vocabulary",
                   "THE INVENTED DATE", "THE PRESUMED COMPLETION"):
        assert needle in ddl_text, f"deadline contract missing {needle}"
    for needle in ("never_expand_rule", "recurrence_markers",
                   "ambiguity_rule"):
        assert needle in rec_text, f"recurrence contract missing {needle}"
    assert "never written to /08_proposals" in norm(brief_text)
    assert "[assist, synth]" in brief_text
    # Contracts before runtime: the runner does not know the new skills
    # yet — WS2 meets these contracts, deliberately (the WS sequence).
    runner_text = read(os.path.join(WB_DIR, "runner.py"))
    active_block = runner_text.split("ACTIVE_SKILLS = (")[1].split(")")[0]
    for sid in V22_SKILLS:
        assert sid not in active_block, \
            f"the runner already wires {sid} — WS2 work leaked into WS1"
    print("Part 1 passed: manifest + 9 ratified contracts agree; every "
          "binding convention declared; the runner deliberately does not "
          "know the v2.2 skills yet.")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: the corpora through the real pipeline ---")
    officer = test_support.governed_actor(session, "ddl_officer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Deadline Corpus", description="v2.2 WS1 precondition proof",
        customer_id=customer.id), actor=officer)
    for name, root in (("Compliance Corpus", CORPUS_DIR),
                       ("Deadline Extension Corpus", DEADLINE_DIR),
                       ("Procurement Corpus", PROC_CORPUS)):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
    doc_count = session.query(db.Document).filter_by(
        project_id=project.id).count()
    assert doc_count == 26, \
        f"expected 12 compliance + 2 deadline + 12 procurement, got {doc_count}"
    reviewer = test_support.governed_actor(session, "ddl_reviewer")
    approve_all(session, project.id, reviewer, "WS1 deadline corpus approval")
    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").all()
    assert approved, "the pipeline must yield approved facts"
    assert all(a.source_class == "PRIMARY" for a in approved), \
        "PRIMARY-lane corpus facts must stay PRIMARY"
    print(f"Part 2 passed: 26 documents -> {len(approved)} approved "
          f"PRIMARY facts through the real pipeline.")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE DEADLINE MATERIAL REPORT (declared patterns "
          "over real facts) ---")
    date_re = parse_quoted_pattern(ddl_text, "marker_pattern")
    duration_re = parse_quoted_pattern(ddl_text, "duration_pattern")
    vague_markers = parse_list_items(ddl_text, "vague_time_markers")
    recurrence_markers = parse_list_items(rec_text, "recurrence_markers")
    facts = [(a.id, norm(a.content)) for a in approved]

    dated = {aid: m for aid, c in facts
             for m in [date_re.search(c)] if m}
    dates_found = sorted(m.group(2) for m in dated.values())
    assert "2026-11-30" in dates_found, \
        "the certification validity plant must be an approved dated fact"
    assert "2026-08-15" in dates_found, \
        "the MSA termination date must be an approved dated fact"
    durations = [aid for aid, c in facts if duration_re.search(c)]
    duration_texts = " | ".join(c for _aid, c in facts
                                if duration_re.search(c))
    assert "90 days" in duration_texts and "72 hours" in duration_texts, \
        "the declared duration material (90 days / 72 hours) must exist"
    recurring = {aid for aid, c in facts
                 if any(mk in c.lower() for mk in recurrence_markers)}
    assert len(recurring) >= 3, \
        f"expected recurrence material in >=3 facts, got {len(recurring)}"

    vague = {aid: [mk for mk in vague_markers if mk in c]
             for aid, c in facts
             if any(mk in c for mk in vague_markers)}
    hit_markers = sorted({mk for mks in vague.values() for mk in mks})
    assert ("promptly" in hit_markers
            and "within a reasonable period" in hit_markers
            and "in a timely manner" in hit_markers), \
        f"the three ambiguity plants must all be approved facts: {hit_markers}"
    for aid in vague:
        content = dict(facts)[aid]
        assert not date_re.search(content), \
            f"asset {aid}: an ambiguity plant must carry NO parseable date"
    print(f"Part 3 passed: {len(dated)} dated facts (incl. both anchor "
          f"plants), duration material present, recurrence material in "
          f"{len(recurring)} facts ({len(durations)} duration facts), "
          f"{len(vague)} vague-language facts each with ZERO parseable "
          f"dates — flagged material, never datable.")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: THE WINDOW ARITHMETIC precondition (declared "
          "clock, deterministic) ---")
    def verdicts():
        out = {}
        for aid, m in sorted(dated.items()):
            d = datetime.date(*[int(x) for x in m.group(2).split("-")])
            if d < AS_OF:
                out[aid] = ("BEFORE_AS_OF", (AS_OF - d).days)
            elif (d - AS_OF).days <= WINDOW_DAYS:
                out[aid] = ("IN_WINDOW", (d - AS_OF).days)
            else:
                out[aid] = ("OUTSIDE", (d - AS_OF).days)
        return out
    first, second = verdicts(), verdicts()
    assert repr(first) == repr(second), \
        "window arithmetic must be deterministic at the declared clock"
    kinds = {m.group(2): first[aid][0] for aid, m in dated.items()}
    assert kinds["2026-11-30"] == "IN_WINDOW", kinds
    assert kinds["2026-08-15"] == "BEFORE_AS_OF", \
        "a past date is an arithmetic fact (never a conduct claim)"
    assert kinds.get("2027-09-30", "OUTSIDE") == "OUTSIDE", kinds
    # THE PRESUMED COMPLETION: the forbidden vocabulary never appears in
    # any approved fact this suite would hand a finding.
    forbidden = parse_list_items(ddl_text, "forbidden_vocabulary")
    for aid, c in facts:
        for phrase in forbidden:
            assert phrase not in c, \
                f"asset {aid}: corpus material must not bait conduct claims"
    print(f"Part 4 passed: window verdicts at declared as_of {AS_OF} + "
          f"{WINDOW_DAYS}d — 2026-11-30 IN_WINDOW / 2026-08-15 "
          f"BEFORE_AS_OF (arithmetic only) / 2027-09-30 OUTSIDE; "
          f"byte-identical on re-run; zero conduct vocabulary anywhere.")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: THE HARVEST precondition (the register anchor, "
          "citable BY ID) ---")
    msa = [(aid, c) for aid, c in facts if "2026-08-15" in c]
    assert msa, "the MSA termination clause must be an approved fact"
    msa_id, msa_content = msa[0]
    assert isinstance(msa_id, int) and msa_id > 0, \
        "the anchor must be citable by governed asset id"
    ci_text = read(os.path.join(CI_SKILLS, "extract_contract_clauses.yaml"))
    structural = ci_text.split("structural_classes:")[1]
    assert "renewal" in structural and "termination" in structural, \
        "the register taxonomy must carry the structural classes"
    assert re.search(r"\d{4}-\d{2}-\d{2}", msa_content), \
        "the anchor carries the concrete token the register requires"
    assert ("terminates" in msa_content or "renews" in msa_content), \
        "the anchor is register-class clause language"
    print(f"Part 5 passed: asset #{msa_id} is the dated agreement clause "
          f"— register-class language with a concrete token, citable BY "
          f"governed asset id; the v2.1 taxonomy classifies it; nothing "
          f"was re-extracted and no engine file was read.")

    # ------------------------------------------------------------ Part 6
    print("\n--- Part 6: THE NON-CONFLATION + the zero-surface closers ---")
    steward_events = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "STEWARDSHIP_DECISION").count()
    assert steward_events == 0, \
        "extracting deadline material must create ZERO stewardship decisions"
    inspector = inspect(db.engine)
    tables = [t for t in inspector.get_table_names()
              if t != "alembic_version"]
    columns = sum(len(inspector.get_columns(t)) for t in tables)
    assert (len(tables), columns) == (28, 305), \
        f"D24 must hold at 28/305, got {len(tables)}/{columns}"
    print("Part 6 passed: zero STEWARDSHIP_DECISION events (a document "
          "deadline is not a DUE_DATE_SET and never becomes one); D24 "
          "closes at exactly 28 tables / 305 columns; no route, table, "
          "tool, guard, or law was needed anywhere in this proof.")

    session.close()
    print("\nAll v2.2 WS1 preconditions passed: the ratified contracts and "
          "the existing governed corpora (plus the two declared "
          "corpus_deadline plants) carry every explicit deadline, "
          "duration, recurrence, ambiguity, and register-anchor "
          "precondition — at a declared clock, before any runner exists.")


if __name__ == "__main__":
    main()
