import json
import datetime
import threading

from sqlalchemy.orm import Session

from app import database as db
from app import crud
from app import schemas
from app import identity
from app import policy
from app import classification

# Tier-2 engine-verified auto-approval (v1.2.1 WS3, D26).
#
# The candidate-contradiction check: a CANDIDATE asset is verified
# against the project's APPROVED corpus before a Tier-2 policy may
# auto-approve it. The disciplines:
#
#   - Tier-2 verification is a REFUSAL-TO-APPROVE mechanism, never a
#     rejection mechanism. The engine may say "do not auto-approve this
#     candidate"; it never makes the human governance decision that
#     content is false. A contradicted candidate is HELD - a declared
#     exception naming the contradicting approved asset.
#   - Async per D4: ingestion returns immediately and records only that
#     the pass was SCHEDULED; the background task owns its own session
#     and writes its own audit events.
#   - Verdicts live in event provenance ONLY - never AssetRelationship
#     rows. Candidate checks must not pollute the approved-conflict
#     surfaces or the conflict score.
#   - The conflict engine's calibration discipline: strict contradiction
#     threshold, embedding pre-filter above a pair cap, dropped pairs
#     counted and DECLARED (D12).
#   - Domain scoping: a policy with domain coverage compares the
#     candidate only against the approved corpus under those prefixes
#     (WS1 taxonomy); no coverage = the whole project's approved corpus.
#   - Approval goes through crud.update_knowledge_asset - the one
#     governed transition path - with the DELEGATED actor
#     `policy:<name>`, exactly like every other tier.
#
# The verifier seam (the fake-Graph pattern applied to NLI): tests
# inject a deterministic verifier via `verifier_factory`; production
# resolves the real NLI engine. Whichever verifier runs, its identity is
# recorded in provenance - the seam is explicit and auditable, never
# hidden. Real NLI stays behind the existing EM_NLI_* environment knobs.

ALLOWED_CONTRADICTION_MODES = {"CLEAN_REQUIRED"}

# Test seam: a callable returning a verifier object (or None for "engine
# unavailable"). None here means "resolve the real NLI engine".
verifier_factory = None

_pending_threads = []


def validate_engine_conditions(conditions):
    """Structural validation - loud, never permissive. Returns the
    normalized dict, or None when empty (an empty object is stored as
    NULL: not a Tier-2 policy, the D19 empty-config invariant)."""
    if conditions is None:
        return None
    if not isinstance(conditions, dict):
        raise ValueError("engine_conditions must be an object")
    if not conditions:
        return None
    unknown = set(conditions) - {"contradiction_check"}
    if unknown:
        raise ValueError(f"engine_conditions: unknown fields {sorted(unknown)}")
    mode = conditions.get("contradiction_check")
    if mode not in ALLOWED_CONTRADICTION_MODES:
        raise ValueError(
            f"engine_conditions.contradiction_check must be one of "
            f"{sorted(ALLOWED_CONTRADICTION_MODES)}, got {mode!r}")
    return conditions


def is_tier2(policy_row) -> bool:
    return bool(policy_row.engine_conditions)


def tier2_policies_in_scope(session: Session, project_id: int, connector_id: int = None) -> list:
    return [p for p in policy.policies_for_scope(session, project_id, connector_id)
            if is_tier2(p)]


# ------------------------------------------------------------- verifier

class NLIContradictionVerifier:
    """The real engine: pairwise NLI of the candidate against the corpus
    with the conflict engine's calibration (strict threshold, embedding
    pre-filter above the pair cap, both directions judged)."""

    def __init__(self, pipe):
        from app import conflict_engine
        from app import verification_engine
        self._pipe = pipe
        self._threshold = conflict_engine.CONFLICT_CONTRADICTION_THRESHOLD
        self._max_pairs = conflict_engine.MAX_NLI_PAIRS
        self.identity = {
            **verification_engine.verifier_identity(),
            "check": "TIER2_CANDIDATE_CONTRADICTION_V1",
            "contradiction_threshold": self._threshold,
        }

    def check(self, candidate, corpus: list) -> dict:
        from app import ingestion
        from app import verification_engine
        kept, dropped = corpus, 0
        if len(corpus) > self._max_pairs:
            cand_emb = ingestion.get_embedding(candidate.content)
            scored = sorted(
                ((verification_engine._cosine(cand_emb,
                                              ingestion.get_embedding(a.content)), a)
                 for a in corpus),
                key=lambda item: item[0], reverse=True)
            kept = [a for _, a in scored[:self._max_pairs]]
            dropped = len(corpus) - len(kept)
        contradictions = []
        for approved in kept:
            results = self._pipe(
                [{"text": candidate.content, "text_pair": approved.content},
                 {"text": approved.content, "text_pair": candidate.content}],
                top_k=None, truncation=True)
            score = max(
                next((s["score"] for s in r if s["label"].lower() == "contradiction"), 0.0)
                for r in results)
            if score >= self._threshold:
                contradictions.append({"asset_id": approved.id, "score": round(score, 4)})
        return {"pairs_checked": len(kept), "pairs_dropped": dropped,
                "contradictions": contradictions}


def _resolve_verifier():
    if verifier_factory is not None:
        return verifier_factory()
    from app import verification_engine
    pipe = verification_engine.get_nli_pipeline()
    return NLIContradictionVerifier(pipe) if pipe is not None else None


# ------------------------------------------------------------ scheduling

def schedule_pass(project_id: int, document_ids: list, connector_id: int = None,
                  ingestion_job_id: int = None, on_behalf_of_fact_id: int = None):
    """Schedule the Tier-2 pass (D4): the caller returns immediately;
    the pass runs in the background owning its own session. Callers
    record only that the pass was SCHEDULED - never results."""
    thread = threading.Thread(
        target=_run_with_owned_session,
        args=(project_id, list(document_ids), connector_id,
              ingestion_job_id, on_behalf_of_fact_id),
        daemon=True)
    _pending_threads.append(thread)
    thread.start()
    return thread


def drain():
    """Wait for every scheduled pass to complete. Test/sentinel hook -
    the WS0 guard's guarantee is 'after ALL background tasks complete',
    and this is how it is honored."""
    while _pending_threads:
        _pending_threads.pop().join()


def _run_with_owned_session(project_id, document_ids, connector_id,
                            ingestion_job_id, on_behalf_of_fact_id):
    session = db.SessionLocal()  # D4: the background task owns its session
    try:
        run_pass(session, project_id, document_ids, connector_id=connector_id,
                 ingestion_job_id=ingestion_job_id,
                 on_behalf_of_fact_id=on_behalf_of_fact_id)
    except Exception as e:
        # A failed pass approves nothing and says so - never silent.
        try:
            actor = identity.system_actor(session, "policy_engine")
            crud.log_audit_event(
                session, actor=actor.display, identity_fact_id=actor.fact(session).id,
                event_type="POLICY_TIER2_COMPLETED",
                target_id=str(ingestion_job_id) if ingestion_job_id else None,
                details=json.dumps({"error": str(e), "auto_approved": 0}))
        except Exception:
            print(f"TIER2: pass failed and the failure event could not be written: {e}")
    finally:
        session.close()


# ------------------------------------------------------------- the pass

def run_pass(session: Session, project_id: int, document_ids: list,
             connector_id: int = None, ingestion_job_id: int = None,
             on_behalf_of_fact_id: int = None) -> dict:
    """Evaluate Tier-2 policies against the still-CANDIDATE assets of one
    ingestion event. Clean under a satisfied policy -> approved through
    the governed path with full engine provenance; contradicted -> HELD,
    the contradicting approved asset named; engine unavailable -> nothing
    approved, declared (D12)."""
    summary = {
        "policies_evaluated": 0,
        "assets_considered": 0,
        "auto_approved": 0,
        "held_contradicted": 0,
        "skipped_not_covered": 0,
        "engine_available": False,
        "pairs_dropped_total": 0,
    }
    policies = tier2_policies_in_scope(session, project_id, connector_id)
    summary["policies_evaluated"] = len(policies)
    if not policies or not document_ids:
        return summary

    assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id,
        db.KnowledgeAsset.document_id.in_(document_ids),
        db.KnowledgeAsset.status == "CANDIDATE",
    ).order_by(db.KnowledgeAsset.id).all()
    summary["assets_considered"] = len(assets)

    verifier = _resolve_verifier()
    on_behalf_of_fact = identity.get_fact(session, on_behalf_of_fact_id)
    source_context = classification._source_context(session, document_ids, ingestion_job_id)

    approved_ids, held = [], []
    verifier_identity = getattr(verifier, "identity", None)
    if verifier is not None:
        summary["engine_available"] = True
        policy_actors = {}
        for asset in assets:
            source_uri, source_metadata = source_context.get(asset.document_id, (None, {}))
            matched, matched_evidence = None, None
            for p in policies:
                if asset.type not in p.asset_types:
                    continue
                if not policy.domain_covered(p, asset):
                    continue
                met, evidence = policy.source_conditions_met(p, source_metadata)
                if not met:
                    continue
                matched, matched_evidence = p, evidence
                break
            if not matched:
                summary["skipped_not_covered"] += 1
                continue

            corpus = _approved_corpus(session, project_id, matched.domains,
                                      exclude_asset_id=asset.id)
            verdict = verifier.check(asset, corpus)
            summary["pairs_dropped_total"] += verdict.get("pairs_dropped", 0)
            if verdict["contradictions"]:
                # Held, never rejected: the engine refuses to approve;
                # only a human may refuse content. The contradicting
                # approved asset is NAMED.
                summary["held_contradicted"] += 1
                held.append({
                    "asset_id": asset.id,
                    "policy_id": matched.id,
                    "contradictions": verdict["contradictions"],
                    "pairs_checked": verdict["pairs_checked"],
                    "pairs_dropped": verdict.get("pairs_dropped", 0),
                })
                continue

            if matched.id not in policy_actors:
                policy_actors[matched.id] = identity.delegated_actor(
                    session, f"policy:{matched.name}", on_behalf_of=on_behalf_of_fact)
            provenance = {
                "policy_id": matched.id,
                "policy_name": matched.name,
                "policy_version": matched.version,
                "policy_snapshot": {"asset_types": matched.asset_types,
                                    "connector_id": matched.connector_id,
                                    "source_conditions": matched.source_conditions,
                                    "engine_conditions": matched.engine_conditions,
                                    "domains": matched.domains},
                "asset_type": asset.type,
                "document_id": asset.document_id,
                "ingestion_job_id": ingestion_job_id,
                "approved_without_human": True,
                "tier": "TIER2",
                # The engine verdict that carried this approval - the
                # verifier's identity (real NLI fingerprint or the
                # declared deterministic test seam), the coverage, and
                # the declared drops. Event provenance is the ONLY home
                # of candidate verdicts (never AssetRelationship rows).
                "engine_verdict": {
                    "verifier": verifier_identity,
                    "pairs_checked": verdict["pairs_checked"],
                    "pairs_dropped": verdict.get("pairs_dropped", 0),
                    "domain_scope": matched.domains or "PROJECT",
                    "contradictions": [],
                },
                "triggered_at": datetime.datetime.utcnow().isoformat(),
            }
            if matched.source_conditions:
                provenance["source_authority"] = {"matched": matched_evidence,
                                                  "source_uri": source_uri}
            crud.update_knowledge_asset(
                session, asset.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
                actor=policy_actors[matched.id],
                audit_event_type="ASSET_AUTO_APPROVED",
                audit_details=json.dumps(provenance),
                review_notes=f"approved by policy: {matched.name} "
                             f"(v{matched.version}, engine-verified)",
            )
            summary["auto_approved"] += 1
            approved_ids.append(asset.id)
    else:
        # Engine unavailable: refuse to approve, and say so (D12).
        summary["skipped_not_covered"] = 0

    engine_actor = identity.system_actor(session, "policy_engine")
    crud.log_audit_event(
        session, actor=engine_actor.display, identity_fact_id=engine_actor.fact(session).id,
        event_type="POLICY_TIER2_COMPLETED",
        target_id=str(ingestion_job_id) if ingestion_job_id else None,
        details=json.dumps({
            **summary,
            "connector_id": connector_id,
            "approved_asset_ids": approved_ids,
            "held": held,
            "verifier": verifier_identity,
            "policies": [{"id": p.id, "name": p.name, "version": p.version}
                         for p in policies],
        }))
    return summary


def _approved_corpus(session: Session, project_id: int, domains,
                     exclude_asset_id: int = None) -> list:
    """The comparison corpus: the project's APPROVED assets, scoped by
    the policy's domain prefixes when present (WS1 taxonomy), the whole
    project otherwise."""
    query = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id,
        db.KnowledgeAsset.status == "APPROVED")
    if exclude_asset_id:
        query = query.filter(db.KnowledgeAsset.id != exclude_asset_id)
    assets = query.order_by(db.KnowledgeAsset.id).all()
    if not domains:
        return assets
    return [a for a in assets if a.domain and any(
        a.domain == d or a.domain.startswith(d + "/") for d in domains)]
