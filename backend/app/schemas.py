from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

# Access tiers (mirrors identity.ACCESS_TIERS / mcp_gateway.VALID_CLEARANCES;
# kept literal here so the schema layer stays import-light). Audit QW-6
# (docs/audit-2026-07-07.md, L-SEC-4): an unknown access_level used to fall
# through to INTERNAL rank downstream - a mistyped "RESTRICTED" silently
# DOWNGRADED the asset. Classification must fail closed: reject at the
# boundary, never guess.
ACCESS_TIERS = ("PUBLIC", "INTERNAL", "RESTRICTED", "EXECUTIVE")


def _validate_access_tier(v):
    if v is None:
        return v
    tier = str(v).strip().upper()
    if tier not in ACCESS_TIERS:
        raise ValueError(
            f"Unknown access_level {v!r}: must be one of {', '.join(ACCESS_TIERS)}. "
            "Classification fails closed - unknown tiers are rejected, never defaulted.")
    return tier

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
    access_level: Optional[str] = "INTERNAL" # one of ACCESS_TIERS; unknown values rejected (QW-6)
    extraction_method: Optional[str] = "MOCK_RULE_BASED"

    _access_tier_guard = field_validator("access_level")(_validate_access_tier)

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
    access_level: Optional[str] = None # one of ACCESS_TIERS; unknown values rejected (QW-6)
    # v1.2.1 WS1 (D27): human domain correction through the normal update
    # surface - a governed act (ASSET_DOMAIN_CORRECTED), never an edit.
    domain: Optional[str] = None

    _access_tier_guard = field_validator("access_level")(_validate_access_tier)

class KnowledgeAssetResponse(KnowledgeAssetBase):
    id: int
    project_id: int
    status: str
    domain: Optional[str] = None  # v1.2.1 WS1 (D27): governed domain path
    # v1.4.0 WS2 (D30): PRIMARY | DERIVED - read-only exposure; the class
    # is channel-decided and never caller-suppliable (Guard 5 sweeps any
    # write-shaped schema carrying it).
    source_class: str = "PRIMARY"
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
    # v1.2.0 (D25): BINDING a credential to a connector is a custody act
    # (credentials:manage, checked in-route) - by reference, never by value.
    external_credential_id: Optional[int] = None
    # v1.4.0 WS1 (D29/D30): the channel declaration. PROPOSAL marks the
    # agent-finding return path; its candidates are constitutionally
    # outside every policy tier and become DERIVED on human acceptance.
    lane: Optional[str] = "PRIMARY"

class SourceConnectorResponse(BaseModel):
    id: int
    project_id: int
    name: str
    type: str
    root_path: str
    include_extensions: Optional[str] = None
    external_credential_id: Optional[int] = None  # v1.2.0 (D25)
    lane: str  # v1.4.0 (D29/D30): PRIMARY | PROPOSAL
    created_at: datetime
    class Config:
        from_attributes = True

# v1.2.0 WS1 (D25): outbound credential custody. The response model is the
# structural no-leak boundary: it HAS no field for secret material -
# ciphertext, wrapped keys, and master-key material cannot serialize
# through it. There is no reveal schema and never will be one (the
# operator supplied the secret; reveal is "never", not "once").
class ExternalCredentialCreate(BaseModel):
    name: str
    purpose: str  # custody.CREDENTIAL_PURPOSES: CONNECTOR | PROVIDER
    secret: str   # accepted once, encrypted immediately, never returned
    granted_scopes: Optional[List[str]] = None  # custody evidence (D25)
    coordinates: Optional[dict] = None  # NON-secret identifiers (tenant/client ids)

class ExternalCredentialRotate(BaseModel):
    secret: str   # the ONLY thing rotation re-enters
    granted_scopes: Optional[List[str]] = None  # None = inherit from the old generation
    coordinates: Optional[dict] = None

class ExternalCredentialRevoke(BaseModel):
    reason: Optional[str] = None

class ExternalCredentialResponse(BaseModel):
    id: int
    name: str
    purpose: str
    fingerprint: str
    status: str
    granted_scopes: List[str] = []
    coordinates: dict = {}
    owner_principal_id: int
    key_id: str  # master-key GENERATION identifier - reveals nothing
    replaces_credential_id: Optional[int] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class ExternalCredentialDetailResponse(ExternalCredentialResponse):
    # Custody history: a computed projection of EXTERNAL_CREDENTIAL_* /
    # custody audit events (D24 posture - never a persisted view).
    custody_events: List[dict] = []

class MasterKeyRotationResponse(BaseModel):
    old_key_id: str
    new_key_id: str
    credentials_rewrapped: int

class LLMFunctionSettingUpdate(BaseModel):
    model: Optional[str] = None  # None/empty clears the row -> env/default resolution
    provider: Optional[str] = None  # v1.1: OPENAI | ANTHROPIC (validated against llm.ADAPTERS); None keeps current
    # v1.0: no actor field - the identity boundary decides the actor.

class LLMFunctionSettingResponse(BaseModel):
    function: str
    description: str
    provider: str
    configured_model: Optional[str] = None  # what the DB row says (None = unset)
    effective_model: str                    # what resolution actually yields
    source: str                             # CONFIG | ENV | DEFAULT

class PackageModelSelectionUpdate(BaseModel):
    # v1.1 WS3: callers propose a selection; the boundary validates it
    # against COMPLETED PACKAGE evaluation runs for this exact package_hash.
    provider: str
    model: str
    supporting_evaluation_run_ids: List[int]
    rationale: str

class PackageModelSelectionResponse(BaseModel):
    id: int
    agent_package_id: int
    package_version: str
    package_hash: str
    selected_provider: str
    selected_model_name: str
    supporting_evaluation_run_ids: List[int]
    rationale: str
    selected_by_principal_id: int
    selected_at: datetime
    class Config:
        from_attributes = True

class ExpertAgentBindingCreate(BaseModel):
    # v1.1 WS4: the binding copies the model from the package's CURRENT
    # selection - callers never choose it. The optional expected_* fields
    # are a confirmation proposal: if supplied and they differ from the
    # current selection, creation is refused (selected model mismatch).
    agent_principal_id: int
    expected_provider: Optional[str] = None
    expected_model: Optional[str] = None

class ExpertAgentBindingResponse(BaseModel):
    id: int
    agent_package_id: int
    package_version: str
    package_hash: str
    selected_provider: str
    selected_model_name: str
    agent_principal_id: int
    principal_clearance_at_issue: str
    selection_evidence: Optional[dict] = None
    identity_fact_id: int
    created_at: datetime
    class Config:
        from_attributes = True

class ApprovalPolicyCreate(BaseModel):
    name: str
    asset_types: List[str]  # subset of the allowed KnowledgeAsset types
    connector_id: Optional[int] = None  # None = applies to any source, incl. manual upload
    # v1.2.1 WS2 (D26 Tier-0): deterministic source-authority conditions -
    # [{"key": "list_item_fields.ApprovalStatus", "equals": "Approved"}].
    # None/empty = the pre-Tier-0 policy, unchanged.
    source_conditions: Optional[List[dict]] = None
    # v1.2.1 WS3 (D26 Tier-2): engine-verified conditions -
    # {"contradiction_check": "CLEAN_REQUIRED"}. None/empty = not Tier-2.
    engine_conditions: Optional[dict] = None
    # v1.2.1 WS3 (D26/D27): optional domain-prefix coverage narrowing.
    domains: Optional[List[str]] = None
    # v1.0: no created_by field - the identity boundary decides the actor.

class ApprovalPolicyUpdate(BaseModel):
    name: Optional[str] = None
    asset_types: Optional[List[str]] = None
    connector_id: Optional[int] = None
    enabled: Optional[bool] = None
    source_conditions: Optional[List[dict]] = None  # a definition change (D17)
    engine_conditions: Optional[dict] = None        # a definition change (D17)
    domains: Optional[List[str]] = None             # a definition change (D17)

class ApprovalPolicyResponse(BaseModel):
    id: int
    project_id: int
    name: str
    asset_types: List[str]
    connector_id: Optional[int] = None
    enabled: bool
    version: int
    source_conditions: Optional[List[dict]] = None  # v1.2.1 WS2 (D26 Tier-0)
    engine_conditions: Optional[dict] = None        # v1.2.1 WS3 (D26 Tier-2)
    domains: Optional[List[str]] = None             # v1.2.1 WS3 (D26/D27)
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# Classification policies (v1.2.1 WS1, D27): the ApprovalPolicy governed
# shape mirrored for the other outcome species - assigning a domain,
# never granting APPROVED. Rules validated in app.classification.
class ClassificationPolicyCreate(BaseModel):
    name: str
    rules: List[dict]  # [{"domain": path, "match": {uri_prefix?, metadata?}}]
    connector_id: Optional[int] = None  # None = applies to any source

class ClassificationPolicyUpdate(BaseModel):
    name: Optional[str] = None
    rules: Optional[List[dict]] = None
    connector_id: Optional[int] = None
    enabled: Optional[bool] = None

class ClassificationPolicyResponse(BaseModel):
    id: int
    project_id: int
    name: str
    rules: List[dict]
    connector_id: Optional[int] = None
    enabled: bool
    version: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class TaxonomyReorganizeRequest(BaseModel):
    # [{"kind": "rename", "from_domain": X, "to_domain": Y} |
    #  {"kind": "reclassify", "domain": X}]
    operations: List[dict]
    reason: str

class ProjectionRenderRequest(BaseModel):
    # v1.3 WS1 (D28): a file render is a declared, parameterized act.
    # status_inclusion defaults to APPROVED-only (scoping ruling 4);
    # whatever is included is recorded in the manifest and the event.
    renderer: str = "projection"
    clearance: str = "INTERNAL"
    status_inclusion: Optional[List[str]] = None
    domain_prefix: Optional[str] = None

class IngestionJobResponse(BaseModel):
    id: int
    project_id: int
    connector_id: int
    status: str # PENDING | RUNNING | COMPLETED | FAILED
    files_discovered: int
    files_ingested: int
    files_duplicate: int
    files_changed: int = 0
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
    status: str # INGESTED | DUPLICATE | CHANGED | FAILED
    error: Optional[str] = None
    details: Optional[dict] = None # change summary for CHANGED rows
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
    # A caller may NARROW its query to a lower tier, never widen it: the
    # effective clearance is decided by the boundary from the authenticated
    # principal (identity.effective_query_clearance, H-SEC-1 fix 2026-07-07).
    # Unknown tiers are rejected at validation (QW-6), never silently ignored.
    access_level: Optional[str] = None # optional self-imposed ceiling: PUBLIC | INTERNAL | RESTRICTED | EXECUTIVE

    _access_tier_guard = field_validator("access_level")(_validate_access_tier)

class CitationModel(BaseModel):
    asset_id: int
    revision: Optional[int] = None # active approved revision number, if revision history exists
    name: str
    content: str
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    source_section: Optional[str] = None
    source_hash: Optional[str] = None
    # LIVE-channel citations record the asset's status at answer time.
    # PACKAGE-channel citations cite frozen package contents (approved by
    # construction at compile, D9) and carry no live status - reported as
    # None, never fabricated (D12). Required-ness here made the evaluations
    # list 500 on any project with PACKAGE runs (found at v1.1.x WS1).
    asset_status: Optional[str] = None
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
    # v1.4.0 WS2 (D30): source-class context, computed at read time by
    # conflict_engine.class_annotations - never stored on the relationship.
    # PRIMARY×DERIVED conflicts declare the asymmetry; the DERIVED side is
    # the presumptive review target ("primary prevails unless a human
    # rules otherwise"). Nothing auto-resolves; the gate is class-blind.
    source_asset_source_class: Optional[str] = None
    target_asset_source_class: Optional[str] = None
    class_asymmetry: Optional[str] = None  # PRIMARY_OVER_DERIVED when declared
    presumptive_review_target_asset_id: Optional[int] = None
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
    notes: Optional[str] = None
    # v1.0: no reviewer field - the identity boundary decides the actor.

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
    # v1.0: no actor field - the identity boundary decides the actor.

class RevisionReviewUpdate(BaseModel):
    action: str # APPROVE | REJECT
    notes: Optional[str] = None
    # v1.0: no reviewer field - the identity boundary decides the actor.

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
    comment: Optional[str] = None
    # v1.0: no reviewer field - the identity boundary decides the actor.

# Identity Boundary v1.0 (docs/identity-boundary-v1.md)
class LoginRequest(BaseModel):
    name: str
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class AuthIdentityResponse(BaseModel):
    name: str
    display_name: str
    role: Optional[str] = None
    kind: str
    must_change_password: bool = False

class LoginResponse(AuthIdentityResponse):
    token: str

# Identity administration (WS2b): AGENT/SERVICE principals + API tokens.
class PrincipalCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    kind: str  # HUMAN | AGENT | SERVICE (SYSTEM/DELEGATED are platform-managed)
    role: Optional[str] = None  # HUMAN/SERVICE; AGENT is always AGENT_CONSUMER
    clearance: Optional[str] = None  # AGENT only: PUBLIC | INTERNAL | RESTRICTED | EXECUTIVE

class PrincipalUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    clearance: Optional[str] = None  # AGENT only
    active: Optional[bool] = None

class PrincipalResponse(BaseModel):
    id: int
    name: str
    display_name: str
    kind: str
    role: Optional[str] = None
    clearance: Optional[str] = None
    active: bool
    created_by: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class PrincipalCreatedResponse(PrincipalResponse):
    # HUMAN creation returns a generated one-time password - shown exactly
    # once (the bootstrap pattern); must_change_password forces rotation.
    one_time_password: Optional[str] = None

class TokenIssueRequest(BaseModel):
    principal_name: str
    label: Optional[str] = None
    expires_days: Optional[int] = None  # None = no expiry (revocation is the control)

class TokenIssuedResponse(BaseModel):
    token: str  # plaintext - exists exactly here, exactly once; only the hash is stored
    fingerprint: str
    principal_name: str
    label: Optional[str] = None
    expires_at: Optional[datetime] = None

class TokenResponse(BaseModel):
    fingerprint: str
    principal_name: str
    principal_kind: str
    label: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

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
    # v1.1 WS2: PACKAGE runs name the artifact under test; the consumer
    # model is resolved through D19 config, never caller-supplied.
    run_type: str = "LIVE"  # LIVE | PACKAGE
    agent_package_id: Optional[int] = None  # required iff run_type=PACKAGE

class EvaluationRunResponse(BaseModel):
    id: int
    project_id: int
    expert_model_id: int
    expert_model_version: Optional[str]
    run_type: str = "LIVE"
    package_version: Optional[str] = None
    package_hash: Optional[str] = None
    consumer_model_provider: Optional[str] = None
    consumer_model_name: Optional[str] = None
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



class StewardshipDecisionCreate(BaseModel):
    """A human stewardship decision on a computed exception (v2.0, D32).
    The exception_key is the Governance Inbox item id (inbox-item-v1); the
    server confirms it names a currently-present exception before recording
    the append-only decision. Kind-specific fields are validated by
    app.stewardship against the ratified seven-kind vocabulary."""
    exception_key: str
    kind: str
    reason: Optional[str] = None
    escalated_to: Optional[str] = None
    owner_label: Optional[str] = None
    owner_principal_id: Optional[int] = None
    due_date: Optional[str] = None
    clears_kind: Optional[str] = None
