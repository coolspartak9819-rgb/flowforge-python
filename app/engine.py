import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from app.db import session_factory
from app.models import Workflow, WorkflowRun

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutionResult:
    requeue: bool = False
    delay_seconds: float = 0


def utc_now() -> datetime:
    return datetime.now(UTC)


class WorkflowEngine:
    async def execute(self, run_id: str) -> ExecutionResult:
        async with session_factory() as session:
            run = await session.get(WorkflowRun, run_id)
            if run is None:
                return ExecutionResult()
            workflow = await session.get(Workflow, run.workflow_id)
            if workflow is None:
                await self._fail(session, run, "workflow not found")
                return ExecutionResult()

            if run.status in {"COMPLETED", "FAILED"}:
                return ExecutionResult()
            if run.status == "PENDING":
                run.status = "RUNNING"
                run.started_at = utc_now()
                run.attempts += 1
                await session.commit()
            elif run.status == "RETRYING":
                run.status = "RUNNING"
                run.attempts += 1
                await session.commit()

            try:
                for index in range(run.current_step, len(workflow.definition)):
                    step = workflow.definition[index]
                    run.current_step = index
                    await session.commit()
                    await self._run_step(step)
                run.current_step = len(workflow.definition)
                run.status = "COMPLETED"
                run.finished_at = utc_now()
                await session.commit()
                return ExecutionResult()
            except Exception as error:
                logger.exception("workflow run failed", extra={"run_id": run_id})
                run.error = str(error)[:2000]
                if run.attempts < run.max_attempts:
                    run.status = "RETRYING"
                    await session.commit()
                    delay = float(2 ** max(0, run.attempts - 1))
                    return ExecutionResult(requeue=True, delay_seconds=delay)
                await self._fail(session, run, run.error)
                return ExecutionResult()

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
