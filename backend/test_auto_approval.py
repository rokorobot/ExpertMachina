import json
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
# Force rule-based extraction: auto-approval assertions depend on
# deterministic asset names and types, never on an LLM.
os.environ["OPENAI_API_KEY"] = "mock-key"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import connectors
from app import ingestion
from app import policy
from app.main import create_approval_policy, update_approval_policy

# Isolated vector store: the dev server holds a lock on ./qdrant_db.
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_policy_qdrant_")

# Rule-extraction fixtures: one SYSTEM sentence (platform/database/server
# keywords) and one POLICY sentence ("must") per file, each >= 30 chars.
SYSTEM_SENTENCE = "The platform runs on a PostgreSQL database server cluster."
POLICY_SENTENCE = "All operators must complete safety training before access is granted."
# Distinct content for the second document - identical text would dedup.
SYSTEM_SENTENCE_2 = "The reporting platform archives records in a SQLite database server."
SYSTEM_SENTENCE_2_CHANGED = "The reporting platform archives records in a MariaDB database server."
POLICY_SENTENCE_2 = "All vendors must sign the data processing agreement before integration."


def write_file(folder, name, *sentences):
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(sentences) + "\n")
    return path


def run_scan(session, connector):
    job = db.IngestionJob(project_id=connector.project_id, connector_id=connector.id, status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    connectors.execute_ingestion_job(session, job.id)
    session.refresh(job)
    assert job.status == "COMPLETED", f"Job should complete: {job.status} / {job.error}"
    return job


def events_of(session, event_type):
    return session.query(db.AuditEvent).filter(db.AuditEvent.event_type == event_type).all()


def main():
    print("\nInitializing test database for Policy-Based Auto Approval checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Policy Test", description="Auto approval", customer_id=customer.id))

    folder_a = tempfile.mkdtemp(prefix="em_policy_src_a_")
    folder_b = tempfile.mkdtemp(prefix="em_policy_src_b_")
    connector_a = db.SourceConnector(project_id=project.id, name="Share A", type="LOCAL_FOLDER",
                                     root_path=folder_a, include_extensions=".txt")
    connector_b = db.SourceConnector(project_id=project.id, name="Share B", type="LOCAL_FOLDER",
                                     root_path=folder_b, include_extensions=".txt")
    session.add_all([connector_a, connector_b])
    session.commit()
    session.refresh(connector_a)
    session.refresh(connector_b)

    # Part 1: with no policies, nothing runs and nothing claims to have run.
    print("\n--- Part 1: No policies -> everything stays CANDIDATE, no policy events ---")
    write_file(folder_a, "doc1.txt", SYSTEM_SENTENCE, POLICY_SENTENCE)
    run_scan(session, connector_a)
    assets = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.project_id == project.id).all()
    assert assets and all(a.status == "CANDIDATE" for a in assets), \
        "Without a policy every asset must remain CANDIDATE"
    assert not events_of(session, "POLICY_AUTOAPPROVAL_COMPLETED"), \
        "No policies in scope -> no summary event (nothing claims to have run)"
    assert not events_of(session, "ASSET_AUTO_APPROVED")
    print(f"Part 1 passed: {len(assets)} CANDIDATE assets, zero policy events.")

    # Part 2: an unscoped SYSTEM policy approves new SYSTEM assets with full
    # provenance; POLICY-type assets are declared skipped; pre-existing
    # candidates from earlier ingestion events are untouched.
    print("\n--- Part 2: SYSTEM policy fires on a new scan with provenance ---")
    pol = create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
        name="Low-risk system docs", asset_types=["SYSTEM"], created_by="GovernanceOfficer"),
        db_session=session)
    assert pol.version == 1 and pol.enabled
    assert events_of(session, "POLICY_CREATED"), "Policy creation must be audited"

    pre_existing_ids = {a.id for a in assets}
    write_file(folder_a, "doc2.txt", SYSTEM_SENTENCE_2, POLICY_SENTENCE_2)
    job2 = run_scan(session, connector_a)

    new_assets = [a for a in session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id).all() if a.id not in pre_existing_ids]
    system_assets = [a for a in new_assets if a.type == "SYSTEM"]
    policy_assets = [a for a in new_assets if a.type == "POLICY"]
    assert system_assets and policy_assets, f"Fixture must extract both types: {[(a.type, a.name) for a in new_assets]}"
    assert all(a.status == "APPROVED" for a in system_assets), "SYSTEM assets must be auto-approved"
    assert all(a.status == "CANDIDATE" for a in policy_assets), "POLICY assets must stay in the review queue"
    assert all(session.get(db.KnowledgeAsset, i).status == "CANDIDATE" for i in pre_existing_ids), \
        "Policy applies to THIS ingestion event only, never retroactively"

    approved = system_assets[0]
    review = session.query(db.AssetReview).filter(db.AssetReview.asset_id == approved.id).first()
    assert review and review.approver == f"policy:{pol.name}", review.approver if review else None
    assert "approved by policy: Low-risk system docs (v1)" in review.notes
    baseline = [r for r in approved.revisions if r.status == "APPROVED"]
    assert baseline and baseline[0].revision_number == 1, "Approval must create the baseline revision"

    auto_events = events_of(session, "ASSET_AUTO_APPROVED")
    assert len(auto_events) == len(system_assets)
    prov = json.loads(auto_events[0].details)
    assert prov["policy_id"] == pol.id and prov["policy_version"] == 1
    assert prov["approved_without_human"] is True
    assert prov["ingestion_job_id"] == job2.id
    assert prov["policy_snapshot"]["asset_types"] == ["SYSTEM"]
    assert auto_events[0].actor == f"policy:{pol.name}"

    summaries = events_of(session, "POLICY_AUTOAPPROVAL_COMPLETED")
    assert len(summaries) == 1
    summary = json.loads(summaries[0].details)
    assert summary["auto_approved"] == len(system_assets)
    assert summary["skipped_type_not_covered"] >= 1, "Declined assets must be declared, never silent"
    print(f"Part 2 passed: {len(system_assets)} auto-approved with provenance, "
          f"{summary['skipped_type_not_covered']} declared skips, queue keeps POLICY assets.")

    # Part 3: a source change to an auto-approved asset becomes a candidate
    # revision and WAITS - policies never approve revisions.
    print("\n--- Part 3: Changed source -> candidate revision stays human-gated ---")
    write_file(folder_a, "doc2.txt", SYSTEM_SENTENCE_2_CHANGED, POLICY_SENTENCE_2)
    job3 = run_scan(session, connector_a)
    assert job3.files_changed == 1, f"doc2 must be detected as CHANGED: {job3.files_changed}"
    session.refresh(approved)
    assert approved.content == SYSTEM_SENTENCE_2, "Approved content must not change without a human"
    pending = [r for r in approved.revisions if r.status == "CANDIDATE"]
    assert pending, "The change must produce a CANDIDATE revision"
    assert pending[0].status == "CANDIDATE", "A policy must never approve a revision"
    print("Part 3 passed: revision created by the change, still CANDIDATE despite a matching SYSTEM policy.")

    # Part 4: scoping the policy to connector A (a definition change) bumps
    # the version; connector B scans are no longer covered.
    print("\n--- Part 4: Connector scope + version bump ---")
    pol = update_approval_policy(pol.id, schemas.ApprovalPolicyUpdate(connector_id=connector_a.id),
                                 actor="GovernanceOfficer", db_session=session)
    assert pol.version == 2, "Definition change must bump the version"
    assert events_of(session, "POLICY_UPDATED")
    write_file(folder_b, "doc3.txt", "The analytics platform stores metrics in a Qdrant database node.")
    run_scan(session, connector_b)
    b_doc = session.query(db.Document).filter(db.Document.filename == "doc3.txt").first()
    b_assets = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.document_id == b_doc.id).all()
    assert b_assets and all(a.status == "CANDIDATE" for a in b_assets), \
        "A policy scoped to connector A must not fire for connector B"
    print("Part 4 passed: version 1 -> 2 on scope change, connector B stays manual.")

    # Part 5: disabling is an audited operational toggle, not a new version.
    print("\n--- Part 5: Disabled policy is a no-op ---")
    pol = update_approval_policy(pol.id, schemas.ApprovalPolicyUpdate(enabled=False),
                                 actor="GovernanceOfficer", db_session=session)
    assert pol.enabled is False and pol.version == 2, "Enable/disable must not bump the version"
    assert events_of(session, "POLICY_DISABLED")
    write_file(folder_a, "doc4.txt", "The backup server replicates the database to a standby platform node.")
    run_scan(session, connector_a)
    d4 = session.query(db.Document).filter(db.Document.filename == "doc4.txt").first()
    d4_assets = session.query(db.KnowledgeAsset).filter(db.KnowledgeAsset.document_id == d4.id).all()
    assert d4_assets and all(a.status == "CANDIDATE" for a in d4_assets), \
        "A disabled policy must approve nothing"
    print("Part 5 passed: disabled policy approved nothing, toggle audited without a version bump.")

    # Part 6: rule hygiene - invalid asset types are rejected.
    print("\n--- Part 6: Validation ---")
    try:
        create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
            name="Bad", asset_types=["SYSTEM", "SALARY"]), db_session=session)
        raise AssertionError("Invalid asset type must be rejected")
    except Exception as e:
        assert "SALARY" in str(e), str(e)
    try:
        create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
            name="Empty", asset_types=[]), db_session=session)
        raise AssertionError("Empty asset type list must be rejected")
    except Exception as e:
        assert "non-empty" in str(e), str(e)
    print("Part 6 passed: invalid and empty type lists rejected.")

    print("\nAll Policy-Based Auto Approval checks passed.")


if __name__ == "__main__":
    main()
