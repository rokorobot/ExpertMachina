import os
import sys
import json
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from app import database as db
from app import schemas
from app import crud
from app import identity
from app import query_engine
from app.main import app
from fastapi.testclient import TestClient
import test_support

def test_audit_logging_scenarios():
    print("\nInitializing test database for Audit expansion checks...")
    
    # Use in-memory SQLite database. StaticPool: every connection checkout
    # must reach the SAME memory database - TestClient serves requests on a
    # worker thread, and without it a post-commit checkout gets a fresh,
    # empty :memory: connection ("no such table").
    from sqlalchemy.pool import StaticPool
    TEST_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Prepopulate default customer
    customer = crud.get_or_create_default_customer(session)
    
    admin = test_support.governed_actor(session, "Admin")

    # Create Project
    project = crud.create_project(
        session,
        schemas.ProjectCreate(name="Audit Logging Test", description="Telemetry logs", customer_id=customer.id),
        actor=admin
    )

    # Create mock document and chunk
    doc = crud.create_document(session, project_id=project.id, filename="SLA_Refund.txt", file_path="uploads/SLA_Refund.txt", actor=admin)
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
    crud.update_knowledge_asset(session, asset_id=asset.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor=admin)

    # Build Expert Model with SLA asset
    model = crud.create_expert_model(
        session,
        schemas.ExpertModelCreate(name="Refund Expert", description="SLA rules", project_id=project.id, asset_ids=[asset.id]),
        actor=admin
    )

    # We mock app dependency injection to use this test database
    from app.main import get_db
    app.dependency_overrides[get_db] = lambda: session
    client = TestClient(app)

    # Identity boundary (v1.0): the query route requires an authenticated
    # actor - callers can no longer act anonymously. This suite pre-dated
    # the boundary (the reason it fell out of CI); repaired 2026-07-07 to
    # authenticate like every modern suite does.
    auditor = identity.create_principal(session, name="auditor", display_name="Auditor",
                                        kind="HUMAN", role="ADMIN", created_by="test-suite")
    identity.set_password(session, auditor, "auditor-password-123", actor="test-suite")
    r = client.post("/api/auth/login", json={"name": "auditor", "password": "auditor-password-123"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    HEADERS = {"Authorization": f"Bearer {r.json()['token']}"}

    # --- SCENARIO 1: Ask unrelated question (triggers INSUFFICIENT EVIDENCE block) ---
    print("\n--- Running Scenario 1: Unrelated question (Expected Block) ---")
    response = client.post(
        f"/api/projects/{project.id}/query",
        json={"expert_model_id": model.id, "question": "Does clinical monitoring cover remote audits?"},
        headers=HEADERS
    )
    
    assert response.status_code == 200, "Query request failed"
    data = response.json()
    print(f"Query response: {data}")
    assert data["answer"] == "INSUFFICIENT EVIDENCE"
    assert data["verification_status"] == "INSUFFICIENT_EVIDENCE"
    
    # Query audit timeline events to verify ASK_EXPERT_BLOCKED_INSUFFICIENT_EVIDENCE
    events = crud.get_audit_events(session, limit=10)
    blocked_event = next((e for e in events if e.event_type == "ASK_EXPERT_BLOCKED_INSUFFICIENT_EVIDENCE"), None)
    assert blocked_event is not None, "Failed to log ASK_EXPERT_BLOCKED_INSUFFICIENT_EVIDENCE audit log event"
    print(f"Log event verified: type='{blocked_event.event_type}'")
    
    # Parse event details
    details = json.loads(blocked_event.details)
    print(f"Log event details schema: {details}")
    assert details["verification_status"] == "INSUFFICIENT_EVIDENCE"
    assert "Clinical monitoring covers remote audits." in details["unsupported_claims"]
    # The boundary decides the actor: the ledger records the authenticated
    # principal's display, never a hardcoded operator string.
    assert details["operator"] == "Auditor"
    print("Scenario 1: Passed (blocked query successfully logged with full verification details)")

    # --- SCENARIO 2: Valid Grounded Question (Expected ASK_EXPERT_QUERY log) ---
    print("\n--- Running Scenario 2: Grounded question (Expected Success log) ---")
    response_ok = client.post(
        f"/api/projects/{project.id}/query",
        json={"expert_model_id": model.id, "question": "What is the SLA refund percentage?"},
        headers=HEADERS
    )
    assert response_ok.status_code == 200
    data_ok = response_ok.json()
    print(f"Query response SLA: {data_ok}")
    assert data_ok["verification_status"] == "VERIFIED"
    
    events_ok = crud.get_audit_events(session, limit=10)
    success_event = next((e for e in events_ok if e.event_type == "ASK_EXPERT_QUERY"), None)
    assert success_event is not None, "Failed to log ASK_EXPERT_QUERY audit log event"
    print(f"Log event verified: type='{success_event.event_type}'")
    details_ok = json.loads(success_event.details)
    assert details_ok["verification_status"] == "VERIFIED"
    assert details_ok["coverage_score"] == 1.0
    print("Scenario 2: Passed (successful query successfully logged in secure ledger)")

    print("\n=== All Audit Logging Expansion tests passed successfully! ===")
    session.close()

if __name__ == "__main__":
    test_audit_logging_scenarios()
