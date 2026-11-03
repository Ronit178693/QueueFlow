# QueueFlow
What Boto3 actually does is construct AWS-API-shaped HTTP requests (the specific format, headers, and signing scheme that AWS services expect) and send them to whatever endpoint URL it’s configured to use. By default, if you don’t specify anything, that endpoint happens to be AWS’s real servers (like sqs.ap-south-1.amazonaws.com). But that default can be overridden.

## Dead-letter queue (DLQ)

The main queue (`queueflow-jobs`) has a redrive policy pointing at `queueflow-dlq`: after a message fails processing `maxReceiveCount` (3) times, SQS automatically moves it to the DLQ instead of redelivering it forever. The main queue's `VisibilityTimeout` controls how long a message stays hidden after a worker receives it before it becomes eligible for redelivery.

Set this up with `scripts/config_dlq.py` (creates the DLQ, looks up its ARN, and applies the redrive policy + visibility timeout to the main queue). Inspect what's currently in the DLQ with `scripts/inspect_dlq.py`.

### Manual setup (for reference)

`scripts/config_dlq.py` automates everything below via boto3, but here's the equivalent manual walkthrough against LocalStack, for understanding what's actually happening under the hood.

**Step 1: Make sure LocalStack is running.**

**Step 2: Create the dead-letter queue**

```
aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name queueflow-dlq
```

The response should contain the DLQ URL.

Next, retrieve its ARN:

```
aws --endpoint-url=http://localhost:4566 sqs get-queue-attributes `
  --queue-url http://localhost:4566/000000000000/queueflow-dlq `
  --attribute-names QueueArn
```

You'll get something resembling:

```
arn:aws:sqs:ap-south-1:000000000000:queueflow-dlq
```

Use the actual ARN returned by LocalStack.

**Step 3: Configure the redrive policy**

A redrive policy tells SQS when to move a message from the main queue into the DLQ.

For this experiment, we'll set:
- `maxReceiveCount` = 3
- Main queue visibility timeout = 5 seconds

The short visibility timeout is only for our experiment, so we don't have to wait a full minute between receives.

Run the following PowerShell commands:

```powershell
$endpoint = "http://localhost:4566"

$mainUrl = (aws --endpoint-url=$endpoint sqs get-queue-url `
    --queue-name queueflow-jobs | ConvertFrom-Json).QueueUrl

$dlqUrl = (aws --endpoint-url=$endpoint sqs get-queue-url `
    --queue-name queueflow-dlq | ConvertFrom-Json).QueueUrl

$dlqArn = (aws --endpoint-url=$endpoint sqs get-queue-attributes `
    --queue-url $dlqUrl --attribute-names QueueArn |
    ConvertFrom-Json).Attributes.QueueArn

$policy = @{
    deadLetterTargetArn = $dlqArn
    maxReceiveCount = 3
} | ConvertTo-Json -Compress

$attributes = @{
    RedrivePolicy = $policy
    VisibilityTimeout = "5"
} | ConvertTo-Json -Compress

aws --endpoint-url=$endpoint sqs set-queue-attributes `
    --queue-url $mainUrl `
    --attributes $attributes
```

At this point, the main queue has a DLQ configured.

## Idempotency: what's covered, and what isn't

Job claiming (`claims.py`) uses a lease (`lease_token` + `lease_expires_at`) so only one worker owns a job at a time, and a job is only marked `succeeded` if the worker completing it still holds that lease. This correctly handles:

- Two workers racing to claim the same message.
- A worker crashing or stalling mid-processing: its lease expires and another worker can reclaim the job.
- A duplicate SQS delivery of a message for a job that's already `succeeded`: the worker sees the existing status and deletes the message without reprocessing.

**This is not full end-to-end idempotency.** There's an edge case the current design does not cover: the window between the business operation finishing and the job being marked `succeeded` in the database.

If a worker completes `process_job()` (the actual business operation, e.g. an external call or a side effect) but then crashes, loses its DB connection, or has its lease expire before `complete_job()` commits, the job is left in `processing` with an expired lease. Another worker (or the same one, after the SQS message's visibility timeout elapses) will then claim the job again and run `process_job()` a second time — even though the business operation already happened once.

The queue-level machinery (lease tokens, redelivery, status checks) only guarantees the job *record* isn't double-processed when the database bookkeeping is in a consistent state. It can't tell "the business operation already ran, we just failed to record it" apart from "the business operation never ran." Closing that gap requires **business-level idempotency**: when performing the actual operation, record a durable fact about it — e.g. store the result (or just a marker) keyed by `job_id` in whatever system the operation affects, so that re-running `process_job()` for the same `job_id` can first check "has this already been done?" and skip or no-op if so, rather than performing the side effect again.

Without that, anything in `process_job()` with a real-world side effect (charging a card, sending an email, calling a non-idempotent external API) can execute more than once for the same job.