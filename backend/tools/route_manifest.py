"""Route-manifest tool (audit T2.4, the main.py router split).

THE RULING: the router split is a PURE RELOCATION. No endpoint semantics,
model schemas, dependency behavior, path names, status codes, or audit
events may change. This tool is the proof: it emits a deterministic,
diffable manifest of EVERY route's public contract from the live FastAPI
app. Capture it BEFORE the split (main @ f90bb25) and assert byte-identity
AFTER - test_route_manifest.py pins it in CI.

Per route we capture what the ruling protects:
  method(s), path, operation name, tags, status_code, response_model, and
  the SECURITY fingerprint - the ordered dependency chain, with require_perm
  guards resolved to `require_perm:<permission>` (extracted from the guard
  closure) so an auth change cannot hide behind a renamed closure.

Deliberately NOT captured: endpoint module/qualname (that is exactly what
relocation changes) - the point is the CONTRACT is invariant while the code
moves.

Usage:
    python tools/route_manifest.py            # print manifest JSON + digest
    python tools/route_manifest.py --digest   # print only the sha256
"""
import hashlib
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("EM_NLI_VERIFICATION", "off")
os.environ.setdefault("OPENAI_API_KEY", "mock-key")


def _perm_from_guard(call):
    """require_perm(permission) returns a `guard` closure that closes over
    `permission`. Extract it so the manifest records the ACTUAL permission a
    route enforces, not just 'a guard is present'."""
    closure = getattr(call, "__closure__", None)
    if not closure:
        return None
    freevars = getattr(getattr(call, "__code__", None), "co_freevars", ())
    if "permission" in freevars:
        idx = freevars.index("permission")
        try:
            val = closure[idx].cell_contents
            if isinstance(val, str):
                return val
        except (IndexError, ValueError):
            return None
    return None


def _typestr(t):
    """Full-fidelity type string so List[A] != List[B] (a plain __name__
    would collapse every List[...] to 'List' and hide a contract change)."""
    if t is None:
        return None
    s = str(t)
    if s.startswith("<class "):  # plain class -> its dotted name
        return getattr(t, "__name__", s)
    return s.replace("typing.", "")


def _dep_fingerprint(dependant):
    """A stable, ordered list of the dependency chain's call identities.
    require_perm guards resolve to `require_perm:<permission>`; everything
    else to the callable __name__."""
    out = []
    for sub in dependant.dependencies:
        call = sub.call
        perm = _perm_from_guard(call)
        if perm is not None:
            out.append(f"require_perm:{perm}")
        else:
            out.append(getattr(call, "__name__", repr(call)))
        # recurse (require_perm's guard itself depends on require_actor+get_db)
        child = _dep_fingerprint(sub)
        if child:
            out.append({getattr(call, "__name__", "?"): child})
    return out


def build_manifest():
    from fastapi.routing import APIRoute
    from app.main import app

    routes = []
    for r in app.routes:
        if not isinstance(r, APIRoute):
            continue
        routes.append({
            "path": r.path,
            "methods": sorted(r.methods or []),
            "name": r.name,
            "tags": [str(t) for t in (r.tags or [])],
            "status_code": r.status_code,
            "response_model": _typestr(r.response_model),
            "deps": _dep_fingerprint(r.dependant),
        })
    routes.sort(key=lambda x: (x["path"], ",".join(x["methods"])))
    return routes


def digest(manifest):
    blob = json.dumps(manifest, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def main():
    m = build_manifest()
    d = digest(m)
    if "--digest" in sys.argv:
        print(d)
        return
    print(json.dumps(m, indent=2, sort_keys=True))
    print(f"\n# routes={len(m)} sha256={d}")


if __name__ == "__main__":
    main()
