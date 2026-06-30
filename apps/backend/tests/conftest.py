"""Shared test fixtures."""

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Override settings BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["UPLOAD_DIR"] = str(Path(__file__).parent / "_test_uploads")
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["TESTING"] = "1"  # disable the in-process rate limiter
os.environ["ENABLE_AUTH"] = "false"  # most backend tests run in auth-disabled mode

from app.database import get_db
from app.main import app
from app.models.db_models import Base


class _AsyncSessionAdapter:
    """Async-compatible facade over a synchronous SQLAlchemy Session.

    Why this exists:
    - Some environments hang on ``aiosqlite.connect()``.
    - Application code and tests already use ``await db.execute(...)`` style.
    - This adapter keeps that call shape while using fast, stable sync SQLite.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)

    def add(self, instance: Any) -> None:
        self._session.add(instance)

    def add_all(self, instances: list[Any]) -> None:
        self._session.add_all(instances)

    async def execute(self, *args: Any, **kwargs: Any):
        return self._session.execute(*args, **kwargs)

    async def scalar(self, *args: Any, **kwargs: Any):
        return self._session.scalar(*args, **kwargs)

    async def scalars(self, *args: Any, **kwargs: Any):
        return self._session.scalars(*args, **kwargs)

    async def get(self, *args: Any, **kwargs: Any):
        return self._session.get(*args, **kwargs)

    async def flush(self) -> None:
        self._session.flush()

    async def refresh(self, instance: Any, *args: Any, **kwargs: Any) -> None:
        self._session.refresh(instance, *args, **kwargs)

    async def delete(self, instance: Any) -> None:
        self._session.delete(instance)

    async def commit(self) -> None:
        self._session.commit()

    async def rollback(self) -> None:
        self._session.rollback()

    async def close(self) -> None:
        self._session.close()


class _AsyncSessionContext:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory
        self._wrapped: _AsyncSessionAdapter | None = None

    async def __aenter__(self) -> _AsyncSessionAdapter:
        self._wrapped = _AsyncSessionAdapter(self._factory())
        return self._wrapped

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._wrapped is not None:
            await self._wrapped.close()


class _AsyncSessionMaker:
    def __init__(self, factory: sessionmaker[Session] | None = None) -> None:
        self._factory = factory

    def bind_factory(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def __call__(self) -> _AsyncSessionContext:
        if self._factory is None:
            raise RuntimeError("Test session maker is not initialized.")
        return _AsyncSessionContext(self._factory)


def _new_test_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )


_test_engine = _new_test_engine()
_sync_session_maker = sessionmaker(bind=_test_engine, expire_on_commit=False)
_test_session_maker = _AsyncSessionMaker(_sync_session_maker)


async def _override_get_db() -> AsyncIterator[_AsyncSessionAdapter]:
    async with _test_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db


class _SyncJobQueue:
    """In-process test queue: runs the job to completion before returning.

    This preserves the synchronous semantics that the test suite
    relied on under FastAPI's BackgroundTasks — the test sends a
    POST, the job runs inside the request, and by the time the test
    asserts, the row is in its final state.
    """

    def __init__(self) -> None:
        self._draining = False
        self._inflight: set[Awaitable[Any]] = set()

    @property
    def draining(self) -> bool:
        return self._draining

    @property
    def in_flight(self) -> int:
        return len(self._inflight)

    async def submit(self, job_id: str, run: Callable[[], Awaitable[Any]]) -> None:
        if self._draining:
            raise RuntimeError("test queue is draining")
        # Run synchronously (await) so the test sees the final state.
        await run()

    async def shutdown(self, timeout: float = 5.0) -> None:
        self._draining = True


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test and reset the in-process job queue."""
    global _test_engine

    # Fresh in-memory DB per test prevents teardown hangs from stale locks.
    _test_engine.dispose()
    _test_engine = _new_test_engine()
    _test_session_maker.bind_factory(sessionmaker(bind=_test_engine, expire_on_commit=False))
    Base.metadata.create_all(bind=_test_engine)
    # Install the synchronous test queue for the duration of the test.
    from app.services.jobs import reset_job_queue_for_tests

    reset_job_queue_for_tests()
    from app.services import jobs as jobs_module

    jobs_module._job_queue = _SyncJobQueue()  # type: ignore[attr-defined]
    yield
    # Drain anything still in flight (none, in the sync queue, but
    # be defensive) and then drop the schema.
    jobs_module._job_queue = None  # type: ignore[attr-defined]
    _test_engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
