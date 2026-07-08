"""Procurement Document Intelligence Workbench runner - the v1.8
reference consumer.

Canonical workbench #3 in the catalog. The runner is a consumer, never
a subsystem (D22): its only doors are the .empkg via
app.package_consumer, the MCP gateway as a real client at a real AGENT
token's clearance, and file writes into the vault - one proposal per
finding into /08_proposals, the renegotiation brief into
/07_agent_workspaces. Guard 5 sweeps this module the moment it exists.
Built on workbench/common.py (the ruling-6 shared plumbing, reached by
relative import so the reuse stays inside the swept root).

THE SENSITIVITY POSTURE (the cardinal sin): THE INVENTED NUMBER. The
runner may quote clause numbers, percentages, dates, notice periods,
and money figures only when verbatim present in governed evidence, and
may compute date windows only from verbatim-extracted dates at the
declared as_of clock. It never estimates spend, infers market rates,
converts a paraphrased quantity ("one fifth") into a number, rounds,
normalizes, extrapolates, or invents a figure, and it refuses
unparseable dates rather than guessing. The manifest's
forbidden_vocabulary is enforced HERE, on every finding statement,
before anything is written.

The runner HONORS the six skill contracts, not just carries them:
markers, term classes, the date convention, increase markers, the
certification requirement + question template, and the named policy
are READ FROM the contract files (skills/*.yaml), never hardcoded; a
skill whose contract is not status: ACTIVE is refused; the gated list
([OE]/[ES]) is refused live naming the unminted decision; refusal-first
cuts both ways (a contract outside the window, a certification that
exists with supplier-named coverage, a conforming policy → NO finding,
declared in `skipped`).

Two injectable seams, as in v1.6/v1.7: `answerer` (real =
package_consumer.consume through the D19 resolver; CI = the declared
deterministic contract-follower) and `narrator` (default =
deterministic templates; the real-model run overrides it). Whatever
narrates, every finding cites the governed evidence it rests on: no
evidence, no finding. DERIVED evidence is cited AS DERIVED.
"""
import os
import re

from ..common import (
    import_package_consumer as _import_package_consumer,
    excerpt as _excerpt,
    overlap as _overlap,
    subject_tokens as _subject_tokens,
    load_active_contracts,
    StdioMcpGraphClient,       # noqa: F401 - the real-run transport, re-exported
    write_hashed as _write,
    SAME_SUBJECT_MINIMUM,
)

ACTIVE_SKILLS = (
    "extract_vendor_terms",
    "detect_renewal_window",
    "detect_price_increase_clauses",
    "identify_missing_supplier_certifications",
    "detect_vendor_policy_conflict",
    "prepare_renegotiation_brief",
)

FINDING_KINDS = {
    "extract_vendor_terms": ("VENDOR_TERM", "EXCERPT_BACKED"),
    "detect_renewal_window": ("RENEWAL_WINDOW", "EXCERPT_BACKED"),
    "detect_price_increase_clauses": ("PRICE_INCREASE_CLAUSE", "EXCERPT_BACKED"),
    "identify_missing_supplier_certifications": ("MISSING_SUPPLIER_CERTIFICATION", "REFUSAL_BACKED"),
    "detect_vendor_policy_conflict": ("VENDOR_POLICY_CONFLICT", "CONFLICT_BACKED"),
}

REFUSAL_MARKER = "INSUFFICIENT EVIDENCE"

# THE GATED LIST (the v1.8 WS0 ruling; mirrored from the manifest's
# refused_until_minted + the calendar refusal ruling 4). Tags are gates:
# the runner refuses each at runtime, naming the unminted decision.
GATED_SKILLS = {
    "compare_contract_pricing_vs_invoices": "the Operational Evidence Realm",
    "compare_sla_obligations_vs_service_records": "the Operational Evidence Realm",
    "detect_vendor_usage_vs_license_count": "the Operational Evidence Realm",
    "detect_supplier_performance_gaps": "the Operational Evidence Realm",
    "identify_owner_gaps": "Exception Stewardship",
    # the calendar refusal (ruling 4): recurrence/persistent-calendar
    # skills stay refused - point-in-time window detection only.
    "track_recurrence_rules": "the persistent-calendar refusal (ruling 4)",
    "generate_renewal_calendar": "the persistent-calendar refusal (ruling 4)",
    # SEQUENCED (ruling 3): cross-document counting is out of this
    # milestone's evidence rules.
    "detect_single_supplier_dependency": "the SEQUENCED cross-document counting rule (ruling 3)",
    "propose_vendor_consolidation": "the SEQUENCED cross-document counting rule (ruling 3)",
}


def require_ungated(skill_id):
    if skill_id in GATED_SKILLS:
        raise RuntimeError(
            f"Skill {skill_id} is gated: {GATED_SKILLS[skill_id]} is not "
            f"minted - the runner refuses the task and names the gate.")


def _norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _sentences(text):
    return [t.strip() for t in re.split(r"(?<=[.;])\s+", _norm(text)) if t.strip()]


# ------------------------------------------------ contract-field parsing
# Contract-declared conventions are parsed from the ratified YAMLs (the
# doors allow no YAML library). Self-contained here so workbench/common.py
# stays frozen this milestone (the WS2 industrialization ruling); a future
# cleanup could lift shared parsers into common.

def _read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def _block(lines, key, indent=0):
    """The raw block under `key:` at the given indent (list/nested bodies)."""
    out, capturing = [], False
    prefix = " " * indent
    for line in lines:
        if line.startswith(f"{prefix}{key}:") and (indent == 0 or line[:indent].isspace()):
            capturing = True
            continue
        if capturing:
            if line.strip().startswith("#") or not line.strip():
                continue
            if line and not line[indent:indent + 1].isspace() and not line.startswith(" " * (indent + 1)):
                break
            out.append(line)
    return out


def parse_quoted_list(path, key, indent=0):
    values = []
    for line in _block(_read_lines(path), key, indent):
        s = line.strip()
        if s.startswith("- "):
            values.append(s[2:].strip().strip('"'))
    return values


def parse_rule_lines(path, key):
    rules, default = [], None
    for line in _block(_read_lines(path), key):
        s = line.strip()
        if not s.startswith("- ") or "->" not in s:
            continue
        lhs, target = s[2:].rsplit("->", 1)
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
    lowered = (text or "").lower()
    for needles, target in rules:
        if any(n in lowered for n in needles):
            return target
    return default


def parse_scalar(path, key):
    for line in _read_lines(path):
        s = line.strip()
        if s.startswith(f"{key}:"):
            return s.split(":", 1)[1].strip().strip('"')
    return None


def parse_marker_pattern(path):
    """The declared date_convention.marker_pattern - a quoted, possibly
    wrapped regex whose YAML escaping (\\\\d) unwraps to \\d."""
    lines = _read_lines(path)
    block = _block(lines, "date_convention")
    raw, capturing = [], False
    for line in block:
        s = line.strip()
        if s.startswith("marker_pattern:"):
            raw.append(s.split(":", 1)[1].strip())
            capturing = not raw[-1].endswith('"')
        elif capturing:
            raw.append(s)
            if s.endswith('"'):
                capturing = False
    pattern = " ".join(raw).strip().strip('"').replace("\\\\", "\\")
    if not pattern:
        raise RuntimeError(f"{path}: date_convention declares no marker_pattern")
    return re.compile(pattern)


def parse_nested_quoted_list(path, outer, inner):
    block = _block(_read_lines(path), outer)
    values, capturing = [], False
    for line in block:
        s = line.strip()
        if s.startswith(f"{inner}:"):
            capturing = True
            continue
        if capturing:
            if s.startswith("- "):
                values.append(s[2:].strip().strip('"'))
            elif s and not s.startswith("#"):
                break
    return values


def parse_forbidden_vocabulary(manifest_path):
    return [v.lower() for v in parse_quoted_list(manifest_path, "forbidden_vocabulary")]


def parse_requirement_convention(path):
    block = _block(_read_lines(path), "requirement_convention")
    out = {}
    key, buf = None, []
    for line in block:
        s = line.strip()
        m = re.match(r"(\w+):\s*(.*)", s)
        if m and m.group(1) in ("requirement_trigger", "scope_trigger",
                                "question_template"):
            if key:
                out[key] = _norm(" ".join(buf)).strip('"')
            key, buf = m.group(1), [m.group(2)]
        elif key:
            buf.append(s)
    if key:
        out[key] = _norm(" ".join(buf)).strip('"')
    return out


# ------------------------------------------------------------ narration

def _class_of(entry):
    return (entry.get("source_class") or "PRIMARY").upper()


def _cite(entry):
    tag = " [DERIVED]" if _class_of(entry) == "DERIVED" else ""
    return f"asset {entry['asset_id']}{tag}"


def default_narrator(finding):
    """Deterministic narration. Every template states DOCUMENTATION status,
    never practice, and never adds a number of its own (THE INVENTED
    NUMBER posture)."""
    kind = finding["finding_kind"]
    if kind == "VENDOR_TERM":
        return (f"An approved vendor document states an explicit term "
                f"({finding['cite']}, term_class {finding['term_class']}): "
                f"\"{finding['excerpt']}\". This is what the contract binds "
                f"- extraction states documentation, never performance.")
    if kind == "RENEWAL_WINDOW":
        auto = (f" An auto-renewal clause applies: "
                f"\"{finding['auto_renewal_excerpt']}\"."
                if finding.get("auto_renewal_excerpt") else "")
        return (f"A governed vendor contract ({finding['cite']}) carries an "
                f"explicit dated term inside the declared window: "
                f"\"{finding['excerpt']}\". At the declared as_of "
                f"{finding['as_of']} with window {finding['window_days']} "
                f"days, that date is {finding['days_until']} days away (date "
                f"arithmetic only).{auto} A human schedules the renewal "
                f"decision; the workbench never renews or notifies.")
    if kind == "PRICE_INCREASE_CLAUSE":
        note = (" The quantity is stated in words, not a figure - it is "
                "quoted as text and never converted to a number."
                if finding.get("non_numeric") else "")
        return (f"A governed vendor contract ({finding['cite']}) contains a "
                f"price-adjustment clause: \"{finding['excerpt']}\".{note} A "
                f"human reviews the clause before renewal.")
    if kind == "MISSING_SUPPLIER_CERTIFICATION":
        return (f"An approved policy requires a certification "
                f"({finding['requirement_cite']}: "
                f"\"{finding['requirement_excerpt']}\") for {finding['supplier']}, "
                f"who is documented in scope ({finding['scope_cite']}), but the "
                f"governed corpus cannot produce the certificate - the "
                f"question \"{finding['question']}\" is reproducibly refused. "
                f"The documents do not evidence the certification; this says "
                f"nothing about the supplier's certification in the world.")
    if kind == "VENDOR_POLICY_CONFLICT":
        return (f"A vendor contract term and the {finding['named_policy']} "
                f"oblige incompatible handling of the same subject: "
                f"{finding['cite_contract']} states \"{finding['excerpt_contract']}\" "
                f"while {finding['cite_policy']} states "
                f"\"{finding['excerpt_policy']}\". Until a human reconciles "
                f"them, the governed corpus carries both.")
    return f"Finding of kind {kind}."


PROPOSED_ACTIONS = {
    "VENDOR_TERM": (
        "Review the extracted term at the human gate: accept it as a "
        "DERIVED vendor-term fact or reject it with a recorded reason. An "
        "accepted term becomes a governed input for later diagnosis "
        "(composition across the valve)."),
    "RENEWAL_WINDOW": (
        "Schedule the renewal decision through the human workflow before "
        "the dated deadline. The finding is a point-in-time diagnosis at "
        "the declared as_of - not a calendar, not a recurring reminder."),
    "PRICE_INCREASE_CLAUSE": (
        "Review the price-adjustment clause before the next renewal. The "
        "finding quotes the clause; it never estimates the resulting "
        "spend or a market comparison."),
    "MISSING_SUPPLIER_CERTIFICATION": (
        "Obtain or ingest the supplier certificate through the governed "
        "pipeline. The finding states the governed corpus does not hold "
        "the certificate - never that the supplier is uncertified in the "
        "world."),
    "VENDOR_POLICY_CONFLICT": (
        "A human reconciles the two statements - renegotiate the term or "
        "amend the policy through the governed workflow; the workbench "
        "never picks the surviving side."),
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
        f"# {kind.replace('_', ' ').title()} - procurement finding",
        "",
        "Agent-synthesized finding. This document is a PROPOSAL: it becomes",
        "knowledge only if a human accepts it at the gate, and then as a",
        "DERIVED fact (D29/D30). Every number and date in it is quoted",
        "verbatim from a governed clause - the workbench invents no figure.",
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
                   binding_id, graph_client, as_of, window_days,
                   domain_prefix="procurement", answerer=None, narrator=None,
                   backend_dir=None, skills_dir=None, manifest_path=None,
                   requested_skills=None, brief_vendor="CloudHost",
                   persistent_calendar=False,
                   workbench_name="procurement-intelligence"):
    """The six ratified skills over the doors, at a DECLARED as_of +
    window_days. Returns a run summary: proposal paths (one per finding),
    the renegotiation brief path, the findings, and what was skipped with
    the refusing reason."""
    import datetime

    # The declared clock: as_of + window_days are run parameters, never
    # wall-clock, never defaulted.
    if not as_of or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(as_of)):
        raise RuntimeError(
            "detect_renewal_window refuses: no as_of declared for the run "
            "(expected YYYY-MM-DD) - the clock is a declared parameter, "
            "never sampled.")
    if not isinstance(window_days, int) or window_days <= 0:
        raise RuntimeError(
            "detect_renewal_window refuses: no positive window_days declared "
            "- the window is a declared parameter, never defaulted.")
    if persistent_calendar:
        raise RuntimeError(
            "the runner refuses a persistent renewal calendar / recurrence "
            "tracker (ruling 4): only point-in-time window detection at the "
            "declared as_of is allowed - a persistent calendar is the "
            "two-state-machine drift D1 names.")
    as_of_date = datetime.date(*(int(p) for p in str(as_of).split("-")))
    window_end = as_of_date + datetime.timedelta(days=window_days)

    for skill_id in (requested_skills or ACTIVE_SKILLS):
        require_ungated(skill_id)

    pc = _import_package_consumer(backend_dir)
    package = pc.load_package(package_path)   # verifies the hash chain
    package_hash = package["package_hash"]
    expert_model_id = package["manifest"]["expert_model_id"]
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
    markers = parse_quoted_list(
        contracts["extract_vendor_terms"]["path"], "explicit_markers")
    marker_re = re.compile(
        r"(?:" + "|".join(re.escape(m) for m in markers) + r")")
    term_rules = parse_rule_lines(
        contracts["extract_vendor_terms"]["path"], "term_class_rules")
    date_re = parse_marker_pattern(contracts["detect_renewal_window"]["path"])
    auto_markers = [m.lower() for m in parse_nested_quoted_list(
        contracts["detect_renewal_window"]["path"], "date_convention",
        "auto_renewal_markers")]
    renewal_context = [m.lower() for m in parse_nested_quoted_list(
        contracts["detect_renewal_window"]["path"], "date_convention",
        "renewal_context_markers")]
    increase_markers = [m.lower() for m in parse_quoted_list(
        contracts["detect_price_increase_clauses"]["path"], "increase_markers")]
    pct_re = re.compile(r"\d+(?:\.\d+)?\s?%")
    req = parse_requirement_convention(
        contracts["identify_missing_supplier_certifications"]["path"])
    named_policy = parse_scalar(
        contracts["detect_vendor_policy_conflict"]["path"], "named_policy")
    boilerplate = frozenset(
        w.lower() for w in parse_quoted_list(
            contracts["detect_vendor_policy_conflict"]["path"],
            "subject_boilerplate_stopwords"))

    def shared_subject_ex(a, b):
        """The inherited v1.6 same-subject overlap, minus the contract's
        declared boilerplate stopwords (the ruling-6 doc-vs-named-policy
        refinement: legal boilerplate is not subject matter)."""
        return len((_subject_tokens(a) - boilerplate)
                   & (_subject_tokens(b) - boilerplate))

    proposals_dir = os.path.join(vault_dir, "08_proposals")
    workspace_dir = os.path.join(vault_dir, "07_agent_workspaces")
    for required in (proposals_dir, workspace_dir):
        if not os.path.isdir(required):
            raise RuntimeError(f"{required} missing - bootstrap the vault first.")

    subgraph = graph_client.get_domain_subgraph(project_id, domain_prefix)
    exclusions = {k: v for k, v in (subgraph.get("excluded") or {}).items() if v}

    findings, skipped = [], []
    entries = sorted(knowledge.values(), key=lambda e: e["asset_id"])

    def doc_of(entry):
        return _norm((entry.get("provenance") or {}).get("source_document") or "")

    def check_posture(statement):
        lowered = statement.lower()
        for phrase in forbidden:
            if phrase in lowered:
                raise RuntimeError(
                    f"THE INVENTED NUMBER: forbidden vocabulary {phrase!r} in "
                    f"a finding statement - numeric overclaiming is refused at "
                    f"the source.")

    def add_finding(finding):
        finding["statement"] = narrator(finding)
        check_posture(finding["statement"])
        findings.append(finding)

    # ---- Walk 1: extract_vendor_terms (EXCERPT_BACKED) ------------------
    skill = "extract_vendor_terms"
    kind, basis = FINDING_KINDS[skill]
    for entry in entries:
        content = _norm(entry.get("content"))
        if not marker_re.search(content):
            continue
        term_class = apply_rules(*term_rules, content)
        add_finding({
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "asset_id": entry["asset_id"], "cite": _cite(entry),
            "excerpt": _excerpt(content), "term_class": term_class,
            "cited_assets": [entry["asset_id"]],
            "evidence_lines": [
                f"Term excerpt (verbatim): {_cite(entry)} - \"{_excerpt(content)}\"",
                f"Term class: {term_class} (the declared excerpt keyword "
                f"rules; UNCLASSIFIED is honest, never guessed)",
                f"Explicit marker required: {'|'.join(markers)} - a sentence "
                f"without a marker is never extracted",
            ],
        })

    # ---- Walk 2: detect_renewal_window (EXCERPT_BACKED, date arithmetic) -
    skill = "detect_renewal_window"
    kind, basis = FINDING_KINDS[skill]
    # group auto-renewal evidence by source document (extraction may split
    # the dated clause and the auto-renewal clause into separate assets).
    auto_by_doc = {}
    for entry in entries:
        content = _norm(entry.get("content"))
        if any(m in content.lower() for m in auto_markers):
            auto_by_doc.setdefault(doc_of(entry), entry)
    dated_docs = set()
    for entry in entries:
        content = _norm(entry.get("content"))
        m = date_re.search(content)
        if m:
            dated_docs.add(doc_of(entry))
            date_str = m.group(2)
            d = datetime.date(*(int(p) for p in date_str.split("-")))
            days_until = (d - as_of_date).days
            if as_of_date <= d <= window_end:
                auto = auto_by_doc.get(doc_of(entry))
                lines = [
                    f"Dated term (verbatim): {_cite(entry)} - \"{_excerpt(content)}\"",
                    f"Declared clock: as_of {as_of}, window {window_days} days "
                    f"(window end {window_end.isoformat()}) - a run parameter, "
                    f"never wall-clock",
                    f"Computed days-until: {days_until} (date arithmetic over "
                    f"the verbatim date only - the sole computed value)",
                ]
                if auto:
                    lines.append(
                        f"Auto-renewal clause (verbatim): {_cite(auto)} - "
                        f"\"{_excerpt(_norm(auto.get('content')))}\"")
                add_finding({
                    "skill": skill, "finding_kind": kind, "evidence_basis": basis,
                    "asset_id": entry["asset_id"], "cite": _cite(entry),
                    "excerpt": _excerpt(content), "as_of": str(as_of),
                    "window_days": window_days, "days_until": days_until,
                    "auto_renewal_excerpt": (_excerpt(_norm(auto.get("content")))
                                             if auto else None),
                    "cited_assets": sorted({entry["asset_id"]}
                                           | ({auto["asset_id"]} if auto else set())),
                    "evidence_lines": lines,
                })
            else:
                skipped.append({
                    "skill": skill,
                    "reason": f"asset {entry['asset_id']}: the dated term "
                              f"({date_str}) is outside the declared window "
                              f"[{as_of}, {window_end.isoformat()}] - a covered "
                              f"control, no finding"})
    # the unparseable-date refusal: a renewal-context document with NO
    # parseable date is refused, declared - never guessed.
    ctx_docs = {}
    for entry in entries:
        content = _norm(entry.get("content"))
        if any(c in content.lower() for c in renewal_context) and not date_re.search(content):
            ctx_docs.setdefault(doc_of(entry), entry)
    for doc, entry in sorted(ctx_docs.items()):
        if doc in dated_docs:
            continue
        skipped.append({
            "skill": skill,
            "reason": f"asset {entry['asset_id']} ({doc}): renewal-context "
                      f"language with no parseable date under the declared "
                      f"marker pattern - REFUSED, declared (the clock is never "
                      f"guessed)"})

    # ---- Walk 3: detect_price_increase_clauses (EXCERPT_BACKED) ---------
    skill = "detect_price_increase_clauses"
    kind, basis = FINDING_KINDS[skill]
    for entry in entries:
        content = _norm(entry.get("content"))
        if not any(mk in content.lower() for mk in increase_markers):
            continue
        non_numeric = not pct_re.search(content)
        add_finding({
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "asset_id": entry["asset_id"], "cite": _cite(entry),
            "excerpt": _excerpt(content), "non_numeric": non_numeric,
            "cited_assets": [entry["asset_id"]],
            "evidence_lines": [
                f"Price-adjustment clause (verbatim): {_cite(entry)} - "
                f"\"{_excerpt(content)}\"",
                ("The quantity is stated in words - quoted as text, "
                 "non_numeric: true; never converted to a number"
                 if non_numeric else
                 "The percentage is quoted verbatim from the clause; the "
                 "finding adds no number of its own"),
            ],
        })

    # ---- Walk 4: identify_missing_supplier_certifications (REFUSAL) -----
    skill = "identify_missing_supplier_certifications"
    kind, basis = FINDING_KINDS[skill]
    req_entries = [e for e in entries
                   if req.get("requirement_trigger", "").lower()
                   in _norm(e.get("content")).lower()]
    scope_re = re.compile(r"([A-Z][A-Za-z0-9]+)\s+" +
                          re.escape(req.get("scope_trigger", "processes customer data")))
    if req_entries:
        req_entry = req_entries[0]
        seen_suppliers = set()
        for entry in entries:
            content = _norm(entry.get("content"))
            sm = scope_re.search(content)
            if not sm:
                continue
            supplier = sm.group(1)
            if supplier in seen_suppliers:
                continue
            seen_suppliers.add(supplier)
            question = req.get("question_template", "").replace(
                "{supplier}", supplier)
            result = answerer(question)
            answer = result.get("answer") or ""
            covered = (REFUSAL_MARKER not in answer
                       and supplier.lower() in _norm(answer).lower())
            if covered:
                skipped.append({
                    "skill": skill,
                    "reason": f"{supplier}: an approved document names the "
                              f"certificate - the corpus answers "
                              f"\"{question}\" with supplier-named evidence; a "
                              f"covered control, no finding"})
                continue
            add_finding({
                "skill": skill, "finding_kind": kind, "evidence_basis": basis,
                "supplier": supplier, "question": question,
                "requirement_cite": _cite(req_entry),
                "requirement_excerpt": _excerpt(_norm(req_entry.get("content"))),
                "scope_cite": _cite(entry),
                "cited_assets": sorted({req_entry["asset_id"], entry["asset_id"]}),
                "evidence_lines": [
                    f"Requirement (verbatim): {_cite(req_entry)} - "
                    f"\"{_excerpt(_norm(req_entry.get('content')))}\"",
                    f"Supplier in scope (verbatim): {_cite(entry)} - "
                    f"\"{_excerpt(content)}\"",
                    f"Reproducible refusal: \"{question}\" -> the packaged "
                    f"answering contract returned INSUFFICIENT EVIDENCE "
                    f"(SUPPLIER-NAMED COVERAGE: another supplier's certificate "
                    f"is never evidence)",
                ],
            })

    # ---- Walk 5: detect_vendor_policy_conflict (CONFLICT_BACKED) --------
    skill = "detect_vendor_policy_conflict"
    kind, basis = FINDING_KINDS[skill]
    policy_docs = {doc_of(e) for e in entries
                   if "procurement policy" in doc_of(e).replace("-", " ").lower()
                   or "procurement-policy" in doc_of(e).lower()}
    conflict_payload = graph_client.get_conflicts(expert_model_id)
    pairs = sorted((r for r in conflict_payload["relationships"]
                    if r["relationship_type"] == "CONFLICTS_WITH"
                    and r["classification"] == "DIRECT_CONTRADICTION"
                    and r["status"] in ("DETECTED", "CONFIRMED")),
                   key=lambda r: r["id"])
    for rel in pairs:
        a_id, b_id = rel["source_asset_id"], rel["target_asset_id"]
        a, b = knowledge.get(a_id), knowledge.get(b_id)
        if a is None or b is None:
            skipped.append({"skill": skill,
                            "reason": f"conflict {rel['id']}: a participant is "
                                      f"outside this binding's clearance - "
                                      f"evidence cannot be cited, no finding"})
            continue
        content_a, content_b = _norm(a.get("content")), _norm(b.get("content"))
        doc_a, doc_b = doc_of(a), doc_of(b)
        if doc_a and doc_a == doc_b:
            skipped.append({"skill": skill,
                            "reason": f"conflict {rel['id']}: both statements "
                                      f"are from the same document ({doc_a}) - "
                                      f"intra-document ordering, deferred to "
                                      f"the governance conflict review"})
            continue
        shared = shared_subject_ex(content_a, content_b)
        if shared < SAME_SUBJECT_MINIMUM:
            skipped.append({"skill": skill,
                            "reason": f"conflict {rel['id']}: no shared subject "
                                      f"matter ({shared} token(s)) - deferred to "
                                      f"the governance conflict review, "
                                      f"declared"})
            continue
        # name the policy side explicitly (the doc-vs-named-policy route).
        if doc_b in policy_docs:
            contract_e, policy_e = a, b
        else:
            contract_e, policy_e = (b, a) if doc_a in policy_docs else (a, b)
        add_finding({
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "named_policy": named_policy or "Procurement Policy",
            "cite_contract": _cite(contract_e), "cite_policy": _cite(policy_e),
            "excerpt_contract": _excerpt(_norm(contract_e.get("content"))),
            "excerpt_policy": _excerpt(_norm(policy_e.get("content"))),
            "cited_assets": sorted((a_id, b_id)),
            "evidence_lines": [
                f"Contract term (verbatim): {_cite(contract_e)} - "
                f"\"{_excerpt(_norm(contract_e.get('content')))}\"",
                f"Named policy (verbatim): {_cite(policy_e)} - "
                f"\"{_excerpt(_norm(policy_e.get('content')))}\"",
                f"Cross-document ({doc_a} vs {doc_b}); shared subject tokens: "
                f"{shared} (the v1.6 evidence rules, inherited wholesale)",
                f"Governed conflict relationship {rel['id']} "
                f"({rel['classification']}, confidence {rel['confidence']:.3f}, "
                f"status {rel['status']})",
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

    # ---- The renegotiation brief (assist - never a proposal) -------------
    def kind_findings(k):
        return [f for f in findings if f["finding_kind"] == k]
    retrieval = pc.retrieve(package, brief_vendor, top_k=5)
    known = [f"- {_cite(e)} ({e.get('name')}): "
             f"\"{_excerpt(_norm(e.get('content')))}\""
             for e in retrieval["selected"]]
    brief = [
        f"# Renegotiation brief - {brief_vendor}",
        "",
        "Internal assist output (prepare_renegotiation_brief, [assist,",
        "synth]). NOT a proposal: this brief never enters knowledge. It is",
        "preparation material for a human entering a negotiation - never a",
        "negotiation position, never a savings estimate. Narrative framing:",
        "SYNTHESIS_INFERRED.",
        "",
        "## Known (approved terms, cited)",
        "",
    ]
    brief += known or ["- (no approved coverage for this vendor - stated "
                       "rather than composed around)"]
    brief += ["", "## Expiring or moving (window findings + price clauses, "
                  "verbatim)", ""]
    brief += [f"- {f['cite']}: \"{f['excerpt']}\" (days-until "
              f"{f['days_until']}, computed at as_of {f['as_of']})"
              for f in kind_findings("RENEWAL_WINDOW")] \
        + [f"- {f['cite']}: \"{f['excerpt']}\"" +
           (" [non-numeric: quoted as text]" if f.get("non_numeric") else "")
           for f in kind_findings("PRICE_INCREASE_CLAUSE")] \
        or ["- (none in this run - an empty section is itself information)"]
    brief += ["", "## Missing (certification questions the corpus refuses)", ""]
    brief += [f"- {f['supplier']}: \"{f['requirement_excerpt']}\" -> refused: "
              f"\"{f['question']}\"" for f in kind_findings("MISSING_SUPPLIER_CERTIFICATION")] \
        or ["- (none in this run - an empty section is itself information)"]
    brief += ["", "## Unverified (documented, but no door can evidence "
                  "practice or spend)", ""]
    brief += [f"- {f['cite']}: \"{f['excerpt']}\" - documented "
              f"(term_class {f['term_class']}); no door evidences performance, "
              f"spend, or a market comparison"
              for f in kind_findings("VENDOR_TERM")] \
        or ["- (none in this run - an empty section is itself information)"]
    brief += [
        "",
        f"Findings proposed by this run (PENDING, not consulted as facts): "
        f"{len(findings)}",
        "Accepted DERIVED facts are cited as DERIVED wherever consumed. No "
        "target price, savings estimate, or market rate appears in this brief.",
        "",
    ]
    if exclusions:
        brief += [f"Exclusions declared by the gateway: {exclusions}.", ""]
    brief_path = _write(workspace_dir,
                        f"{workbench_name}-renegotiation-brief",
                        "\n".join(brief))

    return {"proposals": sorted(proposal_paths), "brief": brief_path,
            "findings": findings, "skipped": skipped,
            "exclusions": exclusions, "as_of": str(as_of),
            "window_days": window_days,
            "contracts": {s: contracts[s]["path"] for s in ACTIVE_SKILLS}}
