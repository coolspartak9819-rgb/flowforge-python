from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(
            text(
                "ALTER TABLE workflow_runs "
                "ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE workflow_runs "
                "ADD COLUMN IF NOT EXISTS max_attempts INTEGER NOT NULL DEFAULT 3"
            )
        )
        await connection.execute(
            text("ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(255)")
        )
        await connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_workflow_runs_idempotency_key "
                "ON workflow_runs (idempotency_key)"
            )
        )
