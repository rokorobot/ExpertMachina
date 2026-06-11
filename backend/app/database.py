import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "sqlite:///./expert_machina.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True)


class Principal(Base):
    """Identity Boundary v1.0 (docs/identity-boundary-v1.md): the MUTABLE
    registry of actors. Five kinds: HUMAN | DELEGATED | SYSTEM | SERVICE |
    AGENT. The constitutional symmetry: Principal changes; IdentityFact
    never changes - KnowledgeAsset/AssetRevision applied to identity.
    No delete - deactivate (D17 pattern): audit history references
    principals indefinitely. DELEGATED principals (policy:X, connector:Y)
    are auto-registered when their governed object is created and never
    authenticate; their authority is the causal chain."""
    __tablename__ = "principals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)  # stable slug: "alice", "policy:Low-risk docs", "system"
    display_name = Column(String, nullable=False)
    kind = Column(String, nullable=False)  # HUMAN | DELEGATED | SYSTEM | SERVICE | AGENT
    role = Column(String, nullable=True)  # identity.ROLES: ADMIN | GOVERNANCE_REVIEWER | KNOWLEDGE_OPERATOR | AGENT_CONSUMER | READ_ONLY; None for SYSTEM/DELEGATED
    clearance = Column(String, nullable=True)  # AGENT kind only: PUBLIC | INTERNAL | RESTRICTED | EXECUTIVE
    active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    credentials = relationship("Credential", back_populates="principal", foreign_keys="Credential.principal_id")


class Credential(Base):
    """Governed credential lineage (revoke, never delete). Stores HASHES
    only - hashes verify, they don't reveal (D19); plaintext tokens are
    shown once at creation and never persisted. Rotation revokes the old
    row and creates a new one, so 'which credential authenticated Alice
    six months ago' stays answerable forever via the fingerprint.
    Credential lineage is first-class: enterprise forensics interrogate
    credentials (which token? which generation? revoked when?) more often
    than principals. SESSION rows record which credential authenticated
    the login via issued_by_credential_id - lineage is complete."""
    __tablename__ = "credentials"
    id = Column(Integer, primary_key=True, index=True)
    principal_id = Column(Integer, ForeignKey("principals.id"), nullable=False)
    kind = Column(String, nullable=False)  # PASSWORD | API_TOKEN | SESSION
    secret_hash = Column(String, nullable=False)  # pbkdf2 (PASSWORD) / sha256 (API_TOKEN, SESSION)
    fingerprint = Column(String, nullable=False, unique=True, index=True)  # stable public identifier: cred_<id>:<hash-prefix>
    label = Column(String, nullable=True)
    issued_by_credential_id = Column(Integer, ForeignKey("credentials.id"), nullable=True)  # SESSION: the credential that authenticated the login
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    principal = relationship("Principal", back_populates="credentials", foreign_keys=[principal_id])


class IdentityFact(Base):
    """IMMUTABLE identity evidence - the ClaimVerdict pattern applied to
    actors (D3: observe, record - not negotiate). Answers exactly one
    question: WHO was authenticated at action time. Snapshots survive any
    later change to the principal: rename, role change, password rotation,
    deactivation - future user-table state is never required to explain
    past governed actions (D20 candidate).
    PURITY RULE (design review ruling): never add request-context columns
    (route, operation, parameters, write inventory) - that is a future
    RequestFact between this table and the written records. The Alice test
    asserts this column set structurally, so creep fails CI.
    on_behalf_of_fact_id carries identity delegation only (WHO authorized);
    the causal WHY lives in ActionContext (governed objects + D17
    provenance) and evolves independently."""
    __tablename__ = "identity_facts"
    id = Column(Integer, primary_key=True, index=True)
    principal_id = Column(Integer, ForeignKey("principals.id"), nullable=False)
    principal_name = Column(String, nullable=False)  # as at action time
    display_name = Column(String, nullable=False)  # as at action time
    principal_kind = Column(String, nullable=False)
    role_snapshot = Column(String, nullable=True)  # role held at that moment
    authentication_method = Column(String, nullable=False)  # PASSWORD | API_TOKEN | DELEGATED | INTERNAL
    credential_fingerprint = Column(String, nullable=True)  # NULL for SYSTEM/DELEGATED
    on_behalf_of_fact_id = Column(Integer, ForeignKey("identity_facts.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="NEW") # NEW, INGESTING, TRANSFORMING, REVIEW, PUBLISHED

class SourceConnector(Base):
    """Enterprise Source Connector (MVP 0.10.0). Read-only discovery over an
    existing repository. LOCAL_FOLDER only for now - cloud connectors wait
    for the credentials/identity layer. Connector output becomes ordinary
    ExpertMachina objects (Document -> CANDIDATE assets); there is no
    connector-specific review flow by design."""
    __tablename__ = "source_connectors"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String, nullable=False)
    type = Column(String, default="LOCAL_FOLDER") # LOCAL_FOLDER (cloud types reserved for v1.x)
    root_path = Column(String, nullable=False)
    include_extensions = Column(String, default=".txt,.md,.pdf,.docx") # comma-separated
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class IngestionJob(Base):
    """One 'Scan now' execution of a connector. Counters are live facts
    (updated per file so progress polling works); per-file outcomes live in
    SourceDocument rows. No silent skips - every discovered file gets a row."""
    __tablename__ = "ingestion_jobs"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    connector_id = Column(Integer, ForeignKey("source_connectors.id"))
    status = Column(String, default="PENDING") # PENDING | RUNNING | COMPLETED | FAILED
    files_discovered = Column(Integer, default=0)
    files_ingested = Column(Integer, default=0)
    files_duplicate = Column(Integer, default=0)
    files_changed = Column(Integer, default=0) # MVP 0.10.1: source changed -> candidate revisions
    files_failed = Column(Integer, default=0)
    error = Column(Text, nullable=True) # job-level failure / non-fatal extraction error
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class SourceDocument(Base):
    """Discovered-file inventory: provenance from the source URI through to
    the ordinary Document the file became (or why it didn't)."""
    __tablename__ = "source_documents"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    connector_id = Column(Integer, ForeignKey("source_connectors.id"))
    ingestion_job_id = Column(Integer, ForeignKey("ingestion_jobs.id"))
    source_uri = Column(String, nullable=False) # absolute path at the source
    file_hash = Column(String, nullable=True) # sha256 of file content
    size_bytes = Column(Integer, nullable=True)
    source_modified_at = Column(DateTime, nullable=True)
    status = Column(String, default="INGESTED") # INGESTED | DUPLICATE | CHANGED | FAILED
    error = Column(Text, nullable=True)
    details_json = Column(Text, nullable=True) # MVP 0.10.1: change summary (revisions created, assets added, ...)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def details(self):
        import json
        return json.loads(self.details_json) if self.details_json else None


class ApprovalPolicy(Base):
    """Policy-Based Auto Approval (MVP 0.10.2). A deterministic, versioned
    rule: newly extracted CANDIDATE assets whose type matches an enabled
    policy (optionally scoped to one connector) are approved at ingestion
    time by the actor 'policy:<name>'. Policies are governed facts - every
    definition change bumps version and writes an audit event, so an
    ASSET_AUTO_APPROVED event is always traceable to the exact rule text
    that fired. Applies to NEW candidate assets only; candidate revisions
    of approved assets always require a human."""
    __tablename__ = "approval_policies"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String, nullable=False)
    asset_types_json = Column(Text, nullable=False)  # JSON array of asset types this policy auto-approves
    connector_id = Column(Integer, ForeignKey("source_connectors.id"), nullable=True)  # NULL = any source, incl. manual upload
    enabled = Column(Boolean, default=True)
    version = Column(Integer, default=1)  # bumped on every definition change
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def asset_types(self):
        import json
        return json.loads(self.asset_types_json) if self.asset_types_json else []


class LLMFunctionConfig(Base):
    """LLM Provider Settings (MVP 0.12). Governed model-per-function
    configuration: WHICH model serves an LLM-using function. Stores model
    selection, never credentials - API keys stay env-based until the v1.x
    identity layer (D14). Empty table = prior behavior: resolution falls
    through to the OPENAI_MODEL env var, then the gpt-4o-mini default.
    Clearing a row's model resets the function; no delete endpoint needed.
    Changes are LLM_CONFIG_UPDATED audit events."""
    __tablename__ = "llm_function_configs"
    id = Column(Integer, primary_key=True, index=True)
    function = Column(String, nullable=False, unique=True)  # EXTRACTION | CLAIM_DECOMPOSITION | CLAIM_JUDGE | ANSWER_GENERATION
    provider = Column(String, default="OPENAI")  # only OPENAI for now (D11); adapter abstraction earned with a second provider
    model = Column(String, nullable=True)  # None = fall through to env/default
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=True)
    department = Column(String, nullable=True)
    owner = Column(String, nullable=True)
    version = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    status = Column(String, default="UPLOADED") # UPLOADED, PARSED, FAILED
    content_hash = Column(String, nullable=True) # sha256 of file content (MVP 0.10.0, dedup key)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    table_count = Column(Integer, default=0)
    docling_json = Column(Text, nullable=True) # docling structured data
    embedding_ref = Column(String, nullable=True) # Reference to Qdrant vector id

    document = relationship("Document", back_populates="chunks")

class KnowledgeAsset(Base):
    __tablename__ = "knowledge_assets"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    type = Column(String, nullable=False) # PROCEDURE, POLICY, ROLE, SYSTEM, WORKFLOW, PRODUCT, DEPARTMENT
    name = Column(String, nullable=False)
    owner = Column(String, nullable=True)
    condition = Column(String, nullable=True)
    source_citation = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    status = Column(String, default="CANDIDATE") # CANDIDATE, REVIEWED, APPROVED, ARCHIVED
    access_level = Column(String, default="INTERNAL") # PUBLIC, INTERNAL, RESTRICTED, EXECUTIVE
    
    # Advanced Provenance fields
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id"), nullable=True)
    source_page = Column(Integer, nullable=True)
    source_section = Column(String, nullable=True)
    source_hash = Column(String, nullable=True)
    extraction_method = Column(String, default="MOCK_RULE_BASED") # MOCK_RULE_BASED, LOCAL_RULE_BASED, LLM_ASSISTED, HUMAN_CREATED

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    reviews = relationship("AssetReview", back_populates="asset", cascade="all, delete-orphan")
    quality_scores = relationship("QualityScore", back_populates="asset", cascade="all, delete-orphan")
    revisions = relationship("AssetRevision", back_populates="asset", cascade="all, delete-orphan")

    # Revision projection helpers: the asset row always mirrors the active
    # approved revision; these expose revision state to API responses.
    @property
    def revision_count(self):
        return len(self.revisions)

    @property
    def active_revision_number(self):
        approved = [r.revision_number for r in self.revisions if r.status == "APPROVED"]
        return max(approved) if approved else None

    @property
    def has_pending_revision(self):
        return any(r.status == "CANDIDATE" for r in self.revisions)


class AssetRevision(Base):
    """Immutable content/version records (MVP 0.7 Sprint 4). The parent
    knowledge_assets row is the stable logical identity; approved content is
    never edited in place - edits create a new CANDIDATE revision here.
    A superseded revision is ARCHIVED with superseded_by_revision_id set."""
    __tablename__ = "asset_revisions"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("knowledge_assets.id"), nullable=False)
    revision_number = Column(Integer, nullable=False)
    status = Column(String, default="CANDIDATE") # CANDIDATE | APPROVED | REJECTED | ARCHIVED
    content = Column(Text, nullable=False)
    source_hash = Column(String, nullable=True) # chunk provenance hash at revision time
    content_hash = Column(String, nullable=False) # sha256 of this revision's content
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    identity_fact_id = Column(Integer, ForeignKey("identity_facts.id"), nullable=True)  # approver's fact; NULL = pre-boundary legacy (D12)
    supersedes_revision_id = Column(Integer, ForeignKey("asset_revisions.id"), nullable=True)
    superseded_by_revision_id = Column(Integer, ForeignKey("asset_revisions.id"), nullable=True)
    change_reason = Column(Text, nullable=True)

    asset = relationship("KnowledgeAsset", back_populates="revisions")

class AssetReview(Base):
    __tablename__ = "asset_reviews"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("knowledge_assets.id"))
    reviewer = Column(String, nullable=True)
    approver = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, default=datetime.datetime.utcnow)
    identity_fact_id = Column(Integer, ForeignKey("identity_facts.id"), nullable=True)  # NULL = pre-boundary legacy (D12)

    asset = relationship("KnowledgeAsset", back_populates="reviews")

class QualityScore(Base):
    __tablename__ = "quality_scores"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("knowledge_assets.id"))
    coverage_score = Column(Integer, default=0)
    freshness_score = Column(Integer, default=0)
    verification_score = Column(Integer, default=0)
    conflict_score = Column(Integer, default=0)
    overall_score = Column(Integer, default=0)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)

    asset = relationship("KnowledgeAsset", back_populates="quality_scores")

class ExpertModel(Base):
    __tablename__ = "expert_models"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    asset_count = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0)
    coverage_score = Column(Float, default=0.0)
    asset_ids_json = Column(Text, nullable=True) # JSON array of grouped asset IDs
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AgentPackage(Base):
    __tablename__ = "agent_packages"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String, nullable=False)
    expert_model_id = Column(Integer, ForeignKey("expert_models.id"))
    governance_version = Column(String, default="0.1.0")
    quality_score = Column(Float, default=0.0)
    asset_references = Column(Text, nullable=True) # JSON array of knowledge asset IDs included
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    # Agent Package Builder (MVP 0.9.4): the exported .empkg artifact.
    # Export crosses the governance boundary - the package is compiled FOR a
    # declared clearance level so a file handed to a PUBLIC agent can never
    # carry higher-tier assets past the gateway's checks.
    clearance_level = Column(String, default="INTERNAL") # PUBLIC | INTERNAL | RESTRICTED | EXECUTIVE
    file_path = Column(String, nullable=True)
    package_hash = Column(String, nullable=True) # sha256 of manifest.json, which hashes every file
    manifest_json = Column(Text, nullable=True)

    @property
    def manifest(self):
        import json
        return json.loads(self.manifest_json) if self.manifest_json else None

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    actor = Column(String, default="system")
    event_type = Column(String, nullable=False) # DOCUMENT_UPLOADED, DOCUMENT_PARSED, ASSET_GENERATED, ASSET_REVIEWED, ASSET_APPROVED, AGENT_PACKAGE_CREATED
    target_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    # Identity Boundary v1.0: NULL = pre-boundary legacy ("we did not
    # know"), never reconstructed later (D12). actor stays populated as
    # the readable display string; the fact is the source of truth.
    identity_fact_id = Column(Integer, ForeignKey("identity_facts.id"), nullable=True)

class AssetRelationship(Base):
    """Semantic relationships between approved assets, detected by the
    Knowledge Integrity Engine (MVP 0.7 Sprint 1). Conflicts carry a
    classification and survive operator review across rescans."""
    __tablename__ = "asset_relationships"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    expert_model_id = Column(Integer, ForeignKey("expert_models.id"))
    source_asset_id = Column(Integer, ForeignKey("knowledge_assets.id"), nullable=False)
    target_asset_id = Column(Integer, ForeignKey("knowledge_assets.id"), nullable=False)
    relationship_type = Column(String, nullable=False) # CONFLICTS_WITH | SUPPORTS | RELATED
    classification = Column(String, nullable=True) # DIRECT_CONTRADICTION | TEMPORAL_SUPERSESSION | SCOPE_CONFLICT | ACCESS_CONFLICT
    confidence = Column(Float, default=0.0)
    verifier_json = Column(Text, nullable=True) # verifier identity snapshot that produced the verdict
    status = Column(String, default="DETECTED") # DETECTED | CONFIRMED | DISMISSED
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    @property
    def verifier(self):
        import json
        return json.loads(self.verifier_json) if self.verifier_json else None

class BenchmarkQuestion(Base):
    __tablename__ = "benchmark_questions"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    question = Column(String, nullable=False)
    expected_claims_json = Column(Text, nullable=False) # JSON array of strings
    expected_answer_type = Column(String, nullable=False) # FACTUAL | PROCEDURAL | POLICY | REFUSAL
    required_citation_count = Column(Integer, default=0)
    tags = Column(String, nullable=True) # comma-separated tags
    severity = Column(String, nullable=False, default="MEDIUM") # LOW | MEDIUM | HIGH | CRITICAL
    min_required_coverage = Column(Float, default=0.95)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def expected_claims(self):
        import json
        return json.loads(self.expected_claims_json) if self.expected_claims_json else []

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    expert_model_id = Column(Integer, ForeignKey("expert_models.id"))
    expert_model_version = Column(String, nullable=True) # or package_id
    asset_ids_snapshot = Column(Text, nullable=False) # JSON array of IDs
    asset_hashes_snapshot = Column(Text, nullable=False) # JSON dict of ID -> Hash
    benchmark_question_ids_snapshot = Column(Text, nullable=False) # JSON array of IDs
    status = Column(String, default="PENDING") # PENDING, RUNNING, COMPLETED, FAILED
    average_coverage_score = Column(Float, default=0.0)
    average_confidence_score = Column(Float, default=0.0)
    pass_rate = Column(Float, default=0.0)
    failed_question_ids_json = Column(Text, nullable=True) # JSON array of question IDs that failed
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    results = relationship("EvaluationQuestionResult", back_populates="run", cascade="all, delete-orphan")

class EvaluationQuestionResult(Base):
    __tablename__ = "evaluation_question_results"
    id = Column(Integer, primary_key=True, index=True)
    evaluation_run_id = Column(Integer, ForeignKey("evaluation_runs.id"))
    benchmark_question_id = Column(Integer, ForeignKey("benchmark_questions.id"))
    question_text = Column(String, nullable=False)
    generated_answer = Column(Text, nullable=True)
    coverage_score = Column(Float, default=0.0)
    confidence_score = Column(Float, default=0.0)
    verification_status = Column(String, nullable=True)
    passed = Column(Boolean, default=False)
    unsupported_claims_json = Column(Text, nullable=True) # JSON array of strings
    citations_json = Column(Text, nullable=True) # JSON array of citations

    run = relationship("EvaluationRun", back_populates="results")
    claim_verdicts = relationship("ClaimVerdict", back_populates="question_result", cascade="all, delete-orphan")

    @property
    def unsupported_claims(self):
        import json
        return json.loads(self.unsupported_claims_json) if self.unsupported_claims_json else []

    @property
    def citations(self):
        import json
        return json.loads(self.citations_json) if self.citations_json else []

class ClaimVerdict(Base):
    """Immutable verification artifact (MVP 0.9.2): one row per claim judged
    during an evaluation run. Never updated and never reviewed in place -
    a human judgment about a verdict is a VERIFICATION_REVIEWED audit event,
    remediation happens on the asset or revision, and the next evaluation run
    produces fresh verdicts against the corrected knowledge. evaluator_type /
    evaluator_id are identity-ready for future HUMAN / LLM evaluators."""
    __tablename__ = "claim_verdicts"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    expert_model_id = Column(Integer, ForeignKey("expert_models.id"))
    evaluation_run_id = Column(Integer, ForeignKey("evaluation_runs.id"))
    question_result_id = Column(Integer, ForeignKey("evaluation_question_results.id"))
    benchmark_question_id = Column(Integer, ForeignKey("benchmark_questions.id"))
    claim = Column(Text, nullable=False)
    verdict = Column(String, nullable=False) # ENTAILED | CONTRADICTED | UNSUPPORTED
    confidence = Column(Float, nullable=True) # winning-verdict probability; None for legacy fallback verifiers
    supporting_asset_ids_json = Column(Text, nullable=True) # JSON array of asset IDs
    contradicting_asset_ids_json = Column(Text, nullable=True) # JSON array of asset IDs
    verifier_json = Column(Text, nullable=True) # verifier identity snapshot incl. weight fingerprint
    evaluator_type = Column(String, default="AUTOMATED") # AUTOMATED | HUMAN | LLM
    evaluator_id = Column(String, default="verification_engine")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    question_result = relationship("EvaluationQuestionResult", back_populates="claim_verdicts")

    @property
    def supporting_asset_ids(self):
        import json
        return json.loads(self.supporting_asset_ids_json) if self.supporting_asset_ids_json else []

    @property
    def contradicting_asset_ids(self):
        import json
        return json.loads(self.contradicting_asset_ids_json) if self.contradicting_asset_ids_json else []

    @property
    def verifier(self):
        import json
        return json.loads(self.verifier_json) if self.verifier_json else None

def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_columns()


def _ensure_columns():
    """Additive SQLite migrations: create_all never adds columns to existing
    tables, so columns introduced after a table shipped are ALTERed in here."""
    from sqlalchemy import text
    additions = {
        "agent_packages": {
            "clearance_level": "TEXT DEFAULT 'INTERNAL'",
            "file_path": "TEXT",
            "package_hash": "TEXT",
            "manifest_json": "TEXT",
        },
        "documents": {
            "content_hash": "TEXT",
        },
        "ingestion_jobs": {
            "files_changed": "INTEGER DEFAULT 0",
        },
        "source_documents": {
            "details_json": "TEXT",
        },
        # Identity Boundary v1.0: nullable fact references on the landing
        # pads. NULL on pre-boundary rows means "we did not know" - facts
        # are never retroactively fabricated (D12).
        "audit_events": {
            "identity_fact_id": "INTEGER",
        },
        "asset_reviews": {
            "identity_fact_id": "INTEGER",
        },
        "asset_revisions": {
            "identity_fact_id": "INTEGER",
        },
    }
    with engine.connect() as conn:
        for table, columns in additions.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if not existing:
                continue  # table not created yet; create_all handles it fully
            for column, ddl in columns.items():
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
        conn.commit()
