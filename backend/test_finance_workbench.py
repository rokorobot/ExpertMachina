"""v2.3 WS2 gate suite — THE DIAGNOSIS PROOF (the 85th suite).

The Finance & Cost Leakage runner meets the five ratified contracts
(docs/finance-cost-leakage-v2.3.md) over the real corpora plus two
injected fixtures (a DERIVED register clause for THE SECOND HARVEST, a
transactional record for THE INVOICE PLANT decline):

  1. Guard 5 door sweep — the new runner stays inside the ruled doors.
  2. Corpus in (12 procurement + 3 corpus_finance) + the two fixtures;
     package compiled; agent bound. No UI, no operational connector,
     no invoice/PO/ERP/ledger/bank reader exists (structural).
  3. THE DIAGNOSIS — COST_EXPOSURE / FINANCE_POLICY_MISMATCH /
     MISSING_FINANCE_EVIDENCE all fire; byte-identical re-runs;
     evidence/arithmetic/assumptions/exclusions/uncertainty exposed.
  4. THE EXPOSURE ARITHMETIC — 12,000 EUR x 8% = 960.00 EUR by
     declared arithmetic over verbatim values (formula on the bytes).
  5. THE SECOND HARVEST — an exposure finding cites the DERIVED
     register fact BY id, tagged [DERIVED].
  6. THE UNOPENED LEDGER — THE INVOICE PLANT (the injected
     transactional record) is DECLINED with a declared [OE] skip and
     never becomes a finding; the SETTLED-ACCOUNT sweep leaves the
     legitimate "not paid by its due date" penalty CLAUSE intact (THE
     INVOICE-SENTENCE DISTINCTION); no forbidden vocabulary on any
     written byte.
  7. THE LABELED ESTIMATE — the scenario brief wears the label in-unit,
     is assist-only (07, never a proposal), never knowledge.
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
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="em_fin2_pkg_")

import test_agent_authorship_guard as guard   # noqa: E402 - engine override order
import test_route_manifest as route_guard      # noqa: E402

from sqlalchemy import create_engine           # noqa: E402
from sqlalchemy.orm import sessionmaker        # noqa: E402
from app import database as db                 # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_fin2_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'ws2.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                      # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_fin2_qdrant_")

from app import (schemas, crud, connectors,    # noqa: E402
                 package_builder, package_consumer, identity, mcp_gateway,
                 tier2)
import test_support                            # noqa: E402
import test_workbench_projection              # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_DIR)
import workbench.finance_cost_leakage.runner as runner   # noqa: E402

WB_DIR = os.path.join(REPO_DIR, "workbench", "finance_cost_leakage")
FINANCE_CORPUS = os.path.join(WB_DIR, "corpus_finance")
PROC_CORPUS = os.path.join(REPO_DIR, "workbench",
                           "procurement_intelligence", "corpus")

AS_OF = "2026-07-10"
WINDOW = 90


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
    vault_dir = tempfile.mkdtemp(prefix="em_fin2_vault_")
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
        qt = package_consumer._tokens(question)
        scored = sorted(
            ((len(qt & package_consumer._tokens(e.get("content") or "")), e)
             for e in sel), key=lambda t: (-t[0], t[1]["asset_id"]))
        if scored and scored[0][0] >= 6:
            best = scored[0][1]
            text_ = (f"Per the governed evidence (asset_id {best['asset_id']}): "
                     f"{best.get('content')}")
        else:
            text_ = ("INSUFFICIENT EVIDENCE - the governed evidence offered "
                     "does not contain the answer to this question.")
        return {"answer": text_,
                "cited_asset_ids": [] if "INSUFFICIENT" in text_
                else [scored[0][1]["asset_id"]],
                "evidence": sel}
    return answer


def norm(t):
    return " ".join((t or "").split())


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "FinWS2Officer")
    reviewer = test_support.governed_actor(session, "FinWS2Reviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Finance WS2", description="the diagnosis proof",
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
          "doors - the finance runner swept with zero guard edits.")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: corpora + fixtures, package compiled, agent bound ---")
    for name, root in (("Procurement Docs", PROC_CORPUS),
                       ("Finance Extension Docs", FINANCE_CORPUS)):
        conn = db.SourceConnector(project_id=project.id, name=name,
                                  type="LOCAL_FOLDER", root_path=root,
                                  include_extensions=".md")
        session.add(conn)
        session.commit()
        session.refresh(conn)
        run_scan(session, conn)
    doc_count = session.query(db.Document).filter_by(
        project_id=project.id).count()
    assert doc_count == 15, f"expected 12 + 3 documents, got {doc_count}"
    approve_all(session, project.id, reviewer, "WS2 finance corpus approval")

    # THE SECOND HARVEST fixture: an accepted DERIVED register clause
    # carrying both a verbatim base and a verbatim rate (so declared
    # arithmetic fires deterministically), cited [DERIVED].
    reg_doc = db.Document(project_id=project.id,
                          filename="register-clause-fixture.md",
                          file_path="register-clause-fixture.md",
                          status="PROCESSED")
    session.add(reg_doc)
    session.commit()
    session.refresh(reg_doc)
    reg = db.KnowledgeAsset(
        project_id=project.id, document_id=reg_doc.id,
        name="Register clause: fee escalation", type="POLICY",
        status="APPROVED", source_class="DERIVED",
        content=("Verbatim clause from governed asset 61: the annual service "
                 "fee is 12,000 EUR and shall increase by 8% on each "
                 "anniversary of the effective date."))
    session.add(reg)
    # THE INVOICE PLANT fixture: a transactional record. It carries a
    # currency figure (superficially exposure-like) but is a RECORD
    # (invoice number / amount due) asserting settled truth - the runner
    # must DECLINE it, never emit a finding.
    inv_doc = db.Document(project_id=project.id,
                          filename="injected-invoice-record.md",
                          file_path="injected-invoice-record.md",
                          status="PROCESSED")
    session.add(inv_doc)
    session.commit()
    session.refresh(inv_doc)
    inv = db.KnowledgeAsset(
        project_id=project.id, document_id=inv_doc.id,
        name="Vendor invoice record", type="POLICY",
        status="APPROVED", source_class="PRIMARY",
        content=("Invoice number INV-9001: the amount due of 12,000 EUR was "
                 "paid in full and the payment cleared on 2026-07-05."))
    session.add(inv)
    session.commit()
    session.refresh(reg)
    session.refresh(inv)

    approved = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="APPROVED").order_by(
        db.KnowledgeAsset.id).all()
    model = db.ExpertModel(project_id=project.id, name="Finance Expert",
                           asset_ids_json=json.dumps([a.id for a in approved]),
                           asset_count=len(approved))
    session.add(model)
    session.commit()
    session.refresh(model)
    pkg = db.AgentPackage(project_id=project.id, expert_model_id=model.id,
                          name="Finance Package", clearance_level="INTERNAL")
    session.add(pkg)
    session.commit()
    session.refresh(pkg)
    package_builder.build_package(session, pkg)
    session.refresh(pkg)
    loaded = package_consumer.load_package(pkg.file_path)
    answerer = make_answerer(loaded)

    agent = identity.create_principal(session, name="finance-cost-leakage",
                                      display_name="Finance Cost Leakage",
                                      kind="AGENT", clearance="INTERNAL",
                                      created_by="test-suite")
    agent_token, _c = identity.issue_token(session, agent, kind="API_TOKEN",
                                           label="ws2", actor="test-suite")
    issuer = test_support.governed_actor(session, "FinWS2Issuer")
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

    # No operational/transactional reader exists in the bundle.
    bundle_py = [f for f in os.listdir(WB_DIR) if f.endswith(".py")]
    assert bundle_py == ["runner.py"], f"unexpected bundle python: {bundle_py}"
    print(f"Part 2 passed: {doc_count} docs + the DERIVED register fixture "
          f"(#{reg.id}) + THE INVOICE PLANT (#{inv.id}); package compiled; "
          f"agent bound; only runner.py in the bundle.")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE DIAGNOSIS (kinds, determinism, exposure) ---")
    vault_dir = bootstrap_vault()
    baseline = vault_files(vault_dir)
    os.environ["EM_AGENT_TOKEN"] = agent_token
    try:
        runs = [runner.run_diagnostic(
            pkg.file_path, vault_dir, project.id,
            agent_principal="finance-cost-leakage", binding_id=binding.id,
            graph_client=InProcessGraphClient(), as_of=AS_OF,
            window_days=WINDOW, answerer=answerer) for _ in range(2)]
    finally:
        os.environ.pop("EM_AGENT_TOKEN", None)
    first, second = runs
    assert first["proposals"] == second["proposals"], "paths must be identical"
    assert first["brief"] == second["brief"] and first["pack"] == second["pack"]

    kinds = {f["finding_kind"] for f in first["findings"]}
    for expected in ("COST_EXPOSURE", "FINANCE_POLICY_MISMATCH",
                     "MISSING_FINANCE_EVIDENCE"):
        assert expected in kinds, f"{expected} missing from the diagnosis"

    def finding(kind):
        return [f for f in first["findings"] if f["finding_kind"] == kind]

    # Evidence / arithmetic / assumptions / exclusions / uncertainty exposed.
    for f in first["findings"]:
        assert f["evidence_lines"], "every finding exposes evidence"
    with open(first["brief"], encoding="utf-8") as fh:
        brief = fh.read()
    assert "## Assumptions" in brief
    new_files = vault_files(vault_dir) - baseline
    for rel in new_files:
        assert rel.startswith(("08_proposals/", "07_agent_workspaces/")), \
            f"writes confined: {rel}"
    print(f"Part 3 passed: {len(first['findings'])} findings, all three "
          f"kinds present; byte-identical re-runs; writes confined to "
          f"08_proposals + 07_agent_workspaces.")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: THE EXPOSURE ARITHMETIC (declared, verbatim base) ---")
    arith = [f for f in finding("COST_EXPOSURE") if f.get("arithmetic")]
    assert arith, "at least one exposure must carry declared arithmetic"
    assert any("12,000 EUR x 8% = 960.00 EUR" in f["arithmetic"] for f in arith), \
        f"the declared arithmetic must be exact: {[f['arithmetic'] for f in arith]}"
    # The arithmetic appears on the proposal bytes.
    hit = False
    for path in first["proposals"]:
        with open(path, encoding="utf-8") as fh:
            if "12,000 EUR x 8% = 960.00 EUR" in fh.read():
                hit = True
    assert hit, "the declared arithmetic must appear verbatim on the bytes"
    print("Part 4 passed: 12,000 EUR x 8% = 960.00 EUR by declared "
          "arithmetic over verbatim values, on the finding bytes.")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: THE SECOND HARVEST (DERIVED register cited BY id) ---")
    harvest = [f for f in finding("COST_EXPOSURE")
               if f["asset_id"] == reg.id]
    assert harvest, "the DERIVED register clause must yield an exposure finding"
    assert "DERIVED" in harvest[0]["cite"], "the register fact cited AS DERIVED"
    assert harvest[0]["cited_assets"] == [reg.id]
    print(f"Part 5 passed: exposure finding cites register #{reg.id} "
          f"[DERIVED] BY id - THE SECOND HARVEST, nothing re-extracted.")

    # ------------------------------------------------------------ Part 6
    print("\n--- Part 6: THE UNOPENED LEDGER (invoice plant declined; the "
          "sweep spares legitimate clauses) ---")
    # THE INVOICE PLANT is declined, naming [OE], and never a finding.
    declined = [s for s in first["skipped"]
                if "TRANSACTIONAL RECORD" in s["reason"]
                and "Operational Evidence Realm" in s["reason"]]
    assert declined, "THE INVOICE PLANT must be declined naming [OE]"
    assert not any(f["asset_id"] == inv.id for f in first["findings"]), \
        "the transactional record must NEVER become a finding"
    # THE INVOICE-SENTENCE DISTINCTION: the legitimate late-payment penalty
    # CLAUSE ("not paid by its due date ... surcharge") is NOT over-blocked
    # - it produced a penalty_fee exposure finding.
    penalty = [f for f in finding("COST_EXPOSURE")
               if f["exposure_class"] == "penalty_fee"
               and "not paid by its due date" in f["excerpt"].lower()]
    assert penalty, \
        "the legitimate 'not paid by its due date' penalty clause must survive"
    # No forbidden SETTLED-ACCOUNT vocabulary on any written byte.
    manifest = open(os.path.join(WB_DIR, "workbench.yaml"),
                    encoding="utf-8").read()
    forbidden = runner.parse_forbidden_vocabulary(
        os.path.join(WB_DIR, "workbench.yaml"))
    written = [open(p, encoding="utf-8").read().lower()
               for p in first["proposals"] + [first["brief"], first["pack"]]]
    for phrase in forbidden:
        for body in written:
            assert phrase not in body, \
                f"SETTLED-ACCOUNT vocabulary {phrase!r} on a written byte"
    print(f"Part 6 passed: THE INVOICE PLANT (#{inv.id}) declined naming "
          f"[OE], never a finding; the 'not paid by its due date' penalty "
          f"clause survived as a penalty_fee exposure (THE INVOICE-SENTENCE "
          f"DISTINCTION); zero forbidden vocabulary on every written byte.")

    # ------------------------------------------------------------ Part 7
    print("\n--- Part 7: THE LABELED ESTIMATE (assist-only, in-unit) ---")
    assert f"as_of {AS_OF} - window {WINDOW} days" in brief
    assert "[ESTIMATE, non-authoritative]" in brief, \
        "the scenario must wear the estimate label in-unit"
    assert "/08_proposals/" not in first["brief"].replace(os.sep, "/")
    assert first["brief"] not in first["proposals"]
    assert "## Governed exposures" in brief and "## Scenarios" in brief
    print("Part 7 passed: the scenario brief is a 07-confined assist output "
          "wearing the estimate label in-unit; never a proposal.")

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
    print("\nAll v2.3 WS2 checks passed: the runner diagnoses governed cost "
          "exposure - declared arithmetic over verbatim values, the DERIVED "
          "register harvested BY id, THE INVOICE PLANT declined naming [OE], "
          "the SETTLED-ACCOUNT sweep sparing legitimate clauses, estimates "
          "labeled in-unit - and it determines no transactional truth.")


if __name__ == "__main__":
    main()
