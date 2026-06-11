import os
import sys
import json
import hashlib
import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import evaluation
from app import governance_inbox
from app import main as app_main
import test_support


def make_fixture(session):
    customer = crud.get_or_create_default_customer(session)
    qa = test_support.governed_actor(session, "qa")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Verdict Test", description="Persisted verification verdicts", customer_id=customer.id), actor=qa)
    doc = crud.create_document(session, project_id=project.id, filename="SLA.txt", file_path="uploads/sla.txt", actor=qa)
    text = "Deliveries exceeding SLA deadline by 48 hours receive 15% refund."
    chunk = db.DocumentChunk(document_id=doc.id, text=text, chunk_index=0)
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    asset = crud.create_knowledge_asset(session, schemas.KnowledgeAssetCreate(
        type="POLICY", name="SLA Refund Policy", content=text, project_id=project.id,
        document_id=doc.id, chunk_id=chunk.id, source_page=1, source_section="S1",
        source_hash=hashlib.sha256(text.encode()).hexdigest()))
    crud.update_knowledge_asset(session, asset_id=asset.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor=qa)
    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Verdict Expert", description="", project_id=project.id, asset_ids=[asset.id]), actor=qa)
    crud.create_benchmark_question(session, schemas.BenchmarkQuestionCreate(
        project_id=project.id, question="What is the SLA refund percentage?",
        expected_claims=[text], expected_answer_type="FACTUAL",
        required_citation_count=1, severity="MEDIUM", min_required_coverage=0.95))
    return project, model, asset


def add_verdict(session, project, model, run_id, result_id, verdict, claim, confidence=0.9):
    v = db.ClaimVerdict(
        project_id=project.id, expert_model_id=model.id, evaluation_run_id=run_id,
        question_result_id=result_id, benchmark_question_id=None,
        claim=claim, verdict=verdict, confidence=confidence,
        supporting_asset_ids_json="[]", contradicting_asset_ids_json="[]",
        verifier_json=json.dumps({"method": "TEST_FIXTURE"}),
        evaluator_type="AUTOMATED", evaluator_id="verification_engine")
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


def main():
    print("\nInitializing test database for Persisted Verification Verdict checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    project, model, asset = make_fixture(session)

    # Part 1: evaluation runs persist one verdict per judged claim.
    print("\n--- Part 1: Evaluation run persists claim verdicts with full provenance ---")
    run = evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
        project_id=project.id, expert_model_id=model.id))
    evaluation.run_evaluation_batch(session, run.id)
    session.refresh(run)
    assert run.status == "COMPLETED"
    verdicts = session.query(db.ClaimVerdict).filter(db.ClaimVerdict.evaluation_run_id == run.id).all()
    assert len(verdicts) >= 1, "No claim verdicts persisted by the evaluation run"
    results = session.query(db.EvaluationQuestionResult).filter(
        db.EvaluationQuestionResult.evaluation_run_id == run.id).all()
    result_ids = {r.id for r in results}
    for v in verdicts:
        assert v.verdict in ("ENTAILED", "CONTRADICTED", "UNSUPPORTED")
        assert v.question_result_id in result_ids, "Verdict not linked to a question result"
        assert v.expert_model_id == model.id and v.project_id == project.id
        assert v.evaluator_type == "AUTOMATED" and v.evaluator_id == "verification_engine"
        assert v.verifier and v.verifier.get("method"), "Verifier identity snapshot missing"
        assert v.created_at is not None
    print(f"Part 1 passed: {len(verdicts)} verdicts persisted, all linked and provenance-stamped.")

    # Part 2: verdicts are immutable artifacts - no workflow state by design.
    print("\n--- Part 2: ClaimVerdict carries no mutable review state ---")
    assert not hasattr(db.ClaimVerdict, "status"), "ClaimVerdict must NOT have a status column"
    assert not hasattr(db.ClaimVerdict, "reviewed_by"), "ClaimVerdict must NOT carry reviewer state"
    print("Part 2 passed: no status, no reviewer fields - measurement, not workflow object.")

    # Part 3: evidence gaps appear in the governance inbox from the latest run.
    print("\n--- Part 3: EVIDENCE_GAP inbox items from latest completed run ---")
    result_id = results[0].id
    gap_unsup = add_verdict(session, project, model, run.id, result_id, "UNSUPPORTED",
                            "All adverse events must be reported within 24 hours.", 0.88)
    gap_contra = add_verdict(session, project, model, run.id, result_id, "CONTRADICTED",
                             "Refund applies after 12 hours of delay.", 0.97)
    inbox = governance_inbox.build_inbox(session, project.id)
    gaps = {i["source_id"]: i for i in inbox["items"] if i["type"] == "EVIDENCE_GAP"}
    assert gap_unsup.id in gaps and gap_contra.id in gaps
    unsup_item = gaps[gap_unsup.id]
    contra_item = gaps[gap_contra.id]
    assert unsup_item["severity"] == "LOW" and unsup_item["bucket"] == "CAN_WAIT"
    assert contra_item["severity"] == "MEDIUM" and contra_item["bucket"] == "NEEDS_REVIEW"
    assert contra_item["deep_link"] == f"/?tab=evaluations&run={run.id}&result={result_id}"
    # HIGH remains gate-blocking-only: no evidence gap may ever be HIGH.
    assert all(i["severity"] != "HIGH" for i in inbox["items"] if i["type"] == "EVIDENCE_GAP")
    print("Part 3 passed: gaps surfaced with correct severity, bucket, and scorecard deep link.")

    # Part 4: only the LATEST completed run feeds the inbox (no cross-run state).
    print("\n--- Part 4: Superseded runs drop out of the inbox automatically ---")
    run2 = evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
        project_id=project.id, expert_model_id=model.id))
    evaluation.run_evaluation_batch(session, run2.id)
    inbox = governance_inbox.build_inbox(session, project.id)
    stale = [i for i in inbox["items"] if i["type"] == "EVIDENCE_GAP" and i["source_id"] in (gap_unsup.id, gap_contra.id)]
    assert not stale, "Gaps from a superseded run must disappear once a newer run completes"
    print("Part 4 passed: latest-run rule supersedes old gaps without any mutable state.")

    # Part 5: reviewing a verdict logs VERIFICATION_REVIEWED and mutates nothing.
    print("\n--- Part 5: VERIFICATION_REVIEWED audit event; verdict row untouched ---")
    before = (gap_unsup.verdict, gap_unsup.confidence, gap_unsup.evaluator_id)
    response = app_main.review_claim_verdict(
        gap_unsup.id,
        schemas.VerificationReviewCreate(comment="Evidence exists in SOP-17 appendix."),
        db_session=session, actor=test_support.governed_actor(session, "robert"))
    assert response["event_type"] == "VERIFICATION_REVIEWED"
    event = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "VERIFICATION_REVIEWED",
        db.AuditEvent.target_id == str(gap_unsup.id)).first()
    assert event is not None and event.actor == "robert"
    details = json.loads(event.details)
    assert details["verdict_seen"] == "UNSUPPORTED"
    assert details["comment"] == "Evidence exists in SOP-17 appendix."
    session.refresh(gap_unsup)
    assert (gap_unsup.verdict, gap_unsup.confidence, gap_unsup.evaluator_id) == before, \
        "Review must never mutate the verdict artifact"
    print("Part 5 passed: human judgment recorded in the audit ledger, artifact immutable.")

    # Part 6: coverage trend over completed runs (MVP 0.9.3).
    print("\n--- Part 6: Coverage trend reports runs oldest-first with honest verdict metrics ---")
    trend = evaluation.coverage_trend(session, model.id)
    run_ids = [p["run_id"] for p in trend["runs"]]
    assert run_ids == sorted(run_ids), "Trend must be ordered oldest-first"
    assert len(run_ids) == 2, f"Expected both completed runs in the trend: {run_ids}"
    first, second = trend["runs"]
    # Run 1 had real verdicts (incl. the two injected gaps); run 2 only its own.
    assert first["claims_total"] and first["verdict_counts"]["UNSUPPORTED"] >= 1
    assert first["supported_pct"] is not None
    assert second["claims_total"] >= 1 and second["supported_pct"] is not None
    # A run with no verdicts must report None, never fabricated zeros.
    bare_run = db.EvaluationRun(
        project_id=project.id, expert_model_id=model.id,
        asset_ids_snapshot="[]", asset_hashes_snapshot="{}",
        benchmark_question_ids_snapshot="[]", status="COMPLETED",
        completed_at=datetime.datetime.utcnow())
    session.add(bare_run)
    session.commit()
    trend = evaluation.coverage_trend(session, model.id)
    bare = next(p for p in trend["runs"] if p["run_id"] == bare_run.id)
    assert bare["claims_total"] is None and bare["verdict_counts"] is None and bare["supported_pct"] is None
    print("Part 6 passed: trend is ordered, measured, and never fabricates verdict data.")

    print("\n=== All Persisted Verification Verdict tests passed successfully! ===")


if __name__ == "__main__":
    main()
