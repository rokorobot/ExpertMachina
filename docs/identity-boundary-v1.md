# Identity Boundary — v1.0 Design

> Ratified scope from the v1.0 scoping session (June 2026, post-v0.12.0).
> This is the build contract for the v1.0.0 release. D20 is ratified in
> docs/DECISIONS.md only when the boundary ships with evidence.

## Constitutional ruling: the boundary is the release

v1.0 ships as **one release** with internal workstreams — never as separate
"identity evidence" / "authentication" / "roles" releases. Rationale (ruled
at scoping): an evidence-only release would record
`authentication_method = ASSERTED` everywhere — technically honest (D12),
architecturally clean, but operationally any local browser could still claim
to be GovernanceOfficer. The evidence would faithfully record assertions
while the system still could not answer the enterprise-boundary question
*"who performed this action?"* — only *"someone asserted they were X."*
That is precisely the false-assurance failure D14 forbids. A boundary either
exists or it doesn't; the moment the system can answer

> Who did this, under what authority, authenticated how, using which
> credential lineage?

for every governed action, v1.0 has arrived. Until then, D14 remains in
force (single operator, actor strings, no false assurance).

**v1.0.0 core boundary (minimum viable identity boundary):**

- Principal registry
- IdentityFact (immutable evidence)
- Password authentication
- API tokens
- Role assignment
- Authorization checks
- Actor resolution dependency
- Migration of existing actor strings

**v1.1 enterprise extensions (integrations, not boundary shape):**
OIDC, SAML, SSO, SCIM, LDAP, Azure AD, Google Workspace — alternative ways
to *establish* identity; they do not change what the boundary records or
decides. Stored provider/connector credentials (the D19 and D14 unblocks
for cloud connectors) are also v1.1: D19 says keys stay environment-based
"until the v1.x identity/credentials layer exists" — the boundary is that
layer's prerequisite, and cloud-provider OAuth is an integration in the
same sense SSO is.

## D20 (candidate — ratify with evidence at release)

> Callers propose identity. The identity boundary decides actor.
> Governed actions must record identity facts as immutable historical
> evidence at action time. Future user-table state must never be
> required to explain past governed actions.

Fourth instance of the family principle (D17/D18/D19):
*Proposal and Decision must be separated. Convenience proposes.
Governance decides.* Governance distrusts **reconstruction**, not users.

## Acceptance test (the Alice test)

Operator Alice approves asset 42. Six months later — after her role
changed, her name changed, her password rotated, her account was
deactivated — the system proves: who Alice was, what role she held at
that moment, what action she performed, and which credential
authenticated her. If the answer requires resolving a mutable users
table, the model is too shallow. `backend/test_identity_boundary.py`
encodes this end-to-end; v1.0.0 does not tag until it passes.

## Principal taxonomy (five kinds)

Derived from the de facto actor vocabulary observed in the v0.12.0 audit
survey (11 routes accepting caller-supplied actor strings; hardcoded
frontend names; env-asserted MCP identity):

| Kind | Today's strings | Identity established by |
|---|---|---|
| HUMAN | "GovernanceOfficer", "ExpertReviewer", "operator" | Password-authenticated session |
| DELEGATED | "policy:X", "connector:Y" | Never authenticates — acts because a governed object exists; identity = the governed object + the causal chain (`on_behalf_of`) |
| SYSTEM | "system", "conflict_engine", "verification_engine", "policy_engine" | Internal principals, no credentials, method=INTERNAL |
| SERVICE | future webhooks, CI integrations, schedulers, background workers | API tokens; non-human, non-agent |
| AGENT | MCP consumers ("claude-desktop-rk") | API tokens + governed clearance (replaces EM_AGENT_ID/EM_AGENT_CLEARANCE env assertion) |

DELEGATED vs SYSTEM vs SERVICE: policies and connectors are *delegated*
(their authority flows from a governed object and a triggering action);
the engines are *system* (the platform acting as itself); webhooks and
schedulers are *services* (external automation with their own
credentials, but not knowledge-consuming agents).

## Schema

The constitutional symmetry: **Principal changes; IdentityFact never
changes** — mirroring KnowledgeAsset (mutable head) / AssetRevision
(immutable history). D1 justifies the IdentityFact table: identity-at-
action-time is a fact that does not survive otherwise. "Who approved
revision 42?" must resolve to `IdentityFact #183`, not to AuditEvent
details-JSON parsing, and never to today's users table.

### Principal (mutable registry)

```
id, name (unique slug), display_name, kind (HUMAN|DELEGATED|SYSTEM|SERVICE|AGENT),
role (HUMAN/SERVICE/AGENT; see roles), clearance (AGENT only),
active (no delete — deactivate, D17 pattern), created_at, created_by
```

### Credential (governed lineage; no delete — revoke)

```
id, principal_id, kind (PASSWORD|API_TOKEN|SESSION), secret_hash,
fingerprint (stable public identifier, e.g. cred_<id>:<sha256-prefix>),
name/label, created_at, expires_at, revoked_at, last_used_at
```

Rotation revokes the old row and creates a new one — credential lineage
survives the way revision lineage does. Plaintext tokens are shown once
at creation; only hashes are stored (D19: the store never holds usable
secrets it doesn't need — hashes verify, they don't reveal).

### IdentityFact (immutable evidence — the ClaimVerdict pattern)

```
id, principal_id, principal_name + display_name (as at action time),
principal_kind, role_snapshot, authentication_method
(PASSWORD|API_TOKEN|DELEGATED|INTERNAL), credential_fingerprint (nullable
for SYSTEM/DELEGATED), on_behalf_of_fact_id (nullable self-FK: the causal
chain for DELEGATED actors), created_at
```

No status column, no reviewer fields, never updated (D3 applied to
actors). The boundary mints **one fact per authenticated request** that
performs a governed write; every record written in that request
references it. DELEGATED chains: a scan started by Alice produces
`connector:X` facts with `on_behalf_of` → Alice's fact; `policy:Y` facts
chain to the ingestion job's fact (generalizing D17's triggering-job
provenance).

### Landing-pad upgrades (additive, nullable — `_ensure_columns`)

`identity_fact_id` FK added to AuditEvent, AssetReview, AssetRevision.
Existing string columns (actor, approver, approved_by) remain and are
populated from the fact's display name — readable history, single source
of truth. ClaimVerdict keeps evaluator_type/evaluator_id (the engine is a
SYSTEM principal; linkage can come later without schema change).

## Actor resolution dependency (the boundary itself)

One FastAPI dependency resolves every governed request:
session/bearer token → Credential → Principal → minted IdentityFact →
an `Actor` object handed to routes and crud. **All 11 caller-supplied
actor ingress points are removed** (query params `?actor=`, body fields
`reviewer`/`created_by`/`actor`, hardcoded frontend names, the
`"user"` literal in package compilation). This is a breaking API change —
v1.0 is the major version where that is allowed. crud-level functions
take the Actor object, not strings; a string-typed actor parameter
becomes a type error, which is the structural guarantee the seam tests
assert.

MCP gateway: `EM_AGENT_TOKEN` replaces `EM_AGENT_ID`/`EM_AGENT_CLEARANCE`.
The token resolves to an AGENT principal whose clearance is governed in
the registry, not asserted by env. Unauthenticated MCP access is
**refused** (a boundary that grants courtesy access is not a boundary);
the refusal is audited.

## Authentication

- **Passwords**: argon2 (or bcrypt via passlib) hashes on Credential
  rows. Login issues an opaque session token (Credential kind=SESSION,
  hashed at rest, expiring), sent as `Authorization: Bearer`. The session
  credential records which password credential authenticated it —
  lineage is complete.
- **Bootstrap**: first startup with zero HUMAN principals creates
  `admin` with a one-time generated password printed to the console,
  `must_change_password` enforced. SYSTEM principals (system,
  conflict_engine, verification_engine, policy_engine) are seeded.
  DELEGATED principals are auto-registered when their governed object
  (policy, connector) is created, and backfilled for existing ones.
- **API tokens**: created/revoked by ADMIN in Settings; shown once;
  scoped to a SERVICE or AGENT principal.

## Authorization (roles)

Role set derived from the observed vocabulary, not invented:

| Role | Permissions |
|---|---|
| ADMIN | everything incl. principals, credentials, LLM settings |
| GOVERNANCE_OFFICER | approvals, revisions, conflicts, policies, package compile |
| REVIEWER | asset review, claim-verdict review |
| VIEWER | read-only |

Role→permission mapping is code-resident (governed in code) for v1.0;
custom roles are a later decision. Enforcement at the boundary:
`actor = Depends(require("assets:approve"))`. Reads require an
authenticated session (the UI logs in); MCP clearance remains the
separate read-channel control it already is (D10). Reviewer/approver
separation of duties stays in Future Direction — roles make it
*possible*, v1.0 does not impose it.

D5 check: the boundary authenticates **callers**, it does not gate
**ingestion** — a scan triggered by an authorized actor runs with zero
new checkpoints; the only hard gate remains compile time.

## Migration (honest history — D12)

- Existing AuditEvent/AssetReview/AssetRevision rows keep their actor
  strings with `identity_fact_id = NULL` — truthfully pre-boundary.
  **No retroactive IdentityFacts are ever fabricated.** UI labels legacy
  records as such.
- Schema changes are additive via `database._ensure_columns()`.
- Frontend: login screen, session handling, current-user display,
  hardcoded actor names deleted, Settings gains Users & Tokens
  administration (ADMIN only), role-aware action visibility.

## Workstreams (internal phases of ONE release)

| WS | Content | Checkpoint |
|---|---|---|
| 1 — Evidence | Principal/Credential/IdentityFact tables, resolution dependency, all 11 ingress conversions, delegated chains | seam + product tests green; no string actor reaches crud |
| 2 — Authentication | password login, sessions, API tokens, MCP token auth, bootstrap | unauthenticated write refused; MCP env assertion gone |
| 3 — Authorization | role checks per route, frontend role-aware UI, Users & Tokens admin | VIEWER cannot mutate; HTTP suite proves per-role 403s |
| 4 — Migration & hardening | legacy marking, bootstrap polish, deployment docs, PROJECT_STATE/DECISIONS regeneration | Alice test passes end-to-end → tag v1.0.0, ratify D20 |

Workstream order is buildable order; nothing releases until WS4's
checkpoint. Test layers follow the v0.11.1 contract: product
(test_identity_boundary.py — the Alice test), architectural (boundary
seam: crud refuses non-Actor identities), transport (HTTP suite: auth
required, per-role 403s, actor params rejected).
