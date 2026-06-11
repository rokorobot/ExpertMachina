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

def run_test():
    print("Initializing test database...")
    db.init_db()
    
    session = db.SessionLocal()
    try:
        # 1. Setup default customer
        print("\nChecking Customer Initialization...")
        customer = crud.get_or_create_default_customer(session)
        print(f"Default customer loaded: {customer.name} (API key: {customer.api_key})")
        
        # 2. Create a test project
        print("\nCreating Project...")
        proj_in = schemas.ProjectCreate(
            name="Clinical QA Automation Project",
            description="Testing ingestion of SOP documents and QA validation extraction.",
            customer_id=customer.id
        )
        auditor = test_support.governed_actor(session, "Lead Auditor")
        project = crud.create_project(session, proj_in, actor=auditor)
        print(f"Project created: {project.name} (Status: {project.status})")
        
        # 3. Create simulated document file
        print("\nCreating Sample Document File...")
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
        print("\nLogging Document...")
        doc = crud.create_document(
            session,
            project_id=project.id,
            filename=sample_filename,
            file_path=sample_path,
            department="Facilities",
            owner="Facility Manager",
            actor=auditor
        )
        print(f"Document logged: {doc.filename} (Status: {doc.status})")
        
        # 5. Ingest / Parse / Chunk / Embed
        print("\nRunning Ingestion (Parsing, Chunking, Indexing)...")
        parsed = ingestion.parse_and_index_document(session, doc.id)
        print(f"Ingestion completion: {parsed}")
        
        # Verify chunks
        chunks = crud.get_document_chunks(session, doc.id)
        print(f"Created {len(chunks)} document chunks:")
        for c in chunks:
            print(f" - Chunk {c.chunk_index} (Text: '{c.text[:60]}...')")
            
        # 6. Extract Knowledge Assets
        print("\nRunning Knowledge Asset Extraction...")
        extracted = extraction.extract_knowledge_assets_from_project(session, project.id)
        print(f"Extraction completion: {extracted}")
        
        # Verify assets
        assets = crud.get_knowledge_assets(session, project.id)
        print(f"Extracted {len(assets)} knowledge assets:")
        for a in assets:
            print(f" - [{a.type}] {a.name} (Source: {a.source_citation})")
            print(f"   Provenance: Document ID: {a.document_id}, Chunk ID: {a.chunk_id}, Hash: {a.source_hash[:10]}, Method: {a.extraction_method}")
            print(f"   Governance Status: {a.status}, Access: {a.access_level}")
            
            # Print quality scores
            for score in a.quality_scores:
                print(f"   Quality - Overall: {score.overall_score}, Coverage: {score.coverage_score}, Freshness: {score.freshness_score}, Verification: {score.verification_score}, Conflict: {score.conflict_score}")
                
        # 7. Approve assets
        print("\nSimulating Asset Review & Approval...")
        for a in assets:
            crud.update_knowledge_asset(
                session,
                asset_id=a.id,
                update=schemas.KnowledgeAssetUpdate(status="APPROVED"),
                actor=auditor
            )
            
        # 8. Build Expert Model
        print("\nBuilding Expert Model...")
        asset_ids = [a.id for a in assets]
        model_in = schemas.ExpertModelCreate(
            name="Facility Safety Expert Model",
            description="Expert model grouping Facilities and Safety SOP rules.",
            project_id=project.id,
            asset_ids=asset_ids
        )
        expert = crud.create_expert_model(session, model_in, actor=auditor)
        print(f"Expert Model created: {expert.name} (Assets grouped: {expert.asset_count}, Avg Quality: {expert.quality_score}%, Avg Coverage: {expert.coverage_score}%)")
        
        # 9. Build Agent Package
        print("\nCompiling Agent Package...")
        pkg_in = schemas.AgentPackageCreate(
            name="Safety Agent v0.1",
            expert_model_id=expert.id,
            project_id=project.id,
            governance_version="0.1.0"
        )
        pkg = crud.create_agent_package(session, pkg_in, actor=auditor)
        print(f"Agent Package compiled: {pkg.name} (Quality score: {pkg.quality_score}%, Governance version: {pkg.governance_version})")
        print(f"References serialized: {pkg.asset_references[:200]}...")
        
        # 10. Audit ledger
        print("\nVerifying Audit Ledger Log events:")
        events = crud.get_audit_events(session, limit=10)
        for e in reversed(events):
            print(f" - [{e.timestamp.strftime('%H:%M:%S')}] Actor: {e.actor} | Event: {e.event_type} | Details: {e.details}")
            
        print("\n--- Pipeline verification successful! ---")
        
    finally:
        session.close()

if __name__ == "__main__":
    run_test()
