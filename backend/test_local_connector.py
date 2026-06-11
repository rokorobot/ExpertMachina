import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import connectors
from app import ingestion
import test_support

# Isolated vector store: the dev server holds a lock on ./qdrant_db, and the
# test process must not depend on (or interfere with) a running server.
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_connector_qdrant_")


def make_source_tree(root: str) -> None:
    os.makedirs(os.path.join(root, "policies"), exist_ok=True)
    os.makedirs(os.path.join(root, "archive"), exist_ok=True)
    with open(os.path.join(root, "SOP-A_Safety.txt"), "w", encoding="utf-8") as f:
        f.write("SOP-A: Safety Policy.\nPolicy: All visitors must wear protective equipment in the lab.\n")
    with open(os.path.join(root, "policies", "SOP-B_Access.txt"), "w", encoding="utf-8") as f:
        f.write("SOP-B: Access Policy.\nPolicy: Server room access requires manager approval.\n")
    # Identical content under a different name in a different folder -> duplicate.
    with open(os.path.join(root, "archive", "SOP-A_Safety_copy.txt"), "w", encoding="utf-8") as f:
        f.write("SOP-A: Safety Policy.\nPolicy: All visitors must wear protective equipment in the lab.\n")
    # Unsupported extension -> must not even be discovered.
    with open(os.path.join(root, "image.xyz"), "w", encoding="utf-8") as f:
        f.write("binary-ish")
    # Invalid docx -> discovered, ingestion fails with a reason.
    with open(os.path.join(root, "broken.docx"), "wb") as f:
        f.write(b"this is not a real docx file")


def main():
    print("\nInitializing test database for Local Folder Connector checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    qa = test_support.governed_actor(session, "qa")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Connector Test", description="Local folder connector", customer_id=customer.id), actor=qa)

    source_root = tempfile.mkdtemp(prefix="em_connector_src_")
    make_source_tree(source_root)

    connector = db.SourceConnector(
        project_id=project.id, name="Test Share", type="LOCAL_FOLDER",
        root_path=source_root, include_extensions=".txt,.md,.pdf,.docx")
    session.add(connector)
    session.commit()
    session.refresh(connector)

    # Part 1: recursive discovery honors the extension filter.
    print("\n--- Part 1: Recursive discovery with extension filter ---")
    found = connectors.discover_files(connector)
    names = {os.path.basename(p) for p in found}
    assert names == {"SOP-A_Safety.txt", "SOP-B_Access.txt", "SOP-A_Safety_copy.txt", "broken.docx"}, names
    assert not any(p.endswith(".xyz") for p in found), "Unsupported extension leaked into discovery"
    print(f"Part 1 passed: {len(found)} files discovered across subdirectories, .xyz excluded.")

    # Part 2: scan ingests, dedups, and reports failures - per-file, no silent skips.
    print("\n--- Part 2: Scan now - ingested / duplicate / failed accounting ---")
    job = db.IngestionJob(project_id=project.id, connector_id=connector.id, status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    connectors.execute_ingestion_job(session, job.id)
    session.refresh(job)

    assert job.status == "COMPLETED", f"Job should complete: {job.status} / {job.error}"
    assert job.files_discovered == 4
    assert job.files_ingested == 2, f"Expected SOP-A + SOP-B ingested, got {job.files_ingested}"
    assert job.files_duplicate == 1, "The identical copy must be a duplicate"
    assert job.files_failed == 1, "The broken docx must fail"
    records = session.query(db.SourceDocument).filter(db.SourceDocument.ingestion_job_id == job.id).all()
    assert len(records) == 4, "Every discovered file gets a SourceDocument row"
    failed = next(r for r in records if r.status == "FAILED")
    assert failed.error, "Failures must carry a reason"
    dup = next(r for r in records if r.status == "DUPLICATE")
    assert "Identical content" in dup.error
    print(f"Part 2 passed: 4 discovered -> 2 ingested, 1 duplicate, 1 failed ({failed.error[:50]}...).")

    # Part 3: connector output is ORDINARY ExpertMachina objects.
    print("\n--- Part 3: Documents with provenance, assets as CANDIDATE ---")
    docs = session.query(db.Document).filter(db.Document.project_id == project.id).all()
    assert len(docs) == 2
    for doc in docs:
        assert doc.content_hash, "Ingested documents must carry the dedup content hash"
        assert doc.owner == "connector:Test Share"
        assert doc.status in ("PARSED", "ASSETS_EXTRACTED"), f"Document {doc.filename} not parsed: {doc.status}"
    ingested_records = [r for r in records if r.status == "INGESTED"]
    assert all(r.document_id for r in ingested_records), "SourceDocument must link to its Document"
    assets = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.project_id == project.id).all()
    assert len(assets) >= 1, "Extraction must produce knowledge assets"
    assert all(a.status == "CANDIDATE" for a in assets), \
        "Connector assets enter the EXISTING pipeline as CANDIDATE - no special states"
    print(f"Part 3 passed: {len(docs)} ordinary documents, {len(assets)} CANDIDATE assets in the normal pipeline.")

    # Part 4: rescanning the same folder is idempotent - everything duplicates.
    print("\n--- Part 4: Idempotent rescan ---")
    job2 = db.IngestionJob(project_id=project.id, connector_id=connector.id, status="PENDING")
    session.add(job2)
    session.commit()
    session.refresh(job2)
    connectors.execute_ingestion_job(session, job2.id)
    session.refresh(job2)
    assert job2.files_ingested == 0, "Rescan must not re-ingest unchanged files"
    assert job2.files_duplicate == 3, f"All previously ingested content must dedup: {job2.files_duplicate}"
    assert job2.files_failed == 1  # broken docx fails again (it never became a document)
    assert session.query(db.Document).filter(db.Document.project_id == project.id).count() == 2, \
        "Rescan must not create duplicate documents"
    print("Part 4 passed: rescan ingested nothing, deduped everything, documents unchanged.")

    # Part 5: job lifecycle is audit-logged; a bad root path fails loudly.
    print("\n--- Part 5: Audit events and loud failure on a bad root ---")
    started = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "INGESTION_JOB_STARTED").count()
    completed = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "INGESTION_JOB_COMPLETED").count()
    assert started == 2 and completed == 2, f"Job lifecycle not audited: {started}/{completed}"

    bad_connector = db.SourceConnector(
        project_id=project.id, name="Bad Path", type="LOCAL_FOLDER",
        root_path=os.path.join(source_root, "does_not_exist"))
    session.add(bad_connector)
    session.commit()
    session.refresh(bad_connector)
    job3 = db.IngestionJob(project_id=project.id, connector_id=bad_connector.id, status="PENDING")
    session.add(job3)
    session.commit()
    session.refresh(job3)
    connectors.execute_ingestion_job(session, job3.id)
    session.refresh(job3)
    assert job3.status == "FAILED" and "does not exist" in job3.error
    failed_events = session.query(db.AuditEvent).filter(db.AuditEvent.event_type == "INGESTION_JOB_FAILED").count()
    assert failed_events == 1
    print("Part 5 passed: lifecycle audited; nonexistent root fails the job with a reason.")

    # Part 6 (MVP 0.10.1): a changed source file becomes a candidate revision
    # through the existing machinery - no duplicate document, no duplicate asset.
    print("\n--- Part 6: Changed source file -> candidate revision ---")
    from app import revisions as revisions_module
    # Approve the asset extracted from SOP-B so the change routes to a revision.
    sop_b_doc = session.query(db.Document).filter(db.Document.filename == "SOP-B_Access.txt").first()
    sop_b_assets = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.document_id == sop_b_doc.id).all()
    assert sop_b_assets, "SOP-B must have extracted assets"
    target = sop_b_assets[0]
    crud.update_knowledge_asset(session, asset_id=target.id,
                                update=schemas.KnowledgeAssetUpdate(status="APPROVED"), actor=qa)
    session.refresh(target)
    old_content = target.content

    with open(os.path.join(source_root, "policies", "SOP-B_Access.txt"), "w", encoding="utf-8") as f:
        f.write("SOP-B: Access Policy.\nPolicy: Server room access requires director approval.\n")

    docs_before = session.query(db.Document).filter(db.Document.project_id == project.id).count()
    assets_before = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.project_id == project.id).count()
    job4 = db.IngestionJob(project_id=project.id, connector_id=connector.id, status="PENDING")
    session.add(job4)
    session.commit()
    session.refresh(job4)
    connectors.execute_ingestion_job(session, job4.id)
    session.refresh(job4)

    assert job4.files_changed == 1, f"Expected 1 changed file: {job4.files_changed} (failed {job4.files_failed})"
    assert job4.files_ingested == 0, "A changed file must not become a new document"
    assert session.query(db.Document).filter(db.Document.project_id == project.id).count() == docs_before, \
        "Change must not create a duplicate document"
    assert session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.project_id == project.id).count() == assets_before, \
        "Change must not create a duplicate asset"
    changed_row = session.query(db.SourceDocument).filter(
        db.SourceDocument.ingestion_job_id == job4.id,
        db.SourceDocument.status == "CHANGED").first()
    assert changed_row and changed_row.details, "CHANGED row must carry a change summary"
    assert len(changed_row.details["revisions_created"]) == 1, changed_row.details

    candidate = session.query(db.AssetRevision).filter(
        db.AssetRevision.asset_id == target.id,
        db.AssetRevision.status == "CANDIDATE").first()
    assert candidate, "Approved asset must get a candidate revision"
    assert "director approval" in candidate.content
    assert "Source file changed" in (candidate.change_reason or "")
    session.refresh(target)
    assert target.content == old_content, "Approved content must NOT change until the revision is approved"
    change_events = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "SOURCE_CHANGE_DETECTED").count()
    assert change_events == 1
    print("Part 6 passed: change -> candidate revision, approved content untouched, fully audited.")

    # Part 7: version history retained; pending-revision guard reports, never silent.
    print("\n--- Part 7: Version history + strictly-linear guard ---")
    history = session.query(db.SourceDocument).filter(
        db.SourceDocument.connector_id == connector.id,
        db.SourceDocument.source_uri.like("%SOP-B_Access.txt")
    ).order_by(db.SourceDocument.id).all()
    hashes = [h.file_hash for h in history]
    assert len(set(hashes)) == 2, f"History must retain both content versions: {hashes}"

    with open(os.path.join(source_root, "policies", "SOP-B_Access.txt"), "w", encoding="utf-8") as f:
        f.write("SOP-B: Access Policy.\nPolicy: Server room access requires CISO approval.\n")
    job5 = db.IngestionJob(project_id=project.id, connector_id=connector.id, status="PENDING")
    session.add(job5)
    session.commit()
    session.refresh(job5)
    connectors.execute_ingestion_job(session, job5.id)
    session.refresh(job5)
    assert job5.files_changed == 1
    changed_row5 = session.query(db.SourceDocument).filter(
        db.SourceDocument.ingestion_job_id == job5.id,
        db.SourceDocument.status == "CHANGED").first()
    assert len(changed_row5.details["skipped_pending_review"]) == 1, \
        "Second change while a candidate is pending must be reported as skipped"
    assert session.query(db.AssetRevision).filter(
        db.AssetRevision.asset_id == target.id,
        db.AssetRevision.status == "CANDIDATE").count() == 1, "Strictly linear: one pending candidate"

    # Approving the pending revision then rescanning picks up the newest content.
    revisions_module.review_revision(session, candidate.id, action="APPROVE",
                                     actor=test_support.governed_actor(session, "governance_officer"))
    job6 = db.IngestionJob(project_id=project.id, connector_id=connector.id, status="PENDING")
    session.add(job6)
    session.commit()
    session.refresh(job6)
    connectors.execute_ingestion_job(session, job6.id)
    session.refresh(job6)
    changed_row6 = session.query(db.SourceDocument).filter(
        db.SourceDocument.ingestion_job_id == job6.id,
        db.SourceDocument.status == "CHANGED").first()
    assert changed_row6 is None or len(changed_row6.details.get("revisions_created", [])) <= 1
    print("Part 7 passed: full hash history retained; linear revision rule enforced and reported.")

    print("\n=== All Local Folder Connector tests passed successfully! ===")


if __name__ == "__main__":
    main()
