
import json
import uuid

from create_queue import get_queue_url, sqs

queue_url = get_queue_url()

job = {
    "job_id": str(uuid.uuid4()),
    "job_type": "report",
    "payload": {
        "report_name": "monthly_sales",
        "period": "2026-09",
    },
}

response = sqs.send_message(
    QueueUrl=queue_url,
    MessageBody=json.dumps(job),
)

print("Job submitted:", job["job_id"])
print("SQS Message ID:", response["MessageId"])

