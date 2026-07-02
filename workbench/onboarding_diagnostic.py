"""Onboarding Diagnostic Workbench - the v1.4.0 reference consumer.

The first Operations Realm workbench (D22 held: EM binds, customers
execute - this is the reference execution, not a runtime EM governs).
It diagnoses a company's onboarding knowledge and PROPOSES findings;
it never writes knowledge (D29: the one-way valve).

The doors, and nothing else (guard-enforced):
  - the .empkg Expert Package via app.package_consumer (hash-chain
    verified, gate-snapshot honored, clearance-filtered);
  - the MCP gateway as a real client at a real AGENT token's clearance
    (the graph tools are the relational access; D27 domain prefixes the
    scoping dimension);
  - file writes into the vault: /08_proposals ONLY (the return path)
    and /07_agent_workspaces (ungoverned scratch).

Synthesis sits behind an injectable seam: the CI gate injects a
deterministic synthesizer; the real run uses package_consumer.consume,
which generates through the D19 resolver/adapter boundary. Whatever
synthesizes, every finding cites the governed asset ids it drew from -
evidence-backed diagnosis, or no diagnosis.

The proposal document opens with the frontmatter contract from
vault/00_system/agent-contract.md; every claim in it is verified
against governed records at the gate, never trusted from this file.
"""
import hashlib
import json
import os
import sys

# The package-consumer door: app.package_consumer resolves once the
# backend directory is on sys.path (EM_BACKEND_DIR or --backend-dir).
def _import_package_consumer(backend_dir=None):
    backend_dir = backend_dir or os.environ.get("EM_BACKEND_DIR")
    if backend_dir and backend_dir not in sys.path:
        sys.path.append(backend_dir)
    from app import package_consumer
    return package_consumer


DEFAULT_QUESTIONS = (
    "What must a new hire complete before receiving badge access?",
    "Which systems store onboarding and training records?",
    "What training is required before system access is granted?",
)


class StdioMcpGraphClient:
    """The real MCP door: a stdio client session against
    backend/mcp_server.py, authenticated by the EM_AGENT_TOKEN in the
    server's environment - per-call token resolution, registry
    clearance, audited refusals. The CI gate injects an in-process
    substitute that resolves the same token through the same gateway;
    this class is the transport the real run uses."""

    def __init__(self, python_exe, server_path, env=None, cwd=None):
        self._params = dict(command=python_exe, args=[server_path],
                            env=env, cwd=cwd)

    def get_domain_subgraph(self, project_id, domain_prefix):
        import asyncio
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def _call():
            server = StdioServerParameters(**self._params)
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "get_domain_subgraph",
                        {"project_id": project_id,
                         "domain_prefix": domain_prefix})
                    return json.loads(result.content[0].text)
        return asyncio.run(_call())


def package_synthesizer(package_path, questions, backend_dir=None):
    """The real synthesis seam: one consume() per question through the
    D19 resolver/adapter boundary. Findings cite exactly what the
    consumer's package-local retrieval offered and the answer cited."""
    package_consumer = _import_package_consumer(backend_dir)
    findings = []
    for question in questions:
        result = package_consumer.consume(package_path, question)
        findings.append({
            "question": question,
            "finding": result["answer"],
            "cited_asset_ids": result["cited_asset_ids"],
        })
    return findings


def _graph_observations(subgraph):
    """Deterministic relational observations from the governed subgraph
    (the agents' relational access): domain coverage and visible
    conflict edges - structure the package alone cannot show."""
    if not subgraph:
        return []
    observations = []
    groups = subgraph.get("groups") or {}
    for domain in sorted(groups):
        observations.append(
            f"Domain '{domain}' holds {len(groups[domain])} governed asset(s).")
    conflict_edges = [e for e in subgraph.get("edges", [])
                      if e.get("relation") == "CONFLICTS_WITH"]
    for edge in conflict_edges:
        asymmetry = (edge.get("metadata") or {}).get("class_asymmetry")
        note = " (primary prevails)" if asymmetry else ""
        observations.append(
            f"Visible conflict: {edge['source_id']} vs {edge['target_id']}{note}.")
    excluded = subgraph.get("excluded") or {}
    declared = {k: v for k, v in excluded.items() if v}
    if declared:
        observations.append(f"Exclusions declared by the gateway: {declared}.")
    return observations


def run_diagnostic(package_path, vault_dir, project_id,
                   agent_principal, binding_id,
                   domain_prefix=None, questions=None,
                   synthesizer=None, graph_client=None,
                   backend_dir=None,
                   workbench_name="onboarding-diagnostic"):
    """Consume the package + the governed graph, synthesize findings,
    and write ONE proposal document to <vault>/08_proposals. Returns the
    written path. Deterministic for a fixed corpus + synthesizer: the
    filename derives from the content hash, and the content carries no
    timestamps - the scan and the ledger stamp time, not the proposal."""
    package_consumer = _import_package_consumer(backend_dir)
    package = package_consumer.load_package(package_path)  # verify the chain
    package_hash = package["package_hash"]
    questions = tuple(questions or DEFAULT_QUESTIONS)

    subgraph = None
    if graph_client is not None:
        subgraph = graph_client.get_domain_subgraph(project_id, domain_prefix)

    if synthesizer is not None:
        findings = synthesizer(package_path, questions)
    else:
        findings = package_synthesizer(package_path, questions,
                                       backend_dir=backend_dir)

    cited = sorted({asset_id for f in findings
                    for asset_id in f.get("cited_asset_ids", [])})
    lines = [
        "---",
        "em_proposal: 1",
        f"agent_principal: {agent_principal}",
        f"binding_id: {binding_id}",
        f"package_hash: {package_hash}",
        f"workbench: {workbench_name}",
        f"cited_assets: {','.join(str(i) for i in cited)}",
        "---",
        "",
        f"# Onboarding diagnostic - {package['manifest'].get('package_name', 'Expert Package')}",
        "",
        "Agent-synthesized findings. Evidence citations name the governed",
        "assets each finding drew from. This document is a PROPOSAL: it",
        "becomes knowledge only if a human accepts it at the gate, and then",
        "as a DERIVED fact (D29/D30).",
        "",
    ]
    for f in findings:
        lines.append(f"## {f['question']}")
        lines.append("")
        lines.append(f["finding"])
        lines.append("")
        lines.append(f"Evidence: governed assets "
                     f"{', '.join(str(i) for i in f.get('cited_asset_ids', [])) or 'none'}.")
        lines.append("")
    observations = _graph_observations(subgraph)
    if observations:
        lines.append("## Relational observations (governed graph)")
        lines.append("")
        for note in observations:
            lines.append(f"- {note}")
        lines.append("")
    content = "\n".join(lines)

    proposals_dir = os.path.join(vault_dir, "08_proposals")
    if not os.path.isdir(proposals_dir):
        raise RuntimeError(
            f"{proposals_dir} does not exist - bootstrap the vault first "
            f"(vault/bootstrap.py). The workbench writes proposals ONLY there.")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
    path = os.path.join(proposals_dir, f"{workbench_name}-{digest}.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return path
