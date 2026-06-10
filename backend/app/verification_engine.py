import os
import math

from app import ingestion

# Phase 3 Verifier: local NLI entailment (English-first) with embedding pre-filter.
# Falls back to None when transformers/torch are unavailable so callers can
# degrade to the LLM-judge or keyword-overlap paths in query_engine.
NLI_MODEL_ID = os.environ.get("EM_NLI_MODEL_ID", "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")
ENTAILMENT_THRESHOLD = float(os.environ.get("EM_NLI_ENTAILMENT_THRESHOLD", "0.80"))
CONTRADICTION_THRESHOLD = float(os.environ.get("EM_NLI_CONTRADICTION_THRESHOLD", "0.80"))
PREFILTER_TOP_K = int(os.environ.get("EM_NLI_PREFILTER_TOP_K", "4"))
ENGINE_VERSION = "nli-v1"

_nli_pipeline = None
_nli_load_failed = False


def is_enabled() -> bool:
    # EM_NLI_VERIFICATION=off forces the legacy fallback paths (used by tests
    # that must stay deterministic without model downloads).
    return os.environ.get("EM_NLI_VERIFICATION", "auto").lower() != "off"


def verifier_identity() -> dict:
    return {
        "method": "NLI_LOCAL",
        "model_id": NLI_MODEL_ID,
        "engine_version": ENGINE_VERSION,
        "entailment_threshold": ENTAILMENT_THRESHOLD,
        "contradiction_threshold": CONTRADICTION_THRESHOLD,
    }


def get_nli_pipeline():
    global _nli_pipeline, _nli_load_failed
    if _nli_pipeline is not None:
        return _nli_pipeline
    if _nli_load_failed or not is_enabled():
        return None
    try:
        from transformers import pipeline
        _nli_pipeline = pipeline(
            "text-classification",
            model=NLI_MODEL_ID,
            device=-1,
        )
        return _nli_pipeline
    except Exception as e:
        print(f"NLI verifier unavailable ({e}). Falling back to legacy verification.")
        _nli_load_failed = True
        return None


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def prefilter_evidence(claim: str, citations: list, top_k: int = PREFILTER_TOP_K) -> list:
    """Bi-encoder recall stage: rank evidence by embedding similarity so the
    NLI cross-encoder only judges the top-k candidate pairs per claim."""
    if len(citations) <= top_k:
        return citations
    try:
        claim_vec = ingestion.get_embedding(claim)
        scored = [
            (_cosine(claim_vec, ingestion.get_embedding(cite["content"])), idx)
            for idx, cite in enumerate(citations)
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [citations[idx] for _, idx in scored[:top_k]]
    except Exception as e:
        print(f"Embedding pre-filter failed ({e}). Using unfiltered evidence.")
        return citations[:top_k]


def verify_claims_nli(claims: list, citations: list) -> dict:
    """
    Judges every (evidence, claim) pair with a local NLI cross-encoder.

    Returns None when the NLI stack is unavailable so the caller can fall back.
    Otherwise returns claim mappings with three-way verdicts:
      ENTAILED      - at least one evidence asset entails the claim
      CONTRADICTED  - no entailment, and at least one asset contradicts the claim
      UNSUPPORTED   - the evidence neither entails nor contradicts the claim
    """
    if not claims or not citations:
        return None
    pipe = get_nli_pipeline()
    if pipe is None:
        return None

    pair_index = []
    inputs = []
    for claim_idx, claim in enumerate(claims):
        for cite in prefilter_evidence(claim, citations):
            pair_index.append((claim_idx, cite["asset_id"]))
            inputs.append({"text": cite["content"], "text_pair": claim})

    try:
        results = pipe(inputs, top_k=None, truncation=True)
    except Exception as e:
        print(f"NLI inference failed ({e}). Falling back to legacy verification.")
        return None

    per_claim = [{"supporting": [], "contradicting": []} for _ in claims]
    for (claim_idx, asset_id), scores in zip(pair_index, results):
        score_map = {entry["label"].lower(): entry["score"] for entry in scores}
        entailment = score_map.get("entailment", 0.0)
        contradiction = score_map.get("contradiction", 0.0)
        if entailment >= ENTAILMENT_THRESHOLD and entailment >= contradiction:
            per_claim[claim_idx]["supporting"].append(asset_id)
        elif contradiction >= CONTRADICTION_THRESHOLD and contradiction > entailment:
            per_claim[claim_idx]["contradicting"].append(asset_id)

    claim_mappings = []
    unsupported_claims = []
    contradicted_claims = []
    for claim_idx, claim in enumerate(claims):
        supporting = sorted(set(per_claim[claim_idx]["supporting"]))
        contradicting = sorted(set(per_claim[claim_idx]["contradicting"]))
        if supporting:
            verdict = "ENTAILED"
        elif contradicting:
            verdict = "CONTRADICTED"
            contradicted_claims.append(claim)
        else:
            verdict = "UNSUPPORTED"
            unsupported_claims.append(claim)
        claim_mappings.append({
            "claim": claim,
            "verdict": verdict,
            "supporting_assets": supporting,
            "contradicting_assets": contradicting,
        })

    return {
        "claim_mappings": claim_mappings,
        "unsupported_claims": unsupported_claims,
        "contradicted_claims": contradicted_claims,
        "verifier": verifier_identity(),
    }
