"""SharePointProvider (v1.2.0 WS2, D25 + D18) - the first credentialed
provider on the UNCHANGED connector framework.

The provider speaks the four-method contract over Microsoft Graph and
NOTHING else:

    validate  -> token + site/drive resolution reachable
    describe  -> audit-safe source context (never secrets)
    discover  -> drive items as ConnectorItems (URI = item identity)
    fetch     -> bytes for one item

POLICY-FREE BY RULING: this provider reports Graph facts VERBATIM -
site, drive, item id, webUrl, eTag/cTag, modified time, modified-by,
whatever the tenant exposes - and decides nothing. Classification and
source-authority inheritance belong to v1.2.x policies. URI = identity,
the framework's content hash = the only change verdict, metadata =
context (D18) - a changed Graph timestamp with unchanged bytes is a
DUPLICATE, exactly as for every other provider.

Credentials (D25): the client secret arrives through the custody seam
(custody.release_for_scan -> framework -> constructor), in memory only.
Non-secret coordinates (tenant_id, client_id) ride on the credential's
custody metadata. Nothing here logs, stores, or returns the secret;
error messages never echo it.

Configuration: connector.root_path is the site URL, optionally suffixed
with '::LibraryName' to select a named document library (default: the
site's default drive), e.g.
    https://contoso.sharepoint.com/sites/QMS
    https://contoso.sharepoint.com/sites/QMS::Policies

The Graph transport is injectable (CI drives a fake transport - the
fake:// pattern that ratified D18); the default transport is stdlib
urllib. Structural purity: this module imports stdlib + the connector
contract only.
"""
import datetime
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from app.connectors.exceptions import ConnectorError, FetchError, SourceValidationError
from app.connectors.models import ConnectorFetchResult, ConnectorItem

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
LOGIN_BASE = "https://login.microsoftonline.com"
MAX_THROTTLE_RETRIES = 3

# Test seam: CI replaces this factory with a fake Graph transport.
# A transport exposes request(method, url, headers=None, data=None)
# -> (status: int, headers: dict, body: bytes).
default_transport_factory = None


class UrllibTransport:
    """The live transport - stdlib only, follows redirects (Graph content
    downloads 302 to a pre-authenticated URL)."""

    def request(self, method, url, headers=None, data=None):
        req = urllib.request.Request(url, method=method, data=data,
                                     headers=headers or {})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers or {}), e.read()


class SharePointProvider:
    """Source enumeration over one SharePoint document library - and
    nothing else. Every verdict (duplicate/changed/new/failed), all
    hashing, and all governance stay in the framework (D18)."""

    def __init__(self, connector, parseable_extensions, secret=None,
                 coordinates=None, transport=None):
        self.connector = connector
        self.parseable_extensions = set(parseable_extensions)
        self._secret = secret  # custody-released, in memory only
        self.coordinates = coordinates or {}
        factory = default_transport_factory or UrllibTransport
        self.transport = transport or factory()
        self.site_url, self.library = self._parse_root(connector.root_path)
        self._token = None
        self._site_id = None
        self._drive_id = None

    # ------------------------------------------------------------ config

    @staticmethod
    def _parse_root(root_path):
        raw = (root_path or "").strip()
        if "::" in raw:
            site, library = raw.split("::", 1)
            return site.strip().rstrip("/"), library.strip()
        return raw.rstrip("/"), None

    def _extensions(self) -> set:
        raw = self.connector.include_extensions or ",".join(sorted(self.parseable_extensions))
        wanted = {e.strip().lower() for e in raw.split(",") if e.strip()}
        return wanted & self.parseable_extensions

    # -------------------------------------------------------------- auth

    def _acquire_token(self) -> str:
        if self._token:
            return self._token
        tenant = self.coordinates.get("tenant_id")
        client = self.coordinates.get("client_id")
        if not tenant or not client:
            raise SourceValidationError(
                "SharePoint credential coordinates must include tenant_id "
                "and client_id (non-secret custody metadata on the bound "
                "credential).")
        if not self._secret:
            raise SourceValidationError(
                "SharePoint connector has no released client secret - bind "
                "an ACTIVE CONNECTOR credential; the custody layer releases "
                "it to the scan.")
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": client,
            "client_secret": self._secret,
            "scope": "https://graph.microsoft.com/.default",
        }).encode("ascii")
        status, _headers, raw = self.transport.request(
            "POST", f"{LOGIN_BASE}/{tenant}/oauth2/v2.0/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=body)
        payload = _json_or_empty(raw)
        if status != 200 or "access_token" not in payload:
            # Actionable, and NEVER echoing the secret: Graph's error code
            # + description name the cause (bad secret, unknown client,
            # consent missing).
            raise SourceValidationError(
                f"SharePoint authentication failed (HTTP {status}): "
                f"{payload.get('error', 'unknown_error')} - "
                f"{payload.get('error_description', 'no description')[:300]}")
        self._token = payload["access_token"]
        return self._token

    # ------------------------------------------------------------- graph

    def _graph(self, url) -> dict:
        """One authenticated Graph GET with declared failure handling:
        throttling is retried (Retry-After honored) then declared; auth
        and permission failures are operator-actionable; nothing silent."""
        token = self._acquire_token()
        for attempt in range(MAX_THROTTLE_RETRIES + 1):
            status, headers, raw = self.transport.request(
                "GET", url, headers={"Authorization": f"Bearer {token}"})
            if status == 429:
                if attempt == MAX_THROTTLE_RETRIES:
                    raise ConnectorError(
                        f"Microsoft Graph throttled the scan ({MAX_THROTTLE_RETRIES} "
                        f"retries exhausted) at {url}. The scan failed; rerun later.")
                retry_after = _int_or(headers.get("Retry-After"), 1)
                time.sleep(min(retry_after, 30))
                continue
            if status in (401, 403):
                payload = _json_or_empty(raw)
                message = payload.get("error", {}).get("message") or repr(raw[:200])
                raise SourceValidationError(
                    f"Microsoft Graph refused the request (HTTP {status}) at "
                    f"{url}: {message}. Check the granted permission scope on "
                    f"the credential (Sites.Selected on this site, or "
                    f"Sites.Read.All).")
            if status != 200:
                raise ConnectorError(
                    f"Microsoft Graph returned HTTP {status} at {url}: {raw[:200]!r}")
            return _json_or_empty(raw)

    def _ensure_resolved(self):
        """Resolve the configured site URL (and optional library name) to
        Graph site/drive ids. Resolution is reachability work - validate()
        territory - but discover() self-resolves so the contract holds
        when called directly."""
        if self._site_id and self._drive_id:
            return
        parsed = urllib.parse.urlparse(self.site_url)
        if not parsed.netloc or not parsed.path:
            raise SourceValidationError(
                f"SharePoint root_path must be a site URL like "
                f"https://tenant.sharepoint.com/sites/Name "
                f"(optionally ::LibraryName): {self.connector.root_path!r}")
        site = self._graph(f"{GRAPH_BASE}/sites/{parsed.netloc}:{parsed.path}")
        self._site_id = site.get("id")
        if not self._site_id:
            raise SourceValidationError(
                f"Site not resolvable through Graph: {self.site_url}")
        if self.library:
            drives = self._graph(f"{GRAPH_BASE}/sites/{self._site_id}/drives")
            match = [d for d in drives.get("value", [])
                     if d.get("name") == self.library]
            if not match:
                available = sorted(d.get("name", "?") for d in drives.get("value", []))
                raise SourceValidationError(
                    f"Document library '{self.library}' not found on "
                    f"{self.site_url}; available: {available}")
            self._drive_id = match[0]["id"]
        else:
            drive = self._graph(f"{GRAPH_BASE}/sites/{self._site_id}/drive")
            self._drive_id = drive.get("id")
        if not self._drive_id:
            raise SourceValidationError(
                f"No document library resolvable on {self.site_url}")

    # ---------------------------------------------------------- contract

    def validate(self) -> None:
        """Reachability only: token acquisition + site/drive resolution.
        Whether ingestion should run stays the framework's question."""
        self._ensure_resolved()

    def describe(self) -> dict:
        """Audit-safe source context - configuration and resolved ids,
        never credentials."""
        described = {"provider": "SHAREPOINT", "site_url": self.site_url,
                     "library": self.library,
                     "extensions": sorted(self._extensions())}
        if self._site_id:
            described["site_id"] = self._site_id
            described["drive_id"] = self._drive_id
        return described

    def discover(self) -> list:
        """Enumerate the library's files as ConnectorItems, deterministic
        order, pagination followed to the end. URI = the Graph drive-item
        identity (stable across renames and moves within the drive -
        stronger identity than a path). Metadata is Graph's description
        of the item, VERBATIM - context only, never a verdict."""
        self._ensure_resolved()
        items = []
        pending = [f"{GRAPH_BASE}/drives/{self._drive_id}/root/children"]
        while pending:
            url = pending.pop(0)
            page = self._graph(url)
            for entry in page.get("value", []):
                if "folder" in entry:
                    pending.append(
                        f"{GRAPH_BASE}/drives/{self._drive_id}/items/{entry['id']}/children")
                    continue
                if "file" not in entry:
                    continue  # packages, notebooks etc.: not files, declared by facet
                name = entry.get("name", "")
                ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
                if ext not in self._extensions():
                    continue
                items.append(ConnectorItem(
                    uri=f"sharepoint://{self._site_id}/{self._drive_id}/{entry['id']}",
                    name=name,
                    metadata=self._verbatim(entry)))
            next_link = page.get("@odata.nextLink")
            if next_link:
                pending.append(next_link)
        return sorted(items, key=lambda i: (i.metadata.get("web_url") or "", i.uri))

    def fetch(self, item: ConnectorItem) -> ConnectorFetchResult:
        """Bytes for one item. The framework's sha256 of these bytes is
        the ONLY change verdict; the metadata here is described context."""
        item_id = item.uri.rsplit("/", 1)[-1]
        token = self._acquire_token()
        status, _headers, raw = self.transport.request(
            "GET", f"{GRAPH_BASE}/drives/{self._drive_id}/items/{item_id}/content",
            headers={"Authorization": f"Bearer {token}"})
        if status != 200:
            raise FetchError(
                f"Graph content download failed (HTTP {status}) for "
                f"{item.name} ({item.uri}): {raw[:200]!r}")
        return ConnectorFetchResult(
            data=raw,
            metadata={
                "size_bytes": len(raw),
                "modified_at": _parse_graph_time(
                    item.metadata.get("last_modified_at")),
            })

    # ---------------------------------------------------------- verbatim

    @staticmethod
    def _verbatim(entry: dict) -> dict:
        """Graph facts, reported as Graph states them - no interpretation,
        no policy. v1.2.x classification/Tier-0 policies consume these
        from ConnectorItem.metadata; the provider decides nothing."""
        by_modified = (entry.get("lastModifiedBy") or {}).get("user", {})
        by_created = (entry.get("createdBy") or {}).get("user", {})
        return {
            "web_url": entry.get("webUrl"),
            "etag": entry.get("eTag"),
            "ctag": entry.get("cTag"),
            "size_bytes": entry.get("size"),
            "created_at": entry.get("createdDateTime"),
            "last_modified_at": entry.get("lastModifiedDateTime"),
            "last_modified_by": by_modified.get("displayName"),
            "last_modified_by_email": by_modified.get("email"),
            "created_by": by_created.get("displayName"),
            "parent_path": (entry.get("parentReference") or {}).get("path"),
            "mime_type": (entry.get("file") or {}).get("mimeType"),
            # Tenant-exposed list-item fields (content type, approval
            # status where the tenant surfaces them) ride along verbatim
            # when Graph includes them; absent means the tenant did not
            # expose them - never fabricated (D12).
            "list_item_fields": (entry.get("listItem") or {}).get("fields"),
        }


def _json_or_empty(raw: bytes) -> dict:
    try:
        return json.loads(raw.decode("utf-8")) if raw else {}
    except (ValueError, UnicodeDecodeError):
        return {}


def _int_or(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _parse_graph_time(value):
    """Graph ISO-8601 ('2026-07-01T10:00:00Z') -> naive UTC datetime, the
    convention source_modified_at uses. None stays None (D12: absent is
    absent, never fabricated)."""
    if not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    except ValueError:
        return None
