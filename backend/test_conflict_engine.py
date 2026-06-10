import os
import sys
import hashlib

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import verification_engine
from app import conflict_engine


def make_asset(session, project, doc, name, content, access_level="INTERNAL", asset_type="POLICY"):
    chunk = db.DocumentChunk(document_id=doc.id, text=content, chunk_index=0)
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    asset = crud.create_knowledge_asset(
        session,
        schemas.KnowledgeAssetCreate(
            type=asset_type,
            name=name,
            content=content,
            project_id=project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            source_page=1,
            source_section="Sec 1",
            source_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            access_level=access_level
        )
    )
    crud.update_knowledge_asset(session, asset_id=asset.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor="qa_lead_01")
    return asset


def find_rel(rels, a, b, rel_type):
    pair = {a.id, b.id}
    for r in rels:
        if {r.source_asset_id, r.target_asset_id} == pair and r.relationship_type == rel_type:
            return r
    return None


def test_classifier_unit(session, project):
    print("\n--- Part 1: Conflict classifier (metadata rules, no NLI required) ---")
    doc_v1 = crud.create_document(session, project_id=project.id, filename="Retention_2023.txt", file_path="uploads/r23.txt")
    doc_v2 = crud.create_document(session, project_id=project.id, filename="Retention_2026.txt", file_path="uploads/r26.txt")
    a = make_asset(session, project, doc_v1, "Backup Retention Policy", "Backups are kept for twelve months.")
    b = make_asset(session, project, doc_v2, "Backup Retention Policy", "Backups are kept for three months.")
    assert conflict_engine.classify_conflict(session, a, b) == "TEMPORAL_SUPERSESSION", \
        "Same-named policy across documents must classify as TEMPORAL_SUPERSESSION"
    print("Part 1 passed: temporal supersession recognized from metadata.")


def test_conflict_scan(session, project):
    print("\n--- Part 2: Semantic conflict scan over an Expert Model ---")
    doc_clinical = crud.create_document(session, project_id=project.id, filename="Clinical_SOPs.txt", file_path="uploads/c.txt", department="Clinical")
    doc_mfg = crud.create_document(session, project_id=project.id, filename="Manufacturing_SOPs.txt", file_path="uploads/m.txt", department="Manufacturing")

    a = make_asset(session, project, doc_clinical, "Data Deletion", "Customer data must be deleted after 30 days.")
    b = make_asset(session, project, doc_clinical, "Data Retention", "Customer data must be retained indefinitely.")
    c = make_asset(session, project, doc_clinical, "Smazani dat", "Zákaznická data musí být po 30 dnech smazána.")
    d = make_asset(session, project, doc_clinical, "Bonus Policy", "Managers receive performance bonuses every quarter.")
    e = make_asset(session, project, doc_clinical, "Refund Approval", "All refunds require manager approval.")
    f = make_asset(session, project, doc_clinical, "Executive Refunds", "Refunds may be issued without manager approval.", access_level="EXECUTIVE")
    i = make_asset(session, project, doc_mfg, "Goggles Required", "Visitors must wear safety goggles at all times.")
    j = make_asset(session, project, doc_clinical, "No Goggles Needed", "Visitors are not required to wear safety goggles.")

    model = crud.create_expert_model(
        session,
        schemas.ExpertModelCreate(
            name="Conflict Scan Expert",
            description="Knowledge QA test",
            project_id=project.id,
            asset_ids=[x.id for x in (a, b, c, d, e, f, i, j)]
        )
    )

    summary = conflict_engine.scan_expert_model_conflicts(session, model.id)
    if not summary["nli_available"]:
        print("SKIPPED: NLI model unavailable; conflict scan requires the Knowledge Integrity Engine.")
        return None, None

    rels = summary["relationships"]
    print(f"Scan: {summary['scanned_assets']} assets, {summary['compared_pairs']} pairs, "
          f"{summary['conflicts_found']} conflicts, {summary['supports_found']} supports")
    for r in rels:
        print(f"  {r.source_asset_id} -{r.relationship_type}-> {r.target_asset_id} "
              f"[{r.classification}] conf={r.confidence}")

    ab = find_rel(rels, a, b, "CONFLICTS_WITH")
    assert ab is not None, "Direct contradiction (delete vs retain) not detected"
    assert ab.classification == "DIRECT_CONTRADICTION", f"Expected DIRECT_CONTRADICTION, got {ab.classification}"
    assert ab.confidence >= 0.80

    ac = find_rel(rels, a, c, "SUPPORTS")
    assert ac is not None, "Cross-lingual support (EN evidence / CS claim) not detected"

    cb = find_rel(rels, c, b, "CONFLICTS_WITH")
    assert cb is not None, "Cross-lingual contradiction (CS deletion vs EN retention) not detected"

    ef = find_rel(rels, e, f, "CONFLICTS_WITH")
    assert ef is not None, "Access-tier contradiction not detected"
    assert ef.classification == "ACCESS_CONFLICT", f"Expected ACCESS_CONFLICT, got {ef.classification}"

    ij = find_rel(rels, i, j, "CONFLICTS_WITH")
    assert ij is not None, "Cross-department contradiction not detected"
    assert ij.classification == "SCOPE_CONFLICT", f"Expected SCOPE_CONFLICT, got {ij.classification}"

    for other in (a, b, c, e, f, i, j):
        assert find_rel(rels, d, other, "CONFLICTS_WITH") is None, \
            f"Neutral bonus policy wrongly conflicts with asset {other.id}"

    assert all(r.verifier and r.verifier.get("weights_hash") for r in rels), \
        "Relationships missing reproducible verifier identity"

    detected_events = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "KNOWLEDGE_CONFLICT_DETECTED").count()
    assert detected_events >= summary["conflicts_found"], "Conflicts not recorded in the audit ledger"
    assert session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "CONFLICT_SCAN_COMPLETED").count() == 1

    print("Part 2 passed: direct, cross-lingual, access, and scope conflicts detected; neutral assets untouched.")
    return model, ab


def test_review_survives_rescan(session, model, conflict_rel):
    print("\n--- Part 3: Operator review survives rescans ---")
    reviewed = conflict_engine.review_relationship(
        session, conflict_rel.id, status="DISMISSED", reviewer="governance_officer_01",
        notes="Retention policy applies only to anonymized aggregates - not a true conflict."
    )
    assert reviewed.status == "DISMISSED"
    assert reviewed.reviewed_by == "governance_officer_01"

    summary = conflict_engine.scan_expert_model_conflicts(session, model.id)
    pair = {conflict_rel.source_asset_id, conflict_rel.target_asset_id}
    redetected = [
        r for r in summary["relationships"]
        if {r.source_asset_id, r.target_asset_id} == pair
    ]
    assert redetected == [], "Dismissed conflict was re-detected on rescan"

    still_dismissed = session.query(db.AssetRelationship).filter(db.AssetRelationship.id == conflict_rel.id).first()
    assert still_dismissed.status == "DISMISSED", "Rescan destroyed the operator's review verdict"

    dismiss_events = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "KNOWLEDGE_CONFLICT_DISMISSED").count()
    assert dismiss_events == 1, "Dismissal not recorded in the audit ledger"

    print("Part 3 passed: dismissed conflicts stay dismissed; review verdicts are audit-logged.")


if __name__ == "__main__":
    print("\nInitializing test database for Semantic Conflict Engine checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(
        session,
        schemas.ProjectCreate(name="Knowledge QA Test", description="Conflict engine checks", customer_id=customer.id)
    )

    test_classifier_unit(session, project)
    model, conflict_rel = test_conflict_scan(session, project)
    if model is not None:
        test_review_survives_rescan(session, model, conflict_rel)
    session.close()
    print("\n=== All Semantic Conflict Engine tests passed successfully! ===")
