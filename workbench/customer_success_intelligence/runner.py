"""Customer Success Intelligence Workbench runner - the v2.4 reference consumer.

Canonical workbench #6 in the catalog; the SIXTH commercial workbench
and the substrate's THIRD consumer. The runner is a consumer, never a
subsystem (D22): its only doors are the .empkg via app.package_consumer,
the MCP gateway as a real client at a real AGENT token's clearance, and
file writes into the vault - one proposal per finding into /08_proposals,
the review brief into /07_agent_workspaces. Guard 5 sweeps this module
the moment it exists. Built on workbench/common.py (the ruling-6 shared
plumbing, reached by relative import so the reuse stays inside the swept
root) - the SEVENTH zero-edit reuse target.

THE SPINE: v2.4 diagnoses per-customer term deviation, obligation
exposure, and coverage gaps from approved documents, register facts, and
declared-clock windows - never the state, behavior, or future of the
customer relationship itself.

THE SENSITIVITY POSTURE (the cardinal sin + its twin):
  - THE IMPUTED HEALTH: the runner never asserts the state, behavior,
    sentiment, satisfaction, adoption, churn risk, renewal likelihood,
    or future of a customer relationship as a governed fact. The
    manifest's forbidden_vocabulary is swept over every written byte
    QUOTE-FRAME-AWARE: a forbidden phrase may appear ONLY inside a
    verbatim quoted-claim blockquote (a line beginning "> ") of an
    UNBACKED_HEALTH_ASSUMPTION finding, never in the workbench's own
    prose. THE QUOTE FRAME is the whole exemption.
  - THE HEALTH-SENTENCE DISTINCTION: a document statement ABOUT the
    relationship is evidence the runner may QUOTE as an unsupported
    assumption; telemetry AS DATA is [OE]. THE HEALTH-SCORE PLANT (an
    approved account plan carrying a health-score table) surfaces ONLY
    inside the quote frame; it never becomes customer-health truth.
  - THE BASELINE DOCTRINE: no standard baseline, no deviation
    diagnosis. Deviation is computed ONLY against approved facts
    carrying the declared baseline marker; a missing baseline is a
    declared refusal, never an inferred norm.

THE UNREAD CUSTOMER: no operational customer-data door exists
(structural); the health-score plant surfaces only as a quoted
unsupported assumption (adversarial); the IMPUTED-HEALTH sweep runs
quote-frame-aware on every written byte (byte-level).

The runner HONORS the five skill contracts: the baseline markers,
deviation axes + value patterns, obligation markers, coverage classes +
markers, and assumption markers are READ FROM the contract files, never
hardcoded. A non-ACTIVE contract is refused; the gated list ([OE]/[ES])
is refused live naming the unminted decision.

Two injectable seams (as in v1.6-v2.3): `answerer` (real =
package_consumer.consume through the D19 resolver; CI = the declared
deterministic contract-follower) and `narrator` (default =
deterministic templates; the real-model run overrides it). Whatever
narrates, every finding cites the governed evidence it rests on: no
evidence, no finding. DERIVED register evidence is cited AS DERIVED
(THE THIRD HARVEST).
"""
import datetime
import os
import re

from ..common import (
    import_package_consumer as _import_package_consumer,
    excerpt as _excerpt,
    load_active_contracts,
    StdioMcpGraphClient,       # noqa: F401 - the real-run transport, re-exported
    write_hashed as _write,
)

ACTIVE_SKILLS = (
    "detect_customer_term_deviation",
    "detect_customer_renewal_obligations",
    "detect_customer_coverage_gap",
    "detect_unbacked_customer_health_assumption",
    "prepare_customer_success_review_brief",
)

FINDING_KINDS = {
    "detect_customer_term_deviation": ("CUSTOMER_TERM_DEVIATION", "EXCERPT_BACKED"),
    "detect_customer_renewal_obligations": ("CUSTOMER_RENEWAL_OBLIGATION", "EXCERPT_BACKED"),
    "detect_customer_coverage_gap": ("CUSTOMER_COVERAGE_GAP", "REFUSAL_BACKED"),
    "detect_unbacked_customer_health_assumption": ("UNBACKED_HEALTH_ASSUMPTION", "EXCERPT_BACKED"),
}

# THE GATED LIST (the v2.4 WS0 ruling 4/4a + the manifest's
# refused_until_minted): the relationship-state family stays [OE], and
# ownerless-obligation assignment stays [ES]. Refused live, naming the
# unminted decision.
GATED_SKILLS = {
    "detect_declining_activity": "the Operational Evidence Realm",
    "detect_low_usage": "the Operational Evidence Realm",
    "detect_unresolved_customer_issues": "the Operational Evidence Realm",
    "score_customer_risk": "the Operational Evidence Realm",
    "cluster_recurring_complaints": "the Operational Evidence Realm",
    "identify_churn_signals": "the Operational Evidence Realm",
    "detect_customer_obligations_without_owner": "Exception Stewardship",
}

# THE QUOTE FRAME: a written line beginning with this prefix is verbatim
# quoted document material (never the workbench's own assertion) and is
# the SOLE exemption from the IMPUTED-HEALTH vocabulary sweep.
QUOTE_PREFIX = "> "

# Declared word->days map for notice periods stated in words (the
# corpus states "sixty days", "ninety days"). Extended only as the
# corpus needs; an unmapped word yields no computed notice (reported
# qualitatively), never a guessed number.
_WORD_DAYS = {
    "five": 5, "ten": 10, "fifteen": 15, "twenty": 20, "thirty": 30,
    "sixty": 60, "ninety": 90, "one hundred twenty": 120,
}
_TERM_END_MARKERS = ("ends on", "before that date", "before the end",
                     "end of the current term")


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
# frozen this milestone (the SEVENTH zero-edit reuse).

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


def parse_nested_marker_map(path, outer, map_key):
    """A nested map of `key: ["m", ...]` (values may wrap) inside a
    convention block -> {key: [markers]}."""
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


def parse_flat_quoted_list(path, key):
    """`key: ["a", "b", ...]` (possibly wrapped) -> [a, b, ...]."""
    lines = _read_lines(path)
    buf, capturing = "", False
    for line in lines:
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
    return re.findall(r'"([^"]+)"', buf)


# ------------------------------------------------------------ narration

def _class_of(entry):
    return (entry.get("source_class") or "PRIMARY").upper()


def _cite(entry):
    tag = " [DERIVED]" if _class_of(entry) == "DERIVED" else ""
    return f"asset {entry['asset_id']}{tag}"


def _source_doc(entry):
    prov = entry.get("provenance") or {}
    return prov.get("source_document") or ""


def default_narrator(finding):
    """Deterministic narration. Every template states what the DOCUMENTS
    show, never the relationship's state, and never restates the
    IMPUTED-HEALTH vocabulary in prose (the quoted claim lives only in
    the quote frame)."""
    kind = finding["finding_kind"]
    if kind == "CUSTOMER_TERM_DEVIATION":
        return (f"Customer {finding['customer']}'s governed agreement deviates "
                f"from the approved standard terms on the {finding['axis']} "
                f"axis. Customer term ({finding['cite']}): "
                f"\"{finding['excerpt']}\". Standard term "
                f"({finding['baseline_cite']}): \"{finding['baseline_excerpt']}\". "
                f"The customer states {finding['customer_values']}; the standard "
                f"states {finding['baseline_values']}. Two approved DOCUMENTS "
                f"differ - this says nothing about whether the deviation helps "
                f"or harms the customer.")
    if kind == "CUSTOMER_RENEWAL_OBLIGATION":
        base = (f"An approved document states a renewal/notice obligation for "
                f"customer {finding['customer']} ({finding['cite']}): "
                f"\"{finding['excerpt']}\".")
        if finding.get("arithmetic"):
            base += f" Declared date arithmetic: {finding['arithmetic']}."
        base += (f" The obligation date {finding['action_date']} falls "
                 f"{finding['days_until']} day(s) from the declared as_of "
                 f"{finding['as_of']} (window {finding['window_days']} days).")
        if finding.get("harvested"):
            base += (" Source is an accepted DERIVED register fact (v2.1) - "
                     "THE THIRD HARVEST, cited BY id, nothing re-extracted.")
        return base + (" This states what the documents OBLIGATE and WHEN - "
                       "never the customer's intent, disposition, or the "
                       "outcome of the renewal.")
    if kind == "CUSTOMER_COVERAGE_GAP":
        return (f"A documented customer obligation ({finding['cite']}, "
                f"coverage_class {finding['coverage_class']}): "
                f"\"{finding['excerpt']}\" has no approved covering procedure - "
                f"the question \"{finding['question']}\" is reproducibly "
                f"refused by the governed corpus. Absence of coverage is the "
                f"finding; this says nothing about whether the customer has "
                f"been affected.")
    if kind == "UNBACKED_HEALTH_ASSUMPTION":
        return (f"An approved document ({finding['cite']}) carries a customer "
                f"relationship-state claim with no governed evidence. The claim "
                f"is quoted verbatim below inside the quote frame. The workbench "
                f"does not adjudicate whether it is true or false; its subject "
                f"matter is Operational Evidence ([OE]) that no governed door "
                f"evidences.")
    return f"Finding of kind {kind}."


PROPOSED_ACTIONS = {
    "CUSTOMER_TERM_DEVIATION": (
        "Review the deviation at the human gate ahead of the renewal or QBR "
        "conversation: accept it as a DERIVED fact about the customer's "
        "governed terms, or reject it with a recorded reason. The workbench "
        "never renegotiates, amends, or approves terms."),
    "CUSTOMER_RENEWAL_OBLIGATION": (
        "Schedule the human renewal/communication preparation for this "
        "obligation. The workbench never renews, notifies, or contacts the "
        "customer, and never states a likelihood of renewal."),
    "CUSTOMER_COVERAGE_GAP": (
        "Create or approve the covering procedure through governed authoring. "
        "The finding states the corpus does not document the coverage - never "
        "that the customer has been harmed (that would require [OE])."),
    "UNBACKED_HEALTH_ASSUMPTION": (
        "Decide at the human gate whether to remove the claim, evidence it "
        "through the governed pipeline, or govern it. The workbench never "
        "validates the claim - its truth is [OE]."),
}


def _sweep_forbidden(text, forbidden):
    """Quote-frame-aware IMPUTED-HEALTH sweep. Every non-quote line
    (a line NOT beginning with the quote prefix) must be free of every
    forbidden phrase; quoted verbatim lines are the sole exemption.
    Returns the offending (phrase, line) or None."""
    for raw in text.splitlines():
        if raw.startswith(QUOTE_PREFIX):
            continue
        low = raw.lower()
        for phrase in forbidden:
            if phrase in low:
                return phrase, raw
    return None


def _proposal_document(finding, agent_principal, binding_id, package_hash,
                       exclusions, workbench_name, forbidden):
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
        f"# {kind.replace('_', ' ').title()} - customer-success finding",
        "",
        "Agent-synthesized finding. This document is a PROPOSAL: it becomes",
        "knowledge only if a human accepts it at the gate, and then as a",
        "DERIVED fact (D29/D30). It states what the governed DOCUMENTS show",
        "about this customer's terms, obligations, and coverage - never the",
        "state, behavior, or future of the customer relationship itself.",
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
    if finding.get("quoted_claim"):
        # THE QUOTE FRAME: the verbatim relationship-state claim, rendered
        # as a blockquote - the sole place the IMPUTED-HEALTH vocabulary
        # may appear, explicitly NOT the workbench's assertion.
        lines += [
            "",
            "## Quoted unsupported claim (THE QUOTE FRAME - verbatim document "
            "text; NOT the workbench's assertion)",
            "",
            f"{QUOTE_PREFIX}\"{finding['quoted_claim']}\"",
            "",
            "The workbench does not adjudicate whether this claim is true; its "
            "subject matter (customer health, adoption, churn, sentiment, or "
            "renewal likelihood) is Operational Evidence ([OE]) that no "
            "governed door evidences.",
        ]
    lines += ["", "## Proposed action", "", PROPOSED_ACTIONS[kind], ""]
    if exclusions:
        lines += ["## What the agent could not see", "",
                  f"Exclusions declared by the gateway: {exclusions}.", ""]
    doc = "\n".join(lines)
    hit = _sweep_forbidden(doc, forbidden)
    if hit:
        raise RuntimeError(
            f"THE IMPUTED HEALTH: forbidden vocabulary {hit[0]!r} appeared "
            f"OUTSIDE the quote frame in a written proposal line: {hit[1]!r} "
            f"- a relationship-state assertion is refused at the source.")
    return doc


# ----------------------------------------------------------- axis helpers

def _axis_values(content, patterns):
    """The declared value patterns over a fact's bytes - verbatim,
    never normalized. Returns a sorted tuple for deterministic display."""
    low = content.lower()
    found = set()
    for pat in patterns:
        for m in re.finditer(pat, low):
            found.add(m.group(0))
    return tuple(sorted(found))


def _notice_days(content):
    """A notice period stated in words -> integer days, or None. Longest
    word phrase first ('one hundred twenty' before 'twenty')."""
    low = content.lower()
    for word in sorted(_WORD_DAYS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(word)} days\b", low):
            return _WORD_DAYS[word]
    return None


# ------------------------------------------------------------ the run

def run_diagnostic(package_path, vault_dir, project_id, agent_principal,
                   binding_id, graph_client, as_of, window_days, customers,
                   domain_prefix="customer_success", answerer=None,
                   narrator=None, backend_dir=None, skills_dir=None,
                   manifest_path=None, requested_skills=None,
                   brief_topic="renewal",
                   workbench_name="customer-success-intelligence"):
    """THE ACTIVE FOUR + the assist brief over the doors, per named
    customer, at a DECLARED as_of + window_days. Returns a run summary:
    proposal paths (one per finding), the review-brief path, the findings,
    and what was skipped (conforming customers, out-of-window obligations,
    covered controls) with the reason."""
    if not as_of or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(as_of)):
        raise RuntimeError(
            "the runner refuses: no as_of declared for the run (expected "
            "YYYY-MM-DD) - the clock is a declared parameter, never sampled.")
    if not isinstance(window_days, int) or window_days <= 0:
        raise RuntimeError(
            "the runner refuses: no positive window_days declared - the "
            "window is a declared parameter, never defaulted.")
    if not customers:
        raise RuntimeError(
            "the runner refuses: no customer declared - the customer is a "
            "declared parameter; the per-customer axis has no default.")
    as_of_date = datetime.date(*(int(p) for p in str(as_of).split("-")))
    window_end = as_of_date + datetime.timedelta(days=window_days)

    for skill_id in (requested_skills or ACTIVE_SKILLS):
        require_ungated(skill_id)

    pc = _import_package_consumer(backend_dir)
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
    dev_path = contracts["detect_customer_term_deviation"]["path"]
    baseline_markers = parse_nested_marker_map(dev_path, "deviation_convention",
                                               "baseline_markers")
    deviation_axes = parse_nested_marker_map(dev_path, "deviation_convention",
                                             "deviation_axes")
    axis_value_patterns = parse_nested_marker_map(
        dev_path, "deviation_convention", "axis_value_patterns")
    std_marker = baseline_markers["standard_terms"][0]

    ren_path = contracts["detect_customer_renewal_obligations"]["path"]
    obligation_markers = parse_flat_quoted_list(ren_path, "obligation_markers")

    cov_path = contracts["detect_customer_coverage_gap"]["path"]
    coverage_markers = parse_nested_marker_map(cov_path, "coverage_convention",
                                               "obligation_markers")

    asm_path = contracts["detect_unbacked_customer_health_assumption"]["path"]
    assumption_markers = parse_flat_quoted_list(asm_path, "assumption_markers")

    proposals_dir = os.path.join(vault_dir, "08_proposals")
    workspace_dir = os.path.join(vault_dir, "07_agent_workspaces")
    for required in (proposals_dir, workspace_dir):
        if not os.path.isdir(required):
            raise RuntimeError(f"{required} missing - bootstrap the vault first.")

    subgraph = graph_client.get_domain_subgraph(project_id, domain_prefix)
    exclusions = {k: v for k, v in (subgraph.get("excluded") or {}).items() if v}

    entries = sorted(knowledge.values(), key=lambda e: e["asset_id"])
    for e in entries:
        e["_content"] = _norm(e.get("content"))

    # Customer attribution: a fact is customer-side for C if its content
    # names C, or it shares a source_document with a fact that names C
    # (so the Acme date sentence, which omits the name, is still Acme's).
    customer_docs = {c: set() for c in customers}
    for e in entries:
        for c in customers:
            if c.lower() in e["_content"].lower():
                customer_docs[c].add(_source_doc(e))

    def customer_of(entry):
        low = entry["_content"].lower()
        doc = _source_doc(entry)
        for c in customers:
            if c.lower() in low or (doc and doc in customer_docs[c]):
                return c
        return None

    baseline_facts = [e for e in entries
                      if std_marker.lower() in e["_content"].lower()]

    findings, skipped = [], []

    def add_finding(finding):
        finding["statement"] = narrator(finding)
        hit = _sweep_forbidden(finding["statement"], forbidden)
        if hit:
            raise RuntimeError(
                f"THE IMPUTED HEALTH: forbidden vocabulary {hit[0]!r} in a "
                f"narration line {hit[1]!r} - refused at the source.")
        findings.append(finding)

    # ---- Walk 1: detect_customer_term_deviation (EXCERPT_BACKED) --------
    # THE BASELINE DOCTRINE: no baseline fact, no deviation. Per customer,
    # per declared axis: if the customer's verbatim axis values differ
    # from the baseline's, a deviation; if identical, SILENCE.
    skill = "detect_customer_term_deviation"
    kind, basis = FINDING_KINDS[skill]
    if not baseline_facts:
        skipped.append({
            "skill": skill,
            "reason": "no approved fact carries the standard-terms baseline "
                      "marker - THE BASELINE DOCTRINE: no standard baseline, "
                      "no deviation diagnosis; the walk refuses, declared."})
    else:
        for c in customers:
            c_facts = [e for e in entries if customer_of(e) == c]
            for axis, axis_marks in deviation_axes.items():
                patterns = axis_value_patterns.get(axis, [])

                def _pick(facts):
                    for e in sorted(facts, key=lambda e: e["asset_id"]):
                        low = e["_content"].lower()
                        if any(mk in low for mk in axis_marks):
                            vals = _axis_values(e["_content"], patterns)
                            if vals:
                                return e, vals
                    return None, ()

                base_e, base_vals = _pick(baseline_facts)
                cust_e, cust_vals = _pick(c_facts)
                if not (base_vals and cust_vals):
                    continue
                if cust_vals == base_vals:
                    skipped.append({
                        "skill": skill,
                        "reason": f"{c} conforms to the standard on the {axis} "
                                  f"axis ({list(cust_vals)}) - conformance is "
                                  f"SILENCE, never a finding"})
                    continue
                add_finding({
                    "skill": skill, "finding_kind": kind,
                    "evidence_basis": basis, "customer": c, "axis": axis,
                    "asset_id": cust_e["asset_id"], "cite": _cite(cust_e),
                    "excerpt": _excerpt(cust_e["_content"]),
                    "baseline_cite": _cite(base_e),
                    "baseline_excerpt": _excerpt(base_e["_content"]),
                    "customer_values": list(cust_vals),
                    "baseline_values": list(base_vals),
                    "cited_assets": sorted({cust_e["asset_id"],
                                            base_e["asset_id"]}),
                    "evidence_lines": [
                        f"Customer term (verbatim): {_cite(cust_e)} - "
                        f"\"{_excerpt(cust_e['_content'])}\"",
                        f"Standard term (verbatim): {_cite(base_e)} - "
                        f"\"{_excerpt(base_e['_content'])}\"",
                        f"Axis: {axis} - customer states {list(cust_vals)}, "
                        f"standard states {list(base_vals)} (values verbatim, "
                        f"never normalized; document-vs-document)",
                    ],
                })

    # ---- Walk 2: detect_customer_renewal_obligations (EXCERPT_BACKED) ----
    # THE THIRD HARVEST: DERIVED register facts flow through this walk and
    # are cited AS DERIVED. Dated obligations get a declared-clock window;
    # a term-end + a notice period co-located in one fact yields declared
    # date arithmetic. Out-of-window -> a covered control, no finding.
    skill = "detect_customer_renewal_obligations"
    kind, basis = FINDING_KINDS[skill]
    date_re = re.compile(r"(\d{4}-\d{2}-\d{2})")
    for entry in entries:
        content = entry["_content"]
        low = content.lower()
        if not any(mk in low for mk in obligation_markers):
            continue
        m = date_re.search(content)
        if not m:
            continue   # dateless obligations are out of THE THIRD HARVEST scope
        stated = datetime.date(*(int(p) for p in m.group(1).split("-")))
        harvested = _class_of(entry) == "DERIVED"
        c = customer_of(entry)
        if c is None and not harvested:
            continue
        notice = _notice_days(content)
        arithmetic = None
        action_date = stated
        if notice is not None and any(k in low for k in _TERM_END_MARKERS):
            action_date = stated - datetime.timedelta(days=notice)
            arithmetic = (f"{m.group(1)} - {notice} days = "
                          f"{action_date.isoformat()} (date arithmetic over "
                          f"the verbatim term-end date and notice period)")
        days_until = (action_date - as_of_date).days
        if not (as_of_date <= action_date <= window_end):
            skipped.append({
                "skill": skill,
                "reason": f"asset {entry['asset_id']}"
                          + (f" ({c})" if c else "")
                          + f": the obligation date {action_date.isoformat()} "
                          f"is outside the declared window [{as_of}, "
                          f"{window_end.isoformat()}] - a covered control, no "
                          f"finding"})
            continue
        lines = [
            f"Obligation excerpt (verbatim): {_cite(entry)} - "
            f"\"{_excerpt(content)}\"",
            f"Stated date (verbatim): {m.group(1)}",
        ]
        if arithmetic:
            lines.append(f"Declared arithmetic: {arithmetic}")
        lines.append(
            f"Window: {action_date.isoformat()} is {days_until} day(s) from "
            f"as_of {as_of} (window {window_days}d, end "
            f"{window_end.isoformat()}) - date arithmetic only")
        if harvested:
            lines.append("Source is an accepted DERIVED register fact (v2.1) "
                         "- THE THIRD HARVEST, cited BY id, nothing "
                         "re-extracted")
        add_finding({
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "customer": c or "(register-declared)", "asset_id": entry["asset_id"],
            "cite": _cite(entry), "excerpt": _excerpt(content),
            "arithmetic": arithmetic, "action_date": action_date.isoformat(),
            "days_until": days_until, "as_of": str(as_of),
            "window_days": window_days, "harvested": harvested,
            "cited_assets": [entry["asset_id"]], "evidence_lines": lines,
        })

    # ---- Walk 3: detect_customer_coverage_gap (REFUSAL_BACKED) -----------
    # On the per-customer axis: a customer-side obligation carrying a
    # class marker, with no approved covering material. Coverage = an
    # approved fact carrying the marker that is NOT customer-side (a
    # shared procedure, not a per-customer promise) and NOT a deferral
    # (it describes the mechanics rather than pointing at them). An
    # obligation with no such coverage is a gap; a covered obligation
    # stays silent (escalation, whose procedure exists).
    skill = "detect_customer_coverage_gap"
    kind, basis = FINDING_KINDS[skill]
    deferrals = ("must follow", "shall follow", "in accordance with",
                 "shall conduct", "shall deliver", "must be notified",
                 "include", "guaranteed", "as agreed")
    coverage_questions = {
        "qbr_procedure": "Which approved procedure documents how the quarterly "
                         "business review is run?",
        "playbook": "Which approved playbook covers this obligation?",
        "escalation": "Which approved procedure documents the escalation path?",
        "delivery_process": "Which approved process documents the delivery of "
                            "this outcome?",
        "service_commitment_evidence": "Which approved evidence documents this "
                                       "service commitment?",
    }
    for cls, marks in coverage_markers.items():
        obligations, coverage = [], []
        for e in entries:
            low = e["_content"].lower()
            if not any(mk in low for mk in marks):
                continue
            if customer_of(e) is not None:
                obligations.append(e)          # a per-customer obligation
            elif not any(d in low for d in deferrals):
                coverage.append(e)             # shared procedure/mechanics
        if obligations and not coverage:
            obligations.sort(key=lambda e: e["asset_id"])
            primary = obligations[0]
            add_finding({
                "skill": skill, "finding_kind": kind, "evidence_basis": basis,
                "coverage_class": cls, "asset_id": primary["asset_id"],
                "cite": _cite(primary), "excerpt": _excerpt(primary["_content"]),
                "question": coverage_questions.get(
                    cls, f"Which approved material covers the {cls} obligation?"),
                "cited_assets": sorted(e["asset_id"] for e in obligations),
                "evidence_lines": [
                    f"Obligation excerpt (verbatim): {_cite(primary)} - "
                    f"\"{_excerpt(primary['_content'])}\"",
                    f"Coverage class: {cls}",
                    f"Obligation facts (cited): "
                    f"{sorted(e['asset_id'] for e in obligations)}",
                    f"Reproducible refusal: the governed corpus offers no "
                    f"approved procedure for this obligation",
                ],
            })

    # ---- Walk 4: detect_unbacked_customer_health_assumption -------------
    # A relationship-state claim inside an approved document, surfaced
    # VERBATIM inside THE QUOTE FRAME as an unsupported assumption - never
    # adjudicated. The quoted claim is the ONLY place forbidden vocabulary
    # may appear (rendered as a blockquote by _proposal_document).
    skill = "detect_unbacked_customer_health_assumption"
    kind, basis = FINDING_KINDS[skill]
    for entry in entries:
        content = entry["_content"]
        low = content.lower()
        fired = [mk for mk in assumption_markers if mk in low]
        if not fired:
            continue
        c = customer_of(entry)
        add_finding({
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "customer": c or "(unnamed)", "asset_id": entry["asset_id"],
            "cite": _cite(entry), "quoted_claim": _excerpt(content, 300),
            "marker_count": len(fired),
            "cited_assets": [entry["asset_id"]],
            "evidence_lines": [
                f"Claim source (cited): {_cite(entry)}"
                + (f" - customer {c}" if c else ""),
                f"The document carries {len(fired)} relationship-state "
                f"claim marker(s); the verbatim claim is quoted below in the "
                f"quote frame (never restated as the workbench's assertion)",
                "No governed evidence backs the claim; its subject matter is "
                "[OE] (usage / adoption / churn / satisfaction / renewal "
                "likelihood) that no governed door evidences",
            ],
        })

    # ---- One proposal document per finding -------------------------------
    proposal_paths = []
    for finding in findings:
        content = _proposal_document(finding, agent_principal, binding_id,
                                     package_hash, exclusions, workbench_name,
                                     forbidden)
        proposal_paths.append(_write(proposals_dir,
                                     f"{workbench_name}-{finding['skill']}",
                                     content))

    # ---- prepare_customer_success_review_brief (assist, 07 only) ---------
    def kind_findings(k):
        return [f for f in findings if f["finding_kind"] == k]

    brief = [
        f"# Customer success review brief - {brief_topic}",
        "",
        f"Declared clock: as_of {as_of} - window {window_days} days. "
        f"Customers: {', '.join(customers)}.",
        "Internal assist output (prepare_customer_success_review_brief,",
        "[assist, synth]). NOT a proposal: this brief never enters knowledge",
        "and is never written to /08_proposals. Every statement is cited;",
        "narrative framing is SYNTHESIS_INFERRED. It NARRATES governed facts",
        "and quoted assumptions - it never assesses the relationship, ranks a",
        "customer, or states a renewal likelihood.",
        "",
        "## Customer terms & deviations (cited)",
        "",
    ]
    brief += [f"- {f['customer']} [{f['axis']}]: {f['cite']} vs "
              f"{f['baseline_cite']} - customer {f['customer_values']}, "
              f"standard {f['baseline_values']}"
              for f in kind_findings("CUSTOMER_TERM_DEVIATION")] \
        or ["- (no deviation found - a conforming customer is silent here)"]
    brief += ["", "## Renewal & communication windows (declared clock, cited)", ""]
    brief += [f"- {f['customer']}: {f['cite']} -> action date "
              f"{f['action_date']} ({f['days_until']}d from as_of)"
              + (f"; {f['arithmetic']}" if f.get("arithmetic") else "")
              for f in kind_findings("CUSTOMER_RENEWAL_OBLIGATION")] \
        or ["- (no obligation inside the declared window)"]
    brief += ["", "## Coverage gaps (refusal-backed, cited)", ""]
    brief += [f"- {f['coverage_class']}: {f['cite']} - \"{f['excerpt']}\""
              for f in kind_findings("CUSTOMER_COVERAGE_GAP")] \
        or ["- (no coverage gap found)"]
    brief += ["", "## Escalation rules as documented (cited)", ""]
    esc_docs = [e for e in entries
                if "escalation" in e["_content"].lower()
                and "procedure" in (_source_doc(e) or "").lower()]
    brief += [f"- {_cite(e)}: \"{_excerpt(e['_content'])}\"" for e in esc_docs] \
        or ["- (no governed escalation procedure in scope)"]
    brief += ["", "## Unbacked assumptions (quoted; never adjudicated)", ""]
    for f in kind_findings("UNBACKED_HEALTH_ASSUMPTION"):
        # THE QUOTE FRAME inside the brief: the verbatim claim as a
        # blockquote, exempt from the sweep; the workbench's own line clean.
        brief.append(f"- {f['cite']} carries an unsupported relationship-state "
                     f"claim (quoted verbatim, not adjudicated):")
        brief.append(f"{QUOTE_PREFIX}\"{f['quoted_claim']}\"")
    if not kind_findings("UNBACKED_HEALTH_ASSUMPTION"):
        brief.append("- (no unbacked relationship-state claim found)")
    brief += [
        "", "## Exclusions & refusals", "",
        "- Customer usage, activity, tickets, NPS, CRM state, sentiment, "
        "adoption, churn probability, renewal likelihood, revenue-at-risk, and "
        "customer ranking are Operational Evidence ([OE]) and are refused - "
        "this brief cannot and does not report them.",
        f"- Gateway exclusions: {exclusions or 'none declared'}.",
        "",
    ]
    brief_text = "\n".join(brief)
    hit = _sweep_forbidden(brief_text, forbidden)
    if hit:
        raise RuntimeError(
            f"THE IMPUTED HEALTH: forbidden vocabulary {hit[0]!r} outside the "
            f"quote frame in the review brief: {hit[1]!r} - refused.")
    brief_path = _write(workspace_dir,
                        f"{workbench_name}-review-brief", brief_text)

    return {"proposals": sorted(proposal_paths), "brief": brief_path,
            "findings": findings, "skipped": skipped, "exclusions": exclusions,
            "as_of": str(as_of), "window_days": window_days,
            "customers": list(customers),
            "contracts": {s: contracts[s]["path"] for s in ACTIVE_SKILLS}}
