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

export interface AgentPackage {
  id: number;
  project_id: number;
  name: string;
  expert_model_id: number;
  governance_version: string;
  quality_score: number;
  asset_references: string;
  created_at: string;
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

interface AppState {
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
  createAgentPackage: (projectId: number, name: string, expertModelId: number, version?: string) => Promise<void>;
  fetchAuditTrail: () => Promise<void>;
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
}

const API_BASE = 'http://localhost:8000/api';

export const useAppStore = create<AppState>((set, get) => ({
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
      const res = await fetch(`${API_BASE}/projects`);
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
      const res = await fetch(`${API_BASE}/projects`, {
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
        fetch(`${API_BASE}/projects/${projectId}/documents`),
        fetch(`${API_BASE}/projects/${projectId}/assets`),
        fetch(`${API_BASE}/projects/${projectId}/experts`),
        fetch(`${API_BASE}/projects/${projectId}/packages`),
        fetch(`${API_BASE}/dashboard/${projectId}`),
        fetch(`${API_BASE}/projects/${projectId}/trust-scores`)
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

      const res = await fetch(`${API_BASE}/projects/${projectId}/documents`, {
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
      const res = await fetch(`${API_BASE}/projects/${projectId}/documents/batch-demo`, {
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
      const res = await fetch(`${API_BASE}/projects/${projectId}/extract`, {
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
      const res = await fetch(`${API_BASE}/assets/${assetId}?actor=ExpertReviewer`, {
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
      const res = await fetch(`${API_BASE}/assets/bulk?actor=ExpertReviewer`, {
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
      const res = await fetch(`${API_BASE}/projects/${projectId}/experts`, {
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

  createAgentPackage: async (projectId: number, name: string, expertModelId: number, version?: string) => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/packages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, expert_model_id: expertModelId, project_id: projectId, governance_version: version || '0.1.0' }),
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

  fetchAuditTrail: async () => {
    try {
      const res = await fetch(`${API_BASE}/audit`);
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
      const res = await fetch(`${API_BASE}/knowledge-assets/${assetId}`, {
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
        fetch(`${API_BASE}/experts/${expertModelId}/conflicts`),
        fetch(`${API_BASE}/experts/${expertModelId}/conflict-score`)
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
      const res = await fetch(`${API_BASE}/experts/${expertModelId}/conflict-scan`, {
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

  fetchRevisionQueue: async (projectId: number) => {
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/revisions`);
      if (!res.ok) throw new Error('Failed to fetch revision queue');
      const data = await res.json();
      set({ revisionQueue: data });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  reviewRevision: async (revisionId: number, action: string, notes: string, projectId: number) => {
    try {
      const res = await fetch(`${API_BASE}/revisions/${revisionId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, reviewer: 'GovernanceOfficer', notes }),
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
      const res = await fetch(`${API_BASE}/conflicts/${relationshipId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, reviewer: 'GovernanceOfficer', notes }),
      });
      if (!res.ok) throw new Error('Failed to record conflict review');
      await get().fetchConflicts(expertModelId);
      get().fetchAuditTrail();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  }
}));
