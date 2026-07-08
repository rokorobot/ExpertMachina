"""v2.0 WS3 - THE MILESTONE GATE for Risk & Exception Stewardship, with
THE STEWARDSHIP PROOF.

D32, proven end to end as a governed constitutional boundary:

    The exception never becomes a row; the human decisions about it do.

The full species of computed exception is seeded through the REAL
machinery - an unreviewed DIRECT_CONTRADICTION (HIGH, blocks the compile
gate), a pending candidate revision, an uncovered CANDIDATE, a
no-evaluation governance warning, a HELD PROPOSAL with unverifiable
synthesis provenance (the vault lane, D29), and a STALE RENDER (the
projection engine's recompose-and-compare, D28). A governance reviewer
stewards across the FULL seven-kind vocabulary THROUGH THE RATIFIED DOOR
(the one POST route, over HTTP), and then the law is proven on the
result:

  - THE ROW TEST: the computed queue is byte-identical with every
    stewardship annotation stripped; no exception-shaped table exists;
    the knowledge fingerprint is unchanged by all stewardship activity;
  - THE LEDGER-ALONE RECONSTRUCTION: an independent re-derivation of the
    stewardship state from raw AuditEvents (latest-per-kind, CLEARED
    undo) equals the module's join exactly;
  - THE OVERDUE SUPERSESSION: a past due date computes overdue at read;
    a NEWER DUE_DATE_SET supersedes it (latest-per-kind wins) and
    overdue recomputes - stored nowhere, ever;
  - THE SILENT VETO refused: risk-accepting the HIGH blocker changes
    neither its severity nor the compile-gate verdict;
  - stewardship never dirties a render: the projection is NOT stale
    after 8 decisions; a governed fact change makes it stale; the stale
    item is itself stewardable;
  - THE VANISHING TEST, three species: dismiss the conflict, approve the
    uncovered candidate, regenerate the render - each exception leaves
    the computed queue while its decision history remains in the ledger,
    honestly joined as ruling on a no-longer-present exception;
  - the boundaries: an AGENT bearer is 403 on the door; the route
    manifest stands at exactly 88 (the one ratified amendment); the MCP
    surface at 9 tools; D24 at 28 tables / 305 columns.

THE COMMERCIAL VERDICT is not automated: the user answers as the
GOVERNANCE OFFICER on the recorded evidence.
"""
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_stew3_render_")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_stew3_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'accept.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_stew3_qdrant_")

from fastapi.testclient import TestClient     # noqa: E402
from app import main                          # noqa: E402
from app import (schemas, crud, identity, connectors,  # noqa: E402
                 conflict_engine, stewardship, tier2, policy)
from app.projections import engine as projection_engine   # noqa: E402
import test_support                           # noqa: E402
import test_workbench_projection              # noqa: E402
import test_route_manifest as route_guard     # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENT_TYPE = "STEWARDSHIP_DECISION"

_NON_KNOWLEDGE = {"audit_events", "credentials", "identity_facts", "principals"}


def knowledge_fingerprint(session):
    h = hashlib.sha256()
    for table in db.Base.metadata.sorted_tables:
        if table.name in _NON_KNOWLEDGE:
            continue
        h.update(table.name.encode())
        for row in session.execute(table.select().order_by(*table.primary_key.columns)):
            h.update(repr(tuple(row)).encode())
    return h.hexdigest()


def strip_stewardship(inbox):
    items = copy.deepcopy(inbox["items"])
    for i in items:
        i.pop("stewardship", None)
    summary = {k: v for k, v in inbox["summary"].items() if k != "stewarded"}
    return items, summary


def independent_reconstruction(session, keys):
    """A from-scratch re-derivation of the stewardship state from raw
    ledger rows - deliberately NOT the module's code path. Latest event
    per (key, kind); CLEARED removes the kind it names. If this equals
    the module's join, the ledger alone carries the whole state."""
    grouped = {}
    for event in session.query(db.AuditEvent).filter(
            db.AuditEvent.event_type == EVENT_TYPE).order_by(db.AuditEvent.id):
        d = json.loads(event.details)
        if d["exception_key"] not in keys:
            continue
        active = grouped.setdefault(d["exception_key"], {})
        if d["kind"] == "CLEARED":
            active.pop(d["clears_kind"], None)
        else:
            active[d["kind"]] = d
    return {k: {kind: {f: d[f] for f in ("kind", "exception_key")}
                for kind, d in active.items()}
            for k, active in grouped.items()}


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


def _login(client, name, password):
    r = client.post("/api/auth/login", json={"name": name, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def seed(session):
    """Every computed-exception species, through the real machinery."""
    for name, role in (("stew3officer", "ADMIN"),
                       ("stew3reviewer", "GOVERNANCE_REVIEWER")):
        p = identity.create_principal(session, name=name, display_name=name,
                                      kind="HUMAN", role=role,
                                      created_by="test-suite")
        identity.set_password(session, p, f"{name}-password-123", actor=name)
    officer = test_support.governed_actor(session, "Stew3Actor")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Stewardship Gate", description="THE MILESTONE GATE",
        customer_id=customer.id), actor=officer)

    def asset(name, content, status="APPROVED"):
        a = db.KnowledgeAsset(project_id=project.id, name=name, content=content,
                              type="POLICY", status=status)
        session.add(a)
        session.commit()
        session.refresh(a)
        return a

    a1 = asset("Retention", "Customer contract records must be retained for "
                            "ten years after contract termination.")
    a2 = asset("Disposal", "Customer contract records must be destroyed three "
                           "years after contract termination.")
    uncovered = asset("Uncovered", "New supplier onboarding must follow the "
                                   "approved sourcing process.",
                      status="CANDIDATE")
    model = db.ExpertModel(project_id=project.id, name="Gate Expert",
                           asset_ids_json=json.dumps([a1.id, a2.id]),
                           asset_count=2)
    session.add(model)
    session.commit()
    session.refresh(model)
    session.add(db.AssetRelationship(
        project_id=project.id, expert_model_id=model.id,
        source_asset_id=a1.id, target_asset_id=a2.id,
        relationship_type="CONFLICTS_WITH", classification="DIRECT_CONTRADICTION",
        confidence=0.99, status="DETECTED",
        verifier_json=json.dumps({"method": "GATE_FIXTURE"})))
    session.commit()
    # a pending candidate revision (the divert path, real machinery)
    crud.update_knowledge_asset(
        session, a2.id,
        schemas.KnowledgeAssetUpdate(
            content="Customer contract records must be destroyed four years "
                    "after contract termination."),
        actor=officer, review_notes="gate: candidate revision")
    # the held proposal with UNVERIFIABLE provenance (the vault lane, D29):
    vault_dir = tempfile.mkdtemp(prefix="em_stew3_vault_")
    result = subprocess.run([sys.executable,
                             os.path.join(REPO_DIR, "vault", "bootstrap.py"),
                             "--vault-dir", vault_dir],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    with open(os.path.join(vault_dir, "08_proposals",
                           "gate-fixture-proposal.md"),
              "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join([
            "---", "em_proposal: 1", "agent_principal: phantom-agent",
            "binding_id: 999999", "package_hash: deadbeef" * 8,
            "workbench: gate-fixture", "cited_assets: ", "---", "",
            "# Held proposal", "",
            "The onboarding checklist must include a security review step.",
            ""]))
    lane = db.SourceConnector(project_id=project.id, name="Proposal Lane",
                              type="LOCAL_FOLDER",
                              root_path=os.path.join(vault_dir, "08_proposals"),
                              include_extensions=".md", lane="PROPOSAL")
    session.add(lane)
    session.commit()
    session.refresh(lane)
    run_scan(session, lane)
    # the projection render (graph): current and NOT stale at seed time
    render = projection_engine.render(session, officer, project.id,
                                      renderer="graph")
    assert render["renderer"] == "graph"
    return project, model, uncovered, officer


def main_test():
    db.init_db()
    with db.SessionLocal() as boot:
        project, model, uncovered, _officer = seed(boot)
        project_id, model_id, uncovered_id = project.id, model.id, uncovered.id

    with TestClient(main.app) as client:
        REVIEWER = _login(client, "stew3reviewer", "stew3reviewer-password-123")

        def inbox():
            r = client.get(f"/api/projects/{project_id}/governance/inbox",
                           headers=REVIEWER)
            assert r.status_code == 200, r.text
            return r.json()

        def steward(payload, expect=200):
            r = client.post(f"/api/projects/{project_id}/stewardship",
                            json=payload, headers=REVIEWER)
            assert r.status_code == expect, f"{expect} != {r.status_code}: {r.text}"
            return r.json() if expect == 200 else None

        # ------------------------------------------------------- Stage 1
        print("\n--- Stage 1: every exception species, computed, unstewarded ---")
        before = inbox()
        by_type = {}
        for item in before["items"]:
            by_type.setdefault(item["type"], []).append(item)
        for species in ("CONFLICT", "REVISION", "INGESTION_EXCEPTION",
                        "GOVERNANCE_WARNING"):
            assert species in by_type, f"species missing: {species}"
        kinds_present = {i.get("classification") for i in
                         by_type["INGESTION_EXCEPTION"]}
        assert "PROPOSAL_PROVENANCE_UNVERIFIED" in kinds_present, \
            "the held proposal with unverifiable provenance must surface"
        assert "NOT_COVERED" in kinds_present
        assert all(i["stewardship"] is None for i in before["items"])
        assert not any(i["type"] == "PROJECTION_STALE" for i in before["items"]), \
            "the fresh render must not be stale"
        high = next(i for i in before["items"] if i["severity"] == "HIGH")
        prop = next(i for i in by_type["INGESTION_EXCEPTION"]
                    if i["classification"] == "PROPOSAL_PROVENANCE_UNVERIFIED")
        unc = next(i for i in by_type["INGESTION_EXCEPTION"]
                   if i["classification"] == "NOT_COVERED")
        warn = by_type["GOVERNANCE_WARNING"][0]
        rev = by_type["REVISION"][0]
        with db.SessionLocal() as s:
            gate_before = conflict_engine.evaluate_compile_gate(s, model_id)
            fp_before = knowledge_fingerprint(s)
        assert not gate_before["allowed"]
        items_before, summary_before = strip_stewardship(before)
        print(f"Stage 1 passed: {len(before['items'])} computed exceptions "
              f"across 4 species incl. the held proposal "
              f"({prop['id']}) and the HIGH blocker ({high['id']}); render "
              f"fresh; queue unstewarded.")

        # ------------------------------------------------------- Stage 2
        print("\n--- Stage 2: the reviewer stewards the full vocabulary, "
              "through the door ---")
        steward({"exception_key": high["id"], "kind": "ACKNOWLEDGED"})
        steward({"exception_key": high["id"], "kind": "RISK_ACCEPTED",
                 "reason": "Retention harmonization scheduled next quarter."})
        steward({"exception_key": high["id"], "kind": "OWNER_ASSIGNED",
                 "owner_label": "Records Management"})
        steward({"exception_key": high["id"], "kind": "DUE_DATE_SET",
                 "due_date": "2020-01-01"})
        steward({"exception_key": prop["id"], "kind": "ESCALATED",
                 "reason": "Unverifiable provenance needs a ruling.",
                 "escalated_to": "Governance officer"})
        steward({"exception_key": unc["id"], "kind": "DISMISSED",
                 "reason": "Duplicate of the sourcing-process work."})
        steward({"exception_key": warn["id"], "kind": "ACKNOWLEDGED"})
        steward({"exception_key": prop["id"], "kind": "CLEARED",
                 "reason": "Escalation resolved: held for the ordinary gate.",
                 "clears_kind": "ESCALATED"})
        steward({"exception_key": rev["id"], "kind": "OWNER_ASSIGNED",
                 "owner_label": "Policy team"})
        with db.SessionLocal() as s:
            n = s.query(db.AuditEvent).filter_by(event_type=EVENT_TYPE).count()
        assert n == 9
        print("Stage 2 passed: 9 decisions across all seven kinds, five "
              "exceptions, four species - every one through the ratified "
              "door.")

        # ------------------------------------------------------- Stage 3
        print("\n--- Stage 3: THE ROW TEST ---")
        after = inbox()
        items_after, summary_after = strip_stewardship(after)
        assert items_after == items_before, \
            "THE ROW TEST: existence must be identical with decisions ignored"
        assert summary_after == summary_before
        assert after["summary"]["stewarded"] == 5
        with db.SessionLocal() as s:
            assert knowledge_fingerprint(s) == fp_before, \
                "stewardship changed a knowledge fact - D32 violated"
            live = {t.name: sorted(c.name for c in t.columns)
                    for t in db.Base.metadata.sorted_tables}
            assert live == test_workbench_projection.FROZEN_SCHEMA
            for name in live:
                assert "exception" not in name.lower() and \
                    "stewardship" not in name.lower()
        # stewardship never dirties a render:
        assert not any(i["type"] == "PROJECTION_STALE" for i in after["items"]), \
            "9 ledger decisions must not make the projection stale"
        print("Stage 3 passed: the queue byte-identical stripped; knowledge "
              "fingerprint unchanged; no exception-shaped table (D24 "
              "28/305); the render still fresh after 9 decisions.")

        # ------------------------------------------------------- Stage 4
        print("\n--- Stage 4: THE LEDGER-ALONE RECONSTRUCTION + overdue ---")
        keys = {high["id"], prop["id"], unc["id"], warn["id"], rev["id"]}
        with db.SessionLocal() as s:
            module_join = stewardship.stewardship_for(s, keys)
            independent = independent_reconstruction(s, keys)
        module_shape = {k: {kind: {"kind": d["kind"],
                                   "exception_key": d["exception_key"]}
                            for kind, d in v["active"].items()}
                        for k, v in module_join.items()}
        assert module_shape == independent, \
            "the module's join must equal the from-scratch ledger re-derivation"
        assert set(module_join[prop["id"]]["active"]) == set(), \
            "CLEARED removed the only decision kind on the proposal"
        assert module_join[high["id"]]["overdue"] is True
        # supersession: a NEWER DUE_DATE_SET wins; overdue recomputes
        steward({"exception_key": high["id"], "kind": "DUE_DATE_SET",
                 "due_date": "2999-12-31"})
        with db.SessionLocal() as s:
            refreshed = stewardship.stewardship_for(s, [high["id"]])
        assert refreshed[high["id"]]["overdue"] is False, \
            "the latest declared due date wins; overdue recomputes at read"
        assert refreshed[high["id"]]["history_count"] == 5
        print("Stage 4 passed: an independent raw-ledger re-derivation equals "
              "the module's join; CLEARED emptied the proposal's state while "
              "its history stands; overdue recomputed FALSE under the "
              "superseding due date - stored nowhere.")

        # ------------------------------------------------------- Stage 5
        print("\n--- Stage 5: THE SILENT VETO refused + the AGENT boundary ---")
        latest = inbox()
        high_now = next(i for i in latest["items"] if i["id"] == high["id"])
        assert high_now["severity"] == "HIGH"
        with db.SessionLocal() as s:
            assert conflict_engine.evaluate_compile_gate(s, model_id) == \
                gate_before, "the risk-accepted HIGH must still block compile"
        with db.SessionLocal() as s:
            agent = identity.create_principal(s, name="stew3-agent",
                                              display_name="Agent",
                                              kind="AGENT", clearance="INTERNAL",
                                              created_by="test-suite")
            token, _c = identity.issue_token(s, agent, kind="API_TOKEN",
                                             label="gate", actor="test-suite")
        r = client.post(f"/api/projects/{project_id}/stewardship",
                        json={"exception_key": high["id"],
                              "kind": "ACKNOWLEDGED"},
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403
        print("Stage 5 passed: severity and the compile gate unmoved by "
              "risk acceptance; the AGENT bearer refused 403 on the door.")

        # ------------------------------------------------------- Stage 6
        print("\n--- Stage 6: a fact change makes the render stale; the "
              "stale item is stewardable ---")
        with db.SessionLocal() as s:
            actor = test_support.governed_actor(s, "Stew3Actor")
            a3 = db.KnowledgeAsset(project_id=project_id, name="New policy",
                                   content="Visitors must sign the register "
                                           "at reception.",
                                   type="POLICY", status="APPROVED")
            s.add(a3)
            s.commit()
        stale_view = inbox()
        stale_items = [i for i in stale_view["items"]
                       if i["type"] == "PROJECTION_STALE"]
        assert stale_items, "a governed fact change must surface staleness"
        steward({"exception_key": stale_items[0]["id"], "kind": "ACKNOWLEDGED"})
        print(f"Stage 6 passed: the render went stale on a governed fact "
              f"change ({stale_items[0]['id']}) and took an ACKNOWLEDGED "
              f"decision like any exception.")

        # ------------------------------------------------------- Stage 7
        print("\n--- Stage 7: THE VANISHING TEST (three species) ---")
        with db.SessionLocal() as s:
            actor = test_support.governed_actor(s, "Stew3Actor")
            # 1. review the conflict (the governed fix)
            import datetime
            rel = s.query(db.AssetRelationship).filter_by(
                project_id=project_id).first()
            rel.status = "DISMISSED"
            rel.reviewed_by = "stew3reviewer"
            rel.reviewed_at = datetime.datetime.utcnow()
            # 2. approve the uncovered candidate (the human review)
            crud.update_knowledge_asset(
                s, uncovered_id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
                actor=actor, review_notes="gate: reviewed")
            s.commit()
            # 3. regenerate the render (staleness repaired by regeneration)
            projection_engine.render(s, actor, project_id, renderer="graph")
        final = inbox()
        active_ids = {i["id"] for i in final["items"]
                      if i["bucket"] != "RESOLVED"}
        assert high["id"] not in active_ids, "the dismissed conflict left"
        assert unc["id"] not in active_ids, "the approved candidate left"
        assert not any(i["type"] == "PROJECTION_STALE" for i in final["items"]
                       if i["bucket"] != "RESOLVED"), "regeneration cured staleness"
        with db.SessionLocal() as s:
            history = stewardship.stewardship_for(
                s, [high["id"], unc["id"], stale_items[0]["id"]])
        assert history[high["id"]]["history_count"] == 5
        assert history[unc["id"]]["history_count"] == 1
        assert history[stale_items[0]["id"]]["history_count"] == 1
        print("Stage 7 passed: three species vanished with their governed "
              "fixes (review, approval, regeneration); 7 decisions on the "
              "vanished exceptions remain reconstructable from the ledger "
              "alone - history outlives existence.")

        # ------------------------------------------------------- Stage 8
        print("\n--- Stage 8: THE CLOSING LINES ---")
        manifest = route_guard.build_manifest()
        assert len(manifest) == 88
        assert route_guard.digest(manifest) == route_guard.FROZEN_DIGEST
        assert len([r for r in manifest if "stewardship" in r["path"]]) == 1
        from app import mcp_gateway as gw
        nine = ("ask_expert", "get_trust_score", "get_provenance",
                "get_conflicts", "check_gate_status", "get_graph_neighbors",
                "get_lineage_path", "get_domain_subgraph",
                "get_revision_history")
        assert len([n for n in dir(gw) if n in nine]) == 9
        with db.SessionLocal() as s:
            live = {t.name: sorted(c.name for c in t.columns)
                    for t in db.Base.metadata.sorted_tables}
            tables, columns = len(live), sum(len(c) for c in live.values())
            assert (tables, columns) == (28, 305)
            for e in s.query(db.AuditEvent).filter_by(
                    event_type=EVENT_TYPE).all():
                assert e.identity_fact_id is not None
                fact = s.query(db.IdentityFact).filter_by(
                    id=e.identity_fact_id).first()
                assert fact.principal_kind == "HUMAN", \
                    "every stewardship decision was made by a HUMAN"
        print(f"Stage 8 passed: route manifest at exactly 88 (the one "
              f"ratified amendment); MCP at 9; D24 at {tables}/{columns}; "
              f"every decision on the ledger carries a HUMAN identity fact.")

    print("\n=== THE v2.0 MILESTONE GATE PASSED: the exception never became "
          "a row - existence computed from governed facts alone, identical "
          "with every decision ignored; the human decisions about it do - "
          "append-only, identity-backed, reconstructable from the ledger "
          "alone, surviving the exceptions they ruled on; severity and the "
          "gate never moved; no agent held the pen. 88 routes, 9 tools, "
          "28 tables / 305 columns. ===")


if __name__ == "__main__":
    main_test()
