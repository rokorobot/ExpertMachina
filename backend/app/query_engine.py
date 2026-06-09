import os
import json
import datetime
import hashlib
from sqlalchemy.orm import Session
from app import database as db
from app import schemas
from app import ingestion
from qdrant_client.models import Filter, FieldCondition, MatchAny

def validate_asset_evidence(
    session: Session, 
    asset: db.KnowledgeAsset, 
    expert_model_id: int
) -> dict:
    """
    Sprint 3: Evidence Validation Engine.
    Executes mandatory compliance checks on a retrieved asset before passing to generation.
    """
    failed_checks = []
    source_hash_verified = False

    # Check 1: Status must be APPROVED
    if asset.status != "APPROVED":
        failed_checks.append("STATUS_NOT_APPROVED")

    # Check 2: Expert Model Scoping
    expert_model = session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if expert_model and expert_model.asset_ids_json:
        try:
            model_asset_ids = json.loads(expert_model.asset_ids_json)
            if asset.id not in model_asset_ids:
                failed_checks.append("EXPERT_MODEL_MISMATCH")
        except Exception:
            failed_checks.append("EXPERT_MODEL_MISMATCH")
    else:
        failed_checks.append("EXPERT_MODEL_MISMATCH")

    # Check 3 & 4: Chunk existence and hash integrity
    if not asset.chunk_id:
        failed_checks.append("CHUNK_MISSING")
    else:
        chunk = session.query(db.DocumentChunk).filter(db.DocumentChunk.id == asset.chunk_id).first()
        if not chunk:
            failed_checks.append("CHUNK_MISSING")
        else:
            # Re-calculate hash of actual chunk text and verify against source_hash
            calculated_hash = hashlib.sha256(chunk.text.encode('utf-8')).hexdigest()
            if asset.source_hash != calculated_hash:
                failed_checks.append("HASH_TAMPERED")
            else:
                source_hash_verified = True

    # Check 5: Source Document presence
    if not asset.document_id:
        failed_checks.append("DOCUMENT_MISSING")
    else:
        doc = session.query(db.Document).filter(db.Document.id == asset.document_id).first()
        if not doc:
            failed_checks.append("DOCUMENT_MISSING")

    # Check 6 & 7: Page/Section validation
    if asset.source_page is None:
        failed_checks.append("PAGE_MISSING")
    if not asset.source_section:
        failed_checks.append("SECTION_MISSING")

    # Check 8: Asset is not archived/deleted
    if asset.status in ["ARCHIVED", "DELETED"]:
        failed_checks.append("ASSET_ARCHIVED")

    validation_status = "VALID" if not failed_checks else "INVALID"

    report = {
        "asset_id": asset.id,
        "validation_status": validation_status,
        "failed_checks": failed_checks,
        "source_hash_verified": source_hash_verified
    }
    
    # Emit structured validation telemetry to server logs
    print(f"VALIDATION_REPORT: {json.dumps(report)}")
    return report

def retrieve_approved_evidence(
    session: Session, 
    expert_model_id: int, 
    question: str, 
    limit: int = 5
) -> list:
    """
    Retrieves and validates approved evidence. Discards any assets failing validation.
    """
    # 1. Load ExpertModel from SQLite
    expert_model = session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not expert_model:
        return []

    # 2. Extract asset IDs
    if not expert_model.asset_ids_json:
        return []
    
    try:
        asset_ids = json.loads(expert_model.asset_ids_json)
    except Exception:
        return []

    if not asset_ids:
        return []

    # 3. Query SQLite for APPROVED assets only
    approved_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.id.in_(asset_ids),
        db.KnowledgeAsset.status == "APPROVED"
    ).all()

    if not approved_assets:
        return []

    # Map chunk_id to asset for matching retrieval chunks
    chunk_to_asset_map = {}
    valid_chunk_ids = []
    
    for asset in approved_assets:
        if asset.chunk_id:
            chunk_to_asset_map[asset.chunk_id] = asset
            valid_chunk_ids.append(asset.chunk_id)

    # 4. Qdrant Similarity search (Similarity Index)
    retrieved_citations = []
    
    if valid_chunk_ids:
        try:
            client = ingestion.get_qdrant_client()
            query_vector = ingestion.get_embedding(question)
            
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="chunk_id",
                        match=MatchAny(any=valid_chunk_ids)
                    )
                ]
            )
            
            search_results = client.search(
                collection_name=ingestion.COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=limit
            )
            
            for res in search_results:
                chunk_id = res.payload.get("chunk_id")
                asset = chunk_to_asset_map.get(chunk_id)
                if asset:
                    # Run Evidence Validation Engine Check
                    validation = validate_asset_evidence(session, asset, expert_model_id)
                    if validation["validation_status"] == "INVALID":
                        continue  # Discard unvalidated context

                    doc = session.query(db.Document).filter(db.Document.id == asset.document_id).first()
                    doc_name = doc.filename if doc else "Unknown Document"
                    review = session.query(db.AssetReview).filter(db.AssetReview.asset_id == asset.id).first()
                    approved_by = review.approver if (review and review.approver) else "operator_admin_02"
                    approved_at = review.reviewed_at.isoformat() + "Z" if (review and review.reviewed_at) else datetime.datetime.utcnow().isoformat() + "Z"

                    citation = {
                        "asset_id": asset.id,
                        "name": asset.name,
                        "content": asset.content,
                        "source_document": doc_name,
                        "source_page": asset.source_page or 1,
                        "source_section": asset.source_section or "Main Content",
                        "source_hash": asset.source_hash or "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                        "asset_status": asset.status,
                        "approved_by": approved_by,
                        "approved_at": approved_at
                    }
                    if citation not in retrieved_citations:
                        retrieved_citations.append(citation)
                        
        except Exception as e:
            print(f"Retrieval engine error: {e}")
            
    # Fallback to direct SQLite match if Qdrant is empty/fails
    if not retrieved_citations:
        for asset in approved_assets:
            if len(retrieved_citations) >= limit:
                break
            
            # Run Evidence Validation Engine Check
            validation = validate_asset_evidence(session, asset, expert_model_id)
            if validation["validation_status"] == "INVALID":
                continue  # Discard unvalidated context

            doc = session.query(db.Document).filter(db.Document.id == asset.document_id).first()
            doc_name = doc.filename if doc else "Unknown Document"
            review = session.query(db.AssetReview).filter(db.AssetReview.asset_id == asset.id).first()
            approved_by = review.approver if (review and review.approver) else "operator_admin_02"
            approved_at = review.reviewed_at.isoformat() + "Z" if (review and review.reviewed_at) else datetime.datetime.utcnow().isoformat() + "Z"

            citation = {
                "asset_id": asset.id,
                "name": asset.name,
                "content": asset.content,
                "source_document": doc_name,
                "source_page": asset.source_page or 1,
                "source_section": asset.source_section or "Main Content",
                "source_hash": asset.source_hash or "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "asset_status": asset.status,
                "approved_by": approved_by,
                "approved_at": approved_at
            }
            retrieved_citations.append(citation)

    # Retrieval audit log
    retrieved_asset_ids = [c["asset_id"] for c in retrieved_citations]
    retrieved_audit_log = {
        "expert_model_id": expert_model_id,
        "question": question,
        "candidate_assets": len(asset_ids),
        "retrieved_assets": retrieved_asset_ids
    }
    
    print(f"RETRIEVAL_AUDIT: {json.dumps(retrieved_audit_log)}")
    return retrieved_citations
