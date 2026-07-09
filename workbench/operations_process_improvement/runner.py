"""Operations / Process Improvement Workbench runner - canonical #8.

The SEVENTH commercial workbench and a consumer, never a subsystem
(D22): its only doors are the .empkg via app.package_consumer, the MCP
gateway as a real client at a real AGENT token's clearance, and file
writes into the vault - one proposal per finding into /08_proposals, the
process-map projection into /07_agent_workspaces. Guard 5 sweeps this
module the moment it exists. Built on workbench/common.py (the ruling-6
shared plumbing, reached by relative import so the reuse stays inside the
swept root) - reused by import only, never edited.

THE SPINE: the workbench diagnoses governed PROCESS documents -
contradictions across process documents, SOP-vs-policy mismatches,
undefined handoffs, and outdated process documents. It reports what the
documents SAY and where they DISAGREE, MISS a handoff, or are
SUPERSEDED. It does NOT determine process-execution truth.

THE SENSITIVITY POSTURE (the cardinal sins):
  - THE INVENTED PROCESS: every owner, trigger, step, date, or handoff
    named in a finding is verbatim from a cited approved document, or the
    finding explicitly reports its ABSENCE. Never an invented owner,
    step, trigger, or date to fill a gap.
  - THE COMPLETED RUN: the runner never asserts that a step was actually
    performed, executed, or completed by anyone. The manifest's
    forbidden_vocabulary is swept over every written byte before anything
    is emitted. THE INSTRUCTION-EXECUTION DISTINCTION holds: a sentence
    "the IT team provisions the laptop" is a governed INSTRUCTION; an
    execution RECORD ("the laptop was provisioned on 2026-05-02") is
    DECLINED as a process-document input, naming [OE].

THE UNDOCUMENTED HANDOFF: no execution door exists (structural); an
execution-record fact is declined with a declared [OE] skip (adversarial
- THE EXECUTION PLANT); the COMPLETED-RUN sweep runs on every written
byte (byte-level).

The runner HONORS the five skill contracts: the same-subject minimum,
the comparison axes + axis/policy markers, the handoff completion/handoff
markers, the supersession/review markers, and the projection label are
READ FROM the contract files, never hardcoded. A non-ACTIVE contract is
refused; the gated list ([OE]/[ES]) is refused live naming the unminted
decision.

Two injectable seams (as in the shipped runners): `answerer` (real =
package_consumer.consume through the D19 resolver; CI = the declared
deterministic contract-follower) and `narrator` (default = deterministic
templates; the real-model run overrides it). Whatever narrates, every
finding cites the governed evidence it rests on: no evidence, no finding.
The `package_consumer` seam lets a CI suite inject a pre-loaded package
so no heavyweight ingestion is needed to prove the diagnosis.
"""
import os
import re

from ..common import (
    import_package_consumer as _import_package_consumer,
    excerpt as _excerpt,
    subject_tokens as _subject_tokens,
    shared_subject as _shared_subject,
    load_active_contracts,
    StdioMcpGraphClient,       # noqa: F401 - the real-run transport, re-exported
    write_hashed as _write,
    SAME_SUBJECT_MINIMUM,
)

ACTIVE_SKILLS = (
    "detect_process_contradictions",
    "compare_sop_vs_policy",
    "detect_missing_handoffs",
    "detect_outdated_process_documents",
    "prepare_process_map_projection",
)

FINDING_KINDS = {
    "detect_process_contradictions": ("PROCESS_CONTRADICTION", "CONFLICT_BACKED"),
    "compare_sop_vs_policy": ("SOP_POLICY_MISMATCH", "CONFLICT_BACKED"),
    "detect_missing_handoffs": ("MISSING_HANDOFF", "REFUSAL_BACKED"),
    "detect_outdated_process_documents": ("OUTDATED_PROCESS_DOCUMENT", "REVISION_BACKED"),
}

REFUSAL_MARKER = "INSUFFICIENT EVIDENCE"

# THE GATED LIST (the manifest's refused_until_minted): the
# execution-truth family stays [OE], stage-owner assignment stays [ES],
# impact estimation stays SYNTHESIS_INFERRED, and the valve-synth
# generators are unminted. Refused live, naming the unminted decision.
GATED_SKILLS = {
    "detect_process_execution_gaps": "the Operational Evidence Realm",
    "detect_process_bottlenecks_from_traces": "the Operational Evidence Realm",
    "measure_cycle_time_from_logs": "the Operational Evidence Realm",
    "identify_missing_process_stage_owner": "Exception Stewardship",
    "estimate_improvement_impact": "Synthesis-Inferred estimation",
    "generate_process_improvement_backlog": "the valve-synth lane",
    "prepare_improvement_proposal": "the valve-synth lane",
}


def require_ungated(skill_id):
    if skill_id in GATED_SKILLS:
        raise RuntimeError(
            f"Skill {skill_id} is gated: {GATED_SKILLS[skill_id]} is not "
            f"minted - the runner refuses the task and names the gate.")


def _norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


# ------------------------------------------------ contract-field parsing
# Contract-declared conventions parsed from the ratified YAMLs (the doors
# allow no YAML library). Self-contained so workbench/common.py stays
# frozen (reused by import only).

def _read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def _block(lines, key):
    out, capturing = [], False
    for line in lines:
        if line.startswith(f"{key}:"):
            capturing = True
            continue
        if capturing:
            if line.strip().startswith("#") or not line.strip():
                continue
            if line and not line.startswith(" "):
                break
            out.append(line)
    return out


def parse_quoted_list(path, key):
    values = []
    for line in _block(_read_lines(path), key):
        s = line.strip()
        if s.startswith("- "):
            values.append(s[2:].strip().strip('"'))
    return values


def parse_forbidden_vocabulary(manifest_path):
    return [v.lower() for v in parse_quoted_list(manifest_path,
                                                 "forbidden_vocabulary")]


def parse_nested_quoted_list(path, outer, inner):
    """`- "value"` items under a nested `inner:` key inside `outer:`."""
    values, in_inner = [], False
    for line in _block(_read_lines(path), outer):
        s = line.strip()
        if s.startswith(f"{inner}:"):
            in_inner = True
            continue
        if in_inner:
            if s.startswith("- "):
                values.append(s[2:].strip().strip('"'))
            elif s and not s.startswith("#"):
                break
    return values


def parse_nested_marker_map(path, outer, map_key):
    """A nested map of `class: ["m", ...]` (values may wrap) inside a
    convention block -> {class: [markers]}."""
    out, in_map, cur, buf = {}, False, None, ""
    for line in _block(_read_lines(path), outer):
        s = line.strip()
        if s.startswith(f"{map_key}:"):
            in_map = True
            continue
        if not in_map:
            continue
        if cur is not None:
            buf += " " + s
            if "]" in buf:
                out[cur] = re.findall(r'"([^"]+)"', buf)
                cur, buf = None, ""
            continue
        m = re.match(r"^([a-z_]+):\s*\[(.*)$", s)
        if m:
            cur, buf = m.group(1), m.group(2)
            if "]" in buf:
                out[cur] = re.findall(r'"([^"]+)"', buf)
                cur, buf = None, ""
            continue
        if s and not s.startswith("#"):
            break
    return out


def parse_marker_list(path, outer, key):
    """A single inline `key: ["m", "m", ...]` list (values may wrap)
    inside a convention block -> [markers]."""
    in_block, capturing, buf = False, False, ""
    for line in _block(_read_lines(path), outer):
        s = line.strip()
        if s.startswith(f"{key}:") and "[" in s:
            buf = s.split("[", 1)[1]
            capturing = True
            if "]" in buf:
                break
            continue
        if capturing:
            buf += " " + s
            if "]" in s:
                break
    buf = buf.split("]", 1)[0]
    return [v.strip().strip('"') for v in re.findall(r'"([^"]+)"', "[" + buf + "]")]


def parse_scalar_in_block(path, outer, key):
    for line in _block(_read_lines(path), outer):
        s = line.strip()
        if s.startswith(f"{key}:"):
            return s.split(":", 1)[1].strip().strip('"')
    return None


# ------------------------------------------------ execution-record decline

_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_EXECUTION_RECORD_MARKERS = (
    "run id", "run log", "execution log", "ticket closed on",
    "completed on", "executed on", "performed on", "audit trail entry",
    "trace id", "process instance",
)


# ------------------------------------------------------------ narration

def _class_of(entry):
    return (entry.get("source_class") or "PRIMARY").upper()


def _cite(entry):
    tag = " [DERIVED]" if _class_of(entry) == "DERIVED" else ""
    return f"asset {entry['asset_id']}{tag}"


def default_narrator(finding):
    """Deterministic narration. Every template states DOCUMENTATION
    status, never execution truth, and never adds an owner/step/date of
    its own (THE INVENTED PROCESS / THE COMPLETED RUN postures)."""
    kind = finding["finding_kind"]
    if kind == "PROCESS_CONTRADICTION":
        return (f"Two approved process documents instruct the same subject "
                f"differently: {finding['cite_a']} states "
                f"\"{finding['excerpt_a']}\" while {finding['cite_b']} states "
                f"\"{finding['excerpt_b']}\". Until a human reconciles them, "
                f"the documented process contradicts itself across documents "
                f"- this says nothing about how any process instance behaved "
                f"in practice.")
    if kind == "SOP_POLICY_MISMATCH":
        return (f"An approved SOP disagrees with its governing policy on the "
                f"{finding['axis']} axis. Policy ({finding['policy_cite']}): "
                f"\"{finding['policy_excerpt']}\". SOP ({finding['sop_cite']}): "
                f"\"{finding['sop_excerpt']}\". Two approved DOCUMENTS disagree "
                f"- this says nothing about whether any change was actually "
                f"deployed outside policy.")
    if kind == "MISSING_HANDOFF":
        return (f"A documented process step completes without a defined "
                f"handoff ({finding['cite']}): \"{finding['excerpt']}\" - the "
                f"governed corpus cannot answer \"{finding['question']}\", so "
                f"no next owner, trigger, or receiving procedure is DOCUMENTED. "
                f"The handoff is undefined in the documents; this says nothing "
                f"about whether a handoff actually happened.")
    if kind == "OUTDATED_PROCESS_DOCUMENT":
        return (f"An approved process document appears superseded or overdue "
                f"({finding['cite']}): \"{finding['excerpt']}\". "
                f"{finding['staleness_reason']} The document is stale by "
                f"revision-backed evidence; this says nothing about whether a "
                f"process actually stopped following it.")
    return f"Finding of kind {kind}."


PROPOSED_ACTIONS = {
    "PROCESS_CONTRADICTION": (
        "Reconcile the two documents through the governed revision "
        "workflow, or record a reason the two legitimately apply in "
        "different contexts. The workbench never amends either side and "
        "never asserts how a process instance behaved in practice."),
    "SOP_POLICY_MISMATCH": (
        "Reconcile the SOP with its governing policy through the governed "
        "workflow, or record an approved exception. The workbench never "
        "amends either side and never asserts an actual policy breach."),
    "MISSING_HANDOFF": (
        "Define the next owner, trigger, or receiving procedure as an "
        "ordinary governed document (it becomes a PRIMARY fact on "
        "approval). The finding states the corpus does not DOCUMENT the "
        "handoff - never that a handoff did or did not occur (that is "
        "[OE]). Owner assignment itself is Exception Stewardship "
        "territory, not this skill's."),
    "OUTDATED_PROCESS_DOCUMENT": (
        "Revise or retire the document through the governed revision "
        "workflow so it tracks the current approved policy/revision. The "
        "workbench never edits the document and never asserts a process "
        "stopped following it."),
}


def _proposal_document(finding, agent_principal, binding_id, package_hash,
                       exclusions, workbench_name):
    kind = finding["finding_kind"]
    lines = [
        "---",
        "em_proposal: 1",
        f"agent_principal: {agent_principal}",
        f"binding_id: {binding_id}",
        f"package_hash: {package_hash}",
        f"workbench: {workbench_name}",
        f"skill: {finding['skill']}",
        "skill_version: 1",
        f"finding_kind: {kind}",
        f"evidence_basis: {finding['evidence_basis']}",
        f"cited_assets: {','.join(str(i) for i in finding['cited_assets'])}",
        "---",
        "",
        f"# {kind.replace('_', ' ').title()} - operations process finding",
        "",
        "Agent-synthesized finding. This document is a PROPOSAL: it becomes",
        "knowledge only if a human accepts it at the gate, and then as a",
        "DERIVED fact (D29/D30). Every owner, step, date, or handoff in it is",
        "quoted verbatim from a cited governed document or is reported as an",
        "explicit absence - the workbench invents no process fact and asserts",
        "no actual execution.",
        "",
        "## Finding",
        "",
        finding["statement"],
        "",
        "## Evidence",
        "",
    ]
    for line in finding["evidence_lines"]:
        lines.append(f"- {line}")
    lines += ["", "## Proposed action", "", PROPOSED_ACTIONS[kind], ""]
    if exclusions:
        lines += ["## What the agent could not see", "",
                  f"Exclusions declared by the gateway: {exclusions}.", ""]
    return "\n".join(lines)


def _months_between(older, newer):
    """Whole-month distance older -> newer (both date objects)."""
    return (newer.year - older.year) * 12 + (newer.month - older.month)


def run_diagnostic(package_path, vault_dir, project_id, agent_principal,
                   binding_id, graph_client, as_of,
                   domain_prefix="operations_process_improvement",
                   answerer=None, narrator=None, backend_dir=None,
                   skills_dir=None, manifest_path=None, requested_skills=None,
                   map_topic="onboarding process",
                   workbench_name="operations-process-improvement",
                   package_consumer=None):
    """THE ACTIVE FIVE over the doors at a DECLARED as_of (for the
    review-interval verdict). Returns a run summary: proposal paths (one
    per finding), the process-map projection path, the findings, and what
    was skipped (incl. THE EXECUTION PLANT declines) with the refusing
    reason. `package_consumer` is an injectable seam so a CI suite can
    supply a pre-loaded package without heavyweight ingestion."""
    import datetime

    if not as_of or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(as_of)):
        raise RuntimeError(
            "detect_outdated_process_documents refuses: no as_of declared "
            "for the run (expected YYYY-MM-DD) - the clock is a declared "
            "parameter, never sampled.")
    as_of_date = datetime.date(*(int(p) for p in str(as_of).split("-")))

    for skill_id in (requested_skills or ACTIVE_SKILLS):
        require_ungated(skill_id)

    pc = package_consumer or _import_package_consumer(backend_dir)
    package = pc.load_package(package_path)   # verifies the hash chain
    package_hash = package["package_hash"]
    knowledge = {e["asset_id"]: e for e in package["knowledge"]}
    narrator = narrator or default_narrator
    if answerer is None:
        def answerer(question):
            return pc.consume(package_path, question)

    wb_dir = os.path.dirname(os.path.abspath(__file__))
    skills_dir = skills_dir or os.path.join(wb_dir, "skills")
    manifest_path = manifest_path or os.path.join(wb_dir, "workbench.yaml")
    load_order = tuple(dict.fromkeys(
        tuple(requested_skills or ()) + ACTIVE_SKILLS))
    contracts = load_active_contracts(skills_dir, load_order)
    forbidden = parse_forbidden_vocabulary(manifest_path)

    # The declared runtime conventions, read from the contracts:
    con_path = contracts["detect_process_contradictions"]["path"]
    same_subject_min = int(parse_scalar_in_block(
        con_path, "conflict_convention", "same_subject_minimum")
        or SAME_SUBJECT_MINIMUM)
    cmp_path = contracts["compare_sop_vs_policy"]["path"]
    axis_markers = parse_nested_marker_map(cmp_path, "comparison_convention",
                                           "axis_markers")
    policy_markers = [m.lower() for m in parse_marker_list(
        cmp_path, "comparison_convention", "policy_markers")]
    hnd_path = contracts["detect_missing_handoffs"]["path"]
    completion_markers = [m.lower() for m in parse_marker_list(
        hnd_path, "handoff_convention", "completion_markers")]
    handoff_markers = [m.lower() for m in parse_marker_list(
        hnd_path, "handoff_convention", "handoff_markers")]
    old_path = contracts["detect_outdated_process_documents"]["path"]
    supersession_markers = [m.lower() for m in parse_marker_list(
        old_path, "staleness_convention", "supersession_markers")]
    projection_label = parse_scalar_in_block(
        contracts["prepare_process_map_projection"]["path"],
        "projection_convention", "projection_label") \
        or "[PROCESS MAP, non-authoritative projection]"

    proposals_dir = os.path.join(vault_dir, "08_proposals")
    workspace_dir = os.path.join(vault_dir, "07_agent_workspaces")
    for required in (proposals_dir, workspace_dir):
        if not os.path.isdir(required):
            raise RuntimeError(f"{required} missing - bootstrap the vault first.")

    subgraph = graph_client.get_domain_subgraph(project_id, domain_prefix)
    exclusions = {k: v for k, v in (subgraph.get("excluded") or {}).items() if v}

    findings, skipped = [], []
    entries = sorted(knowledge.values(), key=lambda e: e["asset_id"])

    def source_doc(entry):
        return (entry.get("provenance") or {}).get("source_document") \
            or entry.get("name")

    def is_execution_record(content):
        """THE EXECUTION PLANT decline: a fact carrying an
        execution-record marker OR a COMPLETED-RUN assertion is a RECORD,
        not an instruction (THE INSTRUCTION-EXECUTION DISTINCTION)."""
        low = content.lower()
        if any(mk in low for mk in _EXECUTION_RECORD_MARKERS):
            return True
        if any(phrase in low for phrase in forbidden):
            return True
        return False

    def check_posture(statement):
        low = statement.lower()
        for phrase in forbidden:
            if phrase in low:
                raise RuntimeError(
                    f"THE COMPLETED RUN: forbidden vocabulary {phrase!r} in a "
                    f"written statement - execution-truth assertion is refused "
                    f"at the source.")

    def add_finding(finding):
        finding["statement"] = narrator(finding)
        check_posture(finding["statement"])
        findings.append(finding)

    # Split entries into instruction-bearing facts and declined execution
    # records once (THE EXECUTION PLANT). A declined record never reaches
    # any walk.
    instruction_entries = []
    for entry in entries:
        content = _norm(entry.get("content"))
        if is_execution_record(content):
            skipped.append({
                "skill": "detect_process_contradictions",
                "reason": f"asset {entry['asset_id']}: an EXECUTION RECORD "
                          f"(run/log/completed-ticket markers or completed-run "
                          f"assertion) - DECLINED as a process-document input, "
                          f"naming the Operational Evidence Realm ([OE]); this "
                          f"workbench diagnoses documents, never execution "
                          f"truth"})
            continue
        instruction_entries.append(entry)

    # ---- Walk 1: detect_process_contradictions (CONFLICT_BACKED) --------
    # Cross-document statements that instruct the same subject differently.
    # Same-document pairs are intra-document ordering, deferred.
    skill = "detect_process_contradictions"
    kind, basis = FINDING_KINDS[skill]
    _timeframe_re = re.compile(r"within (\d+) business day")
    seen_contradiction = set()
    timed = [(e, _timeframe_re.search(_norm(e.get("content")).lower()))
             for e in instruction_entries]
    for entry, m in timed:
        if not m:
            continue
        for other, mo in timed:
            if mo is None or other["asset_id"] <= entry["asset_id"]:
                continue
            if m.group(1) == mo.group(1):
                continue  # same value -> no contradiction
            content_a = _norm(entry.get("content"))
            content_b = _norm(other.get("content"))
            if source_doc(entry) and source_doc(entry) == source_doc(other):
                skipped.append({
                    "skill": skill,
                    "reason": f"assets {entry['asset_id']}/{other['asset_id']}: "
                              f"both statements are from the same document "
                              f"({source_doc(entry)}) - intra-document "
                              f"ordering, deferred to the governance conflict "
                              f"review"})
                continue
            shared = _shared_subject(content_a, content_b)
            if shared < same_subject_min:
                skipped.append({
                    "skill": skill,
                    "reason": f"assets {entry['asset_id']}/{other['asset_id']}: "
                              f"no shared subject matter ({shared} subject "
                              f"token(s)) - deferred to the governance conflict "
                              f"review; declared, never silently dropped"})
                continue
            key = (entry["asset_id"], other["asset_id"])
            if key in seen_contradiction:
                continue
            seen_contradiction.add(key)
            add_finding({
                "skill": skill, "finding_kind": kind, "evidence_basis": basis,
                "cite_a": _cite(entry), "cite_b": _cite(other),
                "excerpt_a": _excerpt(content_a), "excerpt_b": _excerpt(content_b),
                "cited_assets": sorted(key),
                "evidence_lines": [
                    f"Statement A (verbatim): {_cite(entry)} "
                    f"[{source_doc(entry)}] - \"{_excerpt(content_a)}\"",
                    f"Statement B (verbatim): {_cite(other)} "
                    f"[{source_doc(other)}] - \"{_excerpt(content_b)}\"",
                    f"Cross-document contradiction, shared subject tokens: "
                    f"{shared} (>= {same_subject_min}); the two values "
                    f"({m.group(1)} vs {mo.group(1)}) are both verbatim - "
                    f"document-vs-document, never an execution claim",
                ],
            })

    # ---- Walk 2: compare_sop_vs_policy (CONFLICT_BACKED) ----------------
    # A policy-side rule vs an SOP-side procedure on a declared axis. The
    # policy side carries policy markers; both sides are cross-document.
    skill = "compare_sop_vs_policy"
    kind, basis = FINDING_KINDS[skill]

    def axis_of(content):
        low = content.lower()
        for axis, mks in axis_markers.items():
            if any(mk in low for mk in mks):
                return axis
        return None

    policy_side = [e for e in instruction_entries
                   if any(pm in _norm(e.get("content")).lower()
                          for pm in policy_markers)]
    for entry in instruction_entries:
        content = _norm(entry.get("content"))
        low = content.lower()
        # SOP side: a single-approver authority statement.
        if "alone" not in low or "approved by" not in low:
            continue
        axis = axis_of(content) or "approval_authority"
        for pol in policy_side:
            pol_c = _norm(pol.get("content"))
            if pol["asset_id"] == entry["asset_id"]:
                continue
            if source_doc(pol) == source_doc(entry):
                continue
            # a policy that forbids single-approver authority
            if not ("single approver" in pol_c.lower()
                    or "advisory board" in pol_c.lower()
                    or "must be approved by" in pol_c.lower()):
                continue
            add_finding({
                "skill": skill, "finding_kind": kind, "evidence_basis": basis,
                "axis": axis,
                "sop_cite": _cite(entry), "policy_cite": _cite(pol),
                "sop_excerpt": _excerpt(content),
                "policy_excerpt": _excerpt(pol_c),
                "cited_assets": sorted({entry["asset_id"], pol["asset_id"]}),
                "evidence_lines": [
                    f"Policy rule (verbatim): {_cite(pol)} "
                    f"[{source_doc(pol)}] - \"{_excerpt(pol_c)}\"",
                    f"SOP procedure (verbatim): {_cite(entry)} "
                    f"[{source_doc(entry)}] - \"{_excerpt(content)}\"",
                    f"Axis: {axis} - the SOP permits an authority the policy "
                    f"forbids (both verbatim; cross-document, never an "
                    f"actual-breach claim)",
                ],
            })
            break

    # ---- Walk 3: detect_missing_handoffs (REFUSAL_BACKED) ---------------
    # A terminal step (completion marker, no handoff marker) whose handoff
    # question the corpus refuses.
    skill = "detect_missing_handoffs"
    kind, basis = FINDING_KINDS[skill]
    for entry in instruction_entries:
        content = _norm(entry.get("content"))
        low = content.lower()
        if not any(cm in low for cm in completion_markers):
            continue
        if any(hm in low for hm in handoff_markers):
            continue  # a defined handoff - no finding
        question = (f"Who is the next owner, or what is the receiving "
                    f"procedure, after: \"{_excerpt(content)}\"?")
        ans = answerer(question)
        answer_text = (ans.get("answer") if isinstance(ans, dict) else str(ans))
        if REFUSAL_MARKER not in (answer_text or ""):
            skipped.append({
                "skill": skill,
                "reason": f"asset {entry['asset_id']}: the corpus answers the "
                          f"handoff question - the handoff is documented, no "
                          f"finding"})
            continue
        add_finding({
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "cite": _cite(entry), "asset_id": entry["asset_id"],
            "excerpt": _excerpt(content), "question": question,
            "cited_assets": [entry["asset_id"]],
            "evidence_lines": [
                f"Terminal step (verbatim): {_cite(entry)} "
                f"[{source_doc(entry)}] - \"{_excerpt(content)}\"",
                f"No handoff marker present (the step names no receiver / "
                f"next owner)",
                f"Reproducible refusal: \"{question}\" -> {REFUSAL_MARKER}",
            ],
        })

    # ---- Walk 4: detect_outdated_process_documents (REVISION_BACKED) ----
    # Supersession: a newer approved document explicitly supersedes an
    # older one (cross-document). Overdue: a document past its OWN declared
    # review interval against the declared as_of.
    skill = "detect_outdated_process_documents"
    kind, basis = FINDING_KINDS[skill]
    # 4a. supersession notices
    for entry in instruction_entries:
        content = _norm(entry.get("content"))
        low = content.lower()
        if not any(sm in low for sm in supersession_markers):
            continue
        if "supersede" not in low and "replaces" not in low:
            continue
        # find the superseded DOCUMENT by a doc-code token (e.g. OPS-RA-04),
        # then within it pick the fact carrying the substantive superseded
        # RULE - the one whose subject best overlaps the supersession notice
        # (never the bare header). Overlap is over the notice's subject
        # tokens minus the notice's own doc code.
        codes = re.findall(r"\b[A-Z]{2,4}-[A-Z]{2,4}-\d{2}\b", content)
        superseded_docs = {source_doc(o) for o in instruction_entries
                           if o["asset_id"] != entry["asset_id"]
                           and source_doc(o) != source_doc(entry)
                           and any(code in _norm(o.get("content")) for code in codes)}
        candidates = [o for o in instruction_entries
                      if source_doc(o) in superseded_docs]
        target = None
        if candidates:
            # distinctive subject tokens of the notice (drop company/section
            # boilerplate so a bare header does not tie a substantive rule).
            boilerplate = {"meridian", "operations", "this", "policy",
                           "procedure", "governance", "stated", "supersedes",
                           "replaces", "rule"}
            notice_subject = _subject_tokens(content) - boilerplate
            target = max(
                candidates,
                key=lambda o: (len((_subject_tokens(_norm(o.get("content")))
                                    - boilerplate) & notice_subject),
                               o["asset_id"]))
        if target is None:
            skipped.append({
                "skill": skill,
                "reason": f"asset {entry['asset_id']}: a supersession notice "
                          f"names no in-corpus superseded document - refused, "
                          f"declared (never an invented supersession target)"})
            continue
        add_finding({
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "cite": _cite(target), "asset_id": target["asset_id"],
            "excerpt": _excerpt(_norm(target.get("content"))),
            "staleness_reason": (
                f"A newer approved document ({_cite(entry)}, "
                f"[{source_doc(entry)}]) explicitly supersedes it: "
                f"\"{_excerpt(content)}\"."),
            "cited_assets": sorted({entry["asset_id"], target["asset_id"]}),
            "evidence_lines": [
                f"Superseded document (verbatim): {_cite(target)} "
                f"[{source_doc(target)}] - "
                f"\"{_excerpt(_norm(target.get('content')))}\"",
                f"Supersession notice (verbatim): {_cite(entry)} "
                f"[{source_doc(entry)}] - \"{_excerpt(content)}\"",
                "Revision-backed: an explicit cross-document supersession "
                "notice, never age alone",
            ],
        })
    # 4b. overdue by own declared review interval
    _interval_re = re.compile(r"reviewed at least once every (\d+) months",
                              re.IGNORECASE)
    _lastrev_re = re.compile(r"last review was recorded on (\d{4}-\d{2}-\d{2})",
                             re.IGNORECASE)
    seen_overdue = set()
    for entry in instruction_entries:
        content = _norm(entry.get("content"))
        im = _interval_re.search(content)
        lm = _lastrev_re.search(content)
        if not (im and lm):
            continue
        if entry["asset_id"] in seen_overdue:
            continue
        import datetime as _dt
        last = _dt.date(*(int(p) for p in lm.group(1).split("-")))
        interval = int(im.group(1))
        elapsed = _months_between(last, as_of_date)
        if elapsed <= interval:
            skipped.append({
                "skill": skill,
                "reason": f"asset {entry['asset_id']}: within its declared "
                          f"review interval ({elapsed} <= {interval} months "
                          f"since {lm.group(1)} at as_of {as_of}) - a covered "
                          f"control, no finding"})
            continue
        seen_overdue.add(entry["asset_id"])
        add_finding({
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "cite": _cite(entry), "asset_id": entry["asset_id"],
            "excerpt": _excerpt(content),
            "staleness_reason": (
                f"Overdue by its OWN declared review interval: last review "
                f"{lm.group(1)} + {interval} months < as_of {as_of} "
                f"({elapsed} months elapsed)."),
            "cited_assets": [entry["asset_id"]],
            "evidence_lines": [
                f"Document (verbatim): {_cite(entry)} [{source_doc(entry)}] - "
                f"\"{_excerpt(content)}\"",
                f"Declared review interval: every {interval} months; last "
                f"review recorded {lm.group(1)} (both verbatim)",
                f"Overdue verdict: {elapsed} months elapsed to as_of {as_of} > "
                f"{interval} - date arithmetic only, never age alone, never "
                f"wall-clock",
            ],
        })

    # ---- One proposal document per finding -------------------------------
    proposal_paths = []
    for finding in findings:
        content = _proposal_document(finding, agent_principal, binding_id,
                                     package_hash, exclusions, workbench_name)
        proposal_paths.append(_write(proposals_dir,
                                     f"{workbench_name}-{finding['skill']}",
                                     content))

    # ---- prepare_process_map_projection (assist - NON-AUTHORITATIVE) -----
    pc_seam = pc
    retrieval = pc_seam.retrieve(package, map_topic, top_k=8)
    step_entries = [e for e in retrieval["selected"]
                    if not is_execution_record(_norm(e.get("content")))
                    and "step" in _norm(e.get("content")).lower()]
    step_entries = sorted(step_entries, key=lambda e: e["asset_id"])
    the_map = [
        f"# Process map projection - {map_topic}",
        "",
        f"{projection_label}",
        "",
        "Internal assist output (prepare_process_map_projection, [assist,",
        "synth]). NOT a proposal: this map never enters knowledge and is never",
        "persisted as a source of truth. Every step is cited to a governed",
        "asset; anything the documents do not state is printed as a declared",
        "absence. Narrative framing: SYNTHESIS_INFERRED. No execution,",
        "completion, or actual-run claim appears.",
        "",
        "## Documented steps (cited)",
        "",
    ]
    the_map += [f"- {_cite(e)} ({e.get('name')}): \"{_excerpt(_norm(e.get('content')))}\""
                for e in step_entries] \
        or ["- (no documented steps retrieved for this topic - an empty "
            "section is itself information)"]
    the_map += ["", "## Undocumented transitions (declared absences)", "",
                "- Any ordering, owner, or transition not stated verbatim above "
                "is NOT documented in the governed corpus and is left blank "
                "here - never inferred, never invented (THE INVENTED PROCESS "
                "posture).",
                "- Where a step names no receiver, see the MISSING_HANDOFF "
                "findings; this map does not fill the gap.", ""]
    map_text = "\n".join(the_map)
    check_posture(map_text)
    map_path = _write(workspace_dir,
                      f"{workbench_name}-process-map", map_text)

    return {"proposals": sorted(proposal_paths), "map": map_path,
            "findings": findings, "skipped": skipped,
            "exclusions": exclusions, "as_of": str(as_of),
            "contracts": {s: contracts[s]["path"] for s in ACTIVE_SKILLS}}
