"""v1.2.1 WS2 gate suite (docs/ingestion-automation-v1.2.1.md): Tier-0
source-authority policies over a fake Graph tenant (D26).

The gate: source-approved documents reach APPROVED through source
metadata conditions; unapproved documents from the SAME scan remain
governed exceptions (declared, never silent); ASSET_AUTO_APPROVED quotes
the matched authority metadata VERBATIM; condition-less policies retain
v0.10.2 behavior exactly; later policy edits bump the version while
historical approval events keep pointing at the original rule snapshot
that fired.

The guardrail: source authority is EVIDENCE for approval, not approval
itself - a Tier-0 source is trusted only through an explicit governed
policy with versioned rules and audit evidence. The metadata itself is
source provenance, never editable approval state (no API writes it).
"""
import os
import sys
import json
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_SECRET_KEY"] = "tier0-suite-master-key"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_tier0_qdrant_")

from app import crud
from app import custody
from app import policy
from app import schemas
from app.connectors import framework
from app.connectors.providers import sharepoint
from app.main import create_approval_policy, update_approval_policy
import test_sharepoint_provider as sp
import test_support

# The tenant: three parseable documents in one library, each carrying a
# different authority posture. Every document extracts a POLICY asset
# (rule-based extraction: "must" + >=30 chars), so the SAME scan yields
# approved-in-source, draft-in-source, and no-authority-exposed assets.
APPROVED_TEXT = b"All operators must complete safety training before access is granted.\n"
DRAFT_TEXT = b"Contractors must wear identification badges inside the facility.\n"
SILENT_TEXT = b"Visitors must sign the reception logbook before entering the plant.\n"


class Tier0Graph(sp.FakeGraph):
    """The fake Graph tenant, now exposing listItem fields (content type
    and tenant approval status) for SOME items - exactly what a governed
    SharePoint library exposes, absent where the tenant exposes nothing."""

    def __init__(self):
        super().__init__()
        self.items["item-1"]["content"] = APPROVED_TEXT       # safety-policy.txt
        self.items["item-4"]["content"] = DRAFT_TEXT          # Ops/retention.txt
        self.items["item-2"] = dict(drive="drive-1", parent=None,
                                    name="visitor-note.txt", content=SILENT_TEXT,
                                    modified="2026-06-20T08:30:00Z",
                                    modified_by="Site Owner")
        self.fields = {
            "item-1": {"ApprovalStatus": "Approved", "ContentType": "SOP"},
            "item-4": {"ApprovalStatus": "Draft", "ContentType": "SOP"},
            # item-2: the tenant exposes NO list-item fields at all.
        }

    def _entry(self, item_id):
        entry = super()._entry(item_id)
        fields = self.fields.get(item_id)
        if fields:
            entry["listItem"] = {"fields": fields}
        return entry


def events_of(session, event_type):
    return session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == event_type).order_by(db.AuditEvent.id).all()


def asset_for_document(session, project_id, filename):
    doc = session.query(db.Document).filter(
        db.Document.project_id == project_id,
        db.Document.filename == filename).first()
    assert doc, f"Document {filename} not ingested"
    assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id == doc.id).all()
    assert assets, f"No assets extracted from {filename}"
    return assets


def main():
    print("\nInitializing test database for Tier-0 Source Authority (D26) checks...")
    tmp = tempfile.mkdtemp(prefix="em_tier0_test_")
    db.engine = create_engine(f"sqlite:///{os.path.join(tmp, 'tier0.db')}",
                              connect_args={"check_same_thread": False})
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)
    db.Base.metadata.create_all(db.engine)
    session = db.SessionLocal()

    admin = test_support.governed_actor(session, "tier0_admin", role="ADMIN")
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Tier0", description="D26 gate", customer_id=customer.id), actor=officer)

    graph = Tier0Graph()
    sharepoint.default_transport_factory = lambda: graph
    cred = custody.create_external_credential(
        session, name="Graph client", purpose="CONNECTOR", secret=sp.FAKE_SECRET,
        actor=admin, granted_scopes=["Sites.Selected"],
        coordinates={"tenant_id": sp.TENANT, "client_id": sp.CLIENT})
    connector = db.SourceConnector(
        project_id=project.id, name="qms-tier0", type="SHAREPOINT",
        root_path=sp.SITE_URL, external_credential_id=cred.id)
    session.add(connector)
    session.commit()
    session.refresh(connector)

    def scan():
        job = db.IngestionJob(project_id=project.id, connector_id=connector.id,
                              status="PENDING")
        session.add(job)
        session.commit()
        framework.execute_ingestion_job(session, job.id)
        session.refresh(job)
        assert job.status == "COMPLETED", job.error
        return job

    # The Tier-0 policy exists BEFORE the scan: approval happens at
    # ingestion, through the same governed path as always.
    pol = create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
        name="QMS source authority",
        asset_types=sorted(policy.ALLOWED_ASSET_TYPES),
        source_conditions=[{"key": "list_item_fields.ApprovalStatus",
                            "equals": "Approved"}]),
        db_session=session, actor=officer)
    assert pol.version == 1 and pol.source_conditions

    # Part 1: rejected shapes - a malformed condition is a rejected
    # definition, never a rule that silently never fires.
    print("\n--- Part 1: condition validation (loud, never permissive) ---")
    for bad, why in [
        ([{"equals": "x"}], "condition without key"),
        ([{"key": "k"}], "condition without operator"),
        ([{"key": "k", "equals": "a", "in": ["b"]}], "both operators"),
        ([{"key": "k", "in": "not-a-list"}], "in must be a list"),
        ([{"key": "k", "equals": "a", "regex": ".*"}], "unknown field"),
    ]:
        try:
            create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
                name="Bad", asset_types=["POLICY"], source_conditions=bad),
                db_session=session, actor=officer)
            raise AssertionError(f"Must reject: {why}")
        except Exception as e:
            assert getattr(e, "status_code", None) == 400, f"{why}: {e}"
    print("Part 1 passed: five malformed condition shapes rejected at "
          "definition time.")

    # Part 2: the scan - metadata persisted verbatim, Tier-0 fires only
    # where the source authority is present.
    print("\n--- Part 2: one scan, three authority postures ---")
    job = scan()
    assert job.files_ingested == 3, (job.files_ingested, job.error)

    rows = {r.source_uri.rsplit("/", 1)[-1]: r
            for r in session.query(db.SourceDocument).filter_by(
                ingestion_job_id=job.id).all()}
    approved_row = rows["item-1"]
    meta = approved_row.source_metadata
    assert meta["list_item_fields"] == {"ApprovalStatus": "Approved",
                                        "ContentType": "SOP"}, \
        "Discovery metadata must be persisted VERBATIM on the scan row"
    assert meta["last_modified_by"] == "Quality Manager"
    silent_row = rows["item-2"]
    assert silent_row.source_metadata.get("list_item_fields") is None, \
        "Fields the tenant does not expose stay absent - never fabricated (D12)"

    approved_assets = asset_for_document(session, project.id, "safety-policy.txt")
    draft_assets = asset_for_document(session, project.id, "retention.txt")
    silent_assets = asset_for_document(session, project.id, "visitor-note.txt")
    assert all(a.status == "APPROVED" for a in approved_assets), \
        "Source-approved documents must reach APPROVED via Tier-0"
    assert all(a.status == "CANDIDATE" for a in draft_assets), \
        "Draft-in-source stays a governed exception"
    assert all(a.status == "CANDIDATE" for a in silent_assets), \
        "Absent authority metadata never satisfies a condition (D12)"

    # Tier-0 provenance: the inherited authority quoted VERBATIM, plus
    # the exact rule snapshot that fired.
    auto = events_of(session, "ASSET_AUTO_APPROVED")
    assert len(auto) == len(approved_assets)
    prov = json.loads(auto[0].details)
    assert prov["policy_version"] == 1
    assert prov["policy_snapshot"]["source_conditions"] == [
        {"key": "list_item_fields.ApprovalStatus", "equals": "Approved"}]
    assert prov["source_authority"]["matched"] == {
        "list_item_fields.ApprovalStatus": "Approved"}
    assert prov["source_authority"]["source_uri"].endswith("/item-1")

    # The exceptions are DECLARED, never silently ignored.
    summary = json.loads(events_of(session, "POLICY_AUTOAPPROVAL_COMPLETED")[-1].details)
    assert summary["auto_approved"] == len(approved_assets)
    assert summary["skipped_source_conditions_unmet"] == \
        len(draft_assets) + len(silent_assets), summary
    held = set(summary["source_condition_held_ids"])
    assert held == {a.id for a in draft_assets} | {a.id for a in silent_assets}
    print(f"Part 2 passed: {len(approved_assets)} approved with authority "
          f"quoted verbatim; {len(held)} held and declared from the same scan.")

    # Part 3: the NULL-condition invariant - a condition-less policy
    # behaves exactly as v0.10.2, even where metadata is absent.
    print("\n--- Part 3: condition-less policies retain v0.10.2 behavior ---")
    create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
        name="Plain tier-1", asset_types=sorted(policy.ALLOWED_ASSET_TYPES)),
        db_session=session, actor=officer)
    result = policy.apply_auto_approval(
        session, project.id,
        [a.document_id for a in draft_assets + silent_assets],
        connector_id=connector.id, ingestion_job_id=job.id,
        on_behalf_of_fact=officer.fact(session))
    assert result["auto_approved"] == len(draft_assets) + len(silent_assets), result
    for a in draft_assets + silent_assets:
        session.refresh(a)
        assert a.status == "APPROVED", \
            "A condition-less policy fires regardless of source metadata (D19 invariant)"
    # Its provenance carries NO source_authority claim - it did not use one.
    latest = json.loads(events_of(session, "ASSET_AUTO_APPROVED")[-1].details)
    assert latest["policy_snapshot"]["source_conditions"] is None
    assert "source_authority" not in latest
    # Empty condition arrays evaluate as "no conditions to fail".
    class EmptyConditions:
        source_conditions = []
    met, evidence = policy.source_conditions_met(EmptyConditions(), None)
    assert met and evidence is None
    print("Part 3 passed: condition-less policy approved everything Tier-0 "
          "held, without claiming authority it did not use; empty arrays "
          "preserve prior behavior.")

    # Part 4: versioning - editing conditions bumps the version; history
    # keeps pointing at the rule that actually fired.
    print("\n--- Part 4: condition edits bump the version; history immutable ---")
    pol = update_approval_policy(pol.id, schemas.ApprovalPolicyUpdate(
        source_conditions=[{"key": "list_item_fields.ApprovalStatus",
                            "in": ["Approved", "Published"]}]),
        db_session=session, actor=officer)
    assert pol.version == 2, "A condition edit is a definition change"
    updated = json.loads(events_of(session, "POLICY_UPDATED")[-1].details)
    assert updated["old"]["source_conditions"] == [
        {"key": "list_item_fields.ApprovalStatus", "equals": "Approved"}]
    assert updated["new"]["source_conditions"] == [
        {"key": "list_item_fields.ApprovalStatus", "in": ["Approved", "Published"]}]
    # The historical approval event still carries version 1 and the
    # ORIGINAL rule snapshot - later edits never rewrite or reinterpret it.
    historical = json.loads(events_of(session, "ASSET_AUTO_APPROVED")[0].details)
    assert historical["policy_version"] == 1
    assert historical["policy_snapshot"]["source_conditions"] == [
        {"key": "list_item_fields.ApprovalStatus", "equals": "Approved"}]
    print("Part 4 passed: v1 -> v2 on condition edit; the v1 approval "
          "event still quotes the v1 rule.")

    # Part 5: metadata is source provenance, not editable approval state -
    # no API surface writes source_metadata_json (route-table proof).
    print("\n--- Part 5: source metadata has no write surface ---")
    from app.main import app as fastapi_app
    for route in fastapi_app.routes:
        path = getattr(route, "path", "")
        if "source" in path.lower() and "metadata" in path.lower():
            raise AssertionError(f"No route may administer source metadata: {path}")
    import inspect
    fields = [f for f in vars(schemas).values()
              if inspect.isclass(f) and hasattr(f, "model_fields")]
    for model in fields:
        assert "source_metadata_json" not in model.model_fields, (
            f"{model.__name__} exposes source_metadata_json as writable "
            f"input - it is scan evidence, never editable state")
    print("Part 5 passed: no route, no schema accepts source metadata as "
          "input - it exists only as recorded scan evidence.")

    # D25 discipline carried over: nothing in this suite surfaced the
    # fake client secret anywhere.
    with db.engine.connect() as conn:
        for table in db.Base.metadata.sorted_tables:
            for row in conn.execute(table.select()):
                assert sp.FAKE_SECRET not in str(tuple(row)), \
                    f"D25 violation: secret readable in {table.name}"

    session.close()
    print("\nAll Tier-0 Source Authority (D26) checks passed: source "
          "authority is evidence consumed by explicit governed policies - "
          "inherited approvals quote it verbatim, exceptions are declared, "
          "and the rule that fired stays answerable forever.")


if __name__ == "__main__":
    main()
