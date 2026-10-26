
from create_queue import get_queue_url, sqs

queue_url = get_queue_url()

sqs.set_queue_attributes(
    QueueUrl=queue_url,
    Attributes={
        "VisibilityTimeout": "5",
    },
)

print("Visibility timeout set to 5 seconds.")
