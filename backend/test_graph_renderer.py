import hashlib
import json
import os
import shutil
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Reuse the WS1 suite's environment discipline and seeded corpus - one
# seeding vocabulary across the projection gates. Importing it also sets
# EM_NLI_VERIFICATION/OPENAI_API_KEY/EM_SECRET_KEY; the render dir is
# re-pointed below so this suite owns its own output tree.
import test_projection_engine as ws1
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_graph_out_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app.projections import engine as projection_engine
from app.projections.renderers import graph as graph_renderer
from app.projections.renderers import vis_network_js
import test_support

# Graph Renderer suite (v1.3.0 WS2, D28, docs/projection-engine-v1.3.md).
#
# The lens proof: rendered artifacts are disposable, tamper-evident,
# clearance-honest presentation files. Delete every rendered artifact -
# no governed fact is lost; re-render - content-identical artifacts
# come back; corrupt a file on disk - the ledger + manifest alone
# detect it; open graph.html air-gapped - it makes no external request
# of any kind. graphify's export shapes (MIT), governed edition.

TREASURY_MARKER = ws1.TREASURY_MARKER


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_output(project_id, name) -> bytes:
    return ws1.read_output(project_id, "graph", name)


def governed_snapshot(session):
    snapshot = {}
    for table in db.Base.metadata.sorted_tables:
        order = [table.c[c.name] for c in table.primary_key.columns] \
            or list(table.columns)
        rows = session.execute(table.select().order_by(*order)).fetchall()
        snapshot[table.name] = [tuple(repr(v) for v in row) for row in rows]
    return snapshot


def part_1_files_and_shape(session, project, rows, officer):
    print("\n--- Part 1: graph.json + graph.html on the WS1 contract ---")
    summary = projection_engine.render(session, officer, project.id,
                                       renderer="graph",
                                       clearance="EXECUTIVE")
    assert sorted(summary["files"]) == ["graph.html", "graph.json",
                                        "projection.json"]
    graph = json.loads(read_output(project.id, "graph.json"))
    assert graph["schema"] == graph_renderer.GRAPH_SCHEMA
    projection = projection_engine.compose(session, project.id,
                                           clearance="EXECUTIVE")
    assert len(graph["nodes"]) == len(projection.nodes)
    assert len(graph["edges"]) == len(projection.edges)
    # D27 domains fill graphify's community slot: groups come from the
    # taxonomy, and the conflict edge keeps its governed evidence.
    asset_groups = {n["group"] for n in graph["nodes"] if n["kind"] == "ASSET"}
    assert asset_groups == {"finances/accounting", "finances/treasury", "hr"}
    conflict = [e for e in graph["edges"] if e["relation"] == "CONFLICTS_WITH"]
    assert conflict and conflict[0]["metadata"]["classification"] == "SCOPE_CONFLICT"
    # Content identity discipline carries over: no stamps in content.
    raw = read_output(project.id, "graph.json")
    assert b"rendered_at" not in raw and b"audit_cursor" not in raw
    print(f"Part 1 passed: {len(graph['nodes'])} nodes / "
          f"{len(graph['edges'])} edges, domain groups, evidence on edges, "
          f"stamp-free content.")


def part_2_clearance_on_files(session, project, rows, officer):
    print("\n--- Part 2: D9 clearance on the rendered artifacts ---")
    projection_engine.render(session, officer, project.id,
                             renderer="graph", clearance="INTERNAL")
    for name in ("graph.json", "graph.html", "projection.json"):
        assert TREASURY_MARKER.encode() not in read_output(project.id, name), \
            f"EXECUTIVE content leaked into {name} of an INTERNAL render"
    graph = json.loads(read_output(project.id, "graph.json"))
    assert graph["excluded"]["assets_above_clearance"] == 1, \
        "The render itself declares what it excludes"
    print("Part 2 passed: EXECUTIVE content absent from every rendered "
          "byte; the exclusion declared inside the artifact.")


def part_3_air_gap(session, project, officer):
    print("\n--- Part 3: self-contained, air-gap safe ---")
    projection_engine.render(session, officer, project.id, renderer="graph",
                             clearance="EXECUTIVE")
    html = read_output(project.id, "graph.html").decode("utf-8")
    for marker in ("<script src=", "<link ", "unpkg.com", "cdn.",
                   "sourceMappingURL", "http-equiv=\"refresh\""):
        assert marker not in html, f"External reference in graph.html: {marker}"
    assert "@version 9.1.6" in html, "vendored vis-network missing"
    assert vis_network_js.VIS_NETWORK_JS[:2000] in html, \
        "the vendored library must be INLINE, not referenced"
    assert "em-graph-data" in html and "forceAtlas2Based" in html
    print(f"Part 3 passed: one self-contained file "
          f"({len(html) // 1024} KiB), vendored vis-network inline, zero "
          f"external references.")


def part_4_determinism(session, project, officer):
    print("\n--- Part 4: byte-identical renderer output ---")
    projection_engine.render(session, officer, project.id, renderer="graph")
    first = {name: read_output(project.id, name)
             for name in ("graph.json", "graph.html", "projection.json")}
    projection_engine.render(session, officer, project.id, renderer="graph")
    for name, data in first.items():
        assert read_output(project.id, name) == data, \
            f"{name} must be byte-identical for identical facts"
    print("Part 4 passed: graph.json and graph.html byte-identical "
          "across renders.")


def part_5_the_lens_proof(session, project, officer):
    print("\n--- Part 5: THE LENS PROOF (delete everything, lose nothing) ---")
    summary_before = projection_engine.render(
        session, officer, project.id, renderer="graph", clearance="EXECUTIVE")
    before_state = governed_snapshot(session)

    # Delete EVERY rendered artifact, every renderer, the whole tree.
    shutil.rmtree(os.environ["EM_PROJECTION_DIR"])
    assert governed_snapshot(session) == before_state, \
        "D28 violation: deleting renders touched governed state"

    # Re-render: content-identical artifacts return - the ledger-recorded
    # hashes of the destroyed files match the resurrected ones exactly.
    summary_after = projection_engine.render(
        session, officer, project.id, renderer="graph", clearance="EXECUTIVE")
    assert summary_after["files"] == summary_before["files"], \
        "Re-render after total deletion must reproduce identical content"
    assert summary_after["projection_hash"] == summary_before["projection_hash"]
    print("Part 5 passed: total deletion lost no governed fact; "
          "re-render reproduced every file hash exactly.")


def part_6_tamper_evidence(session, project, officer):
    print("\n--- Part 6: tamper detectable from ledger + files alone ---")
    projection_engine.render(session, officer, project.id, renderer="graph",
                             clearance="EXECUTIVE")
    event = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "PROJECTION_RENDERED").order_by(
        db.AuditEvent.id.desc()).first()
    recorded = json.loads(event.details)
    # Fresh render: every disk byte matches the ledger.
    for name, digest in recorded["files"].items():
        assert sha256(read_output(project.id, name)) == digest
    # The adversarial edit: one byte appended to graph.json.
    path = ws1.out_path(project.id, "graph", "graph.json")
    with open(path, "ab") as f:
        f.write(b" ")
    tampered = sha256(read_output(project.id, "graph.json"))
    assert tampered != recorded["files"]["graph.json"], \
        "A tampered render must be detectable from the ledger alone"
    # And governed state never noticed (renders are not inputs).
    fresh = projection_engine.render_history(session, project.id)
    assert fresh[0]["stale"] is False, \
        "File tampering must not read back as governed drift"
    print("Part 6 passed: one tampered byte detected against the ledger "
          "hash; governed state and staleness unaffected.")


def part_7_aggregation(session, project, officer):
    print("\n--- Part 7: the above-limit aggregated fallback ---")
    saved_limit = graph_renderer.NODE_LIMIT
    graph_renderer.NODE_LIMIT = 3
    try:
        projection_engine.render(session, officer, project.id,
                                 renderer="graph", clearance="EXECUTIVE")
        html = read_output(project.id, "graph.html").decode("utf-8")
        graph = json.loads(read_output(project.id, "graph.json"))
        assert '"aggregated":true' in html.replace(" ", ""), \
            "Above the limit, the html view must aggregate"
        assert len(graph["nodes"]) > 3, \
            "graph.json keeps FULL node-level detail regardless of the limit"
    finally:
        graph_renderer.NODE_LIMIT = saved_limit
    projection_engine.render(session, officer, project.id, renderer="graph",
                             clearance="EXECUTIVE")
    print("Part 7 passed: html aggregates above the limit; graph.json "
          "never loses detail; restored below the limit.")


def part_8_custody_sweep(session, project, officer):
    print("\n--- Part 8: the D25 sweep covers the graph surface ---")
    projection_engine.render(session, officer, project.id, renderer="graph",
                             clearance="EXECUTIVE")
    render_root = os.path.join(os.environ["EM_PROJECTION_DIR"],
                               f"project_{project.id}")
    swept = 0
    for root, _dirs, files in os.walk(render_root):
        for name in files:
            with open(os.path.join(root, name), "rb") as f:
                assert ws1.SENTINEL.encode() not in f.read(), \
                    f"D25 violation: sentinel readable in {name}"
            swept += 1
    assert swept >= 4
    print(f"Part 8 passed: {swept} rendered file(s) swept clean.")


def main():
    tmp = tempfile.mkdtemp(prefix="em_graph_db_")
    engine = create_engine(f"sqlite:///{os.path.join(tmp, 'suite.db')}",
                           connect_args={"check_same_thread": False})
    db.engine = engine
    db.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = Session
    session = Session()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    project, rows = ws1.seed(session, officer)
    from app import custody
    custody.create_external_credential(
        session, name="sweep-sentinel", purpose="CONNECTOR",
        secret=ws1.SENTINEL, actor=officer)

    part_1_files_and_shape(session, project, rows, officer)
    part_2_clearance_on_files(session, project, rows, officer)
    part_3_air_gap(session, project, officer)
    part_4_determinism(session, project, officer)
    part_5_the_lens_proof(session, project, officer)
    part_6_tamper_evidence(session, project, officer)
    part_7_aggregation(session, project, officer)
    part_8_custody_sweep(session, project, officer)
    print("\n=== All Graph Renderer (WS2) tests passed successfully! ===")


if __name__ == "__main__":
    main()
