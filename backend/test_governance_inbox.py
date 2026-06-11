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
from app import governance_inbox
from app import revisions


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


def items_of(inbox, item_type):
    return [i for i in inbox["items"] if i["type"] == item_type]


def main():
    print("\nInitializing test database for Governance Inbox checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(name="Inbox Test", description="Governance inbox", customer_id=customer.id))
    doc = crud.create_document(session, project_id=project.id, filename="Policies.txt", file_path="uploads/p.txt")

    asset_ids = []
    texts = [
        "Customer data must be deleted after 30 days.",
        "Customer data must be retained indefinitely.",
        "Passwords must be rotated every 90 days.",
    ]
    for i, text in enumerate(texts):
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
        name="Inbox Expert", description="", project_id=project.id, asset_ids=asset_ids))

    # Part 1: clean project - no work items, readiness present, gate open.
    print("\n--- Part 1: Clean project inbox is empty but readiness reports the model ---")
    inbox = governance_inbox.build_inbox(session, project.id)
    assert inbox["summary"]["needs_review"] == 0
    assert inbox["summary"]["recently_resolved"] == 0
    assert inbox["summary"]["blocked_expert_models"] == 0
    assert inbox["summary"]["total_expert_models"] == 1
    assert len(inbox["readiness"]) == 1
    assert inbox["readiness"][0]["compile_allowed"] is True
    # No completed evaluation run yet - that is a live governance fact.
    warnings = items_of(inbox, "GOVERNANCE_WARNING")
    assert any(w["id"].endswith("no_evaluation") for w in warnings)
    assert all(w["bucket"] == "CAN_WAIT" and w["severity"] == "LOW" for w in warnings)
    print("Part 1 passed.")

    # Part 2: unreviewed direct contradiction is a HIGH item and matches the gate.
    print("\n--- Part 2: Blocking conflict surfaces as HIGH and agrees with the compile gate ---")
    rel = add_conflict(session, model, asset_ids[0], asset_ids[1], "DIRECT_CONTRADICTION", "DETECTED")
    inbox = governance_inbox.build_inbox(session, project.id)
    conflicts = items_of(inbox, "CONFLICT")
    assert len(conflicts) == 1
    item = conflicts[0]
    assert item["severity"] == "HIGH" and item["bucket"] == "NEEDS_REVIEW"
    assert item["classification"] == "DIRECT_CONTRADICTION"
    assert item["confidence"] == 0.99
    assert item["deep_link"] == f"/?tab=conflicts&expert={model.id}&relationship={rel.id}"
    gate = conflict_engine.evaluate_compile_gate(session, model.id)
    gate_blocking_ids = {b["relationship_id"] for b in gate["blocking_conflicts"]}
    inbox_high_ids = {c["source_id"] for c in conflicts if c["severity"] == "HIGH"}
    assert gate_blocking_ids == inbox_high_ids, "Inbox HIGH items must be exactly the gate's blocking conflicts"
    assert inbox["summary"]["blocked_expert_models"] == 1
    assert inbox["readiness"][0]["compile_allowed"] is False
    print("Part 2 passed.")

    # Part 3: advisory classification is MEDIUM and does not block.
    print("\n--- Part 3: Advisory conflict is MEDIUM / NEEDS_REVIEW ---")
    rel_adv = add_conflict(session, model, asset_ids[0], asset_ids[2], "TEMPORAL_SUPERSESSION", "DETECTED")
    inbox = governance_inbox.build_inbox(session, project.id)
    adv = next(c for c in items_of(inbox, "CONFLICT") if c["source_id"] == rel_adv.id)
    assert adv["severity"] == "MEDIUM" and adv["bucket"] == "NEEDS_REVIEW"
    # Sorting: HIGH before MEDIUM before LOW.
    severities = [i["severity"] for i in inbox["items"]]
    rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    assert severities == sorted(severities, key=lambda s: rank[s]), "Items must be severity-sorted"
    print("Part 3 passed.")

    # Part 4: dismissal moves the conflict to RESOLVED and reopens the gate.
    print("\n--- Part 4: Dismissed conflict lands in recently-resolved ---")
    conflict_engine.review_relationship(session, rel.id, status="DISMISSED", reviewer="gov", notes="Contextual")
    conflict_engine.review_relationship(session, rel_adv.id, status="DISMISSED", reviewer="gov", notes="Superseded")
    inbox = governance_inbox.build_inbox(session, project.id)
    resolved = [i for i in inbox["items"] if i["bucket"] == "RESOLVED"]
    assert {r["source_id"] for r in resolved} == {rel.id, rel_adv.id}
    assert all(r["resolved_at"] for r in resolved)
    assert inbox["summary"]["needs_review"] == 0
    assert inbox["summary"]["blocked_expert_models"] == 0
    print("Part 4 passed.")

    # Part 5: confirmed conflicts follow the gate policy in both modes.
    print("\n--- Part 5: Confirmed conflict severity follows EM_GATE_CONFIRMED_POLICY ---")
    rel_conf = add_conflict(session, model, asset_ids[1], asset_ids[2], "SCOPE_CONFLICT", "CONFIRMED")
    inbox = governance_inbox.build_inbox(session, project.id)
    conf = next(c for c in items_of(inbox, "CONFLICT") if c["source_id"] == rel_conf.id)
    assert conf["severity"] == "HIGH" and conf["bucket"] == "NEEDS_REVIEW"  # default policy blocks
    os.environ["EM_GATE_CONFIRMED_POLICY"] = "allow"
    try:
        inbox = governance_inbox.build_inbox(session, project.id)
        conf = next(c for c in items_of(inbox, "CONFLICT") if c["source_id"] == rel_conf.id)
        assert conf["severity"] == "MEDIUM" and conf["bucket"] == "CAN_WAIT"
        assert inbox["summary"]["blocked_expert_models"] == 0
    finally:
        os.environ.pop("EM_GATE_CONFIRMED_POLICY")
    session.delete(rel_conf)
    session.commit()

    print("Part 5 passed.")

    # Part 6: candidate revision is a NEEDS_REVIEW item; approval resolves it.
    print("\n--- Part 6: Revision lifecycle moves through the inbox buckets ---")
    candidate = revisions.create_candidate_revision(
        session, asset_ids[2], "Passwords must be rotated every 180 days.",
        actor="it-sec", change_reason="NIST update")
    inbox = governance_inbox.build_inbox(session, project.id)
    revs = items_of(inbox, "REVISION")
    assert len(revs) == 1
    rev_item = revs[0]
    assert rev_item["severity"] == "MEDIUM" and rev_item["bucket"] == "NEEDS_REVIEW"
    assert rev_item["deep_link"] == f"/?tab=revisions&revision={candidate.id}"

    revisions.review_revision(session, candidate.id, action="APPROVE", actor="gov", notes="ok")
    inbox = governance_inbox.build_inbox(session, project.id)
    revs = items_of(inbox, "REVISION")
    assert all(r["bucket"] == "RESOLVED" for r in revs)
    assert any(r["source_id"] == candidate.id and r["status"] == "APPROVED" for r in revs)
    assert inbox["summary"]["needs_review"] == 0
    print("Part 6 passed.")

    print("\n=== All Governance Inbox tests passed successfully! ===")


if __name__ == "__main__":
    main()
