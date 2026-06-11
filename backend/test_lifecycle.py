import os
import sys

# Ensure backend folder is in path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app import database as db
from app import schemas
from app import crud
from app import ingestion
from app import extraction
import test_support

def run_lifecycle_test():
    print("Initializing test database for lifecycle checks...")
    db.init_db()
    
    session = db.SessionLocal()
    try:
        # 1. Setup default customer
        customer = crud.get_or_create_default_customer(session)
        auditor = test_support.governed_actor(session, "Lead Auditor")

        # 2. Create a test project
        proj_in = schemas.ProjectCreate(
            name="Lifecycle Test Project",
            description="Testing document lifecycle state transitions.",
            customer_id=customer.id
        )
        project = crud.create_project(session, proj_in, actor=auditor)
        print(f"Project created: {project.name}")
        
        # 3. Create simulated document file
        sample_filename = "SOP-999_Emergency_Shutdown.txt"
        os.makedirs("./uploads", exist_ok=True)
        sample_path = "./uploads/test_SOP-999.txt"
        
        content = (
            "SOP-999: Standard Emergency Shutdown Procedure.\n"
            "Department: Facilities\n"
            "Policy: In the event of a thermal runaway, power must be cut off immediately by the Facility Manager.\n"
            "Procedure:\n"
            "1. Press the big red emergency stop button located in Hallway B.\n"
            "2. Wait for coolant pumps to engage (requires up to 30 seconds).\n"
            "3. Facility Manager must sign off on the shutdown logs before evacuation."
        )
        
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # 4. Upload / Log Document
        doc = crud.create_document(
            session,
            project_id=project.id,
            filename=sample_filename,
            file_path=sample_path,
            department="Facilities",
            owner="Facility Manager",
            actor=auditor
        )
        print(f"Initial doc status: {doc.status} (Expected: INGESTED)")
        assert doc.status == "INGESTED"
        
        # 5. Ingest / Parse
        ingestion.parse_and_index_document(session, doc.id)
        session.refresh(doc)
        print(f"Parsed doc status: {doc.status} (Expected: PARSED)")
        assert doc.status == "PARSED"
        
        # 6. Extract Knowledge Assets
        extraction.extract_knowledge_assets_from_project(session, project.id)
        session.refresh(doc)
        print(f"Extracted assets doc status: {doc.status} (Expected: ASSETS_EXTRACTED)")
        assert doc.status == "ASSETS_EXTRACTED"
        
        # Verify assets
        assets = [a for a in crud.get_knowledge_assets(session, project.id) if a.document_id == doc.id]
        print(f"Extracted {len(assets)} assets.")
        assert len(assets) > 0
        
        # Verify that get_documents includes this document (ASSETS_EXTRACTED is visible)
        active_docs = crud.get_documents(session, project.id)
        assert doc.id in [d.id for d in active_docs]
        print("Initial extracted candidate assets state: document is visible.")

        # 7. Approve one asset (mixed state: 1 APPROVED, 1 CANDIDATE)
        crud.update_knowledge_asset(
            session,
            asset_id=assets[0].id,
            update=schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=auditor
        )
        session.refresh(doc)
        print(f"One approved asset doc status: {doc.status} (Expected: PARTIALLY_APPROVED)")
        assert doc.status == "PARTIALLY_APPROVED"
        
        # Verify document is still visible in mixed state
        active_docs = crud.get_documents(session, project.id)
        assert doc.id in [d.id for d in active_docs]
        print("Mixed approved + candidate state: document is visible.")
        
        # 8. Approve all remaining assets
        for a in assets[1:]:
            crud.update_knowledge_asset(
                session,
                asset_id=a.id,
                update=schemas.KnowledgeAssetUpdate(status="APPROVED"),
                actor=auditor
            )
        session.refresh(doc)
        print(f"All approved assets doc status: {doc.status} (Expected: APPROVED)")
        assert doc.status == "APPROVED"
        
        # Verify document is still visible when approved
        active_docs = crud.get_documents(session, project.id)
        assert doc.id in [d.id for d in active_docs]
        print("All approved assets state: document is visible.")

        # Test Expert Model / Knowledge Base transfer constraint:
        # Let's temporarily reject one asset to test transfer constraint
        crud.update_knowledge_asset(
            session,
            asset_id=assets[0].id,
            update=schemas.KnowledgeAssetUpdate(status="ARCHIVED"),
            actor=auditor
        )
        model_in = schemas.ExpertModelCreate(
            name="Compliance Expert Model",
            description="Testing Approved-only transfer",
            project_id=project.id,
            asset_ids=[assets[0].id, assets[1].id]
        )
        try:
            model = crud.create_expert_model(session, model_in, actor=auditor)
            assert False, "Expert Model creation should have been blocked because an asset is ARCHIVED"
        except ValueError as e:
            print(f"Expert Model creation blocked as expected: {e}")
        
        # 9. Reject / Archive all assets
        for a in assets:
            crud.update_knowledge_asset(
                session,
                asset_id=a.id,
                update=schemas.KnowledgeAssetUpdate(status="ARCHIVED"),
                actor=auditor
            )
        session.refresh(doc)
        print(f"All rejected assets doc status: {doc.status} (Expected: ALL_ASSETS_REJECTED)")
        assert doc.status == "ALL_ASSETS_REJECTED"
        
        # Verify that get_documents excludes this document
        active_docs = crud.get_documents(session, project.id)
        print(f"Active documents in project: {[d.filename for d in active_docs]} (Expected empty list)")
        assert doc.id not in [d.id for d in active_docs]
        
        # Verify that extraction skips this document (extraction runs on PARSED documents)
        # Since status is ALL_ASSETS_REJECTED, it should not be pulled for extraction
        extraction_run = extraction.extract_knowledge_assets_from_project(session, project.id)
        print(f"Asset extraction run on ALL_ASSETS_REJECTED document returned: {extraction_run} (Expected: False)")
        assert extraction_run is False

        # 10. Delete all assets from document
        crud.delete_knowledge_assets_by_document(session, doc.id, actor=auditor)
        session.refresh(doc)
        print(f"All assets deleted doc status: {doc.status} (Expected: DELETED)")
        assert doc.status == "DELETED"
        
        # Verify that extraction skips this document (status is DELETED)
        extraction_run = extraction.extract_knowledge_assets_from_project(session, project.id)
        print(f"Asset extraction run on DELETED document returned: {extraction_run} (Expected: False)")
        assert extraction_run is False
        
        print("\n--- All lifecycle assertions passed successfully! ---")
        
    finally:
        session.close()

if __name__ == "__main__":
    run_lifecycle_test()
