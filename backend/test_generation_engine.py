import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import database as db
from app import schemas
from app import crud
from app import query_engine

def test_grounded_generation():
    print("\nInitializing test database for Answer Generation checks...")
    
    # Use in-memory SQLite database
    TEST_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Prepopulate default customer
    customer = crud.get_or_create_default_customer(session)
    
    # 1. Create Project
    project = crud.create_project(
        session, 
        schemas.ProjectCreate(name="Generation Test Project", description="Testing grounded prompts", customer_id=customer.id)
    )
    
    # Create Expert Model with NO assets
    model_empty = crud.create_expert_model(
        session,
        schemas.ExpertModelCreate(name="Empty Expert Model", description="No assets", project_id=project.id, asset_ids=[])
    )

    # --- TEST A: Fallback with no evidence ---
    print("\n--- Running Test A: Requesting answer with NO validated evidence ---")
    gen_empty = query_engine.generate_evidence_answer(
        session,
        expert_model_id=model_empty.id,
        question="How should changes be verified?",
        validated_citations=[]
    )
    print(f"Generated result empty case: {gen_empty}")
    assert gen_empty["answer"] == "No validated evidence could be found to answer this question."
    assert gen_empty["used_evidence_ids"] == []
    print("Test A: Passed (correctly returned standard refusal string)")

    # --- TEST B: Answer with evidence ---
    print("\n--- Running Test B: Requesting answer WITH validated evidence ---")
    mock_citations = [
        {
            "asset_id": 42,
            "name": "Deviation Logging SLA",
            "content": "All critical deviations must be logged in the quality management system within 24 hours.",
            "source_document": "SOP-001.txt",
            "source_page": 2,
            "source_section": "Sec 4.1",
            "source_hash": "some-hash",
            "asset_status": "APPROVED",
            "approved_by": "operator_admin_02",
            "approved_at": "2026-06-10T00:30:00Z"
        }
    ]
    
    gen_evidence = query_engine.generate_evidence_answer(
        session,
        expert_model_id=model_empty.id,  # just pass ID for scoping
        question="What is the deviation logging timeline?",
        validated_citations=mock_citations
    )
    print(f"Generated result evidence case: {gen_evidence}")
    assert gen_empty["answer"] != gen_evidence["answer"]
    assert 42 in gen_evidence["used_evidence_ids"]
    assert "critical deviations must be logged" in gen_evidence["answer"]
    print("Test B: Passed (correctly generated grounded response containing evidence details)")

    print("\n=== All Answer Generation Engine tests passed successfully! ===")
    session.close()

if __name__ == "__main__":
    test_grounded_generation()
