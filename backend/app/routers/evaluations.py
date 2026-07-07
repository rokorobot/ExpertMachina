"""Evaluations routes (audit T2.4, relocated VERBATIM from app/main.py).

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


# Benchmark routes
@router.get("/api/projects/{project_id}/benchmarks", response_model=List[schemas.BenchmarkQuestionResponse])
def get_benchmarks(project_id: int, limit: int = 100, db_session: Session = Depends(get_db),
                   actor: identity.Actor = Depends(require_perm("assets:read"))):
    return crud.get_benchmark_questions(db_session, project_id, limit=limit)

@router.post("/api/projects/{project_id}/benchmarks", response_model=schemas.BenchmarkQuestionResponse)
def create_benchmark(project_id: int, q_in: schemas.BenchmarkQuestionCreate, db_session: Session = Depends(get_db),
                     actor: identity.Actor = Depends(require_perm("assets:review"))):
    if q_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    return crud.create_benchmark_question(db_session, q_in)

@router.put("/api/projects/{project_id}/benchmarks/{benchmark_id}", response_model=schemas.BenchmarkQuestionResponse)
def update_benchmark(project_id: int, benchmark_id: int, q_update: schemas.BenchmarkQuestionUpdate, db_session: Session = Depends(get_db),
                     actor: identity.Actor = Depends(require_perm("assets:review"))):
    q = crud.get_benchmark_question(db_session, benchmark_id)
    if not q or q.project_id != project_id:
        raise HTTPException(status_code=404, detail="Benchmark question not found")
    updated = crud.update_benchmark_question(db_session, benchmark_id, q_update)
    return updated

@router.delete("/api/projects/{project_id}/benchmarks/{benchmark_id}")
def delete_benchmark(project_id: int, benchmark_id: int, db_session: Session = Depends(get_db),
                     actor: identity.Actor = Depends(require_perm("assets:review"))):
    q = crud.get_benchmark_question(db_session, benchmark_id)
    if not q or q.project_id != project_id:
        raise HTTPException(status_code=404, detail="Benchmark question not found")
    deleted = crud.delete_benchmark_question(db_session, benchmark_id)
    return {"message": "Benchmark question deleted successfully"}

# Evaluation runs routes
@router.post("/api/projects/{project_id}/evaluations", response_model=schemas.EvaluationRunResponse)
def trigger_evaluation(
    project_id: int,
    run_in: schemas.EvaluationRunCreate,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db),
    actor: identity.Actor = Depends(require_perm("assets:review"))
):
    if run_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    
    try:
        db_run = evaluation.create_evaluation_run(db_session, run_in)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # v1.1 WS2 channel rules: LIVE refuses package coordinates,
        # PACKAGE requires them - violations are bad requests, not 404s.
        raise HTTPException(status_code=400, detail=str(e))

    # Trigger execution in the background
    background_tasks.add_task(evaluation.run_evaluation_batch, db_session, db_run.id)
    return db_run

@router.get("/api/projects/{project_id}/evaluations", response_model=List[schemas.EvaluationRunResponse])
def list_evaluations(project_id: int, db_session: Session = Depends(get_db),
                     actor: identity.Actor = Depends(require_perm("assets:read"))):
    return db_session.query(db.EvaluationRun).filter(db.EvaluationRun.project_id == project_id).order_by(db.EvaluationRun.started_at.desc()).all()

@router.get("/api/projects/{project_id}/evaluations/{run_id}", response_model=schemas.EvaluationRunResponse)
def get_evaluation(project_id: int, run_id: int, db_session: Session = Depends(get_db),
                   actor: identity.Actor = Depends(require_perm("assets:read"))):
    run = db_session.query(db.EvaluationRun).filter(db.EvaluationRun.id == run_id, db.EvaluationRun.project_id == project_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return run

# Persisted Verification Verdicts (MVP 0.9.2). A verdict is an immutable
# measurement: reviewing one records a VERIFICATION_REVIEWED audit event and
# never mutates the ClaimVerdict row. Remediation happens on the asset or
# revision; the next evaluation run produces fresh verdicts.
# Answer Coverage Governance (MVP 0.9.3): trend over persisted run facts.
@router.get("/api/experts/{expert_model_id}/coverage-trend")
def get_expert_coverage_trend(expert_model_id: int, db_session: Session = Depends(get_db),
                              actor: identity.Actor = Depends(require_perm("assets:read"))):
    model = db_session.query(db.ExpertModel).filter(db.ExpertModel.id == expert_model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Expert Model {expert_model_id} not found")
    return evaluation.coverage_trend(db_session, expert_model_id)

@router.get("/api/evaluations/{run_id}/verdicts", response_model=List[schemas.ClaimVerdictResponse])
def get_run_claim_verdicts(run_id: int, verdict: Optional[str] = None, db_session: Session = Depends(get_db),
                           actor: identity.Actor = Depends(require_perm("assets:read"))):
    query = db_session.query(db.ClaimVerdict).filter(db.ClaimVerdict.evaluation_run_id == run_id)
    if verdict:
        query = query.filter(db.ClaimVerdict.verdict == verdict)
    return query.order_by(db.ClaimVerdict.id).all()

@router.post("/api/claim-verdicts/{verdict_id}/review")
def review_claim_verdict(verdict_id: int, review: schemas.VerificationReviewCreate, db_session: Session = Depends(get_db),
                         actor: identity.Actor = Depends(require_perm("assets:review"))):
    v = db_session.query(db.ClaimVerdict).filter(db.ClaimVerdict.id == verdict_id).first()
    if not v:
        raise HTTPException(status_code=404, detail=f"Claim verdict {verdict_id} not found")
    crud.log_audit_event(
        db_session,
        actor=actor.display,
        identity_fact_id=actor.fact(db_session).id,
        event_type="VERIFICATION_REVIEWED",
        target_id=str(v.id),
        details=json.dumps({
            "claim_verdict_id": v.id,
            "claim": v.claim,
            "verdict_seen": v.verdict,
            "confidence_seen": v.confidence,
            "expert_model_id": v.expert_model_id,
            "evaluation_run_id": v.evaluation_run_id,
            "question_result_id": v.question_result_id,
            "comment": review.comment
        })
    )
    return {"claim_verdict_id": v.id, "reviewed_by": actor.display, "event_type": "VERIFICATION_REVIEWED"}
