"""Operations / Process Improvement Workbench - THE DIAGNOSIS PROOF.

The runner meets the five ratified contracts over the synthetic corpus,
driven through a lightweight in-process package + injected answerer /
graph-client seams (exactly as the shipped reference suites inject their
CI seams - no execution/operational door is ever opened, and no
heavyweight ingestion is needed to prove the diagnosis):

  - each [now] skill produces evidence-cited findings on the seeded
    corpus (PROCESS_CONTRADICTION, SOP_POLICY_MISMATCH, MISSING_HANDOFF,
    OUTDATED_PROCESS_DOCUMENT), and the assist writes a cited,
    non-authoritative process map;
  - refusal-first: at least one refusal/no-evidence case PER skill
    (named `*refusal*` so `-k refusal` selects them) - never a
    fabricated finding when the corpus lacks support;
  - the denied-access case (named `*denied*` so `-k denied` selects it):
    when clearance excludes needed documents the workbench degrades to
    EXPLICIT refusal (an empty, declared result), never silent omission,
    never fabrication;
  - THE EXECUTION PLANT: an injected execution-record fact is DECLINED
    naming [OE] and never becomes a finding (adversarial);
  - projection-only: the run writes nothing outside the vault's
    08_proposals / 07_agent_workspaces, and the COMPLETED-RUN vocabulary
    never appears on any written byte.

pytest-native cases (so `-k` selection works and `pytest <file>`
collects them); the module also runs standalone under the suite harness.
"""
import os
import re
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_ROOT)

import workbench.operations_process_improvement.runner as runner  # noqa: E402

WB_DIR = os.path.join(REPO_ROOT, "workbench", "operations_process_improvement")
CORPUS_DIR = os.path.join(WB_DIR, "corpus_operations")
MANIFEST = os.path.join(WB_DIR, "workbench.yaml")

AS_OF = "2026-07-09"
REFUSAL = ("INSUFFICIENT EVIDENCE - the governed evidence offered does not "
           "contain the answer to this question.")


def norm(t):
    return " ".join((t or "").split())


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- fixtures
# The corpus becomes governed knowledge entries. Each document is one
# asset carrying its full text (the runner reads `content`, `name`,
# `provenance.source_document`, `source_class`, `asset_id`). This mirrors
# the shipped package shape without the heavyweight ingestion pipeline.

# The governed pipeline splits each document into sentence/clause-level
# knowledge assets. The fixture mirrors that: each document contributes a
# handful of assets (the meaningful sentences the seeded defects live in),
# with a stable per-document key so a suite can EXCLUDE a whole document by
# key (the denied-access / single-side refusal cases). This is the faithful
# shape - the runner's excerpting and same-subject rules operate on
# sentence-level facts exactly as they do over the real package.

# key -> ordered list of sentence-level fact contents. Each document is
# visibly synthetic (the fictional company appears in its first fact).
DOCUMENTS = {
    "onboarding": (
        "employee-onboarding-sop.md",
        [
            "Meridian Operations Ltd Employee Onboarding SOP OPS-ON-01. This "
            "SOP defines the standard onboarding process for new hires.",
            "Step 1. The People team creates the employee record. On "
            "completion the People team hands off to the IT team to provision "
            "accounts.",
            "Step 4. The onboarding buddy programme runs for the first two "
            "weeks. The onboarding buddy programme is complete after the "
            "two-week period.",
            "New hire system access requests must be approved within 2 "
            "business days of the request.",
        ]),
    "access_request": (
        "access-request-procedure.md",
        [
            "Meridian Operations Ltd Access Request Procedure OPS-AC-02. This "
            "procedure defines how a request for access is reviewed and "
            "provisioned.",
            "Staff system access requests must be approved within 5 business "
            "days of the request.",
            "Step 2. When the resource owner approves the access request, the "
            "request is routed to the IT team for provisioning.",
            "When access is no longer required the access record is marked "
            "for revocation. The marked access record is then closed out.",
        ]),
    "change_policy": (
        "change-management-policy.md",
        [
            "Meridian Operations Ltd Change Management Policy POL-CM-01. This "
            "policy governs how production changes are authorized.",
            "Every production change must be approved by the Change Advisory "
            "Board before it is deployed. No production change may be deployed "
            "on the authority of a single approver.",
            "This policy must be reviewed at least once every 12 months. The "
            "last review was recorded on 2024-01-15.",
        ]),
    "change_sop": (
        "change-management-sop.md",
        [
            "Meridian Operations Ltd Change Management SOP OPS-CM-03. This SOP "
            "defines the operational steps for a production change.",
            "Step 2. The team lead reviews the change ticket. A production "
            "change may be approved by the team lead alone before it is "
            "deployed.",
            "This SOP must be reviewed at least once every 6 months. The last "
            "review was recorded on 2024-02-01.",
        ]),
    "remote_sop": (
        "remote-access-sop.md",
        [
            "Meridian Operations Ltd Remote Access SOP OPS-RA-04. This SOP "
            "defines how a staff member is granted remote access.",
            "Remote access to Meridian systems is granted using a shared team "
            "VPN credential issued by the IT team.",
        ]),
    "access_governance": (
        "access-governance-policy.md",
        [
            "Meridian Operations Ltd Access Governance Policy POL-AG-02. This "
            "policy supersedes the shared-credential remote access rule "
            "stated in the Remote Access SOP OPS-RA-04.",
            "Remote access is granted using a personal individually issued "
            "VPN credential with multi-factor authentication. Shared team VPN "
            "credentials are prohibited.",
            "This policy must be reviewed at least once every 12 months. The "
            "last review was recorded on 2026-05-01.",
        ]),
}

DOC_ORDER = ("onboarding", "access_request", "change_policy", "change_sop",
             "remote_sop", "access_governance")

# The execution-record PLANT (adversarial): an execution record cannot
# exist in a process-document corpus by accident - it is injected. Even
# "approved", it must be DECLINED as a process-document input, naming
# [OE]; it must never become a finding. It carries execution-record
# markers no instruction sentence carries.
EXECUTION_PLANT = (
    "Meridian change execution record. Run id RUN-7788: the platform team "
    "executed the deployment and the run completed on 2026-07-05. The ticket "
    "was closed on 2026-07-05.")

PLANT_ID = 99


def build_knowledge(exclude_docs=None, with_plant=True):
    """Build sentence-level governed assets. `exclude_docs` drops whole
    documents by key (the clearance/refusal cases). Asset ids are stable
    and contiguous within each retained document."""
    exclude_docs = set(exclude_docs or ())
    knowledge = []
    next_id = 1
    for key in DOC_ORDER:
        if key in exclude_docs:
            next_id += 10  # keep ids stable/disjoint across runs
            continue
        name, sentences = DOCUMENTS[key]
        for sentence in sentences:
            knowledge.append({
                "asset_id": next_id,
                "name": name,
                "content": sentence,
                "source_class": "PRIMARY",
                "provenance": {"source_document": name},
            })
            next_id += 1
        next_id = (next_id // 10 + 1) * 10  # pad to the next decade
    if with_plant:
        knowledge.append({
            "asset_id": PLANT_ID,
            "name": "change-execution-record.md",
            "content": EXECUTION_PLANT,
            "source_class": "PRIMARY",
            "provenance": {"source_document": "change-execution-record.md"},
        })
    return knowledge


def asset_ids_for(key, knowledge):
    name = DOCUMENTS[key][0]
    return {e["asset_id"] for e in knowledge if e["name"] == name}


class FakePackageConsumer:
    """The injected .empkg door seam: serves a pre-built package and a
    deterministic retrieve/consume. `answerable` is the set of question
    substrings the packaged answering contract can answer; everything
    else returns the packaged refusal verbatim (refusal-first)."""

    def __init__(self, knowledge, answerable=()):
        self._package = {
            "package_hash": "opsdiag" + "0" * 57,
            "knowledge": knowledge,
            "manifest": {"expert_model_id": 1},
        }
        self._answerable = tuple(answerable)

    def load_package(self, _path):
        return self._package

    def retrieve(self, package, _topic, top_k=8):
        return {"selected": package["knowledge"][:top_k]}

    def consume(self, _path, question):
        for needle in self._answerable:
            if needle.lower() in (question or "").lower():
                return {"answer": "Per the governed evidence: covered.",
                        "cited_asset_ids": [1], "evidence": []}
        return {"answer": REFUSAL, "cited_asset_ids": [], "evidence": []}


class FakeGraphClient:
    def __init__(self, excluded=None):
        self._excluded = excluded or {}

    def get_domain_subgraph(self, _project_id, _domain_prefix):
        return {"excluded": self._excluded}


def make_answerer(fake_pc):
    def answer(question):
        return fake_pc.consume(None, question)
    return answer


def run(knowledge, answerable=(), excluded=None, requested_skills=None):
    vault = tempfile.mkdtemp(prefix="em_ops_vault_")
    os.makedirs(os.path.join(vault, "08_proposals"))
    os.makedirs(os.path.join(vault, "07_agent_workspaces"))
    fake_pc = FakePackageConsumer(knowledge, answerable=answerable)
    return runner.run_diagnostic(
        package_path="unused.empkg", vault_dir=vault, project_id=1,
        agent_principal="operations-agent", binding_id=1,
        graph_client=FakeGraphClient(excluded), as_of=AS_OF,
        answerer=make_answerer(fake_pc), package_consumer=fake_pc,
        requested_skills=requested_skills), vault


def kinds(diag):
    return {f["finding_kind"] for f in diag["findings"]}


def of_kind(diag, kind):
    return [f for f in diag["findings"] if f["finding_kind"] == kind]


# ------------------------------------------------- positive diagnosis cases

def test_each_skill_produces_evidence_cited_findings():
    diag, _vault = run(build_knowledge())
    for kind in ("PROCESS_CONTRADICTION", "SOP_POLICY_MISMATCH",
                 "MISSING_HANDOFF", "OUTDATED_PROCESS_DOCUMENT"):
        found = of_kind(diag, kind)
        assert found, f"{kind} missing from the diagnosis"
        for f in found:
            assert f["evidence_lines"], f"{kind} finding exposes no evidence"
            assert f["cited_assets"], f"{kind} finding cites no assets"
    # every proposal document carries the verbatim evidence on its bytes.
    assert diag["proposals"], "at least one proposal must be written"
    for path in diag["proposals"]:
        body = read(path)
        assert "## Evidence" in body and "verbatim" in body


def test_contradiction_is_cross_document_and_cites_both_sides():
    diag, _vault = run(build_knowledge())
    con = of_kind(diag, "PROCESS_CONTRADICTION")[0]
    assert con["cited_assets"] == sorted(con["cited_assets"])
    assert len(con["cited_assets"]) == 2
    joined = " ".join(con["evidence_lines"]).lower()
    assert "2 business day" in joined and "5 business day" in joined


def test_sop_policy_mismatch_names_axis_and_both_documents():
    diag, _vault = run(build_knowledge())
    mm = of_kind(diag, "SOP_POLICY_MISMATCH")[0]
    assert mm["axis"] == "approval_authority"
    assert "team lead alone" in mm["sop_excerpt"].lower()
    assert "change advisory board" in mm["policy_excerpt"].lower()


def test_outdated_document_supersession_is_revision_backed():
    diag, _vault = run(build_knowledge())
    outs = of_kind(diag, "OUTDATED_PROCESS_DOCUMENT")
    superseded = [f for f in outs
                  if "supersedes" in f["staleness_reason"].lower()]
    assert superseded, "the supersession finding must fire"
    assert "shared team vpn credential" in superseded[0]["excerpt"].lower()


def test_overdue_by_declared_interval_is_revision_backed():
    diag, _vault = run(build_knowledge())
    outs = of_kind(diag, "OUTDATED_PROCESS_DOCUMENT")
    overdue = [f for f in outs if "overdue" in f["staleness_reason"].lower()]
    assert overdue, "at least one document overdue by its own review interval"


def test_assist_writes_a_labeled_nonauthoritative_process_map():
    diag, _vault = run(build_knowledge())
    body = read(diag["map"])
    assert "[PROCESS MAP, non-authoritative projection]" in body
    assert "07_agent_workspaces" in diag["map"].replace(os.sep, "/")
    assert "/08_proposals/" not in diag["map"].replace(os.sep, "/")
    assert diag["map"] not in diag["proposals"]
    assert "Documented steps (cited)" in body
    assert "asset " in body  # steps are cited


# ------------------------------------------------- THE EXECUTION PLANT

def test_execution_record_plant_is_declined_naming_oe():
    diag, _vault = run(build_knowledge(with_plant=True))
    declined = [s for s in diag["skipped"]
                if "EXECUTION RECORD" in s["reason"]
                and "Operational Evidence Realm" in s["reason"]]
    assert declined, "THE EXECUTION PLANT must be declined naming [OE]"
    assert not any(f.get("asset_id") == PLANT_ID for f in diag["findings"]), \
        "the execution record must never become a finding"
    assert not any(PLANT_ID in f["cited_assets"] for f in diag["findings"]), \
        "no finding may cite the execution record"


# ------------------------------------------------- projection-only / no writes

def test_run_writes_only_inside_the_vault_lanes():
    diag, vault = run(build_knowledge())
    written = diag["proposals"] + [diag["map"]]
    for path in written:
        rel = os.path.relpath(path, vault).replace(os.sep, "/")
        assert rel.startswith(("08_proposals/", "07_agent_workspaces/")), \
            f"a write escaped the vault lanes: {rel}"


def test_no_completed_run_vocabulary_on_any_written_byte():
    diag, _vault = run(build_knowledge())
    forbidden = runner.parse_forbidden_vocabulary(MANIFEST)
    bodies = [read(p).lower() for p in diag["proposals"] + [diag["map"]]]
    for phrase in forbidden:
        for body in bodies:
            assert phrase not in body, \
                f"COMPLETED-RUN vocabulary {phrase!r} on a written byte"


def test_findings_are_deterministic_across_reruns():
    k = build_knowledge()
    a, _va = run(k)
    b, _vb = run(k)
    assert {f["finding_kind"] for f in a["findings"]} == \
        {f["finding_kind"] for f in b["findings"]}
    assert len(a["findings"]) == len(b["findings"])


# ------------------------------------------------- refusal-first (per skill)

def test_refusal_contradiction_no_second_document():
    """detect_process_contradictions refuses (no finding) when only one
    document instructs the subject - never an assumed second side."""
    k = build_knowledge(exclude_docs={"access_request"})  # drop 5-day side
    diag, _vault = run(k)
    assert not of_kind(diag, "PROCESS_CONTRADICTION"), \
        "no contradiction may be fabricated from a single side"


def test_refusal_sop_policy_no_policy_side():
    """compare_sop_vs_policy refuses when the policy side is absent -
    never an assumed policy."""
    k = build_knowledge(exclude_docs={"change_policy"})  # drop the policy
    diag, _vault = run(k)
    assert not of_kind(diag, "SOP_POLICY_MISMATCH"), \
        "no mismatch may be fabricated without the policy side"


def test_refusal_missing_handoff_when_corpus_answers():
    """detect_missing_handoffs refuses (no finding) when the handoff
    question is answerable - a documented handoff is not a gap."""
    # make every handoff question answerable
    diag, _vault = run(build_knowledge(),
                       answerable=("next owner", "receiving procedure"))
    assert not of_kind(diag, "MISSING_HANDOFF"), \
        "a documented handoff must produce no finding"
    # and the skip is declared, never silent
    assert any(s["skill"] == "detect_missing_handoffs"
               and "documented" in s["reason"] for s in diag["skipped"])


def test_refusal_outdated_within_interval_and_no_supersession():
    """detect_outdated_process_documents refuses when nothing is
    superseded and every review interval is current."""
    # a corpus with only current, non-superseded documents
    k = [{
        "asset_id": 1, "name": "current-sop.md", "source_class": "PRIMARY",
        "provenance": {"source_document": "current-sop.md"},
        "content": ("Meridian Operations Ltd SOP. Step 1. The team performs "
                    "the work and routes to the reviewer. This SOP must be "
                    "reviewed at least once every 12 months. The last review "
                    "was recorded on 2026-06-01."),
    }]
    diag, _vault = run(k)
    assert not of_kind(diag, "OUTDATED_PROCESS_DOCUMENT"), \
        "a current, non-superseded document must produce no staleness finding"


def test_refusal_assist_empty_corpus_declares_absence():
    """prepare_process_map_projection refuses to invent steps: an empty
    corpus yields a declared-absence map, never fabricated steps."""
    diag, _vault = run([])
    body = read(diag["map"])
    assert "[PROCESS MAP, non-authoritative projection]" in body
    assert "empty section is itself information" in body
    assert not diag["findings"], "an empty corpus yields no findings"


def test_refusal_first_all_skills_on_empty_corpus():
    """The whole run refuses on an empty corpus: zero findings, the map
    declares its absences, nothing fabricated."""
    diag, _vault = run([])
    assert diag["findings"] == []
    assert diag["proposals"] == []
    assert read(diag["map"])  # the map still exists, declaring absence


# ------------------------------------------------- denied-access (clearance)

def test_denied_access_degrades_to_explicit_refusal():
    """When clearance EXCLUDES the documents needed for a finding, the
    workbench degrades to explicit refusal (an empty, declared result) -
    never a silent omission, never a fabricated finding. Here the policy
    side of the SOP-vs-policy mismatch is above clearance."""
    # exclude the change-management policy: the SOP side remains but the
    # policy side is unreadable -> no mismatch may be asserted.
    k = build_knowledge(exclude_docs={"change_policy"})
    diag, vault = run(k, excluded={"change-management-policy.md":
                                   "above AGENT clearance"})
    assert not of_kind(diag, "SOP_POLICY_MISMATCH"), \
        "with the policy side denied, no mismatch may be fabricated"
    # the exclusion is DECLARED (surfaced on the proposal bytes), not silent.
    assert diag["exclusions"], "the clearance exclusion must be declared"
    for path in diag["proposals"]:
        body = read(path)
        if "What the agent could not see" in body:
            assert "above AGENT clearance" in body
            break


def test_denied_access_never_fabricates_the_missing_side():
    """The denied case must produce NO finding standing on the excluded
    document - refusal, not invention. With the change policy above
    clearance, no asset from it exists in the package, and no SOP-side
    mismatch may be asserted against an imagined policy."""
    excluded_ids = asset_ids_for("change_policy", build_knowledge())
    k = build_knowledge(exclude_docs={"change_policy"})
    diag, _vault = run(k, excluded={"change-management-policy.md": "denied"})
    present = {e["asset_id"] for e in k}
    for f in diag["findings"]:
        assert not (set(f["cited_assets"]) & excluded_ids), \
            "a finding cited an asset excluded by clearance"
        assert set(f["cited_assets"]) <= present, \
            "a finding cited an asset not in the cleared package"
    assert not of_kind(diag, "SOP_POLICY_MISMATCH"), \
        "no mismatch may be asserted with the policy side denied"


# ------------------------------------------------- gated-skill refusal

def test_gated_skill_is_refused_naming_the_unminted_decision():
    try:
        run(build_knowledge(),
            requested_skills=("identify_missing_process_stage_owner",))
        assert False, "a gated skill must be refused"
    except RuntimeError as e:
        assert "gated" in str(e) and "Exception Stewardship" in str(e)


def test_gated_execution_skill_refused_naming_oe():
    try:
        run(build_knowledge(),
            requested_skills=("measure_cycle_time_from_logs",))
        assert False, "a gated [OE] skill must be refused"
    except RuntimeError as e:
        assert "Operational Evidence Realm" in str(e)


def main():
    fns = [g for name, g in sorted(globals().items())
           if name.startswith("test_") and callable(g)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print("\n=== All operations acceptance checks passed: each skill "
          "produces evidence-cited findings; refusal-first per skill; the "
          "denied-access case degrades to explicit refusal; THE EXECUTION "
          "PLANT declined naming [OE]; projection-only, no COMPLETED-RUN "
          "vocabulary on any byte. ===")


if __name__ == "__main__":
    main()
