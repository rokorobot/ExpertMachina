"""Import-cycle guard (audit T3.1, the crud<->identity cycle break).

Before T3.1, app/crud.py imported app/identity at module load while
app/identity reached app/crud through a lazy in-function import
(identity._audit -> crud.log_audit_event). That single edge closed a
crud<->identity import cycle. T3.1 moved the shared function to the neutral
app/audit.py; identity now depends on audit, not crud.

This guard freezes the result: crud may depend on identity, but identity must
NOT depend on crud (by ANY import - top-level or lazy), and the neutral audit
module must depend on neither. It parses the source with AST, so a lazy
`from app import crud` re-introduced inside a function fails CI just as loudly
as a top-level one. Permanent, like the D24 and route-manifest guards.
"""
import ast
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")


def app_module_imports(filename):
    """Every app.* module this file imports, top-level OR inside a function
    (AST walk catches lazy imports too)."""
    src = open(os.path.join(APP, filename), encoding="utf-8").read()
    tree = ast.parse(src)
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            # from app import crud  |  from app.crud import x  |  from app import audit
            if node.module == "app":
                for a in node.names:
                    mods.add(a.name)
            elif node.module and node.module.startswith("app."):
                mods.add(node.module.split(".", 2)[1])
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("app."):
                    mods.add(a.name.split(".", 2)[1])
    return mods


def main():
    crud_imports = app_module_imports("crud.py")
    identity_imports = app_module_imports("identity.py")
    audit_imports = app_module_imports("audit.py")

    # The cycle break: identity must not depend on crud in any form.
    assert "crud" not in identity_imports, (
        "T3.1 regression: app/identity.py imports app/crud (top-level or lazy) - "
        "the crud<->identity cycle is back. The audit-write helper lives in the "
        "neutral app/audit.py; route identity's audit writes through there.")

    # crud legitimately depends on identity (one direction = no cycle).
    assert "identity" in crud_imports, (
        "app/crud.py should still import app/identity (one-directional, no cycle)."
    )

    # The hinge module stays neutral: audit imports neither crud nor identity.
    assert "crud" not in audit_imports and "identity" not in audit_imports, (
        f"app/audit.py must stay neutral (imports neither crud nor identity); "
        f"got {sorted(audit_imports)}.")

    # Behavioral surface preserved: crud re-exports the moved function.
    from app import crud, audit
    assert crud.log_audit_event is audit.log_audit_event, (
        "crud.log_audit_event must re-export app.audit.log_audit_event so its "
        "~18 callers are unchanged.")

    print("Import-cycle guard passed: identity -/-> crud (cycle removed), "
          "crud -> identity one-directional, audit neutral, "
          "crud.log_audit_event re-exported.")


if __name__ == "__main__":
    main()
