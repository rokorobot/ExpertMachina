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
from app import ingestion
from app import query_engine
import test_support


def _disabled_qdrant():
    raise RuntimeError("Qdrant disabled in integrity test: force deterministic SQLite path")


def build_fixture(session):
    customer = crud.get_or_create_default_customer(session)
    qa_lead = test_support.governed_actor(session, "qa_lead_01")
    project = crud.create_project(
        session,
        schemas.ProjectCreate(name="Integrity Test", description="Access and provenance checks", customer_id=customer.id),
        actor=qa_lead
    )
    doc = crud.create_document(session, project_id=project.id, filename="Tiered_Policies.txt", file_path="uploads/Tiered_Policies.txt", actor=qa_lead)

    assets = {}
    tiers = [
        ("PUBLIC", "Office hours are 9 to 5 on weekdays."),
        ("INTERNAL", "Critical deviations must be logged within 24 hours."),
        ("EXECUTIVE", "Executive bonus pool is 4 percent of net profit."),
    ]
    for idx, (tier, text) in enumerate(tiers):
        chunk = db.DocumentChunk(document_id=doc.id, text=text, chunk_index=idx)
        session.add(chunk)
        session.commit()
        session.refresh(chunk)
        asset = crud.create_knowledge_asset(
            session,
            schemas.KnowledgeAssetCreate(
                type="POLICY",
                name=f"{tier} Policy",
                content=text,
                project_id=project.id,
                document_id=doc.id,
                chunk_id=chunk.id,
                source_page=idx + 1,
                source_section=f"Sec {idx + 1}",
                source_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                access_level=tier
            )
        )
        crud.update_knowledge_asset(session, asset_id=asset.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor=qa_lead)
        assets[tier] = asset

    model = crud.create_expert_model(
        session,
        schemas.ExpertModelCreate(
            name="Tiered Expert",
            description="Access tier checks",
            project_id=project.id,
            asset_ids=[a.id for a in assets.values()]
        ),
        actor=qa_lead
    )
    return assets, model


def test_access_level_enforcement(session, assets, model):
    print("\n--- Part 1: Access tier enforcement in evidence retrieval ---")

    res_internal = query_engine.retrieve_approved_evidence(
        session, expert_model_id=model.id, question="What are the policies?", caller_access_level="INTERNAL"
    )
    cited_ids = [c["asset_id"] for c in res_internal["citations"]]
    assert assets["EXECUTIVE"].id not in cited_ids, "EXECUTIVE asset leaked to INTERNAL caller"
    assert assets["EXECUTIVE"].id in res_internal["access_blocked_asset_ids"], "Blocked asset not recorded for audit"
    assert assets["PUBLIC"].id in cited_ids and assets["INTERNAL"].id in cited_ids, \
        "Caller-tier assets missing from citations"

    res_exec = query_engine.retrieve_approved_evidence(
        session, expert_model_id=model.id, question="What are the policies?", caller_access_level="EXECUTIVE"
    )
    exec_cited = [c["asset_id"] for c in res_exec["citations"]]
    assert assets["EXECUTIVE"].id in exec_cited, "EXECUTIVE caller must see EXECUTIVE assets"
    assert res_exec["access_blocked_asset_ids"] == [], "EXECUTIVE caller should have nothing blocked"

    res_public = query_engine.retrieve_approved_evidence(
        session, expert_model_id=model.id, question="What are the policies?", caller_access_level="PUBLIC"
    )
    public_cited = [c["asset_id"] for c in res_public["citations"]]
    assert public_cited == [assets["PUBLIC"].id], f"PUBLIC caller must see only PUBLIC assets, got {public_cited}"

    print("Part 1 passed: access tiers enforced, blocked assets audit-logged.")


def test_honest_provenance(session, assets, model):
    print("\n--- Part 2: Honest provenance in citations ---")

    res = query_engine.retrieve_approved_evidence(
        session, expert_model_id=model.id, question="What are the policies?", caller_access_level="EXECUTIVE"
    )
    by_id = {c["asset_id"]: c for c in res["citations"]}

    # Approval via crud now records a real review row.
    cite = by_id[assets["INTERNAL"].id]
    assert cite["approved_by"] == "qa_lead_01", f"Expected real approver, got {cite['approved_by']}"
    assert cite["approved_at"] is not None, "Approval timestamp missing despite recorded review"
    assert cite["approved_by"] != "operator_admin_02", "Fabricated approver fallback still present"

    # An approved asset with no review row must report None, not a fabricated identity.
    orphan_text = "Legacy policy approved before review tracking existed."
    orphan_chunk = db.DocumentChunk(document_id=assets["PUBLIC"].document_id, text=orphan_text, chunk_index=99)
    session.add(orphan_chunk)
    session.commit()
    session.refresh(orphan_chunk)
    orphan = db.KnowledgeAsset(
        project_id=assets["PUBLIC"].project_id,
        type="POLICY",
        name="Orphan Policy",
        content=orphan_text,
        status="APPROVED",
        access_level="PUBLIC",
        document_id=assets["PUBLIC"].document_id,
        chunk_id=orphan_chunk.id,
        source_page=9,
        source_section="Sec 9",
        source_hash=hashlib.sha256(orphan_text.encode("utf-8")).hexdigest()
    )
    session.add(orphan)
    session.commit()
    session.refresh(orphan)

    citation = query_engine._build_citation(session, orphan)
    assert citation["approved_by"] is None, f"Expected None for unrecorded approver, got {citation['approved_by']}"
    assert citation["approved_at"] is None, "Expected None for unrecorded approval timestamp"

    print("Part 2 passed: citations report recorded provenance or None - never fabricated values.")


if __name__ == "__main__":
    print("\nInitializing test database for integrity and access checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    ingestion.get_qdrant_client = _disabled_qdrant

    assets, model = build_fixture(session)
    test_access_level_enforcement(session, assets, model)
    test_honest_provenance(session, assets, model)
    session.close()
    print("\n=== All MVP 0.5 integrity and access control tests passed successfully! ===")
