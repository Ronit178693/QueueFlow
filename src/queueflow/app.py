
from fastapi import FastAPI

from queueflow.api.jobs import router as jobs_router

app = FastAPI(
    title="QueueFlow",
    description="Reliable asynchronous job processing with SQS",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


app.include_router(jobs_router)
