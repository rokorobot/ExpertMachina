# v0.12.0 — LLM Provider Settings: Scoping Brief

Agreed scope (2026-06-11). Numbered release: this creates a new governed
configuration subsystem (table, endpoints, UI surface, audit events) and
changes four model-using call sites.

## The deliverable in one sentence

Env vars become governed, audited runtime configuration with
model-per-function resolution — WITHOUT building a multi-provider runtime,
LLM benchmarking, or secret management.

## The key design rule

```
Store model selection.
Do not store credentials.
```

API keys remain env-based until the v1.x identity/credentials layer (D14).
Config rows may reference WHICH env var holds a key; never the key itself.

## The central invariant (backward compatibility)

```
DB config missing → OPENAI_MODEL env → gpt-4o-mini default
```

An empty config table preserves today's behavior exactly. Discovery note:
before v0.12 no call site actually honored OPENAI_MODEL — all four
hardcoded gpt-4o-mini; the resolver makes the long-documented env override
real as the middle precedence tier.

## Deliverables

- `LLMFunctionConfig` table — a governed fact in the ApprovalPolicy mold:
  function, provider (only "OPENAI" populated for now — D11), model,
  updated_at/updated_by. No delete endpoint needed: clearing the model
  resets the function to env/default resolution.
- `backend/app/llm.py` resolver — `resolve(function, session=None)` with
  the three-tier precedence; opens its own short read session when the
  call site has none (claims.py, query_engine verification path).
- The four call sites resolve through it:
  extraction.extract_via_llm (EXTRACTION), claims._decompose_llm
  (CLAIM_DECOMPOSITION), query_engine legacy judge (CLAIM_JUDGE — incl.
  the verifier fingerprint, which must report the RESOLVED model, never a
  hardcoded string; D12 honest measurement), query_engine answer
  generation (ANSWER_GENERATION).
- API: GET /api/settings/llm (per function: configured model, effective
  model, resolution source), PUT /api/settings/llm/{function}
  (set or clear). Every change writes an LLM_CONFIG_UPDATED audit event
  with old/new.
- UI: minimal Settings tab, one "LLM Models" section — the long-deferred
  Settings area arrives because the config store now exists to justify it.
- Tests: resolver precedence suite (test_llm_settings.py) + HTTP smoke
  coverage (third regression layer, from birth).

## Do not overbuild (the connector lesson applied)

A `provider` column is enough. The LLMProviderAdapter abstraction is
earned when a second provider is actually implemented — exactly like the
connector framework was extracted against the real LocalFolder provider,
not guessed. Non-OpenAI SDK code remains ask-first (D11).

## Explicitly out of scope

- Secret/credential storage (v1.x identity layer)
- Non-OpenAI adapters and test-connection buttons (meaningless without
  stored credentials)
- Per-package model EVALUATION (the post-v1.0 arc; this milestone only
  lays its configuration rail)

## D-register candidate at release

"Store model selection, never credentials; empty configuration preserves
prior behavior" — ratify as D19 when v0.12.0 ships, evidence: the
resolver precedence tests.
