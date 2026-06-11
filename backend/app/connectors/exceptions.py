# Connector contract exceptions (MVP 0.11 Step 2). Deliberately minimal:
# the framework treats ANY exception escaping a provider as a declared
# failure (recorded with its message, never silent) - this hierarchy lets
# providers be intentional, it does not let the framework branch on types.


class ConnectorError(Exception):
    """Base for provider-raised errors."""


class SourceValidationError(ConnectorError):
    """validate() failed: the source is unreachable or unusable.
    The message is operator-facing - it becomes the job error."""


class FetchError(ConnectorError):
    """fetch() failed for one item. The scan continues; the item's
    SourceDocument row records the reason (seam test 2)."""
