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


async def consume_runs(redis: Redis, consumer_name: str, handler) -> None:
    await ensure_consumer_group(redis)
    while True:
        messages = await redis.xreadgroup(
            GROUP_NAME,
            consumer_name,
            {STREAM_NAME: ">"},
            count=1,
            block=1000,
        )
        for _, entries in messages:
            for message_id, values in entries:
                await handler(values["run_id"])
                await redis.xack(STREAM_NAME, GROUP_NAME, message_id)
