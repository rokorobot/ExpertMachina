import os
import math
import hashlib

from app import ingestion

# Knowledge Integrity Engine: local NLI entailment with embedding pre-filter.
# Falls back to None when transformers/torch are unavailable so callers can
# degrade to the LLM-judge or keyword-overlap paths in query_engine.
#
# Default is multilingual (validated on English, Czech, and cross-lingual
# English-evidence/Czech-claim pairs). For English-only corpora, set
# EM_NLI_MODEL_ID=MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli as the
# optimized mode.
NLI_MODEL_ID = os.environ.get("EM_NLI_MODEL_ID", "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7")
ENTAILMENT_THRESHOLD = float(os.environ.get("EM_NLI_ENTAILMENT_THRESHOLD", "0.80"))
CONTRADICTION_THRESHOLD = float(os.environ.get("EM_NLI_CONTRADICTION_THRESHOLD", "0.80"))
PREFILTER_TOP_K = int(os.environ.get("EM_NLI_PREFILTER_TOP_K", "4"))
ENGINE_VERSION = "nli-v1"

_nli_pipeline = None
_nli_load_failed = False
_model_fingerprint = None


def is_enabled() -> bool:
    # EM_NLI_VERIFICATION=off forces the legacy fallback paths (used by tests
    # that must stay deterministic without model downloads).
    return os.environ.get("EM_NLI_VERIFICATION", "auto").lower() != "off"


def _compute_model_fingerprint() -> dict:
    """SHA256 over the cached model weight files plus the HF snapshot
    revision, so any historical verification verdict can be reproduced
    against the exact weights that produced it."""
    global _model_fingerprint
    if _model_fingerprint is not None:
        return _model_fingerprint
    fingerprint = {"model_revision": None, "weights_hash": None}
    try:
        from huggingface_hub import snapshot_download
        snapshot_path = snapshot_download(NLI_MODEL_ID, local_files_only=True)
        fingerprint["model_revision"] = os.path.basename(snapshot_path)
        hasher = hashlib.sha256()
        weight_files = sorted(
            f for f in os.listdir(snapshot_path)
            if f.endswith((".safetensors", ".bin"))
        )
        for weight_file in weight_files:
            with open(os.path.join(snapshot_path, weight_file), "rb") as fh:
                for block in iter(lambda: fh.read(1 << 20), b""):
                    hasher.update(block)
        if weight_files:
            fingerprint["weights_hash"] = hasher.hexdigest()
    except Exception as e:
        print(f"Model fingerprint unavailable ({e}).")
    _model_fingerprint = fingerprint
    return fingerprint


def verifier_identity() -> dict:
    fingerprint = _compute_model_fingerprint()
    return {
        "method": "NLI_LOCAL",
        "model_id": NLI_MODEL_ID,
        "model_revision": fingerprint["model_revision"],
        "weights_hash": fingerprint["weights_hash"],
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

    per_claim = [{"supporting": {}, "contradicting": {}, "max_neutral": 0.0} for _ in claims]
    for (claim_idx, asset_id), scores in zip(pair_index, results):
        score_map = {entry["label"].lower(): entry["score"] for entry in scores}
        entailment = score_map.get("entailment", 0.0)
        contradiction = score_map.get("contradiction", 0.0)
        neutral = score_map.get("neutral", 0.0)
        state = per_claim[claim_idx]
        state["max_neutral"] = max(state["max_neutral"], neutral)
        if entailment >= ENTAILMENT_THRESHOLD and entailment >= contradiction:
            state["supporting"][asset_id] = max(state["supporting"].get(asset_id, 0.0), entailment)
        elif contradiction >= CONTRADICTION_THRESHOLD and contradiction > entailment:
            state["contradicting"][asset_id] = max(state["contradicting"].get(asset_id, 0.0), contradiction)

    claim_mappings = []
    unsupported_claims = []
    contradicted_claims = []
    for claim_idx, claim in enumerate(claims):
        state = per_claim[claim_idx]
        supporting = sorted(state["supporting"])
        contradicting = sorted(state["contradicting"])
        # Confidence is the model probability behind the winning verdict.
        if supporting:
            verdict = "ENTAILED"
            confidence = max(state["supporting"].values())
        elif contradicting:
            verdict = "CONTRADICTED"
            confidence = max(state["contradicting"].values())
            contradicted_claims.append(claim)
        else:
            verdict = "UNSUPPORTED"
            confidence = state["max_neutral"]
            unsupported_claims.append(claim)
        claim_mappings.append({
            "claim": claim,
            "verdict": verdict,
            "confidence": round(confidence, 3),
            "supporting_assets": supporting,
            "contradicting_assets": contradicting,
        })

    return {
        "claim_mappings": claim_mappings,
        "unsupported_claims": unsupported_claims,
        "contradicted_claims": contradicted_claims,
        "verifier": verifier_identity(),
    }
