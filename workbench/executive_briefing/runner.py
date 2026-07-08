"""Executive Operations Briefing Workbench runner - the v1.9 reference
consumer, the FIRST cross-workbench consumer.

Canonical workbench #1, two-stage by standing ruling (v1 here; the
decision queue stays behind [PMD]). A consumer, never a subsystem
(D22): its only doors are the .empkg via app.package_consumer and the
MCP gateway as a real client at a real AGENT token's clearance. Built
on workbench/common.py (relative import, zero shared-module edits).

THE SENSITIVITY POSTURE (the cardinal sin): THE UNSOURCED SENTENCE.
Every sentence written into the briefing pack is one of: governed-cited
(asset / conflict / trust component / revision), the declared clock
(as_of / since), inside an explicitly SYNTHESIS_INFERRED-framed
section, or a boundary sentence naming an actual limitation. The runner
enforces this at the source - it refuses to write an unsourced
sentence. Its twin, FALSE COMPLETENESS, is guarded structurally: the
mandatory "What this briefing cannot see" section, and the manifest's
forbidden vocabulary swept over every written byte.

THE FINDINGS RULING (v1.9): read-compose summaries NEVER re-enter
knowledge - only generate_unknowns_evidence_gaps_report proposes
(finding kind EXECUTIVE_EVIDENCE_GAP), because a documented gap is
genuinely new information. The five summarize/answer skills write into
the briefing pack (assist, /07_agent_workspaces) only.

Zero door growth: the nine frozen MCP tools + the .empkg are the whole
input surface. Anything not derivable through an existing door is
declared in the boundary section, never silently absent. One project,
one binding (v1).
"""
import datetime
import os
import re

from ..common import (
    import_package_consumer as _import_package_consumer,
    excerpt as _excerpt,
    load_active_contracts,
    StdioMcpGraphClient,
    write_hashed as _write,
)

ACTIVE_SKILLS = (
    "summarize_accepted_findings",
    "summarize_unresolved_conflicts",
    "summarize_governance_health",
    "answer_what_changed_since",
    "generate_unknowns_evidence_gaps_report",
    "prepare_executive_briefing",
)

# The ONLY proposal-emitting skill (the v1.9 findings ruling); the five
# read-compose skills emit no findings - their output is briefing-pack only.
FINDING_KINDS = {
    "generate_unknowns_evidence_gaps_report": ("EXECUTIVE_EVIDENCE_GAP", "REFUSAL_BACKED"),
}
READ_COMPOSE_SKILLS = frozenset((
    "summarize_accepted_findings", "summarize_unresolved_conflicts",
    "summarize_governance_health", "answer_what_changed_since"))

REFUSAL_MARKER = "INSUFFICIENT EVIDENCE"

# THE GATED LIST (WS0 ruling 2 + the boundary posture): refused live,
# naming the unminted decision or the standing ruling.
GATED_SKILLS = {
    "identify_decisions_needing_approval": "the Pipeline Metadata Door (stage 2)",
    "produce_executive_decision_queue": "the Pipeline Metadata Door (stage 2)",
    "compare_period_vs_previous": "the Operational Evidence Realm",
    "compare_operational_metrics": "the Operational Evidence Realm",
    "route_to_responsible_owner": "Exception Stewardship",
    "identify_obligation_owner": "Exception Stewardship",
    "produce_cross_functional_risk_register": "the persistent-register refusal (a persisted register is the row-temptation the [ES] shape refuses)",
    "schedule_weekly_briefing": "the schedule refusal (a human runs the briefing; the workbench never recurs)",
    "aggregate_across_projects": "the one-project ruling (v1 reads one project, one binding)",
}


class BriefingGraphClient(StdioMcpGraphClient):
    """The real MCP door for the briefing - the shared stdio client plus
    get_trust_score (an existing frozen tool common's client did not need;
    added here as a runner-local subclass so common.py stays frozen)."""

    def get_trust_score(self, expert_model_id):
        return self._call("get_trust_score", {"expert_model_id": expert_model_id})


def require_ungated(skill_id):
    if skill_id in GATED_SKILLS:
        raise RuntimeError(
            f"Skill {skill_id} is refused: {GATED_SKILLS[skill_id]} - the "
            f"runner refuses the task and names the boundary.")


def _norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


# ------------------------------------------------ contract-field parsing
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
    values, current = [], None
    for line in _block(_read_lines(path), key):
        s = line.strip()
        if s.startswith("- "):
            if current is not None:
                values.append(current)
            current = s[2:].strip().strip('"')
        elif current is not None and line.startswith("    "):
            current = _norm(current + " " + s.strip('"'))
    if current is not None:
        values.append(current)
    return [_norm(v) for v in values]


def parse_forbidden_vocabulary(manifest_path):
    return [v.lower() for v in parse_quoted_list(manifest_path, "forbidden_vocabulary")]


# ---------------------------------------------- workbench-of-origin
# The proposal filename convention is "{workbench}-{skill_id}-{12hex}.md":
# workbench names are hyphen-joined words (no underscore); skill_ids carry
# underscores. Origin derivable with ZERO new machinery.
_ORIGIN_RE = re.compile(r"^([a-z][a-z-]*?)-([a-z][a-z_]*)-[0-9a-f]{12}\.md$")


def _origin(entry):
    if (entry.get("source_class") or "PRIMARY").upper() != "DERIVED":
        return None
    src = (entry.get("provenance") or {}).get("source_document") or ""
    m = _ORIGIN_RE.match(src)
    return m.group(1) if m else "origin-undeclared"


def _class(entry):
    return (entry.get("source_class") or "PRIMARY").upper()


# ---------------------------------------------- THE UNSOURCED SENTENCE
# a line in a CITED section must carry one of these source tokens; prose
# is allowed only in the two framed sections (synth + boundary).
_SOURCE_TOKENS = ("asset ", "conflict ", "trust component", "revision ",
                  REFUSAL_MARKER, "as_of", "since ", "exclud", "[DERIVED]",
                  "[PMD]", "[OE]", "[ES]")


def _line_sourced(line):
    s = line.strip()
    if not s or s.startswith("#"):
        return True
    return any(tok in line for tok in _SOURCE_TOKENS)


def run_briefing(package_path, vault_dir, project_id, agent_principal,
                 binding_id, graph_client, as_of, since,
                 answerer=None, backend_dir=None, skills_dir=None,
                 manifest_path=None, requested_skills=None,
                 schedule=False, project_ids=None,
                 workbench_name="executive-briefing"):
    """The six ratified skills over the doors, at a DECLARED as_of + since.
    Returns a run summary: the briefing pack path, the gap proposal paths
    (the only proposals), the gap findings, and what was skipped."""
    for label, val in (("as_of", as_of), ("since", since)):
        if not val or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(val)):
            raise RuntimeError(
                f"prepare_executive_briefing refuses: no {label} declared for "
                f"the run (expected YYYY-MM-DD) - the clock is a declared "
                f"parameter, never sampled.")
    if schedule:
        raise RuntimeError(
            "the runner refuses to schedule or recur: a human runs the "
            "briefing point-in-time at the declared clock; the workbench "
            "never recurs (the schedule refusal).")
    if project_ids is not None and len(set(project_ids)) > 1:
        raise RuntimeError(
            "the runner refuses multi-project aggregation: v1 reads one "
            "project, one binding (the one-project ruling).")
    for skill_id in (requested_skills or ACTIVE_SKILLS):
        require_ungated(skill_id)

    since_iso = f"{since}T00:00:00"

    pc = _import_package_consumer(backend_dir)
    package = pc.load_package(package_path)   # verifies the hash chain
    package_hash = package["package_hash"]
    expert_model_id = package["manifest"]["expert_model_id"]
    entries = sorted(package["knowledge"], key=lambda e: e["asset_id"])
    knowledge = {e["asset_id"]: e for e in entries}
    if answerer is None:
        def answerer(question):
            return pc.consume(package_path, question)

    wb_dir = os.path.dirname(os.path.abspath(__file__))
    skills_dir = skills_dir or os.path.join(wb_dir, "skills")
    manifest_path = manifest_path or os.path.join(wb_dir, "workbench.yaml")
    contracts = load_active_contracts(
        skills_dir, tuple(requested_skills or ()) + ACTIVE_SKILLS)
    forbidden = parse_forbidden_vocabulary(manifest_path)
    questions = parse_quoted_list(
        contracts["generate_unknowns_evidence_gaps_report"]["path"],
        "question_frame")

    proposals_dir = os.path.join(vault_dir, "08_proposals")
    workspace_dir = os.path.join(vault_dir, "07_agent_workspaces")
    for required in (proposals_dir, workspace_dir):
        if not os.path.isdir(required):
            raise RuntimeError(f"{required} missing - bootstrap the vault first.")

    subgraph = graph_client.get_domain_subgraph(project_id, "")
    exclusions = {k: v for k, v in (subgraph.get("excluded") or {}).items() if v}

    # ---- Section 1: accepted findings (by class + workbench-of-origin) --
    accepted_lines = []
    for e in entries:
        cls = _class(e)
        origin = _origin(e)
        tag = (f" [DERIVED, origin: {origin}]" if cls == "DERIVED"
               else " [PRIMARY]")
        accepted_lines.append(
            f"- asset {e['asset_id']}{tag}: \"{_excerpt(_norm(e.get('content')))}\"")
    derived = [e for e in entries if _class(e) == "DERIVED"]
    origins = sorted({_origin(e) for e in derived})

    # ---- Section 2: unresolved conflicts --------------------------------
    conflict_payload = graph_client.get_conflicts(expert_model_id)
    unresolved = sorted((r for r in conflict_payload["relationships"]
                         if r["status"] in ("DETECTED", "CONFIRMED")),
                        key=lambda r: r["id"])
    conflict_lines = []
    for r in unresolved:
        a, b = knowledge.get(r["source_asset_id"]), knowledge.get(r["target_asset_id"])
        ax = f"\"{_excerpt(_norm(a.get('content')))}\"" if a else "(above clearance - excluded)"
        bx = f"\"{_excerpt(_norm(b.get('content')))}\"" if b else "(above clearance - excluded)"
        conflict_lines.append(
            f"- conflict {r['id']} ({r['classification']}, status {r['status']}): "
            f"asset {r['source_asset_id']} {ax} vs asset {r['target_asset_id']} {bx}")

    # ---- Section 3: governance health (door-limited) --------------------
    trust = graph_client.get_trust_score(expert_model_id)
    health_lines = []
    for c in trust.get("components", []):
        if c.get("measured"):
            health_lines.append(
                f"- trust component {c['key']}: score {c['score']} "
                f"(weight {c['weight']}) - {_norm(c.get('reason'))}")
        else:
            health_lines.append(
                f"- trust component {c['key']}: not measured (no underlying "
                f"data) - declared, never scored as zero")
    health_lines.append(
        f"- unresolved conflicts: {len(unresolved)} "
        f"(conflict ids {', '.join(str(r['id']) for r in unresolved) or 'none'})")

    # ---- Section 4: what changed since (declared clock) -----------------
    changed_lines = []
    for e in entries:
        try:
            hist = graph_client.get_revision_history(e["asset_id"])
        except Exception:
            continue
        for rev in hist.get("revisions", []):
            at = rev.get("approved_at")
            if rev.get("status") == "APPROVED" and at and at > since_iso:
                changed_lines.append(
                    f"- asset {e['asset_id']} revision {rev['revision_number']} "
                    f"accepted at {at} (since {since})")
    changed_lines.sort()

    # ---- Section 5: unknowns & evidence gaps (REFUSAL_BACKED proposals) --
    gap_lines, findings, skipped = [], [], []
    for question in questions:
        result = answerer(question)
        answer = result.get("answer") or ""
        if REFUSAL_MARKER not in answer:
            skipped.append({"skill": "generate_unknowns_evidence_gaps_report",
                            "reason": f"the corpus answers \"{question}\" - a "
                                      f"covered control, no gap"})
            continue
        gap_lines.append(
            f"- gap: \"{question}\" -> the packaged answering contract "
            f"returned {REFUSAL_MARKER} (reproducible)")
        findings.append({
            "skill": "generate_unknowns_evidence_gaps_report",
            "finding_kind": "EXECUTIVE_EVIDENCE_GAP",
            "evidence_basis": "REFUSAL_BACKED", "question": question,
            "cited_assets": [],
            "statement": (f"The governed corpus cannot answer a declared "
                          f"executive question: \"{question}\". The "
                          f"reproducible {REFUSAL_MARKER} refusal is the gap; "
                          f"this says nothing about whether the answer exists "
                          f"in the world - only that the governed corpus does "
                          f"not hold it."),
            "evidence_lines": [
                f"Declared executive question (verbatim): \"{question}\"",
                f"Reproducible refusal: the packaged answering contract "
                f"returned {REFUSAL_MARKER}",
                "Absence becomes a finding, never a fact.",
            ],
        })

    # ---- Assemble the briefing pack (assist; 07_agent_workspaces) -------
    def section(title, lines, empty_note, prose=False):
        body = lines or [f"- ({empty_note} - an empty section is itself "
                         f"information)"]
        return (title, prose, body)

    sections = [
        section("## Accepted findings (by class and workbench-of-origin)",
                accepted_lines, "no approved knowledge in scope"),
        section("## Unresolved conflicts", conflict_lines,
                "no unresolved governed conflicts"),
        section("## Governance health (door-visible signals only)",
                health_lines, "no health signal available"),
        section(f"## What changed since {since}", changed_lines,
                f"no governed change accepted after since {since}"),
        section("## Unknowns & evidence gaps", gap_lines,
                "no declared executive question refused"),
    ]
    # Recommended attention - the ONLY synthesis section, wholly framed.
    attn = [
        "This section is SYNTHESIS_INFERRED: it prioritizes the governed",
        "signals above for a human's attention; it decides nothing and",
        "approves nothing.",
        f"- {len(unresolved)} unresolved conflict(s) and {len(findings)} "
        "evidence gap(s) are the governed signals most worth a human's "
        "review this cycle.",
    ]
    sections.append(("## Recommended attention [SYNTHESIS_INFERRED]", True, attn))
    # The boundary section - FALSE COMPLETENESS guard.
    boundary = [
        "This briefing composes ONLY what the governed doors expose. It "
        "does not and cannot see:",
        "- pending or held proposals and the computed inbox: agent "
        "visibility of ungated material is the Pipeline Metadata Door "
        "[PMD], not minted - this briefing reports accepted facts only.",
        "- operational metrics, execution data, and period-vs-period "
        "operational comparison: the Operational Evidence Realm [OE], not "
        "minted.",
        "- owner assignment, routing, and stewardship: Exception "
        "Stewardship [ES], not minted.",
        (f"- content above this binding's clearance: "
         f"{exclusions or 'none excluded this run'} (declared by the "
         f"gateway, never guessed)."),
    ]
    sections.append(("## What this briefing cannot see", True, boundary))

    header = [
        f"# Executive Operations Briefing - as_of {as_of}",
        "",
        "Internal assist output (prepare_executive_briefing, [assist,",
        "synth]). NOT a proposal: this pack never enters knowledge. Every",
        "sentence is governed-cited, the declared clock, framed as",
        f"SYNTHESIS_INFERRED, or a declared boundary. Declared clock: as_of",
        f"{as_of}, since {since} (run parameters, never wall-clock).",
        "",
    ]
    pack = list(header)
    for title, prose, lines in sections:
        pack.append(title)
        pack.append("")
        pack.extend(lines)
        pack.append("")

    # THE UNSOURCED SENTENCE + FALSE COMPLETENESS, enforced at the source.
    cited_titles = {sections[i][0] for i in range(5)}
    active_title = None
    for line in pack:
        s = line.strip()
        if s.startswith("## "):
            active_title = line
            continue
        prose_section = active_title not in cited_titles
        if not prose_section and not _line_sourced(line):
            raise RuntimeError(
                f"THE UNSOURCED SENTENCE: a cited-section line carries no "
                f"governed source token: {line!r}")
        low = line.lower()
        for phrase in forbidden:
            if phrase in low:
                raise RuntimeError(
                    f"FALSE COMPLETENESS: forbidden vocabulary {phrase!r} in "
                    f"the briefing - refused at the source.")
    brief_path = _write(workspace_dir,
                        f"{workbench_name}-executive-briefing",
                        "\n".join(pack))

    # ---- The gap proposals (the ONLY proposals; /08_proposals) ----------
    proposal_paths = []
    for f in findings:
        lines = [
            "---", "em_proposal: 1", f"agent_principal: {agent_principal}",
            f"binding_id: {binding_id}", f"package_hash: {package_hash}",
            f"workbench: {workbench_name}", f"skill: {f['skill']}",
            "skill_version: 1", f"finding_kind: {f['finding_kind']}",
            f"evidence_basis: {f['evidence_basis']}",
            f"cited_assets: {','.join(str(i) for i in f['cited_assets'])}",
            "---", "",
            "# Executive Evidence Gap - a governed unknown", "",
            "Agent-synthesized finding. This document is a PROPOSAL: it",
            "becomes knowledge only if a human accepts it at the gate, and",
            "then as a DERIVED fact (D29/D30). It records that the governed",
            "corpus cannot answer a declared executive question - never that",
            "the answer does not exist in the world.", "",
            "## Finding", "", f["statement"], "", "## Evidence", "",
        ]
        for line in f["evidence_lines"]:
            lines.append(f"- {line}")
        lines += ["", "## Proposed action", "",
                  "Author or ingest the missing document through the governed "
                  "pipeline; on acceptance it becomes a DERIVED fact that "
                  "closes the gap.", ""]
        if exclusions:
            lines += ["## What the agent could not see", "",
                      f"Exclusions declared by the gateway: {exclusions}.", ""]
        proposal_paths.append(_write(
            proposals_dir, f"{workbench_name}-{f['skill']}", "\n".join(lines)))

    return {"briefing": brief_path, "proposals": sorted(proposal_paths),
            "findings": findings, "skipped": skipped, "exclusions": exclusions,
            "as_of": str(as_of), "since": str(since),
            "accepted_origins": origins, "unresolved_conflicts": len(unresolved),
            "contracts": {s: contracts[s]["path"] for s in ACTIVE_SKILLS}}
