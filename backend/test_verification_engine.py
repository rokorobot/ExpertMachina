import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import database as db
from app import schemas
from app import crud
from app import query_engine

def test_claims_verification_rules():
    print("\nInitializing test database for Answer Verification checks...")
    
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
        schemas.ProjectCreate(name="Verification System Test", description="Testing claim mappings", customer_id=customer.id)
    )
    
    # 2. Ingest document and chunks
    doc = crud.create_document(session, project_id=project.id, filename="DeviationsSOP.txt", file_path="uploads/DeviationsSOP.txt")
    
    chunk_a = db.DocumentChunk(document_id=doc.id, text="Critical deviations must be logged within 24 hours.", chunk_index=0)
    chunk_b = db.DocumentChunk(document_id=doc.id, text="Quality managers review deviations weekly.", chunk_index=1)
    session.add_all([chunk_a, chunk_b])
    session.commit()
    session.refresh(chunk_a)
    session.refresh(chunk_b)
    
    # 3. Create approved Assets
    asset_a = crud.create_knowledge_asset(
        session,
        schemas.KnowledgeAssetCreate(
            type="POLICY",
            name="Asset A",
            content="Critical deviations must be logged within 24 hours.",
            project_id=project.id,
            document_id=doc.id,
            chunk_id=chunk_a.id,
            source_page=1,
            source_section="Sec 1",
            source_hash="hash-a"
        )
    )
    asset_b = crud.create_knowledge_asset(
        session,
        schemas.KnowledgeAssetCreate(
            type="POLICY",
            name="Asset B",
            content="Quality managers review deviations weekly.",
            project_id=project.id,
            document_id=doc.id,
            chunk_id=chunk_b.id,
            source_page=1,
            source_section="Sec 2",
            source_hash="hash-b"
        )
    )
    
    crud.update_knowledge_asset(session, asset_id=asset_a.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor="Admin")
    crud.update_knowledge_asset(session, asset_id=asset_b.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor="Admin")

    # Build Expert Model with both assets
    model = crud.create_expert_model(
        session,
        schemas.ExpertModelCreate(name="Deviation Expert Model", description="Checks", project_id=project.id, asset_ids=[asset_a.id, asset_b.id])
    )

    # 4. Mock retrieve validated evidence context
    citations = [
        {
            "asset_id": asset_a.id,
            "name": asset_a.name,
            "content": asset_a.content,
            "source_document": doc.filename,
            "source_page": asset_a.source_page,
            "source_section": asset_a.source_section,
            "source_hash": asset_a.source_hash,
            "asset_status": asset_a.status
        },
        {
            "asset_id": asset_b.id,
            "name": asset_b.name,
            "content": asset_b.content,
            "source_document": doc.filename,
            "source_page": asset_b.source_page,
            "source_section": asset_b.source_section,
            "source_hash": asset_b.source_hash,
            "asset_status": asset_b.status
        }
    ]

    # Test generated answer containing unsupported claim
    generated_answer = (
        "Critical deviations must be logged within 24 hours. "
        "Quality managers review deviations weekly. "
        "A deviation committee approves all cases."
    )

    print("\n--- Running Success Test: Verification of Unsupported Claims ---")
    verification = query_engine.verify_answer_claims(
        session,
        answer_text=generated_answer,
        validated_citations=citations
    )
    
    print(f"Verification Report: {verification}")
    
    # Assert claim counts and alignment
    assert len(verification["claim_mappings"]) == 3, "Failed to extract exactly 3 claims"
    
    # Claim 1 should be supported by Asset A
    assert asset_a.id in verification["claim_mappings"][0]["supporting_assets"], "Claim 1 mapping failed"
    # Claim 2 should be supported by Asset B
    assert asset_b.id in verification["claim_mappings"][1]["supporting_assets"], "Claim 2 mapping failed"
    # Claim 3 should have 0 supporting assets
    assert len(verification["claim_mappings"][2]["supporting_assets"]) == 0, "Claim 3 incorrectly mapped"
    
    # Assert coverage is 2/3 = 0.67
    assert verification["coverage_score"] == 0.67, f"Expected coverage_score 0.67, got {verification['coverage_score']}"
    # Assert verification status is INSUFFICIENT_EVIDENCE
    assert verification["verification_status"] == "INSUFFICIENT_EVIDENCE", "Verification status should be INSUFFICIENT_EVIDENCE"
    # Assert unsupported claims lists claim 3
    assert "A deviation committee approves all cases." in verification["unsupported_claims"], "Failed to identify evidence gap"

    print("Test passed: Verification successfully flagged unsupported claims and set status to INSUFFICIENT_EVIDENCE.")
    print("\n=== All Answer Verification Engine tests passed successfully! ===")
    session.close()

if __name__ == "__main__":
    test_claims_verification_rules()
