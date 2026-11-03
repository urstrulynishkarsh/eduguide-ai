"""Shared test setup.

* `tests/unit` needs nothing running.
* `tests/api` needs PostgreSQL (start it with `docker compose up -d`).

API tests use their own database (`eduguide_test`). It is wiped and rebuilt
from the migrations at the start of each run, and every test runs inside a
transaction that is rolled back afterwards, so tests never see each other's data.
"""

import asyncio
import os
import shutil
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://eduguide:eduguide@localhost:5432/eduguide_test"
)

# The app reads its settings when it is imported, so these must be set first.
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-never-use-outside-tests-0123456789"
os.environ["LOG_LEVEL"] = "WARNING"
# Uploaded files go to a throw-away folder; OCR is off unless a test switches in a fake one.
TEST_STORAGE_DIR = tempfile.mkdtemp(prefix="eduguide-test-storage-")
os.environ["STORAGE_DIR"] = TEST_STORAGE_DIR
os.environ["OCR_PROVIDER"] = "none"
os.environ["LLM_PROVIDER"] = "none"  # tests that need the AI switch in a FakeLLM

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import make_url, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.core.tasks import Job, get_task_queue  # noqa: E402
from app.main import app  # noqa: E402
from app.rag import embeddings  # noqa: E402
from tests.fakes import FakeEmbeddings  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent


def alembic_config() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


def _refuse_non_test_database() -> None:
    name = make_url(TEST_DATABASE_URL).database or ""
    if not name.endswith("_test"):
        raise RuntimeError(
            f"Refusing to run: tests wipe their database, and '{name}' does not end in '_test'."
        )


async def _reset_schema() -> None:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


@pytest.fixture(scope="session")
def migrated_database() -> None:
    """An empty test database with every migration applied."""
    _refuse_non_test_database()
    try:
        asyncio.run(_reset_schema())
    except (OSError, ConnectionError) as exc:
        pytest.exit(
            f"Cannot reach the test database at {make_url(TEST_DATABASE_URL).render_as_string()}.\n"
            f"Start it with `docker compose up -d` from the project root. ({exc})",
            returncode=2,
        )
    command.upgrade(alembic_config(), "head")


@pytest.fixture
async def db_session(migrated_database: None) -> AsyncIterator[AsyncSession]:
    """A session whose work is thrown away when the test ends.

    The app calls `commit()` as usual; here a commit only releases a savepoint
    inside an outer transaction that is rolled back at the end.
    """
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch: pytest.MonkeyPatch) -> FakeEmbeddings:
    """The real search model is ~1 GB; tests use a small bag-of-words stand-in."""
    fake = FakeEmbeddings()
    monkeypatch.setattr(embeddings, "get_embedding_provider", lambda: fake)
    return fake


@pytest.fixture(scope="session", autouse=True)
def _remove_test_storage() -> Any:
    yield
    shutil.rmtree(TEST_STORAGE_DIR, ignore_errors=True)


class InlineTaskQueue:
    """Runs background jobs immediately, inside the request, with the test session.

    The real queue runs them later in their own session; running them inline makes tests
    deterministic: when the upload request returns, the book has been read.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.jobs: list[str] = []

    async def enqueue(self, job: Job, /, **kwargs: Any) -> None:
        self.jobs.append(job.__name__)
        await job(self.session, **kwargs)


@pytest.fixture
def task_queue(db_session: AsyncSession) -> InlineTaskQueue:
    return InlineTaskQueue(db_session)


@pytest.fixture
async def client(db_session: AsyncSession, task_queue: InlineTaskQueue) -> AsyncIterator[AsyncClient]:
    """An HTTP client that talks to the app in-process, using the test session."""

    async def use_test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = use_test_session
    app.dependency_overrides[get_task_queue] = lambda: task_queue
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
            yield http_client
    finally:
        app.dependency_overrides.clear()
