import datetime
import os

from app.connectors.exceptions import SourceValidationError
from app.connectors.models import ConnectorFetchResult, ConnectorItem


class LocalFolderProvider:
    """Source enumeration over a local or mounted directory - and nothing
    else. The provider describes what exists (URIs, names, context) and
    hands over bytes on request; every verdict (duplicate/changed/new/
    failed), all hashing, and all governance stay in the framework.
    """

    def __init__(self, connector, parseable_extensions):
        # Seam 1 (concern map): parseable_extensions is the FRAMEWORK's
        # parser capability, handed in at construction; include_extensions
        # is operator config on the connector row. Enumeration filters on
        # the intersection - never ingest a type the parser can't handle,
        # declared, not silent.
        self.connector = connector
        self.parseable_extensions = set(parseable_extensions)

    def _extensions(self) -> set:
        raw = self.connector.include_extensions or ",".join(sorted(self.parseable_extensions))
        wanted = {e.strip().lower() for e in raw.split(",") if e.strip()}
        return wanted & self.parseable_extensions

    def validate(self) -> None:
        """Reachability only - whether ingestion should run is the
        framework's question. Message is operator-facing (becomes the
        job error, byte-identical to the pre-0.11 behavior)."""
        if not os.path.isdir(self.connector.root_path):
            raise SourceValidationError(
                f"Connector root path does not exist or is not a directory: {self.connector.root_path}")

    def describe(self) -> dict:
        """Audit-safe source context, logged by the framework without
        interpretation. Field order matters: payloads must stay identical
        to the pre-0.11 INGESTION_JOB_STARTED events."""
        return {"root_path": self.connector.root_path,
                "extensions": sorted(self._extensions())}

    def discover(self) -> list[ConnectorItem]:
        """Recursive walk filtered to the extension intersection, sorted for
        deterministic scans. URI = os.path.abspath of the discovered path -
        byte-identical to the identity the v0.10.x reconciliation recorded,
        so prior SourceDocument rows keep matching."""
        matches = []
        for dirpath, _dirnames, filenames in os.walk(self.connector.root_path):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in self._extensions():
                    matches.append(os.path.join(dirpath, filename))
        return [ConnectorItem(uri=os.path.abspath(path), name=os.path.basename(path))
                for path in sorted(matches)]

    def fetch(self, item: ConnectorItem) -> ConnectorFetchResult:
        """Read one file. Called at ingest time, not discovery time - size,
        mtime, and content are measured when the framework processes the
        item, exactly as v0.10.x did. Metadata is described context only;
        the framework's sha256 of data remains the sole change verdict."""
        stat = os.stat(item.uri)
        with open(item.uri, "rb") as f:
            data = f.read()
        return ConnectorFetchResult(
            data=data,
            metadata={
                "size_bytes": stat.st_size,
                "modified_at": datetime.datetime.utcfromtimestamp(stat.st_mtime),
            })
