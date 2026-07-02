import json
import os
import sys
import tempfile
from dataclasses import asdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
# The v1.0 posture carried over: env-asserted identity is hostile noise.
os.environ["EM_AGENT_ID"] = "mallory-agent"
os.environ["EM_AGENT_CLEARANCE"] = "EXECUTIVE"

import test_projection_engine as ws1

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import identity
from app import mcp_gateway
from app.projections import engine as projection_engine
import test_support

# MCP Graph Query Tools suite (v1.3.0 WS3, D28/D10,
# docs/projection-engine-v1.3.md).
#
# The agent proof: lineage is a path query. An agent walks
# document -> asset -> expert -> package -> binding as ONE query with
# every hop resolving from the live projection; a node above the
# agent's clearance is an audited MCP_ACCESS_DENIED; unreachable pairs
# and out-of-scope nodes are declared answers, never silent gaps (D12);
# and the tools return the engine's own structures - one composition,
# two channels (D10): the governed channel computes, the portable
# channel is files, and the governed channel NEVER reads the files.

HOSTILE_NODE = "asset:424242"


def events_of(session, event_type):
    return session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == event_type).order_by(db.AuditEvent.id).all()


def part_1_path_proof(session, project, rows):
    print("\n--- Part 1: THE PATH PROOF (lineage as one query) ---")
    result = mcp_gateway.get_lineage_path(
        project.id, f"document:{rows['doc1'].id}", "binding:1",
        session=session)
    assert result["path_found"] is True
    walked = [n["id"] for n in result["nodes"]]
    assert walked[0] == f"document:{rows['doc1'].id}"
    assert walked[-1] == "binding:1"
    relations = [e["relation"] for e in result["edges"]]
    assert relations == ["PROVENANCE", "MEMBER_OF", "COMPILED_FROM",
                         "BOUND_TO"], relations
    assert result["hops"] == 4
    # Every hop resolves: each path node is a full projection node.
    for node in result["nodes"]:
        assert node["kind"] and node["id"], node
    print(f"Part 1 passed: document -> binding in {result['hops']} hops "
          f"({' -> '.join(relations)}), every hop a resolved governed node.")


def part_2_engine_identity(session, project, rows):
    print("\n--- Part 2: one composition, two channels (D10) ---")
    neighbors = mcp_gateway.get_graph_neighbors(
        project.id, f"asset:{rows['a1'].id}", session=session)
    projection = projection_engine.compose(
        session, project.id, clearance="INTERNAL",
        status_inclusion=("APPROVED",))
    engine_node = [n for n in projection.nodes
                   if n.id == f"asset:{rows['a1'].id}"][0]
    assert neighbors["node"] == asdict(engine_node), \
        "The tool must return the engine's own structure, not a re-model"
    tool_edges = {(e["relation"], e["source_id"], e["target_id"])
                  for e in neighbors["edges"]}
    engine_edges = {(e.relation, e.source_id, e.target_id)
                    for e in projection.edges
                    if f"asset:{rows['a1'].id}" in (e.source_id, e.target_id)}
    assert tool_edges == engine_edges
    assert neighbors["clearance"] == "INTERNAL", \
        "Clearance comes from the registry, never the hostile env"
    print(f"Part 2 passed: tool output IS the engine's projection "
          f"({len(tool_edges)} edges), at registry clearance INTERNAL.")


def part_3_clearance_denial(session, project, rows):
    print("\n--- Part 3: the denial is ledger evidence ---")
    denied_before = len(events_of(session, "MCP_ACCESS_DENIED"))
    try:
        mcp_gateway.get_graph_neighbors(
            project.id, f"asset:{rows['a2'].id}", session=session)
        raise AssertionError("EXECUTIVE node served to an INTERNAL agent")
    except ValueError as e:
        assert "EXECUTIVE" in str(e)
    denials = events_of(session, "MCP_ACCESS_DENIED")
    assert len(denials) == denied_before + 1
    detail = json.loads(denials[-1].details)
    assert detail["asset_id"] == rows["a2"].id
    assert detail["required_access_level"] == "EXECUTIVE"
    assert detail["clearance"] == "INTERNAL"
    assert denials[-1].identity_fact_id is not None
    # The same discipline through the path tool: the protected node can
    # be neither an endpoint...
    try:
        mcp_gateway.get_lineage_path(
            project.id, f"asset:{rows['a1'].id}", f"asset:{rows['a2'].id}",
            session=session)
        raise AssertionError("path endpoint above clearance was served")
    except ValueError:
        pass
    # ...nor a silent intermediate: the conflict edge to it is simply
    # not in the INTERNAL projection.
    neighbors = mcp_gateway.get_graph_neighbors(
        project.id, f"asset:{rows['a1'].id}", session=session)
    assert not [e for e in neighbors["edges"]
                if e["relation"] == "CONFLICTS_WITH"]
    print("Part 3 passed: denial audited with the agent's fact, endpoint "
          "and intermediate exposure both closed.")


def part_4_declared_misses(session, project, rows):
    print("\n--- Part 4: absence is declared, never silent (D12) ---")
    try:
        mcp_gateway.get_graph_neighbors(
            project.id, f"asset:{rows['a3'].id}", session=session)
        raise AssertionError("CANDIDATE asset served through the graph")
    except LookupError as e:
        assert "not approved knowledge" in str(e)
    try:
        mcp_gateway.get_graph_neighbors(project.id, HOSTILE_NODE,
                                        session=session)
        raise AssertionError("nonexistent node produced an answer")
    except LookupError as e:
        assert "not found" in str(e)
    # An unreachable pair is a declared ANSWER, not an error: the new
    # isolated asset connects to nothing.
    isolated = db.KnowledgeAsset(
        project_id=project.id, type="SYSTEM", name="Isolated Note",
        content="An approved note with no document and no expert model.",
        status="APPROVED", access_level="INTERNAL")
    session.add(isolated)
    session.commit()
    result = mcp_gateway.get_lineage_path(
        project.id, f"asset:{isolated.id}", "binding:1", session=session)
    assert result["path_found"] is False
    assert "No chain of governed relations" in result["reason"]
    print("Part 4 passed: candidate refused with reason, unknown node "
          "refused with reason, unreachable pair answered with reason.")


def part_5_domain_subgraph(session, project, rows):
    print("\n--- Part 5: the domain lens through the governed channel ---")
    result = mcp_gateway.get_domain_subgraph(project.id, "finances",
                                             session=session)
    ids = {n["id"] for n in result["nodes"]}
    assert f"asset:{rows['a1'].id}" in ids
    assert f"asset:{rows['a2'].id}" not in ids  # above INTERNAL clearance
    assert f"asset:{rows['a4'].id}" not in ids  # hr, outside the prefix
    assert result["excluded"]["assets_above_clearance"] == 1
    assert result["excluded"]["assets_outside_domain_scope"] >= 1
    assert result["scope"] == {"domain_prefix": "finances"}
    assert "finances/accounting" in result["groups"]
    print(f"Part 5 passed: {len(ids)} nodes under 'finances' at INTERNAL, "
          f"every exclusion counted.")


def part_6_never_reads_renders(session, project, rows):
    print("\n--- Part 6: the governed channel never reads the portable one ---")
    before = mcp_gateway.get_graph_neighbors(
        project.id, f"asset:{rows['a1'].id}", session=session)
    hostile_dir = tempfile.mkdtemp(prefix="em_mcp_hostile_")
    with open(os.path.join(hostile_dir, "graph.json"), "w",
              encoding="utf-8") as f:
        json.dump({"nodes": [{"id": HOSTILE_NODE, "label": "HOSTILE",
                              "status": "APPROVED"}],
                   "edges": [{"from": HOSTILE_NODE,
                              "to": f"asset:{rows['a1'].id}",
                              "relation": "SUPPORTS"}]}, f)
    saved = os.environ.get("EM_PROJECTION_DIR")
    os.environ["EM_PROJECTION_DIR"] = hostile_dir
    try:
        after = mcp_gateway.get_graph_neighbors(
            project.id, f"asset:{rows['a1'].id}", session=session)
        assert after == before, \
            "D28/D10 violation: a graph tool consulted rendered files"
        try:
            mcp_gateway.get_graph_neighbors(project.id, HOSTILE_NODE,
                                            session=session)
            raise AssertionError("a node that exists only in a rendered "
                                 "file was answered")
        except LookupError:
            pass
    finally:
        if saved is None:
            os.environ.pop("EM_PROJECTION_DIR", None)
        else:
            os.environ["EM_PROJECTION_DIR"] = saved
    print("Part 6 passed: hostile rendered graph invisible to the "
          "governed channel.")


def part_7_audit_discipline(session, project, rows):
    print("\n--- Part 7: every graph call is MCP_TOOL_CALLED evidence ---")
    called = {}
    for event in events_of(session, "MCP_TOOL_CALLED"):
        detail = json.loads(event.details)
        called[detail["tool_name"]] = called.get(detail["tool_name"], 0) + 1
    for tool in ("get_graph_neighbors", "get_lineage_path",
                 "get_domain_subgraph"):
        assert called.get(tool), f"{tool} left no ledger trace"
    projection_events = events_of(session, "PROJECTION_RENDERED")
    assert not projection_events, \
        "Graph QUERIES are reads - only file renders write the ledger"
    print(f"Part 7 passed: {sum(called.values())} audited tool calls; "
          f"queries left zero PROJECTION_RENDERED events.")


def main():
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False})
    db.engine = engine
    db.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    project, rows = ws1.seed(session, officer)

    # The calling agent: INTERNAL in the registry; the env hostilely
    # claims EXECUTIVE and is inert (v1.0 discipline, re-proven here).
    token, _cred = identity.issue_token(session, rows["agent"],
                                        label="graph tools suite")
    os.environ["EM_AGENT_TOKEN"] = token

    part_1_path_proof(session, project, rows)
    part_2_engine_identity(session, project, rows)
    part_3_clearance_denial(session, project, rows)
    part_4_declared_misses(session, project, rows)
    part_5_domain_subgraph(session, project, rows)
    part_6_never_reads_renders(session, project, rows)
    part_7_audit_discipline(session, project, rows)
    print("\n=== All MCP Graph Tools (WS3) tests passed successfully! ===")


if __name__ == "__main__":
    main()
