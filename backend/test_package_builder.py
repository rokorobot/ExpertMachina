import os
import sys
import json
import hashlib
import zipfile
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="empkg_test_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import package_builder


def make_asset(session, project, doc, name, text, access_level="INTERNAL", idx=0):
    chunk = db.DocumentChunk(document_id=doc.id, text=text, chunk_index=idx)
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    a = crud.create_knowledge_asset(session, schemas.KnowledgeAssetCreate(
        type="POLICY", name=name, content=text, project_id=project.id,
        document_id=doc.id, chunk_id=chunk.id, source_page=1, source_section="S1",
        source_hash=hashlib.sha256(text.encode()).hexdigest()))
    crud.update_knowledge_asset(session, asset_id=a.id,
                                update=schemas.KnowledgeAssetUpdate(status="APPROVED", access_level=access_level),
                                actor="qa")
    session.refresh(a)
    return a


def main():
    print("\nInitializing test database for Agent Package Builder checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Package Test", description="Agent package builder", customer_id=customer.id))
    doc = crud.create_document(session, project_id=project.id, filename="Safety.txt", file_path="uploads/s.txt")

    a_public = make_asset(session, project, doc, "Evacuation Protocol",
                          "During thermal runaway, evacuate the battery hall immediately.", "INTERNAL", 0)
    a_internal = make_asset(session, project, doc, "Shutdown Logs",
                            "Facility Manager signs shutdown logs within 24 hours after evacuation.", "INTERNAL", 1)
    a_exec = make_asset(session, project, doc, "Executive Crisis Plan",
                        "Executive board convenes a crisis cell within 2 hours of a severe incident.", "EXECUTIVE", 2)
    # An approved project asset NOT in the model - must never leak into packages.
    a_outsider = make_asset(session, project, doc, "Unrelated HR Policy",
                            "Vacation requests require two weeks notice.", "INTERNAL", 3)

    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Facility Safety Expert", description="", project_id=project.id,
        asset_ids=[a_public.id, a_internal.id, a_exec.id]))

    # Part 1: compile emits a hashed, well-formed .empkg artifact.
    print("\n--- Part 1: Compile emits the .empkg with a tamper-evident hash chain ---")
    pkg = crud.create_agent_package(session, schemas.AgentPackageCreate(
        name="Facility Safety Expert", project_id=project.id,
        expert_model_id=model.id, governance_version="1.0", clearance_level="EXECUTIVE"))
    assert pkg.file_path and os.path.exists(pkg.file_path), "No .empkg file emitted"
    assert pkg.package_hash and pkg.manifest, "Package hash / manifest not persisted"
    with zipfile.ZipFile(pkg.file_path) as zf:
        names = set(zf.namelist())
        expected = {"manifest.json", "knowledge.json", "trust.json", "coverage.json",
                    "evidence.json", "governance.json", "instructions.md"}
        assert names == expected, f"Unexpected package contents: {names}"
        manifest_bytes = zf.read("manifest.json")
        manifest = json.loads(manifest_bytes)
        # Every file hash in the manifest must match the actual zip entry...
        for fname, expected_hash in manifest["files"].items():
            actual = hashlib.sha256(zf.read(fname)).hexdigest()
            assert actual == expected_hash, f"Hash mismatch for {fname}"
        # ...and the package hash is the hash of manifest.json itself.
        assert pkg.package_hash == hashlib.sha256(manifest_bytes).hexdigest()
    print("Part 1 passed: 7-file package, all hashes verified, chain anchored in manifest.")

    # Part 2: package contains ONLY the model's member assets (no project leak).
    print("\n--- Part 2: Only member assets are packaged ---")
    with zipfile.ZipFile(pkg.file_path) as zf:
        knowledge = json.loads(zf.read("knowledge.json"))
    packaged_ids = {k["asset_id"] for k in knowledge}
    assert packaged_ids == {a_public.id, a_internal.id, a_exec.id}, f"Wrong assets: {packaged_ids}"
    assert a_outsider.id not in packaged_ids, "Non-member project asset leaked into the package"
    assert all(k["provenance"]["source_hash"] for k in knowledge), "Provenance missing"
    print("Part 2 passed: member assets only, full provenance attached.")

    # Part 3: clearance filtering - INTERNAL package excludes EXECUTIVE assets.
    print("\n--- Part 3: Clearance level filters assets, exclusions are reported ---")
    pkg_internal = crud.create_agent_package(session, schemas.AgentPackageCreate(
        name="Facility Safety Expert", project_id=project.id,
        expert_model_id=model.id, governance_version="1.0", clearance_level="INTERNAL"))
    with zipfile.ZipFile(pkg_internal.file_path) as zf:
        knowledge = json.loads(zf.read("knowledge.json"))
        manifest = json.loads(zf.read("manifest.json"))
        governance = json.loads(zf.read("governance.json"))
    ids = {k["asset_id"] for k in knowledge}
    assert a_exec.id not in ids, "EXECUTIVE asset leaked into INTERNAL package"
    assert ids == {a_public.id, a_internal.id}
    assert manifest["excluded_assets_above_clearance"] == 1, "Exclusion not reported in manifest"
    assert governance["excluded_assets_above_clearance"] == 1, "Exclusion not reported in governance"
    assert manifest["clearance_level"] == "INTERNAL"
    print("Part 3 passed: higher-tier asset excluded and the exclusion is declared, not silent.")

    # Part 4: reproducibility - same model state, same knowledge hash.
    print("\n--- Part 4: Same model state produces the same knowledge hash ---")
    pkg_repeat = crud.create_agent_package(session, schemas.AgentPackageCreate(
        name="Facility Safety Expert", project_id=project.id,
        expert_model_id=model.id, governance_version="1.0", clearance_level="EXECUTIVE"))
    assert pkg_repeat.manifest["knowledge_hash"] == pkg.manifest["knowledge_hash"], \
        "Knowledge hash must be deterministic for identical model state"
    print("Part 4 passed: knowledge hash is reproducible (compiled_at varies, content does not).")

    # Part 5: a blocked gate still prevents the artifact from existing.
    print("\n--- Part 5: Blocked compile gate prevents export ---")
    rel = db.AssetRelationship(
        project_id=project.id, expert_model_id=model.id,
        source_asset_id=a_public.id, target_asset_id=a_internal.id,
        relationship_type="CONFLICTS_WITH", classification="DIRECT_CONTRADICTION",
        confidence=0.99, status="DETECTED", verifier_json=json.dumps({"method": "TEST_FIXTURE"}))
    session.add(rel)
    session.commit()
    packages_before = session.query(db.AgentPackage).count()
    files_before = len(os.listdir(os.environ["EM_PACKAGE_DIR"]))
    try:
        crud.create_agent_package(session, schemas.AgentPackageCreate(
            name="Should Not Exist", project_id=project.id,
            expert_model_id=model.id, governance_version="1.0", clearance_level="EXECUTIVE"))
        raise AssertionError("Compile was allowed despite a blocking conflict")
    except ValueError:
        pass
    assert session.query(db.AgentPackage).count() == packages_before, "Blocked package row persisted"
    assert len(os.listdir(os.environ["EM_PACKAGE_DIR"])) == files_before, "Blocked package file emitted"
    print("Part 5 passed: the gate guards the artifact, not just the row.")

    print("\n=== All Agent Package Builder tests passed successfully! ===")


if __name__ == "__main__":
    main()
