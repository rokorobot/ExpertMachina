import os
import sys
import json
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import database as db
from app import schemas
from app import crud
from app import evaluation

def test_evaluation_engine():
    print("\nInitializing database for Evaluation Engine checks...")
    TEST_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Prepopulate default customer
    customer = crud.get_or_create_default_customer(session)
    
    # Create Project
    project = crud.create_project(
        session, 
        schemas.ProjectCreate(name="Evaluation Validation Project", description="Benchmarking tests", customer_id=customer.id)
    )
    
    # Create mock document and chunk
    doc = crud.create_document(session, project_id=project.id, filename="SLA_Refund.txt", file_path="uploads/SLA_Refund.txt")
    chunk = db.DocumentChunk(document_id=doc.id, text="Deliveries exceeding SLA deadline by 48 hours receive 15% refund.", chunk_index=0)
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    
    correct_hash = hashlib.sha256(chunk.text.encode('utf-8')).hexdigest()
    
    # Create approved Asset
    asset = crud.create_knowledge_asset(
        session,
        schemas.KnowledgeAssetCreate(
            type="POLICY",
            name="SLA Refund Policy",
            content="Deliveries exceeding SLA deadline by 48 hours receive 15% refund.",
            project_id=project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            source_page=1,
            source_section="Refund SLA",
            source_hash=correct_hash
        )
    )
    crud.update_knowledge_asset(session, asset_id=asset.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor="Admin")

    # Build Expert Model with SLA asset
    model = crud.create_expert_model(
        session,
        schemas.ExpertModelCreate(name="Refund Expert", description="SLA rules", project_id=project.id, asset_ids=[asset.id])
    )

    # Add Benchmark Questions representing different expected answer types and metrics constraints
    # Q1: Factual question that should pass
    q1 = crud.create_benchmark_question(
        session,
        schemas.BenchmarkQuestionCreate(
            project_id=project.id,
            question="What is the SLA refund percentage?",
            expected_claims=["Deliveries exceeding SLA deadline by 48 hours receive 15% refund."],
            expected_answer_type="FACTUAL",
            required_citation_count=1,
            tags="sla,refund",
            severity="MEDIUM",
            min_required_coverage=0.95
        )
    )

    # Q2: Refusal question that should pass (because answer is unsupported and expected type is REFUSAL)
    q2 = crud.create_benchmark_question(
        session,
        schemas.BenchmarkQuestionCreate(
            project_id=project.id,
            question="Does clinical monitoring cover remote audits?",
            expected_claims=["Clinical monitoring covers remote audits."],
            expected_answer_type="REFUSAL",
            required_citation_count=0,
            tags="unrelated",
            severity="LOW",
            min_required_coverage=0.0
        )
    )

    # Q3: Factual question that is unrelated and will trigger INSUFFICIENT EVIDENCE (should fail because expected answer type is FACTUAL)
    q3 = crud.create_benchmark_question(
        session,
        schemas.BenchmarkQuestionCreate(
            project_id=project.id,
            question="What is the deviation logging timeline?",
            expected_claims=["Critical deviations must be logged within 24 hours."],
            expected_answer_type="FACTUAL",
            required_citation_count=1,
            tags="deviation",
            severity="HIGH",
            min_required_coverage=0.95
        )
    )

    print("\n--- Running Evaluation Run (Live Context) ---")
    run_in = schemas.EvaluationRunCreate(project_id=project.id, expert_model_id=model.id)
    db_run = evaluation.create_evaluation_run(session, run_in)
    
    # Execute batch run
    evaluation.run_evaluation_batch(session, db_run.id)
    
    # Reload from DB
    session.refresh(db_run)
    assert db_run.status == "COMPLETED"
    assert db_run.pass_rate == 0.67 # 2 passed out of 3 (Q1 passed, Q2 passed, Q3 failed)
    
    # Reload results
    results = db_run.results
    assert len(results) == 3
    
    r1 = next(r for r in results if r.benchmark_question_id == q1.id)
    r2 = next(r for r in results if r.benchmark_question_id == q2.id)
    r3 = next(r for r in results if r.benchmark_question_id == q3.id)

    assert r1.passed is True
    assert r2.passed is True
    assert r3.passed is False # Expected FACTUAL but returned INSUFFICIENT_EVIDENCE
    
    print("Pass/Fail Refusal Rules: PASSED")

    # --- SNAPSHOT REPRODUCIBILITY TEST ---
    print("\n--- Testing Snapshot Reproducibility ---")
    # Archive/Reject the SLA asset so new queries fail
    crud.update_knowledge_asset(session, asset_id=asset.id, update=schemas.KnowledgeAssetUpdate(status="ARCHIVED"), actor="Auditor")
    
    # If we run a live query, it should return INSUFFICIENT EVIDENCE now
    from app import query_engine
    live_citations = query_engine.retrieve_approved_evidence(session, model.id, "What is the SLA refund percentage?")
    assert len(live_citations["citations"]) == 0, "Live query should have blocked archived asset"

    # But if we run a batch run utilizing the SNAPSHOT we took earlier, it should still retrieve and evaluate correctly!
    # Let's verify that the snapshot run retains the asset list and hashes:
    snapshot_run_in = schemas.EvaluationRunCreate(project_id=project.id, expert_model_id=model.id)
    db_run_snap = evaluation.create_evaluation_run(session, snapshot_run_in)
    
    # The new run_snap took a snapshot *after* the asset was archived, so it should have 0 assets in snapshot
    snap_asset_ids = json.loads(db_run_snap.asset_ids_snapshot)
    assert len(snap_asset_ids) == 0

    # Let's manually trigger a batch run on our FIRST run (which had the asset snapshotted before archival)
    # The first run has asset ID 1 snapshotted, so executing it again will still use the snapshotted asset list!
    # To demonstrate this, we delete the results of run 1 and execute it again:
    for res in results:
        session.delete(res)
    session.commit()
    
    evaluation.run_evaluation_batch(session, db_run.id)
    session.refresh(db_run)
    assert db_run.pass_rate == 0.67 # Still passes Q1 and Q2, demonstrating it bypassed the live SQLite APPROVED status filter
    
    print("Snapshot Reproducibility Test: PASSED")
    print("\n=== All Evaluation Batch Engine and Scorecard tests passed! ===")
    session.close()

if __name__ == "__main__":
    test_evaluation_engine()
