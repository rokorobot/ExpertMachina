"""Finance & Cost Leakage Workbench runner - the v2.3 reference consumer.

Canonical workbench #2 in the catalog; the FIFTH commercial workbench
and the substrate's SECOND consumer. The runner is a consumer, never a
subsystem (D22): its only doors are the .empkg via app.package_consumer,
the MCP gateway as a real client at a real AGENT token's clearance, and
file writes into the vault - one proposal per finding into /08_proposals,
the scenario brief + evidence pack into /07_agent_workspaces. Guard 5
sweeps this module the moment it exists. Built on workbench/common.py
(the ruling-6 shared plumbing, reached by relative import so the reuse
stays inside the swept root) - the SIXTH zero-edit reuse target.

THE SPINE: v2.3 diagnoses governed cost exposure from approved
documents, register facts, and declared-clock windows. It does NOT
determine transactional financial truth.

THE SENSITIVITY POSTURE (the cardinal sins):
  - THE INVENTED MONEY: every money value is verbatim from a cited
    approved fact, or declared arithmetic (the formula stated) over
    verbatim values, or a labeled non-authoritative estimate. Never an
    invented, inferred, approximated, or scenario value as governed fact.
  - THE SETTLED ACCOUNT: the runner never asserts transactional truth
    (paid, spent, booked, balanced, cleared, issued, processed). The
    manifest's forbidden_vocabulary is swept over every written byte
    before anything is emitted. THE INVOICE-SENTENCE DISTINCTION holds:
    a clause "payable within 21 days of the invoice date" is governed
    evidence; a transactional RECORD (invoice number / amount due /
    remit to) is DECLINED as an exposure input, naming [OE].

THE UNOPENED LEDGER: no transactional door exists (structural); a
transactional-record fact is declined with a declared [OE] skip
(adversarial - THE INVOICE PLANT); the SETTLED-ACCOUNT sweep runs on
every written byte (byte-level).

The runner HONORS the five skill contracts: exposure classes + class
markers + transactional-record markers, the comparison axes, the
requirement classes, and the estimate label are READ FROM the contract
files, never hardcoded. A non-ACTIVE contract is refused; the gated
list ([OE]/[ES]) is refused live naming the unminted decision.

Two injectable seams (as in v1.6-v2.2): `answerer` (real =
package_consumer.consume through the D19 resolver; CI = the declared
deterministic contract-follower) and `narrator` (default =
deterministic templates; the real-model run overrides it). Whatever
narrates, every finding cites the governed evidence it rests on: no
evidence, no finding. DERIVED register evidence is cited AS DERIVED
(THE SECOND HARVEST).
"""
import os
import re

from ..common import (
    import_package_consumer as _import_package_consumer,
    excerpt as _excerpt,
    subject_tokens as _subject_tokens,
    load_active_contracts,
    StdioMcpGraphClient,       # noqa: F401 - the real-run transport, re-exported
    write_hashed as _write,
)

ACTIVE_SKILLS = (
    "detect_cost_exposure",
    "compare_terms_vs_finance_policy",
    "detect_missing_finance_evidence",
    "prepare_cost_exposure_scenario",
    "prepare_finance_evidence_pack",
)

FINDING_KINDS = {
    "detect_cost_exposure": ("COST_EXPOSURE", "EXCERPT_BACKED"),
    "compare_terms_vs_finance_policy": ("FINANCE_POLICY_MISMATCH", "CONFLICT_BACKED"),
    "detect_missing_finance_evidence": ("MISSING_FINANCE_EVIDENCE", "REFUSAL_BACKED"),
}

REFUSAL_MARKER = "INSUFFICIENT EVIDENCE"

# THE GATED LIST (the v2.3 WS0 ruling 4 + the manifest's
# refused_until_minted): the transactional-truth family stays [OE], and
# owner assignment stays [ES]. Refused live, naming the unminted decision.
GATED_SKILLS = {
    "detect_duplicate_invoices": "the Operational Evidence Realm",
    "compare_po_vs_invoices": "the Operational Evidence Realm",
    "detect_unusual_cost_increases": "the Operational Evidence Realm",
    "flag_overdue_receivables": "the Operational Evidence Realm",
    "detect_budget_overrun_from_accounting": "the Operational Evidence Realm",
    "detect_payment_terms_not_followed": "the Operational Evidence Realm",
    "identify_missing_finance_obligation_owner": "Exception Stewardship",
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
# frozen this milestone (the SIXTH zero-edit reuse).

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


def parse_scalar(path, key):
    for line in _read_lines(path):
        s = line.strip()
        if s.startswith(f"{key}:"):
            return s.split(":", 1)[1].strip().strip('"')
    return None


def parse_inline_list(path, key):
    """An inline `key: [a, b, c]` list (values may wrap across lines);
    returns the bare names. Distinct from parse_quoted_list (dash items)."""
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
    return [v.strip().strip('"') for v in buf.split(",") if v.strip()]


# ------------------------------------------------------------ money doctrine

_CURRENCY_RE = re.compile(r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*EUR")
_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _money(value):
    return f"{value:,.2f} EUR"


def declared_arithmetic(content):
    """Tier-2: when a currency base AND a percentage are BOTH verbatim in
    one cited fact, compute the increase with the formula stated. Returns
    (formula_string, result_money) or None - never an invented base."""
    cur = _CURRENCY_RE.search(content)
    pct = _PCT_RE.search(content)
    if not (cur and pct):
        return None
    base = float(cur.group(1).replace(",", ""))
    rate = float(pct.group(1))
    result = base * rate / 100.0
    return (f"{cur.group(1)} EUR x {pct.group(1)}% = {_money(result)} "
            f"(declared arithmetic over verbatim values only)"), _money(result)


# ------------------------------------------------------------ narration

def _class_of(entry):
    return (entry.get("source_class") or "PRIMARY").upper()


def _cite(entry):
    tag = " [DERIVED]" if _class_of(entry) == "DERIVED" else ""
    return f"asset {entry['asset_id']}{tag}"


def default_narrator(finding):
    """Deterministic narration. Every template states DOCUMENTATION /
    EXPOSURE status, never transactional truth, and never adds a money
    value of its own (THE INVENTED MONEY / THE SETTLED ACCOUNT postures)."""
    kind = finding["finding_kind"]
    if kind == "COST_EXPOSURE":
        base = (f"An approved document states a cost exposure "
                f"({finding['cite']}, exposure_class {finding['exposure_class']}): "
                f"\"{finding['excerpt']}\".")
        if finding.get("arithmetic"):
            base += (f" Declared arithmetic: {finding['arithmetic']}.")
        if finding.get("days_until") is not None:
            base += (f" The dated exposure falls {finding['days_until']} day(s) "
                     f"from the declared as_of {finding['as_of']} (window "
                     f"{finding['window_days']} days).")
        return base + (" This states what the contract COULD cost and when "
                       "exposure falls due - never any actual outlay or "
                       "settlement.")
    if kind == "FINANCE_POLICY_MISMATCH":
        return (f"An approved contract term ({finding['cite']}) disagrees with "
                f"an approved finance policy ({finding['policy_cite']}) on the "
                f"{finding['axis']} axis. Contract: \"{finding['excerpt']}\". "
                f"Policy: \"{finding['policy_excerpt']}\". Two approved "
                f"DOCUMENTS disagree - this says nothing about whether any "
                f"payment actually breached policy.")
    if kind == "MISSING_FINANCE_EVIDENCE":
        return (f"A documented finance requirement ({finding['cite']}, "
                f"requirement_class {finding['requirement_class']}): "
                f"\"{finding['excerpt']}\" has no approved covering evidence - "
                f"the question \"{finding['question']}\" is reproducibly "
                f"refused. The corpus does not DOCUMENT the evidence; this "
                f"says nothing about whether the spend or approval happened.")
    return f"Finding of kind {kind}."


PROPOSED_ACTIONS = {
    "COST_EXPOSURE": (
        "Review the cost exposure at the human gate: accept it as a DERIVED "
        "exposure fact or reject it with a recorded reason. The workbench "
        "never renegotiates, pays, or books - and never states an actual "
        "cost, only what the document could cost."),
    "FINANCE_POLICY_MISMATCH": (
        "Reconcile the contract term with the finance policy through the "
        "governed workflow, or record an approved exception. The workbench "
        "never amends either side and never asserts an actual breach."),
    "MISSING_FINANCE_EVIDENCE": (
        "Produce or ingest the covering evidence through the governed "
        "pipeline. The finding states the corpus does not document the "
        "evidence - never that the underlying spend or approval did or did "
        "not occur (that is [OE])."),
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
        f"# {kind.replace('_', ' ').title()} - finance cost-exposure finding",
        "",
        "Agent-synthesized finding. This document is a PROPOSAL: it becomes",
        "knowledge only if a human accepts it at the gate, and then as a",
        "DERIVED fact (D29/D30). Every money value in it is quoted verbatim",
        "from a governed fact or is declared arithmetic over verbatim values",
        "- the workbench invents no figure and asserts no actual spend.",
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
                   domain_prefix="finance", answerer=None, narrator=None,
                   backend_dir=None, skills_dir=None, manifest_path=None,
                   requested_skills=None, brief_topic="colocation",
                   workbench_name="finance-cost-leakage"):
    """THE ACTIVE FIVE over the doors at a DECLARED as_of + window_days.
    Returns a run summary: proposal paths (one per finding), the scenario
    brief path, the evidence-pack path, the findings, and what was
    skipped (incl. THE INVOICE PLANT declines) with the refusing reason."""
    import datetime

    if not as_of or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(as_of)):
        raise RuntimeError(
            "detect_cost_exposure refuses: no as_of declared for the run "
            "(expected YYYY-MM-DD) - the clock is a declared parameter, "
            "never sampled.")
    if not isinstance(window_days, int) or window_days <= 0:
        raise RuntimeError(
            "detect_cost_exposure refuses: no positive window_days declared "
            "- the window is a declared parameter, never defaulted.")
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
    exp_path = contracts["detect_cost_exposure"]["path"]
    class_markers = parse_nested_marker_map(exp_path, "exposure_convention",
                                            "class_markers")
    record_markers = [m.lower() for m in parse_nested_quoted_list(
        exp_path, "exposure_convention", "transactional_record_markers")]
    cmp_path = contracts["compare_terms_vs_finance_policy"]["path"]
    axis_markers = parse_nested_marker_map(cmp_path, "comparison_convention",
                                           "axis_markers")
    req_path = contracts["detect_missing_finance_evidence"]["path"]
    req_classes = parse_inline_list(req_path, "requirement_classes")
    estimate_label = parse_scalar(
        contracts["prepare_cost_exposure_scenario"]["path"], "estimate_label") \
        or "[ESTIMATE, non-authoritative]"

    proposals_dir = os.path.join(vault_dir, "08_proposals")
    workspace_dir = os.path.join(vault_dir, "07_agent_workspaces")
    for required in (proposals_dir, workspace_dir):
        if not os.path.isdir(required):
            raise RuntimeError(f"{required} missing - bootstrap the vault first.")

    subgraph = graph_client.get_domain_subgraph(project_id, domain_prefix)
    exclusions = {k: v for k, v in (subgraph.get("excluded") or {}).items() if v}

    findings, skipped = [], []
    entries = sorted(knowledge.values(), key=lambda e: e["asset_id"])

    def is_transactional_record(content):
        """THE INVOICE PLANT decline: a fact carrying a transactional-record
        marker OR a SETTLED-ACCOUNT assertion is a RECORD, not a clause."""
        low = content.lower()
        if any(mk in low for mk in record_markers):
            return True
        if any(phrase in low for phrase in forbidden):
            return True
        return False

    def classify_exposure(content):
        low = content.lower()
        for cls, mks in class_markers.items():
            if any(mk in low for mk in mks):
                return cls
        return None

    def check_posture(statement):
        low = statement.lower()
        for phrase in forbidden:
            if phrase in low:
                raise RuntimeError(
                    f"THE SETTLED ACCOUNT: forbidden vocabulary {phrase!r} in "
                    f"a written statement - transactional-truth assertion is "
                    f"refused at the source.")

    def add_finding(finding):
        finding["statement"] = narrator(finding)
        check_posture(finding["statement"])
        findings.append(finding)

    # ---- Walk 1: detect_cost_exposure (EXCERPT_BACKED + arithmetic) ------
    # THE SECOND HARVEST: DERIVED register facts flow through this walk and
    # are cited AS DERIVED. THE INVOICE PLANT: a transactional record is
    # declined, declared, naming [OE].
    skill = "detect_cost_exposure"
    kind, basis = FINDING_KINDS[skill]
    for entry in entries:
        content = _norm(entry.get("content"))
        if is_transactional_record(content):
            skipped.append({
                "skill": skill,
                "reason": f"asset {entry['asset_id']}: a TRANSACTIONAL RECORD "
                          f"(invoice/PO/statement markers or settled-account "
                          f"assertion) - DECLINED as an exposure input, naming "
                          f"the Operational Evidence Realm ([OE]); v2.3 "
                          f"diagnoses documents, never transactional truth"})
            continue
        cls = classify_exposure(content)
        if cls is None:
            continue
        lines = [
            f"Exposure excerpt (verbatim): {_cite(entry)} - \"{_excerpt(content)}\"",
            f"Exposure class: {cls} (the declared class markers)",
        ]
        if _class_of(entry) == "DERIVED":
            lines.append("Source is an accepted DERIVED register fact (v2.1) "
                         "- THE SECOND HARVEST, cited BY id, nothing "
                         "re-extracted")
        arith = declared_arithmetic(content)
        arithmetic = None
        if arith:
            arithmetic = arith[0]
            lines.append(f"Declared arithmetic: {arith[0]}")
        else:
            pct = _PCT_RE.search(content)
            if pct:
                lines.append(f"Rate quoted verbatim: {pct.group(0)} (no "
                             f"verbatim base in this fact - reported "
                             f"qualitatively, never applied to an invented base)")
            else:
                lines.append("Qualitative exposure (no verbatim figure - never "
                             "an invented number)")
        finding = {
            "skill": skill, "finding_kind": kind, "evidence_basis": basis,
            "asset_id": entry["asset_id"], "cite": _cite(entry),
            "excerpt": _excerpt(content), "exposure_class": cls,
            "arithmetic": arithmetic, "as_of": None, "window_days": None,
            "days_until": None, "cited_assets": [entry["asset_id"]],
            "evidence_lines": lines,
        }
        m = _DATE_RE.search(content)
        if m and cls in ("renewal_cost", "price_increase"):
            d = datetime.date(*(int(p) for p in m.group(1).split("-")))
            days_until = (d - as_of_date).days
            if as_of_date <= d <= window_end:
                finding["as_of"] = str(as_of)
                finding["window_days"] = window_days
                finding["days_until"] = days_until
                finding["evidence_lines"].append(
                    f"Dated exposure {m.group(1)}: {days_until} day(s) from "
                    f"as_of {as_of} (window {window_days}d, end "
                    f"{window_end.isoformat()}) - date arithmetic only")
            else:
                skipped.append({
                    "skill": skill,
                    "reason": f"asset {entry['asset_id']}: the dated exposure "
                              f"({m.group(1)}) is outside the declared window "
                              f"[{as_of}, {window_end.isoformat()}] - a covered "
                              f"control, no finding"})
                continue
        add_finding(finding)

    # ---- Walk 2: compare_terms_vs_finance_policy (CONFLICT_BACKED) -------
    # A contract-side term vs a policy-side rule on a declared axis. The
    # policy side carries policy markers ("must be approved", "at least N
    # days"); the contract side carries a payable/fee term. Document-vs-
    # document only - never an actual-breach assertion.
    skill = "compare_terms_vs_finance_policy"
    kind, basis = FINDING_KINDS[skill]
    policy_facts = [e for e in entries
                    if not is_transactional_record(_norm(e.get("content")))
                    and re.search(r"at least \d+ days|must be approved",
                                  _norm(e.get("content")).lower())]
    payable_re = re.compile(r"payable within (\d+) days")
    floor_re = re.compile(r"at least (\d+) days")
    for entry in entries:
        content = _norm(entry.get("content"))
        if is_transactional_record(content):
            continue
        pm = payable_re.search(content.lower())
        if not pm:
            continue
        contract_days = int(pm.group(1))
        # find a policy fact declaring a payment-terms floor
        for pol in policy_facts:
            pol_c = _norm(pol.get("content"))
            fm = floor_re.search(pol_c.lower())
            if not fm or pol["asset_id"] == entry["asset_id"]:
                continue
            floor_days = int(fm.group(1))
            if contract_days < floor_days:
                add_finding({
                    "skill": skill, "finding_kind": kind,
                    "evidence_basis": basis, "axis": "payment_terms",
                    "asset_id": entry["asset_id"], "cite": _cite(entry),
                    "excerpt": _excerpt(content),
                    "policy_cite": _cite(pol),
                    "policy_excerpt": _excerpt(pol_c),
                    "cited_assets": sorted({entry["asset_id"], pol["asset_id"]}),
                    "evidence_lines": [
                        f"Contract term (verbatim): {_cite(entry)} - "
                        f"\"{_excerpt(content)}\" ({contract_days} days)",
                        f"Policy floor (verbatim): {_cite(pol)} - "
                        f"\"{_excerpt(pol_c)}\" ({floor_days} days)",
                        f"Axis: payment_terms - {contract_days} < {floor_days} "
                        f"(both figures verbatim; document-vs-document, never "
                        f"an actual-payment claim)",
                    ],
                })
                break

    # ---- Walk 3: detect_missing_finance_evidence (REFUSAL_BACKED) --------
    # A documented requirement whose evidence question the corpus refuses.
    skill = "detect_missing_finance_evidence"
    kind, basis = FINDING_KINDS[skill]
    req_questions = {
        "spend_approval": "Which approved record evidences the spend approval "
                          "required by the finance policy?",
        "policy_coverage": "Which approved document covers the required "
                           "finance-policy area?",
        "service_obligation": "Which approved record evidences the service "
                              "obligation the contract pays for?",
    }
    seen_reqs = set()
    for entry in entries:
        content = _norm(entry.get("content"))
        if is_transactional_record(content):
            continue
        low = content.lower()
        rc = None
        if "must be approved" in low or "spend commitment" in low:
            rc = "spend_approval"
        if rc and rc in req_classes and rc not in seen_reqs:
            question = req_questions[rc]
            ans = answerer(question)
            answer_text = (ans.get("answer") if isinstance(ans, dict)
                           else str(ans))
            if REFUSAL_MARKER in (answer_text or ""):
                seen_reqs.add(rc)
                add_finding({
                    "skill": skill, "finding_kind": kind,
                    "evidence_basis": basis, "requirement_class": rc,
                    "asset_id": entry["asset_id"], "cite": _cite(entry),
                    "excerpt": _excerpt(content), "question": question,
                    "cited_assets": [entry["asset_id"]],
                    "evidence_lines": [
                        f"Requirement excerpt (verbatim): {_cite(entry)} - "
                        f"\"{_excerpt(content)}\"",
                        f"Requirement class: {rc}",
                        f"Reproducible refusal: \"{question}\" -> "
                        f"{REFUSAL_MARKER}",
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

    # ---- prepare_cost_exposure_scenario (assist - THE LABELED ESTIMATE) --
    def kind_findings(k):
        return [f for f in findings if f["finding_kind"] == k]
    exposures = kind_findings("COST_EXPOSURE")
    scenario = [
        "# Cost-exposure scenario brief",
        "",
        f"Declared clock: as_of {as_of} - window {window_days} days.",
        "Internal assist output (prepare_cost_exposure_scenario, [assist,",
        "synth]). NOT a proposal: this brief never enters knowledge and is",
        "never persisted. Every governed figure is cited; every estimate",
        f"wears the label {estimate_label} in-unit. Narrative framing:",
        "SYNTHESIS_INFERRED. No actual spend, payment, or balance appears.",
        "",
        "## Governed exposures (cited)",
        "",
    ]
    scenario += [f"- {f['cite']} [{f['exposure_class']}]: \"{f['excerpt']}\""
                 + (f" -> {f['arithmetic']}" if f.get("arithmetic") else "")
                 for f in exposures] \
        or ["- (none in this run - an empty section is itself information)"]
    scenario += ["", "## Scenarios (labeled, non-authoritative)", ""]
    if exposures:
        scenario += [
            f"- Illustration {estimate_label}: if every governed exposure "
            f"above recurred annually, the combined annual exposure would be "
            f"a planning figure to size against the budget - a scenario under "
            f"the stated assumption, NOT a governed number.",
        ]
    else:
        scenario += ["- (no governed exposures to build a scenario on)"]
    scenario += ["", "## Assumptions", "",
                 "- Every figure above is either governed (cited) or wears the "
                 f"{estimate_label} label; no estimate is presented as fact.",
                 "- Actual spend/payment/balance is out of scope ([OE]).", ""]
    scenario_text = "\n".join(scenario)
    check_posture(scenario_text)
    brief_path = _write(workspace_dir,
                        f"{workbench_name}-cost-exposure-scenario",
                        scenario_text)

    # ---- prepare_finance_evidence_pack (assist) --------------------------
    retrieval = pc.retrieve(package, brief_topic, top_k=5)
    known = [f"- {_cite(e)} ({e.get('name')}): \"{_excerpt(_norm(e.get('content')))}\""
             for e in retrieval["selected"]]
    pack = [
        f"# Finance evidence pack - {brief_topic}",
        "",
        "Internal assist output (prepare_finance_evidence_pack, [assist,",
        "synth]). NOT a proposal: never enters knowledge, never an accounting",
        "statement. known / exposed / conflicting / estimated separated.",
        "Narrative framing: SYNTHESIS_INFERRED.",
        "",
        "## Known (approved cost/term statements, cited)",
        "",
    ]
    pack += known or ["- (no approved coverage for this topic)"]
    pack += ["", "## Exposed (accepted exposure/mismatch/gap findings, "
                 "PENDING here - cited as DERIVED once accepted)", ""]
    pack += [f"- {f['cite']} [{f['finding_kind']}]: \"{f['excerpt']}\""
             for f in findings] \
        or ["- (none in this run - an empty section is itself information)"]
    pack += ["", "## Conflicting (governed finance-policy mismatches)", ""]
    pack += [f"- {f['cite']} vs {f['policy_cite']} ({f['axis']})"
             for f in kind_findings("FINANCE_POLICY_MISMATCH")] \
        or ["- (none in this run - an empty section is itself information)"]
    pack += ["", "## Estimated (labeled non-authoritative only)", "",
             f"- (no estimate is asserted as fact; scenarios wear the "
             f"{estimate_label} label and live in the scenario brief)", ""]
    pack += [
        f"Findings proposed by this run (PENDING, not consulted as facts): "
        f"{len(findings)}",
        "No actual spend, payment, balance, or accounting figure appears in "
        "this pack.",
        "",
    ]
    pack_text = "\n".join(pack)
    check_posture(pack_text)
    pack_path = _write(workspace_dir,
                       f"{workbench_name}-finance-evidence-pack", pack_text)

    return {"proposals": sorted(proposal_paths), "brief": brief_path,
            "pack": pack_path, "findings": findings, "skipped": skipped,
            "exclusions": exclusions, "as_of": str(as_of),
            "window_days": window_days,
            "contracts": {s: contracts[s]["path"] for s in ACTIVE_SKILLS}}
