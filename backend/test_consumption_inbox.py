import os
import sys
import json
import hashlib
import re
import tempfile
import inspect

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ.pop("OPENAI_MODEL", None)
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="empkg_inbox_test_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import llm
from app import evaluation
from app import identity
from app import consumption_inbox
from app.main import update_llm_setting
import test_support

# v1.1.x WS2 acceptance suite (docs/workbench-v1.1x.md). The gate: a fully
# computed Consumption Inbox producing items for the nine ratified
# conditions, severity assigned by ONE shared function (D2), missing hops
# declared rather than dropped (D12), and NOTHING persisted - no inbox
# rows, no is_stale, no dismiss/mark-resolved. The suite is a story: facts
# change, items appear; facts change again, items disappear. At no point
# does anything write inbox state.

RATIFIED_TAXONOMY = {
    "BINDING_PACKAGE_HASH_DRIFT": "HIGH",
    "BINDING_PRINCIPAL_INACTIVE": "HIGH",
    "BINDING_CLEARANCE_BELOW_PACKAGE": "HIGH",
    "SELECTION_PACKAGE_HASH_DRIFT": "MEDIUM",
    "SELECTION_PREDATES_NEWER_RUNS": "MEDIUM",
    "SELECTED_MODEL_ABSENT_FROM_LATEST_RUNS": "MEDIUM",
    "EVALUATED_BUT_NO_SELECTION": "LOW",
    "SELECTED_BUT_NO_BINDING": "LOW",
    "BOUND_PRINCIPAL_NO_ACTIVE_CREDENTIAL": "LOW",
}


class FakeConsumerEngine:
    def __call__(self, model, system, user, max_tokens):
        match = re.search(r"\[asset_id (\d+)\][^\n]*\n  Content: ([^\n]+)", system)
        return match.group(2).strip() if match else "No evidence."


def make_asset(session, project, doc, name, text, idx, qa):
    chunk = db.DocumentChunk(document_id=doc.id, text=text, chunk_index=idx)
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    a = crud.create_knowledge_asset(session, schemas.KnowledgeAssetCreate(
        type="POLICY", name=name, content=text, project_id=project.id,
        document_id=doc.id, chunk_id=chunk.id, source_page=1, source_section="S1",
        source_hash=hashlib.sha256(text.encode()).hexdigest()))
    crud.update_knowledge_asset(session, asset_id=a.id,
                                update=schemas.KnowledgeAssetUpdate(status="APPROVED"),
                                actor=qa)
    return a


def run_package_eval(session, qa, project, model, pkg, consumer_model, provider):
    update_llm_setting("package_consumer", schemas.LLMFunctionSettingUpdate(
        model=consumer_model, provider=provider), db_session=session, actor=qa)
    run = evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
        project_id=project.id, expert_model_id=model.id,
        run_type="PACKAGE", agent_package_id=pkg.id))
    evaluation.run_evaluation_batch(session, run.id)
    session.refresh(run)
    assert run.status == "COMPLETED", run.status
    return run


def conditions(inbox, package_id=None):
    return sorted(i["condition"] for i in inbox["items"]
                  if package_id is None or i["package_id"] == package_id)


def the_item(inbox, condition):
    matches = [i for i in inbox["items"] if i["condition"] == condition]
    assert len(matches) == 1, f"expected exactly one {condition}, got {len(matches)}"
    return matches[0]


def row_counts(session):
    return {t.name: session.execute(t.select()).fetchall().__len__()
            for t in db.Base.metadata.sorted_tables}


def main():
    print("\nInitializing test database for Computed Consumption Inbox (WS2) checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = TestingSessionLocal
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    qa = test_support.governed_actor(session, "qa")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Inbox Test", description="WS2", customer_id=customer.id), actor=qa)
    doc = crud.create_document(session, project_id=project.id, filename="Safety.txt",
                               file_path="uploads/s.txt", actor=qa)
    a1 = make_asset(session, project, doc, "Evacuation Protocol",
                    "During thermal runaway, evacuate the battery hall immediately.", 0, qa)
    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Facility Safety Expert", description="", project_id=project.id,
        asset_ids=[a1.id]), actor=qa)
    pkg = crud.create_agent_package(session, schemas.AgentPackageCreate(
        name="Facility Safety Expert", project_id=project.id,
        expert_model_id=model.id, governance_version="1.0",
        clearance_level="INTERNAL"), actor=qa)
    b = db.BenchmarkQuestion(
        project_id=project.id,
        question="What must staff do during thermal runaway in the battery hall?",
        expected_claims_json=json.dumps([]), expected_answer_type="FACTUAL",
        required_citation_count=1, min_required_coverage=0.5)
    session.add(b)
    session.commit()

    saved_adapters = dict(llm.ADAPTERS)
    llm.ADAPTERS["OPENAI"] = FakeConsumerEngine()
    llm.ADAPTERS["ANTHROPIC"] = FakeConsumerEngine()
    try:
        # --- Part 0: the shared severity function IS the ratified taxonomy ---
        print("\n--- Part 0: One shared severity function, the ratified nine ---")
        assert consumption_inbox.SEVERITY_BY_CONDITION == RATIFIED_TAXONOMY, \
            "The severity map must be exactly the nine ratified conditions"
        for cond, sev in RATIFIED_TAXONOMY.items():
            assert consumption_inbox.severity_of(cond) == sev
        try:
            consumption_inbox.severity_of("MADE_UP_CONDITION")
            raise AssertionError("Unknown conditions must be a loud error, never a quiet LOW")
        except KeyError:
            pass
        print("Part 0 passed: severity_of covers exactly the ratified taxonomy and rejects strangers.")

        # --- Part 1: quiet baseline - a package with no evidence raises nothing ---
        print("\n--- Part 1: No evidence, no items ---")
        inbox = consumption_inbox.build_inbox(session, project.id)
        assert inbox["items"] == [], f"Expected an empty inbox, got {conditions(inbox)}"
        print("Part 1 passed: a package without evaluations, selection, or bindings is not a work item.")

        # --- Part 2: evaluated but never selected (LOW) ---
        print("\n--- Part 2: EVALUATED_BUT_NO_SELECTION ---")
        run1 = run_package_eval(session, qa, project, model, pkg, "gpt-4o-mini", "OPENAI")
        run2 = run_package_eval(session, qa, project, model, pkg, "claude-sonnet-4-6", "ANTHROPIC")
        inbox = consumption_inbox.build_inbox(session, project.id)
        assert conditions(inbox) == ["EVALUATED_BUT_NO_SELECTION"]
        item = the_item(inbox, "EVALUATED_BUT_NO_SELECTION")
        assert item["severity"] == "LOW" and item["deep_link"] == f"/?tab=consumption&package={pkg.id}"
        print("Part 2 passed: waiting evidence surfaces as LOW with a workbench deep link.")

        # --- Part 3: selecting clears it; unbound selection surfaces (LOW) ---
        print("\n--- Part 3: SELECTED_BUT_NO_BINDING ---")
        crud.set_package_model_selection(session, pkg.id, schemas.PackageModelSelectionUpdate(
            provider="OPENAI", model="gpt-4o-mini",
            supporting_evaluation_run_ids=[run1.id, run2.id],
            rationale="Initial selection over both runs."), actor=qa)
        inbox = consumption_inbox.build_inbox(session, project.id)
        assert conditions(inbox) == ["SELECTED_BUT_NO_BINDING"], conditions(inbox)
        print("Part 3 passed: the decision exists but serves no one - LOW hygiene, nothing dismissed.")

        # --- Part 4: binding to a credential-less agent (LOW) ---
        print("\n--- Part 4: BOUND_PRINCIPAL_NO_ACTIVE_CREDENTIAL ---")
        agent = identity.create_principal(session, "agent-hall", "Battery Hall Agent",
                                          kind="AGENT", clearance="INTERNAL")
        binding = crud.create_expert_agent_binding(session, pkg.id,
            schemas.ExpertAgentBindingCreate(agent_principal_id=agent.id), actor=qa)
        inbox = consumption_inbox.build_inbox(session, project.id)
        assert conditions(inbox) == ["BOUND_PRINCIPAL_NO_ACTIVE_CREDENTIAL"], conditions(inbox)
        item = the_item(inbox, "BOUND_PRINCIPAL_NO_ACTIVE_CREDENTIAL")
        assert item["binding_id"] == binding.id and item["principal_name"] == "agent-hall"
        print("Part 4 passed: a bound agent that cannot authenticate is declared, not assumed fine.")

        # --- Part 5: clean state + recompute stability ---
        print("\n--- Part 5: clean inbox, stable recomputation ---")
        identity.issue_token(session, agent, label="hall-token", actor="qa")
        first = consumption_inbox.build_inbox(session, project.id)
        second = consumption_inbox.build_inbox(session, project.id)
        assert first["items"] == [] and second["items"] == []
        f, s = dict(first), dict(second)
        f.pop("generated_at"), s.pop("generated_at")
        assert f == s, "Recomputing from the same facts must yield the same inbox"
        print("Part 5 passed: healthy lifecycle = empty inbox; same facts, same result.")

        # --- Part 6: new evidence after the decision (MEDIUM) ---
        print("\n--- Part 6: SELECTION_PREDATES_NEWER_RUNS ---")
        run3 = run_package_eval(session, qa, project, model, pkg, "gpt-4o", "OPENAI")
        inbox = consumption_inbox.build_inbox(session, project.id)
        assert conditions(inbox) == ["SELECTION_PREDATES_NEWER_RUNS"], conditions(inbox)
        assert the_item(inbox, "SELECTION_PREDATES_NEWER_RUNS")["severity"] == "MEDIUM"

        # Re-selecting (a governed act, not a dismissal) clears the item.
        crud.set_package_model_selection(session, pkg.id, schemas.PackageModelSelectionUpdate(
            provider="OPENAI", model="gpt-4o",
            supporting_evaluation_run_ids=[run1.id, run2.id, run3.id],
            rationale="Re-selected over the full comparative evidence set."), actor=qa)
        inbox = consumption_inbox.build_inbox(session, project.id)
        assert inbox["items"] == [], conditions(inbox)
        print("Part 6 passed: items clear by changing facts (re-selection), never by dismissal.")

        # --- Part 7: recompile -> drift (HIGH for the binding, MEDIUM for the selection) ---
        print("\n--- Part 7: hash drift after recompile ---")
        pkg2 = crud.create_agent_package(session, schemas.AgentPackageCreate(
            name="Facility Safety Expert", project_id=project.id,
            expert_model_id=model.id, governance_version="2.0",
            clearance_level="INTERNAL"), actor=qa)
        assert pkg2.package_hash != pkg.package_hash
        inbox = consumption_inbox.build_inbox(session, project.id)
        assert conditions(inbox) == ["BINDING_PACKAGE_HASH_DRIFT", "SELECTION_PACKAGE_HASH_DRIFT"], \
            conditions(inbox)
        drift = the_item(inbox, "BINDING_PACKAGE_HASH_DRIFT")
        assert drift["severity"] == "HIGH" and drift["binding_id"] == binding.id
        assert f"binding={binding.id}" in drift["deep_link"], \
            "Binding items carry the future Binding Explorer target"
        assert the_item(inbox, "SELECTION_PACKAGE_HASH_DRIFT")["severity"] == "MEDIUM"
        # The current artifact has NO completed runs yet: the 'latest
        # successful evaluations' set does not exist, so ABSENT must not
        # fire - absence of evidence is not a fabricated mismatch (D12).
        assert "SELECTED_MODEL_ABSENT_FROM_LATEST_RUNS" not in conditions(inbox)
        # Severity ordering: HIGH strictly before MEDIUM/LOW in the list.
        sev_seq = [i["severity"] for i in inbox["items"]]
        assert sev_seq == sorted(sev_seq, key=lambda s: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[s])
        print("Part 7 passed: recompile makes the old binding HIGH and the old selection MEDIUM.")

        # --- Part 8: identity drift on the binding (HIGH twice) ---
        print("\n--- Part 8: principal inactive / clearance below package ---")
        agent.active = False
        session.commit()
        inbox = consumption_inbox.build_inbox(session, project.id)
        assert "BINDING_PRINCIPAL_INACTIVE" in conditions(inbox)
        assert the_item(inbox, "BINDING_PRINCIPAL_INACTIVE")["severity"] == "HIGH"

        agent.active = True
        agent.clearance = "PUBLIC"  # package is INTERNAL
        session.commit()
        inbox = consumption_inbox.build_inbox(session, project.id)
        assert "BINDING_PRINCIPAL_INACTIVE" not in conditions(inbox)
        assert "BINDING_CLEARANCE_BELOW_PACKAGE" in conditions(inbox)
        low = the_item(inbox, "BINDING_CLEARANCE_BELOW_PACKAGE")
        assert low["severity"] == "HIGH" and "PUBLIC" in low["reason"]
        agent.clearance = "INTERNAL"
        session.commit()
        print("Part 8 passed: identity drift surfaces per binding; restoring identity clears it.")

        # --- Part 9: selected model absent from the latest evaluations (MEDIUM) ---
        print("\n--- Part 9: SELECTED_MODEL_ABSENT_FROM_LATEST_RUNS ---")
        run_package_eval(session, qa, project, model, pkg2, "claude-sonnet-4-6", "ANTHROPIC")
        inbox = consumption_inbox.build_inbox(session, project.id)
        conds = conditions(inbox)
        # The current artifact now HAS latest runs; pkg's selected gpt-4o is
        # not among them. pkg2 is evaluated but unselected (LOW). The old
        # binding still drifts (HIGH).
        assert "SELECTED_MODEL_ABSENT_FROM_LATEST_RUNS" in conds, conds
        assert "EVALUATED_BUT_NO_SELECTION" in conds, conds
        assert "BINDING_PACKAGE_HASH_DRIFT" in conds, conds
        assert the_item(inbox, "EVALUATED_BUT_NO_SELECTION")["package_id"] == pkg2.id
        print("Part 9 passed: stale decisions and waiting evidence coexist, each at its own severity.")

        # --- Part 10: a missing hop is DECLARED, never dropped ---
        print("\n--- Part 10: declared missing hops (D12) ---")
        # Adversarial corruption: principals have no governed delete - rip the
        # row out from under the binding (raw SQL, past the ORM) to create
        # the pathological state the endpoint must declare rather than skip.
        session.execute(db.Principal.__table__.delete().where(
            db.Principal.__table__.c.id == agent.id))
        session.commit()
        session.expire_all()
        inbox = consumption_inbox.build_inbox(session, project.id)
        unverifiable = the_item(inbox, "BINDING_PRINCIPAL_INACTIVE")
        assert unverifiable["severity"] == "HIGH"
        assert any("not found in the registry" in m for m in unverifiable["missing"]), \
            "A binding whose principal cannot be resolved must DECLARE the missing hop"
        assert inbox["summary"]["items_with_declared_missing_hops"] >= 1
        print("Part 10 passed: an unresolvable principal is an unverifiable binding, declared loudly.")

        # --- Part 11: computing the inbox writes NOTHING ---
        print("\n--- Part 11: pure read - zero writes, structural purity ---")
        before = row_counts(session)
        for _ in range(3):
            consumption_inbox.build_inbox(session, project.id)
            consumption_inbox.build_inbox(session, None)  # cross-project scope
        assert row_counts(session) == before, \
            "build_inbox must not create, update, or delete any row in any table"
        # Token scan over CODE (comments stripped - the header narrative may
        # name the anti-patterns it forbids): no write machinery, no staleness
        # column reference.
        source = inspect.getsource(consumption_inbox)
        code_only = "\n".join(line.split("#", 1)[0] for line in source.splitlines())
        for forbidden in ("session.add", ".commit(", "session.delete",
                          "log_audit_event", "is_stale"):
            assert forbidden not in code_only, \
                f"consumption_inbox must stay a pure projection: found '{forbidden}'"
        # No dismiss / mark-resolved: the invariant lives in the ROUTE table.
        # The consumption surface is exactly one path, and it answers GET only.
        from app.main import app as fastapi_app
        consumption_routes = [r for r in fastapi_app.routes
                              if "consumption" in getattr(r, "path", "")]
        assert [r.path for r in consumption_routes] == ["/api/consumption/inbox"], \
            "Exactly the ONE ratified consumption endpoint"
        assert consumption_routes[0].methods == {"GET"}, \
            "No dismiss, no mark-resolved, no writes: GET is the whole surface"
        # Every item everywhere carries the shared function's verdict.
        for i in inbox["items"]:
            assert i["severity"] == consumption_inbox.severity_of(i["condition"])
        print("Part 11 passed: the inbox is a pure projection - no writes, no lifecycle verbs in source.")

    finally:
        llm.ADAPTERS.clear()
        llm.ADAPTERS.update(saved_adapters)

    print("\nAll Consumption Inbox (WS2) checks passed - computed, never stored; "
          "items appear and disappear only when governed facts change.")


if __name__ == "__main__":
    main()
