import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import engine, get_session, init_db
from app.engine import WorkflowEngine
from app.models import Workflow, WorkflowRun
from app.schemas import RunResponse, WorkflowCreate, WorkflowResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
engine_runner = WorkflowEngine()
web_path = Path(__file__).parent / "web" / "index.html"


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield
    await engine_runner.shutdown()
    await engine.dispose()


app = FastAPI(title="FlowForge", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(web_path)


@app.post("/api/workflows", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(payload: WorkflowCreate, session: AsyncSession = Depends(get_session)):
    workflow = Workflow(
        id=str(uuid4()),
        name=payload.name,
        description=payload.description,
        definition=[step.model_dump() for step in payload.steps],
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)
    return _workflow_response(workflow)


@app.get("/api/workflows", response_model=list[WorkflowResponse])
async def list_workflows(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(Workflow).order_by(Workflow.created_at.desc()))
    return [_workflow_response(workflow) for workflow in result]


@app.post("/api/workflows/{workflow_id}/runs", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_run(workflow_id: str, session: AsyncSession = Depends(get_session)):
    workflow = await session.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    run = WorkflowRun(id=str(uuid4()), workflow_id=workflow_id)
    session.add(run)
    await session.commit()
    await session.refresh(run)
    engine_runner.start(run.id)
    return _run_response(run)


@app.get("/api/runs", response_model=list[RunResponse])
async def list_runs(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(100))
    return [_run_response(run) for run in result]


@app.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)):
    run = await session.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _run_response(run)


def _workflow_response(workflow: Workflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        steps=workflow.definition,
        created_at=workflow.created_at,
    )


def _run_response(run: WorkflowRun) -> RunResponse:
    return RunResponse(
        id=run.id,
        workflow_id=run.workflow_id,
        status=run.status,
        current_step=run.current_step,
        error=run.error,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )
