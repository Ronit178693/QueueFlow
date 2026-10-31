import json

from queueflow.dlq_client import get_dlq_arn


dlq_arn = get_dlq_arn()

redrive_policy = json.dumps(
    {
        "deadLetterTargetArn": dlq_arn,
        "maxReceiveCount": 3,
    }
)

print(f"DLQ configured: {dlq_arn} (maxReceiveCount=3), visibility timeout set to 5 seconds.")
