# FastAPI.
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException, Query
from fastapi.responses import JSONResponse

from typing import List, Dict
from uuid import uuid4

# Worker and job management.

from dramatiq.message import Message
from dramatiq.results.errors import ResultMissing, ResultTimeout

from app.tasks.ingest import ingest_document
from app.core.minio_client import MinioClient # Bucket client for MinIO/S3.
from app.tasks import results_backend

router = APIRouter()
minio_client = MinioClient()


@router.post("/upload")
async def upload_and_enqueue(
    files: List[UploadFile] = File(...),
    collection: str = Form(...)
):
    jobs: List[Dict] = []
    try:
        for f in files:
            doc_id = str(uuid4())
            s3_key = f"uploads/{doc_id}/{f.filename}"

            data = await f.read()
            minio_client.put_bytes(
                s3_key, data, content_type=f.content_type or "application/octet-stream"
            )

            msg: Message = ingest_document.send(
                doc_id=doc_id,
                s3_key=s3_key,
                filename=f.filename,
                collection=collection,
            )

            jobs.append({
                "job_id": msg.message_id,
                "queue": msg.queue_name,
                "doc_id": doc_id,
                "s3_key": s3_key,
            })
            
        return JSONResponse({"count": len(jobs), "jobs": jobs})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload/Enqueue failed: {type(e).__name__}: {e}")
    
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
    job_id: str, # TODO : Do basemodel.
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
