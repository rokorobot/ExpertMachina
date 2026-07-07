"""Projections routes (audit T2.4, relocated VERBATIM from app/main.py).

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


# Projection routes (v1.3 WS1, D28): a file render exports governed
# knowledge as a portable artifact - the .empkg act-class, so it rides
# assets:approve (scoping ruling 2). The history is a computed read
# projected from PROJECTION_RENDERED ledger events alone (D24), with a
# recompose-and-compare staleness verdict on the latest render per
# renderer. Responses are metadata-only summaries, never file contents.
# The engine is the only module that emits PROJECTION_* events or names
# the render directory - this route proposes; the engine decides.
@router.post("/api/projects/{project_id}/projections/render")
def render_projection(project_id: int, request: schemas.ProjectionRenderRequest,
                      db_session: Session = Depends(get_db),
                      actor: identity.Actor = Depends(require_perm("assets:approve"))):
    project = db_session.query(db.Project).filter(db.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return projection_engine.render(
            db_session, actor, project_id,
            renderer=request.renderer,
            clearance=request.clearance,
            status_inclusion=tuple(request.status_inclusion)
            if request.status_inclusion else projection_engine.DEFAULT_STATUS_INCLUSION,
            domain_prefix=request.domain_prefix)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/projects/{project_id}/projections")
def list_projections(project_id: int,
                     db_session: Session = Depends(get_db),
                     actor: identity.Actor = Depends(require_perm("assets:read"))):
    return projection_engine.render_history(db_session, project_id)

# v1.5 WS3 (D31/D8): the renderer registry, metadata only - name, the
# DECLARED content mode, and the output species. The top-level
# Projections area (earned by renderer plurality: graph + vault) builds
# its render controls from this instead of hardcoding backend truth.
@router.get("/api/projections/renderers")
def list_projection_renderers(actor: identity.Actor = Depends(require_perm("assets:read"))):
    return [{"name": name,
             "content_mode": spec.get("content_mode"),
             "output": spec.get("output"),
             "managed_folders": list(spec.get("managed_folders") or [])}
            for name, spec in sorted(projection_engine.RENDERERS.items())]
