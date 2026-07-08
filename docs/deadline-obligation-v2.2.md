# v2.2 — Deadline & Obligation Intelligence — Build Contract

> Scoped 2026-07-08 (the v2.2 scoping session, post-v2.1.0 release;
> baseline main `d70e917`, tag `v2.1.0` = `2938286`, harness 80/80,
> D24 at 28 tables / 305 columns, route manifest 88 routes frozen,
> MCP frozen at 9 tools, [OE]/[PMD] unminted). Input briefs:
> PROJECT_STATE.md, docs/DECISIONS.md (through D32), docs/roadmap.md,
> docs/workbench-skill-registry.md (workbench 9 — the v1.7 deadline
> deferral block; workbench 16 — the register), and the gate records
> in docs/compliance-workbench-v1.7.md,
> docs/procurement-workbench-v1.8.md,
> docs/exception-stewardship-v2.0.md, and
> docs/contract-intelligence-v2.1.md. **WS0 RATIFIED by the user on
> 2026-07-08** — the rulings below stand as written; gate records are
> appended here as each workstream closes.

## The milestone in one sentence

The compliance workbench's deferred deadline family, unlocked by
[ES], comes ACTIVE — deadlines, windows, recurrence rules, and
deadline gaps **computed from governed document facts at a declared
clock, never tracked in a state machine** — and the v2.1 clause
register gets its **first downstream harvest**: deadline findings
citing accepted register clauses BY ID.

## Ruling 1 — A workbench EXTENSION, not a new workbench

The deferred subtasks (registry #9, subtasks 6, 7, 17, 18) belong to
catalog #9 Compliance & Obligation — deferred at the v1.7 WS0 gate,
not homeless. v2.2 is the catalog's **first shipped-workbench
extension**: new ratified contracts added to
`workbench/compliance_obligation/`, its runner extended, its law
untouched. No new workbench is minted (the 16-workbench catalog stays
closed). This is itself the milestone's structural proof: *the
catalog can grow a shipped workbench without re-opening anything.*
(Noted openly: the first post-ship edit of a shipped runner —
Guard 5 sweeps it unchanged, the existing v1.7 suites must stay
green untouched.)

## Ruling 2 — The deferral's fear is ANSWERED, by name

The v1.7 deferral text: *"persistent deadline stewardship risks a
second operational state machine before [ES] is scoped."* D32
answered it: **decisions persist; existence never does.** The
tracking verb dies at scoping — `track_explicit_deadlines` is
ratified as **detection**, never tracking. A deadline is a finding
computed at the declared `as_of`; the only things that ever persist
are (a) a human-accepted DERIVED fact through the valve, and (b) a
human's D32 stewardship decision. No deadline table, no calendar
store, no reminder queue — ZERO schema, D24 held at 28/305.

## Ruling 3 — THE ACTIVE THREE (consolidations declared)

| ACTIVE skill (v2.2) | Consolidates | Kind · evidence basis |
|---|---|---|
| `detect_obligation_deadlines` [now] | `track_explicit_deadlines` + `identify_upcoming_obligations_30_60_90` + `detect_certification_expiry_risk` | OBLIGATION_DEADLINE · EXCERPT_BACKED + declared-clock arithmetic — the v1.8 `detect_renewal_window` discipline verbatim: windows computed ONLY from verbatim dates at declared `as_of` + declared `window_days`; declared `deadline_classes` (certification_expiry, reporting, notice, renewal, payment, generic); an explicit obligation whose time language is vague or absent yields DEADLINE_AMBIGUITY / MISSING_DEADLINE — flagged, never dated |
| `extract_recurrence_rules` [now] | `track_recurrence_rules` | RECURRENCE_RULE · EXCERPT_BACKED — verbatim recurrence language ("annually", "within 30 days of quarter end") as a quoted fact; ambiguity flagged, never assumed; a recurrence rule is NEVER expanded into generated concrete dates |
| `prepare_obligation_calendar_brief` [assist, synth] | — | The point-in-time human brief at the declared clock, confined to `07_agent_workspaces`, SYNTHESIS_INFERRED-framed, never a finding — the v1.8 persistent-calendar refusal CARRIES: persistence refused live, a snapshot brief allowed |

**Reuse, not re-minting**: obligation owners are covered —
`detect_undocumented_obligation_owner` (ACTIVE, v1.7) detects;
OWNER_ASSIGNED / DUE_DATE_SET (D32, v2.0) steward. Escalation dates
in contract text are a deadline class; escalation as workflow is
[ES], already shipped. Neither family is touched.

## Ruling 4 — THE CARDINAL SIN: THE INVENTED DATE + THE PRESUMED COMPLETION

- **THE INVENTED DATE** (the v1.8 invented-number posture,
  date-specialized): a date appears in a finding only when verbatim
  in governed evidence, or as declared-clock arithmetic from a
  verbatim date. Never: inferred deadlines without explicit source
  text; vague language converted to dates ("promptly", "in a timely
  manner", "within a reasonable period" produce DEADLINE_AMBIGUITY,
  never a date); unparseable dates refused, declared.
- **THE PRESUMED COMPLETION** (the [OE] boundary, sharpened): the
  workbench knows what documents REQUIRE and WHEN — never what
  HAPPENED. A deadline date earlier than `as_of` may be reported as
  exactly that arithmetic fact; "missed", "breached", "overdue
  obligation", "complied", "outstanding" as claims about conduct are
  forbidden vocabulary, swept on every written byte. The [OE]-gated
  skills (`verify_obligations_against_operational_records` etc.) are
  exactly these claims — refused live, naming the unminted decision.

## Ruling 5 — THE HARVEST: the register as first-class input

`detect_obligation_deadlines` reads approved facts INCLUDING the
v2.1 register's accepted DERIVED clause facts, cited BY ID —
renewal/expiry/notice/certification clauses whose concrete-token
rule already guarantees a date or duration anchor. The first
downstream harvest of the shared engine: the register proved two
readers cite one governed fact; v2.2 proves a NEW CAPABILITY builds
on it without re-extracting anything.

## Ruling 6 — [OE] and [PMD]: NOT minted

- **[OE]: no.** Every finding derives from governed document facts +
  the declared clock. WS3 must show the refusal of an
  operational-status request live.
- **[PMD]: no.** No agent-side queue visibility is needed; the doors
  stay the package + the 9 frozen MCP tools.

## Ruling 7 — THE NON-CONFLATION RULING

A document-extracted contractual deadline (a fact about what a
contract says) and a DUE_DATE_SET stewardship decision (a human
ruling about a computed exception) are different species and never
converge: the runner never writes stewardship decisions, stewardship
never creates deadline facts, Guard 7 is untouched. WS3 proves both
co-existing on the same subject without either becoming the other.

## Ruling 8 — Zero new surface, zero new law

No D33, no 8th guard family, route manifest held at 88, MCP frozen
at 9, D24 at 28/305, `workbench/common.py` targeted unchanged a
FIFTH time. Corpus: reuse the v1.7/v1.8 corpora + register fixtures;
WS1's precondition proof decides whether a small number of new plant
documents (vague-language trap, recurrence, certification expiry)
are needed in the compliance corpus — plants added only against a
proven gap, recorded in CORPUS.md.

## The named proofs

- **THE COMPUTED CALENDAR** (the distinctive WS3 stage, the
  deferral's answer): delete every runner output → nothing lost;
  re-run at the same declared clock → byte-identical findings; no
  deadline persisted anywhere — *the calendar is a projection of
  governed facts at a declared clock, never a state machine.*
- **THE HARVEST PROOF**: a deadline finding citing a v2.1 register
  asset BY ID, its window computed from the register clause's
  verbatim date.
- **THE AMBIGUITY PROOF**: the vague-language plants each yield
  DEADLINE_AMBIGUITY and no date, on the bytes.
- **THE NON-CONFLATION PROOF**: per Ruling 7.
- **THE COMMERCIAL VERDICT** (user-ratified, never automated) — the
  reader is the compliance/obligation owner: *"Would you run your
  obligation-deadline review from this view — every date verbatim or
  declared-clock arithmetic, every vague duty flagged rather than
  dated, and nothing claiming what actually happened?"*

## Non-goals (refused deliberately, not omitted)

Notifications/reminders; any persistent calendar or deadline store;
obligation completion/status; new D32 decision kinds (the seven-kind
vocabulary stays closed); MCP growth; [OE]/[PMD]; D23 (would defer a
twelfth time); schema of any kind.

## The WS sequence

- **WS0** — these rulings. **RATIFIED 2026-07-08.**
- **WS1** — the three contracts + registry promotion (#9 grows to
  nine ratified skills; the four deferred drafts move to
  CONSOLIDATED/renamed with `ratified_path`; global sweep constants
  move — exact numbers pinned at WS1) + corpus additions only against
  a proven gap + THE PRECONDITION PROOF suite (dates / recurrence /
  ambiguity detectable in approved facts and register fixtures,
  BEFORE any runner).
- **WS2** — the compliance runner extended on `common.py` (zero
  shared-module edits; Guard 5 sweeps with zero edits; the existing
  v1.7 suites stay green untouched) + THE DIAGNOSIS PROOF suite.
- **WS3** — THE MILESTONE GATE suite + the four named proofs + the
  in-browser before/after (the Operations Workbench Catalog panel
  shows the harvest live) + THE COMMERCIAL VERDICT.

Model routing per the standing split: WS0 scoping on Fable; WS1–WS3
implementation on Opus 4.8; release mechanics on Sonnet.

## Standing boundaries

The protected boundary carries verbatim from the catalog arc:
generated draft contract ≠ executable skill; ratified workbench
contract ≠ global permission; corpus plant map ≠ runtime evidence;
runner output ≠ canonical knowledge. Every gate re-runs the D25
custody sweep and closes on the D24 snapshot. Guard 5 sweeps the
extended runner; Guard 6 holds the vault seam; Guard 7 holds the
stewardship boundary (Ruling 7). EM never launches the workbench
(D22). Language rulings per Ruling 4 and the standing D29/D30
provenance discipline.
