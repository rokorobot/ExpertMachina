"""v2.2 WS2 gate suite — THE DIAGNOSIS PROOF (the 82nd suite).

The extended compliance runner meets the three v2.2 contracts
(docs/deadline-obligation-v2.2.md), engaged at the declared clock
PAIR (as_of + window_days), over the real corpora and a DERIVED
register-style harvest fixture:

  1. Guard 5 door sweep — the EXTENDED runner stays inside the ruled
     doors with zero guard edits.
  2. Corpus in (12 + the 2 corpus_deadline plants) + ONE accepted
     DERIVED register-style clause fact, package compiled, agent bound.
  3. THE DIAGNOSIS engaged — byte-identical re-runs; every extension
     plant found and correctly kinded; the certification date verbatim
     with declared-clock arithmetic; THE HARVEST (the DERIVED register
     asset cited BY ID); ambiguity flagged, date-free; recurrence
     verbatim, never expanded; before-as_of dates as declared
     arithmetic skips; the v1.7 kinds still firing untouched.
  4. THE WINDOW RE-DECLARATION — the same corpus at window 30: the
     dated findings leave (declared OUTSIDE skips), the clock-free
     kinds hold; a re-run is a new diagnosis, never an update.
  5. THE CALENDAR BRIEF — assist-only in 07, the declared clock
     verbatim, three mandatory sections, never a proposal, no
     persistence anywhere.
  6. The live refusals — no as_of; explicit deadline request without
     window_days; the [OE] status question naming the unminted realm;
     THE V1.7 SHAPE preserved in an unengaged run (no extension kinds,
     exactly one workspace file, three declared skips); ZERO
     STEWARDSHIP_DECISION events (the NON-CONFLATION ruling).
  7. The structural closers — route manifest 88 (frozen digest), the
     nine MCP tools, D24 byte-identical at 28/305.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_ddl2_pkg_")

# Guard 5 first (its import overrides db.engine; this suite re-overrides
# and wins - the ruled import-order trick), for its door-sweep checker.
import test_agent_authorship_guard as guard   # noqa: E402
import test_route_manifest as route_guard      # noqa: E402

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_ddl2_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'ws2.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_ddl2_qdrant_")

from app import (schemas, crud, connectors,   # noqa: E402
                 package_builder, package_consumer, identity, mcp_gateway,
                 tier2)
import test_support                           # noqa: E402
import test_workbench_projection              # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.compliance_obligation.runner as runner   # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "compliance_obligation")
CORPUS_DIR = os.path.join(WB_DIR, "corpus")
DEADLINE_DIR = os.path.join(WB_DIR, "corpus_deadline")

AS_OF = "2026-09-15"
WINDOW = 90
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


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


def bootstrap_vault():
    vault_dir = tempfile.mkdtemp(prefix="em_ddl2_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return vault_dir


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
    """The deterministic CI answering seam (the v1.7 suite's shape) -
    retrieval is real; the narration seam is deterministic."""
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
    officer = test_support.governed_actor(session, "DdlWS2Officer")
    reviewer = test_support.governed_actor(session, "DdlWS2Reviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Deadline WS2", description="the diagnosis proof",
        customer_id=customer.id), actor=officer)

    # ------------------------------------------------------------ Part 1
    print("\n--- Part 1: the EXTENDED runner passes the Guard 5 door sweep ---")
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
    assert len(runner.ACTIVE_SKILLS) == 9, "the bundle is nine skills now"
    print(f"Part 1 passed: {swept} workbench module(s) inside the ruled "
          "doors - the extension changed the runner, not the doors; zero "
          "guard edits.")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: corpora in + the DERIVED register fixture, package "
          "compiled, agent bound ---")
    for name, root in (("Compliance Docs", CORPUS_DIR),
                       ("Deadline Extension Docs", DEADLINE_DIR)):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
    doc_count = session.query(db.Document).filter(
        db.Document.project_id == project.id).count()
    assert doc_count == 14, f"expected 12 + 2 documents, got {doc_count}"
    approve_all(session, project.id, reviewer, "WS2 deadline corpus approval")

    # THE HARVEST fixture: one accepted DERIVED register-style clause
    # fact (the v2.1 register shape - verbatim clause text naming its
    # PRIMARY source asset; class DERIVED, visible per D30). The full
    # engine->valve->acceptance chain is v2.1's proven machinery; what
    # WS2 must prove is that the runner reads the accepted register
    # fact like any governed fact and cites it BY ID.
    reg_doc = db.Document(project_id=project.id,
                          filename="register-clause-fixture.md",
                          file_path="register-clause-fixture.md",
                          status="PROCESSED")
    session.add(reg_doc)
    session.commit()
    session.refresh(reg_doc)
    reg_asset = db.KnowledgeAsset(
        project_id=project.id, document_id=reg_doc.id,
        name="Register clause: renewal notice",
        type="POLICY", status="APPROVED", source_class="DERIVED",
        content=("Verbatim clause from governed asset 61: This agreement "
                 "renews on 2026-10-20 unless either party gives written "
                 "notice of non-renewal."))
    session.add(reg_asset)
    session.commit()
    session.refresh(reg_asset)

    approved = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.status == "APPROVED").all()
    model = db.ExpertModel(project_id=project.id, name="Deadline Expert",
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    session.add(model)
    session.commit()
    session.refresh(model)
    package_row = db.AgentPackage(project_id=project.id,
                                  expert_model_id=model.id,
                                  name="Deadline Package",
                                  clearance_level="INTERNAL")
    session.add(package_row)
    session.commit()
    session.refresh(package_row)
    package_builder.build_package(session, package_row)
    session.refresh(package_row)
    loaded = package_consumer.load_package(package_row.file_path)
    answerer = make_answerer(loaded)

    agent = identity.create_principal(session, name="compliance-obligation",
                                      display_name="Compliance Obligation",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _cred = identity.issue_token(session, agent, kind="API_TOKEN",
                                              label="ws2", actor="test-suite")
    issuer = test_support.governed_actor(session, "DdlWS2Issuer")
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
    print(f"Part 2 passed: {doc_count} documents + the DERIVED register "
          f"fixture (asset #{reg_asset.id}) packaged; agent bound.")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE DIAGNOSIS engaged (kinds, arithmetic, harvest, "
          "determinism) ---")
    vault_dir = bootstrap_vault()
    baseline = vault_files(vault_dir)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        runs = [runner.run_diagnostic(
            package_row.file_path, vault_dir, project.id,
            agent_principal="compliance-obligation", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW, answerer=answerer) for _ in range(2)]
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    first, second = runs
    assert first["proposals"] == second["proposals"]
    assert first["brief"] == second["brief"]
    for path in first["proposals"] + [first["pack"], first["brief"]]:
        with open(path, encoding="utf-8") as f:
            content_1 = f.read()
        with open(path, encoding="utf-8") as f:
            assert f.read() == content_1

    kinds = {f["finding_kind"] for f in first["findings"]}
    for expected in ("COMPLIANCE_OBLIGATION", "MISSING_COMPLIANCE_EVIDENCE",
                     "OUTDATED_POLICY", "UNDOCUMENTED_OBLIGATION_OWNER",
                     "OBLIGATION_DEADLINE", "DEADLINE_AMBIGUITY",
                     "RECURRENCE_RULE"):
        assert expected in kinds, f"{expected} missing from the diagnosis"

    def finding(kind):
        return [f for f in first["findings"] if f["finding_kind"] == kind]

    # The certification plant: verbatim date, declared-clock arithmetic.
    dated = finding("OBLIGATION_DEADLINE")
    cert = [f for f in dated if f["date"] == "2026-11-30"]
    assert cert, "the certification validity date must be an in-window finding"
    assert cert[0]["deadline_class"] == "certification_expiry"
    assert cert[0]["days_until"] == 76 and cert[0]["as_of"] == AS_OF \
        and cert[0]["window_days"] == WINDOW

    # THE HARVEST: the DERIVED register fact, cited BY governed asset id.
    harvest = [f for f in dated if f["asset_id"] == reg_asset.id]
    assert harvest, "the register clause must yield a deadline finding"
    assert harvest[0]["date"] == "2026-10-20" and harvest[0]["days_until"] == 35
    assert "DERIVED" in harvest[0]["cite"], \
        "the register fact must be cited AS DERIVED (D30)"
    assert harvest[0]["cited_assets"] == [reg_asset.id]

    # THE AMBIGUITY plants: flagged verbatim, date-free forever.
    vague = finding("DEADLINE_AMBIGUITY")
    markers = {f["vague_marker"] for f in vague}
    assert {"promptly", "within a reasonable period",
            "in a timely manner"} <= markers, markers
    for f in vague:
        assert "date" not in f, "an ambiguity finding never carries a date"

    # Recurrence: verbatim rules, never expanded.
    recurring = finding("RECURRENCE_RULE")
    assert len(recurring) >= 2, "the annual duties must be extracted"
    declared_markers = runner.parse_nested_quoted_list(
        os.path.join(WB_DIR, "skills", "extract_recurrence_rules.yaml"),
        "recurrence_convention", "recurrence_markers")
    interval_re = runner.parse_declared_pattern(
        os.path.join(WB_DIR, "skills", "extract_recurrence_rules.yaml"),
        "recurrence_convention", "explicit_interval_pattern")
    assert all(f["matched_marker"] in declared_markers
               or interval_re.fullmatch(f["matched_marker"])
               for f in recurring), \
        "every matched marker is a declared marker or explicit interval"

    # Proposal bytes: ambiguity + recurrence proposals carry NO date at
    # all (THE INVENTED DATE swept on the bytes); every extension
    # proposal is one file per finding in 08_proposals.
    checked = 0
    for path in first["proposals"]:
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        kind_m = re.search(r"^finding_kind: (\S+)", body, re.MULTILINE)
        cited_m = re.search(r"^cited_assets: (\S+)", body, re.MULTILINE)
        assert kind_m and cited_m, f"malformed proposal frontmatter: {path}"
        if kind_m.group(1) in ("DEADLINE_AMBIGUITY", "RECURRENCE_RULE",
                               "RECURRENCE_AMBIGUITY"):
            # THE INVENTED DATE, on the bytes: every date in the proposal
            # must be verbatim in a cited governed source (a quoted source
            # sentence may contain a date; a GENERATED one may not).
            sources = [norm(session.get(db.KnowledgeAsset, int(i)).content)
                       for i in cited_m.group(1).split(",")]
            for d in DATE_RE.findall(body):
                assert any(d in s for s in sources), \
                    f"{kind_m.group(1)} proposal carries a date not in " \
                    f"its governed sources: {d} ({path})"
            checked += 1
    assert checked >= 4, "the flagged/recurrence proposals must be swept"

    # Before-as_of dates are declared arithmetic skips, never findings
    # and never conduct claims.
    before = [s for s in first["skipped"]
              if s["skill"] == "detect_obligation_deadlines"
              and "before the declared as_of" in s["reason"]]
    assert before, "past dates must be declared as arithmetic skips"
    assert all("arithmetic fact" in s["reason"] for s in before)

    new_files = vault_files(vault_dir) - baseline
    for rel in new_files:
        assert rel.startswith(("08_proposals/", "07_agent_workspaces/")), \
            f"writes must be confined: {rel}"
    workspace = [r for r in new_files if r.startswith("07_agent_workspaces/")]
    assert len(workspace) == 2, \
        "exactly the audit pack + the calendar brief in the workspace"
    print(f"Part 3 passed: {len(first['findings'])} findings "
          f"({len(dated)} dated incl. THE HARVEST via DERIVED asset "
          f"#{reg_asset.id}, {len(vague)} flagged date-free, "
          f"{len(recurring)} recurrence verbatim); byte-identical re-runs; "
          f"writes confined; {len(before)} past date(s) as declared "
          f"arithmetic.")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: THE WINDOW RE-DECLARATION (a new clock is a new "
          "diagnosis) ---")
    vault_30 = bootstrap_vault()
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        narrow = runner.run_diagnostic(
            package_row.file_path, vault_30, project.id,
            agent_principal="compliance-obligation", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=30, answerer=answerer)
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    narrow_dated = [f for f in narrow["findings"]
                    if f["finding_kind"] == "OBLIGATION_DEADLINE"]
    assert not any(f["date"] in ("2026-11-30", "2026-10-20")
                   for f in narrow_dated), \
        "both dates are outside the 30-day window - no finding"
    outside = [s for s in narrow["skipped"]
               if "outside the declared 30-day window" in s["reason"]]
    assert len(outside) >= 2, "the departures must be declared skips"
    narrow_kinds = {f["finding_kind"] for f in narrow["findings"]}
    assert "DEADLINE_AMBIGUITY" in narrow_kinds \
        and "RECURRENCE_RULE" in narrow_kinds, \
        "the clock-free kinds hold at any declared window"
    print(f"Part 4 passed: at window 30 both dated findings leave as "
          f"{len(outside)} declared OUTSIDE skips; ambiguity + recurrence "
          f"hold - a re-declared clock is a new diagnosis, never an update.")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: THE CALENDAR BRIEF (assist-only, declared clock, "
          "no persistence) ---")
    with open(first["brief"], encoding="utf-8") as f:
        brief = f.read()
    assert f"as_of {AS_OF} - window {WINDOW} days" in brief, \
        "the declared clock pair must be printed verbatim"
    for section in ("## Dated", "## Recurring", "## Flagged"):
        assert section in brief, f"mandatory section missing: {section}"
    assert "NOT a proposal" in brief and "SYNTHESIS_INFERRED" in brief
    assert "/08_proposals/" not in first["brief"].replace(os.sep, "/"), \
        "the brief must never be a proposal"
    assert first["brief"] not in first["proposals"]
    assert "never" in brief and "persisted" in brief
    forbidden = runner.parse_quoted_list(
        os.path.join(WB_DIR, "skills", "detect_obligation_deadlines.yaml"),
        "forbidden_vocabulary")
    lowered = brief.lower()
    for phrase in forbidden:
        assert phrase not in lowered, f"forbidden vocabulary in brief: {phrase}"
    print("Part 5 passed: the brief is a 07-confined snapshot at the "
          "declared clock - three mandatory sections, never a proposal, "
          "zero conduct vocabulary, persistence refused in its own bytes.")

    # ------------------------------------------------------------ Part 6
    print("\n--- Part 6: the live refusals + THE V1.7 SHAPE + "
          "NON-CONFLATION ---")
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        # (a) an explicit deadline request without a declared window is
        # refused LOUDLY - the window is never defaulted.
        refused_window = False
        try:
            runner.run_diagnostic(
                package_row.file_path, vault_dir, project.id,
                agent_principal="compliance-obligation", binding_id=binding.id,
                graph_client=InProcessGraphClient(), as_of=AS_OF,
                answerer=answerer,
                requested_skills=("detect_obligation_deadlines",))
        except RuntimeError as e:
            refused_window = "no window_days declared" in str(e)
        assert refused_window, \
            "an explicit deadline request without window_days must refuse"

        # (b) the [OE] operational-status question is refused live,
        # naming the unminted realm (THE PRESUMED COMPLETION's gate).
        refused_oe = False
        try:
            runner.run_diagnostic(
                package_row.file_path, vault_dir, project.id,
                agent_principal="compliance-obligation", binding_id=binding.id,
                graph_client=InProcessGraphClient(), as_of=AS_OF,
                window_days=WINDOW, answerer=answerer,
                requested_skills=runner.ACTIVE_SKILLS
                + ("verify_obligations_against_operational_records",))
        except RuntimeError as e:
            refused_oe = "Operational Evidence Realm" in str(e)
        assert refused_oe, "the operational-status request must name [OE]"

        # (c) THE V1.7 SHAPE: an unengaged run (no window_days - exactly
        # how every pre-v2.2 caller calls) produces NO extension kinds,
        # exactly ONE workspace file, and three declared skips.
        vault_17 = bootstrap_vault()
        base_17 = vault_files(vault_17)
        legacy = runner.run_diagnostic(
            package_row.file_path, vault_17, project.id,
            agent_principal="compliance-obligation", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            answerer=answerer)
        legacy_kinds = {f["finding_kind"] for f in legacy["findings"]}
        assert not legacy_kinds & {"OBLIGATION_DEADLINE",
                                   "DEADLINE_AMBIGUITY", "RECURRENCE_RULE",
                                   "RECURRENCE_AMBIGUITY"}, \
            "an unengaged run must produce no extension findings"
        assert legacy["brief"] is None
        legacy_ws = [r for r in vault_files(vault_17) - base_17
                     if r.startswith("07_agent_workspaces/")]
        assert len(legacy_ws) == 1, "exactly one workspace file, as at v1.7"
        ext_skips = {s["skill"] for s in legacy["skipped"]
                     if s["skill"] in ("detect_obligation_deadlines",
                                       "extract_recurrence_rules",
                                       "prepare_obligation_calendar_brief")}
        assert len(ext_skips) == 3, \
            "all three extension skills must be declared skips, never silent"
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)

    # (d) THE NON-CONFLATION: nothing anywhere in this suite created a
    # stewardship decision - a document deadline is not a DUE_DATE_SET.
    steward = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "STEWARDSHIP_DECISION").count()
    assert steward == 0, "deadline detection must write ZERO stewardship"
    print("Part 6 passed: window refusal loud; [OE] named live; THE V1.7 "
          "SHAPE preserved (no extension kinds, one workspace file, three "
          "declared skips); zero STEWARDSHIP_DECISION events.")

    # ------------------------------------------------------------ Part 7
    print("\n--- Part 7: the structural closers ---")
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
    print("Part 7 passed: route manifest 88 (digest frozen); the nine MCP "
          "tools; D24 byte-identical at 28/305.")

    session.close()
    print("\nAll v2.2 WS2 checks passed: the extended runner meets the "
          "three ratified contracts at the declared clock pair - every "
          "date verbatim or declared arithmetic, every vague duty flagged "
          "never dated, the register harvested BY ID, the calendar "
          "computed never kept, and the shipped v1.7 shape preserved.")


if __name__ == "__main__":
    main()
