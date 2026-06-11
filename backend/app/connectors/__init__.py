# Source Connector package (MVP 0.11). Step 1 of the retrofit: the v0.10.x
# connectors.py module moved here verbatim as framework.py; extraction into
# provider adapters follows in later steps. This __init__ preserves the
# existing import surface - `from app import connectors` callers (main.py,
# test suites) keep working unchanged.

from app.connectors.framework import (  # noqa: F401
    SUPPORTED_EXTENSIONS,
    UPLOAD_DIR,
    discover_files,
    execute_ingestion_job,
    run_ingestion_job,
)

# The provider contract (Step 2) - the language the framework and provider
# adapters speak. Types only until the extraction steps wire them in.
from app.connectors.exceptions import (  # noqa: F401
    ConnectorError,
    FetchError,
    SourceValidationError,
)
from app.connectors.models import (  # noqa: F401
    ConnectorFetchResult,
    ConnectorItem,
    ConnectorProvider,
)
