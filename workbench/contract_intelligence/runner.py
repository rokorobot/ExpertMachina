"""Contract Intelligence Workbench runner - the v2.1 reference consumer,
THE SHARED ENGINE (canonical #16, the fourth commercial workbench).

A consumer, never a subsystem (D22): its only doors are the .empkg via
app.package_consumer and the MCP gateway as a real client at a real
AGENT token's clearance. Built on workbench/common.py (relative import,
zero shared-module edits - the fourth reuse).

THE SENSITIVITY POSTURE (the cardinal sin): THE PARAPHRASED CLAUSE. A
shared engine amplifies its own distortions into every consumer at
once, so every clause candidate's statement carries the VERBATIM
excerpt - parties, dates, amounts, percentages, and notice periods
exactly as the contract wrote them (THE INVENTED NUMBER posture
inherited whole from v1.8). Extraction adds ONLY declared structure:
the clause_class from the PINNED, CLOSED fifteen-class taxonomy,
assigned by the declared first-match rules (one clause = one class;
shadowing is pinned, declared, and reported - never hidden). Its twin,
THE LEGAL CONCLUSION, is refused by the manifest's forbidden
vocabulary, swept over every written byte pre-write.

THE SHARED-ENGINE RULE (v2.1 WS0 ruling 5): an accepted clause
candidate becomes a DERIVED register entry that the UNCHANGED consumer
workbenches cite through their own packages. The feed is governed
facts alone - this module is imported by no consumer, imports no
consumer, and writes no store. Idempotence across generations: a
clause already present in the package as an accepted register entry
(origin contract-intelligence) is SKIPPED, never re-proposed.

THE REGISTER DISTINCTION (ruled): the extraction may become governed
DERIVED structure through the valve; the review brief may synthesize
for a reader but never becomes a fact - assist output only.
"""
import os
import re

from ..common import (
    import_package_consumer as _import_package_consumer,
    load_active_contracts,
    StdioMcpGraphClient,   # noqa: F401 - the real MCP door for deployments
    write_hashed as _write,
)

ACTIVE_SKILLS = (
    "extract_contract_clauses",
    "detect_missing_contract_metadata",
    "prepare_contract_review_brief",
)

FINDING_KINDS = {
    "extract_contract_clauses": ("CONTRACT_CLAUSE", "EXCERPT_BACKED"),
    "detect_missing_contract_metadata": ("CONTRACT_METADATA_GAP",
                                         "ABSENCE_DECLARED"),
}

# THE GATED LIST (WS0 rulings 2-3 + the standing boundary posture):
# refused live, naming the unminted decision or the ruling.
GATED_SKILLS = {
    "detect_contract_owner_gaps": "Exception Stewardship stays "
        "per-workbench gated exactly as D32's minting ruled",
    "compare_contract_pricing_vs_invoices": "the Operational Evidence Realm",
    "verify_pricing_vs_invoices": "the Operational Evidence Realm",
    "list_pending_register_candidates": "the Pipeline Metadata Door",
    "compare_contract_vs_internal_policy": "SEQUENCED (v2.1 ruling 3): "
        "v1.8 owns the shipped commercial case; a general comparison "
        "engine deserves its own evidence rule",
    "compare_customer_contract_vs_support_sop": "SEQUENCED (v2.1 ruling 3)",
    "detect_conflicting_contract_clauses": "SEQUENCED (v2.1 ruling 3): "
        "the platform NLI conflict engine owns cross-asset contradiction",
    "prepare_renewal_decision_brief": "SEQUENCED (v2.1 ruling 3)",
    "prepare_negotiation_points": "SEQUENCED (v2.1 ruling 3): negotiation "
        "synthesis is a posture question of its own",
}

_ORIGIN_RE = re.compile(r"^([a-z][a-z-]*?)-([a-z][a-z_]*)-[0-9a-f]{12}\.md$")


def require_ungated(skill_id):
    if skill_id in GATED_SKILLS:
        raise RuntimeError(
            f"Skill {skill_id} is refused: {GATED_SKILLS[skill_id]} - the "
            f"runner refuses the task and names the boundary.")


def _norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


# ------------------------------------------------ contract-field parsing
def _read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_taxonomy(engine_contract_path):
    """The PINNED taxonomy: ordered [(clause_class, [keywords])] parsed
    from the ratified contract bytes - the rules ARE the contract."""
    rules, capturing = [], False
    for line in _read_text(engine_contract_path).splitlines():
        if line.startswith("clause_class_taxonomy:"):
            capturing = True
            continue
        if capturing:
            s = line.strip()
            if s.startswith("#") or not s:
                continue
            if line and not line.startswith(" "):
                break
            m = re.match(r'- (\w+): (.+)$', s)
            if m:
                kws = re.findall(r'"([^"]+)"', m.group(2))
                rules.append((m.group(1), [k.lower() for k in kws]))
    if not rules:
        raise RuntimeError(f"{engine_contract_path}: no clause_class_taxonomy")
    return rules


def parse_regimes(engine_contract_path):
    """(commitment_classes, structural_classes, explicit_markers)."""
    text = _read_text(engine_contract_path)

    def class_list(anchor):
        seg = text.split(anchor, 1)[1]
        m = re.search(r"classes: \[([^\]]+)\]", seg)
        return [c.strip() for c in m.group(1).replace("\n", " ").split(",")]

    commitment = class_list("commitment_classes:")
    structural = class_list("structural_classes:")
    seg = text.split("explicit_markers:", 1)[1]
    markers = [m.lower() for m in re.findall(r'"([^"]+)"',
                                             seg.split("]", 1)[0])]
    return commitment, structural, markers


def parse_contract_document_terms(engine_contract_path):
    """The declared contract-document scope: the quoted title terms of
    the contract_document_rule block."""
    text = _read_text(engine_contract_path)
    seg = text.split("contract_document_rule:", 1)[1]
    seg = seg.split("allowed_inputs:", 1)[0]
    terms = [t.lower() for t in re.findall(r'"([^"]+)"', seg)]
    if not terms:
        raise RuntimeError("contract_document_rule declares no terms")
    return terms


def parse_required_metadata(metadata_contract_path):
    """[(group_name, [any_of classes])] from required_metadata."""
    groups, current = [], None
    capturing = False
    for line in _read_text(metadata_contract_path).splitlines():
        if line.startswith("required_metadata:"):
            capturing = True
            continue
        if capturing:
            s = line.strip()
            if s.startswith("#") or not s:
                continue
            if line and not line.startswith(" "):
                break
            gm = re.match(r"- group: (\w+)$", s)
            if gm:
                current = gm.group(1)
                continue
            am = re.match(r"any_of: \[([^\]]+)\]", s)
            if am and current:
                groups.append((current,
                               [c.strip() for c in am.group(1).split(",")]))
                current = None
    if not groups:
        raise RuntimeError(f"{metadata_contract_path}: no required_metadata")
    return groups


def parse_forbidden_vocabulary(manifest_path):
    seg = _read_text(manifest_path).split("forbidden_vocabulary:", 1)[1]
    seg = seg.split("domain_scope:", 1)[0]
    return [v.lower() for v in re.findall(r'^  - "([^"]+)"$', seg,
                                          re.MULTILINE)]


# ------------------------------------------------ the declared rules, applied
def classify(sentence, rules):
    """First-match over the PINNED order - one clause, one class;
    shadowing is declared behavior."""
    low = sentence.lower()
    for cls, kws in rules:
        if any(k in low for k in kws):
            return cls
    return None


def qualifies(sentence, cls, commitment, structural, markers):
    low = sentence.lower()
    if cls in commitment:
        return any(m in low for m in markers)
    if cls in structural:
        return bool(re.search(r"\d{4}-\d{2}-\d{2}", sentence)
                    or re.search(r"\d", sentence)
                    or re.search(r"days|months|years|anniversary", low)
                    or re.search(r"\b[A-Z][a-z]+[A-Z]", sentence))
    return False


def _is_register_entry(entry):
    """An accepted register entry already in the package: DERIVED with
    origin contract-intelligence via the v1.9 filename convention."""
    if (entry.get("source_class") or "PRIMARY").upper() != "DERIVED":
        return False
    src = (entry.get("provenance") or {}).get("source_document") or ""
    m = _ORIGIN_RE.match(src)
    return bool(m and m.group(1) == "contract-intelligence")


PROPOSED_ACTIONS = {
    "CONTRACT_CLAUSE": (
        "Review the clause candidate at the human gate: accept it as a "
        "DERIVED register entry or reject it with a recorded reason. An "
        "accepted entry is the clause register - the single upstream "
        "source any consuming workbench cites through its own package "
        "(composition across the valve; the feed is governed facts alone)."),
    "CONTRACT_METADATA_GAP": (
        "Locate or author the missing clause through the governed "
        "pipeline; on acceptance the register gains the entry and the "
        "gap closes. The gap states that no clause was detectable under "
        "the pinned taxonomy - never that the clause does not exist."),
}


def _proposal_document(finding, agent_principal, binding_id, package_hash,
                       exclusions, workbench_name):
    kind = finding["finding_kind"]
    lines = [
        "---", "em_proposal: 1", f"agent_principal: {agent_principal}",
        f"binding_id: {binding_id}", f"package_hash: {package_hash}",
        f"workbench: {workbench_name}", f"skill: {finding['skill']}",
        "skill_version: 1", f"finding_kind: {kind}",
        f"evidence_basis: {finding['evidence_basis']}",
        f"cited_assets: {','.join(str(i) for i in finding['cited_assets'])}",
        "---", "",
        f"# {kind.replace('_', ' ').title()} - register candidate", "",
        "Agent-synthesized finding. This document is a PROPOSAL: it becomes",
        "knowledge only if a human accepts it at the gate, and then as a",
        "DERIVED fact (D29/D30). The clause text is quoted VERBATIM from a",
        "governed asset - the engine paraphrases nothing and concludes",
        "nothing about validity or enforceability.", "",
        "## Finding", "", finding["statement"], "", "## Evidence", "",
    ]
    for line in finding["evidence_lines"]:
        lines.append(f"- {line}")
    lines += ["", "## Proposed action", "", PROPOSED_ACTIONS[kind], ""]
    if exclusions:
        lines += ["## What the agent could not see", "",
                  f"Exclusions declared by the gateway: {exclusions}.", ""]
    return "\n".join(lines)


def run_diagnostic(package_path, vault_dir, project_id, agent_principal,
                   binding_id, graph_client, as_of, answerer=None,
                   backend_dir=None, skills_dir=None, manifest_path=None,
                   requested_skills=None,
                   workbench_name="contract-intelligence"):
    """The three ratified skills over the doors at a DECLARED as_of.
    Returns: proposal paths (one per finding), the review brief path,
    the findings, the register entries already carried by the package
    (skipped - idempotence), and the per-contract coverage."""
    if not as_of or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(as_of)):
        raise RuntimeError(
            "extract_contract_clauses refuses: no as_of declared for the "
            "run (expected YYYY-MM-DD) - the clock is a declared "
            "parameter, never sampled.")
    for skill_id in (requested_skills or ACTIVE_SKILLS):
        require_ungated(skill_id)

    pc = _import_package_consumer(backend_dir)
    package = pc.load_package(package_path)   # verifies the hash chain
    package_hash = package["package_hash"]
    entries = sorted(package["knowledge"], key=lambda e: e["asset_id"])

    wb_dir = os.path.dirname(os.path.abspath(__file__))
    skills_dir = skills_dir or os.path.join(wb_dir, "skills")
    manifest_path = manifest_path or os.path.join(wb_dir, "workbench.yaml")
    contracts = load_active_contracts(
        skills_dir, tuple(requested_skills or ()) + ACTIVE_SKILLS)
    engine_path = contracts["extract_contract_clauses"]["path"]
    meta_path = contracts["detect_missing_contract_metadata"]["path"]
    rules = parse_taxonomy(engine_path)
    commitment, structural, markers = parse_regimes(engine_path)
    doc_terms = parse_contract_document_terms(engine_path)
    required_groups = parse_required_metadata(meta_path)
    forbidden = parse_forbidden_vocabulary(manifest_path)

    proposals_dir = os.path.join(vault_dir, "08_proposals")
    workspace_dir = os.path.join(vault_dir, "07_agent_workspaces")
    for required in (proposals_dir, workspace_dir):
        if not os.path.isdir(required):
            raise RuntimeError(f"{required} missing - bootstrap the vault first.")

    subgraph = graph_client.get_domain_subgraph(project_id, "")
    exclusions = {k: v for k, v in (subgraph.get("excluded") or {}).items() if v}

    # ---- the contract-document scope (the declared rule) ----------------
    def source_doc(entry):
        return (entry.get("provenance") or {}).get("source_document") or ""

    def in_scope(entry):
        low = source_doc(entry).lower()
        return any(t in low for t in doc_terms)

    # register entries already accepted into this package (idempotence:
    # their clauses are REGISTERED - never re-proposed)
    register_entries = [e for e in entries if _is_register_entry(e)]
    registered_texts = [_norm(e.get("content")) for e in register_entries]

    def already_registered(content):
        n = _norm(content)
        return any(n in r or r in n for r in registered_texts)

    # ---- extract_contract_clauses (THE ENGINE) ---------------------------
    findings = []
    per_doc_classes = {}
    for e in entries:
        if not in_scope(e) or _is_register_entry(e):
            continue
        content = _norm(e.get("content"))
        cls = classify(content, rules)
        if not cls or not qualifies(content, cls, commitment, structural,
                                    markers):
            continue
        per_doc_classes.setdefault(source_doc(e), set()).add(cls)
        if already_registered(content):
            continue   # idempotence across generations - declared below
        findings.append({
            "skill": "extract_contract_clauses",
            "finding_kind": "CONTRACT_CLAUSE",
            "evidence_basis": "EXCERPT_BACKED",
            "clause_class": cls,
            "contract_document": source_doc(e),
            "cited_assets": [e["asset_id"]],
            "statement": (f"Clause class {cls} (pinned taxonomy, "
                          f"first-match). Verbatim clause from governed "
                          f"asset {e['asset_id']}: \"{content}\""),
            "evidence_lines": [
                f"Contract document (verbatim filename): {source_doc(e)}",
                f"Governed source: asset {e['asset_id']} - the excerpt above "
                f"is its content, unaltered.",
                "The engine adds declared structure only; it states what "
                "the contract SAYS.",
            ],
        })

    registered_skipped = [
        {"skill": "extract_contract_clauses",
         "reason": (f"already registered: an accepted register entry "
                    f"(asset {e['asset_id']}) carries this clause - the "
                    f"engine never re-proposes the register")}
        for e in register_entries]

    # ---- detect_missing_contract_metadata --------------------------------
    contract_docs = sorted({source_doc(e) for e in entries
                            if in_scope(e) and not _is_register_entry(e)})
    covered_controls = []
    for doc in contract_docs:
        present = per_doc_classes.get(doc, set())
        doc_asset_ids = sorted(e["asset_id"] for e in entries
                               if source_doc(e) == doc)
        missing = [(g, any_of) for g, any_of in required_groups
                   if not (present & set(any_of))]
        if not missing:
            covered_controls.append(doc)
            continue
        for group, any_of in missing:
            findings.append({
                "skill": "detect_missing_contract_metadata",
                "finding_kind": "CONTRACT_METADATA_GAP",
                "evidence_basis": "ABSENCE_DECLARED",
                "contract_document": doc,
                "missing_group": group,
                "cited_assets": doc_asset_ids,
                "statement": (
                    f"No clause of required group '{group}' (any of: "
                    f"{', '.join(any_of)}) was detectable in contract "
                    f"document {doc} under the pinned taxonomy. This "
                    f"declares what detection could not find - never that "
                    f"the clause does not exist."),
                "evidence_lines": [
                    f"Contract document (verbatim filename): {doc}",
                    f"Assets searched: {', '.join(str(i) for i in doc_asset_ids)}",
                    f"Classes probed: {', '.join(any_of)} (first-match rules "
                    f"of the ratified engine contract)",
                    "Absence becomes a finding, never a fact.",
                ],
            })

    # ---- the review brief (assist; THE REGISTER DISTINCTION) -------------
    brief = [
        f"# Contract review brief - as_of {as_of}",
        "",
        "Internal assist output (prepare_contract_review_brief, [assist]).",
        "NOT a proposal: this brief never enters knowledge (THE REGISTER",
        "DISTINCTION - synthesis for a reader never becomes a fact). Every",
        "clause line quotes governed content verbatim with its asset id.",
        f"Declared clock: as_of {as_of} (a run parameter, never wall-clock).",
        "",
        "## The register carried by this package",
        "",
    ]
    if register_entries:
        for e in register_entries:
            brief.append(f"- asset {e['asset_id']} [DERIVED, origin: "
                         f"contract-intelligence]: \"{_norm(e.get('content'))}\"")
    else:
        brief.append("- (no accepted register entries in this package yet - "
                     "an empty register is itself information)")
    brief += ["", "## Clause candidates proposed this run", ""]
    clause_findings = [f for f in findings
                       if f["finding_kind"] == "CONTRACT_CLAUSE"]
    if clause_findings:
        for f in clause_findings:
            brief.append(f"- [{f['clause_class']}] asset "
                         f"{f['cited_assets'][0]} of "
                         f"{f['contract_document']}: {f['statement']}")
    else:
        brief.append("- (no new clause candidates this run)")
    brief += ["", "## Metadata gaps declared this run", ""]
    gap_findings = [f for f in findings
                    if f["finding_kind"] == "CONTRACT_METADATA_GAP"]
    if gap_findings:
        for f in gap_findings:
            brief.append(f"- {f['contract_document']}: missing group "
                         f"'{f['missing_group']}' (declared, never inferred)")
    else:
        brief.append("- (every contract document carries its required "
                     "groups - a covered control)")
    brief += ["", "## Covered contracts (no gap - refusal-first)", ""]
    for doc in covered_controls:
        brief.append(f"- {doc}: all required groups detectable")
    if not covered_controls:
        brief.append("- (none this run)")
    if exclusions:
        brief += ["", "## What this brief cannot see", "",
                  f"- Exclusions declared by the gateway: {exclusions} "
                  f"(declared, never guessed)."]
    brief_text = "\n".join(brief) + "\n"

    # ---- the posture, enforced pre-write ---------------------------------
    outputs = [("brief", brief_text)]
    proposal_docs = []
    for f in findings:
        doc_text = _proposal_document(f, agent_principal, binding_id,
                                      package_hash, exclusions,
                                      workbench_name)
        proposal_docs.append((f, doc_text))
        outputs.append((f["finding_kind"], doc_text))
    for label, text in outputs:
        low = text.lower()
        for phrase in forbidden:
            if phrase in low:
                raise RuntimeError(
                    f"THE LEGAL CONCLUSION: forbidden vocabulary {phrase!r} "
                    f"in {label} - refused at the source.")

    brief_path = _write(workspace_dir, f"{workbench_name}-review-brief",
                        brief_text)
    proposal_paths = []
    for f, doc_text in proposal_docs:
        proposal_paths.append(_write(
            proposals_dir, f"{workbench_name}-{f['skill']}", doc_text))

    return {"proposals": sorted(set(proposal_paths)), "findings": findings,
            "brief": brief_path, "skipped": registered_skipped,
            "covered_contracts": covered_controls,
            "register_entries": [e["asset_id"] for e in register_entries],
            "coverage": {d: sorted(c) for d, c in per_doc_classes.items()},
            "exclusions": exclusions, "as_of": str(as_of),
            "contracts": {s: contracts[s]["path"] for s in ACTIVE_SKILLS}}
