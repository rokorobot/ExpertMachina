# v1.7.0 — The Compliance & Obligation Workbench — Build Contract

> Scoped 2026-07-03 from the proposal recorded at the v1.6 closeout.
> Input briefs: PROJECT_STATE.md, docs/DECISIONS.md (through D31),
> docs/roadmap.md, docs/workbench-catalog.md,
> docs/workbench-skill-registry.md (workbench 9), and the gate records
> in docs/customer-ops-workbench-v1.6.md. This is the build contract
> for the SECOND governed operations workbench in the ratified catalog
> sequence (Customer Operations → **Compliance & Obligation** →
> Procurement Document Intelligence), built on the v1.6 template:
> scoping → promote selected skill contracts from the registry →
> realistic corpus → corpus proof BEFORE any runner → runner →
> proposal valve → THE COMMERCIAL VERDICT. Gate records are appended
> here as each workstream is accepted.

## The milestone in one sentence

The Compliance & Obligation Workbench extracts explicit obligations
from governed documents, detects missing evidence, outdated policies,
undocumented owners, and conflicting compliance statements — every
finding document-grounded through the four existing doors, re-entering
knowledge only through the valve — and proves for the first time that
skills compose ACROSS the valve: a second-generation finding citing an
ACCEPTED DERIVED fact, its derivation visible at the human gate.

## The sensitivity posture (the cardinal sin)

**Compliance overclaiming is the cardinal sin.** No finding may imply
verification of PRACTICE the doors cannot evidence — the workbench
knows what the company **documents**, never what it **does**.
Document-grounded, or refused.

- Every finding statement is about documents: "the approved corpus
  states / does not state / cannot answer" — never about conduct.
- Language rulings (per-finding, contract-backed): "documented",
  "undocumented", "the governed corpus cannot answer", "no approved
  document names", "declared review interval overdue" — **never**
  "compliant", "non-compliant", "violation", "breach", "verified",
  "the company complies / fails to comply", or any phrase that reads
  as an audit conclusion about practice.
- The [OE]-gated skills (policy-vs-practice, operational-records
  verification) are exactly the practice claims this workbench must
  refuse; their refusals name the unminted decision.
- The audit-readiness pack is [assist] and separates
  **known / missing / contradictory / unverified** explicitly — the
  "unverified" bucket IS the posture: what the documents claim but the
  doors cannot evidence is declared unverified, never asserted.

## The opening question (evidence-first, per tradition)

> A compliance owner reads the diagnosis as the audit-facing reader
> and must be able to act on every finding without trusting the
> agent: which obligation excerpt was extracted verbatim, which
> requirement has no approved covering evidence, which policy is
> overdue by its own declared review interval, which obligation no
> approved document assigns an owner, and which two governed
> statements contradict — each answerable from cited governed records
> alone, and none implying anything about practice. If any finding
> reads as an audit conclusion, it is not a finding.

## Scoping rulings (proposed for ratification)

1. **THE ACTIVE SIX** — promoted from the registry (workbench 9),
   consolidations declared openly:

   | ACTIVE skill (v1.7) | Base pattern | Finding kind · evidence basis |
   |---|---|---|
   | `extract_compliance_obligations` | extract-candidates | COMPLIANCE_OBLIGATION · EXCERPT_BACKED (verbatim must/shall excerpt + declared source type) |
   | `detect_missing_evidence` | missing-evidence | MISSING_COMPLIANCE_EVIDENCE · REFUSAL_BACKED (requirement excerpt + reproducible refusal) |
   | `identify_outdated_policies` | outdated-guidance | OUTDATED_POLICY · REVISION_BACKED (supersession chain OR the document's OWN declared review interval overdue — never age alone) |
   | `detect_undocumented_obligation_owner` | missing-evidence (owner axis) | UNDOCUMENTED_OBLIGATION_OWNER · REFUSAL_BACKED (obligation excerpt + refused owner question) |
   | `detect_conflicting_compliance_statements` | contradictory-guidance | CONFLICTING_COMPLIANCE_STATEMENTS · CONFLICT_BACKED |
   | `prepare_audit_readiness_pack` | assist | [assist] — known/missing/contradictory/unverified clearly separated; never a finding |

   Consolidations (recorded in the registry drafts at promotion):
   - `extract_compliance_obligations` consolidates the registry's four
     `extract_obligations_from_*` drafts (contracts / policies /
     certifications / regulatory documents) into ONE contract with a
     **declared `source_type` field** on every finding, and folds
     `classify_obligation_type` in as a declared `obligation_type`
     field (reporting, renewal, certification, notification, SLA,
     audit, approval, training, retention, security, payment,
     delivery — assigned only when the excerpt names it; else
     UNCLASSIFIED, honestly).
   - `detect_missing_evidence` is ONE skill with **declared
     requirement classes**, absorbing the
     `detect_sla_evidence_gaps` / `detect_reporting_obligation_gaps` /
     `detect_notification_obligation_gaps` draft variants.
   - Consolidated drafts carry `ratified_path` pointing at the
     consolidating contract plus a `consolidated_into` note — the
     draft≠ratified sweep asserts the mapping explicitly, so
     consolidation never reads as silent promotion.

2. **THE SPLIT RULING (`detect_undocumented_obligation_owner`)**:
   detecting that **no approved document names an owner** for an
   explicit obligation is document-grounded and [now] — absence of a
   documented owner is a finding, never a fact. **Assigning, routing,
   or tracking** owners stays [ES]-gated in
   `identify_obligation_owner_gaps` (unpromoted). The proposed action
   on such a finding is "document the owner" — the workbench never
   nominates one.

3. **THE GATED LIST, named per contract** (tags are gates; the runner
   refuses each at runtime, naming the unminted decision):
   - **[OE]**: `compare_policy_vs_practice`,
     `verify_obligations_against_operational_records`,
     `detect_missed_operational_reporting_events`,
     `detect_practice_evidence_from_logs_tickets_payments` — every
     practice-verification claim.
   - **[PMD]**: `detect_unapproved_compliance_guidance`; the
     agent-side visibility of `generate_obligation_approval_queue`.
   - **[ES]**: owner assignment/routing
     (`identify_obligation_owner_gaps` beyond detection, per ruling 2).

4. **THE DELIBERATE DEFERRAL (not gated): the deadline family** —
   `track_explicit_deadlines`, `track_recurrence_rules`,
   `identify_upcoming_obligations_30_60_90`,
   `detect_certification_expiry_risk`. Document-side legal ([now] by
   tag) but they invite the register/calendar temptation — a
   persistent obligations calendar is the two-state-machine drift D1
   names, and due-date stewardship is [ES] territory. Deferred to
   after the Exception Stewardship scoping, deliberately; the drafts
   stay SEQUENCED.

5. **THE DISTINCTIVE v1.7 PROOF — composition ACROSS the valve, live
   for the first time (a named WS3 stage: THE COMPOSITION PROOF).**
   Registry rule 6 has been law-on-paper since v1.6; v1.7 executes it:
   extracted obligations are accepted as DERIVED facts by a human →
   the package is recompiled (accepted findings flow to agents
   automatically, D30 class-travels) → a **second**
   `detect_missing_evidence` run consumes the ACCEPTED obligation
   facts (never pending proposals) → its findings cite DERIVED
   evidence, flagged as DERIVED citations = second-generation
   synthesis visible at the gate (the v1.4 WS1 derivation-depth
   machinery, exercised commercially for the first time).

6. **THE ENGINEERING RULING — `workbench/common.py`.** The v1.6
   runner plumbing (contract loading + ACTIVE gating, door setup,
   proposal writing, frontmatter claims, determinism discipline) is
   extracted into `workbench/common.py` — stdlib-only, under the same
   Guard 5-swept root; Guard 5 Part 5 sweeps it automatically the
   moment it lands (zero guard edits, re-proven at the WS2 gate). The
   catalog's first reuse moment: the customer-ops runner is refactored
   onto it with its suite green and zero assertion edits.

7. **Determinism and the review-interval clock.** The
   review-interval condition (`identify_outdated_policies`) compares a
   document's OWN declared interval + last-review date against a
   **declared `as_of` date parameter** recorded in the finding — never
   wall-clock. Byte-identical re-runs hold at a pinned `as_of`.

8. **THE CORPUS (~12 knowledge-only documents, D27 held — domain
   scope `compliance`).** No operational records, no logs, no tickets,
   no filings. Plants for all five finding skills **including the
   covered controls — refusal-first cuts both ways**:
   - explicit must/shall extraction triggers across declared source
     types (contract, policy, certification, regulatory);
   - a requirement whose approved covering evidence is genuinely
     absent AND a requirement whose evidence document EXISTS (the
     covered control: no finding);
   - a policy overdue by its own declared review interval (the new
     plant species) AND a policy whose declared review is current;
   - an obligation no approved document assigns an owner AND an
     obligation whose owner IS named in an approved document (the
     covered control: no finding);
   - a same-subject, cross-document compliance contradiction
     (NLI-detectable, the v1.6 evidence rules inherited wholesale:
     same-subject, cross-document, governance vocabulary excluded
     from subject tokens);
   - the EXECUTIVE clearance sentinel;
   - the plant map (`CORPUS.md`) OUTSIDE the scanned folder — the
     non-runtime oracle, per the v1.6 protected boundary.

9. **The v1.6 evidence rules inherited wholesale** for
   `detect_conflicting_compliance_statements`: same-subject (≥ 2
   shared subject tokens beyond timeframe vocabulary), cross-document,
   governance vocabulary excluded from subject tokens. Declared in the
   contract, never silent.

10. **No new law, re-affirmed (not re-litigated): no D32 and no
    seventh guard family.** Guard 5 sweeps every new module under
    `workbench/` the moment it lands — `common.py` and the new bundle
    alike, with zero guard edits as the WS2 evidence. The three named
    decisions (Operational Evidence Realm, Exception Stewardship,
    Pipeline Metadata Door) stay named, not minted; dependent skills
    stay gated per contract, refused at runtime.

11. **Zero schema. Zero backend change. Zero new endpoints, MCP tools,
    or UI areas.** The D24 snapshot holds at **28 tables / 305
    columns**, asserted at the milestone gate. The Operations area
    already carries the second workbench with zero new surface.

12. **THE COMMERCIAL VERDICT is user-ratified, not automated**: the
    user reads the rendered diagnosis as the **audit-facing reader**
    — is every finding useful, bounded, document-grounded, and free
    of practice overclaim? The milestone closes on that verdict or it
    does not close.

13. **The honest slots carry**: the ONE real-model diagnostic run
    (code-complete, one provider key away — the customer-ops corpus
    remains its natural vehicle; the audit-readiness pack is this
    workbench's vehicle) and the v1.2.0 live-SharePoint-tenant scan.

## Schema changes

**None.** Behavior and fixture data only. D24 at 28/305 at every gate.

## Module map (planned)

| Location | Role |
|---|---|
| `workbench/common.py` | the extracted runner plumbing (ruling 6) — stdlib-only, doors only, Guard 5-swept |
| `workbench/compliance_obligation/workbench.yaml` | the manifest: canonical #9, domain scope `compliance`, binding expectations, the six-skill list, the gated list |
| `workbench/compliance_obligation/skills/*.yaml` | the six ratified contracts (13-field shape) |
| `workbench/compliance_obligation/runner.py` | the reference consumer on `common.py` — doors only; contracts drive runtime; gated skills refused live |
| `workbench/compliance_obligation/corpus/` (+ `CORPUS.md` outside the scanned folder) | the 12-document plant corpus + the non-runtime oracle (no `corpus_seed/`: the outdated-policy plant is the review-interval species — the supersession species was proven at v1.6, so no revision choreography here) |
| `backend/test_compliance_corpus.py` (WS1) | THE CORPUS PROOF — before any runner |
| `backend/test_compliance_workbench.py` (WS2) | THE DIAGNOSIS PROOF |
| `backend/test_compliance_acceptance.py` (WS3) | THE MILESTONE GATE + THE COMPOSITION PROOF |

No changes under `backend/app/`. CI grows 44 → 47 suites.

## Workstreams

### WS0 — The rulings (no code)

This document ratified: the ACTIVE SIX with their consolidations, the
split ruling, the gated list, the deadline deferral, the composition
proof as a named WS3 stage, the common.py extraction, the sensitivity
posture, the corpus shape.

**Gate:** user ratification of the rulings above; all 44 pre-existing
suites green with zero assertion edits; D24 at 28/305.

### WS1 — The contracts + the corpus + THE CORPUS PROOF

The six contracts promoted into
`workbench/compliance_obligation/skills/` (registry drafts gain
`ratified_path` / `consolidated_into`); the manifest; the ~12-document
corpus with its plants and covered controls; `CORPUS.md` outside the
scanned folder. Then `backend/test_compliance_corpus.py` — the plants
verifiable through EM's own machinery BEFORE any runner exists:

1. real-NLI detection of the compliance contradiction in
   gate-evidence mode (`EM_CORPUS_PROOF_NLI=1`; bare CI skips loudly
   with declared fixture conflicts);
2. the review-interval condition derivable from the document's own
   declared interval + the pinned `as_of` (never age alone);
3. reproducible `consume()` refusals for the missing-evidence and
   undocumented-owner questions AND the covered-control answers
   (refusing correctly before answering correctly — both directions);
4. the draft≠ratified sweep over all 361 generated contracts: exactly
   the ratified set ACTIVE, consolidation mapping asserted.

**Gate:** the corpus-proof evidence recorded; user ratifies the corpus
as realistic and the six contracts as the declared product.

### WS2 — `common.py` + the runner + THE DIAGNOSIS PROOF

`workbench/common.py` extracted (customer-ops runner refactored onto
it, its suite green, zero assertion edits); the compliance runner —
doors only, contracts driving runtime (frames/questions read from the
YAMLs), refusal-first, evidence-driven kinding, the declared evidence
rules. `backend/test_compliance_workbench.py`: every plant found and
correctly kinded; covered controls produce NO finding; a gated skill
([OE]/[PMD]/[ES]) refused live naming the unminted decision; every
citation names a consumed packaged asset; no practice-overclaim
vocabulary in any finding byte (the posture sweep); byte-identical
re-runs at pinned `as_of`; the EXECUTIVE sentinel absent; writes
confined to `/08_proposals` + the assist pack in
`/07_agent_workspaces`; Guard 5 sweeps both new modules with zero
guard edits.

**Gate:** the diagnosis-proof evidence recorded; user ratifies the
runner as the accepted Compliance & Obligation workbench.

### WS3 — THE MILESTONE GATE + THE COMPOSITION PROOF + THE COMMERCIAL VERDICT

`backend/test_compliance_acceptance.py`: the full commercial loop —
corpus in through the real pipeline (classification into `compliance`,
human approval) → INTERNAL package + real AGENT binding → the
diagnosis through the doors → every candidate held DERIVED under a
global permissive Tier-1 policy + a live approve-everything Tier-2
engine → a human accepts findings → DERIVED facts with verified
provenance → **THE COMPOSITION PROOF** (ruling 5): package recompiled
with the accepted obligation facts → the second `detect_missing_evidence`
run consumes ACCEPTED facts only → a second-generation finding citing
DERIVED evidence, the derivation flagged at the gate → the vault
before/after (marked non-canonical DERIVED notes; untouchable floor
intact) → the in-browser before/after on a seeded throwaway DB →
closing lines: the ledger alone proves no agent wrote canonical
facts; the EXECUTIVE sentinel absent from every byte; D24 at exactly
28/305; all six guard families green; the D25 sweep clean.

**Plus THE COMMERCIAL VERDICT (ruling 12):** the user reads the
diagnosis as the audit-facing reader.

**Plus the honest slots** attempted/carried per ruling 13.

## Explicitly out of scope (refused deliberately, not omitted)

- Policy-vs-practice and every operational-records verification —
  behind the Operational Evidence Realm.
- Unapproved-guidance detection and the agent-side approval queue —
  behind the Pipeline Metadata Door.
- Owner assignment/routing/tracking — behind Exception Stewardship.
- The deadline family — deferred to after the [ES] scoping (ruling 4).
- The Procurement workbench (third), the Executive Briefing stages.
- Any MCP surface growth (frozen at 9 tools), any schema change.
- D23 — deferred a seventh time.

## Standing boundaries

The protected boundary carries verbatim from v1.6: generated draft
contract ≠ executable skill; ratified workbench contract ≠ global
permission; corpus plant map ≠ runtime evidence; runner output ≠
canonical knowledge. Every gate re-runs the D25 custody sweep and
closes on the D24 snapshot. Guard 5 sweeps the new modules; Guard 6
holds the vault seam. EM never launches the workbench (D22). Language
rulings per the sensitivity posture and the standing D29/D30
vocabulary.

## Gate records

### WS0 — SCOPING RATIFICATION: PASSED (2026-07-03, user-ratified)

**"I ratify docs/compliance-workbench-v1.7.md as the build contract
for the Compliance & Obligation Workbench."** D24 verified at 28/305
on the untouched tree (all 44 suites standing as released — WS0 is
rulings only, zero code).

Accepted at the gate, verbatim in substance:

- **The milestone claim**: extraction, missing evidence, outdated
  policies, undocumented owners, conflicting statements — every
  finding through the valve; and the FIRST proof of composition
  across the valve: an accepted DERIVED obligation fact becomes the
  governed input for a later missing-evidence finding, derivation
  depth visible at the gate.
- **The sensitivity posture**: compliance overclaiming is the
  cardinal sin. The workbench may say what approved documents state,
  omit, contradict, supersede, or cannot answer. It may not imply
  that ExpertMachina verified company practice, operational
  execution, logs, tickets, payments, filings, pipelines, calendars,
  or external systems without a ratified evidence door.
  Document-grounded, or refused.
- **THE ACTIVE SIX** as proposed (ruling 1), with the consolidation
  rulings: four extraction drafts → one `extract_compliance_obligations`
  with declared `source_type`; `classify_obligation_type` folded in as
  `obligation_type` with UNCLASSIFIED when the excerpt does not
  support classification; the evidence-gap variants → one
  `detect_missing_evidence` with declared requirement classes;
  consolidated drafts must carry `ratified_path` AND
  `consolidated_into` — consolidation never becomes silent promotion.
- **The owner split**: detecting that no approved document names an
  owner is allowed now; assigning, routing, tracking, or maintaining
  owners remains [ES]-gated.
- **The gated list** ([OE]/[PMD]/[ES]) as proposed (ruling 3).
- **The deadline deferral**: the four deadline-family drafts remain
  SEQUENCED, deliberately — "deadline extraction may be document-side
  in theory, but persistent deadline stewardship risks creating a
  second operational state machine before [ES] is scoped."
- **THE COMPOSITION PROOF** as a named WS3 stage (ruling 5).
- **The engineering ruling**: `workbench/common.py` may extract the
  reusable v1.6 plumbing, stdlib-only, Guard 5-swept; Customer
  Operations may be refactored onto it provided its suite stays green
  with zero assertion edits and no global skill activation is
  introduced.
- **The corpus direction** (ruling 8) including covered controls and
  `CORPUS.md` outside the scanned folder as the non-runtime oracle.
- **The WS1 requirements**, before any runner exists: real-NLI
  detection of the compliance contradiction in gate-evidence mode;
  review-interval overdue logic from the document's own declared
  interval plus pinned `as_of`; `consume()` refusals for absent
  evidence and undocumented-owner questions; `consume()` answers for
  covered controls; explicit obligation extraction only; draft
  contracts do not masquerade as ratified contracts.
- **Standing boundaries reaffirmed**: no D32; no seventh guard
  family; zero schema change; D24 at 28/305; zero backend change in
  WS0; no new MCP tools, endpoints, or UI areas; D23 deferred again;
  the three named decisions remain unminted; and the protected
  boundary verbatim (generated draft contract ≠ executable skill;
  ratified workbench contract ≠ global permission; corpus plant map ≠
  runtime evidence; runner output ≠ canonical knowledge).

**Verdict: v1.7.0 WS0 PASSED.** WS1 may proceed: the six contracts,
the compliance corpus, CORPUS.md, and
`backend/test_compliance_corpus.py`.

### WS1 — The Contracts, the Corpus, and THE CORPUS PROOF: evidence recorded, gate pending ratification

Deliverables: the ratified bundle
(`workbench/compliance_obligation/workbench.yaml` + the six contracts
in `skills/*.yaml`), the 12-document corpus (`corpus/`) with
`CORPUS.md` outside the scanned folder (the non-runtime oracle), the
registry/generator consolidation machinery, and
`backend/test_compliance_corpus.py` (added to CI — now 45 suites).
**Both execution modes green; every WS0-ratified WS1 requirement
proven BEFORE any runner exists.**

**The seven parts, all green:**

1. **The corpus through the real pipeline**: 12 documents scanned via
   a PRIMARY-lane connector, 50 assets human-approved, every plant
   sentence present in governed content.
2. **Explicit obligation extraction only**: the declared
   explicit-marker rule (must / shall / is required to) selects 16
   explicit statements including every P1 plant; the P7 implied
   sentence ("encouraged to archive...") carries no marker and never
   enters the obligation set; the declared source_type (filename
   rules) and obligation_type (excerpt keyword rules, UNCLASSIFIED
   when unsupported) reproduce the plant-map expectations across all
   four source types.
3. **The review-interval condition** (the new plant species): from
   the documents' OWN declared convention ("must be reviewed every N
   months, and its last completed review was dated YYYY-MM-DD") at
   the pinned declared `as_of` 2026-06-01 — the acceptable-use policy
   is OVERDUE (due 2025-05-02) and the access-control policy is
   CURRENT (due 2026-11-10). Never age alone, never wall-clock.
4. **Real-NLI detection (`EM_CORPUS_PROOF_NLI=1`, the gate-evidence
   run)**: the scan judges ALL 1225 pairs and detects P5 — "retained
   for ten years" × "destroyed three years", same subject,
   cross-document — as a governed **DIRECT_CONTRADICTION at
   confidence 0.995** (31 conflicts total; the long tail is the known
   v1.6 signal-to-noise territory, handled by the WS2 declared
   evidence rules). The compile gate blocks on the unreviewed
   contradictions and opens only by governed human dismissal; the
   INTERNAL package compiles with the EXECUTIVE sentinel
   (`EM-EXEC-SENTINEL-7C2R`) absent from every byte. In bare CI the
   detection assertion skips loudly and a declared fixture conflict
   drives the gate flow (the v1.6 honesty pattern).
5. **Refusal preconditions, deterministically**: the gap questions
   are uncovered (max retrieval overlaps 4/3 < 6) while the covered
   controls are covered (14/9 ≥ 6) — the requirement excerpts
   retrievable, the gaps real.
6. **consume() refuses AND answers, reproducibly**: both gap
   questions (the training completion summary; the breach-notification
   owner) refused identically across runs with zero citations; both
   covered controls (the incident-response test report exists; the
   Compliance Officer IS named) answered WITH citations — refusing
   correctly before answering correctly, **in both directions** (the
   covered-control half is new at v1.7: refusal-first cuts both
   ways). CI runs the declared deterministic contract-follower at the
   D19 seam; the real-model refusal remains the open honest slot.
7. **Draft ≠ ratified + the consolidation ruling**: 364 drafts swept
   (361 at v1.6 + the three v1.7-minted skill ids); exactly 11 ACTIVE
   (5 customer-ops + 6 compliance), each with a resolving
   ratified_path; the 8 CONSOLIDATED drafts each carry
   `consolidated_into` + a ratified_path resolving to the
   consolidating contract; the four deadline-family drafts stay
   SEQUENCED with the deferral named; both bundle manifests agree
   with their ratified skill files; the suite's question frames are
   asserted to be the ratified contracts' frames verbatim.

**Honesty discipline recorded at the gate:**

- **The pair-cap raise in gate-evidence mode** (declared in the
  suite): the embedding pre-filter ranks by `ingestion.get_embedding`,
  which is a mock under the CI key — the first gate run showed it
  silently dropping the plant pair. Gate-evidence mode raises the
  declared `EM_CONFLICT_MAX_PAIRS` knob so EVERY pair is judged (D12:
  no silent caps deciding plant fate). Deployment posture unchanged.
- **One corpus wording tuning** (the v1.6 P1 precedent): the finance
  guideline's section heading was renamed ("Contract records" →
  "Disposal of customer agreements") because identical glued headings
  gave both assets identical extracted names, which the metadata
  classifier correctly reads as TEMPORAL_SUPERSESSION (same policy,
  two documents). The rename makes the plant classify as the
  DIRECT_CONTRADICTION it is; business meaning unchanged; the suite
  now asserts the classification explicitly.
- **One recorded assertion edit** (driven by the ratified promotion):
  `test_customer_ops_corpus.py` Part 7 now scopes its
  exactly-5-ACTIVE assertion to the customer-ops draft folder — the
  global count is 11 by this milestone's ratified promotion. The v1.6
  suite is otherwise untouched and green.
- **No `corpus_seed/`, by design**: the outdated-policy plant is the
  review-interval species; the supersession species was proven at
  v1.6, so no revision choreography is repeated here.
- **The sensitivity posture held in the proof itself**: every
  assertion is about what the governed corpus states or cannot answer
  — nothing in the suite verifies practice.

**Regression at the gate**: the v1.6 customer-ops corpus, workbench,
and acceptance suites green; Guard 5 swept the new bundle with zero
guard edits (Part 5: 3 workbench modules); the D24 guard green at
exactly 28 tables / 305 columns.

**THE GATE (per WS0): user ratification of the corpus as realistic
and the six contracts as the declared product is now requested.**

### WS2 — `common.py` + the Runner + THE DIAGNOSIS PROOF: RATIFIED (2026-07-07, user-ratified)

Commits: part 1 `ab4bfae` (merged as main `2adf29a`, PR #13 — the
`workbench/common.py` extraction, the catalog's first reuse moment:
customer-ops runner refactored onto it, its suites green with zero
assertion edits, Guard 5 sweeping the shared module with zero guard
edits; the reuse mechanic recorded: relative imports keep intra-
workbench reuse inside the swept root); part 2 (PR #14 — the
compliance runner + `backend/test_compliance_workbench.py`, the 47th
suite, passed first run; full harness 67/67).

**The gate ruling (user, verbatim):**

> v1.7 WS2 Part 2 — Compliance & Obligation Runner: RATIFIED
>
> The diagnosis-proof evidence is accepted.
>
> The Compliance & Obligation runner is ratified as the accepted WS2
> workbench because it:
>
> - reads and honors the six skill contracts at runtime rather than
>   hardcoding mirrored rules;
> - requires a declared as_of clock and refuses undeclared time
>   sampling;
> - extracts only explicit obligation markers and correctly ignores
>   implied/non-marker text;
> - produces deterministic, byte-identical diagnosis output;
> - keeps all generated proposals DERIVED under the live permissive
>   policy;
> - refuses gated operational evidence comparison as required;
> - preserves forbidden-vocabulary and sentinel safety;
> - passes THE DIAGNOSIS PROOF and the full harness.
>
> Gate ruling: WS2 Part 2 is accepted.

The recorded evidence: 5 workbench modules inside the Guard 5 doors
(zero guard edits); 20 per-finding proposals across all five kinds,
byte-identical re-runs at the pinned `as_of 2026-06-01`; P1 ×6
obligations extracted verbatim and typed by the declared rules across
all four source types; P7 never extracted; P2/P3 (due 2025-05-02)/
P4/P5 found and correctly kinded; P2c/P3c/P4c covered controls silent
with declared reasons; the cross-topic noise pair deferred by the
inherited same-subject rule; no-as_of, gated-[OE] (naming the
Operational Evidence Realm), and SEQUENCED-contract refusals proven
live; the EXECUTIVE sentinel and the manifest's forbidden vocabulary
absent from every written byte; writes confined to /08_proposals +
the four-section audit-readiness pack in /07_agent_workspaces; the
return path holding all 20 proposals as DERIVED candidates with
provenance verified against the governed binding.

*(This ruling necessarily accepts the WS1 corpus as the declared
product — the ratified diagnosis runs over it; the WS1 gate's
requested corpus ratification closes with this record rather than
silently.)*

**Verdict: v1.7.0 WS2 PASSED.** WS3 may proceed: THE MILESTONE GATE +
THE COMPOSITION PROOF + THE COMMERCIAL VERDICT.
