import os

from sqlalchemy.orm import Session

from app import database as db

# LLM Provider Settings (MVP 0.12): governed model-per-function resolution.
#
# The central invariant (scoping brief / D19 candidate):
#
#   DB config missing -> OPENAI_MODEL env -> gpt-4o-mini default
#
# An empty config table preserves pre-0.12 behavior. The resolver stores
# model SELECTION only - credentials stay in the environment until the
# v1.x identity layer (D14). Provider is OPENAI-only for now (D11); the
# adapter abstraction is earned when a second provider is implemented.

DEFAULT_MODEL = "gpt-4o-mini"

# The four LLM-using functions in the codebase, by call site.
FUNCTIONS = {
    "EXTRACTION": "Knowledge asset extraction from document chunks (extraction.py)",
    "CLAIM_DECOMPOSITION": "Atomic claim decomposition (claims.py)",
    "CLAIM_JUDGE": "Legacy per-claim evidence judge fallback (query_engine.py)",
    "ANSWER_GENERATION": "Evidence-grounded answer generation (query_engine.py)",
}


def resolve(function: str, session: Session = None) -> dict:
    """Resolve the model serving a function, with its provenance:
    {function, provider, model, source} where source is one of
    CONFIG | ENV | DEFAULT. Opens its own short read session when the
    call site has none (claims decomposition, verification path)."""
    if function not in FUNCTIONS:
        raise ValueError(f"Unknown LLM function '{function}'. Known: {sorted(FUNCTIONS)}")

    owns_session = session is None
    if owns_session:
        session = db.SessionLocal()
    try:
        row = session.query(db.LLMFunctionConfig).filter(
            db.LLMFunctionConfig.function == function).first()
        if row and row.model:
            return {"function": function, "provider": row.provider or "OPENAI",
                    "model": row.model, "source": "CONFIG"}
    finally:
        if owns_session:
            session.close()

    env_model = os.environ.get("OPENAI_MODEL")
    if env_model:
        return {"function": function, "provider": "OPENAI",
                "model": env_model, "source": "ENV"}
    return {"function": function, "provider": "OPENAI",
            "model": DEFAULT_MODEL, "source": "DEFAULT"}


def model_for(function: str, session: Session = None) -> str:
    """Convenience: just the model name for a function."""
    return resolve(function, session)["model"]
