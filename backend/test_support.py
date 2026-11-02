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


# ------------------------------------------------ D33 adversarial answerers
# v2.5.0 WS2: the shapes that broke lexical refusal detection, derived from
# any CI contract-follower. A runner that reads the declared status (D33)
# finds the SAME refusal-backed gaps under the first two; one that parsed
# prose would not. The third proves "missing header = UNDETERMINED, never
# guessed".
from app.package_consumer import parse_answer_status as _parse   # noqa: E402

ADVERSARIAL_SCOPE = "the procedure the question asks for (adversarial fixture)"


def adversarial_answerer(base, mode):
    """Wrap a CI answerer. mode:
      "scoped"   - REFUSED -> STATUS: PARTIAL with a REFUSED_SCOPE line and
                   NO refusal marker anywhere; ANSWERED -> the same answer
                   with the marker mentioned mid-text.
      "headless" - every answer loses its status line (UNDETERMINED)."""
    def answer(question):
        result = dict(base(question))
        text = result.get("answer") or ""
        status = _parse(text, "empkg-v1.1")["answer_status"]
        lines = text.splitlines()
        body = "\n".join(lines[1:]).strip()
        if mode == "headless":
            result["answer"] = body
        elif status == "REFUSED":
            result["answer"] = (f"STATUS: PARTIAL\nREFUSED_SCOPE: {ADVERSARIAL_SCOPE}\n"
                                "The governed assets offer related context only.")
        else:
            result["answer"] = (text + "\nFor anything beyond this: INSUFFICIENT "
                                "EVIDENCE - mentioned mid-text, not a refusal.")
        return result
    return answer


def refusal_backed(findings):
    """(skill, question) of every REFUSAL_BACKED finding - the identity the
    adversarial runs must reproduce."""
    return sorted((f["skill"], f.get("question")) for f in findings
                  if f.get("evidence_basis") == "REFUSAL_BACKED")


def d33_adversarial_proof(rerun, answerer, first, agent_token=None):
    """THE D33 ADVERSARIAL PROOF for one workbench (v2.5 WS2).

    rerun(answerer, vault_dir) must repeat the suite's baseline run with
    the given answerer into the given (fresh) vault. Asserts:
      scoped   - EXACTLY the baseline refusal-backed findings, each carrying
                 the declared refused scope (no marker anywhere), and no
                 extra finding from the mid-text mentions;
      headless - no refusal-backed finding at all; every read answer is
                 UNDETERMINED (never guessed).
    Returns the number of refusal-backed findings reproduced."""
    import subprocess
    import tempfile
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = refusal_backed(first["findings"])
    assert base, "the corpus must plant refusal-backed gaps"
    for mode in ("scoped", "headless"):
        vault = tempfile.mkdtemp(prefix=f"em_d33_{mode}_")
        r = subprocess.run([sys.executable, os.path.join(repo, "vault", "bootstrap.py"),
                            "--vault-dir", vault], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        if agent_token:
            os.environ["EM_AGENT_TOKEN"] = agent_token
        try:
            run = rerun(adversarial_answerer(answerer, mode), vault)
        finally:
            if agent_token:
                os.environ.pop("EM_AGENT_TOKEN", None)
        got, counts = refusal_backed(run["findings"]), run["answer_status_counts"]
        if mode == "scoped":
            assert got == base, ("scoped refusals must reproduce the gaps", base, got)
            for f in run["findings"]:
                if f.get("evidence_basis") == "REFUSAL_BACKED":
                    assert any(ADVERSARIAL_SCOPE in line for line in f["evidence_lines"]), f
            assert "REFUSED" not in counts and "UNDETERMINED" not in counts, counts
        else:
            assert got == [], ("a headless answer must never mint a finding", got)
            assert set(counts) == {"UNDETERMINED"}, counts
    return len(base)
