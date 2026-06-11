'use client';

import React, { useEffect, useState, useRef } from 'react';
import {
  LayoutDashboard,
  FileText,
  Database,
  ShieldCheck,
  History,
  Upload,
  Plus,
  Folder,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowRight,
  HelpCircle,
  Trash2,
  Sparkles,
  Info,
  Clock,
  Lock,
  Boxes,
  FileCheck,
  MessageSquare,
  Send,
  FileCode2,
  Bot,
  AlertTriangle,
  ShieldAlert,
  Scale,
  ExternalLink,
  Inbox
} from 'lucide-react';
import { useAppStore } from '../store';

interface ConsoleCitation {
  asset_id: string;
  name: string;
  content: string;
  source_document: string;
  source_page: number;
  source_section: string;
  source_hash: string;
  asset_status: string;
  approved_by: string;
  approved_at: string;
}

interface ConsoleResult {
  answer: string;
  confidence_score: number;
  coverage_score: number;
  verification_status: 'VERIFIED' | 'PARTIALLY_VERIFIED' | 'INSUFFICIENT_EVIDENCE';
  citations: ConsoleCitation[];
}

interface ConsoleHistoryEntry {
  question: string;
  expert_model: string;
  verification_status: ConsoleResult['verification_status'];
  coverage_score: number;
  confidence_score: number;
  timestamp: string;
}

export default function Home() {
  const {
    projects,
    activeProjectId,
    documents,
    assets,
    experts,
    packages,
    auditEvents,
    stats,
    loading,
    error,
    fetchProjects,
    setActiveProject,
    createProject,
    uploadDocument,
    triggerBatchDemo,
    triggerExtraction,
    updateAssetStatus,
    bulkUpdateAssetStatus,
    createExpertModel,
    createAgentPackage,
    fetchAuditTrail,
    deleteAsset,
    deleteDocumentAssets,
    conflicts,
    conflictScanSummary,
    conflictScanLoading,
    conflictScore,
    fetchConflicts,
    runConflictScan,
    reviewConflict,
    revisionQueue,
    fetchRevisionQueue,
    reviewRevision,
    trustScores,
    benchmarks,
    evaluationRuns,
    evaluationRunning,
    fetchEvaluations,
    createBenchmark,
    deleteBenchmark,
    startEvaluation,
    agentActivity,
    fetchAgentActivity,
    governanceInbox,
    governanceInboxLoading,
    fetchGovernanceInbox,
    reviewClaimVerdict,
    coverageTrend,
    fetchCoverageTrend,
    sourceConnectors,
    ingestionJobs,
    jobFiles,
    fetchConnectors,
    createConnector,
    scanConnector,
    fetchIngestionJobs,
    fetchJobFiles
  } = useAppStore();

  const [activeTab, setActiveTab] = useState<'dashboard' | 'inbox' | 'documents' | 'assets' | 'experts' | 'evaluations' | 'conflicts' | 'revisions' | 'agents' | 'audit' | 'console'>('dashboard');

  useEffect(() => {
    if (activeTab === 'agents') {
      fetchAgentActivity();
    }
  }, [activeTab]);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [projectDesc, setProjectDesc] = useState('');
  const [selectedDocFilterId, setSelectedDocFilterId] = useState<number | null>(null);
  
  // Doc Upload forms
  const [uploadDept, setUploadDept] = useState('Quality Assurance');
  const [uploadOwner, setUploadOwner] = useState('QA Manager');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const firstAssetRef = useRef<HTMLDivElement>(null);

  // Expert model form
  const [selectedAssetIds, setSelectedAssetIds] = useState<number[]>([]);
  const [expertName, setExpertName] = useState('');
  const [expertDesc, setExpertDesc] = useState('');

  // Agent Package form
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [packageName, setPackageName] = useState('');
  const [packageVersion, setPackageVersion] = useState('0.1.0');
  const [packageClearance, setPackageClearance] = useState<'PUBLIC' | 'INTERNAL' | 'RESTRICTED' | 'EXECUTIVE'>('INTERNAL');

  // Console state
  const [selectedExpertId, setSelectedExpertId] = useState<number | null>(null);
  const [consoleQuestion, setConsoleQuestion] = useState('');
  const [consoleLoading, setConsoleLoading] = useState(false);
  const [consoleStep, setConsoleStep] = useState('');
  const [consoleResponse, setConsoleResponse] = useState<ConsoleResult | null>(null);
  const [consoleHistory, setConsoleHistory] = useState<ConsoleHistoryEntry[]>([]);

  // Evaluations workspace state
  const [benchQuestion, setBenchQuestion] = useState('');
  const [benchClaims, setBenchClaims] = useState('');
  const [benchType, setBenchType] = useState<'FACTUAL' | 'PROCEDURAL' | 'POLICY' | 'REFUSAL'>('FACTUAL');
  const [benchSeverity, setBenchSeverity] = useState<'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'>('MEDIUM');
  const [benchCitations, setBenchCitations] = useState(1);
  const [benchCoverage, setBenchCoverage] = useState(0.95);
  const [evalModelId, setEvalModelId] = useState<number | null>(null);
  const [expandedRunId, setExpandedRunId] = useState<number | null>(null);
  // Answer Coverage Governance (MVP 0.9.3)
  const [trustExplainerId, setTrustExplainerId] = useState<number | null>(null);

  useEffect(() => {
    if (activeTab === 'evaluations' && evalModelId !== null) {
      fetchCoverageTrend(evalModelId);
    }
  }, [activeTab, evalModelId, evaluationRuns]);

  useEffect(() => {
    if (activeTab === 'evaluations' && activeProjectId !== null) {
      fetchEvaluations(activeProjectId);
    }
  }, [activeTab, activeProjectId]);

  useEffect(() => {
    if (activeTab === 'evaluations' && experts.length > 0 && evalModelId === null) {
      setEvalModelId(experts[0].id);
    }
  }, [activeTab, experts]);

  // Audit Ledger Explorer state
  const [auditCategory, setAuditCategory] = useState<'ALL' | 'QUERIES' | 'GATEWAY' | 'PUBLICATION' | 'REVISIONS' | 'CONFLICTS' | 'ASSETS' | 'DOCUMENTS'>('ALL');
  const [auditActor, setAuditActor] = useState('');
  const [auditTarget, setAuditTarget] = useState('');
  const [auditSince, setAuditSince] = useState('');
  const [auditUntil, setAuditUntil] = useState('');
  const [expandedEventId, setExpandedEventId] = useState<number | null>(null);

  // Revision Review Workbench state
  const [revisionStatusFilter, setRevisionStatusFilter] = useState<'PENDING' | 'APPROVED' | 'REJECTED' | 'ALL'>('PENDING');
  const [revisionReview, setRevisionReview] = useState<{ id: number; action: 'APPROVE' | 'REJECT' } | null>(null);
  const [revisionReviewReason, setRevisionReviewReason] = useState('');

  useEffect(() => {
    if (activeTab === 'revisions' && activeProjectId !== null) {
      fetchRevisionQueue(activeProjectId);
    }
  }, [activeTab, activeProjectId]);

  // Conflict Review Workbench state
  const [conflictModelId, setConflictModelId] = useState<number | null>(null);
  const [conflictStatusFilter, setConflictStatusFilter] = useState<'ALL' | 'DETECTED' | 'CONFIRMED' | 'DISMISSED'>('ALL');
  const [conflictReview, setConflictReview] = useState<{ id: number; action: 'CONFIRMED' | 'DISMISSED' } | null>(null);
  const [conflictReviewReason, setConflictReviewReason] = useState('');

  useEffect(() => {
    if (activeTab === 'conflicts' && experts.length > 0 && conflictModelId === null) {
      setConflictModelId(experts[0].id);
    }
  }, [activeTab, experts]);

  useEffect(() => {
    if (activeTab === 'conflicts' && conflictModelId !== null) {
      fetchConflicts(conflictModelId);
    }
  }, [activeTab, conflictModelId]);

  // Source Connectors state (MVP 0.10.0)
  const [connectorName, setConnectorName] = useState('');
  const [connectorPath, setConnectorPath] = useState('');
  const [connectorExts, setConnectorExts] = useState('.txt,.md,.pdf,.docx');
  const [expandedJobId, setExpandedJobId] = useState<number | null>(null);

  useEffect(() => {
    if (activeTab === 'documents' && activeProjectId !== null) {
      fetchConnectors(activeProjectId);
      fetchIngestionJobs(activeProjectId);
    }
  }, [activeTab, activeProjectId]);

  // Live progress: poll while any job is pending/running on the documents tab.
  useEffect(() => {
    if (activeTab !== 'documents' || activeProjectId === null) return;
    const active = ingestionJobs.some(j => j.status === 'PENDING' || j.status === 'RUNNING');
    if (!active) return;
    const timer = setInterval(() => {
      fetchIngestionJobs(activeProjectId);
    }, 2500);
    return () => clearInterval(timer);
  }, [activeTab, activeProjectId, ingestionJobs]);

  // A finished scan changes documents/assets/inbox - refresh project data once.
  const prevJobsRef = useRef<string>('');
  useEffect(() => {
    const signature = ingestionJobs.map(j => `${j.id}:${j.status}`).join('|');
    if (prevJobsRef.current && signature !== prevJobsRef.current &&
        activeProjectId !== null && !ingestionJobs.some(j => j.status === 'PENDING' || j.status === 'RUNNING')) {
      useAppStore.getState().fetchProjectData(activeProjectId);
      fetchGovernanceInbox(activeProjectId);
    }
    prevJobsRef.current = signature;
  }, [ingestionJobs]);

  // Governance Inbox & Readiness Console state (MVP 0.9.1)
  const [inboxModelFilter, setInboxModelFilter] = useState<number | null>(null);
  const [highlightRelationshipId, setHighlightRelationshipId] = useState<number | null>(null);
  const [highlightRevisionId, setHighlightRevisionId] = useState<number | null>(null);
  // Persisted Verification Verdicts state (MVP 0.9.2)
  const [highlightResultId, setHighlightResultId] = useState<number | null>(null);
  const [verdictReview, setVerdictReview] = useState<number | null>(null);
  const [verdictReviewComment, setVerdictReviewComment] = useState('');
  const [reviewedVerdictIds, setReviewedVerdictIds] = useState<Set<number>>(new Set());

  // Keep the inbox (and its nav badge) fresh: on workspace change and on tab entry.
  useEffect(() => {
    if (activeProjectId !== null) {
      fetchGovernanceInbox(activeProjectId);
    }
  }, [activeProjectId]);

  useEffect(() => {
    if (activeTab === 'inbox' && activeProjectId !== null) {
      fetchGovernanceInbox(activeProjectId);
    }
  }, [activeTab, activeProjectId]);

  // A deep-link highlight only makes sense on the tab it belongs to.
  useEffect(() => {
    if (activeTab !== 'conflicts' && highlightRelationshipId !== null) setHighlightRelationshipId(null);
    if (activeTab !== 'revisions' && highlightRevisionId !== null) setHighlightRevisionId(null);
    if (activeTab !== 'evaluations' && highlightResultId !== null) setHighlightResultId(null);
  }, [activeTab]);

  // Inbox deep-link navigation: parse the item's deep_link and set workbench
  // state directly — the inbox is a control tower, the decision happens in
  // the specialized workbench.
  const openDeepLink = (link: string) => {
    const params = new URLSearchParams(link.split('?')[1] || '');
    const tab = params.get('tab');
    const expert = params.get('expert');
    const relationship = params.get('relationship');
    const revision = params.get('revision');
    if (tab === 'conflicts') {
      if (expert) setConflictModelId(Number(expert));
      setConflictStatusFilter('ALL');
      setHighlightRelationshipId(relationship ? Number(relationship) : null);
      setActiveTab('conflicts');
    } else if (tab === 'revisions') {
      setRevisionStatusFilter('ALL');
      setHighlightRevisionId(revision ? Number(revision) : null);
      setActiveTab('revisions');
    } else if (tab === 'evaluations') {
      const run = params.get('run');
      const result = params.get('result');
      if (run) setExpandedRunId(Number(run));
      setHighlightResultId(result ? Number(result) : null);
      setActiveTab('evaluations');
    } else if (tab === 'experts') {
      setActiveTab('experts');
    }
  };

  // Scroll the deep-linked card into view once its workbench has rendered.
  useEffect(() => {
    const targetId =
      activeTab === 'conflicts' && highlightRelationshipId !== null ? `conflict-${highlightRelationshipId}` :
      activeTab === 'revisions' && highlightRevisionId !== null ? `revision-${highlightRevisionId}` :
      activeTab === 'evaluations' && highlightResultId !== null ? `eval-result-${highlightResultId}` : null;
    if (!targetId) return;
    const timer = setTimeout(() => {
      document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 250);
    return () => clearTimeout(timer);
  }, [activeTab, highlightRelationshipId, highlightRevisionId, highlightResultId, conflicts, revisionQueue, evaluationRuns]);

  // Pre-fill model selection when entering console
  useEffect(() => {
    if (activeTab === 'console' && experts.length > 0 && selectedExpertId === null) {
      setSelectedExpertId(experts[0].id);
    }
  }, [activeTab, experts]);

  const handleConsoleQuery = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedExpertId || !consoleQuestion.trim()) return;

    setConsoleResponse(null);
    setConsoleLoading(true);
    
    const steps = [
      "Initializing query context on selected Expert Model...",
      "Retrieving matching approved knowledge assets in scope...",
      "Stage 1 Validation: Verifying status, source hashes & provenance...",
      "Stage 2 Verification: Checking claim coverage against source context..."
    ];

    let currentStepIdx = 0;
    setConsoleStep(steps[0]);

    const interval = setInterval(() => {
      currentStepIdx++;
      if (currentStepIdx < steps.length) {
        setConsoleStep(steps[currentStepIdx]);
      } else {
        clearInterval(interval);
        
        // Mocking logic
        const q = consoleQuestion.toLowerCase();
        let mockResult: ConsoleResult = {
          answer: "INSUFFICIENT EVIDENCE",
          confidence_score: 0.38,
          coverage_score: 0.42,
          verification_status: "INSUFFICIENT_EVIDENCE",
          citations: []
        };

        if (q.includes("deviation") || q.includes("sla threshold") || q.includes("logging")) {
          mockResult = {
            answer: "All critical deviations must be logged in the quality management system within 24 hours of identification, while major deviations must be logged within 72 hours. Minor deviations should be recorded within 5 business days.",
            confidence_score: 0.96,
            coverage_score: 1.00,
            verification_status: "VERIFIED",
            citations: [
              {
                asset_id: "asset_018b321a-4d2c-7431-a8e1-5bc4123490aa",
                name: "Deviation Class Policy",
                content: "All critical deviations must be logged in the quality management system within 24 hours.",
                source_document: "SOP-001_Deviation_Management.txt",
                source_page: 2,
                source_section: "4.1 Classification of Deviations",
                source_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                asset_status: "APPROVED",
                approved_by: "operator_admin_02",
                approved_at: "2026-06-10T00:30:00Z"
              }
            ]
          };
        } else if (q.includes("refund") || q.includes("delivery") || q.includes("voucher")) {
          mockResult = {
            answer: "For deliveries exceeding the SLA deadline by more than 48 hours, customers are eligible for a 15% refund on the monthly service charge. Furthermore, customer support usually attempts to offer a complimentary voucher for goodwill, though voucher rules are unverified.",
            confidence_score: 0.88,
            coverage_score: 0.92,
            verification_status: "PARTIALLY_VERIFIED",
            citations: [
              {
                asset_id: "asset_018b321a-4d2c-7431-a8e5-5bc4123490bc",
                name: "Late Delivery Refund Policy",
                content: "For deliveries exceeding the SLA deadline by more than 48 hours, customers are eligible for a 15% refund.",
                source_document: "SOP-002_SLA_Refund_Policy.txt",
                source_page: 1,
                source_section: "2.1 SLA Violations & Credits",
                source_hash: "e4392a8321a4f00d892d131498b2c45eef723d91ca21377f2bc21a4f89d31c4b",
                asset_status: "APPROVED",
                approved_by: "operator_admin_02",
                approved_at: "2026-06-10T00:31:12Z"
              }
            ]
          };
        }

        setConsoleResponse(mockResult);
        setConsoleHistory(prev => [
          {
            question: consoleQuestion,
            expert_model: experts.find(e => e.id === selectedExpertId)?.name || 'Unknown Expert',
            verification_status: mockResult.verification_status,
            coverage_score: mockResult.coverage_score,
            confidence_score: mockResult.confidence_score,
            timestamp: new Date().toISOString()
          },
          ...prev
        ]);
        setConsoleLoading(false);
      }
    }, 600);
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  // Hydrate governance deep-link state (?tab=conflicts&expert=11&relationship=42)
  // from the URL once on load. The assets tab stays path-based (/knowledge-assets).
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    const urlTabs = ['inbox', 'documents', 'experts', 'evaluations', 'conflicts', 'revisions', 'agents', 'audit', 'console'] as const;
    if (tab && (urlTabs as readonly string[]).includes(tab)) {
      const expert = params.get('expert');
      const relationship = params.get('relationship');
      const revision = params.get('revision');
      if (tab === 'conflicts' && expert) setConflictModelId(Number(expert));
      if (tab === 'conflicts' && relationship) {
        setHighlightRelationshipId(Number(relationship));
        setConflictStatusFilter('ALL');
      }
      if (tab === 'revisions' && revision) {
        setHighlightRevisionId(Number(revision));
        setRevisionStatusFilter('ALL');
      }
      if (tab === 'inbox' && expert) setInboxModelFilter(Number(expert));
      if (tab === 'evaluations') {
        const run = params.get('run');
        const result = params.get('result');
        if (run) setExpandedRunId(Number(run));
        if (result) setHighlightResultId(Number(result));
      }
      setActiveTab(tab as typeof urlTabs[number]);
    }
  }, []);

  // Parse path and query parameters for deep linking
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const pathname = window.location.pathname;
      const searchParams = new URLSearchParams(window.location.search);
      const documentIdParam = searchParams.get('documentId');
      const documentParam = searchParams.get('document');
      
      if (pathname.includes('/knowledge-assets')) {
        setActiveTab('assets');
      }
      
      if (documentIdParam) {
        setSelectedDocFilterId(Number(documentIdParam));
      } else if (documentParam && documents.length > 0) {
        const doc = documents.find(d => d.filename === documentParam);
        if (doc) {
          setSelectedDocFilterId(doc.id);
        }
      }
    }
  }, [documents]);

  // Sync state back to URL for clean user navigation
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const currentPath = window.location.pathname;
      const currentSearch = window.location.search;
      
      let newPath = '/';
      let newSearch = '';

      if (activeTab === 'assets') {
        newPath = '/knowledge-assets';
        if (selectedDocFilterId) {
          newSearch = `?documentId=${selectedDocFilterId}`;
        }
      } else if (activeTab !== 'dashboard') {
        // Governance workflows are URL-addressable: tab plus the active
        // workbench selection round-trip through the address bar.
        const params = new URLSearchParams();
        params.set('tab', activeTab);
        if (activeTab === 'conflicts' && conflictModelId !== null) params.set('expert', String(conflictModelId));
        if (activeTab === 'conflicts' && highlightRelationshipId !== null) params.set('relationship', String(highlightRelationshipId));
        if (activeTab === 'revisions' && highlightRevisionId !== null) params.set('revision', String(highlightRevisionId));
        if (activeTab === 'inbox' && inboxModelFilter !== null) params.set('expert', String(inboxModelFilter));
        if (activeTab === 'evaluations' && expandedRunId !== null) params.set('run', String(expandedRunId));
        if (activeTab === 'evaluations' && highlightResultId !== null) params.set('result', String(highlightResultId));
        newSearch = `?${params.toString()}`;
      }

      const targetUrl = newPath + newSearch;
      const currentUrl = currentPath + currentSearch;

      if (currentUrl !== targetUrl) {
        window.history.pushState(null, '', targetUrl);
      }
    }
  }, [activeTab, selectedDocFilterId, conflictModelId, highlightRelationshipId, highlightRevisionId, inboxModelFilter, expandedRunId, highlightResultId]);

  // Listen to browser back/forward buttons
  useEffect(() => {
    const handlePopState = () => {
      const pathname = window.location.pathname;
      const searchParams = new URLSearchParams(window.location.search);
      const documentIdParam = searchParams.get('documentId');
      const documentParam = searchParams.get('document');
      const tabParam = searchParams.get('tab');
      const urlTabs = ['inbox', 'documents', 'experts', 'evaluations', 'conflicts', 'revisions', 'agents', 'audit', 'console'];

      if (pathname.includes('/knowledge-assets')) {
        setActiveTab('assets');
      } else if (tabParam && urlTabs.includes(tabParam)) {
        setActiveTab(tabParam as 'inbox' | 'documents' | 'experts' | 'evaluations' | 'conflicts' | 'revisions' | 'agents' | 'audit' | 'console');
      } else {
        setActiveTab('dashboard');
      }
      
      if (documentIdParam) {
        setSelectedDocFilterId(Number(documentIdParam));
      } else if (documentParam) {
        const doc = documents.find(d => d.filename === documentParam);
        if (doc) {
          setSelectedDocFilterId(doc.id);
        } else {
          setSelectedDocFilterId(null);
        }
      } else {
        setSelectedDocFilterId(null);
      }
    };
    
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [documents]);

  // Scroll to first matching highlighted asset
  useEffect(() => {
    if (activeTab === 'assets' && selectedDocFilterId && firstAssetRef.current) {
      const timer = setTimeout(() => {
        firstAssetRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [activeTab, selectedDocFilterId, assets]);

  // Keyboard review shortcuts (A=Approve, R=Reject) for active filtered document candidates
  useEffect(() => {
    const handleKeyDown = async (e: KeyboardEvent) => {
      if (
        document.activeElement?.tagName === 'INPUT' ||
        document.activeElement?.tagName === 'TEXTAREA'
      ) {
        return;
      }

      if (activeTab === 'assets' && selectedDocFilterId) {
        const pendingAsset = assets.find(
          a => a.document_id === selectedDocFilterId && a.status === 'CANDIDATE'
        );

        if (pendingAsset) {
          if (e.key === 'a' || e.key === 'A') {
            await updateAssetStatus(pendingAsset.id, 'APPROVED');
          } else if (e.key === 'r' || e.key === 'R') {
            await updateAssetStatus(pendingAsset.id, 'ARCHIVED');
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, selectedDocFilterId, assets]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim()) return;
    await createProject(projectName, projectDesc);
    setProjectName('');
    setProjectDesc('');
    setShowNewProjectModal(false);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!activeProjectId || !e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    await uploadDocument(activeProjectId, file, uploadDept, uploadOwner);
  };

  const handleBuildExpertModel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProjectId || !expertName.trim() || selectedAssetIds.length === 0) return;
    await createExpertModel(activeProjectId, expertName, expertDesc, selectedAssetIds);
    setExpertName('');
    setExpertDesc('');
    setSelectedAssetIds([]);
  };

  const handleBuildAgentPackage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProjectId || !packageName.trim() || !selectedModelId) return;
    await createAgentPackage(activeProjectId, packageName, selectedModelId, packageVersion, packageClearance);
    setPackageName('');
    setSelectedModelId(null);
  };

  const activeProject = projects.find(p => p.id === activeProjectId);

  // Computed approved assets
  const approvedAssets = assets.filter(a => a.status === 'APPROVED');

  return (
    <div className="flex h-screen bg-[#070b12] text-slate-100 overflow-hidden font-sans">
      
      {/* SIDEBAR NAVIGATION */}
      <aside className="w-64 border-r border-slate-900 bg-[#090d16]/95 flex flex-col justify-between z-10">
        <div>
          {/* LOGO */}
          <div className="p-6 border-b border-slate-900 flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-emerald-500 flex items-center justify-center shadow-lg shadow-cyan-500/10">
              <Boxes className="w-5 h-5 text-[#070b12]" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-wider text-gradient-cyan">EXPERTMACHINA</span>
              <span className="text-[10px] block text-slate-500 tracking-widest font-mono">GOVERNANCE & RAG v0.1</span>
            </div>
          </div>

          {/* PROJECT SELECTOR */}
          <div className="p-4 border-b border-slate-900 bg-slate-950/40">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-slate-400 tracking-wider flex items-center gap-1.5">
                <Folder className="w-3.5 h-3.5 text-cyan-400" /> WORKSPACE
              </label>
              <button 
                onClick={() => setShowNewProjectModal(true)}
                className="text-[10px] text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1 bg-cyan-950/30 px-1.5 py-0.5 rounded border border-cyan-900/50"
              >
                <Plus className="w-2.5 h-2.5" /> NEW
              </button>
            </div>
            {projects.length === 0 ? (
              <span className="text-xs text-slate-500 italic block">No workspaces created</span>
            ) : (
              <select 
                value={activeProjectId || ''} 
                onChange={(e) => setActiveProject(Number(e.target.value))}
                className="w-full bg-[#0d1424] border border-slate-800 rounded px-2.5 py-1.5 text-sm text-slate-200 outline-none focus:border-cyan-500 transition-colors"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            )}
          </div>

          {/* NAV ITEMS */}
          <nav className="p-4 space-y-1.5">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'dashboard'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Executive Dashboard</span>
            </button>

            <button
              onClick={() => setActiveTab('inbox')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'inbox'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <Inbox className="w-4 h-4" />
              <span>Governance Inbox</span>
              {governanceInbox && governanceInbox.summary.needs_review > 0 && (
                <span className="ml-auto bg-rose-950/40 text-[10px] text-rose-400 font-mono px-2 py-0.5 rounded-full border border-rose-900/40">
                  {governanceInbox.summary.needs_review}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('documents')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'documents'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Document Inventory</span>
              {ingestionJobs.some(j => j.status === 'PENDING' || j.status === 'RUNNING') ? (
                <span className="ml-auto bg-cyan-950/40 text-[10px] text-cyan-400 font-mono px-2 py-0.5 rounded-full border border-cyan-900/40 animate-pulse">
                  scanning
                </span>
              ) : documents.length > 0 && (
                <span className="ml-auto bg-slate-800 text-[10px] text-slate-300 font-mono px-2 py-0.5 rounded-full">
                  {documents.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('assets')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'assets'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <Database className="w-4 h-4" />
              <span>Knowledge Assets</span>
              {assets.length > 0 && (
                <span className="ml-auto bg-slate-850 text-[10px] text-cyan-400 font-mono px-2 py-0.5 rounded-full border border-cyan-950">
                  {assets.filter(a => a.status === 'CANDIDATE').length} new
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('experts')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'experts'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Experts & Packages</span>
            </button>

            <button
              onClick={() => setActiveTab('evaluations')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'evaluations'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <FileCode2 className="w-4 h-4" />
              <span>Evaluations</span>
              {evaluationRunning && (
                <span className="ml-auto bg-cyan-950/40 text-[10px] text-cyan-400 font-mono px-2 py-0.5 rounded-full border border-cyan-900/40 animate-pulse">
                  running
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('conflicts')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'conflicts'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              <span>Knowledge Conflicts</span>
              {conflicts.filter(c => c.status === 'DETECTED' && c.relationship_type === 'CONFLICTS_WITH').length > 0 && (
                <span className="ml-auto bg-rose-950/40 text-[10px] text-rose-400 font-mono px-2 py-0.5 rounded-full border border-rose-900/40">
                  {conflicts.filter(c => c.status === 'DETECTED' && c.relationship_type === 'CONFLICTS_WITH').length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('revisions')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'revisions'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <FileCheck className="w-4 h-4" />
              <span>Revision Reviews</span>
              {revisionQueue.filter(r => r.revision.status === 'CANDIDATE').length > 0 && (
                <span className="ml-auto bg-yellow-950/40 text-[10px] text-yellow-400 font-mono px-2 py-0.5 rounded-full border border-yellow-900/40">
                  {revisionQueue.filter(r => r.revision.status === 'CANDIDATE').length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('console')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'console'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              <span>Ask Expert Console</span>
            </button>

            <button
              onClick={() => setActiveTab('agents')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'agents'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <Bot className="w-4 h-4" />
              <span>Agent Center</span>
              {agentActivity && agentActivity.agents.length > 0 && (
                <span className="ml-auto bg-purple-950/40 text-[10px] text-purple-400 font-mono px-2 py-0.5 rounded-full border border-purple-900/40">
                  {agentActivity.agents.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('audit')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'audit'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <History className="w-4 h-4" />
              <span>Audit Ledger</span>
            </button>
          </nav>
        </div>

        {/* PROFILE BLOCK */}
        <div className="p-4 border-t border-slate-900 bg-slate-950/20 text-xs text-slate-500 space-y-2">
          <div className="flex items-center gap-2 text-slate-400 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 glow-dot"></span>
            <span>Local Node online</span>
          </div>
          <div className="text-[10px] text-slate-600 font-mono uppercase">
            Active Workspace ID: {activeProjectId || 'None'}
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        
        {/* HEADER BAR */}
        <header className="h-16 border-b border-slate-900 bg-[#090d16]/50 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-20">
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-100 flex items-center gap-2">
              {activeProject ? activeProject.name : 'Select a Workspace'}
              {activeProject && (
                <span className="text-[10px] font-mono tracking-widest px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-400 border border-cyan-900/40 uppercase">
                  {activeProject.status}
                </span>
              )}
            </h1>
          </div>

          <div className="flex items-center space-x-4">
            {error && (
              <div className="bg-rose-950/40 border border-rose-900/50 rounded-lg px-3 py-1 flex items-center gap-2 text-xs text-rose-300">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Error: {error}</span>
              </div>
            )}
            {loading && (
              <div className="text-xs text-slate-400 flex items-center gap-2 font-mono">
                <div className="w-3 h-3 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
                <span>processing engine...</span>
              </div>
            )}
          </div>
        </header>

        {/* WORKSPACE DETAILED VIEWS */}
        <div className="p-8 max-w-7xl w-full mx-auto space-y-6">

          {/* SELECT PROJECT PLACEHOLDER */}
          {!activeProjectId && (
            <div className="text-center py-20 glass-panel rounded-2xl max-w-lg mx-auto space-y-4">
              <Boxes className="w-12 h-12 text-slate-700 mx-auto" />
              <h3 className="font-bold text-lg text-slate-300">No active workspace</h3>
              <p className="text-sm text-slate-500 px-8">
                Please create a workspace project or select an existing project from the sidebar to inspect documents and compile digital expertise.
              </p>
              <button 
                onClick={() => setShowNewProjectModal(true)}
                className="bg-gradient-to-r from-cyan-500 to-emerald-500 text-slate-950 font-semibold px-4 py-2 rounded-lg text-xs tracking-wider uppercase hover:shadow-cyan-500/10 transition-shadow"
              >
                Create Workspace
              </button>
            </div>
          )}

          {activeProjectId && (
            <>
              {/* TAB 1: EXECUTIVE DASHBOARD */}
              {activeTab === 'dashboard' && (
                <div className="space-y-6">
                  {/* OVERVIEW STATS CARDS */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
                    <div className="glass-panel p-5 rounded-xl flex flex-col justify-between space-y-2">
                      <span className="text-xs text-slate-400 tracking-wider">DOCUMENTS INGESTED</span>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-extrabold text-slate-100">{stats?.documents_uploaded || 0}</span>
                        <span className="text-[10px] text-slate-500 font-mono">({stats?.documents_parsed || 0} PARSED)</span>
                      </div>
                      <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                        <div 
                          className="bg-cyan-500 h-full transition-all duration-500" 
                          style={{ width: `${stats?.documents_uploaded ? (stats.documents_parsed / stats.documents_uploaded) * 100 : 0}%` }}
                        ></div>
                      </div>
                    </div>

                    <div className="glass-panel p-5 rounded-xl flex flex-col justify-between space-y-2">
                      <span className="text-xs text-slate-400 tracking-wider">KNOWLEDGE ASSETS</span>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-extrabold text-gradient-cyan">{stats?.assets_extracted || 0}</span>
                        <span className="text-[10px] text-emerald-400 font-mono">({stats?.assets_status_counts?.APPROVED || 0} GOVERNED)</span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">Mapped to Qdrant local store</span>
                    </div>

                    <div className="glass-panel p-5 rounded-xl flex flex-col justify-between space-y-2">
                      <span className="text-xs text-slate-400 tracking-wider">EXPERT MODELS</span>
                      <span className="text-3xl font-extrabold text-slate-100">{stats?.expert_models || 0}</span>
                      <span className="text-[10px] text-slate-500 font-mono">Active knowledge vectors</span>
                    </div>

                    <div className="glass-panel-glow p-5 rounded-xl flex flex-col justify-between space-y-2">
                      <span className="text-xs text-slate-400 tracking-wider">DEPLOYABLE PACKAGES</span>
                      <span className="text-3xl font-extrabold text-gradient-rainbow">{stats?.agent_packages || 0}</span>
                      <span className="text-[10px] text-cyan-400 font-mono">Immutable assets ready</span>
                    </div>
                  </div>

                  {/* READINESS SCORING METER & STATE DISTRIBUTION */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* READINESS GAUGE */}
                    <div className="glass-panel p-6 rounded-xl flex flex-col justify-between space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold text-slate-300">Transformation Readiness</h4>
                        <Info className="w-4 h-4 text-slate-500" />
                      </div>
                      <div className="relative flex items-center justify-center py-4">
                        <div className="text-center">
                          <span className="text-5xl font-black text-gradient-emerald">{stats?.readiness_score || 0}%</span>
                          <span className="block text-[10px] text-slate-400 font-mono uppercase mt-1">Overall Quality Score</span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-400 text-center leading-relaxed">
                        Readiness calculation computes coverage depth, freshness, verification, and conflict scores of all extracted knowledge assets.
                      </p>
                    </div>

                    {/* GOVERNANCE DISTRIBUTION */}
                    <div className="glass-panel p-6 rounded-xl flex flex-col justify-between col-span-2 space-y-4">
                      <h4 className="text-sm font-semibold text-slate-300">Governance Pipeline Distribution</h4>
                      <div className="grid grid-cols-4 gap-4 py-3">
                        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-center">
                          <span className="text-xs text-slate-400 block font-mono">CANDIDATE</span>
                          <span className="text-2xl font-bold text-slate-300">{stats?.assets_status_counts?.CANDIDATE || 0}</span>
                        </div>
                        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-center">
                          <span className="text-xs text-slate-400 block font-mono">REVIEWED</span>
                          <span className="text-2xl font-bold text-yellow-400">{stats?.assets_status_counts?.REVIEWED || 0}</span>
                        </div>
                        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-center">
                          <span className="text-xs text-slate-400 block font-mono">APPROVED</span>
                          <span className="text-2xl font-bold text-emerald-400">{stats?.assets_status_counts?.APPROVED || 0}</span>
                        </div>
                        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-center">
                          <span className="text-xs text-slate-400 block font-mono">ARCHIVED</span>
                          <span className="text-2xl font-bold text-slate-500">{stats?.assets_status_counts?.ARCHIVED || 0}</span>
                        </div>
                      </div>
                      <div className="h-4 bg-slate-950 rounded-full overflow-hidden flex">
                        {stats?.assets_extracted ? (
                          <>
                            <div className="bg-slate-400 h-full" style={{ width: `${((stats.assets_status_counts.CANDIDATE) / stats.assets_extracted) * 100}%` }}></div>
                            <div className="bg-yellow-500 h-full" style={{ width: `${((stats.assets_status_counts.REVIEWED) / stats.assets_extracted) * 100}%` }}></div>
                            <div className="bg-emerald-500 h-full" style={{ width: `${((stats.assets_status_counts.APPROVED) / stats.assets_extracted) * 100}%` }}></div>
                            <div className="bg-slate-700 h-full" style={{ width: `${((stats.assets_status_counts.ARCHIVED) / stats.assets_extracted) * 100}%` }}></div>
                          </>
                        ) : (
                          <div className="bg-slate-900 w-full h-full"></div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* DEMO TRANSFORMATION ACTION CARD */}
                  {documents.length === 0 && (
                    <div className="glass-panel p-8 rounded-xl border border-cyan-900/30 flex flex-col md:flex-row items-center justify-between gap-6 bg-gradient-to-r from-slate-950 via-slate-900/40 to-slate-950">
                      <div className="space-y-2 text-center md:text-left">
                        <h3 className="font-bold text-slate-200 flex items-center justify-center md:justify-start gap-2">
                          <Sparkles className="w-4 h-4 text-cyan-400 animate-pulse" />
                          Transform Company Knowledge Instantly
                        </h3>
                        <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
                          Test the entire operational pipeline with a single click. Load our standard pre-bundled clinical trial protocols and SLA policies, let Docling/LlamaIndex chunk them, vector-store them in local Qdrant, and extract governed knowledge assets automatically.
                        </p>
                      </div>
                      <button
                        onClick={async () => {
                          if (activeProjectId) {
                            await triggerBatchDemo(activeProjectId);
                            await triggerExtraction(activeProjectId);
                          }
                        }}
                        className="w-full md:w-auto bg-gradient-to-r from-cyan-500 to-emerald-500 text-slate-950 font-bold px-5 py-3 rounded-lg text-xs tracking-wider uppercase flex items-center justify-center gap-2 shrink-0 hover:opacity-90 transition-opacity"
                      >
                        Run Batch Demo <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: DOCUMENT INVENTORY */}
              {activeTab === 'documents' && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  
                  {/* UPLOADER PANEL */}
                  <div className="glass-panel p-6 rounded-xl space-y-5 h-fit">
                    <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3">
                      Ingest New Document
                    </h3>
                    
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Department</label>
                        <input 
                          type="text" 
                          value={uploadDept} 
                          onChange={(e) => setUploadDept(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200" 
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Document Owner</label>
                        <input 
                          type="text" 
                          value={uploadOwner} 
                          onChange={(e) => setUploadOwner(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200" 
                        />
                      </div>
                      
                      {/* DRAG DROP */}
                      <div 
                        onClick={() => fileInputRef.current?.click()}
                        className="border-2 border-dashed border-slate-800 hover:border-cyan-500/50 hover:bg-cyan-950/5 rounded-xl p-8 text-center cursor-pointer transition-all duration-300"
                      >
                        <Upload className="w-8 h-8 text-slate-500 mx-auto mb-3" />
                        <span className="text-xs font-semibold text-slate-300 block mb-1">Click to browse file</span>
                        <span className="text-[10px] text-slate-500 block">PDF, TXT, DOCX formats supported</span>
                        <input 
                          type="file" 
                          ref={fileInputRef} 
                          onChange={handleFileUpload} 
                          className="hidden" 
                        />
                      </div>
                    </div>

                    <div className="border-t border-slate-900 pt-4">
                      <button
                        onClick={async () => activeProjectId && await triggerBatchDemo(activeProjectId)}
                        className="w-full py-2 bg-slate-900 hover:bg-slate-850 text-slate-300 rounded text-xs font-semibold border border-slate-800 flex items-center justify-center gap-2 transition-colors"
                      >
                        <FileCheck className="w-3.5 h-3.5" />
                        Quick-Load 3 Standard SOPs
                      </button>
                    </div>
                  </div>

                  {/* DOCUMENT LIST */}
                  <div className="col-span-2 glass-panel p-6 rounded-xl space-y-4">
                    <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center justify-between">
                      <span>Document Inventory Inventory ({documents.length})</span>
                      {documents.length > 0 && (
                        <button
                          onClick={async () => activeProjectId && await triggerExtraction(activeProjectId)}
                          className="text-[10px] bg-cyan-950 hover:bg-cyan-900 text-cyan-400 border border-cyan-800/50 rounded px-2.5 py-1 font-mono uppercase tracking-wider flex items-center gap-1.5 transition-colors"
                        >
                          <Sparkles className="w-3.5 h-3.5 animate-pulse" /> Extract Assets
                        </button>
                      )}
                    </h3>

                    {documents.length === 0 ? (
                      <div className="text-center py-20 text-slate-500 italic text-xs">
                        No documents uploaded yet. Use the upload panel to begin ingestion.
                      </div>
                    ) : (
                      <div className="space-y-3.5 max-h-[500px] overflow-y-auto pr-2">
                        {documents.map((doc) => (
                          <div 
                            key={doc.id} 
                            onClick={() => {
                              setSelectedDocFilterId(doc.id);
                              setActiveTab('assets');
                              window.history.pushState(null, '', `/knowledge-assets?documentId=${doc.id}`);
                            }}
                            className="bg-slate-950/60 border border-slate-900 rounded-lg p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 hover:border-cyan-500/30 hover:bg-slate-900/50 cursor-pointer transition-all duration-300"
                          >
                            <div className="space-y-1">
                              <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                                <FileText className="w-3.5 h-3.5 text-cyan-500" />
                                {doc.filename}
                              </span>
                              <div className="flex flex-wrap gap-2 text-[10px] text-slate-500 font-mono">
                                <span>Dept: {doc.department}</span>
                                <span>•</span>
                                <span>Owner: {doc.owner}</span>
                                <span>•</span>
                                <span>Type: {doc.file_type}</span>
                                <span>•</span>
                                <span>Version: {doc.version}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-4 self-end md:self-center">
                              {/* Readiness markers */}
                              <div className="flex items-center gap-1.5 font-mono text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                                <span className="text-slate-400">LlamaIndex Vector Index:</span>
                                <span className="text-emerald-400">STORED</span>
                              </div>
                              
                              {doc.status === 'INGESTED' ? (
                                <span className="flex items-center gap-1.5 text-xs text-yellow-500 font-semibold bg-yellow-950/20 border border-yellow-900/30 px-2.5 py-0.5 rounded-full">
                                  <Clock className="w-3.5 h-3.5" /> INGESTED
                                </span>
                              ) : doc.status === 'PARSED' ? (
                                <span className="flex items-center gap-1.5 text-xs text-yellow-400 font-semibold bg-yellow-950/30 border border-yellow-900/40 px-2.5 py-0.5 rounded-full">
                                  <CheckCircle2 className="w-3.5 h-3.5" /> PARSED
                                </span>
                              ) : doc.status === 'ASSETS_EXTRACTED' ? (
                                <span className="flex items-center gap-1.5 text-xs text-blue-400 font-semibold bg-blue-950/30 border border-blue-900/40 px-2.5 py-0.5 rounded-full">
                                  <FileText className="w-3.5 h-3.5" /> EXTRACTED
                                </span>
                              ) : doc.status === 'PARTIALLY_APPROVED' ? (
                                <span className="flex items-center gap-1.5 text-xs text-purple-400 font-semibold bg-purple-950/30 border border-purple-900/40 px-2.5 py-0.5 rounded-full">
                                  <Sparkles className="w-3.5 h-3.5 animate-pulse" /> PARTIAL
                                </span>
                              ) : doc.status === 'APPROVED' ? (
                                <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold bg-emerald-950/30 border border-emerald-900/40 px-2.5 py-0.5 rounded-full">
                                  <CheckCircle2 className="w-3.5 h-3.5" /> APPROVED
                                </span>
                              ) : doc.status === 'FAILED' ? (
                                <span className="flex items-center gap-1.5 text-xs text-rose-400 font-semibold bg-rose-950/30 border border-rose-900/40 px-2.5 py-0.5 rounded-full">
                                  <XCircle className="w-3.5 h-3.5" /> FAILED
                                </span>
                              ) : (
                                <span className="flex items-center gap-1.5 text-xs text-slate-400 font-semibold bg-slate-900 border border-slate-800 px-2.5 py-0.5 rounded-full">
                                  {doc.status}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 3: KNOWLEDGE ASSETS */}
              {activeTab === 'assets' && (
                <div className="space-y-6">
                  <div className="flex justify-between items-center border-b border-slate-900 pb-3">
                    <div className="flex items-center gap-3">
                      <h3 className="font-bold text-sm text-slate-200 tracking-wide">
                        Knowledge Transformation Review Queue
                        {selectedDocFilterId ? (
                          <span className="text-cyan-400 ml-2 font-mono">
                            (Filtered by Document: #{selectedDocFilterId})
                          </span>
                        ) : (
                          ` (${assets.length} items)`
                        )}
                      </h3>
                      {selectedDocFilterId && (
                        <button
                          onClick={() => {
                            setSelectedDocFilterId(null);
                            window.history.pushState(null, '', '/knowledge-assets');
                          }}
                          className="text-[10px] text-cyan-400 hover:text-cyan-300 font-mono bg-cyan-950/30 px-2 py-0.5 rounded border border-cyan-900/50 transition-colors"
                        >
                          Clear Filter
                        </button>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      {assets.length > 0 && (
                        <button
                          onClick={async () => activeProjectId && await triggerExtraction(activeProjectId)}
                          className="bg-slate-900 hover:bg-slate-850 text-slate-300 border border-slate-800 rounded px-2.5 py-1 text-xs font-mono uppercase flex items-center gap-1.5 transition-colors"
                        >
                          Re-run Extraction
                        </button>
                      )}
                    </div>
                  </div>

                  {assets.length === 0 ? (
                    <div className="text-center py-20 glass-panel rounded-xl text-slate-500 italic text-xs">
                      No knowledge assets generated yet. Parse document files first and run the extraction trigger.
                    </div>
                  ) : (
                    <div className="space-y-8">
                      {(() => {
                        const grouped: { [key: string]: { docId: number | null; docName: string; items: typeof assets } } = {};
                        assets.forEach(asset => {
                          const doc = documents.find(d => d.id === asset.document_id);
                          const docName = doc ? doc.filename : "Manual / Unknown Source";
                          const key = doc ? `doc_${doc.id}` : "manual";
                          if (!grouped[key]) {
                            grouped[key] = { docId: asset.document_id, docName, items: [] };
                          }
                          grouped[key].items.push(asset);
                        });

                        let entries = Object.entries(grouped);
                        if (selectedDocFilterId !== null) {
                          entries = entries.filter(([, group]) => group.docId === selectedDocFilterId);
                        }

                        if (entries.length === 0 && selectedDocFilterId !== null) {
                          return (
                            <div className="text-center py-20 glass-panel rounded-xl space-y-4">
                              <AlertCircle className="w-12 h-12 text-yellow-500 mx-auto" />
                              <h3 className="font-bold text-sm text-slate-350">No assets extracted from this document yet.</h3>
                              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                                This document has been ingested but assets have not been extracted yet. Click the &quot;Extract Assets&quot; button in the Document Inventory to generate them.
                              </p>
                              <button
                                onClick={() => {
                                  setSelectedDocFilterId(null);
                                  window.history.pushState(null, '', '/knowledge-assets');
                                }}
                                className="text-xs text-cyan-400 hover:underline"
                              >
                                Clear Filter and View All
                              </button>
                            </div>
                          );
                        }

                        return entries.map(([key, group]) => {
                          const hasPending = group.items.some(item => item.status !== 'APPROVED' && item.status !== 'ARCHIVED');
                          
                          const doc = documents.find(d => d.id === group.docId);
                          const docStatus = doc ? doc.status : "N/A";
                          const docModified = doc ? new Date(doc.modified_at).toLocaleString() : "N/A";

                          const approvedGroup = group.items.filter(item => item.status === 'APPROVED').length;
                          const rejectedGroup = group.items.filter(item => item.status === 'ARCHIVED').length;
                          const candidateGroup = group.items.filter(item => item.status === 'CANDIDATE').length;

                          let statusReason = "Active review queue";
                          if (docStatus === "INGESTED") statusReason = "Document uploaded, awaiting parsing";
                          else if (docStatus === "PARSED") statusReason = "Parsed and indexed in Qdrant, awaiting asset extraction";
                          else if (docStatus === "ASSETS_EXTRACTED") statusReason = "Assets extracted, awaiting review";
                          else if (docStatus === "PARTIALLY_APPROVED") statusReason = "Governance active: some assets approved, others in review";
                          else if (docStatus === "APPROVED") statusReason = "Fully governed: all extracted knowledge assets approved";
                          else if (docStatus === "ALL_ASSETS_REJECTED") statusReason = "Hidden from active inventory because all extracted assets were rejected";
                          else if (docStatus === "DELETED") statusReason = "Excluded: all knowledge assets deleted";

                          return (
                            <div key={key} className="space-y-4 border border-slate-900 bg-[#090d16]/30 p-4 rounded-xl">
                              <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 bg-slate-950/80 p-3 rounded-lg border border-slate-900">
                                <span className="text-xs font-semibold flex items-center gap-2 text-slate-350">
                                  <FileText className="w-4 h-4 text-cyan-400" />
                                  Source Document: <span className="text-cyan-300 font-mono">{group.docName}</span> ({group.items.length} assets)
                                </span>
                                {group.docId && (
                                  <div className="flex flex-wrap gap-2">
                                    {hasPending && (
                                      <>
                                        <button
                                          onClick={async () => {
                                            const pending = group.items.filter(item => item.status !== 'APPROVED' && item.status !== 'ARCHIVED');
                                            const pendingIds = pending.map(item => item.id);
                                            if (pendingIds.length > 0) {
                                              await bulkUpdateAssetStatus(pendingIds, 'APPROVED');
                                            }
                                          }}
                                          className="text-[10px] text-emerald-400 hover:text-emerald-350 font-mono flex items-center gap-1.5 bg-emerald-950/20 px-2 py-1 rounded border border-emerald-900/30 transition-colors"
                                        >
                                          Approve All {candidateGroup} Assets
                                        </button>
                                        <button
                                          onClick={async () => {
                                            const pending = group.items.filter(item => item.status !== 'APPROVED' && item.status !== 'ARCHIVED');
                                            const pendingIds = pending.map(item => item.id);
                                            if (pendingIds.length > 0) {
                                              await bulkUpdateAssetStatus(pendingIds, 'ARCHIVED');
                                            }
                                          }}
                                          className="text-[10px] text-yellow-500 hover:text-yellow-400 font-mono flex items-center gap-1.5 bg-yellow-950/20 px-2 py-1 rounded border border-yellow-900/30 transition-colors"
                                        >
                                          Reject All {candidateGroup} Assets
                                        </button>
                                      </>
                                    )}
                                    {group.items.some(item => item.status === 'ARCHIVED') && (
                                      <button
                                        onClick={async () => {
                                          if (window.confirm(`Are you sure you want to permanently delete all ${rejectedGroup} rejected assets from this document?`)) {
                                            if (group.docId) await deleteDocumentAssets(group.docId, 'ARCHIVED');
                                          }
                                        }}
                                        className="text-[10px] text-rose-450 hover:text-rose-400 font-mono flex items-center gap-1 bg-rose-950/20 px-2 py-1 rounded border border-rose-900/30 transition-colors"
                                      >
                                        <Trash2 className="w-3 h-3" /> Delete {rejectedGroup} rejected
                                      </button>
                                    )}
                                    {group.items.some(item => item.status === 'CANDIDATE') && (
                                      <button
                                        onClick={async () => {
                                          if (window.confirm(`Are you sure you want to permanently delete all ${candidateGroup} candidate assets from this document?`)) {
                                            if (group.docId) await deleteDocumentAssets(group.docId, 'CANDIDATE');
                                          }
                                        }}
                                        className="text-[10px] text-orange-400 hover:text-orange-300 font-mono flex items-center gap-1 bg-orange-950/20 px-2 py-1 rounded border border-orange-900/30 transition-colors"
                                      >
                                        <Trash2 className="w-3.5 h-3.5" /> Delete {candidateGroup} candidates
                                      </button>
                                    )}
                                    <button
                                      onClick={async () => {
                                        if (window.confirm(`Are you sure you want to permanently delete ALL ${group.items.length} assets from this document? This action is destructive and cannot be undone.`)) {
                                          if (group.docId) await deleteDocumentAssets(group.docId);
                                        }
                                      }}
                                      className="text-[10px] text-red-400 hover:text-red-350 font-mono flex items-center gap-1 bg-red-950/20 px-2 py-1 rounded border border-red-900/30 transition-colors"
                                    >
                                      <Trash2 className="w-3.5 h-3.5" /> Delete All {group.items.length} Assets
                                    </button>
                                  </div>
                                )}
                              </div>

                              {/* GOVERNANCE AUDIT PANEL */}
                              <div className="bg-slate-950/40 border border-slate-900/50 rounded-lg p-4 grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-mono">
                                <div className="space-y-1">
                                  <span className="text-[10px] text-slate-500 block uppercase font-semibold">Lifecycle State</span>
                                  <span className={`font-bold uppercase flex items-center gap-1.5 ${
                                    docStatus === 'APPROVED' ? 'text-emerald-400' :
                                    docStatus === 'ALL_ASSETS_REJECTED' ? 'text-rose-400' :
                                    docStatus === 'PARTIALLY_APPROVED' ? 'text-cyan-400' : 'text-yellow-400'
                                  }`}>
                                    <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                                    {docStatus}
                                  </span>
                                  <span className="text-[9px] text-slate-500 block italic leading-tight">{statusReason}</span>
                                </div>
                                
                                <div className="space-y-1">
                                  <span className="text-[10px] text-slate-500 block uppercase font-semibold">Extracted Assets</span>
                                  <div className="grid grid-cols-3 gap-1 text-[10px] text-center text-slate-350">
                                    <div className="bg-slate-900/40 p-1 rounded border border-slate-900/20">
                                      <span className="text-[8px] text-slate-500 block">APRV</span>
                                      <span className="font-bold text-emerald-400">{approvedGroup}</span>
                                    </div>
                                    <div className="bg-slate-900/40 p-1 rounded border border-slate-900/20">
                                      <span className="text-[8px] text-slate-500 block">REJ</span>
                                      <span className="font-bold text-rose-400">{rejectedGroup}</span>
                                    </div>
                                    <div className="bg-slate-900/40 p-1 rounded border border-slate-900/20">
                                      <span className="text-[8px] text-slate-500 block">PEND</span>
                                      <span className="font-bold text-yellow-400">{candidateGroup}</span>
                                    </div>
                                  </div>
                                </div>

                                <div className="space-y-1 md:col-span-2">
                                  <span className="text-[10px] text-slate-500 block uppercase font-semibold">Governance Verification Trace</span>
                                  <div className="text-[10px] text-slate-400 space-y-0.5 leading-tight">
                                    <div>Last Transition: <span className="text-slate-300">{docModified}</span></div>
                                    <div>Workspace Owner: <span className="text-cyan-400 font-semibold">{doc ? doc.owner : 'N/A'}</span></div>
                                    <div>Integrity Hash Check: <span className="text-emerald-400">100% GOVERNED</span></div>
                                  </div>
                                </div>
                              </div>


                              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {group.items.map((asset, index) => {
                                  const score = asset.quality_scores?.[0];
                                  const isHighlighted = selectedDocFilterId === asset.document_id;
                                  return (
                                    <div 
                                      key={asset.id} 
                                      ref={isHighlighted && index === 0 ? firstAssetRef : undefined}
                                      className={`rounded-xl p-6 flex flex-col justify-between space-y-4 hover:border-slate-700 transition-all duration-300 ${
                                        isHighlighted 
                                          ? 'border-2 border-cyan-500/80 shadow-[0_0_15px_rgba(6,182,212,0.15)] bg-[#0c1624]/80' 
                                          : 'glass-panel'
                                      } ${
                                        asset.status === 'APPROVED' ? 'border-l-4 border-l-emerald-500' : 
                                        asset.status === 'ARCHIVED' ? 'border-l-4 border-l-rose-500/70 opacity-60' : 'border-l-4 border-l-yellow-500'
                                      }`}
                                    >
                                      <div className="space-y-1.5">
                                        <div className="flex justify-between items-start">
                                          <span className="text-[10px] font-mono bg-slate-900 text-cyan-400 px-2 py-0.5 rounded border border-slate-800 uppercase tracking-wider">
                                            {asset.type}
                                          </span>
                                          <div className="flex gap-2">
                                            {asset.active_revision_number != null && (
                                              <span
                                                title="Active approved revision — older revisions are archived as superseded"
                                                className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950/30 border border-cyan-900/40 text-cyan-400"
                                              >
                                                Rev {asset.active_revision_number} · Current
                                              </span>
                                            )}
                                            {asset.has_pending_revision && (
                                              <span
                                                title="A candidate revision is awaiting review — the current revision stays active until it is approved"
                                                className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-yellow-950/40 border border-yellow-900/40 text-yellow-400"
                                              >
                                                Candidate Pending
                                              </span>
                                            )}
                                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-950 border border-slate-900 text-slate-400">
                                              Access: {asset.access_level}
                                            </span>
                                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                                              asset.status === 'APPROVED' ? 'bg-emerald-950/40 text-emerald-400' :
                                              asset.status === 'ARCHIVED' ? 'bg-rose-950/30 text-rose-450' : 'bg-yellow-950/40 text-yellow-400'
                                            }`}>
                                              {asset.status === 'ARCHIVED' ? 'REJECTED' : asset.status}
                                            </span>
                                          </div>
                                        </div>
                                        <h4 className="font-bold text-sm text-slate-100">{asset.name}</h4>
                                      </div>

                                      <div className="bg-slate-950/50 border border-slate-900 rounded p-3 text-xs leading-relaxed text-slate-300 font-mono italic">
                                        &quot;{asset.content}&quot;
                                      </div>

                                      <div className="space-y-3.5 border-t border-slate-900/60 pt-3">
                                        <div className="space-y-1">
                                          <span className="text-[10px] text-slate-500 block uppercase font-mono tracking-wider">Source Provenance</span>
                                          <div className="grid grid-cols-2 gap-2 bg-slate-950/30 p-2 rounded border border-slate-900 text-[10px] font-mono">
                                            <div className="text-slate-400 truncate">Citation: {asset.source_citation}</div>
                                            <div className="text-slate-400">Page: {asset.source_page} | Sec: {asset.source_section}</div>
                                            <div className="text-slate-450 truncate">Hash: {asset.source_hash || 'N/A'}</div>
                                            <div className="text-cyan-400">Method: {asset.extraction_method}</div>
                                          </div>
                                        </div>

                                        {score && (
                                          <div className="space-y-1.5">
                                            <div className="flex justify-between items-center text-[10px] font-mono">
                                              <span className="text-slate-500 uppercase">Knowledge Quality Scores</span>
                                              <span className="text-emerald-400 font-bold">Overall: {score.overall_score}%</span>
                                            </div>
                                            
                                            <div className="grid grid-cols-4 gap-2 text-[8px] font-mono">
                                              <div className="bg-slate-900 p-1.5 rounded text-center border border-slate-850">
                                                <span className="text-slate-400 block mb-0.5">Coverage</span>
                                                <span className="text-[10px] text-slate-200 font-semibold">{score.coverage_score}%</span>
                                              </div>
                                              <div className="bg-slate-900 p-1.5 rounded text-center border border-slate-850">
                                                <span className="text-slate-400 block mb-0.5">Freshness</span>
                                                <span className="text-[10px] text-slate-200 font-semibold">{score.freshness_score}%</span>
                                              </div>
                                              <div className="bg-slate-900 p-1.5 rounded text-center border border-slate-850">
                                                <span className="text-slate-400 block mb-0.5">Verified</span>
                                                <span className="text-[10px] text-slate-200 font-semibold">{score.verification_score}%</span>
                                              </div>
                                              <div className="bg-slate-900 p-1.5 rounded text-center border border-slate-850">
                                                <span className="text-slate-400 block mb-0.5">No Conflict</span>
                                                <span className="text-[10px] text-slate-200 font-semibold">{score.conflict_score}%</span>
                                              </div>
                                            </div>
                                          </div>
                                        )}
                                      </div>

                                      <div className="flex items-center gap-2 pt-2 border-t border-slate-900/60">
                                        {asset.status !== 'APPROVED' && (
                                          <button
                                            onClick={() => updateAssetStatus(asset.id, 'APPROVED')}
                                            className="flex-1 py-1.5 bg-emerald-950/40 hover:bg-emerald-900/40 text-emerald-400 font-semibold rounded text-xs border border-emerald-900/30 transition-colors"
                                          >
                                            Approve
                                          </button>
                                        )}
                                        {asset.status !== 'ARCHIVED' && (
                                          <button
                                            onClick={() => updateAssetStatus(asset.id, 'ARCHIVED')}
                                            className="px-3 py-1.5 bg-rose-950/30 hover:bg-rose-950/50 text-rose-450 hover:text-rose-400 font-semibold rounded text-xs border border-rose-900/30 transition-colors"
                                          >
                                            Reject as Invalid
                                          </button>
                                        )}
                                        {(asset.status === 'CANDIDATE' || asset.status === 'ARCHIVED') && (
                                          <button
                                            onClick={() => deleteAsset(asset.id)}
                                            className="px-2.5 py-1.5 bg-rose-950/30 hover:bg-rose-950/50 text-rose-450 hover:text-rose-400 rounded text-xs border border-rose-900/30 transition-colors"
                                            title="Delete Asset"
                                          >
                                            <Trash2 className="w-3.5 h-3.5" />
                                          </button>
                                        )}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          );
                        });
                      })()}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: EXPERTS & AGENTS */}
              {activeTab === 'experts' && (
                <div className="space-y-8">
                  
                  {/* EXPERT MODEL BUILDER SECTION */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* BUILDER PANEL */}
                    <div className="glass-panel p-6 rounded-xl space-y-4">
                      <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-cyan-400" />
                        Construct Expert Knowledge Model
                      </h3>
                      
                      {approvedAssets.length === 0 ? (
                        <div className="text-center py-10 text-xs text-slate-500 italic">
                          No approved assets available. Please approve assets in the Knowledge Assets queue before building models.
                        </div>
                      ) : (
                        <form onSubmit={handleBuildExpertModel} className="space-y-4">
                          <div>
                            <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Expert Model Name</label>
                            <input 
                              type="text" 
                              required
                              placeholder="e.g. Quality Operations Expert"
                              value={expertName} 
                              onChange={(e) => setExpertName(e.target.value)}
                              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200" 
                            />
                          </div>

                          <div>
                            <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Description</label>
                            <textarea
                              rows={2}
                              placeholder="Describe the domain expertise scope"
                              value={expertDesc}
                              onChange={(e) => setExpertDesc(e.target.value)}
                              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200 resize-none"
                            ></textarea>
                          </div>

                          {/* ASSETS CHECKLIST */}
                          <div>
                            <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">
                              Select Governed Assets to Group ({selectedAssetIds.length} chosen)
                            </label>
                            <div className="space-y-2 max-h-48 overflow-y-auto pr-2 border border-slate-900 rounded p-2 bg-slate-950/40">
                              {approvedAssets.map((asset) => (
                                <label key={asset.id} className="flex items-start gap-2.5 text-xs text-slate-300 cursor-pointer p-1 rounded hover:bg-slate-900">
                                  <input 
                                    type="checkbox"
                                    checked={selectedAssetIds.includes(asset.id)}
                                    onChange={(e) => {
                                      if (e.target.checked) {
                                        setSelectedAssetIds([...selectedAssetIds, asset.id]);
                                      } else {
                                        setSelectedAssetIds(selectedAssetIds.filter(id => id !== asset.id));
                                      }
                                    }}
                                    className="mt-0.5 accent-cyan-500"
                                  />
                                  <div>
                                    <span className="font-semibold block text-[10px] text-cyan-400 font-mono">[{asset.type}] {asset.name}</span>
                                    <span className="text-[10px] text-slate-500 italic">Citation: {asset.source_citation}</span>
                                  </div>
                                </label>
                              ))}
                            </div>
                          </div>

                          <button 
                            type="submit" 
                            disabled={selectedAssetIds.length === 0}
                            className="w-full py-2 bg-gradient-to-r from-cyan-500 to-cyan-600 text-slate-950 font-bold rounded text-xs tracking-wider uppercase disabled:opacity-40"
                          >
                            Build Expert Model
                          </button>
                        </form>
                      )}
                    </div>

                    {/* MODELS INVENTORY */}
                    <div className="glass-panel p-6 rounded-xl space-y-4">
                      <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3">
                        Active Expert Models ({experts.length})
                      </h3>

                      {experts.length === 0 ? (
                        <div className="text-center py-16 text-slate-500 italic text-xs">
                          No expert models generated. Group assets using the builder.
                        </div>
                      ) : (
                        <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
                          {experts.map((model) => (
                            <div key={model.id} className="bg-slate-950/60 border border-slate-900 rounded-lg p-4 space-y-3.5">
                              <div className="flex justify-between items-start">
                                <div>
                                  <h4 className="font-bold text-sm text-slate-200">{model.name}</h4>
                                  <span className="text-[10px] text-slate-500 block mt-0.5">{model.description || 'No description'}</span>
                                </div>
                                <span className="text-[9px] font-mono bg-slate-900 text-slate-400 border border-slate-850 px-2 py-0.5 rounded">
                                  ID: EM-{model.id}
                                </span>
                              </div>

                              <div className="grid grid-cols-3 gap-2 bg-slate-950/80 p-2.5 rounded border border-slate-900 text-center font-mono text-[10px]">
                                <div>
                                  <span className="text-slate-500 block text-[8px] uppercase">Asset Count</span>
                                  <span className="text-slate-200 font-bold text-xs">{model.asset_count}</span>
                                </div>
                                <div>
                                  <span className="text-slate-500 block text-[8px] uppercase">Avg Quality</span>
                                  <span className="text-emerald-400 font-bold text-xs">{model.quality_score}%</span>
                                </div>
                                <div>
                                  <span className="text-slate-500 block text-[8px] uppercase">Avg Coverage</span>
                                  <span className="text-cyan-400 font-bold text-xs">{model.coverage_score}%</span>
                                </div>
                              </div>

                              {/* EXPERT MODEL TRUST SCORE — hierarchical, every component explainable */}
                              {(() => {
                                const ts = trustScores.find(t => t.expert_model_id === model.id);
                                if (!ts) return null;
                                // Weighted contribution per measured component: these sum
                                // exactly to the trust score (weights renormalized).
                                const totalWeight = ts.components.filter(c => c.measured).reduce((s, c) => s + c.weight, 0);
                                const contribution = (c: typeof ts.components[number]) =>
                                  c.measured && c.score != null && totalWeight > 0
                                    ? (c.score * c.weight) / totalWeight : null;
                                const explaining = trustExplainerId === model.id;
                                return (
                                  <div className="bg-slate-950/60 border border-slate-900 rounded p-3 space-y-2" title={ts.summary}>
                                    <div className="flex items-center justify-between">
                                      <span className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">
                                        Trust Score <span className="text-slate-600">({ts.score_version})</span>
                                      </span>
                                      <div className="flex items-center gap-2">
                                        <button
                                          onClick={() => setTrustExplainerId(explaining ? null : model.id)}
                                          className="text-[9px] font-mono text-cyan-400 hover:text-cyan-300 border border-cyan-900/40 bg-cyan-950/20 rounded px-2 py-0.5"
                                        >
                                          {explaining ? 'Hide' : 'Why this score?'}
                                        </button>
                                        <span className={`text-base font-bold font-mono ${
                                          ts.trust_score == null ? 'text-slate-500' :
                                          ts.trust_score >= 90 ? 'text-emerald-400' :
                                          ts.trust_score >= 70 ? 'text-yellow-400' : 'text-rose-400'
                                        }`}>
                                          {ts.trust_score ?? 'N/A'}
                                        </span>
                                      </div>
                                    </div>
                                    <div className="space-y-1">
                                      {ts.components.map((c) => {
                                        const contrib = contribution(c);
                                        return (
                                        <div key={c.key} className="flex items-center gap-2" title={c.reason}>
                                          <span className="text-[9px] font-mono text-slate-400 w-36 shrink-0 truncate">{c.label}</span>
                                          <div className="flex-1 h-1.5 bg-slate-900 rounded overflow-hidden">
                                            {c.measured && c.score != null && (
                                              <div
                                                className={`h-full rounded ${
                                                  c.score >= 90 ? 'bg-emerald-500/80' :
                                                  c.score >= 70 ? 'bg-yellow-500/80' : 'bg-rose-500/80'
                                                }`}
                                                style={{ width: `${c.score}%` }}
                                              />
                                            )}
                                          </div>
                                          <span className={`text-[9px] font-mono w-12 text-right ${
                                            !c.measured ? 'text-slate-600 italic' :
                                            c.score! >= 90 ? 'text-emerald-400' :
                                            c.score! >= 70 ? 'text-yellow-400' : 'text-rose-400'
                                          }`}>
                                            {c.measured ? c.score : 'N/M'}
                                          </span>
                                          <span className="text-[9px] font-mono text-slate-500 w-12 text-right">
                                            {contrib !== null ? `+${contrib.toFixed(1)}` : '—'}
                                          </span>
                                        </div>
                                        );
                                      })}
                                    </div>
                                    {explaining && (
                                      <div className="space-y-1.5 border-t border-slate-900/60 pt-2">
                                        <span className="text-[8px] font-mono text-slate-600 uppercase tracking-wider block">
                                          Contributions sum to the trust score (weights renormalized over measured components)
                                        </span>
                                        {ts.components.map((c) => (
                                          <div key={c.key} className="text-[9px] font-mono">
                                            <span className="text-slate-400">{c.label}</span>
                                            <span className="text-slate-500"> · weight {c.weight}</span>
                                            <p className="text-slate-300 font-sans italic">{c.reason}</p>
                                            {c.key === 'governance_health' && Array.isArray((c.details as { penalties?: unknown }).penalties) &&
                                              ((c.details as { penalties: { signal: string; count: number; penalty: number }[] }).penalties).map((p, i) => (
                                                <span key={i} className="text-[9px] text-rose-400/80 block pl-2">
                                                  − {p.penalty} · {p.count}× {p.signal.replace(/_/g, ' ')}
                                                </span>
                                              ))}
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                );
                              })()}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* AGENT PACKAGE COMPILER SECTION */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
                    {/* PACKAGE COMPILER FORM */}
                    <div className="glass-panel p-6 rounded-xl space-y-4 bg-gradient-to-br from-slate-950 to-slate-900/40">
                      <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                        <Lock className="w-4 h-4 text-emerald-400" />
                        Compile Deployable Agent Package
                      </h3>

                      {experts.length === 0 ? (
                        <div className="text-center py-10 text-xs text-slate-500 italic">
                          No expert models built. Create models first to package them.
                        </div>
                      ) : (
                        <form onSubmit={handleBuildAgentPackage} className="space-y-4">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                              <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Select Expert Model</label>
                              <select
                                required
                                value={selectedModelId || ''}
                                onChange={(e) => setSelectedModelId(Number(e.target.value))}
                                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-2 text-xs text-slate-200 outline-none focus:border-cyan-500 transition-colors"
                              >
                                <option value="">Select model...</option>
                                {experts.map(m => (
                                  <option key={m.id} value={m.id}>{m.name}</option>
                                ))}
                              </select>
                            </div>
                            
                            <div>
                              <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Governance Version</label>
                              <input
                                type="text"
                                required
                                value={packageVersion}
                                onChange={(e) => setPackageVersion(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200"
                              />
                            </div>

                            <div>
                              <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Package Clearance</label>
                              <select
                                value={packageClearance}
                                onChange={(e) => setPackageClearance(e.target.value as typeof packageClearance)}
                                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-2 text-xs text-slate-200 outline-none focus:border-cyan-500 transition-colors"
                              >
                                {(['PUBLIC', 'INTERNAL', 'RESTRICTED', 'EXECUTIVE'] as const).map(c => (
                                  <option key={c} value={c}>{c}</option>
                                ))}
                              </select>
                              <span className="text-[9px] text-slate-500 block mt-1">
                                Assets above this tier are excluded from the exported package.
                              </span>
                            </div>
                          </div>

                          <div>
                            <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Agent Package Name</label>
                            <input 
                              type="text" 
                              required
                              placeholder="e.g. Regulatory Audit Agent"
                              value={packageName} 
                              onChange={(e) => setPackageName(e.target.value)}
                              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200" 
                            />
                          </div>

                          <button 
                            type="submit" 
                            disabled={!selectedModelId}
                            className="w-full py-2 bg-gradient-to-r from-emerald-500 to-emerald-600 text-slate-950 font-bold rounded text-xs tracking-wider uppercase disabled:opacity-40"
                          >
                            Compile Agent Package
                          </button>
                        </form>
                      )}
                    </div>

                    {/* PACKAGES INVENTORY */}
                    <div className="glass-panel p-6 rounded-xl space-y-4">
                      <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3">
                        Published Agent Packages ({packages.length})
                      </h3>

                      {packages.length === 0 ? (
                        <div className="text-center py-16 text-slate-500 italic text-xs">
                          No compiled packages. Run compiler to package digital expert models.
                        </div>
                      ) : (
                        <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
                          {packages.map((pkg) => {
                            let assetRefs: { type: string; name: string; access_level: string }[] = [];
                            try {
                              assetRefs = JSON.parse(pkg.asset_references || '[]');
                            } catch {}

                            return (
                              <div key={pkg.id} className="bg-slate-950/60 border border-slate-900 rounded-lg p-4 space-y-3">
                                <div className="flex justify-between items-start">
                                  <div>
                                    <h4 className="font-bold text-sm text-slate-200">{pkg.name}</h4>
                                    <span className="text-[10px] text-slate-500 block mt-0.5">
                                      Version: {pkg.governance_version}
                                      {pkg.clearance_level && <> · Clearance: <span className="text-cyan-400">{pkg.clearance_level}</span></>}
                                      {pkg.manifest?.trust_score != null && <> · Trust at compile: <span className="text-emerald-400">{pkg.manifest.trust_score}</span></>}
                                    </span>
                                  </div>
                                  <div className="text-right">
                                    <span className="text-[10px] text-emerald-400 font-bold block">Avg Quality</span>
                                    <span className="text-sm font-black font-mono text-slate-200">{pkg.quality_score}%</span>
                                  </div>
                                </div>

                                {pkg.package_hash && (
                                  <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-900/60 border border-slate-900 rounded p-2">
                                    <span className="text-[9px] font-mono text-slate-500" title={pkg.package_hash}>
                                      Package hash: <span className="text-slate-300">{pkg.package_hash.slice(0, 20)}…</span>
                                      {pkg.manifest && pkg.manifest.excluded_assets_above_clearance > 0 && (
                                        <span className="text-yellow-400 block">
                                          {pkg.manifest.excluded_assets_above_clearance} asset{pkg.manifest.excluded_assets_above_clearance > 1 ? 's' : ''} excluded above clearance
                                        </span>
                                      )}
                                    </span>
                                    <a
                                      href={`http://localhost:8000/api/packages/${pkg.id}/download`}
                                      className="text-[10px] text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1.5 bg-cyan-950/20 px-3 py-1.5 rounded border border-cyan-900/30 transition-colors"
                                    >
                                      <FileCode2 className="w-3 h-3" /> Download .empkg
                                    </a>
                                  </div>
                                )}

                                <div className="border-t border-slate-900/60 pt-2 space-y-1">
                                  <span className="text-[9px] text-slate-500 block uppercase font-mono tracking-wider">Governed Knowledge Contents ({assetRefs.length} assets)</span>
                                  <div className="space-y-1">
                                    {assetRefs.map((ref, idx) => (
                                      <div key={idx} className="flex justify-between text-[9px] font-mono bg-slate-900/80 p-1 px-2 rounded text-slate-400">
                                        <span className="truncate max-w-[200px]">[{ref.type}] {ref.name}</span>
                                        <span className="text-cyan-400 font-semibold">{ref.access_level}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>

                </div>
              )}

              {/* TAB: EVALUATIONS (Benchmark Datasets, Runs, Scorecards) */}
              {activeTab === 'evaluations' && (
                <div className="space-y-6">

                  {/* BENCHMARK DATASETS */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="glass-panel p-6 rounded-xl space-y-4">
                      <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                        <FileCode2 className="w-4 h-4 text-cyan-400" />
                        Create Benchmark Question
                      </h3>
                      <form
                        onSubmit={async (e) => {
                          e.preventDefault();
                          if (activeProjectId === null || !benchQuestion.trim()) return;
                          await createBenchmark(activeProjectId, {
                            question: benchQuestion.trim(),
                            expected_claims: benchClaims.split('\n').map(c => c.trim()).filter(Boolean),
                            expected_answer_type: benchType,
                            severity: benchSeverity,
                            required_citation_count: benchType === 'REFUSAL' ? 0 : benchCitations,
                            min_required_coverage: benchCoverage
                          });
                          setBenchQuestion('');
                          setBenchClaims('');
                        }}
                        className="space-y-3"
                      >
                        <div>
                          <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Question</label>
                          <textarea
                            rows={2}
                            required
                            placeholder="e.g. Within what timeframe must critical deviations be logged?"
                            value={benchQuestion}
                            onChange={(e) => setBenchQuestion(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200 resize-none"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Expected Answer Type</label>
                            <select
                              value={benchType}
                              onChange={(e) => setBenchType(e.target.value as typeof benchType)}
                              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-2 text-xs text-slate-200 outline-none focus:border-cyan-500"
                            >
                              <option value="FACTUAL">FACTUAL</option>
                              <option value="PROCEDURAL">PROCEDURAL</option>
                              <option value="POLICY">POLICY</option>
                              <option value="REFUSAL">REFUSAL — must return INSUFFICIENT EVIDENCE</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Severity</label>
                            <select
                              value={benchSeverity}
                              onChange={(e) => setBenchSeverity(e.target.value as typeof benchSeverity)}
                              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-2 text-xs text-slate-200 outline-none focus:border-cyan-500"
                            >
                              <option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option>
                            </select>
                          </div>
                        </div>
                        {benchType !== 'REFUSAL' ? (
                          <>
                            <div>
                              <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Expected Claims (one per line)</label>
                              <textarea
                                rows={2}
                                placeholder={"Critical deviations must be logged within 24 hours."}
                                value={benchClaims}
                                onChange={(e) => setBenchClaims(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200 resize-none"
                              />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                              <div>
                                <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Required Citations</label>
                                <input type="number" min={0} max={10} value={benchCitations}
                                  onChange={(e) => setBenchCitations(Number(e.target.value))}
                                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200" />
                              </div>
                              <div>
                                <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Min Coverage (0–1)</label>
                                <input type="number" min={0} max={1} step={0.05} value={benchCoverage}
                                  onChange={(e) => setBenchCoverage(Number(e.target.value))}
                                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200" />
                              </div>
                            </div>
                          </>
                        ) : (
                          <p className="text-[10px] text-slate-500 font-mono italic bg-slate-950/40 border border-slate-900/60 rounded p-2.5">
                            REFUSAL tests pass only when the expert correctly returns INSUFFICIENT EVIDENCE —
                            proving the system knows when <span className="text-slate-300">not</span> to answer.
                          </p>
                        )}
                        <button type="submit" className="w-full py-2 bg-gradient-to-r from-cyan-500 to-cyan-600 text-slate-950 font-bold rounded text-xs tracking-wider uppercase">
                          Add Benchmark Question
                        </button>
                      </form>
                    </div>

                    <div className="glass-panel p-6 rounded-xl space-y-4">
                      <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3">
                        Benchmark Dataset ({benchmarks.length})
                      </h3>
                      {benchmarks.length === 0 ? (
                        <div className="text-center py-12 text-xs text-slate-500 italic">
                          No benchmark questions yet. Until benchmarks run, the Trust Score reports
                          Evaluation Reliability and Evidence Coverage as NOT_MEASURED.
                        </div>
                      ) : (
                        <div className="space-y-2.5 max-h-96 overflow-y-auto pr-2">
                          {benchmarks.map((b) => (
                            <div key={b.id} className="bg-slate-950/60 border border-slate-900 rounded-lg p-3 space-y-1.5">
                              <div className="flex justify-between items-start gap-2">
                                <p className="text-xs text-slate-200">{b.question}</p>
                                <button onClick={() => activeProjectId !== null && deleteBenchmark(activeProjectId, b.id)}
                                  className="text-slate-600 hover:text-rose-400 shrink-0" title="Delete benchmark question">
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                              <div className="flex flex-wrap gap-1.5 font-mono text-[9px]">
                                <span className={`px-2 py-0.5 rounded-full border ${
                                  b.expected_answer_type === 'REFUSAL'
                                    ? 'bg-purple-950/40 text-purple-400 border-purple-900/50'
                                    : 'bg-cyan-950/30 text-cyan-400 border-cyan-900/40'
                                }`}>{b.expected_answer_type}</span>
                                <span className="px-2 py-0.5 rounded-full bg-slate-900 text-slate-400 border border-slate-800">{b.severity}</span>
                                {b.expected_answer_type !== 'REFUSAL' && (
                                  <span className="px-2 py-0.5 rounded-full bg-slate-900 text-slate-400 border border-slate-800">
                                    cov ≥ {b.min_required_coverage} · cites ≥ {b.required_citation_count}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* RUN EVALUATION */}
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3">
                      Run Evaluation
                      <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                        Snapshot-based batch — results feed Evaluation Reliability and Evidence Coverage in the Trust Score
                      </span>
                    </h3>
                    <div className="flex flex-wrap items-end gap-4">
                      <div className="flex-1 min-w-[220px]">
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Expert Model</label>
                        <select
                          value={evalModelId ?? ''}
                          onChange={(e) => setEvalModelId(Number(e.target.value))}
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200"
                        >
                          {experts.map((m) => (
                            <option key={m.id} value={m.id}>EM-{m.id} — {m.name}</option>
                          ))}
                        </select>
                      </div>
                      <button
                        onClick={() => activeProjectId !== null && evalModelId !== null && startEvaluation(activeProjectId, evalModelId)}
                        disabled={evaluationRunning || evalModelId === null || benchmarks.length === 0}
                        className="py-2 px-5 bg-gradient-to-r from-cyan-500 to-cyan-600 text-slate-950 font-bold rounded text-xs tracking-wider uppercase disabled:opacity-40"
                      >
                        {evaluationRunning ? 'Evaluating…' : `Run ${benchmarks.length} Benchmark${benchmarks.length === 1 ? '' : 's'}`}
                      </button>
                    </div>
                  </div>

                  {/* COVERAGE TREND (MVP 0.9.3) — answer coverage over completed runs */}
                  {(() => {
                    if (!coverageTrend || coverageTrend.expert_model_id !== evalModelId) return null;
                    const points = coverageTrend.runs;
                    if (points.length === 0) return null;

                    const W = 420, H = 110, PL = 30, PR = 12, PT = 10, PB = 18;
                    const x = (i: number) => points.length === 1
                      ? PL + (W - PL - PR) / 2
                      : PL + (i * (W - PL - PR)) / (points.length - 1);
                    const y = (pct: number) => PT + (100 - pct) * (H - PT - PB) / 100;
                    const line = (vals: (number | null)[]) =>
                      vals.map((v, i) => v === null ? null : `${x(i)},${y(v)}`)
                        .filter(Boolean).join(' ');

                    const passVals = points.map(p => p.pass_rate * 100);
                    const covVals = points.map(p => p.average_coverage_score * 100);
                    const supVals = points.map(p => p.supported_pct);

                    const SERIES = [
                      { label: 'Pass Rate', color: '#34d399', vals: passVals as (number | null)[] },
                      { label: 'Avg Coverage', color: '#22d3ee', vals: covVals as (number | null)[] },
                      { label: 'Supported Claims', color: '#facc15', vals: supVals },
                    ];

                    return (
                      <div className="glass-panel p-6 rounded-xl space-y-3">
                        <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                          <Sparkles className="w-4 h-4 text-cyan-400" />
                          Answer Coverage Trend
                          <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                            Computed from persisted evaluation runs and claim verdicts — runs before verdict persistence show no claim series
                          </span>
                        </h3>
                        <div className="flex flex-wrap gap-4 items-start">
                          <svg viewBox={`0 0 ${W} ${H}`} className="flex-1 min-w-[280px] max-w-[560px]">
                            {[0, 50, 100].map(g => (
                              <g key={g}>
                                <line x1={PL} y1={y(g)} x2={W - PR} y2={y(g)} stroke="#1e293b" strokeWidth="1" />
                                <text x={PL - 4} y={y(g) + 3} textAnchor="end" fontSize="7" fill="#64748b" fontFamily="monospace">{g}</text>
                              </g>
                            ))}
                            {SERIES.map(s => (
                              <polyline key={s.label} points={line(s.vals)} fill="none" stroke={s.color} strokeWidth="1.5" strokeOpacity="0.85" />
                            ))}
                            {SERIES.map(s => s.vals.map((v, i) => v === null ? null : (
                              <circle key={`${s.label}-${i}`} cx={x(i)} cy={y(v)} r="2.5" fill={s.color}>
                                <title>{`RUN-${points[i].run_id} ${s.label}: ${Math.round(v)}%`}</title>
                              </circle>
                            )))}
                            {points.map((p, i) => (
                              <text key={p.run_id} x={x(i)} y={H - 4} textAnchor="middle" fontSize="7" fill="#64748b" fontFamily="monospace">
                                RUN-{p.run_id}
                              </text>
                            ))}
                          </svg>
                          <div className="space-y-2 min-w-[180px]">
                            <div className="flex flex-wrap gap-3">
                              {SERIES.map(s => (
                                <span key={s.label} className="flex items-center gap-1.5 text-[9px] font-mono text-slate-400">
                                  <span className="w-2.5 h-0.5 rounded" style={{ backgroundColor: s.color }} />
                                  {s.label}
                                </span>
                              ))}
                            </div>
                            <div className="space-y-1">
                              {points.map(p => (
                                <div key={p.run_id} className="flex items-center gap-2 text-[9px] font-mono">
                                  <span className="text-slate-500 w-12 shrink-0">RUN-{p.run_id}</span>
                                  {p.verdict_counts ? (
                                    <>
                                      <span className="text-emerald-400">{p.verdict_counts.ENTAILED} entailed</span>
                                      <span className="text-rose-400">{p.verdict_counts.CONTRADICTED} contradicted</span>
                                      <span className="text-yellow-400">{p.verdict_counts.UNSUPPORTED} unsupported</span>
                                    </>
                                  ) : (
                                    <span className="text-slate-600 italic">verdicts not persisted for this run</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })()}

                  {/* RUN HISTORY & SCORECARDS */}
                  <div className="space-y-4">
                    {evaluationRuns.length === 0 ? (
                      <div className="glass-panel rounded-xl p-12 text-center text-xs text-slate-500 italic">
                        No evaluation runs yet.
                      </div>
                    ) : (
                      [...evaluationRuns].sort((a, b) => b.id - a.id).map((run) => {
                        const model = experts.find(m => m.id === run.expert_model_id);
                        const expanded = expandedRunId === run.id;
                        const benchById = (id: number) => benchmarks.find(b => b.id === id);
                        return (
                          <div key={run.id} className={`glass-panel rounded-xl p-5 space-y-3 border-l-4 ${
                            run.status === 'COMPLETED' ? (run.pass_rate >= 0.8 ? 'border-l-emerald-500' : 'border-l-yellow-500') :
                            run.status === 'FAILED' ? 'border-l-rose-500' : 'border-l-cyan-500'
                          }`}>
                            <div className="flex flex-wrap justify-between items-center gap-2 cursor-pointer"
                              onClick={() => setExpandedRunId(expanded ? null : run.id)}>
                              <div className="flex items-center gap-3">
                                <span className="text-[10px] font-mono bg-slate-900 text-slate-400 border border-slate-850 px-2 py-0.5 rounded">RUN-{run.id}</span>
                                <span className="font-bold text-sm text-slate-200">{model ? model.name : `EM-${run.expert_model_id}`}</span>
                                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                                  run.status === 'COMPLETED' ? 'bg-emerald-950/40 text-emerald-400' :
                                  run.status === 'FAILED' ? 'bg-rose-950/30 text-rose-400' : 'bg-cyan-950/40 text-cyan-400 animate-pulse'
                                }`}>{run.status}</span>
                              </div>
                              {run.status === 'COMPLETED' && (
                                <div className="flex gap-2 font-mono text-[10px]">
                                  <div className="bg-slate-950/80 border border-slate-900 rounded px-3 py-1 text-center">
                                    <span className="text-slate-500 block text-[8px] uppercase">Pass Rate</span>
                                    <span className={`font-bold ${run.pass_rate >= 0.8 ? 'text-emerald-400' : 'text-yellow-400'}`}>{Math.round(run.pass_rate * 100)}%</span>
                                  </div>
                                  <div className="bg-slate-950/80 border border-slate-900 rounded px-3 py-1 text-center">
                                    <span className="text-slate-500 block text-[8px] uppercase">Avg Coverage</span>
                                    <span className="text-cyan-400 font-bold">{Math.round(run.average_coverage_score * 100)}%</span>
                                  </div>
                                  <div className="bg-slate-950/80 border border-slate-900 rounded px-3 py-1 text-center">
                                    <span className="text-slate-500 block text-[8px] uppercase">Avg Confidence</span>
                                    <span className="text-slate-200 font-bold">{Math.round(run.average_confidence_score * 100)}%</span>
                                  </div>
                                </div>
                              )}
                            </div>

                            {expanded && run.results.length > 0 && (
                              <div className="space-y-2.5 border-t border-slate-900/60 pt-3">
                                {run.results.map((r) => {
                                  const bench = benchById(r.benchmark_question_id);
                                  const isRefusal = bench?.expected_answer_type === 'REFUSAL';
                                  return (
                                    <div key={r.id} id={`eval-result-${r.id}`} className={`bg-slate-950/50 border rounded-lg p-3 space-y-1.5 ${
                                      r.passed ? 'border-emerald-900/40' : 'border-rose-900/40'
                                    } ${highlightResultId === r.id ? 'ring-2 ring-cyan-500/70' : ''}`}>
                                      <div className="flex flex-wrap justify-between items-center gap-2">
                                        <p className="text-xs text-slate-200">{r.question_text}</p>
                                        <div className="flex gap-1.5 font-mono text-[9px] shrink-0">
                                          {isRefusal && (
                                            <span className="px-2 py-0.5 rounded-full bg-purple-950/40 text-purple-400 border border-purple-900/50">REFUSAL TEST</span>
                                          )}
                                          <span className={`px-2 py-0.5 rounded-full font-bold ${
                                            r.passed ? 'bg-emerald-950/40 text-emerald-400' : 'bg-rose-950/30 text-rose-400'
                                          }`}>{r.passed ? 'PASSED' : 'FAILED'}</span>
                                        </div>
                                      </div>
                                      {isRefusal ? (
                                        <p className={`text-[10px] font-mono ${r.passed ? 'text-emerald-400/90' : 'text-rose-400/90'}`}>
                                          {r.passed
                                            ? 'Expert correctly returned INSUFFICIENT EVIDENCE — it knows when not to answer.'
                                            : 'Expert answered when it should have refused — unverified knowledge leaked.'}
                                        </p>
                                      ) : (
                                        <>
                                          <p className="text-[10px] text-slate-400 font-mono italic truncate">
                                            Answer: {r.generated_answer || '—'}
                                          </p>
                                          <div className="flex flex-wrap gap-1.5 font-mono text-[9px]">
                                            <span className="px-2 py-0.5 rounded bg-slate-900/80 text-slate-400 border border-slate-800">coverage {r.coverage_score}</span>
                                            <span className="px-2 py-0.5 rounded bg-slate-900/80 text-slate-400 border border-slate-800">{r.verification_status}</span>
                                            <span className="px-2 py-0.5 rounded bg-slate-900/80 text-slate-400 border border-slate-800">{r.citations.length} citation{r.citations.length === 1 ? '' : 's'}</span>
                                          </div>
                                          {!r.passed && r.unsupported_claims.length > 0 && (r.claim_verdicts || []).length === 0 && (
                                            <p className="text-[9px] text-rose-400/80 font-mono">
                                              Unsupported: {r.unsupported_claims.join(' | ')}
                                            </p>
                                          )}
                                        </>
                                      )}

                                      {/* PERSISTED CLAIM VERDICTS (MVP 0.9.2) — immutable verifier artifacts.
                                          Shown for refusal tests too: the verdicts are why the expert refused. */}
                                      {(r.claim_verdicts || []).length > 0 && (
                                            <div className="space-y-1 border-t border-slate-900/60 pt-1.5">
                                              {r.claim_verdicts.map((v) => (
                                                <div key={v.id} className="space-y-1">
                                                  <div className="flex flex-wrap items-center gap-1.5 font-mono text-[9px]">
                                                    <span className={`px-1.5 py-0.5 rounded font-bold ${
                                                      v.verdict === 'ENTAILED' ? 'bg-emerald-950/40 text-emerald-400' :
                                                      v.verdict === 'CONTRADICTED' ? 'bg-rose-950/40 text-rose-400' :
                                                      'bg-yellow-950/40 text-yellow-400'
                                                    }`}>{v.verdict}</span>
                                                    {v.confidence !== null && (
                                                      <span className="text-slate-500">{v.confidence.toFixed(3)}</span>
                                                    )}
                                                    <span className="text-slate-300 font-sans text-[10px] italic flex-1 min-w-[160px]">&quot;{v.claim}&quot;</span>
                                                    {v.verdict !== 'ENTAILED' && (
                                                      reviewedVerdictIds.has(v.id) ? (
                                                        <span className="text-emerald-400/80">review recorded</span>
                                                      ) : verdictReview !== v.id && (
                                                        <button
                                                          onClick={() => { setVerdictReview(v.id); setVerdictReviewComment(''); }}
                                                          className="text-cyan-400 hover:text-cyan-300 px-1.5 py-0.5 rounded border border-cyan-900/30 bg-cyan-950/20"
                                                        >
                                                          Record Review
                                                        </button>
                                                      )
                                                    )}
                                                  </div>
                                                  {verdictReview === v.id && (
                                                    <div className="space-y-1.5 pl-2 border-l-2 border-slate-800">
                                                      <textarea
                                                        rows={2}
                                                        autoFocus
                                                        placeholder="Human judgment — recorded as a VERIFICATION_REVIEWED audit event; the verdict artifact itself is never modified."
                                                        value={verdictReviewComment}
                                                        onChange={(e) => setVerdictReviewComment(e.target.value)}
                                                        className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1.5 text-[10px] focus:border-cyan-500 outline-none text-slate-200 resize-none"
                                                      />
                                                      <div className="flex gap-2">
                                                        <button
                                                          disabled={!verdictReviewComment.trim()}
                                                          onClick={async () => {
                                                            await reviewClaimVerdict(v.id, 'GovernanceOfficer', verdictReviewComment.trim());
                                                            setReviewedVerdictIds(prev => new Set(prev).add(v.id));
                                                            setVerdictReview(null);
                                                            setVerdictReviewComment('');
                                                          }}
                                                          className="text-[9px] font-mono font-bold px-2.5 py-1 rounded uppercase tracking-wider bg-cyan-500 text-slate-950 disabled:opacity-40"
                                                        >
                                                          Record Verification Review
                                                        </button>
                                                        <button
                                                          onClick={() => { setVerdictReview(null); setVerdictReviewComment(''); }}
                                                          className="text-[9px] font-mono text-slate-500 hover:text-slate-300 px-2 py-1"
                                                        >
                                                          Cancel
                                                        </button>
                                                      </div>
                                                    </div>
                                                  )}
                                                </div>
                                              ))}
                                            </div>
                                          )}
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}

              {/* SCAN FOLDER + INGESTION JOBS (MVP 0.10.0) — second ingestion
                  method inside Document Inventory, NOT a separate area: one
                  source type does not justify a connector administration
                  surface (that arrives with multiple source types in v0.11+).
                  Output is ordinary documents and CANDIDATE assets. */}
              {activeTab === 'documents' && (
                <div className="space-y-6 mt-6">

                  {/* SCAN FOLDER */}
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                      <Folder className="w-4 h-4 text-cyan-400" />
                      Scan Folder
                      <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                        Bulk ingestion from a local or mounted folder — discovered files become ordinary documents and CANDIDATE assets
                      </span>
                    </h3>
                    <form
                      onSubmit={async (e) => {
                        e.preventDefault();
                        if (activeProjectId === null || !connectorName.trim() || !connectorPath.trim()) return;
                        await createConnector(activeProjectId, connectorName.trim(), connectorPath.trim(), connectorExts.trim());
                        setConnectorName('');
                        setConnectorPath('');
                      }}
                      className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end"
                    >
                      <div>
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Connector Name</label>
                        <input type="text" required value={connectorName} onChange={(e) => setConnectorName(e.target.value)}
                          placeholder="e.g. Quality SOP Share"
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200" />
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Folder Path</label>
                        <input type="text" required value={connectorPath} onChange={(e) => setConnectorPath(e.target.value)}
                          placeholder="C:\\shares\\policies or /mnt/docs"
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200 font-mono" />
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">File Types</label>
                        <input type="text" value={connectorExts} onChange={(e) => setConnectorExts(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200 font-mono" />
                      </div>
                      <button type="submit"
                        className="py-2 px-5 bg-gradient-to-r from-cyan-500 to-cyan-600 text-slate-950 font-bold rounded text-xs tracking-wider uppercase disabled:opacity-40">
                        Add Connector
                      </button>
                    </form>

                    {/* CONNECTOR LIST */}
                    {sourceConnectors.length > 0 && (
                      <div className="space-y-2 pt-2">
                        {sourceConnectors.map((c) => {
                          const busy = ingestionJobs.some(j => j.connector_id === c.id && (j.status === 'PENDING' || j.status === 'RUNNING'));
                          return (
                            <div key={c.id} className="flex flex-wrap items-center gap-3 bg-slate-950/60 border border-slate-900 rounded-lg p-3">
                              <span className="text-[10px] font-mono bg-slate-900 text-slate-400 border border-slate-850 px-2 py-0.5 rounded">{c.type}</span>
                              <span className="font-bold text-sm text-slate-200">{c.name}</span>
                              <span className="text-[10px] font-mono text-slate-500 flex-1 min-w-[180px] truncate" title={c.root_path}>{c.root_path}</span>
                              <span className="text-[9px] font-mono text-slate-600">{c.include_extensions}</span>
                              <button
                                onClick={() => activeProjectId !== null && scanConnector(c.id, activeProjectId)}
                                disabled={busy}
                                className="text-[10px] text-cyan-400 hover:text-cyan-300 font-mono bg-cyan-950/20 border border-cyan-900/30 rounded px-3 py-1.5 uppercase tracking-wider disabled:opacity-40"
                              >
                                {busy ? 'Scanning…' : 'Scan Now'}
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* RECENT INGESTION JOBS */}
                  {ingestionJobs.length > 0 && (
                    <div className="space-y-4">
                      <h4 className="text-xs font-bold text-slate-300 tracking-wide flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 text-cyan-400" />
                        Recent Ingestion Jobs
                        <span className="text-slate-500 font-mono text-[10px] font-normal">
                          {ingestionJobs.length} job{ingestionJobs.length > 1 ? 's' : ''}
                        </span>
                      </h4>
                      {ingestionJobs.map((job) => {
                        const connector = sourceConnectors.find(c => c.id === job.connector_id);
                        const expanded = expandedJobId === job.id;
                        const files = jobFiles[job.id] || [];
                        return (
                          <div key={job.id} className={`glass-panel rounded-xl p-5 space-y-3 border-l-4 ${
                            job.status === 'COMPLETED' ? (job.files_failed > 0 ? 'border-l-yellow-500' : 'border-l-emerald-500') :
                            job.status === 'FAILED' ? 'border-l-rose-500' : 'border-l-cyan-500'
                          }`}>
                            <div className="flex flex-wrap justify-between items-center gap-2 cursor-pointer"
                              onClick={() => {
                                const next = expanded ? null : job.id;
                                setExpandedJobId(next);
                                if (next !== null) fetchJobFiles(job.id);
                              }}>
                              <div className="flex items-center gap-3">
                                <span className="text-[10px] font-mono bg-slate-900 text-slate-400 border border-slate-850 px-2 py-0.5 rounded">JOB-{job.id}</span>
                                <span className="font-bold text-sm text-slate-200">{connector?.name || `Connector ${job.connector_id}`}</span>
                                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                                  job.status === 'COMPLETED' ? 'bg-emerald-950/40 text-emerald-400' :
                                  job.status === 'FAILED' ? 'bg-rose-950/30 text-rose-400' : 'bg-cyan-950/40 text-cyan-400 animate-pulse'
                                }`}>{job.status}</span>
                                <span className="text-[9px] font-mono text-slate-500">{new Date(job.started_at).toLocaleString()}</span>
                              </div>
                              <div className="flex gap-2 font-mono text-[10px]">
                                <div className="bg-slate-950/80 border border-slate-900 rounded px-3 py-1 text-center">
                                  <span className="text-slate-500 block text-[8px] uppercase">Discovered</span>
                                  <span className="text-slate-200 font-bold">{job.files_discovered}</span>
                                </div>
                                <div className="bg-slate-950/80 border border-slate-900 rounded px-3 py-1 text-center">
                                  <span className="text-slate-500 block text-[8px] uppercase">Ingested</span>
                                  <span className="text-emerald-400 font-bold">{job.files_ingested}</span>
                                </div>
                                <div className="bg-slate-950/80 border border-slate-900 rounded px-3 py-1 text-center">
                                  <span className="text-slate-500 block text-[8px] uppercase">Duplicates</span>
                                  <span className="text-yellow-400 font-bold">{job.files_duplicate}</span>
                                </div>
                                <div className="bg-slate-950/80 border border-slate-900 rounded px-3 py-1 text-center">
                                  <span className="text-slate-500 block text-[8px] uppercase">Failed</span>
                                  <span className={`font-bold ${job.files_failed > 0 ? 'text-rose-400' : 'text-slate-500'}`}>{job.files_failed}</span>
                                </div>
                              </div>
                            </div>

                            {job.error && (
                              <p className="text-[10px] text-rose-400/90 font-mono bg-rose-950/20 border border-rose-900/30 rounded p-2">
                                {job.error}
                              </p>
                            )}

                            {expanded && files.length > 0 && (
                              <div className="space-y-1 border-t border-slate-900/60 pt-3 max-h-72 overflow-y-auto pr-2">
                                {files.map((f) => (
                                  <div key={f.id} className="flex flex-wrap items-center gap-2 text-[9px] font-mono bg-slate-950/50 rounded px-2 py-1">
                                    <span className={`px-1.5 py-0.5 rounded font-bold ${
                                      f.status === 'INGESTED' ? 'bg-emerald-950/40 text-emerald-400' :
                                      f.status === 'DUPLICATE' ? 'bg-yellow-950/40 text-yellow-400' :
                                      'bg-rose-950/40 text-rose-400'
                                    }`}>{f.status}</span>
                                    <span className="text-slate-300 flex-1 min-w-[200px] truncate" title={f.source_uri}>{f.source_uri}</span>
                                    {f.size_bytes !== null && <span className="text-slate-600">{f.size_bytes} B</span>}
                                    {f.document_id && <span className="text-cyan-400">DOC-{f.document_id}</span>}
                                    {f.error && <span className="text-slate-400 italic w-full pl-1">{f.error}</span>}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* TAB: GOVERNANCE INBOX & READINESS CONSOLE (MVP 0.9.1) */}
              {activeTab === 'inbox' && (
                <div className="space-y-6">

                  {/* HEADER + SUMMARY */}
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <div className="flex justify-between items-center border-b border-slate-900 pb-3">
                      <h3 className="font-bold text-sm text-slate-200 tracking-wide flex items-center gap-2">
                        <Inbox className="w-4 h-4 text-cyan-400" />
                        Governance Inbox
                        <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                          One prioritized operating view over existing reviewable records — decisions happen in the specialized workbenches
                        </span>
                      </h3>
                      <button
                        onClick={() => activeProjectId !== null && fetchGovernanceInbox(activeProjectId)}
                        className="text-[10px] text-cyan-400 hover:text-cyan-300 font-mono bg-cyan-950/30 border border-cyan-900/40 rounded px-3 py-1.5 uppercase tracking-wider"
                      >
                        {governanceInboxLoading ? 'Refreshing…' : 'Refresh'}
                      </button>
                    </div>

                    {governanceInbox && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-center">
                        <div className="bg-slate-950/80 border border-slate-900 rounded-lg p-3">
                          <span className="text-slate-500 block text-[9px] uppercase">Needs Review Now</span>
                          <span className={`font-bold text-xl ${governanceInbox.summary.needs_review > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                            {governanceInbox.summary.needs_review}
                          </span>
                        </div>
                        <div className="bg-slate-950/80 border border-slate-900 rounded-lg p-3">
                          <span className="text-slate-500 block text-[9px] uppercase">Can Wait</span>
                          <span className="text-yellow-400 font-bold text-xl">{governanceInbox.summary.can_wait}</span>
                        </div>
                        <div className="bg-slate-950/80 border border-slate-900 rounded-lg p-3">
                          <span className="text-slate-500 block text-[9px] uppercase">Recently Resolved</span>
                          <span className="text-slate-300 font-bold text-xl">{governanceInbox.summary.recently_resolved}</span>
                        </div>
                        <div className="bg-slate-950/80 border border-slate-900 rounded-lg p-3">
                          <span className="text-slate-500 block text-[9px] uppercase">Blocked Models</span>
                          <span className={`font-bold text-xl ${governanceInbox.summary.blocked_expert_models > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                            {governanceInbox.summary.blocked_expert_models}/{governanceInbox.summary.total_expert_models}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* EXPERT MODEL FILTER */}
                    {experts.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-1">
                        <button
                          onClick={() => setInboxModelFilter(null)}
                          className={`text-[10px] font-mono px-3 py-1 rounded-full border transition-colors ${
                            inboxModelFilter === null
                              ? 'bg-cyan-950/40 text-cyan-400 border-cyan-800'
                              : 'bg-slate-950 text-slate-500 border-slate-900 hover:text-slate-300'
                          }`}
                        >
                          ALL MODELS
                        </button>
                        {experts.map((m) => (
                          <button
                            key={m.id}
                            onClick={() => setInboxModelFilter(m.id)}
                            className={`text-[10px] font-mono px-3 py-1 rounded-full border transition-colors ${
                              inboxModelFilter === m.id
                                ? 'bg-cyan-950/40 text-cyan-400 border-cyan-800'
                                : 'bg-slate-950 text-slate-500 border-slate-900 hover:text-slate-300'
                            }`}
                          >
                            EM-{m.id} {m.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* COMPILE READINESS PANEL */}
                  {governanceInbox && governanceInbox.readiness.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-slate-300 tracking-wide flex items-center gap-2">
                        <Boxes className="w-3.5 h-3.5 text-cyan-400" />
                        Compile Readiness
                        <span className="text-slate-500 font-mono text-[10px] font-normal">
                          Can each Expert Model be deployed today?
                        </span>
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {governanceInbox.readiness
                          .filter(r => inboxModelFilter === null || r.expert_model_id === inboxModelFilter)
                          .map((r) => (
                          <div
                            key={r.expert_model_id}
                            className={`glass-panel rounded-xl p-5 space-y-3 border-l-4 ${
                              r.compile_allowed ? 'border-l-emerald-500' : 'border-l-rose-500'
                            }`}
                          >
                            <div className="flex justify-between items-center gap-2">
                              <span className="font-bold text-sm text-slate-100 truncate">
                                <span className="text-[10px] font-mono text-slate-500 mr-2">EM-{r.expert_model_id}</span>
                                {r.expert_model_name}
                              </span>
                              <span className={`text-[10px] font-mono font-bold px-2.5 py-1 rounded-full ${
                                r.compile_allowed
                                  ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/50'
                                  : 'bg-rose-950/40 text-rose-400 border border-rose-900/50'
                              }`}>
                                {r.compile_allowed ? 'READY' : 'BLOCKED'}
                              </span>
                            </div>

                            <div className="flex items-center gap-4">
                              <div className="text-center shrink-0">
                                <span className={`text-2xl font-bold font-mono block ${
                                  r.trust_score === null ? 'text-slate-600' :
                                  r.trust_score >= 90 ? 'text-emerald-400' :
                                  r.trust_score >= 70 ? 'text-yellow-400' : 'text-rose-400'
                                }`}>
                                  {r.trust_score ?? '—'}
                                </span>
                                <span className="text-[9px] text-slate-500 font-mono uppercase">Trust</span>
                              </div>
                              <div className="flex gap-2 font-mono text-[10px] flex-wrap">
                                <span className={`px-2 py-1 rounded border ${
                                  r.blocking_conflicts.length > 0
                                    ? 'bg-rose-950/30 text-rose-400 border-rose-900/40'
                                    : 'bg-slate-950 text-slate-500 border-slate-900'
                                }`}>
                                  {r.blocking_conflicts.length} blocking
                                </span>
                                <span className="px-2 py-1 rounded border bg-slate-950 text-slate-400 border-slate-900">
                                  {r.advisory_conflicts.length} advisory
                                </span>
                                <span className="px-2 py-1 rounded border bg-slate-950 text-slate-500 border-slate-900">
                                  {r.dismissed_conflicts} dismissed
                                </span>
                                {!r.conflict_scan_performed && (
                                  <span className="px-2 py-1 rounded border bg-yellow-950/30 text-yellow-400 border-yellow-900/40">
                                    never scanned
                                  </span>
                                )}
                              </div>
                            </div>

                            {r.governance_facts.length > 0 && (
                              <div className="space-y-1 border-t border-slate-900/60 pt-2">
                                {r.governance_facts.map((fact, i) => (
                                  <span key={i} className="text-[10px] font-mono text-slate-400 block">• {fact}</span>
                                ))}
                              </div>
                            )}

                            {!r.compile_allowed && (
                              <button
                                onClick={() => setInboxModelFilter(r.expert_model_id)}
                                className="text-[10px] text-rose-400 hover:text-rose-300 font-mono flex items-center gap-1.5 bg-rose-950/20 px-3 py-1.5 rounded border border-rose-900/30 transition-colors"
                              >
                                <ArrowRight className="w-3 h-3" /> View Blocking Items
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* PRIORITIZED WORK ITEM BUCKETS */}
                  {(() => {
                    if (!governanceInbox) {
                      return (
                        <div className="glass-panel rounded-xl p-12 text-center text-xs text-slate-500 italic">
                          {governanceInboxLoading ? 'Computing governance inbox…' : 'No inbox data. Select a workspace project.'}
                        </div>
                      );
                    }

                    const matchesModel = (item: typeof governanceInbox.items[number]) =>
                      inboxModelFilter === null ||
                      item.expert_model_id === inboxModelFilter ||
                      (item.related_expert_model_ids || []).includes(inboxModelFilter);
                    const visible = governanceInbox.items.filter(matchesModel);

                    const SEVERITY_BADGE: Record<string, string> = {
                      HIGH: 'bg-rose-950/40 text-rose-400 border-rose-900/50',
                      MEDIUM: 'bg-yellow-950/40 text-yellow-400 border-yellow-900/50',
                      LOW: 'bg-slate-900 text-slate-400 border-slate-800',
                    };
                    const TYPE_META: Record<string, { label: string; action: string }> = {
                      CONFLICT: { label: 'CONFLICT', action: 'Review Conflict' },
                      REVISION: { label: 'REVISION', action: 'Review Revision' },
                      GOVERNANCE_WARNING: { label: 'WARNING', action: 'Open Expert Model' },
                      EVIDENCE_GAP: { label: 'EVIDENCE GAP', action: 'Review Evaluation' },
                    };
                    const BUCKETS = [
                      { key: 'NEEDS_REVIEW', label: 'Needs Review Now', hint: 'blocking or awaiting a human verdict' },
                      { key: 'CAN_WAIT', label: 'Can Wait', hint: 'informational warnings and policy-allowed items' },
                      { key: 'RESOLVED', label: `Recently Resolved`, hint: `reviewed within the last ${governanceInbox.resolved_window_days} days` },
                    ] as const;

                    if (visible.length === 0) {
                      return (
                        <div className="glass-panel rounded-xl p-12 text-center text-xs text-slate-500 italic">
                          No governance items{inboxModelFilter !== null ? ' for this Expert Model' : ''}. All clear.
                        </div>
                      );
                    }

                    const renderItem = (item: typeof visible[number], blocking = false) => (
                      <div
                        key={item.id}
                        className={`glass-panel rounded-xl p-4 flex flex-wrap items-center gap-3 ${
                          item.bucket === 'RESOLVED' ? 'opacity-60' : ''
                        } ${blocking ? 'border-rose-900/50' : ''}`}
                      >
                        <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border shrink-0 ${SEVERITY_BADGE[item.severity]}`}>
                          {item.severity}
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded border bg-slate-950 text-slate-400 border-slate-900 shrink-0">
                          {TYPE_META[item.type]?.label || item.type}
                        </span>
                        <div className="flex-1 min-w-[220px] space-y-0.5">
                          <span className="text-xs font-bold text-slate-200 block">{item.title}</span>
                          <span className="text-[10px] text-slate-400 block">{item.reason}</span>
                          <span className="text-[9px] font-mono text-slate-500 block">
                            {item.expert_model_name && <>EM-{item.expert_model_id} {item.expert_model_name} · </>}
                            {item.classification && <>{item.classification.toLowerCase().replace(/_/g, ' ')} · </>}
                            {item.confidence !== null && item.confidence !== undefined && <>confidence {item.confidence.toFixed(3)} · </>}
                            {item.status}
                            {item.created_at && <> · {new Date(item.created_at).toLocaleString()}</>}
                          </span>
                        </div>
                        {item.bucket !== 'RESOLVED' && (
                          <button
                            onClick={() => openDeepLink(item.deep_link)}
                            className="text-[10px] text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1.5 bg-cyan-950/20 px-3 py-1.5 rounded border border-cyan-900/30 transition-colors shrink-0"
                          >
                            {TYPE_META[item.type]?.action || 'Open'} <ArrowRight className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    );

                    // HIGH severity = blocks the compile gate (guaranteed by the
                    // inbox API via relationship_gate_disposition) — surfaced in a
                    // dedicated section, grouped per Expert Model.
                    const blockingItems = visible.filter(i => i.severity === 'HIGH');
                    const blockingGroups = Array.from(
                      blockingItems.reduce((groups, item) => {
                        const key = item.expert_model_id ?? -1;
                        const group = groups.get(key) || { items: [] as typeof blockingItems };
                        group.items.push(item);
                        return groups.set(key, group);
                      }, new Map<number, { items: typeof blockingItems }>()).entries()
                    );
                    const describeBlocking = (items: typeof blockingItems) => {
                      const counts = new Map<string, number>();
                      items.forEach(i => {
                        const label = i.classification
                          ? i.classification.toLowerCase().replace(/_/g, ' ')
                          : (TYPE_META[i.type]?.label || i.type).toLowerCase();
                        counts.set(label, (counts.get(label) || 0) + 1);
                      });
                      return Array.from(counts.entries())
                        .map(([label, n]) => `${n} ${label}${n > 1 ? 's' : ''}`)
                        .join(', ');
                    };

                    return (
                      <div className="space-y-6">
                        {blockingItems.length > 0 && (
                          <div className="space-y-3">
                            <h4 className="text-xs font-bold text-rose-400 tracking-wide flex items-center gap-2">
                              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                              Blocking Deployment
                              <span className="text-slate-500 font-mono text-[10px] font-normal">
                                {blockingItems.length} item{blockingItems.length > 1 ? 's' : ''} — blocks the compile gate until reviewed
                              </span>
                            </h4>
                            {blockingGroups.map(([modelId, group]) => (
                              <div key={modelId} className="space-y-2">
                                <h5 className="text-[10px] font-mono font-bold text-rose-300 flex items-center gap-2">
                                  {modelId !== -1
                                    ? <>EM-{modelId} {group.items[0].expert_model_name}</>
                                    : 'Unassigned'}
                                  <span className="text-slate-500 font-normal">— {describeBlocking(group.items)}</span>
                                </h5>
                                {group.items.map((item) => renderItem(item, true))}
                              </div>
                            ))}
                          </div>
                        )}
                        {BUCKETS.map((bucket) => {
                          const bucketItems = visible.filter(i =>
                            i.bucket === bucket.key &&
                            // HIGH items already shown in Blocking Deployment above
                            !(bucket.key === 'NEEDS_REVIEW' && i.severity === 'HIGH')
                          );
                          if (bucketItems.length === 0) return null;
                          return (
                            <div key={bucket.key} className="space-y-3">
                              <h4 className="text-xs font-bold text-slate-300 tracking-wide flex items-center gap-2">
                                {bucket.key === 'NEEDS_REVIEW' ? <AlertTriangle className="w-3.5 h-3.5 text-rose-400" /> :
                                 bucket.key === 'CAN_WAIT' ? <Clock className="w-3.5 h-3.5 text-yellow-400" /> :
                                 <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                                {bucket.label}
                                <span className="text-slate-500 font-mono text-[10px] font-normal">
                                  {bucketItems.length} item{bucketItems.length > 1 ? 's' : ''} — {bucket.hint}
                                </span>
                              </h4>
                              {bucketItems.map((item) => renderItem(item))}
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* TAB: KNOWLEDGE CONFLICTS (Conflict Review Workbench) */}
              {activeTab === 'conflicts' && (
                <div className="space-y-6">

                  {/* SCAN CONTROL BAR */}
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 text-rose-400" />
                      Conflict Review Workbench
                      <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                        Semantic contradiction detection across approved assets — before agent consumption
                      </span>
                    </h3>

                    {experts.length === 0 ? (
                      <div className="text-center py-10 text-xs text-slate-500 italic">
                        No Expert Models available. Build a model in Experts &amp; Packages first.
                      </div>
                    ) : (
                      <div className="flex flex-wrap items-end gap-4">
                        <div className="flex-1 min-w-[220px]">
                          <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Expert Model</label>
                          <select
                            value={conflictModelId ?? ''}
                            onChange={(e) => setConflictModelId(Number(e.target.value))}
                            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200"
                          >
                            {experts.map((m) => (
                              <option key={m.id} value={m.id}>EM-{m.id} — {m.name}</option>
                            ))}
                          </select>
                        </div>
                        <button
                          onClick={() => conflictModelId !== null && runConflictScan(conflictModelId)}
                          disabled={conflictScanLoading || conflictModelId === null}
                          className="py-2 px-5 bg-gradient-to-r from-rose-500 to-rose-600 text-slate-950 font-bold rounded text-xs tracking-wider uppercase disabled:opacity-40 flex items-center gap-2"
                        >
                          <Scale className="w-3.5 h-3.5" />
                          {conflictScanLoading ? 'Scanning Pairs…' : 'Run Conflict Scan'}
                        </button>

                        {conflictScanSummary && conflictScanSummary.expert_model_id === conflictModelId && (
                          <div className="flex gap-2 font-mono text-[10px]">
                            <div className="bg-slate-950/80 border border-slate-900 rounded px-3 py-1.5 text-center">
                              <span className="text-slate-500 block text-[8px] uppercase">Assets</span>
                              <span className="text-slate-200 font-bold">{conflictScanSummary.scanned_assets}</span>
                            </div>
                            <div className="bg-slate-950/80 border border-slate-900 rounded px-3 py-1.5 text-center">
                              <span className="text-slate-500 block text-[8px] uppercase">Pairs</span>
                              <span className="text-cyan-400 font-bold">{conflictScanSummary.compared_pairs}</span>
                            </div>
                            <div className="bg-slate-950/80 border border-slate-900 rounded px-3 py-1.5 text-center">
                              <span className="text-slate-500 block text-[8px] uppercase">Conflicts</span>
                              <span className="text-rose-400 font-bold">{conflictScanSummary.conflicts_found}</span>
                            </div>
                            <div className="bg-slate-950/80 border border-slate-900 rounded px-3 py-1.5 text-center">
                              <span className="text-slate-500 block text-[8px] uppercase">Supports</span>
                              <span className="text-emerald-400 font-bold">{conflictScanSummary.supports_found}</span>
                            </div>
                            {!conflictScanSummary.nli_available && (
                              <div className="bg-yellow-950/30 border border-yellow-900/40 rounded px-3 py-1.5 text-yellow-400 flex items-center">
                                NLI engine unavailable
                              </div>
                            )}
                            {conflictScanSummary.dropped_pairs > 0 && (
                              <div className="bg-yellow-950/30 border border-yellow-900/40 rounded px-3 py-1.5 text-yellow-400 flex items-center">
                                {conflictScanSummary.dropped_pairs} low-similarity pairs not scanned
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* SEMANTIC CONFLICT SCORE — standalone metric, never averaged into quality */}
                    {conflictScore && conflictScore.expert_model_id === conflictModelId && (
                      <div className="bg-slate-950/60 border border-slate-900 rounded-lg p-4 flex flex-wrap items-center gap-5">
                        <div className="text-center">
                          <span className={`text-3xl font-bold font-mono block ${
                            conflictScore.semantic_conflict_score >= 90 ? 'text-emerald-400' :
                            conflictScore.semantic_conflict_score >= 70 ? 'text-yellow-400' : 'text-rose-400'
                          }`}>
                            {conflictScore.semantic_conflict_score}
                          </span>
                          <span className="text-[9px] text-slate-500 font-mono uppercase tracking-wider">Semantic Conflict Score</span>
                        </div>
                        <div className="flex-1 min-w-[240px] space-y-1.5">
                          <p className="text-xs text-slate-300">
                            {conflictScore.semantic_conflict_summary}
                          </p>
                          {conflictScore.breakdown.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {conflictScore.breakdown.map((b, i) => (
                                <span key={i} className="text-[9px] font-mono px-2 py-0.5 rounded bg-slate-900/80 border border-slate-800 text-slate-400">
                                  {b.count}× {b.status.toLowerCase()} {b.classification.toLowerCase().replace(/_/g, ' ')} → −{b.penalty}
                                </span>
                              ))}
                            </div>
                          )}
                          <span className="text-[9px] text-slate-600 font-mono block italic">
                            Standalone integrity metric ({conflictScore.score_version}) — reported separately from quality score, never silently averaged.
                          </span>
                        </div>
                      </div>
                    )}

                    {/* STATUS FILTERS */}
                    <div className="flex gap-2 pt-1">
                      {(['ALL', 'DETECTED', 'CONFIRMED', 'DISMISSED'] as const).map((f) => (
                        <button
                          key={f}
                          onClick={() => setConflictStatusFilter(f)}
                          className={`text-[10px] font-mono px-3 py-1 rounded-full border transition-colors ${
                            conflictStatusFilter === f
                              ? 'bg-cyan-950/40 text-cyan-400 border-cyan-800'
                              : 'bg-slate-950 text-slate-500 border-slate-900 hover:text-slate-300'
                          }`}
                        >
                          {f}{f !== 'ALL' && ` (${conflicts.filter(c => c.status === f).length})`}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* CONFLICT CARDS GROUPED BY CLASSIFICATION */}
                  {(() => {
                    const visible = conflicts.filter(c =>
                      conflictStatusFilter === 'ALL' || c.status === conflictStatusFilter
                    );
                    const conflictRels = visible.filter(c => c.relationship_type === 'CONFLICTS_WITH');
                    const supportRels = visible.filter(c => c.relationship_type === 'SUPPORTS');
                    const assetById = (id: number) => assets.find(a => a.id === id);

                    const CLASS_STYLES: Record<string, { label: string; badge: string }> = {
                      DIRECT_CONTRADICTION: { label: 'Direct Contradiction', badge: 'bg-rose-950/40 text-rose-400 border-rose-900/50' },
                      TEMPORAL_SUPERSESSION: { label: 'Temporal Supersession', badge: 'bg-yellow-950/40 text-yellow-400 border-yellow-900/50' },
                      SCOPE_CONFLICT: { label: 'Scope Conflict', badge: 'bg-cyan-950/40 text-cyan-400 border-cyan-900/50' },
                      ACCESS_CONFLICT: { label: 'Access Conflict', badge: 'bg-purple-950/40 text-purple-400 border-purple-900/50' },
                    };

                    const groups = Object.keys(CLASS_STYLES)
                      .map(key => ({ key, items: conflictRels.filter(c => c.classification === key) }))
                      .filter(g => g.items.length > 0);

                    if (conflictRels.length === 0 && supportRels.length === 0) {
                      return (
                        <div className="glass-panel rounded-xl p-12 text-center text-xs text-slate-500 italic">
                          No relationships {conflictStatusFilter !== 'ALL' ? `with status ${conflictStatusFilter} ` : ''}for this Expert Model.
                          Run a conflict scan to analyze approved assets pairwise.
                        </div>
                      );
                    }

                    const renderEvidence = (assetId: number) => {
                      const asset = assetById(assetId);
                      return (
                        <div className="bg-slate-950/60 border border-slate-900 rounded p-3 space-y-1.5 flex-1 min-w-0">
                          <div className="flex justify-between items-center gap-2">
                            <span className="text-[10px] font-mono text-cyan-400 truncate">
                              [{asset?.type || 'ASSET'}] {asset?.name || `Asset #${assetId}`}
                            </span>
                            <button
                              onClick={() => {
                                if (asset) {
                                  setSelectedDocFilterId(asset.document_id);
                                  setActiveTab('assets');
                                }
                              }}
                              title="Open source asset"
                              className="text-slate-500 hover:text-cyan-400 transition-colors shrink-0"
                            >
                              <ExternalLink className="w-3 h-3" />
                            </button>
                          </div>
                          <p className="text-xs text-slate-300 font-mono italic leading-relaxed">
                            &quot;{asset?.content || 'Asset content unavailable (asset may have been deleted).'}&quot;
                          </p>
                          {asset && (
                            <span className="text-[9px] font-mono text-slate-500 block">
                              Access: {asset.access_level} · Page {asset.source_page} · {asset.source_section}
                            </span>
                          )}
                        </div>
                      );
                    };

                    const renderCard = (rel: typeof conflicts[number], isConflict: boolean) => (
                      <div
                        key={rel.id}
                        id={`conflict-${rel.id}`}
                        className={`glass-panel rounded-xl p-5 space-y-4 border-l-4 ${
                          rel.status === 'DISMISSED' ? 'opacity-55 border-l-slate-600' :
                          rel.status === 'CONFIRMED' ? (isConflict ? 'border-l-rose-500' : 'border-l-emerald-500') :
                          isConflict ? 'border-l-rose-500/70' : 'border-l-emerald-500/70'
                        } ${highlightRelationshipId === rel.id ? 'ring-2 ring-cyan-500/70' : ''}`}
                      >
                        <div className="flex flex-wrap justify-between items-center gap-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[10px] font-mono text-slate-300">
                              Asset #{rel.source_asset_id}
                            </span>
                            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                              isConflict ? 'bg-rose-950/40 text-rose-400' : 'bg-emerald-950/40 text-emerald-400'
                            }`}>
                              {rel.relationship_type === 'CONFLICTS_WITH' ? 'conflicts_with' : 'supports'}
                            </span>
                            <span className="text-[10px] font-mono text-slate-300">
                              Asset #{rel.target_asset_id}
                            </span>
                            {isConflict && rel.classification && (
                              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${CLASS_STYLES[rel.classification]?.badge || 'bg-slate-900 text-slate-400 border-slate-800'}`}>
                                {CLASS_STYLES[rel.classification]?.label || rel.classification}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 font-mono text-[10px]">
                            <span className="text-slate-500">Confidence:</span>
                            <span className={`font-bold ${rel.confidence >= 0.95 ? 'text-rose-400' : 'text-yellow-400'}`}>
                              {rel.confidence.toFixed(3)}
                            </span>
                            <span className={`px-2 py-0.5 rounded-full ${
                              rel.status === 'CONFIRMED' ? 'bg-rose-950/40 text-rose-400' :
                              rel.status === 'DISMISSED' ? 'bg-slate-900 text-slate-500' :
                              'bg-yellow-950/40 text-yellow-400'
                            }`}>
                              {rel.status}
                            </span>
                          </div>
                        </div>

                        <div className="flex flex-col md:flex-row gap-3 items-stretch">
                          {renderEvidence(rel.source_asset_id)}
                          <div className="flex items-center justify-center shrink-0">
                            {isConflict
                              ? <AlertTriangle className="w-4 h-4 text-rose-500" />
                              : <ArrowRight className="w-4 h-4 text-emerald-500" />}
                          </div>
                          {renderEvidence(rel.target_asset_id)}
                        </div>

                        {rel.status !== 'DETECTED' && (
                          <div className="bg-slate-950/40 border border-slate-900/60 rounded p-2.5 text-[10px] font-mono text-slate-400">
                            <span className="text-slate-500 uppercase">Reviewed by</span> <span className="text-cyan-400">{rel.reviewed_by}</span>
                            {rel.reviewed_at && <span className="text-slate-500"> · {new Date(rel.reviewed_at).toLocaleString()}</span>}
                            {rel.notes && (
                              <p className="text-slate-300 italic mt-1 font-sans">Reason: {rel.notes}</p>
                            )}
                          </div>
                        )}

                        {rel.status === 'DETECTED' && isConflict && (
                          conflictReview?.id === rel.id ? (
                            <div className="space-y-2 border-t border-slate-900/60 pt-3">
                              <label className="block text-[10px] text-slate-400 font-mono uppercase">
                                Decision reason — recorded in the audit ledger ({conflictReview.action === 'CONFIRMED' ? 'confirming conflict' : 'dismissing as contextual'})
                              </label>
                              <textarea
                                rows={2}
                                autoFocus
                                placeholder="e.g. Different departments; manufacturing SOP does not apply to clinical operations."
                                value={conflictReviewReason}
                                onChange={(e) => setConflictReviewReason(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200 resize-none"
                              />
                              <div className="flex gap-2">
                                <button
                                  onClick={async () => {
                                    if (conflictModelId !== null) {
                                      await reviewConflict(rel.id, conflictReview.action, conflictReviewReason.trim() || null, conflictModelId);
                                      setConflictReview(null);
                                      setConflictReviewReason('');
                                    }
                                  }}
                                  className={`text-[10px] font-mono font-bold px-3 py-1.5 rounded uppercase tracking-wider ${
                                    conflictReview.action === 'CONFIRMED'
                                      ? 'bg-rose-500 text-slate-950'
                                      : 'bg-slate-700 text-slate-100'
                                  }`}
                                >
                                  {conflictReview.action === 'CONFIRMED' ? 'Record Confirmation' : 'Record Dismissal'}
                                </button>
                                <button
                                  onClick={() => { setConflictReview(null); setConflictReviewReason(''); }}
                                  className="text-[10px] font-mono text-slate-500 hover:text-slate-300 px-3 py-1.5"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="flex gap-2 border-t border-slate-900/60 pt-3">
                              <button
                                onClick={() => { setConflictReview({ id: rel.id, action: 'CONFIRMED' }); setConflictReviewReason(''); }}
                                className="text-[10px] text-rose-400 hover:text-rose-300 font-mono flex items-center gap-1.5 bg-rose-950/20 px-3 py-1.5 rounded border border-rose-900/30 transition-colors"
                              >
                                <AlertTriangle className="w-3 h-3" /> Confirm Conflict
                              </button>
                              <button
                                onClick={() => { setConflictReview({ id: rel.id, action: 'DISMISSED' }); setConflictReviewReason(''); }}
                                className="text-[10px] text-slate-400 hover:text-slate-200 font-mono flex items-center gap-1.5 bg-slate-900/40 px-3 py-1.5 rounded border border-slate-800 transition-colors"
                              >
                                <XCircle className="w-3 h-3" /> Dismiss as Contextual
                              </button>
                            </div>
                          )
                        )}
                      </div>
                    );

                    return (
                      <div className="space-y-6">
                        {groups.map(group => (
                          <div key={group.key} className="space-y-3">
                            <h4 className="text-xs font-bold text-slate-300 tracking-wide flex items-center gap-2">
                              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${CLASS_STYLES[group.key].badge}`}>
                                {CLASS_STYLES[group.key].label}
                              </span>
                              <span className="text-slate-500 font-mono text-[10px]">{group.items.length} pair{group.items.length > 1 ? 's' : ''}</span>
                            </h4>
                            {group.items.map(rel => renderCard(rel, true))}
                          </div>
                        ))}

                        {supportRels.length > 0 && (
                          <div className="space-y-3 pt-2">
                            <h4 className="text-xs font-bold text-slate-300 tracking-wide flex items-center gap-2">
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded border bg-emerald-950/40 text-emerald-400 border-emerald-900/50">
                                Supporting Relationships
                              </span>
                              <span className="text-slate-500 font-mono text-[10px]">{supportRels.length} pair{supportRels.length > 1 ? 's' : ''}</span>
                            </h4>
                            {supportRels.map(rel => renderCard(rel, false))}
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* TAB: REVISION REVIEWS (Revision Review Workbench) */}
              {activeTab === 'revisions' && (
                <div className="space-y-6">
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                      <FileCheck className="w-4 h-4 text-yellow-400" />
                      Revision Review Workbench
                      <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                        Approved knowledge is never edited in place — review candidate revisions before they go live
                      </span>
                    </h3>

                    <div className="flex gap-2">
                      {(['PENDING', 'APPROVED', 'REJECTED', 'ALL'] as const).map((f) => {
                        const count = f === 'ALL' ? revisionQueue.length :
                          revisionQueue.filter(r => r.revision.status === (f === 'PENDING' ? 'CANDIDATE' : f)).length;
                        return (
                          <button
                            key={f}
                            onClick={() => setRevisionStatusFilter(f)}
                            className={`text-[10px] font-mono px-3 py-1 rounded-full border transition-colors ${
                              revisionStatusFilter === f
                                ? 'bg-cyan-950/40 text-cyan-400 border-cyan-800'
                                : 'bg-slate-950 text-slate-500 border-slate-900 hover:text-slate-300'
                            }`}
                          >
                            {f} ({count})
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {(() => {
                    const wanted = revisionStatusFilter === 'PENDING' ? 'CANDIDATE' : revisionStatusFilter;
                    const visible = revisionQueue.filter(r =>
                      revisionStatusFilter === 'ALL' || r.revision.status === wanted
                    );

                    if (visible.length === 0) {
                      return (
                        <div className="glass-panel rounded-xl p-12 text-center text-xs text-slate-500 italic">
                          No {revisionStatusFilter !== 'ALL' ? revisionStatusFilter.toLowerCase() + ' ' : ''}revisions.
                          Editing an approved asset creates a candidate revision that appears here for review.
                        </div>
                      );
                    }

                    // Simple word-level diff: shared prefix/suffix, highlighted middle.
                    const diffWords = (a: string, b: string) => {
                      const aw = a.split(/\s+/), bw = b.split(/\s+/);
                      let p = 0;
                      while (p < aw.length && p < bw.length && aw[p] === bw[p]) p++;
                      let s = 0;
                      while (s < aw.length - p && s < bw.length - p && aw[aw.length - 1 - s] === bw[bw.length - 1 - s]) s++;
                      return {
                        prefix: aw.slice(0, p).join(' '),
                        removed: aw.slice(p, aw.length - s).join(' '),
                        added: bw.slice(p, bw.length - s).join(' '),
                        suffix: aw.slice(aw.length - s).join(' ')
                      };
                    };

                    const shortHash = (h: string | null) => h ? h.slice(0, 16) + '…' : 'N/A';

                    return (
                      <div className="space-y-5">
                        {visible.map((item) => {
                          const rev = item.revision;
                          const hasBaseline = item.baseline_content != null;
                          const d = hasBaseline ? diffWords(item.baseline_content!, rev.content) : null;
                          const statusLabel = rev.status === 'CANDIDATE' ? 'PENDING' :
                            rev.status === 'ARCHIVED' ? 'SUPERSEDED' : rev.status;
                          return (
                            <div key={rev.id} id={`revision-${rev.id}`} className={`glass-panel rounded-xl p-5 space-y-4 border-l-4 ${
                              rev.status === 'CANDIDATE' ? 'border-l-yellow-500' :
                              rev.status === 'APPROVED' ? 'border-l-emerald-500' :
                              rev.status === 'REJECTED' ? 'border-l-rose-500/70 opacity-70' : 'border-l-slate-600 opacity-60'
                            } ${highlightRevisionId === rev.id ? 'ring-2 ring-cyan-500/70' : ''}`}>
                              <div className="flex flex-wrap justify-between items-center gap-2">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="text-[10px] font-mono bg-slate-900 text-cyan-400 px-2 py-0.5 rounded border border-slate-800 uppercase">{item.asset_type}</span>
                                  <span className="font-bold text-sm text-slate-100">{item.asset_name}</span>
                                  <span className="text-[10px] font-mono text-slate-500">
                                    {item.baseline_revision_number != null ? `Rev ${item.baseline_revision_number} → ` : ''}Rev {rev.revision_number}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2 font-mono text-[10px]">
                                  <span className="text-slate-500">{rev.created_by} · {new Date(rev.created_at).toLocaleString()}</span>
                                  <span className={`px-2 py-0.5 rounded-full ${
                                    rev.status === 'CANDIDATE' ? 'bg-yellow-950/40 text-yellow-400' :
                                    rev.status === 'APPROVED' ? 'bg-emerald-950/40 text-emerald-400' :
                                    rev.status === 'REJECTED' ? 'bg-rose-950/30 text-rose-400' : 'bg-slate-900 text-slate-500'
                                  }`}>{statusLabel}</span>
                                </div>
                              </div>

                              {rev.change_reason && (
                                <p className="text-xs text-slate-300 italic bg-slate-950/40 border border-slate-900/60 rounded p-2.5">
                                  Reason: {rev.change_reason}
                                </p>
                              )}

                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div className="bg-rose-950/10 border border-rose-900/30 rounded p-3 space-y-2">
                                  <span className="text-[9px] font-mono text-rose-400/80 uppercase tracking-wider block">
                                    − {hasBaseline ? `Rev ${item.baseline_revision_number} (current until approval)` : 'No baseline (first revision)'}
                                  </span>
                                  <p className="text-xs font-mono leading-relaxed text-slate-300">
                                    {d ? (<>
                                      {d.prefix && <span>{d.prefix} </span>}
                                      {d.removed && <span className="bg-rose-950/60 text-rose-300 line-through px-1 rounded">{d.removed}</span>}
                                      {d.suffix && <span> {d.suffix}</span>}
                                    </>) : <span className="text-slate-600 italic">—</span>}
                                  </p>
                                  <div className="text-[9px] font-mono text-slate-500 space-y-0.5 border-t border-slate-900/60 pt-1.5">
                                    <div>Content Hash: {shortHash(item.baseline_content_hash)}</div>
                                    <div>Source Hash: {shortHash(item.baseline_source_hash)}</div>
                                  </div>
                                </div>
                                <div className="bg-emerald-950/10 border border-emerald-900/30 rounded p-3 space-y-2">
                                  <span className="text-[9px] font-mono text-emerald-400/80 uppercase tracking-wider block">
                                    + Rev {rev.revision_number} ({statusLabel.toLowerCase()})
                                  </span>
                                  <p className="text-xs font-mono leading-relaxed text-slate-300">
                                    {d ? (<>
                                      {d.prefix && <span>{d.prefix} </span>}
                                      {d.added && <span className="bg-emerald-950/60 text-emerald-300 px-1 rounded">{d.added}</span>}
                                      {d.suffix && <span> {d.suffix}</span>}
                                    </>) : rev.content}
                                  </p>
                                  <div className="text-[9px] font-mono text-slate-500 space-y-0.5 border-t border-slate-900/60 pt-1.5">
                                    <div>Content Hash: {shortHash(rev.content_hash)}</div>
                                    <div>Source Hash: {shortHash(rev.source_hash)}</div>
                                  </div>
                                </div>
                              </div>

                              {rev.status === 'APPROVED' && rev.approved_by && (
                                <div className="bg-slate-950/40 border border-slate-900/60 rounded p-2.5 text-[10px] font-mono text-slate-400">
                                  <span className="text-slate-500 uppercase">Approved by</span> <span className="text-emerald-400">{rev.approved_by}</span>
                                  {rev.approved_at && <span className="text-slate-500"> · {new Date(rev.approved_at).toLocaleString()}</span>}
                                </div>
                              )}

                              {rev.status === 'CANDIDATE' && (
                                revisionReview?.id === rev.id ? (
                                  <div className="space-y-2 border-t border-slate-900/60 pt-3">
                                    <label className="block text-[10px] text-slate-400 font-mono uppercase">
                                      Review reason (required) — recorded in the audit ledger ({revisionReview.action === 'APPROVE' ? 'approving revision' : 'rejecting revision'})
                                    </label>
                                    <textarea
                                      rows={2}
                                      autoFocus
                                      placeholder="e.g. Legal directive verified against source document."
                                      value={revisionReviewReason}
                                      onChange={(e) => setRevisionReviewReason(e.target.value)}
                                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200 resize-none"
                                    />
                                    <div className="flex gap-2">
                                      <button
                                        disabled={!revisionReviewReason.trim()}
                                        onClick={async () => {
                                          if (activeProjectId !== null) {
                                            await reviewRevision(rev.id, revisionReview.action, revisionReviewReason.trim(), activeProjectId);
                                            setRevisionReview(null);
                                            setRevisionReviewReason('');
                                          }
                                        }}
                                        className={`text-[10px] font-mono font-bold px-3 py-1.5 rounded uppercase tracking-wider disabled:opacity-40 ${
                                          revisionReview.action === 'APPROVE' ? 'bg-emerald-500 text-slate-950' : 'bg-rose-500 text-slate-950'
                                        }`}
                                      >
                                        {revisionReview.action === 'APPROVE' ? 'Record Approval' : 'Record Rejection'}
                                      </button>
                                      <button
                                        onClick={() => { setRevisionReview(null); setRevisionReviewReason(''); }}
                                        className="text-[10px] font-mono text-slate-500 hover:text-slate-300 px-3 py-1.5"
                                      >
                                        Cancel
                                      </button>
                                    </div>
                                    {revisionReview.action === 'APPROVE' && (
                                      <span className="text-[9px] text-slate-500 font-mono italic block">
                                        Approval supersedes the current revision; conflict rescans of affected Expert Models are scheduled in the background and refresh the Inbox when complete.
                                      </span>
                                    )}
                                  </div>
                                ) : (
                                  <div className="flex gap-2 border-t border-slate-900/60 pt-3">
                                    <button
                                      onClick={() => { setRevisionReview({ id: rev.id, action: 'APPROVE' }); setRevisionReviewReason(''); }}
                                      className="text-[10px] text-emerald-400 hover:text-emerald-300 font-mono flex items-center gap-1.5 bg-emerald-950/20 px-3 py-1.5 rounded border border-emerald-900/30 transition-colors"
                                    >
                                      <CheckCircle2 className="w-3 h-3" /> Approve Revision
                                    </button>
                                    <button
                                      onClick={() => { setRevisionReview({ id: rev.id, action: 'REJECT' }); setRevisionReviewReason(''); }}
                                      className="text-[10px] text-rose-400 hover:text-rose-300 font-mono flex items-center gap-1.5 bg-rose-950/20 px-3 py-1.5 rounded border border-rose-900/30 transition-colors"
                                    >
                                      <XCircle className="w-3 h-3" /> Reject Revision
                                    </button>
                                  </div>
                                )
                              )}
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* TAB: AGENT CENTER (MCP gateway operations) */}
              {activeTab === 'agents' && (
                <div className="space-y-6">
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <div className="flex justify-between items-center border-b border-slate-900 pb-3">
                      <h3 className="font-bold text-sm text-slate-200 tracking-wide flex items-center gap-2">
                        <Bot className="w-4 h-4 text-purple-400" />
                        Agent Center
                        <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                          MCP gateway activity — read-only governance surface, every call audit-logged
                        </span>
                      </h3>
                      <button onClick={() => fetchAgentActivity()}
                        className="text-[10px] text-purple-400 hover:text-purple-300 font-mono bg-purple-950/30 border border-purple-900/40 rounded px-3 py-1.5 uppercase tracking-wider">
                        Refresh
                      </button>
                    </div>

                    {agentActivity && (
                      <div className="grid grid-cols-3 gap-3 font-mono text-center">
                        <div className="bg-slate-950/80 border border-slate-900 rounded-lg p-3">
                          <span className="text-slate-500 block text-[9px] uppercase">Connected Agents</span>
                          <span className="text-purple-400 font-bold text-xl">{agentActivity.agents.length}</span>
                        </div>
                        <div className="bg-slate-950/80 border border-slate-900 rounded-lg p-3">
                          <span className="text-slate-500 block text-[9px] uppercase">Gateway Calls</span>
                          <span className="text-cyan-400 font-bold text-xl">{agentActivity.total_calls}</span>
                        </div>
                        <div className="bg-slate-950/80 border border-slate-900 rounded-lg p-3">
                          <span className="text-slate-500 block text-[9px] uppercase">Access Denials</span>
                          <span className={`font-bold text-xl ${agentActivity.total_denied > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>{agentActivity.total_denied}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {!agentActivity || agentActivity.agents.length === 0 ? (
                    <div className="glass-panel rounded-xl p-12 text-center space-y-3">
                      <Bot className="w-10 h-10 text-slate-600 mx-auto" />
                      <p className="text-xs text-slate-500 italic">
                        No agent activity yet. Connect an MCP client (Claude Desktop, Claude Code, Cursor) to
                        backend/mcp_server.py with EM_AGENT_ID and EM_AGENT_CLEARANCE set — every tool call will appear here.
                      </p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                      {agentActivity.agents.map((a) => (
                        <div key={a.agent_id} className="glass-panel rounded-xl p-5 space-y-3.5 border-l-4 border-l-purple-500/70">
                          <div className="flex flex-wrap justify-between items-center gap-2">
                            <div className="flex items-center gap-2">
                              <Bot className="w-4 h-4 text-purple-400" />
                              <span className="font-bold text-sm text-slate-100 font-mono">{a.agent_id}</span>
                            </div>
                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                              a.clearance === 'EXECUTIVE' ? 'bg-rose-950/40 text-rose-400 border-rose-900/50' :
                              a.clearance === 'RESTRICTED' ? 'bg-yellow-950/40 text-yellow-400 border-yellow-900/50' :
                              a.clearance === 'INTERNAL' ? 'bg-cyan-950/30 text-cyan-400 border-cyan-900/40' :
                              'bg-slate-900 text-slate-400 border-slate-800'
                            }`}>
                              Clearance: {a.clearance || 'UNKNOWN'}
                            </span>
                          </div>

                          <div className="grid grid-cols-3 gap-2 bg-slate-950/80 p-2.5 rounded border border-slate-900 text-center font-mono text-[10px]">
                            <div>
                              <span className="text-slate-500 block text-[8px] uppercase">Calls</span>
                              <span className="text-slate-200 font-bold text-xs">{a.calls}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block text-[8px] uppercase">Denied</span>
                              <span className={`font-bold text-xs ${a.denied > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>{a.denied}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block text-[8px] uppercase">Refused Answers</span>
                              <span className={`font-bold text-xs ${a.blocked_answers > 0 ? 'text-yellow-400' : 'text-slate-200'}`}>{a.blocked_answers}</span>
                            </div>
                          </div>

                          <div className="space-y-1.5">
                            <span className="text-[9px] text-slate-500 font-mono uppercase block">Tools Used</span>
                            <div className="flex flex-wrap gap-1.5">
                              {Object.entries(a.tools).sort((x, y) => y[1] - x[1]).map(([tool, count]) => (
                                <span key={tool} className="text-[9px] font-mono px-2 py-0.5 rounded bg-slate-900/80 border border-slate-800 text-slate-300">
                                  {tool} × {count}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div className="text-[9px] font-mono text-slate-500 border-t border-slate-900/60 pt-2 flex flex-wrap gap-x-4 gap-y-1">
                            <span>Models: {a.expert_models.length ? a.expert_models.map(m => `EM-${m}`).join(', ') : '—'}</span>
                            <span>Last seen: {new Date(a.last_seen).toLocaleString()}</span>
                            <span>{a.gateway_version}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 5: AUDIT LEDGER EXPLORER */}
              {activeTab === 'audit' && (
                <div className="space-y-6">
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <div className="flex justify-between items-center border-b border-slate-900 pb-3">
                      <h3 className="font-bold text-sm text-slate-200 tracking-wide flex items-center gap-2">
                        <History className="w-4 h-4 text-cyan-400" />
                        Audit Ledger Explorer
                        <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                          Immutable event stream — what did the agent know, cite, and rely on?
                        </span>
                      </h3>
                      <button
                        onClick={() => fetchAuditTrail({
                          actor: auditActor.trim() || undefined,
                          target_id: auditTarget.trim() || undefined,
                          since: auditSince || undefined,
                          until: auditUntil || undefined,
                        })}
                        className="text-[10px] text-cyan-400 hover:text-cyan-300 font-mono bg-cyan-950/30 border border-cyan-900/40 rounded px-3 py-1.5 uppercase tracking-wider"
                      >
                        Apply Filters
                      </button>
                    </div>

                    {/* FILTER BAR */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div>
                        <label className="block text-[10px] text-slate-400 font-mono mb-1 uppercase">Actor / Agent</label>
                        <input type="text" placeholder="e.g. live-verification-agent" value={auditActor}
                          onChange={(e) => setAuditActor(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-[11px] focus:border-cyan-500 outline-none text-slate-200" />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400 font-mono mb-1 uppercase">Target (model / asset)</label>
                        <input type="text" placeholder="e.g. 11" value={auditTarget}
                          onChange={(e) => setAuditTarget(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-[11px] focus:border-cyan-500 outline-none text-slate-200" />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400 font-mono mb-1 uppercase">From</label>
                        <input type="date" value={auditSince} onChange={(e) => setAuditSince(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-[11px] focus:border-cyan-500 outline-none text-slate-200" />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400 font-mono mb-1 uppercase">To</label>
                        <input type="date" value={auditUntil} onChange={(e) => setAuditUntil(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-[11px] focus:border-cyan-500 outline-none text-slate-200" />
                      </div>
                    </div>

                    {/* CATEGORY CHIPS */}
                    <div className="flex flex-wrap gap-2">
                      {([
                        ['ALL', 'All'], ['QUERIES', 'Answer Traces'], ['GATEWAY', 'Agent Gateway'],
                        ['PUBLICATION', 'Compile Gates'], ['REVISIONS', 'Revisions'],
                        ['CONFLICTS', 'Conflicts'], ['ASSETS', 'Assets'], ['DOCUMENTS', 'Documents']
                      ] as const).map(([key, label]) => (
                        <button key={key} onClick={() => setAuditCategory(key)}
                          className={`text-[10px] font-mono px-3 py-1 rounded-full border transition-colors ${
                            auditCategory === key
                              ? 'bg-cyan-950/40 text-cyan-400 border-cyan-800'
                              : 'bg-slate-950 text-slate-500 border-slate-900 hover:text-slate-300'
                          }`}>
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* EVENT LIST WITH TRACE VIEWS */}
                  {(() => {
                    const inCategory = (t: string) => {
                      switch (auditCategory) {
                        case 'QUERIES': return t.startsWith('ASK_EXPERT');
                        case 'GATEWAY': return t === 'MCP_TOOL_CALLED';
                        case 'PUBLICATION': return t === 'AGENT_PACKAGE_CREATED' || t.startsWith('GOVERNANCE_BLOCKED');
                        case 'REVISIONS': return t.startsWith('ASSET_REVISION');
                        case 'CONFLICTS': return t.startsWith('KNOWLEDGE_CONFLICT') || t === 'CONFLICT_SCAN_COMPLETED';
                        case 'ASSETS': return t.startsWith('ASSET_') && !t.startsWith('ASSET_REVISION');
                        case 'DOCUMENTS': return t.startsWith('DOCUMENT');
                        default: return true;
                      }
                    };
                    const visible = auditEvents.filter(e => inCategory(e.event_type));

                    const chipClass = (t: string) =>
                      t.startsWith('ASK_EXPERT_BLOCKED') || t.startsWith('GOVERNANCE_BLOCKED') ? 'bg-rose-950/40 text-rose-400 border-rose-900/50' :
                      t.startsWith('ASK_EXPERT') ? 'bg-cyan-950/40 text-cyan-400 border-cyan-900/40' :
                      t === 'MCP_TOOL_CALLED' ? 'bg-purple-950/40 text-purple-400 border-purple-900/50' :
                      t.startsWith('ASSET_REVISION') ? 'bg-yellow-950/40 text-yellow-400 border-yellow-900/50' :
                      t.startsWith('KNOWLEDGE_CONFLICT') || t === 'CONFLICT_SCAN_COMPLETED' ? 'bg-orange-950/40 text-orange-400 border-orange-900/50' :
                      t === 'AGENT_PACKAGE_CREATED' ? 'bg-emerald-950/40 text-emerald-400 border-emerald-900/50' :
                      'bg-slate-900 text-slate-400 border-slate-800';

                    const parse = (details: string) => { try { return JSON.parse(details); } catch { return null; } };
                    const short = (h: unknown) => typeof h === 'string' && h.length > 18 ? h.slice(0, 18) + '…' : String(h ?? '—');

                    const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
                      <div className="flex gap-2 items-baseline">
                        <span className="text-[9px] font-mono text-slate-500 uppercase w-40 shrink-0">{label}</span>
                        <span className="text-[11px] text-slate-300 font-mono break-all">{children}</span>
                      </div>
                    );

                    const renderTrace = (evt: typeof auditEvents[number]) => {
                      const t = evt.event_type;
                      const d = parse(evt.details);
                      if (!d) return <pre className="text-[10px] text-slate-400 font-mono whitespace-pre-wrap">{evt.details}</pre>;

                      if (t.startsWith('ASK_EXPERT')) {
                        return (
                          <div className="space-y-1.5">
                            <Row label="Who asked">{d.operator} <span className="text-slate-500">· clearance {d.caller_access_level}</span></Row>
                            <Row label="Question">{d.question}</Row>
                            <Row label="Retrieved assets">{(d.retrieved_assets || []).join(', ') || 'none'}</Row>
                            {(d.access_blocked_assets || []).length > 0 && (
                              <Row label="Blocked by clearance"><span className="text-rose-400">{d.access_blocked_assets.join(', ')}</span></Row>
                            )}
                            <Row label="Validated citations">
                              {Array.isArray(d.citations) && d.citations.length > 0
                                ? d.citations.map((c: { asset_id: number; revision: number | null }) =>
                                    `asset ${c.asset_id}${c.revision != null ? ` (rev ${c.revision})` : ''}`).join(', ')
                                : (d.used_evidence_ids || []).join(', ') || 'none'}
                            </Row>
                            {(d.contradicted_claims || []).length > 0 && (
                              <Row label="Contradicted claims"><span className="text-rose-400">{d.contradicted_claims.join(' | ')}</span></Row>
                            )}
                            {(d.unsupported_claims || []).length > 0 && (
                              <Row label="Unsupported claims">{d.unsupported_claims.join(' | ')}</Row>
                            )}
                            <Row label="Verdict">
                              <span className={d.verification_status === 'VERIFIED' ? 'text-emerald-400' : d.verification_status === 'PARTIALLY_VERIFIED' ? 'text-yellow-400' : 'text-rose-400'}>
                                {d.verification_status}
                              </span>
                              <span className="text-slate-500"> · coverage {d.coverage_score} · confidence {d.confidence_score}</span>
                            </Row>
                            {d.verifier && (
                              <Row label="Verifier">{d.verifier.method} · {d.verifier.model_id || '—'} · weights {short(d.verifier.weights_hash)} · claims via {d.verifier.claim_decomposition || '—'}</Row>
                            )}
                            <Row label="Answer hash">{short(d.answer_hash)}</Row>
                          </div>
                        );
                      }
                      if (t === 'MCP_TOOL_CALLED') {
                        return (
                          <div className="space-y-1.5">
                            <Row label="Agent">{d.agent_id} <span className="text-slate-500">· clearance {d.clearance}</span></Row>
                            <Row label="Tool">{d.tool_name} <span className="text-slate-500">({d.gateway_version})</span></Row>
                            <Row label="Expert model">EM-{d.expert_model_id}</Row>
                            {d.question && <Row label="Question">{d.question}</Row>}
                          </div>
                        );
                      }
                      if (t === 'GOVERNANCE_BLOCKED_UNRESOLVED_CONFLICTS') {
                        return (
                          <div className="space-y-1.5">
                            <Row label="Attempted package">{d.attempted_package_name}</Row>
                            <Row label="Verdict"><span className="text-rose-400">PUBLICATION BLOCKED</span></Row>
                            {(d.blocking_conflicts || []).map((b: { reason: string; classification: string | null; source_asset_id: number | null; target_asset_id: number | null; confidence: number | null }, i: number) => (
                              <Row key={i} label={`Blocking conflict ${i + 1}`}>
                                {b.reason}{b.classification ? ` · ${b.classification}` : ''}{b.source_asset_id ? ` · assets ${b.source_asset_id}↔${b.target_asset_id}` : ''}{b.confidence ? ` · conf ${b.confidence}` : ''}
                              </Row>
                            ))}
                            <Row label="Policy">confirmed={d.policy?.confirmed_policy} · blocking classes: {(d.policy?.blocking_classifications || []).join(', ')}</Row>
                          </div>
                        );
                      }
                      if (t === 'AGENT_PACKAGE_CREATED' && d.compile_gate) {
                        return (
                          <div className="space-y-1.5">
                            <Row label="Package">{d.package_name} <span className="text-slate-500">· EM-{d.expert_model_id} · v{d.governance_version}</span></Row>
                            <Row label="Gate verdict"><span className="text-emerald-400">ALLOWED</span></Row>
                            <Row label="Conflict scan performed">{String(d.compile_gate.conflict_scan_performed)}</Row>
                            <Row label="Advisory / dismissed">{d.compile_gate.advisory_conflicts} / {d.compile_gate.dismissed_conflicts}</Row>
                            <Row label="Policy">confirmed={d.compile_gate.policy?.confirmed_policy}</Row>
                          </div>
                        );
                      }
                      if (t.startsWith('ASSET_REVISION')) {
                        return (
                          <div className="space-y-1.5">
                            <Row label="Asset / revision">asset {d.asset_id} · rev {d.revision_number}</Row>
                            {d.supersedes_revision_id != null && <Row label="Supersedes">revision row {d.supersedes_revision_id}</Row>}
                            {d.superseded_revision_id != null && <Row label="Superseded">revision row {d.superseded_revision_id}</Row>}
                            {d.change_reason && <Row label="Change reason">{d.change_reason}</Row>}
                            {d.notes && <Row label="Review notes">{d.notes}</Row>}
                            {d.content_hash && <Row label="Content hash">{short(d.content_hash)}</Row>}
                            {(d.post_approval_scans || []).map((s: { expert_model_id: number; conflicts_found?: number; invalidated_reviews?: number; semantic_conflict_score?: number }, i: number) => (
                              <Row key={i} label={`Auto-rescan EM-${s.expert_model_id}`}>
                                {s.conflicts_found ?? 0} conflicts · {s.invalidated_reviews ?? 0} verdicts invalidated · score {s.semantic_conflict_score}
                              </Row>
                            ))}
                          </div>
                        );
                      }
                      if (t.startsWith('KNOWLEDGE_CONFLICT')) {
                        return (
                          <div className="space-y-1.5">
                            <Row label="Pair">assets {d.source_asset_id} ↔ {d.target_asset_id}</Row>
                            {d.classification && <Row label="Classification">{d.classification}</Row>}
                            {d.confidence != null && <Row label="Confidence">{d.confidence}</Row>}
                            {d.notes && <Row label="Decision reason">{d.notes}</Row>}
                            {d.verifier && <Row label="Verifier">{d.verifier.method} · weights {short(d.verifier.weights_hash)}</Row>}
                          </div>
                        );
                      }
                      if (t === 'CONFLICT_SCAN_COMPLETED') {
                        return (
                          <div className="space-y-1.5">
                            <Row label="Scanned / pairs">{d.scanned_assets} assets · {d.compared_pairs} pairs{d.dropped_pairs ? ` · ${d.dropped_pairs} dropped` : ''}</Row>
                            <Row label="Found">{d.conflicts_found} conflicts · {d.supports_found} supports</Row>
                            {d.semantic_conflict_score != null && <Row label="Conflict score">{d.semantic_conflict_score} — {d.semantic_conflict_summary}</Row>}
                          </div>
                        );
                      }
                      return <pre className="text-[10px] text-slate-400 font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">{JSON.stringify(d, null, 2)}</pre>;
                    };

                    return (
                      <div className="glass-panel p-6 rounded-xl">
                        <div className="text-[10px] font-mono text-slate-500 pb-3">{visible.length} event{visible.length === 1 ? '' : 's'}</div>
                        <div className="space-y-2 max-h-[560px] overflow-y-auto pr-2">
                          {visible.length === 0 ? (
                            <div className="text-slate-500 italic text-xs text-center py-10">No events match the current filters.</div>
                          ) : visible.map((evt) => {
                            const expanded = expandedEventId === evt.id;
                            return (
                              <div key={evt.id} className={`bg-slate-950/50 border rounded-lg transition-colors ${expanded ? 'border-cyan-900/60' : 'border-slate-900 hover:border-slate-800'}`}>
                                <div className="flex flex-wrap items-center gap-2 p-2.5 cursor-pointer"
                                  onClick={() => setExpandedEventId(expanded ? null : evt.id)}>
                                  <span className="text-[10px] text-slate-500 font-mono w-36 shrink-0">{new Date(evt.timestamp).toLocaleString()}</span>
                                  <span className={`text-[9px] font-mono px-2 py-0.5 rounded border uppercase ${chipClass(evt.event_type)}`}>{evt.event_type}</span>
                                  <span className="text-[10px] text-slate-400 font-mono">{evt.actor}</span>
                                  {evt.target_id && <span className="text-[9px] text-slate-600 font-mono ml-auto">target {evt.target_id}</span>}
                                </div>
                                {expanded && (
                                  <div className="border-t border-slate-900/60 p-3.5">
                                    {renderTrace(evt)}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* TAB 6: ASK EXPERT CONSOLE (Sprint 1 UI Shell) */}
              {activeTab === 'console' && (
                <div className="space-y-6">
                  {experts.length === 0 ? (
                    <div className="glass-panel p-8 rounded-xl text-center space-y-4 max-w-lg mx-auto mt-10">
                      <HelpCircle className="w-12 h-12 text-slate-500 mx-auto" />
                      <h4 className="font-bold text-sm text-slate-200 tracking-wide">No Expert Models Compiled Yet</h4>
                      <p className="text-xs text-slate-400">
                        ExpertMachina restricts queries strictly to the context of a compiled Expert Model. Build one to get started.
                      </p>
                      <button
                        onClick={() => setActiveTab('experts')}
                        className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-cyan-600 text-slate-950 font-bold rounded text-xs tracking-wider uppercase transition-all hover:scale-[1.02]"
                      >
                        Create Expert Model
                      </button>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                      
                      {/* Left Sidebar: Controls & History */}
                      <div className="lg:col-span-1 space-y-6">
                        <div className="glass-panel p-5 rounded-xl space-y-4">
                          <h4 className="font-bold text-xs text-slate-400 font-mono uppercase tracking-wider">Scoping Parameters</h4>
                          
                          <div className="space-y-1">
                            <label className="block text-[10px] text-slate-500 font-mono uppercase">Target Expert Model</label>
                            <select
                              value={selectedExpertId || ''}
                              onChange={(e) => setSelectedExpertId(Number(e.target.value))}
                              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:border-cyan-500 outline-none"
                            >
                              {experts.map(m => (
                                <option key={m.id} value={m.id}>{m.name}</option>
                              ))}
                            </select>
                          </div>

                          <div className="pt-2 border-t border-slate-900/60">
                            <label className="block text-[10px] text-slate-500 font-mono uppercase mb-2">Sample Quick Queries</label>
                            <div className="space-y-1.5">
                              <button
                                onClick={() => setConsoleQuestion("What is the deviation logging SLA threshold?")}
                                className="w-full text-left p-2 bg-slate-950 border border-slate-900 hover:border-slate-800 rounded text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
                              >
                                Deviation logging SLA threshold
                              </button>
                              <button
                                onClick={() => setConsoleQuestion("What is the SLA refund percentage for late delivery?")}
                                className="w-full text-left p-2 bg-slate-950 border border-slate-900 hover:border-slate-800 rounded text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
                              >
                                SLA refund percentage for late delivery
                              </button>
                              <button
                                onClick={() => setConsoleQuestion("Does clinical monitoring cover remote audits?")}
                                className="w-full text-left p-2 bg-slate-950 border border-slate-900 hover:border-slate-800 rounded text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
                              >
                                Clinical monitoring remote audits
                              </button>
                            </div>
                          </div>
                        </div>

                        {/* Query Session History */}
                        <div className="glass-panel p-5 rounded-xl space-y-4">
                          <h4 className="font-bold text-xs text-slate-400 font-mono uppercase tracking-wider">Session Queries</h4>
                          <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                            {consoleHistory.length === 0 ? (
                              <div className="text-[11px] text-slate-500 italic py-2">No queries submitted in this session.</div>
                            ) : (
                              consoleHistory.map((hist, idx) => (
                                <div key={idx} className="p-2 rounded bg-slate-950/40 border border-slate-900 space-y-1">
                                  <div className="flex justify-between items-center text-[9px] font-mono">
                                    <span className="text-slate-500 truncate max-w-[100px]">{hist.expert_model}</span>
                                    <span className={`px-1 rounded ${
                                      hist.verification_status === 'VERIFIED' ? 'text-emerald-400 bg-emerald-950/20' :
                                      hist.verification_status === 'PARTIALLY_VERIFIED' ? 'text-amber-400 bg-amber-950/20' :
                                      'text-rose-400 bg-rose-950/20'
                                    }`}>
                                      {hist.verification_status}
                                    </span>
                                  </div>
                                  <p className="text-[11px] text-slate-300 truncate">{hist.question}</p>
                                </div>
                              ))
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Right Panel: Chat interface & verification trace */}
                      <div className="lg:col-span-2 space-y-6">
                        
                        {/* Ask input box */}
                        <form onSubmit={handleConsoleQuery} className="glass-panel p-4 rounded-xl flex items-center gap-3">
                          <input
                            type="text"
                            value={consoleQuestion}
                            onChange={(e) => setConsoleQuestion(e.target.value)}
                            placeholder="Ask a compliance question grounded in the selected expert model..."
                            className="flex-1 bg-slate-950 border border-slate-850 focus:border-cyan-500 text-xs text-slate-200 px-3 py-2.5 rounded outline-none"
                            disabled={consoleLoading}
                          />
                          <button
                            type="submit"
                            disabled={consoleLoading || !consoleQuestion.trim()}
                            className="bg-cyan-500 hover:bg-cyan-600 disabled:opacity-50 disabled:hover:bg-cyan-500 text-slate-950 px-4 py-2.5 rounded font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 transition-colors"
                          >
                            <Send className="w-3.5 h-3.5" />
                            <span>Ask</span>
                          </button>
                        </form>

                        {/* Output verification dashboard */}
                        <div className="min-h-[300px]">
                          {consoleLoading ? (
                            <div className="glass-panel p-8 rounded-xl flex flex-col items-center justify-center min-h-[300px] text-center space-y-4">
                              <div className="relative w-12 h-12">
                                <span className="absolute inset-0 rounded-full border-2 border-cyan-950"></span>
                                <span className="absolute inset-0 rounded-full border-t-2 border-cyan-400 animate-spin"></span>
                              </div>
                              <p className="text-xs text-cyan-400 font-mono tracking-wider animate-pulse">{consoleStep}</p>
                            </div>
                          ) : consoleResponse ? (
                            <div className="space-y-6 animate-fade-in">
                              
                              {/* Answer block */}
                              <div className={`glass-panel p-6 rounded-xl border-t-2 space-y-4 ${
                                consoleResponse.verification_status === 'VERIFIED' ? 'border-t-emerald-500' :
                                consoleResponse.verification_status === 'PARTIALLY_VERIFIED' ? 'border-t-amber-500' :
                                'border-t-rose-500'
                              }`}>
                                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-900/60 pb-3">
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs font-bold text-slate-200 tracking-wide">Grounded Response</span>
                                    <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold tracking-wide ${
                                      consoleResponse.verification_status === 'VERIFIED' ? 'text-emerald-400 bg-emerald-950/30 border border-emerald-900/40' :
                                      consoleResponse.verification_status === 'PARTIALLY_VERIFIED' ? 'text-amber-400 bg-amber-950/30 border border-amber-900/40' :
                                      'text-rose-400 bg-rose-950/30 border border-rose-900/40'
                                    }`}>
                                      {consoleResponse.verification_status.replace('_', ' ')}
                                    </span>
                                  </div>
                                  
                                  <div className="flex items-center gap-3">
                                    <div className="text-right">
                                      <span className="block text-[8px] text-slate-500 font-mono uppercase">Coverage</span>
                                      <span className={`text-xs font-mono font-bold ${
                                        consoleResponse.coverage_score >= 0.95 ? 'text-emerald-400' :
                                        consoleResponse.coverage_score >= 0.80 ? 'text-amber-400' :
                                        'text-rose-400'
                                      }`}>
                                        {(consoleResponse.coverage_score * 100).toFixed(0)}%
                                      </span>
                                    </div>
                                    <div className="text-right">
                                      <span className="block text-[8px] text-slate-500 font-mono uppercase">Confidence</span>
                                      <span className="text-xs font-mono text-cyan-400 font-bold">
                                        {(consoleResponse.confidence_score * 100).toFixed(0)}%
                                      </span>
                                    </div>
                                  </div>
                                </div>

                                {consoleResponse.verification_status === 'INSUFFICIENT_EVIDENCE' ? (
                                  <div className="p-4 rounded bg-rose-950/20 border border-rose-900/30 space-y-2">
                                    <div className="flex items-center gap-2 text-rose-400 text-xs font-bold font-mono">
                                      <AlertTriangle className="w-4 h-4" />
                                      <span>COMPLIANCE BOUNDARY BLOCKED</span>
                                    </div>
                                    <p className="text-xs text-slate-400 leading-relaxed">
                                      No approved evidence could be verified in the selected Expert Model to back this response. Answer generation aborted to maintain strict compliance boundaries.
                                    </p>
                                  </div>
                                ) : (
                                  <div className="space-y-4">
                                    {consoleResponse.verification_status === 'PARTIALLY_VERIFIED' && (
                                      <div className="flex items-start gap-2 p-3 rounded bg-amber-950/10 border border-amber-900/30 text-[11px] text-amber-400">
                                        <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                                        <span>Warning: Paragraph matches are below 95%. Synthesized answer contains ungrounded training claims. Treat citations as primary truths.</span>
                                      </div>
                                    )}
                                    <p className="text-xs text-slate-300 leading-relaxed font-sans font-medium whitespace-pre-wrap">
                                      {consoleResponse.answer}
                                    </p>
                                  </div>
                                )}
                              </div>

                              {/* Evidence list */}
                              {consoleResponse.citations.length > 0 && (
                                <div className="space-y-3">
                                  <h5 className="font-bold text-xs text-slate-400 font-mono uppercase tracking-wider flex items-center gap-1.5">
                                    <FileCheck className="w-4 h-4 text-emerald-400" />
                                    <span>Knowledge Chain of Custody citations ({consoleResponse.citations.length})</span>
                                  </h5>

                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {consoleResponse.citations.map((cite, idx) => (
                                      <div key={idx} className="glass-panel p-4 rounded-lg space-y-3 relative overflow-hidden border-l-2 border-l-emerald-500">
                                        <div className="flex justify-between items-start">
                                          <div>
                                            <span className="block text-[8px] text-slate-500 font-mono uppercase">Asset Citation</span>
                                            <span className="text-xs font-bold text-slate-200">{cite.name}</span>
                                          </div>
                                          <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/20 text-emerald-400 border border-emerald-900/40 uppercase">
                                            {cite.asset_status}
                                          </span>
                                        </div>

                                        <p className="text-[11px] text-slate-400 italic font-mono bg-slate-950/30 p-2 rounded">
                                          &quot;{cite.content}&quot;
                                        </p>

                                        <div className="grid grid-cols-2 gap-2 border-t border-slate-900/80 pt-2 text-[9px] font-mono text-slate-500">
                                          <div>
                                            <span className="block text-[8px] text-slate-600">SOURCE FILE</span>
                                            <span className="text-slate-400">{cite.source_document}</span>
                                          </div>
                                          <div>
                                            <span className="block text-[8px] text-slate-600">LOCATOR</span>
                                            <span className="text-slate-400">Page {cite.source_page} | {cite.source_section.split(':')[0]}</span>
                                          </div>
                                          <div className="col-span-2">
                                            <span className="block text-[8px] text-slate-600">BLOCK HASH</span>
                                            <span className="text-slate-400 block truncate">{cite.source_hash}</span>
                                          </div>
                                          <div className="col-span-2">
                                            <span className="block text-[8px] text-slate-600">APPROVAL LEDGER</span>
                                            <span className="text-slate-400">Approved by {cite.approved_by} on {new Date(cite.approved_at).toLocaleString()}</span>
                                          </div>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                            </div>
                          ) : (
                            <div className="glass-panel p-8 rounded-xl flex flex-col items-center justify-center min-h-[300px] text-center space-y-4">
                              <HelpCircle className="w-10 h-10 text-slate-500" />
                              <h4 className="font-bold text-xs text-slate-400 font-mono uppercase tracking-wider">Awaiting Operator Query</h4>
                              <p className="text-xs text-slate-500 max-w-sm">
                                Enter a question or pick one of the sample quick queries to audit response trust layers.
                              </p>
                            </div>
                          )}
                        </div>

                      </div>

                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* NEW WORKSPACE PROJECT MODAL */}
      {showNewProjectModal && (
        <div className="fixed inset-0 bg-[#070b12]/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="glass-panel p-6 rounded-xl w-full max-w-md space-y-4">
            <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3">
              Initialize Knowledge Workspace Project
            </h3>
            
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Project Name</label>
                <input 
                  type="text" 
                  required
                  placeholder="e.g. Q3 Compliance Transformation"
                  value={projectName} 
                  onChange={(e) => setProjectName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200" 
                />
              </div>

              <div>
                <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Description</label>
                <textarea
                  rows={3}
                  placeholder="Enter project goals and scope boundaries"
                  value={projectDesc}
                  onChange={(e) => setProjectDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200 resize-none"
                ></textarea>
              </div>

              <div className="flex items-center gap-3 border-t border-slate-900 pt-4">
                <button 
                  type="submit" 
                  className="flex-1 py-2 bg-gradient-to-r from-cyan-500 to-cyan-600 text-slate-950 font-bold rounded text-xs tracking-wider uppercase"
                >
                  Create
                </button>
                <button 
                  type="button" 
                  onClick={() => setShowNewProjectModal(false)}
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-850 text-slate-400 rounded text-xs border border-slate-800 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
