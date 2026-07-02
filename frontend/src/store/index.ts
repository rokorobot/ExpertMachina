import { create } from 'zustand';

export interface Project {
  id: number;
  name: string;
  description: string;
  customer_id: number;
  status: string;
}

export interface Document {
  id: number;
  project_id: number;
  filename: string;
  file_type: string;
  department: string;
  owner: string;
  version: string;
  file_path: string;
  status: string;
  created_at: string;
  modified_at: string;
}

export interface QualityScore {
  id: number;
  asset_id: number;
  coverage_score: number;
  freshness_score: number;
  verification_score: number;
  conflict_score: number;
  overall_score: number;
  recorded_at: string;
}

export interface AssetReview {
  id: number;
  asset_id: number;
  reviewer: string;
  approver: string;
  notes: string;
  reviewed_at: string;
}

export interface KnowledgeAsset {
  id: number;
  project_id: number;
  type: string;
  name: string;
  owner: string;
  condition: string;
  source_citation: string;
  content: string;
  status: string;
  access_level: string;
  document_id: number;
  chunk_id: number;
  source_page: number;
  source_section: string;
  source_hash: string;
  extraction_method: string;
  created_at: string;
  domain: string | null; // v1.2.1 (D27): governed hierarchical domain path
  source_class: string; // v1.4.0 (D30): PRIMARY | DERIVED — channel-decided, read-only
  quality_scores: QualityScore[];
  reviews: AssetReview[];
  revision_count: number;
  active_revision_number: number | null;
  has_pending_revision: boolean;
}

export interface ExpertModel {
  id: number;
  project_id: number;
  name: string;
  description: string;
  asset_count: number;
  quality_score: number;
  coverage_score: number;
  created_at: string;
}

export interface AgentPackageManifest {
  package_format: string;
  package_name: string;
  expert_model_id: number;
  expert_model: string;
  governance_version: string;
  clearance_level: string;
  compiled_at: string;
  trust_score: number | null;
  asset_count: number;
  excluded_assets_above_clearance: number;
  knowledge_hash: string;
  files: Record<string, string>;
}

export interface AgentPackage {
  id: number;
  project_id: number;
  name: string;
  expert_model_id: number;
  governance_version: string;
  quality_score: number;
  asset_references: string;
  created_at: string;
  clearance_level: string | null;
  package_hash: string | null;
  manifest: AgentPackageManifest | null;
}

// v1.1.x Consumption Operations Workbench (D24): everything below is a
// PROJECTION of governed facts - the workbench reads selections,
// comparisons, runs, and audit events; its only write is the existing
// model-selection PUT.
export interface PackageModelSelection {
  id: number;
  agent_package_id: number;
  package_version: string;
  package_hash: string;
  selected_provider: string;
  selected_model_name: string;
  supporting_evaluation_run_ids: number[];
  rationale: string;
  selected_by_principal_id: number;
  selected_at: string;
}

export interface ModelComparisonRun {
  run_id: number;
  completed_at: string | null;
  pass_rate: number;
  average_coverage_score: number;
  claims_total: number | null;
  verdict_counts: Record<string, number> | null;
}

export interface ModelComparisonEntry {
  provider: string;
  model: string;
  runs: ModelComparisonRun[];
  latest: ModelComparisonRun;
}

export interface ModelComparison {
  agent_package_id: number;
  package_name: string;
  package_version: string;
  package_hash: string;
  models: ModelComparisonEntry[];
  note: string;
}

// v1.1.x WS2: the Computed Consumption Inbox. Every item is derived live
// by the backend from governed facts - nothing here is ever persisted,
// and there is deliberately no dismiss/resolve action to call.
export interface ConsumptionInboxItem {
  id: string;
  condition: string;
  severity: string; // HIGH | MEDIUM | LOW (one shared backend function)
  title: string;
  reason: string;
  project_id: number;
  package_id: number;
  package_name: string;
  package_version: string;
  binding_id: number | null;
  selection_id: number | null;
  principal_id: number | null;
  principal_name: string | null;
  missing: string[]; // declared unresolvable hops (D12)
  deep_link: string;
}

export interface ConsumptionInbox {
  inbox_version: string;
  project_id: number | null;
  generated_at: string;
  summary: {
    high: number;
    medium: number;
    low: number;
    total_packages: number;
    items_with_declared_missing_hops: number;
  };
  items: ConsumptionInboxItem[];
}

// v1.1.x WS3: the Binding Explorer. A binding is an append-only snapshot
// (D22 - a binding, never a runtime); its lineage is composed server-side
// because the chain is a product claim. Every section carries a `missing`
// list: hops that could not be resolved, declared - never dropped (D12).
export interface ExpertAgentBinding {
  id: number;
  agent_package_id: number;
  package_version: string;
  package_hash: string;
  selected_provider: string;
  selected_model_name: string;
  agent_principal_id: number;
  principal_clearance_at_issue: string;
  selection_evidence: Record<string, unknown> | null;
  identity_fact_id: number;
  created_at: string;
}

export interface LineageRun {
  run_id: number;
  run_type: string;
  status: string;
  consumer_model_provider: string | null;
  consumer_model_name: string | null;
  package_hash: string | null;
  pass_rate: number;
  average_coverage_score: number;
  completed_at: string | null;
  evaluates_bound_artifact: boolean;
}

export interface BindingLineage {
  lineage_version: string;
  generated_at: string;
  binding: {
    id: number; agent_package_id: number; package_version: string;
    package_hash: string; selected_provider: string; selected_model_name: string;
    agent_principal_id: number; principal_clearance_at_issue: string; created_at: string;
  };
  issued_by: {
    identity_fact_id?: number; principal_name?: string; display_name?: string;
    principal_kind?: string; role_at_issue?: string; authentication_method?: string;
    issued_at?: string; missing: string[];
  };
  package: {
    package_id?: number; project_id?: number; name?: string; version?: string;
    hash?: string; clearance_level?: string; compiled_at?: string;
    trust_score_at_compile?: number | null; asset_count_at_compile?: number;
    expert_model?: string; missing: string[];
  };
  family_status: {
    current_package_id?: number; current_version?: string; current_hash?: string;
    artifact_count?: number; superseded?: boolean; missing: string[];
  };
  model: {
    provider: string; model: string;
    current_selection: { provider: string; model: string; selected_at: string | null; rationale: string } | null;
    matches_current_selection: boolean | null; missing: string[];
  };
  selection_evidence: {
    selection_id?: number; rationale?: string; selected_at?: string | null;
    supporting_evaluation_run_ids?: number[]; selected_by?: string; missing: string[];
  };
  evaluation_runs: { runs: LineageRun[]; missing: string[] };
  assets: {
    assets: { asset_id: number; name: string; type: string; source_document: string | null;
              source_page: number | null; source_hash: string | null; live_status: string | null }[];
    missing: string[];
  };
  source_documents: {
    documents: { document_id: number; filename: string; status: string;
                 content_hash: string | null; created_at: string | null }[];
    missing: string[];
  };
  principal: {
    principal_id?: number; name?: string; display_name?: string; kind?: string;
    role?: string | null; clearance_now?: string; active?: boolean;
    created_at?: string; missing: string[];
  };
  credentials: {
    active_count: number; revoked_count: number; kinds: string[];
    last_used_at: string | null; missing: string[];
  };
  audit: {
    events: { id: number; timestamp: string; actor: string; event_type: string;
              identity_fact_id: number | null }[];
    missing: string[];
  };
  warnings: ConsumptionInboxItem[];
  declared_missing_total: number;
}

export interface AssetRelationship {
  id: number;
  project_id: number;
  expert_model_id: number;
  source_asset_id: number;
  target_asset_id: number;
  relationship_type: string; // CONFLICTS_WITH | SUPPORTS | RELATED
  classification: string | null; // DIRECT_CONTRADICTION | TEMPORAL_SUPERSESSION | SCOPE_CONFLICT | ACCESS_CONFLICT
  confidence: number;
  status: string; // DETECTED | CONFIRMED | DISMISSED
  detected_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  notes: string | null;
  verifier: Record<string, unknown> | null;
  // v1.4.0 (D30): computed source-class context — never stored on the
  // relationship. Primary prevails: the DERIVED side is the presumptive
  // review target; nothing auto-resolves; the compile gate is class-blind.
  source_asset_source_class: string | null;
  target_asset_source_class: string | null;
  class_asymmetry: string | null; // PRIMARY_OVER_DERIVED when declared
  presumptive_review_target_asset_id: number | null;
}

export interface ConflictScanSummary {
  expert_model_id: number;
  scanned_assets: number;
  compared_pairs: number;
  dropped_pairs: number;
  nli_available: boolean;
  conflicts_found: number;
  supports_found: number;
  semantic_conflict_score: number | null;
  semantic_conflict_summary: string | null;
}

export interface ConflictScore {
  expert_model_id: number;
  semantic_conflict_score: number;
  semantic_conflict_summary: string;
  breakdown: { status: string; classification: string; count: number; penalty: number }[];
  score_version: string;
}

export interface AssetRevision {
  id: number;
  asset_id: number;
  revision_number: number;
  status: string; // CANDIDATE | APPROVED | REJECTED | ARCHIVED
  content: string;
  source_hash: string | null;
  content_hash: string;
  created_by: string | null;
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
  supersedes_revision_id: number | null;
  superseded_by_revision_id: number | null;
  change_reason: string | null;
}

export interface RevisionQueueItem {
  revision: AssetRevision;
  asset_id: number;
  asset_name: string;
  asset_type: string;
  asset_access_level: string | null;
  baseline_revision_number: number | null;
  baseline_content: string | null;
  baseline_content_hash: string | null;
  baseline_source_hash: string | null;
}

export interface BenchmarkQuestion {
  id: number;
  project_id: number;
  question: string;
  expected_claims: string[];
  expected_answer_type: string; // FACTUAL | PROCEDURAL | POLICY | REFUSAL
  required_citation_count: number;
  tags: string | null;
  severity: string; // LOW | MEDIUM | HIGH | CRITICAL
  min_required_coverage: number;
  created_at: string;
}

export interface ClaimVerdict {
  id: number;
  project_id: number;
  expert_model_id: number;
  evaluation_run_id: number;
  question_result_id: number;
  benchmark_question_id: number;
  claim: string;
  verdict: string; // ENTAILED | CONTRADICTED | UNSUPPORTED
  confidence: number | null;
  supporting_asset_ids: number[];
  contradicting_asset_ids: number[];
  verifier: Record<string, unknown> | null;
  evaluator_type: string; // AUTOMATED | HUMAN | LLM
  evaluator_id: string;
  created_at: string;
}

export interface EvaluationQuestionResult {
  id: number;
  evaluation_run_id: number;
  benchmark_question_id: number;
  question_text: string;
  generated_answer: string | null;
  coverage_score: number;
  confidence_score: number;
  verification_status: string | null;
  passed: boolean;
  unsupported_claims: string[];
  citations: { asset_id: number; name: string; content: string }[];
  claim_verdicts: ClaimVerdict[];
}

export interface EvaluationRun {
  id: number;
  project_id: number;
  expert_model_id: number;
  expert_model_version: string | null;
  // v1.1 WS2: the channel is a property of the run, never a sibling
  // concept. PACKAGE runs carry binding coordinates; LIVE runs carry none.
  run_type: string; // LIVE | PACKAGE
  package_version: string | null;
  package_hash: string | null;
  consumer_model_provider: string | null;
  consumer_model_name: string | null;
  status: string; // PENDING | RUNNING | COMPLETED | FAILED
  average_coverage_score: number;
  average_confidence_score: number;
  pass_rate: number;
  started_at: string;
  completed_at: string | null;
  results: EvaluationQuestionResult[];
}

export interface SourceConnector {
  id: number;
  project_id: number;
  name: string;
  type: string; // LOCAL_FOLDER | SHAREPOINT (v1.2.0)
  root_path: string;
  include_extensions: string | null;
  external_credential_id: number | null; // v1.2.0 (D25): by reference, never by value
  lane: string; // v1.4.0 (D29/D30): PRIMARY | PROPOSAL — the channel declaration
  created_at: string;
}

// v1.4.1 (the D8 amendment): the Operations view — a pure computed
// projection of Operations Realm activity. Nothing here is stored; the
// provenance verdicts are recomputed by the backend at every read.
export interface OperationsProvenance {
  provenance_claimed: boolean;
  provenance_verified: boolean;
  reasons: string[];
  claimed: Record<string, string>;
  unrecognized_keys: string[];
  verified: {
    binding_id: number;
    agent_principal: string;
    agent_principal_id: number;
    agent_package_id: number | null;
    package_hash: string;
    package_version: string | null;
    selected_provider: string | null;
    selected_model_name: string | null;
    binding_identity_fact_id: number;
  } | null;
  cited_assets: {
    claimed: number[];
    found: number[];
    missing: number[];
    malformed: string[];
    derived_evidence: number[];
  } | null;
}

export interface OperationsPipelineEntry {
  document_id: number;
  filename: string;
  connector_id: number;
  ingested_at: string | null;
  agent_principal: string | null;
  provenance: OperationsProvenance;
  candidates: { asset_id: number; name: string; type: string; status: string; source_class: string }[];
  held_count: number;
  accepted_count: number;
}

export interface OperationsAgent {
  principal_id: number;
  name: string;
  display_name: string;
  active: boolean;
  clearance: string | null;
  bindings: number;
  latest_binding: {
    binding_id: number;
    package_version: string | null;
    package_hash: string;
    selected_provider: string | null;
    selected_model_name: string | null;
    created_at: string | null;
  } | null;
  proposals: { proposal_documents: number; held_candidates: number; accepted_derived: number; unverified_documents: number };
}

export interface OperationsView {
  project_id: number;
  agents: OperationsAgent[];
  pipeline: OperationsPipelineEntry[];
  lanes: {
    connector_id: number;
    name: string;
    root_path: string;
    include_extensions: string | null;
    created_at: string | null;
    last_scan: { job_id: number; status: string; started_at: string | null; completed_at: string | null; files_discovered: number; files_ingested: number; files_changed: number } | null;
  }[];
  unattributed_proposals: { proposal_documents: number; held_candidates: number; accepted_derived: number; unverified_documents: number } | null;
  summary: { agents: number; active_agents: number; lanes: number; proposal_documents: number; held_candidates: number; accepted_derived: number; unverified_documents: number };
}

// v1.2.0 (D25): outbound credential METADATA. There is deliberately no
// field for secret material anywhere in these shapes - the backend never
// returns it and the UI never asks for it back. Reveal is "never".
export interface ExternalCredential {
  id: number;
  name: string;
  purpose: string; // CONNECTOR | PROVIDER
  fingerprint: string;
  status: string; // ACTIVE | REVOKED
  granted_scopes: string[];
  coordinates: Record<string, string>;
  owner_principal_id: number;
  key_id: string; // master-key generation identifier - reveals nothing
  replaces_credential_id: number | null;
  created_at: string;
  revoked_at: string | null;
}

export interface CustodyEvent {
  event_type: string;
  timestamp: string;
  actor: string;
  identity_fact_id: number | null;
  details: Record<string, unknown> | null;
}

export interface ExternalCredentialDetail extends ExternalCredential {
  custody_events: CustodyEvent[]; // projected from the audit ledger (D24)
}

export interface LLMFunctionSetting {
  function: string;
  description: string;
  provider: string;
  configured_model: string | null; // DB row (null = unset)
  effective_model: string;         // what resolution yields
  source: string;                  // CONFIG | ENV | DEFAULT
}

// v1.2.1 (D26): a Tier-0 source-authority condition on an approval policy.
export interface SourceCondition {
  key: string;              // dotted path into the verbatim source metadata
  equals?: string;          // exactly one of equals / in
  in?: string[];
}

export interface ApprovalPolicy {
  id: number;
  project_id: number;
  name: string;
  asset_types: string[];
  connector_id: number | null; // null = applies to any source, incl. manual upload
  enabled: boolean;
  version: number; // bumped on every definition change
  source_conditions: SourceCondition[] | null; // v1.2.1 (D26 Tier-0)
  engine_conditions: { contradiction_check?: string } | null; // v1.2.1 (D26 Tier-2)
  domains: string[] | null; // v1.2.1 (D26/D27): domain-prefix coverage
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface IngestionJob {
  id: number;
  project_id: number;
  connector_id: number;
  status: string; // PENDING | RUNNING | COMPLETED | FAILED
  files_discovered: number;
  files_ingested: number;
  files_duplicate: number;
  files_changed: number;
  files_failed: number;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface SourceDocument {
  id: number;
  ingestion_job_id: number;
  source_uri: string;
  file_hash: string | null;
  size_bytes: number | null;
  source_modified_at: string | null;
  status: string; // INGESTED | DUPLICATE | CHANGED | FAILED
  error: string | null;
  details: {
    revisions_created: { asset_id: number; revision_id: number }[];
    updated_in_place: number;
    assets_added: number;
    unchanged: number;
    skipped_pending_review: { asset_id: number; reason: string }[];
    possibly_stale: { asset_id: number; name: string }[];
  } | null;
  document_id: number | null;
  created_at: string;
}

export interface CoverageTrendPoint {
  run_id: number;
  completed_at: string | null;
  pass_rate: number;
  average_coverage_score: number;
  claims_total: number | null;
  verdict_counts: { ENTAILED: number; CONTRADICTED: number; UNSUPPORTED: number } | null;
  supported_pct: number | null;
}

export interface CoverageTrend {
  expert_model_id: number;
  runs: CoverageTrendPoint[];
}

export interface AgentActivity {
  agent_id: string;
  clearance: string | null;
  calls: number;
  denied: number;
  blocked_answers: number;
  tools: Record<string, number>;
  expert_models: number[];
  last_seen: string;
  gateway_version: string | null;
}

export interface AgentActivitySummary {
  agents: AgentActivity[];
  total_calls: number;
  total_denied: number;
}

export interface TrustComponent {
  key: string;
  label: string;
  score: number | null;
  weight: number;
  measured: boolean;
  reason: string;
  details: Record<string, unknown>;
}

export interface TrustScore {
  expert_model_id: number;
  trust_score: number | null;
  score_version: string;
  summary: string;
  components: TrustComponent[];
}

export interface GovernanceInboxItem {
  id: string;
  type: 'CONFLICT' | 'REVISION' | 'GOVERNANCE_WARNING';
  source_id: number;
  expert_model_id: number | null;
  expert_model_name: string | null;
  related_expert_model_ids?: number[];
  asset_id?: number;
  source_asset_id?: number;
  target_asset_id?: number;
  status: string;
  classification: string | null;
  confidence: number | null;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  bucket: 'NEEDS_REVIEW' | 'CAN_WAIT' | 'RESOLVED';
  title: string;
  reason: string;
  deep_link: string;
  created_at: string | null;
  resolved_at: string | null;
}

export interface GovernanceGateConflictRef {
  relationship_id: number | null;
  source_asset_id: number | null;
  target_asset_id: number | null;
  classification: string | null;
  status: string | null;
  confidence: number | null;
  reason?: string;
}

export interface GovernanceReadiness {
  expert_model_id: number;
  expert_model_name: string;
  trust_score: number | null;
  trust_summary: string;
  compile_allowed: boolean;
  blocking_conflicts: GovernanceGateConflictRef[];
  advisory_conflicts: GovernanceGateConflictRef[];
  dismissed_conflicts: number;
  conflict_scan_performed: boolean;
  governance_facts: string[];
}

// v1.3 (D28): one PROJECTION_RENDERED ledger event, projected. `stale`
// is computed (recompose-and-compare) for the latest render per
// renderer; a stale render is regenerated, never edited.
export interface ProjectionRenderRecord {
  event_id: number;
  timestamp: string | null;
  actor: string;
  current: boolean;
  stale: boolean | null;
  renderer?: string;
  engine_version?: string;
  clearance?: string;
  status_inclusion?: string[];
  domain_prefix?: string | null;
  audit_cursor?: number;
  rendered_at?: string;
  counts?: { nodes: number; edges: number; groups: number };
  excluded?: Record<string, number>;
  projection_hash?: string;
  manifest_hash?: string;
  files?: Record<string, string>;
  output?: string;
}

export interface GovernanceInbox {
  project_id: number;
  inbox_version: string;
  generated_at: string;
  resolved_window_days: number;
  gate_policy: Record<string, unknown>;
  summary: {
    needs_review: number;
    can_wait: number;
    recently_resolved: number;
    high_severity: number;
    blocked_expert_models: number;
    total_expert_models: number;
  };
  items: GovernanceInboxItem[];
  readiness: GovernanceReadiness[];
}

export interface AuditEvent {
  id: number;
  timestamp: string;
  actor: string;
  event_type: string;
  target_id: string;
  details: string;
}

export interface DashboardStats {
  documents_uploaded: number;
  documents_parsed: number;
  documents_failed: number;
  readiness_score: number;
  assets_extracted: number;
  expert_models: number;
  agent_packages: number;
  assets_status_counts: {
    CANDIDATE: number;
    REVIEWED: number;
    APPROVED: number;
    ARCHIVED: number;
  };
}

export interface AuthUser {
  name: string;
  display_name: string;
  role: string | null;
  kind: string;
  must_change_password: boolean;
}

export interface Principal {
  id: number;
  name: string;
  display_name: string;
  kind: string;
  role: string | null;
  clearance: string | null;
  active: boolean;
  created_by: string | null;
  created_at: string;
  one_time_password?: string | null;
}

export interface ApiToken {
  fingerprint: string;
  principal_name: string;
  principal_kind: string;
  label: string | null;
  created_at: string;
  expires_at: string | null;
  revoked_at: string | null;
  last_used_at: string | null;
}

// WS3: a MIRROR of identity.ROLE_PERMISSIONS for hiding what the backend
// would refuse. The backend is the source of truth - this only shapes UI.
const ROLE_PERMISSIONS: Record<string, string[]> = {
  ADMIN: ['identity:manage', 'tokens:manage', 'assets:read', 'assets:review', 'assets:approve',
          'assets:delete', 'documents:ingest', 'connectors:manage', 'audit:read',
          'settings:manage', 'mcp:consume', 'credentials:manage'],
  GOVERNANCE_REVIEWER: ['assets:read', 'assets:review', 'assets:approve', 'audit:read'],
  KNOWLEDGE_OPERATOR: ['assets:read', 'documents:ingest', 'connectors:manage'],
  AGENT_CONSUMER: ['mcp:consume'],
  READ_ONLY: ['assets:read'],
};

export function can(user: AuthUser | null, permission: string): boolean {
  if (!user || !user.role) return false;
  return (ROLE_PERMISSIONS[user.role] || []).includes(permission);
}

interface AppState {
  // Identity Boundary v1.0: who is logged in. The backend decides the
  // actor from the bearer token - the frontend never sends actor names.
  currentUser: AuthUser | null;
  authReady: boolean;
  authError: string | null;
  login: (name: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<boolean>;
  restoreSession: () => Promise<void>;

  projects: Project[];
  activeProjectId: number | null;
  documents: Document[];
  assets: KnowledgeAsset[];
  experts: ExpertModel[];
  packages: AgentPackage[];
  auditEvents: AuditEvent[];
  stats: DashboardStats | null;
  loading: boolean;
  error: string | null;
  
  fetchProjects: () => Promise<void>;
  setActiveProject: (id: number) => void;
  createProject: (name: string, description: string) => Promise<void>;
  fetchProjectData: (projectId: number) => Promise<void>;
  uploadDocument: (projectId: number, file: File, department: string, owner: string) => Promise<void>;
  triggerBatchDemo: (projectId: number) => Promise<void>;
  triggerExtraction: (projectId: number) => Promise<void>;
  updateAssetStatus: (assetId: number, status: string, notes?: string) => Promise<void>;
  bulkUpdateAssetStatus: (assetIds: number[], status: string) => Promise<void>;
  createExpertModel: (projectId: number, name: string, description: string, assetIds: number[]) => Promise<void>;
  createAgentPackage: (projectId: number, name: string, expertModelId: number, version?: string, clearanceLevel?: string) => Promise<void>;
  fetchAuditTrail: (filters?: { actor?: string; target_id?: string; since?: string; until?: string; limit?: number }) => Promise<void>;
  deleteAsset: (assetId: number) => Promise<void>;
  deleteDocumentAssets: (documentId: number, status?: string) => Promise<void>;

  conflicts: AssetRelationship[];
  conflictScanSummary: ConflictScanSummary | null;
  conflictScanLoading: boolean;
  conflictScore: ConflictScore | null;
  fetchConflicts: (expertModelId: number) => Promise<void>;
  runConflictScan: (expertModelId: number) => Promise<void>;
  reviewConflict: (relationshipId: number, status: string, notes: string | null, expertModelId: number) => Promise<void>;

  revisionQueue: RevisionQueueItem[];
  fetchRevisionQueue: (projectId: number) => Promise<void>;
  reviewRevision: (revisionId: number, action: string, notes: string, projectId: number) => Promise<void>;

  trustScores: TrustScore[];

  governanceInbox: GovernanceInbox | null;
  governanceInboxLoading: boolean;
  fetchGovernanceInbox: (projectId: number) => Promise<void>;
  reviewClaimVerdict: (verdictId: number, comment: string) => Promise<void>;

  // v1.3 (D28): render history is a ledger projection (PROJECTION_RENDERED
  // events + a computed staleness verdict); rendering is a governed act.
  projections: ProjectionRenderRecord[];
  projectionsLoading: boolean;
  fetchProjections: (projectId: number) => Promise<void>;
  renderProjection: (projectId: number, body: {
    renderer: string; clearance: string; domain_prefix?: string | null;
  }) => Promise<boolean>;

  sourceConnectors: SourceConnector[];
  ingestionJobs: IngestionJob[];
  jobFiles: Record<number, SourceDocument[]>;
  fetchConnectors: (projectId: number) => Promise<void>;
  createConnector: (projectId: number, name: string, rootPath: string, extensions?: string,
                    type?: string, externalCredentialId?: number | null,
                    lane?: string) => Promise<void>;
  scanConnector: (connectorId: number, projectId: number) => Promise<void>;

  // v1.4.1 (the D8 amendment): the Operations area — a computed
  // projection; the only write in the area is the pre-existing
  // asset-review PATCH (updateAssetStatus).
  operations: OperationsView | null;
  operationsLoading: boolean;
  fetchOperations: (projectId: number) => Promise<void>;
  fetchIngestionJobs: (projectId: number) => Promise<void>;
  fetchJobFiles: (jobId: number) => Promise<void>;

  // v1.2.0 (D25) custody administration - credentials:manage only. The
  // secret is sent once at create/rotate and never returned by anything;
  // these shapes have no field it could come back through.
  externalCredentials: ExternalCredential[];
  fetchExternalCredentials: () => Promise<void>;
  createExternalCredential: (name: string, purpose: string, secret: string,
                             grantedScopes: string[],
                             coordinates: Record<string, string>) => Promise<void>;
  rotateExternalCredential: (credentialId: number, secret: string) => Promise<void>;
  revokeExternalCredential: (credentialId: number, reason: string) => Promise<void>;
  fetchCredentialDetail: (credentialId: number) => Promise<ExternalCredentialDetail | null>;

  llmSettings: LLMFunctionSetting[];
  fetchLLMSettings: () => Promise<void>;
  updateLLMSetting: (fn: string, model: string | null) => Promise<void>;

  // Identity administration (WS3, ADMIN only)
  principals: Principal[];
  apiTokens: ApiToken[];
  lastOneTimePassword: { name: string; password: string } | null;
  lastIssuedToken: { principal: string; token: string; fingerprint: string } | null;
  fetchPrincipals: () => Promise<void>;
  createPrincipal: (payload: { name: string; kind: string; role?: string; clearance?: string; display_name?: string }) => Promise<boolean>;
  updatePrincipal: (name: string, payload: { role?: string; active?: boolean; clearance?: string; display_name?: string }) => Promise<boolean>;
  resetPrincipalPassword: (name: string) => Promise<void>;
  fetchApiTokens: () => Promise<void>;
  issueApiToken: (principalName: string, label?: string, expiresDays?: number) => Promise<void>;
  revokeApiToken: (fingerprint: string) => Promise<void>;

  approvalPolicies: ApprovalPolicy[];
  fetchApprovalPolicies: (projectId: number) => Promise<void>;
  createApprovalPolicy: (projectId: number, name: string, assetTypes: string[], connectorId: number | null,
                         conditions?: { source_conditions?: SourceCondition[] | null;
                                        engine_conditions?: { contradiction_check: string } | null;
                                        domains?: string[] | null }) => Promise<void>;
  toggleApprovalPolicy: (policyId: number, enabled: boolean, projectId: number) => Promise<void>;
  // v1.2.1 (D27): a domain correction is a governed act on the normal
  // asset-update path (ASSET_DOMAIN_CORRECTED) - never a content edit.
  correctAssetDomain: (assetId: number, domain: string | null) => Promise<void>;

  agentActivity: AgentActivitySummary | null;
  fetchAgentActivity: () => Promise<void>;

  benchmarks: BenchmarkQuestion[];
  evaluationRuns: EvaluationRun[];
  evaluationRunning: boolean;
  coverageTrend: CoverageTrend | null;
  fetchCoverageTrend: (expertModelId: number) => Promise<void>;
  fetchEvaluations: (projectId: number) => Promise<void>;
  createBenchmark: (projectId: number, payload: Record<string, unknown>) => Promise<void>;
  deleteBenchmark: (projectId: number, benchmarkId: number) => Promise<void>;
  startEvaluation: (projectId: number, expertModelId: number) => Promise<void>;

  // v1.1.x Consumption Operations Workbench (D24: projections only).
  packageSelection: PackageModelSelection | null;
  packageComparison: ModelComparison | null;
  selectionHistory: AuditEvent[];
  consumptionLoading: boolean;
  selectionError: string | null;
  consumptionInbox: ConsumptionInbox | null;
  fetchConsumptionInbox: (projectId?: number | null) => Promise<void>;
  fetchPackageConsumption: (packageId: number) => Promise<void>;
  projectBindings: ExpertAgentBinding[];
  fetchProjectBindings: () => Promise<void>;
  bindingLineage: BindingLineage | null;
  fetchBindingLineage: (bindingId: number) => Promise<void>;
  submitModelSelection: (packageId: number, payload: {
    provider: string;
    model: string;
    supporting_evaluation_run_ids: number[];
    rationale: string;
  }) => Promise<boolean>;
}

const API_BASE = 'http://localhost:8000/api';

// Identity Boundary v1.0: the bearer token is the only identity input any
// request carries (?actor= params and reviewer fields are gone - the
// boundary decides the actor). apiFetch injects the token; a 401 clears
// the session so the login gate re-renders.
let AUTH_TOKEN: string | null =
  typeof window !== 'undefined' ? window.localStorage.getItem('em_token') : null;

const apiFetch = async (input: string, init: RequestInit = {}): Promise<Response> => {
  const headers = new Headers(init.headers || {});
  if (AUTH_TOKEN) headers.set('Authorization', `Bearer ${AUTH_TOKEN}`);
  const res = await globalThis.fetch(input, { ...init, headers });
  if (res.status === 401 && AUTH_TOKEN) {
    AUTH_TOKEN = null;
    window.localStorage.removeItem('em_token');
    useAppStore.setState({ currentUser: null });
  }
  return res;
};

export const useAppStore = create<AppState>((set, get) => ({
  currentUser: null,
  authReady: false,
  authError: null,

  restoreSession: async () => {
    if (!AUTH_TOKEN) {
      set({ authReady: true, currentUser: null });
      return;
    }
    try {
      const res = await apiFetch(`${API_BASE}/auth/me`);
      if (res.ok) {
        set({ currentUser: await res.json(), authReady: true });
      } else {
        set({ currentUser: null, authReady: true });
      }
    } catch {
      set({ currentUser: null, authReady: true });
    }
  },

  login: async (name: string, password: string) => {
    set({ authError: null });
    try {
      const res = await globalThis.fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, password }),
      });
      if (!res.ok) {
        set({ authError: 'Invalid credentials' });
        return false;
      }
      const data = await res.json();
      AUTH_TOKEN = data.token;
      window.localStorage.setItem('em_token', data.token);
      set({
        currentUser: {
          name: data.name, display_name: data.display_name, role: data.role,
          kind: data.kind, must_change_password: data.must_change_password,
        },
        authReady: true,
      });
      return true;
    } catch {
      set({ authError: 'Backend unreachable' });
      return false;
    }
  },

  logout: async () => {
    try {
      await apiFetch(`${API_BASE}/auth/logout`, { method: 'POST' });
    } catch {
      // session revocation is best-effort; the local token is cleared regardless
    }
    AUTH_TOKEN = null;
    window.localStorage.removeItem('em_token');
    set({ currentUser: null });
  },

  changePassword: async (currentPassword: string, newPassword: string) => {
    set({ authError: null });
    const res = await apiFetch(`${API_BASE}/auth/change-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      set({ authError: body?.detail || 'Password change failed' });
      return false;
    }
    set({ currentUser: await res.json() });
    return true;
  },

  projects: [],
  activeProjectId: null,
  documents: [],
  assets: [],
  experts: [],
  packages: [],
  auditEvents: [],
  stats: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const res = await apiFetch(`${API_BASE}/projects`);
      if (!res.ok) throw new Error('Failed to fetch projects');
      const data = await res.json();
      set({ projects: data, loading: false });
      
      // Auto-set first project if none active
      if (data.length > 0 && get().activeProjectId === null) {
        get().setActiveProject(data[0].id);
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  setActiveProject: (id: number) => {
    set({ activeProjectId: id });
    get().fetchProjectData(id);
  },

  createProject: async (name: string, description: string) => {
    set({ loading: true, error: null });
    try {
      const res = await apiFetch(`${API_BASE}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, customer_id: 1 }),
      });
      if (!res.ok) throw new Error('Failed to create workspace project');
      await get().fetchProjects();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  fetchProjectData: async (projectId: number) => {
    set({ loading: true, error: null });
    try {
      // Fetch stats, docs, assets, experts, packages in parallel
      const [docsRes, assetsRes, expertsRes, packagesRes, statsRes, trustRes] = await Promise.all([
        apiFetch(`${API_BASE}/projects/${projectId}/documents`),
        apiFetch(`${API_BASE}/projects/${projectId}/assets`),
        apiFetch(`${API_BASE}/projects/${projectId}/experts`),
        apiFetch(`${API_BASE}/projects/${projectId}/packages`),
        apiFetch(`${API_BASE}/dashboard/${projectId}`),
        apiFetch(`${API_BASE}/projects/${projectId}/trust-scores`)
      ]);

      const documents = docsRes.ok ? await docsRes.json() : [];
      const assets = assetsRes.ok ? await assetsRes.json() : [];
      const experts = expertsRes.ok ? await expertsRes.json() : [];
      const packages = packagesRes.ok ? await packagesRes.json() : [];
      const stats = statsRes.ok ? await statsRes.json() : null;
      const trustScores = trustRes.ok ? await trustRes.json() : [];

      set({ documents, assets, experts, packages, stats, trustScores, loading: false });
      get().fetchAuditTrail();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  uploadDocument: async (projectId: number, file: File, department: string, owner: string) => {
    set({ loading: true, error: null });
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('department', department);
      formData.append('owner', owner);

      const res = await apiFetch(`${API_BASE}/projects/${projectId}/documents`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('Failed to upload document');
      await get().fetchProjectData(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  triggerBatchDemo: async (projectId: number) => {
    set({ loading: true, error: null });
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/documents/batch-demo`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to load batch demo documents');
      await get().fetchProjectData(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  triggerExtraction: async (projectId: number) => {
    set({ loading: true, error: null });
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/extract`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to extract knowledge assets');
      await get().fetchProjectData(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  updateAssetStatus: async (assetId: number, status: string, notes?: string) => {
    const pid = get().activeProjectId;
    if (!pid) return;
    set({ loading: true, error: null });
    try {
      const res = await apiFetch(`${API_BASE}/assets/${assetId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error('Failed to update asset status');
      
      // If notes are supplied, create review details
      // Simple mockup review post for MVP governance tracking
      await get().fetchProjectData(pid);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  bulkUpdateAssetStatus: async (assetIds: number[], status: string) => {
    const pid = get().activeProjectId;
    if (!pid) return;
    set({ loading: true, error: null });
    try {
      const res = await apiFetch(`${API_BASE}/assets/bulk`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ asset_ids: assetIds, status }),
      });
      if (!res.ok) throw new Error('Failed to bulk update asset status');
      await get().fetchProjectData(pid);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  createExpertModel: async (projectId: number, name: string, description: string, assetIds: number[]) => {
    set({ loading: true, error: null });
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/experts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, project_id: projectId, asset_ids: assetIds }),
      });
      if (!res.ok) throw new Error('Failed to build Expert Model');
      await get().fetchProjectData(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  createAgentPackage: async (projectId: number, name: string, expertModelId: number, version?: string, clearanceLevel?: string) => {
    set({ loading: true, error: null });
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/packages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, expert_model_id: expertModelId, project_id: projectId, governance_version: version || '0.1.0', clearance_level: clearanceLevel || 'INTERNAL' }),
      });
      if (!res.ok) {
        // Surface governance gate blocks (409) with their reason.
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to compile Agent Package');
      }
      await get().fetchProjectData(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false });
    }
  },

  fetchAuditTrail: async (filters?: { actor?: string; target_id?: string; since?: string; until?: string; limit?: number }) => {
    try {
      const params = new URLSearchParams();
      params.set('limit', String(filters?.limit ?? 300));
      if (filters?.actor) params.set('actor', filters.actor);
      if (filters?.target_id) params.set('target_id', filters.target_id);
      if (filters?.since) params.set('since', filters.since);
      if (filters?.until) params.set('until', filters.until);
      const res = await apiFetch(`${API_BASE}/audit?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        set({ auditEvents: data });
      }
    } catch (err) {
      console.error('Audit trail error', err);
    }
  },

  deleteAsset: async (assetId: number) => {
    const pid = get().activeProjectId;
    if (!pid) return;
    
    // Optimistic local state update
    const currentAssets = get().assets;
    set({ assets: currentAssets.filter(a => a.id !== assetId) });
    
    try {
      const res = await apiFetch(`${API_BASE}/knowledge-assets/${assetId}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Failed to delete asset');
      await get().fetchProjectData(pid);
    } catch (err) {
      // Rollback on error
      set({ assets: currentAssets, error: err instanceof Error ? err.message : String(err) });
    }
  },

  deleteDocumentAssets: async (documentId: number, status?: string) => {
    const pid = get().activeProjectId;
    if (!pid) return;
    
    // Optimistic local state update
    const currentAssets = get().assets;
    set({ 
      assets: currentAssets.filter(a => !(a.document_id === documentId && (!status || a.status === status))) 
    });
    
    try {
      const url = status 
        ? `${API_BASE}/documents/${documentId}/knowledge-assets?status=${status}`
        : `${API_BASE}/documents/${documentId}/knowledge-assets`;
      
      const res = await fetch(url, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Failed to delete document assets');
      await get().fetchProjectData(pid);
    } catch (err) {
      // Rollback on error
      set({ assets: currentAssets, error: err instanceof Error ? err.message : String(err) });
    }
  },

  conflicts: [],
  conflictScanSummary: null,
  conflictScanLoading: false,
  conflictScore: null,

  fetchConflicts: async (expertModelId: number) => {
    try {
      const [relsRes, scoreRes] = await Promise.all([
        apiFetch(`${API_BASE}/experts/${expertModelId}/conflicts`),
        apiFetch(`${API_BASE}/experts/${expertModelId}/conflict-score`)
      ]);
      if (!relsRes.ok) throw new Error('Failed to fetch conflict relationships');
      const conflicts = await relsRes.json();
      const conflictScore = scoreRes.ok ? await scoreRes.json() : null;
      set({ conflicts, conflictScore });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  runConflictScan: async (expertModelId: number) => {
    set({ conflictScanLoading: true, error: null });
    try {
      const res = await apiFetch(`${API_BASE}/experts/${expertModelId}/conflict-scan`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Conflict scan failed');
      const summary = await res.json();
      set({ conflictScanSummary: summary, conflictScanLoading: false });
      await get().fetchConflicts(expertModelId);
      get().fetchAuditTrail();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), conflictScanLoading: false });
    }
  },

  trustScores: [],
  revisionQueue: [],
  agentActivity: null,
  governanceInbox: null,
  governanceInboxLoading: false,

  fetchGovernanceInbox: async (projectId: number) => {
    set({ governanceInboxLoading: true });
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/governance/inbox`);
      if (!res.ok) throw new Error('Failed to fetch governance inbox');
      const data = await res.json();
      set({ governanceInbox: data, governanceInboxLoading: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), governanceInboxLoading: false });
    }
  },

  projections: [],
  projectionsLoading: false,
  fetchProjections: async (projectId: number) => {
    set({ projectionsLoading: true });
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/projections`);
      if (!res.ok) throw new Error('Failed to fetch render history');
      set({ projections: await res.json(), projectionsLoading: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), projectionsLoading: false });
    }
  },
  renderProjection: async (projectId: number, body) => {
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/projections/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || 'Render failed');
      }
      await get().fetchProjections(projectId);
      return true;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
      return false;
    }
  },

  sourceConnectors: [],
  ingestionJobs: [],
  jobFiles: {},

  fetchConnectors: async (projectId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/connectors`);
      if (res.ok) set({ sourceConnectors: await res.json() });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  createConnector: async (projectId: number, name: string, rootPath: string, extensions?: string,
                          type?: string, externalCredentialId?: number | null,
                          lane?: string) => {
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/connectors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name, root_path: rootPath, include_extensions: extensions || null,
          type: type || 'LOCAL_FOLDER',
          external_credential_id: externalCredentialId ?? null,
          // v1.4.0 (D29/D30): the channel declaration — PROPOSAL marks
          // the agent-finding return path; its candidates hold for the
          // human gate and become DERIVED on acceptance.
          lane: lane || 'PRIMARY',
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to create connector');
      }
      await get().fetchConnectors(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  scanConnector: async (connectorId: number, projectId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/connectors/${connectorId}/scan`, { method: 'POST' });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to start scan');
      }
      await get().fetchIngestionJobs(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  fetchIngestionJobs: async (projectId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/ingestion-jobs`);
      if (res.ok) set({ ingestionJobs: await res.json() });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  fetchJobFiles: async (jobId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/ingestion-jobs/${jobId}/files`);
      if (res.ok) {
        const data = await res.json();
        set({ jobFiles: { ...get().jobFiles, [jobId]: data } });
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  // v1.4.1 (the D8 amendment): the Operations view — pure projection,
  // recomputed by the backend on every read; nothing to invalidate.
  operations: null,
  operationsLoading: false,
  fetchOperations: async (projectId: number) => {
    set({ operationsLoading: true });
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/operations`);
      if (!res.ok) throw new Error('Failed to fetch the Operations view');
      set({ operations: await res.json(), operationsLoading: false });
    } catch (err) {
      set({ operationsLoading: false,
            error: err instanceof Error ? err.message : String(err) });
    }
  },

  // v1.2.0 (D25) custody administration. Secrets travel one way: into
  // create/rotate request bodies, never back. Errors surface the backend
  // detail so refusals (custody permission, revoked binding) stay loud.
  externalCredentials: [],

  fetchExternalCredentials: async () => {
    try {
      const res = await apiFetch(`${API_BASE}/credentials`);
      if (res.ok) set({ externalCredentials: await res.json() });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  createExternalCredential: async (name: string, purpose: string, secret: string,
                                   grantedScopes: string[],
                                   coordinates: Record<string, string>) => {
    const res = await apiFetch(`${API_BASE}/credentials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name, purpose, secret,
        granted_scopes: grantedScopes.length ? grantedScopes : null,
        coordinates: Object.keys(coordinates).length ? coordinates : null,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail || 'Failed to create credential');
    }
    await get().fetchExternalCredentials();
  },

  rotateExternalCredential: async (credentialId: number, secret: string) => {
    const res = await apiFetch(`${API_BASE}/credentials/${credentialId}/rotate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ secret }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail || 'Failed to rotate credential');
    }
    await get().fetchExternalCredentials();
  },

  revokeExternalCredential: async (credentialId: number, reason: string) => {
    const res = await apiFetch(`${API_BASE}/credentials/${credentialId}/revoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: reason || null }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail || 'Failed to revoke credential');
    }
    await get().fetchExternalCredentials();
  },

  fetchCredentialDetail: async (credentialId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/credentials/${credentialId}`);
      if (res.ok) return await res.json() as ExternalCredentialDetail;
      return null;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
      return null;
    }
  },

  llmSettings: [],

  fetchLLMSettings: async () => {
    try {
      const res = await apiFetch(`${API_BASE}/settings/llm`);
      if (res.ok) set({ llmSettings: await res.json() });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  updateLLMSetting: async (fn: string, model: string | null) => {
    try {
      const res = await apiFetch(`${API_BASE}/settings/llm/${fn}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to update LLM setting');
      }
      await get().fetchLLMSettings();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  // Identity administration (WS3, ADMIN only). One-time secrets are held in
  // transient state for a single display and never persisted client-side.
  principals: [],
  apiTokens: [],
  lastOneTimePassword: null,
  lastIssuedToken: null,

  fetchPrincipals: async () => {
    try {
      const res = await apiFetch(`${API_BASE}/identity/principals`);
      if (res.ok) set({ principals: await res.json() });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  createPrincipal: async (payload) => {
    try {
      const res = await apiFetch(`${API_BASE}/identity/principals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to create principal');
      }
      const created = await res.json();
      if (created.one_time_password) {
        set({ lastOneTimePassword: { name: created.name, password: created.one_time_password } });
      }
      await get().fetchPrincipals();
      return true;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
      return false;
    }
  },

  updatePrincipal: async (name, payload) => {
    try {
      const res = await apiFetch(`${API_BASE}/identity/principals/${encodeURIComponent(name)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to update principal');
      }
      await get().fetchPrincipals();
      return true;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
      return false;
    }
  },

  resetPrincipalPassword: async (name) => {
    try {
      const res = await apiFetch(`${API_BASE}/identity/principals/${encodeURIComponent(name)}/reset-password`, {
        method: 'POST',
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to reset password');
      }
      const data = await res.json();
      set({ lastOneTimePassword: { name: data.name, password: data.one_time_password } });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  fetchApiTokens: async () => {
    try {
      const res = await apiFetch(`${API_BASE}/identity/tokens`);
      if (res.ok) set({ apiTokens: await res.json() });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  issueApiToken: async (principalName, label, expiresDays) => {
    try {
      const res = await apiFetch(`${API_BASE}/identity/tokens`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ principal_name: principalName, label: label || null,
                               expires_days: expiresDays ?? null }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to issue token');
      }
      const data = await res.json();
      set({ lastIssuedToken: { principal: data.principal_name, token: data.token, fingerprint: data.fingerprint } });
      await get().fetchApiTokens();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  revokeApiToken: async (fingerprint) => {
    try {
      const res = await apiFetch(`${API_BASE}/identity/tokens/${encodeURIComponent(fingerprint)}/revoke`, {
        method: 'POST',
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to revoke token');
      }
      await get().fetchApiTokens();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  approvalPolicies: [],

  fetchApprovalPolicies: async (projectId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/approval-policies`);
      if (res.ok) set({ approvalPolicies: await res.json() });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  createApprovalPolicy: async (projectId: number, name: string, assetTypes: string[], connectorId: number | null,
                               conditions?: { source_conditions?: SourceCondition[] | null;
                                              engine_conditions?: { contradiction_check: string } | null;
                                              domains?: string[] | null }) => {
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/approval-policies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, asset_types: assetTypes, connector_id: connectorId,
                               ...(conditions ?? {}) }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to create approval policy');
      }
      await get().fetchApprovalPolicies(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  correctAssetDomain: async (assetId: number, domain: string | null) => {
    const pid = get().activeProjectId;
    if (!pid) return;
    try {
      const res = await apiFetch(`${API_BASE}/assets/${assetId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to correct asset domain');
      }
      await get().fetchProjectData(pid);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  toggleApprovalPolicy: async (policyId: number, enabled: boolean, projectId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/approval-policies/${policyId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to update approval policy');
      }
      await get().fetchApprovalPolicies(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  // Records a VERIFICATION_REVIEWED audit event; the verdict artifact itself
  // is immutable and never changes.
  reviewClaimVerdict: async (verdictId: number, comment: string) => {
    try {
      const res = await apiFetch(`${API_BASE}/claim-verdicts/${verdictId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment }),
      });
      if (!res.ok) throw new Error('Failed to record verification review');
      get().fetchAuditTrail();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  fetchAgentActivity: async () => {
    try {
      const res = await apiFetch(`${API_BASE}/agents/activity`);
      if (!res.ok) throw new Error('Failed to fetch agent activity');
      const data = await res.json();
      set({ agentActivity: data });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  benchmarks: [],
  evaluationRuns: [],
  evaluationRunning: false,
  coverageTrend: null,

  fetchCoverageTrend: async (expertModelId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/experts/${expertModelId}/coverage-trend`);
      if (!res.ok) throw new Error('Failed to fetch coverage trend');
      const data = await res.json();
      set({ coverageTrend: data });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  fetchEvaluations: async (projectId: number) => {
    try {
      const [bRes, rRes] = await Promise.all([
        apiFetch(`${API_BASE}/projects/${projectId}/benchmarks`),
        apiFetch(`${API_BASE}/projects/${projectId}/evaluations`)
      ]);
      const benchmarks = bRes.ok ? await bRes.json() : [];
      const evaluationRuns = rRes.ok ? await rRes.json() : [];
      set({ benchmarks, evaluationRuns });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  createBenchmark: async (projectId: number, payload: Record<string, unknown>) => {
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/benchmarks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, project_id: projectId }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to create benchmark question');
      }
      await get().fetchEvaluations(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  deleteBenchmark: async (projectId: number, benchmarkId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/benchmarks/${benchmarkId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete benchmark question');
      await get().fetchEvaluations(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  startEvaluation: async (projectId: number, expertModelId: number) => {
    set({ evaluationRunning: true, error: null });
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/evaluations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, expert_model_id: expertModelId }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to start evaluation run');
      }
      const run = await res.json();
      // The batch executes server-side in the background: poll until terminal.
      for (let i = 0; i < 200; i++) {
        await new Promise(resolve => setTimeout(resolve, 3000));
        const statusRes = await apiFetch(`${API_BASE}/projects/${projectId}/evaluations/${run.id}`);
        if (!statusRes.ok) continue;
        const current = await statusRes.json();
        await get().fetchEvaluations(projectId);
        if (current.status === 'COMPLETED' || current.status === 'FAILED') break;
      }
      // Completed runs feed Evaluation Reliability and Evidence Coverage.
      await get().fetchProjectData(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    } finally {
      set({ evaluationRunning: false });
    }
  },

  // v1.1.x Selection Workbench reads (D24): the current selection, the
  // computed comparison, and the PACKAGE_MODEL_SELECTED audit history are
  // all projections of governed facts. Nothing here is cached or persisted;
  // a 404 selection means "no model selected yet" (honest absence, D12) and
  // a 403 history means the role lacks audit:read - the panel hides.
  packageSelection: null,
  packageComparison: null,
  selectionHistory: [],
  consumptionLoading: false,
  selectionError: null,
  consumptionInbox: null,
  projectBindings: [],
  bindingLineage: null,

  fetchProjectBindings: async () => {
    // WS3: bindings are listed per package (the existing reads); the
    // explorer composes the project-wide list client-side - a projection,
    // not a new endpoint.
    try {
      const pkgs = get().packages;
      const results = await Promise.all(pkgs.map(p =>
        apiFetch(`${API_BASE}/packages/${p.id}/bindings`)
          .then(r => (r.ok ? r.json() : []))
          .catch(() => [])));
      set({ projectBindings: results.flat() });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  fetchBindingLineage: async (bindingId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/bindings/${bindingId}/lineage`);
      if (res.ok) set({ bindingLineage: await res.json() });
      else set({ bindingLineage: null });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  fetchConsumptionInbox: async (projectId?: number | null) => {
    // WS2: one read, fully computed server-side. There is no action to
    // take ON an item - deep links lead to where the facts change.
    try {
      const qs = projectId != null ? `?project_id=${projectId}` : '';
      const res = await apiFetch(`${API_BASE}/consumption/inbox${qs}`);
      if (res.ok) set({ consumptionInbox: await res.json() });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  fetchPackageConsumption: async (packageId: number) => {
    set({ consumptionLoading: true, selectionError: null });
    try {
      const [selRes, cmpRes, histRes] = await Promise.all([
        apiFetch(`${API_BASE}/packages/${packageId}/model-selection`),
        apiFetch(`${API_BASE}/packages/${packageId}/model-comparison`),
        apiFetch(`${API_BASE}/audit?event_prefix=PACKAGE_MODEL_SELECTED&target_id=${packageId}&limit=100`),
      ]);
      const packageSelection = selRes.ok ? await selRes.json() : null;
      const packageComparison = cmpRes.ok ? await cmpRes.json() : null;
      const selectionHistory = histRes.ok ? await histRes.json() : [];
      set({ packageSelection, packageComparison, selectionHistory, consumptionLoading: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), consumptionLoading: false });
    }
  },

  submitModelSelection: async (packageId, payload) => {
    // The ONLY write in the workbench milestone: the existing governed PUT
    // (assets:approve). The boundary validates the evidence; refusals are
    // surfaced verbatim, never retried or softened.
    set({ selectionError: null });
    try {
      const res = await apiFetch(`${API_BASE}/packages/${packageId}/model-selection`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Selection was refused');
      }
      await get().fetchPackageConsumption(packageId);
      return true;
    } catch (err) {
      set({ selectionError: err instanceof Error ? err.message : String(err) });
      return false;
    }
  },

  fetchRevisionQueue: async (projectId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/projects/${projectId}/revisions`);
      if (!res.ok) throw new Error('Failed to fetch revision queue');
      const data = await res.json();
      set({ revisionQueue: data });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  reviewRevision: async (revisionId: number, action: string, notes: string, projectId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/revisions/${revisionId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, notes }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Failed to record revision review');
      }
      // Approval changes the served asset content and rescans conflict
      // graphs of affected models - refresh everything derived.
      await get().fetchRevisionQueue(projectId);
      await get().fetchProjectData(projectId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  reviewConflict: async (relationshipId: number, status: string, notes: string | null, expertModelId: number) => {
    try {
      const res = await apiFetch(`${API_BASE}/conflicts/${relationshipId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, notes }),
      });
      if (!res.ok) throw new Error('Failed to record conflict review');
      await get().fetchConflicts(expertModelId);
      get().fetchAuditTrail();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  }
}));
