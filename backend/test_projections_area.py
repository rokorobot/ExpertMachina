import json
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ["EM_PROJECTION_DIR"] = tempfile.mkdtemp(prefix="em_area_renders_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

# v1.5 WS3 gate suite - the top-level Projections area (D28/D31/D8,
# docs/em-vault-v1.5.md). Renderer plurality (graph + vault) earned the
# area; this suite proves its backend surface: the renderer registry is
# metadata-only backend truth, the render route accepts the vault at
# assets:approve, the history is projected from PROJECTION_RENDERED
# events alone, and the v1.3 staleness lifecycle holds on the vault
# renderer (fresh -> drift -> LOW inbox item -> regeneration clears,
# no dismiss; "regenerated", never "synced").

_tmpdir = tempfile.mkdtemp(prefix="em_area_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'area.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_area_qdrant_")

from app import schemas  # noqa: E402
from app import crud  # noqa: E402
from app import identity  # noqa: E402
from app import governance_inbox  # noqa: E402
from app.projections import engine as projection_engine  # noqa: E402
import test_support  # noqa: E402


def make_vault():
    base = tempfile.mkdtemp(prefix="em_area_vault_")
    for folder in ("00_system", "07_agent_workspaces", "08_proposals"):
        os.makedirs(os.path.join(base, folder))
    return base


def approved_asset(session, project_id, name, content, domain=None):
    asset = db.KnowledgeAsset(project_id=project_id, name=name, type="POLICY",
                              content=content, status="APPROVED",
                              access_level="INTERNAL", domain=domain)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def main():
    db.init_db()
    session = db.SessionLocal()
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Area", description="WS3 gate", customer_id=customer.id),
        actor=officer)
    approved_asset(session, project.id, "Badge Policy",
                   "Badges are returned at the front desk on the last day.",
                   domain="operations")
    vault = make_vault()
    os.environ["EM_VAULT_DIR"] = vault

    from fastapi.testclient import TestClient
    from app import main as app_main
    try:
        with TestClient(app_main.app) as client:
            with db.SessionLocal() as boot:
                for name, role in [("area-admin", "ADMIN"),
                                   ("area-reader", "READ_ONLY")]:
                    p = identity.create_principal(
                        boot, name=name, display_name=name, kind="HUMAN",
                        role=role, created_by="test-suite")
                    identity.set_password(boot, p, f"{name}-pass-1",
                                          actor="test-suite")
            def login(name):
                r = client.post("/api/auth/login",
                                json={"name": name, "password": f"{name}-pass-1"})
                return {"Authorization": f"Bearer {r.json()['token']}"}
            ADMIN = login("area-admin")
            READER = login("area-reader")

            # -------------------------------------------------- Part 1
            # The renderer registry: metadata-only backend truth.
            print("\n--- Part 1: the renderer registry endpoint ---")
            r = client.get("/api/projections/renderers", headers=READER)
            assert r.status_code == 200, r.text
            renderers = {entry["name"]: entry for entry in r.json()}
            assert set(renderers) == {"projection", "graph", "vault"}
            assert renderers["graph"]["content_mode"] == "METADATA_EXCERPT"
            assert renderers["vault"]["content_mode"] == "FULL_CONTENT"
            assert renderers["vault"]["output"] == "VAULT"
            assert renderers["vault"]["managed_folders"] == [
                "01_overview", "02_knowledge", "03_domains",
                "04_indexes", "05_conflicts", "06_audit"]
            for entry in renderers.values():
                json.dumps(entry)  # metadata only - no callables can leak
            print(f"Part 1 passed: 3 renderers declared, modes and managed "
                  f"folders as ratified, metadata only.")

            # -------------------------------------------------- Part 2
            # The render route: the vault renders at assets:approve;
            # readers read history; readers cannot render.
            print("\n--- Part 2: the governed render route (vault) ---")
            r = client.post(f"/api/projects/{project.id}/projections/render",
                            json={"renderer": "vault", "clearance": "INTERNAL"},
                            headers=READER)
            assert r.status_code == 403, "rendering is assets:approve"
            r = client.post(f"/api/projects/{project.id}/projections/render",
                            json={"renderer": "vault", "clearance": "INTERNAL"},
                            headers=ADMIN)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["content_mode"] == "FULL_CONTENT"
            assert body["output"].startswith("vault:")
            assert "content" not in json.dumps(body.get("files", {})), \
                "route responses stay metadata-only"
            assert os.path.isfile(os.path.join(
                vault, "06_audit", "manifest.json"))
            r = client.get(f"/api/projects/{project.id}/projections",
                           headers=READER)
            assert r.status_code == 200
            history = r.json()
            assert history and history[0]["renderer"] == "vault"
            assert history[0]["current"] and history[0]["stale"] is False
            assert history[0]["content_mode"] == "FULL_CONTENT"
            print("Part 2 passed: reader refused to render, admin rendered "
                  "the vault, history projected from the ledger with the "
                  "declared content mode.")
    finally:
        pass

    # ------------------------------------------------------ Part 3
    # The staleness lifecycle on the vault renderer (the v1.3 discipline
    # re-verified on the second renderer): fresh -> drift -> LOW inbox
    # item -> regeneration clears, no dismiss.
    print("\n--- Part 3: the staleness lifecycle on the vault ---")
    history = projection_engine.render_history(session, project.id)
    latest = next(h for h in history if h["current"])
    assert latest["stale"] is False, "fresh render must be current"

    approved_asset(session, project.id, "Visitor Policy",
                   "Visitors sign in at reception and wear a badge.",
                   domain="operations")
    history = projection_engine.render_history(session, project.id)
    latest = next(h for h in history if h["current"])
    assert latest["stale"] is True, "an approved fact drifted the render"
    stale_items = [i for i in governance_inbox.build_inbox(
        session, project.id)["items"] if i["type"] == "PROJECTION_STALE"]
    assert stale_items and stale_items[0]["severity"] == "LOW"
    assert stale_items[0]["renderer"] == "vault"
    assert "regenerate" in stale_items[0]["reason"].lower()
    assert "sync" not in stale_items[0]["reason"].lower(), \
        'language ruling: "regenerated", never "synced"'

    projection_engine.render(session, officer, project.id, renderer="vault")
    history = projection_engine.render_history(session, project.id)
    current = [h for h in history if h["renderer"] == "vault" and h["current"]]
    superseded = [h for h in history
                  if h["renderer"] == "vault" and not h["current"]]
    assert len(current) == 1 and current[0]["stale"] is False
    assert superseded, "the older render is superseded, never rewritten"
    assert not [i for i in governance_inbox.build_inbox(
        session, project.id)["items"] if i["type"] == "PROJECTION_STALE"], \
        "regeneration alone clears the item - no dismiss exists"
    # The regenerated vault carries the new fact - full content, live.
    with open(os.path.join(vault, "06_audit", "source_inventory.md"),
              encoding="utf-8") as f:
        assert "Visitor Policy" in f.read()
    print("Part 3 passed: fresh -> stale (LOW, no dismiss) -> regenerated "
          "clears; the older render superseded; the new fact in the vault.")

    os.environ.pop("EM_VAULT_DIR", None)
    session.close()
    print("\nAll v1.5 WS3 Projections-area checks passed: the registry is "
          "metadata-only backend truth, the vault renders through the "
          "governed route, and the staleness lifecycle holds on the second "
          "renderer - regenerated, never synced.")


if __name__ == "__main__":
    main()
