import os
import sys
import json
import hashlib
import re
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ.pop("OPENAI_MODEL", None)
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="empkg_select_test_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import llm
from app import evaluation
from app.main import update_llm_setting
import test_support

# v1.1 WS3 acceptance suite (docs/consumption-arc-v1.md). The gate:
#
#   Given at least two successful PACKAGE evaluation runs for the same
#   AgentPackage, an operator with permission can select one model for that
#   package. The selection is audited and references the supporting
#   EvaluationRun ids. The selected model must have a successful PACKAGE
#   run for that exact package_hash. Changing the selection creates a new
#   audited decision; old audit remains. Comparison stays computed.
#
# Selection attaches to the PACKAGE layer (ruled at WS2 acceptance):
# ExpertModel is knowledge design, AgentPackage is the frozen artifact,
# binding is deployment - "which model for this artifact?" belongs here.


class FakeConsumerEngine:
    def __init__(self, name):
        self.name = name

    def __call__(self, model, system, user, max_tokens):
        match = re.search(r"\[asset_id (\d+)\][^\n]*\n  Content: ([^\n]+)", system)
        return match.group(2).strip()


def make_asset(session, project, doc, name, text, idx=0):
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
                                actor=test_support.governed_actor(session, "qa"))
    session.refresh(a)
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


def expect_refusal(session, pkg_id, update, fragment, actor):
    try:
        crud.set_package_model_selection(session, pkg_id, update, actor=actor)
        raise AssertionError(f"Selection accepted but should refuse: {fragment}")
    except ValueError as e:
        assert fragment in str(e), f"expected '{fragment}' in: {e}"


def main():
    print("\nInitializing test database for Package Model Selection (WS3) checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = TestingSessionLocal
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    qa = test_support.governed_actor(session, "qa")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Selection Test", description="WS3", customer_id=customer.id), actor=qa)
    doc = crud.create_document(session, project_id=project.id, filename="Safety.txt",
                               file_path="uploads/s.txt", actor=qa)
    a_evac = make_asset(session, project, doc, "Evacuation Protocol",
                        "During thermal runaway, evacuate the battery hall immediately.", 0)
    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Facility Safety Expert", description="", project_id=project.id,
        asset_ids=[a_evac.id]), actor=qa)
    pkg = crud.create_agent_package(session, schemas.AgentPackageCreate(
        name="Facility Safety Expert", project_id=project.id,
        expert_model_id=model.id, governance_version="1.0",
        clearance_level="INTERNAL"), actor=qa)
    # A second, distinct artifact (different governance_version -> different
    # manifest -> different hash) - evidence about it must not transfer.
    pkg_other = crud.create_agent_package(session, schemas.AgentPackageCreate(
        name="Facility Safety Expert", project_id=project.id,
        expert_model_id=model.id, governance_version="2.0",
        clearance_level="INTERNAL"), actor=qa)
    assert pkg_other.package_hash != pkg.package_hash

    b = db.BenchmarkQuestion(
        project_id=project.id,
        question="What must staff do during thermal runaway in the battery hall?",
        expected_claims_json=json.dumps([]), expected_answer_type="FACTUAL",
        required_citation_count=1, min_required_coverage=0.9)
    session.add(b)
    session.commit()

    saved_adapters = dict(llm.ADAPTERS)
    llm.ADAPTERS["OPENAI"] = FakeConsumerEngine("ENGINE-A")
    llm.ADAPTERS["ANTHROPIC"] = FakeConsumerEngine("ENGINE-B")
    try:
        run_a = run_package_eval(session, qa, project, model, pkg, "gpt-4o-mini", "openai")
        run_b = run_package_eval(session, qa, project, model, pkg, "claude-opus-4-8", "anthropic")
        run_other = run_package_eval(session, qa, project, model, pkg_other,
                                     "claude-opus-4-8", "anthropic")
        pending_run = evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
            project_id=project.id, expert_model_id=model.id,
            run_type="PACKAGE", agent_package_id=pkg.id))  # never executed
        live_run = evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
            project_id=project.id, expert_model_id=model.id))  # wrong channel

        # Part 1: selection without valid evidence is refused, case by case.
        print("\n--- Part 1: The boundary validates the proposed evidence ---")
        good = dict(provider="OPENAI", model="gpt-4o-mini",
                    supporting_evaluation_run_ids=[run_a.id, run_b.id],
                    rationale="Best pass rate at lowest cost.")
        expect_refusal(session, pkg.id, schemas.PackageModelSelectionUpdate(
            **{**good, "rationale": "  "}), "requires a rationale", qa)
        expect_refusal(session, pkg.id, schemas.PackageModelSelectionUpdate(
            **{**good, "supporting_evaluation_run_ids": []}), "selection without evidence", qa)
        expect_refusal(session, pkg.id, schemas.PackageModelSelectionUpdate(
            **{**good, "supporting_evaluation_run_ids": [99999]}), "does not exist", qa)
        expect_refusal(session, pkg.id, schemas.PackageModelSelectionUpdate(
            **{**good, "supporting_evaluation_run_ids": [live_run.id]}),
            "PACKAGE-channel only", qa)
        expect_refusal(session, pkg.id, schemas.PackageModelSelectionUpdate(
            **{**good, "supporting_evaluation_run_ids": [pending_run.id]}),
            "not COMPLETED", qa)
        expect_refusal(session, pkg.id, schemas.PackageModelSelectionUpdate(
            **{**good, "supporting_evaluation_run_ids": [run_other.id]}),
            "different package artifact", qa)
        # The selected model must itself have a successful run for THIS hash.
        expect_refusal(session, pkg.id, schemas.PackageModelSelectionUpdate(
            provider="ANTHROPIC", model="claude-haiku-4-5",
            supporting_evaluation_run_ids=[run_a.id, run_b.id],
            rationale="Sounds fast."), "cannot be selected", qa)
        try:
            crud.set_package_model_selection(session, pkg.id + 999,
                                             schemas.PackageModelSelectionUpdate(**good), actor=qa)
            raise AssertionError("Missing package must be a lookup failure")
        except LookupError:
            pass
        assert session.query(db.PackageModelSelection).count() == 0, \
            "No refused proposal may leave a selection behind"
        print("Part 1 passed: rationale, evidence channel, status, hash, and model-run checks hold.")

        # Part 2: THE WS3 GATE - a valid selection over two player runs.
        print("\n--- Part 2: A governed selection with audited evidence ---")
        selection = crud.set_package_model_selection(
            session, pkg.id, schemas.PackageModelSelectionUpdate(**good), actor=qa)
        assert (selection.selected_provider, selection.selected_model_name) == ("OPENAI", "gpt-4o-mini")
        assert selection.package_version == "1.0" and selection.package_hash == pkg.package_hash
        assert selection.supporting_evaluation_run_ids == [run_a.id, run_b.id], \
            "Supporting evidence may include the losing player's run - that IS the comparison"
        assert selection.selected_by_principal_id == qa.principal.id
        assert selection.selected_at is not None
        events = session.query(db.AuditEvent).filter(
            db.AuditEvent.event_type == "PACKAGE_MODEL_SELECTED").all()
        assert len(events) == 1
        details = json.loads(events[0].details)
        assert details["old_selection"] is None
        assert details["new_selection"]["model"] == "gpt-4o-mini"
        assert details["new_selection"]["supporting_evaluation_run_ids"] == [run_a.id, run_b.id]
        assert details["new_selection"]["rationale"] == good["rationale"]
        assert events[0].identity_fact_id is not None, \
            "The selection decision must carry the actor's identity fact"
        print("Part 2 passed: selection persisted with coordinates, evidence, and identity fact.")

        # Part 3: re-selection updates the ONE current row; audit accumulates.
        print("\n--- Part 3: Changing the selection is a new decision, not an edit of history ---")
        first_event_details = events[0].details
        selection2 = crud.set_package_model_selection(
            session, pkg.id, schemas.PackageModelSelectionUpdate(
                provider="ANTHROPIC", model="claude-opus-4-8",
                supporting_evaluation_run_ids=[run_b.id],
                rationale="Higher coverage on the hard questions after re-review."), actor=qa)
        assert selection2.id == selection.id, "One current selection per package"
        assert session.query(db.PackageModelSelection).count() == 1
        assert selection2.selected_model_name == "claude-opus-4-8"
        events = session.query(db.AuditEvent).filter(
            db.AuditEvent.event_type == "PACKAGE_MODEL_SELECTED").order_by(db.AuditEvent.id.asc()).all()
        assert len(events) == 2, "Every selection change is its own audited decision"
        assert events[0].details == first_event_details, "Old audit remains untouched"
        latest = json.loads(events[1].details)
        assert latest["old_selection"]["model"] == "gpt-4o-mini"
        assert latest["new_selection"]["model"] == "claude-opus-4-8"
        print("Part 3 passed: same row, new decision, full old/new lineage in the ledger.")

        # Part 4: comparison stays computed and selection-free.
        print("\n--- Part 4: Comparison compares; selection selects ---")
        comparison = evaluation.package_model_comparison(session, pkg.id)
        assert "selected" not in json.dumps(comparison), \
            "The computed comparison must not carry selection state"
        compared = {(m["provider"], m["model"]) for m in comparison["models"]}
        assert compared == {("OPENAI", "gpt-4o-mini"), ("ANTHROPIC", "claude-opus-4-8")}
        print("Part 4 passed: the comparison view is unchanged by selection.")

        # Part 5: the write surface sits at the approval tier (structural).
        print("\n--- Part 5: Selection requires assets:approve at the route boundary ---")
        main_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "main.py")
        with open(main_src_path, encoding="utf-8") as f:
            src = f.read()
        put_route = src.split('@app.put("/api/packages/{package_id}/model-selection"')[1].split("@app.")[0]
        assert 'require_perm("assets:approve")' in put_route, \
            "Selecting a model is an approval-tier decision"
        get_route = src.split('@app.get("/api/packages/{package_id}/model-selection"')[1].split("@app.")[0]
        assert 'require_perm("assets:read")' in get_route
        print("Part 5 passed: write at assets:approve, read at assets:read.")
    finally:
        llm.ADAPTERS.clear()
        llm.ADAPTERS.update(saved_adapters)

    print("\n=== All Package Model Selection (WS3) tests passed successfully! ===")


if __name__ == "__main__":
    main()
