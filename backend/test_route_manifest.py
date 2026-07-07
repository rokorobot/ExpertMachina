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
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("EM_NLI_VERIFICATION", "off")
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from tools.route_manifest import build_manifest, digest

# Frozen at f90bb25 (post-audit-hardening), BEFORE the router split.
# 87 routes; full-fidelity response models + resolved permissions.
FROZEN_ROUTE_COUNT = 87
FROZEN_DIGEST = "a9558682393177b85b521f50a20cc4a40b2d301719a43a4bda77bd4d15de6053"

GUIDANCE = ("The router split (T2.4) is a pure relocation. If a route's "
            "contract legitimately changed, update FROZEN_DIGEST (and the "
            "count) here in the same commit, with the reason - never silently.")


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
