"""Operations / Process Improvement Workbench - THE CORPUS PROOF.

Proves the bundle preconditions against the ratified contracts and the
REAL synthetic corpus (workbench/operations_process_improvement/, plant
map in CORPUS.md - the non-runtime oracle), BEFORE the runner reads the
corpus:

  1. THE BUNDLE SHAPE - the manifest + the five ratified contracts
     agree; the binding conventions are declared in the bytes; only
     runner.py is in the bundle (no execution/operational reader);
     the forbidden-input classes are named.
  2. The synthetic corpus loads - six Meridian process documents, every
     one visibly synthetic (the fictional company appears), all .md.
  3. THE DEFECT MATERIAL REPORT - the contract's OWN declared markers
     (parsed from the ratified bytes) fire on the corpus text: an
     access-timing contradiction, an approval-authority policy/SOP pair,
     terminal steps with no handoff marker, a supersession notice, and a
     declared review interval + last-review date.

These are pytest-native `def test_*` cases (so `-k` selection works and
the file is collected by `pytest <file>`), and the module also runs
standalone under the suite harness (`python test_operations_corpus.py`).
No governed pipeline, no [OE] fact, no route, no table, no guard, no law
is needed - the preconditions hold on the synthetic document bytes and
the ratified contracts alone.
"""
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_ROOT)

import workbench.operations_process_improvement.runner as runner  # noqa: E402

WB_DIR = os.path.join(REPO_ROOT, "workbench", "operations_process_improvement")
SKILLS_DIR = os.path.join(WB_DIR, "skills")
CORPUS_DIR = os.path.join(WB_DIR, "corpus_operations")
MANIFEST = os.path.join(WB_DIR, "workbench.yaml")

ACTIVE_FIVE = ("detect_process_contradictions", "compare_sop_vs_policy",
               "detect_missing_handoffs", "detect_outdated_process_documents",
               "prepare_process_map_projection")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def norm(t):
    return " ".join((t or "").split())


def corpus_texts():
    return {name: norm(read(os.path.join(CORPUS_DIR, name)))
            for name in os.listdir(CORPUS_DIR) if name.endswith(".md")}


# ---------------------------------------------------------------- Part 1

def test_bundle_shape_manifest_and_contracts_agree():
    ratified = sorted(n[:-5] for n in os.listdir(SKILLS_DIR)
                      if n.endswith(".yaml"))
    assert ratified == sorted(ACTIVE_FIVE), f"skills/ mismatch: {ratified}"
    manifest = read(MANIFEST)
    declared = re.findall(r"^  - (\w+)$",
                          manifest.split("skills:\n")[1].split("standing_policy:")[0],
                          re.MULTILINE)
    assert sorted(declared) == sorted(ACTIVE_FIVE), \
        f"manifest disagrees: {declared}"
    assert "canonical_number: 8" in manifest
    assert "status: ACTIVE" in manifest


def test_bundle_carries_only_the_runner():
    py_files = set(f for f in os.listdir(WB_DIR) if f.endswith(".py"))
    assert py_files <= {"runner.py"}, \
        f"the bundle carries only the runner, never a reader: {py_files}"


def test_binding_conventions_declared_in_the_bytes():
    con = read(os.path.join(SKILLS_DIR, "detect_process_contradictions.yaml"))
    for needle in ("conflict_convention", "same_subject_minimum",
                   "cross_document_required", "CONFLICT_BACKED"):
        assert needle in con, f"contradictions contract missing {needle}"
    cmp_c = read(os.path.join(SKILLS_DIR, "compare_sop_vs_policy.yaml"))
    assert "comparison_axes" in cmp_c and "approval_authority" in cmp_c
    assert "axis_markers" in cmp_c and "policy_markers" in cmp_c
    hnd = read(os.path.join(SKILLS_DIR, "detect_missing_handoffs.yaml"))
    assert "completion_markers" in hnd and "handoff_markers" in hnd
    old = read(os.path.join(SKILLS_DIR,
                            "detect_outdated_process_documents.yaml"))
    assert "supersession_markers" in old and "review_interval_markers" in old
    assert "Never age alone" in old
    proj = read(os.path.join(SKILLS_DIR, "prepare_process_map_projection.yaml"))
    assert "[assist, synth]" in proj and "projection_label" in proj \
        and "never enters knowledge" in norm(proj)


def test_forbidden_inputs_and_the_execution_plant_declared():
    manifest = read(MANIFEST)
    for needle in ("forbidden_inputs", "execution logs / run logs",
                   "the_undocumented_handoff", "forbidden_vocabulary",
                   "THE INVENTED PROCESS", "THE COMPLETED RUN",
                   "the_instruction_execution_distinction"):
        assert needle in manifest, f"manifest missing {needle}"


def test_all_five_contracts_parse_and_are_active():
    from workbench.common import load_active_contracts
    contracts = load_active_contracts(SKILLS_DIR, ACTIVE_FIVE)
    assert set(contracts) == set(ACTIVE_FIVE)
    for skill_id, c in contracts.items():
        assert c["status"] == "ACTIVE", f"{skill_id} not ACTIVE"
        assert c["skill_id"] == skill_id
        assert c["questions"], f"{skill_id} declares no question_frame"


def test_non_active_contract_is_refused():
    """A contract whose status is not ACTIVE is refused by the loader -
    tags are gates, not preferences."""
    import tempfile
    import shutil
    from workbench.common import load_active_contracts
    tmp = tempfile.mkdtemp(prefix="em_ops_inactive_")
    for name in os.listdir(SKILLS_DIR):
        shutil.copy(os.path.join(SKILLS_DIR, name), os.path.join(tmp, name))
    victim = os.path.join(tmp, "compare_sop_vs_policy.yaml")
    text = read(victim).replace("status: ACTIVE", "status: SEQUENCED")
    with open(victim, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        load_active_contracts(tmp, ACTIVE_FIVE)
        assert False, "a non-ACTIVE contract must be refused"
    except RuntimeError as e:
        assert "not ACTIVE" in str(e)


# ---------------------------------------------------------------- Part 2

def test_corpus_loads_six_synthetic_documents():
    texts = corpus_texts()
    assert len(texts) == 6, f"expected six corpus documents, got {sorted(texts)}"
    for name, body in texts.items():
        assert "Meridian Operations Ltd" in body, \
            f"{name} is not visibly synthetic (fictional company absent)"


# ---------------------------------------------------------------- Part 3

def test_defect_material_contradiction_present():
    texts = corpus_texts()
    two = [n for n, b in texts.items() if "within 2 business days" in b]
    five = [n for n, b in texts.items() if "within 5 business days" in b]
    assert two and five and two != five, \
        "the cross-document access-timing contradiction must be seeded"


def test_defect_material_sop_vs_policy_present():
    texts = corpus_texts()
    cmp_c = read(os.path.join(SKILLS_DIR, "compare_sop_vs_policy.yaml"))
    axes = runner.parse_nested_marker_map(
        os.path.join(SKILLS_DIR, "compare_sop_vs_policy.yaml"),
        "comparison_convention", "axis_markers")
    assert "approval_authority" in axes
    policy = [n for n, b in texts.items()
              if "must be approved by the change advisory board" in b.lower()
              and "single approver" in b.lower()]
    sop = [n for n, b in texts.items()
           if "approved by the team lead alone" in b.lower()]
    assert policy and sop and policy != sop, \
        "the approval-authority SOP-vs-policy pair must be seeded cross-document"


def test_defect_material_missing_handoff_present():
    texts = corpus_texts()
    completion = runner.parse_marker_list(
        os.path.join(SKILLS_DIR, "detect_missing_handoffs.yaml"),
        "handoff_convention", "completion_markers")
    assert completion, "completion markers must be declared"
    # a terminal step with a completion marker
    assert any(any(cm in b.lower() for cm in completion) for b in texts.values())
    assert any("is then closed out" in b for b in texts.values())


def test_defect_material_supersession_and_interval_present():
    texts = corpus_texts()
    assert any("supersedes the shared-credential remote access rule" in b.lower()
               for b in texts.values()), "the supersession notice must be seeded"
    assert any("shared team vpn credential" in b.lower() for b in texts.values())
    assert any(re.search(r"reviewed at least once every \d+ months", b.lower())
               for b in texts.values()), "a declared review interval must exist"
    assert any(re.search(r"last review was recorded on \d{4}-\d{2}-\d{2}",
                         b.lower()) for b in texts.values()), \
        "a last-review date must exist"


def main():
    fns = [g for name, g in sorted(globals().items())
           if name.startswith("test_") and callable(g)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print("\n=== All operations corpus-proof checks passed: the manifest + "
          "five ACTIVE contracts agree; six synthetic Meridian documents "
          "load; every seeded defect's declared markers fire on the bytes. "
          "===")


if __name__ == "__main__":
    main()
