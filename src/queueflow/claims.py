
from sqlalchemy import update, and_, or_, update
from sqlalchemy.orm import Session

from queueflow.db.models import Job

from datetime import datetime, timedelta, timezone

from uuid import uuid4

LEASE_SECONDS = 60


def claim_job(db: Session, job_id: str) -> Job | None:
    now = datetime.now(timezone.utc)
    # Lease tocken
    token = str(uuid4())

    statement = (
        update(Job)
        .where(
            Job.id == job_id,
            or_(
                Job.status.in_(["queued", "failed"]),
                and_(
                    Job.status == "processing",
                    Job.lease_expires_at < now,
                ),
            ),
        )
        .values(
            status="processing",
            attempts=Job.attempts + 1,
            last_error=None,
            lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
            lease_token=token,
        )
        .returning(Job.id)
    )

    claimed_id = db.execute(statement).scalar_one_or_none()

    if claimed_id is None:
        db.rollback()
        return None

    db.commit()
    return db.get(Job, claimed_id)

# Gets the token from the worker for comparision with the token stored in the DB 
def complete_job(db: Session, job_id: str, token: str) -> bool:
    statement = (
        update(Job)
        .where(
            Job.id == job_id,
            Job.status == "processing",
            # The job is still owned by the worker
            Job.lease_token == token,
            # The worker still got the time to complete the job
            Job.lease_expires_at > datetime.now(timezone.utc),
        )
        .values(
            # If the above conditions matches mark the job a success 
            status="succeeded",
            lease_expires_at=None,
            lease_token=None,
        )
        .returning(Job.id)
    )

    completed_id = db.execute(statement).scalar_one_or_none()

    if completed_id is None:
        db.rollback()
        return False

    db.commit()
    return True

