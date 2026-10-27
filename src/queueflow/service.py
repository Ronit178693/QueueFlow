
import json
import uuid

from sqlalchemy.orm import Session

from queueflow.db.models import Job
from queueflow.queue import get_queue_url, sqs
from queueflow.schemas import JobCreate


def submit_job(data: JobCreate, db: Session) -> Job:
    job = Job(
        id=str(uuid.uuid4()),
        job_type=data.job_type,
        payload=data.payload,
        status="queued",
        attempts=0,
    )

    # First persist the job in PostgreSQL.
    db.add(job)
    db.commit()
    db.refresh(job)

    # Then publish a message to SQS.
    message = {
        "job_id": job.id,
        "job_type": job.job_type,
    }

    try:
        sqs.send_message(
            QueueUrl=get_queue_url(),
            MessageBody=json.dumps(message),
        )
    except Exception as exc:
        # Record the publication failure for visibility.
        job.status = "failed"
        job.last_error = f"Failed to publish to SQS: {exc}"[:1000]
        db.commit()
        raise

    return job


def get_job(job_id: str, db: Session) -> Job | None:
    return db.get(Job, job_id)