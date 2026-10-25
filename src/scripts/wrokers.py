import json
import time

from create_queue import get_queue_url, sqs


def process_job(job: dict) -> None:
    """Simulate a background job."""
    job_id = job["job_id"]
    job_type = job["job_type"]

    print(f"Processing job: {job_id}")
    print(f"Job type: {job_type}")

    # Simulate a slow task, such as generating a report.
    time.sleep(3)

    print(f"Job completed successfully: {job_id}")


def run_worker() -> None:
    queue_url = get_queue_url()
    print("Worker started. Waiting for jobs...")

    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )

        messages = response.get("Messages", [])

        if not messages:
            continue

        for message in messages:
            try:
                job = json.loads(message["Body"])

                process_job(job)

                # Delete only after successful processing.
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=message["ReceiptHandle"],
                )

                print(f"Deleted message: {message['MessageId']}")

            except Exception as exc:
                # Do not delete a failed message.
                # SQS can make it available again after its
                # visibility timeout expires.
                print(f"Job processing failed: {exc}")


if __name__ == "__main__":
    run_worker()
