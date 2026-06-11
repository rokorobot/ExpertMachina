import os
import sys
import json
import asyncio
import hashlib

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
# Identity Boundary v1.0: these legacy env vars no longer establish
# identity. They are set to HOSTILE values on purpose - the suite proves
# they are inert (the MCP twin of WS1c's ?actor=Mallory).
os.environ["EM_AGENT_ID"] = "mallory-agent"
os.environ["EM_AGENT_CLEARANCE"] = "EXECUTIVE"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import identity
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

    # Governed agent identity: AGENT principal in the registry (clearance
    # INTERNAL there - the env hostilely claims EXECUTIVE) + an issued token.
    agent = identity.create_principal(session, name="test-agent-007", display_name="test-agent-007",
                                      kind="AGENT", clearance="INTERNAL", created_by="test-suite")
    agent_token, agent_cred = identity.issue_token(session, agent, label="gateway suite")
    os.environ["EM_AGENT_TOKEN"] = agent_token

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
    print("\n--- Part 2: Agent clearance enforced in ask_expert (registry, not env) ---")
    result = mcp_gateway.ask_expert(model.id, "What is the deviation logging deadline?", session=session)
    cited_ids = [c["asset_id"] for c in result["citations"]]
    assert internal.id in cited_ids, "INTERNAL asset missing from citations"
    assert executive.id not in cited_ids, \
        "EXECUTIVE asset leaked: the registry says INTERNAL - the env's hostile EXECUTIVE claim must be inert!"
    assert "answer" in result and "coverage_score" in result and "verification_status" in result
    print("Part 2 passed: registry clearance (INTERNAL) enforced; hostile env EXECUTIVE claim inert.")

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
        assert d["agent_id"] == "test-agent-007", \
            f"Token decides identity, not the env's 'mallory-agent': {d['agent_id']}"
        assert d["clearance"] == "INTERNAL"
        assert d["expert_model_id"] == model.id
        assert d["gateway_version"] == "mcp-gateway-v1"
        assert d["timestamp"]
        tools_called.add(d["tool_name"])
        # WS2b deliverable: MCP audit events carry identity facts.
        assert e.identity_fact_id is not None, "MCP_TOOL_CALLED must carry the agent's fact"
        fact = session.query(db.IdentityFact).filter_by(id=e.identity_fact_id).first()
        assert fact.principal_name == "test-agent-007"
        assert fact.principal_kind == "AGENT"
        assert fact.authentication_method == "API_TOKEN"
        assert fact.credential_fingerprint == agent_cred.fingerprint
    assert tools_called == {"ask_expert", "get_trust_score", "check_gate_status"}
    # The underlying ASK_EXPERT event carries the agent as actor.
    ask_event = session.query(db.AuditEvent).filter(db.AuditEvent.event_type.like("ASK_EXPERT%")).order_by(db.AuditEvent.id.desc()).first()
    assert ask_event.actor == "test-agent-007", "Underlying query event must carry the agent identity"
    print("Part 4 passed: gateway calls audited with token-decided identity, registry clearance,")
    print("               and identity facts (who/kind/method/credential) on every event.")

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
    assert all(e.identity_fact_id is not None for e in denials), "Denials carry identity facts too"
    print("Part 6 passed: denials enforced and audit-logged with required clearance.")

    # Part 7: the WS2b boundary proof - an agent cannot assert who it is.
    print("\n--- Part 7: Agent identity is governed (token, registry, live revocation) ---")
    # 7a: registry clearance change takes effect on the NEXT call (per-call
    # resolution) - promote the agent and the EXECUTIVE asset is served.
    agent.clearance = "EXECUTIVE"
    session.commit()
    prov = mcp_gateway.get_provenance(executive.id, session=session)
    assert prov["asset_id"] == executive.id, "Registry promotion must take effect immediately"
    agent.clearance = "INTERNAL"
    session.commit()
    # 7b: no token + legacy env present -> explicit refusal naming the dead vars.
    saved = os.environ.pop("EM_AGENT_TOKEN")
    try:
        mcp_gateway.get_trust_score(model.id, session=session)
        raise AssertionError("Unauthenticated agent must be refused")
    except PermissionError as e:
        assert "EM_AGENT_ID" in str(e) and "EM_AGENT_TOKEN" in str(e), \
            f"Refusal must name the dead env vars explicitly: {e}"
    refusals = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "MCP_AUTH_REFUSED").all()
    assert refusals and json.loads(refusals[-1].details)["reason"] == "env_asserted_identity"
    assert "EM_AGENT_ID" in json.loads(refusals[-1].details)["legacy_env_vars_present"]
    # 7c: no token, no legacy vars -> refused and audited as no_token.
    saved_id = os.environ.pop("EM_AGENT_ID")
    saved_cl = os.environ.pop("EM_AGENT_CLEARANCE")
    try:
        mcp_gateway.get_trust_score(model.id, session=session)
        raise AssertionError("Unauthenticated agent must be refused")
    except PermissionError:
        pass
    refusals = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "MCP_AUTH_REFUSED").all()
    assert json.loads(refusals[-1].details)["reason"] == "no_token"
    os.environ["EM_AGENT_ID"] = saved_id
    os.environ["EM_AGENT_CLEARANCE"] = saved_cl
    # 7d: garbage token -> refused.
    os.environ["EM_AGENT_TOKEN"] = "emk_completely-forged"
    try:
        mcp_gateway.get_trust_score(model.id, session=session)
        raise AssertionError("Forged token must be refused")
    except PermissionError:
        pass
    # 7e: non-AGENT principals don't pass the gateway even with a valid token.
    svc = identity.create_principal(session, name="ci-service", display_name="ci-service",
                                    kind="SERVICE", created_by="test-suite")
    svc_token, _ = identity.issue_token(session, svc, label="not-an-agent")
    os.environ["EM_AGENT_TOKEN"] = svc_token
    try:
        mcp_gateway.get_trust_score(model.id, session=session)
        raise AssertionError("SERVICE token must not pass the agent gateway")
    except PermissionError as e:
        assert "SERVICE" in str(e)
    # 7f: revocation kills a LIVE session - same env token, next call fails.
    os.environ["EM_AGENT_TOKEN"] = saved
    mcp_gateway.get_trust_score(model.id, session=session)  # still works
    identity.revoke_credential(session, agent_cred, actor="admin", reason="compromised")
    try:
        mcp_gateway.get_trust_score(model.id, session=session)
        raise AssertionError("Revoked token must fail closed mid-session")
    except PermissionError:
        pass
    print("Part 7 passed: registry clearance is live; no-token/forged/non-agent refused")
    print("               (legacy env vars named in the refusal); revocation kills live sessions.")

    session.close()
    print("\n=== All MCP Gateway tests passed successfully! ===")


if __name__ == "__main__":
    main()
