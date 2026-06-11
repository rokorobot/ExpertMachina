import os
import sys
import hashlib

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import revisions
from app import query_engine


def setup():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(
        session,
        schemas.ProjectCreate(name="Revision Test", description="Immutable history checks", customer_id=customer.id)
    )
    doc = crud.create_document(session, project_id=project.id, filename="SOP_Deviations.txt", file_path="uploads/sop.txt")
    original = "Critical deviations must be logged within 24 hours."
    chunk = db.DocumentChunk(document_id=doc.id, text=original, chunk_index=0)
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    asset = crud.create_knowledge_asset(
        session,
        schemas.KnowledgeAssetCreate(
            type="POLICY", name="Deviation Logging", content=original, project_id=project.id,
            document_id=doc.id, chunk_id=chunk.id, source_page=1, source_section="Sec 1",
            source_hash=hashlib.sha256(original.encode("utf-8")).hexdigest()
        )
    )
    return session, asset


def main():
    print("\nInitializing test database for Asset Revision Workflow checks...")
    session, asset = setup()

    # 1. First approval lazily creates baseline revision 1.
    print("\n--- Part 1: Lazy baseline revision on first approval ---")
    crud.update_knowledge_asset(session, asset_id=asset.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor="qa_lead_01")
    session.refresh(asset)
    assert len(asset.revisions) == 1, f"Expected baseline revision, got {len(asset.revisions)}"
    baseline = asset.revisions[0]
    assert baseline.revision_number == 1 and baseline.status == "APPROVED"
    assert baseline.content_hash == hashlib.sha256(asset.content.encode("utf-8")).hexdigest()
    assert asset.active_revision_number == 1
    print("Part 1 passed: revision 1 created from existing asset state on first approval.")

    # 2. Editing approved content creates a CANDIDATE revision; asset row untouched.
    print("\n--- Part 2: Approved content is never edited in place ---")
    original_content = asset.content
    edited = "Critical deviations must be logged within 12 hours."
    crud.update_knowledge_asset(session, asset_id=asset.id, update=schemas.KnowledgeAssetUpdate(content=edited), actor="sop_editor_01")
    session.refresh(asset)
    assert asset.content == original_content, "Approved asset content was mutated in place!"
    candidates = [r for r in asset.revisions if r.status == "CANDIDATE"]
    assert len(candidates) == 1, f"Expected one candidate revision, got {len(candidates)}"
    candidate = candidates[0]
    assert candidate.revision_number == 2 and candidate.content == edited
    assert candidate.supersedes_revision_id == baseline.id
    assert asset.has_pending_revision is True
    created_events = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "ASSET_REVISION_CREATED").count()
    assert created_events == 1, "Revision creation not audit-logged"
    print("Part 2 passed: edit diverted into candidate revision 2; active content unchanged.")

    # 3. Linear rule: no second candidate while one is pending.
    print("\n--- Part 3: Strictly linear (one pending candidate) ---")
    try:
        revisions.create_candidate_revision(session, asset.id, "Another edit.", actor="sop_editor_02")
        raise AssertionError("Second concurrent candidate revision was allowed")
    except ValueError:
        pass
    print("Part 3 passed: concurrent candidate rejected.")

    # 4. Approving the candidate supersedes the old revision and updates the projection.
    print("\n--- Part 4: Approval supersedes and promotes ---")
    revisions.review_revision(session, candidate.id, action="APPROVE", actor="governance_officer_01", notes="12h SLA per 2026 policy update")
    session.refresh(asset)
    session.refresh(baseline)
    session.refresh(candidate)
    assert asset.content == edited, "Asset projection not updated to approved revision content"
    assert candidate.status == "APPROVED" and candidate.approved_by == "governance_officer_01"
    assert baseline.status == "ARCHIVED", "Old revision not archived"
    assert baseline.superseded_by_revision_id == candidate.id, "supersedes chain broken"
    assert asset.active_revision_number == 2
    assert asset.has_pending_revision is False
    approved_events = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "ASSET_REVISION_APPROVED").count()
    assert approved_events == 1, "Revision approval not audit-logged"
    review_rows = session.query(db.AssetReview).filter(db.AssetReview.asset_id == asset.id).count()
    assert review_rows >= 2, "Revision approval did not record an AssetReview row"
    print("Part 4 passed: revision 2 active, revision 1 archived+superseded, fully audit-logged.")

    # 5. Rejection leaves the active revision untouched.
    print("\n--- Part 5: Rejected revisions change nothing ---")
    rejected = revisions.create_candidate_revision(session, asset.id, "Deviations need not be logged.", actor="rogue_editor")
    revisions.review_revision(session, rejected.id, action="REJECT", actor="governance_officer_01", notes="Contradicts regulatory requirement")
    session.refresh(asset)
    assert asset.content == edited
    assert asset.active_revision_number == 2
    rejected_events = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "ASSET_REVISION_REJECTED").count()
    assert rejected_events == 1
    print("Part 5 passed: rejection recorded; active content unchanged.")

    # 6. Revision integrity check: direct tampering around the workflow fails validation.
    print("\n--- Part 6: Revision integrity in evidence validation ---")
    citation = query_engine._build_citation(session, asset)
    assert citation["revision"] == 2, f"Citation missing active revision number, got {citation['revision']}"

    asset.content = "Tampered content bypassing the revision workflow."
    session.commit()
    report = query_engine.validate_asset_evidence(session, asset, expert_model_id=999, asset_hashes_override={str(asset.id): asset.source_hash})
    assert "REVISION_CONTENT_MISMATCH" in report["failed_checks"], \
        f"Direct content tampering not detected: {report['failed_checks']}"
    print("Part 6 passed: tampering around the revision workflow is detected at validation time.")

    # 7. Self-healing: approval SCHEDULES a background rescan of affected
    # Expert Models (v0.9.2a) - the approval itself returns immediately.
    print("\n--- Part 7: Post-approval conflict rescan is scheduled, then runs in background ---")
    import json as _json
    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Affected Expert", description="", project_id=asset.project_id, asset_ids=[asset.id]))
    fix = revisions.create_candidate_revision(
        session, asset.id, "Critical deviations must be logged within 12 hours.",
        actor="sop_editor_01", change_reason="Restore content after tamper test")
    revisions.review_revision(session, fix.id, action="APPROVE", actor="governance_officer_01")
    approved_event = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "ASSET_REVISION_APPROVED"
    ).order_by(db.AuditEvent.id.desc()).first()
    details = _json.loads(approved_event.details)
    assert details.get("rescan_scheduled") is True, "Approval event must record that a rescan was scheduled"
    assert details.get("affected_model_ids") == [model.id], \
        f"Approval event must name the affected models: {details.get('affected_model_ids')}"
    assert "post_approval_scans" not in details, \
        "Approval event must not pretend scans already completed"

    # Simulate the background task (the endpoint schedules
    # revisions.run_post_approval_rescan; tests drive the same logic with
    # the test session instead of a fresh SessionLocal).
    session.refresh(asset)
    scans = revisions._rescan_affected_models(session, asset)
    assert len(scans) == 1 and scans[0]["expert_model_id"] == model.id, \
        f"Affected Expert Model not rescanned by background task: {scans}"
    assert "semantic_conflict_score" in scans[0], "Rescan result missing refreshed conflict score"
    if scans[0]["nli_available"]:
        scan_events = session.query(db.AuditEvent).filter(
            db.AuditEvent.event_type == "CONFLICT_SCAN_COMPLETED",
            db.AuditEvent.target_id == str(model.id)
        ).count()
        assert scan_events >= 1, "Background scan must write its own CONFLICT_SCAN_COMPLETED event"
    print(f"  Rescan recorded: {scans[0]}")
    print("Part 7 passed: approval schedules the rescan; background task heals the conflict graph.")

    session.close()
    print("\n=== All Asset Revision Workflow tests passed successfully! ===")


if __name__ == "__main__":
    main()
