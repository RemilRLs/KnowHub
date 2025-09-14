# app/api/v1/routes/ingest.py
from fastapi import APIRouter, HTTPException, Query

from dramatiq.message import Message
from dramatiq.results.errors import ResultMissing, ResultTimeout

from app.tasks.ingest import ingest_document
from app.tasks import results_backend

router = APIRouter()

@router.post("/ingest")
def enqueue_ingest(doc_id: str):
    msg = ingest_document.send(doc_id)
    return {
        "job_id": msg.message_id,
        "queue": msg.queue_name,
    }

def build_message_for(job_id: str, queue_name: str) -> Message:
    return Message(
        queue_name=queue_name,
        actor_name=ingest_document.actor_name,
        args=(),
        kwargs={},
        options={},
        message_id=job_id,
    )

@router.get("/ingest/{job_id}")
def job_status(
    job_id: str, # Do basemodel
    queue: str = Query(...),
    wait_ms: int = 0
):
    msg = build_message_for(job_id, queue)

    try:
        result = results_backend.get_result(
            msg, block=wait_ms > 0, timeout=wait_ms or None
        )
        return {"status": "done", "result": result}
    except ResultMissing:
        return {"status": "pending"}
    except ResultTimeout:
        return {"status": "timeout"}
