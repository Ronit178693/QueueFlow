
import uuid

from db.models import Job
from db.sessions import SessionLocal

job_id = str(uuid.uuid4())

with SessionLocal() as session:
    job = Job(
        id=job_id,
        job_type="report",
        payload={
            "report_name": "monthly_sales",
            "period": "2026-09",
        },
        status="queued",
    )

    session.add(job)
    session.commit()

with SessionLocal() as session:
    saved_job = session.get(Job, job_id)

    print("Job ID:", saved_job.id)
    print("Job type:", saved_job.job_type)
    print("Status:", saved_job.status)
    print("Payload:", saved_job.payload)
