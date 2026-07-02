"""v1.2.0 WS2 acceptance suite (docs/credentials-cloud-connector-v1.2.md):
SharePointProvider on the UNCHANGED D18 framework, driven in CI by a fake
Graph transport - the fake:// pattern that ratified D18, applied to
Microsoft Graph. No live tenant, no real secret, ever (the contract's
hard boundary): the one manual live-tenant scan is recorded separately as
gate evidence.

The gate: a SharePoint library scans end-to-end into ordinary Documents
and CANDIDATE assets; hash-only change verdicts (a changed Graph
timestamp with unchanged bytes is a DUPLICATE); the client secret enters
only through custody release-for-scan; auth failure, throttling,
pagination, metadata, and fetch paths covered - every failure declared,
never silent; the provider is policy-free and structurally pure.
"""
import os
import sys
import json
import tempfile
import urllib.parse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_SECRET_KEY"] = "sharepoint-suite-master-key"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_sp_qdrant_")

from app import custody
from app import identity
from app.connectors import framework
from app.connectors.providers import sharepoint
from app.connectors.exceptions import ConnectorError, SourceValidationError
from app.connectors.models import ConnectorItem
import test_support

FAKE_SECRET = "SENTINEL-GRAPH-CLIENT-SECRET-77c4b1ea-MUST-NEVER-SURFACE"
TENANT, CLIENT = "tenant-000", "client-000"
SITE_URL = "https://contoso.sharepoint.com/sites/QMS"

DOC_TEXT = ("All operators must complete safety training before access is "
            "granted.\nRetention period for audit records is seven years.\n")


class FakeGraph:
    """A small in-memory tenant: one site, two document libraries, nested
    folders, pagination, and switchable failure modes (bad auth, throttle,
    permission denial). Speaks exactly the transport protocol the provider
    expects: request(method, url, headers, data) -> (status, headers, body)."""

    def __init__(self):
        self.token_calls = 0
        self.throttle_remaining = 0
        self.deny_scope = False
        self.valid_secret = FAKE_SECRET
        self.issued_token = "fake-graph-token-1"
        self.site_id = "site-abc"
        self.drives = {"drive-1": "Documents", "drive-2": "Policies"}
        # drive-1: two files + one folder (nested file) + one filtered .exe,
        # root children split across TWO pages (pagination proof).
        self.items = {
            "item-1": dict(drive="drive-1", parent=None, name="safety-policy.txt",
                           content=DOC_TEXT.encode(), modified="2026-07-01T10:00:00Z",
                           modified_by="Quality Manager"),
            "item-2": dict(drive="drive-1", parent=None, name="readme.md",
                           content=b"# QMS\nGoverned documents live here.\n",
                           modified="2026-06-20T08:30:00Z", modified_by="Site Owner"),
            "item-3": dict(drive="drive-1", parent=None, name="tool.exe",
                           content=b"MZ...", modified="2026-05-01T00:00:00Z",
                           modified_by="IT"),
            "item-4": dict(drive="drive-1", parent="fold-1", name="retention.txt",
                           content=b"Audit records are retained for seven years.\n",
                           modified="2026-07-02T09:00:00Z", modified_by="Records Officer"),
            "item-5": dict(drive="drive-2", parent=None, name="approved-sop.txt",
                           content=b"Escalations must be logged within 24 hours.\n",
                           modified="2026-07-01T12:00:00Z", modified_by="QMS Approver"),
        }
        self.folders = {"fold-1": dict(drive="drive-1", parent=None, name="Ops")}

    # ------------------------------------------------------------ model

    def touch_all(self):
        """Bump every Graph timestamp WITHOUT changing content - the
        classic enterprise-connector trap (D18 Test C)."""
        for item in self.items.values():
            item["modified"] = "2026-07-03T23:59:59Z"

    def set_content(self, item_id, content: bytes):
        self.items[item_id]["content"] = content

    def _entry(self, item_id):
        it = self.items[item_id]
        return {
            "id": item_id, "name": it["name"], "size": len(it["content"]),
            "webUrl": f"{SITE_URL}/{it['name']}",
            "eTag": f"etag-{item_id}-{len(it['content'])}",
            "cTag": f"ctag-{item_id}",
            "createdDateTime": "2026-01-01T00:00:00Z",
            "lastModifiedDateTime": it["modified"],
            "lastModifiedBy": {"user": {"displayName": it["modified_by"],
                                        "email": "user@contoso.com"}},
            "createdBy": {"user": {"displayName": "Author"}},
            "parentReference": {"path": f"/drives/{it['drive']}/root:"},
            "file": {"mimeType": "text/plain"},
        }

    def _folder_entry(self, folder_id):
        f = self.folders[folder_id]
        return {"id": folder_id, "name": f["name"], "folder": {"childCount": 1},
                "parentReference": {"path": f"/drives/{f['drive']}/root:"}}

    def _children(self, drive, parent):
        entries = [self._folder_entry(fid) for fid, f in self.folders.items()
                   if f["drive"] == drive and f["parent"] == parent]
        entries += [self._entry(iid) for iid, it in self.items.items()
                    if it["drive"] == drive and it["parent"] == parent]
        return entries

    # -------------------------------------------------------- transport

    def request(self, method, url, headers=None, data=None):
        def ok(payload):
            return 200, {}, json.dumps(payload).encode()

        if "login.microsoftonline.com" in url:
            self.token_calls += 1
            form = dict(urllib.parse.parse_qsl((data or b"").decode()))
            if form.get("client_id") != CLIENT or form.get("client_secret") != self.valid_secret:
                return 401, {}, json.dumps({
                    "error": "invalid_client",
                    "error_description": "AADSTS7000215: Invalid client secret provided."}).encode()
            return ok({"access_token": self.issued_token, "expires_in": 3599})

        if (headers or {}).get("Authorization") != f"Bearer {self.issued_token}":
            return 401, {}, json.dumps({"error": {"message": "InvalidAuthenticationToken"}}).encode()
        if self.throttle_remaining > 0:
            self.throttle_remaining -= 1
            return 429, {"Retry-After": "0"}, b""
        if self.deny_scope:
            return 403, {}, json.dumps({"error": {
                "message": "Access denied: the app has no roles on this site."}}).encode()

        if url.endswith(":/sites/QMS") or ":/sites/QMS" in url:
            return ok({"id": self.site_id, "displayName": "QMS"})
        if url.endswith(f"/sites/{self.site_id}/drive"):
            return ok({"id": "drive-1", "name": "Documents"})
        if url.endswith(f"/sites/{self.site_id}/drives"):
            return ok({"value": [{"id": d, "name": n} for d, n in self.drives.items()]})
        for drive in self.drives:
            if url.endswith(f"/drives/{drive}/root/children"):
                entries = self._children(drive, None)
                # pagination: first page carries one entry + nextLink
                return ok({"value": entries[:1],
                           "@odata.nextLink":
                           f"{sharepoint.GRAPH_BASE}/drives/{drive}/root/children?page=2"})
            if url.endswith(f"/drives/{drive}/root/children?page=2"):
                return ok({"value": self._children(drive, None)[1:]})
        for fid in self.folders:
            if f"/items/{fid}/children" in url:
                return ok({"value": self._children(self.folders[fid]["drive"], fid)})
        for iid, it in self.items.items():
            if f"/items/{iid}/content" in url:
                return 200, {}, it["content"]
        return 404, {}, json.dumps({"error": {"message": f"itemNotFound: {url}"}}).encode()


def make_provider(graph, connector=None, secret=FAKE_SECRET, coordinates=None):
    class Row:  # a connector row shape; the provider needs attributes only
        root_path = SITE_URL
        include_extensions = None
        type = "SHAREPOINT"
    return sharepoint.SharePointProvider(
        connector or Row(), framework.SUPPORTED_EXTENSIONS, secret=secret,
        coordinates=coordinates if coordinates is not None
        else {"tenant_id": TENANT, "client_id": CLIENT},
        transport=graph)


def part_a_structural_purity():
    """The provider is policy-free and structurally pure: stdlib + the
    connector contract only. No database, no crud, no policy, no custody -
    it receives what the framework hands it and reports what Graph says."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "app", "connectors", "providers", "sharepoint.py")).read()
    for forbidden in ("from app import", "app.database", "app.crud",
                      "app.policy", "app.custody", "app.identity",
                      "import requests", "import httpx"):
        assert forbidden not in src, (
            f"SharePointProvider purity violated: {forbidden!r}. Providers "
            f"describe; the framework decides (D18); custody releases (D25).")
    for required in ("from app.connectors.models import",
                     "from app.connectors.exceptions import"):
        assert required in src
    print("Part A passed: provider imports stdlib + the connector contract "
          "only - policy-free, database-free, custody consumed by "
          "injection, never by import.")


def part_b_auth_and_validation():
    graph = FakeGraph()

    # Wrong secret: declared, actionable, and the secret is NOT echoed.
    bad = make_provider(graph, secret="wrong-secret-value")
    try:
        bad.validate()
        raise AssertionError("bad client secret validated")
    except SourceValidationError as e:
        assert "authentication failed" in str(e) and "invalid_client" in str(e)
        assert "wrong-secret-value" not in str(e) and FAKE_SECRET not in str(e)

    # Missing coordinates / missing secret: actionable refusals.
    try:
        make_provider(graph, coordinates={}).validate()
        raise AssertionError("validated without tenant/client coordinates")
    except SourceValidationError as e:
        assert "tenant_id" in str(e)
    try:
        make_provider(graph, secret=None).validate()
        raise AssertionError("validated without a released secret")
    except SourceValidationError as e:
        assert "custody" in str(e)

    # Good credential: resolves site + default drive; token is acquired
    # once and cached; describe() carries context, never the secret.
    graph.token_calls = 0
    provider = make_provider(graph)
    provider.validate()
    items = provider.discover()
    assert provider._site_id == "site-abc" and provider._drive_id == "drive-1"
    assert graph.token_calls == 1, "token acquired once per provider lifetime"
    described = json.dumps(provider.describe())
    assert FAKE_SECRET not in described
    assert "site-abc" in described

    # Permission denial: actionable, names the scope conversation.
    graph2 = FakeGraph()
    graph2.deny_scope = True
    try:
        make_provider(graph2).validate()
        raise AssertionError("scope denial validated")
    except SourceValidationError as e:
        assert "Sites.Selected" in str(e), "the error must point at Graph scopes"

    # Named library selection via ::LibraryName.
    class Row:
        root_path = SITE_URL + "::Policies"
        include_extensions = None
        type = "SHAREPOINT"
    lib = make_provider(FakeGraph(), connector=Row())
    lib.validate()
    assert lib._drive_id == "drive-2"
    lib_items = lib.discover()
    assert [i.name for i in lib_items] == ["approved-sop.txt"]
    print("Part B passed: auth failures declared without echoing secrets; "
          "coordinates and released-secret preconditions actionable; token "
          "cached; scope denials name the permission conversation; named "
          "libraries resolve.")
    return items


def part_c_discovery_verbatim(items):
    """Pagination followed to the end; nested folders walked; extension
    intersection filters (the .exe never appears); URIs are Graph item
    identities; metadata is Graph's description VERBATIM - no policy."""
    names = sorted(i.name for i in items)
    assert names == ["readme.md", "retention.txt", "safety-policy.txt"], names
    assert all(i.uri.startswith("sharepoint://site-abc/drive-1/") for i in items)
    by_name = {i.name: i for i in items}
    meta = by_name["safety-policy.txt"].metadata
    assert meta["web_url"].endswith("safety-policy.txt")
    assert meta["etag"] and meta["ctag"]
    assert meta["last_modified_at"] == "2026-07-01T10:00:00Z"
    assert meta["last_modified_by"] == "Quality Manager"
    assert meta["mime_type"] == "text/plain"
    assert meta["list_item_fields"] is None, (
        "fields the tenant does not expose stay absent - never fabricated (D12)")
    # Deterministic order across calls.
    graph = FakeGraph()
    p = make_provider(graph)
    assert [i.uri for i in p.discover()] == [i.uri for i in p.discover()]
    print("Part C passed: pagination + nested folders walked; unparseable "
          "types filtered by the capability intersection; metadata is "
          "verbatim Graph fact, absent fields absent.")


def part_d_end_to_end_scan(session):
    """The D18 proof, repeated for the credentialed path: a SharePoint
    library scans end-to-end through the UNCHANGED framework into ordinary
    Documents and CANDIDATE assets; the client secret enters only through
    custody release-for-scan; hash stays the only change verdict."""
    graph = FakeGraph()
    sharepoint.default_transport_factory = lambda: graph

    admin = test_support.governed_actor(session, "sp_admin", role="ADMIN")
    cred = custody.create_external_credential(
        session, name="Graph client", purpose="CONNECTOR", secret=FAKE_SECRET,
        actor=admin, granted_scopes=["Sites.Selected"],
        coordinates={"tenant_id": TENANT, "client_id": CLIENT})
    project = db.Project(name="SP", description="", customer_id=1)
    session.add(project)
    session.commit()
    connector = db.SourceConnector(
        project_id=project.id, name="qms-sharepoint", type="SHAREPOINT",
        root_path=SITE_URL, external_credential_id=cred.id)
    session.add(connector)
    session.commit()

    def scan():
        job = db.IngestionJob(project_id=project.id, connector_id=connector.id,
                              status="PENDING")
        session.add(job)
        session.commit()
        framework.execute_ingestion_job(session, job.id)
        session.refresh(job)
        return job

    job1 = scan()
    assert job1.status == "COMPLETED", job1.error
    assert job1.files_discovered == 3 and job1.files_ingested == 3, (
        job1.files_discovered, job1.files_ingested)

    # Ordinary objects: Documents with content hashes, CANDIDATE assets,
    # SourceDocument provenance rows with the Graph item URIs.
    docs = session.query(db.Document).filter_by(project_id=project.id).all()
    assert len(docs) == 3 and all(d.content_hash for d in docs)
    assets = session.query(db.KnowledgeAsset).filter_by(project_id=project.id).all()
    assert assets and all(a.status == "CANDIDATE" for a in assets), (
        "connector output becomes ordinary CANDIDATE assets - D6, unchanged")
    sources = session.query(db.SourceDocument).filter_by(ingestion_job_id=job1.id).all()
    assert all(s.source_uri.startswith("sharepoint://site-abc/") for s in sources)

    # The secret entered ONLY through custody: exactly one
    # EXTERNAL_CREDENTIAL_USED for the scan, carrying the job context.
    used = [e for e in session.query(db.AuditEvent).filter_by(
        event_type="EXTERNAL_CREDENTIAL_USED").all()
        if json.loads(e.details).get("ingestion_job_id") == job1.id]
    assert len(used) == 1
    assert json.loads(used[0].details)["granted_scopes"] == ["Sites.Selected"]

    # D18 Test C, repeated for SharePoint: every Graph timestamp changes,
    # no content changes -> ALL DUPLICATE (hash is the only verdict), and
    # the new timestamp is still recorded as context.
    graph.touch_all()
    job2 = scan()
    assert job2.status == "COMPLETED" and job2.files_duplicate == 3, (
        job2.files_duplicate, job2.error)
    dup = session.query(db.SourceDocument).filter_by(
        ingestion_job_id=job2.id, status="DUPLICATE").first()
    assert dup.source_modified_at and dup.source_modified_at.year == 2026
    assert dup.source_modified_at.month == 7 and dup.source_modified_at.day == 3, (
        "the changed timestamp is recorded as context even though the "
        "verdict is DUPLICATE")

    # Content change -> CHANGED through the existing machinery.
    graph.set_content("item-1", DOC_TEXT.encode() + b"Visitors must sign in at reception.\n")
    job3 = scan()
    assert job3.status == "COMPLETED" and job3.files_changed == 1, (
        job3.files_changed, job3.error)

    print("Part D passed: end-to-end scan into ordinary Documents and "
          "CANDIDATE assets; secret entered only via custody (one USED "
          "event per scan); timestamp-only changes are DUPLICATEs with "
          "context recorded; content changes are CHANGED.")
    return project, connector, cred


def part_e_declared_failures(session, project, connector, cred):
    """Throttling retried then declared; a bad credential fails the JOB
    loudly end-to-end; no failure path echoes secret material anywhere."""
    # Throttle once -> retry succeeds (Retry-After honored).
    graph = FakeGraph()
    graph.throttle_remaining = 1
    p = make_provider(graph)
    assert len(p.discover()) == 3, "one 429 must be retried, not fatal"

    # Persistent throttle -> declared ConnectorError.
    graph2 = FakeGraph()
    graph2.throttle_remaining = 10 ** 6
    try:
        make_provider(graph2).validate()
        raise AssertionError("persistent throttling did not fail")
    except ConnectorError as e:
        assert "throttled" in str(e)

    # Fetch failure for one item is a FetchError (the framework records it
    # and continues - seam behavior, unchanged).
    graph3 = FakeGraph()
    p3 = make_provider(graph3)
    p3.validate()
    ghost = ConnectorItem(uri="sharepoint://site-abc/drive-1/item-404", name="ghost.txt")
    try:
        p3.fetch(ghost)
        raise AssertionError("fetching a missing item did not fail")
    except Exception as e:
        assert "404" in str(e)

    # End-to-end: rotate the credential to a WRONG secret -> the next scan
    # FAILS loudly with the declared Graph auth error; nothing silent.
    admin = test_support.governed_actor(session, "sp_admin", role="ADMIN")
    custody.rotate_external_credential(session, cred, new_secret="rotated-but-wrong",
                                       actor=admin)
    graph4 = FakeGraph()  # still expects FAKE_SECRET
    sharepoint.default_transport_factory = lambda: graph4
    job = db.IngestionJob(project_id=project.id, connector_id=connector.id,
                          status="PENDING")
    session.add(job)
    session.commit()
    framework.execute_ingestion_job(session, job.id)
    session.refresh(job)
    assert job.status == "FAILED"
    assert "authentication failed" in job.error and "invalid_client" in job.error
    assert "rotated-but-wrong" not in job.error and FAKE_SECRET not in job.error

    # The custody sweep discipline, applied here: no secret material is
    # readable in any table or audit payload after everything above.
    with db.engine.connect() as conn:
        for table in db.Base.metadata.sorted_tables:
            for row in conn.execute(table.select()):
                for value in row:
                    for s in (FAKE_SECRET, "rotated-but-wrong", "wrong-secret-value"):
                        assert s not in str(value), (
                            f"D25 violation: secret readable in {table.name}")
    print("Part E passed: throttling retried then declared; missing items "
          "and bad credentials fail loudly end-to-end; no failure path "
          "echoes secret material; the sweep stays clean.")


def main_test():
    tmp = tempfile.mkdtemp(prefix="em_sp_test_")
    db.engine = create_engine(f"sqlite:///{os.path.join(tmp, 'sp.db')}",
                              connect_args={"check_same_thread": False})
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)
    db.Base.metadata.create_all(db.engine)
    session = db.SessionLocal()

    part_a_structural_purity()
    items = part_b_auth_and_validation()
    part_c_discovery_verbatim(items)
    project, connector, cred = part_d_end_to_end_scan(session)
    part_e_declared_failures(session, project, connector, cred)
    session.close()

    print("\nWS2 SharePoint suite passed: the four-method contract over a "
          "fake Graph tenant - credentialed through custody, policy-free, "
          "hash-verdict-only, every failure declared. The framework was "
          "not modified; it just met its second provider.")


if __name__ == "__main__":
    main_test()
