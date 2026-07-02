# Governed Credential Store & First Cloud Connector — v1.2.0 Design

> Ratified scope from the v1.2.0 scoping session (July 2026, post-v1.1.1).
> This is the build contract for the milestone. Its input was the
> pre-scoping brief (docs/scoping-1.2-credentials-cloud-connector.md); the
> brief's candidate rulings were confirmed or refined here. **D25** is
> recorded in docs/DECISIONS.md and enforced structurally (WS0).

## The milestone's nature

v1.0 built the identity boundary for credentials EM **issues and verifies**
(inbound: hashes verify, never reveal). v1.2.0 adds the species v1.0
deliberately excluded: credentials EM **holds and presents outward** — a
SharePoint client secret first, eventually LLM provider keys. This is the
D19/D14 unblock, taken now that the boundary exists. The SharePoint
connector is the acceptance driver; the credential store is the
constitutional content.

The two species stay in separate tables — the v1.0 `credentials` table's
hash-only contract is a security property and is not touched:

| | Inbound (v1.0, unchanged) | Outbound (new, v1.2.0) |
| :--- | :--- | :--- |
| Purpose | verify a caller | authenticate EM to an external system |
| Storage | hash only | encrypted at rest, decryptable |
| Reveal | plaintext once, at issuance | **never — the caller supplied it; no surface ever returns it** |
| Lineage | revoke-never-delete | same (rotation = revoke old row + create new) |

Note the asymmetry in the Reveal row: inbound secrets are minted by EM and
must be shown once; outbound secrets are supplied BY the operator, so there
is no legitimate reason for any API surface to ever return one. "Never" is
absolute, not "once".

## The evidence question, answered (the scoping opener)

> What custody evidence must exist for an outbound credential so that, six
> months later, the system can prove which secret authenticated which scan,
> who controlled it, and that it never leaked into any surface?

1. **Which secret, which scan** — every credential generation carries a
   public `fingerprint`: a random identifier assigned at creation,
   deliberately NOT derived from the plaintext (a derived fingerprint is an
   oracle). Every scan's IngestionJob records the credential id; every scan
   emits `CREDENTIAL_USED` with id + fingerprint + granted scopes. Rotation
   links generations via `replaces_credential_id`. Scan → job → generation
   resolves by join, never by reconstruction (D20 posture).
2. **Who controlled it** — custody actions (create, rotate, revoke) are
   governed writes carrying identity facts; the row records its owning
   principal; `created_identity_fact_id` is NOT nullable — no pre-boundary
   outbound credentials exist.
3. **Never leaked** — provable only structurally: the custody sweep guard
   (WS0) seeds a sentinel secret and adversarially sweeps every surface.
   In CI permanently.
4. **How much it was allowed to reach** — granted permission scopes are
   custody evidence (D25 final sentence): recorded at creation, carried on
   use events, never inferred.

## Ratified rulings (scoping session, 2026-07-02)

### 1. D25 — Credential Custody (full text in docs/DECISIONS.md)

Outbound credentials are governed secrets: stored encrypted, never returned
by any API, never exported, never logged. The ledger records custody
events, never contents. Configuration and connectors reference credentials
by id. Granted scope is custody evidence. The family shape, fifth instance:
**routes and connectors propose credential use; the custody layer decides
release.**

### 2. Encryption: envelope scheme under an env master key

`EM_SECRET_KEY` (env-provided, consistent with the D19 tier; OS
keystore/KMS is a later enterprise extension). The master key wraps a
per-credential data key; the data key encrypts the secret. Master-key
rotation re-wraps data keys — **no secret is ever re-entered**. Only secret
material is encrypted; non-secret coordinates (tenant id, client id) are
ordinary custody metadata. A missing or wrong master key is reported loudly
at startup (the `validate_boundary` pattern); recovery is a documented
procedure, never a bypass (D21 posture).

### 3. A new 12th permission: `credentials:manage`, ADMIN-only

Custody must not ride on `connectors:manage`: KNOWLEDGE_OPERATOR holds it,
and SERVICE principals may hold KNOWLEDGE_OPERATOR — credentialed
automation must never mint or rotate outbound secrets. The seam:

- **Administer** (create / rotate / revoke / list metadata) requires
  `credentials:manage` — ADMIN-only in the initial matrix.
- **Use** stays where it lives: a scan under `connectors:manage` PROPOSES
  use of the connector's bound credential; the custody layer DECIDES
  release (status ACTIVE, purpose matches, scopes recorded) and logs
  `CREDENTIAL_USED`. Plaintext reaches the provider adapter in memory at
  use time and nowhere else.

Denied custody actions are AUTHZ_DENIED audit events (v1.0 discipline,
already enforced by `require_perm`).

### 4. Use-event granularity: per scan

`CREDENTIAL_USED` is written once per scan (linked to the IngestionJob),
not per HTTP request — the scan is the governed act; per-request events
would bloat the ledger without adding provable custody information.

### 5. LLM provider keys: store generic, migration deferred

The store carries `purpose = CONNECTOR | PROVIDER` from day one, but
migrating OPENAI/ANTHROPIC keys out of env vars is OUT of v1.2.0
acceptance — it touches D19's resolution invariant and is its own explicit
later step (v1.2.x candidate). Until then D19 holds unchanged: provider
keys stay env-based.

### 6. Graph scope minimization

`Sites.Selected` is the documented recommended minimum (per-site grants);
`Sites.Read.All` the fallback for tenants without per-site consent. The
provider is scope-agnostic — it reports what Graph permits, verbatim
(D18: no policy in the provider). Whatever was granted is recorded on the
credential and carried on use events.

### 7. WS2 gate evidence: fake Graph in CI + one live run

CI cannot hold a live tenant. The provider takes an injectable transport
seam; CI drives it with a fake Graph transport (the `fake://` pattern that
ratified D18). ONE manual live-tenant scan is recorded as gate evidence in
this document at WS2 acceptance. Live verification is required for the
gate; it is not required to be repeatable in CI.

## Schema (justified by D25; snapshot updated in the same commit — D24)

New table `external_credentials` (working columns; exact shape settles in
WS0/WS1, additions require no new ruling, new WRITABLE semantics do):

- identity: `id`, `fingerprint` (random, public), `name`,
  `purpose` (CONNECTOR | PROVIDER), `owner_principal_id`
- custody metadata: `granted_scopes` (JSON), non-secret coordinates
  (e.g. tenant id, client id) as metadata JSON
- secret material: `ciphertext`, `wrapped_data_key`, `key_id`
  (master-key generation)
- lineage: `status` (ACTIVE | REVOKED), `replaces_credential_id`,
  `created_at`, `created_identity_fact_id` (NOT nullable),
  `revoked_at`, `revoked_identity_fact_id`

`source_connectors` gains nullable `external_credential_id` (LocalFolder
needs none — honest NULL, not a dummy credential).

New audit events: `EXTERNAL_CREDENTIAL_CREATED`, `_ROTATED`, `_REVOKED`,
`_USED` — custody events, never contents. (Amended at WS0: the working
names `CREDENTIAL_*` collide with the v1.0 boundary's inbound events —
`CREDENTIAL_CREATED`/`_REVOKED` already mean password/token lineage. The
two species stay distinguishable in the ledger, exactly as in storage.)

API surface: POST create / POST rotate / POST revoke /
GET list-and-detail returning **metadata only**. There is no reveal
endpoint and never will be one under D25.

## Hard boundaries for this milestone

- No surface returns, exports, logs, or projects a stored secret. Ever.
- **No live SharePoint (or any real tenant) secret may enter CI, test
  fixtures, audit payloads, schema/test snapshots, or .empkg artifacts.**
  CI and fixtures use synthetic sentinel secrets only; the live-tenant
  credential exists solely in the operator's environment and the encrypted
  store, and the WS2 live-run gate evidence records custody metadata
  (fingerprint, granted scopes) — never material.
- The v1.0 `credentials` table is untouched.
- No provider-key migration (ruling 5). No SSO/SAML/SCIM. No
  Confluence/Drive providers. No orchestration surface (D22).
  **D23 stays DEFERRED.**
- The D18 tradeoff holds: the framework still fetches and hashes content —
  no metadata-based fetch skipping, even though Graph offers timestamps.
- Framework, reconciliation, change detection, revision machinery, and
  approval policies are NOT modified by the SharePoint provider.
- Every schema change lands with the D24 frozen-snapshot update in the
  same commit, citing D25.

## Workstreams and acceptance gates

### WS0 — D25 + the custody guard

D25 recorded in docs/DECISIONS.md; the `external_credentials` table and
connector column land WITH the updated D24 schema snapshot in the same
commit; the custody sweep guard lands BEFORE any secret-handling code path
ships — the lock goes on the door first.

**Pass condition:**
> `backend/test_credential_custody.py` (in CI permanently) seeds a
> sentinel secret through the real creation path and adversarially sweeps
> every surface for it: every API response (including the credential GET
> itself), audit event payloads, log output, .empkg exports, lineage and
> inbox projections, and error responses from forced failure paths. Any
> hit fails CI. The D24 schema guard is green with the updated snapshot,
> updated in the same commit as the D25-justified schema change.

Evidence: `backend/test_credential_custody.py` +
`test_workbench_projection.py` snapshot diff (one commit).

**Gate: PASSED (accepted July 2026).** Accepted on the constitutional
point proven: the custody guard exists BEFORE the credential door opens.
The guard's five parts landed in CI permanently: frozen custody schema
shape (no plaintext-shaped column, species separation from the v1.0
inbound table), loud refusal without `EM_SECRET_KEY`, the real creation
path (envelope encryption, random plaintext-independent fingerprints,
scope evidence, D20 seam), the sentinel sweep (every table, audit
payloads, reprs, failure paths, raw database bytes), and the adversarial
self-proof — CI demonstrably catches the two most likely regressions
(encryption silently disabled; a plaintext-shaped column). D24 snapshot
updated in the same commit (27 tables, 288 columns); all 20 suites green,
`test_connector_seam.py` untouched.

**Accepted deviation:** custody audit events use `EXTERNAL_CREDENTIAL_*`
rather than `CREDENTIAL_*`, because v1.0 already uses
`CREDENTIAL_CREATED` / `CREDENTIAL_REVOKED` for inbound identity
credentials. This preserves the D25 species separation in both storage
and audit history.

### WS1 — The custody layer

Envelope encryption under `EM_SECRET_KEY`; `credentials:manage` permission
(ADMIN-only) enforced on all custody routes; custody audit events with
identity facts; rotation lineage; the internal release seam
(`custody.release` — status + purpose checked, `CREDENTIAL_USED` written,
plaintext handed to the caller in memory only).

**Pass condition (gate text to confirm at WS0 acceptance):**
> The Alice test for secrets: create a credential, run scans, rotate it,
> run more scans, revoke the old generation. Six months later (i.e. from
> the ledger alone): every historical scan resolves to the exact
> credential generation that authenticated it; the revoked generation is
> provably unusable (release refused, refusal audited); rotation never
> re-entered any secret; no custody event contains secret material.
>
> Boundary integrity: a principal without `credentials:manage` cannot
> create, read metadata of, rotate, or revoke credentials — and each
> denial is an AUTHZ_DENIED audit event carrying the actor's fact.
>
> Custody guard and D24 guard remain green.

Evidence: `backend/test_credential_custody.py` (extended),
`test_authorization.py` (the 12-permission grid), master-key rotation
covered without secret re-entry.

**Gate: PASSED (accepted July 2026).** The Alice test for secrets +
boundary-integrity denials proven end to end, preserving the D25 line:
secrets are usable through governed custody release but never become
visible governed facts. Evidence (custody suite parts 6–8 + the extended
authorization grid; all 20 suites green): the ADMIN
create/use-for-scan/rotate/revoke lifecycle; non-admin custody routes
denied with audited AUTHZ_DENIED; operators scan admin-bound connectors
under connectors:manage but cannot bind credentials (binding is a
custody act, payload-dependent authorization); revoked generations can
be neither released (refusal = custody event; a refused scan FAILS
loudly) nor bound (409); every EXTERNAL_CREDENTIAL_USED carries
fingerprint, key generation, granted scopes, connector context, job id,
and identity fact — the ledger alone resolves which generation
authenticated which scan across rotation; the route-level sentinel sweep
covers custody APIs, connector/job endpoints, and the audit surface;
master-key rotation re-wraps with ciphertexts byte-identical (no secret
re-entered), key material env-only. Language discipline held: "release"
is internal seam vocabulary; operator surfaces say "use credential for
scan".

**Accepted ruling (WS1): rotation re-points bound connectors to the
successor generation.** Connectors bind the LOGICAL credential;
credential generations remain custody lineage; historical
EXTERNAL_CREDENTIAL_USED events keep the exact generation/fingerprint
used for each scan. Rotation preserves operational continuity without
rewriting history; the re-point is recorded in the
EXTERNAL_CREDENTIAL_ROTATED event (`rebound_connector_ids`).

**Accepted ruling (WS1): CUSTODY_MASTER_KEY_ROTATED is a separate
custody event type.** Master-key rotation is store-wide, not
credential-specific; the audit fact records old key id, new key id,
credential/data-key count, actor/identity fact, and timestamp — never
key material.

### WS2 — SharePointProvider

The D18 payoff: a provider speaking the existing four-method contract
(`validate / describe / discover / fetch`) via Microsoft Graph
(client-credentials flow; the client secret released through WS1 custody).
URI = drive-item identity; the framework's content hash remains the only
change verdict; SharePoint metadata (library, content type, modified-by,
tenant approval status where exposed) rides in `ConnectorItem.metadata`
verbatim — v1.2.x Tier-0 policies will consume it from there; the provider
carries no policy.

**Pass condition (gate text to confirm at WS1 acceptance):**
> A SharePoint document library scans end-to-end into ordinary Documents
> and CANDIDATE assets; rescans classify NEW / DUPLICATE / CHANGED by
> content hash exactly as LocalFolder does; CHANGED approved content flows
> through the D7 revision machinery untouched.
>
> All pre-existing connector suites pass UNCHANGED;
> `test_connector_seam.py` is untouched; the framework diff is zero (a
> provider was added, nothing was modified).
>
> CI drives the provider through an injected fake Graph transport,
> including auth-failure, throttling/permission-error, and pagination
> paths — every failure declared, never silent (D12).
>
> ONE live-tenant scan is performed manually and recorded as gate
> evidence here, including the granted scope set as it appears in
> custody evidence. The recorded evidence contains custody metadata
> only — no live secret enters the repository, CI, fixtures, snapshots,
> or any artifact (the hard boundary above applies to gate evidence
> itself).

Evidence: `backend/test_sharepoint_provider.py` (fake transport, in CI);
live-run record appended at acceptance.

**Gate: PASSED — CI gate complete; live-tenant verification pending
availability (accepted July 2026).** The ratified gate evidence mode
(fake Graph in CI + one live run) explicitly permits this split; no live
SharePoint secret may enter CI or fixtures, and the slot is recorded
honestly as pending, never silently completed. Evidence:
- SharePointProvider implements the four-method contract over Graph;
  metadata reported VERBATIM (webUrl, eTag/cTag, modified time,
  modified-by, mime type, tenant-exposed listItem fields when present) —
  absent means absent (D12); the provider is policy-free and
  structurally pure (stdlib + connector contract only, asserted in CI).
- URI = Graph drive-item identity; the framework's content hash stayed
  the only change verdict: every-timestamp-bumped/zero-content-changed
  scanned as ALL DUPLICATE with the new timestamps recorded as context
  (the D18 Test C trap, re-proven on the credentialed path).
- The client secret enters only through custody release-for-scan;
  exactly one EXTERNAL_CREDENTIAL_USED per scan; a bad credential fails
  the JOB loudly with the Graph error, echoing no secret; the
  full-database sweep stays clean.
- Fake Graph CI covers auth failure, permission denial (errors name
  Sites.Selected / Sites.Read.All), pagination + nested folders,
  throttling (Retry-After honored, persistent throttle declared),
  fetch failure, duplicates, and changed content.
- Framework decision logic unchanged — the accepted diff is the
  `_provider_for` registry dispatch (the second-provider change D8/D18
  anticipated) + non-secret coordinate pass-through;
  `test_connector_seam.py` untouched and green; all 21 suites green.

**Live SharePoint scan evidence to append when tenant access exists:**
- tenant/library identifier (redacted or non-sensitive)
- credential fingerprint
- granted scopes
- connector id/type
- scan/job id
- discovered/fetched/ingested/duplicate/changed/failed counts
- confirmation no secret material appears in gate evidence

### WS3 — Sources & Connectors UI area

Earned by D8 — the second provider type creates genuine plurality. A
top-level **Sources & Connectors** area: connector CRUD (both provider
types; LocalFolder administration moves here from Document Inventory),
credential binding, scan history, and the credential administration
surface (create / rotate / revoke; metadata + fingerprint + custody
history only). Visibility over existing facts; the only writes are
connector and credential administration, both governed by WS1.

**Pass condition (gate text to confirm at WS2 acceptance):**
> A Sources & Connectors area exists. An ADMIN can create a credential
> (secret entered once, never displayed again — no reveal affordance
> exists anywhere in the UI), bind it to a SharePoint connector, scan,
> and read scan history and custody history.
>
> Role-awareness mirrors the backend: custody controls require
> `credentials:manage`; connector controls require `connectors:manage`;
> others see projections only.
>
> No new backend writes beyond the WS1 custody routes and existing
> connector routes. No persisted UI state. D24 + custody guards green.
> Full frontend checks pass.

**Language ruling:** the UI says **"credential"** and **"rotate"** /
**"revoke"** — never "password", never "delete". Nothing in the UI ever
implies a secret can be viewed.

## Build order

WS0 first, alone — guard before door, exactly as v1.1.1 did. Then
WS1 → WS2 → WS3, each starting only after the prior gate passes. Gate
texts for WS1–WS3 are confirmed (or refined) at the preceding acceptance,
per the established rhythm. Any reversal of a ruling above is recorded as
a supersession in docs/DECISIONS.md.
