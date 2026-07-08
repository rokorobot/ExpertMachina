"""v2.0 WS2 - the Exception Stewardship door, end to end over HTTP.

The one ratified human-surface route (the route manifest's first 87->88
amendment) proven as D32 in motion:

  - a HUMAN reviewer writes each of the SEVEN ratified decision kinds
    through POST /api/projects/{id}/stewardship; an AGENT bearer is
    refused 403 on the same route; a phantom key is 404;
  - the vocabulary is enforced at the door: an invalid kind and a missing
    required field are 400; OWNER_ASSIGNED requires a label; owner_principal
    is optional metadata; DUE_DATE_SET stores a declared date and computes
    overdue at read (never stored); CLEARED is an append-only undo;
  - THE QUEUE IS THE JOIN: the computed inbox is byte-identical with every
    stewardship annotation stripped (existence never moves); with the
    annotations it carries latest-per-kind state; a RISK_ACCEPTED HIGH is
    still HIGH and still blocks the compile gate (THE SILENT VETO refused);
  - THE VANISHING TEST: fixing the underlying governed fact removes the
    exception from the computed queue while its full decision history
    remains reconstructable from the ledger alone;
  - decisions append to AuditEvent only - the governed knowledge
    fingerprint is byte-identical through all stewardship writes;
  - exactly ONE new route (88 total, digest re-frozen), MCP still 9, D24
    still 28/305.
"""
import copy
import hashlib
import json
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_stew_ws2_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'ws2.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_stew_ws2_qdrant_")

from fastapi.testclient import TestClient     # noqa: E402
from app import main                          # noqa: E402
from app import (schemas, crud, identity, governance_inbox,  # noqa: E402
                 conflict_engine, stewardship)
import test_workbench_projection              # noqa: E402
import test_route_manifest as route_guard     # noqa: E402


def _login(client, name, password):
    r = client.post("/api/auth/login", json={"name": name, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# Auth/ledger bookkeeping that legitimately churns during an HTTP session
# and is NOT knowledge: the ledger (where decisions land by design),
# credential last_used_at (touched on every authenticated request),
# lazily-minted identity facts, and the principal registry (this test
# creates an AGENT principal mid-run to prove the 403). Guard 7 Part 5
# already proves the RIGOROUS whole-table-except-ledger fingerprint at the
# module level with zero auth churn; here we assert the narrower, honest
# integration claim: stewardship changes no KNOWLEDGE fact.
_NON_KNOWLEDGE = {"audit_events", "credentials", "identity_facts", "principals"}


def knowledge_fingerprint(session):
    """Every governed KNOWLEDGE table - stewardship must change nothing it
    is not (auth/ledger bookkeeping excluded; see _NON_KNOWLEDGE)."""
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


def seed(session):
    """A real computed queue with a HIGH blocker: an unreviewed
    DIRECT_CONTRADICTION (blocks the compile gate) plus an uncovered
    CANDIDATE (an ingestion exception)."""
    officer = identity.create_principal(session, name="ws2officer",
                                        display_name="Officer", kind="HUMAN",
                                        role="ADMIN", created_by="test-suite")
    identity.set_password(session, officer, "ws2officer-password-123",
                          actor="ws2officer")
    reviewer = identity.create_principal(session, name="ws2reviewer",
                                         display_name="Reviewer", kind="HUMAN",
                                         role="GOVERNANCE_REVIEWER",
                                         created_by="test-suite")
    identity.set_password(session, reviewer, "ws2reviewer-password-123",
                          actor="ws2reviewer")
    from app import identity as idmod
    actor = idmod.system_actor(session)
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Stewardship WS2", description="the door", customer_id=customer.id),
        actor=actor)

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
    asset("Uncovered", "New supplier onboarding must follow the sourcing "
                       "process.", status="CANDIDATE")
    model = db.ExpertModel(project_id=project.id, name="WS2 Expert",
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
        verifier_json=json.dumps({"method": "WS2_FIXTURE"})))
    session.commit()
    return project, model, a1, a2


def main_test():
    db.init_db()
    with db.SessionLocal() as boot:
        project, model, a1, a2 = seed(boot)
        project_id = project.id
        model_id = model.id

    with TestClient(main.app) as client:
        REVIEWER = _login(client, "ws2reviewer", "ws2reviewer-password-123")

        # -------------------------------------------------- Part 1
        print("\n--- Part 1: the door exists, exactly one new route ---")
        manifest = route_guard.build_manifest()
        assert len(manifest) == route_guard.FROZEN_ROUTE_COUNT == 88
        assert route_guard.digest(manifest) == route_guard.FROZEN_DIGEST
        stew_routes = [r for r in manifest if "stewardship" in r["path"]]
        assert len(stew_routes) == 1, stew_routes
        assert stew_routes[0]["methods"] == ["POST"]
        assert "require_perm:assets:review" in json.dumps(stew_routes[0]["deps"])
        # MCP surface still 9; D24 still 28/305.
        from app import mcp_gateway as gw
        nine = ("ask_expert", "get_trust_score", "get_provenance",
                "get_conflicts", "check_gate_status", "get_graph_neighbors",
                "get_lineage_path", "get_domain_subgraph", "get_revision_history")
        assert len([n for n in dir(gw) if n in nine]) == 9
        assert "stewardship" not in json.dumps(
            [t for t in dir(gw)]).lower()
        live = {t.name: sorted(c.name for c in t.columns)
                for t in db.Base.metadata.sorted_tables}
        assert live == test_workbench_projection.FROZEN_SCHEMA
        assert (len(live), sum(len(c) for c in live.values())) == (28, 305)
        print("Part 1 passed: 88 routes (digest re-frozen), one stewardship "
              "POST under assets:review; MCP still 9 tools; D24 at 28/305.")

        # -------------------------------------------------- Part 2
        print("\n--- Part 2: the computed queue BEFORE any stewardship ---")
        before = client.get(f"/api/projects/{project_id}/governance/inbox",
                            headers=REVIEWER).json()
        items_before, summary_before = strip_stewardship(before)
        assert all(i["stewardship"] is None for i in before["items"])
        assert before["summary"]["stewarded"] == 0
        high = next(i for i in before["items"] if i["severity"] == "HIGH")
        held = next(i for i in before["items"]
                    if i["type"] == "INGESTION_EXCEPTION")
        with db.SessionLocal() as s:
            gate_before = conflict_engine.evaluate_compile_gate(s, model_id)
            fp_before = knowledge_fingerprint(s)
        assert not gate_before["allowed"], "the contradiction must block compile"
        print(f"Part 2 passed: HIGH exception {high['id']} blocks the gate; "
              f"ingestion exception {held['id']} present; queue unstewarded.")

        # -------------------------------------------------- Part 3
        print("\n--- Part 3: a human writes all seven kinds through the door ---")
        def steward(payload, expect=200):
            r = client.post(f"/api/projects/{project_id}/stewardship",
                            json=payload, headers=REVIEWER)
            assert r.status_code == expect, f"{expect} expected: {r.status_code} {r.text}"
            return r
        steward({"exception_key": high["id"], "kind": "ACKNOWLEDGED"})
        steward({"exception_key": high["id"], "kind": "RISK_ACCEPTED",
                 "reason": "Accepted until the retention harmonization lands."})
        steward({"exception_key": high["id"], "kind": "OWNER_ASSIGNED",
                 "owner_label": "Records Management", "owner_principal_id": None})
        steward({"exception_key": high["id"], "kind": "DUE_DATE_SET",
                 "due_date": "2020-01-01"})   # a past date -> overdue computed
        steward({"exception_key": held["id"], "kind": "DISMISSED",
                 "reason": "Duplicate of the sourcing-process candidate."})
        r = steward({"exception_key": held["id"], "kind": "ESCALATED",
                     "reason": "Owner unresponsive.",
                     "escalated_to": "Procurement lead"})
        assert r.json()["stewardship"]["active"].get("ESCALATED")
        steward({"exception_key": held["id"], "kind": "CLEARED",
                 "reason": "Resolved at standup.", "clears_kind": "ESCALATED"})
        with db.SessionLocal() as s:
            n = s.query(db.AuditEvent).filter_by(
                event_type="STEWARDSHIP_DECISION").count()
        assert n == 7, f"seven decisions expected on the ledger, got {n}"
        print("Part 3 passed: 7 decisions across all seven ratified kinds "
              "recorded through the door.")

        # -------------------------------------------------- Part 4
        print("\n--- Part 4: vocabulary + guards enforced at the door ---")
        steward({"exception_key": high["id"], "kind": "INVENTED"}, expect=400)
        steward({"exception_key": high["id"], "kind": "RISK_ACCEPTED"}, expect=400)
        steward({"exception_key": high["id"], "kind": "OWNER_ASSIGNED"}, expect=400)
        steward({"exception_key": high["id"], "kind": "DUE_DATE_SET",
                 "due_date": "not-a-date"}, expect=400)
        steward({"exception_key": high["id"], "kind": "CLEARED",
                 "reason": "x", "clears_kind": "NONEXISTENT"}, expect=400)
        steward({"exception_key": "CONFLICT-999999", "kind": "ACKNOWLEDGED"},
                expect=404)
        # an AGENT bearer is refused on the door (Guard 7 proves this too;
        # re-proven here through the live HTTP surface).
        with db.SessionLocal() as s:
            agent = identity.create_principal(s, name="ws2-agent",
                                              display_name="Agent", kind="AGENT",
                                              clearance="INTERNAL",
                                              created_by="test-suite")
            token, _c = identity.issue_token(s, agent, kind="API_TOKEN",
                                             label="ws2", actor="test-suite")
        r = client.post(f"/api/projects/{project_id}/stewardship",
                        json={"exception_key": high["id"], "kind": "ACKNOWLEDGED"},
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"AGENT must be refused: {r.status_code}"
        print("Part 4 passed: invalid kind / missing reason / missing owner "
              "label / bad date / bad clears_kind all 400; phantom key 404; "
              "AGENT bearer 403.")

        # -------------------------------------------------- Part 5
        print("\n--- Part 5: THE QUEUE IS THE JOIN (existence never moves) ---")
        after = client.get(f"/api/projects/{project_id}/governance/inbox",
                           headers=REVIEWER).json()
        items_after, summary_after = strip_stewardship(after)
        assert items_after == items_before, \
            "stripping stewardship must reproduce the pre-stewardship queue"
        assert summary_after == summary_before, "existence summary must not move"
        # the annotations are present and correct when included:
        high_after = next(i for i in after["items"] if i["id"] == high["id"])
        active = high_after["stewardship"]["active"]
        assert set(active) == {"ACKNOWLEDGED", "RISK_ACCEPTED", "OWNER_ASSIGNED",
                               "DUE_DATE_SET"}
        assert active["OWNER_ASSIGNED"]["owner_label"] == "Records Management"
        assert high_after["stewardship"]["overdue"] is True, \
            "a past due_date computes overdue at read (never stored)"
        held_after = next(i for i in after["items"] if i["id"] == held["id"])
        # DISMISSED present; ESCALATED cleared by the CLEARED undo:
        assert set(held_after["stewardship"]["active"]) == {"DISMISSED"}, \
            "CLEARED must remove ESCALATED without mutating prior events"
        assert after["summary"]["stewarded"] == 2
        # D2 severity honesty + THE SILENT VETO refused:
        assert high_after["severity"] == "HIGH", "severity must not move"
        with db.SessionLocal() as s:
            gate_after = conflict_engine.evaluate_compile_gate(s, model_id)
        assert gate_after == gate_before, \
            "a risk-accepted HIGH must still block the compile gate"
        print("Part 5 passed: queue byte-identical with annotations stripped; "
              "annotations correct (overdue computed; ESCALATED cleared); "
              "HIGH still HIGH and still blocking.")

        # -------------------------------------------------- Part 6
        print("\n--- Part 6: append-only ledger + knowledge fingerprint ---")
        with db.SessionLocal() as s:
            fp_after = knowledge_fingerprint(s)
            assert fp_after == fp_before, \
                "stewardship wrote outside the ledger - D32 violated"
            events = s.query(db.AuditEvent).filter_by(
                event_type="STEWARDSHIP_DECISION").order_by(db.AuditEvent.id).all()
            assert len(events) == 7, "the 400/404/403 attempts wrote nothing"
            for e in events:
                assert e.identity_fact_id is not None, "decisions are identity-backed"
                d = json.loads(e.details)
                assert d["key_version"] == "inbox-item-v1"
                assert e.target_id == d["exception_key"]
            # the CLEARED event is a NEW row, not a mutation of the ESCALATED one
            kinds = [json.loads(e.details)["kind"] for e in events]
            assert kinds.count("ESCALATED") == 1 and kinds.count("CLEARED") == 1
        print("Part 6 passed: knowledge fingerprint byte-identical; 7 "
              "identity-backed append-only events; CLEARED is a new row, not "
              "an edit.")

        # -------------------------------------------------- Part 7
        print("\n--- Part 7: THE VANISHING TEST ---")
        # fix the underlying governed fact: a human reviews (dismisses) the
        # conflict -> the HIGH exception leaves the computed queue.
        with db.SessionLocal() as s:
            rel = s.query(db.AssetRelationship).filter_by(
                project_id=project_id).first()
            rel.status = "DISMISSED"
            rel.reviewed_by = "ws2reviewer"
            import datetime
            rel.reviewed_at = datetime.datetime.utcnow()
            s.commit()
        vanished = client.get(f"/api/projects/{project_id}/governance/inbox",
                             headers=REVIEWER).json()
        assert not any(i["id"] == high["id"] and i["bucket"] != "RESOLVED"
                       for i in vanished["items"]), \
            "the fixed exception must leave the active queue"
        # its decision history remains reconstructable from the ledger alone:
        with db.SessionLocal() as s:
            history = stewardship.stewardship_for(s, [high["id"]])
        assert history.get(high["id"]), \
            "the stewardship history must survive the exception's disappearance"
        assert history[high["id"]]["history_count"] == 4, \
            "all four decisions on the HIGH exception remain in the ledger"
        print("Part 7 passed: the fixed exception left the computed queue; its "
              "4-decision history remains reconstructable from the ledger "
              "alone - the exception never was a row; its decisions endure.")

    print("\n=== All v2.0 WS2 stewardship-door checks passed: the one "
          "human-surface route records append-only, identity-backed, "
          "spec-valid decisions keyed to the computed exception identity; the "
          "queue is the join; existence, severity, and the gate move only "
          "with governed facts; and the decision history outlives the "
          "exception. 88 routes, 9 MCP tools, 28/305. ===")


if __name__ == "__main__":
    main_test()
