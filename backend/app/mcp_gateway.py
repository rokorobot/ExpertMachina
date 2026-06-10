import os
import json
import datetime

from app import database as db
from app import crud
from app import query_engine
from app import conflict_engine
from app import trust

# MCP Agent Gateway (MVP 0.9 Sprint 1) - READ-ONLY.
#
# The gateway exposes Governance Contract v1; it adds no semantics of its
# own. Every tool delegates to the exact functions the REST console uses,
# and every call emits an MCP_TOOL_CALLED audit event - the gateway itself
# is part of the governance boundary.
#
# Agent identity and clearance come from the MCP server configuration
# (per-agent connection): EM_AGENT_ID and EM_AGENT_CLEARANCE. Clearance
# follows Access Model v1 (PUBLIC < INTERNAL < RESTRICTED < EXECUTIVE)
# and defaults to the most restrictive tier when unset.

GATEWAY_VERSION = "mcp-gateway-v1"
VALID_CLEARANCES = ("PUBLIC", "INTERNAL", "RESTRICTED", "EXECUTIVE")


def agent_identity() -> dict:
    clearance = os.environ.get("EM_AGENT_CLEARANCE", "PUBLIC").upper()
    if clearance not in VALID_CLEARANCES:
        clearance = "PUBLIC"
    return {
        "agent_id": os.environ.get("EM_AGENT_ID", "unidentified-agent"),
        "clearance": clearance,
    }


def _audit_tool_call(session, tool_name: str, expert_model_id, extra: dict = None):
    identity = agent_identity()
    crud.log_audit_event(
        session,
        actor=identity["agent_id"],
        event_type="MCP_TOOL_CALLED",
        target_id=str(expert_model_id) if expert_model_id is not None else None,
        details=json.dumps({
            "tool_name": tool_name,
            "agent_id": identity["agent_id"],
            "clearance": identity["clearance"],
            "expert_model_id": expert_model_id,
            "gateway_version": GATEWAY_VERSION,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            **(extra or {})
        })
    )


def ask_expert(expert_model_id: int, question: str, session=None) -> dict:
    """Verified Answer v1 (Governance Contract section 8), under the
    calling agent's clearance."""
    own_session = session is None
    session = session or db.SessionLocal()
    try:
        identity = agent_identity()
        _audit_tool_call(session, "ask_expert", expert_model_id, {"question": question})
        result = query_engine.execute_expert_query(
            session,
            expert_model_id=expert_model_id,
            question=question,
            caller_access_level=identity["clearance"],
            actor=identity["agent_id"]
        )
        return result
    finally:
        if own_session:
            session.close()


def get_trust_score(expert_model_id: int, session=None) -> dict:
    """Trust Score v1 (Governance Contract section 7)."""
    own_session = session is None
    session = session or db.SessionLocal()
    try:
        _audit_tool_call(session, "get_trust_score", expert_model_id)
        return trust.compute_trust_score(session, expert_model_id)
    finally:
        if own_session:
            session.close()


def check_gate_status(expert_model_id: int, session=None) -> dict:
    """Compile Gate v1 verdict (Governance Contract section 6),
    previewed without side effects."""
    own_session = session is None
    session = session or db.SessionLocal()
    try:
        _audit_tool_call(session, "check_gate_status", expert_model_id)
        gate = conflict_engine.evaluate_compile_gate(session, expert_model_id)
        return {
            "expert_model_id": expert_model_id,
            "status": "ALLOWED" if gate["allowed"] else "BLOCKED",
            "reasons": gate["blocking_conflicts"],
            "advisory_conflicts": gate["advisory_conflicts"],
            "dismissed_conflicts": gate["dismissed_conflicts"],
            "conflict_scan_performed": gate["conflict_scan_performed"],
            "policy": gate["policy"]
        }
    finally:
        if own_session:
            session.close()
