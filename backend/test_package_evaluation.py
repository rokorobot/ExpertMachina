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
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="empkg_eval_test_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import llm
from app import evaluation
from app.main import update_llm_setting
import test_support

# v1.1 WS2 acceptance suite (docs/consumption-arc-v1.md). The gate:
#
#   Given one .empkg and the same benchmark questions, run PACKAGE
#   evaluations across at least two configured consumer models, persist
#   EvaluationRun with package_version + consumer_model, persist immutable
#   ClaimVerdicts, report unrun models as absent (not zero), and prove the
#   referee is not one of the player models.
#
# Channel rule under test: LIVE runs carry no package coordinates; PACKAGE
# runs require them, resolved through D19 config (callers propose nothing).
# Hard boundary: the package channel answers through package_consumer ONLY -
# proven here by drifting the DB content away from the packaged content and
# by failing a run rather than mislabeling it when config changes mid-flight.


class FakeConsumerEngine:
    """A player model at the llm.ADAPTERS seam. Echoes the top-ranked
    packaged evidence verbatim (so the referee can entail it) and honors
    the packaged refusal contract for out-of-knowledge questions."""

    def __init__(self, name):
        self.name = name
        self.calls = []

    def __call__(self, model, system, user, max_tokens):
        self.calls.append({"model": model, "user": user})
        if "France" in user:
            return ("INSUFFICIENT EVIDENCE - this question is outside the "
                    "governed knowledge of this expert package.")
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


def add_benchmark(session, project_id, question, answer_type, min_coverage=0.9):
    b = db.BenchmarkQuestion(
        project_id=project_id, question=question,
        expected_claims_json=json.dumps([]), expected_answer_type=answer_type,
        required_citation_count=1 if answer_type != "REFUSAL" else 0,
        min_required_coverage=min_coverage)
    session.add(b)
    session.commit()
    session.refresh(b)
    return b


def configure_consumer(session, actor, model, provider=None):
    update_llm_setting("package_consumer", schemas.LLMFunctionSettingUpdate(
        model=model, provider=provider), db_session=session, actor=actor)


def main():
    print("\nInitializing test database for Package Evaluation (WS2) checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = TestingSessionLocal
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    qa = test_support.governed_actor(session, "qa")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Package Eval", description="WS2", customer_id=customer.id), actor=qa)
    doc = crud.create_document(session, project_id=project.id, filename="Safety.txt",
                               file_path="uploads/s.txt", actor=qa)

    a_evac = make_asset(session, project, doc, "Evacuation Protocol",
                        "During thermal runaway, evacuate the battery hall immediately.", 0)
    a_logs = make_asset(session, project, doc, "Shutdown Logs",
                        "Facility Manager signs shutdown logs within 24 hours after evacuation.", 1)

    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Facility Safety Expert", description="", project_id=project.id,
        asset_ids=[a_evac.id, a_logs.id]), actor=qa)
    pkg = crud.create_agent_package(session, schemas.AgentPackageCreate(
        name="Facility Safety Expert", project_id=project.id,
        expert_model_id=model.id, governance_version="1.0",
        clearance_level="INTERNAL"), actor=qa)

    add_benchmark(session, project.id,
                  "What must staff do during thermal runaway in the battery hall?", "FACTUAL")
    add_benchmark(session, project.id, "What is the capital of France?", "REFUSAL")

    # Part 1: the channel rule at creation time.
    print("\n--- Part 1: LIVE refuses package coordinates; PACKAGE requires them ---")
    try:
        evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
            project_id=project.id, expert_model_id=model.id, agent_package_id=pkg.id))
        raise AssertionError("LIVE run accepted package coordinates")
    except ValueError as e:
        assert "no package coordinates" in str(e), str(e)
    try:
        evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
            project_id=project.id, expert_model_id=model.id, run_type="PACKAGE"))
        raise AssertionError("PACKAGE run accepted without agent_package_id")
    except ValueError as e:
        assert "require agent_package_id" in str(e), str(e)
    try:
        evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
            project_id=project.id, expert_model_id=model.id + 999,
            run_type="PACKAGE", agent_package_id=pkg.id))
        raise AssertionError("Missing expert model must be a lookup failure")
    except LookupError:
        pass
    try:
        evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
            project_id=project.id, expert_model_id=model.id,
            run_type="PACKAGE", agent_package_id=pkg.id + 999))
        raise AssertionError("Missing package must be a lookup failure")
    except LookupError:
        pass
    live_run = evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
        project_id=project.id, expert_model_id=model.id))
    assert live_run.run_type == "LIVE" and live_run.package_hash is None \
        and live_run.consumer_model_name is None
    print("Part 1 passed: channel rules enforced at creation; LIVE carries no coordinates.")

    # Part 2: THE WS2 GATE - one .empkg, same questions, two configured
    # consumer models, coordinates + immutable verdicts persisted.
    print("\n--- Part 2: Two PACKAGE evaluations across two configured models ---")
    engine_a, engine_b = FakeConsumerEngine("ENGINE-A"), FakeConsumerEngine("ENGINE-B")
    saved_adapters = dict(llm.ADAPTERS)
    llm.ADAPTERS["OPENAI"], llm.ADAPTERS["ANTHROPIC"] = engine_a, engine_b
    try:
        configure_consumer(session, qa, "gpt-4o-mini", provider="openai")
        run_a = evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
            project_id=project.id, expert_model_id=model.id,
            run_type="PACKAGE", agent_package_id=pkg.id))
        assert run_a.run_type == "PACKAGE"
        assert run_a.package_version == "1.0" and run_a.package_hash == pkg.package_hash
        assert (run_a.consumer_model_provider, run_a.consumer_model_name) == ("OPENAI", "gpt-4o-mini")
        assert set(json.loads(run_a.asset_ids_snapshot)) == {a_evac.id, a_logs.id}, \
            "PACKAGE run snapshot must be the packaged assets"
        evaluation.run_evaluation_batch(session, run_a.id)
        session.refresh(run_a)
        assert run_a.status == "COMPLETED", run_a.status
        assert run_a.pass_rate == 1.0, f"factual + refusal should both pass: {run_a.pass_rate}"
        assert engine_a.calls, "Player A was never consulted"

        configure_consumer(session, qa, "claude-opus-4-8", provider="anthropic")
        run_b = evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
            project_id=project.id, expert_model_id=model.id,
            run_type="PACKAGE", agent_package_id=pkg.id))
        assert (run_b.consumer_model_provider, run_b.consumer_model_name) == ("ANTHROPIC", "claude-opus-4-8")
        evaluation.run_evaluation_batch(session, run_b.id)
        session.refresh(run_b)
        assert run_b.status == "COMPLETED" and run_b.pass_rate == 1.0
        assert engine_b.calls, "Player B was never consulted"

        verdicts_a = session.query(db.ClaimVerdict).filter(
            db.ClaimVerdict.evaluation_run_id == run_a.id).all()
        verdicts_b = session.query(db.ClaimVerdict).filter(
            db.ClaimVerdict.evaluation_run_id == run_b.id).all()
        assert verdicts_a and verdicts_b, "ClaimVerdicts must persist on the package channel"
        assert all(v.verdict == "ENTAILED" for v in verdicts_a), \
            [v.verdict for v in verdicts_a]
        refusal_results = session.query(db.EvaluationQuestionResult).filter(
            db.EvaluationQuestionResult.evaluation_run_id == run_a.id,
            db.EvaluationQuestionResult.generated_answer == "INSUFFICIENT EVIDENCE").all()
        assert len(refusal_results) == 1 and refusal_results[0].passed, \
            "The refusal contract must pass the REFUSAL benchmark"
        assert not refusal_results[0].claim_verdicts, \
            "A refusal is policy compliance, not a knowledge claim - no verdicts (D12)"
        print("Part 2 passed: coordinates persisted, verdicts persisted, both players ran.")

        # Part 3: the referee is not one of the players.
        print("\n--- Part 3: Referee independence ---")
        referee_a = {v.verifier_json for v in verdicts_a}
        referee_b = {v.verifier_json for v in verdicts_b}
        assert referee_a == referee_b, "The referee must be identical across player runs"
        referee = json.loads(verdicts_a[0].verifier_json)
        for player in ("gpt-4o-mini", "claude-opus-4-8", "ENGINE-A", "ENGINE-B"):
            assert player not in (referee.get("model_id") or ""), \
                f"Referee identity names a player: {referee}"
        assert all(v.evaluator_id == "verification_engine" for v in verdicts_a + verdicts_b)
        print(f"Part 3 passed: one referee ({referee['method']}) judged both players.")

        # Part 4: no live DB retrieval - drift the database away from the
        # package; the evaluated evidence must stay the packaged content.
        print("\n--- Part 4: Database drift cannot reach a PACKAGE run ---")
        packaged_content = a_evac.content
        a_evac.content = "DRIFTED: do NOT evacuate; await further instructions."
        session.commit()
        run_c = evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
            project_id=project.id, expert_model_id=model.id,
            run_type="PACKAGE", agent_package_id=pkg.id))
        evaluation.run_evaluation_batch(session, run_c.id)
        session.refresh(run_c)
        assert run_c.status == "COMPLETED"
        factual = session.query(db.EvaluationQuestionResult).filter(
            db.EvaluationQuestionResult.evaluation_run_id == run_c.id,
            db.EvaluationQuestionResult.generated_answer != "INSUFFICIENT EVIDENCE").first()
        cited = {c["asset_id"]: c["content"] for c in json.loads(factual.citations_json)}
        assert cited[a_evac.id] == packaged_content, \
            "PACKAGE-run evidence must come from the .empkg, not the drifted database"
        assert "DRIFTED" not in factual.generated_answer
        print("Part 4 passed: the package, not the database, is the knowledge universe.")

        # Part 5: a run FAILS rather than mislabels when config drifts
        # between creation and execution (D12).
        print("\n--- Part 5: Mid-flight consumer drift fails the run honestly ---")
        run_d = evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
            project_id=project.id, expert_model_id=model.id,
            run_type="PACKAGE", agent_package_id=pkg.id))
        assert run_d.consumer_model_provider == "ANTHROPIC"
        configure_consumer(session, qa, "gpt-4o-mini", provider="openai")  # the drift
        evaluation.run_evaluation_batch(session, run_d.id)
        session.refresh(run_d)
        assert run_d.status == "FAILED", \
            "A run whose recorded model did not answer must FAIL, never mislabel"
        assert session.query(db.EvaluationQuestionResult).filter(
            db.EvaluationQuestionResult.evaluation_run_id == run_d.id).count() == 0, \
            "A failed run must not keep partial results as if measured"
        print("Part 5 passed: recorded coordinates are binding - drift fails the run.")

        # Part 6: comparison is computed; unrun models are ABSENT, not zero.
        print("\n--- Part 6: Computed model comparison (absent, not zero) ---")
        comparison = evaluation.package_model_comparison(session, pkg.id)
        assert comparison["package_hash"] == pkg.package_hash
        assert comparison["package_version"] == "1.0"
        compared = {(m["provider"], m["model"]) for m in comparison["models"]}
        assert compared == {("OPENAI", "gpt-4o-mini"), ("ANTHROPIC", "claude-opus-4-8")}, compared
        # Never-run models (e.g. claude-haiku-4-5) are absent - no zero rows.
        assert not any(m["model"] == "claude-haiku-4-5" for m in comparison["models"])
        # The FAILED drift run contributes nothing.
        all_run_ids = {r["run_id"] for m in comparison["models"] for r in m["runs"]}
        assert run_d.id not in all_run_ids, "FAILED runs must not appear in the comparison"
        anthropic_runs = next(m for m in comparison["models"] if m["provider"] == "ANTHROPIC")
        assert {r["run_id"] for r in anthropic_runs["runs"]} == {run_b.id, run_c.id}
        assert anthropic_runs["latest"]["run_id"] == run_c.id
        assert all(m["latest"]["pass_rate"] == 1.0 for m in comparison["models"])
        print("Part 6 passed: comparison computed from run facts; nothing persisted, nothing zeroed.")

        # Part 7: the channels stay separate in reads - coverage_trend
        # tracks the governed knowledge base (LIVE), never frozen artifacts.
        print("\n--- Part 7: coverage_trend excludes PACKAGE runs ---")
        trend = evaluation.coverage_trend(session, model.id)
        assert trend["runs"] == [], \
            f"PACKAGE runs must not appear in the live coverage trend: {trend['runs']}"
        print("Part 7 passed: PACKAGE runs measure the artifact, not the knowledge base trend.")
    finally:
        llm.ADAPTERS.clear()
        llm.ADAPTERS.update(saved_adapters)

    print("\n=== All Package Evaluation (WS2) tests passed successfully! ===")


if __name__ == "__main__":
    main()
