from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from queueflow.db.sessions import SessionLocal
from queueflow.schemas import JobCreate, JobResponse, JobStatusResponse
from queueflow.service import get_job, submit_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def get_db():
    with SessionLocal() as db:
        yield db


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_job(
    data: JobCreate,
    db: Session = Depends(get_db),
):
    try:
        job = submit_job(data, db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to publish job to the queue.",
        ) from exc

    return JobResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def read_job(
    job_id: str,
    db: Session = Depends(get_db),
):
    job = get_job(job_id, db)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    return JobStatusResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        payload=job.payload,
        attempts=job.attempts,
        last_error=job.last_error,
    )
