import os
import json
import datetime
from sqlalchemy.orm import Session
from app import database as db
from app import schemas
from app import query_engine
from app import package_consumer
from app import llm

# Evaluation (MVP 0.4 onward). v1.1 WS2: evaluation is ONE concept; the
# channel is a property of the run, never a sibling code path or table.
#
#   LIVE    - the governed channel: query_engine retrieval over the DB
#             asset snapshot (the pre-WS2 behavior, unchanged).
#   PACKAGE - the portable channel: every answer comes from
#             package_consumer.consume() over a verified .empkg. No live
#             database retrieval; the package IS the knowledge universe.
#             That is what makes "this Expert Package version performs
#             best on this model" an honest, reproducible claim.
#
# In BOTH channels the referee is the same verification engine (NLI /
# deterministic fallbacks) - independent of every model under test. The
# consumer model under test on a PACKAGE run is resolved through D19
# config at creation (callers propose nothing) and the run FAILS rather
# than mislabels if the resolution drifts before execution (D12).


def create_evaluation_run(session: Session, run_in: schemas.EvaluationRunCreate) -> db.EvaluationRun:
    run_type = (run_in.run_type or "LIVE").upper()
    if run_type not in ("LIVE", "PACKAGE"):
        raise ValueError(f"Unknown run_type '{run_in.run_type}'. Known: LIVE, PACKAGE")

    expert_model = session.query(db.ExpertModel).filter(db.ExpertModel.id == run_in.expert_model_id).first()
    if not expert_model:
        raise LookupError(f"Expert Model with ID {run_in.expert_model_id} not found")

    package_fields = {}
    if run_type == "LIVE":
        if run_in.agent_package_id is not None:
            raise ValueError("LIVE runs take no package coordinates - the channels are never blurred (D10)")
        # The knowledge universe of a LIVE run: approved DB assets.
        # Audit QW-5 (docs/audit-2026-07-07.md, M-CQ-1): a malformed
        # asset_ids_json used to be swallowed silently, quietly giving the
        # run an EMPTY knowledge universe - the evaluation basis corrupted
        # with no trace. Refusal-first: a run whose basis cannot be read
        # is refused (400 at the route), never launched hollow.
        approved_assets = []
        if expert_model.asset_ids_json:
            try:
                asset_ids = json.loads(expert_model.asset_ids_json)
            except Exception as e:
                raise ValueError(
                    f"Expert Model {expert_model.id} has unreadable asset_ids_json "
                    f"({e}); refusing to launch a LIVE run over an empty knowledge "
                    "universe. Repair the expert model first.")
            approved_assets = session.query(db.KnowledgeAsset).filter(
                db.KnowledgeAsset.id.in_(asset_ids),
                db.KnowledgeAsset.status == "APPROVED"
            ).all()
        asset_ids_snapshot = [a.id for a in approved_assets]
        asset_hashes_snapshot = {str(a.id): a.source_hash for a in approved_assets if a.source_hash}
    else:
        if not run_in.agent_package_id:
            raise ValueError("PACKAGE runs require agent_package_id - the package is the unit under test")
        pkg = session.query(db.AgentPackage).filter(
            db.AgentPackage.id == run_in.agent_package_id).first()
        if not pkg:
            raise LookupError(f"Agent Package with ID {run_in.agent_package_id} not found")
        if pkg.expert_model_id != run_in.expert_model_id:
            raise ValueError(
                f"Agent Package {pkg.id} was compiled from Expert Model {pkg.expert_model_id}, "
                f"not {run_in.expert_model_id}")
        if not pkg.file_path or not os.path.exists(pkg.file_path):
            raise ValueError(f"Agent Package {pkg.id} has no .empkg artifact on disk")
        # Verify the hash chain at creation - a run is never scheduled
        # against an artifact that already fails verification.
        loaded = package_consumer.load_package(pkg.file_path)
        if loaded["package_hash"] != pkg.package_hash:
            raise ValueError(
                f"Package artifact hash {loaded['package_hash'][:16]}... does not match the "
                f"recorded package hash {(pkg.package_hash or '')[:16]}... - refusing to evaluate")
        # The consumer model under test: D19 resolution, recorded as run
        # coordinates. Callers do not propose a model; config decides.
        resolved = llm.resolve("PACKAGE_CONSUMER", session)
        package_fields = {
            "run_type": "PACKAGE",
            "package_version": pkg.governance_version,
            "package_hash": pkg.package_hash,
            "consumer_model_provider": resolved["provider"],
            "consumer_model_name": resolved["model"],
        }
        # The knowledge universe of a PACKAGE run: the packaged assets.
        asset_ids_snapshot = [k["asset_id"] for k in loaded["knowledge"]]
        asset_hashes_snapshot = {
            str(k["asset_id"]): (k.get("provenance") or {}).get("source_hash")
            for k in loaded["knowledge"]
            if (k.get("provenance") or {}).get("source_hash")
        }

    benchmarks = session.query(db.BenchmarkQuestion).filter(
        db.BenchmarkQuestion.project_id == run_in.project_id
    ).all()
    benchmark_question_ids = [b.id for b in benchmarks]

    db_run = db.EvaluationRun(
        project_id=run_in.project_id,
        expert_model_id=run_in.expert_model_id,
        expert_model_version=run_in.expert_model_version,
        asset_ids_snapshot=json.dumps(asset_ids_snapshot),
        asset_hashes_snapshot=json.dumps(asset_hashes_snapshot),
        benchmark_question_ids_snapshot=json.dumps(benchmark_question_ids),
        status="PENDING",
        started_at=datetime.datetime.utcnow(),
        **package_fields
    )
    session.add(db_run)
    session.commit()
    session.refresh(db_run)
    return db_run

def coverage_trend(session: Session, expert_model_id: int) -> dict:
    """Answer Coverage Governance (MVP 0.9.3): coverage and verdict-mix
    trend over COMPLETED evaluation runs, oldest first. Pure read over
    persisted run facts and claim verdicts - no new state. Runs that
    predate verdict persistence (v0.9.2) report verdict metrics as
    unmeasured (None), never fabricated zeros. LIVE channel only - the
    trend tracks the governed knowledge base; PACKAGE runs measure a
    frozen artifact and live in package_model_comparison instead."""
    runs = session.query(db.EvaluationRun).filter(
        db.EvaluationRun.expert_model_id == expert_model_id,
        db.EvaluationRun.status == "COMPLETED",
        db.EvaluationRun.run_type != "PACKAGE"
    ).order_by(db.EvaluationRun.id.asc()).all()

    points = []
    for run in runs:
        verdicts = session.query(db.ClaimVerdict).filter(
            db.ClaimVerdict.evaluation_run_id == run.id
        ).all()
        counts = {"ENTAILED": 0, "CONTRADICTED": 0, "UNSUPPORTED": 0}
        for v in verdicts:
            if v.verdict in counts:
                counts[v.verdict] += 1
        total = sum(counts.values())
        points.append({
            "run_id": run.id,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "pass_rate": run.pass_rate,
            "average_coverage_score": run.average_coverage_score,
            "claims_total": total if total else None,
            "verdict_counts": counts if total else None,
            "supported_pct": round(counts["ENTAILED"] / total * 100, 1) if total else None,
        })
    return {"expert_model_id": expert_model_id, "runs": points}


def package_model_comparison(session: Session, agent_package_id: int) -> dict:
    """v1.1 WS2: computed comparison of COMPLETED PACKAGE runs for one
    package artifact, grouped by consumer model. A pure read over run
    facts (D1 - no leaderboard table, nothing persisted). Models that
    were never run are ABSENT from the result, never zero (D12). This
    view compares; it does not select - model selection is WS3, a
    governed decision, not a property of this read."""
    pkg = session.query(db.AgentPackage).filter(
        db.AgentPackage.id == agent_package_id).first()
    if not pkg:
        raise LookupError(f"Agent Package with ID {agent_package_id} not found")

    runs = session.query(db.EvaluationRun).filter(
        db.EvaluationRun.run_type == "PACKAGE",
        db.EvaluationRun.package_hash == pkg.package_hash,
        db.EvaluationRun.status == "COMPLETED"
    ).order_by(db.EvaluationRun.id.asc()).all()

    by_model = {}
    for run in runs:
        key = (run.consumer_model_provider, run.consumer_model_name)
        verdicts = session.query(db.ClaimVerdict).filter(
            db.ClaimVerdict.evaluation_run_id == run.id).all()
        counts = {"ENTAILED": 0, "CONTRADICTED": 0, "UNSUPPORTED": 0}
        for v in verdicts:
            if v.verdict in counts:
                counts[v.verdict] += 1
        total = sum(counts.values())
        by_model.setdefault(key, []).append({
            "run_id": run.id,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "pass_rate": run.pass_rate,
            "average_coverage_score": run.average_coverage_score,
            "claims_total": total if total else None,
            "verdict_counts": counts if total else None,
        })

    return {
        "agent_package_id": pkg.id,
        "package_name": pkg.name,
        "package_version": pkg.governance_version,
        "package_hash": pkg.package_hash,
        "models": [{
            "provider": provider,
            "model": model,
            "runs": model_runs,
            "latest": model_runs[-1],
        } for (provider, model), model_runs in sorted(by_model.items())],
        "note": "Models never evaluated against this package are absent, not zero (D12).",
    }


def _package_answer(session: Session, db_run, file_path: str, question: str):
    """One PACKAGE-channel question: consume through the verified package
    (the ONLY retrieval/generation path on this channel) and verify with
    the same independent referee the LIVE channel uses. Returns
    (answer, citations, verification)."""
    result = package_consumer.consume(file_path, question, session=session)

    if result["package"]["package_hash"] != db_run.package_hash:
        raise RuntimeError(
            "Package artifact changed between run creation and execution - refusing to evaluate")
    actual = result["model"]
    if (actual["provider"], actual["model"]) != (db_run.consumer_model_provider,
                                                 db_run.consumer_model_name):
        raise RuntimeError(
            f"Consumer model drifted mid-run: run records "
            f"{db_run.consumer_model_provider}/{db_run.consumer_model_name} but "
            f"{actual['provider']}/{actual['model']} answered - refusing to mislabel the run (D12)")

    citations = [{
        "asset_id": e["asset_id"],
        "name": e.get("name"),
        "content": e.get("content"),
        "access_level": e.get("access_level"),
        "source_document": (e.get("provenance") or {}).get("source_document"),
    } for e in result["evidence"]]

    answer = result["answer"]
    if answer.startswith("INSUFFICIENT EVIDENCE"):
        # The packaged answering policy's refusal contract. A refusal is
        # policy compliance, not a knowledge claim - judging its sentence
        # against evidence would persist junk verdicts (D12).
        verification = {
            "coverage_score": 0.0,
            "verification_status": "INSUFFICIENT_EVIDENCE",
            "unsupported_claims": [],
            "contradicted_claims": [],
            "claim_mappings": [],
            "verifier": {"method": "REFUSAL_RECOGNIZED", "engine_version": "none"},
        }
    else:
        verification = query_engine.verify_answer_claims(session, answer, citations)
    return answer, citations, verification


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

        package_path = None
        if db_run.run_type == "PACKAGE":
            pkg = session.query(db.AgentPackage).filter(
                db.AgentPackage.package_hash == db_run.package_hash).first()
            if not pkg or not pkg.file_path or not os.path.exists(pkg.file_path):
                raise RuntimeError(
                    f"Package with hash {(db_run.package_hash or '')[:16]}... has no artifact to evaluate")
            package_path = pkg.file_path

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
            if db_run.run_type == "PACKAGE":
                # Portable channel: package_consumer is the ONLY
                # retrieval/generation path. No query_engine retrieval,
                # no DB assets - the verified .empkg is the universe.
                answer, citations, verification = _package_answer(
                    session, db_run, package_path, b.question)
            else:
                # Governed channel (pre-WS2 behavior, unchanged):
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
                answer = gen_result["answer"]

                # 3. Answer Verification
                verification = query_engine.verify_answer_claims(
                    session,
                    answer_text=answer,
                    validated_citations=citations
                )

            coverage_score = verification["coverage_score"]
            verification_status = verification["verification_status"]
            conf_score = 0.95 if coverage_score >= 0.95 else 0.85 if coverage_score >= 0.80 else 0.40

            final_answer = answer
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
            # discarding them. Same persistence on BOTH channels - and the
            # verifier identity recorded here is the referee's, never the
            # consumer model under test.
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
        session.rollback()
        db_run = session.query(db.EvaluationRun).filter(db.EvaluationRun.id == run_id).first()
        db_run.status = "FAILED"
        db_run.completed_at = datetime.datetime.utcnow()
        session.commit()
