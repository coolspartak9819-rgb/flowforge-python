import asyncio
import logging
import os
import socket

from redis.asyncio import Redis

from app.config import settings
from app.db import engine, init_db
from app.engine import WorkflowEngine
from app.queue import consume_runs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await redis.ping()
    engine_runner = WorkflowEngine()
    consumer_name = os.getenv("WORKER_NAME", socket.gethostname())
    logger.info("FlowForge worker %s is ready", consumer_name)
    try:
        await consume_runs(
            redis,
            consumer_name,
            engine_runner.execute,
            recovery_idle_ms=settings.worker_recovery_idle_ms,
        )
    finally:
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
