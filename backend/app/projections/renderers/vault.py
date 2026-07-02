"""EM Vault renderer (v1.5 WS1, D31) - the projection engine's second
renderer: the governed knowledge tree as a deterministic Markdown vault.

The WS1 claim (user-ratified): render approved governed knowledge into
a deterministic Markdown vault tree with domain-first organization,
full governed content where clearance permits, YAML frontmatter,
wikilinks, DERIVED marking, and manifest-backed regeneration. The vault
is readable by humans and agents, but remains a projection only -
readable and useful, yes; authoritative, no.

Renderer disciplines (D28 + D31, guard-enforced):
  - imports: stdlib + the projection contract (+ swept siblings) ONLY;
    this module never sees the session, never filters, never decides
    content - it receives a completed, clearance-filtered FULL_CONTENT
    projection and chooses only its shape on disk;
  - deterministic bytes: same projection -> byte-identical files. The
    volatile stamps (rendered_at, audit cursor, manifest hash) live in
    the engine-written manifest.json and the PROJECTION_RENDERED event,
    NEVER inside note bytes - otherwise every re-render would look like
    drift and the disappearance test could not reproduce ledger hashes.
    Every note links to the render manifest instead of embedding it;
  - every note is visibly a derived render, never canonical: the
    frontmatter says em_rendered/derived/canonical and the body says
    "This note is not canonical." in plain sight;
  - plain Markdown + YAML frontmatter + wikilinks - no .obsidian, no
    plugins, no git machinery (Obsidian compatibility is a property,
    not a dependency);
  - managed folders only: 01_overview, 02_knowledge, 03_domains,
    04_indexes, 05_conflicts, 06_audit (the user-ratified WS1 shape);
    the engine's floor keeps everything else out of reach.

Deliberately not rendered (recorded at the WS1 gate): a "Summary"
section (mechanical truncation adds nothing over the content, and
anything more would be synthesis - D15); a glossary index (no governed
fact species backs one; inventing it would be synthesis); expert/
package notes (they surface through 04_indexes; the .empkg remains the
package artifact).
"""
import json

from app.projections import contract

MANAGED_FOLDERS = ("01_overview", "02_knowledge", "03_domains",
                   "04_indexes", "05_conflicts", "06_audit")
GOVERNANCE_FOLDER = "06_audit"
UNCLASSIFIED = "_unclassified"

NOT_CANONICAL = (
    "> Derived render from ExpertMachina governed knowledge.\n"
    "> **This note is not canonical.** The canonical source remains the\n"
    "> governed asset record; this file is a disposable projection -\n"
    "> delete it and nothing is lost, regenerate it and it returns\n"
    "> byte-identical. Render authority dies at ingress (D31).\n")
DERIVED_NOTICE = (
    "> **DERIVED** - agent-synthesized knowledge, accepted by a human at\n"
    "> the governed gate. Primary prevails in conflicts unless a human\n"
    "> rules otherwise (D30).\n")


def _slug(text: str) -> str:
    out = []
    for ch in (text or "").lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "_":
            out.append("_")
    return "".join(out).strip("_") or "untitled"


def _yaml_value(value):
    """YAML-safe scalars via JSON (a strict YAML subset for strings,
    numbers, booleans, and null)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    return json.dumps(str(value), ensure_ascii=False)


def _frontmatter(pairs) -> str:
    lines = ["---"]
    for key, value in pairs:
        lines.append(f"{key}: {_yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _asset_id(node) -> int:
    return int(node.id.partition(":")[2])


def _note_stem(node) -> str:
    return f"asset_{_asset_id(node)}_{_slug(node.label)}"


def _domain_stem(domain) -> str:
    return f"domain_{_slug(domain or UNCLASSIFIED)}"


def _domain_folder(domain) -> str:
    if not domain:
        return UNCLASSIFIED
    return "/".join(_slug(part) for part in domain.split("/"))


def _conflict_stem(edge, index_by_id) -> str:
    a = index_by_id[edge.source_id]
    b = index_by_id[edge.target_id]
    return f"conflict_{_asset_id(a)}_{_asset_id(b)}"


def render_files(projection: contract.Projection) -> dict:
    """{relative path: text} - every path inside the managed folders,
    every byte a pure function of the projection."""
    if projection.content_mode != contract.FULL_CONTENT:
        raise ValueError(
            "The vault renderer requires a declared FULL_CONTENT "
            "projection - a workspace of excerpts is not human-readable "
            "knowledge (v1.5 scoping ruling 1)")

    files = {}
    nodes_by_id = {n.id: n for n in projection.nodes}
    assets = sorted((n for n in projection.nodes if n.kind == "ASSET"),
                    key=_asset_id)
    documents = {n.id: n for n in projection.nodes if n.kind == "DOCUMENT"}
    packages = sorted((n for n in projection.nodes if n.kind == "PACKAGE"),
                      key=lambda n: int(n.id.partition(":")[2]))

    provenance_by_asset = {}
    conflict_edges = []
    support_edges = []
    for edge in projection.edges:
        if edge.relation == "PROVENANCE":
            provenance_by_asset[edge.source_id] = edge.target_id
        elif edge.relation == "CONFLICTS_WITH":
            if edge.source_id in nodes_by_id and edge.target_id in nodes_by_id:
                conflict_edges.append(edge)
        elif edge.relation == "SUPPORTS":
            if edge.source_id in nodes_by_id and edge.target_id in nodes_by_id:
                support_edges.append(edge)
    conflicts_by_asset = {}
    for edge in conflict_edges:
        conflicts_by_asset.setdefault(edge.source_id, []).append(edge)
        conflicts_by_asset.setdefault(edge.target_id, []).append(edge)

    domains = {}  # domain value (or None) -> [asset nodes]
    for node in assets:
        domains.setdefault(node.domain, []).append(node)

    # ---- 02_knowledge: one note per approved governed asset.
    for node in assets:
        meta = node.metadata or {}
        stem = _note_stem(node)
        front = _frontmatter([
            ("em_rendered", True),
            ("derived", True),
            ("canonical", False),
            ("projection_type", "VAULT_KNOWLEDGE_NOTE"),
            ("content_mode", projection.content_mode),
            ("asset_id", _asset_id(node)),
            ("asset_title", node.label),
            ("asset_type", meta.get("type")),
            ("asset_status", node.status),
            ("asset_clearance", meta.get("access_level")),
            ("source_class", meta.get("source_class")),
            ("domain", node.domain),
            ("source_hash", meta.get("source_hash")),
            ("engine_version", projection.engine_version),
        ])
        body = [f"# {node.label}", "", NOT_CANONICAL.rstrip()]
        if meta.get("source_class") == "DERIVED":
            body += ["", DERIVED_NOTICE.rstrip()]
        body += ["", "## Governed Content", "", node.content or ""]
        source_lines = ["", "## Source", ""]
        source_lines.append(f"- Domain: [[{_domain_stem(node.domain)}]]")
        doc_id = provenance_by_asset.get(node.id)
        if doc_id and doc_id in documents:
            source_lines.append(
                f"- Source document: {documents[doc_id].label} ({doc_id})")
        for edge in sorted(conflicts_by_asset.get(node.id, []),
                           key=lambda e: (e.source_id, e.target_id)):
            other = edge.target_id if edge.source_id == node.id else edge.source_id
            asym = (edge.metadata or {}).get("class_asymmetry")
            note = " - primary prevails" if asym else ""
            source_lines.append(
                f"- Conflicts with [[{_note_stem(nodes_by_id[other])}]] "
                f"([[{_conflict_stem(edge, nodes_by_id)}]]"
                f", {(edge.metadata or {}).get('classification')}{note})")
        source_lines.append("- Render manifest: [[render_manifest]]")
        body += source_lines
        files[f"02_knowledge/{_domain_folder(node.domain)}/{stem}.md"] = \
            front + "\n".join(body) + "\n"

    # ---- 03_domains: one index page per domain (honest _unclassified).
    for domain in sorted(domains, key=lambda d: (d is None, d or "")):
        members = sorted(domains[domain], key=_asset_id)
        title = domain or "Unclassified (honestly NULL - D12)"
        lines = [_frontmatter([
            ("em_rendered", True), ("derived", True), ("canonical", False),
            ("projection_type", "VAULT_DOMAIN_INDEX"),
            ("domain", domain),
            ("engine_version", projection.engine_version),
        ])]
        lines.append(f"# {title}\n")
        lines.append(NOT_CANONICAL)
        lines.append("## Knowledge Notes\n")
        for node in members:
            marker = " `DERIVED`" if (node.metadata or {}).get(
                "source_class") == "DERIVED" else ""
            lines.append(f"- [[{_note_stem(node)}]]{marker}")
        domain_conflicts = sorted(
            {(_conflict_stem(e, nodes_by_id))
             for node in members for e in conflicts_by_asset.get(node.id, [])})
        if domain_conflicts:
            lines.append("\n## Conflicts\n")
            for stem in domain_conflicts:
                lines.append(f"- [[{stem}]]")
        files[f"03_domains/{_domain_stem(domain)}.md"] = \
            "\n".join(lines) + "\n"

    # ---- 05_conflicts: one note per visible conflict + index.
    conflict_stems = []
    for edge in sorted(conflict_edges, key=lambda e: (e.source_id, e.target_id)):
        a, b = nodes_by_id[edge.source_id], nodes_by_id[edge.target_id]
        meta = edge.metadata or {}
        stem = _conflict_stem(edge, nodes_by_id)
        conflict_stems.append(stem)
        lines = [_frontmatter([
            ("em_rendered", True), ("derived", True), ("canonical", False),
            ("projection_type", "VAULT_CONFLICT_NOTE"),
            ("classification", meta.get("classification")),
            ("confidence", meta.get("confidence")),
            ("review_status", meta.get("review_status")),
            ("class_asymmetry", meta.get("class_asymmetry")),
            ("engine_version", projection.engine_version),
        ])]
        lines.append(f"# Conflict: {a.label} vs {b.label}\n")
        lines.append(NOT_CANONICAL)
        lines.append(f"- [[{_note_stem(a)}]] "
                     f"(`{(a.metadata or {}).get('source_class')}`)")
        lines.append(f"- [[{_note_stem(b)}]] "
                     f"(`{(b.metadata or {}).get('source_class')}`)")
        lines.append(f"- Classification: {meta.get('classification')} "
                     f"(confidence {meta.get('confidence')})")
        lines.append(f"- Review status: {meta.get('review_status')}")
        if meta.get("class_asymmetry"):
            lines.append("- Primary prevails: the derived side is the "
                         "presumptive review target unless a human rules "
                         "otherwise (D30).")
        lines.append("- Resolution happens in the Knowledge Conflicts "
                     "workbench, never by editing this note.")
        files[f"05_conflicts/{stem}.md"] = "\n".join(lines) + "\n"
    conflict_index = [_frontmatter([
        ("em_rendered", True), ("derived", True), ("canonical", False),
        ("projection_type", "VAULT_INDEX"),
        ("engine_version", projection.engine_version)])]
    conflict_index.append("# Conflicts\n")
    conflict_index.append(NOT_CANONICAL)
    conflict_index += ([f"- [[{stem}]]" for stem in conflict_stems]
                       or ["No visible conflicts in this render's scope."])
    files["05_conflicts/index.md"] = "\n".join(conflict_index) + "\n"

    # ---- 04_indexes: global navigation surfaces.
    def index_file(name, title, body_lines):
        text = [_frontmatter([
            ("em_rendered", True), ("derived", True), ("canonical", False),
            ("projection_type", "VAULT_INDEX"),
            ("engine_version", projection.engine_version)])]
        text.append(f"# {title}\n")
        text.append(NOT_CANONICAL)
        text.extend(body_lines)
        files[f"04_indexes/{name}.md"] = "\n".join(text) + "\n"

    index_file("assets", "All Knowledge Notes", [
        f"- [[{_note_stem(n)}]] - {(n.metadata or {}).get('type')} - "
        f"{n.domain or UNCLASSIFIED}"
        + (" - `DERIVED`" if (n.metadata or {}).get('source_class') == 'DERIVED' else "")
        for n in assets] or ["No assets in this render's scope."])
    index_file("domains", "Domains", [
        f"- [[{_domain_stem(d)}]] ({len(domains[d])} note(s))"
        for d in sorted(domains, key=lambda d: (d is None, d or ""))])
    index_file("conflicts", "Conflict Index", [
        f"- [[{stem}]]" for stem in conflict_stems]
        or ["No visible conflicts in this render's scope."])
    index_file("packages", "Expert Packages", [
        f"- {p.label} - clearance {(p.metadata or {}).get('clearance_level')} - "
        f"hash {((p.metadata or {}).get('package_hash') or '')[:16]}... "
        f"(the .empkg is the portable content artifact; consume it there or "
        f"via the MCP gateway - packages have no vault notes by design)"
        for p in packages] or ["No compiled packages in this render's scope."])

    # ---- 01_overview: the landing surfaces.
    files["01_overview/index.md"] = "\n".join([
        _frontmatter([
            ("em_rendered", True), ("derived", True), ("canonical", False),
            ("projection_type", "VAULT_OVERVIEW"),
            ("engine_version", projection.engine_version)]),
        "# ExpertMachina Vault Render\n",
        NOT_CANONICAL,
        "Rendered from governed ExpertMachina knowledge. This vault is a",
        "derived projection only. Canonical knowledge remains in the",
        "governed database.\n",
        "## Navigation\n",
        "- [[assets]]",
        "- [[domains]]",
        "- [[conflicts]]",
        "- [[packages]]",
        "- [[source_inventory]]",
        "- [[render_manifest]]",
    ]) + "\n"
    files["01_overview/clearance_scope.md"] = "\n".join([
        _frontmatter([
            ("em_rendered", True), ("derived", True), ("canonical", False),
            ("projection_type", "VAULT_CLEARANCE_SCOPE"),
            ("clearance", projection.clearance),
            ("content_mode", projection.content_mode),
            ("engine_version", projection.engine_version)]),
        "# Clearance & Scope\n",
        NOT_CANONICAL,
        f"- Compiled FOR clearance: **{projection.clearance}** (D9)",
        f"- Status inclusion: {', '.join(projection.status_inclusion)}",
        f"- Domain scope: {projection.scope.get('domain_prefix') or 'whole project'}",
        f"- Content mode: {projection.content_mode} (declared - D31)",
        "\n## Declared exclusions (D12 - nothing is excluded silently)\n",
    ] + [f"- {key}: {value}"
         for key, value in sorted(projection.excluded.items())]) + "\n"
    files["01_overview/render_manifest.md"] = "\n".join([
        _frontmatter([
            ("em_rendered", True), ("derived", True), ("canonical", False),
            ("projection_type", "VAULT_MANIFEST_POINTER"),
            ("engine_version", projection.engine_version)]),
        "# Render Manifest\n",
        NOT_CANONICAL,
        "The volatile render stamps - `rendered_at`, the audit cursor, and",
        "the manifest hash - live in `06_audit/manifest.json` (written and",
        "stamped by the projection engine) and in the PROJECTION_RENDERED",
        "audit event, never inside note bytes: notes stay byte-identical",
        "across re-renders so real drift is detectable and the",
        "disappearance test can reproduce every ledger-recorded hash.",
        "",
        "To verify this vault: compare each file's sha256 against the",
        "`files` map in `06_audit/manifest.json`, and the manifest's own",
        "hash against the ledger event.",
    ]) + "\n"

    # ---- 06_audit: deterministic self-description (the engine adds
    # projection.json + manifest.json here - the governance folder).
    files["06_audit/render_event.md"] = "\n".join([
        _frontmatter([
            ("em_rendered", True), ("derived", True), ("canonical", False),
            ("projection_type", "VAULT_RENDER_EVENT"),
            ("engine_version", projection.engine_version),
            ("content_mode", projection.content_mode),
            ("clearance", projection.clearance)]),
        "# Render Self-Description\n",
        NOT_CANONICAL,
        f"- Engine: {projection.engine_version}",
        f"- Content mode: {projection.content_mode}",
        f"- Clearance: {projection.clearance}",
        f"- Status inclusion: {', '.join(projection.status_inclusion)}",
        f"- Nodes: {len(projection.nodes)} · Edges: {len(projection.edges)}"
        f" · Domain groups: {len(projection.groups)}",
        "- Stamps (`rendered_at`, audit cursor, manifest hash):",
        "  `06_audit/manifest.json` + the PROJECTION_RENDERED ledger event.",
    ]) + "\n"
    files["06_audit/source_inventory.md"] = "\n".join([
        _frontmatter([
            ("em_rendered", True), ("derived", True), ("canonical", False),
            ("projection_type", "VAULT_SOURCE_INVENTORY"),
            ("engine_version", projection.engine_version)]),
        "# Source Inventory\n",
        NOT_CANONICAL,
        "Every governed asset this render projected, with its recorded",
        "source hash - the machine-readable provenance floor.\n",
    ] + [
        f"- asset {_asset_id(n)}: {n.label} - {(n.metadata or {}).get('type')}"
        f" - {n.domain or UNCLASSIFIED} - class "
        f"{(n.metadata or {}).get('source_class')} - source_hash "
        f"{(n.metadata or {}).get('source_hash') or 'none recorded'}"
        for n in assets]) + "\n"

    return files
