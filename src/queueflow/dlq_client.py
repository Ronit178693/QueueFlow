import os

from queueflow.sqs_client import sqs


def get_dlq_url() -> str:
    # create_queue is idempotent: if the queue already exists, SQS just
    # returns its existing URL instead of erroring or duplicating it.
    response = sqs.create_queue(
        QueueName=os.getenv("SQS_DLQ_NAME", "queueflow-dlq")
    )
    return response["QueueUrl"]


def get_dlq_arn() -> str:
    dlq_url = get_dlq_url()
    response = sqs.get_queue_attributes(
        QueueUrl=dlq_url,
        AttributeNames=["QueueArn"],
    )
    return response["Attributes"]["QueueArn"]
