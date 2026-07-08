# v1.9.0 — The Executive Operations Briefing Workbench — Build Contract

> Scoped 2026-07-07 (post-v1.8.0; baseline main `21fc3d2`, tag `v1.8.0`
> = 4bb0033, harness 71/71, D24 at 28 tables / 305 columns, route
> manifest 87 routes frozen at digest `a9558682…`, MCP frozen at 9
> tools). Catalog #1, **two-stage by standing ruling** (v1 now; the
> decision queue stays behind [PMD]). The FIRST CROSS-WORKBENCH
> CONSUMER: it reads what the sellable trio produced. Gate records are
> appended as each workstream closes.

## The milestone in one sentence

The governed leadership view — accepted facts (PRIMARY and DERIVED,
class and workbench-of-origin visible), unresolved conflicts, trust and
governance health, what changed since the declared date, and the
declared unknowns — composed into a briefing where **every sentence is
cited, clocked, or declared synthesis, and the briefing states exactly
what it cannot see.**

## The sensitivity posture (the cardinal sin)

**THE UNSOURCED SENTENCE.** An executive acts on briefing sentences; a
sentence that traces to nothing is the executive analog of v1.7's
practice overclaim and v1.8's invented number. Every sentence in the
briefing pack must carry a governed citation (asset / conflict /
revision / trust component), be the declared clock (`as_of` /
`since`), or sit inside an explicitly SYNTHESIS_INFERRED-framed
section. Its twin sin: **false completeness** — the briefing must
DECLARE its boundaries in the pack itself (no pending proposals [PMD];
no operational metrics [OE]; clearance exclusions declared; "what this
briefing cannot see" is a mandatory section). Forbidden vocabulary
(swept over every written byte at the WS2 gate): "all clear",
"no risks exist", "nothing requires attention", "everything is on
track", "fully compliant", "the complete picture", "comprehensive view
of", "we approved", "the board approved", "you should approve",
"guaranteed", "certainly will".

## The opening question (evidence-first, per tradition)

"What did my governed knowledge system accept, dispute, and fail to
answer since the last time I looked — and can I trust every sentence of
the answer enough to skip the status meeting?"

## The visibility budget (the load-bearing WS0 finding)

Zero door growth means **the nine frozen MCP tools + the .empkg ARE
the entire visibility budget** — verified against the live gateway:

| Signal | The existing door |
|---|---|
| Accepted knowledge, DERIVED class + workbench-of-origin | the package (`source_class` travels, D30; `provenance.source_document` = the proposal filename `{workbench}-{skill}-{hash}.md` — origin derivable with ZERO new machinery) + `get_provenance` |
| Unresolved / dismissed conflicts | `get_conflicts` |
| Trust and its five components | `get_trust_score` |
| What changed since the declared date | `get_revision_history` (approved_at vs the declared `since`) |
| Domain structure + clearance exclusions declared | `get_domain_subgraph` |
| The unknowns | `consume()` refusals on declared executive question frames |

Anything not derivable through an existing door is OUT of v1 scope and
**declared in the briefing's boundary section** — never silently
absent. The computed Governance Inbox is a human surface, not a door;
its agent-side visibility is exactly the [PMD] question, unminted.

## Scoping rulings (proposed for ratification)

1. **THE ACTIVE SIX** (consolidations in the standing style; absorbed
   drafts gain `consolidated_into` + `ratified_path`):
   - `summarize_accepted_findings` [now] — the heart: APPROVED facts
     with `source_class` visible; every DERIVED fact cited AS DERIVED
     **with its workbench-of-origin named** (derived from
     `provenance.source_document`); PRIMARY and DERIVED never blended
     without the class shown. EXCERPT_BACKED.
   - `summarize_unresolved_conflicts` [now] — governed CONFLICTS_WITH
     pairs via `get_conflicts`, status shown, both excerpts cited;
     absorbs the conflicts/gates half of
     `detect_unresolved_blockers_by_department` (its held-proposals
     half stays [PMD]). CONFLICT_BACKED.
   - `summarize_governance_health` [now, door-limited] — trust
     components (`get_trust_score`), unresolved-conflict counts,
     revision staleness derivable from `get_revision_history`, domain
     exclusions declared; absorbs `identify_major_operational_risks`
     (a "major risk" in v1 = a door-visible signal: an unresolved
     DIRECT_CONTRADICTION, a low trust component, a stale chain —
     named as such, never an operational claim). METADATA_BACKED.
   - `answer_what_changed_since` [now] — revisions/acceptances with
     approved_at after the **declared `since`** (the standing
     declared-clock discipline: `as_of` + `since` are run parameters,
     recorded verbatim, wall-clock never sampled). REVISION_BACKED.
   - `generate_unknowns_evidence_gaps_report` [now] — declared
     executive question frames run through consume(); reproducible
     refusals ARE the unknowns; a question the corpus answers produces
     NO gap entry (refusal-first cuts both ways). REFUSAL_BACKED.
   - `prepare_executive_briefing` [assist, synth] — THE product:
     absorbs `generate_weekly_ceo_briefing` + `summarize_company_status`
     + `prepare_board_report` + `produce_recommended_next_actions`
     (the last as the SYNTHESIS_INFERRED "recommended attention"
     section — recommendations prepare, never decide). Renamed from
     "weekly": **the briefing is point-in-time at the declared clock;
     a human runs it weekly — the workbench never schedules, never
     recurs** (the v1.7/v1.8 calendar refusal applied to cadence).
     Mandatory sections, even when empty: Accepted findings (by
     workbench, DERIVED marked) · Unresolved conflicts · Governance
     health · What changed since `since` · Unknowns & evidence gaps ·
     Recommended attention [SYNTHESIS_INFERRED] · **What this briefing
     cannot see** (the boundary section: [PMD]/[OE]/clearance
     exclusions, declared). Written to `/07_agent_workspaces`, never a
     proposal, never enters knowledge.

2. **THE GATED LIST, refused live naming the unminted decision**:
   [PMD] `identify_decisions_needing_approval`,
   `produce_executive_decision_queue`, and the held-proposals half of
   `detect_unresolved_blockers_by_department` — stage 2 of the
   two-stage ruling, refused live; candidate content NEVER
   agent-readable. [OE] the operational-metrics half of
   `compare_period_vs_previous`. [ES] risk-register owner columns.

3. **SEQUENCED (deferred, not gated)**: `identify_unsupported_claims`
   (platform knowledge-quality territory, workbench #10);
   `produce_cross_functional_risk_register` as a standalone persistent
   surface (a persisted register is the row-temptation the [ES] shape
   refuses — its door-visible content lives inside
   `summarize_governance_health`); `compare_period_vs_previous` for
   governance history (needs its own two-clock evidence rule — a
   declared `since_a`/`since_b` comparison deserves its own ruling).

4. **THE FINDINGS QUESTION (a genuine v1.9 novelty, ruled here):** the
   briefing consumer produces mostly ASSIST output. Do any skills emit
   PROPOSALS? Ruling: **yes, exactly one narrow kind** —
   `generate_unknowns_evidence_gaps_report` emits one proposal per
   evidence gap (finding kind `EXECUTIVE_EVIDENCE_GAP`,
   REFUSAL_BACKED, the missing-evidence pattern) so a gap the CEO
   cares about can be accepted as a DERIVED fact and tracked through
   the governed loop. The four summarize/answer skills are
   READ-COMPOSE skills: their output lives in the briefing pack only
   (assist), because "a summary of accepted facts" re-entering
   knowledge as a fact is circular derivation — refused by ruling.
   This keeps the valve meaningful: the briefing proposes only what is
   genuinely NEW information (a documented gap), never a restatement.

5. **THE BRIEFING PROOF (the distinctive v1.9 proof — a named WS3
   stage, preconditions at WS1):**
   - every sentence in the briefing pack carries a citation token, the
     declared clock, or sits inside a SYNTHESIS_INFERRED-framed
     section — swept mechanically over the pack bytes;
   - every DERIVED citation names its workbench-of-origin;
   - byte-identical regeneration at the same declared `as_of`/`since`;
   - **THE PENDING-PROPOSAL SENTINEL** (the v1.9 plant species): a
     held, unaccepted proposal seeded with a sentinel string — the
     sentinel must appear in NO briefing byte (the [PMD] boundary
     proven on bytes, the way the EXEC sentinel proves clearance);
   - the EXEC clearance sentinel absent, exclusions declared;
   - **ZERO DOOR GROWTH proven structurally**: the route-manifest
     guard digest UNCHANGED (`a9558682…`, 87 routes — the T2.4 guard
     becomes the door-growth instrument), the MCP surface still frozen
     at 9 tools (Guard 5's standing assertion), zero schema (D24 at
     28/305);
   - the boundary section present and truthful (names [PMD], [OE],
     and the clearance exclusions actually encountered).

6. **THE CROSS-WORKBENCH FIXTURE (WS1's corpus analog):** v1.9's input
   is not a new document corpus — it is the governed state the trio
   produces. WS1 builds the fixture by running the compliance AND
   procurement loops (the cheapest deterministic pair) in ONE project:
   accept a subset of findings as DERIVED (both workbenches
   represented), leave held candidates including THE PENDING-PROPOSAL
   SENTINEL, leave one conflict unresolved (the governance-health
   plant), approve one revision after the declared `since` (the
   what-changed plant), keep the EXEC sentinel above clearance, and
   declare 2–3 executive question frames the corpus refuses (the
   unknowns plants) plus one it answers (the covered control). THE
   FIXTURE PROOF (WS1, before any runner): accepted DERIVED facts
   carry workbench-of-origin via provenance; the pending sentinel is
   in no package byte; the clock preconditions hold both directions.

7. **One project, one binding, v1**: the briefing reads ONE project's
   governed state through ONE INTERNAL binding (the deployment
   reality: a company = a project). Multi-project aggregation is out
   of scope, declared.

8. **Zero schema. Zero backend change. Zero new endpoints, MCP tools,
   or UI areas.** No D32; no seventh guard family; Guard 5 sweeps the
   new bundle the moment it lands. `workbench/common.py` expected
   unchanged again (third reuse; recorded at the WS2 gate).

9. **THE COMMERCIAL VERDICT (user-ratified, never automated)** — the
   reader is the CEO: *"As the CEO: is this briefing trustworthy
   enough to replace a status meeting — every claim traceable, every
   unknown declared — and bounded enough that you know exactly what it
   will not tell you?"*

10. **Model routing (recorded)**: WS0/WS1/WS3 → Fable; WS2 → Opus 4.8
    after ratification (escalate to Fable if the sentence-citation
    sweep, DERIVED-origin derivation, or boundary framing gets
    subtle); release choreography → Sonnet 5.

11. **The honest slots carry**: the real-model diagnostic run (the
    executive briefing is arguably the BEST vehicle yet — a narrated
    briefing over real governed facts) and the v1.2.0 live-SharePoint
    scan.

## Module map (planned)

| Location | Role |
|---|---|
| `workbench/executive_briefing/workbench.yaml` | canonical #1, two-stage declared, THE UNSOURCED SENTENCE posture + forbidden vocabulary, the visibility budget, the gated/SEQUENCED lists |
| `workbench/executive_briefing/skills/*.yaml` | the six ratified 13-field contracts |
| `workbench/executive_briefing/runner.py` | on common.py (zero shared-module edits expected); question frames, section list, boundary declarations parsed from the YAMLs |
| *(no corpus/ directory)* | the cross-workbench fixture is built by the suites from the existing trio corpora (ruling 6) — the briefing has no documents of its own |
| `backend/test_executive_fixture.py` (WS1) | THE FIXTURE PROOF |
| `backend/test_executive_workbench.py` (WS2) | THE DIAGNOSIS PROOF |
| `backend/test_executive_acceptance.py` (WS3) | THE MILESTONE GATE + THE BRIEFING PROOF |

CI grows 71 → 74 suites. No changes under `backend/app/`.

## Workstreams

**WS0 — this document.** Gate: user ratification of rulings 1–11; all
71 suites standing; D24 at 28/305. On ratification: branch
`feat/v19-executive-briefing` off main, this contract committed as the
scoping commit (+ registry promotion annotations at WS1).

**WS1 — the contracts + THE CROSS-WORKBENCH FIXTURE + THE FIXTURE
PROOF** (ruling 6; the draft≠ratified sweep moves 17→23 ACTIVE with the
consolidations recorded). Gate: user ratifies the fixture as realistic
and the six contracts as the declared product.

**WS2 — the runner + THE DIAGNOSIS PROOF** (Opus; contracts drive
runtime; the sentence-citation discipline enforced at the source;
byte-identical at the declared clock; gated list refused live). Gate:
user ratifies the runner.

**WS3 — THE MILESTONE GATE + THE BRIEFING PROOF + THE COMMERCIAL
VERDICT** (ruling 5; the in-browser before/after per the standing
pattern; release closeout: tag v1.9.0, PROJECT_STATE/roadmap regen).

## Explicitly out of scope (refused deliberately, not omitted)

The executive decision queue and any pending-proposal visibility
([PMD], stage 2 — refused live); operational metrics and
period-vs-period operational comparisons ([OE]); owner assignment
([ES]); a persistent risk register or briefing schedule (the
row/calendar temptations, refused by standing rulings); multi-project
aggregation (ruling 7); restatement-proposals (ruling 4 — summaries
never re-enter knowledge as facts).

## Gate records

*(appended as workstreams close; WS0 ratification pending)*

### WS0 — SCOPING RATIFICATION: PASSED (2026-07-07, user-ratified)

Ratified verbatim: rulings 1–11 — the ACTIVE SIX
(summarize_accepted_findings / summarize_unresolved_conflicts /
summarize_governance_health / answer_what_changed_since /
generate_unknowns_evidence_gaps_report / prepare_executive_briefing);
cardinal sin THE UNSOURCED SENTENCE, twin sin FALSE COMPLETENESS;
distinctive proof THE BRIEFING PROOF; the fixture model =
cross-workbench governed-state fixture, not a new document corpus; the
novel findings ruling (summaries never re-enter knowledge; only
EXECUTIVE_EVIDENCE_GAP proposals allowed); the boundary posture (no
[PMD] pending-proposal visibility, no [OE] operational metrics, no
[ES] owner/routing/stewardship, no persistent risk register, no
schedule/calendar behavior, no multi-project aggregation); the
architecture posture (zero schema, zero backend change, zero new
doors, route manifest unchanged, MCP frozen at 9 tools, D24 at
28/305). Sequence: this scoping commit → WS1 (contracts + THE
CROSS-WORKBENCH FIXTURE + THE FIXTURE PROOF, on Fable). Baseline at
ratification: main 21fc3d2, tag v1.8.0 = 4bb0033, harness 71/71.

**Verdict: v1.9.0 WS0 PASSED.** WS1 may proceed.

### WS1 — The Contracts, THE CROSS-WORKBENCH FIXTURE, and THE FIXTURE PROOF: evidence recorded, gate pending ratification (2026-07-07)

Delivered: the SIX ratified 13-field contracts in
`workbench/executive_briefing/skills/` (consolidations per ruling 1,
never silent: summarize_governance_health absorbs
identify_major_operational_risks; prepare_executive_briefing absorbs
generate_weekly_ceo_briefing + summarize_company_status +
prepare_board_report + produce_recommended_next_actions; the
detect_unresolved_blockers split recorded as a split_note — its
conflicts half ratified into summarize_unresolved_conflicts, its
held-proposals half staying [PMD]); the manifest (`workbench.yaml`:
canonical #1, two-stage declared, THE UNSOURCED SENTENCE posture + the
12-phrase forbidden vocabulary, the visibility budget, the findings
ruling, the gated/SEQUENCED lists); the registry promotion (**23
ACTIVE / 18 CONSOLIDATED globally**, every ratified_path resolving; the
prepare_executive_briefing consolidation-target draft added; both
prior corpus proofs' sweep constants moved 17→23 / 13→18 — the
recorded-assertion-edit pattern, third occurrence, both suites re-run
green). No corpus directory of its own — ruling 6 held.

**THE FIXTURE PROOF** (`backend/test_executive_fixture.py`, the 72nd
suite — all seven parts green; full harness 72/72):
1. THE CROSS-WORKBENCH FIXTURE is real: both corpora (12+12
   documents) in ONE project, 86 PRIMARY facts across two domains,
   BOTH runners diagnosing through the doors (25+26 proposals), 297
   candidates held DERIVED under the valve.
2. One acceptance per workbench — and both accepted DERIVED facts'
   **workbench-of-origin derivable from provenance.source_document**
   (compliance-obligation and procurement-intelligence both named),
   with zero new machinery.
3. **THE PENDING-PROPOSAL SENTINEL** (EM-PENDING-SENTINEL-9K3W): a
   held, never-accepted proposal is a CANDIDATE in the lane and its
   bytes appear in NO package — the [PMD] boundary provable on bytes.
4. The declared `since` discriminates: an acceptance after the
   captured since sorts after it; the earlier ones before it —
   approved_at ordering over governed revision records, both
   directions.
5. Door-visible health: an unresolved DIRECT_CONTRADICTION inserted
   AFTER the package compiled (post-compile drift, the realistic
   rhythm) is visible via get_conflicts; get_trust_score returns the
   components; both declared executive gap questions refuse
   reproducibly; the covered control answers.
6. Contract shape + the draft≠ratified sweep honest at 23/18; the
   suite's questions are the contract's frames verbatim.
7. Zero schema: D24 at exactly 28 tables / 305 columns.

**Two authoring notes (recorded, the standing lessons):** the pending
sentinel's plant sentence needed an explicit extraction trigger
("must") to become a governed candidate (the v1.8 corpus lesson); and
one declared gap question was reworded at WS1 (insurance → board
quorum) because its generic vocabulary collided with the ISO
certification statement at the declared retrieval threshold — chosen
empirically (max doc-level overlap 4 < 6), recorded in the contract,
never a silent threshold bend.

**THE GATE (per WS0): user ratification of the cross-workbench fixture
as realistic and the six contracts as the declared product is now
requested. WS2 (the runner, on Opus per the recorded routing) starts
only on ratification.**

**WS1 RATIFICATION: PASSED (user-ratified)** — the cross-workbench
fixture accepted as realistic and the six contracts as the declared
product. WS2 proceeded on the recorded Opus routing.

### WS2 — The Runner + THE DIAGNOSIS PROOF: evidence recorded, gate pending ratification (2026-07-07)

Delivered: `workbench/executive_briefing/runner.py` on
`workbench/common.py` (relative import; **zero shared-module edits** —
common.py untouched, the third industrialization proof). The runner
composes the briefing pack from the existing doors ONLY: accepted
findings by class + workbench-of-origin (derived from
provenance.source_document via the filename convention, zero new
machinery); unresolved conflicts (get_conflicts, both sides cited);
governance health (get_trust_score components + unresolved-conflict
count, door-limited); what-changed (get_revision_history approved_at >
the declared since); unknowns (declared question frames through
consume(), refusals REFUSAL_BACKED). THE UNSOURCED SENTENCE is enforced
at the source: the runner refuses to write a cited-section line without
a governed token, and the forbidden vocabulary is refused pre-write.
Exactly one proposal kind (EXECUTIVE_EVIDENCE_GAP); the read-compose
skills emit none. get_trust_score reached via a runner-local
BriefingGraphClient(StdioMcpGraphClient) subclass - an EXISTING frozen
tool, no new door, no common edit.

**THE DIAGNOSIS PROOF** (`backend/test_executive_workbench.py`, the
73rd suite - eight parts green, first run; full harness 73/73):
1. Guard 5 sweeps 7 workbench modules, zero guard edits.
2. The cross-workbench fixture: both loops in one project, accepted
   DERIVED facts from BOTH workbenches, a post-compile-drift conflict.
3. One briefing pack (7 mandatory sections) + 3 gap proposals,
   byte-identical at the declared clock, confined (pack to
   07_agent_workspaces, gaps to 08_proposals); forbidden vocabulary,
   the EXECUTIVE sentinel, AND THE PENDING-PROPOSAL SENTINEL absent
   from every written byte.
4. Both DERIVED origins named (compliance-obligation +
   procurement-intelligence), PRIMARY class visible; conflicts cite
   both sides; trust components + conflict count door-visible;
   what-changed cites the post-since acceptance; the boundary section
   names [PMD]/[OE]/[ES].
5. The findings ruling: 3 EXECUTIVE_EVIDENCE_GAP proposals,
   REFUSAL_BACKED, empty citations; the read-compose skills emitted no
   proposals.
6. no-as_of / no-since / schedule / multi-project refused; [PMD] /
   [OE] / [ES] / persistent-register / schedule skills refused live
   naming the boundary.
7. **ZERO DOOR GROWTH proven structurally**: the route-manifest digest
   is byte-identical (the T2.4 guard = the door-growth instrument);
   the MCP surface still frozen at 9 tools; D24 at 28/305.
8. The gap proposals hold DERIVED at the valve, provenance verified
   against the governed binding.

**Regression at the gate**: full harness 73/73 green; Guard 5 green
(swept the runner with zero edits); the route manifest and MCP surface
unchanged; D24 held at 28/305.

**THE GATE (per WS0): user ratification of the runner as the accepted
Executive Briefing workbench is now requested. WS3 (THE BRIEFING PROOF
+ the browser proof + THE COMMERCIAL VERDICT, on Fable per the recorded
routing) starts only on ratification.**

**WS2 RATIFICATION: PASSED (2026-07-08, user-ratified)** — the
Executive Briefing runner, the contract-driven sentence discipline,
the pending-proposal boundary, THE DIAGNOSIS PROOF, and the
runner-local `BriefingGraphClient` adapter to the existing
`get_trust_score` tool are accepted (an adapter to a frozen tool,
never door growth). WS3 opened on Fable per the recorded routing.

### WS3 — THE MILESTONE GATE + THE BRIEFING PROOF: evidence recorded, THE COMMERCIAL VERDICT pending (2026-07-08)

`backend/test_executive_acceptance.py` (the 74th suite) — eight
stages, all green; full harness **74/74** (413.98s):

1. The workstream record: WS0/WS1/WS2 gate records + both prior
suites present; six ACTIVE contracts (read-compose finding kinds
empty, the gap skill's single kind, the briefing [assist, synth]);
**`BriefingGraphClient` recorded structurally as an adapter** — a
subclass of the shared stdio client whose ONLY addition is
`get_trust_score`, one of the nine frozen tools; never door growth.
2. The cross-workbench fixture through the real pipeline: 24
documents (both corpora), 3 accepted DERIVED facts (both workbenches
+ the post-since plant), the pending sentinel held, package v2 with a
post-compile conflict, the valve policies (permissive Tier-1 +
approve-everything Tier-2) live before any lane scan.
3. THE BRIEFING at the declared clock, twice: byte-identical
regeneration (sha256 over every written file), confined to
07_agent_workspaces / 08_proposals.
4. **THE BRIEFING PROOF (the distinctive stage, swept test-side,
independent of the runner's own enforcement)**: 182 cited-section
lines each carrying a governed source token (header clocked verbatim;
exactly the 7 declared sections); every `[DERIVED]` tag origin-named,
both workbenches present, PRIMARY visible; the pending + EXECUTIVE
sentinels and the 12 forbidden phrases in NO written or packaged
byte; the boundary section quotes the gateway's declared exclusions
VERBATIM (truthfulness bound to the door's own counts); **the covered
question left no gap, no proposal, and no byte** (amended into a temp
contract copy — frames are contract-declared); 13 refusals live
(no-as_of / no-since / schedule / multi-project + all nine gated
skills naming their boundary); ZERO DOOR GROWTH structural — route
digest byte-identical, MCP frozen at 9 tools, D24 at 28/305.
5. The valve at the gate: 13 gap candidates held DERIVED under
maximal policy permissiveness; the pending plant still held; ONE
human acceptance → APPROVED DERIVED, the approval event quoting
VERIFIED synthesis provenance (a REFUSAL_BACKED gap cites nothing —
the provenance record honestly carries no cited-assets verdict).
6. Composition: the accepted gap traveled DERIVED into package v3
(pending candidates structurally absent) and the NEXT briefing cites
it **[DERIVED, origin: executive-briefing]** and reports it in
what-changed — the briefing consuming its own human-accepted finding.
7. The vault before/after: the accepted gap renders as a marked
DERIVED note, visibly non-canonical; no sentinel in any rendered
note; the pack and every proposal byte-identical through the render.
8. THE CLOSING LINES: every approval event non-AGENT; every APPROVED
DERIVED fact human-reviewed; **no shared summary fact store
anywhere** (the pack never ingested, read-compose output only in
07_agent_workspaces, no table that could hold one); 168 files
sentinel-clean; D24 at exactly 28 tables / 305 columns.

**One gate-discovered fix, recorded (the standing
recorded-assertion-edit pattern):** the ratified "mandatory sections,
even when empty" (ruling 1) was unwritable as built — the runner's
own sentence sweep refused its own empty-note line the first time a
recompiled model produced an empty conflicts section. The fix: the
empty-note marker ("an empty section is itself information") is a
DECLARED ABSENCE source token, in the runner and mirrored in the
gate's independent test-side sweep. Stage 6 now asserts the
discipline live (the v3 briefing's empty conflicts section declares
its emptiness). WS2's suite re-run green after the edit; full harness
74/74.

**The in-browser before/after (recorded 2026-07-08): PASSED.** Seeded
throwaway DB (the `backend/.ui-gate-db` pattern, seed_v19, this
branch's code — `frontend/` and `backend/app/` are byte-identical to
main on this branch, the zero-door posture made visible): login as a
governed GOVERNANCE_REVIEWER (`exec_reviewer`); Operations BEFORE —
55 proposals, 308 held DERIVED, 2 accepted DERIVED (the trio seeds;
ZERO executive gaps), the 3 EXECUTIVE_EVIDENCE_GAP proposals showing
PROVENANCE VERIFIED against binding #2; ONE live **Accept as
DERIVED** (candidate #394, the gap Finding statement; the
pre-existing review PATCH, the area's only write) → AFTER — 307 held,
**3 accepted DERIVED**, the gap group at "4 held · 1 accepted", #394
APPROVED DERIVED; zero console errors, zero console warnings; the
only non-2xx request is the pre-login session-restore probe (401 by
design — the login gate).

**The honest slots carry:** the ONE real-model diagnostic run
(PENDING, no provider key; a narrated briefing over real governed
facts is the natural vehicle) and the v1.2.0 live-SharePoint scan.

**THE GATE: THE COMMERCIAL VERDICT (ruling 9) — the user reads the
exported briefing pack as the CEO.** The question, verbatim: *"As the
CEO: is this briefing trustworthy enough to replace a status meeting
— every claim traceable, every unknown declared — and bounded enough
that you know exactly what it will not tell you?"* The milestone
closes on that verdict or it does not close.
