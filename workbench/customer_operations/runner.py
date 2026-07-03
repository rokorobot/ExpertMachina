"""Customer Operations Workbench runner - the v1.6 reference consumer.

Canonical workbench #5 in the catalog (workbench.yaml is the manifest;
the five ratified skill contracts in skills/ are the binding v1.6
execution contracts). The runner is a consumer, never a subsystem
(D22): its only doors are the .empkg via app.package_consumer, the MCP
gateway as a real client at a real AGENT token's clearance, and file
writes into the vault - one proposal per finding into /08_proposals,
the assist brief into /07_agent_workspaces. Guard 5 sweeps this module
the moment it exists.

The runner HONORS the skill contracts, not just carries them:
  - question frames are READ FROM the contract files (skills/*.yaml),
    never hardcoded;
  - a skill whose contract is not status: ACTIVE is refused - tags are
    gates, not preferences;
  - refusal-first: a coverage question the corpus answers produces NO
    finding; an obligation that is not explicit produces NO finding;
    evidence that cannot be cited produces NO finding.

Detection is a deterministic evidence walk over the doors (governed
conflicts, revision chains, reproducible refusals). Two injectable
seams: `answerer` (real = package_consumer.consume through the D19
resolver; CI = a deterministic contract-follower) and `narrator`
(default = deterministic templates; the real-model run overrides it -
the open honest slot). Whatever narrates, every finding cites the
governed evidence it rests on: no evidence, no finding.
"""
import hashlib
import json
import os
import re
import sys

ACTIVE_SKILLS = (
    "detect_customer_promise_conflict",
    "detect_outdated_customer_guidance",
    "detect_missing_support_playbook",
    "detect_sla_obligation_gap",
    "prepare_customer_policy_brief",
)

FINDING_KINDS = {
    "detect_customer_promise_conflict": ("CUSTOMER_PROMISE_CONFLICT", "CONFLICT_BACKED"),
    "detect_outdated_customer_guidance": ("OUTDATED_CUSTOMER_GUIDANCE", "REVISION_BACKED"),
    "detect_missing_support_playbook": ("MISSING_SUPPORT_PLAYBOOK", "REFUSAL_BACKED"),
    "detect_sla_obligation_gap": ("SLA_OBLIGATION_GAP", "REFUSAL_BACKED"),
}

REFUSAL_MARKER = "INSUFFICIENT EVIDENCE"


def _import_package_consumer(backend_dir=None):
    backend_dir = backend_dir or os.environ.get("EM_BACKEND_DIR")
    if backend_dir and backend_dir not in sys.path:
        sys.path.append(backend_dir)
    from app import package_consumer
    return package_consumer


def _tokens(text):
    # Deliberately keeps 2-char tokens: the corpus lesson - numbers
    # ("30", "14", "24", "48") often carry the whole difference between
    # two policy statements.
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(t) >= 2}


def _overlap(a, b):
    return len(_tokens(a) & _tokens(b))


# The declared same-subject rule (a ratified evidence-rule refinement,
# recorded at the WS3 gate): a promise conflict requires the two
# statements to share SUBJECT MATTER, not merely parallel timeframe
# structure ("within N days/hours") - the NLI engine over-fires on
# different-topic timeframe sentences. Subject tokens are alphabetic,
# length >= 4, excluding the timeframe vocabulary. Pairs without shared
# subject are DEFERRED to the governance conflict review (EM's own
# surface already holds every detected conflict) - declared, never
# silently dropped.
TIMEFRAME_STOPWORDS = frozenset((
    "within", "business", "days", "hours", "must", "shall", "every",
    "each", "during", "receive", "request", "requests", "target",
    "response", "working", "calendar", "month", "months", "year",
))
SAME_SUBJECT_MINIMUM = 2


def _subject_tokens(text):
    return {t for t in re.findall(r"[a-z]+", (text or "").lower())
            if len(t) >= 4 and t not in TIMEFRAME_STOPWORDS}


def _shared_subject(a, b):
    return len(_subject_tokens(a) & _subject_tokens(b))


def _excerpt(text, limit=200):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def load_skill_contract(skills_dir, skill_id):
    """Minimal line-based read of one ratified contract (stdlib only -
    the doors allow no YAML library): skill_id, status, boundary tags,
    and the question_frame entries (with wrapped-line joining)."""
    path = os.path.join(skills_dir, f"{skill_id}.yaml")
    if not os.path.isfile(path):
        raise RuntimeError(f"Skill contract missing: {path}")
    contract = {"skill_id": None, "status": None, "boundary_tags": None,
                "questions": [], "path": path}
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    in_frame = False
    current = None
    for line in lines:
        if line.startswith("skill_id:"):
            contract["skill_id"] = line.split(":", 1)[1].strip()
        elif line.startswith("status:"):
            contract["status"] = line.split(":", 1)[1].strip()
        elif line.startswith("boundary_tags:"):
            contract["boundary_tags"] = line.split(":", 1)[1].strip()
        elif line.startswith("question_frame:"):
            in_frame = True
        elif in_frame:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                if current is not None:
                    contract["questions"].append(current)
                current = stripped[2:].strip().strip('"')
            elif line.startswith("    ") and current is not None:
                current = current.rstrip('"') + " " + stripped.rstrip('"')
            else:
                if current is not None:
                    contract["questions"].append(current)
                    current = None
                in_frame = False
    if current is not None:
        contract["questions"].append(current)
    contract["questions"] = [" ".join(q.split()) for q in contract["questions"]]
    if contract["skill_id"] != skill_id:
        raise RuntimeError(f"{path}: skill_id mismatch ({contract['skill_id']})")
    return contract


class StdioMcpGraphClient:
    """The real MCP door: a stdio client session against
    backend/mcp_server.py authenticated by EM_AGENT_TOKEN in the
    server's environment. The CI gate injects an in-process substitute
    that resolves the same token through the same gateway functions."""

    def __init__(self, python_exe, server_path, env=None, cwd=None):
        self._params = dict(command=python_exe, args=[server_path],
                            env=env, cwd=cwd)

    def _call(self, tool, arguments):
        import asyncio
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def _run():
            server = StdioServerParameters(**self._params)
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool, arguments)
                    return json.loads(result.content[0].text)
        return asyncio.run(_run())

    def get_conflicts(self, expert_model_id):
        return self._call("get_conflicts", {"expert_model_id": expert_model_id})

    def get_revision_history(self, asset_id):
        return self._call("get_revision_history", {"asset_id": asset_id})

    def get_domain_subgraph(self, project_id, domain_prefix):
        return self._call("get_domain_subgraph",
                          {"project_id": project_id,
                           "domain_prefix": domain_prefix})


def default_narrator(finding):
    """Deterministic narration templates. The real-model run replaces
    this seam (the open honest slot); the evidence is identical either
    way - narration presents, it never decides."""
    kind = finding["finding_kind"]
    if kind == "CUSTOMER_PROMISE_CONFLICT":
        return (f"A customer-facing commitment and an internal working rule "
                f"disagree: governed asset {finding['asset_a']} states "
                f"\"{finding['excerpt_a']}\" while governed asset "
                f"{finding['asset_b']} states \"{finding['excerpt_b']}\". "
                f"Until a human reconciles them, staff and customers are "
                f"working from different promises.")
    if kind == "OUTDATED_CUSTOMER_GUIDANCE":
        return (f"Governed asset {finding['outdated_asset']} still gives "
                f"guidance (\"{finding['excerpt_outdated']}\") that tracks a "
                f"superseded revision of asset {finding['revised_asset']}, "
                f"whose current approved revision states "
                f"\"{finding['excerpt_current']}\". The outdated guidance is "
                f"customer-visible until revised or retired.")
    if kind == "MISSING_SUPPORT_PLAYBOOK":
        return (f"Approved guidance creates a customer situation "
                f"(\"{finding['trigger_excerpt']}\", asset "
                f"{finding['trigger_asset']}) but the governed corpus cannot "
                f"answer \"{finding['question']}\" - no approved procedure "
                f"covers it. Support agents facing this situation have no "
                f"playbook to follow.")
    if kind == "SLA_OBLIGATION_GAP":
        return (f"An approved document commits the company to an obligation "
                f"(\"{finding['trigger_excerpt']}\", asset "
                f"{finding['trigger_asset']}) but the governed corpus cannot "
                f"answer \"{finding['question']}\" - no approved procedure "
                f"explains how the obligation is fulfilled or by whom.")
    return f"Finding of kind {kind}."


PROPOSED_ACTIONS = {
    "CUSTOMER_PROMISE_CONFLICT": ("Reconcile the two statements: revise one "
                                  "side through the governed revision "
                                  "workflow, or dismiss the conflict with a "
                                  "recorded reason if both legitimately "
                                  "apply in different contexts."),
    "OUTDATED_CUSTOMER_GUIDANCE": ("Revise or retire the outdated guidance "
                                   "through the governed revision workflow "
                                   "so it tracks the current approved "
                                   "policy revision."),
    "MISSING_SUPPORT_PLAYBOOK": ("Author the missing procedure as an "
                                 "ordinary governed document (it becomes a "
                                 "PRIMARY fact on approval)."),
    "SLA_OBLIGATION_GAP": ("Author the fulfillment procedure as an ordinary "
                           "governed document and assign ownership at the "
                           "human layer (owner assignment is Exception "
                           "Stewardship territory, not this skill's)."),
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
        f"# {kind.replace('_', ' ').title()} - customer operations finding",
        "",
        "Agent-synthesized finding. This document is a PROPOSAL: it becomes",
        "knowledge only if a human accepts it at the gate, and then as a",
        "DERIVED fact (D29/D30).",
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


def _write(path_dir, name_stub, content):
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
    path = os.path.join(path_dir, f"{name_stub}-{digest}.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return path


def run_diagnostic(package_path, vault_dir, project_id, agent_principal,
                   binding_id, graph_client, domain_prefix="customer_operations",
                   answerer=None, narrator=None, backend_dir=None,
                   skills_dir=None, brief_topic="enterprise refunds",
                   workbench_name="customer-operations"):
    """The five ratified skills over the four doors. Returns a run
    summary: proposal paths (one per finding), the assist brief path,
    the findings, and what was skipped with the refusing reason."""
    pc = _import_package_consumer(backend_dir)
    package = pc.load_package(package_path)  # verifies the hash chain
    package_hash = package["package_hash"]
    expert_model_id = package["manifest"]["expert_model_id"]
    knowledge = {e["asset_id"]: e for e in package["knowledge"]}
    narrator = narrator or default_narrator
    if answerer is None:
        def answerer(question):  # the real D19 path
            return pc.consume(package_path, question)

    skills_dir = skills_dir or os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "skills")
    contracts = {}
    for skill_id in ACTIVE_SKILLS:
        contract = load_skill_contract(skills_dir, skill_id)
        if contract["status"] != "ACTIVE":
            raise RuntimeError(
                f"Skill {skill_id} is {contract['status']}, not ACTIVE - "
                f"tags are gates, not preferences; the runner refuses.")
        contracts[skill_id] = contract

    proposals_dir = os.path.join(vault_dir, "08_proposals")
    workspace_dir = os.path.join(vault_dir, "07_agent_workspaces")
    for required in (proposals_dir, workspace_dir):
        if not os.path.isdir(required):
            raise RuntimeError(f"{required} missing - bootstrap the vault first.")

    subgraph = graph_client.get_domain_subgraph(project_id, domain_prefix)
    exclusions = {k: v for k, v in (subgraph.get("excluded") or {}).items() if v}

    findings, skipped = [], []

    # ---- The conflict walk: promise conflicts + outdated guidance -----
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
                history_cache[asset_id] = None  # above clearance - declared
        return history_cache[asset_id]

    def superseded_match(revised_id, other_content):
        """True when `other_content` tracks a superseded (ARCHIVED)
        revision of `revised_id` more closely than its current one -
        the REVISION_BACKED evidence rule."""
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
            skipped.append({"skill": "detect_customer_promise_conflict",
                            "reason": f"conflict {rel['id']}: a participant is "
                                      f"outside this binding's clearance - "
                                      f"evidence cannot be cited, no finding"})
            continue
        content_a, content_b = a.get("content") or "", b.get("content") or ""
        shared = _shared_subject(content_a, content_b)
        if shared < SAME_SUBJECT_MINIMUM:
            skipped.append({
                "skill": "detect_customer_promise_conflict",
                "reason": f"conflict {rel['id']}: no shared subject matter "
                          f"({shared} subject token(s)) - deferred to the "
                          f"governance conflict review, which already holds "
                          f"it; declared, never silently dropped"})
            continue
        match_a = superseded_match(a_id, content_b)  # b tracks a's old rev?
        match_b = superseded_match(b_id, content_a)  # a tracks b's old rev?
        if match_a or match_b:
            match = match_a or match_b
            revised_id, outdated_id = (a_id, b_id) if match_a else (b_id, a_id)
            outdated = knowledge[outdated_id]
            skill = "detect_outdated_customer_guidance"
            kind, basis = FINDING_KINDS[skill]
            chain_lines = [
                (f"revision {r['revision_number']}: {r['status']}"
                 + (f", superseded by revision id {r['superseded_by_revision_id']}"
                    if r["superseded_by_revision_id"] else ""))
                for r in match["chain"]]
            finding = {
                "skill": skill, "finding_kind": kind, "evidence_basis": basis,
                "outdated_asset": outdated_id, "revised_asset": revised_id,
                "excerpt_outdated": _excerpt(outdated.get("content")),
                "excerpt_current": _excerpt(match["current"]["content"]),
                "cited_assets": sorted((outdated_id, revised_id)),
                "evidence_lines": [
                    f"Outdated guidance: governed asset {outdated_id} - "
                    f"\"{_excerpt(outdated.get('content'))}\"",
                    f"Current approved revision of asset {revised_id}: "
                    f"\"{_excerpt(match['current']['content'])}\"",
                    f"Superseded revision it tracks: "
                    f"\"{_excerpt(match['superseded']['content'])}\"",
                    f"Revision chain of asset {revised_id}: "
                    + "; ".join(chain_lines),
                    f"Governed conflict relationship {rel['id']} "
                    f"({rel['classification']}, confidence {rel['confidence']:.3f}, "
                    f"status {rel['status']})",
                ],
            }
        else:
            skill = "detect_customer_promise_conflict"
            kind, basis = FINDING_KINDS[skill]
            finding = {
                "skill": skill, "finding_kind": kind, "evidence_basis": basis,
                "asset_a": a_id, "asset_b": b_id,
                "excerpt_a": _excerpt(content_a), "excerpt_b": _excerpt(content_b),
                "cited_assets": sorted((a_id, b_id)),
                "evidence_lines": [
                    f"Governed asset {a_id}: \"{_excerpt(content_a)}\"",
                    f"Governed asset {b_id}: \"{_excerpt(content_b)}\"",
                    f"Governed conflict relationship {rel['id']} "
                    f"({rel['classification']}, confidence {rel['confidence']:.3f}, "
                    f"status {rel['status']})",
                ],
            }
        finding["statement"] = narrator(finding)
        findings.append(finding)

    # ---- The coverage walk: missing playbooks + obligation gaps -------
    for skill in ("detect_missing_support_playbook", "detect_sla_obligation_gap"):
        kind, basis = FINDING_KINDS[skill]
        for question in contracts[skill]["questions"]:
            result = answerer(question)
            answer = result.get("answer") or ""
            if REFUSAL_MARKER not in answer:
                skipped.append({"skill": skill,
                                "reason": f"the corpus answers "
                                          f"\"{question}\" - no gap, no finding"})
                continue
            evidence = result.get("evidence") or []
            if skill == "detect_sla_obligation_gap":
                candidates = [e for e in evidence
                              if re.search(r"\b(shall|must)\b",
                                           (e.get("content") or "").lower())]
                reason_none = ("no EXPLICIT obligation statement found for "
                               f"\"{question}\" - implied obligations are "
                               "NEEDS_REVIEW territory, never a finding")
            else:
                candidates = evidence
                reason_none = ("no governed document explicitly names the "
                               f"situation behind \"{question}\" - no finding")
            candidates = [e for e in candidates
                          if _overlap(question, e.get("content") or "") >= 3]
            if not candidates:
                skipped.append({"skill": skill, "reason": reason_none})
                continue
            trigger = max(candidates,
                          key=lambda e: (_overlap(question, e.get("content") or ""),
                                         -e["asset_id"]))
            partial_ids = sorted({e["asset_id"] for e in evidence})
            finding = {
                "skill": skill, "finding_kind": kind, "evidence_basis": basis,
                "question": question,
                "trigger_asset": trigger["asset_id"],
                "trigger_excerpt": _excerpt(trigger.get("content")),
                "cited_assets": sorted(set(partial_ids) | {trigger["asset_id"]}),
                "evidence_lines": [
                    f"Triggering governed excerpt: asset {trigger['asset_id']} - "
                    f"\"{_excerpt(trigger.get('content'))}\"",
                    f"Reproducible refusal: \"{question}\" -> the packaged "
                    f"answering contract returned INSUFFICIENT EVIDENCE",
                    f"Nearest partial evidence offered by retrieval: assets "
                    f"{', '.join(str(i) for i in partial_ids) or 'none'}",
                ],
            }
            finding["statement"] = narrator(finding)
            findings.append(finding)

    # ---- One proposal document per finding -----------------------------
    proposal_paths = []
    for finding in findings:
        content = _proposal_document(finding, agent_principal, binding_id,
                                     package_hash, exclusions, workbench_name)
        proposal_paths.append(_write(proposals_dir,
                                     f"{workbench_name}-{finding['skill']}",
                                     content))

    # ---- The assist brief (never a proposal, never enters knowledge) --
    brief_contract = contracts["prepare_customer_policy_brief"]
    retrieval = pc.retrieve(package, brief_topic, top_k=5)
    brief_lines = [
        f"# Customer policy brief - {brief_topic}",
        "",
        "Internal assist output (prepare_customer_policy_brief, [assist,",
        "synth]). NOT a proposal: this brief never enters knowledge. Content",
        "meant to become knowledge is authored by a human (PRIMARY) or",
        "proposed through the valve. Narrative framing: SYNTHESIS_INFERRED.",
        "",
        "## Approved guidance in scope",
        "",
    ]
    for entry in retrieval["selected"]:
        brief_lines.append(f"- asset {entry['asset_id']} ({entry.get('name')}): "
                           f"\"{_excerpt(entry.get('content'))}\"")
    brief_lines += [
        "",
        "## Findings context",
        "",
        f"- Findings proposed by this run (PENDING, not consulted as facts): "
        f"{len(findings)}",
        "- Accepted DERIVED findings consulted: none available at run time "
        "(this skill consumes ACCEPTED findings only, never pending "
        "proposals).",
        "",
    ]
    if exclusions:
        brief_lines += [f"Exclusions declared by the gateway: {exclusions}.", ""]
    brief_path = _write(workspace_dir, f"{workbench_name}-policy-brief",
                        "\n".join(brief_lines))

    return {"proposals": sorted(proposal_paths), "brief": brief_path,
            "findings": findings, "skipped": skipped,
            "exclusions": exclusions,
            "contracts": {s: contracts[s]["path"] for s in ACTIVE_SKILLS}}
