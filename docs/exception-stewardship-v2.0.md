# v2.0.0 — Risk & Exception Stewardship — Build Contract (the [ES] minting milestone)

> Scoped 2026-07-08 (post-v1.9.0; baseline main `5d8ed60`, tag `v1.9.0`
> = `a9ded83`, harness 74/74, D24 at 28 tables / 305 columns, route
> manifest 87 routes frozen at digest `a9558682…`, MCP frozen at 9
> tools). **A LAW milestone, not a catalog bundle**: it mints the
> Exception Stewardship decision named-not-minted at v1.6 and deferred
> deliberately through four workbench milestones. Catalog #15 is Layer
> 1 PLATFORM — its computed half already shipped as EM itself (the
> Governance Inbox + the Operations Proposal Pipeline); this milestone
> ships its HUMAN half. Gate records are appended as each workstream
> closes.

## The milestone in one sentence

Humans can now steward the computed exception queue — acknowledge,
accept risk, dismiss with reason, escalate, assign an owner, set a due
date — as durable, identity-backed, append-only governed decisions,
while exception EXISTENCE remains computed from governed facts at read
time, always: **the exception never becomes a row; the human decisions
about it do.**

## The law (proposed for ratification): D32 — Exception Stewardship

> The exception never becomes a row; the human decisions about it do.
>
> Exception existence is computed from governed facts at read time,
> always. No persisted state may create, mirror, or extinguish an
> exception — a work-item row whose OPEN/CLOSED tracks governed state
> is the two-state-machine drift D1 names, and is refused permanently.
>
> What persists is the human stewardship decision: an identity-backed,
> append-only governed record, keyed to the exception's stable
> computed identity, carrying its own reason. Decisions annotate the
> queue; they never decide what is in it. A stewardship decision
> changes no governed knowledge fact, no severity, and no gate verdict
> — fixing facts is the only way an exception leaves the queue, and
> the decision history remains as evidence even after the exception it
> ruled on has vanished.
>
> Only humans steward. Agents may propose findings through the valve
> (D29); they may never acknowledge, accept, dismiss, escalate, own,
> or schedule an exception.

**The number, ruled here:** the register assigns numbers
chronologically at minting (the v1.2→v1.3 precedent: a named rule is
NOT a number until its own scoping session). v1.6 named *a moment that
would earn a D32* (skill-aware acceptance, among others); it reserved
no number. Exception Stewardship is the next minted law and takes
**D32**; the skill-aware-acceptance moment, if it ever arrives, takes
whatever number is next THEN.

## The sensitivity posture (the cardinal sin)

**THE SECOND STATE MACHINE.** The moment a persisted status can
disagree with the governed facts — an exception row marked CLOSED
while the underlying candidate is still held, an OPEN item whose
conflict a human already dismissed — the queue becomes a parallel
truth that must be reconciled instead of trusted. Every design choice
below is downstream of refusing that row. Its twin: **THE SILENT
VETO** — a stewardship decision that makes an exception disappear
(a "dismiss" that filters existence rather than annotating it) turns a
human note into an ungoverned suppression channel. Dismissal moves an
item out of the default *presentation*; existence, severity (D2), and
the compile gate never change. A risk-accepted HIGH is still HIGH and
still blocks compile — the record proves a human accepted the risk; it
never unblocks the deployment.

## The opening question (evidence-first, per tradition)

"Which computed exceptions has a human already ruled on, who ruled,
why, and by when must someone look again — provable from the ledger
alone, with zero chance the queue and the facts disagree?"

## What exists today (the grounding, verified)

- The Governance Inbox (v0.9.1 → v1.4.1) computes every item live with
  a deterministic identity already in place: `CONFLICT-{rel_id}`,
  `REVISION-{rev_id}`, `EVIDENCE_GAP-{verdict_id}`,
  `WARNING-{model_id}-{signal}`, `INGESTION_EXCEPTION-{asset_id}`,
  `PROJECTION-{event_id}`. No exception row exists anywhere; severity
  comes from ONE shared function per D2.
- The one existing "human decision persists" precedent lands ON a
  governed row (conflict CONFIRMED/DISMISSED with reviewed_by +
  reason) — possible only because conflicts HAVE a row. Warnings,
  NOT_COVERED candidates, proposal holds, and stale renders have
  nowhere to record a human ruling today. That gap is this milestone.
- D3 is the persistence shape: a human judgment about a measurement is
  an AuditEvent (`VERIFICATION_REVIEWED`), never workflow state on the
  artifact.

## Scoping rulings (proposed for ratification)

1. **THE LEDGER-ONLY SHAPE — zero schema.** A stewardship decision is
   an `AuditEvent` (`event_type = STEWARDSHIP_DECISION`), written
   through the one governed audit writer with the actor's identity
   fact (D20), carrying in `details`: the exception key + type, the
   decision kind, the reason, and the kind-specific fields. **D24
   stays at 28 tables / 305 columns through a LAW milestone** — the
   D3 pattern applied whole. Tradeoff accepted: the queue join is a
   read-time ledger projection (the `_latest_automation_evidence`
   pattern, already standing); a projection cache is refused as the
   drift bug itself. A `StewardshipDecision` table is the named
   alternative if event-scan cost ever bites — a register amendment,
   never a quiet migration.

2. **THE EXCEPTION KEY (the load-bearing identity ruling).** The
   stable computed identity IS the Governance Inbox item id as
   computed today (`key_version: inbox-item-v1`). It derives from the
   governed fact that produces the exception, so identical governed
   state yields identical keys on every recompute — proven as a WS1
   precondition. A new measurement generation (a fresh evaluation run
   produces new verdict ids) is a NEW exception requiring fresh
   stewardship — sticky stewardship across generations is SEQUENCED,
   deliberately (honest and conservative beats magic identity
   matching). Scope: the Governance Inbox item set (conflicts,
   revisions, evidence gaps, warnings, ingestion/proposal exceptions,
   projection staleness). The Consumption Inbox: SEQUENCED — the same
   law applies later by amendment, not by a wider first gate.

3. **THE DECISION VOCABULARY (ruled, closed, seven kinds):**
   `ACKNOWLEDGED` · `RISK_ACCEPTED` (reason required) · `DISMISSED`
   (reason required) · `ESCALATED` (reason + escalated_to label
   required) · `OWNER_ASSIGNED` (owner_label required;
   owner_principal_id optional — EM does not govern the org chart, so
   an owner is a declared label, identity-backed when the owner IS a
   principal) · `DUE_DATE_SET` (due_date required, `YYYY-MM-DD`,
   declared; **overdue is computed at read time against the request's
   clock, never stored**) · `CLEARED` (names the kind it clears;
   reason required — the append-only undo). Current state per
   exception = latest event per (key, kind), with `CLEARED` removing
   that kind; everything derived at read, nothing mutated, ever.

4. **THE QUEUE IS THE JOIN.** The existing inbox response annotates
   each item with its current stewardship state (`stewardship: {...}`)
   and grows presentation filters (unstewarded / acknowledged /
   risk-accepted / dismissed / escalated / owned / due). Buckets,
   severities, ordering, and the compile gate are untouched — the
   D2 invariant asserted at the gate. No new read endpoint; the join
   rides `GET /api/projects/{id}/governance/inbox`.

5. **DOOR GROWTH: EXACTLY ONE ROUTE, AMENDED OPENLY.** One new write
   endpoint (`POST /api/projects/{id}/stewardship`), guarded by the
   existing `assets:review` permission (a stewardship decision is a
   governance review act; a dedicated `stewardship:decide` permission
   is SEQUENCED if separation-of-duties pressure arrives). AGENT
   bearers refused (Guard 5's grid must cover the new route — checked
   at WS1, amended openly if the grid is enumerated). **The route
   manifest moves 87 → 88 and FROZEN_DIGEST is re-frozen in the same
   ratified commit — the first exercise of the T2.4 amendment path:
   the guard makes door growth loud, and this is what loud looks
   like.** MCP stays frozen at 9 tools: agent visibility of
   stewardship state is exactly the [PMD] question, refused live,
   unminted. Zero new UI areas (D8): stewardship controls land inside
   the existing Governance Inbox area.

6. **Guard 7 — `test_exception_stewardship_guard.py`, BEFORE the
   door (the seventh permanent guard family).** Charter:
   - **THE ROW SENTINEL**: D24 byte-identical at 28/305; no module
     outside the audit writer persists stewardship; a planted
     exception/stewardship table or status column is caught.
   - **THE EXISTENCE SENTINEL** (the D1 drift plant): the computed
     item set (ids, severities, pre-stewardship buckets) is IDENTICAL
     with all STEWARDSHIP_DECISION events present vs absent — a
     planted existence-filter driven by decisions is caught.
   - **Append-only**: stewardship writes flow ONLY through the audit
     writer; a planted update/delete of a prior decision event is
     caught.
   - **AGENT powerlessness**: an AGENT token on the stewardship route
     is refused (D29's spirit on the new door).
   - **Knowledge untouched**: a stewardship write changes zero bytes
     in the governed knowledge tables (fingerprint before/after).
   - **Severity honesty (D2)**: annotation never alters severity or
     the gate verdict.
   Adversarially self-proven at the WS1 gate, like Guards 4/5/6.

7. **No runner, no corpus, deliberately.** The [ES] "skills"
   (`record_human_acknowledgement`, `record_risk_acceptance`,
   `record_dismissal_with_reason`, `record_escalation`,
   `route_to_responsible_owner`) are HUMAN acts on the operator
   surface — promoting them into agent skill contracts would put the
   stewardship pen in the agent's hand, which D32 exists to refuse.
   The registry entries gain `ratified_path` pointers to this
   contract with `status: HUMAN_SURFACE` (a new honest status — they
   are delivered, not agent-runnable). `produce_department_owner_view`
   ships as the owner filter on the queue (presentation only).
   `track_unresolved_risks` is the queue itself (computed; its
   persistence question is answered by D32: decisions persist,
   existence never does).

8. **THE STEWARDSHIP PROOF (the distinctive proof — a named WS3
   stage, preconditions at WS1):**
   - real exceptions seeded through the real machinery (held
     candidates incl. a proposal hold, an unresolved conflict, a
     governance warning, a stale render);
   - a human stewards across the FULL vocabulary (all seven kinds,
     including a CLEARED undo), every decision an identity-backed
     ledger event;
   - **THE ROW TEST**: the queue recomputes IDENTICALLY from governed
     facts with every decision ignored; the knowledge-table
     fingerprint is unchanged by all stewardship activity;
   - **THE VANISHING TEST**: fix an underlying fact (approve the held
     candidate; review the conflict) → the exception leaves the queue
     while its decision history remains in the ledger, honestly
     joined as ruling on a no-longer-present exception;
   - identity stability: N recomputes → identical keys; the join
     lands every time;
   - **THE OVERDUE COMPUTATION**: due date declared once; overdue
     derived at a declared clock, stored nowhere;
   - **severity/gate honesty**: risk-accepting a HIGH blocker changes
     neither its severity nor the compile-gate verdict;
   - AGENT refused on the door; the ENTIRE stewardship state
     reconstructs from AuditEvents alone (the ledger-alone closing
     line, the D29 tradition applied to [ES]);
   - route manifest at exactly 88 with the re-frozen digest; MCP at
     9; D24 at 28/305.

9. **THE COMMERCIAL VERDICT (user-ratified, never automated)** — the
   reader is the GOVERNANCE OFFICER: *"As the governance officer:
   would you run your weekly exception review from this queue — every
   decision durable and attributable, every exception honest about
   whether it still exists, and nothing tracked twice?"*

10. **Model routing (recorded)**: WS0/WS1/WS3 → Fable; WS2 → Opus 4.8
    after ratification; release choreography → Sonnet 5.

11. **The honest slots carry**: the ONE real-model diagnostic run and
    the v1.2.0 live-SharePoint scan (neither is this milestone's
    vehicle — there is no runner).

## Module map (planned)

| Location | Role |
|---|---|
| `backend/app/stewardship.py` | the decision vocabulary, validation (kind-required fields), the ledger write (through `app/audit.py` with identity facts), the read-time join (latest-per-(key,kind), CLEARED semantics, overdue computation) |
| `backend/app/routers/…` | ONE new POST route (87→88, digest re-frozen); the inbox response annotation wired in `governance_inbox.build_inbox` |
| `backend/test_exception_stewardship_guard.py` (WS1) | Guard 7, adversarially self-proven before the door |
| `backend/test_stewardship_acceptance.py` (WS3) | THE MILESTONE GATE + THE STEWARDSHIP PROOF |
| `frontend` Governance Inbox | stewardship controls + stewarded filters (existing area; no new area per D8) |
| `docs/DECISIONS.md` | D32 appended at WS1 (the law lands with its guard, the standing pattern) |

CI grows 74 → 76 suites. Schema unchanged (28/305). Route manifest
87 → 88 by ratified amendment. MCP unchanged at 9.

## Workstreams

**WS0 — this document.** Gate: user ratification of the law text and
rulings 1–11; 74/74 standing. On ratification: this contract committed
as the scoping commit on `feat/v20-exception-stewardship`.

**WS1 — Guard 7 + the spec, before the door** (the guard
adversarially self-proven; the exception-key stability precondition
proven over the real inbox; D32 appended to the register; the registry
[ES] entries annotated). Gate: user ratifies the guard evidence and
the key ruling as proven.

**WS2 — the door + the join + the operator surface** (Opus; the ONE
route, the inbox annotation, the route-manifest amendment in the same
commit, the Governance Inbox controls). Gate: user ratifies the
stewardship surface.

**WS3 — THE MILESTONE GATE + THE STEWARDSHIP PROOF + THE COMMERCIAL
VERDICT** (the in-browser before/after per the standing pattern: a
live acknowledge/risk-accept/owner-assign on a seeded queue; release
closeout: tag v2.0.0, PROJECT_STATE/roadmap regen).

## Explicitly out of scope (refused deliberately, not omitted)

A persisted exception/register row in any form (D32's core); the
deadline-extraction family (`track_explicit_deadlines`,
`track_recurrence_rules` — they UNLOCK after [ES] and get their own
session; a due date on a decision is a stewardship attribute, not
document extraction); sticky stewardship across measurement
generations (ruling 2); Consumption-Inbox stewardship (sequenced,
same law); agent visibility of stewardship or pipeline state ([PMD],
refused live); a dedicated stewardship permission (sequenced);
notifications, digests, schedules (the calendar refusal stands);
org-chart governance (owners are declared labels, optionally
principal-backed); skill-aware acceptance (a different named moment —
NOT this number).

## Gate records

*(appended as workstreams close)*

### WS0 — SCOPING RATIFICATION: PASSED (2026-07-08, user-ratified)

Ratified verbatim: rulings 1–11 and the D32 text as written. The two
consequential calls ruled explicitly:
- **D32 belongs to Exception Stewardship now.** Skill-aware acceptance
  was a future pressure point, not a reserved decision number — the
  chronological register rule wins.
- **The ledger-only shape is approved.** No exception row. No
  StewardshipDecision table in v2.0. The persisted artifact is the
  append-only `STEWARDSHIP_DECISION` AuditEvent keyed to the computed
  exception identity. A table remains a named future alternative only
  if event-scan cost becomes real.

The law: **the exception never becomes a row; the human decisions
about it do.**

The route-manifest move 87 → 88 is explicitly allowed for this law
milestone — the first ratified use of the T2.4 amendment path. MCP
remains frozen at 9 tools. Schema remains 28/305.

Sequence: this scoping commit → WS1 on Fable (mint D32 in the
register; Guard 7 `test_exception_stewardship_guard.py`; the
key-stability precondition; the row sentinel / existence sentinel /
append-only / AGENT refusal / knowledge-fingerprint / D2 severity
checks proven BEFORE the door exists). WS2 held until WS1 is
ratified, then Opus for the one route + queue join. WS3 returns to
Fable for THE STEWARDSHIP PROOF and the governance-officer verdict.

**Verdict: v2.0.0 WS0 PASSED.** WS1 may proceed.

### WS1 — D32 minted + Guard 7 before the door: evidence recorded, gate pending ratification (2026-07-08)

Delivered:
- **D32 appended to `docs/DECISIONS.md`** — the ratified law text
  verbatim + the companion rulings (the ledger-only shape, the
  exception key `inbox-item-v1`, the seven-kind closed vocabulary,
  the queue-is-the-join with D2 severity honesty, the one-route
  87→88 amendment) + why/tradeoff/enforcement in the register's
  standing shape.
- **The registry annotated**: the [ES] tag definition records the
  minting (the human surface exists; [ES]-tagged skills in OTHER
  workbenches remain gated per-workbench — stewardship pens stay in
  human hands); workbench 15's five stewardship entries carry
  `HUMAN_SURFACE at v2.0` with their decision-kind mappings;
  `track_unresolved_risks`' persistence question is answered by D32.
- **Guard 7** — `backend/test_exception_stewardship_guard.py` (the
  seventh permanent guard family, the 75th suite), all six parts
  green, BEFORE any door exists:
  1. **THE ROW SENTINEL**: D24 byte-identical at 28/305; no
     exception/stewardship-shaped table; 57 app modules swept (the
     event type spelled nowhere; direct AuditEvent construction
     beside it forbidden); all THREE plants caught (a stewardship
     table, a direct event construction, an out-of-module mention).
  2. **Append-only is law**: no module in app/ deletes or
     bulk-updates ledger rows; both mutation plants caught; the
     seven-kind vocabulary closed and enforced — the guard IS the
     spec until the door exists, and `app/stewardship.py`'s
     vocabulary must equal it the moment it lands.
  3. **THE KEY-STABILITY PRECONDITION** over a REAL computed inbox
     (an unreviewed DIRECT_CONTRADICTION, a pending candidate
     revision, an uncovered candidate, a no-evaluation warning): 5
     computed exceptions, byte-identical ids across 3 recomputes,
     four key grammars, keys derived from the governed facts that
     produce them (`inbox-item-v1`).
  4. **THE EXISTENCE SENTINEL + D2**: all seven decision kinds
     written to the ledger in the ratified event shape (raw at WS1 —
     the door does not exist); the computed queue IDENTICAL with
     decisions present vs absent; the compile-gate verdict unchanged
     (THE SILENT VETO refused: the risk-accepted HIGH still blocks);
     severity unchanged; the planted existence filter caught.
  5. **THE KNOWLEDGE FINGERPRINT**: every governed table
     byte-identical through 7 stewardship writes (only the ledger
     grew); every decision carries the deciding human's identity
     fact and validates against the spec on its ledger bytes.
  6. **STRUCTURAL AGENT REFUSAL, door-aware**: no AGENT-permitted
     role carries `assets:review` (AGENT_CONSUMER = {mcp:consume},
     frozen); the MCP gateway is stewardship-silent ([PMD] holds);
     the route manifest matches its guard (87 — the door does not
     exist yet); the part detects a stewardship route dynamically
     and live-refuses an AGENT bearer on it the moment WS2 mounts
     one — **the guard is waiting for the door, zero edits needed**.

**Regression at the gate**: Guard 7 green; full harness
**75/75** green (the guard auto-discovered as the 75th suite);
route manifest digest unchanged (87 — no door yet); MCP frozen at 9;
D24 at 28/305.

**THE GATE (per WS0): user ratification of the guard evidence and the
key ruling as proven is now requested. WS2 (the one route + the queue
join, on Opus per the recorded routing) starts only on ratification.**
