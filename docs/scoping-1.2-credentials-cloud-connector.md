# v1.2 — Governed Credentials, Cloud Acquisition & Ingestion Automation: Pre-Scoping Brief

> Design constraints ruled post-v1.1.1 (July 2026), BEFORE the scoping
> session. This is input to scoping, not a build contract — the contract
> is written when the milestone is scoped. Recorded here per D16:
> repo-resident state beats chat memory.

## Strategic context: the road to the Operations Realm

The destination named at the July 2026 strategy sessions: ExpertMachina is a
**two-realm system**.

- **Knowledge Realm** (built, v0.x–v1.1.1): preserves company knowledge as
  immutable evidence, extracts and governs meaning, resolves
  trust/conflict/approval, compiles portable packages. D15 rules absolutely
  here: extract and verify, never synthesize.
- **Operations Realm** (the goal): workbenches and bound agents that query,
  diagnose, and optimize company processes using that knowledge. Synthesis
  *is* the product here — but authority is not: operational findings become
  company facts only by re-entering through the governed ingestion pipeline.

The border between the realms is the v1.1 consumption arc (Package →
Evaluation → Selection → Binding). The authorship rule that keeps the border
honest, named at these sessions and to be ratified when the first workbench
ships:

> **Humans author facts; agents propose them.**

Human decisions (directives, memos, signed policies) enter as ordinary
documents through standard ingestion → PRIMARY facts. Only agent-synthesized
findings go through the proposal lane → human gate → DERIVED facts. The
one-way valve constrains agents, not people.

**The dependency chain that fixes the milestone order:**

A real workbench needs a real corpus → real corpora live in
SharePoint/Confluence → cloud connectors need stored credentials (the gap
D19 deliberately left for v1.x). Bulk real-world ingestion without a review
avalanche needs automation → the biggest automation lever (source-authority
inheritance) needs those same cloud connectors. Workbench agents need
relational access → projection engine. Workbench findings need a return
path → proposal lane + derived source class.

Hence the arc (each milestone independently valuable; v1.3+ directional,
not locked — anticipation discipline):

| Milestone | Theme |
| :--- | :--- |
| **v1.2.0** | Governed Credential Store + first cloud connector (SharePoint) |
| **v1.2.x** (likely v1.2.1) | Ingestion automation (policy tiers) + domain classification |
| v1.3.0 | Projection engine + graph renderer (ratifies the projection rule) |
| v1.4.0 | First diagnostic workbench pilot (ratifies derived-source-class + one-way valve) |
| v1.5 | EM Vault — full human-readable rendered workspace |

This brief scopes **v1.2.0 and v1.2.x** in detail. Later milestones appear
only where a v1.2 design choice would otherwise foreclose them.

---

## v1.2.0 — Governed Credential Store & First Cloud Connector

### The milestone's nature

v1.0 built the identity boundary for credentials EM **issues and verifies**
(inbound: password hashes, token hashes — hashes verify, they never reveal).
v1.2.0 adds the species v1.0 deliberately excluded: credentials EM **holds
and presents outward** (outbound: a SharePoint client secret, a Graph API
token, eventually LLM provider keys). This is the D19/D14 unblock — "stored
provider/connector credentials land after the boundary exists" — and the
boundary now exists.

### The constitutional distinction: two credential species

| | Inbound (exists, v1.0) | Outbound (new, v1.2.0) |
| :--- | :--- | :--- |
| Purpose | verify a caller | authenticate EM to an external system |
| Storage | hash only (`credentials` table) | **encrypted at rest, decryptable** |
| Reveal | never — plaintext shown once at creation | to the provider adapter only, at use time |
| Lineage | revoke-never-delete | same (rotation = revoke old row + create new) |

Do **not** overload the v1.0 `credentials` table — its hash-only contract is
a security property worth keeping pure. Outbound secrets get their own
governed table (working name: `ExternalCredential`), owned by a principal,
scoped to a purpose (connector X / provider Y), with full custody lineage.

### Decision candidate — Credential Custody (extends D19; number assigned at ratification)

> Outbound credentials are governed secrets: stored encrypted, never
> returned by any API, never exported in any artifact or projection, never
> written into audit events or logs. The audit ledger records custody
> events — created, rotated, revoked, used — never contents.
> Configuration and connectors reference credentials by id; they never
> contain them.

This is the D9 hard rule (".empkg never contains keys") generalized to the
whole platform, and the D17/D18/D19/D20 family shape applied a fifth time:
*routes and connectors propose credential use; the custody layer decides
release.*

The sharpest statement of the distinction: **outbound credential plaintext
is not a governed fact; custody events are governed facts.** The system
governs the existence, ownership, use, rotation, and revocation of the
secret — never the secret value itself.

### Scoping questions (settle at the session, not in this brief)

1. **Encryption key custody**: env-provided master key (`EM_SECRET_KEY`)
   first — consistent with D19's "keys env-based" tier; OS keystore/KMS as a
   later enterprise extension. The scheme must make key rotation possible
   without re-entering every secret.
2. **Who may create/rotate/revoke**: which of the 11 permissions guards
   credential custody — likely a new permission rather than overloading
   `assets:approve`. Custody actions are identity-fact evidence like every
   governed decision (D20).
3. **Use-event granularity**: `CREDENTIAL_USED` per scan (not per HTTP
   request) is the likely honest-and-affordable level; ruled at scoping.
4. **LLM provider keys in scope or not**: the same store naturally serves
   D19's env tier (OPENAI/ANTHROPIC keys). Recommended: build the store
   generically, migrate provider keys only if the milestone stays lean —
   the connector is the acceptance driver, not the settings screen.
5. **Graph permission scope minimization**: what is the minimum Microsoft
   Graph permission set needed for discovery and fetch, and how is that
   granted scope recorded as credential custody evidence? In real
   enterprise deployments "SharePoint connector" is immediately a
   tenant-permission/security conversation — the ledger must be able to
   prove not just *which* credential was used but *how much* it was
   allowed to reach.

### The SharePoint provider (the D18 payoff)

The v0.11 framework retrofit was done precisely so this milestone is thin:

- `SharePointProvider` speaks the existing four-method contract
  (`validate / describe / discover / fetch` — `connectors/models.py`),
  via Microsoft Graph. URI = drive item identity; content hash = change
  verdict; metadata = context. **Providers describe; the framework decides**
  (D18) — the framework, reconciliation, change detection, revision
  machinery, and approval policies are not touched.
- Source-system metadata (library, content type, modified-by, approval
  status where the tenant exposes it) rides in `ConnectorItem.metadata` —
  v1.2.x classification and Tier-0 policies consume it from there. The
  provider carries **no policy**: it reports what SharePoint says, verbatim.
- The "Sources & Connectors" UI area is now earned (D8: second provider
  type) — connector CRUD, credential binding, scan history. Scope it as
  visibility over existing facts; the only new writes are connector/
  credential administration.

### Acceptance test candidates (gate the milestone on these)

1. **The custody proof (structural, in CI permanently)**: no API response,
   no audit event payload, no export, no projection, no log line contains a
   stored secret — tested adversarially (seed a known secret, sweep every
   surface for it), the schema-guard pattern applied to secrecy.
2. **The Alice test for secrets**: rotate a connector credential; six months
   later the ledger proves which credential generation authenticated every
   historical scan, and the revoked generation is provably unusable.
3. **The D18 proof, repeated**: a real SharePoint library scans end-to-end;
   its output is ordinary Documents and CANDIDATE assets; all pre-existing
   connector suites pass **unchanged**; `test_connector_seam.py` untouched.
4. **Boundary integrity**: a principal without the custody permission
   cannot create, read, rotate, or bind credentials — and the denial is an
   audit event (v1.0 discipline).

### Explicitly out of scope for v1.2.0

SSO/SAML/SCIM (enterprise extensions, later — they gate sales, not the
product loop); Confluence/Drive providers (adapter additions after
SharePoint proves the credentialed path); any orchestration surface;
D23 (still deferred).

---

## v1.2.x (likely v1.2.1) — Ingestion Automation & Domain Classification

### The milestone's nature

The user-stated risk: *per-document human validation is a non-workable
barrier.* The ruled answer: **humans review by exception, never by
document** — D5 ("gate deployment, never ingestion") supplied the
principle; this milestone supplies the machinery. North-star metric
(already derivable from audit events): time from document arrival to
usable expert model.

### The automation ladder (tiers 0 and 2 are this milestone)

- **Tier 0 — source-authority inheritance** (the biggest lever for
  digitally mature companies): a D17 policy matching on source-system
  governance metadata ("published in the QMS", "approved in SharePoint
  library X") auto-approves documents the company already validated. The
  company paid the validation cost once; EM must not charge it twice.
  Policy provenance records the inherited authority explicitly.
- **Tier 1 — deterministic classification policies**: shipped (v0.10.2).
- **Tier 2 — governance engines as the automated reviewer**: the deferred
  item from v0.10.2 arrives — condition-based policy rules that consult
  engine results: auto-approve when the conflict scan is clean, claims
  verify, and the document class is not sensitive. Deterministic → NLI
  ladder discipline holds; LLM-advisory classification stays later.
- **Tier 3 — humans see only exceptions**, severity-ranked through the
  existing inbox pattern. Target for a mature corpus: **≥90% of documents
  reach APPROVED untouched by humans, every one carrying machine-verifiable
  policy provenance, every exception declared** (D12 — no silent drops).

**D17 boundary, reaffirmed**: all automation applies to new CANDIDATE
assets only. Revision auto-approval stays forbidden. The known tension —
in a living KB, *revision* review is where human load will actually
accumulate — is documented here deliberately and left unresolved: future
risk-based revision policies (diff-outside-claims, NLI semantic
equivalence) would amend D17 and are scoped only when a real deployment
shows the pressure. Never smuggled in.

### Domain classification (the taxonomy layer)

Ruled at the July 2026 sessions:

- Assets gain a **governed domain field — a hierarchical path**
  (`finances/accounting`), assigned at ingestion by classification policies
  (connector structure + metadata rules; the D17 ladder), human-correctable
  through the normal review surface.
- **Domains and asset types are orthogonal**: domains are business
  dimensions (HR, finances, …); types are semantic species (claims, rules,
  processes, entities). Never siblings in any hierarchy.
- **Reorganizations nest by default** (prefix scopes — future bindings,
  clearances, workbench scopes — survive splits); replacement is an
  explicit, audited taxonomy decision with the old→new mapping recorded.
- The taxonomy lives in the **database as governed metadata**. Folder
  structures (v1.5 vault) and graph groupings (v1.3) are *renderings* of
  it — moving a rendered file never reclassifies anything (D24 posture).
- Transactional records (invoices, wage records) are **not knowledge
  assets** — EM governs what the company *knows*, not every record it
  *has*. Sources and evidence, yes; asset mirroring, no. This scope trap
  is named here so it is refused deliberately, not accidentally.

### Acceptance test candidates

1. Bulk-scan a realistic mixed corpus through a Tier-0 + Tier-2 policy
   set: ≥90% auto-approved with policy provenance, 100% of exceptions
   present and severity-ranked in the inbox, zero revisions auto-approved.
2. Taxonomy proof: reorganize a domain (split `finances` →
   `finances/accounting` + `finances/treasury`) by policy change alone —
   assets reassigned with audit provenance, no content or history touched,
   prefix queries still resolve the parent domain.
3. The D17 structural test: the automation diff adds no second approval
   path — every auto-approval flows through `crud.update_knowledge_asset`
   exactly as v0.10.2 established.

---

## Where v1.2 must not foreclose the later arc

- **Projection engine (v1.3)**: renderer-agnostic from day one — facts →
  renderer → files; graph.json first, vault renderer later. Nothing in
  v1.2 should assume a single export shape. Projection rule candidate
  (ratify at v1.3): *no projection is ever authoritative; every projection
  regenerates from governed facts; ingestion only through connectors;
  every render stamped with `rendered_at` + audit cursor.*
- **Derived source class (v1.4)**: PRIMARY vs DERIVED with agent-synthesis
  provenance, trust weighting, and primary-over-derived conflict
  discipline. v1.2 classification design should leave room for a source
  class dimension without schema upheaval.
- **Proposal lane (v1.4)**: agent findings enter via the filesystem
  proposal directory through LocalFolderProvider — the existing pipeline.
  No new ingestion channel now or later.

## Standing boundaries (unchanged by this milestone)

- The three disciplines: no orchestration creep, no leaderboard disease,
  no rewriting history.
- D24 schema guard: v1.2's new tables (credential store, and any policy
  extensions) are **governed facts justified by ratified decisions** — the
  frozen schema snapshot is updated in the same commit as each ratified
  decision, exactly as the guard prescribes.
- D23 (binding lifecycle) remains DEFERRED.
- Language rulings carry over: "select model" never "deploy model";
  "binding" never "deployed agent".

## The opening questions for the scoping session

In the tradition of evidence-first scoping (v1.0: "what identity evidence
must exist…"), open with these, not with schemas:

> **v1.2.0:** What custody evidence must exist for an outbound credential
> so that, six months later, the system can prove which secret
> authenticated which scan, who controlled it, and that it never leaked
> into any surface?

> **v1.2.x:** Which classes of documents can reach APPROVED with zero human
> attention while every exception is declared, ranked, and audit-explained —
> and what is the honest ceiling of that percentage for a real corpus?
