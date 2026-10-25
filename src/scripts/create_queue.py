import os

import boto3
from dotenv import load_dotenv

load_dotenv()

sqs = boto3.client(
    "sqs",
    region_name=os.getenv("AWS_REGION", "ap-south-1"),
    endpoint_url=os.getenv("SQS_ENDPOINT_URL", "http://localhost:4566"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
)


def get_queue_url() -> str:
    response = sqs.get_queue_url(
        QueueName=os.getenv("SQS_QUEUE_NAME", "queueflow-jobs")
    )
    return response["QueueUrl"]
