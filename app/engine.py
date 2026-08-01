import asyncio
import logging
from datetime import UTC, datetime

from app.db import session_factory
from app.models import Workflow, WorkflowRun

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


class WorkflowEngine:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    def start(self, run_id: str) -> None:
        task = asyncio.create_task(self.execute(run_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def shutdown(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def execute(self, run_id: str) -> None:
        async with session_factory() as session:
            run = await session.get(WorkflowRun, run_id)
            if run is None:
                return
            workflow = await session.get(Workflow, run.workflow_id)
            if workflow is None:
                await self._fail(session, run, "workflow not found")
                return

            run.status = "RUNNING"
            run.started_at = utc_now()
            await session.commit()

            try:
                for index, step in enumerate(workflow.definition):
                    run.current_step = index
                    await session.commit()
                    await self._run_step(step)
                run.current_step = len(workflow.definition)
                run.status = "COMPLETED"
                run.finished_at = utc_now()
                await session.commit()
            except Exception as error:
                logger.exception("workflow run failed", extra={"run_id": run_id})
                await self._fail(session, run, str(error))

    async def _run_step(self, step: dict) -> None:
        if step["kind"] == "delay":
            await asyncio.sleep(step.get("seconds", 0.2))
        elif step["kind"] == "fail":
            raise RuntimeError(step.get("message") or "step failed intentionally")
        elif step["kind"] == "log":
            logger.info("workflow step: %s", step.get("message", "step completed"))

    async def _fail(self, session, run: WorkflowRun, message: str) -> None:
        run.status = "FAILED"
        run.error = message[:2000]
        run.finished_at = utc_now()
        await session.commit()
