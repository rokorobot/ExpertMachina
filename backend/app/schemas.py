from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CustomerBase(BaseModel):
    name: str

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: int
    api_key: str
    class Config:
        from_attributes = True

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    customer_id: int

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    status: str
    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: int
    project_id: int
    filename: str
    file_type: Optional[str]
    department: Optional[str]
    owner: Optional[str]
    version: Optional[str]
    file_path: Optional[str]
    status: str
    created_at: datetime
    modified_at: datetime
    class Config:
        from_attributes = True

class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    text: str
    chunk_index: int
    table_count: int
    docling_json: Optional[str]
    embedding_ref: Optional[str]
    class Config:
        from_attributes = True

class QualityScoreBase(BaseModel):
    coverage_score: int
    freshness_score: int
    verification_score: int
    conflict_score: int
    overall_score: int

class QualityScoreResponse(QualityScoreBase):
    id: int
    asset_id: int
    recorded_at: datetime
    class Config:
        from_attributes = True

class AssetReviewBase(BaseModel):
    reviewer: Optional[str]
    approver: Optional[str]
    notes: Optional[str]

class AssetReviewCreate(AssetReviewBase):
    pass

class AssetReviewResponse(AssetReviewBase):
    id: int
    asset_id: int
    reviewed_at: datetime
    class Config:
        from_attributes = True

class KnowledgeAssetBase(BaseModel):
    type: str # PROCEDURE, POLICY, ROLE, etc.
    name: str
    owner: Optional[str] = None
    condition: Optional[str] = None
    source_citation: Optional[str] = None
    content: str
    access_level: Optional[str] = "INTERNAL" # PUBLIC, INTERNAL, etc.
    extraction_method: Optional[str] = "MOCK_RULE_BASED"

class KnowledgeAssetCreate(KnowledgeAssetBase):
    project_id: int
    document_id: Optional[int] = None
    chunk_id: Optional[int] = None
    source_page: Optional[int] = None
    source_section: Optional[str] = None
    source_hash: Optional[str] = None

class KnowledgeAssetUpdate(BaseModel):
    name: Optional[str] = None
    owner: Optional[str] = None
    condition: Optional[str] = None
    source_citation: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None # CANDIDATE, REVIEWED, APPROVED, ARCHIVED
    access_level: Optional[str] = None

class KnowledgeAssetResponse(KnowledgeAssetBase):
    id: int
    project_id: int
    status: str
    document_id: Optional[int]
    chunk_id: Optional[int]
    source_page: Optional[int]
    source_section: Optional[str]
    source_hash: Optional[str]
    created_at: datetime
    quality_scores: List[QualityScoreResponse] = []
    reviews: List[AssetReviewResponse] = []
    class Config:
        from_attributes = True

class ExpertModelBase(BaseModel):
    name: str
    description: Optional[str] = None
    project_id: int

class ExpertModelCreate(ExpertModelBase):
    asset_ids: List[int] # List of asset IDs to group

class ExpertModelResponse(ExpertModelBase):
    id: int
    asset_count: int
    quality_score: float
    coverage_score: float
    created_at: datetime
    class Config:
        from_attributes = True

class AgentPackageBase(BaseModel):
    name: str
    expert_model_id: int
    project_id: int
    governance_version: Optional[str] = "0.1.0"

class AgentPackageCreate(AgentPackageBase):
    pass

class AgentPackageResponse(AgentPackageBase):
    id: int
    quality_score: float
    asset_references: Optional[str] # JSON string of asset references and metadata
    created_at: datetime
    class Config:
        from_attributes = True

class AuditEventResponse(BaseModel):
    id: int
    timestamp: datetime
    actor: str
    event_type: str
    target_id: Optional[str]
    details: Optional[str]
    class Config:
        from_attributes = True

class AssetBulkUpdate(BaseModel):
    asset_ids: List[int]
    status: str

class QueryInput(BaseModel):
    expert_model_id: int
    question: str

class CitationModel(BaseModel):
    asset_id: int
    name: str
    content: str
    source_document: str
    source_page: int
    source_section: str
    source_hash: str
    asset_status: str
    approved_by: str
    approved_at: str

class QueryResponse(BaseModel):
    answer: str
    confidence_score: float
    coverage_score: float
    verification_status: str
    citations: List[CitationModel]
    unsupported_claims: Optional[List[str]] = []

class BenchmarkQuestionBase(BaseModel):
    question: str
    expected_answer_type: str # FACTUAL | PROCEDURAL | POLICY | REFUSAL
    required_citation_count: Optional[int] = 0
    tags: Optional[str] = None
    severity: Optional[str] = "MEDIUM" # LOW | MEDIUM | HIGH | CRITICAL
    min_required_coverage: Optional[float] = 0.95

class BenchmarkQuestionCreate(BenchmarkQuestionBase):
    project_id: int
    expected_claims: List[str]

class BenchmarkQuestionUpdate(BaseModel):
    question: Optional[str] = None
    expected_claims: Optional[List[str]] = None
    expected_answer_type: Optional[str] = None
    required_citation_count: Optional[int] = None
    tags: Optional[str] = None
    severity: Optional[str] = None
    min_required_coverage: Optional[float] = None

class BenchmarkQuestionResponse(BenchmarkQuestionBase):
    id: int
    project_id: int
    expected_claims: List[str]
    created_at: datetime
    class Config:
        from_attributes = True

