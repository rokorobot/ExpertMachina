# Business Ontology — What the Imported Knowledge Supports (Scope)

> Drafted 2026-11-04. Companion to docs/scoping-bridge-relations.md
> (D34, proposed). **Docs only.** Measured by reading every imported
> document, not by sampling.

## Source

The imported knowledge reachable in this repo is the seven workbench
corpora: **41 documents, ~5,200 words** (`workbench/*/corpus*`; the
`corpus_seed` refund policy is a duplicate and excluded). No live
instance database is in the repo; a real customer import would be
re-scoped against this same method.

Two caveats that shape everything below:

1. **These are test fixtures, not one enterprise.** The operations
   corpus is "Meridian Operations Ltd"; the rest is an unnamed company.
   Loading all of it into one project merges two fictional firms. Fine
   for a demo; wrong for a claim about "the" enterprise.
2. **The corpora contain deliberate plants** (contradictions,
   supersessions, named-but-absent documents, an invoice record). An
   ontology extracted from them inherits those, by design — the
   conflict engine and the refusal machinery already own them.

## Verdict per layer

| Layer | Extractable from evidence? | Size | Confidence |
|---|---|---|---|
| Domain concepts | **Yes** | ~35 concepts | high |
| Organization (roles/teams) | **Yes, richest layer** | ~28 roles/bodies | high |
| Process | **Partly** — 6 with explicit steps, 8 described without steps, 5 named but undocumented | 19 | high for the 6; medium for the 8 |
| Application | **Thin** — ~12 systems named, no inventory, functions almost never stated | 12 | low |
| Capability | **No** — no capability map exists; capabilities can only be *proposed* | ~10 candidates | n/a (DERIVED only) |
| Bridge relations | **Yes, but not the ones D34 proposed** | ~40 evidenced | see below |

## 1. Domain concepts (high confidence)

Concepts the documents define or rule on — candidates for the domain
layer as *concept assets*, not as instance data:

- **Customer side:** Customer (segments: consumer, business, standard,
  enterprise), Customer Account, Account Plan, Health Score, Order,
  Delivery, Refund, Refund Exception, Warranty, Warranty Claim,
  Complaint, Support Request, Incident (SEV-1/2/3), Escalation, Contact
  Channel, Service Performance Report, Quarterly Business Review,
  Maintenance Window, Availability Target.
- **Agreement side:** Agreement (master service, customer-specific,
  standard terms, vendor, framework, data processing, SLA schedule,
  addendum, statement of work), Term, Renewal, Notice Period, Payment
  Terms, Fee / Price Increase, Minimum Commitment, Late-Payment Penalty.
- **Supplier side:** Vendor / Supplier, Supplier File, Sub-processor,
  Certificate (ISO 27001), Vendor Review.
- **Control side:** Policy, Standard, SOP, Risk Acceptance, Exception,
  Review Cadence, Training Cycle, Personal Data, Data Breach, Record /
  Retention Period, Archive Register, Spend Commitment, Budget Line,
  Invoice (concept only — invoice *records* stay refused, D27/[OE]).
- **People/IT side:** Employee, New Hire, Leaver, Access Request,
  Access Record, Credential (personal vs shared VPN), Production Change,
  Change Ticket, Emergency Change.

Domain classification (D27 paths) maps cleanly onto six roots:
`customer-operations`, `customer-success`, `compliance`, `finance`,
`procurement`, `operations` — i.e. the existing workbench split.

## 2. Organization (high confidence, densest evidence)

Every procedure names who acts. Roles and bodies with evidence:
support agent, shift lead, support manager, head of customer
operations, chief executive officer, chief financial officer, chief
operating officer, finance director, department manager, finance
administrator, Compliance Officer, executive sponsor, on-call
responder, on-duty engineer, resource owner, hiring manager,
onboarding buddy, engineer, team lead, Change Advisory Board, IT team,
platform team, People team, security team, legal team, finance team,
account team, vendor management office.

Authority thresholds are fully extractable as structured facts: refund
matrix (4 bands, EXECUTIVE), spend approval (3 bands), escalation chain
(3 levels).

## 3. Process

**With explicit, ordered steps (extractable as process + step assets):**

| Process | Source | Steps | Actors per step |
|---|---|---|---|
| Access Request | OPS-AC-02 | 3 + revocation | requester → resource owner → IT team |
| Change Management | OPS-CM-03 | 4 | engineer → team lead → platform team |
| Employee Onboarding | OPS-ON-01 | 4 | People team → IT team → hiring manager → buddy |
| Remote Access | OPS-RA-04 | 2 | staff member → IT team (rule **superseded**) |
| Complaint Handling | complaint-handling-procedure | 4 + intake/closure | shift lead → owner → support manager |
| Support Escalation | support-escalation-procedure | 3-level chain | agent → shift lead → support manager → head of CO |

**Described, no step list:** refund request, warranty claim, incident
response (activation + post-incident review), records destruction,
recertification audit scheduling, renewal preparation, vendor review
cycle, price-increase review.

**Named but undocumented (gaps — refusal territory, not ontology):**
enterprise refund exception playbook, offboarding checklist, approved
sourcing process, access request *workflow* tooling, support annex.

## 4. Application (low confidence — the weak layer)

Named systems: customer portal, support email, phone line, support
system (interaction records), sign-in / password reset, VPN, change
ticket (tooling implied, never named), CloudHost production hosting
(managed backups, restore testing), DataFlow (usage analytics),
SecureStore (encrypted archival), legacy datacenter estate, finance
archive space, the company's own hosted service (ISO scope).

What is **missing**: any application inventory, any statement of the
form "step N is performed in system X" beyond the VPN and the customer
portal, and any application *function*. "Replace an application → which
processes break?" is answerable today for **CloudHost only**, and only
partly (see the worked trace).

## 5. Capability (not extractable — must be authored)

No document states a capability. Candidate capabilities a human could
ratify, each with its evidence cluster:

Customer Service Management · Customer Contract & Success Management ·
Incident Management · Information Security & Access Management ·
Compliance & Certification Management · Change & Release Management ·
Workforce Management (onboarding, training) · Vendor & Procurement
Management · Financial Control (spend, payment, budget) · Records &
Retention Management.

Under D29/D30 an agent may only **propose** these; accepted, they are
DERIVED. To make them PRIMARY, the owner writes a one-page capability
map and ingests it as an ordinary document. **That single document is
the biggest unlock in this scope** — without it the capability layer
does not exist.

## 6. Bridge relations — what the evidence actually contains

Counted by relation shape (explicit statements only):

| Relation | Count (approx) | Examples |
|---|---|---|
| PERFORMED_BY (step → role) | ~20 | every step in the 6 explicit processes |
| GOVERNS (policy → process/rule) | ~10 | access control policy → access request; change policy → change SOP; info-sec policy → access/AUP/training/IR standards; procurement policy → supplier certification |
| SUPERSEDES | 1 | POL-AG-02 → OPS-RA-04 remote access rule |
| DEPENDS_ON / REFERENCES (process → process/doc) | ~6 | onboarding → access request; customer agreements → escalation procedure (×3); refund ↔ warranty; refund → exception playbook (absent) |
| SUPPORTED_BY (step → system) | ~3 | remote access → VPN; refund/warranty → customer portal; interactions → support system |
| REALIZES (process → capability) | 0 | no capability evidence |

**Finding: the D34 vocabulary is the wrong shape for this data.** It
proposed `SUPPORTED_BY`, `REALIZES`, `PART_OF`, `OWNED_BY`. The evidence
is dominated by `GOVERNS` and `PERFORMED_BY`; `SUPPORTED_BY` is the
rarest and `REALIZES` has zero evidence. Recommendation for D34 WS0:
start the vocabulary with **`GOVERNS`, `PERFORMED_BY`, `DEPENDS_ON`,
`SUPERSEDES`**, and add `SUPPORTED_BY` / `REALIZES` only when an
application inventory and a capability map are ingested.

## Worked trace — "replace CloudHost" (what the graph could answer today)

| Hop | Evidence | Status |
|---|---|---|
| CloudHost → operates production hosting, backups, restore testing | cloudhost-master-services-agreement | evidenced |
| CloudHost → 99.9% availability for production | cloudhost-sla-schedule | evidenced |
| CloudHost → subprocessor-notification duty on personal data | cloudhost-sla-schedule | evidenced |
| Production hosting → the hosted service in ISO 27001 scope | iso-27001-certification-statement says "hosted service and its supporting infrastructure" — **does not name CloudHost** | **gap — declared, not inferred** |
| Customer 99.5% availability promise depends on CloudHost | enterprise MSA states the target; **no document links it to CloudHost** | **gap — declared, not inferred** |
| Capability affected | no capability map | **gap** |

That is the honest product: 3 evidenced hops, 3 declared gaps. An
ungoverned graph would draw all six.

## Plants an extraction run will surface (expected, not defects)

refund window 14 vs 30 days · enterprise first response 24h vs 48h ·
contract records destroy at 3y vs retain 10y · vendor payment terms
≥30 vs ≥45 days (and CloudHost at 21) · CAB approval vs team-lead-only
approval · shared vs personal VPN credential (resolved by supersession)
· overdue policy reviews (AUP 2024-05-02, change policy 2024-01-15,
change SOP 2024-02-01) · ISO certificate expiry 2026-11-30 with a
90-day booking duty · invoice INV-4471 (must be declined as a record).

## Recommended next steps

1. **Owner:** ratify the corrected D34 vocabulary (§6) in WS0.
2. **Owner:** author two short documents — a capability map and an
   application inventory (system → functions → processes it supports).
   Without them, two of the five layers stay empty by law, not by bug.
3. **Build (after D34 ratification):** the extraction pass proposes
   `PERFORMED_BY` / `GOVERNS` / `DEPENDS_ON` / `SUPERSEDES` from the six
   explicit processes first — the highest-evidence, lowest-risk slice.
4. Keep Meridian and the unnamed company in separate projects for any
   claim about a single enterprise.
