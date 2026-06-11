"""Shared fixture for the Identity Boundary (v1.0): governed actors for
the standalone test suites.

Tests act the way production actors act - real principal, real password
credential, real session token, real IdentityFact lineage. There is
deliberately NO bypass: if a suite can fabricate an actor more cheaply
than production can, the suite is no longer testing the boundary.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import identity

_PASSWORD = "test-suite-password-123"
_cache = {}


def governed_actor(session, name="test_officer", role="GOVERNANCE_REVIEWER"):
    """Get-or-create a HUMAN principal with the given name, authenticate it,
    and return a boundary-decided Actor. display_name == name so suites that
    assert recorded actor strings keep asserting the same values."""
    principal = identity.get_principal(session, name)
    if principal is None:
        principal = identity.create_principal(session, name=name, display_name=name,
                                              kind="HUMAN", role=role, created_by="test-suite")
        identity.set_password(session, principal, _PASSWORD, actor=name)
    token, _ = identity.authenticate_password(session, name, _PASSWORD)
    if token is None:
        raise RuntimeError(f"test_support could not authenticate '{name}'")
    p, c = identity.resolve_token(session, token)
    return identity.Actor(p, "PASSWORD", credential=c)
