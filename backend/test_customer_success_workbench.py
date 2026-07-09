"""v2.4 WS2 gate suite — THE DIAGNOSIS PROOF (the 88th suite).

The Customer Success Intelligence runner meets the five ratified
contracts (docs/customer-success-intelligence-v2.4.md) over the real
corpora (12 customer-operations + 4 corpus_customer_success/) plus one
injected DERIVED register fixture for THE THIRD HARVEST:

  1. Guard 5 door sweep — the new runner stays inside the ruled doors.
  2. Corpora in + the DERIVED register fixture; package compiled; agent
     bound. No UI, no operational customer-data reader
     (CRM/usage/ticket/NPS/telemetry/health-score) exists (structural).
  A. THE DIAGNOSIS — all four finding kinds fire where they should:
     CUSTOMER_TERM_DEVIATION (Acme, both axes), CUSTOMER_RENEWAL_
     OBLIGATION (Acme window + the harvest), CUSTOMER_COVERAGE_GAP
     (the Acme QBR gap), UNBACKED_HEALTH_ASSUMPTION (the plant).
  B. THE CUSTOM TERMS PROOF — Northwind (the conforming customer)
     produces ZERO deviation findings (both axes conform), proven from
     the runner's actual output and the proposal bytes, not a fixture
     shortcut.
  C. THE IMPUTED HEALTH SWEEP (quote-frame-aware) — the manifest's
     relationship-state vocabulary appears on NO written byte except
     inside a verbatim quoted-claim blockquote ("> ...") of an
     UNBACKED_HEALTH_ASSUMPTION proposal; and it DOES appear there (the
     plant surfaced only through THE QUOTE FRAME).
  D. THE THIRD HARVEST — the DERIVED register fixture yields a renewal
     obligation citing it BY id, tagged [DERIVED], inside the declared
     window; the runner invents no obligation outside cited evidence.
  E. Determinism — repeated runs produce byte-identical proposals and
     brief (content-hash names, no timestamps, sorted walks).
  F. Write confinement — the runner writes only to /08_proposals and
     /07_agent_workspaces; nothing else in the vault changes.
  G. Structural non-existence — no operational customer-data reader
     module, no ranking/scoring/churn/health path; the [OE]/[ES] gated
     family is refused live, naming the unminted decision.
  8. The closers — route manifest 88, the nine MCP tools, D24 28/305.
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
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_cs2_pkg_")

import test_agent_authorship_guard as guard   # noqa: E402 - engine override order
import test_route_manifest as route_guard      # noqa: E402

from sqlalchemy import create_engine           # noqa: E402
from sqlalchemy.orm import sessionmaker        # noqa: E402
from app import database as db                 # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_cs2_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'ws2.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                      # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_cs2_qdrant_")

from app import (schemas, crud, connectors,    # noqa: E402
                 package_builder, package_consumer, identity, mcp_gateway,
                 tier2)
import test_support                            # noqa: E402
import test_workbench_projection              # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.customer_success_intelligence.runner as runner   # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "customer_success_intelligence")
CS_CORPUS = os.path.join(WB_DIR, "corpus_customer_success")
CUSOPS_CORPUS = os.path.join(REPO_DIR, "workbench",
                             "customer_operations", "corpus")

AS_OF = "2026-07-10"
WINDOW = 90
CUSTOMERS = ("Acme Industrial", "Northwind Logistics")


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
    vault_dir = tempfile.mkdtemp(prefix="em_cs2_vault_")
    r = subprocess.run([sys.executable,
                        os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                        "--vault-dir", vault_dir],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
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
    def answer(question):
        sel = package_consumer.retrieve(loaded_package, question,
                                        top_k=8)["selected"]
        return {"answer": "INSUFFICIENT EVIDENCE - the governed corpus offers "
                          "no covering procedure for this question.",
                "cited_asset_ids": [], "evidence": sel}
    return answer


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "CSWS2Officer")
    reviewer = test_support.governed_actor(session, "CSWS2Reviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Customer Success WS2", description="the diagnosis proof",
        customer_id=customer.id), actor=officer)

    # ------------------------------------------------------------ Part 1
    print("\n--- Part 1: the runner passes the Guard 5 door sweep ---")
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
    assert len(runner.ACTIVE_SKILLS) == 5
    print(f"Part 1 passed: {swept} workbench module(s) inside the ruled "
          "doors - the customer-success runner swept with zero guard edits.")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: corpora + the DERIVED register fixture, package, "
          "agent bound ---")
    for name, root in (("Customer Operations Docs", CUSOPS_CORPUS),
                       ("Customer Success Docs", CS_CORPUS)):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
    doc_count = session.query(db.Document).filter_by(
        project_id=project.id).count()
    assert doc_count == 16, f"expected 12 + 4 documents, got {doc_count}"
    approve_all(session, project.id, reviewer, "WS2 cs corpus approval")

    # THE THIRD HARVEST fixture: an accepted DERIVED register clause
    # carrying a renewal obligation with an in-window date, cited [DERIVED].
    reg_doc = db.Document(project_id=project.id,
                          filename="register-clause-fixture.md",
                          file_path="register-clause-fixture.md",
                          status="PROCESSED")
    session.add(reg_doc)
    session.commit()
    session.refresh(reg_doc)
    reg = db.KnowledgeAsset(
        project_id=project.id, document_id=reg_doc.id,
        name="Register clause: Acme renewal", type="POLICY",
        status="APPROVED", source_class="DERIVED",
        content=("Verbatim clause from governed asset 47: this agreement with "
                 "Acme Industrial renews and the customer must be notified "
                 "before the renewal date 2026-08-20."))
    session.add(reg)
    session.commit()
    session.refresh(reg)

    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").order_by(
        db.KnowledgeAsset.id).all()
    model = db.ExpertModel(project_id=project.id, name="CS Expert",
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    session.add(model)
    session.commit()
    session.refresh(model)
    pkg = db.AgentPackage(project_id=project.id, expert_model_id=model.id,
                          name="CS Package", clearance_level="INTERNAL")
    session.add(pkg)
    session.commit()
    session.refresh(pkg)
    package_builder.build_package(session, pkg)
    session.refresh(pkg)
    loaded = package_consumer.load_package(pkg.file_path)
    answerer = make_answerer(loaded)

    agent = identity.create_principal(session,
                                      name="customer-success-intelligence",
                                      display_name="Customer Success",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _c = identity.issue_token(session, agent, kind="API_TOKEN",
                                           label="ws2", actor="test-suite")
    issuer = test_support.governed_actor(session, "CSWS2Issuer")
    binding = db.ExpertAgentBinding(
        agent_package_id=pkg.id, agent_principal_id=agent.id,
        package_hash=pkg.package_hash, package_version="v1",
        principal_clearance_at_issue="INTERNAL",
        selected_provider="ANTHROPIC", selected_model_name="claude-opus-4-8",
        selection_evidence_json="{}",
        identity_fact_id=issuer.fact(session).id)
    session.add(binding)
    session.commit()
    session.refresh(binding)

    # No operational/UI reader module exists in the bundle.
    bundle_py = [f for f in os.listdir(WB_DIR) if f.endswith(".py")]
    assert bundle_py == ["runner.py"], f"unexpected bundle python: {bundle_py}"
    for root, _dirs, files in os.walk(WB_DIR):
        for fname in files:
            assert not fname.endswith((".tsx", ".jsx", ".html", ".css")), \
                f"no UI module may exist in the bundle: {fname}"
    print(f"Part 2 passed: {doc_count} docs + the DERIVED register fixture "
          f"(#{reg.id}); package compiled; agent bound; only runner.py in "
          f"the bundle.")

    # ------------------------------------------------------------ Part A/E
    print("\n--- Part A: THE DIAGNOSIS (four kinds fire; determinism) ---")
    vault_dir = bootstrap_vault()
    baseline = vault_files(vault_dir)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        runs = [runner.run_diagnostic(
            pkg.file_path, vault_dir, project.id,
            agent_principal="customer-success-intelligence",
            binding_id=binding.id, graph_client=InProcessGraphClient(),
            as_of=AS_OF, window_days=WINDOW, customers=CUSTOMERS,
            answerer=answerer) for _ in range(2)]
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    first, second = runs

    kinds = {f["finding_kind"] for f in first["findings"]}
    for expected in ("CUSTOMER_TERM_DEVIATION", "CUSTOMER_RENEWAL_OBLIGATION",
                     "CUSTOMER_COVERAGE_GAP", "UNBACKED_HEALTH_ASSUMPTION"):
        assert expected in kinds, f"{expected} missing from the diagnosis"

    def findings(kind):
        return [f for f in first["findings"] if f["finding_kind"] == kind]

    # The intended fixtures each fire: Acme deviates on BOTH axes; the QBR
    # coverage gap is Acme's; the plant produced >= 4 assumption findings.
    dev_axes = {f["axis"] for f in findings("CUSTOMER_TERM_DEVIATION")
                if f["customer"] == "Acme Industrial"}
    assert dev_axes == {"reporting_cadence", "renewal_notice"}, dev_axes
    assert any(f["coverage_class"] == "qbr_procedure"
               for f in findings("CUSTOMER_COVERAGE_GAP")), "the QBR gap must fire"
    assert len(findings("UNBACKED_HEALTH_ASSUMPTION")) >= 4, \
        "the health-score plant must yield assumption findings"
    for f in first["findings"]:
        assert f["evidence_lines"], "every finding exposes evidence"

    # E — determinism: byte-identical proposals + brief across re-runs.
    assert first["proposals"] == second["proposals"], "paths must be identical"
    assert (open(first["brief"], encoding="utf-8").read()
            == open(second["brief"], encoding="utf-8").read()), \
        "the brief must be byte-identical across re-runs"
    for p in first["proposals"]:
        assert os.path.isfile(p)
    print(f"Part A/E passed: {len(first['findings'])} findings, all four "
          f"kinds present (Acme deviates on both axes; the QBR gap fires; "
          f"{len(findings('UNBACKED_HEALTH_ASSUMPTION'))} assumption "
          f"findings); byte-identical re-runs.")

    # ------------------------------------------------------------ Part B
    print("\n--- Part B: THE CUSTOM TERMS PROOF (Northwind is silent) ---")
    nw_dev = [f for f in findings("CUSTOMER_TERM_DEVIATION")
              if f["customer"] == "Northwind Logistics"]
    assert not nw_dev, \
        "the conforming customer must produce ZERO deviation findings"
    # Proven on the bytes too: no CUSTOMER_TERM_DEVIATION proposal names
    # Northwind (its conformance is silence, not a suppressed finding).
    for p in first["proposals"]:
        body = open(p, encoding="utf-8").read()
        if "finding_kind: CUSTOMER_TERM_DEVIATION" in body:
            assert "Northwind" not in body, \
                "no deviation proposal may mention the conforming customer"
    # Northwind IS present in the run - as reproducible conformance skips
    # on BOTH axes (silence is a decision, recorded, not an absence).
    nw_skips = [s for s in first["skipped"]
                if "Northwind Logistics conforms" in s["reason"]]
    nw_axes = {axis for axis in ("reporting_cadence", "renewal_notice")
               if any(axis in s["reason"] for s in nw_skips)}
    assert nw_axes == {"reporting_cadence", "renewal_notice"}, \
        f"Northwind must conform on BOTH axes: {nw_axes}"
    print(f"Part B passed: Northwind produces zero deviation findings and no "
          f"deviation proposal names it; it conforms on both axes "
          f"({len(nw_skips)} recorded conformance skips).")

    # ------------------------------------------------------------ Part C
    print("\n--- Part C: THE IMPUTED HEALTH SWEEP (quote-frame-aware) ---")
    forbidden = runner.parse_forbidden_vocabulary(
        os.path.join(WB_DIR, "workbench.yaml"))
    assert len(forbidden) >= 12
    written = first["proposals"] + [first["brief"]]
    quoted_hits = 0
    for path in written:
        for raw in open(path, encoding="utf-8").read().splitlines():
            low = raw.lower()
            in_quote_frame = raw.startswith(runner.QUOTE_PREFIX)
            for phrase in forbidden:
                if phrase in low:
                    assert in_quote_frame, (
                        f"IMPUTED-HEALTH vocabulary {phrase!r} on a NON-quote "
                        f"byte in {os.path.basename(path)}: {raw!r}")
                    quoted_hits += 1
    # The plant DID surface - through the quote frame, verbatim, only.
    assert quoted_hits > 0, \
        "the plant's relationship-state claim must surface inside the quote frame"
    # And it surfaced specifically in an UNBACKED_HEALTH_ASSUMPTION proposal.
    plant_props = [p for p in first["proposals"]
                   if "finding_kind: UNBACKED_HEALTH_ASSUMPTION"
                   in open(p, encoding="utf-8").read()]
    assert plant_props, "the plant must yield UNBACKED_HEALTH_ASSUMPTION proposals"
    assert any(any(line.startswith(runner.QUOTE_PREFIX)
                   and any(ph in line.lower() for ph in forbidden)
                   for line in open(p, encoding="utf-8").read().splitlines())
               for p in plant_props), \
        "an assumption proposal must carry the claim inside the quote frame"
    print(f"Part C passed: the IMPUTED-HEALTH vocabulary appears on "
          f"{quoted_hits} byte(s), every one inside a quoted-claim blockquote; "
          f"zero on any narration byte - THE QUOTE FRAME is the whole "
          f"exemption.")

    # ------------------------------------------------------------ Part D
    print("\n--- Part D: THE THIRD HARVEST (DERIVED register cited BY id) ---")
    harvest = [f for f in findings("CUSTOMER_RENEWAL_OBLIGATION")
               if f["asset_id"] == reg.id]
    assert harvest, "the DERIVED register clause must yield a renewal obligation"
    hv = harvest[0]
    assert "[DERIVED]" in hv["cite"], "the register fact cited AS DERIVED"
    assert hv["harvested"] is True
    assert hv["cited_assets"] == [reg.id]
    assert hv["action_date"] == "2026-08-20", "the in-window register date"
    # The runner invents no obligation: every renewal finding's excerpt is a
    # verbatim substring of a cited governed fact (nothing fabricated).
    knowledge = {e["asset_id"]: " ".join((e.get("content") or "").split())
                 for e in loaded["knowledge"]}
    for f in findings("CUSTOMER_RENEWAL_OBLIGATION"):
        for aid in f["cited_assets"]:
            assert aid in knowledge, f"cited asset {aid} not in the package"
        core = f["excerpt"].rstrip(".")[:60]
        assert core in knowledge[f["asset_id"]], \
            "the obligation excerpt must be verbatim from the cited fact"
    print(f"Part D passed: register #{reg.id} [DERIVED] yields an in-window "
          f"renewal obligation cited BY id ({hv['action_date']}); no "
          f"obligation invented outside cited evidence.")

    # ------------------------------------------------------------ Part F
    print("\n--- Part F: write confinement ---")
    new_files = vault_files(vault_dir) - baseline
    assert new_files, "the run must have written something"
    for rel in new_files:
        assert rel.startswith(("08_proposals/", "07_agent_workspaces/")), \
            f"writes must be confined: {rel}"
    # The brief lives in 07, never 08; proposals live in 08, never 07.
    assert "/07_agent_workspaces/" in first["brief"].replace(os.sep, "/")
    assert first["brief"] not in first["proposals"]
    for p in first["proposals"]:
        assert "/08_proposals/" in p.replace(os.sep, "/")
    print(f"Part F passed: {len(new_files)} new vault file(s), all confined to "
          f"08_proposals + 07_agent_workspaces; brief in 07, proposals in 08.")

    # ------------------------------------------------------------ Part G
    print("\n--- Part G: structural non-existence (no [OE]/[ES] path) ---")
    # The relationship-state family is gated [OE]; ownerless-obligation
    # assignment is [ES]. Each is refused live, naming the unminted decision.
    oe_family = ("detect_declining_activity", "detect_low_usage",
                 "detect_unresolved_customer_issues", "score_customer_risk",
                 "cluster_recurring_complaints", "identify_churn_signals")
    for skill in oe_family:
        assert runner.GATED_SKILLS.get(skill) == "the Operational Evidence Realm"
    assert runner.GATED_SKILLS.get("detect_customer_obligations_without_owner") \
        == "Exception Stewardship"
    # A gated skill requested at runtime is refused, naming the gate.
    for skill, realm in (("score_customer_risk", "Operational Evidence"),
                         ("detect_customer_obligations_without_owner",
                          "Exception Stewardship")):
        raised = False
        try:
            runner.run_diagnostic(
                pkg.file_path, vault_dir, project.id,
                agent_principal="customer-success-intelligence",
                binding_id=binding.id, graph_client=InProcessGraphClient(),
                as_of=AS_OF, window_days=WINDOW, customers=CUSTOMERS,
                answerer=answerer, requested_skills=(skill,))
        except RuntimeError as exc:
            raised = True
            assert realm in str(exc), f"the gate must name {realm}: {exc}"
        assert raised, f"{skill} must be refused live"
    # No operational-reader/scoring symbol exists in the runner surface.
    for banned in ("score_customer", "rank_customer", "churn", "health_score",
                   "read_crm", "read_usage", "read_tickets", "read_nps"):
        assert not hasattr(runner, banned), \
            f"the runner must expose no {banned} path"
    # The manifest names the refused families.
    manifest = open(os.path.join(WB_DIR, "workbench.yaml"),
                    encoding="utf-8").read()
    assert "refused_until_minted" in manifest
    assert "operational_evidence" in manifest and "[OE]" in manifest
    assert "exception_stewardship" in manifest
    print("Part G passed: the [OE] relationship-state family and the [ES] "
          "ownerless-obligation skill are refused live, naming the unminted "
          "decision; no scoring/ranking/CRM/usage/ticket/NPS path exists.")

    # ------------------------------------------------------------ Part 8
    print("\n--- Part 8: the closers ---")
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
    print("Part 8 passed: route manifest 88 (digest frozen); the nine MCP "
          "tools; D24 byte-identical at 28/305.")

    session.close()
    print("\nAll v2.4 WS2 checks passed: the runner diagnoses per-customer "
          "term deviation, obligation windows, coverage gaps, and unbacked "
          "assumptions - the conforming customer stays silent, the plant "
          "surfaces only through THE QUOTE FRAME, the DERIVED register is "
          "harvested BY id, writes stay confined, and it knows nothing of "
          "the customer relationship's state.")


if __name__ == "__main__":
    main()
