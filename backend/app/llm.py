import os

from sqlalchemy.orm import Session

from app import database as db

# LLM Provider Settings (MVP 0.12): governed model-per-function resolution.
#
# The central invariant (D19):
#
#   DB config missing -> OPENAI_MODEL env -> gpt-4o-mini default
#
# An empty config table preserves pre-0.12 behavior. The resolver stores
# model SELECTION only - credentials stay in the environment until the
# enterprise credentials milestone (D14/D19).
#
# Provider adapters (v1.1 WS1): the second provider earned the abstraction
# D11 deferred. Adapters speak one shape - (model, system, user, max_tokens)
# -> text - and are chosen by the resolved provider. Call sites that need
# the boundary pattern (Consumer / Evaluation -> resolver -> adapter ->
# response, per the v1.1 scoping ruling) go through generate(); they never
# import a provider SDK directly. The env tier remains OPENAI-only: a
# non-OPENAI provider is reachable exclusively through explicit, audited
# config (D19 - configuration is opt-in acceleration).

DEFAULT_MODEL = "gpt-4o-mini"

# The LLM-using functions in the codebase, by call site.
FUNCTIONS = {
    "EXTRACTION": "Knowledge asset extraction from document chunks (extraction.py)",
    "CLAIM_DECOMPOSITION": "Atomic claim decomposition (claims.py)",
    "CLAIM_JUDGE": "Legacy per-claim evidence judge fallback (query_engine.py)",
    "ANSWER_GENERATION": "Evidence-grounded answer generation (query_engine.py)",
    "PACKAGE_CONSUMER": "Portable-channel answer generation from an Expert Package (package_consumer.py)",
}


def _openai_adapter(model: str, system: str, user: str, max_tokens: int) -> str:
    from openai import OpenAI
    client = OpenAI()  # reads OPENAI_API_KEY from the environment (D19)
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _anthropic_adapter(model: str, system: str, user: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment (D19)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()


ADAPTERS = {
    "OPENAI": _openai_adapter,
    "ANTHROPIC": _anthropic_adapter,
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


def generate(function: str, system: str, user: str,
             session: Session = None, max_tokens: int = 4096) -> dict:
    """The provider-adapter boundary: resolve the function's model (D19),
    dispatch to that provider's adapter, return the text WITH its model
    provenance: {function, provider, model, source, text}."""
    resolved = resolve(function, session)
    provider = (resolved["provider"] or "OPENAI").upper()
    adapter = ADAPTERS.get(provider)
    if adapter is None:
        raise ValueError(
            f"No adapter for provider '{provider}'. Known: {sorted(ADAPTERS)}")
    text = adapter(resolved["model"], system, user, max_tokens)
    return {**resolved, "text": text}
