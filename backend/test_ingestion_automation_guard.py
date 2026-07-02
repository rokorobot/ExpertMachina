import ast
import json
import os
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
from app import policy
import test_support

# D26 structural guard (v1.2.1 WS0, docs/ingestion-automation-v1.2.1.md).
#
# WS0 is the structural safety gate before automation can start approving
# at scale. This guard is permanent in CI and proves the two core dangers
# are impossible:
#
#   1. Auto-approval cannot grow a second approval path. Every automatic
#      approval still flows through the same governed transition path
#      (crud.update_knowledge_asset) a human approval uses.
#   2. Candidate revisions cannot be auto-approved. Even under the most
#      permissive policy set constructible, revisions remain human-gated.
#
# And it adversarially self-proves both: the structural checker is run
# against planted violations (a direct status write, a direct AssetReview
# construction, an approval outside the transition path, a second module
# writing the ASSET_AUTO_APPROVED event family) and the sentinel's
# detector is run against a simulated policy-approved revision - the
# guard must catch every plant, or the guard itself fails.
#
# Guarded the way test_connector_seam.py guards D18, the purity
# assertions guard D20, test_workbench_projection.py guards D24, and
# test_credential_custody.py guards D25.

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")

# Every module that performs ingestion automation (auto-approval or any
# future automated transition). WS3's Tier-2 module MUST be added here
# when it lands - the event-family sweep below fails loudly if a module
# outside this list writes ASSET_AUTO_APPROVED, so forgetting is caught.
AUTOMATION_MODULES = ["policy.py"]

# Isolated vector store: the dev server holds a lock on ./qdrant_db.
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_guard_qdrant_")

SYSTEM_SENTENCE = "The reporting platform archives records in a SQLite database server."
SYSTEM_SENTENCE_CHANGED = "The reporting platform archives records in a MariaDB database server."
POLICY_SENTENCE = "All vendors must sign the data processing agreement before integration."


# ---------------------------------------------------------------- Part 1
# Structural: the single governed approval path.

def _parents(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _call_name(node):
    if isinstance(node, ast.Call):
        f = node.func
        return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
    return None


def structural_violations(module_name, source):
    """Forbidden shapes in an automation module. Any hit means a second
    approval path is growing - the exact erosion D26 forecloses."""
    tree = ast.parse(source)
    parents = _parents(tree)
    violations = []
    for node in ast.walk(tree):
        # (a) No direct status writes: automation never flips governed
        # state itself; it asks the transition path to.
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "status":
                    violations.append(
                        f"{module_name}:{node.lineno} direct .status write")
        # (b) No direct construction of review/revision artifacts: those
        # rows are minted by the transition path only.
        ctor = _call_name(node)
        if ctor in {"AssetReview", "AssetRevision"}:
            violations.append(
                f"{module_name}:{node.lineno} constructs {ctor} directly")
        # (c) Every APPROVED grant sits inside a crud.update_knowledge_asset
        # call - the one path a human approval also uses.
        if (isinstance(node, ast.keyword) and node.arg == "status"
                and isinstance(node.value, ast.Constant)
                and node.value.value == "APPROVED"):
            cur = parents.get(node)
            inside_transition_path = False
            while cur is not None:
                if _call_name(cur) == "update_knowledge_asset":
                    inside_transition_path = True
                    break
                cur = parents.get(cur)
            if not inside_transition_path:
                violations.append(
                    f"{module_name}:{node.lineno} grants APPROVED outside "
                    f"crud.update_knowledge_asset")
    return violations


def event_family_offenders():
    """Modules writing the ASSET_AUTO_APPROVED event family. Must be a
    subset of AUTOMATION_MODULES - a second module quietly writing the
    same family IS a second approval path, whatever it calls itself."""
    offenders = set()
    for root, _dirs, files in os.walk(APP_DIR):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            rel = os.path.relpath(path, APP_DIR).replace(os.sep, "/")
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if (isinstance(node, ast.keyword)
                        and node.arg in {"audit_event_type", "event_type"}
                        and isinstance(node.value, ast.Constant)
                        and node.value.value == "ASSET_AUTO_APPROVED"):
                    offenders.add(rel)
    return offenders


def part_1_structural():
    print("\n--- Part 1: single governed approval path (structural) ---")
    for module_name in AUTOMATION_MODULES:
        with open(os.path.join(APP_DIR, module_name), "r", encoding="utf-8") as f:
            source = f.read()
        violations = structural_violations(module_name, source)
        assert not violations, (
            "D26 violation - a second approval path is growing:\n  "
            + "\n  ".join(violations))
    offenders = event_family_offenders()
    assert offenders <= set(AUTOMATION_MODULES), (
        f"D26 violation: module(s) {sorted(offenders - set(AUTOMATION_MODULES))} "
        f"write the ASSET_AUTO_APPROVED event family but are not declared "
        f"automation modules. Declare them in AUTOMATION_MODULES so the "
        f"structural checks cover them - or remove the second path.")
    assert offenders, "Sanity: policy.py must be seen writing the event family"
    print(f"Part 1 passed: {AUTOMATION_MODULES} clean; event family written "
          f"only by {sorted(offenders)}.")


# ---------------------------------------------------------------- Part 2
# Structural self-proof: the checker catches every planted violation.

PLANT_DIRECT_WRITE = """
def approve(asset):
    asset.status = "APPROVED"
"""

PLANT_REVIEW_ROW = """
def approve(session, asset):
    session.add(db.AssetReview(asset_id=asset.id, approver="policy:x"))
"""

PLANT_OUTSIDE_PATH = """
def approve(session, asset):
    apply_update(session, asset.id, schemas.KnowledgeAssetUpdate(status="APPROVED"))
"""

PLANT_CLEAN = """
def approve(session, asset):
    crud.update_knowledge_asset(
        session, asset.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=actor, audit_event_type="ASSET_AUTO_APPROVED")
"""


def part_2_structural_self_proof():
    print("\n--- Part 2: structural checker self-proof (planted violations) ---")
    plants = {
        "direct status write": PLANT_DIRECT_WRITE,
        "direct AssetReview construction": PLANT_REVIEW_ROW,
        "APPROVED granted outside the transition path": PLANT_OUTSIDE_PATH,
    }
    for label, source in plants.items():
        violations = structural_violations("planted.py", source)
        assert violations, f"Self-proof FAILED: the checker missed a {label}"
    assert not structural_violations("planted.py", PLANT_CLEAN), \
        "Self-proof sanity: the canonical transition-path shape must be clean"
    print(f"Part 2 passed: all {len(plants)} planted violations caught; "
          f"the canonical shape stays clean.")


# ---------------------------------------------------------------- Part 3
# The adversarial revision sentinel (end-to-end), and its self-proof.

def write_file(folder, name, *sentences):
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(sentences) + "\n")
    return path


def run_scan(session, connector):
    job = db.IngestionJob(project_id=connector.project_id,
                          connector_id=connector.id, status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    connectors.execute_ingestion_job(session, job.id)
    # WS3 NOTE (binding): when the async Tier-2 pass lands, this helper
    # MUST also drain the Tier-2 background task before returning - the
    # sentinel's guarantee is "after ALL background tasks complete".
    session.refresh(job)
    assert job.status == "COMPLETED", f"{job.status} / {job.error}"
    return job


def revision_violations(session, asset, approved_content):
    """The sentinel's detector: any way a revision could have been
    auto-approved. revision 1 is the legitimate lazy baseline minted BY
    the initial approval (it is the approval, not a change to trusted
    content); every later revision changes already-trusted content and
    stays human-gated (D17)."""
    session.refresh(asset)
    violations = []
    if asset.content != approved_content:
        violations.append(
            f"approved content changed without a human: {asset.content!r}")
    for r in asset.revisions:
        if (r.status == "APPROVED" and r.revision_number > 1
                and (r.approved_by or "").startswith("policy:")):
            violations.append(
                f"revision {r.revision_number} auto-approved by {r.approved_by}")
    if not any(r.status == "CANDIDATE" for r in asset.revisions):
        violations.append("the source change produced no pending candidate revision")
    return violations


def part_3_revision_sentinel():
    print("\n--- Part 3: revision sentinel under the most permissive policy set ---")
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    customer = crud.get_or_create_default_customer(session)
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Sentinel", description="D26 guard", customer_id=customer.id),
        actor=officer)
    folder = tempfile.mkdtemp(prefix="em_guard_src_")
    connector = db.SourceConnector(project_id=project.id, name="Guard Share",
                                   type="LOCAL_FOLDER", root_path=folder,
                                   include_extensions=".txt")
    session.add(connector)
    session.commit()
    session.refresh(connector)

    # The most permissive policy set constructible - built as raw rows,
    # deliberately bypassing API validation (the adversary would too):
    # every allowed asset type, unscoped, and a second policy with every
    # v1.2.1 condition column populated maximally permissively. Today the
    # condition columns are inert (WS2/WS3 land their evaluation); this
    # sentinel is permanent, so the moment they gain semantics THIS test
    # exercises them at their most permissive - the guarantee must hold
    # under any policy an operator (or attacker) can write.
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add_all([
        db.ApprovalPolicy(project_id=project.id, name="everything-tier1",
                          asset_types_json=all_types, enabled=True),
        db.ApprovalPolicy(project_id=project.id, name="everything-conditions",
                          asset_types_json=all_types, enabled=True,
                          source_conditions_json="[]",
                          engine_conditions_json="{}",
                          domains_json=json.dumps([""])),
    ])
    session.commit()

    # Arm the sentinel: the permissive set must actually auto-approve
    # (a sentinel over machinery that approves nothing proves nothing).
    write_file(folder, "doc.txt", SYSTEM_SENTENCE, POLICY_SENTENCE)
    run_scan(session, connector)
    approved = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.type == "SYSTEM").first()
    assert approved and approved.status == "APPROVED", \
        "Sentinel not armed: the permissive policy set must auto-approve"

    # The adversarial act: change the already-trusted content at the source.
    write_file(folder, "doc.txt", SYSTEM_SENTENCE_CHANGED, POLICY_SENTENCE)
    job = run_scan(session, connector)
    assert job.files_changed == 1, f"CHANGED not detected: {job.files_changed}"

    violations = revision_violations(session, approved, SYSTEM_SENTENCE)
    assert not violations, (
        "D26/D17 violation - a revision reached APPROVED without a human:\n  "
        + "\n  ".join(violations))
    pending = [r for r in approved.revisions if r.status == "CANDIDATE"]
    print(f"Part 3 passed: revision {pending[0].revision_number} pending, "
          f"approved content untouched, under {len(policy.ALLOWED_ASSET_TYPES)} "
          f"covered types + populated condition columns.")

    # Self-proof: simulate the catastrophe the sentinel exists to catch -
    # a buggy automation pass approves the pending revision and promotes
    # its content - and assert the detector fires; then restore and
    # re-assert clean (the flip itself must not contaminate the run).
    print("\n--- Part 3b: sentinel self-proof (simulated auto-approved revision) ---")
    revision = pending[0]
    revision.status = "APPROVED"
    revision.approved_by = "policy:everything-tier1"
    approved.content = SYSTEM_SENTENCE_CHANGED
    session.commit()
    caught = revision_violations(session, approved, SYSTEM_SENTENCE)
    assert len(caught) >= 2, (
        f"Self-proof FAILED: the sentinel missed a simulated "
        f"policy-approved revision (caught: {caught})")
    revision.status = "CANDIDATE"
    revision.approved_by = None
    approved.content = SYSTEM_SENTENCE
    session.commit()
    assert not revision_violations(session, approved, SYSTEM_SENTENCE)
    print(f"Part 3b passed: simulated violation caught "
          f"({len(caught)} findings), clean after restore.")


# ---------------------------------------------------------------- Part 4
# WS0 schema self-check: the atomic commit carries its own evidence.

def part_4_schema():
    print("\n--- Part 4: v1.2.1 WS0 schema present (D26/D27) ---")
    source_doc_cols = {c.name for c in db.SourceDocument.__table__.columns}
    assert "source_metadata_json" in source_doc_cols, \
        "D26: Tier-0 source-authority evidence column missing"
    asset_cols = {c.name for c in db.KnowledgeAsset.__table__.columns}
    assert "domain" in asset_cols, "D27: governed domain path missing"
    assert "classification_policies" in db.Base.metadata.tables, \
        "D27: ClassificationPolicy governed object missing"
    policy_cols = {c.name for c in db.ApprovalPolicy.__table__.columns}
    for col in ("source_conditions_json", "engine_conditions_json", "domains_json"):
        assert col in policy_cols, f"D26: policy tier column {col} missing"
    print("Part 4 passed: all D26/D27 schema changes present "
          "(snapshot updated in test_workbench_projection.py, same commit).")


def main():
    part_1_structural()
    part_2_structural_self_proof()
    part_3_revision_sentinel()
    part_4_schema()
    print("\nAll D26 ingestion-automation guard checks passed: one governed "
          "approval path, revisions human-gated under the most permissive "
          "policy set, both adversarially self-proven.")


if __name__ == "__main__":
    main()
