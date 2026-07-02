import ast
import json
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_ingress_renders_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

# GUARD 6 - the D31 structural guard (v1.5 WS0, docs/em-vault-v1.5.md).
# The SIXTH permanent guard family, built BEFORE the vault renderer
# exists, guarding the way the five before it guard D24/D25/D26/D28/
# D29+D30.
#
# D31 (Render Authority Dies at Ingress): rendered knowledge may be
# copied, moved, or submitted, but no property of a render - stamps,
# manifest, provenance annotations, vault placement - survives as
# authority when its content re-enters the governed system. A rendered
# file re-enters only as an ordinary document; through the proposal
# lane it becomes at most a held DERIVED candidate - never PRIMARY,
# never auto-approved, never canonical by accident. And the vault is
# one tree with two natures: managed folders are disposable projection
# output; the untouchable folders (00_system / 07_agent_workspaces /
# 08_proposals) are inputs no render path may delete, overwrite, or
# manage.
#
# The guard adversarially self-proves its detectors: the laundering
# catastrophe (an ingested rendered note flipped to APPROVED PRIMARY),
# the floor violations (specs managing untouchable or unknown folders,
# output paths escaping the managed set), and the path-discipline sweep
# plant must all be caught - or the guard itself fails.

_tmpdir = tempfile.mkdtemp(prefix="em_ingress_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'ingress.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_ingress_qdrant_")

from app import schemas  # noqa: E402
from app import crud  # noqa: E402
from app import connectors  # noqa: E402
from app import policy  # noqa: E402
from app import proposals  # noqa: E402
from app import tier2  # noqa: E402
from app import governance_inbox  # noqa: E402
from app.projections import contract  # noqa: E402
from app.projections import engine as projection_engine  # noqa: E402
import test_support  # noqa: E402

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
FLOOR_MODULE = "projections/engine.py"  # the ONLY app module that may name the floor
UNTOUCHABLE_NAMES = ("00_system", "07_agent_workspaces", "08_proposals")

CORPUS = {
    "retention.txt": "The archive platform stores retention ledgers in a SQLite database server.",
    "policy.txt": "All auditors must sign the evidence handling agreement before access.",
}
EXEC_SENTENCE = "The payroll platform stores TOPSECRET-INGRESS salary bands in an Oracle database server."


def write_file(folder, name, text):
    path = os.path.join(folder, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def run_scan(session, connector):
    job = db.IngestionJob(project_id=connector.project_id,
                          connector_id=connector.id, status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    connectors.execute_ingestion_job(session, job.id)
    tier2.drain()
    session.refresh(job)
    assert job.status == "COMPLETED", f"{job.status} / {job.error}"
    return job


def make_vault(base):
    """The v1.4 skeleton shape with planted input content: the guard's
    untouchable plants are what a real deployment holds."""
    plants = {
        os.path.join("00_system", "agent-contract.md"): "# The Vault Contract (planted)\n",
        os.path.join("07_agent_workspaces", "scratch.txt"): "work in progress - agent scratch\n",
        os.path.join("08_proposals", "pending-proposal.md"): "---\nem_proposal: 1\n---\nA pending agent finding.\n",
    }
    for rel, text in plants.items():
        write_file(base, rel, text)
    return plants


def read_tree(base):
    found = {}
    for root, _dirs, files in os.walk(base):
        for name in files:
            path = os.path.join(root, name)
            with open(path, "rb") as f:
                found[os.path.relpath(path, base).replace(os.sep, "/")] = f.read()
    return found


def laundering_violations(session, lane_doc_ids):
    """The D31 detector: every way an ingested rendered file could have
    gained authority."""
    violations = []
    assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_doc_ids or {-1})).all()
    for asset in assets:
        if asset.source_class != "DERIVED":
            violations.append(
                f"lane asset {asset.id} is {asset.source_class}, not DERIVED")
        if asset.status == "APPROVED":
            human_reviews = [r for r in asset.reviews
                             if r.approver and not r.approver.startswith("policy:")]
            if not human_reviews:
                violations.append(
                    f"lane asset {asset.id} APPROVED without a human review")
    for event in session.query(db.AuditEvent).filter_by(
            event_type="ASSET_AUTO_APPROVED").all():
        target = session.query(db.KnowledgeAsset).filter_by(
            id=int(event.target_id)).first() if event.target_id else None
        if target is not None and target.document_id in (lane_doc_ids or set()):
            violations.append(
                f"ASSET_AUTO_APPROVED event {event.id} targets ingested "
                f"rendered content")
    return violations


# ---------------------------------------------------------------- Part 1
# THE LAUNDERING PLANT: rendered artifacts dropped into 08_proposals
# become ordinary proposal evidence behind the valve - nothing more.

def part_1_laundering_plant(session, officer, project, rendered_dir,
                            render_event_count):
    print("\n--- Part 1: THE LAUNDERING PLANT (D31's cornerstone) ---")
    vault = tempfile.mkdtemp(prefix="em_ingress_vault1_")
    make_vault(vault)

    # The rendered artifacts, verbatim: the graph render's files carry
    # every kind of authority a launderer could hope for - manifest
    # stamps, an audit cursor, hashed file claims, "APPROVED" statuses
    # inside projection content.
    with open(os.path.join(rendered_dir, "graph.json"), "r", encoding="utf-8") as f:
        graph_bytes = f.read()
    with open(os.path.join(rendered_dir, "manifest.json"), "r", encoding="utf-8") as f:
        manifest_text = f.read()
    hostile_manifest = json.dumps({**json.loads(manifest_text),
                                   "audit_cursor": 999999})
    write_file(vault, os.path.join("08_proposals", "rendered-note.json"), graph_bytes)
    write_file(vault, os.path.join("08_proposals", "manifest-claim.json"), hostile_manifest)
    # The forged variant: a rendered file dressed as a proposal, claiming
    # a binding that does not exist.
    write_file(vault, os.path.join("08_proposals", "rendered-forged.md"),
               "---\nem_proposal: 1\nagent_principal: onboarding-diagnostic\n"
               "binding_id: 424242\npackage_hash: ph_forged\n---\n" + graph_bytes)

    # The most permissive policy environment constructible (the D26/D29
    # sentinel posture): global policies + a live approve-everything
    # Tier-2 engine.
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add_all([
        db.ApprovalPolicy(project_id=project.id, name="ingress-tier1",
                          asset_types_json=all_types, enabled=True),
        db.ApprovalPolicy(project_id=project.id, name="ingress-tier2",
                          asset_types_json=all_types, enabled=True,
                          engine_conditions_json=json.dumps(
                              {"contradiction_check": "CLEAN_REQUIRED"})),
    ])
    lane = db.SourceConnector(project_id=project.id, name="Ingress Lane",
                              type="LOCAL_FOLDER",
                              root_path=os.path.join(vault, "08_proposals"),
                              include_extensions=".json,.md", lane="PROPOSAL")
    session.add(lane)
    session.commit()
    session.refresh(lane)
    run_scan(session, lane)

    lane_doc_ids = policy.proposal_lane_document_ids(
        session, [d.id for d in session.query(db.Document).filter_by(
            project_id=project.id).all()])
    assert lane_doc_ids, "the rendered files must have been ingested"
    lane_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_doc_ids)).all()
    for asset in lane_assets:
        assert asset.status == "CANDIDATE", (
            f"D31 VIOLATION: ingested rendered content {asset.id} is "
            f"{asset.status} - render authority survived ingress")
        assert asset.source_class == "DERIVED", (
            f"D31 VIOLATION: ingested rendered content {asset.id} is "
            f"{asset.source_class}")
    violations = laundering_violations(session, lane_doc_ids)
    assert not violations, "D31 violations:\n  " + "\n  ".join(violations)

    # Authority death: the manifest's cursor claim replayed nothing -
    # the ledger still holds exactly the renders THIS guard performed,
    # and the render history is untouched by ingestion.
    events_now = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type.like("PROJECTION_%")).count()
    assert events_now == render_event_count, (
        f"D31 VIOLATION: ingestion changed the projection event family "
        f"({render_event_count} -> {events_now})")
    history = projection_engine.render_history(session, project.id)
    assert len(history) == render_event_count
    assert all(h["audit_cursor"] != 999999 for h in history), \
        "D31 VIOLATION: a hostile cursor claim reached the render history"

    # The forged variant is a DECLARED exception at the gate (the D30
    # machinery, proven at the seam): unverifiable, held for review.
    forged_doc = next(
        doc_id for doc_id in lane_doc_ids
        if "forged" in (session.query(db.Document).filter_by(
            id=doc_id).first().filename or ""))
    verdict = proposals.verify_provenance(session, forged_doc)
    assert not verdict["provenance_verified"]
    assert any("does not exist in governed records" in r
               for r in verdict["reasons"])
    kinds = {i["asset_id"]: i["classification"]
             for i in governance_inbox.build_inbox(session, project.id)["items"]
             if i["type"] == "INGESTION_EXCEPTION"}
    forged_assets = [a for a in lane_assets if a.document_id == forged_doc]
    assert forged_assets and all(
        kinds.get(a.id) == "PROPOSAL_PROVENANCE_UNVERIFIED"
        for a in forged_assets), "the forged variant must be a declared exception"

    print(f"Part 1 passed: {len(lane_assets)} candidates from rendered "
          f"files - all held, all DERIVED, zero authority replayed, the "
          f"forged variant declared.")

    # Part 1b - the laundering catastrophe, simulated and caught.
    print("\n--- Part 1b: laundering detector self-proof ---")
    victim = lane_assets[0]
    saved = (victim.status, victim.source_class)
    victim.status = "APPROVED"
    victim.source_class = "PRIMARY"
    session.commit()
    caught = laundering_violations(session, lane_doc_ids)
    assert len(caught) >= 2, f"Self-proof FAILED: {caught}"
    victim.status, victim.source_class = saved
    session.commit()
    assert not laundering_violations(session, lane_doc_ids)
    print(f"Part 1b passed: simulated catastrophe caught "
          f"({len(caught)} findings), clean after restore.")
    return lane_doc_ids


# ---------------------------------------------------------------- Part 2
# Regeneration isolation: wholesale regeneration is structurally
# confined to the managed folders (proven with an in-test VAULT spec -
# the real vault renderer inherits this floor the moment it exists).

PROBE = "_ws0_vault_probe"


def probe_files(projection):
    body = "\n".join(
        f"[[{n.id}]] {n.label}: {n.content or '(no content)'}"
        for n in projection.nodes if n.kind == "ASSET")
    return {
        "01_start/home.md": "# Vault home (probe)\n",
        "02_knowledge/notes.md": body + "\n",
        "06_governance/info.md": f"excluded: {projection.excluded}\n",
    }


def part_2_regeneration_isolation(session, officer, project):
    print("\n--- Part 2: regeneration isolation (the untouchable floor) ---")
    vault = tempfile.mkdtemp(prefix="em_ingress_vault2_")
    plants = make_vault(vault)
    # Stale junk INSIDE a managed folder: wholesale regeneration must
    # remove it (managed folders are disposable, D28/D31).
    write_file(vault, os.path.join("01_start", "stale-junk.md"), "old render junk\n")
    os.environ["EM_VAULT_DIR"] = vault

    projection_engine.RENDERERS[PROBE] = {
        "files": probe_files,
        "content_mode": contract.FULL_CONTENT,
        "output": "VAULT",
        "managed_folders": ("01_start", "02_knowledge", "06_governance"),
        "governance_folder": "06_governance",
    }
    try:
        result = projection_engine.render(session, officer, project.id,
                                          renderer=PROBE)
    finally:
        del projection_engine.RENDERERS[PROBE]
        os.environ.pop("EM_VAULT_DIR", None)

    tree = read_tree(vault)
    for rel, text in plants.items():
        key = rel.replace(os.sep, "/")
        assert tree.get(key) == text.encode("utf-8"), (
            f"D31 VIOLATION: untouchable input {key} was altered or "
            f"destroyed by regeneration")
    assert "01_start/stale-junk.md" not in tree, \
        "managed folders must regenerate wholesale"
    assert "01_start/home.md" in tree and "02_knowledge/notes.md" in tree
    assert "06_governance/manifest.json" in tree
    assert "06_governance/projection.json" in tree

    # The declared content mode, everywhere it must be (D31 ruling):
    manifest = json.loads(tree["06_governance/manifest.json"])
    assert manifest["content_mode"] == "FULL_CONTENT"
    assert result["content_mode"] == "FULL_CONTENT"
    assert result["managed_folders"] == ["01_start", "02_knowledge",
                                         "06_governance"]
    event = session.query(db.AuditEvent).filter_by(
        event_type="PROJECTION_RENDERED").order_by(
        db.AuditEvent.id.desc()).first()
    assert json.loads(event.details)["content_mode"] == "FULL_CONTENT"

    # Clearance before content (D31 companion ruling): the INTERNAL
    # render carries full INTERNAL content and not one byte of the
    # EXECUTIVE asset.
    notes = tree["02_knowledge/notes.md"].decode("utf-8")
    assert "retention ledgers" in notes, "FULL_CONTENT must carry content"
    everything = b"".join(tree.values())
    assert b"TOPSECRET-INGRESS" not in everything, \
        "D31 VIOLATION: content above clearance reached the vault"
    print(f"Part 2 passed: 3 untouchable plants byte-identical, managed "
          f"folders regenerated wholesale, content mode declared in "
          f"manifest + event, clearance filtered before content.")


# ---------------------------------------------------------------- Part 3
# The floor refuses loudly - before any deletion can occur.

def part_3_floor_refusals(session, officer, project):
    print("\n--- Part 3: the floor refuses loudly ---")
    vault = tempfile.mkdtemp(prefix="em_ingress_vault3_")
    plants = make_vault(vault)
    os.environ["EM_VAULT_DIR"] = vault
    base_spec = {"files": probe_files, "content_mode": contract.FULL_CONTENT,
                 "output": "VAULT", "governance_folder": "06_governance"}
    refusals = {
        "manages an untouchable folder": {
            **base_spec, "managed_folders": ("08_proposals", "06_governance")},
        "manages a folder outside the reserved window": {
            **base_spec, "managed_folders": ("09_extra", "06_governance")},
        "declares no managed folders": {
            **base_spec, "managed_folders": ()},
        "stamps outside the managed set": {
            **base_spec, "managed_folders": ("01_start",),
            "governance_folder": "06_governance"},
        "path traversal in a managed name": {
            **base_spec, "managed_folders": ("01_../08_proposals", "06_governance")},
    }
    try:
        for label, spec in refusals.items():
            projection_engine.RENDERERS[PROBE] = spec
            try:
                projection_engine.render(session, officer, project.id,
                                         renderer=PROBE)
                raise AssertionError(f"Self-proof FAILED: a spec that "
                                     f"{label} was not refused")
            except ValueError:
                pass
            finally:
                del projection_engine.RENDERERS[PROBE]
        # An output path escaping the managed set is refused at write time.
        projection_engine.RENDERERS[PROBE] = {
            **base_spec,
            "files": lambda p: {"07_agent_workspaces/evil.md": "boo"},
            "managed_folders": ("06_governance",),
        }
        try:
            projection_engine.render(session, officer, project.id,
                                     renderer=PROBE)
            raise AssertionError("Self-proof FAILED: an output path into an "
                                 "untouchable folder was written")
        except ValueError:
            pass
        finally:
            del projection_engine.RENDERERS[PROBE]
    finally:
        os.environ.pop("EM_VAULT_DIR", None)
    tree = read_tree(vault)
    for rel, text in plants.items():
        assert tree.get(rel.replace(os.sep, "/")) == text.encode("utf-8"), \
            "a refused render must leave the untouchable inputs intact"
    print(f"Part 3 passed: {len(refusals) + 1} floor violations refused "
          f"loudly; every untouchable plant intact.")


# ---------------------------------------------------------------- Part 4
# Path discipline (structural): the floor's names live in ONE place.

def path_discipline_violations(rel, source):
    """The sweep's checker: within backend/app, EM_VAULT_DIR and the
    untouchable folder names may appear only in the floor module
    (app/projections/engine.py) - no other app code can even construct
    a path into the vault's inputs."""
    if rel == FLOOR_MODULE:
        return []
    violations = []
    if "EM_VAULT_DIR" in source:
        violations.append(f"{rel}: names EM_VAULT_DIR")
    for name in UNTOUCHABLE_NAMES:
        if name in source:
            violations.append(f"{rel}: names the untouchable folder '{name}'")
    return violations


def part_4_path_discipline():
    print("\n--- Part 4: path discipline (one floor, one module) ---")
    offenders = []
    for root, _dirs, files in os.walk(APP_DIR):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            rel = os.path.relpath(path, APP_DIR).replace(os.sep, "/")
            with open(path, "r", encoding="utf-8") as f:
                offenders.extend(path_discipline_violations(rel, f.read()))
    assert not offenders, (
        "D31 violation - the floor's names leaked:\n  "
        + "\n  ".join(offenders))
    with open(os.path.join(APP_DIR, FLOOR_MODULE), "r", encoding="utf-8") as f:
        floor_source = f.read()
    for name in UNTOUCHABLE_NAMES:
        assert name in floor_source, "sanity: the floor must define its names"
    # Self-proof: a planted renderer-shaped source naming the ingress is
    # caught; the floor module itself is exempt by name, nothing else is.
    plant = 'def render_files(p):\n    return {"08_proposals/note.md": "x"}\n'
    assert path_discipline_violations("projections/renderers/planted.py", plant), \
        "Self-proof FAILED: the sweep missed a renderer naming the ingress"
    assert path_discipline_violations("crud.py", "EM_VAULT_DIR"), \
        "Self-proof FAILED: the sweep missed EM_VAULT_DIR outside the floor"
    assert not path_discipline_violations(FLOOR_MODULE, floor_source), \
        "Self-proof sanity: the floor module itself is the one legal home"
    print("Part 4 passed: EM_VAULT_DIR + the untouchable names confined to "
          "the floor module; the sweep catches strays (self-proven).")


class ApproveEverythingVerifier:
    """The most permissive engine constructible - even under it, an
    ingested rendered file must hold (the D26/D29 sentinel posture,
    applied to the D31 seam)."""
    identity = {"method": "GUARD_APPROVE_EVERYTHING",
                "note": "adversarial ingress seam"}

    def check(self, candidate, corpus):
        return {"pairs_checked": len(corpus), "pairs_dropped": 0,
                "contradictions": []}


def main():
    db.init_db()
    tier2.verifier_factory = ApproveEverythingVerifier
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Ingress Guard", description="D31 guard", customer_id=customer.id),
        actor=officer)

    # Seed: a real corpus through the real pipeline, one EXECUTIVE asset
    # for the clearance-before-content proof, and ONE legitimate graph
    # render whose files become the laundering plant.
    corpus_folder = tempfile.mkdtemp(prefix="em_ingress_corpus_")
    primary = db.SourceConnector(project_id=project.id, name="Corpus",
                                 type="LOCAL_FOLDER", root_path=corpus_folder,
                                 include_extensions=".txt")
    session.add(primary)
    session.commit()
    session.refresh(primary)
    for name, sentence in CORPUS.items():
        write_file(corpus_folder, name, sentence + "\n")
    write_file(corpus_folder, "restricted.txt", EXEC_SENTENCE + "\n")
    run_scan(session, primary)
    reviewer = test_support.governed_actor(session, "IngressReviewer")
    for asset in session.query(db.KnowledgeAsset).filter_by(
            project_id=project.id, status="CANDIDATE").all():
        crud.update_knowledge_asset(
            session, asset.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
            actor=reviewer, review_notes="guard corpus")
    restricted = next(a for a in session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id).all() if "TOPSECRET-INGRESS" in (a.content or ""))
    restricted.access_level = "EXECUTIVE"
    session.commit()

    render_result = projection_engine.render(session, officer, project.id,
                                             renderer="graph")
    assert render_result["content_mode"] == "METADATA_EXCERPT", \
        "the graph renderer declares METADATA_EXCERPT (D31 ruling)"
    rendered_dir = os.path.join(os.environ["EM_PROJECTION_DIR"],
                                f"project_{project.id}", "graph")

    lane_doc_ids = part_1_laundering_plant(session, officer, project,
                                           rendered_dir, render_event_count=1)
    part_2_regeneration_isolation(session, officer, project)
    part_3_floor_refusals(session, officer, project)
    part_4_path_discipline()

    session.close()
    print("\nAll D31 render-ingress guard checks passed: render authority "
          "dies at ingress - rendered files become only held DERIVED "
          "candidates behind the valve; wholesale regeneration is confined "
          "to the managed folders; the untouchable floor holds; the floor's "
          "names live in one module - all adversarially self-proven.")


if __name__ == "__main__":
    main()
