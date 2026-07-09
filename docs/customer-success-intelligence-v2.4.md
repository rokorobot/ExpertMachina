# v2.4 — Customer Success Intelligence — Build Contract

> Scoped 2026-07-09 (the v2.4 pre-scope + WS0 session, post-v2.3.0
> release; baseline main `7c2203b`, tag `v2.3.0` = `5fd448f`, harness
> 86/86, D24 at 28/305, route manifest 88, MCP 9, seven guard
> families, sweep 34/58, [OE]/[PMD] unminted). Input briefs:
> PROJECT_STATE.md, DECISIONS.md (through D32),
> docs/workbench-skill-registry.md (workbench 6 — split from Customer
> Support at the v1.6 WS0 gate), docs/workbench-catalog.md, and the
> gate records of v1.6/v2.1/v2.2/v2.3 (the base patterns + the
> register/calendar substrate). The SIXTH commercial workbench and
> the THIRD consumer of the earned substrate. The pre-scope followed
> the ratified six-question template (what is it / who reads it / may
> say / must never say / cardinal sin / undeniable proof). **WS0
> RATIFIED by the user on 2026-07-09** — the rulings below stand as
> written; gate records are appended per workstream.

## The milestone identity (the spine, carried verbatim into every gate)

**v2.4 is document-governed customer-success intelligence, not a
churn, health, CRM, or retention-prediction engine.** *"v2.4
diagnoses per-customer term deviation, obligation exposure, and
coverage gaps from approved documents, register facts, and
declared-clock windows — never the state, behavior, or future of the
customer relationship itself."*

**The ratified name: Customer Success Intelligence** — NOT "Customer
Success / Retention." "Retention" promises churn probability,
likelihood, health, sentiment, activity, renewal odds — all
forbidden. The reader is the CS lead / Head of Customer Success
preparing for a QBR or renewal; the workbench stays document-bound.
Commercial positioning: *a governed customer-success preparation
workbench.* The distinctive angle no shipped workbench carries: **the
per-customer axis** — v1.6 asked "do our customer-facing documents
agree with each other?"; v2.4 asks "for THIS named customer, what did
we promise, what deviates from standard, what falls due, and what has
no playbook?"

## Ruling 1 — The boundary (registry #6 ratified as binding, renamed)

INCLUDED: per-customer deviation from governed standard terms
(clause-cited both ways); renewal/communication/reporting obligations
with verbatim dates and declared-clock windows; coverage gaps,
refusal-backed (missing playbook / QBR procedure / escalation
coverage / delivery process behind a cited promise);
CS-policy-vs-contract contradictions; unbacked relationship-state
assumptions found IN documents ("healthy adoption" asserted with no
governed evidence — surfaced as an unsupported claim, never
adjudicated). EXCLUDED (all [OE]): actual usage, activity, tickets,
NPS, CRM state, sentiment, adoption, churn probability, revenue at
risk, renewal likelihood, customer ranking or prioritization of any
kind (ranking implies health knowledge), anything person-level about
customer contacts.

**THE HEALTH-SENTENCE DISTINCTION** (the invoice-sentence lineage): a
clause, playbook sentence, account-plan statement, or
customer-success assumption is document evidence, in-scope. Usage
records, CRM exports, tickets, NPS, health-score tables, activity
feeds, and relationship-state metrics are [OE]. **A document
containing a health claim does not authorize the workbench to know
customer health** — it may identify the claim as an unsupported
assumption or a forbidden [OE] relationship-state assertion, but it
may not use it to infer the relationship's state.

## Ruling 2 — THE ACTIVE FOUR + one assist brief (consolidation map; sweep numbers pinned at WS1)

| ACTIVE (v2.4) | Consolidates (registry #6 drafts) | Kind · basis |
|---|---|---|
| `detect_customer_term_deviation` [now] | drafts 5 (as a declared baseline axis) | CUSTOMER_TERM_DEVIATION · EXCERPT/CONFLICT-backed; customer clause vs governed standard-terms clause, cited both ways BY id; declared baseline classes (standard_terms, cs_policy) |
| `detect_customer_renewal_obligations` [now] | drafts 1 + 2 | CUSTOMER_RENEWAL_OBLIGATION · EXCERPT_BACKED; THE THIRD HARVEST — v2.1 register clauses (`renewal`, `sla`, `notification_obligation`, `reporting_obligation`) BY id; windows on the v2.2 declared clock; no re-extraction |
| `detect_customer_coverage_gap` [now] | drafts 3 + 7 + 8 + 14 | CUSTOMER_COVERAGE_GAP · REFUSAL_BACKED; declared coverage classes (playbook, qbr_procedure, escalation, delivery_process, service_commitment_evidence) |
| `detect_unbacked_customer_health_assumption` [now] | draft 15 (renamed singular) | UNBACKED_HEALTH_ASSUMPTION · EXCERPT_BACKED; surfaces the claim verbatim + its missing evidence; NEVER asserts whether the claim is true |
| `prepare_customer_success_review_brief` [assist, synth] | drafts 6 + 10 + 12 + 13 + 16 | the QBR/renewal preparation brief — evidence, deviations, windows, gaps, assumptions, exclusions as declared sections; narrative [synth]-declared; never a finding, never enters knowledge |

**One cross-workbench consolidation (the v2.3 precedent, ratified):**
draft 9 `extract_customer_communication_obligations` → CONSOLIDATED
into the v2.1 register (`extract_contract_clauses` —
`notification_obligation`/`reporting_obligation` classes; the
shared-engine principle: nothing re-extracts). Draft 4
`detect_customer_obligations_without_owner` stays **SEQUENCED/[ES]**
per Ruling 4a. Draft 11 `detect_outdated_cs_documentation` →
CONSOLIDATED into the shipped v1.7 `identify_outdated_policies`
(domain-scoped at runtime — the v2.3 cross-workbench mechanism,
unchanged). The six Future-[OE] drafts stay FUTURE.

## Ruling 3 — THE BASELINE DOCTRINE: no standard baseline, no deviation diagnosis

Deviation is computable ONLY against a **governed, approved
standard-terms document**, cited by asset id. No approved standard in
scope → `detect_customer_term_deviation` REFUSES with a declared skip
naming the missing baseline. The workbench never infers "standard"
from industry practice, averages, prior customers, or common sense —
that would be the customer-success version of invented money.
Doctrine line, carried into the contract bytes: **"No standard
baseline, no deviation diagnosis."**

**THE CARDINAL SIN — THE IMPUTED HEALTH**: presenting the state,
behavior, sentiment, satisfaction, adoption, churn risk, renewal
likelihood, or future of a customer relationship as a governed fact
from documents. **Its twin — THE HEALTH-SENTENCE DISTINCTION**
(Ruling 1): evidence is what documents SAY; the relationship's state
is [OE]. Both swept on every written byte (forbidden
relationship-state vocabulary — "healthy," "at risk," "likely to
churn/renew," "satisfied," "declining," "high adoption," and kin —
permitted ONLY inside verbatim-quoted document claims framed as
unsupported assumptions).

## Ruling 4 — Forbidden inputs (exhaustive)

Usage/activity records · CRM exports · tickets · NPS/survey results ·
health-score tables AS DATA · activity feeds · revenue/ARR-at-risk
records · any relationship-state metric — plus the standing base
(ungoverned sources; candidate/held content; other skills' pending
findings; wall-clock time). **THE HEALTH-SCORE PLANT (adversarial)**:
an account plan or CS memo carrying a customer health-score table and
adoption claims, ingested through the pipeline as an approved
document, must NOT become telemetry — the workbench may surface its
claims only as unsupported assumptions
(`detect_unbacked_customer_health_assumption`) or declare the
[OE] boundary; it must never mint a relationship-state finding from
it. Approved-document status does not launder telemetry into
relationship knowledge.

### Ruling 4a — The [ES] slice (deferred)

`detect_customer_obligations_without_owner` is **SEQUENCED/[ES]** for
v2.4. It may become ACTIVE at a later session ONLY if it consumes
existing governed v2.0 OWNER_ASSIGNED stewardship decisions strictly
read-only and introduces no new ownership, staffing, assignment, or
execution state. The first version stays cleaner without it.

## Ruling 5 — Allowed / disallowed outputs

ALLOWED: CUSTOMER_TERM_DEVIATION / CUSTOMER_RENEWAL_OBLIGATION /
CUSTOMER_COVERAGE_GAP / UNBACKED_HEALTH_ASSUMPTION findings through
the unchanged valve; the 07-confined review brief. Every diagnosis
exposes evidence (by id, DERIVED as DERIVED), windows (declared clock
verbatim), assumptions, exclusions, uncertainty. DISALLOWED: any
assertion of relationship state, health, satisfaction, usage,
adoption, sentiment, churn/renewal likelihood; customer ranking or
scoring; renewal *likelihood* (only renewal *obligations and
windows*); invented dates or terms; anything [OE]/[PMD];
schedules/reminders/tracking (v2.2 carries — decisions persist,
existence never does).

## Ruling 6 — The named proofs

- **THE CUSTOM TERMS PROOF** (the distinctive positive proof): the
  customer whose contract deviates from approved standard terms is
  FOUND, deviation cited by clause id against the standard's clause
  id; **the conforming customer stays silent**. Silence on the
  compliant case is what makes it a diagnosis, not a report generator.
- **THE UNREAD CUSTOMER** (the distinctive negative proof, UNOPENED
  LEDGER lineage): the full diagnosis completes citing only approved
  documents + register facts BY ID + declared-clock windows, and no
  operational customer-data door exists — proven three ways:
  structurally (no door), adversarially (THE HEALTH-SCORE PLANT
  declined or surfaced only as an unsupported assumption, [OE]
  named), and on the bytes (THE IMPUTED HEALTH sweep).
- **THE THIRD HARVEST PROOF**: renewal/SLA/communication-obligation
  findings cite v2.1 register clauses BY governed asset id through
  the REAL chain (finding → DERIVED register → PRIMARY contract) —
  nothing re-extracted, exactly two governed copies.
- **THE COMPUTED RENEWAL WINDOW PROOF**: every window computed from
  declared clocks over verbatim dates; deletion loses nothing; the
  declared clock reproduces every byte (the v2.2 inheritance).
- **THE IMPUTED HEALTH SWEEP**: every byte of every output swept for
  relationship-state assertions — "healthy," "at risk," "likely to
  churn," "satisfied," "declining," "high adoption," and kin exist
  ONLY inside verbatim-quoted document claims framed as unsupported
  assumptions; nothing else survives.
- **THE COMMERCIAL VERDICT** (user-ratified, never automated) — the
  CS reader (CS lead / Head of Customer Success): *"As a CS lead
  preparing for a QBR or renewal, would you put this governed
  customer-success diagnosis in front of your team — knowing it shows
  only cited customer-specific terms, deviations from approved
  standards, renewal/communication windows, and coverage gaps, while
  refusing to tell you whether the customer is healthy, satisfied,
  active, likely to renew, or at risk unless an operational evidence
  realm is deliberately minted?"*

## Ruling 7 — The corpus decision (ruling-10 shape, gaps to be proven at WS1)

REUSE FIRST: the shipped corpora carry customer-facing material (the
v1.6 customer-operations corpus: SLAs, support procedures, promise
material; the v2.1/v2.3 contract material + the register substrate).
**Pre-registered likely gaps (to be PROVEN at WS1 before any plant
lands)**: (a) no governed **standard-terms document** (the
load-bearing baseline — almost certainly absent); (b) no
**named-customer contract that deviates** from it; (c) no
**named-customer contract that conforms** (the silence half of THE
CUSTOM TERMS PROOF); (d) CS playbook/QBR/escalation material with a
**deliberate coverage gap**; (e) **THE HEALTH-SCORE PLANT**'s
adversarial account plan (it cannot exist by accident). If proven,
plants land in a **`corpus_customer_success/` extension folder** (the
ratified v2.2/v2.3 pattern — shipped doc-count assertions
byte-untouched), plant map appended, user-ratified at the mid-WS1
stop.

## Ruling 8 — Zero new surface, zero new law (standalone, substrate consumer)

New bundle `workbench/customer_success_intelligence/` (a **STANDALONE
workbench** — new reader, new per-customer axis, new cardinal sin,
distinct commercial verdict; it HARVESTS v2.1/v2.2 substrate but is
not an extension) on `common.py` (zero shared-module edits, the
seventh reuse target). No D33, no eighth guard, no new decision
kinds, no new constitutional realm, route manifest 88, MCP 9, D24
28/305, Guard 7 untouched, [OE]/[PMD] refused live and named.

## The gate checklist (each claim testable)

deviation cited both ways BY id against the governed standard ·
refuses when no approved baseline exists ("no standard baseline, no
deviation diagnosis") · conforming customer produces ZERO findings ·
cites register clauses BY ID, nothing re-extracted · windows on
declared clocks, reproducible from source facts · CANNOT read
usage/CRM/tickets/NPS/health scores as data (structural + adversarial
+ byte-level) · CANNOT assert relationship state, health,
satisfaction, or churn/renewal likelihood · CANNOT rank or score
customers · relationship-state vocabulary survives only inside
verbatim-quoted unsupported claims · every diagnosis exposes
evidence/windows/assumptions/exclusions/uncertainty · zero new
routes/tables/tools/guards/law · [OE]/[PMD] refused live · Guard 7
untouched · shipped suites byte-untouched · the valve holds; one
human acceptance stays DERIVED.

## The WS sequence + the Opus handoff note

- **WS0** — these rulings. **RATIFIED 2026-07-09.**
- **WS1** (Opus per routing) — the five contracts + registry #6
  promotion (4 ACTIVE + 1 assist / the consolidations incl. the
  cross-workbench pair, drafts with `consolidated_into` + resolving
  `ratified_path`; sweep constants move from 34/58 — pinned at WS1) +
  the corpus-gap stop (state the gaps, user ratifies the plants) +
  THE PRECONDITION PROOF (87th suite) BEFORE any runner.
- **WS2** — the runner on `common.py` + THE DIAGNOSIS PROOF (88th).
- **WS3** — THE MILESTONE GATE (89th) + the six named proofs +
  browser before/after (the Workbench Catalog panel gains its
  Customer Success card via ONE `WORKBENCH_CATALOG_INFO` row —
  presentation only) + THE COMMERCIAL VERDICT.
- **The v2.2 five + v2.3 seven engineering lessons apply verbatim**
  (recorded in the memory playbook): extension maps for any constant
  a shipped suite derives dynamically; gates refuse first, parameter
  refusals second and targeted-only; the three
  operational-evidence fingerprint exclusions; a verbatim quote
  containing forbidden vocabulary is NOT the sin — sweep against full
  cited source content, never truncated excerpts; extension-corpus
  folders keep shipped assertions byte-untouched.

## Standing boundaries

Generated draft ≠ executable skill; ratified contract ≠ global
permission; plant map ≠ runtime evidence; runner output ≠ canonical
knowledge. Every gate re-runs the D25 sweep and closes on the D24
snapshot. Guard 5 sweeps the new bundle the moment it exists; Guard 6
holds the vault seam; Guard 7 holds stewardship. EM never launches
the workbench (D22). Language per Rulings 1/3/5 and D29/D30.
