"""Audit-ledger write helper (audit T3.1, the crud<->identity cycle break).

`log_audit_event` lived in app/crud.py, but app/identity.py needed it too -
and crud imports identity at module load, so identity could only reach crud
through a lazy in-function `from app import crud` (identity._audit). That
single edge closed a crud<->identity import cycle.

The function depends on NOTHING but the ORM models and datetime, so it is the
neutral hinge: moved here, both crud and identity import it top-level, and
the cycle is gone. crud re-exports it (`crud.log_audit_event`) so its ~18
callers are unchanged. This is a pure relocation - the append-only audit
write behavior is byte-identical; test_import_cycle.py proves the edge is
gone and the harness proves the behavior held.
"""
import datetime

from sqlalchemy.orm import Session

from app import database as db


def log_audit_event(session: Session, actor: str, event_type: str, target_id: str = None,
                    details: str = None, identity_fact_id: int = None):
    # identity_fact_id (Identity Boundary v1.0): the immutable evidence of
    # WHO acted. NULL = pre-boundary legacy; actor remains the readable
    # display string either way.
    event = db.AuditEvent(
        timestamp=datetime.datetime.utcnow(),
        actor=actor,
        event_type=event_type,
        target_id=target_id,
        details=details,
        identity_fact_id=identity_fact_id
    )
    session.add(event)
    session.commit()
    return event
