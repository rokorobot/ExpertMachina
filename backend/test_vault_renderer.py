import json
import os
import re
import shutil
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ["EM_SECRET_KEY"] = "vault-ws1-master-key-material-1"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

# v1.5 WS1 gate suite - the vault knowledge-tree renderer (D31,
# docs/em-vault-v1.5.md; the user-ratified WS1 shape and guard list).
#
# The WS1 claim: render approved governed knowledge into a
# deterministic Markdown vault tree with domain-first organization,
# full governed content where clearance permits, YAML frontmatter,
# wikilinks, DERIVED marking, and manifest-backed regeneration -
# readable and useful, yes; authoritative, no.

_tmpdir = tempfile.mkdtemp(prefix="em_vaultws1_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'vault.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_vaultws1_qdrant_")

from app import schemas  # noqa: E402
from app import crud  # noqa: E402
from app import connectors  # noqa: E402
from app import custody  # noqa: E402
from app import policy  # noqa: E402
from app import tier2  # noqa: E402
from app.projections import engine as projection_engine  # noqa: E402
from app.projections.renderers import vault as vault_renderer  # noqa: E402
import test_support  # noqa: E402

SENTINEL = "SENTINEL-vault-ws1-secret-7ac2e9"
EXEC_MARKER = "TOPSECRET-VAULT-WS1"
LONG_CONTENT = ("Refunds are honored within thirty days of purchase when the "
                "item is undamaged and accompanied by proof of purchase. "
                "Store credit applies after thirty days. Exceptions for "
                "perishable goods require a duty manager's sign-off, and "
                "every exception is recorded in the register log with the "
                "manager's identifier and the original receipt number so the "
                "finance team can reconcile exceptions at month end.")
assert len(LONG_CONTENT) > projection_engine.EXCERPT_LIMIT

UNTOUCHABLE_PLANTS = {
    "00_system/agent-contract.md": "# The Vault Contract (planted)\n",
    "07_agent_workspaces/scratch.txt": "agent scratch - work in progress\n",
    "08_proposals/pending-proposal.md": "---\nem_proposal: 1\n---\nA pending finding.\n",
}


def write_file(base, rel, text):
    path = os.path.join(base, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def make_vault():
    base = tempfile.mkdtemp(prefix="em_vaultws1_vault_")
    for rel, text in UNTOUCHABLE_PLANTS.items():
        write_file(base, rel, text)
    return base


def read_tree(base):
    found = {}
    for root, _dirs, files in os.walk(base):
        for name in files:
            path = os.path.join(root, name)
            with open(path, "rb") as f:
                found[os.path.relpath(path, base).replace(os.sep, "/")] = f.read()
    return found


def managed_files(tree):
    return {rel: data for rel, data in tree.items()
            if rel.split("/")[0] in vault_renderer.MANAGED_FOLDERS}


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
    identity = {"method": "GUARD_APPROVE_EVERYTHING", "note": "ws1 seam"}

    def check(self, candidate, corpus):
        return {"pairs_checked": len(corpus), "pairs_dropped": 0,
                "contradictions": []}


def seed(session, officer):
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Vault WS1", description="knowledge tree gate",
        customer_id=customer.id), actor=officer)

    def document(filename):
        doc = db.Document(project_id=project.id, filename=filename,
                          file_path=os.path.join(_tmpdir, filename),
                          status="APPROVED")
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc

    def asset(name, content, domain, source_class="PRIMARY",
              access_level="INTERNAL", doc=None, asset_type="POLICY"):
        row = db.KnowledgeAsset(
            project_id=project.id, name=name, type=asset_type,
            content=content, status="APPROVED", access_level=access_level,
            domain=domain, source_class=source_class,
            source_hash="sh_" + name.replace(" ", "_").lower(),
            document_id=doc.id if doc else None)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    doc1 = document("refund-handbook.pdf")
    refund = asset("Customer Refund Policy", LONG_CONTENT,
                   "customer_operations", doc=doc1)
    finding = asset("Refund Finding",
                    "Refunds must be denied after fourteen days in every case.",
                    "customer_operations", source_class="DERIVED")
    ledger = asset("Ledger Retention Rule",
                   "Ledgers are retained for ten years in the finance archive.",
                   "finance/accounting")
    stray = asset("Visitor Badge Note",
                  "Visitor badges are returned at the front desk.", None)
    secret = asset("Executive Compensation Bands",
                   f"The {EXEC_MARKER} compensation bands are reviewed yearly.",
                   "finance/accounting", access_level="EXECUTIVE")
    session.add(db.AssetRelationship(
        project_id=project.id, expert_model_id=None,
        source_asset_id=refund.id, target_asset_id=finding.id,
        relationship_type="CONFLICTS_WITH",
        classification="DIRECT_CONTRADICTION", confidence=0.99,
        status="DETECTED"))
    session.commit()
    return project, {"refund": refund, "finding": finding, "ledger": ledger,
                     "stray": stray, "secret": secret}


def main():
    db.init_db()
    tier2.verifier_factory = ApproveEverythingVerifier
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    custody.create_external_credential(
        session, name="ws1-sentinel", purpose="CONNECTOR",
        secret=SENTINEL, actor=officer)
    project, assets = seed(session, officer)
    vault = make_vault()
    os.environ["EM_VAULT_DIR"] = vault

    # ------------------------------------------------------------ Part 1
    # Exact inventory: the expected tree, nothing more, floor intact.
    print("\n--- Part 1: exact inventory ---")
    result = projection_engine.render(session, officer, project.id,
                                      renderer="vault")
    assert result["content_mode"] == "FULL_CONTENT"
    tree = read_tree(vault)
    note = {key: f"asset_{a.id}_{vault_renderer._slug(a.name)}"
            for key, a in assets.items()}
    expected = {
        "01_overview/index.md", "01_overview/clearance_scope.md",
        "01_overview/render_manifest.md",
        f"02_knowledge/customer_operations/{note['refund']}.md",
        f"02_knowledge/customer_operations/{note['finding']}.md",
        f"02_knowledge/finance/accounting/{note['ledger']}.md",
        f"02_knowledge/_unclassified/{note['stray']}.md",
        "03_domains/domain_customer_operations.md",
        "03_domains/domain_finance_accounting.md",
        "03_domains/domain_unclassified.md",
        "04_indexes/assets.md", "04_indexes/domains.md",
        "04_indexes/conflicts.md", "04_indexes/packages.md",
        f"05_conflicts/conflict_{assets['refund'].id}_{assets['finding'].id}.md",
        "05_conflicts/index.md",
        "06_audit/render_event.md", "06_audit/source_inventory.md",
        "06_audit/projection.json", "06_audit/manifest.json",
    }
    assert set(managed_files(tree)) == expected, (
        f"extra: {sorted(set(managed_files(tree)) - expected)}\n"
        f"missing: {sorted(expected - set(managed_files(tree)))}")
    for rel, text in UNTOUCHABLE_PLANTS.items():
        assert tree[rel] == text.encode("utf-8"), f"floor altered: {rel}"
    print(f"Part 1 passed: exactly {len(expected)} managed files; the "
          f"EXECUTIVE asset has no note; the floor plants intact.")

    # ------------------------------------------------------------ Part 2
    # Clearance on note bytes: the sentinel absent everywhere; the
    # exclusion declared in bytes.
    print("\n--- Part 2: clearance on note bytes ---")
    everything = b"".join(managed_files(tree).values())
    assert EXEC_MARKER.encode() not in everything, \
        "content above clearance reached the vault"
    assert note["secret"].encode() not in everything, \
        "even the excluded asset's note stem must not leak"
    scope = tree["01_overview/clearance_scope.md"].decode("utf-8")
    assert "assets_above_clearance: 1" in scope, \
        "the exclusion must be declared in vault bytes (D12)"
    print("Part 2 passed: zero EXECUTIVE bytes; the exclusion declared "
          "inside 01_overview/clearance_scope.md.")

    # ------------------------------------------------------------ Part 3
    # DERIVED marking, frontmatter, full content, resolvable wikilinks.
    print("\n--- Part 3: marking, frontmatter, content, wikilinks ---")
    markdown = {rel: data.decode("utf-8")
                for rel, data in managed_files(tree).items()
                if rel.endswith(".md")}
    for rel, text in markdown.items():
        assert text.startswith("---\n"), f"{rel}: missing frontmatter"
        for marker in ("em_rendered: true", "derived: true",
                       "canonical: false"):
            assert marker in text, f"{rel}: missing '{marker}'"
        assert "This note is not canonical." in text, \
            f"{rel}: the not-canonical line must be visible, not YAML-only"
    refund_note = markdown[
        f"02_knowledge/customer_operations/{note['refund']}.md"]
    assert LONG_CONTENT in refund_note, "full governed content, verbatim"
    assert f'asset_id: {assets["refund"].id}' in refund_note
    assert 'source_class: "PRIMARY"' in refund_note
    assert 'source_hash: "sh_customer_refund_policy"' in refund_note
    assert "refund-handbook.pdf" in refund_note, "document provenance"
    finding_note = markdown[
        f"02_knowledge/customer_operations/{note['finding']}.md"]
    assert 'source_class: "DERIVED"' in finding_note
    assert "**DERIVED**" in finding_note and "Primary prevails" in finding_note
    conflict_note = markdown[
        f"05_conflicts/conflict_{assets['refund'].id}_{assets['finding'].id}.md"]
    assert "primary prevails" in conflict_note.lower()
    assert f"[[{note['refund']}]]" in conflict_note

    stems = {rel.rsplit("/", 1)[-1][:-3] for rel in markdown}
    for rel, text in markdown.items():
        for target in re.findall(r"\[\[([^\]]+)\]\]", text):
            assert target in stems, f"{rel}: dangling wikilink [[{target}]]"
    print(f"Part 3 passed: {len(markdown)} notes marked and frontmattered; "
          f"full content verbatim; every wikilink resolves.")

    # ------------------------------------------------------------ Part 4
    # Determinism: byte-identical re-render (the volatile stamps live in
    # manifest.json only, by ratified design).
    print("\n--- Part 4: determinism ---")
    projection_engine.render(session, officer, project.id, renderer="vault")
    second = read_tree(vault)
    first_managed = managed_files(tree)
    second_managed = managed_files(second)
    assert set(first_managed) == set(second_managed)
    for rel in sorted(first_managed):
        if rel == "06_audit/manifest.json":
            continue  # the ONE volatile file: rendered_at + cursor live here
        assert first_managed[rel] == second_managed[rel], \
            f"non-deterministic bytes: {rel}"
    m1 = json.loads(first_managed["06_audit/manifest.json"])
    m2 = json.loads(second_managed["06_audit/manifest.json"])
    assert m1["files"] == m2["files"], \
        "the manifest's file-hash map is the deterministic core"
    assert m1["content_mode"] == m2["content_mode"] == "FULL_CONTENT"
    print("Part 4 passed: every file byte-identical across renders; "
          "manifest.json volatile only in its stamps, identical in its "
          "file-hash map.")

    # ------------------------------------------------------------ Part 5
    # D27 taxonomy: governed correction moves the folder, not the
    # knowledge; moving a rendered file reclassifies nothing.
    print("\n--- Part 5: the D27 taxonomy proof ---")
    def governed_content(text):
        # The knowledge itself: between "## Governed Content" and
        # "## Source" (the Source section's domain wikilink legitimately
        # follows the taxonomy - it is metadata, not content).
        return text.split("## Governed Content", 1)[1].split("## Source", 1)[0]

    ledger = assets["ledger"]
    body_before = governed_content(markdown[
        f"02_knowledge/finance/accounting/{note['ledger']}.md"])
    crud.update_knowledge_asset(
        session, ledger.id, schemas.KnowledgeAssetUpdate(domain="finance/tax"),
        actor=officer)
    projection_engine.render(session, officer, project.id, renderer="vault")
    third = read_tree(vault)
    moved_rel = f"02_knowledge/finance/tax/{note['ledger']}.md"
    assert moved_rel in third, "the note must follow the governed taxonomy"
    assert f"02_knowledge/finance/accounting/{note['ledger']}.md" not in third
    body_after = governed_content(third[moved_rel].decode("utf-8"))
    assert body_after == body_before, \
        "the governed content is untouched by the reorganization"
    session.refresh(ledger)
    assert ledger.status == "APPROVED" and ledger.domain == "finance/tax"

    # Moving the rendered FILE changes nothing governed (D27/D31): the
    # file is a lens; the next render puts governed truth back.
    src = os.path.join(vault, moved_rel.replace("/", os.sep))
    dst = os.path.join(vault, "02_knowledge", "customer_operations",
                       f"{note['ledger']}.md")
    shutil.move(src, dst)
    session.refresh(ledger)
    assert ledger.domain == "finance/tax", \
        "moving a rendered file must never reclassify anything"
    projection_engine.render(session, officer, project.id, renderer="vault")
    fourth = read_tree(vault)
    assert moved_rel in fourth
    assert f"02_knowledge/customer_operations/{note['ledger']}.md" not in fourth
    print("Part 5 passed: governed correction moved the folder with the "
          "body byte-identical; a manual file move reclassified nothing "
          "and regeneration restored governed truth.")

    # ------------------------------------------------------------ Part 6
    # Regeneration: stale managed files destroyed; the floor untouched -
    # with the REAL renderer (WS0 proved it with a probe).
    print("\n--- Part 6: regeneration isolation (real renderer) ---")
    write_file(vault, "02_knowledge/stale.md", "old junk\n")
    write_file(vault, "03_domains/old.md", "old junk\n")
    projection_engine.render(session, officer, project.id, renderer="vault")
    fifth = read_tree(vault)
    assert "02_knowledge/stale.md" not in fifth
    assert "03_domains/old.md" not in fifth
    for rel, text in UNTOUCHABLE_PLANTS.items():
        assert fifth[rel] == text.encode("utf-8"), f"floor altered: {rel}"
    print("Part 6 passed: stale managed files destroyed; every untouchable "
          "plant byte-identical.")

    # ------------------------------------------------------------ Part 7
    # No flow-back: a REAL vault note into 08_proposals is ordinary
    # proposal evidence behind the valve (WS0's plant, with WS1's files).
    print("\n--- Part 7: no flow-back (the seam, with real notes) ---")
    note_rel = f"02_knowledge/customer_operations/{note['refund']}.md"
    note_bytes = fifth[note_rel]
    write_file(vault, "08_proposals/copied-vault-note.md",
               note_bytes.decode("utf-8"))
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add_all([
        db.ApprovalPolicy(project_id=project.id, name="ws1-tier1",
                          asset_types_json=all_types, enabled=True),
        db.ApprovalPolicy(project_id=project.id, name="ws1-tier2",
                          asset_types_json=all_types, enabled=True,
                          engine_conditions_json=json.dumps(
                              {"contradiction_check": "CLEAN_REQUIRED"})),
    ])
    lane = db.SourceConnector(project_id=project.id, name="WS1 Lane",
                              type="LOCAL_FOLDER",
                              root_path=os.path.join(vault, "08_proposals"),
                              include_extensions=".md", lane="PROPOSAL")
    session.add(lane)
    session.commit()
    session.refresh(lane)
    projection_events_before = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type.like("PROJECTION_%")).count()
    run_scan(session, lane)
    lane_doc_ids = policy.proposal_lane_document_ids(
        session, [d.id for d in session.query(db.Document).filter_by(
            project_id=project.id).all()])
    lane_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.document_id.in_(lane_doc_ids)).all()
    assert lane_assets, "the copied note must have been ingested"
    for asset in lane_assets:
        assert asset.status == "CANDIDATE" and asset.source_class == "DERIVED", \
            (asset.id, asset.status, asset.source_class)
    assert session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type.like("PROJECTION_%")).count() \
        == projection_events_before, \
        "ingesting a vault note must replay zero projection authority"
    print(f"Part 7 passed: {len(lane_assets)} candidate(s) from the copied "
          f"note - held, DERIVED, zero authority replayed.")

    # ------------------------------------------------------------ Part 8
    # The D25 custody sweep over the largest export surface yet.
    print("\n--- Part 8: custody sentinel sweep ---")
    projection_engine.render(session, officer, project.id, renderer="vault")
    final = read_tree(vault)
    swept = 0
    for rel, data in managed_files(final).items():
        assert SENTINEL.encode() not in data, f"custody leak: {rel}"
        swept += 1
    print(f"Part 8 passed: {swept} vault files, sentinel-free.")

    os.environ.pop("EM_VAULT_DIR", None)
    session.close()
    print("\nAll v1.5 WS1 vault-renderer checks passed: an exact, "
          "deterministic, clearance-honest, visibly-derived knowledge tree "
          "- readable and useful, never authoritative.")


if __name__ == "__main__":
    main()
