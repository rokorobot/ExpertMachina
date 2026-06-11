from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# The connector contract (MVP 0.11 Step 2): the language providers and the
# framework speak. Types only - behavior stays in framework.py until the
# extraction steps move it.
#
# The hard invariant these types encode (docs/scoping-0.11-connector-framework.md):
#
#   URI          = identity
#   content hash = change verdict
#   metadata     = context
#
# Providers DESCRIBE source state; only the framework DECIDES reconciliation
# (duplicate / changed / new / failed, revisions, policy, approval).


@dataclass
class ConnectorItem:
    """One source item as described by a provider.

    uri: the item's identity within its connector (D7) - stable across
    scans, constructed by the provider, opaque to the framework.
    name: display/file name used for the eventual Document row.
    metadata: provider-described context (size, modified time, source
    specifics). Context ONLY - the framework never derives a change
    verdict from it.

    Deliberately not file-shaped: one source file may yield many items
    (Slack export channels, Notion pages) - the provider owns that mapping.
    """
    uri: str
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorFetchResult:
    """Raw content for one item: bytes plus described metadata.

    The framework's sha256 of `data` is the only change signal; metadata
    is informational (seam test 3 - modified_at may change while the
    verdict stays NOT CHANGED).
    """
    data: bytes
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ConnectorProvider(Protocol):
    """What a source must be able to do. Four capabilities, discovered
    against the real LocalFolder behavior in Phase 1 - each answers one
    question and deliberately NOT its neighbor:

    validate  -> "Can this source be used?"        not "should ingestion run?"
    describe  -> "How is this source explained
                  in audit events?"                not "how is ingestion configured?"
    discover  -> "What source items exist?"        not "which ones changed?"
    fetch     -> "Give me bytes."                  not "did content change?"

    Everything on the right-hand side is framework territory.
    """

    def validate(self) -> None:
        """Raise (with an operator-actionable message) if the source is
        unreachable or unusable; return None otherwise."""
        ...

    def describe(self) -> dict:
        """Audit-safe source context for job event payloads. The framework
        logs it without understanding provider-specific fields."""
        ...

    def discover(self) -> list[ConnectorItem]:
        """Enumerate the source as ConnectorItems, deterministic order.
        Traversal and URI construction belong to the provider."""
        ...

    def fetch(self, item: ConnectorItem) -> ConnectorFetchResult:
        """Return the raw content of one item. Failures raise; the
        framework records the reason and continues the scan."""
        ...
