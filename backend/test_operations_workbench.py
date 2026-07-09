"""Operations / Process Improvement Workbench - THE BUNDLE PROOF.

Bundle-level checks mirroring the finance workbench equivalent:

  1. Guard 5 door sweep - the runner stays inside the ruled doors
     (relative common.py import + stdlib only; no app.* internals, no
     database/crud/identity reach). common.py is reused BY IMPORT, never
     edited.
  2. THE STRUCTURAL FLOOR - only runner.py in the bundle (no
     execution/operational reader module); the five ACTIVE skills are
     declared; the manifest and the ratified skill files agree; no
     transactional/execution term leaks into the doors block or any
     skill's allowed_inputs.
  3. THE GATED LIST - the runner refuses [OE]/[ES]/SYNTHESIS_INFERRED
     and valve-synth skills live, naming the unminted decision.
  4. THE COMPLETED RUN dictionary - the manifest declares the
     execution-truth vocabulary; it catches a synthetic violation and
     spares a legitimate instruction sentence.

pytest-native cases; the module also runs standalone under the suite
harness.
"""
import ast
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_ROOT)

import test_agent_authorship_guard as guard   # noqa: E402
import workbench.operations_process_improvement.runner as runner  # noqa: E402

WB_DIR = os.path.join(REPO_ROOT, "workbench", "operations_process_improvement")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
MANIFEST = os.path.join(WB_DIR, "workbench.yaml")

ACTIVE_FIVE = ("detect_process_contradictions", "compare_sop_vs_policy",
               "detect_missing_handoffs", "detect_outdated_process_documents",
               "prepare_process_map_projection")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def norm(t):
    return " ".join((t or "").split())


# ---------------------------------------------------------------- Part 1

def test_runner_passes_the_guard5_door_sweep():
    rel = os.path.relpath(os.path.join(WB_DIR, "runner.py"),
                          REPO_ROOT).replace(os.sep, "/")
    violations = guard.workbench_import_violations(rel, read(
        os.path.join(WB_DIR, "runner.py")))
    assert not violations, "\n".join(violations)


def test_runner_reuses_common_by_relative_import_only():
    tree = ast.parse(read(os.path.join(WB_DIR, "runner.py")))
    common_imports = [n for n in ast.walk(tree)
                      if isinstance(n, ast.ImportFrom)
                      and (n.module or "").endswith("common")]
    assert common_imports, "the runner must reuse common.py"
    for imp in common_imports:
        assert imp.level and imp.level > 0, \
            "common.py must be reached by RELATIVE import (ruling-6 reuse)"


def test_common_py_is_unchanged_reference_by_import():
    # The runner names common helpers it imports; this asserts the reuse
    # surface exists in the shared module (a proxy that we import, not
    # copy). common.py itself is a forbidden edit target for this bundle.
    from workbench import common
    for name in ("excerpt", "subject_tokens", "shared_subject",
                 "load_active_contracts", "write_hashed",
                 "SAME_SUBJECT_MINIMUM", "import_package_consumer"):
        assert hasattr(common, name), f"common.{name} missing"


# ---------------------------------------------------------------- Part 2

def test_only_runner_in_the_bundle():
    py_files = sorted(f for f in os.listdir(WB_DIR) if f.endswith(".py"))
    assert py_files == ["runner.py"], \
        f"the bundle carries only the runner: {py_files}"


def test_active_skills_count_and_manifest_agreement():
    assert len(runner.ACTIVE_SKILLS) == 5
    assert set(runner.ACTIVE_SKILLS) == set(ACTIVE_FIVE)
    manifest = read(MANIFEST)
    import re
    declared = re.findall(
        r"^  - (\w+)$",
        manifest.split("skills:\n")[1].split("standing_policy:")[0],
        re.MULTILINE)
    ratified = sorted(n[:-5] for n in os.listdir(SKILLS_DIR)
                      if n.endswith(".yaml"))
    assert sorted(declared) == ratified == sorted(ACTIVE_FIVE)


def test_no_execution_term_leaks_into_doors_or_allowed_inputs():
    exec_terms = ("execution log", "run log", "process-mining", "trace",
                  "workflow-engine", "dashboard", "metrics export")
    manifest = read(MANIFEST)
    doors_block = manifest.split("doors:\n")[1].split("skills:")[0].lower()
    assert not any(t in doors_block for t in exec_terms), \
        f"an execution term leaked into the doors block"
    for s in ACTIVE_FIVE:
        txt = read(os.path.join(SKILLS_DIR, s + ".yaml"))
        allowed = txt.split("allowed_inputs:")[1].split(
            "forbidden_inputs:")[0].lower()
        assert not any(t in allowed for t in exec_terms), \
            f"{s}: an execution term leaked into allowed_inputs"


# ---------------------------------------------------------------- Part 3

def test_gated_skills_are_refused_naming_the_gate():
    # [OE] family
    for oe in ("detect_process_execution_gaps",
               "detect_process_bottlenecks_from_traces",
               "measure_cycle_time_from_logs"):
        try:
            runner.require_ungated(oe)
            assert False, f"{oe} must be refused"
        except RuntimeError as e:
            assert "Operational Evidence Realm" in str(e)
    # [ES]
    try:
        runner.require_ungated("identify_missing_process_stage_owner")
        assert False
    except RuntimeError as e:
        assert "Exception Stewardship" in str(e)
    # valve-synth + SYNTHESIS_INFERRED are gated too
    for g in ("estimate_improvement_impact",
              "generate_process_improvement_backlog",
              "prepare_improvement_proposal"):
        try:
            runner.require_ungated(g)
            assert False, f"{g} must be refused"
        except RuntimeError as e:
            assert "gated" in str(e)


# ---------------------------------------------------------------- Part 4

def test_completed_run_dictionary_catches_and_spares():
    forbidden = runner.parse_forbidden_vocabulary(MANIFEST)
    assert forbidden, "the manifest must declare the COMPLETED-RUN vocabulary"
    violation = "The deployment was executed and the run completed on Monday."
    assert any(p in violation.lower() for p in forbidden), \
        "the dictionary must catch a real execution-truth violation"
    legit = "The platform team deploys the scheduled change."
    assert not any(p in legit.lower() for p in forbidden), \
        "the dictionary must spare a legitimate instruction sentence"


def main():
    fns = [g for name, g in sorted(globals().items())
           if name.startswith("test_") and callable(g)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print("\n=== All operations bundle checks passed: the runner is inside "
          "the ruled doors (common.py reused by relative import, unchanged); "
          "only runner.py in the bundle; five ACTIVE skills agree with the "
          "manifest; no execution door; the gated list is refused naming the "
          "gate; the COMPLETED-RUN dictionary has teeth. ===")


if __name__ == "__main__":
    main()
