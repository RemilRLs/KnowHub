import logging
import pathlib
from typing import List, Optional
from time import time

# FastAPI.
from fastapi import APIRouter, Depends, HTTPException

# Worker and job management.

from dramatiq.message import Message
from dramatiq.results.errors import ResultMissing, ResultTimeout

# Redis

from app.core.redis_config import redis_client


from uuid import uuid4

from app.tasks.ingest import validate_and_promote
from app.core.minio_client import MinioClient # Bucket client for MinIO/S3.
from app.core.job_utils import build_message_for
from app.core.settings import Settings

from app.tasks import results_backend



# Base Models.
from app.api.v1.schemas.presign import PresignReq, PresignResp, EnqueueReq, BatchPresignResp, BatchPresignReq, EnqueueBatchReq, EnqueueBatchResp
from app.api.v1.schemas.ingest import JobStatusReq


router = APIRouter()
logger = logging.getLogger(__name__)

minio_client = MinioClient()

@router.post("/upload/presign/batch", response_model=BatchPresignResp)
def presign_batch(req: BatchPresignReq):
    expires_in = 600
    out = []

    for f in req.files:
        doc_id = str(uuid4())
        logger.info(f"Creating presigned upload for doc_id={doc_id}, filename={f.filename}")
        s3_key = f"uploads/{doc_id}/{f.filename}"

        headers = {"Content-Type": f.content_type or "application/octet-stream"}

        url = minio_client.presigned_put_url(
            key=s3_key,
            expires_seconds=expires_in,
        )

        out.append(PresignResp(
            doc_id=doc_id,
            s3_key=s3_key,
            upload_url=url,
            headers=headers,
            expires_in=expires_in,
        ))

    return BatchPresignResp(
        items=out
    )


@router.post("/upload/presign", response_model=PresignResp)
def presign_upload(req: PresignReq):
    """
    Handles the creation of a presigned URL for uploading a file to S3.
    Endpoint:
        POST /upload/presign
    Args:
        req (PresignReq): The request payload containing the filename and optional content type.
    Returns:
        PresignResp: A response object containing the following:
            - doc_id (str): A unique identifier for the document.
            - s3_key (str): The S3 key where the file will be stored.
            - upload_url (str): The presigned URL for uploading the file.
            - expires_in (int): The expiration time (in seconds) for the presigned URL.
            - headers (dict): Additional headers required for the upload.
    Raises:
        HTTPException: If the file extension is not allowed, a 400 status code is returned with an error message.
    Notes:
        - The allowed file extensions are retrieved from the application settings.
        - The presigned URL is generated using the MinIO client and is valid for 10 minutes (600 seconds).
        - The `Content-Type` header defaults to "application/octet-stream" if not provided in the request.
    """
    allowed_extensions = Settings.get_allowed_extensions()
    file_extension = pathlib.Path(req.filename).suffix.lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File extension not allowed: {req.filename}")

    doc_id = str(uuid4())
    logger.info(f"Creating presigned upload for doc_id={doc_id}, filename={req.filename}")
    s3_key = f"uploads/{doc_id}/{req.filename}"
    
    expires_in = 600 

    url = minio_client.presigned_put_url(
        key=s3_key,
        expires_seconds=expires_in
    )

    # Writing into Redis

    key = f"upload:{doc_id}"
    now = int(time())
    data = {
        "doc_id": doc_id,
        "s3_key": s3_key,
        "filename": req.filename,
        "status": "presigned",
        "created_at": str(now),
        "expires_at": str(now + expires_in),
    }

    pipe = redis_client.pipeline()
    pipe.hset(key, mapping=data)
    pipe.expire(key, expires_in + 120)
    pipe.execute()

    return PresignResp(
        doc_id=doc_id,
        s3_key=s3_key,
        upload_url=url,
        expires_in=expires_in,
        headers={"Content-Type": req.content_type or "application/octet-stream"},
    )


@router.post("/ingest/enqueue/batch", response_model=EnqueueBatchResp)
def enqueue_batch(req: EnqueueBatchReq):
    job_ids: List[str] = []
    file_refused: List[str] = []
    queue_name: Optional[str] = None

    for item in req.items:
        if not minio_client.object_exists(item.s3_key):
            file_refused.append(item.doc_id)
            logger.warning("S3 key not found, skipping: %s", item.s3_key)
            continue

        msg: Message = validate_and_promote.send(
            doc_id=item.doc_id,
            s3_key=item.s3_key,
            filename=item.filename,
            collection=req.collection,
            checksum_sha256=item.checksum_sha256,
        )

        job_ids.append(msg.message_id)
        if queue_name is None:
            queue_name = msg.queue_name

    return EnqueueBatchResp(
        collection=req.collection,
        job_ids=job_ids,
        file_refused=file_refused,
        queue=queue_name,
    )


    
@router.post("/ingest/enqueue")
def enqueue_after_upload(req: EnqueueReq):
    """
    Handles the enqueueing of a document for processing after it has been uploaded.
    Args:
        req (EnqueueReq): The request payload containing details about the document to be enqueued.
    Raises:
        HTTPException: If the specified S3 key does not exist, a 404 error is raised.
    Returns:
        dict: A dictionary containing the job ID and the queue name where the document was enqueued.
    """
    key = f"upload:{req.doc_id}"
    stored = redis_client.hgetall(key)
    
    if not stored or stored.get("s3_key") != req.s3_key:
        raise HTTPException(status_code=400, detail="doc_id and s3_key do not match any known upload.")

    if not stored or stored.get("doc_id") != req.doc_id:
        raise HTTPException(status_code=400, detail="doc_id and s3_key do not match any known upload.")

    if not minio_client.object_exists(req.s3_key):
        raise HTTPException(status_code=404, detail=f"S3 key not found: {req.s3_key}")
    
    msg: Message = validate_and_promote.send(
        doc_id=req.doc_id,
        s3_key=req.s3_key,
        filename=req.filename,
        collection=req.collection,
        checksum_sha256=req.checksum_sha256,
    )

    logger.info(f"Message : {msg}")

    return {
        "job_id": msg.message_id,
        "queue": msg.queue_name,
        "actor": msg.actor_name,
        }

@router.get("/ingest/status")
def job_status(req: JobStatusReq = Depends()):
    """
    Endpoint to check the status of a job.
    Args:
        req (JobStatusReq): Dependency-injected request object containing the job ID 
            and queue information, as well as optional wait time in milliseconds.
    Returns:
        dict: A dictionary containing the status of the job and, if available, the result.
            - If the job is completed, returns {"status": "done", "result": result}.
            - If the job is still pending, returns {"status": "pending"}.
            - If the request times out while waiting for the result, returns {"status": "timeout"}.
    Raises:
        ResultMissing: If the result for the given job ID is not found.
        ResultTimeout: If the operation times out while waiting for the result.
    """
    msg = build_message_for(req.job_id, req.queue, req.actor_name)

    try:
        result = results_backend.get_result(
            msg, block=req.wait_ms > 0, timeout=req.wait_ms or None
        )
        return {"status": "done", "result": result}
    except ResultMissing:
        return {"status": "pending"}
    except ResultTimeout:
        return {"status": "timeout"}

    