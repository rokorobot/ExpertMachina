import os
import sys
import json
import asyncio
import hashlib

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_AGENT_ID"] = "test-agent-007"
os.environ["EM_AGENT_CLEARANCE"] = "INTERNAL"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import ingestion
from app import mcp_gateway
import test_support


def _disabled_qdrant():
    raise RuntimeError("Qdrant disabled in gateway test: deterministic SQLite retrieval")


def make_asset(session, project, doc, name, content, access_level="INTERNAL"):
    chunk = db.DocumentChunk(document_id=doc.id, text=content, chunk_index=0)
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    asset = crud.create_knowledge_asset(session, schemas.KnowledgeAssetCreate(
        type="POLICY", name=name, content=content, project_id=project.id,
        document_id=doc.id, chunk_id=chunk.id, source_page=1, source_section="S1",
        source_hash=hashlib.sha256(content.encode()).hexdigest(), access_level=access_level))
    crud.update_knowledge_asset(session, asset_id=asset.id, update=schemas.KnowledgeAssetUpdate(status="APPROVED"),
                                actor=test_support.governed_actor(session, "qa"))
    return asset


def main():
    print("\nInitializing test database for MCP Gateway checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    ingestion.get_qdrant_client = _disabled_qdrant

    customer = crud.get_or_create_default_customer(session)
    qa = test_support.governed_actor(session, "qa")
    project = crud.create_project(session, schemas.ProjectCreate(name="Gateway Test", description="", customer_id=customer.id), actor=qa)
    doc = crud.create_document(session, project_id=project.id, filename="P.txt", file_path="uploads/p.txt", actor=qa)

    internal = make_asset(session, project, doc, "Internal Policy", "Critical deviations must be logged within 24 hours.")
    executive = make_asset(session, project, doc, "Executive Policy", "Executive bonus pool is 4 percent of net profit.", access_level="EXECUTIVE")
    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Gateway Expert", description="", project_id=project.id, asset_ids=[internal.id, executive.id]), actor=qa)

    # Part 1: tool surface is exactly the six read-only tools (Tier 1 + Tier 2).
    print("\n--- Part 1: Read-only tool surface ---")
    import mcp_server
    tools = asyncio.run(mcp_server.mcp.list_tools())
    names = sorted(t.name for t in tools)
    assert names == ["ask_expert", "check_gate_status", "get_conflicts",
                     "get_provenance", "get_revision_history", "get_trust_score"], f"Unexpected tool surface: {names}"
    forbidden = {"approve_revision", "dismiss_conflict", "publish_package"}
    assert not forbidden.intersection(names), "Write tools must not be exposed in v0.9"
    print(f"Part 1 passed: surface = {names}, no write tools.")

    # Part 2: clearance enforcement through the shared pipeline.
    print("\n--- Part 2: Agent clearance enforced in ask_expert ---")
    result = mcp_gateway.ask_expert(model.id, "What is the deviation logging deadline?", session=session)
    cited_ids = [c["asset_id"] for c in result["citations"]]
    assert internal.id in cited_ids, "INTERNAL asset missing from citations"
    assert executive.id not in cited_ids, "EXECUTIVE asset leaked to INTERNAL-clearance agent!"
    assert "answer" in result and "coverage_score" in result and "verification_status" in result
    print("Part 2 passed: EXECUTIVE asset filtered for INTERNAL agent; Verified Answer v1 shape returned.")

    # Part 3: trust and gate verdicts match contract shapes.
    print("\n--- Part 3: Trust Score v1 and Compile Gate v1 shapes ---")
    ts = mcp_gateway.get_trust_score(model.id, session=session)
    assert ts["score_version"] == "trust-score-v1"
    assert len(ts["components"]) == 5
    assert all("reason" in c for c in ts["components"])

    session.add(db.AssetRelationship(
        project_id=project.id, expert_model_id=model.id,
        source_asset_id=internal.id, target_asset_id=executive.id,
        relationship_type="CONFLICTS_WITH", classification="DIRECT_CONTRADICTION",
        confidence=0.99, status="DETECTED", verifier_json=json.dumps({"method": "TEST"})))
    session.commit()
    gate = mcp_gateway.check_gate_status(model.id, session=session)
    assert gate["status"] == "BLOCKED"
    assert gate["reasons"] and gate["reasons"][0]["reason"] == "UNREVIEWED_CONFLICT"
    print("Part 3 passed: contract-shaped verdicts, gate correctly BLOCKED.")

    # Part 4: every gateway call is audit-logged with agent identity.
    print("\n--- Part 4: MCP_TOOL_CALLED audit trail ---")
    events = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "MCP_TOOL_CALLED").all()
    assert len(events) == 3, f"Expected 3 MCP_TOOL_CALLED events, got {len(events)}"
    tools_called = set()
    for e in events:
        d = json.loads(e.details)
        assert d["agent_id"] == "test-agent-007"
        assert d["clearance"] == "INTERNAL"
        assert d["expert_model_id"] == model.id
        assert d["gateway_version"] == "mcp-gateway-v1"
        assert d["timestamp"]
        tools_called.add(d["tool_name"])
    assert tools_called == {"ask_expert", "get_trust_score", "check_gate_status"}
    # The underlying ASK_EXPERT event carries the agent as actor.
    ask_event = session.query(db.AuditEvent).filter(db.AuditEvent.event_type.like("ASK_EXPERT%")).order_by(db.AuditEvent.id.desc()).first()
    assert ask_event.actor == "test-agent-007", "Underlying query event must carry the agent identity"
    print("Part 4 passed: gateway calls audited with agent id, clearance, tool, model, timestamp.")

    # Part 5: Tier 2 governance surface.
    print("\n--- Part 5: Tier 2 - provenance, conflicts, revision history ---")
    prov = mcp_gateway.get_provenance(internal.id, session=session)
    assert prov["asset_id"] == internal.id
    assert prov["source_hash"] and prov["approved_by"] == "qa"
    assert prov["revision"] == 1 and prov["revision_count"] == 1, \
        f"Approved asset must carry its baseline revision: {prov['revision']}/{prov['revision_count']}"
    assert "extraction_method" in prov and "access_level" in prov

    conflicts = mcp_gateway.get_conflicts(model.id, session=session)
    assert conflicts["semantic_conflict_score"] is not None
    assert len(conflicts["relationships"]) == 1
    rel = conflicts["relationships"][0]
    assert rel["classification"] == "DIRECT_CONTRADICTION" and rel["status"] == "DETECTED"
    assert "content" not in rel, "Conflict relationships must not leak asset content"

    history = mcp_gateway.get_revision_history(internal.id, session=session)
    assert history["asset_id"] == internal.id and isinstance(history["revisions"], list)
    print("Part 5 passed: Tier 2 tools return contract-shaped governance metadata.")

    # Part 6: clearance denial on Tier 2 tools is itself an audit event.
    print("\n--- Part 6: Access denial for above-clearance assets ---")
    try:
        mcp_gateway.get_provenance(executive.id, session=session)
        raise AssertionError("EXECUTIVE asset provenance served to INTERNAL agent!")
    except ValueError as e:
        assert "Access denied" in str(e)
    try:
        mcp_gateway.get_revision_history(executive.id, session=session)
        raise AssertionError("EXECUTIVE revision history served to INTERNAL agent!")
    except ValueError:
        pass
    denials = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "MCP_ACCESS_DENIED").all()
    assert len(denials) == 2, f"Expected 2 MCP_ACCESS_DENIED events, got {len(denials)}"
    d = json.loads(denials[0].details)
    assert d["agent_id"] == "test-agent-007" and d["required_access_level"] == "EXECUTIVE"
    print("Part 6 passed: denials enforced and audit-logged with required clearance.")

    session.close()
    print("\n=== All MCP Gateway tests passed successfully! ===")


if __name__ == "__main__":
    main()
