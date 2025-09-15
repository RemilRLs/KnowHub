# FastAPI.
from fastapi import APIRouter, Depends, HTTPException

# Worker and job management.

from dramatiq.message import Message
from dramatiq.results.errors import ResultMissing, ResultTimeout


from uuid import uuid4

from app.tasks.ingest import ingest_document
from app.core.minio_client import MinioClient # Bucket client for MinIO/S3.
from app.core.job_utils import build_message_for

from app.tasks import results_backend




# Base Models.
from app.api.v1.schemas.presign import PresignReq, PresignResp, EnqueueReq
from app.api.v1.schemas.ingest import JobStatusReq


router = APIRouter()
minio_client = MinioClient()

# Check SHA-256.

@router.post("/upload/presign", response_model=PresignResp)
def presign_upload(req: PresignReq):
    doc_id = str(uuid4())
    s3_key = f"uploads/{doc_id}/{req.filename}"

    expires_in = 600 

    url = minio_client.presigned_put_url(
        key=s3_key,
        expires_seconds=expires_in
    )

    return PresignResp(
        doc_id=doc_id,
        s3_key=s3_key,
        upload_url=url,
        expires_in=expires_in,
        headers={"Content-Type": req.content_type or "application/octet-stream"},
    )


@router.post("/ingest/enqueue")
def enqueue_after_upload(req: EnqueueReq):
    if not minio_client.object_exists(req.s3_key):
        raise HTTPException(status_code=404, detail=f"S3 key not found: {req.s3_key}")
    
    msg: Message = ingest_document.send(
        doc_id=req.doc_id,
        s3_key=req.s3_key,
        filename=req.filename,
        collection=req.collection,
    )

    return {
        "job_id": msg.message_id,
        "queue": msg.queue_name,
        }

@router.get("/ingest/status")
def job_status(req: JobStatusReq = Depends()):
    msg = build_message_for(req.job_id, req.queue)

    try:
        result = results_backend.get_result(
            msg, block=req.wait_ms > 0, timeout=req.wait_ms or None
        )
        return {"status": "done", "result": result}
    except ResultMissing:
        return {"status": "pending"}
    except ResultTimeout:
        return {"status": "timeout"}


# @router.post("/upload")
# async def upload_and_enqueue(
#     files: List[UploadFile] = File(...),
#     collection: str = Form(...)
# ):
#     jobs: List[Dict] = []
#     try:
#         for f in files:
#             doc_id = str(uuid4())
#             s3_key = f"uploads/{doc_id}/{f.filename}"

#             data = await f.read()
#             minio_client.put_bytes(
#                 s3_key, data, content_type=f.content_type or "application/octet-stream"
#             )

#             msg: Message = ingest_document.send(
#                 doc_id=doc_id,
#                 s3_key=s3_key,
#                 filename=f.filename,
#                 collection=collection,
#             )

#             jobs.append({
#                 "job_id": msg.message_id,
#                 "queue": msg.queue_name,
#                 "doc_id": doc_id,
#                 "s3_key": s3_key,
#             })
            
#         return JSONResponse({"count": len(jobs), "jobs": jobs})
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Upload/Enqueue failed: {type(e).__name__}: {e}")
    