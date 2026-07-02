"""v1.2.1 WS4 corpus acceptance gate (docs/ingestion-automation-v1.2.1.md).

The milestone's headline proof, in CI: a mature synthetic corpus (fake
Graph tenant) flows through an active classification + Tier-0 + Tier-2
policy set and reaches >= 90% auto-approval with machine-verifiable
provenance, surfaces 100% of exceptions severity-ranked in the computed
inbox, auto-approves ZERO revisions, silently holds ZERO assets, and
leaves the north-star metric - document arrival to usable expert model -
derivable from audit events ALONE.

The corpus profile (one governed SharePoint library):
  28 x source-approved policy documents  -> Tier-0 (inherited authority)
   1 x source-approved system document   -> Tier-0 (later CHANGED: the
                                             revision case - human-gated)
   1 x ops-classified seed (approved)    -> Tier-0 + WS1 classification
   1 x ops-classified clean candidate    -> Tier-2 engine-verified
   1 x ops-classified contradicting doc  -> Tier-2 HELD (names the seed)
   1 x draft-in-source policy document   -> Tier-0 held (no authority)
   1 x role document (uncovered type)    -> ordinary human queue
"""
import os
import sys
import json
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_SECRET_KEY"] = "corpus-suite-master-key"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_corpus_qdrant_")

from app import crud
from app import custody
from app import policy
from app import tier2
from app import schemas
from app import governance_inbox
from app.connectors import framework
from app.connectors.providers import sharepoint
from app.main import create_approval_policy, create_classification_policy
import test_sharepoint_provider as sp
import test_support

MARKER = "five days weekly"
SEED = "Employees must work from the office five days weekly."
CONTRA = "Employees must work remotely five days weekly."
CLEAN = "Suppliers must submit invoices through the procurement portal."
DRAFT = "Contractors must wear identification badges inside the facility."
ROLE = "The duty manager is responsible for the evening handover briefing."
SYSTEM_DOC = "The reporting platform archives records in a SQLite database server."
SYSTEM_DOC_CHANGED = "The reporting platform archives records in a MariaDB database server."


class MarkerVerifier:
    identity = {"method": "FAKE_DETERMINISTIC_V1", "marker": MARKER,
                "note": "WS4 corpus seam - identity recorded in provenance"}

    def check(self, candidate, corpus):
        contradictions = [
            {"asset_id": a.id, "score": 0.99}
            for a in corpus if MARKER in candidate.content and MARKER in a.content]
        return {"pairs_checked": len(corpus), "pairs_dropped": 0,
                "contradictions": contradictions}


class CorpusGraph(sp.FakeGraph):
    """The mature-corpus tenant: everything in one governed library, each
    item carrying the authority posture a real QMS exposes."""

    def __init__(self):
        super().__init__()
        self.items = {}
        self.folders = {}
        self.fields = {}

        def add(item_id, name, text, fields=None):
            self.items[item_id] = dict(
                drive="drive-1", parent=None, name=name,
                content=(text + "\n").encode(),
                modified="2026-07-01T10:00:00Z", modified_by="Quality Manager")
            if fields:
                self.fields[item_id] = fields

        for i in range(1, 29):
            add(f"proc-{i:02d}", f"directive-{i:02d}.txt",
                f"Operators must follow directive {i:02d} of the quality manual.",
                {"ApprovalStatus": "Approved"})
        add("sys-1", "reporting.txt", SYSTEM_DOC, {"ApprovalStatus": "Approved"})
        add("seed-1", "office-policy.txt", SEED,
            {"ApprovalStatus": "Approved", "Category": "Ops"})
        add("clean-1", "procurement.txt", CLEAN, {"Category": "Ops"})
        add("contra-1", "remote-policy.txt", CONTRA, {"Category": "Ops"})
        add("draft-1", "badges.txt", DRAFT, {"ApprovalStatus": "Draft"})
        add("role-1", "handover.txt", ROLE, {"Category": "Ops"})

    def _entry(self, item_id):
        entry = super()._entry(item_id)
        fields = self.fields.get(item_id)
        if fields:
            entry["listItem"] = {"fields": fields}
        return entry


def events_of(session, event_type):
    return session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == event_type).order_by(db.AuditEvent.id).all()


def main():
    print("\nInitializing test database for the v1.2.1 corpus acceptance gate...")
    tmp = tempfile.mkdtemp(prefix="em_corpus_test_")
    db.engine = create_engine(f"sqlite:///{os.path.join(tmp, 'corpus.db')}",
                              connect_args={"check_same_thread": False})
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)
    db.Base.metadata.create_all(db.engine)
    session = db.SessionLocal()

    tier2.verifier_factory = MarkerVerifier

    admin = test_support.governed_actor(session, "corpus_admin", role="ADMIN")
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Corpus", description="WS4 gate", customer_id=customer.id), actor=officer)

    graph = CorpusGraph()
    sharepoint.default_transport_factory = lambda: graph
    cred = custody.create_external_credential(
        session, name="Graph client", purpose="CONNECTOR", secret=sp.FAKE_SECRET,
        actor=admin, granted_scopes=["Sites.Selected"],
        coordinates={"tenant_id": sp.TENANT, "client_id": sp.CLIENT})
    connector = db.SourceConnector(
        project_id=project.id, name="qms-corpus", type="SHAREPOINT",
        root_path=sp.SITE_URL, external_credential_id=cred.id)
    session.add(connector)
    session.commit()
    session.refresh(connector)

    # The active policy set (all governed, all versioned, all BEFORE the scan):
    create_classification_policy(project.id, schemas.ClassificationPolicyCreate(
        name="Ops by category",
        rules=[{"domain": "ops",
                "match": {"metadata": [{"key": "list_item_fields.Category",
                                        "equals": "Ops"}]}}]),
        db_session=session, actor=officer)
    create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
        name="QMS source authority", asset_types=["POLICY", "SYSTEM"],
        source_conditions=[{"key": "list_item_fields.ApprovalStatus",
                            "equals": "Approved"}]),
        db_session=session, actor=officer)
    create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
        name="Ops engine verified", asset_types=["POLICY"],
        engine_conditions={"contradiction_check": "CLEAN_REQUIRED"},
        domains=["ops"]),
        db_session=session, actor=officer)

    # ---------------------------------------------------------- the scan
    print("\n--- The corpus scan (34 documents, one governed pipeline) ---")
    job = db.IngestionJob(project_id=project.id, connector_id=connector.id,
                          status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    framework.execute_ingestion_job(session, job.id)
    tier2.drain()
    session.refresh(job)
    assert job.status == "COMPLETED", job.error
    assert job.files_ingested == 34, job.files_ingested

    assets = session.query(db.KnowledgeAsset).filter_by(project_id=project.id).all()
    approved = [a for a in assets if a.status == "APPROVED"]
    candidates = [a for a in assets if a.status == "CANDIDATE"]
    rate = len(approved) / len(assets)
    print(f"Corpus: {len(assets)} assets, {len(approved)} auto-approved, "
          f"{len(candidates)} held -> {rate:.1%}")
    assert rate >= 0.90, (
        f"GATE FAILED: mature-corpus auto-approval {rate:.1%} < 90%")

    # Machine-verifiable provenance on EVERY approval - no exceptions.
    auto_events = events_of(session, "ASSET_AUTO_APPROVED")
    approved_by_event = {}
    for e in auto_events:
        details = json.loads(e.details)
        approved_by_event[int(e.target_id)] = details
        assert details["policy_id"] and details["policy_version"] and \
            details["policy_snapshot"], "Provenance must be complete"
        assert details["approved_without_human"] is True
    assert {a.id for a in approved} == set(approved_by_event), \
        "Every approved asset must carry an ASSET_AUTO_APPROVED event - " \
        "no ungoverned approvals"
    tier0 = [d for d in approved_by_event.values() if d["policy_snapshot"]["source_conditions"]]
    tier2_approved = [d for d in approved_by_event.values() if d.get("tier") == "TIER2"]
    assert all(d["source_authority"]["matched"] for d in tier0), \
        "Tier-0 approvals quote the inherited authority verbatim"
    assert len(tier2_approved) == 1 and \
        tier2_approved[0]["engine_verdict"]["verifier"]["method"] == "FAKE_DETERMINISTIC_V1"
    print(f"Provenance: {len(tier0)} Tier-0 (authority quoted), "
          f"{len(tier2_approved)} Tier-2 (engine verdict recorded).")

    # ------------------------------------------------- the revision case
    print("\n--- The revision case: trusted content changes at the source ---")
    graph.set_content("sys-1", (SYSTEM_DOC_CHANGED + "\n").encode())
    job2 = db.IngestionJob(project_id=project.id, connector_id=connector.id,
                           status="PENDING")
    session.add(job2)
    session.commit()
    session.refresh(job2)
    framework.execute_ingestion_job(session, job2.id)
    tier2.drain()
    session.refresh(job2)
    assert job2.status == "COMPLETED" and job2.files_changed == 1, \
        (job2.files_changed, job2.error)
    sys_asset = next(a for a in assets if a.content == SYSTEM_DOC)
    session.refresh(sys_asset)
    assert sys_asset.content == SYSTEM_DOC, \
        "Approved content never changes without a human"
    pending_revisions = [r for r in sys_asset.revisions if r.status == "CANDIDATE"]
    assert pending_revisions, "The source change must produce a candidate revision"
    all_revisions = session.query(db.AssetRevision).all()
    assert not any(
        r.status == "APPROVED" and r.revision_number > 1
        and (r.approved_by or "").startswith("policy:") for r in all_revisions), \
        "ZERO revisions auto-approved - the D17 hard line"
    print("Revision case passed: candidate revision pending, zero revisions "
          "auto-approved.")

    # ------------------------------------------- the exception surface
    print("\n--- 100% of exceptions surfaced, severity-ranked, zero silent holds ---")
    inbox = governance_inbox.build_inbox(session, project.id)
    exceptions = [i for i in inbox["items"] if i["type"] == "INGESTION_EXCEPTION"]
    session.expire_all()
    still_candidates = session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id, status="CANDIDATE").all()
    assert {i["asset_id"] for i in exceptions} == {a.id for a in still_candidates}, \
        "GATE FAILED: every held candidate is surfaced, none silently - and " \
        "nothing else is"
    assert inbox["summary"]["ingestion_exceptions"] == len(exceptions) == 3

    by_kind = {i["classification"]: i for i in exceptions}
    contra_asset = next(a for a in still_candidates if a.content == CONTRA)
    seed_asset = next(a for a in assets if a.content == SEED)
    item = by_kind["TIER2_CONTRADICTION_HELD"]
    assert item["severity"] == "MEDIUM" and item["asset_id"] == contra_asset.id
    assert item["contradicting_asset_id"] == seed_asset.id, \
        "The Tier-2 exception names the contradicting approved asset"
    assert by_kind["SOURCE_AUTHORITY_HELD"]["severity"] == "MEDIUM"
    assert by_kind["NOT_COVERED"]["severity"] == "LOW"
    assert all(i["severity"] != "HIGH" for i in exceptions), \
        "Ingestion exceptions never block the compile gate (D2) - never HIGH"
    # Ranked: within the sorted inbox, every MEDIUM exception precedes
    # every LOW exception.
    positions = {i["classification"]: n for n, i in enumerate(inbox["items"])
                 if i["type"] == "INGESTION_EXCEPTION"}
    assert positions["TIER2_CONTRADICTION_HELD"] < positions["NOT_COVERED"]
    assert positions["SOURCE_AUTHORITY_HELD"] < positions["NOT_COVERED"]
    # Every exception explains itself from provenance.
    assert all(i["reason"] and i["deep_link"] for i in exceptions)
    print(f"Exceptions: {len(exceptions)} surfaced "
          f"({sorted(by_kind)}), ranked, each with why-held and a deep link.")

    # -------------------------- the north-star metric, from events ALONE
    print("\n--- North-star metric: document arrival -> usable expert model ---")
    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        project_id=project.id, name="QMS Expert", description="corpus gate",
        asset_ids=[a.id for a in approved]), actor=officer)

    # Derived exclusively from the audit ledger - no other table touched.
    # Arrival = the FIRST scan's start (the revision rescan came later).
    arrival = events_of(session, "INGESTION_JOB_STARTED")[0].timestamp
    first_approval = min(e.timestamp for e in auto_events)
    usable = events_of(session, "EXPERT_MODEL_CREATED")[-1].timestamp
    assert arrival <= first_approval <= usable
    metric = {
        "document_arrival": arrival.isoformat(),
        "first_auto_approval": first_approval.isoformat(),
        "usable_expert_model": usable.isoformat(),
        "arrival_to_usable_seconds": (usable - arrival).total_seconds(),
    }
    print(f"North-star metric (events alone): "
          f"{metric['arrival_to_usable_seconds']:.1f}s from arrival to "
          f"usable expert model ({len(approved)} governed assets).")

    # D25 discipline: nothing in this suite surfaced the secret.
    with db.engine.connect() as conn:
        for table in db.Base.metadata.sorted_tables:
            for row in conn.execute(table.select()):
                assert sp.FAKE_SECRET not in str(tuple(row)), \
                    f"D25 violation: secret readable in {table.name}"

    session.close()
    print(f"\nv1.2.1 corpus acceptance gate PASSED: {rate:.1%} auto-approved "
          f"with machine-verifiable provenance, 100% of exceptions surfaced "
          f"and ranked, zero revisions auto-approved, zero silent holds, "
          f"north-star metric derivable from the ledger alone.")


if __name__ == "__main__":
    main()
