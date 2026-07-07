"""Settings routes (audit T2.4, relocated VERBATIM from app/main.py).

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


# LLM Provider Settings routes (MVP 0.12): governed model-per-function
# configuration. Stores model selection, never credentials (D14/D19
# candidate). Empty config preserves prior behavior:
# DB config missing -> OPENAI_MODEL env -> gpt-4o-mini default.
@router.get("/api/settings/llm", response_model=List[schemas.LLMFunctionSettingResponse])
def list_llm_settings(db_session: Session = Depends(get_db),
                      actor: identity.Actor = Depends(require_perm("settings:manage"))):
    out = []
    for function, description in llm.FUNCTIONS.items():
        row = db_session.query(db.LLMFunctionConfig).filter(
            db.LLMFunctionConfig.function == function).first()
        resolved = llm.resolve(function, db_session)
        out.append(schemas.LLMFunctionSettingResponse(
            function=function, description=description,
            provider=resolved["provider"],
            configured_model=row.model if row else None,
            effective_model=resolved["model"], source=resolved["source"]))
    return out

@router.put("/api/settings/llm/{function}", response_model=schemas.LLMFunctionSettingResponse)
def update_llm_setting(function: str, update: schemas.LLMFunctionSettingUpdate,
                       db_session: Session = Depends(get_db),
                       actor: identity.Actor = Depends(require_perm("settings:manage"))):
    function = function.upper()
    if function not in llm.FUNCTIONS:
        raise HTTPException(status_code=400,
                            detail=f"Unknown LLM function '{function}'. Known: {sorted(llm.FUNCTIONS)}")
    new_model = (update.model or "").strip() or None
    new_provider = (update.provider or "").strip().upper() or None
    if new_provider and new_provider not in llm.ADAPTERS:
        raise HTTPException(status_code=400,
                            detail=f"Unknown provider '{new_provider}'. Known: {sorted(llm.ADAPTERS)}")
    row = db_session.query(db.LLMFunctionConfig).filter(
        db.LLMFunctionConfig.function == function).first()
    old_model = row.model if row else None
    old_provider = (row.provider if row else None) or "OPENAI"
    if not row:
        row = db.LLMFunctionConfig(function=function, provider="OPENAI")
        db_session.add(row)
    row.model = new_model
    if new_provider:
        row.provider = new_provider
    row.updated_by = actor.display
    row.updated_at = datetime.datetime.utcnow()
    db_session.commit()
    crud.log_audit_event(
        db_session, actor=actor.display, event_type="LLM_CONFIG_UPDATED",
        target_id=function,
        details=json.dumps({"function": function, "old_model": old_model,
                            "new_model": new_model,
                            "old_provider": old_provider, "new_provider": row.provider,
                            "note": "model selection only - credentials never stored (env-based until v1.x)"}),
        identity_fact_id=actor.fact(db_session).id)
    resolved = llm.resolve(function, db_session)
    return schemas.LLMFunctionSettingResponse(
        function=function, description=llm.FUNCTIONS[function],
        provider=resolved["provider"], configured_model=new_model,
        effective_model=resolved["model"], source=resolved["source"])
