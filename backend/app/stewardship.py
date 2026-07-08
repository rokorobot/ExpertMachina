"""Exception Stewardship (v2.0, D32) - the human-decision layer of the
computed exception queue.

    The exception never becomes a row; the human decisions about it do.

Exception EXISTENCE is computed by governance_inbox at read time, always.
What persists is the human stewardship decision: an append-only,
identity-backed STEWARDSHIP_DECISION AuditEvent (D3 shape), keyed to the
exception's stable computed identity (the Governance Inbox item id,
key_version inbox-item-v1). This module is the ONLY writer of that event
type and the ONLY place the vocabulary lives; it constructs no AuditEvent
directly (the governed audit writer is the one pen) and never mutates or
deletes a ledger row (append-only is law - a retraction is a new CLEARED
event, never an edit).

Guard 7 (test_exception_stewardship_guard.py) is the permanent boundary:
it asserts STEWARDSHIP_KINDS below equals its ratified spec, that no
exception/stewardship table exists, that the computed queue is identical
with these decisions present vs absent, and that no AGENT can hold the
stewardship pen. This module is written to satisfy that guard, not to be
trusted on its word.
"""
import datetime
import json

from sqlalchemy.orm import Session

from app import database as db
from app import identity
from app.audit import log_audit_event

EVENT_TYPE = "STEWARDSHIP_DECISION"
KEY_VERSION = "inbox-item-v1"

# THE RATIFIED DECISION VOCABULARY (D32 companion ruling; v2.0 WS0),
# closed at seven kinds. The value is the tuple of kind-specific REQUIRED
# fields, beside the always-required exception_key / exception_type / kind.
# This dict is the spec Guard 7 pins - it must not drift.
STEWARDSHIP_KINDS = {
    "ACKNOWLEDGED": (),
    "RISK_ACCEPTED": ("reason",),
    "DISMISSED": ("reason",),
    "ESCALATED": ("reason", "escalated_to"),
    "OWNER_ASSIGNED": ("owner_label",),   # owner_principal_id optional metadata
    "DUE_DATE_SET": ("due_date",),        # YYYY-MM-DD declared; overdue COMPUTED
    "CLEARED": ("reason", "clears_kind"),  # the append-only undo
}

# Optional, kind-specific metadata a decision MAY carry (validated when
# present, never required). owner_principal_id lets an owner be a governed
# principal WHEN it is one - EM does not govern the org chart, so the label
# is authoritative and the principal id is evidence, never a requirement.
_OPTIONAL_FIELDS = {
    "OWNER_ASSIGNED": ("owner_principal_id",),
}


class StewardshipError(ValueError):
    """A decision the vocabulary refuses (unknown kind, missing required
    field, malformed date, CLEARED naming a non-kind). The route maps it
    to 400; the human is told exactly what was wrong."""


def validate_decision(details: dict) -> list:
    """Return a list of problems ([] = valid). The single source of truth
    for the vocabulary, shared by record_decision and any caller that wants
    to check before writing."""
    problems = []
    kind = details.get("kind")
    if kind not in STEWARDSHIP_KINDS:
        return [f"unknown decision kind: {kind!r} (ruled kinds: "
                f"{sorted(STEWARDSHIP_KINDS)})"]
    for field in ("exception_key", "exception_type"):
        if not details.get(field):
            problems.append(f"{kind}: missing {field}")
    if details.get("key_version") != KEY_VERSION:
        problems.append(f"{kind}: key_version must be {KEY_VERSION!r}")
    for field in STEWARDSHIP_KINDS[kind]:
        if details.get(field) in (None, ""):
            problems.append(f"{kind}: missing required field {field!r}")
    if kind == "DUE_DATE_SET" and details.get("due_date"):
        try:
            datetime.date.fromisoformat(str(details["due_date"]))
        except ValueError:
            problems.append("DUE_DATE_SET: due_date must be a real YYYY-MM-DD "
                            "date (declared by the human; overdue is computed "
                            "at read time, never stored)")
    if kind == "CLEARED":
        target = details.get("clears_kind")
        if target not in STEWARDSHIP_KINDS or target == "CLEARED":
            problems.append("CLEARED: clears_kind must name a ruled non-CLEARED "
                            "kind")
    return problems


def record_decision(session: Session, actor: identity.Actor, exception_key: str,
                    exception_type: str, kind: str, **fields) -> dict:
    """Write ONE append-only STEWARDSHIP_DECISION event, identity-backed
    (D20). No governed knowledge changes; no exception row is created,
    mirrored, mutated, or deleted. Returns the recorded decision as a dict.

    The caller is responsible for having confirmed (via the computed inbox)
    that exception_key names a real, currently-present exception - a phantom
    key never reaches here."""
    identity.require_actor_object(actor)
    # keep only recognized optional metadata; unknown extras are dropped
    # rather than silently persisted (the vocabulary is closed).
    allowed_optional = set(_OPTIONAL_FIELDS.get(kind, ()))
    clean = {k: v for k, v in fields.items()
             if k in STEWARDSHIP_KINDS[kind] or k in allowed_optional}
    details = {"key_version": KEY_VERSION, "exception_key": exception_key,
               "exception_type": exception_type, "kind": kind, **clean}
    problems = validate_decision(details)
    if problems:
        raise StewardshipError("; ".join(problems))
    event = log_audit_event(
        session, actor=actor.principal.name, event_type=EVENT_TYPE,
        target_id=exception_key, details=json.dumps(details),
        identity_fact_id=actor.fact(session).id)
    return _event_to_decision(event, details)


def _event_to_decision(event, details: dict) -> dict:
    out = {"decision_id": event.id, "kind": details["kind"],
           "exception_key": details["exception_key"],
           "exception_type": details["exception_type"],
           "decided_by": event.actor,
           "identity_fact_id": event.identity_fact_id,
           "decided_at": event.timestamp.isoformat() if event.timestamp else None}
    for field in ("reason", "escalated_to", "owner_label", "owner_principal_id",
                  "due_date", "clears_kind"):
        if field in details:
            out[field] = details[field]
    return out


def _decisions_for_keys(session: Session, keys: set) -> dict:
    """{exception_key: [decision dict in chronological order]} for the given
    keys, projected from the ledger alone (append-only, ordered by event id
    = chronological). Read-only."""
    if not keys:
        return {}
    grouped = {}
    for event in session.query(db.AuditEvent).filter(
            db.AuditEvent.event_type == EVENT_TYPE,
            db.AuditEvent.target_id.in_(sorted(keys))
    ).order_by(db.AuditEvent.id).all():
        try:
            details = json.loads(event.details or "{}")
        except ValueError:
            continue
        if details.get("key_version") != KEY_VERSION:
            continue
        grouped.setdefault(event.target_id, []).append(
            _event_to_decision(event, details))
    return grouped


def _current_state(decisions: list, now: datetime.datetime) -> dict:
    """The current stewardship state for one exception: latest event per
    kind, with CLEARED removing the kind it names (the append-only undo).
    DUE_DATE_SET carries a COMPUTED `overdue` derived from `now` - never
    stored. `history_count` records how many decisions stand behind the
    current state."""
    active = {}
    for decision in decisions:                       # chronological
        kind = decision["kind"]
        if kind == "CLEARED":
            active.pop(decision.get("clears_kind"), None)
        else:
            active[kind] = decision
    state = {"active": active, "history_count": len(decisions)}
    due = active.get("DUE_DATE_SET")
    if due and due.get("due_date"):
        try:
            due_date = datetime.date.fromisoformat(str(due["due_date"]))
            state["overdue"] = due_date < now.date()
            state["due_date"] = due["due_date"]
        except ValueError:
            pass
    return state


def stewardship_for(session: Session, keys, now: datetime.datetime = None) -> dict:
    """{exception_key: current-state dict} for keys that carry any decision.
    The read-time join the Governance Inbox annotates each item with. Keys
    with no decisions are simply absent (an unstewarded exception). Overdue
    is computed against `now` (defaults to utcnow), matching the inbox's
    existing read-time clock; it is never persisted."""
    now = now or datetime.datetime.utcnow()
    grouped = _decisions_for_keys(session, set(keys))
    return {key: _current_state(decisions, now)
            for key, decisions in grouped.items()}
