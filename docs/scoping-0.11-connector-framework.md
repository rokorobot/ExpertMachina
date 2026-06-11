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
revision? does policy fire?).

## Provider contract (discovered in Phase 1 — supersedes the discover/fetch sketch)

```
ConnectorProvider must expose:

1. validate()
   Confirms the source is reachable/usable.
   Provider-specific. LocalFolder checks os.path.isdir.
   The framework must not know what "reachable" means.

2. describe()
   Returns audit-safe source context.
   LocalFolder returns root_path and extensions.
   The framework logs it without understanding provider-specific fields.
   (Regression constraint: INGESTION_JOB_STARTED payloads stay identical.)

3. discover()
   Enumerates source items as ConnectorItems.
   Provider owns traversal and URI construction.

4. fetch(item)
   Returns bytes + metadata for one item.
   Provider metadata is informational only.
   Content hash remains the framework's change verdict.
```

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

4. (From Phase 1, seam 5) Within one scan, a CHANGED item's new hash enters
   the in-scan dedup set before reconciliation, so a second item with the
   same new content in the same scan is classified DUPLICATE, not a second
   change.

These prove future providers can plug in safely; they are the contract's
test double.

IMPLEMENTED: backend/test_connector_seam.py — all four passing. The fake
provider uses non-filesystem `fake://` URIs through the real framework
end-to-end, which is itself evidence the framework holds no path
assumptions.

Contract addendum (discovered at fetch extraction): `fetch` metadata has
two well-known OPTIONAL keys the framework records into SourceDocument
context columns if offered — `size_bytes` and `modified_at`. Metadata
remains informational; these names are a soft contract so future
providers know what gets recorded.

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

## Phase 1 discovery: concern map (2026-06-11, baseline `b008512`)

Baseline: test_local_connector (1–7), test_auto_approval (1–6),
test_revision_workflow, test_governance_inbox — all green at HEAD `b008512`.
Public import surface to preserve: exactly `discover_files`,
`execute_ingestion_job`, `run_ingestion_job` (main.py + both test suites,
via `from app import connectors`).

Concern classification of connectors.py:

- **Provider** (filesystem knowledge): `discover_files` (43–52);
  `os.path.abspath` URI construction (168); `os.stat` + open/read = fetch
  (171–175, size/mtime are described context, never verdicts);
  `os.path.basename` → item name (225, 310); `os.path.isdir` preflight
  (83–84 — currently embedded in framework code, becomes `validate()`).
- **Framework** (provider-independent): job lifecycle, counters,
  per-file commits, job audit events, extraction call, policy hook
  (55–158); sha256 of fetched bytes (176); the reconciliation core —
  prior-URI lookup, hash compare, DUPLICATE/CHANGED/NEW verdicts, in-scan
  + cross-document dedup (183–221, D7 made code); document creation,
  parse, failed-parse retry cleanup (230–261, D6); `_apply_source_change`
  reconciliation incl. revisions, possibly_stale, skipped_pending_review,
  SOURCE_CHANGE_DETECTED (291–295, 318–390).

The five seams (contract decisions, preserve exactly):

1. **Extension filtering fuses two concerns**:
   `SUPPORTED_EXTENSIONS` = framework parser capability;
   `include_extensions` = operator/provider config;
   actual enumeration = the intersection ("never ingest a type the parser
   can't handle — declared, not silent"). Framework exposes its parseable
   formats; provider filters enumeration against both.
2. **Staging to UPLOAD_DIR stays framework-side** — the parser and
   `Document.file_path` need local paths, for every provider. Dest-path
   naming (`{project}_c{connector}_{hash8}_{filename}`) stays
   byte-identical.
3. **`_extract_text` is format knowledge, not source knowledge** — a .docx
   parses identically regardless of source; framework-side. It duplicates
   ingestion.py fallbacks — KNOWN DEBT, do NOT unify in v0.11 (behavior-
   change risk outside this contract).
4. **Audit payloads carry provider fields** — INGESTION_JOB_STARTED logs
   root_path/extensions; the framework logs `provider.describe()` output
   without understanding it; payloads stay identical.
5. **`seen_hashes` ordering must be preserved**: on the CHANGED path the
   new hash enters the in-scan dedup set BEFORE source-change
   reconciliation runs (line 201), so a same-scan copy of the changed
   content still dedupes. Exactly the kind of tiny behavior that
   disappears in refactors and causes duplicate/revision weirdness later
   — covered by seam test 4.

Phase 1 verdict: nothing resists separation — every line classified as
provider, framework, or a nameable seam. The hypothesis is alive, and more
honest than the original sketch.

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
