# T2.6 — llama-index inventory & decision (2026-07-07)

Audit follow-up to the five base `llama-index-core` CVEs accepted (with a 2026-08-31
review date) in T2.2. This is the **inventory/proof step** the T2.6 plan requires —
no version changes here; it establishes what uses llama-index, whether each path is
required/optional/dead, and recommends upgrade vs isolate vs shed.

## Declared packages (base `requirements.txt`)

| Package | Pin | Direct use | Classification |
|---|---|---|---|
| `llama-index-vector-stores-qdrant` | 0.2.0 | **none** — `ingestion.py` imports `qdrant_client` directly | **DEAD** |
| `llama-index-core` | 0.10.44 | `extraction.py` (`LLMTextCompletionProgram`) + transitive base of the other three | **OPTIONAL** — carries all 5 CVEs |
| `llama-index-embeddings-openai` | 0.1.9 | `ingestion.get_embedding` | **OPTIONAL** |
| `llama-index-llms-openai` | 0.1.22 | `claims.py`, `extraction.py`, `query_engine.py` ×2 | **OPTIONAL** |

All four share `llama-index-core` transitively (the lock's `# via` shows core is pulled by
embeddings-openai, llms-openai, and vector-stores-qdrant) — so **shedding core is all-or-nothing**:
you cannot drop core while keeping the openai wrappers.

## The six import sites (every one)

| # | Site | What it does | Gate | Fallback |
|---|---|---|---|---|
| 1 | `claims.py:76` `llama_index.llms.openai.OpenAI` | LLM claim decomposition | `api_key and not mock-` | rule-based decomposition |
| 2 | `extraction.py:63-64` `OpenAI` + `LLMTextCompletionProgram` | structured asset extraction (Pydantic schema) | real key | `extract_via_rules` |
| 3 | `ingestion.py:44` `OpenAIEmbedding` | text embeddings | real key | deterministic hash-based mock embedding |
| 4 | `query_engine.py:162` `OpenAI` | LLM claim-alignment judge | `has_api_key` | keyword-overlap |
| 5 | `query_engine.py:306` `OpenAI` | evidence-grounded answer generation | real key | deterministic MOCK generation |

**Every site is:** (a) a lazy import inside a function, (b) gated behind a *real* OpenAI key
(skipped when the key is absent or `mock-…`), and (c) wrapped in `try/except` that logs a
warning and takes a deterministic fallback. **The platform runs fully without llama-index**,
and CI never exercises these paths (all suites use `mock-key`).

## Two decisive facts

1. **llama-index is legacy scaffolding the architecture already superseded.** The D19 provider
   layer in `app/llm.py` already calls the **native** SDKs directly —
   `_openai_adapter` does `from openai import OpenAI; client.chat.completions.create(...)`,
   `_anthropic_adapter` uses `anthropic` — and `openai==2.41.0` / `anthropic==0.109.1` are
   already first-class pinned deps. The six llama-index sites are the old path; llm.py is the
   new one. A native reference implementation already exists in-repo.
2. **The LLM paths cannot be runtime-verified in this environment.** No real `OPENAI_API_KEY`
   is available (the "real-model diagnostic run" is a known open slot). Any change to these
   paths can be verified by import/fallback tests and *mocked* unit tests (patching the openai
   client to assert request shape + response parsing), but **not** by a live call. This
   constraint weighs on all three options equally, and argues for the option with the most
   inspectable, smallest-surface result.

## Options

**A. Shed (recommended).** Replace the six sites with the native `openai` SDK (reference:
`llm._openai_adapter`; add a native embeddings helper and a native structured-output call to
replace `LLMTextCompletionProgram`). Remove all four llama-index packages.
- ✅ Permanently eliminates all 5 CVEs and a heavy transitive tree (dozens of deps).
- ✅ Aligns with the D19 native-provider direction already in `llm.py`.
- ⚠️ Rewrites optional LLM paths that can't be key-verified here; `LLMTextCompletionProgram`→
  native structured output is the one non-trivial rewrite.

**B. Upgrade.** Bump the four packages to `llama-index-core` ≥0.13.
- ✅ Fixes the CVEs, keeps the abstraction.
- ⚠️ 0.10→0.12/0.13 was a major API restructure (import paths like `llama_index.core.program`
  likely moved); keeps a heavy dep the architecture is moving *away* from; also un-key-verifiable.

**C. Isolate (de-base).** Move all four packages into an opt-in `requirements-llm.txt`
(same pattern as T2.5's NLI split). Base drops them.
- ✅ Zero code change (the paths already fail-safe to fallback when the import is absent);
  clears the 5 CVEs from the **base** pip-audit surface immediately.
- ⚠️ Does not *eliminate* the CVEs — they persist for anyone installing the LLM extra.

## Recommendation

**Shed, phased**, because llama-index here is thin legacy scaffolding over OpenAI that the
D19 layer already replaced natively, and shed is the only option that *eliminates* (not
defers) the CVEs while removing a heavy dependency:

1. **Now, zero-risk:** drop the DEAD `llama-index-vector-stores-qdrant` (imported nowhere).
2. **Sites 1, 4, 5** (thin `OpenAI().complete(prompt)`): route through the existing
   `llm._openai_adapter` / a small shared helper. 1:1 replacements.
3. **Site 3** (embeddings): native `client.embeddings.create(...)`.
4. **Site 2** (`LLMTextCompletionProgram`): native structured output (JSON/function-calling)
   parsed into the existing `ExtractedAsset` Pydantic model — the one non-trivial rewrite.
5. Remove all four llama-index pins; regenerate both locks; the base pip-audit ignore list
   drops the five llama-index CVEs.
- **Verification** (given no key): import-time + fallback-path tests stay green in the harness;
  add mocked unit tests that patch the openai client to prove each rewritten call's request
  shape and response parsing. Live-key verification remains the standing open slot.

If the priority is *clearing the base CVE surface today with zero behavioral risk*, **Isolate**
is the pragmatic interim and Shed can follow — but Shed is the correct end state.
