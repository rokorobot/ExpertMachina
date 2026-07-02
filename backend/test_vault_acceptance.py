import hashlib
import json
import os
import shutil
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ["EM_SECRET_KEY"] = "vault-acceptance-master-key-1"
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_vacc_renders_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

# THE v1.5 MILESTONE GATE (D31, docs/em-vault-v1.5.md).
#
# THE DISAPPEARANCE TEST + THE SEAM PROOF (user-ratified acceptance
# target): delete the entire rendered vault output, prove no governed
# fact is lost, regenerate byte-identical managed outputs against
# ledger hashes, keep untouchables intact throughout - and prove the
# live seam: a rendered note entering through 08_proposals becomes held
# DERIVED proposal material, and only after human acceptance becomes an
# honest DERIVED fact, never laundering projection authority. Closing
# on the final line: 28 tables / 305 columns; no schema drift;
# projections are disposable governed lenses.

_tmpdir = tempfile.mkdtemp(prefix="em_vacc_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'vacc.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_vacc_qdrant_")

from app import schemas  # noqa: E402
from app import crud  # noqa: E402
from app import connectors  # noqa: E402
from app import custody  # noqa: E402
from app import policy  # noqa: E402
from app import tier2  # noqa: E402
from app.projections import engine as projection_engine  # noqa: E402
from app.projections.renderers import vault as vault_renderer  # noqa: E402
import test_support  # noqa: E402
import test_workbench_projection  # noqa: E402

SENTINEL = "SENTINEL-v15-acceptance-secret-3fb8d1"
EXEC_MARKER = "TOPSECRET-V15-ACCEPT"
CORPUS = {
    "handbook.txt": "The onboarding platform stores training records in a PostgreSQL database server.",
    "policy.txt": "All new hires must complete safety training before badge access is granted.",
}
UNTOUCHABLE_PLANTS = {
    "00_system/agent-contract.md": "# The Vault Contract (planted)\n",
    "07_agent_workspaces/scratch.txt": "agent work in progress\n",
    "08_proposals/pending-proposal.md": "---\nem_proposal: 1\n---\nA pending finding.\n",
}


def write_file(base, rel, text):
    path = os.path.join(base, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def read_tree(base):
    found = {}
    for root, _dirs, files in os.walk(base):
        for name in files:
            path = os.path.join(root, name)
            with open(path, "rb") as f:
                found[os.path.relpath(path, base).replace(os.sep, "/")] = f.read()
    return found


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


class ApproveEverythingVerifier:
    identity = {"method": "GUARD_APPROVE_EVERYTHING", "note": "v1.5 gate seam"}

    def check(self, candidate, corpus):
        return {"pairs_checked": len(corpus), "pairs_dropped": 0,
                "contradictions": []}


def governed_fingerprint(session):
    """Every governed row, canonically: the disappearance test's 'no
    fact lost' is byte-level, not row-count-level."""
    snapshot = {}
    for table in db.Base.metadata.sorted_tables:
        order = [table.c[c.name] for c in table.primary_key.columns] \
            or list(table.columns)
        rows = session.execute(table.select().order_by(*order)).fetchall()
        snapshot[table.name] = [tuple(repr(v) for v in row) for row in rows]
    return hashlib.sha256(repr(sorted(snapshot.items()))
                          .encode("utf-8")).hexdigest()


def main():
    db.init_db()
    tier2.verifier_factory = ApproveEverythingVerifier
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    custody.create_external_credential(
        session, name="v15-sentinel", purpose="CONNECTOR",
        secret=SENTINEL, actor=officer)
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Vault Acceptance", description="v1.5 milestone gate",
        customer_id=customer.id), actor=officer)

    # --- Stage 1: corpus in through the REAL governed pipeline.
    print("\n--- Stage 1: corpus in ---")
    corpus_folder = tempfile.mkdtemp(prefix="em_vacc_corpus_")
    primary = db.SourceConnector(project_id=project.id, name="Corpus",
                                 type="LOCAL_FOLDER", root_path=corpus_folder,
                                 include_extensions=".txt")
    session.add(primary)
    session.commit()
    session.refresh(primary)
    for name, sentence in CORPUS.items():
        write_file(corpus_folder, name, sentence + "\n")
    write_file(corpus_folder, "restricted.txt",
               f"The payroll platform stores {EXEC_MARKER} bands in an "
               f"Oracle database server.\n")
    run_scan(session, primary)
    reviewer = test_support.governed_actor(session, "GateReviewer")
    for asset in session.query(db.KnowledgeAsset).filter_by(
            project_id=project.id, status="CANDIDATE").all():
        crud.update_knowledge_asset(
            session, asset.id, schemas.KnowledgeAssetUpdate(
                status="APPROVED", domain="onboarding"),
            actor=reviewer, review_notes="corpus approval")
    restricted = next(a for a in session.query(db.KnowledgeAsset).filter_by(
        project_id=project.id).all() if EXEC_MARKER in (a.content or ""))
    restricted.access_level = "EXECUTIVE"
    session.commit()
    print(f"Stage 1 passed: corpus approved by a human; one EXECUTIVE asset.")

    # --- Stage 2: the vault render - stamped, clearance-filtered.
    print("\n--- Stage 2: the vault render ---")
    vault = tempfile.mkdtemp(prefix="em_vacc_vault_")
    for rel, text in UNTOUCHABLE_PLANTS.items():
        write_file(vault, rel, text)
    os.environ["EM_VAULT_DIR"] = vault
    render = projection_engine.render(session, officer, project.id,
                                      renderer="vault")
    assert render["content_mode"] == "FULL_CONTENT"
    ledger_hashes = dict(render["files"])  # the ledger's file-hash record
    tree = read_tree(vault)
    everything = b"".join(data for rel, data in tree.items()
                          if rel.split("/")[0] in vault_renderer.MANAGED_FOLDERS)
    assert EXEC_MARKER.encode() not in everything
    print(f"Stage 2 passed: {len(ledger_hashes)} files rendered, "
          f"clearance-filtered, hashes on the ledger.")

    # --- Stage 3: THE DISAPPEARANCE TEST.
    print("\n--- Stage 3: THE DISAPPEARANCE TEST ---")
    fingerprint_before = governed_fingerprint(session)
    for folder in vault_renderer.MANAGED_FOLDERS:
        shutil.rmtree(os.path.join(vault, folder))
    survivors = read_tree(vault)
    assert set(survivors) == set(UNTOUCHABLE_PLANTS), \
        "after total deletion, only the untouchable inputs remain"
    for rel, text in UNTOUCHABLE_PLANTS.items():
        assert survivors[rel] == text.encode("utf-8")
    assert governed_fingerprint(session) == fingerprint_before, (
        "D28/D31 VIOLATION: deleting the entire rendered vault changed a "
        "governed fact - a hidden dependency on rendered artifacts exists")

    projection_engine.render(session, officer, project.id, renderer="vault")
    regenerated = read_tree(vault)
    for rel, expected_hash in ledger_hashes.items():
        disk = regenerated.get(rel)
        assert disk is not None, f"re-render missing {rel}"
        assert hashlib.sha256(disk).hexdigest() == expected_hash, (
            f"re-render of {rel} does not reproduce the ledger-recorded "
            f"hash - the vault is not a pure function of governed facts")
    for rel, text in UNTOUCHABLE_PLANTS.items():
        assert regenerated[rel] == text.encode("utf-8"), \
            "untouchables intact throughout the disappearance test"
    print(f"Stage 3 passed: total deletion lost nothing; re-render "
          f"reproduced all {len(ledger_hashes)} ledger-recorded hashes; "
          f"untouchables byte-identical throughout.")

    # --- Stage 4: THE SEAM PROOF, live.
    print("\n--- Stage 4: THE SEAM PROOF ---")
    note_rel = next(rel for rel in ledger_hashes
                    if rel.startswith("02_knowledge/") and rel.endswith(".md"))
    write_file(vault, "08_proposals/copied-vault-note.md",
               regenerated[note_rel].decode("utf-8"))
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add_all([
        db.ApprovalPolicy(project_id=project.id, name="v15-tier1",
                          asset_types_json=all_types, enabled=True),
        db.ApprovalPolicy(project_id=project.id, name="v15-tier2",
                          asset_types_json=all_types, enabled=True,
                          engine_conditions_json=json.dumps(
                              {"contradiction_check": "CLEAN_REQUIRED"})),
    ])
    lane = db.SourceConnector(project_id=project.id, name="Vault Lane",
                              type="LOCAL_FOLDER",
                              root_path=os.path.join(vault, "08_proposals"),
                              include_extensions=".md", lane="PROPOSAL")
    session.add(lane)
    session.commit()
    session.refresh(lane)
    projection_events = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type.like("PROJECTION_%")).count()
    run_scan(session, lane)
    assert session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type.like("PROJECTION_%")).count() \
        == projection_events, "ingestion replayed projection authority"

    lane_doc_ids = policy.proposal_lane_document_ids(
        session, [d.id for d in session.query(db.Document).filter_by(
            project_id=project.id).all()])
    lane_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_doc_ids)).all()
    assert lane_assets, "the copied note must have extracted candidates"
    assert all(a.status == "CANDIDATE" and a.source_class == "DERIVED"
               for a in lane_assets), \
        "held DERIVED only - under global tier-1 + approve-everything tier-2"

    # Only human acceptance turns it into a fact - an HONEST one.
    accepted = lane_assets[0]
    crud.update_knowledge_asset(
        session, accepted.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted the re-submitted content")
    session.refresh(accepted)
    assert accepted.status == "APPROVED" and accepted.source_class == "DERIVED"
    event = session.query(db.AuditEvent).filter_by(
        event_type="ASSET_APPROVED", target_id=str(accepted.id)).order_by(
        db.AuditEvent.id.desc()).first()
    prov = json.loads(event.details)["synthesis_provenance"]
    assert prov["provenance_verified"] is False, (
        "the copied render claims no governed binding - acceptance must "
        "record honestly-unverifiable provenance, never launder authority")
    fact = session.query(db.IdentityFact).filter_by(
        id=event.identity_fact_id).first()
    assert fact.principal_kind == "HUMAN"

    # The loop closes visibly: the regenerated vault shows the accepted
    # fact as a marked DERIVED note.
    projection_engine.render(session, officer, project.id, renderer="vault")
    final_tree = read_tree(vault)
    derived_note = next(
        (data for rel, data in final_tree.items()
         if rel.startswith("02_knowledge/")
         and f"asset_{accepted.id}_" in rel), None)
    assert derived_note is not None
    text = derived_note.decode("utf-8")
    assert 'source_class: "DERIVED"' in text and "**DERIVED**" in text
    assert "This note is not canonical." in text
    print(f"Stage 4 passed: the copied note held as DERIVED; a human "
          f"accepted asset {accepted.id} with honestly-unverifiable "
          f"provenance; the regenerated vault shows it visibly DERIVED "
          f"and still non-canonical. No laundering path exists.")

    # --- Stage 5: the D25 custody sweep.
    print("\n--- Stage 5: custody sentinel sweep ---")
    swept = 0
    for rel, data in final_tree.items():
        assert SENTINEL.encode() not in data, f"custody leak: {rel}"
        swept += 1
    for row_event in session.query(db.AuditEvent).all():
        assert SENTINEL not in f"{row_event.details} {row_event.target_id}"
    print(f"Stage 5 passed: {swept} vault files + the ledger, sentinel-free.")

    # --- THE CLOSING LINE.
    print("\n--- The closing line ---")
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    assert live == test_workbench_projection.FROZEN_SCHEMA
    tables = len(live)
    columns = sum(len(cols) for cols in live.values())
    assert (tables, columns) == (28, 305)
    print(f"CLOSING LINE passed: {tables} tables / {columns} columns. "
          f"No schema drift. Projections are disposable governed lenses.")
    print("\n=== v1.5 MILESTONE ACCEPTANCE passed: THE DISAPPEARANCE TEST "
          "+ THE SEAM PROOF - delete everything, lose nothing; re-submit "
          "anything, launder nothing. ===")

    os.environ.pop("EM_VAULT_DIR", None)
    session.close()


if __name__ == "__main__":
    main()
