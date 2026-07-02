import os
import json
import hashlib
import datetime
import zipfile

from sqlalchemy.orm import Session

from app import database as db
from app import trust
from app import evaluation
from app import conflict_engine
from app.query_engine import ACCESS_RANK

# Agent Package Builder (MVP 0.9.4).
#
# Compiles a governed Expert Model into a portable .empkg artifact - the
# thing the compile gate has been guarding all along. Export crosses the
# governance boundary: outside ExpertMachina none of the runtime guarantees
# (per-question verification, access tiers, audit) apply, so the package's
# job is to make its governance state VERIFIABLE, not enforced:
#
#   - every file is sha256-hashed in manifest.json; the package hash is the
#     sha256 of manifest.json itself (tamper-evident chain)
#   - trust / conflict / coverage state is a snapshot stamped compiled_at -
#     the package says "true at compile time", never "enforced"
#   - assets are filtered to the package's declared clearance level, so a
#     file handed to a PUBLIC agent cannot leak higher-tier knowledge
#   - instructions.md carries the answering policy (cite, refuse, never
#     improvise) as a portable contract
#
# The MCP gateway remains the GOVERNED consumption channel (live
# enforcement); packages are the PORTABLE channel (verifiable provenance).

PACKAGE_FORMAT_VERSION = "empkg-v1"


def _package_dir() -> str:
    path = os.environ.get("EM_PACKAGE_DIR", "./packages")
    os.makedirs(path, exist_ok=True)
    return path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(obj) -> bytes:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _slug(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


def member_assets(session: Session, model: db.ExpertModel, clearance_level: str):
    """APPROVED member assets of the model at or below the package clearance.
    Returns (included, excluded_count) - exclusions are reported, never silent."""
    try:
        asset_ids = json.loads(model.asset_ids_json or "[]")
    except Exception:
        asset_ids = []
    assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.id.in_(asset_ids),
        db.KnowledgeAsset.status == "APPROVED"
    ).order_by(db.KnowledgeAsset.id.asc()).all() if asset_ids else []

    clearance_rank = ACCESS_RANK.get((clearance_level or "INTERNAL").upper(), ACCESS_RANK["INTERNAL"])
    included = [a for a in assets
                if ACCESS_RANK.get((a.access_level or "INTERNAL").upper(), ACCESS_RANK["INTERNAL"]) <= clearance_rank]
    return included, len(assets) - len(included)


def _knowledge_file(session: Session, assets: list) -> list:
    entries = []
    for asset in assets:
        doc = session.query(db.Document).filter(db.Document.id == asset.document_id).first()
        entries.append({
            "asset_id": asset.id,
            "name": asset.name,
            "type": asset.type,
            "content": asset.content,
            "access_level": asset.access_level or "INTERNAL",
            # v1.4.0 WS2 (D30): class travels into the portable artifact -
            # a consumer of the package sees derivation, indefinitely.
            "source_class": asset.source_class or "PRIMARY",
            "active_revision_number": asset.active_revision_number,
            "provenance": {
                "source_document": doc.filename if doc else None,
                "source_page": asset.source_page,
                "source_section": asset.source_section,
                "source_hash": asset.source_hash,
            },
        })
    return entries


def _evidence_file(session: Session, expert_model_id: int) -> dict:
    """Persisted verification facts from the latest completed evaluation run -
    no model loading at package time, only artifacts that already exist."""
    run = session.query(db.EvaluationRun).filter(
        db.EvaluationRun.expert_model_id == expert_model_id,
        db.EvaluationRun.status == "COMPLETED"
    ).order_by(db.EvaluationRun.id.desc()).first()
    if not run:
        return {"measured": False, "reason": "No completed evaluation run for this model."}

    verdicts = session.query(db.ClaimVerdict).filter(
        db.ClaimVerdict.evaluation_run_id == run.id
    ).order_by(db.ClaimVerdict.id.asc()).all()
    return {
        "measured": True,
        "evaluation_run_id": run.id,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "pass_rate": run.pass_rate,
        "average_coverage_score": run.average_coverage_score,
        "claim_verdicts": [{
            "claim": v.claim,
            "verdict": v.verdict,
            "confidence": v.confidence,
            "supporting_asset_ids": v.supporting_asset_ids,
            "contradicting_asset_ids": v.contradicting_asset_ids,
            "verifier": v.verifier,
            "evaluator_type": v.evaluator_type,
            "evaluator_id": v.evaluator_id,
        } for v in verdicts],
    }


def _instructions_file(model: db.ExpertModel, package_name: str, clearance_level: str,
                       trust_score, asset_count: int) -> str:
    return f"""# {model.name} - Governed Expert Package

This package was compiled by ExpertMachina from governed, revision-controlled,
conflict-checked, evidence-verified knowledge assets. Trust score at compile
time: {trust_score if trust_score is not None else 'not yet measured'}.
Clearance level: {clearance_level}. Knowledge assets included: {asset_count}.

## Answering policy (binding contract for any consuming agent)

1. Answer ONLY from the knowledge assets in `knowledge.json`. Do not use
   outside knowledge, do not improvise, do not generalize beyond the assets.
2. Cite the `asset_id` of every asset used in an answer.
3. If the assets do not contain the answer, reply exactly:
   "INSUFFICIENT EVIDENCE - this question is outside the governed knowledge
   of this expert package." Refusal is correct behavior, not failure.
4. If two assets appear to contradict each other, say so and cite both -
   never silently pick one.
5. Never reveal assets above this package's clearance level (none are
   included) and never alter provenance fields when citing.
6. Governance state in `trust.json`, `governance.json`, and `coverage.json`
   is a snapshot taken at compile time ({PACKAGE_FORMAT_VERSION}); it is
   verifiable via the hashes in `manifest.json` but not live-enforced.
   For live-governed answers, consume this Expert Model via the
   ExpertMachina MCP gateway instead.
"""


def build_package(session: Session, package_row: db.AgentPackage) -> dict:
    """Emit the .empkg zip for an already gate-checked AgentPackage row.
    Returns the manifest. Files are hashed individually; the package hash is
    the sha256 of manifest.json itself."""
    model = session.query(db.ExpertModel).filter(
        db.ExpertModel.id == package_row.expert_model_id).first()
    if not model:
        raise LookupError(f"Expert Model {package_row.expert_model_id} not found")

    clearance = (package_row.clearance_level or "INTERNAL").upper()
    assets, excluded_count = member_assets(session, model, clearance)

    trust_score = trust.compute_trust_score(session, model.id)
    coverage = evaluation.coverage_trend(session, model.id)
    gate = conflict_engine.evaluate_compile_gate(session, model.id)
    conflict_score = conflict_engine.compute_semantic_conflict_score(session, model.id)
    evidence = _evidence_file(session, model.id)
    knowledge = _knowledge_file(session, assets)

    governance = {
        "compile_gate": "PASSED" if gate["allowed"] else "BLOCKED",
        "gate_policy": gate["policy"],
        "conflict_scan_performed": gate["conflict_scan_performed"],
        "advisory_conflicts": len(gate["advisory_conflicts"]),
        "dismissed_conflicts": gate["dismissed_conflicts"],
        "semantic_conflict_score": conflict_score["semantic_conflict_score"],
        "semantic_conflict_summary": conflict_score["semantic_conflict_summary"],
        "governance_version": package_row.governance_version,
        "excluded_assets_above_clearance": excluded_count,
    }

    files = {
        "knowledge.json": _canonical(knowledge),
        "trust.json": _canonical(trust_score),
        "coverage.json": _canonical(coverage),
        "evidence.json": _canonical(evidence),
        "governance.json": _canonical(governance),
        "instructions.md": _instructions_file(
            model, package_row.name, clearance,
            trust_score["trust_score"], len(assets)).encode("utf-8"),
    }

    manifest = {
        "package_format": PACKAGE_FORMAT_VERSION,
        "package_name": package_row.name,
        "expert_model_id": model.id,
        "expert_model": model.name,
        "governance_version": package_row.governance_version,
        "clearance_level": clearance,
        "compiled_at": datetime.datetime.utcnow().isoformat(),
        "trust_score": trust_score["trust_score"],
        "asset_count": len(assets),
        "excluded_assets_above_clearance": excluded_count,
        "knowledge_hash": _sha256(files["knowledge.json"]),
        "files": {name: _sha256(data) for name, data in sorted(files.items())},
    }
    manifest_bytes = _canonical(manifest)
    package_hash = _sha256(manifest_bytes)

    filename = f"{_slug(package_row.name)}_v{package_row.governance_version}_pkg{package_row.id}.empkg"
    file_path = os.path.join(_package_dir(), filename)
    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", manifest_bytes)
        for name, data in sorted(files.items()):
            zf.writestr(name, data)

    package_row.file_path = file_path
    package_row.package_hash = package_hash
    package_row.manifest_json = manifest_bytes.decode("utf-8")
    session.commit()
    session.refresh(package_row)
    return manifest
