import os
import sys
import json
import hashlib

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import conflict_engine


def add_conflict(session, model, a_id, b_id, classification, status):
    rel = db.AssetRelationship(
        project_id=model.project_id,
        expert_model_id=model.id,
        source_asset_id=a_id,
        target_asset_id=b_id,
        relationship_type="CONFLICTS_WITH",
        classification=classification,
        confidence=0.99,
        status=status,
        verifier_json=json.dumps({"method": "TEST_FIXTURE"})
    )
    session.add(rel)
    session.commit()
    session.refresh(rel)
    return rel


def compile_package(session, project, model, name):
    return crud.create_agent_package(session, schemas.AgentPackageCreate(
        name=name, project_id=project.id, expert_model_id=model.id, governance_version="0.1.0"
    ))


def main():
    print("\nInitializing test database for Package Compile Gate checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(name="Gate Test", description="Compile gates", customer_id=customer.id))
    doc = crud.create_document(session, project_id=project.id, filename="Policies.txt", file_path="uploads/p.txt")

    asset_ids = []
    for i, text in enumerate(["Customer data must be deleted after 30 days.", "Customer data must be retained indefinitely."]):
        chunk = db.DocumentChunk(document_id=doc.id, text=text, chunk_index=i)
        session.add(chunk)
        session.commit()
        session.refresh(chunk)
        a = crud.create_knowledge_asset(session, schemas.KnowledgeAssetCreate(
            type="POLICY", name=f"Policy {i+1}", content=text, project_id=project.id,
            document_id=doc.id, chunk_id=chunk.id, source_page=1, source_section="S1",
            source_hash=hashlib.sha256(text.encode()).hexdigest()))
        crud.update_knowledge_asset(session, asset_id=a.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor="qa")
        asset_ids.append(a.id)

    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Gate Expert", description="", project_id=project.id, asset_ids=asset_ids))

    # Part 1: clean model compiles (vacuous gate pass, gate verdict audit-logged).
    print("\n--- Part 1: Clean model compiles; publication records the gate verdict ---")
    pkg = compile_package(session, project, model, "Clean Package")
    assert pkg is not None
    created = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "AGENT_PACKAGE_CREATED").order_by(db.AuditEvent.id.desc()).first()
    details = json.loads(created.details)
    assert details["compile_gate"]["allowed"] is True
    assert details["compile_gate"]["conflict_scan_performed"] is False
    print("Part 1 passed.")

    # Part 2: unreviewed DIRECT_CONTRADICTION blocks compile.
    print("\n--- Part 2: Unreviewed direct contradiction blocks publication ---")
    rel = add_conflict(session, model, asset_ids[0], asset_ids[1], "DIRECT_CONTRADICTION", "DETECTED")
    try:
        compile_package(session, project, model, "Blocked Package")
        raise AssertionError("Compile was allowed despite an unreviewed direct contradiction")
    except ValueError as e:
        assert "UNREVIEWED_CONFLICT" in str(e)
    blocked = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "GOVERNANCE_BLOCKED_UNRESOLVED_CONFLICTS").count()
    assert blocked == 1, "Gate block not recorded in audit ledger"
    assert session.query(db.AgentPackage).count() == 1, "Blocked package was persisted!"
    print("Part 2 passed.")

    # Part 3: dismissing the conflict re-opens the gate.
    print("\n--- Part 3: Dismissed conflicts do not block ---")
    conflict_engine.review_relationship(session, rel.id, status="DISMISSED", reviewer="gov", notes="Contextual")
    pkg2 = compile_package(session, project, model, "Unblocked Package")
    assert pkg2 is not None
    details2 = json.loads(session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "AGENT_PACKAGE_CREATED").order_by(db.AuditEvent.id.desc()).first().details)
    assert details2["compile_gate"]["dismissed_conflicts"] == 1
    print("Part 3 passed.")

    # Part 4: confirmed conflicts follow the configurable policy.
    print("\n--- Part 4: Confirmed conflict policy (block by default, allow when configured) ---")
    add_conflict(session, model, asset_ids[0], asset_ids[1], "SCOPE_CONFLICT", "CONFIRMED")
    try:
        compile_package(session, project, model, "Confirmed Blocked")
        raise AssertionError("Default policy must block confirmed conflicts")
    except ValueError as e:
        assert "CONFIRMED_CONFLICT" in str(e)
    os.environ["EM_GATE_CONFIRMED_POLICY"] = "allow"
    try:
        pkg3 = compile_package(session, project, model, "Confirmed Allowed")
        assert pkg3 is not None
    finally:
        os.environ.pop("EM_GATE_CONFIRMED_POLICY")
    print("Part 4 passed.")

    # Part 5: unreviewed non-blocking classifications are advisory only.
    print("\n--- Part 5: Unreviewed scope/temporal conflicts are advisory ---")
    add_conflict(session, model, asset_ids[0], asset_ids[1], "TEMPORAL_SUPERSESSION", "DETECTED")
    os.environ["EM_GATE_CONFIRMED_POLICY"] = "allow"  # keep Part 4's confirmed conflict out of the way
    try:
        gate = conflict_engine.evaluate_compile_gate(session, model.id)
        assert gate["allowed"] is True
        assert len(gate["advisory_conflicts"]) == 2  # confirmed scope (allow) + detected temporal
    finally:
        os.environ.pop("EM_GATE_CONFIRMED_POLICY")
    print("Part 5 passed.")

    # Part 6: optional scan requirement.
    print("\n--- Part 6: EM_GATE_REQUIRE_SCAN blocks never-scanned models ---")
    os.environ["EM_GATE_REQUIRE_SCAN"] = "1"
    os.environ["EM_GATE_CONFIRMED_POLICY"] = "allow"
    try:
        gate = conflict_engine.evaluate_compile_gate(session, model.id)
        assert gate["allowed"] is False
        assert any(b["reason"] == "NO_CONFLICT_SCAN" for b in gate["blocking_conflicts"])
    finally:
        os.environ.pop("EM_GATE_REQUIRE_SCAN")
        os.environ.pop("EM_GATE_CONFIRMED_POLICY")
    print("Part 6 passed.")

    session.close()
    print("\n=== All Package Compile Gate tests passed successfully! ===")


if __name__ == "__main__":
    main()
