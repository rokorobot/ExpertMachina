"""ExpertMachina MCP Gateway (MVP 0.9 - read-only).

Transport layer over Governance Contract v1 (docs/governance-contract-v1.md).
Adds no semantics of its own: every tool delegates to the same functions the
governed REST console uses, and every call is recorded in the audit ledger
as MCP_TOOL_CALLED.

Run (stdio, from backend/):
    .venv\\Scripts\\python mcp_server.py

Claude Desktop / Claude Code / Cursor config example:
{
  "mcpServers": {
    "expertmachina": {
      "command": "C:\\\\path\\\\to\\\\backend\\\\.venv\\\\Scripts\\\\python.exe",
      "args": ["C:\\\\path\\\\to\\\\backend\\\\mcp_server.py"],
      "env": {
        "EM_AGENT_TOKEN": "emk_...issued by an ADMIN via /api/identity/tokens..."
      }
    }
  }
}

Identity Boundary v1.0: the agent proposes EM_AGENT_TOKEN; the boundary
decides who it is. Clearance comes from the AGENT principal in the
governed registry (Access Model v1), never from the environment - the
pre-boundary EM_AGENT_ID / EM_AGENT_CLEARANCE variables no longer
establish identity and are refused explicitly when present without a
token. Tokens are resolved per tool call, so revocation and clearance
changes take effect on a live session's next call. Unauthenticated
agents are refused, and every refusal is audited (MCP_AUTH_REFUSED).

Write actions (approve_revision, dismiss_conflict, publish_package) are
deliberately NOT exposed: the governance core must be observable before
it becomes agent-writable.
"""
import os
import sys
import builtins

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# stdio transport discipline: stdout carries JSON-RPC frames ONLY. The
# governance engines print telemetry (VALIDATION_REPORT, RETRIEVAL_AUDIT,
# ...) which must go to stderr or it corrupts the protocol stream.
_original_print = builtins.print


def _stderr_print(*args, **kwargs):
    kwargs.setdefault("file", sys.stderr)
    _original_print(*args, **kwargs)


builtins.print = _stderr_print

from mcp.server.fastmcp import FastMCP

from app import mcp_gateway

mcp = FastMCP(
    "expertmachina",
    instructions=(
        "ExpertMachina Governance Gateway (read-only, Governance Contract v1). "
        "Expert Models are compiled, semantically verified, conflict-checked, "
        "revision-controlled enterprise knowledge. Answers are evidence-backed: "
        "no evidence means no answer. Citations include revision numbers and "
        "provenance; trust and gate verdicts are explainable and versioned."
    ),
)


@mcp.tool()
def ask_expert(expert_model_id: int, question: str) -> dict:
    """Ask an Expert Model an evidence-backed question (Verified Answer v1).

    Returns the answer with citations (document, page, section, hash,
    revision), coverage_score, verification_status, and the verifier
    identity. Answers failing verification return INSUFFICIENT EVIDENCE -
    the system never guesses. Retrieval respects this agent's clearance.
    """
    return mcp_gateway.ask_expert(expert_model_id, question)


@mcp.tool()
def get_trust_score(expert_model_id: int) -> dict:
    """Get the hierarchical Trust Score v1 for an Expert Model.

    Returns the aggregate trust_score plus five explainable components
    (evaluation reliability, evidence coverage, conflict integrity,
    governance health, revision freshness), each with a reason. Components
    without underlying data are NOT_MEASURED, never fabricated.
    """
    return mcp_gateway.get_trust_score(expert_model_id)


@mcp.tool()
def check_gate_status(expert_model_id: int) -> dict:
    """Check the Compile Gate v1 verdict for an Expert Model.

    Returns ALLOWED or BLOCKED with the blocking conflicts (unreviewed or
    confirmed semantic contradictions), advisory conflicts, and the active
    gate policy. A BLOCKED model cannot be published as an Agent Package.
    """
    return mcp_gateway.check_gate_status(expert_model_id)


@mcp.tool()
def get_provenance(asset_id: int) -> dict:
    """Get the chain of custody for a knowledge asset.

    Returns source document, page, section, source hash, extraction method,
    recorded approver identity and timestamp, and the active revision number.
    Subject to this agent's clearance: assets above the agent's tier are
    denied (and the denial is audit-logged).
    """
    return mcp_gateway.get_provenance(asset_id)


@mcp.tool()
def get_conflicts(expert_model_id: int) -> dict:
    """Get semantic conflict relationships for an Expert Model.

    Returns the conflict score with summary and all detected/reviewed
    relationships (classification, confidence, review state, decision
    reasons, verifier fingerprint). Use with get_trust_score to explain why
    trust is below 100. Relationship metadata only - asset content stays
    behind clearance-checked tools.
    """
    return mcp_gateway.get_conflicts(expert_model_id)


@mcp.tool()
def get_revision_history(asset_id: int) -> dict:
    """Get the immutable revision chain for a knowledge asset.

    Returns every revision with status, content, content hash, creator,
    approver, supersession links, and change reasons - approved knowledge is
    never edited in place, so this is the asset's complete content history.
    Subject to this agent's clearance.
    """
    return mcp_gateway.get_revision_history(asset_id)


@mcp.tool()
def get_graph_neighbors(project_id: int, node_id: str) -> dict:
    """Get one governed graph node and every relation touching it.

    Node ids are kind-prefixed: "asset:42", "document:7", "expert:2",
    "package:3", "selection:1", "binding:1", "principal:9". Returns the
    node, its edges (provenance, membership, conflicts, supports, the
    consumption chain), and neighbor nodes - computed live from governed
    facts at this agent's clearance, approved knowledge only. A rendered
    graph file is never consulted (v1.3 D28: this is the governed
    channel; files are the portable one).
    """
    return mcp_gateway.get_graph_neighbors(project_id, node_id)


@mcp.tool()
def get_lineage_path(project_id: int, from_node_id: str,
                     to_node_id: str) -> dict:
    """Lineage as a path query: the shortest chain of governed relations
    connecting two graph nodes (e.g. a source document to the agent
    binding that ultimately serves it). Every hop resolves from the live
    projection under this agent's clearance; an unreachable pair returns
    a declared path_found=false answer, never a silent gap.
    """
    return mcp_gateway.get_lineage_path(project_id, from_node_id, to_node_id)


@mcp.tool()
def get_domain_subgraph(project_id: int, domain_prefix: str) -> dict:
    """Get the governed subgraph under one hierarchical domain prefix
    (e.g. "finances" resolves finances/accounting and finances/treasury).

    Returns nodes, edges, and domain groups scoped to the prefix at this
    agent's clearance, with every exclusion declared as counts - what
    was filtered is stated, never silent.
    """
    return mcp_gateway.get_domain_subgraph(project_id, domain_prefix)


if __name__ == "__main__":
    mcp.run()
