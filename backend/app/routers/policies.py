"""Policies routes (audit T2.4, relocated VERBATIM from app/main.py).

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


# Approval Policy routes (MVP 0.10.2): deterministic, versioned auto-approval
# rules. Policies are governed facts - create/update/toggle are audit events,
# and definition changes bump the version that ASSET_AUTO_APPROVED events
# reference. No delete: disable instead; audit history references the rule.
def _validated_policy_fields(db_session: Session, project_id: int, asset_types: List[str], connector_id: Optional[int]):
    types = [t.strip().upper() for t in (asset_types or []) if t.strip()]
    invalid = [t for t in types if t not in policy.ALLOWED_ASSET_TYPES]
    if not types or invalid:
        raise HTTPException(status_code=400,
                            detail=f"asset_types must be a non-empty subset of {sorted(policy.ALLOWED_ASSET_TYPES)}"
                                   + (f"; invalid: {invalid}" if invalid else ""))
    if connector_id is not None:
        connector = db_session.query(db.SourceConnector).filter(
            db.SourceConnector.id == connector_id, db.SourceConnector.project_id == project_id).first()
        if not connector:
            raise HTTPException(status_code=400, detail=f"Connector {connector_id} not found in project {project_id}")
    return types

@router.post("/api/projects/{project_id}/approval-policies", response_model=schemas.ApprovalPolicyResponse)
def create_approval_policy(project_id: int, policy_in: schemas.ApprovalPolicyCreate, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:approve"))):
    if not policy_in.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    types = _validated_policy_fields(db_session, project_id, policy_in.asset_types, policy_in.connector_id)
    try:
        conditions = policy.validate_source_conditions(policy_in.source_conditions)
        engine_conditions = tier2.validate_engine_conditions(policy_in.engine_conditions)
        domains = policy.validate_domains(policy_in.domains)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    pol = db.ApprovalPolicy(
        project_id=project_id,
        name=policy_in.name.strip(),
        asset_types_json=json.dumps(types),
        connector_id=policy_in.connector_id,
        enabled=True,
        version=1,
        source_conditions_json=json.dumps(conditions) if conditions else None,
        engine_conditions_json=json.dumps(engine_conditions) if engine_conditions else None,
        domains_json=json.dumps(domains) if domains else None,
        created_by=actor.display,
    )
    db_session.add(pol)
    db_session.commit()
    db_session.refresh(pol)
    identity.ensure_delegated_principal(db_session, f"policy:{pol.name}", created_by=actor.name)
    crud.log_audit_event(db_session, actor=actor.display, event_type="POLICY_CREATED",
                         target_id=str(pol.id),
                         details=json.dumps({"name": pol.name, "version": pol.version,
                                             "asset_types": types, "connector_id": pol.connector_id,
                                             "source_conditions": conditions,
                                             "engine_conditions": engine_conditions,
                                             "domains": domains}),
                         identity_fact_id=actor.fact(db_session).id)
    return pol

@router.get("/api/projects/{project_id}/approval-policies", response_model=List[schemas.ApprovalPolicyResponse])
def list_approval_policies(project_id: int, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:read"))):
    return db_session.query(db.ApprovalPolicy).filter(
        db.ApprovalPolicy.project_id == project_id).order_by(db.ApprovalPolicy.id).all()

@router.patch("/api/approval-policies/{policy_id}", response_model=schemas.ApprovalPolicyResponse)
def update_approval_policy(policy_id: int, update: schemas.ApprovalPolicyUpdate,
                           db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:approve"))):
    pol = db_session.query(db.ApprovalPolicy).filter(db.ApprovalPolicy.id == policy_id).first()
    if not pol:
        raise HTTPException(status_code=404, detail=f"Approval policy {policy_id} not found")
    data = update.dict(exclude_unset=True)

    # Definition changes (what the rule approves) bump the version so past
    # ASSET_AUTO_APPROVED events keep pointing at the rule text that fired.
    # The enabled flag is operational, not definitional - audited, no bump.
    definition_changed = False
    if ("asset_types" in data or "connector_id" in data or "name" in data
            or "source_conditions" in data or "engine_conditions" in data
            or "domains" in data):
        new_types = _validated_policy_fields(
            db_session, pol.project_id,
            data.get("asset_types", pol.asset_types),
            data.get("connector_id", pol.connector_id))
        old_snapshot = {"name": pol.name, "asset_types": pol.asset_types,
                        "connector_id": pol.connector_id,
                        "source_conditions": pol.source_conditions,
                        "engine_conditions": pol.engine_conditions,
                        "domains": pol.domains,
                        "version": pol.version}
        if "name" in data and data["name"].strip():
            pol.name = data["name"].strip()
        pol.asset_types_json = json.dumps(new_types)
        if "connector_id" in data:
            pol.connector_id = data["connector_id"]
        # Tier conditions and domain coverage are definition, not
        # operation (D17/D26): editing what the rule requires bumps the
        # version so past events keep pointing at the rule that fired.
        try:
            if "source_conditions" in data:
                conditions = policy.validate_source_conditions(data["source_conditions"])
                pol.source_conditions_json = json.dumps(conditions) if conditions else None
            if "engine_conditions" in data:
                engine_conditions = tier2.validate_engine_conditions(data["engine_conditions"])
                pol.engine_conditions_json = json.dumps(engine_conditions) if engine_conditions else None
            if "domains" in data:
                domains = policy.validate_domains(data["domains"])
                pol.domains_json = json.dumps(domains) if domains else None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        pol.version += 1
        definition_changed = True

    toggled = None
    if "enabled" in data and bool(data["enabled"]) != bool(pol.enabled):
        pol.enabled = bool(data["enabled"])
        toggled = pol.enabled

    pol.updated_at = datetime.datetime.utcnow()
    db_session.commit()
    db_session.refresh(pol)

    if definition_changed:
        identity.ensure_delegated_principal(db_session, f"policy:{pol.name}", created_by=actor.name)
        crud.log_audit_event(db_session, actor=actor.display, event_type="POLICY_UPDATED",
                             target_id=str(pol.id),
                             details=json.dumps({"old": old_snapshot,
                                                 "new": {"name": pol.name, "asset_types": pol.asset_types,
                                                         "connector_id": pol.connector_id,
                                                         "source_conditions": pol.source_conditions,
                                                         "engine_conditions": pol.engine_conditions,
                                                         "domains": pol.domains,
                                                         "version": pol.version}}),
                             identity_fact_id=actor.fact(db_session).id)
    if toggled is not None:
        crud.log_audit_event(db_session, actor=actor.display,
                             event_type="POLICY_ENABLED" if toggled else "POLICY_DISABLED",
                             target_id=str(pol.id),
                             details=json.dumps({"name": pol.name, "version": pol.version}),
                             identity_fact_id=actor.fact(db_session).id)
    return pol

# Classification Policy routes (v1.2.1 WS1, D27): the ApprovalPolicy
# governed shape mirrored for the other outcome species - deterministic,
# versioned rules assigning the governed domain path at ingestion. Same
# D17 discipline: definition changes bump the version ASSET_CLASSIFIED
# events reference; enable/disable is audited without a bump; no delete.
# Administration rides under assets:approve (the scoping ruling: no new
# permission - the same permission that governs approval policies).
def _validated_classification_fields(db_session: Session, project_id: int, rules, connector_id: Optional[int]):
    try:
        validated = classification.validate_rules(rules)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if connector_id is not None:
        connector = db_session.query(db.SourceConnector).filter(
            db.SourceConnector.id == connector_id, db.SourceConnector.project_id == project_id).first()
        if not connector:
            raise HTTPException(status_code=400, detail=f"Connector {connector_id} not found in project {project_id}")
    return validated

@router.post("/api/projects/{project_id}/classification-policies", response_model=schemas.ClassificationPolicyResponse)
def create_classification_policy(project_id: int, policy_in: schemas.ClassificationPolicyCreate,
                                 db_session: Session = Depends(get_db),
                                 actor: identity.Actor = Depends(require_perm("assets:approve"))):
    if not policy_in.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    rules = _validated_classification_fields(db_session, project_id, policy_in.rules, policy_in.connector_id)
    pol = db.ClassificationPolicy(
        project_id=project_id,
        name=policy_in.name.strip(),
        rules_json=json.dumps(rules),
        connector_id=policy_in.connector_id,
        enabled=True,
        version=1,
        created_by=actor.display,
    )
    db_session.add(pol)
    db_session.commit()
    db_session.refresh(pol)
    identity.ensure_delegated_principal(db_session, f"classification:{pol.name}", created_by=actor.name)
    crud.log_audit_event(db_session, actor=actor.display, event_type="CLASSIFICATION_POLICY_CREATED",
                         target_id=str(pol.id),
                         details=json.dumps({"name": pol.name, "version": pol.version,
                                             "rules": rules, "connector_id": pol.connector_id}),
                         identity_fact_id=actor.fact(db_session).id)
    return pol

@router.get("/api/projects/{project_id}/classification-policies", response_model=List[schemas.ClassificationPolicyResponse])
def list_classification_policies(project_id: int, db_session: Session = Depends(get_db),
                                 actor: identity.Actor = Depends(require_perm("assets:read"))):
    return db_session.query(db.ClassificationPolicy).filter(
        db.ClassificationPolicy.project_id == project_id).order_by(db.ClassificationPolicy.id).all()

@router.patch("/api/classification-policies/{policy_id}", response_model=schemas.ClassificationPolicyResponse)
def update_classification_policy(policy_id: int, update: schemas.ClassificationPolicyUpdate,
                                 db_session: Session = Depends(get_db),
                                 actor: identity.Actor = Depends(require_perm("assets:approve"))):
    pol = db_session.query(db.ClassificationPolicy).filter(db.ClassificationPolicy.id == policy_id).first()
    if not pol:
        raise HTTPException(status_code=404, detail=f"Classification policy {policy_id} not found")
    data = update.dict(exclude_unset=True)

    definition_changed = False
    if "rules" in data or "connector_id" in data or "name" in data:
        new_rules = _validated_classification_fields(
            db_session, pol.project_id,
            data.get("rules", pol.rules),
            data.get("connector_id", pol.connector_id))
        old_snapshot = {"name": pol.name, "rules": pol.rules,
                        "connector_id": pol.connector_id, "version": pol.version}
        if "name" in data and data["name"].strip():
            pol.name = data["name"].strip()
        pol.rules_json = json.dumps(new_rules)
        if "connector_id" in data:
            pol.connector_id = data["connector_id"]
        pol.version += 1
        definition_changed = True

    toggled = None
    if "enabled" in data and bool(data["enabled"]) != bool(pol.enabled):
        pol.enabled = bool(data["enabled"])
        toggled = pol.enabled

    pol.updated_at = datetime.datetime.utcnow()
    db_session.commit()
    db_session.refresh(pol)

    if definition_changed:
        identity.ensure_delegated_principal(db_session, f"classification:{pol.name}", created_by=actor.name)
        crud.log_audit_event(db_session, actor=actor.display, event_type="CLASSIFICATION_POLICY_UPDATED",
                             target_id=str(pol.id),
                             details=json.dumps({"old": old_snapshot,
                                                 "new": {"name": pol.name, "rules": pol.rules,
                                                         "connector_id": pol.connector_id, "version": pol.version}}),
                             identity_fact_id=actor.fact(db_session).id)
    if toggled is not None:
        crud.log_audit_event(db_session, actor=actor.display,
                             event_type="CLASSIFICATION_POLICY_ENABLED" if toggled else "CLASSIFICATION_POLICY_DISABLED",
                             target_id=str(pol.id),
                             details=json.dumps({"name": pol.name, "version": pol.version}),
                             identity_fact_id=actor.fact(db_session).id)
    return pol

@router.post("/api/projects/{project_id}/taxonomy/reorganize")
def reorganize_taxonomy(project_id: int, request: schemas.TaxonomyReorganizeRequest,
                        db_session: Session = Depends(get_db),
                        actor: identity.Actor = Depends(require_perm("assets:approve"))):
    """The explicit audited taxonomy operation (D27): rename (prefix
    rewrite - nesting survives by construction) or reclassify (re-run
    current policies over a domain subtree - the policy-driven split).
    Writes ONLY the domain column; ONE TAXONOMY_REORGANIZED event carries
    the reason and the complete old->new mapping."""
    try:
        return classification.reorganize_taxonomy(
            db_session, project_id, request.operations, request.reason, actor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
