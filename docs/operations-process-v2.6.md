# v2.6.0 — Operations / Process Improvement (catalog #8) — Build Contract

> Opened 2026-11-03. Catalog #8 was built and gated in the AgenticTeam
> repo (PR #31, build record: docs/operations-process-workbench.md) and
> merged pending its commercial verdict. This contract brings it through
> the v1.6 template the rest of the catalog follows before that verdict.

## Why (the finding that opened this milestone)

The verdict run put `corpus_operations/` through the REAL governed
pipeline for the first time (scan → extraction → human approval →
empkg-v1.1 package → real AGENT binding → real stdio MCP door → the
runner's real consume() under D33, Anthropic claude-opus-5-5). **The
runner found 2 of ~7 planted defects.** None of the bundle's three
suites had ever run the governed pipeline: the acceptance suite feeds
the runner hand-written paraphrases of the documents through a fake
package door, and the corpus suite checks the raw file bytes ("No
governed pipeline … is needed").

## WS0 — RATIFIED (2026-11-03, user)

1. **WS1 — the pipeline corpus proof:** ingest `corpus_operations/`
   through the real pipeline and assert every CORPUS.md plant survives
   extraction as a packaged fact the contracts can see. No runner change.
2. **WS2 — the runner on real facts:** fix what WS1 and the rerun expose
   against the ingested facts; the fake-door suites stay as fast checks.
3. **WS3 — the gate:** a real-pipeline acceptance suite (findings, the
   valve, human acceptance, vault, 28/305), a D33 real-model run, then
   **THE COMMERCIAL VERDICT** — the owner reads the diagnosis as the
   operations / process owner.

## Gate records

### WS1 — the pipeline corpus proof: evidence recorded, gate pending ratification

**Root cause of the lost plants:** in CI mode the extractor
(`app/extraction.py` `extract_via_rules`) splits on sentence ends and
keeps a sentence only if it carries an extraction keyword (must, shall,
policy, step, then, process, review, role, owner, system, …) and is ≥ 30
characters. Four plants carried none and never became facts:
- P2 SOP side "A production change may be approved by the team lead alone";
- P2 policy side "No production change may be deployed on the authority
  of a single approver";
- P3 "The onboarding buddy programme is complete after the two-week period";
- P4 the Remote Access SOP's own identity line "… Standard Operating
  Procedure OPS-RA-04." (so the supersession could not resolve its target).
`Step N.` labels also split off below 30 characters.

**Corpus amendments (meaning preserved, 5 files, 21 lines):** each lost
plant sentence gains a natural keyword ("In this step, …", "Under this
policy, …", "… programme step is complete …"); the four SOP identity
lines end "… for the <name> process."; `Step N.` → `Step N:`. Non-plant
sentences were deliberately NOT given keywords (e.g. "the change ticket
is closed"), so no unplanted handoff finding is minted.

**`backend/test_operations_pipeline_corpus.py` (the 94th suite):** the
corpus through the real pipeline (58 human-approved facts, 6 documents,
an empkg-v1.1 package), then P1–P6 asserted on the PACKAGED facts with
the contracts' own markers: P1 the 2-vs-5-day contradiction
cross-document; P2 CAB + single-approver (policy) vs team-lead-alone
(SOP); P3 both terminal steps with a completion marker and no handoff
marker; P4 the supersession notice naming OPS-RA-04 + the superseded
document's own code and rule; P5 the three review cadences, interval
and last-review date in the same document **as separate facts**
(pinned for WS2); P6 ordered steps (onboarding 1–4, access 1–3).
Passes on the amended corpus; fails on the original at P2. The three
existing operations suites stay green.

**Rerun on the amended corpus (same verdict-run path):** 7 proposals,
all four finding kinds (contradiction, SOP-vs-policy, missing handoff,
outdated). **What WS2 must fix, now concrete:**
1. **Duplicates from fragment facts:** chunk overlap yields a truncated
   copy of some sentences (assets 48/50 — the buddy-programme handoff
   twice); the superseded Remote Access SOP yields two findings (one per
   supersession sentence). One finding per (skill, document, plant).
2. **Overdue-by-own-interval: 0 findings** — the change-management
   policy (12 months from 2024-01-15) and SOP (6 months from 2024-02-01)
   are overdue at as_of 2026-07-09, but the runner looks for interval and
   date inside one fact; WS1 pins they are separate facts. Join by
   document.

**Caveat (honest):** CI extraction is the rule-based extractor; LLM-mode
extraction (a real OpenAI key) is not exercised in this sandbox.

**The gate:** ratify the corpus amendments and the WS1 proof; WS2 then
begins.
