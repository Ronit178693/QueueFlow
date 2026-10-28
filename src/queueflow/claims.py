
from sqlalchemy import update
from sqlalchemy.orm import Session

from queueflow.db.models import Job


def claim_job(db: Session, job_id: str) -> Job | None:
    """
    Atomically claim a job only if it is queued or failed.

    Returns the claimed job, or None if another worker has
    already claimed it or it has already succeeded.
    """
    
    # Check and write are one atomic operation so no 2 processes on the DB
    statement = (
        update(Job)
        .where(
            Job.id == job_id,
            Job.status.in_(["queued", "failed"]),
        )
        .values(
            status="processing",
            attempts=Job.attempts + 1,
            last_error=None,
        )
        .returning(Job.id)
    )

    claimed_id = db.execute(statement).scalar_one_or_none()

    if claimed_id is None:
        db.rollback()
        return None

    db.commit()
    return db.get(Job, claimed_id)
