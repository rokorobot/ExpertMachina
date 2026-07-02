"""ExpertMachina workbenches (v1.4.0 WS3, D29/D30/D22).

A workbench is a REFERENCE CONSUMER, never a subsystem: it lives outside
backend/ entirely and reaches ExpertMachina only through the existing
doors - the .empkg via app.package_consumer, the MCP gateway as a real
client at a real AGENT token's clearance, and file writes into the
vault's /08_proposals return path. The authorship guard
(backend/test_agent_authorship_guard.py Part 5) sweeps every module in
this package against those doors: stdlib + app.package_consumer +
app.llm + mcp, nothing else. A workbench that could reach the database,
CRUD, routes, or identity would be an internal privileged subsystem -
exactly what D29 forbids it to become.
"""
