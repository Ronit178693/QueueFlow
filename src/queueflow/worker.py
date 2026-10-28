import json
import time

from queueflow.db.models import Job
from queueflow.db.sessions import SessionLocal
from queueflow.sqs_client import get_queue_url, sqs
from queueflow.claims import claim_job


def process_job(job_type: str, payload: dict) -> None:
    """Simulate the business operation for a job."""
    print(f"Executing {job_type}: {payload}")

    # Simulate a slow task.
    time.sleep(3)

    print("Business operation completed.")


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

                    process_job(job.job_type, job.payload)

                    job.status = "succeeded"
                    db.commit()

                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle,
                )
                print(f"Job {job_id} succeeded and message deleted.")

            except Exception as exc:
                print(f"Processing failed: {exc}")

                try:
                    body = json.loads(message["Body"])
                    with SessionLocal() as db:
                        job = db.get(Job, body["job_id"])
                        
                        # If the worker couldnt process the job and the status is not succeeded then mark the status as false
                        if job is not None and job.status != "succeeded":
                            job.status = "failed"
                            job.last_error = str(exc)[:1000]
                            db.commit()
                except Exception as db_exc:
                    print(f"Could not record failure: {db_exc}")

                # Leave the message undeleted. SQS may redeliver it
                # after the visibility timeout expires.


if __name__ == "__main__":
    run_worker()
