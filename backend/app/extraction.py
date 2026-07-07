import os
import hashlib
import re
import datetime
from sqlalchemy.orm import Session
from app import database as db
from app import schemas
from app import crud
from app.logging_config import get_logger

logger = get_logger(__name__)

# Types of assets: PROCEDURE, POLICY, ROLE, SYSTEM, WORKFLOW, PRODUCT, DEPARTMENT

def extract_knowledge_assets_from_project(session: Session, project_id: int):
    # Find all parsed documents for this project
    documents = session.query(db.Document).filter(
        db.Document.project_id == project_id,
        db.Document.status == "PARSED"
    ).all()
    
    if not documents:
        return False
        
    api_key = os.environ.get("OPENAI_API_KEY")
    use_llm = api_key and not api_key.startswith("mock-")
    
    extracted_any = False
    
    for doc in documents:
        # Check if we already have assets for this document
        existing_assets = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.document_id == doc.id).first()
        if existing_assets:
            # Already extracted, ensure document lifecycle state is correctly updated
            crud.update_document_lifecycle(session, doc.id)
            continue
            
        chunks = session.query(db.DocumentChunk).filter(db.DocumentChunk.document_id == doc.id).all()
        if not chunks:
            continue
            
        doc_extracted = False
        for chunk in chunks:
            if use_llm:
                extracted = extract_via_llm(session, project_id, doc, chunk, api_key)
            else:
                extracted = extract_via_rules(session, project_id, doc, chunk)
                
            if extracted:
                doc_extracted = True
                extracted_any = True
                
        if doc_extracted:
            crud.update_document_lifecycle(session, doc.id)
                
    if extracted_any:
        crud.update_project_status(session, project_id, "REVIEW")
        
    return True

def extract_via_llm(session: Session, project_id: int, doc: db.Document, chunk: db.DocumentChunk, api_key: str) -> bool:
    try:
        import json
        import re
        from app import llm as llm_settings

        # T2.6 shed: native openai SDK + JSON parse, replacing the legacy
        # llama_index.core.program.LLMTextCompletionProgram structured-output
        # wrapper. Model-agnostic (works on any chat model, unlike the native
        # structured-output API), and consistent with the JSON idiom already
        # used in claims._decompose_llm.
        prompt = (
            "Analyze the following document chunk and extract distinct organizational "
            "knowledge assets.\n"
            f"Chunk text:\n{chunk.text}\n\n"
            'Output ONLY a JSON object of the form {"assets": [{"type": "...", '
            '"name": "...", "owner": "...", "condition": "...", "source_citation": "...", '
            '"content": "...", "source_section": "..."}]}. '
            "type must be one of PROCEDURE, POLICY, ROLE, SYSTEM, WORKFLOW, PRODUCT, DEPARTMENT."
        )
        raw = llm_settings.openai_complete(llm_settings.model_for("EXTRACTION", session), prompt)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return False
        parsed = json.loads(match.group(0))
        extracted = parsed.get("assets", []) if isinstance(parsed, dict) else []
        if not extracted:
            return False

        for asset in extracted:
            source_hash = hashlib.sha256(chunk.text.encode()).hexdigest()

            # Map type to allowed values
            asset_type = str(asset.get("type", "")).upper()
            if asset_type not in ["PROCEDURE", "POLICY", "ROLE", "SYSTEM", "WORKFLOW", "PRODUCT", "DEPARTMENT"]:
                asset_type = "POLICY"

            db_asset = schemas.KnowledgeAssetCreate(
                project_id=project_id,
                type=asset_type,
                name=asset.get("name") or "Unnamed Asset",
                owner=asset.get("owner") or doc.department or "QA",
                condition=asset.get("condition") or "Always",
                source_citation=asset.get("source_citation") or f"{doc.filename} Chunk {chunk.chunk_index}",
                content=asset.get("content") or "",
                document_id=doc.id,
                chunk_id=chunk.id,
                source_page=1, # Default mock page
                source_section=asset.get("source_section") or "Intro",
                source_hash=source_hash,
                extraction_method="LLM_ASSISTED"
            )
            created = crud.create_knowledge_asset(session, db_asset)
            evaluate_and_save_quality_score(session, created.id, created)

        return True
    except Exception as e:
        logger.warning("LLM Extraction failed: %s. Falling back to Rule Extraction.", e)
        return extract_via_rules(session, project_id, doc, chunk)

def extract_via_rules(session: Session, project_id: int, doc: db.Document, chunk: db.DocumentChunk) -> bool:
    # Rule-based pattern matching fallback
    text = chunk.text
    source_hash = hashlib.sha256(text.encode()).hexdigest()
    
    # We will look for business rules, policies, and procedures
    # Check for keywords and split sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    extracted = False
    
    # Pre-built patterns
    patterns = [
        {
            "type": "POLICY",
            "keywords": ["must", "required", "shall", "mandatory", "policy", "agreement"],
            "owner": "Compliance"
        },
        {
            "type": "PROCEDURE",
            "keywords": ["how to", "step", "first", "then", "process", "workflow", "closure", "deviation", "review"],
            "owner": "Operations"
        },
        {
            "type": "ROLE",
            "keywords": ["role", "responsible for", "officer", "manager", "director", "owner"],
            "owner": "HR"
        },
        {
            "type": "SYSTEM",
            "keywords": ["database", "software", "qdrant", "postgresql", "sqlite", "server", "platform", "system", "infrastructure"],
            "owner": "IT"
        }
    ]
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 30:
            continue
            
        for pat in patterns:
            if any(kw in sentence.lower() for kw in pat["keywords"]):
                # Construct asset name from first few words
                words = sentence.split()
                name = " ".join(words[:4]).rstrip(",.:;-_")
                if len(name) > 40:
                    name = name[:40] + "..."
                    
                # Identify condition if possible
                condition = "General Use"
                if "before" in sentence.lower():
                    condition = "Before action"
                elif "after" in sentence.lower():
                    condition = "Post action"
                elif "if" in sentence.lower():
                    match = re.search(r'if\s+([^,.]+)', sentence, re.IGNORECASE)
                    if match:
                        condition = f"If {match.group(1)}"
                
                db_asset = schemas.KnowledgeAssetCreate(
                    project_id=project_id,
                    type=pat["type"],
                    name=name,
                    owner=pat["owner"],
                    condition=condition,
                    source_citation=f"{doc.filename} (Line {chunk.chunk_index * 10 + 1})",
                    content=sentence,
                    document_id=doc.id,
                    chunk_id=chunk.id,
                    source_page=1 + (chunk.chunk_index // 3),
                    source_section=f"Section {pat['type'].capitalize()} Rules",
                    source_hash=source_hash,
                    extraction_method="MOCK_RULE_BASED"
                )
                
                created = crud.create_knowledge_asset(session, db_asset)
                evaluate_and_save_quality_score(session, created.id, created)
                extracted = True
                break # Extract one asset per sentence max
                
    # If no specific patterns matched but text is not empty, create a generic policy asset
    if not extracted and len(text.strip()) > 50:
        db_asset = schemas.KnowledgeAssetCreate(
            project_id=project_id,
            type="POLICY",
            name=f"Info Asset {chunk.chunk_index + 1}",
            owner=doc.department or "Operations",
            condition="Always",
            source_citation=f"{doc.filename} (Chunk {chunk.chunk_index})",
            content=text[:250] + "..." if len(text) > 250 else text,
            document_id=doc.id,
            chunk_id=chunk.id,
            source_page=1 + (chunk.chunk_index // 3),
            source_section="General",
            source_hash=source_hash,
            extraction_method="MOCK_RULE_BASED"
        )
        created = crud.create_knowledge_asset(session, db_asset)
        evaluate_and_save_quality_score(session, created.id, created)
        extracted = True
        
    return extracted

def evaluate_and_save_quality_score(session: Session, asset_id: int, asset: db.KnowledgeAsset):
    # Formulas for MVP Quality Scoring
    
    # 1. Coverage Score (0-100)
    # Higher if content is descriptive and has a valid citation
    coverage_score = 75
    if len(asset.content) > 100:
        coverage_score += 15
    if asset.source_citation:
        coverage_score += 10
    coverage_score = min(coverage_score, 100)
    
    # 2. Freshness Score (0-100)
    # Higher for newer assets
    freshness_score = 90
    
    # 3. Verification Score (0-100)
    # Higher if owner and condition are defined
    verification_score = 50
    if asset.owner and asset.owner != "System":
        verification_score += 25
    if asset.condition and asset.condition != "Always":
        verification_score += 25
    verification_score = min(verification_score, 100)
    
    # 4. Conflict Score (0-100)
    # Higher is better (meaning NO conflicts). We will mock this or perform a basic word distance search
    # Check other assets in the same project with similar names
    conflict_score = 95
    similar = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == asset.project_id,
        db.KnowledgeAsset.id != asset.id,
        db.KnowledgeAsset.name == asset.name
    ).first()
    if similar:
        conflict_score = 40 # potential conflict / duplication
        
    # Calculate Overall Score (average)
    overall = int((coverage_score + freshness_score + verification_score + conflict_score) / 4)
    
    score_in = schemas.QualityScoreBase(
        coverage_score=coverage_score,
        freshness_score=freshness_score,
        verification_score=verification_score,
        conflict_score=conflict_score,
        overall_score=overall
    )
    
    crud.create_quality_score(session, asset_id, score_in)
    return score_in
