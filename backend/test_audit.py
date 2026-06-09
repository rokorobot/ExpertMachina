import os
import sys
import json

# Ensure backend folder is in path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app import database as db
from app import schemas
from app import crud
from app import ingestion
from app import extraction

def run_audit_test():
    print("Initializing test database for security and audit checks...")
    db.init_db()
    
    session = db.SessionLocal()
    try:
        # Setup customer & project
        customer = crud.get_or_create_default_customer(session)
        project = crud.create_project(
            session,
            schemas.ProjectCreate(
                name="Security Audit Project",
                description="Testing provenance, bypass prevention, and manifest reproducibility.",
                customer_id=customer.id
            )
        )
        
        # Ingest document
        filename = "SOP-888_Thermal_Management.txt"
        os.makedirs("./uploads", exist_ok=True)
        file_path = "./uploads/test_SOP-888.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("SOP-888: Thermal Control Procedures.\nPolicy: Thermal sensors must be calibrated daily by Safety Officers.\nProcedure: 1. Calibrate sensor A. 2. Verify limits.")
            
        doc = crud.create_document(session, project.id, filename, file_path, "Safety", "Safety Officer")
        ingestion.parse_and_index_document(session, doc.id)
        extraction.extract_knowledge_assets_from_project(session, project.id)
        
        # Verify extraction and fetch assets
        assets = [a for a in crud.get_knowledge_assets(session, project.id) if a.document_id == doc.id]
        print(f"Extracted {len(assets)} assets for audit.")
        assert len(assets) >= 1
        
        target_asset = assets[0]
        
        # --- TEST 1: GOVERNANCE BYPASS ---
        print("\n--- Running Test 1: Governance Bypass ---")
        # Reject the asset first
        crud.update_knowledge_asset(
            session,
            asset_id=target_asset.id,
            update=schemas.KnowledgeAssetUpdate(status="ARCHIVED"),
            actor="Auditor"
        )
        # Attempt direct database/API grouping of this rejected asset into an Expert Model
        model_in = schemas.ExpertModelCreate(
            name="Restricted Expert Model",
            description="Trying to bypass governance with rejected asset",
            project_id=project.id,
            asset_ids=[target_asset.id]
        )
        
        try:
            crud.create_expert_model(session, model_in)
            assert False, "Bypass Failed: Rejected asset was grouped into model without raising an error!"
        except ValueError as e:
            print(f"Bypass prevention successfully threw error: {e}")
            
        # Verify GOVERNANCE_BLOCKED_NON_APPROVED_ASSET audit event is logged
        events = crud.get_audit_events(session, limit=5)
        blocked_event = next((ev for ev in events if ev.event_type == "GOVERNANCE_BLOCKED_NON_APPROVED_ASSET"), None)
        assert blocked_event is not None, "Bypass Failed: GOVERNANCE_BLOCKED_NON_APPROVED_ASSET audit event was not logged!"
        print(f"Governance block audit event verified: '{blocked_event.details}'")
        print("Governance Bypass Test: PASSED (Rejected asset successfully blocked with explicit error and audit trace)")
        
        # --- TEST 2: PROVENANCE INTEGRITY ---
        print("\n--- Running Test 2: Provenance Integrity ---")
        # Re-approve the asset so it can enter the package
        crud.update_knowledge_asset(
            session,
            asset_id=target_asset.id,
            update=schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor="Auditor"
        )
        # Re-build expert model with now approved asset
        model_ok = crud.create_expert_model(
            session,
            schemas.ExpertModelCreate(
                name="Governed Expert Model",
                description="Governed grouping",
                project_id=project.id,
                asset_ids=[target_asset.id]
            )
        )
        assert model_ok.asset_count == 1
        
        # Compile package
        pkg = crud.create_agent_package(
            session,
            schemas.AgentPackageCreate(
                name="Audit Package v1",
                expert_model_id=model_ok.id,
                project_id=project.id,
                governance_version="1.0.0"
            )
        )
        
        # Parse serialized metadata
        refs = json.loads(pkg.asset_references)
        assert len(refs) == 1
        ref = refs[0]
        
        # Audit provenance keys
        required_provenance_keys = [
            "source_document",
            "source_page",
            "source_section",
            "source_hash",
            "extraction_method"
        ]
        print("Serialized package manifest keys:")
        for k in required_provenance_keys:
            val = ref.get(k)
            print(f" - {k}: '{val}'")
            assert val is not None, f"Provenance key '{k}' is missing!"
            
        assert ref["source_document"] == filename
        print("Provenance Integrity Test: PASSED (Full audit trace successfully recovered from compiled package)")
        
        # --- TEST 3: PACKAGE REPRODUCIBILITY ---
        print("\n--- Running Test 3: Package Reproducibility ---")
        # Compile a second package from identical assets
        pkg_2 = crud.create_agent_package(
            session,
            schemas.AgentPackageCreate(
                name="Audit Package v2",
                expert_model_id=model_ok.id,
                project_id=project.id,
                governance_version="1.0.0"
            )
        )
        
        # Manifest comparison
        manifest_1 = pkg.asset_references
        manifest_2 = pkg_2.asset_references
        print(f"Manifest 1: {manifest_1}")
        print(f"Manifest 2: {manifest_2}")
        assert manifest_1 == manifest_2, "Reproducibility Failed: Package manifests differ!"
        assert pkg.quality_score == pkg_2.quality_score
        print("Package Reproducibility Test: PASSED (Identical approved assets yield identical packages)")
        
        print("\n=== All MVP 0.2 Governance and Security audits passed successfully! ===")
        
    finally:
        session.close()

if __name__ == "__main__":
    run_audit_test()
