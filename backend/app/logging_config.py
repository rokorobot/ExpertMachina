"""Structured operational logging (audit task T2.1 -
docs/audit-2026-07-07.md, finding H-OPS-1).

The constitutional line this module must never blur:

    The audit ledger is governed proof.
    Structured logging is operational visibility.
    Never substitute one for the other.

Domain events (approvals, custody decisions, authorization denials,
projection renders) stay on the ledger - crud.log_audit_event - exactly
as before. This module carries only the runtime story: errors, warnings,
fallback activations, failed parses, startup diagnostics. Nothing here
is provenance; deleting every log line loses no governed fact.

Secrets discipline (D25, unchanged): no logger call may include bearer
tokens, passwords, outbound credential plaintext, or wrapped keys. The
one-time admin bootstrap credential is deliberately print()ed to the
operator console in main.py and stays OUTSIDE this layer - "shown once,
never logged" is its contract.

Deliberately small (no ELK, no OpenTelemetry, no collectors): stdlib
logging, one stream handler, a request-id contextvar so concurrent
request logs are attributable. JSON formatting can bolt onto the same
seam later without touching call sites.
"""
import contextvars
import logging
import os

LOG_LEVEL = os.environ.get("EM_LOG_LEVEL", "INFO").upper()

# Request correlation: set per-request by the middleware in main.py,
# "-" outside any request (startup, background tasks, scripts).
request_id_var = contextvars.ContextVar("em_request_id", default="-")

_FORMAT = "%(asctime)s %(levelname)s %(name)s [req %(request_id)s] %(message)s"


class RequestContextFilter(logging.Filter):
    """Stamps every record (ours and third-party) with the current
    request id so the format string never KeyErrors."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


_configured = False


def configure_logging() -> None:
    """Configure the root logger once. Idempotent - safe to call from
    main.py import, test suites, and future entry points alike."""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_FORMAT))
    handler.addFilter(RequestContextFilter())
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(LOG_LEVEL)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
