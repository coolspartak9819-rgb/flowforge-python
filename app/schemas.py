from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

StepKind = Literal["log", "delay", "fail"]


class WorkflowStep(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: StepKind
    message: str = ""
    seconds: float = Field(default=0.2, ge=0, le=30)


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    steps: list[WorkflowStep] = Field(min_length=1, max_length=50)


class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    steps: list[WorkflowStep]
    created_at: datetime


class RunResponse(BaseModel):
    id: str
    workflow_id: str
    status: str
    current_step: int
    error: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
