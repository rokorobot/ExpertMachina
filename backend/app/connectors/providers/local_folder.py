import os

from app.connectors.exceptions import SourceValidationError
from app.connectors.models import ConnectorItem


class LocalFolderProvider:
    """Source enumeration over a local or mounted directory - and nothing
    else. The provider describes what exists (URIs, names, context); every
    verdict (duplicate/changed/new/failed), all hashing, and all governance
    stay in the framework.

    Step 3 scope: validate / describe / discover. Fetch remains in the
    framework until its own extraction step so the timing of stat/read
    (at ingest time, not discovery time) stays identical.
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
