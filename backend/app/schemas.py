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
    # Revision projection (MVP 0.7 Sprint 4)
    revision_count: Optional[int] = 0
    active_revision_number: Optional[int] = None
    has_pending_revision: Optional[bool] = False
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

class SourceConnectorCreate(BaseModel):
    name: str
    root_path: str
    type: Optional[str] = "LOCAL_FOLDER"
    include_extensions: Optional[str] = None # comma-separated; defaults to all supported

class SourceConnectorResponse(BaseModel):
    id: int
    project_id: int
    name: str
    type: str
    root_path: str
    include_extensions: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class IngestionJobResponse(BaseModel):
    id: int
    project_id: int
    connector_id: int
    status: str # PENDING | RUNNING | COMPLETED | FAILED
    files_discovered: int
    files_ingested: int
    files_duplicate: int
    files_failed: int
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class SourceDocumentResponse(BaseModel):
    id: int
    ingestion_job_id: int
    source_uri: str
    file_hash: Optional[str] = None
    size_bytes: Optional[int] = None
    source_modified_at: Optional[datetime] = None
    status: str # INGESTED | DUPLICATE | FAILED
    error: Optional[str] = None
    document_id: Optional[int] = None
    created_at: datetime
    class Config:
        from_attributes = True

class AgentPackageBase(BaseModel):
    name: str
    expert_model_id: int
    project_id: int
    governance_version: Optional[str] = "0.1.0"

class AgentPackageCreate(AgentPackageBase):
    # The .empkg is compiled FOR this clearance: assets above it are excluded.
    clearance_level: Optional[str] = "INTERNAL" # PUBLIC | INTERNAL | RESTRICTED | EXECUTIVE

class AgentPackageResponse(AgentPackageBase):
    id: int
    quality_score: float
    asset_references: Optional[str] # JSON string of asset references and metadata
    created_at: datetime
    clearance_level: Optional[str] = None
    package_hash: Optional[str] = None
    manifest: Optional[dict] = None
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
    access_level: Optional[str] = "INTERNAL" # caller clearance: PUBLIC | INTERNAL | RESTRICTED | EXECUTIVE

class CitationModel(BaseModel):
    asset_id: int
    revision: Optional[int] = None # active approved revision number, if revision history exists
    name: str
    content: str
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    source_section: Optional[str] = None
    source_hash: Optional[str] = None
    asset_status: str
    # Provenance is reported honestly: None when not recorded, never fabricated.
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    confidence_score: float
    coverage_score: float
    verification_status: str
    citations: List[CitationModel]
    unsupported_claims: Optional[List[str]] = []
    contradicted_claims: Optional[List[str]] = []
    verifier: Optional[dict] = None

class AssetRelationshipResponse(BaseModel):
    id: int
    project_id: int
    expert_model_id: int
    source_asset_id: int
    target_asset_id: int
    relationship_type: str # CONFLICTS_WITH | SUPPORTS | RELATED
    classification: Optional[str] = None # DIRECT_CONTRADICTION | TEMPORAL_SUPERSESSION | SCOPE_CONFLICT | ACCESS_CONFLICT
    confidence: float
    status: str # DETECTED | CONFIRMED | DISMISSED
    detected_at: datetime
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    notes: Optional[str] = None
    verifier: Optional[dict] = None
    class Config:
        from_attributes = True

class ConflictScanResponse(BaseModel):
    expert_model_id: int
    scanned_assets: int
    compared_pairs: int
    dropped_pairs: int
    nli_available: bool
    conflicts_found: int
    supports_found: int
    relationships: List[AssetRelationshipResponse] = []
    semantic_conflict_score: Optional[float] = None
    semantic_conflict_summary: Optional[str] = None

class ConflictScoreBreakdownItem(BaseModel):
    status: str
    classification: str
    count: int
    penalty: float

class ConflictScoreResponse(BaseModel):
    expert_model_id: int
    semantic_conflict_score: float
    semantic_conflict_summary: str
    breakdown: List[ConflictScoreBreakdownItem] = []
    score_version: str

class ConflictReviewUpdate(BaseModel):
    status: str # CONFIRMED | DISMISSED
    reviewer: Optional[str] = "operator"
    notes: Optional[str] = None

class TrustComponent(BaseModel):
    key: str
    label: str
    score: Optional[float] = None
    weight: float
    measured: bool
    reason: str
    details: dict = {}

class TrustScoreResponse(BaseModel):
    expert_model_id: int
    trust_score: Optional[float] = None
    score_version: str
    summary: str
    components: List[TrustComponent] = []

class AssetRevisionCreate(BaseModel):
    content: str
    change_reason: Optional[str] = None
    actor: Optional[str] = "operator"

class RevisionReviewUpdate(BaseModel):
    action: str # APPROVE | REJECT
    reviewer: Optional[str] = "operator"
    notes: Optional[str] = None

class AssetRevisionResponse(BaseModel):
    id: int
    asset_id: int
    revision_number: int
    status: str # CANDIDATE | APPROVED | REJECTED | ARCHIVED
    content: str
    source_hash: Optional[str] = None
    content_hash: str
    created_by: Optional[str] = None
    created_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    supersedes_revision_id: Optional[int] = None
    superseded_by_revision_id: Optional[int] = None
    change_reason: Optional[str] = None
    class Config:
        from_attributes = True

class RevisionQueueItem(BaseModel):
    """A revision plus its comparison baseline for the review workbench."""
    revision: AssetRevisionResponse
    asset_id: int
    asset_name: str
    asset_type: str
    asset_access_level: Optional[str] = None
    # The revision this one supersedes (or the active revision as fallback) -
    # the left side of the side-by-side comparison.
    baseline_revision_number: Optional[int] = None
    baseline_content: Optional[str] = None
    baseline_content_hash: Optional[str] = None
    baseline_source_hash: Optional[str] = None

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

class ClaimVerdictResponse(BaseModel):
    """Immutable verification artifact (MVP 0.9.2) - no mutable status by
    design; human judgments are VERIFICATION_REVIEWED audit events."""
    id: int
    project_id: int
    expert_model_id: int
    evaluation_run_id: int
    question_result_id: int
    benchmark_question_id: int
    claim: str
    verdict: str # ENTAILED | CONTRADICTED | UNSUPPORTED
    confidence: Optional[float] = None
    supporting_asset_ids: List[int] = []
    contradicting_asset_ids: List[int] = []
    verifier: Optional[dict] = None
    evaluator_type: str
    evaluator_id: str
    created_at: datetime
    class Config:
        from_attributes = True

class VerificationReviewCreate(BaseModel):
    reviewer: Optional[str] = "operator"
    comment: Optional[str] = None

class EvaluationQuestionResultResponse(BaseModel):
    id: int
    evaluation_run_id: int
    benchmark_question_id: int
    question_text: str
    generated_answer: Optional[str]
    coverage_score: float
    confidence_score: float
    verification_status: Optional[str]
    passed: bool
    unsupported_claims: List[str]
    citations: List[CitationModel]
    claim_verdicts: List[ClaimVerdictResponse] = []
    class Config:
        from_attributes = True

class EvaluationRunCreate(BaseModel):
    project_id: int
    expert_model_id: int
    expert_model_version: Optional[str] = None

class EvaluationRunResponse(BaseModel):
    id: int
    project_id: int
    expert_model_id: int
    expert_model_version: Optional[str]
    asset_ids_snapshot: str
    asset_hashes_snapshot: str
    benchmark_question_ids_snapshot: str
    status: str
    average_coverage_score: float
    average_confidence_score: float
    pass_rate: float
    failed_question_ids_json: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    results: List[EvaluationQuestionResultResponse] = []
    class Config:
        from_attributes = True

