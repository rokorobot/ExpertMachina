import os
import re
import json

# Atomic claim decomposition (MVP 0.6). A compound policy sentence like
#   "Critical deviations must be logged within 24 hours and reviewed weekly
#    by the quality manager unless escalated."
# carries several distinct verifiable claims; NLI must judge each one
# separately or coverage scores stay coarse.
#
# Tiers, mirroring the verifier hierarchy:
#   LLM_ATOMIC        - one batched structured LLM call (OPENAI_API_KEY set)
#   RULE_COORDINATION - deterministic: sentence split, then coordinated
#                       passive-modal predicates distributed over the
#                       subject, with trailing condition clauses ("unless
#                       ...") preserved on every resulting claim.

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
CONDITION_SPLIT = re.compile(r"\s+(unless|except when|except where|provided that)\s+", re.IGNORECASE)
MODAL_HEAD = re.compile(
    r"^(?P<head>.*?\b(?:must|shall|should|may|might|will|would|can|cannot)\b(?:\s+not)?\s+(?:be\s+)?)(?P<predicates>.+)$",
    re.IGNORECASE,
)
PARTICIPLE_START = re.compile(r"^\w+(?:ed|en)\b")


def _split_sentences(text: str) -> list:
    sentences = []
    for raw in SENTENCE_SPLIT.split(text):
        cleaned = raw.strip()
        if cleaned and len(cleaned.split()) > 2:
            sentences.append(cleaned)
    return sentences


def _decompose_sentence(sentence: str) -> list:
    """Distribute coordinated passive-modal predicates over their shared
    subject. Conservative by design: sentences that do not match the
    pattern pass through unchanged rather than being split wrongly."""
    condition = None
    main = sentence
    cond_match = CONDITION_SPLIT.search(sentence)
    if cond_match:
        main = sentence[:cond_match.start()].rstrip(" ,.")
        condition = sentence[cond_match.start():].strip().rstrip(".")

    parts = [main.rstrip(".")]
    modal_match = MODAL_HEAD.match(main)
    if modal_match:
        predicates = re.split(r",?\s+and\s+", modal_match.group("predicates"))
        cleaned = [p.strip().rstrip(".") for p in predicates if p.strip()]
        if len(cleaned) > 1 and all(PARTICIPLE_START.match(p) for p in cleaned):
            parts = [modal_match.group("head") + p for p in cleaned]

    if condition:
        parts = [f"{p} {condition}" for p in parts]
    return [p + "." for p in parts]


def _decompose_rule_based(text: str) -> list:
    claims = []
    for sentence in _split_sentences(text):
        claims.extend(_decompose_sentence(sentence))
    return claims


def _decompose_llm(text: str) -> list:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key.startswith("mock-"):
        return None
    try:
        from llama_index.llms.openai import OpenAI
        llm = OpenAI(model="gpt-4o-mini", api_key=api_key)
        prompt = (
            "Decompose the following text into atomic factual claims. Each claim must be "
            "a single self-contained assertion, preserving any conditions (e.g. 'unless "
            "escalated') on every claim they govern. Do not add, infer, or omit facts.\n\n"
            f"TEXT:\n{text}\n\n"
            "Output ONLY a JSON array of claim strings."
        )
        response = str(llm.complete(prompt).text).strip()
        match = re.search(r"\[.*\]", response, re.DOTALL)
        if not match:
            return None
        claims = json.loads(match.group(0))
        cleaned = [c.strip() for c in claims if isinstance(c, str) and len(c.split()) > 2]
        return cleaned or None
    except Exception as e:
        print(f"LLM claim decomposition failed ({e}). Falling back to rule-based decomposition.")
        return None


def decompose_claims(text: str) -> tuple:
    """Returns (claims, method). The method is recorded in the verification
    report so claim granularity is a reproducible part of every verdict."""
    llm_claims = _decompose_llm(text)
    if llm_claims is not None:
        return llm_claims, "LLM_ATOMIC"
    return _decompose_rule_based(text), "RULE_COORDINATION"
