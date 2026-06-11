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

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="NEW") # NEW, INGESTING, TRANSFORMING, REVIEW, PUBLISHED

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
        }
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
