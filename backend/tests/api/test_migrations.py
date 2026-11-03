"""The migrations and the models must always describe the same database."""

import asyncio

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.models import Base
from tests.conftest import TEST_DATABASE_URL, alembic_config


async def _differences() -> list:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as connection:
        differences = await connection.run_sync(
            lambda sync_connection: compare_metadata(
                MigrationContext.configure(sync_connection), Base.metadata
            )
        )
    await engine.dispose()
    return differences


def test_migrations_match_the_models(migrated_database: None):
    """Fails when a model was changed without writing a migration for it."""
    assert asyncio.run(_differences()) == []


def test_migrations_can_be_undone_and_applied_again(migrated_database: None):
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    assert asyncio.run(_differences()) == []
