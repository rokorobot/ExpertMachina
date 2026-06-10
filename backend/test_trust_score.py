import os
import sys
import json
import hashlib
import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import revisions
from app import trust


def make_asset(session, project, doc, name, content):
    chunk = db.DocumentChunk(document_id=doc.id, text=content, chunk_index=0)
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    asset = crud.create_knowledge_asset(session, schemas.KnowledgeAssetCreate(
        type="POLICY", name=name, content=content, project_id=project.id,
        document_id=doc.id, chunk_id=chunk.id, source_page=1, source_section="S1",
        source_hash=hashlib.sha256(content.encode()).hexdigest()))
    crud.update_knowledge_asset(session, asset_id=asset.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor="qa_lead")
    return asset


def main():
    print("\nInitializing test database for Trust Score checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(name="Trust Test", description="", customer_id=customer.id))
    doc = crud.create_document(session, project_id=project.id, filename="P.txt", file_path="uploads/p.txt")

    # --- Model A: rich data with governance debt ---
    a1 = make_asset(session, project, doc, "Policy A", "Customer data must be deleted after 30 days.")
    a2 = make_asset(session, project, doc, "Policy B", "Customer data must be retained indefinitely.")
    model_a = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Rich Model", description="", project_id=project.id, asset_ids=[a1.id, a2.id]))

    # Completed evaluation run: pass rate 0.8, avg coverage 0.9.
    session.add(db.EvaluationRun(
        project_id=project.id, expert_model_id=model_a.id,
        asset_ids_snapshot="[]", asset_hashes_snapshot="{}", benchmark_question_ids_snapshot="[]",
        status="COMPLETED", pass_rate=0.8, average_coverage_score=0.9, average_confidence_score=0.85,
        completed_at=datetime.datetime.utcnow()))
    # One unreviewed direct contradiction (blocks the compile gate too).
    session.add(db.AssetRelationship(
        project_id=project.id, expert_model_id=model_a.id,
        source_asset_id=a1.id, target_asset_id=a2.id,
        relationship_type="CONFLICTS_WITH", classification="DIRECT_CONTRADICTION",
        confidence=0.99, status="DETECTED", verifier_json=json.dumps({"method": "TEST"})))
    session.commit()
    # One pending candidate revision.
    revisions.create_candidate_revision(session, a1.id, "Customer data must be deleted after 60 days.",
                                        actor="editor", change_reason="test")

    print("\n--- Part 1: Hierarchical score with full breakdown ---")
    result = trust.compute_trust_score(session, model_a.id)
    by_key = {c["key"]: c for c in result["components"]}

    assert by_key["evaluation_reliability"]["score"] == 80.0
    assert by_key["evidence_coverage"]["score"] == 90.0
    # 1 detected direct contradiction -> conflict score 90.
    assert by_key["conflict_integrity"]["score"] == 90.0
    # Governance health: 100 - 8 (unreviewed) - 5 (pending revision) - 15 (blocked gate) = 72.
    assert by_key["governance_health"]["score"] == 72.0, f"Got {by_key['governance_health']}"
    assert by_key["revision_freshness"]["score"] == 100.0  # reviews just happened
    # Aggregate: 80*.25 + 90*.20 + 90*.25 + 72*.20 + 100*.10 = 84.9
    assert result["trust_score"] == 84.9, f"Expected 84.9, got {result['trust_score']}"
    assert all(c["reason"] for c in result["components"]), "Every component must carry a reason"
    penalties = {p["signal"] for p in by_key["governance_health"]["details"]["penalties"]}
    assert penalties == {"unreviewed_conflicts", "pending_revisions", "compile_gate_blocked"}
    print(f"  Trust {result['trust_score']} | " + " | ".join(f"{c['label']}: {c['score']}" for c in result["components"]))
    print("Part 1 passed: hierarchical score with exact, explainable components.")

    print("\n--- Part 2: Unmeasured components are excluded, never fabricated ---")
    b1 = make_asset(session, project, doc, "Clean Policy", "Visitors must sign in at reception.")
    model_b = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Bare Model", description="", project_id=project.id, asset_ids=[b1.id]))
    result_b = trust.compute_trust_score(session, model_b.id)
    by_key_b = {c["key"]: c for c in result_b["components"]}
    assert by_key_b["evaluation_reliability"]["measured"] is False
    assert by_key_b["evaluation_reliability"]["score"] is None
    assert by_key_b["evidence_coverage"]["measured"] is False
    assert by_key_b["conflict_integrity"]["score"] == 100.0
    assert by_key_b["governance_health"]["score"] == 100.0
    assert by_key_b["revision_freshness"]["score"] == 100.0
    # Renormalized over measured weights: perfect components -> 100.
    assert result_b["trust_score"] == 100.0, f"Expected 100.0, got {result_b['trust_score']}"
    assert "3 of 5 components" in result_b["summary"]
    print("Part 2 passed: NOT_MEASURED components excluded; weights renormalized.")

    print("\n--- Part 3: Freshness decays with review age ---")
    # Age all reviews of model B's asset by ~200 days.
    for review in session.query(db.AssetReview).filter(db.AssetReview.asset_id == b1.id).all():
        review.reviewed_at = datetime.datetime.utcnow() - datetime.timedelta(days=200)
    session.commit()
    aged = trust.compute_trust_score(session, model_b.id)
    fresh = {c["key"]: c for c in aged["components"]}["revision_freshness"]
    assert fresh["score"] == 50.0, f"Expected 50.0 for 200-day-old review, got {fresh['score']}"
    assert "200 days ago" in fresh["reason"]
    print("Part 3 passed: freshness tiers respond to review age with explainable reasons.")

    session.close()
    print("\n=== All Expert Model Trust Score tests passed successfully! ===")


if __name__ == "__main__":
    main()
