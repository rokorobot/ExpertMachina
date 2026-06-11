# User & Identity Administration Guide

How administrators manage identities, roles, tokens, and access control in
ExpertMachina. Everything in this guide requires the `ADMIN` role; the
**Settings → Users & Tokens** panel is visible only to administrators.

The architectural contract behind this guide is
[docs/identity-boundary-v1.md](identity-boundary-v1.md) (decisions D20/D21
in the [Decision Register](DECISIONS.md)). The short version:

> Callers propose identity. The identity boundary decides the actor.
> Every governed action records immutable identity evidence at action time.

---

## Identity Types

| Kind | Who | Authenticates with | Holds |
| :--- | :--- | :--- | :--- |
| **HUMAN** | administrators, governance reviewers, knowledge operators | username + password (session) | a role |
| **SERVICE** | connectors, scheduled jobs, integrations | API token | a role (never `ADMIN`) |
| **AGENT** | AI systems connected through MCP | API token (`EM_AGENT_TOKEN`) | a clearance; always role `AGENT_CONSUMER` |

Two further kinds are **platform-managed** and never created by hand:
`SYSTEM` (the engines) and `DELEGATED` (`policy:X`, `connector:Y` — governed
automation whose identity chains to whoever triggered it).

---

## Roles & Permissions

The permission matrix is small, code-resident, and enforced on every API
route. The backend is authoritative — UI visibility is convenience only;
calling an endpoint directly is enforced server-side identically.

| Permission | ADMIN | GOVERNANCE_REVIEWER | KNOWLEDGE_OPERATOR | AGENT_CONSUMER | READ_ONLY |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `assets:read` (knowledge, dashboards, inbox) | ✓ | ✓ | ✓ | | ✓ |
| `assets:review` (reviews, revisions, benchmarks) | ✓ | ✓ | | | |
| `assets:approve` (approvals, conflicts, policies, experts, packages) | ✓ | ✓ | | | |
| `assets:delete` | ✓ | | | | |
| `documents:ingest` (uploads, extraction, projects) | ✓ | | ✓ | | |
| `connectors:manage` (create, scan) | ✓ | | ✓ | | |
| `audit:read` (ledger, agent activity) | ✓ | ✓ | | | |
| `settings:manage` (platform configuration) | ✓ | | | | |
| `identity:manage` (principals, roles, resets) | ✓ | | | | |
| `tokens:manage` (issue, list, revoke) | ✓ | | | | |
| `mcp:consume` (the agent gateway) | ✓ | | | ✓ | |

Asset status updates resolve their permission by transition: setting
`APPROVED`/`ARCHIVED` requires `assets:approve`; everything else requires
`assets:review`.

---

## First Run (Bootstrap)

On first startup with an empty database, the backend creates the `admin`
account and prints a **one-time password to its console** — shown once,
never stored in plaintext. Sign in, and the amber rotation banner walks you
through setting your own password (current one-time password, new password,
confirm). Your session stays signed in after the rotation.

---

## Creating a Human User

**Settings → Users & Tokens → Create Principal**

1. Enter the username, choose kind **HUMAN**, choose a role.
2. The system displays a **generated one-time password — exactly once**.
   Hand it to the user through a secure channel.
3. The user signs in and is forced to set their own password at the banner.

New humans default to `READ_ONLY` (least privilege) unless you choose
otherwise. Grant upward only as needed: `READ_ONLY` →
`GOVERNANCE_REVIEWER` / `KNOWLEDGE_OPERATOR` → `ADMIN`.

## Changing Roles

In the principal's row, change the role in the inline dropdown. The change
takes effect on the user's very next request — no re-login required — and
is audited with old → new values and your identity fact.

Guard rails: administrators **cannot change their own role or deactivate
themselves** (escalation/lockout protection), and `SERVICE` principals can
never hold `ADMIN`.

## Resetting Passwords

In the principal's row, **Reset PW**. The system generates a new one-time
password (shown once), forces rotation at next login, and **revokes the
user's live sessions immediately**. Fully audited.

## Deactivating Users

In the principal's row, **Deactivate**. Effects: login blocked, live
sessions and tokens fail closed on their next use, audit event written.
Knowledge assets and historical records are untouched — and the principal
row itself is never deleted, because audit history references it forever.
**Reactivate** restores access.

---

## Creating Service Accounts

**Create Principal** with kind **SERVICE** and a role (`READ_ONLY`,
`KNOWLEDGE_OPERATOR`, or `GOVERNANCE_REVIEWER` — `ADMIN` is prohibited for
services). Then issue a token from the principal's row. A service holds
exactly its role's permissions on the REST API — there is no implicit
machine authority.

## Creating Agent Accounts

**Create Principal** with kind **AGENT** and a **clearance** (`PUBLIC`,
`INTERNAL`, `RESTRICTED`, `EXECUTIVE`). Agents are always
`AGENT_CONSUMER`: they can consume the MCP gateway and nothing else —
agent tokens are **rejected on the REST API by design**.

Issue a token, then configure the agent's MCP connection:

```json
{
  "mcpServers": {
    "expertmachina": {
      "command": "...\\backend\\.venv\\Scripts\\python.exe",
      "args": ["...\\backend\\mcp_server.py"],
      "env": { "EM_AGENT_TOKEN": "emk_..." }
    }
  }
}
```

The agent's clearance comes from the registry — changing it in Users &
Tokens takes effect on the agent's next tool call, as does revoking its
token (live sessions fail closed). The pre-v1.0 `EM_AGENT_ID` /
`EM_AGENT_CLEARANCE` variables no longer establish identity and are
refused explicitly.

---

## Token Management

**Settings → Users & Tokens → API Token Lineage**

- **Issue**: from an AGENT/SERVICE principal's row. The token plaintext is
  shown **exactly once** — only its hash is stored. Store it securely.
- **Revoke**: takes effect on the token's next use, including mid-session.
- **Rotate**: issue a new token, reconfigure the consumer, revoke the old.
- Revoked tokens **stay listed** — lineage, not deletion. Six months later,
  "which credential authenticated this action?" is still answerable.

---

## Audit History

Every security-sensitive action is an immutable audit event carrying the
acting administrator's **identity fact** (who, role at that moment,
authentication method, credential fingerprint):

- `PRINCIPAL_CREATED`, `PRINCIPAL_UPDATED` (with old → new values)
- `CREDENTIAL_CREATED`, `CREDENTIAL_REVOKED`
- `LOGIN_SUCCEEDED`, `LOGIN_FAILED` (failed proposals are recorded as
  proposals, never as actors)
- `AUTHZ_GRANTED` (write permissions), `AUTHZ_DENIED` (always)
- `MCP_AUTH_REFUSED`, `MCP_TOOL_CALLED`, `MCP_ACCESS_DENIED`
- `BOUNDARY_VALIDATION` (startup self-check), `ROLE_VOCABULARY_MIGRATED`

Identity facts are historical evidence: a role change never alters what
past events say about the role the actor held *then*. Use the **Audit
Ledger** tab (requires `audit:read`) as the source of truth.

Optional: set `EM_READ_AUDIT_MODE=FULL` (or `SAMPLED`) to also audit read
grants — the enterprise "who *viewed* this?" question. Default `OFF`.

---

## Recovery

- **Any non-lockout case**: an active `ADMIN` resets passwords in-app (above).
- **Root-admin lockout** (lost password, no other active admin): there is
  deliberately **no recovery command or backdoor**. Follow the documented
  manual procedure in
  [identity-boundary-v1.md → Recovery](identity-boundary-v1.md) — it routes
  through the governed credential path, so even recovery leaves an intact,
  audited lineage. Never edit `identity_facts`: they are historical evidence.

---

## Security Best Practices

- **Least privilege**: start everyone at `READ_ONLY`; grant upward only as
  duties require.
- **No shared accounts** — identity facts are only as good as the mapping
  from principals to people.
- **Rotate service and agent tokens** on a schedule (issue → reconfigure →
  revoke); set `expires_days` at issuance where the consumer supports
  re-provisioning.
- **Review the audit ledger** regularly — especially `AUTHZ_DENIED`,
  `LOGIN_FAILED`, and `MCP_AUTH_REFUSED`.
- **Deactivate unused identities immediately**; never work around the
  boundary with environment variables — it will refuse them anyway.

## Troubleshooting

**User cannot log in** — verify the account is active in Users & Tokens;
reset the password; check `LOGIN_FAILED` events in the audit ledger.

**Service token rejected** — verify the token is not revoked or expired
(API Token Lineage), the principal is active, and the role grants the
permission the endpoint requires (the 403 names it).

**Agent access denied** — agent tokens are valid **only at the MCP
gateway** (REST returns 403 by design); verify `EM_AGENT_TOKEN` is set and
current, the principal is an active AGENT, and its clearance covers the
asset tier; check `MCP_AUTH_REFUSED` / `MCP_ACCESS_DENIED` events.

**Wrong "current password" during rotation** — a field error, not a
session problem: you stay signed in; the first banner field takes the
*one-time* password, the last two take your new password.

Always use audit history as the source of truth.
