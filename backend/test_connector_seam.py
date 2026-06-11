import datetime
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"  # deterministic rule-based extraction

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import ingestion
from app.connectors import framework
from app.connectors.exceptions import FetchError
from app.connectors.models import ConnectorFetchResult, ConnectorItem
import test_support

# Seam tests (MVP 0.11 Step 10): prove the provider/framework BOUNDARY, not
# the behavior - behavior is proven by the unchanged pre-0.11 suites. A fake
# in-memory provider with non-filesystem URIs (fake://...) drives the real
# framework end-to-end; if these pass, the framework demonstrably holds no
# filesystem assumptions and no provider metadata can decide reconciliation.

ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_seam_qdrant_")

SYSTEM_V1 = "The platform runs on a PostgreSQL database server cluster."
SYSTEM_V2 = "The platform runs on a MySQL database server cluster."


class FakeProvider:
    """The contract's test double: describes items and hands over bytes.
    Decides nothing - it cannot even express a verdict."""

    def __init__(self, entries, fail_uris=()):
        # entries: list of (uri, name, content_bytes, metadata)
        self.entries = entries
        self.fail_uris = set(fail_uris)
        self.fetch_calls = []

    def validate(self):
        return None

    def describe(self):
        return {"source": "fake", "kind": "in-memory"}

    def discover(self):
        return [ConnectorItem(uri=uri, name=name) for uri, name, _data, _meta in self.entries]

    def fetch(self, item):
        self.fetch_calls.append(item.uri)
        if item.uri in self.fail_uris:
            raise FetchError(f"simulated fetch failure for {item.uri}")
        for uri, _name, data, meta in self.entries:
            if uri == item.uri:
                return ConnectorFetchResult(data=data, metadata=dict(meta))
        raise FetchError(f"unknown item {item.uri}")


def run_fake_scan(session, connector, provider):
    framework._provider_for = lambda _connector: provider  # inject at the seam
    job = db.IngestionJob(project_id=connector.project_id, connector_id=connector.id, status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    framework.execute_ingestion_job(session, job.id)
    session.refresh(job)
    assert job.status == "COMPLETED", f"Job should complete: {job.status} / {job.error}"
    return job


def records_of(session, job):
    rows = session.query(db.SourceDocument).filter(db.SourceDocument.ingestion_job_id == job.id).all()
    return {r.source_uri: r for r in rows}


def main():
    print("\nInitializing test database for connector seam checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    seam_tester = test_support.governed_actor(session, "SeamTester")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Seam Test", description="Provider/framework boundary", customer_id=customer.id), actor=seam_tester)
    connector = db.SourceConnector(project_id=project.id, name="Fake Source", type="LOCAL_FOLDER",
                                   root_path="fake://nowhere", include_extensions=".txt")
    session.add(connector)
    session.commit()
    session.refresh(connector)
    meta_t1 = {"size_bytes": 11, "modified_at": datetime.datetime(2026, 6, 1, 8, 0, 0)}

    # --- Test A: the framework classifies; the provider cannot. -----------
    print("\n--- Seam test A: NEW / DUPLICATE / CHANGED are framework verdicts ---")
    seed = FakeProvider([
        ("fake://docs/b", "b.txt", b"Document b describes the standard widget assembly sequence.", meta_t1),
        ("fake://docs/c", "c.txt", b"Document c lists the laboratory equipment inventory baseline.", meta_t1),
    ])
    run_fake_scan(session, connector, seed)

    main_scan = FakeProvider([
        ("fake://docs/a", "a.txt", b"Document a introduces the visitor badge issuance overview.", meta_t1),
        ("fake://docs/b", "b.txt", b"Document b describes the standard widget assembly sequence.", meta_t1),
        ("fake://docs/c", "c.txt", b"Document c lists the REVISED laboratory equipment inventory.", meta_t1),
    ])
    job_a = run_fake_scan(session, connector, main_scan)
    assert (job_a.files_ingested, job_a.files_duplicate, job_a.files_changed, job_a.files_failed) == (1, 1, 1, 0), \
        f"Expected 1/1/1/0, got {job_a.files_ingested}/{job_a.files_duplicate}/{job_a.files_changed}/{job_a.files_failed}"
    rows = records_of(session, job_a)
    assert rows["fake://docs/a"].status == "INGESTED"
    assert rows["fake://docs/b"].status == "DUPLICATE"
    assert rows["fake://docs/c"].status == "CHANGED"
    assert not hasattr(main_scan, "classify"), "Provider has no classification capability by construction"
    print("Seam test A passed: framework pronounced NEW/DUPLICATE/CHANGED over fake:// URIs.")

    # --- Test B: one fetch failure never aborts the scan. ------------------
    print("\n--- Seam test B: fetch failure is recorded, scan continues ---")
    failing = FakeProvider([
        ("fake://docs/d", "d.txt", b"Document d records the canteen seating arrangement guidance.", meta_t1),
        ("fake://docs/e", "e.txt", b"Document e would describe parking rules but cannot be read.", meta_t1),
        ("fake://docs/f", "f.txt", b"Document f explains the reception desk telephone etiquette.", meta_t1),
    ], fail_uris=["fake://docs/e"])
    job_b = run_fake_scan(session, connector, failing)
    assert (job_b.files_ingested, job_b.files_failed) == (2, 1), \
        f"d and f must ingest around e's failure: {job_b.files_ingested}/{job_b.files_failed}"
    rows = records_of(session, job_b)
    assert rows["fake://docs/e"].status == "FAILED"
    assert "simulated fetch failure" in rows["fake://docs/e"].error, "Failure must carry the provider's reason"
    assert rows["fake://docs/f"].status == "INGESTED", "Items after the failure must still be processed"
    assert failing.fetch_calls[-1] == "fake://docs/f", "Scan must have continued past the failing item"
    print("Seam test B passed: e failed with a declared reason; d and f ingested; job completed.")

    # --- Test C: D18 executable - metadata is never the change verdict. ----
    print("\n--- Seam test C (D18): modified_at changes, hash unchanged -> NOT CHANGED ---")
    content_g = b"Document g specifies the courier handover acknowledgement steps."
    seed_g = FakeProvider([("fake://docs/g", "g.txt", content_g, meta_t1)])
    run_fake_scan(session, connector, seed_g)

    meta_t2 = {"size_bytes": 11, "modified_at": datetime.datetime(2026, 6, 11, 17, 30, 0)}
    rescan_g = FakeProvider([("fake://docs/g", "g.txt", content_g, meta_t2)])
    job_c = run_fake_scan(session, connector, rescan_g)
    assert job_c.files_changed == 0 and job_c.files_ingested == 0 and job_c.files_duplicate == 1, \
        f"Metadata change alone must classify DUPLICATE: {job_c.files_duplicate}/{job_c.files_changed}"
    row_g = records_of(session, job_c)["fake://docs/g"]
    assert row_g.status == "DUPLICATE", "URI = identity, hash = verdict, metadata = context"
    assert row_g.source_modified_at == meta_t2["modified_at"], \
        "Described context IS recorded - it just never decides the verdict"
    print("Seam test C passed: changed modified_at recorded as context, verdict stayed NOT CHANGED.")

    # --- Test D: seen_hashes ordering - changed content dedupes in-scan. ---
    print("\n--- Seam test D: same-scan copy of changed content is DUPLICATE, one revision only ---")
    seed_h = FakeProvider([("fake://docs/h", "h.txt", SYSTEM_V1.encode(), meta_t1)])
    run_fake_scan(session, connector, seed_h)
    h_doc = session.query(db.SourceDocument).filter(
        db.SourceDocument.source_uri == "fake://docs/h",
        db.SourceDocument.document_id.isnot(None)).first()
    system_asset = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id == h_doc.document_id,
        db.KnowledgeAsset.type == "SYSTEM").first()
    assert system_asset, "Seed extraction must produce the SYSTEM asset"
    crud.update_knowledge_asset(session, system_asset.id,
                                schemas.KnowledgeAssetUpdate(status="APPROVED"), actor=seam_tester)

    both = FakeProvider([
        ("fake://docs/h", "h.txt", SYSTEM_V2.encode(), meta_t1),   # CHANGED first
        ("fake://docs/i", "i.txt", SYSTEM_V2.encode(), meta_t1),   # same new content, new URI
    ])
    job_d = run_fake_scan(session, connector, both)
    rows = records_of(session, job_d)
    assert rows["fake://docs/h"].status == "CHANGED"
    assert rows["fake://docs/i"].status == "DUPLICATE", \
        "The changed hash entered seen_hashes BEFORE reconciliation - same-scan copy dedupes"
    assert "another file in this scan" in rows["fake://docs/i"].error
    candidates = [r for r in session.query(db.AssetRevision).filter(
        db.AssetRevision.asset_id == system_asset.id).all() if r.status == "CANDIDATE"]
    assert len(candidates) == 1, f"Exactly ONE candidate revision, not one per copy: {len(candidates)}"
    session.refresh(system_asset)
    assert system_asset.content == SYSTEM_V1, "Approved content still waits for a human"
    print("Seam test D passed: 1 candidate revision, same-scan copy deduped, approved content untouched.")

    print("\nAll connector seam tests passed - the boundary holds under adversarial inputs.")


if __name__ == "__main__":
    main()
