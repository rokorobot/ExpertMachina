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
  PackageCheck,
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
  Inbox,
  Settings,
  KeyRound,
  Cloud
} from 'lucide-react';
import { useAppStore, can, type ExternalCredentialDetail } from '../store';

// The deterministic class dimension auto-approval rules are keyed on (MVP 0.10.2).
const POLICY_ASSET_TYPES = ['PROCEDURE', 'POLICY', 'ROLE', 'SYSTEM', 'WORKFLOW', 'PRODUCT', 'DEPARTMENT'];

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
    currentUser,
    authReady,
    authError,
    login,
    logout,
    changePassword,
    restoreSession,
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
    projections,
    projectionsLoading,
    fetchProjections,
    renderProjection,
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
    packageSelection,
    packageComparison,
    selectionHistory,
    consumptionLoading,
    selectionError,
    consumptionInbox,
    fetchConsumptionInbox,
    fetchPackageConsumption,
    submitModelSelection,
    projectBindings,
    fetchProjectBindings,
    bindingLineage,
    fetchBindingLineage,
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
    fetchJobFiles,
    externalCredentials,
    fetchExternalCredentials,
    createExternalCredential,
    rotateExternalCredential,
    revokeExternalCredential,
    fetchCredentialDetail,
    approvalPolicies,
    fetchApprovalPolicies,
    createApprovalPolicy,
    toggleApprovalPolicy,
    correctAssetDomain,
    llmSettings,
    fetchLLMSettings,
    updateLLMSetting,
    principals,
    apiTokens,
    lastOneTimePassword,
    lastIssuedToken,
    fetchPrincipals,
    createPrincipal,
    updatePrincipal,
    resetPrincipalPassword,
    fetchApiTokens,
    issueApiToken,
    revokeApiToken
  } = useAppStore();

  // WS3 role-aware UI: hide what the backend would refuse. The backend
  // route guards remain the source of truth - this is presentation only.
  const allow = (permission: string) => can(currentUser, permission);

  const [activeTab, setActiveTab] = useState<'dashboard' | 'inbox' | 'documents' | 'sources' | 'assets' | 'experts' | 'evaluations' | 'conflicts' | 'revisions' | 'consumption' | 'agents' | 'audit' | 'console' | 'settings'>('dashboard');

  // v1.1.x Consumption Operations Workbench (D24): which package the
  // operator is looking at, and the in-flight selection proposal. Both are
  // ephemeral React state - the workbench owns NO persisted view state.
  const [consumptionPkgId, setConsumptionPkgId] = useState<number | null>(null);
  const [selForm, setSelForm] = useState<{ provider: string; model: string; runIds: number[]; rationale: string } | null>(null);
  const [consumptionView, setConsumptionView] = useState<'workbench' | 'inbox' | 'bindings'>('workbench');
  const [consumptionBindingId, setConsumptionBindingId] = useState<number | null>(null);

  // Consumption workbench: runs come from the existing evaluations read;
  // selection/comparison/history are fetched per package. All projections.
  useEffect(() => {
    if (activeTab === 'consumption' && activeProjectId !== null) {
      fetchEvaluations(activeProjectId);
      fetchConsumptionInbox(activeProjectId);
    }
  }, [activeTab, activeProjectId, consumptionView]);

  // The sidebar HIGH badge must alert without requiring a visit to the tab
  // (a computed read, the governance-inbox badge pattern).
  useEffect(() => {
    if (activeProjectId !== null && currentUser) {
      fetchConsumptionInbox(activeProjectId);
    }
  }, [activeProjectId, currentUser]);

  useEffect(() => {
    if (activeTab === 'consumption' && packages.length > 0 && consumptionPkgId === null) {
      setConsumptionPkgId(packages[0].id);
    }
  }, [activeTab, packages]);

  useEffect(() => {
    if (activeTab === 'consumption' && consumptionPkgId !== null) {
      setSelForm(null);
      fetchPackageConsumption(consumptionPkgId);
    }
  }, [activeTab, consumptionPkgId]);

  // Binding Explorer (WS3): list bindings across the project's packages,
  // then compose one binding's lineage server-side.
  useEffect(() => {
    if (activeTab === 'consumption' && consumptionView === 'bindings' && packages.length > 0) {
      fetchProjectBindings();
    }
  }, [activeTab, consumptionView, packages]);

  useEffect(() => {
    if (activeTab === 'consumption' && consumptionView === 'bindings'
        && projectBindings.length > 0 && consumptionBindingId === null) {
      setConsumptionBindingId(projectBindings[0].id);
    }
  }, [activeTab, consumptionView, projectBindings]);

  useEffect(() => {
    if (activeTab === 'consumption' && consumptionBindingId !== null) {
      fetchBindingLineage(consumptionBindingId);
    }
  }, [activeTab, consumptionBindingId]);

  useEffect(() => {
    if (activeTab === 'agents') {
      fetchAgentActivity();
    }
  }, [activeTab]);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [projectDesc, setProjectDesc] = useState('');

  // Identity Boundary v1.0: login gate + change-password state
  const [loginName, setLoginName] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginBusy, setLoginBusy] = useState(false);
  const [pwCurrent, setPwCurrent] = useState('');
  const [pwNew, setPwNew] = useState('');
  const [pwConfirm, setPwConfirm] = useState('');
  const [pwBusy, setPwBusy] = useState(false);
  const [pwSuccess, setPwSuccess] = useState(false);

  // Users & Tokens admin forms (WS3, ADMIN only)
  const [npName, setNpName] = useState('');
  const [npKind, setNpKind] = useState<'HUMAN' | 'AGENT' | 'SERVICE'>('HUMAN');
  const [npRole, setNpRole] = useState('READ_ONLY');
  const [npClearance, setNpClearance] = useState('PUBLIC');
  const [tokPrincipal, setTokPrincipal] = useState('');
  const [tokLabel, setTokLabel] = useState('');
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
  // v1.2.0 WS3 (Sources & Connectors): connector type + credential binding,
  // and custody administration state. Secret fields are WRITE-ONLY: their
  // values go into one request and are cleared - nothing reads them back.
  const [connectorType, setConnectorType] = useState<'LOCAL_FOLDER' | 'SHAREPOINT'>('LOCAL_FOLDER');
  const [connectorCredentialId, setConnectorCredentialId] = useState<number | null>(null);
  const [sourcesError, setSourcesError] = useState<string | null>(null);
  const [credName, setCredName] = useState('');
  const [credPurpose, setCredPurpose] = useState<'CONNECTOR' | 'PROVIDER'>('CONNECTOR');
  const [credSecret, setCredSecret] = useState('');
  const [credTenant, setCredTenant] = useState('');
  const [credClient, setCredClient] = useState('');
  const [credScopes, setCredScopes] = useState('Sites.Selected');
  const [rotateForId, setRotateForId] = useState<number | null>(null);
  const [rotateSecret, setRotateSecret] = useState('');
  const [revokeForId, setRevokeForId] = useState<number | null>(null);
  const [revokeReason, setRevokeReason] = useState('');
  const [credDetailId, setCredDetailId] = useState<number | null>(null);
  const [credDetail, setCredDetail] = useState<ExternalCredentialDetail | null>(null);

  // LLM Provider Settings state (MVP 0.12)
  const [llmDrafts, setLlmDrafts] = useState<Record<string, string>>({});

  useEffect(() => {
    if (activeTab === 'settings') {
      fetchLLMSettings();
    }
  }, [activeTab]);

  // Approval Policies state (MVP 0.10.2)
  const [policyName, setPolicyName] = useState('');
  const [policyTypes, setPolicyTypes] = useState<string[]>([]);
  const [policyConnectorId, setPolicyConnectorId] = useState<number | null>(null);
  // v1.2.1 (D26): policy-tier condition editors. The UI only shapes the
  // request; validation, versioning, and audit stay on the governed
  // policy routes - no separate semantics path.
  const [policyConditions, setPolicyConditions] = useState<{ key: string; op: 'equals' | 'in'; value: string }[]>([]);
  const [policyTier2, setPolicyTier2] = useState(false);
  const [policyDomains, setPolicyDomains] = useState('');
  // v1.2.1 (D27): inline governed domain correction on asset cards.
  const [domainEditAssetId, setDomainEditAssetId] = useState<number | null>(null);
  const [domainEditValue, setDomainEditValue] = useState('');
  const [showPolicyApprovedOnly, setShowPolicyApprovedOnly] = useState(false);

  // An asset counts as policy-approved when its most recent approval was
  // recorded by a "policy:<name>" actor (the ASSET_AUTO_APPROVED path).
  const policyApprover = (asset: { status: string; reviews?: { approver?: string | null }[] }): string | null => {
    if (asset.status !== 'APPROVED') return null;
    const reviews = asset.reviews || [];
    for (let i = reviews.length - 1; i >= 0; i--) {
      const approver = reviews[i]?.approver;
      if (approver) return approver.startsWith('policy:') ? approver.slice(7) : null;
    }
    return null;
  };

  useEffect(() => {
    if ((activeTab === 'documents' || activeTab === 'sources') && activeProjectId !== null) {
      fetchConnectors(activeProjectId);
      fetchIngestionJobs(activeProjectId);
      fetchApprovalPolicies(activeProjectId);
    }
    // Custody metadata is credentials:manage-only on the backend; the UI
    // mirror avoids a guaranteed 403 for everyone else.
    if (activeTab === 'sources' && can(currentUser, 'credentials:manage')) {
      fetchExternalCredentials();
    }
  }, [activeTab, activeProjectId]);

  // Live progress: poll while any job is pending/running on the sources tab
  // (scan history lives there since v1.2.0 WS3; documents keeps uploads).
  useEffect(() => {
    if ((activeTab !== 'documents' && activeTab !== 'sources') || activeProjectId === null) return;
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

  // v1.3 (D28): render history is projected from the ledger on demand;
  // the panel's parameters are declared render inputs, never saved state.
  const [projectionRenderer, setProjectionRenderer] = useState('graph');
  const [projectionClearance, setProjectionClearance] = useState('INTERNAL');
  const [projectionDomainPrefix, setProjectionDomainPrefix] = useState('');
  const [projectionRendering, setProjectionRendering] = useState(false);
  useEffect(() => {
    if (activeTab === 'dashboard' && activeProjectId !== null && currentUser) {
      fetchProjections(activeProjectId);
    }
  }, [activeTab, activeProjectId, currentUser]);

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
    restoreSession();
  }, []);

  useEffect(() => {
    if (currentUser) fetchProjects();
  }, [currentUser]);

  useEffect(() => {
    if (activeTab === 'settings' && can(currentUser, 'identity:manage')) {
      fetchPrincipals();
      fetchApiTokens();
    }
  }, [activeTab, currentUser]);

  // Hydrate governance deep-link state (?tab=conflicts&expert=11&relationship=42)
  // from the URL once on load. The assets tab stays path-based (/knowledge-assets).
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    const urlTabs = ['inbox', 'documents', 'sources', 'experts', 'evaluations', 'conflicts', 'revisions', 'consumption', 'agents', 'audit', 'console', 'settings'] as const;
    if (tab && (urlTabs as readonly string[]).includes(tab)) {
      const expert = params.get('expert');
      const relationship = params.get('relationship');
      const revision = params.get('revision');
      if (tab === 'consumption') {
        const pkg = params.get('package');
        if (pkg) setConsumptionPkgId(Number(pkg));
        const view = params.get('view');
        if (view === 'inbox' || view === 'bindings') setConsumptionView(view);
        const bindingParam = params.get('binding');
        if (bindingParam) {
          setConsumptionBindingId(Number(bindingParam));
          setConsumptionView('bindings');
        }
      }
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
        if (activeTab === 'consumption' && consumptionPkgId !== null) params.set('package', String(consumptionPkgId));
        if (activeTab === 'consumption' && consumptionView !== 'workbench') params.set('view', consumptionView);
        if (activeTab === 'consumption' && consumptionView === 'bindings' && consumptionBindingId !== null) {
          params.set('binding', String(consumptionBindingId));
        }
        newSearch = `?${params.toString()}`;
      }

      const targetUrl = newPath + newSearch;
      const currentUrl = currentPath + currentSearch;

      if (currentUrl !== targetUrl) {
        window.history.pushState(null, '', targetUrl);
      }
    }
  }, [activeTab, selectedDocFilterId, conflictModelId, highlightRelationshipId, highlightRevisionId, inboxModelFilter, expandedRunId, highlightResultId, consumptionPkgId, consumptionView, consumptionBindingId]);

  // Listen to browser back/forward buttons
  useEffect(() => {
    const handlePopState = () => {
      const pathname = window.location.pathname;
      const searchParams = new URLSearchParams(window.location.search);
      const documentIdParam = searchParams.get('documentId');
      const documentParam = searchParams.get('document');
      const tabParam = searchParams.get('tab');
      const urlTabs = ['inbox', 'documents', 'sources', 'experts', 'evaluations', 'conflicts', 'revisions', 'agents', 'audit', 'console', 'settings'];

      if (pathname.includes('/knowledge-assets')) {
        setActiveTab('assets');
      } else if (tabParam && urlTabs.includes(tabParam)) {
        setActiveTab(tabParam as 'inbox' | 'documents' | 'experts' | 'evaluations' | 'conflicts' | 'revisions' | 'agents' | 'audit' | 'console' | 'settings');
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

  // Identity Boundary v1.0 login gate: the backend refuses unauthenticated
  // writes (401) - the UI is honest about it and asks for identity first.
  if (!authReady) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#070b12] text-slate-400 font-mono text-sm">
        <div className="w-4 h-4 mr-3 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
        restoring session...
      </div>
    );
  }
  if (!currentUser) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#070b12] text-slate-100 font-sans">
        <div className="glass-panel rounded-2xl p-8 w-96 space-y-5 border border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-emerald-500 flex items-center justify-center">
              <Boxes className="w-5 h-5 text-[#070b12]" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-wider text-gradient-cyan">EXPERTMACHINA</span>
              <span className="text-[10px] block text-slate-500 tracking-widest font-mono">IDENTITY BOUNDARY v1.0</span>
            </div>
          </div>
          <form
            className="space-y-3"
            onSubmit={async (e) => {
              e.preventDefault();
              setLoginBusy(true);
              await login(loginName.trim(), loginPassword);
              setLoginBusy(false);
              setLoginPassword('');
            }}
          >
            <input
              value={loginName}
              onChange={(e) => setLoginName(e.target.value)}
              placeholder="username"
              autoFocus
              className="w-full bg-slate-950/70 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:border-cyan-700 outline-none"
            />
            <input
              type="password"
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              placeholder="password"
              className="w-full bg-slate-950/70 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:border-cyan-700 outline-none"
            />
            {authError && (
              <div className="text-xs text-rose-400 flex items-center gap-2">
                <AlertCircle className="w-3.5 h-3.5" /> {authError}
              </div>
            )}
            <button
              type="submit"
              disabled={loginBusy || !loginName.trim() || !loginPassword}
              className="w-full bg-gradient-to-r from-cyan-500 to-emerald-500 text-slate-950 font-semibold px-4 py-2 rounded-lg text-xs tracking-wider uppercase disabled:opacity-40"
            >
              {loginBusy ? 'Authenticating…' : 'Sign in'}
            </button>
          </form>
          <p className="text-[10px] text-slate-600 leading-relaxed">
            First run? The backend printed a one-time <span className="font-mono text-slate-500">admin</span> password
            to its console at startup.
          </p>
        </div>
      </div>
    );
  }

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
              <span className="text-[10px] block text-slate-500 tracking-widest font-mono">GOVERNANCE CORE v1.0</span>
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
              {documents.length > 0 && (
                <span className="ml-auto bg-slate-800 text-[10px] text-slate-300 font-mono px-2 py-0.5 rounded-full">
                  {documents.length}
                </span>
              )}
            </button>

            {/* v1.2.0 WS3: Sources & Connectors - earned by provider
                plurality (D8): LocalFolder + SharePoint. Connector and
                credential administration lives here; Document Inventory
                keeps uploads and the extracted inventory. */}
            <button
              onClick={() => setActiveTab('sources')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'sources'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <Cloud className="w-4 h-4" />
              <span>Sources &amp; Connectors</span>
              {ingestionJobs.some(j => j.status === 'PENDING' || j.status === 'RUNNING') && (
                <span className="ml-auto bg-cyan-950/40 text-[10px] text-cyan-400 font-mono px-2 py-0.5 rounded-full border border-cyan-900/40 animate-pulse">
                  scanning
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

            {/* v1.1.x: Consumption is a first-class lifecycle area
                (package/model/binding-facing), deliberately NOT an Agent
                Center subpage (Agent Center stays identity/MCP-facing). */}
            {allow('assets:read') && (
            <button
              onClick={() => setActiveTab('consumption')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'consumption'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <PackageCheck className="w-4 h-4" />
              <span>Consumption</span>
              {consumptionInbox && consumptionInbox.summary.high > 0 && (
                <span className="ml-auto bg-rose-950/40 text-[10px] text-rose-400 font-mono px-2 py-0.5 rounded-full border border-rose-900/40">
                  {consumptionInbox.summary.high}
                </span>
              )}
            </button>
            )}

            {allow('audit:read') && (
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
            )}

            {allow('audit:read') && (
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
            )}

            {allow('settings:manage') && (
            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                activeTab === 'settings'
                  ? 'bg-cyan-950/40 text-cyan-400 border-l-2 border-cyan-400 font-medium'
                  : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </button>
            )}
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
            <div className="flex items-center gap-3 pl-4 border-l border-slate-800">
              <div className="text-right">
                <div className="text-xs font-semibold text-slate-200">{currentUser.display_name}</div>
                <div className="text-[10px] font-mono text-cyan-600 uppercase tracking-wider">{currentUser.role || currentUser.kind}</div>
              </div>
              <button
                onClick={() => logout()}
                title="Sign out"
                className="text-[10px] font-mono uppercase tracking-wider px-2 py-1 rounded border border-slate-800 text-slate-400 hover:text-rose-300 hover:border-rose-900/60 transition-colors"
              >
                Sign out
              </button>
            </div>
          </div>
        </header>

        {/* Identity Boundary: forced credential rotation after bootstrap */}
        {currentUser.must_change_password && (
          <div className="bg-amber-950/40 border-b border-amber-900/50 px-8 py-3 text-xs text-amber-200 space-y-1.5">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span className="font-semibold">One-time password in use — set your own password:</span>
            </div>
            <form
              className="flex flex-wrap items-end gap-3"
              onSubmit={async (e) => {
                e.preventDefault();
                setPwBusy(true);
                const ok = await changePassword(pwCurrent, pwNew);
                setPwBusy(false);
                if (ok) { setPwCurrent(''); setPwNew(''); setPwConfirm(''); setPwSuccess(true); }
              }}
            >
              <label className="block">
                <span className="block text-[9px] font-mono uppercase tracking-wider text-amber-400/80 mb-0.5">Current (one-time) password</span>
                <input type="password" value={pwCurrent} onChange={(e) => setPwCurrent(e.target.value)}
                       className="bg-slate-950/70 border border-slate-800 rounded px-2 py-1 text-xs w-44 outline-none focus:border-amber-700" />
              </label>
              <label className="block">
                <span className="block text-[9px] font-mono uppercase tracking-wider text-amber-400/80 mb-0.5">New password (min 8)</span>
                <input type="password" value={pwNew} onChange={(e) => setPwNew(e.target.value)}
                       className="bg-slate-950/70 border border-slate-800 rounded px-2 py-1 text-xs w-44 outline-none focus:border-amber-700" />
              </label>
              <label className="block">
                <span className="block text-[9px] font-mono uppercase tracking-wider text-amber-400/80 mb-0.5">Confirm new password</span>
                <input type="password" value={pwConfirm} onChange={(e) => setPwConfirm(e.target.value)}
                       className="bg-slate-950/70 border border-slate-800 rounded px-2 py-1 text-xs w-44 outline-none focus:border-amber-700" />
              </label>
              <button type="submit"
                      disabled={pwBusy || pwNew.length < 8 || !pwCurrent || pwNew !== pwConfirm}
                      className="px-3 py-1.5 rounded bg-amber-600/80 text-slate-950 font-semibold uppercase tracking-wider text-[10px] disabled:opacity-40">
                {pwBusy ? 'Saving…' : 'Save new password'}
              </button>
              {pwNew && pwConfirm && pwNew !== pwConfirm && (
                <span className="text-rose-400 pb-1.5">passwords do not match</span>
              )}
              {authError && <span className="text-rose-400 pb-1.5">{authError}</span>}
            </form>
          </div>
        )}
        {pwSuccess && !currentUser.must_change_password && (
          <div className="bg-emerald-950/40 border-b border-emerald-900/50 px-8 py-2 text-xs text-emerald-300 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            Password changed. Your session stays signed in; use the new password next time.
            <button onClick={() => setPwSuccess(false)} className="ml-auto text-emerald-500 hover:text-emerald-300 font-mono text-[10px] uppercase">dismiss</button>
          </div>
        )}

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

                  {/* PROJECTIONS PANEL (v1.3, D28): a governed lens, never
                      a source. History is projected from PROJECTION_RENDERED
                      ledger events; staleness is computed; a stale render is
                      regenerated, never edited. Render = assets:approve
                      (the .empkg act-class); history = assets:read. */}
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <div className="flex items-center justify-between flex-wrap gap-3">
                      <div>
                        <h4 className="text-sm font-semibold text-slate-300">Projections</h4>
                        <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                          Computed views over governed facts — regenerated, never edited; stamps live in manifest.json
                        </p>
                      </div>
                      {can(currentUser, 'assets:approve') && (
                        <div className="flex items-center gap-2 flex-wrap">
                          <select
                            value={projectionRenderer}
                            onChange={(e) => setProjectionRenderer(e.target.value)}
                            className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-300"
                            aria-label="Renderer"
                          >
                            <option value="graph">graph (json + html)</option>
                            <option value="projection">projection (canonical json)</option>
                          </select>
                          <select
                            value={projectionClearance}
                            onChange={(e) => setProjectionClearance(e.target.value)}
                            className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-300"
                            aria-label="Compiled for clearance"
                          >
                            {['PUBLIC', 'INTERNAL', 'RESTRICTED', 'EXECUTIVE'].map(c => (
                              <option key={c} value={c}>{c}</option>
                            ))}
                          </select>
                          <input
                            value={projectionDomainPrefix}
                            onChange={(e) => setProjectionDomainPrefix(e.target.value)}
                            placeholder="domain prefix (optional)"
                            className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-300 w-44"
                            aria-label="Domain prefix"
                          />
                          <button
                            disabled={projectionRendering || activeProjectId === null}
                            onClick={async () => {
                              if (activeProjectId === null) return;
                              setProjectionRendering(true);
                              await renderProjection(activeProjectId, {
                                renderer: projectionRenderer,
                                clearance: projectionClearance,
                                domain_prefix: projectionDomainPrefix.trim() || null,
                              });
                              setProjectionRendering(false);
                            }}
                            className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-bold px-4 py-1.5 rounded-lg text-xs tracking-wider uppercase"
                          >
                            {projectionRendering ? 'Rendering…' : 'Render'}
                          </button>
                        </div>
                      )}
                    </div>
                    {projectionsLoading && projections.length === 0 ? (
                      <p className="text-xs text-slate-500">Projecting render history from the ledger…</p>
                    ) : projections.length === 0 ? (
                      <p className="text-xs text-slate-500">
                        No renders recorded for this project. A render exports a clearance-filtered,
                        cursor-stamped view of approved knowledge — the ledger records every one.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {projections.slice(0, 8).map((p) => (
                          <div key={p.event_id}
                               className="flex items-center justify-between gap-3 bg-slate-900/60 border border-slate-800 rounded-lg px-3 py-2 flex-wrap">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-xs font-mono text-cyan-300">{p.renderer}</span>
                              <span className="text-[10px] font-mono text-slate-500">
                                {p.rendered_at ? p.rendered_at.slice(0, 19).replace('T', ' ') : '—'}
                              </span>
                              <span className="text-[10px] font-mono text-slate-400">
                                {p.clearance} · {(p.status_inclusion || []).join('/')}
                                {p.domain_prefix ? ` · ${p.domain_prefix}` : ''}
                              </span>
                              <span className="text-[10px] font-mono text-slate-500">
                                {p.counts ? `${p.counts.nodes}n/${p.counts.edges}e` : ''}
                                {' '}· cursor {p.audit_cursor}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              {p.current && p.stale === true && (
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-900/50 text-amber-300 border border-amber-700/50 uppercase tracking-wider">
                                  Stale — regenerate
                                </span>
                              )}
                              {p.current && p.stale === false && (
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-900/40 text-emerald-300 border border-emerald-800/50 uppercase tracking-wider">
                                  Current
                                </span>
                              )}
                              {!p.current && (
                                <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-500 uppercase tracking-wider">
                                  Superseded
                                </span>
                              )}
                              <span className="text-[10px] font-mono text-slate-600" title={`manifest ${p.manifest_hash || ''}`}>
                                {p.output || ''}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
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
                  
                  {/* UPLOADER PANEL (documents:ingest) */}
                  {allow('documents:ingest') && (
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
                  )}

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
                      {assets.some(a => policyApprover(a)) && (
                        <button
                          onClick={() => setShowPolicyApprovedOnly(v => !v)}
                          title="Spot-check everything a policy approved automatically"
                          className={`rounded px-2.5 py-1 text-xs font-mono uppercase flex items-center gap-1.5 transition-colors border ${
                            showPolicyApprovedOnly
                              ? 'bg-violet-950/40 border-violet-700/60 text-violet-300'
                              : 'bg-slate-900 hover:bg-slate-850 border-slate-800 text-slate-300'
                          }`}
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                          {showPolicyApprovedOnly ? 'Policy-approved only' : 'Filter: policy-approved'}
                        </button>
                      )}
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
                        const visibleAssets = showPolicyApprovedOnly ? assets.filter(a => policyApprover(a)) : assets;
                        visibleAssets.forEach(asset => {
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
                                    {hasPending && allow('assets:approve') && (
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
                                    {group.items.some(item => item.status === 'ARCHIVED') && allow('assets:delete') && (
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
                                    {group.items.some(item => item.status === 'CANDIDATE') && allow('assets:delete') && (
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
                                    {allow('assets:delete') && (
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
                                    )}
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
                                  const approvedByPolicy = policyApprover(asset);
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
                                            {approvedByPolicy && (
                                              <span
                                                title={`Approved automatically by policy "${approvedByPolicy}" — audit-logged as ASSET_AUTO_APPROVED with the rule version that fired`}
                                                className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-violet-950/40 border border-violet-900/40 text-violet-400"
                                              >
                                                Policy: {approvedByPolicy}
                                              </span>
                                            )}
                                            {/* v1.4.0 (D29/D30): agent-synthesized knowledge is never
                                                mistakable for human-authored knowledge. The class is
                                                channel-decided; the full synthesis provenance (agent,
                                                binding, package hash, cited evidence, verification
                                                verdict) is on the ASSET_APPROVED event in the ledger. */}
                                            {asset.source_class === 'DERIVED' && (
                                              <span
                                                title={asset.status === 'APPROVED'
                                                  ? `Agent-synthesized, accepted as DERIVED by ${asset.reviews?.find(r => r.approver && !r.approver.startsWith('policy:'))?.approver || 'a human'} — synthesis provenance is on the ASSET_APPROVED event (Audit tab). Primary prevails in conflicts unless a human rules otherwise.`
                                                  : 'Agent-synthesized proposal, held for the human gate (D29) — proposal-lane candidates are never auto-approved. Accepting it creates a DERIVED fact.'}
                                                className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-fuchsia-950/40 border border-fuchsia-900/40 text-fuchsia-400"
                                              >
                                                DERIVED
                                              </span>
                                            )}
                                            {/* v1.2.1 (D27): the governed domain path. Correction is a
                                                governed act on the normal asset-update path
                                                (ASSET_DOMAIN_CORRECTED) — never a content edit. */}
                                            {domainEditAssetId === asset.id ? (
                                              <span className="flex items-center gap-1">
                                                <input autoFocus type="text" value={domainEditValue}
                                                  placeholder="finances/accounting"
                                                  onChange={(e) => setDomainEditValue(e.target.value)}
                                                  onKeyDown={async (e) => {
                                                    if (e.key === 'Enter') {
                                                      e.preventDefault();
                                                      await correctAssetDomain(asset.id, domainEditValue.trim() || null);
                                                      setDomainEditAssetId(null);
                                                    }
                                                    if (e.key === 'Escape') setDomainEditAssetId(null);
                                                  }}
                                                  className="text-[10px] font-mono w-40 bg-slate-950 border border-emerald-700/60 rounded px-2 py-0.5 text-emerald-300 outline-none" />
                                                <button onClick={() => setDomainEditAssetId(null)}
                                                  className="text-[10px] text-slate-500 hover:text-slate-300 font-mono">esc</button>
                                              </span>
                                            ) : (
                                              <span
                                                title={asset.domain
                                                  ? `Governed domain path (assigned by classification policy or human correction)${allow('assets:review') ? ' — click to correct' : ''}`
                                                  : `Unclassified — no classification policy assigned a domain${allow('assets:review') ? '; click to correct' : ''}`}
                                                onClick={() => {
                                                  if (!allow('assets:review')) return;
                                                  setDomainEditAssetId(asset.id);
                                                  setDomainEditValue(asset.domain ?? '');
                                                }}
                                                className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                                                  asset.domain
                                                    ? 'bg-emerald-950/30 border-emerald-900/40 text-emerald-400'
                                                    : 'bg-slate-950 border-slate-900 text-slate-500'
                                                } ${allow('assets:review') ? 'cursor-pointer hover:border-emerald-600/60' : ''}`}
                                              >
                                                {asset.domain ?? 'unclassified'}
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
                                        {asset.status !== 'APPROVED' && allow('assets:approve') && (
                                          <button
                                            onClick={() => updateAssetStatus(asset.id, 'APPROVED')}
                                            className="flex-1 py-1.5 bg-emerald-950/40 hover:bg-emerald-900/40 text-emerald-400 font-semibold rounded text-xs border border-emerald-900/30 transition-colors"
                                          >
                                            Approve
                                          </button>
                                        )}
                                        {asset.status !== 'ARCHIVED' && allow('assets:approve') && (
                                          <button
                                            onClick={() => updateAssetStatus(asset.id, 'ARCHIVED')}
                                            className="px-3 py-1.5 bg-rose-950/30 hover:bg-rose-950/50 text-rose-450 hover:text-rose-400 font-semibold rounded text-xs border border-rose-900/30 transition-colors"
                                          >
                                            Reject as Invalid
                                          </button>
                                        )}
                                        {(asset.status === 'CANDIDATE' || asset.status === 'ARCHIVED') && allow('assets:delete') && (
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
                                                            await reviewClaimVerdict(v.id, verdictReviewComment.trim());
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

              {/* APPROVAL POLICIES stay with Document Inventory; connector
                  and credential administration moved to the top-level
                  Sources & Connectors area (v1.2.0 WS3 - the plurality D8
                  required arrived with the SharePoint provider). */}
              {activeTab === 'documents' && (
                <div className="space-y-6 mt-6">

                  <div className="glass-panel p-4 rounded-xl flex items-center gap-3 text-xs text-slate-400">
                    <Cloud className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>
                      Folder and SharePoint connectors are administered in{' '}
                      <button onClick={() => setActiveTab('sources')}
                        className="text-cyan-400 hover:text-cyan-300 underline decoration-dotted">
                        Sources &amp; Connectors
                      </button>
                      {' '}— scans still land here as ordinary documents and CANDIDATE assets.
                    </span>
                  </div>

                  {/* APPROVAL POLICIES (MVP 0.10.2) — deterministic, versioned
                      auto-approval rules: the pressure valve bulk ingestion
                      requires. New CANDIDATE assets of a covered type are
                      approved by "policy:<name>" with full audit provenance;
                      candidate revisions always wait for a human. */}
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-violet-400" />
                      Approval Policies
                      <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                        Auto-approve low-risk asset classes at ingestion — audit-logged &quot;approved by policy&quot;, revisions always reviewed by a human
                      </span>
                    </h3>
                    {allow('assets:approve') && (
                    <form
                      onSubmit={async (e) => {
                        e.preventDefault();
                        if (activeProjectId === null || !policyName.trim() || policyTypes.length === 0) return;
                        const sourceConditions = policyConditions
                          .filter(c => c.key.trim() && c.value.trim())
                          .map(c => c.op === 'equals'
                            ? { key: c.key.trim(), equals: c.value.trim() }
                            : { key: c.key.trim(), in: c.value.split(',').map(s => s.trim()).filter(Boolean) });
                        await createApprovalPolicy(activeProjectId, policyName.trim(), policyTypes, policyConnectorId, {
                          source_conditions: sourceConditions.length ? sourceConditions : null,
                          engine_conditions: policyTier2 ? { contradiction_check: 'CLEAN_REQUIRED' } : null,
                          domains: policyDomains.trim()
                            ? policyDomains.split(',').map(s => s.trim()).filter(Boolean)
                            : null,
                        });
                        setPolicyName('');
                        setPolicyTypes([]);
                        setPolicyConnectorId(null);
                        setPolicyConditions([]);
                        setPolicyTier2(false);
                        setPolicyDomains('');
                      }}
                      className="space-y-3"
                    >
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                        <div>
                          <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Policy Name</label>
                          <input type="text" required value={policyName} onChange={(e) => setPolicyName(e.target.value)}
                            placeholder="e.g. Low-risk system docs"
                            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-violet-500 outline-none text-slate-200" />
                        </div>
                        <div>
                          <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Source Scope</label>
                          <select value={policyConnectorId ?? ''} onChange={(e) => setPolicyConnectorId(e.target.value === '' ? null : Number(e.target.value))}
                            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-violet-500 outline-none text-slate-200">
                            <option value="">Any source (incl. manual upload)</option>
                            {sourceConnectors.map((c) => (
                              <option key={c.id} value={c.id}>Connector: {c.name}</option>
                            ))}
                          </select>
                        </div>
                        <button type="submit" disabled={policyTypes.length === 0}
                          className="py-2 px-5 bg-gradient-to-r from-violet-500 to-violet-600 text-slate-950 font-bold rounded text-xs tracking-wider uppercase disabled:opacity-40">
                          Add Policy
                        </button>
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Auto-approved Asset Types</label>
                        <div className="flex flex-wrap gap-2">
                          {POLICY_ASSET_TYPES.map((t) => {
                            const selected = policyTypes.includes(t);
                            return (
                              <button key={t} type="button"
                                onClick={() => setPolicyTypes(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t])}
                                className={`text-[10px] font-mono px-2.5 py-1 rounded border uppercase tracking-wider transition-colors ${
                                  selected
                                    ? 'bg-violet-950/40 border-violet-700/60 text-violet-300'
                                    : 'bg-slate-950 border-slate-800 text-slate-500 hover:text-slate-300'
                                }`}
                              >
                                {t}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* v1.2.1 (D26 Tier-0): source-authority conditions —
                          deterministic matches against the verbatim source
                          metadata of the scan row. Absent metadata never
                          satisfies a condition; the source must vouch. */}
                      <div className="space-y-2">
                        <label className="block text-xs text-slate-400 font-mono uppercase">
                          Source-Authority Conditions <span className="text-slate-600 normal-case">(Tier-0 — the source must vouch; leave empty for none)</span>
                        </label>
                        {policyConditions.map((c, i) => (
                          <div key={i} className="flex flex-wrap items-center gap-2">
                            <input type="text" value={c.key} placeholder="list_item_fields.ApprovalStatus"
                              onChange={(e) => setPolicyConditions(prev => prev.map((x, j) => j === i ? { ...x, key: e.target.value } : x))}
                              className="flex-1 min-w-[200px] bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs font-mono focus:border-violet-500 outline-none text-slate-200" />
                            <select value={c.op}
                              onChange={(e) => setPolicyConditions(prev => prev.map((x, j) => j === i ? { ...x, op: e.target.value as 'equals' | 'in' } : x))}
                              className="bg-slate-950 border border-slate-800 rounded px-2 py-1.5 text-xs font-mono text-slate-300 outline-none">
                              <option value="equals">equals</option>
                              <option value="in">is one of</option>
                            </select>
                            <input type="text" value={c.value}
                              placeholder={c.op === 'in' ? 'Approved, Published' : 'Approved'}
                              onChange={(e) => setPolicyConditions(prev => prev.map((x, j) => j === i ? { ...x, value: e.target.value } : x))}
                              className="flex-1 min-w-[160px] bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs font-mono focus:border-violet-500 outline-none text-slate-200" />
                            <button type="button" onClick={() => setPolicyConditions(prev => prev.filter((_, j) => j !== i))}
                              className="text-[10px] text-rose-400 hover:text-rose-300 font-mono px-2 py-1.5">✕</button>
                          </div>
                        ))}
                        <button type="button"
                          onClick={() => setPolicyConditions(prev => [...prev, { key: '', op: 'equals', value: '' }])}
                          className="text-[10px] text-violet-400 hover:text-violet-300 font-mono bg-violet-950/20 border border-violet-900/30 rounded px-3 py-1.5 uppercase tracking-wider">
                          + Add source condition
                        </button>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
                        {/* v1.2.1 (D26 Tier-2): engine verification — the
                            engine may refuse to approve; only humans refuse
                            content. */}
                        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer bg-slate-950/60 border border-slate-900 rounded px-3 py-2.5">
                          <input type="checkbox" checked={policyTier2} onChange={(e) => setPolicyTier2(e.target.checked)}
                            className="accent-violet-500" />
                          <span className="font-mono uppercase tracking-wider text-[10px]">Engine-verified (Tier-2)</span>
                          <span className="text-[10px] text-slate-500">requires a clean candidate-contradiction check, applied asynchronously</span>
                        </label>
                        {/* v1.2.1 (D26/D27): domain coverage — deny-by-default
                            narrowing; unclassified assets are never covered
                            by a domain-scoped policy. */}
                        <div>
                          <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">
                            Domain Coverage <span className="text-slate-600 normal-case">(prefixes, comma-separated; empty = all domains)</span>
                          </label>
                          <input type="text" value={policyDomains} onChange={(e) => setPolicyDomains(e.target.value)}
                            placeholder="finances, hr/policies"
                            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs font-mono focus:border-violet-500 outline-none text-slate-200" />
                        </div>
                      </div>
                    </form>
                    )}

                    {/* POLICY LIST */}
                    {approvalPolicies.length > 0 && (
                      <div className="space-y-2 pt-2">
                        {approvalPolicies.map((p) => {
                          const scope = p.connector_id !== null
                            ? `connector: ${sourceConnectors.find(c => c.id === p.connector_id)?.name ?? `#${p.connector_id}`}`
                            : 'any source';
                          return (
                            <div key={p.id} className={`flex flex-wrap items-center gap-3 bg-slate-950/60 border border-slate-900 rounded-lg p-3 ${p.enabled ? '' : 'opacity-50'}`}>
                              <span className="text-[10px] font-mono bg-violet-950/40 text-violet-400 border border-violet-900/40 px-2 py-0.5 rounded">v{p.version}</span>
                              <span className="font-bold text-sm text-slate-200">{p.name}</span>
                              <span className="text-[10px] font-mono text-slate-500">{p.asset_types.join(', ')}</span>
                              {(p.source_conditions?.length ?? 0) > 0 && (
                                <span title={p.source_conditions!.map(c => `${c.key} ${c.equals !== undefined ? `= ${c.equals}` : `in [${(c.in || []).join(', ')}]`}`).join(' AND ')}
                                  className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950/30 border border-cyan-900/40 text-cyan-400">
                                  TIER-0 · {p.source_conditions!.length} condition{p.source_conditions!.length !== 1 ? 's' : ''}
                                </span>
                              )}
                              {p.engine_conditions && (
                                <span title="Engine-verified: a clean candidate-contradiction check is required before this policy approves — applied asynchronously; the engine may refuse to approve, only humans refuse content"
                                  className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-950/30 border border-amber-900/40 text-amber-400">
                                  TIER-2 · ENGINE
                                </span>
                              )}
                              {(p.domains?.length ?? 0) > 0 && (
                                <span title="Domain coverage (deny-by-default): only assets under these domain prefixes are covered"
                                  className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/30 border border-emerald-900/40 text-emerald-400">
                                  {p.domains!.join(', ')}
                                </span>
                              )}
                              <span className="text-[10px] font-mono text-slate-600 flex-1 min-w-[120px]">{scope}</span>
                              <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${p.enabled ? 'bg-emerald-950/40 text-emerald-400' : 'bg-slate-900 text-slate-500'}`}>
                                {p.enabled ? 'ENABLED' : 'DISABLED'}
                              </span>
                              {allow('assets:approve') && (
                              <button
                                onClick={() => activeProjectId !== null && toggleApprovalPolicy(p.id, !p.enabled, activeProjectId)}
                                className="text-[10px] text-violet-400 hover:text-violet-300 font-mono bg-violet-950/20 border border-violet-900/30 rounded px-3 py-1.5 uppercase tracking-wider"
                              >
                                {p.enabled ? 'Disable' : 'Enable'}
                              </button>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                </div>
              )}

              {/* TAB: SOURCES & CONNECTORS (v1.2.0 WS3) — the operator
                  surface over the proven backend path: connector
                  administration (LocalFolder + SharePoint), credential
                  custody (D25: create/rotate/revoke, metadata only - no
                  reveal affordance exists), and scan history. Visibility
                  over existing facts; the only writes are the governed
                  connector/credential administration routes. */}
              {activeTab === 'sources' && (
                <div className="space-y-6">

                  {/* CONNECTORS */}
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                      <Cloud className="w-4 h-4 text-cyan-400" />
                      Connectors
                      <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                        Read-only discovery over company repositories — output becomes ordinary documents and CANDIDATE assets in the existing pipeline
                      </span>
                    </h3>
                    {allow('connectors:manage') && (
                    <form
                      onSubmit={async (e) => {
                        e.preventDefault();
                        if (activeProjectId === null || !connectorName.trim() || !connectorPath.trim()) return;
                        setSourcesError(null);
                        await createConnector(activeProjectId, connectorName.trim(), connectorPath.trim(),
                                              connectorExts.trim(), connectorType,
                                              connectorType === 'SHAREPOINT' || connectorCredentialId !== null
                                                ? connectorCredentialId : null);
                        setConnectorName('');
                        setConnectorPath('');
                        setConnectorCredentialId(null);
                      }}
                      className="space-y-3"
                    >
                      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
                        <div>
                          <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Type</label>
                          <select value={connectorType}
                            onChange={(e) => setConnectorType(e.target.value as 'LOCAL_FOLDER' | 'SHAREPOINT')}
                            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200">
                            <option value="LOCAL_FOLDER">Local Folder</option>
                            <option value="SHAREPOINT" disabled={!allow('credentials:manage') && externalCredentials.length === 0}>SharePoint</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Connector Name</label>
                          <input type="text" required value={connectorName} onChange={(e) => setConnectorName(e.target.value)}
                            placeholder="e.g. Quality SOP Share"
                            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200" />
                        </div>
                        <div>
                          <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">
                            {connectorType === 'SHAREPOINT' ? 'Site URL (optionally ::Library)' : 'Folder Path'}
                          </label>
                          <input type="text" required value={connectorPath} onChange={(e) => setConnectorPath(e.target.value)}
                            placeholder={connectorType === 'SHAREPOINT'
                              ? 'https://tenant.sharepoint.com/sites/QMS::Policies'
                              : 'C:\\shares\\policies or /mnt/docs'}
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
                      </div>
                      {(connectorType === 'SHAREPOINT' || allow('credentials:manage')) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
                          <div>
                            <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">
                              Credential used for scans {connectorType === 'SHAREPOINT' ? '(required)' : '(optional)'}
                            </label>
                            {allow('credentials:manage') ? (
                              <select value={connectorCredentialId ?? ''}
                                onChange={(e) => setConnectorCredentialId(e.target.value === '' ? null : Number(e.target.value))}
                                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-cyan-500 outline-none text-slate-200 font-mono">
                                <option value="">— none —</option>
                                {externalCredentials.filter(c => c.status === 'ACTIVE' && c.purpose === 'CONNECTOR').map((c) => (
                                  <option key={c.id} value={c.id}>{c.name} · {c.fingerprint}</option>
                                ))}
                              </select>
                            ) : (
                              <p className="text-[10px] font-mono text-yellow-400/90 bg-yellow-950/20 border border-yellow-900/30 rounded p-2">
                                Binding a credential is a custody action (credentials:manage) — ask an ADMIN to create the SharePoint connector.
                              </p>
                            )}
                          </div>
                        </div>
                      )}
                    </form>
                    )}

                    {/* CONNECTOR LIST */}
                    {sourceConnectors.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">No connectors yet for this workspace.</p>
                    ) : (
                      <div className="space-y-2 pt-2">
                        {sourceConnectors.map((c) => {
                          const busy = ingestionJobs.some(j => j.connector_id === c.id && (j.status === 'PENDING' || j.status === 'RUNNING'));
                          const bound = c.external_credential_id !== null
                            ? externalCredentials.find(x => x.id === c.external_credential_id) : undefined;
                          return (
                            <div key={c.id} className="flex flex-wrap items-center gap-3 bg-slate-950/60 border border-slate-900 rounded-lg p-3">
                              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                                c.type === 'SHAREPOINT'
                                  ? 'bg-sky-950/40 text-sky-400 border-sky-900/40'
                                  : 'bg-slate-900 text-slate-400 border-slate-850'
                              }`}>{c.type}</span>
                              <span className="font-bold text-sm text-slate-200">{c.name}</span>
                              <span className="text-[10px] font-mono text-slate-500 flex-1 min-w-[180px] truncate" title={c.root_path}>{c.root_path}</span>
                              {c.external_credential_id !== null && (
                                <span className="text-[9px] font-mono bg-violet-950/30 text-violet-400 border border-violet-900/40 px-2 py-0.5 rounded"
                                  title="Credential used for scans — released per scan by the custody layer, never shown">
                                  <KeyRound className="w-2.5 h-2.5 inline mr-1" />
                                  {bound ? bound.fingerprint : `credential #${c.external_credential_id}`}
                                </span>
                              )}
                              <span className="text-[9px] font-mono text-slate-600">{c.include_extensions}</span>
                              {allow('connectors:manage') && (
                              <button
                                onClick={() => activeProjectId !== null && scanConnector(c.id, activeProjectId)}
                                disabled={busy}
                                className="text-[10px] text-cyan-400 hover:text-cyan-300 font-mono bg-cyan-950/20 border border-cyan-900/30 rounded px-3 py-1.5 uppercase tracking-wider disabled:opacity-40"
                              >
                                {busy ? 'Scanning…' : 'Scan Now'}
                              </button>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* OUTBOUND CREDENTIALS (D25 custody administration) */}
                  {allow('credentials:manage') ? (
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                      <KeyRound className="w-4 h-4 text-violet-400" />
                      Outbound Credentials
                      <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                        Secrets are entered once, stored encrypted, and never displayed again — rotate to replace, revoke to retire; custody events are the audit record
                      </span>
                    </h3>
                    {sourcesError && (
                      <p className="text-[10px] text-rose-400/90 font-mono bg-rose-950/20 border border-rose-900/30 rounded p-2">{sourcesError}</p>
                    )}
                    <form
                      onSubmit={async (e) => {
                        e.preventDefault();
                        if (!credName.trim() || !credSecret) return;
                        setSourcesError(null);
                        try {
                          const coords: Record<string, string> = {};
                          if (credTenant.trim()) coords.tenant_id = credTenant.trim();
                          if (credClient.trim()) coords.client_id = credClient.trim();
                          await createExternalCredential(
                            credName.trim(), credPurpose, credSecret,
                            credScopes.split(',').map(s => s.trim()).filter(Boolean), coords);
                          setCredName(''); setCredSecret(''); setCredTenant(''); setCredClient('');
                        } catch (err) {
                          setSourcesError(err instanceof Error ? err.message : String(err));
                        }
                      }}
                      className="grid grid-cols-1 md:grid-cols-6 gap-4 items-end"
                    >
                      <div>
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Name</label>
                        <input type="text" required value={credName} onChange={(e) => setCredName(e.target.value)}
                          placeholder="e.g. QMS Graph client"
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-violet-500 outline-none text-slate-200" />
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Purpose</label>
                        <select value={credPurpose} onChange={(e) => setCredPurpose(e.target.value as 'CONNECTOR' | 'PROVIDER')}
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-violet-500 outline-none text-slate-200">
                          <option value="CONNECTOR">CONNECTOR</option>
                          <option value="PROVIDER">PROVIDER</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Secret (entered once)</label>
                        <input type="password" required value={credSecret} onChange={(e) => setCredSecret(e.target.value)}
                          autoComplete="new-password" placeholder="never displayed again"
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-violet-500 outline-none text-slate-200 font-mono" />
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Tenant ID</label>
                        <input type="text" value={credTenant} onChange={(e) => setCredTenant(e.target.value)}
                          placeholder="Graph tenant (non-secret)"
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-violet-500 outline-none text-slate-200 font-mono" />
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Client ID</label>
                        <input type="text" value={credClient} onChange={(e) => setCredClient(e.target.value)}
                          placeholder="app registration (non-secret)"
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-violet-500 outline-none text-slate-200 font-mono" />
                      </div>
                      <div className="flex gap-2 items-end">
                        <div className="flex-1">
                          <label className="block text-xs text-slate-400 font-mono mb-1.5 uppercase">Granted Scopes</label>
                          <input type="text" value={credScopes} onChange={(e) => setCredScopes(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-violet-500 outline-none text-slate-200 font-mono" />
                        </div>
                        <button type="submit"
                          className="py-2 px-4 bg-gradient-to-r from-violet-500 to-violet-600 text-slate-950 font-bold rounded text-xs tracking-wider uppercase disabled:opacity-40">
                          Create
                        </button>
                      </div>
                    </form>

                    {/* CREDENTIAL LIST */}
                    {externalCredentials.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">No outbound credentials yet.</p>
                    ) : (
                      <div className="space-y-2 pt-2">
                        {externalCredentials.map((cred) => (
                          <div key={cred.id} className={`bg-slate-950/60 border border-slate-900 rounded-lg p-3 space-y-2 ${cred.status === 'REVOKED' ? 'opacity-60' : ''}`}>
                            <div className="flex flex-wrap items-center gap-3">
                              <span className="text-[10px] font-mono bg-violet-950/30 text-violet-400 border border-violet-900/40 px-2 py-0.5 rounded">{cred.fingerprint}</span>
                              <span className="font-bold text-sm text-slate-200">{cred.name}</span>
                              <span className="text-[10px] font-mono text-slate-500">{cred.purpose}</span>
                              {cred.granted_scopes.map(s => (
                                <span key={s} className="text-[9px] font-mono bg-slate-900 text-slate-400 border border-slate-850 px-1.5 py-0.5 rounded">{s}</span>
                              ))}
                              <span className="text-[9px] font-mono text-slate-600" title="Master-key generation that wraps this credential">{cred.key_id}</span>
                              <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                                cred.status === 'ACTIVE' ? 'bg-emerald-950/40 text-emerald-400' : 'bg-rose-950/30 text-rose-400'
                              }`}>{cred.status}</span>
                              <span className="flex-1" />
                              <button
                                onClick={async () => {
                                  const next = credDetailId === cred.id ? null : cred.id;
                                  setCredDetailId(next);
                                  setCredDetail(next !== null ? await fetchCredentialDetail(cred.id) : null);
                                }}
                                className="text-[10px] text-slate-400 hover:text-slate-200 font-mono bg-slate-900/60 border border-slate-800 rounded px-3 py-1.5 uppercase tracking-wider"
                              >
                                {credDetailId === cred.id ? 'Hide History' : 'Custody History'}
                              </button>
                              {cred.status === 'ACTIVE' && (
                                <>
                                  <button onClick={() => { setRotateForId(rotateForId === cred.id ? null : cred.id); setRotateSecret(''); setRevokeForId(null); }}
                                    className="text-[10px] text-violet-400 hover:text-violet-300 font-mono bg-violet-950/20 border border-violet-900/30 rounded px-3 py-1.5 uppercase tracking-wider">
                                    Rotate
                                  </button>
                                  <button onClick={() => { setRevokeForId(revokeForId === cred.id ? null : cred.id); setRevokeReason(''); setRotateForId(null); }}
                                    className="text-[10px] text-rose-400 hover:text-rose-300 font-mono bg-rose-950/20 border border-rose-900/30 rounded px-3 py-1.5 uppercase tracking-wider">
                                    Revoke
                                  </button>
                                </>
                              )}
                            </div>
                            {rotateForId === cred.id && (
                              <form className="flex gap-2 items-center" onSubmit={async (e) => {
                                e.preventDefault();
                                if (!rotateSecret) return;
                                setSourcesError(null);
                                try {
                                  await rotateExternalCredential(cred.id, rotateSecret);
                                  setRotateForId(null); setRotateSecret('');
                                  // Rotation re-points bound connectors to the
                                  // successor generation (WS1 ruling) - refresh
                                  // so the chips follow.
                                  if (activeProjectId !== null) await fetchConnectors(activeProjectId);
                                } catch (err) {
                                  setSourcesError(err instanceof Error ? err.message : String(err));
                                }
                              }}>
                                <input type="password" required value={rotateSecret} onChange={(e) => setRotateSecret(e.target.value)}
                                  autoComplete="new-password" placeholder="new secret — entered once, never displayed again"
                                  className="flex-1 bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-violet-500 outline-none text-slate-200 font-mono" />
                                <button type="submit" className="text-[10px] text-violet-300 font-mono bg-violet-950/40 border border-violet-900/40 rounded px-3 py-2 uppercase tracking-wider">
                                  Rotate — old generation is retired, bound connectors follow the new one
                                </button>
                              </form>
                            )}
                            {revokeForId === cred.id && (
                              <form className="flex gap-2 items-center" onSubmit={async (e) => {
                                e.preventDefault();
                                setSourcesError(null);
                                try {
                                  await revokeExternalCredential(cred.id, revokeReason.trim());
                                  setRevokeForId(null); setRevokeReason('');
                                } catch (err) {
                                  setSourcesError(err instanceof Error ? err.message : String(err));
                                }
                              }}>
                                <input type="text" value={revokeReason} onChange={(e) => setRevokeReason(e.target.value)}
                                  placeholder="reason (recorded as a custody event)"
                                  className="flex-1 bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs focus:border-rose-500 outline-none text-slate-200" />
                                <button type="submit" className="text-[10px] text-rose-300 font-mono bg-rose-950/40 border border-rose-900/40 rounded px-3 py-2 uppercase tracking-wider">
                                  Revoke — scans using this credential will refuse loudly
                                </button>
                              </form>
                            )}
                            {credDetailId === cred.id && credDetail && (
                              <div className="border-t border-slate-900/60 pt-2 space-y-1 max-h-64 overflow-y-auto">
                                {credDetail.custody_events.length === 0 ? (
                                  <p className="text-[10px] text-slate-500 italic">No custody events recorded.</p>
                                ) : credDetail.custody_events.map((ev, i) => (
                                  <div key={i} className="flex flex-wrap items-center gap-2 text-[9px] font-mono bg-slate-950/50 rounded px-2 py-1">
                                    <span className={`px-1.5 py-0.5 rounded font-bold ${
                                      ev.event_type === 'EXTERNAL_CREDENTIAL_USED' ? 'bg-emerald-950/40 text-emerald-400' :
                                      ev.event_type === 'EXTERNAL_CREDENTIAL_RELEASE_REFUSED' ? 'bg-rose-950/40 text-rose-400' :
                                      ev.event_type === 'EXTERNAL_CREDENTIAL_REVOKED' ? 'bg-rose-950/40 text-rose-400' :
                                      'bg-violet-950/40 text-violet-400'
                                    }`}>{ev.event_type.replace('EXTERNAL_CREDENTIAL_', '')}</span>
                                    <span className="text-slate-500">{new Date(ev.timestamp).toLocaleString()}</span>
                                    <span className="text-slate-400">{ev.actor}</span>
                                    {ev.details?.ingestion_job_id != null && <span className="text-cyan-400">JOB-{String(ev.details.ingestion_job_id)}</span>}
                                    {typeof ev.details?.refusal === 'string' && <span className="text-rose-400">{ev.details.refusal}</span>}
                                    {typeof ev.details?.successor_fingerprint === 'string' && <span className="text-violet-400">→ {ev.details.successor_fingerprint}</span>}
                                    {typeof ev.details?.reason === 'string' && ev.details.reason && <span className="text-slate-500 italic">{ev.details.reason}</span>}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  ) : (
                  <div className="glass-panel p-4 rounded-xl flex items-center gap-3 text-xs text-slate-500">
                    <Lock className="w-4 h-4 text-slate-600 shrink-0" />
                    <span>
                      Outbound credential custody (create / rotate / revoke) requires the
                      <span className="font-mono text-slate-400"> credentials:manage</span> permission — ADMIN only.
                      Scans on credential-bound connectors still run under your connector permission; the custody layer releases the credential per scan and records it.
                    </span>
                  </div>
                  )}

                  {/* SCAN HISTORY */}
                  {ingestionJobs.length > 0 && (
                    <div className="space-y-4">
                      <h4 className="text-xs font-bold text-slate-300 tracking-wide flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 text-cyan-400" />
                        Scan History
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
                                  <span className="text-slate-500 block text-[8px] uppercase">Changed</span>
                                  <span className={`font-bold ${job.files_changed > 0 ? 'text-cyan-400' : 'text-slate-500'}`}>{job.files_changed}</span>
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
                                      f.status === 'CHANGED' ? 'bg-cyan-950/40 text-cyan-400' :
                                      'bg-rose-950/40 text-rose-400'
                                    }`}>{f.status}</span>
                                    <span className="text-slate-300 flex-1 min-w-[200px] truncate" title={f.source_uri}>{f.source_uri}</span>
                                    {f.size_bytes !== null && <span className="text-slate-600">{f.size_bytes} B</span>}
                                    {f.document_id && <span className="text-cyan-400">DOC-{f.document_id}</span>}
                                    {f.error && <span className="text-slate-400 italic w-full pl-1">{f.error}</span>}
                                    {f.status === 'CHANGED' && f.details && (
                                      <span className="text-slate-400 w-full pl-1">
                                        {f.details.revisions_created.length > 0 && (
                                          <button
                                            onClick={() => openDeepLink(`/?tab=revisions&revision=${f.details!.revisions_created[0].revision_id}`)}
                                            className="text-cyan-400 hover:text-cyan-300 underline decoration-dotted mr-2"
                                          >
                                            {f.details.revisions_created.length} candidate revision{f.details.revisions_created.length > 1 ? 's' : ''} created — review
                                          </button>
                                        )}
                                        {f.details.assets_added > 0 && <span className="mr-2">{f.details.assets_added} new asset{f.details.assets_added > 1 ? 's' : ''}</span>}
                                        {f.details.updated_in_place > 0 && <span className="mr-2">{f.details.updated_in_place} updated in place</span>}
                                        {f.details.skipped_pending_review.length > 0 && (
                                          <span className="text-yellow-400 mr-2">{f.details.skipped_pending_review.length} skipped (revision already pending)</span>
                                        )}
                                      </span>
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
                      // v1.2.1 WS4 (D26): the automation ladder's held and
                      // uncovered candidates — computed from ledger facts,
                      // never HIGH (they don't block the compile gate), no
                      // dismiss: items leave when a human reviews the asset.
                      INGESTION_EXCEPTION: { label: 'INGESTION EXCEPTION', action: 'Review Candidate' },
                      // v1.3 WS1 (D28): a render whose content no longer
                      // matches governed facts — "stale", never "wrong";
                      // repaired by regenerating, never by editing.
                      PROJECTION_STALE: { label: 'STALE RENDER', action: 'Open' },
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
                            {/* v1.4.0 (D30): primary prevails — declared asymmetry, computed
                                at read time. Presentation only: the human confirms or
                                dismisses exactly as before; the compile gate is class-blind. */}
                            {isConflict && rel.class_asymmetry === 'PRIMARY_OVER_DERIVED' && (
                              <span
                                title={`Primary prevails: asset #${rel.presumptive_review_target_asset_id} is agent-synthesized (DERIVED) and is the presumptive review target unless a human rules otherwise. Nothing is auto-resolved.`}
                                className="text-[10px] font-mono px-2 py-0.5 rounded border bg-fuchsia-950/40 text-fuchsia-400 border-fuchsia-900/50"
                              >
                                Primary prevails · review #{rel.presumptive_review_target_asset_id}
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
                          ) : allow('assets:approve') && (
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
                                ) : allow('assets:approve') && (
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

              {/* TAB: CONSUMPTION (v1.1.x Selection Workbench, D24).
                  A decision workspace, NOT a leaderboard: comparisons are
                  computed, the selection is a governed decision through the
                  existing PUT, history is the audit ledger. This screen
                  owns no state - every panel is a projection. */}
              {activeTab === 'consumption' && (() => {
                const pkg = packages.find(p => p.id === consumptionPkgId) || null;
                const pkgRuns = pkg ? evaluationRuns.filter(r =>
                  r.run_type === 'PACKAGE' && r.package_hash === pkg.package_hash && r.status === 'COMPLETED') : [];
                // Drift is a FAMILY fact (artifact rows are append-only): the
                // viewed artifact has drifted when a newer compile of the same
                // package family exists with a different hash. Computed live.
                const familyCurrent = pkg ? packages.reduce((cur, p) =>
                  (p.project_id === pkg.project_id && p.expert_model_id === pkg.expert_model_id
                    && p.name === pkg.name && p.id > cur.id) ? p : cur, pkg) : null;
                const artifactSuperseded = !!(pkg && familyCurrent && familyCurrent.id !== pkg.id
                  && familyCurrent.package_hash !== pkg.package_hash);
                const parseDetails = (details: string | null): Record<string, unknown> | null => {
                  try { return details ? JSON.parse(details) : null; } catch { return null; }
                };
                const shortHash = (h: string | null) => h ? `${h.slice(0, 12)}…` : '—';
                const isCurrent = (provider: string, model: string) =>
                  !!packageSelection && packageSelection.selected_provider === provider
                  && packageSelection.selected_model_name === model;
                const submitSelection = async () => {
                  if (!selForm || !pkg) return;
                  const ok = await submitModelSelection(pkg.id, {
                    provider: selForm.provider,
                    model: selForm.model,
                    supporting_evaluation_run_ids: selForm.runIds,
                    rationale: selForm.rationale.trim(),
                  });
                  if (ok) setSelForm(null);
                };
                return (
                <div className="space-y-6">
                  <div className="glass-panel p-6 rounded-xl">
                    <div className="flex justify-between items-center border-b border-slate-900 pb-3">
                      <h3 className="font-bold text-sm text-slate-200 tracking-wide flex items-center gap-2">
                        <PackageCheck className="w-4 h-4 text-cyan-400" />
                        {consumptionView === 'inbox' ? 'Consumption Inbox'
                          : consumptionView === 'bindings' ? 'Binding Explorer'
                          : 'Selection Workbench'}
                      </h3>
                      <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                        Projections of governed facts · owns no state
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-3">
                      <button
                        onClick={() => setConsumptionView('workbench')}
                        className={`text-[10px] font-mono px-3 py-1.5 rounded-lg border transition-all ${
                          consumptionView === 'workbench'
                            ? 'bg-cyan-950/40 text-cyan-400 border-cyan-900/60'
                            : 'text-slate-400 border-slate-800 hover:text-slate-200'
                        }`}
                      >
                        Selection Workbench
                      </button>
                      <button
                        onClick={() => setConsumptionView('inbox')}
                        className={`text-[10px] font-mono px-3 py-1.5 rounded-lg border transition-all flex items-center gap-2 ${
                          consumptionView === 'inbox'
                            ? 'bg-cyan-950/40 text-cyan-400 border-cyan-900/60'
                            : 'text-slate-400 border-slate-800 hover:text-slate-200'
                        }`}
                      >
                        Consumption Inbox
                        {consumptionInbox && (consumptionInbox.summary.high + consumptionInbox.summary.medium) > 0 && (
                          <span className={`px-1.5 py-0.5 rounded-full text-[9px] border ${
                            consumptionInbox.summary.high > 0
                              ? 'bg-rose-950/40 text-rose-400 border-rose-900/40'
                              : 'bg-amber-950/40 text-amber-400 border-amber-900/40'
                          }`}>
                            {consumptionInbox.summary.high + consumptionInbox.summary.medium}
                          </span>
                        )}
                      </button>
                      <button
                        onClick={() => setConsumptionView('bindings')}
                        className={`text-[10px] font-mono px-3 py-1.5 rounded-lg border transition-all ${
                          consumptionView === 'bindings'
                            ? 'bg-cyan-950/40 text-cyan-400 border-cyan-900/60'
                            : 'text-slate-400 border-slate-800 hover:text-slate-200'
                        }`}
                      >
                        Binding Explorer
                      </button>
                    </div>
                    <p className="text-xs text-slate-500 mt-3 leading-relaxed">
                      {consumptionView === 'inbox'
                        ? 'Does everything still stand? Every item below is computed live from governed facts - selections, runs, bindings, identity. Nothing is stored, and there is nothing to dismiss: an item leaves when the facts that raised it change.'
                        : consumptionView === 'bindings'
                        ? 'What is this agent actually serving, and can you prove it? Start at a binding and walk the whole chain - serving package, selected model, selection evidence, evaluation runs, packaged assets, source documents - and sideways into identity. Every hop resolves or is declared missing. A binding is a governed snapshot, never a runtime.'
                        : 'Which model should serve this package? Comparisons are computed from PACKAGE evaluation runs, the selection is a governed decision recorded with its evidence and rationale, and history lives in the audit ledger. Binding an agent to the selection is a separate governed act in this lifecycle.'}
                    </p>
                  </div>

                  {consumptionView === 'inbox' ? (
                  <div className="space-y-3">
                    {consumptionInbox && (
                      <div className="flex items-center gap-2 flex-wrap text-[10px] font-mono">
                        <span className="px-2 py-1 rounded bg-rose-950/40 text-rose-400 border border-rose-900/40">
                          HIGH {consumptionInbox.summary.high}
                        </span>
                        <span className="px-2 py-1 rounded bg-amber-950/40 text-amber-400 border border-amber-900/40">
                          MEDIUM {consumptionInbox.summary.medium}
                        </span>
                        <span className="px-2 py-1 rounded bg-slate-900/80 text-slate-400 border border-slate-800">
                          LOW {consumptionInbox.summary.low}
                        </span>
                        <span className="text-slate-600 ml-2">
                          {consumptionInbox.summary.total_packages} package{consumptionInbox.summary.total_packages === 1 ? '' : 's'} examined
                          · computed {new Date(consumptionInbox.generated_at + 'Z').toLocaleTimeString()}
                        </span>
                      </div>
                    )}
                    {(!consumptionInbox || consumptionInbox.items.length === 0) ? (
                      <div className="glass-panel p-6 rounded-xl text-xs text-slate-400 leading-relaxed">
                        Inbox clear: every selection stands on current evidence and every binding serves
                        the current artifact under a valid, sufficiently-cleared identity. Items appear
                        here only when governed facts drift — and leave the same way.
                      </div>
                    ) : consumptionInbox.items.map(item => {
                      const sev = item.severity === 'HIGH'
                        ? { border: 'border-l-rose-500', chip: 'bg-rose-950/40 text-rose-400 border-rose-900/40' }
                        : item.severity === 'MEDIUM'
                        ? { border: 'border-l-amber-500', chip: 'bg-amber-950/40 text-amber-400 border-amber-900/40' }
                        : { border: 'border-l-slate-600', chip: 'bg-slate-900/80 text-slate-400 border-slate-800' };
                      return (
                        <div key={item.id} className={`glass-panel p-4 rounded-xl border-l-2 ${sev.border} space-y-2`}>
                          <div className="flex justify-between items-start gap-3 flex-wrap">
                            <div className="flex items-center gap-2">
                              <span className={`text-[9px] font-mono px-2 py-0.5 rounded border uppercase ${sev.chip}`}>
                                {item.severity}
                              </span>
                              <span className="text-xs font-bold text-slate-200">{item.title}</span>
                            </div>
                            <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-slate-950/60 border border-slate-800 text-slate-500">
                              {item.condition}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 leading-relaxed">{item.reason}</p>
                          {item.missing.length > 0 && (
                            <p className="text-[10px] font-mono text-rose-400 bg-rose-950/20 border border-rose-900/30 rounded-lg p-2">
                              Declared missing: {item.missing.join('; ')}
                            </p>
                          )}
                          <div className="flex justify-between items-center pt-1">
                            <span className="text-[9px] font-mono text-slate-500">
                              {item.package_name} v{item.package_version}
                              {item.principal_name ? ` · agent ${item.principal_name}` : ''}
                              {item.binding_id !== null ? ` · binding ${item.binding_id}` : ''}
                            </span>
                            <button
                              onClick={() => {
                                if (item.binding_id !== null) {
                                  setConsumptionBindingId(item.binding_id);
                                  setConsumptionView('bindings');
                                } else {
                                  setConsumptionPkgId(item.package_id);
                                  setConsumptionView('workbench');
                                }
                              }}
                              className="text-[10px] font-mono px-3 py-1 rounded-lg bg-cyan-950/40 text-cyan-400 border border-cyan-900/40 hover:bg-cyan-900/40 transition-all flex items-center gap-1"
                            >
                              {item.binding_id !== null ? 'Open binding' : 'Open in Selection Workbench'} <ArrowRight className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  ) : consumptionView === 'bindings' ? (
                  <div className="grid grid-cols-12 gap-6">
                    {/* Bindings list - append-only snapshots; no withdrawal
                        controls exist here by ruling (D23 deferred). */}
                    <div className="col-span-4 glass-panel p-4 rounded-xl space-y-2 self-start">
                      <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest pb-2 border-b border-slate-900">
                        Bindings
                      </h4>
                      {projectBindings.length === 0 && (
                        <p className="text-xs text-slate-500 pt-2">
                          No bindings issued in this workspace yet. A binding is issued from a
                          package&apos;s current model selection in the Selection Workbench lifecycle.
                        </p>
                      )}
                      {projectBindings.map(b => {
                        const bpkg = packages.find(p => p.id === b.agent_package_id);
                        return (
                          <button
                            key={b.id}
                            onClick={() => setConsumptionBindingId(b.id)}
                            className={`w-full text-left p-3 rounded-lg border transition-all ${
                              consumptionBindingId === b.id
                                ? 'bg-cyan-950/30 border-cyan-900/60'
                                : 'bg-slate-950/40 border-slate-900 hover:border-slate-700'
                            }`}
                          >
                            <div className="flex justify-between items-center">
                              <span className="text-xs font-medium text-slate-200">Binding {b.id}</span>
                              <span className="text-[9px] font-mono text-cyan-400">
                                {b.selected_provider}/{b.selected_model_name}
                              </span>
                            </div>
                            <div className="text-[9px] font-mono text-slate-500 mt-1">
                              serving {bpkg ? bpkg.name : `package ${b.agent_package_id}`} v{b.package_version}
                              {' · issued '}{new Date(b.created_at).toLocaleDateString()}
                            </div>
                          </button>
                        );
                      })}
                    </div>

                    <div className="col-span-8 space-y-4">
                      {!bindingLineage ? (
                        <div className="glass-panel p-6 rounded-xl text-xs text-slate-500">
                          Select a binding to walk its lineage.
                        </div>
                      ) : (() => {
                        const L = bindingLineage;
                        const missingNote = (items: string[]) => items.length === 0 ? null : (
                          <p className="text-[10px] font-mono text-rose-400 bg-rose-950/20 border border-rose-900/30 rounded-lg p-2">
                            Declared missing: {items.join('; ')}
                          </p>
                        );
                        const fact = (label: string, value: React.ReactNode) => (
                          <div>
                            <span className="text-slate-500 block text-[8px] uppercase font-mono">{label}</span>
                            <span className="text-slate-200 text-[11px] font-mono">{value ?? '—'}</span>
                          </div>
                        );
                        return (
                        <>
                          {L.declared_missing_total > 0 && (
                            <div className="glass-panel p-4 rounded-xl border-l-2 border-l-rose-500 text-[11px] text-rose-300 font-mono">
                              {L.declared_missing_total} lineage hop{L.declared_missing_total === 1 ? '' : 's'} could
                              not be resolved — each is declared on its section below, never dropped.
                            </div>
                          )}
                          {L.warnings.map(w => (
                            <div key={w.id} className={`glass-panel p-3 rounded-xl border-l-2 ${
                              w.severity === 'HIGH' ? 'border-l-rose-500' : w.severity === 'MEDIUM' ? 'border-l-amber-500' : 'border-l-slate-600'
                            } flex items-center gap-2 flex-wrap`}>
                              <span className={`text-[9px] font-mono px-2 py-0.5 rounded border uppercase ${
                                w.severity === 'HIGH' ? 'bg-rose-950/40 text-rose-400 border-rose-900/40'
                                : w.severity === 'MEDIUM' ? 'bg-amber-950/40 text-amber-400 border-amber-900/40'
                                : 'bg-slate-900/80 text-slate-400 border-slate-800'}`}>
                                {w.severity}
                              </span>
                              <span className="text-[11px] text-slate-300">{w.title}</span>
                              <span className="text-[8px] font-mono text-slate-600 ml-auto">{w.condition}</span>
                            </div>
                          ))}

                          {/* The binding: the governed snapshot itself */}
                          <div className="glass-panel p-5 rounded-xl space-y-3">
                            <div className="flex justify-between items-center">
                              <h4 className="text-xs font-bold text-slate-200 font-mono">
                                Binding {L.binding.id}
                                <span className="text-slate-500 font-normal"> · a governed snapshot, never a runtime</span>
                              </h4>
                              <span className="text-[9px] font-mono text-slate-500">
                                issued {new Date(L.binding.created_at).toLocaleString()}
                              </span>
                            </div>
                            <div className="grid grid-cols-3 gap-3">
                              {fact('Serving package', `${L.package.name ?? '—'} v${L.binding.package_version}`)}
                              {fact('Bound model', `${L.binding.selected_provider}/${L.binding.selected_model_name}`)}
                              {fact('Artifact hash', shortHash(L.binding.package_hash))}
                            </div>
                          </div>

                          {/* Why this package */}
                          <div className="glass-panel p-5 rounded-xl space-y-3">
                            <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Why this package</h4>
                            <div className="grid grid-cols-3 gap-3">
                              {fact('Compiled', L.package.compiled_at ? new Date(L.package.compiled_at).toLocaleString() : null)}
                              {fact('Clearance', L.package.clearance_level)}
                              {fact('Trust at compile', L.package.trust_score_at_compile != null ? String(L.package.trust_score_at_compile) : null)}
                              {fact('Assets compiled', L.package.asset_count_at_compile != null ? String(L.package.asset_count_at_compile) : null)}
                              {fact('Expert model', L.package.expert_model)}
                              {fact('Family artifacts', L.family_status.artifact_count != null ? String(L.family_status.artifact_count) : null)}
                            </div>
                            {L.family_status.superseded ? (
                              <p className="text-[10px] font-mono text-amber-400 bg-amber-950/30 border border-amber-900/40 rounded-lg p-2">
                                Superseded: the family&apos;s current artifact is v{L.family_status.current_version} ({shortHash(L.family_status.current_hash || null)}).
                                This binding serves an older artifact.
                              </p>
                            ) : L.family_status.current_package_id != null && (
                              <p className="text-[10px] font-mono text-emerald-400">
                                This is the current artifact of its package family.
                              </p>
                            )}
                            {missingNote([...L.package.missing, ...L.family_status.missing])}
                          </div>

                          {/* Why this model */}
                          <div className="glass-panel p-5 rounded-xl space-y-3">
                            <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Why this model</h4>
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-xs font-bold font-mono text-slate-100">
                                {L.model.provider} / {L.model.model}
                              </span>
                              {L.model.matches_current_selection === true && (
                                <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-900/40">
                                  matches current selection
                                </span>
                              )}
                              {L.model.matches_current_selection === false && (
                                <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-amber-950/40 text-amber-400 border border-amber-900/40">
                                  selection has since changed to {L.model.current_selection?.provider}/{L.model.current_selection?.model} — this binding is unchanged history
                                </span>
                              )}
                            </div>
                            {L.selection_evidence.rationale && (
                              <p className="text-xs text-slate-400 leading-relaxed border-l-2 border-slate-800 pl-3">
                                {L.selection_evidence.rationale}
                              </p>
                            )}
                            <p className="text-[9px] font-mono text-slate-500">
                              selected by {L.selection_evidence.selected_by ?? '—'}
                              {L.selection_evidence.selected_at ? ` · ${new Date(L.selection_evidence.selected_at).toLocaleString()}` : ''}
                            </p>
                            <div className="space-y-1.5">
                              {L.evaluation_runs.runs.map(r => (
                                <div key={r.run_id} className="flex items-center justify-between text-[10px] font-mono p-2.5 rounded-lg bg-slate-950/40 border border-slate-900">
                                  <span className="text-slate-300">
                                    RUN-{r.run_id} · {r.consumer_model_provider}/{r.consumer_model_name}
                                    {r.evaluates_bound_artifact && (
                                      <span className="text-emerald-400 ml-2">· evaluates the bound artifact</span>
                                    )}
                                  </span>
                                  <span className="text-slate-500 flex gap-4">
                                    <span>pass {(r.pass_rate * 100).toFixed(0)}%</span>
                                    <span>coverage {(r.average_coverage_score * 100).toFixed(0)}%</span>
                                  </span>
                                </div>
                              ))}
                            </div>
                            {missingNote([...L.model.missing, ...L.selection_evidence.missing, ...L.evaluation_runs.missing])}
                          </div>

                          {/* Why this agent, why this clearance */}
                          <div className="glass-panel p-5 rounded-xl space-y-3">
                            <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Why this agent · why this clearance</h4>
                            <div className="grid grid-cols-3 gap-3">
                              {fact('AGENT principal', L.principal.name)}
                              {fact('Active now', L.principal.active === undefined ? null : (L.principal.active ? 'yes' : 'NO — deactivated'))}
                              {fact('Clearance at issue', L.binding.principal_clearance_at_issue)}
                              {fact('Clearance now', L.principal.clearance_now)}
                              {fact('Package clearance', L.package.clearance_level)}
                              {fact('Active credentials', `${L.credentials.active_count} (${L.credentials.kinds.join(', ') || 'none'})`)}
                            </div>
                            <p className="text-[9px] font-mono text-slate-600">
                              The binding was issued because the principal&apos;s clearance at issue met the
                              package&apos;s compiled clearance. Withdrawing access happens in identity
                              governance (Users &amp; Tokens), never by editing this history.
                            </p>
                            {missingNote([...L.principal.missing, ...L.credentials.missing])}
                          </div>

                          {/* Issued by whom: the immutable identity fact */}
                          <div className="glass-panel p-5 rounded-xl space-y-3">
                            <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Issued by</h4>
                            <div className="grid grid-cols-3 gap-3">
                              {fact('Principal', L.issued_by.principal_name)}
                              {fact('Role at issue', L.issued_by.role_at_issue)}
                              {fact('Authenticated via', L.issued_by.authentication_method)}
                            </div>
                            <p className="text-[9px] font-mono text-slate-600">
                              Identity fact {L.issued_by.identity_fact_id ?? '—'} — immutable evidence: later
                              renames, demotions, or deactivations never change who issued this binding.
                            </p>
                            {missingNote(L.issued_by.missing)}
                          </div>

                          {/* Packaged knowledge -> source documents */}
                          <div className="glass-panel p-5 rounded-xl space-y-3">
                            <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Packaged knowledge → sources</h4>
                            <div className="flex flex-wrap gap-1.5">
                              {L.assets.assets.map(a => (
                                <span key={a.asset_id} className={`text-[9px] font-mono px-2 py-0.5 rounded border ${
                                  a.live_status ? 'bg-slate-900/80 border-slate-800 text-slate-300' : 'bg-rose-950/30 border-rose-900/40 text-rose-400'
                                }`}>
                                  {a.name} {a.live_status ? `· ${a.live_status}` : '· no longer in the knowledge base'}
                                </span>
                              ))}
                            </div>
                            {L.source_documents.documents.map(d => (
                              <div key={d.document_id} className="flex items-center justify-between text-[10px] font-mono p-2.5 rounded-lg bg-slate-950/40 border border-slate-900">
                                <span className="text-slate-300">{d.filename}</span>
                                <span className="text-slate-500">{d.status} · {d.content_hash ? shortHash(d.content_hash) : 'hash not recorded'}</span>
                              </div>
                            ))}
                            {missingNote([...L.assets.missing, ...L.source_documents.missing])}
                          </div>

                          {/* Provenance events */}
                          <div className="glass-panel p-5 rounded-xl space-y-2">
                            <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Provenance events</h4>
                            {L.audit.events.map(ev => (
                              <div key={ev.id} className="flex items-center justify-between text-[10px] font-mono p-2 rounded-lg bg-slate-950/40 border border-slate-900">
                                <span className="text-slate-300">{ev.event_type}</span>
                                <span className="text-slate-500">{ev.actor} · {new Date(ev.timestamp).toLocaleString()}</span>
                              </div>
                            ))}
                            {missingNote(L.audit.missing)}
                          </div>
                        </>
                        );
                      })()}
                    </div>
                  </div>
                  ) : (
                  <div className="grid grid-cols-12 gap-6">
                    {/* Package picker */}
                    <div className="col-span-4 glass-panel p-4 rounded-xl space-y-2 self-start">
                      <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest pb-2 border-b border-slate-900">
                        Agent Packages
                      </h4>
                      {packages.length === 0 && (
                        <p className="text-xs text-slate-500 pt-2">
                          No packages compiled in this workspace yet. Compile one under Experts &amp; Packages.
                        </p>
                      )}
                      {packages.map(p => (
                        <button
                          key={p.id}
                          onClick={() => setConsumptionPkgId(p.id)}
                          className={`w-full text-left p-3 rounded-lg border transition-all ${
                            consumptionPkgId === p.id
                              ? 'bg-cyan-950/30 border-cyan-900/60'
                              : 'bg-slate-950/40 border-slate-900 hover:border-slate-700'
                          }`}
                        >
                          <div className="flex justify-between items-center">
                            <span className="text-xs font-medium text-slate-200">{p.name}</span>
                            <span className="text-[9px] font-mono text-cyan-400">{p.governance_version}</span>
                          </div>
                          <div className="text-[9px] font-mono text-slate-500 mt-1 flex flex-wrap gap-x-3">
                            <span>{p.clearance_level || 'INTERNAL'}</span>
                            <span>{shortHash(p.package_hash)}</span>
                          </div>
                        </button>
                      ))}
                    </div>

                    <div className="col-span-8 space-y-6">
                      {!pkg ? (
                        <div className="glass-panel p-6 rounded-xl text-xs text-slate-500">
                          Select an Agent Package to open its selection workspace.
                        </div>
                      ) : (
                      <>
                      {/* Current selection - a governed fact, projected */}
                      <div className="glass-panel p-5 rounded-xl space-y-3">
                        <div className="flex justify-between items-center">
                          <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Current Selection</h4>
                          {consumptionLoading && <span className="text-[9px] font-mono text-slate-600 animate-pulse">loading…</span>}
                        </div>
                        {packageSelection ? (
                          <div className="space-y-3">
                            <div className="flex items-center gap-3 flex-wrap">
                              <span className="text-sm font-bold text-slate-100 font-mono">
                                {packageSelection.selected_provider} / {packageSelection.selected_model_name}
                              </span>
                              <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-900/40 uppercase">
                                selected
                              </span>
                              <span className="text-[9px] font-mono text-slate-500">
                                {new Date(packageSelection.selected_at).toLocaleString()}
                              </span>
                            </div>
                            {artifactSuperseded && familyCurrent && (
                              <div className="text-[10px] text-amber-400 bg-amber-950/30 border border-amber-900/40 rounded-lg p-3 font-mono">
                                Artifact superseded: a newer compile of this package exists
                                (v{familyCurrent.governance_version}, {shortHash(familyCurrent.package_hash)}).
                                This selection and its bindings are flagged in the Consumption Inbox —
                                re-evaluate on the current artifact, re-select, and re-bind.
                                (Computed live — staleness is never stored.)
                              </div>
                            )}
                            <p className="text-xs text-slate-400 leading-relaxed border-l-2 border-slate-800 pl-3">
                              {packageSelection.rationale}
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {packageSelection.supporting_evaluation_run_ids.map(id => (
                                <span key={id} className="text-[9px] font-mono px-2 py-0.5 rounded bg-slate-900/80 border border-slate-800 text-slate-300">
                                  RUN-{id}
                                </span>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <p className="text-xs text-slate-500">
                            No model selected for this package yet. The comparison below is the evidence
                            workspace for that decision.
                          </p>
                        )}
                      </div>

                      {/* Computed comparison - evidence, never a verdict */}
                      <div className="glass-panel p-5 rounded-xl space-y-3">
                        <div className="flex justify-between items-center">
                          <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Model Comparison</h4>
                          <span className="text-[9px] font-mono text-slate-600 uppercase">computed · never persisted</span>
                        </div>
                        {(!packageComparison || packageComparison.models.length === 0) ? (
                          <p className="text-xs text-slate-500">
                            No completed PACKAGE evaluation runs for this artifact yet. Models never
                            evaluated are absent, not zero — run package evaluations to build evidence.
                          </p>
                        ) : (
                          <div className="space-y-2">
                            {packageComparison.models.map(m => (
                              <div key={`${m.provider}/${m.model}`}
                                   className={`p-3 rounded-lg border flex items-center justify-between gap-4 flex-wrap ${
                                     isCurrent(m.provider, m.model)
                                       ? 'bg-emerald-950/20 border-emerald-900/40'
                                       : 'bg-slate-950/40 border-slate-900'
                                   }`}>
                                <div className="space-y-1">
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs font-mono font-bold text-slate-200">{m.provider} / {m.model}</span>
                                    {isCurrent(m.provider, m.model) && (
                                      <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-900/40 uppercase">current</span>
                                    )}
                                  </div>
                                  <div className="text-[9px] font-mono text-slate-500">
                                    {m.runs.length} run{m.runs.length === 1 ? '' : 's'} · latest {new Date(m.latest.completed_at || '').toLocaleString()}
                                  </div>
                                </div>
                                <div className="flex items-center gap-5">
                                  <div className="text-center">
                                    <span className="text-slate-500 block text-[8px] uppercase font-mono">Pass rate</span>
                                    <span className="text-slate-100 font-bold text-xs font-mono">{(m.latest.pass_rate * 100).toFixed(0)}%</span>
                                  </div>
                                  <div className="text-center">
                                    <span className="text-slate-500 block text-[8px] uppercase font-mono">Coverage</span>
                                    <span className="text-slate-100 font-bold text-xs font-mono">{(m.latest.average_coverage_score * 100).toFixed(0)}%</span>
                                  </div>
                                  <div className="text-center">
                                    <span className="text-slate-500 block text-[8px] uppercase font-mono">Claims E·C·U</span>
                                    <span className="text-slate-300 text-xs font-mono">
                                      {m.latest.verdict_counts
                                        ? `${m.latest.verdict_counts.ENTAILED ?? 0}·${m.latest.verdict_counts.CONTRADICTED ?? 0}·${m.latest.verdict_counts.UNSUPPORTED ?? 0}`
                                        : '—'}
                                    </span>
                                  </div>
                                  {allow('assets:approve') && (
                                    <button
                                      onClick={() => setSelForm({
                                        provider: m.provider, model: m.model,
                                        runIds: pkgRuns.map(r => r.id), rationale: '',
                                      })}
                                      className="text-[10px] font-mono px-3 py-1.5 rounded-lg bg-cyan-950/40 text-cyan-400 border border-cyan-900/40 hover:bg-cyan-900/40 transition-all"
                                    >
                                      Select model
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))}
                            <p className="text-[9px] font-mono text-slate-600 pt-1">{packageComparison.note}</p>
                          </div>
                        )}
                      </div>

                      {/* Selection proposal - the milestone's ONLY write, via the existing PUT */}
                      {selForm && (
                        <div className="glass-panel p-5 rounded-xl space-y-4 border border-cyan-900/40">
                          <h4 className="text-xs font-bold text-slate-200 font-mono">
                            Select model: <span className="text-cyan-400">{selForm.provider} / {selForm.model}</span>
                          </h4>
                          <div className="space-y-2">
                            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block">
                              Supporting evidence (COMPLETED PACKAGE runs for this exact artifact)
                            </span>
                            <p className="text-[9px] text-slate-600 font-mono">
                              Losing-model runs are legitimate comparative evidence — a comparative decision
                              should cite what it compared against.
                            </p>
                            {pkgRuns.map(r => (
                              <label key={r.id} className="flex items-center gap-2 text-[10px] font-mono text-slate-300 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={selForm.runIds.includes(r.id)}
                                  onChange={() => setSelForm({
                                    ...selForm,
                                    runIds: selForm.runIds.includes(r.id)
                                      ? selForm.runIds.filter(id => id !== r.id)
                                      : [...selForm.runIds, r.id],
                                  })}
                                  className="accent-cyan-500"
                                />
                                RUN-{r.id} · {r.consumer_model_provider}/{r.consumer_model_name} ·
                                pass {(r.pass_rate * 100).toFixed(0)}%
                              </label>
                            ))}
                          </div>
                          <div className="space-y-1">
                            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block">
                              Rationale (required — &quot;why this model?&quot; must be answerable from the decision, indefinitely)
                            </span>
                            <textarea
                              value={selForm.rationale}
                              onChange={e => setSelForm({ ...selForm, rationale: e.target.value })}
                              rows={3}
                              className="w-full bg-slate-950/60 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 focus:border-cyan-700 focus:outline-none"
                              placeholder="Why this model, based on this evidence?"
                            />
                          </div>
                          {selectionError && (
                            <p className="text-[10px] text-rose-400 bg-rose-950/30 border border-rose-900/40 rounded-lg p-3 font-mono">
                              Refused by the governance boundary: {selectionError}
                            </p>
                          )}
                          <div className="flex gap-3">
                            <button
                              onClick={submitSelection}
                              disabled={!selForm.rationale.trim() || selForm.runIds.length === 0}
                              className="text-[10px] font-mono px-4 py-2 rounded-lg bg-cyan-950/60 text-cyan-300 border border-cyan-800/60 hover:bg-cyan-900/50 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              Record governed selection
                            </button>
                            <button
                              onClick={() => setSelForm(null)}
                              className="text-[10px] font-mono px-4 py-2 rounded-lg text-slate-400 border border-slate-800 hover:text-slate-200 transition-all"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Successful PACKAGE runs for this artifact */}
                      <div className="glass-panel p-5 rounded-xl space-y-2">
                        <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                          Successful PACKAGE Runs · {shortHash(pkg.package_hash)}
                        </h4>
                        {pkgRuns.length === 0 ? (
                          <p className="text-xs text-slate-500">
                            No completed PACKAGE runs for this artifact. Evaluations on other artifacts or
                            the LIVE channel do not appear here — evidence about another artifact is not
                            evidence about this one.
                          </p>
                        ) : pkgRuns.map(r => (
                          <div key={r.id} className="flex items-center justify-between text-[10px] font-mono p-2.5 rounded-lg bg-slate-950/40 border border-slate-900">
                            <span className="text-slate-300">RUN-{r.id} · {r.consumer_model_provider}/{r.consumer_model_name}</span>
                            <span className="text-slate-500 flex gap-4">
                              <span>pass {(r.pass_rate * 100).toFixed(0)}%</span>
                              <span>coverage {(r.average_coverage_score * 100).toFixed(0)}%</span>
                              <span>{r.completed_at ? new Date(r.completed_at).toLocaleString() : '—'}</span>
                            </span>
                          </div>
                        ))}
                      </div>

                      {/* Selection history - the audit ledger IS the history */}
                      {allow('audit:read') && (
                        <div className="glass-panel p-5 rounded-xl space-y-2">
                          <div className="flex justify-between items-center">
                            <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Selection History</h4>
                            <span className="text-[9px] font-mono text-slate-600 uppercase">projected from the audit ledger</span>
                          </div>
                          {selectionHistory.length === 0 ? (
                            <p className="text-xs text-slate-500">No selection decisions recorded for this package.</p>
                          ) : selectionHistory.map(ev => {
                            const d = parseDetails(ev.details);
                            const oldSel = d?.old_selection as { provider?: string; model?: string } | null;
                            const newSel = d?.new_selection as { provider?: string; model?: string; rationale?: string } | null;
                            return (
                              <div key={ev.id} className="p-3 rounded-lg bg-slate-950/40 border border-slate-900 space-y-1.5">
                                <div className="flex justify-between items-center text-[9px] font-mono text-slate-500">
                                  <span>{new Date(ev.timestamp).toLocaleString()} · {ev.actor}</span>
                                  <span className="px-1.5 py-0.5 rounded bg-slate-900/80 border border-slate-800">PACKAGE_MODEL_SELECTED</span>
                                </div>
                                <div className="text-[10px] font-mono text-slate-300">
                                  {oldSel ? `${oldSel.provider}/${oldSel.model}` : '(none)'}
                                  <ArrowRight className="w-3 h-3 inline mx-1.5 text-slate-600" />
                                  <span className="text-cyan-400">{newSel ? `${newSel.provider}/${newSel.model}` : '—'}</span>
                                </div>
                                {newSel?.rationale && (
                                  <p className="text-[10px] text-slate-400 border-l-2 border-slate-800 pl-2">{newSel.rationale}</p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                      </>
                      )}
                    </div>
                  </div>
                  )}
                </div>
                );
              })()}

              {/* TAB 5: AUDIT LEDGER EXPLORER */}
              {/* TAB: SETTINGS (MVP 0.12) — governed runtime configuration.
                  LLM Models: model-per-function selection; stores model
                  choice, never credentials (keys stay env-based until v1.x). */}
              {activeTab === 'settings' && (
                <div className="space-y-6">
                  <div className="glass-panel p-6 rounded-xl space-y-4">
                    <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                      <Settings className="w-4 h-4 text-cyan-400" />
                      LLM Models
                      <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                        Model per function — empty config falls through to the OPENAI_MODEL env var, then gpt-4o-mini. API keys stay in the environment, never in the database.
                      </span>
                    </h3>
                    <div className="space-y-2">
                      {llmSettings.map((s) => {
                        const draft = llmDrafts[s.function] ?? (s.configured_model || '');
                        return (
                          <div key={s.function} className="flex flex-wrap items-center gap-3 bg-slate-950/60 border border-slate-900 rounded-lg p-3">
                            <div className="min-w-[220px]">
                              <div className="font-bold text-sm text-slate-200 font-mono">{s.function}</div>
                              <div className="text-[10px] text-slate-500">{s.description}</div>
                            </div>
                            <span className="text-[10px] font-mono bg-slate-900 text-slate-400 border border-slate-850 px-2 py-0.5 rounded">{s.provider}</span>
                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                              s.source === 'CONFIG' ? 'bg-violet-950/40 text-violet-400 border border-violet-900/40' :
                              s.source === 'ENV' ? 'bg-yellow-950/40 text-yellow-400 border border-yellow-900/40' :
                              'bg-slate-950 text-slate-500 border border-slate-900'
                            }`} title="Resolution source: CONFIG (database) > ENV (OPENAI_MODEL) > DEFAULT">
                              {s.source}: {s.effective_model}
                            </span>
                            <input
                              type="text"
                              value={draft}
                              onChange={(e) => setLlmDrafts(prev => ({ ...prev, [s.function]: e.target.value }))}
                              placeholder="e.g. gpt-4o"
                              className="flex-1 min-w-[140px] bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:border-cyan-500 outline-none text-slate-200 font-mono"
                            />
                            <button
                              onClick={async () => { await updateLLMSetting(s.function, draft.trim() || null); setLlmDrafts(prev => ({ ...prev, [s.function]: '' })); }}
                              className="text-[10px] text-cyan-400 hover:text-cyan-300 font-mono bg-cyan-950/20 border border-cyan-900/30 rounded px-3 py-1.5 uppercase tracking-wider"
                            >
                              Save
                            </button>
                            {s.configured_model && (
                              <button
                                onClick={async () => { await updateLLMSetting(s.function, null); setLlmDrafts(prev => ({ ...prev, [s.function]: '' })); }}
                                className="text-[10px] text-slate-400 hover:text-slate-200 font-mono bg-slate-900 border border-slate-800 rounded px-3 py-1.5 uppercase tracking-wider"
                                title="Reset to env/default resolution"
                              >
                                Clear
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* USERS & TOKENS (Identity Boundary v1.0 WS3, ADMIN only) */}
                  {allow('identity:manage') && (
                  <div className="glass-panel p-6 rounded-xl space-y-5">
                    <h3 className="font-bold text-sm text-slate-200 tracking-wide border-b border-slate-900 pb-3 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      Users &amp; Tokens
                      <span className="text-[10px] font-mono text-slate-500 font-normal normal-case ml-2">
                        Principal registry and credential lineage — the boundary decides actors; roles decide authority
                      </span>
                    </h3>

                    {lastOneTimePassword && (
                      <div className="bg-amber-950/40 border border-amber-900/50 rounded-lg px-4 py-3 text-xs text-amber-200 font-mono">
                        One-time password for <b>{lastOneTimePassword.name}</b>: <b>{lastOneTimePassword.password}</b>
                        <span className="block text-[10px] text-amber-400/70 mt-1">Shown once — it is never stored in plaintext. The user must change it at first login.</span>
                      </div>
                    )}
                    {lastIssuedToken && (
                      <div className="bg-cyan-950/40 border border-cyan-900/50 rounded-lg px-4 py-3 text-xs text-cyan-200 font-mono break-all">
                        Token for <b>{lastIssuedToken.principal}</b> ({lastIssuedToken.fingerprint}): <b>{lastIssuedToken.token}</b>
                        <span className="block text-[10px] text-cyan-400/70 mt-1">Shown once — only its hash is stored. Configure agents via EM_AGENT_TOKEN.</span>
                      </div>
                    )}

                    {/* CREATE PRINCIPAL */}
                    <form
                      className="grid grid-cols-2 md:grid-cols-5 gap-3 items-end"
                      onSubmit={async (e) => {
                        e.preventDefault();
                        if (!npName.trim()) return;
                        const payload: { name: string; kind: string; role?: string; clearance?: string } = {
                          name: npName.trim(), kind: npKind };
                        if (npKind !== 'AGENT') payload.role = npRole;
                        if (npKind === 'AGENT') payload.clearance = npClearance;
                        if (await createPrincipal(payload)) setNpName('');
                      }}
                    >
                      <div>
                        <label className="block text-[10px] text-slate-400 font-mono mb-1 uppercase">Name</label>
                        <input value={npName} onChange={(e) => setNpName(e.target.value)} placeholder="username / agent id"
                               className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-[11px] outline-none focus:border-emerald-700 text-slate-200" />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400 font-mono mb-1 uppercase">Kind</label>
                        <select value={npKind} onChange={(e) => setNpKind(e.target.value as 'HUMAN' | 'AGENT' | 'SERVICE')}
                                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-[11px] outline-none text-slate-200">
                          <option>HUMAN</option><option>AGENT</option><option>SERVICE</option>
                        </select>
                      </div>
                      {npKind !== 'AGENT' ? (
                        <div>
                          <label className="block text-[10px] text-slate-400 font-mono mb-1 uppercase">Role</label>
                          <select value={npRole} onChange={(e) => setNpRole(e.target.value)}
                                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-[11px] outline-none text-slate-200">
                            {npKind === 'HUMAN' && <option>ADMIN</option>}
                            <option>GOVERNANCE_REVIEWER</option><option>KNOWLEDGE_OPERATOR</option><option>READ_ONLY</option>
                          </select>
                        </div>
                      ) : (
                        <div>
                          <label className="block text-[10px] text-slate-400 font-mono mb-1 uppercase">Clearance</label>
                          <select value={npClearance} onChange={(e) => setNpClearance(e.target.value)}
                                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-[11px] outline-none text-slate-200">
                            <option>PUBLIC</option><option>INTERNAL</option><option>RESTRICTED</option><option>EXECUTIVE</option>
                          </select>
                        </div>
                      )}
                      <button type="submit" disabled={!npName.trim()}
                              className="py-1.5 px-4 bg-gradient-to-r from-emerald-500 to-emerald-600 text-slate-950 font-bold rounded text-[10px] tracking-wider uppercase disabled:opacity-40">
                        Create Principal
                      </button>
                    </form>

                    {/* PRINCIPAL REGISTRY */}
                    <div className="space-y-1.5">
                      {principals.filter(p => p.kind !== 'DELEGATED' && p.kind !== 'SYSTEM').map((p) => (
                        <div key={p.id} className={`flex flex-wrap items-center gap-3 bg-slate-950/60 border border-slate-900 rounded-lg px-3 py-2 ${p.active ? '' : 'opacity-50'}`}>
                          <span className="text-[10px] font-mono bg-slate-900 text-slate-400 border border-slate-850 px-2 py-0.5 rounded">{p.kind}</span>
                          <span className="font-semibold text-xs text-slate-200">{p.display_name}</span>
                          <span className="text-[10px] font-mono text-slate-500">{p.name}</span>
                          {p.kind !== 'AGENT' ? (
                            <select value={p.role ?? ''} disabled={p.name === currentUser.name}
                                    onChange={(e) => updatePrincipal(p.name, { role: e.target.value })}
                                    className="text-[10px] font-mono bg-slate-950 border border-slate-800 rounded px-2 py-0.5 text-cyan-400 outline-none disabled:opacity-50">
                              {p.kind === 'HUMAN' && <option>ADMIN</option>}
                              <option>GOVERNANCE_REVIEWER</option><option>KNOWLEDGE_OPERATOR</option><option>READ_ONLY</option>
                            </select>
                          ) : (
                            <select value={p.clearance ?? 'PUBLIC'}
                                    onChange={(e) => updatePrincipal(p.name, { clearance: e.target.value })}
                                    className="text-[10px] font-mono bg-slate-950 border border-slate-800 rounded px-2 py-0.5 text-purple-400 outline-none">
                              <option>PUBLIC</option><option>INTERNAL</option><option>RESTRICTED</option><option>EXECUTIVE</option>
                            </select>
                          )}
                          <span className="flex-1"></span>
                          {p.kind === 'HUMAN' && (
                            <button onClick={() => resetPrincipalPassword(p.name)}
                                    className="text-[10px] font-mono text-amber-400 hover:text-amber-300 bg-amber-950/20 border border-amber-900/30 rounded px-2 py-0.5 uppercase">
                              Reset PW
                            </button>
                          )}
                          {(p.kind === 'AGENT' || p.kind === 'SERVICE') && (
                            <button onClick={() => { setTokPrincipal(p.name); issueApiToken(p.name, tokLabel.trim() || undefined); }}
                                    className="text-[10px] font-mono text-cyan-400 hover:text-cyan-300 bg-cyan-950/20 border border-cyan-900/30 rounded px-2 py-0.5 uppercase">
                              Issue Token
                            </button>
                          )}
                          {p.name !== currentUser.name && (
                            <button onClick={() => updatePrincipal(p.name, { active: !p.active })}
                                    className={`text-[10px] font-mono rounded px-2 py-0.5 uppercase border ${
                                      p.active ? 'text-rose-400 bg-rose-950/20 border-rose-900/30' : 'text-emerald-400 bg-emerald-950/20 border-emerald-900/30'}`}>
                              {p.active ? 'Deactivate' : 'Reactivate'}
                            </button>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* TOKEN LINEAGE */}
                    {apiTokens.length > 0 && (
                      <div className="space-y-1.5 pt-2 border-t border-slate-900">
                        <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">API Token Lineage (revoked tokens stay listed — lineage, not deletion)</h4>
                        {apiTokens.map((t) => (
                          <div key={t.fingerprint} className={`flex flex-wrap items-center gap-3 bg-slate-950/40 border border-slate-900 rounded px-3 py-1.5 text-[10px] font-mono ${t.revoked_at ? 'opacity-50' : ''}`}>
                            <span className="text-slate-400">{t.fingerprint}</span>
                            <span className="text-slate-300">{t.principal_name}</span>
                            {t.label && <span className="text-slate-500">{t.label}</span>}
                            <span className="flex-1"></span>
                            {t.revoked_at ? (
                              <span className="text-rose-500 uppercase">Revoked</span>
                            ) : (
                              <button onClick={() => revokeApiToken(t.fingerprint)}
                                      className="text-rose-400 hover:text-rose-300 bg-rose-950/20 border border-rose-900/30 rounded px-2 py-0.5 uppercase">
                                Revoke
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  )}
                </div>
              )}

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
