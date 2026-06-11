import os
import sys
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import database as db
from app import schemas
from app import crud
from app import query_engine
from app import ingestion
import test_support

def test_tampered_chunk_rejection():
    print("\nInitializing test database for Evidence Validation checks...")
    
    # Use in-memory SQLite database
    TEST_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Prepopulate default customer
    customer = crud.get_or_create_default_customer(session)
    
    auditor = test_support.governed_actor(session, "QualityAuditor")

    # 1. Create Project
    project = crud.create_project(
        session,
        schemas.ProjectCreate(name="Validation Test Project", description="Testing tampering detection", customer_id=customer.id),
        actor=auditor
    )

    # 2. Ingest document and chunk
    doc = crud.create_document(session, project_id=project.id, filename="SOP_Compliance.txt", file_path="uploads/SOP_Compliance.txt", actor=auditor)
    
    chunk_text = "Standard Operating Procedure: All changes must be verified through the validation engine."
    correct_hash = hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()
    
    chunk = db.DocumentChunk(document_id=doc.id, text=chunk_text, chunk_index=0)
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    
    # 3. Create Asset pointing to the chunk with correct hash
    asset = crud.create_knowledge_asset(
        session,
        schemas.KnowledgeAssetCreate(
            type="PROCEDURE",
            name="Compliance Rule Asset",
            content="All changes must be verified.",
            project_id=project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            source_page=1,
            source_section="SOP 1.2",
            source_hash=correct_hash
        )
    )
    
    # Approve Asset
    crud.update_knowledge_asset(session, asset_id=asset.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor=auditor)

    # Build Expert Model containing this asset
    model = crud.create_expert_model(
        session,
        schemas.ExpertModelCreate(name="Safety Expert Model", description="Grounded checks", project_id=project.id, asset_ids=[asset.id]),
        actor=auditor
    )

    # --- TEST A: Valid Evidence Retrieval ---
    print("\n--- Running Test A: Querying with correct hash ---")
    citations_ok = query_engine.retrieve_approved_evidence(
        session,
        expert_model_id=model.id,
        question="How should changes be verified?",
        limit=5
    )
    print(f"Citations returned: {citations_ok}")
    assert len(citations_ok["citations"]) == 1, "Retrieval failed to return valid evidence"
    assert citations_ok["citations"][0]["asset_id"] == asset.id, "Correct asset not retrieved"
    print("Test A: Passed (evidence validates successfully and is returned)")

    # --- TEST B: Tampered Chunk Retrieval ---
    print("\n--- Running Test B: Tampering with chunk text ---")
    # Tamper with chunk text directly in SQLite
    chunk.text = "Standard Operating Procedure: Tampered text modifying validation instructions."
    session.commit()
    
    # Execute query again
    print("Executing query on tampered evidence context...")
    citations_tampered = query_engine.retrieve_approved_evidence(
        session,
        expert_model_id=model.id,
        question="How should changes be verified?",
        limit=5
    )
    print(f"Citations returned after tampering: {citations_tampered}")
    
    # Assert that the asset was rejected and not returned
    assert len(citations_tampered["citations"]) == 0, "Security Bypass! Tampered chunk text went undetected by the validation engine!"
    print("Test B: Passed (Tampered evidence successfully rejected and blocked from answer generation)")

    print("\n=== All Evidence Validation Engine checks passed successfully! ===")
    session.close()

if __name__ == "__main__":
    test_tampered_chunk_rejection()
