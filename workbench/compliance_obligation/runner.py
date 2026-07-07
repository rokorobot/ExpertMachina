"""Compliance & Obligation Workbench runner - the v1.7 reference consumer.

Canonical workbench #9 in the catalog (workbench.yaml is the manifest; the
six ratified skill contracts in skills/ are the binding v1.7 execution
contracts). The runner is a consumer, never a subsystem (D22): its only
doors are the .empkg via app.package_consumer, the MCP gateway as a real
client at a real AGENT token's clearance, and file writes into the vault -
one proposal per finding into /08_proposals, the audit-readiness pack into
/07_agent_workspaces. Guard 5 sweeps this module the moment it exists.
Built on workbench/common.py (the v1.7 ruling-6 shared plumbing, reached by
relative import so the reuse stays inside the swept root).

THE SENSITIVITY POSTURE (the cardinal sin): compliance overclaiming. The
runner may say what approved documents state, omit, contradict, supersede,
or cannot answer. It may never imply that practice was verified. The
manifest's forbidden_vocabulary is enforced HERE, on every finding
statement, before anything is written - and swept again over the written
bytes at the WS2 gate.

The runner HONORS the skill contracts, not just carries them:
  - question frames, requirement classes, explicit markers, the
    review-interval marker pattern, and the classification rules are READ
    FROM the contract files (skills/*.yaml), never hardcoded;
  - a skill whose contract is not status: ACTIVE is refused - tags are
    gates, not preferences; the GATED list ([OE]/[PMD]/[ES]) is refused
    live, naming the unminted decision (the v1.7 WS0 ruling 3);
  - refusal-first cuts both ways: a covered control (the corpus answers
    the evidence/owner question; a review current at as_of) produces NO
    finding, declared in `skipped`, never silently dropped;
  - the clock is DECLARED: as_of is a run parameter recorded verbatim in
    every review-interval finding - wall-clock is never sampled.

Two injectable seams, as at v1.6: `answerer` (real = package_consumer
.consume through the D19 resolver; CI = the declared deterministic
contract-follower) and `narrator` (default = deterministic templates; the
real-model run overrides it - the open honest slot). Whatever narrates,
every finding cites the governed evidence it rests on: no evidence, no
finding. DERIVED evidence is cited AS DERIVED - composition across the
valve (registry rule 6) stays visible at the gate.
"""
import os
import re

from ..common import (
    import_package_consumer as _import_package_consumer,
    excerpt as _excerpt,
    overlap as _overlap,
    shared_subject as _shared_subject,
    load_active_contracts,
    load_skill_contract,
    StdioMcpGraphClient,       # noqa: F401 - the real-run transport, re-exported
    write_hashed as _write,
    SAME_SUBJECT_MINIMUM,
)

ACTIVE_SKILLS = (
    "extract_compliance_obligations",
    "detect_missing_evidence",
    "identify_outdated_policies",
    "detect_undocumented_obligation_owner",
    "detect_conflicting_compliance_statements",
    "prepare_audit_readiness_pack",
)

FINDING_KINDS = {
    "extract_compliance_obligations": ("COMPLIANCE_OBLIGATION", "EXCERPT_BACKED"),
    "detect_missing_evidence": ("MISSING_COMPLIANCE_EVIDENCE", "REFUSAL_BACKED"),
    "identify_outdated_policies": ("OUTDATED_POLICY", "REVISION_BACKED"),
    "detect_undocumented_obligation_owner": ("UNDOCUMENTED_OBLIGATION_OWNER", "REFUSAL_BACKED"),
    "detect_conflicting_compliance_statements": ("CONFLICTING_COMPLIANCE_STATEMENTS", "CONFLICT_BACKED"),
}

REFUSAL_MARKER = "INSUFFICIENT EVIDENCE"

# THE GATED LIST (the v1.7 WS0 ruling 3, mirrored verbatim from the build
# contract + the manifest's refused_until_minted): tags are gates - the
# runner refuses each at runtime, naming the unminted decision. Minting any
# of the three named decisions is an explicit register event, never a
# configuration change.
GATED_SKILLS = {
    "compare_policy_vs_practice": "the Operational Evidence Realm",
    "verify_obligations_against_operational_records": "the Operational Evidence Realm",
    "detect_missed_operational_reporting_events": "the Operational Evidence Realm",
    "detect_practice_evidence_from_logs_tickets_payments": "the Operational Evidence Realm",
    "detect_unapproved_compliance_guidance": "the Pipeline Metadata Door",
    "generate_obligation_approval_queue": "the Pipeline Metadata Door",
    "identify_obligation_owner_gaps": "Exception Stewardship",
}


def require_ungated(skill_id):
    """Refuse a gated skill LIVE, naming the unminted decision (ruling 3).
    Detection-of-absence skills that ARE ratified live in ACTIVE_SKILLS;
    everything on the gated list stays refused until its decision is minted
    at a register supersession - never by configuration."""
    if skill_id in GATED_SKILLS:
        raise RuntimeError(
            f"Skill {skill_id} is gated: {GATED_SKILLS[skill_id]} decision is "
            f"not minted - the runner refuses the task and names the gate.")


def _norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


# ------------------------------------------------ contract-field parsing
# The compliance contracts carry structured fields beyond common.py's base
# loader (which reads skill_id/status/boundary_tags/question_frame). These
# helpers read the extra declared fields - stdlib line-based, the doors
# allow no YAML library. The contracts DRIVE runtime: nothing below is a
# preference the runner may ignore.

def _read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def _block(lines, key):
    """The raw indented block under `key:` (list bodies, nested maps)."""
    out, capturing = [], False
    for line in lines:
        if line.startswith(f"{key}:"):
            capturing = True
            continue
        if capturing:
            if line.strip().startswith("#"):
                continue
            if line and not line.startswith(" "):
                break
            out.append(line)
    return out


def parse_quoted_list(path, key):
    """`key:` followed by `- "value"` entries -> the values, in order."""
    values = []
    for line in _block(_read_lines(path), key):
        stripped = line.strip()
        if stripped.startswith("- "):
            values.append(stripped[2:].strip().strip('"'))
    return values


def parse_rule_lines(path, key):
    """Declared deterministic first-match rules of the shape
    `- contains "a" or "b" -> target` / `- "a", "b", or "c" -> target` /
    `- otherwise -> default`. Returns ([(needles, target), ...], default)."""
    rules, default = [], None
    for line in _block(_read_lines(path), key):
        stripped = line.strip()
        if not stripped.startswith("- ") or "->" not in stripped:
            continue
        lhs, target = stripped[2:].rsplit("->", 1)
        target = target.strip()
        needles = re.findall(r'"([^"]+)"', lhs)
        if needles:
            rules.append((tuple(needles), target))
        elif "otherwise" in lhs:
            default = target
    if default is None:
        raise RuntimeError(f"{path}: {key} declares no otherwise-default")
    return rules, default


def apply_rules(rules, default, text):
    """Deterministic first-match (the declared rule order IS the contract)."""
    lowered = (text or "").lower()
    for needles, target in rules:
        if any(n in lowered for n in needles):
            return target
    return default


def parse_keyed_frames(path, key, first_field):
    """Structured frame lists: `- first_field: "..."` followed by
    `question: "..."` (values may wrap; wrapped lines are joined)."""
    frames, current, field = [], None, None
    for line in _block(_read_lines(path), key):
        stripped = line.strip()
        if stripped.startswith(f"- {first_field}:"):
            if current is not None:
                frames.append(current)
            current = {first_field: stripped.split(":", 1)[1].strip().strip('"')}
            field = first_field
        elif current is not None and ":" in stripped and not stripped.startswith('"'):
            name, value = stripped.split(":", 1)
            if name.strip().isidentifier():
                field = name.strip()
                current[field] = value.strip().strip('"')
            else:
                current[field] = _norm(current[field] + " " + stripped.strip('"'))
        elif current is not None and field is not None and stripped:
            current[field] = _norm(current[field].rstrip('"') + " " + stripped.strip('"'))
    if current is not None:
        frames.append(current)
    for frame in frames:
        for k in frame:
            frame[k] = _norm(frame[k])
    return frames


def parse_review_marker(path):
    """The declared review_interval_convention marker_pattern - a quoted,
    possibly wrapped regex whose YAML escaping (\\\\d) unwraps to \\d."""
    lines = _block(_read_lines(path), "review_interval_convention")
    raw, capturing = [], False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("marker_pattern:"):
            raw.append(stripped.split(":", 1)[1].strip())
            capturing = not raw[-1].endswith('"')
        elif capturing:
            raw.append(stripped)
            if stripped.endswith('"'):
                capturing = False
    pattern = " ".join(raw).strip().strip('"').replace("\\\\", "\\")
    if not pattern:
        raise RuntimeError(f"{path}: review_interval_convention declares no "
                           f"marker_pattern")
    return re.compile(pattern)


def parse_forbidden_vocabulary(manifest_path):
    return [v.lower() for v in parse_quoted_list(manifest_path,
                                                 "forbidden_vocabulary")]


def add_months(y, m, d, n):
    total = (m - 1) + n
    return (y + total // 12, total % 12 + 1, d)


def _class_of(entry):
    return (entry.get("source_class") or "PRIMARY").upper()


def _cite(entry):
    """An asset citation line fragment; DERIVED evidence is cited AS
    DERIVED (D30 - derivation depth stays visible at the gate)."""
    cls = _class_of(entry)
    tag = " [DERIVED]" if cls == "DERIVED" else ""
    return f"asset {entry['asset_id']}{tag}"


# ------------------------------------------------------------ narration

def default_narrator(finding):
    """Deterministic narration templates. The real-model run replaces this
    seam (the open honest slot); the evidence is identical either way -
    narration presents, it never decides. Every template states
    DOCUMENTATION status, never practice (the sensitivity posture)."""
    kind = finding["finding_kind"]
    if kind == "COMPLIANCE_OBLIGATION":
        return (f"An approved document states an explicit obligation "
                f"({finding['cite']}, source_type {finding['source_type']}, "
                f"obligation_type {finding['obligation_type']}): "
                f"\"{finding['excerpt']}\". This is what the document obliges "
                f"- extraction states documentation, never practice.")
    if kind == "MISSING_COMPLIANCE_EVIDENCE":
        return (f"A documented requirement ({finding['requirement_cites']}: "
                f"\"{finding['requirement_excerpt']}\") calls for evidence the "
                f"governed corpus cannot produce - the evidence question "
                f"\"{finding['question']}\" is reproducibly refused. The "
                f"documents do not evidence the requirement; this finding says "
                f"nothing about whether the requirement is fulfilled in "
                f"practice.")
    if kind == "OUTDATED_POLICY":
        if finding.get("route") == "REVIEW_INTERVAL":
            return (f"A governed policy ({finding['cite']}) declares its own "
                    f"review discipline (\"{finding['excerpt']}\") and is "
                    f"overdue by it: the review was due {finding['due']} and "
                    f"the declared as_of is {finding['as_of']}. Documentation "
                    f"status only - the policy text may still be entirely "
                    f"sound.")
        return (f"Governed asset {finding['outdated_asset']} still tracks a "
                f"superseded revision of asset {finding['revised_asset']}, "
                f"whose current approved revision states "
                f"\"{finding['excerpt_current']}\". The outdated text stands "
                f"until revised or retired.")
    if kind == "UNDOCUMENTED_OBLIGATION_OWNER":
        return (f"An explicit documented obligation ({finding['cite']}: "
                f"\"{finding['excerpt']}\") has no approved document naming a "
                f"responsible owner - the owner question "
                f"\"{finding['question']}\" is reproducibly refused. The "
                f"governed corpus does not document an owner; this is not a "
                f"statement about who owns the obligation in practice.")
    if kind == "CONFLICTING_COMPLIANCE_STATEMENTS":
        return (f"Two approved documents oblige incompatible handling of the "
                f"same subject: {finding['cite_a']} states "
                f"\"{finding['excerpt_a']}\" while {finding['cite_b']} states "
                f"\"{finding['excerpt_b']}\". Until a human reconciles them, "
                f"the governed corpus carries both statements.")
    return f"Finding of kind {kind}."


PROPOSED_ACTIONS = {
    "COMPLIANCE_OBLIGATION": (
        "Review the extracted obligation at the human gate: accept it as a "
        "DERIVED obligation fact or reject it with a recorded reason. An "
        "accepted obligation becomes a governed requirement source for "
        "evidence tracking (composition across the valve)."),
    "MISSING_COMPLIANCE_EVIDENCE": (
        "Produce or ingest the covering evidence document through the "
        "governed pipeline. The finding states that the governed corpus does "
        "not hold the evidence - never that the evidence does not exist in "
        "the world."),
    "OUTDATED_POLICY": (
        "Schedule the declared review or supersede the policy through the "
        "governed revision workflow - stated as documentation status, never "
        "as a conduct judgment."),
    "UNDOCUMENTED_OBLIGATION_OWNER": (
        "Document the owner in an approved source. Naming a candidate owner "
        "is human work (Exception Stewardship territory), never this "
        "skill's."),
    "CONFLICTING_COMPLIANCE_STATEMENTS": (
        "A human reconciles the two statements through the governed revision "
        "workflow, or dismisses the conflict with a recorded reason - the "
        "workbench never picks the surviving statement."),
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
        f"# {kind.replace('_', ' ').title()} - compliance & obligation finding",
        "",
        "Agent-synthesized finding. This document is a PROPOSAL: it becomes",
        "knowledge only if a human accepts it at the gate, and then as a",
        "DERIVED fact (D29/D30). It states what approved documents say,",
        "omit, or contradict - never what the company does in practice.",
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


def run_diagnostic(package_path, vault_dir, project_id, agent_principal,
                   binding_id, graph_client, as_of,
                   domain_prefix="compliance", answerer=None, narrator=None,
                   backend_dir=None, skills_dir=None, manifest_path=None,
                   requested_skills=None, pack_topic="incident response",
                   workbench_name="compliance-obligation"):
    """The six ratified skills over the doors, at a DECLARED as_of. Returns
    a run summary: proposal paths (one per finding), the audit-readiness
    pack path, the findings, and what was skipped with the refusing
    reason."""
    # The declared clock: as_of is a run parameter, never wall-clock.
    if not as_of or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(as_of)):
        raise RuntimeError(
            "identify_outdated_policies refuses: no as_of declared for the "
            "run (expected YYYY-MM-DD) - the clock is a declared parameter, "
            "never sampled.")
    as_of_tuple = tuple(int(p) for p in str(as_of).split("-"))

    for skill_id in (requested_skills or ACTIVE_SKILLS):
        require_ungated(skill_id)   # ruling 3: gated skills refused live

    pc = _import_package_consumer(backend_dir)
    package = pc.load_package(package_path)   # verifies the hash chain
    package_hash = package["package_hash"]
    expert_model_id = package["manifest"]["expert_model_id"]
    knowledge = {e["asset_id"]: e for e in package["knowledge"]}
    narrator = narrator or default_narrator
    if answerer is None:
        def answerer(question):   # the real D19 path
            return pc.consume(package_path, question)

    wb_dir = os.path.dirname(os.path.abspath(__file__))
    skills_dir = skills_dir or os.path.join(wb_dir, "skills")
    manifest_path = manifest_path or os.path.join(wb_dir, "workbench.yaml")
    # Load the bundle's six PLUS anything extra the caller requested: an
    # extra skill that survived require_ungated still needs an ACTIVE
    # contract on disk - a missing or non-ACTIVE contract refuses here
    # (tags are gates, not preferences).
    load_order = tuple(dict.fromkeys(
        tuple(requested_skills or ()) + ACTIVE_SKILLS))
    contracts = load_active_contracts(skills_dir, load_order)
    forbidden = parse_forbidden_vocabulary(manifest_path)

    # The declared runtime frames, read from the contracts:
    markers = parse_quoted_list(
        contracts["extract_compliance_obligations"]["path"], "explicit_markers")
    if not markers:
        raise RuntimeError("extract_compliance_obligations declares no "
                           "explicit markers - nothing may be extracted")
    marker_re = re.compile(
        r"\b(?:" + "|".join(re.escape(m) for m in markers) + r")\b")
    src_rules = parse_rule_lines(
        contracts["extract_compliance_obligations"]["path"], "source_type_rules")
    kind_rules = parse_rule_lines(
        contracts["extract_compliance_obligations"]["path"],
        "obligation_type_rules")
    requirement_classes = parse_keyed_frames(
        contracts["detect_missing_evidence"]["path"],
        "requirement_classes", "class")
    owner_frames = parse_keyed_frames(
        contracts["detect_undocumented_obligation_owner"]["path"],
        "question_frame", "obligation_trigger")
    review_re = parse_review_marker(
        contracts["identify_outdated_policies"]["path"])

    proposals_dir = os.path.join(vault_dir, "08_proposals")
    workspace_dir = os.path.join(vault_dir, "07_agent_workspaces")
    for required in (proposals_dir, workspace_dir):
        if not os.path.isdir(required):
            raise RuntimeError(f"{required} missing - bootstrap the vault first.")

    subgraph = graph_client.get_domain_subgraph(project_id, domain_prefix)
    exclusions = {k: v for k, v in (subgraph.get("excluded") or {}).items() if v}

    findings, skipped = [], []
    entries = sorted(knowledge.values(), key=lambda e: e["asset_id"])

    def check_posture(statement):
        lowered = statement.lower()
        for phrase in forbidden:
            if phrase in lowered:
                raise RuntimeError(
                    f"THE SENSITIVITY POSTURE: forbidden vocabulary "
                    f"{phrase!r} in a finding statement - compliance "
                    f"overclaiming is refused at the source.")

    def add_finding(finding):
        finding["statement"] = narrator(finding)
        check_posture(finding["statement"])
        findings.append(finding)

    # ---- Walk 1: explicit obligation extraction (EXCERPT_BACKED) --------
    skill = "extract_compliance_obligations"
    kind, basis = FINDING_KINDS[skill]
    for entry in entries:
        content = _norm(entry.get("content"))
        if not marker_re.search(content):
            continue   # no explicit marker -> never an obligation (P7)
        doc = _norm((entry.get("provenance") or {}).get("source_document") or "")
        source_type = apply_rules(*src_rules, doc)
        obligation_type = apply_rules(*kind_rules, content)
        add_finding({
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "asset_id": entry["asset_id"], "cite": _cite(entry),
            "excerpt": _excerpt(content), "source_document": doc,
            "source_type": source_type, "obligation_type": obligation_type,
            "cited_assets": [entry["asset_id"]],
            "evidence_lines": [
                f"Obligation excerpt (verbatim): {_cite(entry)} - \"{_excerpt(content)}\"",
                f"Source document: {doc or 'undeclared'} -> source_type "
                f"{source_type} (the declared filename rules)",
                f"Obligation type: {obligation_type} (the declared excerpt "
                f"keyword rules; UNCLASSIFIED is honest, never guessed)",
                f"Explicit marker rule: {'|'.join(markers)} - a sentence "
                f"without a marker is never extracted",
            ],
        })

    # ---- Walk 2: conflicts (CONFLICT_BACKED) + supersession route -------
    conflict_payload = graph_client.get_conflicts(expert_model_id)
    pairs = sorted((r for r in conflict_payload["relationships"]
                    if r["relationship_type"] == "CONFLICTS_WITH"
                    and r["classification"] == "DIRECT_CONTRADICTION"
                    and r["status"] in ("DETECTED", "CONFIRMED")),
                   key=lambda r: r["id"])
    history_cache = {}

    def history(asset_id):
        if asset_id not in history_cache:
            try:
                history_cache[asset_id] = graph_client.get_revision_history(asset_id)
            except Exception:
                history_cache[asset_id] = None   # above clearance - declared
        return history_cache[asset_id]

    def superseded_match(revised_id, other_content):
        h = history(revised_id)
        if not h:
            return None
        revs = h["revisions"]
        archived = [r for r in revs if r["status"] == "ARCHIVED"]
        current = [r for r in revs
                   if r["revision_number"] == h.get("active_revision_number")]
        if not archived or not current:
            return None
        cur = current[0]
        for old in archived:
            if _overlap(other_content, old["content"]) > _overlap(other_content, cur["content"]):
                return {"chain": revs, "superseded": old, "current": cur}
        return None

    for rel in pairs:
        a_id, b_id = rel["source_asset_id"], rel["target_asset_id"]
        a, b = knowledge.get(a_id), knowledge.get(b_id)
        if a is None or b is None:
            skipped.append({"skill": "detect_conflicting_compliance_statements",
                            "reason": f"conflict {rel['id']}: a participant is "
                                      f"outside this binding's clearance - "
                                      f"evidence cannot be cited, no finding"})
            continue
        content_a, content_b = _norm(a.get("content")), _norm(b.get("content"))
        doc_a = (a.get("provenance") or {}).get("source_document")
        doc_b = (b.get("provenance") or {}).get("source_document")
        if doc_a and doc_a == doc_b:
            # A compliance contradiction is by the contract CROSS-document;
            # intra-document pairs are process ordering, already held by the
            # governance conflict review.
            skipped.append({
                "skill": "detect_conflicting_compliance_statements",
                "reason": f"conflict {rel['id']}: both statements are from "
                          f"the same document ({doc_a}) - intra-document "
                          f"ordering, deferred to the governance conflict "
                          f"review"})
            continue
        shared = _shared_subject(content_a, content_b)
        if shared < SAME_SUBJECT_MINIMUM:
            skipped.append({
                "skill": "detect_conflicting_compliance_statements",
                "reason": f"conflict {rel['id']}: no shared subject matter "
                          f"({shared} subject token(s)) - deferred to the "
                          f"governance conflict review, which already holds "
                          f"it; declared, never silently dropped"})
            continue
        match_a = superseded_match(a_id, content_b)
        match_b = superseded_match(b_id, content_a)
        if match_a or match_b:
            match = match_a or match_b
            revised_id, outdated_id = (a_id, b_id) if match_a else (b_id, a_id)
            outdated = knowledge[outdated_id]
            skill = "identify_outdated_policies"
            kind, basis = FINDING_KINDS[skill]
            chain_lines = [
                (f"revision {r['revision_number']}: {r['status']}"
                 + (f", superseded by revision id {r['superseded_by_revision_id']}"
                    if r["superseded_by_revision_id"] else ""))
                for r in match["chain"]]
            add_finding({
                "skill": skill, "finding_kind": kind, "evidence_basis": basis,
                "route": "REVISION_CHAIN",
                "outdated_asset": outdated_id, "revised_asset": revised_id,
                "excerpt_outdated": _excerpt(_norm(outdated.get("content"))),
                "excerpt_current": _excerpt(_norm(match["current"]["content"])),
                "cited_assets": sorted((outdated_id, revised_id)),
                "evidence_lines": [
                    f"Outdated text: {_cite(outdated)} - "
                    f"\"{_excerpt(_norm(outdated.get('content')))}\"",
                    f"Current approved revision of asset {revised_id}: "
                    f"\"{_excerpt(_norm(match['current']['content']))}\"",
                    f"Revision chain of asset {revised_id}: "
                    + "; ".join(chain_lines),
                    f"Governed conflict relationship {rel['id']} "
                    f"({rel['classification']}, confidence {rel['confidence']:.3f}, "
                    f"status {rel['status']})",
                ],
            })
        else:
            skill = "detect_conflicting_compliance_statements"
            kind, basis = FINDING_KINDS[skill]
            add_finding({
                "skill": skill, "finding_kind": kind, "evidence_basis": basis,
                "asset_a": a_id, "asset_b": b_id,
                "cite_a": _cite(a), "cite_b": _cite(b),
                "excerpt_a": _excerpt(content_a), "excerpt_b": _excerpt(content_b),
                "cited_assets": sorted((a_id, b_id)),
                "evidence_lines": [
                    f"{_cite(a)}: \"{_excerpt(content_a)}\"",
                    f"{_cite(b)}: \"{_excerpt(content_b)}\"",
                    f"Cross-document: {doc_a or '?'} vs {doc_b or '?'}; "
                    f"shared subject tokens: {shared} (the declared v1.6 "
                    f"evidence rules, inherited wholesale)",
                    f"Governed conflict relationship {rel['id']} "
                    f"({rel['classification']}, confidence {rel['confidence']:.3f}, "
                    f"status {rel['status']})",
                ],
            })

    # ---- Walk 3: the review-interval clock (REVISION_BACKED) ------------
    skill = "identify_outdated_policies"
    kind, basis = FINDING_KINDS[skill]
    for entry in entries:
        content = _norm(entry.get("content"))
        m = review_re.search(content)
        if not m:
            continue
        interval = int(m.group(1))
        y, mo, d = (int(p) for p in m.group(2).split("-")) \
            if "-" in m.group(2) else (int(m.group(2)), int(m.group(3)), int(m.group(4)))
        due = add_months(y, mo, d, interval)
        due_str = f"{due[0]:04d}-{due[1]:02d}-{due[2]:02d}"
        if due < as_of_tuple:
            add_finding({
                "skill": skill, "finding_kind": kind, "evidence_basis": basis,
                "route": "REVIEW_INTERVAL",
                "asset_id": entry["asset_id"], "cite": _cite(entry),
                "excerpt": _excerpt(content), "due": due_str,
                "as_of": str(as_of),
                "cited_assets": [entry["asset_id"]],
                "evidence_lines": [
                    f"Declared review discipline (verbatim): {_cite(entry)} - "
                    f"\"{_excerpt(content)}\"",
                    f"Declared interval: {interval} months; last completed "
                    f"review: {m.group(2) if '-' in m.group(2) else '-'.join(m.groups()[1:])}",
                    f"Computed due date: {due_str}; declared as_of: {as_of} "
                    f"(a run parameter recorded verbatim - never wall-clock)",
                    "The document's OWN declared discipline - never age alone",
                ],
            })
        else:
            skipped.append({
                "skill": skill,
                "reason": f"asset {entry['asset_id']}: the declared review is "
                          f"current at as_of {as_of} (due {due_str}) - a "
                          f"covered control, no finding"})

    # ---- Walk 4: missing evidence (REFUSAL_BACKED) -----------------------
    skill = "detect_missing_evidence"
    kind, basis = FINDING_KINDS[skill]
    for frame in requirement_classes:
        question = frame["question"]
        trigger = frame["trigger"].lower()
        result = answerer(question)
        answer = result.get("answer") or ""
        if REFUSAL_MARKER not in answer:
            skipped.append({"skill": skill,
                            "reason": f"the corpus answers \"{question}\" - a "
                                      f"covered control, no gap, no finding"})
            continue
        sources = [e for e in entries
                   if trigger in _norm(e.get("content")).lower()]
        if not sources:
            skipped.append({
                "skill": skill,
                "reason": f"requirement class {frame['class']}: the "
                          f"requirement excerpt is not present at this "
                          f"binding's clearance - evidence cannot be cited, "
                          f"no finding"})
            continue
        primary = sources[0]
        add_finding({
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "requirement_class": frame["class"], "question": question,
            "requirement_excerpt": _excerpt(_norm(primary.get("content"))),
            "requirement_cites": ", ".join(_cite(e) for e in sources),
            "derived_requirement": any(_class_of(e) == "DERIVED"
                                       for e in sources),
            "cited_assets": sorted(e["asset_id"] for e in sources),
            "evidence_lines": [
                f"Documented requirement ({frame['class']}): "
                + "; ".join(f"{_cite(e)} - "
                            f"\"{_excerpt(_norm(e.get('content')))}\""
                            for e in sources),
                f"Reproducible refusal: \"{question}\" -> the packaged "
                f"answering contract returned INSUFFICIENT EVIDENCE",
                "Absence becomes a finding, never a fact: the governed "
                "corpus does not hold the evidence - nothing here verifies "
                "practice",
            ],
        })

    # ---- Walk 5: undocumented owners (REFUSAL_BACKED) --------------------
    skill = "detect_undocumented_obligation_owner"
    kind, basis = FINDING_KINDS[skill]
    for frame in owner_frames:
        question = frame["question"]
        trigger = frame["obligation_trigger"].lower()
        result = answerer(question)
        answer = result.get("answer") or ""
        if REFUSAL_MARKER not in answer:
            skipped.append({"skill": skill,
                            "reason": f"an approved document names the owner - "
                                      f"the corpus answers \"{question}\"; a "
                                      f"covered control, no finding"})
            continue
        sources = [e for e in entries
                   if trigger in _norm(e.get("content")).lower()
                   and marker_re.search(_norm(e.get("content")))]
        if not sources:
            skipped.append({
                "skill": skill,
                "reason": f"no EXPLICIT obligation statement found for "
                          f"trigger \"{frame['obligation_trigger']}\" - "
                          f"implied obligations are NEEDS_REVIEW territory, "
                          f"never a finding"})
            continue
        primary = sources[0]
        add_finding({
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "question": question, "asset_id": primary["asset_id"],
            "cite": _cite(primary),
            "excerpt": _excerpt(_norm(primary.get("content"))),
            "cited_assets": sorted(e["asset_id"] for e in sources),
            "evidence_lines": [
                f"Explicit obligation: "
                + "; ".join(f"{_cite(e)} - "
                            f"\"{_excerpt(_norm(e.get('content')))}\""
                            for e in sources),
                f"Reproducible refusal: \"{question}\" -> the packaged "
                f"answering contract returned INSUFFICIENT EVIDENCE",
                "The governed corpus does not document an owner - naming one "
                "is human work (the split ruling: detection here, "
                "assignment [ES]-gated)",
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

    # ---- The audit-readiness pack (assist - never a proposal) ------------
    # The four mandatory sections, always present even when empty (an empty
    # "missing" section is itself information). The pack prepares humans for
    # an audit; it never concludes for them and never enters knowledge.
    retrieval = pc.retrieve(package, pack_topic, top_k=5)
    known_lines = [
        f"- {_cite(e)} ({e.get('name')}): \"{_excerpt(_norm(e.get('content')))}\""
        for e in retrieval["selected"]]
    missing_findings = [f for f in findings
                        if f["finding_kind"] == "MISSING_COMPLIANCE_EVIDENCE"]
    contradiction_findings = [
        f for f in findings
        if f["finding_kind"] == "CONFLICTING_COMPLIANCE_STATEMENTS"]
    obligation_findings = [f for f in findings
                           if f["finding_kind"] == "COMPLIANCE_OBLIGATION"]
    pack_lines = [
        f"# Audit-readiness pack - {pack_topic}",
        "",
        "Internal assist output (prepare_audit_readiness_pack, [assist,",
        "synth]). NOT a proposal: this pack never enters knowledge. It is",
        "preparation material for humans facing an audit - never an audit",
        "conclusion. Narrative framing: SYNTHESIS_INFERRED.",
        "",
        "## Known (approved statements, cited)",
        "",
    ]
    pack_lines += known_lines or ["- (no approved coverage for this topic - "
                                  "stated rather than composed around)"]
    pack_lines += ["", "## Missing (requirements the corpus reproducibly "
                       "refuses to evidence)", ""]
    pack_lines += [f"- {f['requirement_cites']}: "
                   f"\"{f['requirement_excerpt']}\" -> refused: "
                   f"\"{f['question']}\"" for f in missing_findings] \
        or ["- (none in this run - an empty section is itself information)"]
    pack_lines += ["", "## Contradictory (governed conflict pairs in scope)", ""]
    pack_lines += [f"- {f['cite_a']} vs {f['cite_b']}: "
                   f"\"{f['excerpt_a']}\" / \"{f['excerpt_b']}\""
                   for f in contradiction_findings] \
        or ["- (none in this run - an empty section is itself information)"]
    pack_lines += ["", "## Unverified (documented, but no door can evidence "
                       "practice)", ""]
    pack_lines += [f"- {f['cite']}: \"{f['excerpt']}\" - documented "
                   f"({f['source_type']}/{f['obligation_type']}); practice "
                   f"execution is NOT verified through any door"
                   for f in obligation_findings] \
        or ["- (none in this run - an empty section is itself information)"]
    pack_lines += [
        "",
        f"Findings proposed by this run (PENDING, not consulted as facts): "
        f"{len(findings)}",
        "Accepted DERIVED facts are cited as DERIVED wherever consumed.",
        "",
    ]
    if exclusions:
        pack_lines += [f"Exclusions declared by the gateway: {exclusions}.", ""]
    pack_path = _write(workspace_dir, f"{workbench_name}-audit-readiness-pack",
                       "\n".join(pack_lines))

    return {"proposals": sorted(proposal_paths), "pack": pack_path,
            "findings": findings, "skipped": skipped,
            "exclusions": exclusions, "as_of": str(as_of),
            "contracts": {s: contracts[s]["path"] for s in ACTIVE_SKILLS}}
