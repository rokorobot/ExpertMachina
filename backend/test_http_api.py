import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"  # deterministic rule-based extraction
os.environ.pop("OPENAI_MODEL", None)  # settings part asserts the DEFAULT tier

# HTTP smoke layer (audit M0.2): the function-level suites exercise crud and
# the engines directly, so a broken ROUTE (ordering, params, serialization)
# passes them all - the unreachable /api/assets/bulk shipped that way from
# v0.2 to v0.11. This suite drives the real FastAPI app over HTTP semantics.

# Isolate persistence BEFORE importing the app: swap the module-level engine
# and session factory for a throwaway file DB (main.get_db and background
# code resolve db.SessionLocal at call time, so reassignment is enough).
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

_tmpdir = tempfile.mkdtemp(prefix="em_http_smoke_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'smoke.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_http_smoke_qdrant_")

from fastapi.testclient import TestClient
from app import main

DOC_TEXT = (
    "The platform runs on a PostgreSQL database server cluster.\n"
    "All operators must complete safety training before access is granted.\n"
    "The reporting platform archives records in a SQLite database server.\n"
)


def main_test():
    print("\nStarting HTTP smoke checks against the real FastAPI app...")
    with TestClient(main.app) as client:

        # Part 1: health + project lifecycle over HTTP.
        print("\n--- Part 1: Health and project creation ---")
        r = client.get("/api/health")
        assert r.status_code == 200 and r.json()["status"] == "healthy", r.text
        r = client.post("/api/projects", json={"name": "HTTP Smoke", "description": "smoke", "customer_id": 1})
        assert r.status_code == 200, r.text
        project_id = r.json()["id"]
        print("Part 1 passed: health OK, project created over HTTP.")

        # Part 2: upload with a hostile filename - sanitized, not traversed.
        print("\n--- Part 2: Upload filename sanitization ---")
        r = client.post(f"/api/projects/{project_id}/documents",
                        files={"file": ("..\\..\\evil_smoke.txt", DOC_TEXT.encode(), "text/plain")})
        assert r.status_code == 200, r.text
        assert r.json()["filename"] == "evil_smoke.txt", \
            f"Path components must be stripped: {r.json()['filename']}"
        backend_root = os.path.dirname(os.path.abspath(__file__))
        assert not os.path.exists(os.path.join(backend_root, "..", "evil_smoke.txt")), \
            "File must never land outside the uploads dir"
        r = client.post(f"/api/projects/{project_id}/documents",
                        files={"file": ("..", b"x", "text/plain")})
        assert r.status_code == 400, f"Pure-dot filename must be rejected: {r.status_code}"
        print("Part 2 passed: traversal name sanitized to basename; '..' rejected with 400.")

        # Part 3: extraction produced CANDIDATE assets, listable over HTTP.
        print("\n--- Part 3: Assets listed, all CANDIDATE ---")
        r = client.get(f"/api/projects/{project_id}/assets")
        assert r.status_code == 200, r.text
        assets = r.json()
        assert len(assets) >= 2, f"Expected at least 2 extracted assets, got {len(assets)}"
        assert all(a["status"] == "CANDIDATE" for a in assets)
        print(f"Part 3 passed: {len(assets)} CANDIDATE assets over HTTP.")

        # Part 4: single approve - baseline revision visible in the response.
        print("\n--- Part 4: Single approval creates revision 1 ---")
        first_id = assets[0]["id"]
        r = client.patch(f"/api/assets/{first_id}", json={"status": "APPROVED"},
                         params={"actor": "SmokeTester"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "APPROVED" and body["active_revision_number"] == 1, body
        print("Part 4 passed: APPROVED with active revision 1.")

        # Part 5: BULK approve - the route that was unreachable from v0.2 to
        # v0.11 (shadowed by /api/assets/{asset_id}), and whose old inline
        # logic skipped baseline revisions. Both regressions guarded here.
        print("\n--- Part 5: Bulk approval reachable + revision parity ---")
        rest = [a["id"] for a in assets[1:]]
        r = client.patch("/api/assets/bulk",
                         json={"asset_ids": rest, "status": "APPROVED"},
                         params={"actor": "SmokeTester"})
        assert r.status_code == 200, f"Bulk route must be reachable, got {r.status_code}: {r.text[:200]}"
        bulk_body = r.json()
        assert len(bulk_body) == len(rest)
        assert all(a["status"] == "APPROVED" for a in bulk_body)
        assert all(a["active_revision_number"] == 1 for a in bulk_body), \
            "Bulk approvals must create baseline revisions exactly like single approvals (no second species)"
        print(f"Part 5 passed: {len(bulk_body)} assets bulk-approved with baseline revisions.")

        # Part 6: audit trail records both approval paths identically shaped.
        print("\n--- Part 6: Audit events over HTTP ---")
        r = client.get("/api/audit", params={"limit": 200})
        assert r.status_code == 200, r.text
        events = r.json()
        approvals = [e for e in events if e["event_type"] == "ASSET_APPROVED"]
        assert len(approvals) == len(assets), f"One ASSET_APPROVED per asset: {len(approvals)}"
        assert any("via bulk update" in (e["details"] or "") for e in approvals), \
            "Bulk approvals keep their distinguishing audit detail"
        print(f"Part 6 passed: {len(approvals)} ASSET_APPROVED events, bulk detail preserved.")

        # Part 7: LLM Provider Settings (MVP 0.12) over HTTP - third layer
        # from birth: list, set (CONFIG wins), clear (falls back), reject
        # unknown functions.
        print("\n--- Part 7: LLM settings endpoints ---")
        r = client.get("/api/settings/llm")
        assert r.status_code == 200, r.text
        settings = {s["function"]: s for s in r.json()}
        assert set(settings) == {"EXTRACTION", "CLAIM_DECOMPOSITION", "CLAIM_JUDGE", "ANSWER_GENERATION"}
        assert all(s["source"] == "DEFAULT" and s["effective_model"] == "gpt-4o-mini" for s in settings.values())
        r = client.put("/api/settings/llm/extraction", json={"model": "gpt-4o", "actor": "SmokeTester"})
        assert r.status_code == 200 and r.json()["source"] == "CONFIG" and r.json()["effective_model"] == "gpt-4o", r.text
        r = client.put("/api/settings/llm/EXTRACTION", json={"model": None, "actor": "SmokeTester"})
        assert r.status_code == 200 and r.json()["source"] == "DEFAULT", r.text
        r = client.put("/api/settings/llm/NOT_A_FUNCTION", json={"model": "x"})
        assert r.status_code == 400, f"Unknown function must 400: {r.status_code}"
        r = client.get("/api/audit", params={"limit": 50})
        assert any(e["event_type"] == "LLM_CONFIG_UPDATED" for e in r.json()), \
            "Config changes must be audited"
        print("Part 7 passed: settings listed, set/clear round-trip, unknown rejected, audited.")

    print("\nAll HTTP smoke checks passed.")


if __name__ == "__main__":
    main_test()
