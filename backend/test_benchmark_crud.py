import os
import sys
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import database as db
from app import schemas
from app import crud

def test_benchmark_crud():
    print("\nInitializing test database for Benchmark CRUD...")
    TEST_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Create customer
    customer = crud.get_or_create_default_customer(session)
    
    # Create Project
    project = crud.create_project(
        session,
        schemas.ProjectCreate(name="Benchmark Test Project", description="Testing Sprint 1", customer_id=customer.id)
    )

    # 1. Create Benchmark Question
    q_create = schemas.BenchmarkQuestionCreate(
        project_id=project.id,
        question="How should clinical deviations be escalated?",
        expected_claims=["Critical deviations must be logged in 24 hours.", "VP review is required."],
        expected_answer_type="POLICY",
        required_citation_count=2,
        tags="clinical,deviation",
        severity="HIGH",
        min_required_coverage=0.95
    )
    
    created = crud.create_benchmark_question(session, q_create)
    assert created.id is not None
    assert created.question == "How should clinical deviations be escalated?"
    assert created.expected_answer_type == "POLICY"
    assert created.required_citation_count == 2
    assert created.tags == "clinical,deviation"
    assert created.severity == "HIGH"
    assert created.min_required_coverage == 0.95
    assert "VP review is required." in created.expected_claims
    print("Create Benchmark: PASSED")

    # 2. Get Benchmarks List
    questions = crud.get_benchmark_questions(session, project.id)
    assert len(questions) == 1
    assert questions[0].id == created.id
    print("Get Benchmarks List: PASSED")

    # 3. Update Benchmark
    q_update = schemas.BenchmarkQuestionUpdate(
        question="Updated question string?",
        expected_claims=["Updated expected claim."],
        severity="CRITICAL"
    )
    updated = crud.update_benchmark_question(session, created.id, q_update)
    assert updated.question == "Updated question string?"
    assert "Updated expected claim." in updated.expected_claims
    assert updated.severity == "CRITICAL"
    # Verify non-updated fields remain intact
    assert updated.expected_answer_type == "POLICY"
    print("Update Benchmark: PASSED")

    # 4. Delete Benchmark
    deleted = crud.delete_benchmark_question(session, created.id)
    assert deleted is True
    assert crud.get_benchmark_question(session, created.id) is None
    print("Delete Benchmark: PASSED")

    print("\n=== All Sprint 1 Benchmark CRUD tests passed successfully! ===")
    session.close()

if __name__ == "__main__":
    test_benchmark_crud()
