
from typing import Any, Literal

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    job_type: Literal["report", "email", "webhook"]
    payload: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    job_id: str
    job_type: str
    status: str


class JobStatusResponse(JobResponse):
    payload: dict[str, Any]
    attempts: int
    last_error: str | None
