import os
import shutil
import hashlib
import json
import uuid
import datetime
from fastapi import FastAPI, Depends, Header, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from app import logging_config

# T2.1 (audit H-OPS-1): operational logging configured before anything can
# emit. The audit ledger stays the governed record; logs are runtime
# visibility only - never substitute one for the other.
logging_config.configure_logging()
logger = logging_config.get_logger(__name__)

from app import database as db
from app import schemas
from app import crud
from app import identity
from app import ingestion
from app import extraction
from app import query_engine
from app import evaluation
from app import conflict_engine
from app import revisions
from app import trust
from app import governance_inbox
from app import consumption_inbox
from app import operations_view
from app import binding_lineage
from app import connectors
from app import policy
from app import classification
from app import tier2
from app import llm
from app import custody
from app.projections import engine as projection_engine

# Initialize FastAPI app
app = FastAPI(title="ExpertMachina MVP Backend", version="0.1.0")

# CORS: explicit local frontend origins only (audit hardening). The API has
# no identity layer until v1.x (D14) - a wildcard here let any webpage the
# operator visits call state-mutating endpoints from their browser. Override
# for other deployments via EM_CORS_ORIGINS (comma-separated).
_cors_origins = [o.strip() for o in os.environ.get(
    "EM_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]
if "*" in _cors_origins:
    # Audit QW-3 (docs/audit-2026-07-07.md, M-SEC-3): a wildcard origin
    # combined with allow_credentials lets any webpage the operator visits
    # drive state-mutating endpoints with the victim's credentials. Refuse
    # loudly at import - a misconfigured boundary must never come up quiet.
    raise RuntimeError(
        "EM_CORS_ORIGINS must not contain '*': the API allows credentials, and a "
        "wildcard origin would let any webpage call it as the operator. List the "
        "frontend origins explicitly (comma-separated).")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# T2.1: request correlation. Every log line emitted while serving a request
# carries a short random id, so concurrent requests' operational logs are
# attributable. Observability only - identity facts and audit events remain
# the governed record of WHO did WHAT.
@app.middleware("http")
async def request_context_middleware(request, call_next):
    token = logging_config.request_id_var.set(uuid.uuid4().hex[:12])
    try:
        return await call_next(request)
    finally:
        logging_config.request_id_var.reset(token)

# Upload directory
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# DB dependency


@app.on_event("startup")
def startup_event():
    db.init_db()
    with db.SessionLocal() as session:
        # Create default customer
        crud.get_or_create_default_customer(session)
        # Identity Boundary bootstrap: platform principals, the one-time
        # admin, and DELEGATED registrations for pre-boundary governed
        # objects (their historical audit rows stay legacy - D12).
        identity.ensure_system_principals(session)
        admin, one_time_password = identity.bootstrap_admin(session)
        if one_time_password:
            # DELIBERATELY print(), never the logging layer (T2.1 ruling):
            # "shown once, never logged" is this credential's contract - it
            # must reach the operator's console exactly once and must never
            # land in any routed/collected log stream.
            # flush=True: under uvicorn, stdout is block-buffered - without
            # an explicit flush the one-time credential can sit invisible in
            # the buffer, which operationally means a locked-out admin.
            print("=" * 64, flush=True)
            print("IDENTITY BOUNDARY BOOTSTRAP - one-time admin credential", flush=True)
            print("  username: admin", flush=True)
            print(f"  password: {one_time_password}", flush=True)
            print("  Shown once, never stored in plaintext. Change it after login.", flush=True)
            print("=" * 64, flush=True)
        for pol in session.query(db.ApprovalPolicy).all():
            identity.ensure_delegated_principal(session, f"policy:{pol.name}")
        for conn in session.query(db.SourceConnector).all():
            identity.ensure_delegated_principal(session, f"connector:{conn.name}")
        # WS3: pre-matrix role names migrate in the mutable registry only;
        # historical role_snapshots keep what was true at action time.
        identity.migrate_legacy_roles(session)
        # WS4 hardening: the boundary validates its own data at startup.
        # Report-only (authorization fails closed regardless), but LOUD.
        findings = identity.validate_boundary(session)
        for finding in findings:
            logger.warning("BOUNDARY VALIDATION: %s", finding)


# --- T2.4 router split: shared deps relocated to app/deps.py ---
from app.deps import get_db, require_actor, require_perm, _authorize_or_403  # noqa: E402,F401

# Include the domain routers (pure relocation of the former inline routes).
from app.routers import (  # noqa: E402
    system,
    identity_admin,
    projects,
    sources,
    policies,
    projections,
    settings,
    assets,
    experts,
    packages,
    evaluations,
    insights,
)
app.include_router(system.router)
app.include_router(identity_admin.router)
app.include_router(projects.router)
app.include_router(sources.router)
app.include_router(policies.router)
app.include_router(projections.router)
app.include_router(settings.router)
app.include_router(assets.router)
app.include_router(experts.router)
app.include_router(packages.router)
app.include_router(evaluations.router)
app.include_router(insights.router)

# Backward-compatible surface: suites import handlers from app.main.
from app.routers.system import (  # noqa: E402,F401
    auth_change_password,
    auth_login,
    auth_logout,
    auth_me,
    health_check,
)
from app.routers.identity_admin import (  # noqa: E402,F401
    create_identity_principal,
    issue_identity_token,
    list_identity_tokens,
    list_principals,
    reset_principal_password,
    revoke_identity_token,
    update_identity_principal,
)
from app.routers.projects import (  # noqa: E402,F401
    create_project,
    get_documents,
    get_projects,
    upload_batch_demo,
    upload_document,
)
from app.routers.sources import (  # noqa: E402,F401
    create_external_credential,
    create_source_connector,
    get_external_credential_detail,
    get_ingestion_job,
    list_external_credentials,
    list_ingestion_job_files,
    list_ingestion_jobs,
    list_source_connectors,
    revoke_external_credential,
    rotate_external_credential,
    rotate_master_key,
    scan_source_connector,
)
from app.routers.policies import (  # noqa: E402,F401
    _validated_classification_fields,
    _validated_policy_fields,
    create_approval_policy,
    create_classification_policy,
    list_approval_policies,
    list_classification_policies,
    reorganize_taxonomy,
    update_approval_policy,
    update_classification_policy,
)
from app.routers.projections import (  # noqa: E402,F401
    list_projection_renderers,
    list_projections,
    render_projection,
)
from app.routers.settings import (  # noqa: E402,F401
    list_llm_settings,
    update_llm_setting,
)
from app.routers.assets import (  # noqa: E402,F401
    _asset_transition_permission,
    bulk_update_assets,
    create_asset_revision,
    delete_asset,
    delete_document_assets,
    extract_assets,
    get_asset_revisions,
    get_assets,
    get_project_revision_queue,
    review_asset_revision,
    update_asset,
)
from app.routers.experts import (  # noqa: E402,F401
    _annotated_relationship,
    create_expert,
    execute_query,
    get_compile_gate,
    get_expert_model_conflict_score,
    get_expert_model_conflicts,
    get_expert_model_trust_score,
    get_experts,
    get_project_trust_scores,
    review_conflict,
    run_conflict_scan,
)
from app.routers.packages import (  # noqa: E402,F401
    create_expert_agent_binding,
    create_package,
    download_agent_package,
    get_binding_lineage,
    get_expert_agent_binding,
    get_package_model_comparison,
    get_package_model_selection,
    get_packages,
    list_expert_agent_bindings,
    put_package_model_selection,
)
from app.routers.evaluations import (  # noqa: E402,F401
    create_benchmark,
    delete_benchmark,
    get_benchmarks,
    get_evaluation,
    get_expert_coverage_trend,
    get_run_claim_verdicts,
    list_evaluations,
    review_claim_verdict,
    trigger_evaluation,
    update_benchmark,
)
from app.routers.insights import (  # noqa: E402,F401
    get_agent_activity,
    get_audit_trail,
    get_consumption_inbox,
    get_dashboard_summary,
    get_governance_inbox,
    get_operations_view,
)
