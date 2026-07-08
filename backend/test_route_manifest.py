"""Route-manifest guard (audit T2.4, the main.py router split).

THE RULING: the router split is a PURE RELOCATION - no endpoint semantics,
path names, status codes, response models, dependency behavior, or audit
events may change. This suite is the enforceable form: it rebuilds the live
route contract (method, path, name, tags, status_code, response_model, and
the resolved security dependency chain incl. require_perm:<permission>) from
the FastAPI app and asserts it equals the frozen baseline captured at
f90bb25 (pre-split) - byte-for-byte, 87 routes.

Like test_workbench_projection.py's D24 snapshot, this is permanent: a future
change that legitimately alters a route's contract updates FROZEN_DIGEST here
in the same commit, alongside the reason. A silent drift fails CI.

AMENDMENT LOG (the loud, ratified door-growth trail):
  87 -> 88 (v2.0 WS2, D32 Exception Stewardship): +1 route,
  `POST /api/projects/{project_id}/stewardship`
  (require_perm:assets:review). The FIRST ratified use of this
  amendment path - the guard is designed to make door growth loud, and
  this is what loud looks like: a one-line, reason-carrying re-freeze in
  the same commit that mounts the door. Scoped and ratified at the v2.0
  WS0/WS1 gates (docs/exception-stewardship-v2.0.md, D32).
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("EM_NLI_VERIFICATION", "off")
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from tools.route_manifest import build_manifest, digest

# Baseline was f90bb25 (post-audit-hardening) at 87 routes; amended to 88
# at v2.0 WS2 (the one ratified stewardship door - the amendment log above).
# Full-fidelity response models + resolved permissions.
FROZEN_ROUTE_COUNT = 88
FROZEN_DIGEST = "d8d4eaa59996ce532c42a497845a46ba733dbe9e37ce5f7bda5a83fbe2d3f08b"

GUIDANCE = ("The route contract is frozen. If a route's contract legitimately "
            "changed, update FROZEN_DIGEST (and the count) here in the same "
            "commit, with the reason in the amendment log above - never silently.")


def main():
    manifest = build_manifest()
    live_count = len(manifest)
    live_digest = digest(manifest)

    assert live_count == FROZEN_ROUTE_COUNT, (
        f"route count changed: {live_count} != {FROZEN_ROUTE_COUNT}. {GUIDANCE}")
    assert live_digest == FROZEN_DIGEST, (
        f"route contract drifted from the pre-split baseline.\n"
        f"  live  : {live_digest}\n  frozen: {FROZEN_DIGEST}\n{GUIDANCE}")

    print(f"Route-manifest guard passed: {live_count} routes, contract "
          f"byte-identical to the pre-split baseline (sha256 "
          f"{live_digest[:16]}...). Pure relocation confirmed.")


if __name__ == "__main__":
    main()
