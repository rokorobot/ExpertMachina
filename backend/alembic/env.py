"""Alembic environment (audit T2.3, the migration spine).

The single source of truth for BOTH the schema and the connection is
`app.database`: `target_metadata` is the ORM `Base.metadata` (so
autogenerate compares against the models, and the D24 fingerprint stays
model-defined), and the engine is `app.database.engine` - which the test
harness rebinds per suite. init_db() drives migrations programmatically and
passes the live connection via `config.attributes['connection']`; when run
from the CLI we fall back to the module engine. There is deliberately no
second DATABASE_URL here - a migration path with its own URL is exactly the
drift T2.3 exists to remove.

SQLite note: render_as_batch=True so any future ALTER migration uses batch
(copy-and-recreate) mode, which SQLite requires for most column changes.
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Engine

# backend/ on the path so `app` imports the same package the app runs.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("EM_NLI_VERIFICATION", "off")
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from app import database as db  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = db.Base.metadata


def run_migrations_offline() -> None:
    """`--sql` mode: emit DDL without a live DB, using the module URL."""
    context.configure(
        url=str(db.engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Prefer a caller-supplied connection (init_db passes the live one so
    the harness's per-suite engine is honored); else use the module engine."""
    connectable = config.attributes.get("connection", None)
    if connectable is None:
        connectable = db.engine
    if isinstance(connectable, Engine):
        with connectable.connect() as connection:
            _run(connection)
    else:
        # already a Connection (the init_db path)
        _run(connectable)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
