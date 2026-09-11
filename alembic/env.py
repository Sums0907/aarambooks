import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from src.shared.config import settings
from src.infrastructure.database import Base

# Import every model module that declares tables against this Base so autogenerate sees
# them. Importing the module is what registers the class on Base.metadata - this is the
# same requirement that made scripts/setup_db.py silently create only sabaq_evidence and
# skip core_memories/core_suspended_actions/core_knowledge (see
# docs/claude/DEPLOYMENT_STRATEGY_BRAIN_VPS.md for how that was found).
import src.infrastructure.adapters.postgres_memory  # noqa: F401 (registers MemoryRecord, SuspendedActionRecord)
import src.infrastructure.adapters.postgres_knowledge  # noqa: F401 (registers KnowledgeRecord)
import src.infrastructure.adapters.postgres_sabaq  # noqa: F401 (registers SabaqEvidenceRecord)

# src/brain_core/infrastructure/database.py and src/brain_core/context_engine/models.py each
# declare their own separate declarative_base() too, but neither has any model registered
# against it anywhere in the codebase (context_engine's is explicitly documented as
# intentionally stateless) - so there is nothing there for Alembic to track.

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Always use the app's real settings.database_url rather than alembic.ini's static value,
# so the same migration runs correctly in dev, CI, and on the VPS without editing alembic.ini
# per environment.
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
