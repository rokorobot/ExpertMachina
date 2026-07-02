import ast
import dataclasses
import json
import os
import shutil
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
# Deterministic rule-based extraction: the sentinel depends on stable
# asset names and types, never on an LLM.
os.environ["OPENAI_API_KEY"] = "mock-key"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import connectors
from app import ingestion
from app import governance_inbox
from app.projections import contract
import test_support
import test_workbench_projection

# D28 structural guard (v1.3.0 WS0, docs/projection-engine-v1.3.md).
#
# The Projection Rule: a projection is a governed lens over the
# knowledge system, never another knowledge system. This guard is
# permanent in CI and establishes the constraint BEFORE the engine
# exists. The user-ratified WS0 gate wording:
#
#   Projection code may read governed facts and emit render
#   artifacts/audit events, but it must not write governed state or
#   create new canonical projection state.
#
#   1. Projection modules cannot write governed state.
#   2. Renderers can import only the projection contract, not
#      persistence/write services.
#   3. No schema changes allowed.
#   4. PROJECTION_RENDERED is the only allowed durable trace.
#   5. A read-back sentinel proves that deleting all render artifacts
#      loses no governed knowledge.
#   6. The D24 snapshot remains unchanged.
#
# And it adversarially self-proves: every checker is run against
# planted violations (a session write in a renderer, a governed-model
# construction, a status write, a foreign event family, a schema
# definition, a read-mode open, a forbidden renderer import, an
# unstamped manifest, a PROJECTION event emitted outside the package)
# and the read-back detector is run against a simulated read-back -
# the guard must catch every plant, or the guard itself fails.
#
# Guarded the way test_connector_seam.py guards D18, the purity
# assertions guard D20, test_workbench_projection.py guards D24,
# test_credential_custody.py guards D25, and
# test_ingestion_automation_guard.py guards D26.

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
PROJECTIONS_PREFIX = "projections/"
RENDERERS_PREFIX = "projections/renderers/"

# Session/connection methods that mutate persistent state. Projection
# code composes lenses; it never expresses a durable write. (Design
# constraint this imposes on WS1/WS2 code: no set.add() either - use
# dict/list idioms. A blunt rule that cannot be argued with beats a
# clever one that can.)
SESSION_MUTATORS = {
    "add", "add_all", "delete", "merge", "flush", "commit",
    "bulk_save_objects", "bulk_insert_mappings", "execute", "executemany",
}

# File/deserialization reads. Projection output is write-only: a module
# that can read a file back could make a render an input, and renders
# are never inputs. (json.loads on governed COLUMN text stays legal -
# loads parses strings; load reads files.)
READ_CALLS = {"read", "readlines", "read_text", "read_bytes", "load"}

# Governed model classes, discovered from the live registry so a future
# model is covered automatically.
GOVERNED_MODELS = {cls.__name__ for cls in db.Base.__subclasses__()}

# Isolated vector store: the dev server holds a lock on ./qdrant_db.
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_projguard_qdrant_")

SYSTEM_SENTENCE = "The reporting platform archives records in a SQLite database server."
POLICY_SENTENCE = "All vendors must sign the data processing agreement before integration."
HOSTILE_SENTENCE = "The reporting platform archives records in a HOSTILE database server."


def app_sources():
    """rel path (posix) -> source, for every module under app/."""
    sources = {}
    for root, _dirs, files in os.walk(APP_DIR):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            rel = os.path.relpath(path, APP_DIR).replace(os.sep, "/")
            with open(path, "r", encoding="utf-8") as f:
                sources[rel] = f.read()
    return sources


def _call_name(node):
    if isinstance(node, ast.Call):
        f = node.func
        return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
    return None


def _event_type_constants(node):
    """Constant event-type strings carried by a call node: the
    event_type/audit_event_type keyword, or the third positional
    argument of log_audit_event(session, actor, event_type)."""
    consts = []
    if isinstance(node, ast.Call):
        for kw in node.keywords:
            if kw.arg in {"event_type", "audit_event_type"} and \
                    isinstance(kw.value, ast.Constant) and \
                    isinstance(kw.value.value, str):
                consts.append(kw.value.value)
        if _call_name(node) == "log_audit_event" and len(node.args) >= 3 \
                and isinstance(node.args[2], ast.Constant) \
                and isinstance(node.args[2].value, str):
            consts.append(node.args[2].value)
    return consts


# ---------------------------------------------------------------- Part 1
# Structural: projection modules cannot write governed state, cannot
# define schema, cannot read files back, and may emit only PROJECTION_*.

def governed_write_violations(module_name, source):
    """Forbidden shapes in a projection module. Any hit means the lens
    is growing hands - the exact erosion D28 forecloses."""
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        name = _call_name(node)
        # (a) No persistent-write session methods.
        if name in SESSION_MUTATORS:
            violations.append(
                f"{module_name}:{node.lineno} calls .{name}() - a durable "
                f"write expression")
        # (b) No governed model construction (AuditEvent included: the
        # ledger is reached only through crud.log_audit_event).
        if name in GOVERNED_MODELS:
            violations.append(
                f"{module_name}:{node.lineno} constructs governed model "
                f"{name} directly")
        # (c) No attribute assignment on anything but self/cls: a lens
        # never mutates an object it was handed.
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute):
                    base = target.value
                    if not (isinstance(base, ast.Name) and base.id in {"self", "cls"}):
                        violations.append(
                            f"{module_name}:{node.lineno} assigns attribute "
                            f".{target.attr} on a non-self object")
                # (d) No schema definition.
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    violations.append(
                        f"{module_name}:{node.lineno} defines __tablename__ "
                        f"- canonical projection state is forbidden")
        if name == "Table":
            violations.append(
                f"{module_name}:{node.lineno} defines a Table - canonical "
                f"projection state is forbidden")
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = base.attr if isinstance(base, ast.Attribute) \
                    else getattr(base, "id", None)
                if base_name == "Base":
                    violations.append(
                        f"{module_name}:{node.lineno} subclasses Base - "
                        f"canonical projection state is forbidden")
        # (e) Write-only file access: open() must carry an explicit
        # write/create mode; read calls are forbidden outright.
        if name == "open":
            mode = None
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if not (isinstance(mode, str) and mode.startswith(("w", "x"))):
                violations.append(
                    f"{module_name}:{node.lineno} opens a file outside an "
                    f"explicit write mode - render output is write-only")
        if name in READ_CALLS and isinstance(node.func, ast.Attribute):
            violations.append(
                f"{module_name}:{node.lineno} calls .{name}() - reading "
                f"artifacts back is forbidden (renders are never inputs)")
        # (f) The only allowed durable trace: PROJECTION_* ledger events.
        for value in _event_type_constants(node):
            if not value.startswith("PROJECTION_"):
                violations.append(
                    f"{module_name}:{node.lineno} emits event family "
                    f"{value!r} - projection code may emit PROJECTION_* only")
    return violations


def part_1_structural():
    print("\n--- Part 1: projection modules cannot write governed state ---")
    sources = app_sources()
    projection_modules = sorted(
        rel for rel in sources if rel.startswith(PROJECTIONS_PREFIX))
    assert projection_modules, "Sanity: the projections package must exist"
    for rel in projection_modules:
        violations = governed_write_violations(rel, sources[rel])
        assert not violations, (
            "D28 violation - the lens is growing hands:\n  "
            + "\n  ".join(violations))
    print(f"Part 1 passed: {len(projection_modules)} projection module(s) "
          f"clean ({', '.join(projection_modules)}).")


# ---------------------------------------------------------------- Part 2
# Structural: renderers import only the stdlib + the projection contract.

def renderer_import_violations(module_name, source):
    """A renderer that can reach persistence or a network client could
    decide content, and deciding content is the engine's monopoly.
    Allowed: the stdlib, the projection contract, and SIBLING modules
    inside projections/renderers (WS2 gate amendment: vendored assets
    live as sibling constant modules, and every sibling is swept by
    these same rules - nothing beyond stdlib + contract is transitively
    reachable). Reaching UP (`from .. import engine`, app.projections.*)
    stays forbidden: the engine can see the database; a renderer that
    can see the engine is a renderer with hands."""
    violations = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in sys.stdlib_module_names:
                    violations.append(
                        f"{module_name}:{node.lineno} imports {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 1:
                # Same-package sibling (swept by these same rules) - fine.
                continue
            if node.level > 1:
                violations.append(
                    f"{module_name}:{node.lineno} relative import reaches "
                    f"above the renderers package "
                    f"({'.' * node.level}{module}) - renderers never see "
                    f"the engine")
                continue
            top = module.split(".")[0]
            if top in sys.stdlib_module_names:
                continue
            names = {a.name for a in node.names}
            if module == "app.projections.contract" or (
                    module == "app.projections" and names <= {"contract"}) or \
                    module.startswith("app.projections.renderers"):
                continue
            violations.append(
                f"{module_name}:{node.lineno} imports {', '.join(sorted(names))} "
                f"from {module} - renderers may import stdlib, "
                f"projections.contract, and renderer siblings only")
    return violations


def part_2_renderer_purity():
    print("\n--- Part 2: renderer import purity ---")
    sources = app_sources()
    renderer_modules = sorted(
        rel for rel in sources if rel.startswith(RENDERERS_PREFIX))
    assert renderer_modules, "Sanity: the renderers package must exist"
    for rel in renderer_modules:
        violations = renderer_import_violations(rel, sources[rel])
        assert not violations, (
            "D28 violation - a renderer reached beyond the contract:\n  "
            + "\n  ".join(violations))
    print(f"Part 2 passed: {len(renderer_modules)} renderer module(s) "
          f"import stdlib + the contract only.")


# ---------------------------------------------------------------- Part 3
# App-wide sweeps: the event family and the render directory belong to
# the projections package alone; the contract stamps are mandatory.

def projection_event_offenders(sources):
    """Modules emitting the PROJECTION_* event family. Must live inside
    the projections package - a module elsewhere writing the family IS
    a second projection path, whatever it calls itself."""
    offenders = set()
    for rel, source in sources.items():
        for node in ast.walk(ast.parse(source)):
            for value in _event_type_constants(node):
                if value.startswith("PROJECTION_"):
                    offenders.add(rel)
    return offenders


def projection_dir_offenders(sources):
    """Modules outside the projections package that name the render
    directory. Nothing outside the lens may even locate its output -
    the structural form of 'renders are never inputs'."""
    return {rel for rel, source in sources.items()
            if "EM_PROJECTION_DIR" in source
            and not rel.startswith(PROJECTIONS_PREFIX)}


def stamp_violations(cls, required):
    have = {f.name for f in dataclasses.fields(cls)}
    return sorted(required - have)


def part_3_sweeps_and_stamps():
    print("\n--- Part 3: event family, render directory, mandatory stamps ---")
    sources = app_sources()
    offenders = projection_event_offenders(sources)
    outside = {rel for rel in offenders if not rel.startswith(PROJECTIONS_PREFIX)}
    assert not outside, (
        f"D28 violation: module(s) {sorted(outside)} emit the PROJECTION_* "
        f"event family outside the projections package.")
    dir_offenders = projection_dir_offenders(sources)
    assert not dir_offenders, (
        f"D28 violation: module(s) {sorted(dir_offenders)} reference "
        f"EM_PROJECTION_DIR outside the projections package.")
    missing = stamp_violations(contract.RenderManifest,
                               contract.REQUIRED_MANIFEST_STAMPS)
    assert not missing, f"D28 violation: RenderManifest lost stamps {missing}"
    missing = stamp_violations(contract.Projection,
                               contract.REQUIRED_PROJECTION_STAMPS)
    assert not missing, f"D28 violation: Projection lost stamps {missing}"
    for shape in (contract.ProjectionNode, contract.ProjectionEdge,
                  contract.Projection, contract.RenderManifest):
        assert shape.__dataclass_params__.frozen, \
            f"{shape.__name__} must be frozen - handed projections are immutable"
    print(f"Part 3 passed: PROJECTION_* family confined to the package "
          f"({len(offenders)} emitter(s) today), render dir named nowhere "
          f"else, all stamps present, all shapes frozen.")


# ---------------------------------------------------------------- Part 4
# Adversarial self-proof: every checker catches its planted violation.

PLANT_SESSION_WRITE = """
def render(session, projection):
    session.add(row)
    session.commit()
"""

PLANT_MODEL_CONSTRUCTION = """
def render(db, projection):
    row = db.KnowledgeAsset(name="from-a-render")
"""

PLANT_STATUS_WRITE = """
def render(asset):
    asset.status = "APPROVED"
"""

PLANT_FOREIGN_EVENT = """
def render(session, crud):
    crud.log_audit_event(session, "renderer", "ASSET_AUTO_APPROVED")
"""

PLANT_SCHEMA = """
class ProjectionRun(Base):
    __tablename__ = "projection_runs"
"""

PLANT_READ_BACK = """
def refresh(path):
    with open(path) as f:
        return json.load(f)
"""

PLANT_RENDERER_IMPORT = """
import json
from app.projections.contract import Projection
from app import crud
"""

PLANT_RENDERER_REACH_UP = """
from . import vis_network_js
from .. import engine
"""

PLANT_CLEAN_RENDERER = """
import json
from app.projections.contract import Projection, RenderManifest

def render(projection, out_path):
    payload = {"nodes": [n.label for n in projection.nodes]}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, sort_keys=True)
"""


def part_4_self_proof():
    print("\n--- Part 4: checker self-proof (planted violations) ---")
    plants = {
        "session write in a renderer": PLANT_SESSION_WRITE,
        "governed model construction": PLANT_MODEL_CONSTRUCTION,
        "status write": PLANT_STATUS_WRITE,
        "foreign event family emission": PLANT_FOREIGN_EVENT,
        "schema definition (canonical projection state)": PLANT_SCHEMA,
        "read-mode open + json.load read-back": PLANT_READ_BACK,
    }
    for label, source in plants.items():
        violations = governed_write_violations("planted.py", source)
        assert violations, f"Self-proof FAILED: the checker missed a {label}"
    import_violations = renderer_import_violations(
        "planted.py", PLANT_RENDERER_IMPORT)
    assert import_violations and all("crud" in v for v in import_violations), \
        "Self-proof FAILED: the import checker missed a persistence import"
    reach_up = renderer_import_violations("planted.py", PLANT_RENDERER_REACH_UP)
    assert len(reach_up) == 1 and "above the renderers package" in reach_up[0], \
        "Self-proof FAILED: sibling import must pass, reaching up must not"
    # Emission outside the package is flagged by the sweep.
    offenders = projection_event_offenders({
        "main.py": 'log_audit_event(s, "x", "PROJECTION_RENDERED")',
        "projections/engine.py": 'log_audit_event(s, "x", "PROJECTION_RENDERED")',
    })
    assert offenders == {"main.py", "projections/engine.py"}, offenders
    # An unstamped manifest fails the stamp check.
    @dataclasses.dataclass
    class UnstampedManifest:
        renderer: str
    missing = stamp_violations(UnstampedManifest,
                               contract.REQUIRED_MANIFEST_STAMPS)
    assert missing, "Self-proof FAILED: an unstamped manifest passed"
    # The canonical renderer shape stays clean under BOTH checkers.
    assert not governed_write_violations("clean.py", PLANT_CLEAN_RENDERER)
    assert not renderer_import_violations("clean.py", PLANT_CLEAN_RENDERER)
    print(f"Part 4 passed: {len(plants) + 4} planted violations caught; "
          f"the canonical renderer shape stays clean.")


# ---------------------------------------------------------------- Part 5
# The read-back sentinel (end-to-end): governed knowledge and its
# computed views are independent of render artifacts - adversarially
# edited renders change nothing, and deleting every render loses nothing.

def governed_snapshot(session):
    """Every row of every governed table, deterministically ordered."""
    snapshot = {}
    for table in db.Base.metadata.sorted_tables:
        order = [table.c[c.name] for c in table.primary_key.columns] \
            or list(table.columns)
        rows = session.execute(table.select().order_by(*order)).fetchall()
        snapshot[table.name] = [tuple(repr(v) for v in row) for row in rows]
    return snapshot


def read_surface(session, project_id):
    """Representative computed views + governed reads, canonicalized."""
    inbox = governance_inbox.build_inbox(session, project_id)
    # generated_at is the inbox's own computed-at stamp - it varies per
    # call by design and is not governed state.
    inbox.pop("generated_at", None)
    assets = [(a.name, a.type, a.status, a.content, a.domain)
              for a in session.query(db.KnowledgeAsset)
              .filter(db.KnowledgeAsset.project_id == project_id)
              .order_by(db.KnowledgeAsset.id)]
    return json.dumps({"inbox": inbox, "assets": assets},
                      sort_keys=True, default=str)


def hostile_render_dir():
    """Adversarially edited render artifacts: files that CLAIM different
    governed facts and a manifest that CLAIMS a future ledger cursor.
    If any code path treats these as inputs, the sentinel fires."""
    render_dir = tempfile.mkdtemp(prefix="em_projguard_renders_")
    with open(os.path.join(render_dir, "graph.json"), "w", encoding="utf-8") as f:
        json.dump({"nodes": [{"id": "asset:1", "label": "HOSTILE",
                              "excerpt": HOSTILE_SENTENCE,
                              "status": "APPROVED"}],
                   "edges": [], "audit_cursor": 999999}, f)
    with open(os.path.join(render_dir, "graph.html"), "w", encoding="utf-8") as f:
        f.write("<html><script>window.owned=true</script>HOSTILE</html>")
    with open(os.path.join(render_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"renderer": "graph", "engine_version": "hostile",
                   "rendered_at": "2099-01-01T00:00:00Z",
                   "audit_cursor": 999999,
                   "files": {"graph.json": "0" * 64}}, f)
    return render_dir


def part_5_read_back_sentinel():
    print("\n--- Part 5: read-back sentinel (renders are never inputs) ---")
    tmp = tempfile.mkdtemp(prefix="em_projguard_db_")
    engine = create_engine(f"sqlite:///{os.path.join(tmp, 'guard.db')}",
                           connect_args={"check_same_thread": False})
    db.engine = engine
    db.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = Session
    session = Session()

    customer = crud.get_or_create_default_customer(session)
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Lens Sentinel", description="D28 guard",
        customer_id=customer.id), actor=officer)
    folder = tempfile.mkdtemp(prefix="em_projguard_src_")
    with open(os.path.join(folder, "doc.txt"), "w", encoding="utf-8") as f:
        f.write(SYSTEM_SENTENCE + "\n" + POLICY_SENTENCE + "\n")
    connector = db.SourceConnector(project_id=project.id, name="Guard Share",
                                   type="LOCAL_FOLDER", root_path=folder,
                                   include_extensions=".txt")
    session.add(connector)
    session.commit()
    session.refresh(connector)

    job = db.IngestionJob(project_id=project.id, connector_id=connector.id,
                          status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    connectors.execute_ingestion_job(session, job.id)
    session.refresh(job)
    assert job.status == "COMPLETED", f"{job.status} / {job.error}"
    asset_count = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id).count()
    assert asset_count > 0, "Sentinel not armed: seeding produced no assets"

    # Plant the hostile renders and point the platform's render dir at them.
    render_dir = hostile_render_dir()
    os.environ["EM_PROJECTION_DIR"] = render_dir
    try:
        before_state = governed_snapshot(session)
        before_reads = read_surface(session, project.id)

        # Exercise reads with hostile artifacts present: nothing changes.
        again = read_surface(session, project.id)
        assert again == before_reads
        assert governed_snapshot(session) == before_state, (
            "D28 violation: reading computed views with hostile render "
            "artifacts present changed governed state")

        # Delete EVERY render artifact: no governed knowledge is lost,
        # and every computed view still answers identically.
        shutil.rmtree(render_dir)
        after_reads = read_surface(session, project.id)
        assert after_reads == before_reads, (
            "D28 violation: a computed view depended on render artifacts")
        assert governed_snapshot(session) == before_state, (
            "D28 violation: deleting render artifacts changed governed state")

        # Ingestion is equally blind: a rescan with the (now dangling)
        # render dir configured neither ingests hostile claims nor emits
        # projection events.
        job2 = db.IngestionJob(project_id=project.id,
                               connector_id=connector.id, status="PENDING")
        session.add(job2)
        session.commit()
        session.refresh(job2)
        connectors.execute_ingestion_job(session, job2.id)
        session.refresh(job2)
        assert job2.status == "COMPLETED"
        hostile = session.query(db.KnowledgeAsset).filter(
            db.KnowledgeAsset.content.contains("HOSTILE")).count()
        assert hostile == 0, "D28 violation: hostile render content was ingested"
        projection_events = session.query(db.AuditEvent).filter(
            db.AuditEvent.event_type.like("PROJECTION_%")).count()
        assert projection_events == 0, (
            "D28 violation: a hostile manifest was replayed into the ledger")
        print(f"Part 5 passed: hostile renders inert, deletion lost nothing "
              f"({asset_count} asset(s), {len(before_state)} tables "
              f"byte-identical), rescan blind to render content.")

        # Self-proof: the detectors are not vacuous. A simulated
        # read-back (governed content mutated as if a render had been
        # ingested) must trip both the snapshot and the read surface.
        print("\n--- Part 5b: sentinel self-proof (simulated read-back) ---")
        victim = session.query(db.KnowledgeAsset).filter(
            db.KnowledgeAsset.project_id == project.id).first()
        original = victim.content
        victim.content = HOSTILE_SENTENCE
        session.commit()
        assert governed_snapshot(session) != before_state, \
            "Self-proof FAILED: the snapshot missed a governed mutation"
        assert read_surface(session, project.id) != before_reads, \
            "Self-proof FAILED: the read surface missed a governed mutation"
        victim.content = original
        session.commit()
        assert read_surface(session, project.id) == before_reads
        print("Part 5b passed: simulated read-back caught by both "
              "detectors, clean after restore.")
    finally:
        os.environ.pop("EM_PROJECTION_DIR", None)


# ---------------------------------------------------------------- Part 6
# Zero schema change FROM PROJECTION WORK: the live schema is identical
# to the ratified D24 snapshot - projections never earn tables. The
# count tracks the CURRENT ratified snapshot (it moves ONLY when a
# ratified decision amends FROZEN_SCHEMA in the same commit):
#   28/303 at v1.3.0 (D28 - the milestone's constitutional claim: the
#     v1.2.1 snapshot survived byte-identical),
#   28/305 at v1.4.0 WS0 (D29/D30, docs/diagnostic-workbench-v1.4.md:
#     knowledge_assets.source_class + source_connectors.lane - neither
#     is projection state; renders still live in the ledger).

def part_6_zero_schema():
    print("\n--- Part 6: zero schema change (the constitutional claim) ---")
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    frozen = test_workbench_projection.FROZEN_SCHEMA
    assert live == frozen, (
        "D28 violation: the schema diverged from the ratified D24 "
        "snapshot. A projection engine that needs schema is another "
        "knowledge system - projection work may never be the reason "
        "FROZEN_SCHEMA changes.")
    tables = len(frozen)
    columns = sum(len(cols) for cols in frozen.values())
    assert (tables, columns) == (28, 305), (tables, columns)
    print(f"Part 6 passed: schema identical to the ratified D24 snapshot "
          f"({tables} tables, {columns} columns) - renders live in the "
          f"ledger, not in tables.")


def main():
    part_1_structural()
    part_2_renderer_purity()
    part_3_sweeps_and_stamps()
    part_4_self_proof()
    part_5_read_back_sentinel()
    part_6_zero_schema()
    print("\nAll D28 projection guard checks passed: projection code "
          "cannot write governed state, renderers import only the "
          "contract, PROJECTION_* is the only durable trace, renders are "
          "never inputs, and the schema is unchanged - all adversarially "
          "self-proven.")


if __name__ == "__main__":
    main()
