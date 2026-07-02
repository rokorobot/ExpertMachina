"""The graph renderer (v1.3.0 WS2, D28): graph.json + graph.html.

Ported from graphify's export layer (https://github.com/rokorobot/graphify,
MIT License, (c) 2026 Safi Shamsi) - the to_json node-link shape and the
to_html interactive vis-network visualization (search, click-to-inspect,
group filter, physics clustering, aggregated meta-graph fallback above a
node limit) - adapted to the projection rule:

- Nodes and edges arrive as a completed, clearance-filtered Projection;
  this module never decides content (D28: renderers present; the
  projection engine decides).
- D27 domain paths fill graphify's community slot: no community
  detection, no LLM labeling - the governed taxonomy IS the grouping.
- vis-network is vendored inline (sibling constant module), so a
  rendered graph.html is fully self-contained: no CDN, no network
  access, air-gap safe.
- Output is returned as bytes to the engine, which writes, stamps, and
  records it. Deterministic: same projection = byte-identical files;
  no timestamps in here - ever (stamps live in the manifest).
"""
import json

from app.projections.contract import Projection
from . import vis_network_js

GRAPH_SCHEMA = "em-graph-v1"
# Above this many nodes the full physics view stops being useful;
# graphify's fallback: an aggregated meta-graph, here per domain group
# (and per kind for the non-asset chain). A fixed constant, not an env
# knob - renders must not vary with ambient environment (determinism).
NODE_LIMIT = 400

_KIND_SHAPES = {"ASSET": "dot", "DOCUMENT": "square",
                "EXPERT_MODEL": "diamond", "PACKAGE": "hexagon",
                "SELECTION": "triangle", "BINDING": "triangleDown",
                "PRINCIPAL": "star"}
_RELATION_STYLES = {
    "CONFLICTS_WITH": {"color": "#dc2626", "dashes": True, "width": 2},
    "SUPPORTS": {"color": "#16a34a", "dashes": False, "width": 2},
    "PROVENANCE": {"color": "#94a3b8", "dashes": False, "width": 1},
    "MEMBER_OF": {"color": "#64748b", "dashes": False, "width": 1},
    "COMPILED_FROM": {"color": "#7c3aed", "dashes": False, "width": 1},
    "SELECTED": {"color": "#2563eb", "dashes": False, "width": 1},
    "BOUND_TO": {"color": "#0891b2", "dashes": False, "width": 1},
}


def _group_of(node) -> str:
    if node.kind == "ASSET":
        return node.domain or "(unclassified)"
    return f"({node.kind.lower()})"


def to_graph_json(projection: Projection) -> dict:
    """The node-link shape (graphify's to_json, governed edition). Pure
    content - no cursor, no timestamps: the same content-identity
    discipline as projection.json."""
    return {
        "schema": GRAPH_SCHEMA,
        "generated_by": f"expertmachina {projection.engine_version}",
        "project_id": projection.project_id,
        "clearance": projection.clearance,
        "status_inclusion": list(projection.status_inclusion),
        "scope": projection.scope,
        "excluded": projection.excluded,
        "groups": projection.groups,
        "nodes": [{"id": n.id, "kind": n.kind, "label": n.label,
                   "status": n.status, "domain": n.domain,
                   "group": _group_of(n), "excerpt": n.excerpt,
                   "metadata": n.metadata} for n in projection.nodes],
        "edges": [{"from": e.source_id, "to": e.target_id,
                   "relation": e.relation, "metadata": e.metadata}
                  for e in projection.edges],
    }


def _aggregate(graph: dict) -> dict:
    """graphify's above-limit fallback: collapse to one meta-node per
    group, edges collapsed to weighted cross-group counts."""
    member_counts = {}
    node_groups = {}
    for node in graph["nodes"]:
        node_groups[node["id"]] = node["group"]
        member_counts[node["group"]] = member_counts.get(node["group"], 0) + 1
    edge_counts = {}
    for edge in graph["edges"]:
        gf = node_groups.get(edge["from"])
        gt = node_groups.get(edge["to"])
        if gf is not None and gt is not None and gf != gt:
            key = (min(gf, gt), max(gf, gt))
            edge_counts[key] = edge_counts.get(key, 0) + 1
    return {
        "aggregated": True,
        "nodes": [{"id": group, "kind": "GROUP", "label": group,
                   "group": group, "status": None, "domain": None,
                   "excerpt": None,
                   "metadata": {"members": count}}
                  for group, count in sorted(member_counts.items())],
        "edges": [{"from": a, "to": b, "relation": "CROSS_GROUP",
                   "metadata": {"weight": weight}}
                  for (a, b), weight in sorted(edge_counts.items())],
    }


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ExpertMachina - governed projection (project __PROJECT_ID__)</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, sans-serif; background: #f8fafc; }
  #bar { display: flex; gap: 12px; align-items: center; padding: 10px 16px;
         background: #0f172a; color: #e2e8f0; flex-wrap: wrap; }
  #bar h1 { font-size: 14px; margin: 0; font-weight: 600; }
  #bar .stamp { font-size: 11px; color: #94a3b8; }
  #bar input, #bar select { font-size: 12px; padding: 4px 8px;
         border-radius: 4px; border: 1px solid #334155;
         background: #1e293b; color: #e2e8f0; }
  #banner { padding: 6px 16px; background: #fef3c7; color: #92400e;
            font-size: 12px; display: none; }
  #wrap { display: flex; height: calc(100vh - 46px); }
  #net { flex: 1; }
  #inspect { width: 320px; border-left: 1px solid #e2e8f0; padding: 14px;
             overflow-y: auto; background: #ffffff; font-size: 13px; }
  #inspect h2 { font-size: 13px; margin: 0 0 6px; }
  #inspect .kind { font-size: 10px; letter-spacing: .08em; color: #64748b; }
  #inspect .excerpt { white-space: pre-wrap; background: #f1f5f9;
             border-radius: 6px; padding: 8px; font-size: 12px; }
  #inspect dl { margin: 8px 0; } #inspect dt { font-size: 10px; color: #64748b;
             text-transform: uppercase; letter-spacing: .06em; margin-top: 6px; }
  #inspect dd { margin: 0; font-size: 12px; word-break: break-all; }
  #legend { padding: 8px 0 0; border-top: 1px solid #e2e8f0; margin-top: 10px; }
  #legend span { display: inline-block; font-size: 10px; margin: 2px 8px 2px 0; }
  #legend i { display: inline-block; width: 14px; height: 3px;
              vertical-align: middle; margin-right: 4px; }
</style>
</head>
<body>
<div id="bar">
  <h1>Governed projection - project __PROJECT_ID__</h1>
  <span class="stamp">clearance __CLEARANCE__ &middot; statuses __STATUSES__ &middot;
    a regenerated lens over governed facts - never a source (D28);
    stamps live in manifest.json</span>
  <input id="search" placeholder="Search nodes..." aria-label="Search nodes">
  <select id="groupFilter" aria-label="Filter by group"><option value="">All groups</option></select>
</div>
<div id="banner"></div>
<div id="wrap">
  <div id="net"></div>
  <aside id="inspect"><h2>Inspect</h2>
    <p style="color:#64748b">Click a node. Search and the group filter
    narrow the view; everything shown is a clearance-filtered projection
    of governed facts.</p>
    <div id="detail"></div>
    <div id="legend"></div>
  </aside>
</div>
<script>
/* vendored vis-network (see module header for license + hash) */
__VIS_NETWORK_JS__
</script>
<script id="em-graph-data" type="application/json">
__GRAPH_JSON__
</script>
<script>
(function () {
  "use strict";
  const RELATION_STYLES = __RELATION_STYLES__;
  const KIND_SHAPES = __KIND_SHAPES__;
  const graph = JSON.parse(document.getElementById("em-graph-data").textContent);
  const view = graph.view;
  if (view.aggregated) {
    const banner = document.getElementById("banner");
    banner.style.display = "block";
    banner.textContent = "Aggregated view: " + graph.nodes.length +
      " nodes exceed the interactive limit - one meta-node per group. " +
      "graph.json carries the full node-level detail.";
  }
  const degree = {};
  view.edges.forEach(e => {
    degree[e.from] = (degree[e.from] || 0) + 1;
    degree[e.to] = (degree[e.to] || 0) + 1;
  });
  const nodeIndex = {};
  view.nodes.forEach(n => { nodeIndex[n.id] = n; });
  const visNodes = new vis.DataSet(view.nodes.map(n => ({
    id: n.id,
    label: n.label.length > 34 ? n.label.slice(0, 31) + "..." : n.label,
    group: n.group,
    shape: KIND_SHAPES[n.kind] || "dot",
    value: (degree[n.id] || 1) + (n.metadata && n.metadata.members ? n.metadata.members : 0),
    title: n.kind + (n.status ? " - " + n.status : ""),
  })));
  const visEdges = new vis.DataSet(view.edges.map((e, i) => {
    const style = RELATION_STYLES[e.relation] ||
      { color: "#cbd5e1", dashes: false, width: 1 };
    return { id: "e" + i, from: e.from, to: e.to,
             color: { color: style.color }, dashes: style.dashes,
             width: style.width + (e.metadata && e.metadata.weight ?
               Math.min(Math.log(e.metadata.weight + 1), 4) : 0),
             arrows: "to", title: e.relation };
  }));
  const network = new vis.Network(document.getElementById("net"),
    { nodes: visNodes, edges: visEdges },
    { physics: { solver: "forceAtlas2Based",
                 forceAtlas2Based: { gravitationalConstant: -60,
                                     springLength: 120 },
                 stabilization: { iterations: 220 } },
      nodes: { scaling: { min: 8, max: 34 },
               font: { size: 12, color: "#0f172a" } },
      interaction: { hover: true, tooltipDelay: 120 } });

  const detail = document.getElementById("detail");
  function inspect(id) {
    const n = nodeIndex[id];
    if (!n) { return; }
    detail.replaceChildren();
    const kind = document.createElement("div");
    kind.className = "kind"; kind.textContent = n.kind;
    const title = document.createElement("h2"); title.textContent = n.label;
    detail.append(kind, title);
    const dl = document.createElement("dl");
    [["status", n.status], ["domain", n.domain], ["group", n.group]]
      .concat(Object.entries(n.metadata || {}))
      .forEach(([k, v]) => {
        if (v === null || v === undefined || v === "") { return; }
        const dt = document.createElement("dt"); dt.textContent = k;
        const dd = document.createElement("dd"); dd.textContent = String(v);
        dl.append(dt, dd);
      });
    detail.append(dl);
    if (n.excerpt) {
      const ex = document.createElement("div");
      ex.className = "excerpt"; ex.textContent = n.excerpt;
      detail.append(ex);
    }
  }
  network.on("click", p => { if (p.nodes.length) { inspect(p.nodes[0]); } });

  const groups = [...new Set(view.nodes.map(n => n.group))].sort();
  const groupFilter = document.getElementById("groupFilter");
  groups.forEach(g => {
    const opt = document.createElement("option");
    opt.value = g; opt.textContent = g; groupFilter.append(opt);
  });
  const search = document.getElementById("search");
  function applyFilters() {
    const q = search.value.toLowerCase();
    const g = groupFilter.value;
    view.nodes.forEach(n => {
      const visible = (!q || n.label.toLowerCase().includes(q)) &&
                      (!g || n.group === g);
      visNodes.update({ id: n.id, hidden: !visible });
    });
  }
  search.addEventListener("input", applyFilters);
  groupFilter.addEventListener("change", applyFilters);

  const legend = document.getElementById("legend");
  Object.entries(RELATION_STYLES).forEach(([relation, style]) => {
    const chip = document.createElement("span");
    const swatch = document.createElement("i");
    swatch.style.background = style.color;
    chip.append(swatch, document.createTextNode(relation));
    legend.append(chip);
  });
})();
</script>
</body>
</html>
"""


def _embed_json(payload) -> str:
    """Deterministic serialization, safe to inline in a <script> block:
    '</' can never terminate the containing tag."""
    return json.dumps(payload, sort_keys=True,
                      separators=(",", ":")).replace("</", "<\\/")


def to_graph_html(projection: Projection) -> str:
    """graphify's to_html, governed edition: one self-contained file."""
    graph = to_graph_json(projection)
    if len(graph["nodes"]) > NODE_LIMIT:
        view = _aggregate(graph)
    else:
        view = {"aggregated": False, "nodes": graph["nodes"],
                "edges": graph["edges"]}
    payload = {**graph, "view": view}
    return (_HTML_TEMPLATE
            .replace("__PROJECT_ID__", str(projection.project_id))
            .replace("__CLEARANCE__", projection.clearance)
            .replace("__STATUSES__", "/".join(projection.status_inclusion))
            .replace("__VIS_NETWORK_JS__", vis_network_js.VIS_NETWORK_JS)
            .replace("__GRAPH_JSON__", _embed_json(payload))
            .replace("__RELATION_STYLES__", _embed_json(_RELATION_STYLES))
            .replace("__KIND_SHAPES__", _embed_json(_KIND_SHAPES)))


def render_files(projection: Projection) -> dict:
    """The renderer entry point the engine's registry calls: filename ->
    bytes, nothing else - the engine writes, stamps, and records."""
    return {
        "graph.json": json.dumps(to_graph_json(projection), sort_keys=True,
                                 indent=1).encode("utf-8"),
        "graph.html": to_graph_html(projection).encode("utf-8"),
    }
