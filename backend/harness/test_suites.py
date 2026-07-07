"""The suite harness (audit 2026-07-07, tasks T0.1/T0.2 -
docs/audit-2026-07-07.md, finding H-TEST-1).

CI used to enumerate suites by hand in ci.yml - the mechanism by which
18 of 64 suites silently fell out of CI (all of them green when finally
run; one, test_audit_expansion, had rotted at the identity boundary and
was repaired the day this harness landed). Enumeration is the failure
mode; discovery is the fix:

    Every backend/test_*.py is a suite. A new file is IN CI the moment
    it exists. Leaving one out now requires an explicit, commented
    entry in NOT_SUITES below - visible and reviewable, never silent.

Each suite runs as an isolated subprocess, exactly the isolation the
hand-listed CI always used: the historical suites rebind the
module-global db.engine at IMPORT time, so two of them imported into
one interpreter would cross-wire their databases. pytest contributes
what the hand list could not - automatic discovery, per-suite PASS/FAIL
reporting, and failure aggregation (one broken suite no longer hides
the results of the rest).

Run:  python -m pytest            (from backend/; pytest.ini routes here)
      python -m pytest harness -q
"""
import os
import subprocess
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files matching test_*.py that the per-push harness does NOT run. Every
# entry needs a reason - this list is the only sanctioned way to keep a
# test_*.py out of the per-push CI sweep.
#
# Two kinds live here: non-suites (shared fixtures) and MODEL-DEPENDENT
# suites that belong to the nightly, not per-push. The latter force the
# real NLI cross-encoder on and require the ~1GB model AND its exact
# HuggingFace cache layout - which per-push CI has no business fetching.
# They are the nightly's exclusive gate (nightly-nli.yml, task T0.3),
# which restores the cached model and runs them full-model with a
# fail-on-skip guard, so excluding them here loses zero coverage.
NOT_SUITES = {
    "test_support.py",  # shared fixture module (governed_actor helper), no __main__ suite
    # Model-dependent - nightly only (nightly-nli.yml). test_nli_verification
    # flips EM_NLI on and asserts the model weights-hash fingerprint, which
    # needs the model's real cache snapshot (a live per-push download does not
    # populate it the way the fingerprint path expects - a fresh Linux runner
    # fails on exactly that assertion). test_conflict_engine likewise needs
    # the NLI engine; per-push it would only ever skip.
    "test_nli_verification.py",
    "test_conflict_engine.py",
}

# Per-suite wall-clock ceiling. The slowest suites (package evaluation,
# corpus gates) finish well inside this; a hang fails loudly instead of
# stalling the whole run.
SUITE_TIMEOUT_SECONDS = 900


def _discover():
    names = sorted(
        f for f in os.listdir(BACKEND_DIR)
        if f.startswith("test_") and f.endswith(".py") and f not in NOT_SUITES
    )
    assert names, "Suite discovery found nothing - wrong directory?"
    return names


@pytest.mark.parametrize("suite", _discover())
def test_suite(suite):
    """One governed suite, in its own interpreter."""
    env = dict(os.environ)
    # The same defaults ci.yml sets job-wide; setdefault so an operator
    # (or the future model-cache nightly, T0.3) can override.
    env.setdefault("EM_NLI_VERIFICATION", "off")
    env.setdefault("OPENAI_API_KEY", "mock-key")
    proc = subprocess.run(
        [sys.executable, suite],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=SUITE_TIMEOUT_SECONDS,
    )
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + "\n" + proc.stderr).strip().splitlines()[-40:])
        pytest.fail(
            f"{suite} exited {proc.returncode}. Last output:\n{tail}",
            pytrace=False,
        )
