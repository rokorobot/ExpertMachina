import os
import sys
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup system paths so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import database as db
from app import schemas
from app import crud
from app import query_engine
from app import ingestion

def test_expert_model_isolation():
    print("\nInitializing test database for retrieval engine isolation checks...")
    
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
        schemas.ProjectCreate(name="Retrieval Engine Test", description="Testing isolation", customer_id=customer.id)
    )
    
    # 2. Create mock documents to generate chunk indices
    doc_a = crud.create_document(session, project_id=project.id, filename="DocA.txt", file_path="uploads/DocA.txt")
    doc_b = crud.create_document(session, project_id=project.id, filename="DocB.txt", file_path="uploads/DocB.txt")
    
    # Add dummy chunks directly to database
    chunk_a = db.DocumentChunk(document_id=doc_a.id, text="This is content for Asset A1.", chunk_index=0)
    chunk_b = db.DocumentChunk(document_id=doc_b.id, text="This is content for Asset B1.", chunk_index=0)
    session.add_all([chunk_a, chunk_b])
    session.commit()
    session.refresh(chunk_a)
    session.refresh(chunk_b)
    
    # Mock upsert points to Qdrant collection
    ingestion.init_qdrant()
    client = ingestion.get_qdrant_client()
    from qdrant_client.models import PointStruct
    import hashlib
    
    client.upsert(
        collection_name=ingestion.COLLECTION_NAME,
        points=[
            PointStruct(
                id=hashlib.md5(f"{doc_a.id}-0".encode()).hexdigest(),
                vector=ingestion.get_embedding(chunk_a.text),
                payload={"document_id": doc_a.id, "chunk_id": chunk_a.id, "text": chunk_a.text}
            ),
            PointStruct(
                id=hashlib.md5(f"{doc_b.id}-0".encode()).hexdigest(),
                vector=ingestion.get_embedding(chunk_b.text),
                payload={"document_id": doc_b.id, "chunk_id": chunk_b.id, "text": chunk_b.text}
            )
        ]
    )

    # 3. Create assets and approve them
    asset_a1 = crud.create_knowledge_asset(
        session,
        schemas.KnowledgeAssetCreate(
            type="POLICY",
            name="Asset A1 Policy",
            content="This is content for Asset A1.",
            project_id=project.id,
            document_id=doc_a.id,
            chunk_id=chunk_a.id,
            source_page=1,
            source_section="Introduction",
            source_hash="hash-a1"
        )
    )
    asset_b1 = crud.create_knowledge_asset(
        session,
        schemas.KnowledgeAssetCreate(
            type="POLICY",
            name="Asset B1 Policy",
            content="This is content for Asset B1.",
            project_id=project.id,
            document_id=doc_b.id,
            chunk_id=chunk_b.id,
            source_page=1,
            source_section="Introduction",
            source_hash="hash-b1"
        )
    )
    
    # Approve assets to cross governance check
    crud.update_knowledge_asset(session, asset_id=asset_a1.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor="admin")
    crud.update_knowledge_asset(session, asset_id=asset_b1.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor="admin")

    # 4. Compile Expert Model A (Asset A1)
    model_a = crud.create_expert_model(
        session,
        schemas.ExpertModelCreate(name="Expert Model A", description="Has Asset A1", project_id=project.id, asset_ids=[asset_a1.id])
    )
    
    # Compile Expert Model B (Asset B1)
    model_b = crud.create_expert_model(
        session,
        schemas.ExpertModelCreate(name="Expert Model B", description="Has Asset B1", project_id=project.id, asset_ids=[asset_b1.id])
    )

    # --- SUCCESS TEST 1 ---
    # Question: "What is Asset B1 about?"
    # Selected: Expert Model A
    # Expected: 0 results / INSUFFICIENT EVIDENCE (never Asset B1)
    print("\n--- Running Isolation Test: Query Model A about Asset B1 ---")
    citations_a = query_engine.retrieve_approved_evidence(
        session,
        expert_model_id=model_a.id,
        question="What is Asset B1 about?",
        limit=5
    )
    print(f"Citations returned for Model A: {citations_a}")
    # Verify that Asset B1 was NOT returned
    assert not any(c["asset_id"] == asset_b1.id for c in citations_a), "Security Bypass! Model A query leaked Asset B1!"
    print("Test passed: Model A query successfully isolated from Model B assets.")

    # --- SUCCESS TEST 2 ---
    # Question: "What is Asset B1 about?"
    # Selected: Expert Model B
    # Expected: Asset B1 retrieved successfully
    print("\n--- Running Retrieval Test: Query Model B about Asset B1 ---")
    citations_b = query_engine.retrieve_approved_evidence(
        session,
        expert_model_id=model_b.id,
        question="What is Asset B1 about?",
        limit=5
    )
    print(f"Citations returned for Model B: {citations_b}")
    assert any(c["asset_id"] == asset_b1.id for c in citations_b), "Retrieval Failed: Model B query could not retrieve its own asset!"
    print("Test passed: Model B successfully retrieved its own asset.")

    print("\n=== All Approved Asset Retrieval Engine tests passed successfully! ===")
    session.close()

if __name__ == "__main__":
    test_expert_model_isolation()
