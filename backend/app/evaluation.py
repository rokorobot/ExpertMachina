import json
import datetime
from sqlalchemy.orm import Session
from app import database as db
from app import schemas
from app import query_engine

def create_evaluation_run(session: Session, run_in: schemas.EvaluationRunCreate) -> db.EvaluationRun:
    # 1. Fetch expert model
    expert_model = session.query(db.ExpertModel).filter(db.ExpertModel.id == run_in.expert_model_id).first()
    if not expert_model:
        raise ValueError(f"Expert Model with ID {run_in.expert_model_id} not found")

    # 2. Get active approved assets for the expert model
    approved_assets = []
    if expert_model.asset_ids_json:
        try:
            asset_ids = json.loads(expert_model.asset_ids_json)
            approved_assets = session.query(db.KnowledgeAsset).filter(
                db.KnowledgeAsset.id.in_(asset_ids),
                db.KnowledgeAsset.status == "APPROVED"
            ).all()
        except Exception:
            pass

    asset_ids_snapshot = [a.id for a in approved_assets]
    asset_hashes_snapshot = {str(a.id): a.source_hash for a in approved_assets if a.source_hash}

    # 3. Get all benchmark questions for the project
    benchmarks = session.query(db.BenchmarkQuestion).filter(
        db.BenchmarkQuestion.project_id == run_in.project_id
    ).all()
    
    benchmark_question_ids = [b.id for b in benchmarks]

    # Create EvaluationRun
    db_run = db.EvaluationRun(
        project_id=run_in.project_id,
        expert_model_id=run_in.expert_model_id,
        expert_model_version=run_in.expert_model_version,
        asset_ids_snapshot=json.dumps(asset_ids_snapshot),
        asset_hashes_snapshot=json.dumps(asset_hashes_snapshot),
        benchmark_question_ids_snapshot=json.dumps(benchmark_question_ids),
        status="PENDING",
        started_at=datetime.datetime.utcnow()
    )
    session.add(db_run)
    session.commit()
    session.refresh(db_run)
    return db_run

def run_evaluation_batch(session: Session, run_id: int):
    db_run = session.query(db.EvaluationRun).filter(db.EvaluationRun.id == run_id).first()
    if not db_run:
        return
    
    db_run.status = "RUNNING"
    db_run.started_at = datetime.datetime.utcnow()
    session.commit()

    try:
        # Load snapshots
        asset_ids_snapshot = json.loads(db_run.asset_ids_snapshot)
        asset_hashes_snapshot = json.loads(db_run.asset_hashes_snapshot)
        benchmark_question_ids = json.loads(db_run.benchmark_question_ids_snapshot)

        benchmarks = session.query(db.BenchmarkQuestion).filter(
            db.BenchmarkQuestion.id.in_(benchmark_question_ids)
        ).all()

        total_questions = len(benchmarks)
        if total_questions == 0:
            db_run.status = "COMPLETED"
            db_run.completed_at = datetime.datetime.utcnow()
            session.commit()
            return

        passed_count = 0
        total_coverage = 0.0
        total_confidence = 0.0
        failed_question_ids = []

        for b in benchmarks:
            # 1. Retrieve approved evidence using the snapshot overrides
            retrieval_res = query_engine.retrieve_approved_evidence(
                session,
                expert_model_id=db_run.expert_model_id,
                question=b.question,
                asset_ids_override=asset_ids_snapshot,
                asset_hashes_override=asset_hashes_snapshot,
                # Evaluation batches are operator-initiated and must exercise
                # the full snapshot regardless of asset access tiers.
                caller_access_level="EXECUTIVE"
            )

            citations = retrieval_res["citations"]
            
            # 2. Answer Generation
            gen_result = query_engine.generate_evidence_answer(
                session,
                expert_model_id=db_run.expert_model_id,
                question=b.question,
                validated_citations=citations
            )

            # 3. Answer Verification
            verification = query_engine.verify_answer_claims(
                session,
                answer_text=gen_result["answer"],
                validated_citations=citations
            )

            coverage_score = verification["coverage_score"]
            verification_status = verification["verification_status"]
            conf_score = 0.95 if coverage_score >= 0.95 else 0.85 if coverage_score >= 0.80 else 0.40

            final_answer = gen_result["answer"]
            if verification_status == "INSUFFICIENT_EVIDENCE":
                final_answer = "INSUFFICIENT EVIDENCE"

            # Determine pass/fail based on user metrics rules
            passed = False
            if verification_status == "INSUFFICIENT_EVIDENCE" or final_answer == "INSUFFICIENT EVIDENCE":
                if b.expected_answer_type == "REFUSAL":
                    passed = True
                else:
                    passed = False
            else:
                if b.expected_answer_type == "REFUSAL":
                    passed = False
                else:
                    # Expecting factual, policy, or procedural.
                    # Must meet min required coverage score and citation count thresholds
                    meets_coverage = (coverage_score >= b.min_required_coverage)
                    meets_citations = (len(citations) >= (b.required_citation_count or 0))
                    passed = meets_coverage and meets_citations

            if passed:
                passed_count += 1
            else:
                failed_question_ids.append(b.id)

            total_coverage += coverage_score
            total_confidence += conf_score

            # Save detailed question result
            db_res = db.EvaluationQuestionResult(
                evaluation_run_id=db_run.id,
                benchmark_question_id=b.id,
                question_text=b.question,
                generated_answer=final_answer,
                coverage_score=coverage_score,
                confidence_score=conf_score,
                verification_status=verification_status,
                passed=passed,
                unsupported_claims_json=json.dumps(verification["unsupported_claims"]),
                citations_json=json.dumps(citations)
            )
            session.add(db_res)
            session.flush()  # assign db_res.id so verdicts can link to it

            # Persist every claim verdict as an immutable evaluation artifact
            # (MVP 0.9.2). The verifier already computes these; stop
            # discarding them.
            verifier_snapshot = json.dumps(verification.get("verifier") or {})
            for mapping in verification.get("claim_mappings", []):
                session.add(db.ClaimVerdict(
                    project_id=db_run.project_id,
                    expert_model_id=db_run.expert_model_id,
                    evaluation_run_id=db_run.id,
                    question_result_id=db_res.id,
                    benchmark_question_id=b.id,
                    claim=mapping["claim"],
                    verdict=mapping["verdict"],
                    confidence=mapping.get("confidence"),
                    supporting_asset_ids_json=json.dumps(mapping.get("supporting_assets", [])),
                    contradicting_asset_ids_json=json.dumps(mapping.get("contradicting_assets", [])),
                    verifier_json=verifier_snapshot,
                    evaluator_type="AUTOMATED",
                    evaluator_id="verification_engine"
                ))

        # Update run stats
        db_run.average_coverage_score = round(total_coverage / total_questions, 2)
        db_run.average_confidence_score = round(total_confidence / total_questions, 2)
        db_run.pass_rate = round(passed_count / total_questions, 2)
        db_run.status = "COMPLETED"
        db_run.failed_question_ids_json = json.dumps(failed_question_ids)
        db_run.completed_at = datetime.datetime.utcnow()
        session.commit()

    except Exception as e:
        print(f"Evaluation Run {run_id} failed: {e}")
        db_run.status = "FAILED"
        db_run.completed_at = datetime.datetime.utcnow()
        session.commit()
