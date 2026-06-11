import os
import json
import hashlib
import datetime

from sqlalchemy.orm import Session

from app import database as db
from app import crud
from app import ingestion
from app import extraction

# Enterprise Source Connector - LOCAL_FOLDER (MVP 0.10.0).
#
# Read-only discovery over a local or mounted directory. "Scan now" only:
# recursive walk, extension filter, sha256 dedup, per-file status. No
# watching, no cloud connectors, no credentials, no auto-approval.
#
# The architectural rule: connector output becomes ORDINARY ExpertMachina
# objects. SourceDocument -> Document -> CANDIDATE KnowledgeAssets -> the
# existing governance pipeline (review queue, conflicts, revisions, inbox).
# No connector-specific approval flow, no special "folder assets".
#
# Follows the v0.9.2a discipline: the scan endpoint returns immediately;
# the heavy work runs as a background task with its own session, updating
# job counters per file (live progress) and writing its own audit events.

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
UPLOAD_DIR = "./uploads"


def _extensions(connector: db.SourceConnector) -> set:
    raw = connector.include_extensions or ",".join(sorted(SUPPORTED_EXTENSIONS))
    wanted = {e.strip().lower() for e in raw.split(",") if e.strip()}
    # Never ingest a type the parser can't handle - declared, not silent.
    return wanted & SUPPORTED_EXTENSIONS


def discover_files(connector: db.SourceConnector) -> list:
    """Recursive walk of the connector root, filtered to supported
    extensions. Returns absolute paths, deterministic order."""
    matches = []
    for dirpath, _dirnames, filenames in os.walk(connector.root_path):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in _extensions(connector):
                matches.append(os.path.join(dirpath, filename))
    return sorted(matches)


def run_ingestion_job(job_id: int):
    """Background-task entry point: owns its session (the request that
    scheduled the scan has already returned)."""
    session = db.SessionLocal()
    try:
        execute_ingestion_job(session, job_id)
    finally:
        session.close()


def execute_ingestion_job(session: Session, job_id: int, auto_extract: bool = True) -> db.IngestionJob:
    job = session.query(db.IngestionJob).filter(db.IngestionJob.id == job_id).first()
    if not job:
        print(f"Ingestion job {job_id} not found")
        return None
    connector = session.query(db.SourceConnector).filter(
        db.SourceConnector.id == job.connector_id).first()

    job.status = "RUNNING"
    job.started_at = datetime.datetime.utcnow()
    session.commit()
    crud.log_audit_event(
        session, actor=f"connector:{connector.name}", event_type="INGESTION_JOB_STARTED",
        target_id=str(job.id),
        details=json.dumps({"connector_id": connector.id, "root_path": connector.root_path,
                            "extensions": sorted(_extensions(connector))}))

    try:
        if not os.path.isdir(connector.root_path):
            raise FileNotFoundError(f"Connector root path does not exist or is not a directory: {connector.root_path}")

        files = discover_files(connector)
        job.files_discovered = len(files)
        session.commit()

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        seen_hashes_this_job = set()

        for source_path in files:
            outcome = _ingest_one(session, connector, job, source_path, seen_hashes_this_job)
            if outcome == "INGESTED":
                job.files_ingested += 1
            elif outcome == "DUPLICATE":
                job.files_duplicate += 1
            else:
                job.files_failed += 1
            session.commit()  # per-file commit: progress polling sees live counts

        # Extraction turns parsed documents into ordinary CANDIDATE assets -
        # the same call the manual upload flow makes. A failure here is
        # recorded, never silent, but does not undo the ingested documents.
        if auto_extract and job.files_ingested > 0:
            try:
                extraction.extract_knowledge_assets_from_project(session, job.project_id)
            except Exception as e:
                job.error = f"Asset extraction failed after ingestion: {e}"
                session.commit()

        job.status = "COMPLETED"
        job.completed_at = datetime.datetime.utcnow()
        session.commit()
        crud.log_audit_event(
            session, actor=f"connector:{connector.name}", event_type="INGESTION_JOB_COMPLETED",
            target_id=str(job.id),
            details=json.dumps({
                "files_discovered": job.files_discovered,
                "files_ingested": job.files_ingested,
                "files_duplicate": job.files_duplicate,
                "files_failed": job.files_failed,
                "extraction_error": job.error,
            }))
    except Exception as e:
        job.status = "FAILED"
        job.error = str(e)
        job.completed_at = datetime.datetime.utcnow()
        session.commit()
        crud.log_audit_event(
            session, actor=f"connector:{connector.name}", event_type="INGESTION_JOB_FAILED",
            target_id=str(job.id),
            details=json.dumps({"error": str(e),
                                "files_discovered": job.files_discovered,
                                "files_ingested": job.files_ingested}))
    session.refresh(job)
    return job


def _ingest_one(session: Session, connector: db.SourceConnector, job: db.IngestionJob,
                source_path: str, seen_hashes: set) -> str:
    """Process one discovered file; always writes a SourceDocument row."""
    record = db.SourceDocument(
        project_id=job.project_id,
        connector_id=connector.id,
        ingestion_job_id=job.id,
        source_uri=os.path.abspath(source_path),
    )
    try:
        stat = os.stat(source_path)
        record.size_bytes = stat.st_size
        record.source_modified_at = datetime.datetime.utcfromtimestamp(stat.st_mtime)
        with open(source_path, "rb") as f:
            data = f.read()
        record.file_hash = hashlib.sha256(data).hexdigest()

        duplicate_of = None
        if record.file_hash in seen_hashes:
            duplicate_of = "another file in this scan"
        else:
            existing = session.query(db.Document).filter(
                db.Document.project_id == job.project_id,
                db.Document.content_hash == record.file_hash
            ).first()
            if existing:
                duplicate_of = f"document {existing.id} ({existing.filename})"
                record.document_id = existing.id

        if duplicate_of:
            record.status = "DUPLICATE"
            record.error = f"Identical content already ingested: {duplicate_of}"
            session.add(record)
            return "DUPLICATE"
        seen_hashes.add(record.file_hash)

        # From here on, the file becomes an ORDINARY document: same upload
        # dir, same create_document, same parser as the manual upload flow.
        filename = os.path.basename(source_path)
        dest_path = os.path.join(UPLOAD_DIR, f"{job.project_id}_c{connector.id}_{record.file_hash[:8]}_{filename}")
        with open(dest_path, "wb") as out:
            out.write(data)

        doc = crud.create_document(
            session,
            project_id=job.project_id,
            filename=filename,
            file_path=dest_path,
            department="General",
            owner=f"connector:{connector.name}",
        )
        doc.content_hash = record.file_hash
        session.commit()

        ingestion.parse_and_index_document(session, doc.id)
        session.refresh(doc)
        if doc.status == "FAILED":
            # The SourceDocument row records the failure; remove the dead
            # Document so the inventory stays clean and a rescan can retry
            # the file instead of deduping against a failed ingest.
            session.delete(doc)
            session.commit()
            try:
                os.remove(dest_path)
            except OSError:
                pass
            record.status = "FAILED"
            record.error = "Document parsing failed (unsupported or corrupt file content)"
            session.add(record)
            return "FAILED"
        record.document_id = doc.id

        record.status = "INGESTED"
        session.add(record)
        return "INGESTED"
    except Exception as e:
        record.status = "FAILED"
        record.error = str(e)
        session.add(record)
        return "FAILED"
