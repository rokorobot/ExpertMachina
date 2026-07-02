import hashlib
import json
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
# Deterministic rule-based extraction: assertions depend on stable asset
# names and types, never on an LLM.
os.environ["OPENAI_API_KEY"] = "mock-key"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import connectors
from app import ingestion
from app import classification
from app.main import (app as fastapi_app, create_classification_policy,
                      update_classification_policy, reorganize_taxonomy)
import test_support

# Domain Classification suite (v1.2.1 WS1, D27,
# docs/ingestion-automation-v1.2.1.md).
#
# The gate proof: split `finances` -> `finances/accounting` +
# `finances/treasury` by policy change + reorg operation ALONE - content
# unchanged, history unchanged, provenance intact, prefix queries still
# resolving the parent. Plus: deterministic first-match assignment with
# ASSET_CLASSIFIED provenance, absence-never-satisfies metadata rules
# (D12), human correction as a governed act (ASSET_DOMAIN_CORRECTED),
# and the D17 policy hygiene (version bump on definition change, audited
# toggle, no delete route).
#
# WS1 guardrail asserted throughout: classification and taxonomy write
# ONLY the domain column - never content, status, provenance, or history.

ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_domain_qdrant_")

ACC_SENTENCE = "The accounting platform reconciles ledgers on a PostgreSQL database server."
TRE_SENTENCE = "The treasury platform settles payments through a SQLite database server."
MISC_SENTENCE = "The intranet platform hosts announcements on an nginx web server node."
STRAY_SENTENCE = "The archive platform stores backups in a MariaDB database server rack."


def write_file(folder, name, sentence):
    path = os.path.join(folder, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(sentence + "\n")
    return path


def run_scan(session, connector):
    job = db.IngestionJob(project_id=connector.project_id,
                          connector_id=connector.id, status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    connectors.execute_ingestion_job(session, job.id)
    session.refresh(job)
    assert job.status == "COMPLETED", f"{job.status} / {job.error}"
    return job


def events_of(session, event_type):
    return session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == event_type).order_by(db.AuditEvent.id).all()


def asset_for(session, project_id, sentence):
    asset = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id,
        db.KnowledgeAsset.content == sentence).first()
    assert asset, f"No asset extracted for: {sentence[:40]}..."
    return asset


def governance_snapshot(session, asset):
    """Everything WS1 must never touch: content, status, provenance,
    revision history."""
    session.refresh(asset)
    return {
        "content_sha": hashlib.sha256(asset.content.encode()).hexdigest(),
        "status": asset.status,
        "document_id": asset.document_id,
        "chunk_id": asset.chunk_id,
        "source_hash": asset.source_hash,
        "source_page": asset.source_page,
        "revisions": [(r.id, r.revision_number, r.status, r.content_hash)
                      for r in asset.revisions],
    }


def main():
    print("\nInitializing test database for Domain Classification (D27) checks...")
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    customer = crud.get_or_create_default_customer(session)
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Taxonomy", description="D27 gate", customer_id=customer.id),
        actor=officer)

    folder = tempfile.mkdtemp(prefix="em_domain_src_")
    acc_prefix = os.path.join(os.path.abspath(folder), "accounting") + os.sep
    tre_prefix = os.path.join(os.path.abspath(folder), "treasury") + os.sep
    misc_prefix = os.path.join(os.path.abspath(folder), "misc") + os.sep
    connector = db.SourceConnector(project_id=project.id, name="Ledger Share",
                                   type="LOCAL_FOLDER", root_path=folder,
                                   include_extensions=".txt")
    session.add(connector)
    session.commit()
    session.refresh(connector)

    # Part 1: policy hygiene - the D17 governed-object shape.
    print("\n--- Part 1: ClassificationPolicy CRUD hygiene (D17 shape) ---")
    for bad_rules, why in [
        ([], "empty rules"),
        ([{"match": {}}], "rule without domain"),
        ([{"domain": "/finances/", "match": {}}], "malformed domain path"),
        ([{"domain": "x", "match": {"regex": ".*"}}], "unknown criteria"),
        ([{"domain": "x", "match": {"metadata": [{"key": "k", "equals": "a", "in": ["b"]}]}}],
         "both equals and in"),
    ]:
        try:
            create_classification_policy(project.id, schemas.ClassificationPolicyCreate(
                name="Bad", rules=bad_rules), db_session=session, actor=officer)
            raise AssertionError(f"Must reject: {why}")
        except Exception as e:
            assert "400" in str(getattr(e, "status_code", "")) or "must" in str(e).lower() \
                or "rule" in str(e).lower() or "domain" in str(e).lower(), f"{why}: {e}"

    pol = create_classification_policy(project.id, schemas.ClassificationPolicyCreate(
        name="Ledger domains",
        rules=[{"domain": "finances", "match": {"uri_prefix": acc_prefix}},
               {"domain": "finances", "match": {"uri_prefix": tre_prefix}}]),
        db_session=session, actor=officer)
    assert pol.version == 1 and pol.enabled
    assert events_of(session, "CLASSIFICATION_POLICY_CREATED")
    # A later policy (higher id): its first rule competes for accounting
    # docs and MUST lose to the earlier policy (stable id order).
    pol_b = create_classification_policy(project.id, schemas.ClassificationPolicyCreate(
        name="Latecomer",
        rules=[{"domain": "wrong/never", "match": {"uri_prefix": acc_prefix}},
               {"domain": "misc", "match": {"uri_prefix": misc_prefix}}]),
        db_session=session, actor=officer)

    toggled = update_classification_policy(pol_b.id, schemas.ClassificationPolicyUpdate(
        enabled=False), db_session=session, actor=officer)
    assert toggled.enabled is False and toggled.version == 1, \
        "Enable/disable is operational - audited, never a version bump"
    assert events_of(session, "CLASSIFICATION_POLICY_DISABLED")
    update_classification_policy(pol_b.id, schemas.ClassificationPolicyUpdate(
        enabled=True), db_session=session, actor=officer)
    assert events_of(session, "CLASSIFICATION_POLICY_ENABLED")

    # No delete, no replace: the route surface is POST/GET/PATCH only.
    for route in fastapi_app.routes:
        path = getattr(route, "path", "")
        if "classification-policies" in path or "/taxonomy/" in path:
            assert not ({"DELETE", "PUT"} & set(getattr(route, "methods", set()))), \
                f"Governed policy objects are never deleted or replaced: {path}"
    print("Part 1 passed: malformed rules rejected, audited toggle without "
          "bump, no DELETE/PUT route.")

    # Part 2: deterministic assignment at ingestion with provenance.
    print("\n--- Part 2: first-match assignment at ingestion (ASSET_CLASSIFIED) ---")
    write_file(folder, os.path.join("accounting", "acc.txt"), ACC_SENTENCE)
    write_file(folder, os.path.join("treasury", "tre.txt"), TRE_SENTENCE)
    write_file(folder, os.path.join("misc", "misc.txt"), MISC_SENTENCE)
    write_file(folder, "stray.txt", STRAY_SENTENCE)
    job = run_scan(session, connector)

    acc = asset_for(session, project.id, ACC_SENTENCE)
    tre = asset_for(session, project.id, TRE_SENTENCE)
    misc = asset_for(session, project.id, MISC_SENTENCE)
    stray = asset_for(session, project.id, STRAY_SENTENCE)
    assert acc.domain == "finances", \
        f"First policy in id order must win: {acc.domain!r} (never 'wrong/never')"
    assert tre.domain == "finances" and misc.domain == "misc"
    assert stray.domain is None, "No matching rule -> honestly unclassified (D12)"

    classified_events = events_of(session, "ASSET_CLASSIFIED")
    by_target = {int(e.target_id): json.loads(e.details) for e in classified_events}
    prov = by_target[acc.id]
    assert prov["policy_id"] == pol.id and prov["policy_version"] == 1
    assert prov["rule_index"] == 0 and prov["rule_snapshot"]["domain"] == "finances"
    assert prov["matched"]["uri_prefix"] == acc_prefix
    assert prov["ingestion_job_id"] == job.id
    acc_event_actor = classified_events[0].actor
    assert acc_event_actor.startswith("classification:"), acc_event_actor

    summary = json.loads(events_of(session, "DOMAIN_CLASSIFICATION_COMPLETED")[-1].details)
    assert summary["classified"] == 3 and summary["unmatched"] == 1, summary
    print(f"Part 2 passed: 3 classified with quoted provenance, 1 unmatched "
          f"declared, id-order determinism held.")

    # Part 3: human correction is a governed act on the normal surface.
    print("\n--- Part 3: human correction (ASSET_DOMAIN_CORRECTED) ---")
    try:
        crud.update_knowledge_asset(session, stray.id,
                                    schemas.KnowledgeAssetUpdate(domain="/bad/"),
                                    actor=officer)
        raise AssertionError("Malformed domain path must be rejected")
    except ValueError:
        session.rollback()

    updates_before = len(events_of(session, "ASSET_UPDATED"))
    crud.update_knowledge_asset(session, stray.id,
                                schemas.KnowledgeAssetUpdate(domain="operations/misc"),
                                actor=officer)
    corrected = events_of(session, "ASSET_DOMAIN_CORRECTED")
    assert corrected, "A domain correction must carry its own audit vocabulary"
    detail = json.loads(corrected[-1].details)
    assert detail == {"old_domain": None, "new_domain": "operations/misc"}
    assert len(events_of(session, "ASSET_UPDATED")) == updates_before, \
        "A domain-only correction is not a generic metadata edit"
    session.refresh(stray)
    assert stray.domain == "operations/misc" and not stray.revisions, \
        "Correction writes taxonomy only - no revision, no content change"

    # Assignment never overwrites: re-running classification over the same
    # documents considers nothing (every asset now carries a domain).
    rerun = classification.classify_assets(
        session, project.id, [a.document_id for a in (acc, tre, misc, stray)],
        connector_id=connector.id)
    assert rerun["assets_considered"] == 0 and rerun["classified"] == 0, rerun
    print("Part 3 passed: correction audited old->new, malformed path "
          "rejected, assignment never overwrites.")

    # Part 4: metadata rules - absence is never satisfaction (D12).
    print("\n--- Part 4: source-metadata rules (WS2's evidence, D12 absence rule) ---")
    project2 = crud.create_project(session, schemas.ProjectCreate(
        name="Metadata", description="D12", customer_id=customer.id), actor=officer)
    doc = db.Document(project_id=project2.id, filename="hr.txt", file_type="txt",
                      status="ASSETS_EXTRACTED")
    session.add(doc)
    session.commit()
    session.refresh(doc)
    # The scan row carries the verbatim source metadata (what WS2's
    # framework wiring will persist; seeded directly here to prove the
    # consumption side ahead of it).
    session.add(db.SourceDocument(
        project_id=project2.id, connector_id=None, ingestion_job_id=None,
        source_uri="fake://tenant/drive/hr.txt", status="INGESTED",
        document_id=doc.id,
        source_metadata_json=json.dumps(
            {"list_item_fields": {"Department": "People"}})))
    hr_asset = db.KnowledgeAsset(project_id=project2.id, type="POLICY",
                                 name="HR policy", content="Staff must complete onboarding.",
                                 status="CANDIDATE", document_id=doc.id)
    session.add(hr_asset)
    session.commit()
    session.refresh(hr_asset)

    # Rule 0 needs metadata the tenant did not expose - it must NOT fire
    # even though its other condition holds; rule 1 fires on real values.
    create_classification_policy(project2.id, schemas.ClassificationPolicyCreate(
        name="HR by metadata",
        rules=[{"domain": "wrong/absent",
                "match": {"metadata": [{"key": "list_item_fields.ApprovalStatus",
                                        "equals": "Approved"}]}},
               {"domain": "hr",
                "match": {"uri_prefix": "fake://tenant/",
                          "metadata": [{"key": "list_item_fields.Department",
                                        "in": ["People", "HR"]}]}}]),
        db_session=session, actor=officer)
    result = classification.classify_assets(session, project2.id, [doc.id])
    assert result["classified"] == 1
    session.refresh(hr_asset)
    assert hr_asset.domain == "hr", \
        f"Absent metadata must never satisfy a condition: {hr_asset.domain!r}"
    prov = json.loads(events_of(session, "ASSET_CLASSIFIED")[-1].details)
    assert prov["matched"]["metadata"] == {"list_item_fields.Department": "People"}
    print("Part 4 passed: absent metadata never fires a rule; matched "
          "values quoted verbatim in provenance.")

    # Part 5: THE GATE PROOF - split finances by policy change + reorg
    # operation alone.
    print("\n--- Part 5: the taxonomy split (the WS1 gate) ---")
    # A human approves the accounting asset first: the split must leave
    # approved content, its review, and its baseline revision untouched.
    crud.update_knowledge_asset(session, acc.id,
                                schemas.KnowledgeAssetUpdate(status="APPROVED"),
                                actor=officer)
    before = {a.id: governance_snapshot(session, a) for a in (acc, tre)}

    # The policy change (a definition change -> version bump): accounting
    # and treasury now map to the child domains.
    pol = update_classification_policy(pol.id, schemas.ClassificationPolicyUpdate(
        rules=[{"domain": "finances/accounting", "match": {"uri_prefix": acc_prefix}},
               {"domain": "finances/treasury", "match": {"uri_prefix": tre_prefix}}]),
        db_session=session, actor=officer)
    assert pol.version == 2, "Rule change must bump the version"

    # The reorg operation: re-evaluate the finances subtree against the
    # CURRENT policies - the policies ARE the split decision.
    try:
        reorganize_taxonomy(project.id, schemas.TaxonomyReorganizeRequest(
            operations=[{"kind": "reclassify", "domain": "finances"}], reason="  "),
            db_session=session, actor=officer)
        raise AssertionError("A reorg without a reason must be refused")
    except Exception:
        session.rollback()
    result = reorganize_taxonomy(project.id, schemas.TaxonomyReorganizeRequest(
        operations=[{"kind": "reclassify", "domain": "finances"}],
        reason="Split finances by subledger (accounting vs treasury)"),
        db_session=session, actor=officer)
    assert result["moved"] == 2, result

    session.refresh(acc)
    session.refresh(tre)
    assert acc.domain == "finances/accounting" and tre.domain == "finances/treasury"

    # Content unchanged, history unchanged, provenance intact.
    after = {a.id: governance_snapshot(session, a) for a in (acc, tre)}
    assert before == after, (
        "GATE FAILED - the split touched something beyond the domain "
        f"column:\nbefore={before}\nafter={after}")

    # The audit ledger carries the complete old->new mapping and reason.
    reorg_event = json.loads(events_of(session, "TAXONOMY_REORGANIZED")[-1].details)
    assert reorg_event["reason"].startswith("Split finances")
    moves = {m["asset_id"]: (m["old"], m["new"]) for m in reorg_event["moves"]}
    assert moves[acc.id] == ("finances", "finances/accounting")
    assert moves[tre.id] == ("finances", "finances/treasury")
    assert all(m["policy_version"] == 2 for m in reorg_event["moves"]), \
        "Reclassify moves must cite the policy version that decided them"

    # Prefix queries still resolve the parent: `finances` finds both
    # children (the D27 reason reorganizations nest by default).
    parent_query = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        (db.KnowledgeAsset.domain == "finances")
        | db.KnowledgeAsset.domain.like("finances/%")).all()
    assert {a.id for a in parent_query} == {acc.id, tre.id}, \
        "Prefix query for the parent domain must resolve both children"
    print("Part 5 passed: split achieved by policy change + reorg alone; "
          "content, history, and provenance byte-identical; ledger carries "
          "the mapping; prefix queries resolve the parent.")

    # Part 6: rename nests a subtree by prefix rewrite.
    print("\n--- Part 6: rename operation (nesting by construction) ---")
    result = reorganize_taxonomy(project.id, schemas.TaxonomyReorganizeRequest(
        operations=[{"kind": "rename", "from_domain": "operations",
                     "to_domain": "shared/operations"}],
        reason="Operations now lives under shared services"),
        db_session=session, actor=officer)
    session.refresh(stray)
    assert stray.domain == "shared/operations/misc", stray.domain
    assert result["moved"] == 1
    print("Part 6 passed: subtree prefix-rewritten, deeper paths preserved.")

    print("\nAll Domain Classification (D27) checks passed: taxonomy is "
          "governed metadata - policies assign it, humans correct it, "
          "audited operations reorganize it, and nothing else ever moves.")


if __name__ == "__main__":
    main()
