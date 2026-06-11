# v0.11 — Source Connector Framework: Scoping Brief

Agreed scope (2026-06-11, at v0.10.2 release). This is the design contract for
the milestone; read together with PROJECT_STATE.md and docs/DECISIONS.md.

## The deliverable

The FRAMEWORK is the asset; individual connectors are plugins. v0.11 is NOT
judged by new connector count. It is judged by one acceptance test:

> Can the existing LocalFolder connector be re-expressed as
> **generic sync/reconciliation framework + LocalFolder provider adapter**,
> with behavior identical to v0.10.1/v0.10.2?

If LocalFolder becomes thinner while behavior stays identical, the framework
is real. If the retrofit resists, the abstraction is wrong or premature —
that resistance is the design information, and it must be discovered against
the one provider that already has real behavior, tests, edge cases, and audit
requirements, not guessed against providers that don't exist yet.

## The hard rule

**No SharePoint, Google Drive, or Confluence provider until LocalFolder is
successfully retrofitted.** Cloud providers needing stored credentials remain
blocked on the v1.x identity layer regardless (D14).

## Agreed package layout

```
backend/app/connectors/
  framework.py            # universal sync/reconciliation engine
  providers/
    local_folder.py       # filesystem discovery + file reading only
```

(The v0.10.x `connectors.py` module becomes this package; callers —
main.py, tests — import paths update but behavior must not.)

## Responsibility split

Framework (`framework.py`) owns the universal
sync/reconciliation engine — identical for every provider:

```
discover source items → normalize URI identity → fetch content →
parse/extract text → hash → compare with previous sync state →
classify NEW / DUPLICATE / CHANGED / FAILED →
create document or candidate revision (D7) →
write audit events → run policy auto-approval (new candidates only, D17) →
return declared scan summary (D12)
```

Provider adapter (`connectors/providers/local_folder.py` or equivalent) owns
only source-specific knowledge: how to walk/enumerate the source, filter
unsupported types, open an item, build its URI, read modified time, report
fetch errors. The provider SUPPLIES items; the framework DECIDES everything
(seen this URI? same hash? duplicate? changed? new document or candidate
revision? does policy fire?). Sketch of the interface shape:

```
ConnectorProvider: discover() -> [ConnectorItem(uri, name, modified_at, ...)]
                   fetch(item) -> raw content
```

(Exact interface to be discovered during the retrofit — that's the point.)

## Invariants that must survive the retrofit (the regression contract)

- Source URI is identity within a connector (D7)
- Hash comparison, duplicate handling, CHANGED vs NEW semantics
- Candidate revision creation for changed approved assets; strictly-linear
  rule reported, never bypassed; old chunks retained for provenance
- All audit events and their provenance payloads
- Policy auto-approval runs only on newly created CANDIDATE assets,
  never on revisions (D17)
- The v0.10.1 live demo replays identically: scan → ingest/dup/fail
  accounting → edit approved source → rescan → candidate revision →
  approved content unchanged → inbox shows NEEDS_REVIEW

The existing suites (test_local_connector.py parts 1–7, test_auto_approval.py
parts 1–6) must pass unchanged — they ARE the acceptance test in executable
form. New tests cover only the framework/provider seam itself.

## Seam tests (new in v0.11): prove the boundary, not the behavior

Architecture tests against a FAKE provider — no filesystem, no UI:

1. Fake provider returns one new, one unchanged, one changed item →
   framework classifies NEW / DUPLICATE / CHANGED correctly and routes each
   (document / skip / candidate revision).
2. Provider fetch fails for one item → framework records the failure with a
   reason and continues the scan (no silent skip, no aborted job).
3. Provider supplies stable URI + metadata → framework uses URI as identity
   and content hash as the only change signal (provider metadata like
   modified_at is informational, never the change verdict).

These prove future providers can plug in safely; they are the contract's
test double.

## Interface honesty constraint

The `ConnectorItem` contract must NOT assume one file = one source item.
Enumeration shapes the interface has to survive (even before any of these
are built): a Slack export where one JSON channel file yields many
message-derived items; a git working copy where identity may include repo
path + branch; a Notion export of markdown pages plus nested assets. The
provider owns the mapping from its native shape to items; the framework
only ever sees items.

## Starting point in current code

`connectors.py` already contains both halves mixed: `discover_files` is
provider-ish; `_ingest_one` / `_apply_source_change` / job accounting are
framework-ish; the policy hook is framework-ish. The retrofit is a separation,
not a rewrite.

## Earned afterwards (not before)

- A first-class "Sources & Connectors" UI area — justified by plurality (D8)
  only once a second provider type actually exists.
- Second provider candidates after the retrofit proves out: ones that need no
  stored credentials first (Slack export folder, Notion export folder, git
  working copy, markdown directory, ZIP export) — chosen to exercise a
  DIFFERENT enumeration shape, not for connector coverage. Cloud OAuth
  providers wait for v1.x identity.
