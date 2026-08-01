from redis.asyncio import Redis
from redis.exceptions import ResponseError

STREAM_NAME = "flowforge:runs"
GROUP_NAME = "flowforge-workers"


async def ensure_consumer_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
    except ResponseError as error:
        if "BUSYGROUP" not in str(error):
            raise


async def enqueue_run(redis: Redis, run_id: str) -> str:
    return await redis.xadd(STREAM_NAME, {"run_id": run_id}, maxlen=10000, approximate=True)


async def consume_runs(redis: Redis, consumer_name: str, handler, recovery_idle_ms: int = 30000) -> None:
    await ensure_consumer_group(redis)
    while True:
        _, pending_entries, _ = await redis.xautoclaim(
            STREAM_NAME,
            GROUP_NAME,
            consumer_name,
            min_idle_time=recovery_idle_ms,
            start_id="0-0",
            count=10,
        )
        if pending_entries:
            await _handle_entries(redis, pending_entries, handler)
            continue

        messages = await redis.xreadgroup(
            GROUP_NAME,
            consumer_name,
            {STREAM_NAME: ">"},
            count=1,
            block=1000,
        )
        for _, entries in messages:
            await _handle_entries(redis, entries, handler)


async def _handle_entries(redis: Redis, entries, handler) -> None:
    for message_id, values in entries:
        await handler(values["run_id"])
        await redis.xack(STREAM_NAME, GROUP_NAME, message_id)
