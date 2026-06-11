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
  __init__.py             # preserves existing import surface
  framework.py            # universal sync/reconciliation engine
  models.py               # ConnectorItem, fetch/reconciliation result types
  exceptions.py
  providers/
    __init__.py
    local_folder.py       # filesystem discovery + file reading only
```

(The v0.10.x `connectors.py` module becomes this package; callers —
main.py, tests — import paths update but behavior must not.)

## Success criterion (the whole milestone in one table)

```
User experience:    identical
API behavior:       identical
Database behavior:  identical
Tests:              identical (zero assertion edits)
Architecture:       different
```

If a user can tell the difference, something probably went wrong.

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

## Execution order (agreed 11-step plan)

1. **Move code into the package structure** — no behavior change, imports
   preserved. Structure first, extraction second.
2. **Define the provider contract** — `ConnectorProvider` (discover, fetch)
   and `ConnectorItem` (uri, name, metadata). Provider describes; it never
   decides duplicate / changed / revision / policy / approval.
3. **Extract discovery** — `discover_files` → `providers/local_folder.py`,
   returning ConnectorItems and nothing else.
4. **Extract the reconciliation engine** → `framework.py`: URI identity,
   hash comparison, NEW / DUPLICATE / CHANGED / FAILED classification.
   The framework is the ONLY place that can pronounce those verdicts (D7).
5. **Extract ingestion** — document creation, candidate assets, audit events.
6. **Extract revision logic** — `_apply_source_change` semantics become
   provider-independent framework behavior.
7. **Extract the policy hook** — provider → framework → documents →
   candidates → policy evaluation; new candidates only, never revisions (D17).
8. **Make LocalFolderProvider thin** — walk filesystem, build URIs, read
   files, return content. **If LocalFolderProvider is still huge, the
   extraction failed** — that's the heuristic, not a style preference.
9. **Regression** — existing suites pass with zero rewrites.
10. **Seam tests** — see below.
11. **Architecture review before closing**: could a GitProvider /
    SlackExportProvider / NotionExportProvider be added WITHOUT touching
    framework.py, policy.py, the revision workflow, or the audit system?
    Yes → the framework succeeded. "I'd need to modify framework logic" →
    the abstraction is still wrong; fix it before calling v0.11 done.

## Seam tests (new in v0.11): prove the boundary, not the behavior

Architecture tests against a FAKE provider — no filesystem, no UI:

1. Fake provider returns one new, one unchanged, one changed item →
   framework classifies NEW / DUPLICATE / CHANGED correctly and routes each
   (document / skip / candidate revision).
2. Provider fetch fails for one item → framework records the failure with a
   reason and continues the scan (no silent skip, no aborted job).
3. Provider supplies stable URI + metadata → framework uses URI as identity
   and content hash as the only change signal (provider metadata like
   modified_at is informational, never the change verdict). Executable form:
   `modified_at` changes while content hash is unchanged → verdict is
   **NOT CHANGED** (duplicate). This test is the D18 candidate made runnable.

These prove future providers can plug in safely; they are the contract's
test double.

## Hard invariant: providers describe, the framework decides

```
URI          = identity
content hash = change verdict
metadata     = context
```

Providers may describe source state; only the framework decides
reconciliation. `modified_at` and other provider metadata may explain
provenance but must never decide truth — this forecloses the classic
enterprise-connector bug pair (timestamp changed → false change;
timestamp unchanged → missed content change) and keeps future
SharePoint/Drive/Notion/export providers from smuggling correctness
assumptions into provider code. Candidate for ratification as a
D-register ruling when v0.11 ships.

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

## Status of this brief: hypothesis under test, not destiny

This document records what we BELIEVE the correct architecture is; the
retrofit is the experiment that decides whether it's TRUE. The single-
sentence framing of the milestone: *test whether acquisition behavior can
survive separation from acquisition source.* Three acceptable outcomes:

- **Yes** → a platform.
- **Partially** → a better architecture than imagined, amended here.
- **No** → a corrected understanding of the system, recorded here.

All three create knowledge; only one creates the exact framework imagined
today, and that is fine.

**On resistance** (e.g. a step reveals reconciliation depends on
source-specific semantics nobody anticipated): do NOT hide the complexity,
force it into the framework, and declare the step passed. Instead: record
the observation, challenge the assumption, revise this brief in daylight,
and defer any D-register ratification. Forcing reality to comply with a
hypothesis is the failure mode; amending the hypothesis is the process
working — the same process that produced D17.

## Earned afterwards (not before)

- A first-class "Sources & Connectors" UI area — justified by plurality (D8)
  only once a second provider type actually exists.
- Second provider candidates after the retrofit proves out: ones that need no
  stored credentials first (Slack export folder, Notion export folder, git
  working copy, markdown directory, ZIP export) — chosen to exercise a
  DIFFERENT enumeration shape, not for connector coverage. Cloud OAuth
  providers wait for v1.x identity.
