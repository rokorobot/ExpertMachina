# v1.6.0 — Workbench Catalog v1: the Customer Operations Workbench — Build Contract

> Scoped and ratified 2026-07-03. Input briefs: PROJECT_STATE.md,
> docs/DECISIONS.md (through D31), docs/roadmap.md, and the gate
> records in docs/em-vault-v1.5.md and docs/diagnostic-workbench-v1.4.md
> — including the user-ratified v1.6 opening carried from the v1.5
> closeout: "Workbench Catalog v1: choose the first commercial
> Operations Workbench without breaking the knowledge/transaction
> boundary." Companion artifact ratified at the same session:
> **docs/workbench-catalog.md** (the catalog structure, the commercial
> sequence, the boundary audit, and the three named-but-not-minted
> future decisions). This is the build contract: workstreams, gates,
> and the boundaries that hold. Gate records are appended here as each
> workstream is accepted.

## The milestone in one sentence

The first commercial Operations Workbench diagnoses a company's
customer-operations knowledge — contradictory support policies,
outdated guidance, SLA coverage gaps, process inconsistencies — with
every finding evidence-backed from governed records through the four
existing doors, re-entering knowledge only through the valve, and
producing a diagnosis a customer-operations manager would recognize as
worth acting on.

## The product argument this milestone proves

> ExpertMachina can now turn enterprise knowledge into agent-readable
> operational views without ever letting those views become truth —
> because ExpertMachina improves operations by reasoning over what the
> company officially knows, not by pretending every business record is
> already governed knowledge.

v1.4 proved the loop's mechanics once. v1.6 must prove **commercial
value**: a realistic corpus, a diagnosis a business reader recognizes,
findings a human accepts, and the before/after visible in the vault
and the Operations area.

## The opening question (evidence-first, per tradition)

> A customer-operations manager reads the diagnosis and must be able
> to act on every finding without trusting the agent: which governed
> assets contradict each other, which guidance tracks a superseded
> revision, which declared question the corpus cannot answer, and
> which procedure steps disagree — each answerable from cited governed
> records alone. If any finding rests on "the agent said so," it is
> not a finding.

## Scoping rulings (settled at the session, user-ratified)

1. **No D32.** The catalog is convention, not constitution. Every
   erosion path a catalog opens is already walled: per-workbench
   auto-accept → D29's lane-sentinel clause (register supersession
   only, never configuration); a WorkbenchRegistry table → D1/D24
   (28/305 asserted at every gate); backend imports → Guard 5 Part 5
   (auto-sweeps every module under `workbench/`); laundering →
   D29/D30/D31. A workbench-species ruling would be the register's
   first law over code outside EM's boundary — unenforceable beyond
   what Guard 5 already sweeps, the false assurance D14 forbids.
   **What would earn a D32, named now:** the moment any governed
   surface must DECIDE differently based on workbench or skill
   identity — per-workbench acceptance policies, workbench-scoped
   clearances, a governed workbench registry, or **skill-aware
   acceptance** (the gate validating a proposal against its claimed
   skill contract). None is built or wanted.
2. **No seventh guard family.** A catalog workbench adds no new seam:
   it consumes the same four doors and returns through the same
   valve. The seam map — workbench imports: Guard 5 Part 5; agent
   output entering knowledge: the lane sentinel (D29); the class of
   what is accepted: the source_class writer allowlist (D30);
   rendered material re-submitted: Guard 6 (D31); schema: the D24
   snapshot; secrets: the D25 sweep. WS0's evidence for this ruling:
   the new workbench module is swept by Guard 5 **with zero guard
   edits** the moment it lands.
3. **A workbench is a bundle of declared skills — the skill-contract
   convention** (recorded in `vault/00_system/agent-contract.md` and
   docs/workbench-catalog.md): each catalog workbench ships as
   `workbench/<name>/workbench.yaml` (name, domain scope as a D27
   prefix, binding expectations, skill list) plus `skills/*.yaml` —
   one skill contract per subtask, each with the ten-field shape
   (name, purpose, allowed inputs, forbidden inputs, governed
   evidence rules, allowed finding kinds, output format, human
   approval requirement, audit expectations, failure/refusal
   conditions). ONE root, deliberately: `workbench/` is the
   Guard 5-swept root; a second `/workbenches/` root would sit
   outside the sweep until a guard amendment. Proposal frontmatter
   carries the workbench + skill (+ version) claims alongside the
   D30 claims (agent principal, binding, package hash, cited
   assets) — recorded verbatim, verified where governed records
   permit, **never obeyed** (the v1.4 WS1 unrecognized-claims
   behavior). Zero backend change. Skill contracts are convention,
   not constitution: EM cannot enforce behavior on code it does not
   execute (D22); the contracts govern the reference runner and
   travel as claims the human gate can always see.
4. **Four finding kinds, one refused.** *(AMENDED at the WS0 gate:
   the ACTIVE set is now the five customer-outcome skills — see the
   WS0 gate record. The kinds below survive as named base patterns.)*
   Every finding carries a
   declared kind, a business statement, a proposed action, and a
   declared evidence basis — cited governed asset ids/hashes,
   conflict relationship ids, or a reproducible refusal. No evidence,
   no finding.

   | Kind | Evidence basis (declared per finding) |
   |---|---|
   | `CONTRADICTORY_GUIDANCE` | CONFLICT_BACKED — a governed CONFLICTS_WITH relationship (DIRECT_CONTRADICTION) + both asset ids |
   | `OUTDATED_GUIDANCE` | REVISION_BACKED — TEMPORAL_SUPERSESSION classification + the revision chain |
   | `COVERAGE_GAP` | REFUSAL_BACKED — a declared frame question + the packaged answering contract's INSUFFICIENT EVIDENCE refusal + nearest partial evidence |
   | `PROCESS_INCONSISTENCY` | SYNTHESIS_INFERRED — cited asset ids + quoted passages, honestly declared as model-inferred |

   The four kinds map 1:1 onto the workbench's four skills:
   `detect_contradictory_guidance`, `detect_outdated_guidance`,
   `detect_coverage_gap`, `detect_process_inconsistency` — every
   finding names the skill that produced it.

   **Refused fifth kind**: unclassified/uncovered-knowledge findings —
   UNCLASSIFIED and NOT_COVERED are EM's own computed inbox exception
   kinds (D26); a workbench re-reporting EM's governance hygiene
   blurs the realms. Also refused: any kind requiring
   transactional/ticket evidence (ruling 7).
5. **The detection architecture is the honesty core.** The workbench
   splits into a **deterministic evidence walk** (detect and collect:
   domain subgraph → conflicts + classifications → revision histories
   → frame questions through package `consume()`) and the
   **injectable synthesis seam** (narrate findings, propose actions,
   infer PROCESS_INCONSISTENCY). In CI the seam is a deterministic
   narrator — the CI gate finds the planted issues because the
   EVIDENCE is deterministic, not because a fake was rigged to know
   the answers. PROCESS_INCONSISTENCY is the one kind that genuinely
   requires a model: CI exercises its plumbing through the seam; its
   real proof belongs to the real-model slot — declared honestly,
   never simulated as proven.
6. **One proposal document per finding** (a change from the pilot's
   single document): 1:1 candidate mapping at the human gate,
   per-finding `cited_assets` frontmatter, and per-finding acceptance
   granularity. If per-finding shape still extracts poorly, backend
   proposal-aware extraction tuning is an **explicit escalated
   decision point** (the v1.4 WS3 deferral), never a silent tweak.
7. **The corpus is knowledge-only by design** (D27 held): support
   policies, refund rules, SLA documents, escalation procedures,
   macros, training docs, customer-facing guidance. **No tickets, no
   customer records, no transaction exports.** "Review this week's
   tickets and cluster complaints" is a refused demo question in
   v1.6, deliberately; ticket-stream intelligence is Customer Ops v2,
   behind the Operational Evidence decision (workbench-catalog.md).
8. **The commercial verdict is user-ratified, not automated.** CI
   proves what CI can honestly prove (plants found, citations
   resolving, zero fabricated evidence, determinism, clearance). The
   claim "a customer-operations manager would recognize this as worth
   acting on" is ratified by the user reading the rendered diagnosis
   as the business reader at the milestone gate — the milestone
   closes on that verdict or it does not close.
9. **The catalog enters the record** (docs/workbench-catalog.md):
   Layer 1 as already-shipped platform primitives; the commercial
   sequence **Customer Operations → Compliance & Obligation →
   Procurement Document Intelligence** (superseding the v1.5-closeout
   ordering, by user ruling); the per-workbench D27 boundary audit;
   the three named-but-not-minted decisions — the Operational
   Evidence Realm, Exception Stewardship ("the exception never
   becomes a row; the human decisions about it do"), and the Pipeline
   Metadata Door (Executive Briefing two-stage).
10. **Impact estimates are synthesis content**: declared
    SYNTHESIS_INFERRED inside the finding, never a governed number.
    Drafted replies/emails are consumption outputs, not proposals —
    out of v1.6's claim.
11. **The real-model honest slot closes here if a key exists**: one
    real-model run of this workbench on this corpus, evidence
    appended to this milestone's gate record AND the open v1.4.0 WS4
    slot. Pending honestly otherwise. The SharePoint slot carries
    unchanged.
12. **Language rulings**: "finding", "diagnosis", "evidence basis",
    "declared kind", "proposed action", "held for the human gate",
    "accepted as DERIVED" — never "the agent found a violation", "the
    workbench fixed", "auto-detected fact", "the agent's knowledge",
    or any phrase implying a finding is true before a human rules.

## Key discovered facts (grounding, pre-contract)

- **Three of the four kinds are deterministically detectable from
  door evidence**: conflict edges and classifications
  (`get_conflicts`, `get_domain_subgraph`), revision chains
  (`get_revision_history`), and refusals (`consume()` under the
  packaged answering contract) are all deterministic reads at AGENT
  clearance. The conflict classifier already distinguishes
  DIRECT_CONTRADICTION from TEMPORAL_SUPERSESSION — the
  CONTRADICTORY/OUTDATED split maps onto existing governed
  classifications.
- **The manifest convention costs zero backend surface**:
  proposals.py already records unrecognized frontmatter claims
  verbatim and never obeys them (v1.4 WS1 gate evidence).
- **Guard 5 Part 5 auto-activates per module** under `workbench/`
  (proven at v1.4 WS3: 2 modules swept unprompted) — the no-new-guard
  ruling's structural basis.
- **The v1.4 observed extraction behavior** (shaped multi-finding
  text shredding into ~10 candidates) motivates per-finding proposal
  documents; the deferral of proposal-aware extraction tuning stands
  unless escalated (ruling 6).
- **Accepted findings flow to agents automatically** (D30
  class-travels) — no door growth is needed for anything this
  milestone ships; the Pipeline Metadata Door is the Executive
  Briefing's future need, not this one.

## Schema changes

**None.** The milestone adds behavior and fixture data only. The D24
snapshot holds at **28 tables / 305 columns**, asserted at the
milestone gate.

## Module map (planned)

| Location | Role |
|---|---|
| `workbench/customer_operations/workbench.yaml` | the workbench manifest: name, domain scope (`customer_operations`), binding expectations, skill list |
| `workbench/customer_operations/skills/*.yaml` | the four skill contracts (one per finding kind), each in the ten-field shape |
| `workbench/customer_operations/runner.py` | the reference consumer — sibling of the pilot, doors only (Guard 5-swept): the deterministic evidence walk + the injectable narrator seam, honoring the skill contracts; writes one content-hash-named proposal per finding to `/08_proposals` |
| `workbench/customer_operations/corpus/` | the realistic knowledge-only corpus (~15 documents) with its plants, committed as fixture data; consumed by suites, demos, and the real-model run alike |
| `vault/00_system/agent-contract.md` | grows the workbench catalog manifest convention (WS0) — declared name, domain scope, finding kind, evidence basis; claims recorded verbatim, never obeyed |
| `docs/workbench-catalog.md` | the catalog artifact (ratified at scoping) |
| `backend/test_customer_ops_workbench.py` (WS2) | the diagnosis proof |
| `backend/test_customer_ops_acceptance.py` (WS3) | THE MILESTONE GATE |

No changes under `backend/app/`. Zero new endpoints, zero new MCP
tools, zero UI area changes (the Operations area already carries the
catalog: bound agents and proposals appear there with zero new
surface).

## Workstreams

### WS0 — The rulings + the no-new-seam proof

The two refusals recorded (rulings 1–2), the catalog artifact in the
record (ruling 9), the manifest convention added to
`vault/00_system/agent-contract.md` (ruling 3), zero schema.

**Gate:** the convention text ratified; all 41 pre-existing suites
green with zero assertion edits; D24 at 28/305; the no-new-guard
ruling's basis re-affirmed (Guard 5's workbench door sweep and
adversarial self-proofs standing).

### WS1 — The corpus + the skill contracts

`workbench/customer_operations/corpus/`: ~15 realistic documents —
refund policy with a genuine revision history (v1: 30 days → approved
v2: 14 days), a support FAQ still stating 30 days (the contradiction
plant), Tier-1 SLA present with the Tier-2 SLA genuinely absent (the
coverage-gap plant), an escalation procedure and an incident-handling
guide with misaligned steps (the process plant, real-model territory),
an EXECUTIVE-clearance refund-authority document (the clearance
sentinel), and healthy documents around them. Plus the workbench
bundle declared: `workbench.yaml` (name, domain scope, binding
expectations, skill list) and the four skill contracts in
`skills/*.yaml` — each in the ten-field shape, carrying the kind's
evidence basis, the coverage question set (for `detect_coverage_gap`),
output format, and failure/refusal conditions (no evidence → no
finding, structurally per contract).

**Gate (the corpus + contracts proof):** the plants are independently
verifiable through EM's own machinery before any workbench code reads
them — the conflict scan sees the contradiction, the temporal
classification fires, `consume()` reproducibly refuses the Tier-2 SLA
question; the user ratifies the corpus as realistic (the
business-reader check applied to the input first) and the four skill
contracts as the declared product.

### WS2 — The Customer Operations Workbench

`workbench/customer_operations/runner.py`: doors only; the
deterministic evidence walk; the injectable narrator seam; the runner
honors the WS1 skill contracts (allowed inputs, evidence rules,
refusal conditions, output format); per-finding proposals carrying the
workbench + skill (+ version) claims in frontmatter; writes confined
to `/08_proposals`.

**Gate (the diagnosis proof, `test_customer_ops_workbench.py`):**
every deterministically-detectable plant found and correctly kinded;
every finding names the skill that produced it and conforms to that
skill's declared output format and evidence basis; a skill's refusal
condition proven live (a coverage question the corpus CAN answer
produces no COVERAGE_GAP finding); every citation verified against
what the agent actually consumed; zero fabricated evidence;
byte-identical re-runs; the EXECUTIVE sentinel absent from every
proposal byte with the exclusion declared; Guard 5 sweeps the module
with zero guard edits.

### WS3 — THE MILESTONE GATE

`test_customer_ops_acceptance.py`: the full commercial loop — corpus
in through the real pipeline (classification into
`customer_operations`, human approval) → package compiled and bound to
a real AGENT principal → the workbench diagnoses through the doors →
per-finding proposals held under a global permissive policy + a live
approve-everything Tier-2 engine (the valve live) → a human accepts
findings → DERIVED facts with verified provenance → the vault
re-render shows the marked DERIVED notes → in-browser before/after on
a seeded throwaway DB → closing lines: the ledger alone proves no
agent wrote canonical facts; D24 at 28/305; all six guard families
green; the D25 sweep clean.

**Plus THE COMMERCIAL VERDICT (ruling 8):** the user reads the
rendered diagnosis as the business reader and rules whether a
customer-operations manager would recognize it as worth acting on.

**Plus the honest slots:** the real-model run attempted (ruling 11) —
recorded here and closing the v1.4.0 WS4 slot if a key exists, pending
honestly otherwise.

## Explicitly out of scope (refused deliberately, not omitted)

- **Ticket-stream intelligence** (recurring complaints, SLA breach
  detection from cases, customer-risk scoring, reply drafting over
  live tickets) — Customer Ops v2, behind the Operational Evidence
  decision.
- **The Compliance and Procurement workbenches** — second and third
  in the ratified sequence, each its own scoping session.
- **The Executive Briefing** — two-stage per the catalog; its
  decision-queue stage requires the Pipeline Metadata Door ruling.
- **Exception Stewardship** — named future decision; existence
  computed, human decisions persisted; not needed for this loop (the
  proposal lane already carries acceptance workflow).
- **Any MCP surface growth** — the 9-tool surface stays frozen.
- **Proposal-aware extraction tuning** — unless escalated per ruling 6.
- **D23** (binding lifecycle) — deferred a sixth time.

## Standing boundaries

The three disciplines hold (no orchestration creep, no leaderboard
disease, no rewriting history). Every gate re-runs the D25 custody
sweep (the corpus and diagnosis are new surfaces) and closes on the
D24 snapshot. Guard 5 sweeps the new workbench module and Guard 6
holds the vault seam it writes into. EM never launches the workbench
(D22): the runner is a reference consumer executed outside the
boundary. Language rulings per ruling 12 and the standing D29/D30
vocabulary.

## Gate records

### WS0 — The Catalog, the Registry, and the Two Refusals: ACCEPTED (2026-07-03, user-ratified)

Commits: scoping `b53d551`, WS0 `f825a9c`, skill registry `8694cda`.
**Gate verdict: PASSED.**

**Gate wording (user-ratified at acceptance):** v1.6 WS0 establishes
the workbench catalog and skill registry without adding new
constitutional law, without adding a new guard family, and without
changing schema.

Accepted WS0 rulings:

- `docs/workbench-catalog.md` holds the commercial map.
- `docs/workbench-skill-registry.md` holds the agent-skill contracts.
- The catalog and registry are strategy and contract artifacts, not
  canonical facts and not new executable authority.
- The ten-field skill contract convention is operative for future
  workbenches.
- Boundary tags are real gates: ACTIVE may be implemented now;
  SEQUENCED is drafted but waits for its workbench scope; PLATFORM
  maps to already-shipped machinery; FUTURE is roadmap only; [OE],
  [PMD], and [ES] refuse execution until their decisions are minted.
- Customer Operations v1.6 is correctly limited to the
  document-governed slice.
- Ticket-stream intelligence remains out of scope behind the future
  Operational Evidence decision.
- Pipeline metadata and exception stewardship remain named future
  decisions, not silently built.
- D24 remains intact at 28 / 305.

**THE REGISTRY-SCOPE AMENDMENT (user-ratified at the gate):** WS0 does
not only define the Customer Operations skills. WS0 establishes the
complete Workbench Skill Registry covering the full commercial
catalog. Customer Operations v1.6 is only the first executable subset;
WS1 implements the first executable skill bundle **from the
already-defined registry**. The four technical skills are not "the
product" — they are the first proof that ExpertMachina workbenches are
governed bundles of exact agent skills.

**THE ACTIVE-SET AMENDMENT (user-ratified at the gate):** the four
abstract knowledge-quality skills are replaced as the v1.6 ACTIVE set
by five customer-outcome skills built from the same D27-clean base
patterns — "do not lead with abstract knowledge-quality skills; lead
with customer-outcome skills built from the same safe patterns":

| ACTIVE skill (v1.6) | Base pattern | Finding kind · evidence basis |
|---|---|---|
| `detect_customer_promise_conflict` | contradictory-guidance | CUSTOMER_PROMISE_CONFLICT · CONFLICT_BACKED |
| `detect_missing_support_playbook` | coverage-gap | MISSING_SUPPORT_PLAYBOOK · REFUSAL_BACKED |
| `detect_outdated_customer_guidance` | outdated-guidance | OUTDATED_CUSTOMER_GUIDANCE · REVISION_BACKED |
| `detect_sla_obligation_gap` | extract-candidates + missing-evidence | SLA_OBLIGATION_GAP · REFUSAL_BACKED (obligation excerpt cited) |
| `prepare_customer_policy_brief` | assist | [assist] — evidence-backed topic brief, never a finding |

The four original skills become **named base patterns** in the
registry; `detect_process_inconsistency` is deferred (drafted, not
ACTIVE) until a corpus carries enough procedural material to prove it
honestly. The real-model honest slot re-attaches to finding narration
and the policy brief. The commercial wedge: *"ExpertMachina finds
where customer promises, support procedures, SLA obligations, and
customer-facing guidance do not line up — before customers are
harmed."*

**THE CATALOG NORMALIZATION (user-ratified at the gate):** the
catalog is normalized 14 → **16 workbenches**: Customer Support and
Customer Success / Retention are split, and Contract Intelligence is
added as its own workbench (the shared contract-analysis engine
beneath Procurement, Compliance, and Sales). The v1.6 milestone name
"Customer Operations Workbench" corresponds to #5 (Customer Support)
in the 16-list.

WS1 may proceed: the customer-operations corpus with plants for the
five ACTIVE skills, and the five skill contracts as the
`workbench/customer_operations/` bundle.

### WS1 (part 1) — Business-Reader Ratification: PASSED (2026-07-03, user-ratified)

Commits: bundle + corpus `fcfa1d3`; the generated draft-contract tree
`f928ebd`. **Verdict: PASSED. WS1 may proceed to the corpus-proof
harness, then WS2 runner.**

**Gate wording (user-ratified at acceptance):**

The Customer Operations corpus and the five ACTIVE Customer
Operations skill contracts are ratified as suitable for WS1 proof
construction.

The corpus is accepted as a realistic controlled test bundle: ordinary
healthy documents, known contradiction plants, outdated guidance, and
revision-chain evidence sufficient to prove governed behavior. The
plant map in CORPUS.md is accepted as the **non-runtime oracle** for
test expectations.

The five ratified Customer Operations contracts are accepted as
**binding for v1.6 execution work**. Their behavior must remain
refusal-first, evidence-bound, provenance-aware, and unable to invent
missing facts. They may extract, compare, flag, summarize, or refuse —
but they must not silently repair source truth, overwrite canonical
records, or treat generated drafts as approved knowledge.

**The generated 361-contract tree is accepted as draft inventory
scaffolding only — not a runtime permission grant.** The YAML files in
docs/skill-contracts/ are valid catalog-level draft contracts, not
execution-authoritative contracts: deterministic generated scaffolding
allowed to exist, while each workbench still needs its own scoping
gate before any skill becomes binding runtime behavior. Each
non-Customer-Ops contract remains draft until promoted during its own
workbench scoping session.

**The protected boundary (user-stated, standing for the whole
catalog):**

> generated draft contract ≠ executable skill
> ratified workbench contract ≠ global permission
> corpus plant map ≠ runtime evidence
> runner output ≠ canonical knowledge

**Required WS1 proof (part 2 — the corpus-proof harness):**

1. The conflict scan must detect the promise conflict.
2. The scan must detect the outdated FAQ condition.
3. The revision choreography must produce the superseded chain.
4. `consume()` must reproducibly refuse the playbook question when
   evidence is not approved or safe.
5. `consume()` must reproducibly refuse the reporting question when
   required evidence is missing, conflicting, or not promotable.
6. No generated draft contract may be treated as ratified unless it
   has an explicit `ratified_path` or a workbench-scoped promotion
   record.

The next implementation must prove that Customer Operations can
**refuse correctly before it answers correctly**.

### WS1 (part 2) — The Corpus-Proof Harness: PASSED (evidence recorded)

Suite: `backend/test_customer_ops_corpus.py` (added to CI — now 42
suites). Seven parts, all green in both modes; the required six proven:

1. **Promise conflict detected.** The real NLI conflict scan
   (`EM_CORPUS_PROOF_NLI=1`) detects P1 — the enterprise 24h guarantee
   (`sales-enterprise-brochure.md`) × the 48h first-response target
   (`support-escalation-procedure.md`) — as a governed
   DIRECT_CONTRADICTION at confidence **0.972**.
2. **Outdated-FAQ condition detected.** The same scan detects P3 — the
   FAQ's 30-day refund window × the revision-2 policy's 14-day window
   — as DIRECT_CONTRADICTION at confidence **0.980**.
3. **Superseded chain produced.** The revision choreography (rev-1
   content scanned + approved → rev-2 content rescanned as a CHANGED
   source → candidate revision → human-approved) leaves refund-policy
   rev-1 ARCHIVED with `superseded_by_revision_id` → rev-2 APPROVED;
   the asset serves 14 days; rev-1 retains its 30-day content.
4. **Playbook question refused, reproducibly.** `consume()` returns
   INSUFFICIENT EVIDENCE with zero citations for the enterprise
   refund-exception playbook question (P2), identically across runs.
5. **Reporting question refused, reproducibly.** `consume()` refuses
   the monthly-service-report procedure question (P4) the same way;
   both refusals precede a *covered* control question that is answered
   with a citation — refusing correctly before answering correctly.
6. **Draft ≠ ratified enforced.** All 361 generated draft contracts
   swept: exactly 5 carry `status: ACTIVE`, each with a `ratified_path`
   that resolves to a file under `workbench/customer_operations/skills/`;
   the manifest's skill list and the ratified files agree.

**Honesty discipline recorded at the gate:**
- The conflict scan runs the **real mDeBERTa NLI engine** in the
  gate-evidence run (P1 0.972, P3 0.980, both DIRECT_CONTRADICTION,
  28 conflicts total surfaced from the corpus). In bare CI (NLI model
  unavailable), Part 3 **skips loudly** and declared fixture conflicts
  drive the gate flow — the detection claim rests on the recorded
  real-NLI run, never on a fixture pretending to be detection.
- `consume()` refusal in CI runs through a **declared deterministic
  contract-follower** injected at the D19 `llm.generate` seam (answers
  only when one governed evidence item shares ≥ 6 retrieval tokens with
  the question; else the packaged refusal verbatim). The refusal
  **precondition** — no covering evidence exists in the package — is
  asserted deterministically by retrieval-overlap regardless of mode
  (max overlaps 4/5 < 6 for the gap questions; 8 for the control). The
  real-model refusal remains the open honest slot.
- The EXECUTIVE refund-authority sentinel (`EM-EXEC-SENTINEL-9Q4Z`) is
  absent from every byte of the INTERNAL package (the D9 clearance
  proof, on package bytes).

Corpus wording note: the P1 sentences were tuned to a governed,
NLI-detectable contradiction (a 24h guarantee vs a 48h target — a real
commitment conflict), because two bare SLA numbers ("within 24h" /
"within 48h") are not a logical contradiction to NLI. The plant map in
CORPUS.md is updated to match; the business meaning is unchanged.

**WS1 is complete (parts 1 + 2). WS2 may proceed: the runner
(`workbench/customer_operations/runner.py`) — doors only, honoring the
five ratified skill contracts, emitting one proposal per finding.**

### WS1 — FINAL VERDICT: PASSED (2026-07-03, user-ratified)

Commits: part-1 record `38f2fff`, part-2 harness `ce7a270`. **"I ratify
WS1 Customer Operations as complete."** All part-2 evidence accepted as
recorded above (both execution modes green; P1 @ 0.972 and P3 @ 0.980;
the supersession chain; both refusals before the covered control; the
361-draft sweep with exactly 5 ACTIVE; the EXECUTIVE sentinel absent).

**Accepted correction (user-ratified):** the P1 wording adjustment is
valid — "within 24h" versus "within 48h" is not necessarily a logical
contradiction, because a 24-hour response also satisfies a 48-hour
window. The revised wording — "guaranteed within 24 hours" versus
"first-response target is 48 hours" — is a better business
contradiction and a better NLI plant.

**Boundary conditions preserved (user-restated):** generated draft
contract ≠ executable skill; ratified workbench contract ≠ global
permission; corpus plant map ≠ runtime evidence; runner output ≠
canonical knowledge; local real-NLI evidence is gate evidence while CI
honest-skip mode is harness-shape and deterministic-flow evidence; the
deterministic contract-follower at the D19 seam is acceptable for
proving contract behavior, but the real-model refusal remains an
explicit future evidence slot.

**Customer Operations v1.6 may proceed to WS2 runner construction.**

### WS2 — The Runner (the diagnosis proof): evidence recorded, gate pending ratification

Deliverables: `workbench/customer_operations/runner.py` (the reference
consumer — doors only, Guard 5-swept the moment it landed with zero
guard edits) + `backend/test_customer_ops_workbench.py` (added to CI —
now 43 suites). Two ratified-contract frame questions were tuned to be
refusal-clean against the answering threshold (business meaning
unchanged; recorded here as the WS2 contract edit).

**The runner honors the contracts, not just carries them:**
- question frames are READ FROM `skills/*.yaml` at run time, never
  hardcoded;
- a skill whose contract is not `status: ACTIVE` is refused at run
  time — tags are gates, proven live (a SEQUENCED-flipped contract
  aborted the run);
- refusal-first: a covered question produces NO finding (proven live
  with a control question injected into a copy of the contract frame —
  skipped with the reason "the corpus answers it");
- kinding is evidence-driven: a DIRECT_CONTRADICTION pair becomes
  OUTDATED_CUSTOMER_GUIDANCE only when one side's ARCHIVED revision
  content matches the opposing guidance more closely than its current
  revision (the REVISION_BACKED rule over `get_revision_history`,
  which exposes revision content); otherwise CUSTOMER_PROMISE_CONFLICT.

**The diagnosis proof (deterministic CI mode — fixture conflicts
declared, the real-NLI detection being WS1 gate evidence):** 6
per-finding proposals; all four finding kinds present and correctly
kinded (P1 pairs the 24h promise with the 48h target; P3 shows the
30-day guidance against the current 14-day revision with the chain
cited; P2 cites the playbook-naming excerpt; P4 cites the explicit
`shall` obligation); every proposal parses with valid D30 claims +
catalog claims (workbench / skill / finding_kind / evidence_basis)
conforming to the ratified contracts; every citation names a packaged
INTERNAL asset the agent consumed; byte-identical across runs; writes
confined to `08_proposals` + exactly one assist brief in
`07_agent_workspaces` (the brief declares it never enters knowledge);
the EXECUTIVE sentinel absent from every written byte; gateway
exclusions declared inside every proposal.

**The real-NLI mode (`EM_CORPUS_PROOF_NLI=1`) also passes end-to-end:**
32 per-finding proposals (28 real-NLI conflict findings + 4 coverage
findings), byte-identical, all 172 extracted candidates held DERIVED
under a live permissive policy, provenance verified against the
governed binding.

**The return path holds:** every per-finding proposal ingested through
the PROPOSAL lane under a global permissive policy; every candidate
CANDIDATE + DERIVED; `verify_provenance` confirms the claimed binding,
principal, package hash, and cited assets against governed records.

**Known consideration carried to WS3 (recorded openly):** at the
default conflict threshold (0.90) the real-NLI scan over 35
single-sentence assets surfaces 28 contradictions — the two plants at
0.972/0.980 plus long-tail noise. A business-reader diagnosis should
run at a stricter deployment threshold (`EM_CONFLICT_CONTRADICTION_THRESHOLD`,
e.g. 0.95+) — a configuration posture per the v1.5 WS0 commercial
note, never a governance change; the plants survive any threshold up
to 0.97. The WS3 commercial verdict will rule on the rendered
diagnosis's signal-to-noise.

### WS2 — FINAL VERDICT: PASSED (2026-07-03, user-ratified)

Commit: `c5d08f6`. **"I ratify WS2 as the accepted Customer Operations
runner."** All evidence above accepted: contracts drive the runner at
runtime (frames read from the ratified contracts; a non-executable
contract refused); skill tags act as real gates (SEQUENCED → refusal);
refusal-first proven (a covered question produces no finding);
evidence-driven kinding (the archived-revision rule; P1 and P3 kind
correctly); output discipline preserved (one proposal per finding, D30
+ catalog claims, INTERNAL-only citations, exclusions declared, the
assist brief workspace-local and never-knowledge, sentinel absent,
byte-identical); the return path holds (held DERIVED candidates under
a live permissive policy, provenance resolving to the governed
binding).

**Accepted honest notes:** the two frame-question tunings (business
meaning unchanged, recorded as the WS2 contract edit); the real-NLI
long tail is a WS3 signal-to-noise concern, not a WS2 failure — the
stricter deployment threshold belongs to the commercial/business-reader
posture, not to governance semantics.

**Boundary conditions preserved (user-restated):** the runner is not a
free agent; not a global skill executor; does not promote draft
contracts; runner output is not canonical knowledge; proposals
re-enter only through the governed valve; assist material remains
workspace-local; real-NLI evidence is gate evidence while
deterministic CI proves reproducibility and structural behavior.

**Customer Operations v1.6 may proceed to WS3: THE MILESTONE GATE and
THE COMMERCIAL VERDICT.**

### WS3 — THE MILESTONE GATE: evidence recorded, verdict pending

Commits: the gate suite `8ecab87`; the three declared evidence-rule
refinements `9b22926`, `5caf33e`, `9d56e19`. Suite:
`backend/test_customer_ops_acceptance.py` (CI — now 44 suites),
**passed first run** and green in every mode since.

**The seven stages, all green:** (1) the ratified corpus through the
real pipeline with the revision choreography, 35 PRIMARY facts
human-approved into the `customer_operations` domain; (2) INTERNAL
package + real AGENT binding; (3) THE DIAGNOSIS through the doors —
per-finding proposals across all four kinds, `/08_proposals` only; (4)
**the valve at the gate**: every extracted candidate held DERIVED
under a global permissive Tier-1 policy AND a live approve-everything
Tier-2 engine — never auto-approved; (5) a human accepts one finding
per kind → four APPROVED DERIVED facts, each ASSET_APPROVED event
quoting VERIFIED synthesis provenance (agent, binding, package hash,
cited governed evidence, accepting human, `cited_assets.missing ==
[]`); (6) **the vault before/after**: the re-rendered vault shows
every accepted finding as a `02_knowledge` note with
`source_class: "DERIVED"`, the **DERIVED** notice, and "This note is
not canonical." — the untouchable floor intact through the render;
(7) **THE CLOSING LINES**: every approval event carries a non-AGENT
identity fact; every APPROVED DERIVED fact has a human review; the
EXECUTIVE sentinel absent from every vault/render/package byte; the
live schema equals the frozen D24 snapshot at exactly **28 tables /
305 columns**.

**The signal-to-noise work (the WS3 evidence-rule refinements, each
declared in the contract and suite-proven):** the commercial-mode run
(real NLI at the 0.95 deployment threshold) initially surfaced 29
findings — the NLI engine over-fires on parallel timeframe sentences
about different subjects (0.96–0.999; thresholds cannot separate
them). Three declared evidence rules restored diagnosis quality
without hiding anything: (1) **the same-subject rule** — a promise
conflict requires ≥ 2 shared subject tokens beyond the timeframe and
governance vocabulary; (2) **the cross-document rule** — a promise
conflict is customer-facing vs internal, necessarily cross-document;
intra-document pairs are process ordering; (3) **subject-token
triggers** for the coverage skills. Every deferred pair is declared in
the run summary and remains in EM's own governance conflict review —
the workbench diagnoses the business; EM governs the knowledge.
Result: **29 → 6 findings**, all four kinds, every trigger citing the
right governed excerpt.

**THE COMMERCIAL DIAGNOSIS (real NLI @ 0.95, the artifact for the
business-reader verdict) — the six findings verbatim:**

1. *CUSTOMER_PROMISE_CONFLICT* — "A customer-facing commitment and an
   internal working rule disagree: governed asset 22 states 'Enterprise
   customers are guaranteed a first response within 24 hours, every day
   of the year.' while governed asset 26 states 'The first-response
   target for enterprise incidents is 48 hours.' Until a human
   reconciles them, staff and customers are working from different
   promises." (conflict confidence 0.972)
2. *OUTDATED_CUSTOMER_GUIDANCE* — "Governed asset 29 still gives
   guidance ('Our refund policy allows customers to request a refund
   within 30 days of delivery.') that tracks a superseded revision of
   asset 19, whose current approved revision states 'Refund policy:
   customers may request a refund within 14 days of delivery.' The
   outdated guidance is customer-visible until revised or retired."
   (revision chain cited)
3. *MISSING_SUPPORT_PLAYBOOK* — "Approved guidance creates a customer
   situation ('Such requests must be handled under the enterprise
   refund exception playbook with documented approval.', asset 37) but
   the governed corpus cannot answer 'Which approved playbook governs
   enterprise refund exception handling?' — no approved procedure
   covers it."
4. *MISSING_SUPPORT_PLAYBOOK* — the same uncovered situation triggered
   independently by the sales brochure's promise: "'Enterprise
   agreements support custom terms, including extended refund
   consideration...' but the governed corpus cannot answer 'What is
   the approved procedure for enterprise refund exceptions?'"
5. *SLA_OBLIGATION_GAP* — "An approved document commits the company to
   an obligation ('The provider shall deliver a monthly service
   performance report to the customer within five business days of the
   end of each calendar month.', asset 14) but the governed corpus
   cannot answer 'What is the approved procedure for producing the
   monthly service performance report?'"
6. *SLA_OBLIGATION_GAP* — the same obligation, unowned: "...cannot
   answer 'Who is responsible for delivering the monthly service
   performance report, and by when?'"

Plus the assist brief (never a proposal): approved guidance for the
topic, the run's 6 pending findings declared as PENDING and not
consulted as facts, gateway exclusions declared
(`assets_above_clearance: 1`).

**Honest slots at this gate:** the ONE real-model diagnostic run —
PENDING (no provider key in this environment; the runner's stdio MCP
door and D19 synthesis path are code-complete; the deterministic
contract-follower carried CI). The live-SharePoint tenant scan —
carries unchanged.

**Remaining WS3 item:** the in-browser before/after on a seeded
throwaway DB (the Operations pipeline holding the findings, Accept as
DERIVED live, the vault render) — runs before the final milestone
ratification. **THE COMMERCIAL VERDICT (the user reads the diagnosis
as the business reader) is now requested.**

### WS3 — THE COMMERCIAL VERDICT: PASSED (2026-07-03, user-ratified)

**"This is now a diagnosis a real Customer Operations manager would
recognize as useful, bounded, and worth acting on. I accept the
six-finding Customer Operations diagnosis as commercially credible."**

The diagnosis identifies real management problems rather than abstract
technical artifacts (the six findings, accepted individually); it is
the right level of diagnosis for a Customer Operations manager — not
overloaded with low-value contradictions, not pretending to solve what
governance has not approved; it separates business action from
canonical truth: the workbench proposes fixes, but the knowledge
system remains governed.

**The signal-to-noise refinement accepted:** "the fact that
thresholding alone could not separate false-positive timeframe
conflicts is an important commercial finding, not a failure." The
same-subject, cross-document, and trigger-token rules are appropriate
because they are declared, contract-backed, suite-proven, and leave
deferred conflicts in ExpertMachina's broader review layer rather
than hiding them.

**The practical manager test (user-stated):** "Yes, these are real
risks. Yes, I know who needs to act. Yes, the evidence is specific
enough to verify. Yes, the system is not inventing fixes. Yes, I can
trust that these are proposals, not silent rewrites of company truth."

**The big win (user-stated):** the workbench is no longer just
"detecting contradictions" — it is producing operationally usable
governed diagnosis: what is wrong, why it matters, what evidence
supports it, and where human approval must intervene.

All gate evidence accepted (six commercial findings at deployment
posture; governed citations; DERIVED-only re-entry; human acceptance
required; non-canonical DERIVED vault notes; non-AGENT identity facts
on approvals; D24 at 28/305; honest slots explicit). **Customer
Operations v1.6 may proceed to the remaining in-browser before/after
proof, then full WS3 ratification and the v1.6.0 release.**
