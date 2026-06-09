import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float
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

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    actor = Column(String, default="system")
    event_type = Column(String, nullable=False) # DOCUMENT_UPLOADED, DOCUMENT_PARSED, ASSET_GENERATED, ASSET_REVIEWED, ASSET_APPROVED, AGENT_PACKAGE_CREATED
    target_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)

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

def init_db():
    Base.metadata.create_all(bind=engine)
