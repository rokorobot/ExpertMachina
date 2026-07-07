"""Packages routes (audit T2.4, relocated VERBATIM from app/main.py).

Pure relocation: no endpoint semantics, paths, status codes, response
models, dependency behavior, or audit events changed. Proven by
test_route_manifest.py (byte-identical route contract).
"""
import os
import shutil
import hashlib
import json
import uuid
import datetime
from fastapi import APIRouter, Depends, Header, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app import logging_config
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
from app.deps import get_db, require_actor, require_perm, _authorize_or_403

logger = logging_config.get_logger(__name__)
UPLOAD_DIR = "./uploads"

router = APIRouter()


# Agent Packages routes
@router.get("/api/projects/{project_id}/packages", response_model=List[schemas.AgentPackageResponse])
def get_packages(project_id: int, db_session: Session = Depends(get_db),
                 actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.get_agent_packages(db_session, project_id)

@router.post("/api/projects/{project_id}/packages", response_model=schemas.AgentPackageResponse)
def create_package(project_id: int, pkg_in: schemas.AgentPackageCreate, db_session: Session = Depends(get_db),
                   actor: identity.Actor = Depends(require_perm("assets:approve"))):
    if pkg_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    try:
        pkg = crud.create_agent_package(db_session, pkg_in, actor=actor)
    except ValueError as e:
        # Governance gate block: 409 Conflict, with the reason for the operator.
        raise HTTPException(status_code=409, detail=str(e))
    if not pkg:
        raise HTTPException(status_code=404, detail="Expert model not found")
    return pkg

# Agent Package Builder (MVP 0.9.4): download the compiled .empkg artifact.
@router.get("/api/packages/{package_id}/download")
def download_agent_package(package_id: int, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:read"))):
    from fastapi.responses import FileResponse
    pkg = db_session.query(db.AgentPackage).filter(db.AgentPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    if not pkg.file_path or not os.path.exists(pkg.file_path):
        raise HTTPException(status_code=404, detail="Package artifact not found on disk (compiled before MVP 0.9.4 or file removed)")
    return FileResponse(pkg.file_path, media_type="application/zip",
                        filename=os.path.basename(pkg.file_path))

@router.get("/api/packages/{package_id}/model-comparison")
def get_package_model_comparison(package_id: int, db_session: Session = Depends(get_db),
                                 actor: identity.Actor = Depends(require_perm("assets:read"))):
    # v1.1 WS2: computed comparison over COMPLETED PACKAGE runs (D1 - no
    # leaderboard table). Unrun models are absent, not zero (D12). This
    # endpoint compares; selection is WS3, a governed decision.
    try:
        return evaluation.package_model_comparison(db_session, package_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/packages/{package_id}/model-selection", response_model=schemas.PackageModelSelectionResponse)
def get_package_model_selection(package_id: int, db_session: Session = Depends(get_db),
                                actor: identity.Actor = Depends(require_perm("assets:read"))):
    selection = crud.get_package_model_selection(db_session, package_id)
    if not selection:
        raise HTTPException(status_code=404, detail="No model selected for this package yet")
    return selection

@router.put("/api/packages/{package_id}/model-selection", response_model=schemas.PackageModelSelectionResponse)
def put_package_model_selection(package_id: int, update: schemas.PackageModelSelectionUpdate,
                                db_session: Session = Depends(get_db),
                                actor: identity.Actor = Depends(require_perm("assets:approve"))):
    # v1.1 WS3: selecting a model for a package is a governed decision at
    # the approval tier (the tier that compiled the package). The boundary
    # validates the supporting PACKAGE-run evidence; every change is a
    # PACKAGE_MODEL_SELECTED audit event carrying the actor's identity fact.
    try:
        return crud.set_package_model_selection(db_session, package_id, update, actor=actor)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/packages/{package_id}/bindings", response_model=List[schemas.ExpertAgentBindingResponse])
def list_expert_agent_bindings(package_id: int, db_session: Session = Depends(get_db),
                               actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.list_expert_agent_bindings(db_session, package_id)

@router.post("/api/packages/{package_id}/bindings", response_model=schemas.ExpertAgentBindingResponse)
def create_expert_agent_binding(package_id: int, create: schemas.ExpertAgentBindingCreate,
                                db_session: Session = Depends(get_db),
                                actor: identity.Actor = Depends(require_perm("assets:approve"))):
    # v1.1 WS4 (D22): issue a governed binding of the package's CURRENT
    # selected model to an existing active AGENT principal. The binding is
    # an append-only snapshot - it executes nothing, mints no tokens
    # (token issuance stays in Users & Tokens, a governed identity
    # operation), and orchestrates nothing.
    try:
        return crud.create_expert_agent_binding(db_session, package_id, create, actor=actor)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# v1.1.x WS3: binding-centric reads - the two ratified projection
# endpoints. A binding becomes addressable on its own (not only as a list
# under its package), and its full lineage is composed SERVER-SIDE: the
# chain is a product claim, testable as one artifact. Every expected hop
# resolves or is declared missing (D12) - no silent gaps. The scoped
# provenance events ride with the lineage at assets:read per the WS3 gate
# (READ_ONLY can view lineage); the full ledger stays at audit:read.
@router.get("/api/bindings/{binding_id}", response_model=schemas.ExpertAgentBindingResponse)
def get_expert_agent_binding(binding_id: int, db_session: Session = Depends(get_db),
                             actor: identity.Actor = Depends(require_perm("assets:read"))):
    binding = db_session.query(db.ExpertAgentBinding).filter(
        db.ExpertAgentBinding.id == binding_id).first()
    if not binding:
        raise HTTPException(status_code=404, detail=f"Binding {binding_id} not found")
    return binding

@router.get("/api/bindings/{binding_id}/lineage")
def get_binding_lineage(binding_id: int, db_session: Session = Depends(get_db),
                        actor: identity.Actor = Depends(require_perm("assets:read"))):
    try:
        return binding_lineage.build_lineage(db_session, binding_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
