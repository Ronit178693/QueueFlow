import json
import time

from sqlalchemy import update
from queueflow.db.models import Job
from queueflow.db.sessions import SessionLocal
from queueflow.sqs_client import get_queue_url, sqs
from queueflow.claims import claim_job, complete_job


def process_job(job_type: str, payload: dict) -> None:
    """Simulate the business operation for a job."""
    print(f"Executing {job_type}: {payload}")

    # Simulate a slow task.
    time.sleep(3)

    print("Business operation completed.")


def fail_job(db, job_id: str, token: str, error: str) -> bool:
    """Only the current lease owner may mark a job failed."""
    statement = (
        update(Job)
        .where(
            Job.id == job_id,
            Job.status == "processing",
            Job.lease_token == token,
        )
        .values(
            status="failed",
            last_error=error[:1000],
            lease_expires_at=None,
            lease_token=None,
        )
        .returning(Job.id)
    )

    failed_id = db.execute(statement).scalar_one_or_none()

    if failed_id is None:
        db.rollback()
        return False

    db.commit()
    return True






def run_worker() -> None:
    queue_url = get_queue_url()
    print("Worker started. Waiting for jobs...")

    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )

        for message in response.get("Messages", []):
            receipt_handle = message["ReceiptHandle"]

            try:
                body = json.loads(message["Body"])
                job_id = body["job_id"]

                with SessionLocal() as db:
                    job = claim_job(db, job_id)

                    if job is None:
                        # Another worker may be processing it, or it may
                        # already have succeeded. Inspect before deciding.
                        existing = db.get(Job, job_id)

                        if existing is None:
                            print(f"No database record for job {job_id}")

                        elif existing.status == "succeeded":
                            sqs.delete_message(
                                QueueUrl=queue_url,
                                ReceiptHandle=receipt_handle,
                            )
                            print(f"Removed completed duplicate: {job_id}")

                        else:
                            print(
                                f"Could not claim {job_id}; "
                                f"current status: {existing.status}"
                            )

                        continue

                    token = job.lease_token
                    job_type = job.job_type
                    payload = job.payload

                print(f"Claimed job {job_id} with token {token}")

                process_job(job_type, payload)

                with SessionLocal() as db:
                    completed = complete_job(db, job_id, token)

                if not completed:
                    print(f"Job {job_id}: lease ownership lost.")
                    # Don't delete: another worker may need this message.
                    continue
                
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle,
                )
                print(f"Job {job_id} succeeded and message deleted.")

            except Exception as exc:
                print(f"Processing failed for {job_id}: {exc}")

                if job_id is not None and token is not None:
                    try:
                        with SessionLocal() as db:
                            updated = fail_job(
                                db, job_id, token, str(exc)
                            )
                        if not updated:
                            print("Failure update rejected: lease no longer owned.")
                    except Exception as db_exc:
                        print(f"Could not record failure: {db_exc}")

                # Leave SQS message undeleted for redelivery.



if __name__ == "__main__":
    run_worker()
